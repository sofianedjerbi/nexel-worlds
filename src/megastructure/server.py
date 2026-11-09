"""Authoritative game server: fixed-rate tick loop + WebSocket Agent API.

    uv run python -m megastructure.server --world default --port 7777
"""

import argparse
import asyncio
import collections
import json
import logging
import resource
import signal
import time
from pathlib import Path

from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Response

from .sim import TICK_HZ, TOOL_SPECS, ActionError, Simulation
from .tiles import GROUNDS, RECIPES

log = logging.getLogger("megastructure")
PROTOCOL = 1
# Actions are already paced by game time (one in flight per agent), so these only stop floods.
LIMITS = {"act": (900, 60.0), "observe": (900, 60.0), "say": (20, 60.0), "shout": (3, 60.0)}
FLUSH_EVERY = 10 * TICK_HZ  # ticks (10 s)
WEB = Path(__file__).parent / "web"


def serve_http(connection, request):
    """Plain HTTP GETs (no websocket upgrade) get the browser client."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None
    path = request.path.split("?")[0]
    if path in ("/", "/index.html"):
        return _file(WEB / "index.html", "text/html; charset=utf-8")
    folder, _, name = path.lstrip("/").partition("/")
    if folder in STATIC:
        root = (WEB / folder).resolve()
        f = (root / name).resolve()
        if f.parent == root and f.is_file() and f.suffix in CONTENT_TYPES:   # no subfolders, no "..": only our files
            return _file(f, CONTENT_TYPES[f.suffix], cache=STATIC[folder])
    return connection.respond(404, "not found\n")


STATIC = {"assets": "max-age=3600", "js": "no-cache", "css": "no-cache"}   # folder -> Cache-Control
CONTENT_TYPES = {".png": "image/png", ".ttf": "font/ttf", ".txt": "text/plain",
                 ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}


def _file(path: Path, ctype: str, cache: str = "no-cache") -> Response:
    body = path.read_bytes()
    return Response(200, "OK", Headers([("Content-Type", ctype), ("Content-Length", str(len(body))),
                                        ("Cache-Control", cache)]), body)


def rss_mb() -> float:
    # macOS reports ru_maxrss in bytes (peak resident set)
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


class RateLimiter:
    def __init__(self):
        self.hits = collections.defaultdict(collections.deque)

    def allow(self, key: str) -> bool:
        n, window = LIMITS[key]
        q, now = self.hits[key], time.monotonic()
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= n:
            return False
        q.append(now)
        return True


class GameServer:
    def __init__(self, world_dir: Path, seed: int | None = None, dev: bool = False):
        self.dev = dev  # enables dev_give (QA only; never on a public server)
        world_dir.mkdir(parents=True, exist_ok=True)
        self.sim = Simulation(world_dir / "world.sqlite", seed=seed, event_log=world_dir / "events.jsonl")
        self.conns: dict[int, object] = {}  # agent id -> connection
        self.notify: dict[int, object] = {}  # agent id -> callable(dict) pushing a message to that agent
        self.spectators: dict = {}  # queue -> watched rect (x, y, w, h) or None
        self.sim.listeners.append(self._broadcast)
        self.tick_ms = collections.deque(maxlen=250)
        self.started = time.time()
        self.stopping = asyncio.Event()

    # ---------------------------------------------------------------- tick
    async def tick_loop(self):
        loop = asyncio.get_running_loop()
        period = 1.0 / TICK_HZ
        nxt = loop.time()
        while not self.stopping.is_set():
            t0 = time.perf_counter()
            chunks0 = len(self.sim.world.chunks)
            self.sim.step()
            self.push_ticks()
            t1 = time.perf_counter()
            if self.sim.tick % FLUSH_EVERY == 0:
                self.sim.flush()
                self.sim.maintain()
            dt = (time.perf_counter() - t0) * 1000
            self.tick_ms.append(dt)
            if dt > 50:
                log.warning("slow tick %d: %.0f ms (step %.0f ms, chunks %d -> %d)", self.sim.tick, dt,
                            (t1 - t0) * 1000, chunks0, len(self.sim.world.chunks))
            nxt += period
            delay = nxt - loop.time()
            if delay < -1.0:  # fell far behind (e.g. laptop sleep): don't try to catch up
                nxt = loop.time()
                delay = 0
            await asyncio.sleep(max(0.0, delay))

    def metrics(self) -> dict:
        ms = sorted(self.tick_ms) or [0.0]
        return {
            "tick": self.sim.tick,
            "uptime_s": round(time.time() - self.started),
            "agents_online": sum(1 for a in self.sim.agents.values() if a.online),
            "agents_total": len(self.sim.agents),
            "creatures": collections.Counter(c.kind for c in self.sim.creatures.values()),
            "chunks_loaded": len(self.sim.world.chunks),
            "tick_ms_p50": round(ms[len(ms) // 2], 2),
            "tick_ms_max": round(ms[-1], 2),
            "rss_peak_mb": round(rss_mb(), 1),
            **self.sim.stats,
        }

    # ----------------------------------------------------------- spectators
    def _broadcast(self, ev):
        if not self.spectators:
            return
        msg = json.dumps({"type": "event", "ev": ev})
        for q in list(self.spectators):
            if q.qsize() < 2000:
                q.put_nowait(msg)

    def entities_in(self, x, y, w, h) -> list:
        ents = [{"kind": "agent", "name": a.name, "id": a.id, "x": a.x, "y": a.y, "hp": a.hp,
                 "doing": a.action.tool if a.action else None, "weapon": self.sim.best_weapon(a),
                 "dir": a.action.args.get("dir") if a.action else None,
                 "tid": a.action.args.get("target") if a.action else None,
                 "with": a.action.args.get("with") if a.action else None,
                 "item": a.action.args.get("item") if a.action else None,
                 "run": bool(a.action.args.get("run")) if a.action else False, "sail": a.sailing}
                for a in self.sim.agents.values() if a.online and x <= a.x < x + w and y <= a.y < y + h]
        ents += [{"kind": c.kind, "id": c.id, "x": c.x, "y": c.y, "hp": c.hp, "love": c.love > self.sim.tick, "scared": c.scared > self.sim.tick}
                 for c in self.sim.creatures.values() if x <= c.x < x + w and y <= c.y < y + h]
        return ents

    def mail_in(self, x, y, w, h) -> list:
        return [[mx, my, len(m["letters"])] for (mx, my), m in self.sim.world.meta.items()
                if m.get("letters") and x <= mx < x + w and y <= my < y + h]

    def troughs_in(self, x, y, w, h) -> list:
        """Troughs with feed in them (the client draws hay in the box)."""
        return [[tx, ty] for (tx, ty), m in self.sim.world.meta.items()
                if m.get("items") and x <= tx < x + w and y <= ty < y + h and self.sim.world.block(tx, ty) == "trough"]

    def items_in(self, x, y, w, h) -> list:
        return [[ix, iy, pile] for (ix, iy), pile in self.sim.items.items() if pile and x <= ix < x + w and y <= iy < y + h]

    def push_ticks(self):
        """Every tick, each spectator gets the entities inside the rect it watches; agents whose
        multi-tick action just started get a progress notice (so clients can show a bar at once)."""
        for aid, push in list(self.notify.items()):
            act = self.sim.agents[aid].action
            if (act is not None and act.started_tick == self.sim.tick and act.tool not in ("step", "move_to", "walk")
                    and act.expected >= 2):
                push({"type": "progress", "tool": act.tool, "ticks": act.expected, "tick_hz": TICK_HZ})
        if not self.spectators:
            return
        head = {"type": "tick", "tick": self.sim.tick, "time": self.sim.clock(), "night": self.sim.is_night(),
                "phase": round(self.sim.time_of_day(), 4)}
        for q, rect in list(self.spectators.items()):
            if rect is not None and q.qsize() < 2000:
                q.put_nowait(json.dumps({**head, "entities": self.entities_in(*rect), "items": self.items_in(*rect),
                                         "mail": self.mail_in(*rect), "troughs": self.troughs_in(*rect),
                                         "fires": [[fx, fy] for fx, fy in self.sim.fires
                                                   if rect[0] <= fx < rect[0] + rect[2] and rect[1] <= fy < rect[1] + rect[3]]},
                                        separators=(",", ":")))

    def region(self, x, y, w, h) -> dict:
        w, h = min(int(w), 256), min(int(h), 256)
        world = self.sim.world
        rows = ["".join(world.char(i, j) for i in range(x, x + w)) for j in range(y, y + h)]
        ground = ["".join(GROUNDS[world.get(i, j)[0]].char for i in range(x, x + w)) for j in range(y, y + h)]
        return {"x": x, "y": y, "w": w, "h": h, "rows": rows, "ground": ground, "entities": self.entities_in(x, y, w, h), "tick": self.sim.tick, "time": self.sim.clock(),
                "night": self.sim.is_night(), "phase": round(self.sim.time_of_day(), 4)}

    # ------------------------------------------------------------- handlers
    async def handler(self, ws):
        path = ws.request.path if ws.request else "/agent"
        try:
            if path.startswith("/spectate"):
                await self.spectate(ws)
            else:
                await self.agent_session(ws)
        except ConnectionClosed:
            pass

    async def spectate(self, ws):
        q: asyncio.Queue = asyncio.Queue()
        self.spectators[q] = None

        async def pump():
            while True:
                await ws.send(await q.get())

        pumper = asyncio.create_task(pump())
        try:
            await ws.send(json.dumps({"type": "hello", "tick": self.sim.tick, "protocol": PROTOCOL}))
            async for raw in ws:
                msg = json.loads(raw)
                op = msg.get("op")
                if op == "watch":
                    self.spectators[q] = (int(msg["x"]), int(msg["y"]), min(int(msg["w"]), 200), min(int(msg["h"]), 200))
                    continue
                if op == "region":
                    out = self.region(int(msg["x"]), int(msg["y"]), msg.get("w", 64), msg.get("h", 48))
                elif op == "metrics":
                    out = self.metrics()
                elif op == "recipes":
                    out = {"recipes": {k: {"inputs": r.inputs, "output": r.output, "station": r.station}
                                       for k, r in RECIPES.items()}}
                elif op == "agents":
                    out = {"agents": [dict(a.to_json(), online=a.online) for a in self.sim.agents.values()]}
                else:
                    out = {"error": "unknown op"}
                await ws.send(json.dumps({"type": "reply", "id": msg.get("id"), **out}))
        finally:
            self.spectators.pop(q, None)
            pumper.cancel()

    async def agent_session(self, ws):
        out: asyncio.Queue = asyncio.Queue()

        def reply(mid, ok=True, **kw):
            out.put_nowait(json.dumps({"id": mid, "ok": ok, **kw}, separators=(",", ":")))

        async def writer():
            while True:
                await ws.send(await out.get())

        wtask = asyncio.create_task(writer())
        agent = None
        limits = RateLimiter()
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    mid, op = msg.get("id"), msg.get("op")
                except (json.JSONDecodeError, AttributeError):
                    reply(None, False, error="bad_json")
                    continue
                if op == "ping":
                    reply(mid, tick=self.sim.tick)
                    continue
                if op == "metrics":
                    reply(mid, metrics=self.metrics())
                    continue
                if agent is None:
                    if op != "hello":
                        reply(mid, False, error="hello_first")
                        continue
                    try:
                        agent = self.sim.login(str(msg.get("name", "")), str(msg.get("token", "")),
                                               str(msg.get("persona", "")))
                    except ActionError as e:
                        reply(mid, False, error=e.code, detail=e.detail)
                        continue
                    old = self.conns.get(agent.id)
                    if old is not None and old is not ws:
                        await old.close(4000, "logged in elsewhere")
                        agent.online = True
                    self.conns[agent.id] = ws
                    self.notify[agent.id] = lambda m: out.put_nowait(json.dumps(m, separators=(",", ":")))
                    log.info("agent %s (#%d) connected from %s", agent.name, agent.id, ws.remote_address)
                    reply(mid, agent=agent.to_json(), tick=self.sim.tick, protocol=PROTOCOL, tick_hz=TICK_HZ)
                    continue
                if op == "observe":
                    if not limits.allow("observe"):
                        reply(mid, False, error="rate_limited", detail="observe: 120/min")
                        continue
                    reply(mid, obs=self.sim.observe(agent))
                elif op == "act":
                    tool, args = str(msg.get("tool", "")), msg.get("args") or {}
                    if not isinstance(args, dict):
                        reply(mid, False, error="bad_args", detail="args must be an object")
                        continue
                    if not limits.allow("act") or (tool in ("say", "shout") and not limits.allow(tool)):
                        reply(mid, False, error="rate_limited", detail=f"limits: {LIMITS}")
                        continue

                    def done(result, mid=mid):
                        ok = result.pop("ok", True)
                        if ok:
                            reply(mid, result=result)
                        else:
                            reply(mid, False, error=result.get("error"), detail=result.get("detail"), result=result)

                    self.sim.submit(agent, tool, args, on_done=done)
                elif op == "dev_time" and self.dev:      # jump to a time of day (0..1, 0.75+ is night)
                    from .sim import DAY_TICKS
                    day = self.sim.tick // DAY_TICKS
                    self.sim.tick = day * DAY_TICKS + int(float(msg.get("phase", 0.8)) * DAY_TICKS)
                    reply(mid, tick=self.sim.tick)
                elif op == "dev_skip" and self.dev:      # fast-forward the simulation (QA)
                    for _ in range(min(int(float(msg.get("seconds", 10)) * TICK_HZ), 20000)):
                        self.sim.step()
                    reply(mid, tick=self.sim.tick)
                elif op == "dev_teleport" and self.dev:
                    agent.x, agent.y = int(msg["x"]), int(msg["y"])
                    reply(mid, x=agent.x, y=agent.y)
                elif op == "dev_damage" and self.dev:
                    self.sim.damage(agent, int(msg.get("n", 10)), "dev")
                    reply(mid, hp=agent.hp)
                elif op == "dev_stamp" and self.dev:     # paint ASCII rows (tile chars) at x, y (QA builds)
                    from .tiles import BLOCKS as _BL, GROUNDS as _GR
                    bch, gch = {b.char: b.name for b in _BL}, {g.char: g.name for g in _GR}
                    x0, y0 = int(msg["x"]), int(msg["y"])
                    for j, row in enumerate(list(msg.get("rows") or [])[:200]):
                        for i, ch in enumerate(str(row)[:200]):
                            if ch in gch:
                                self.sim.set_tile(x0 + i, y0 + j, ground=gch[ch], block="none")
                            elif ch in bch:
                                self.sim.set_tile(x0 + i, y0 + j, ground="grass", block=bch[ch])
                    reply(mid)
                elif op == "dev_give" and self.dev:
                    for k, n in dict(msg.get("items") or {}).items():
                        agent.add(str(k), int(n))
                    reply(mid, inventory=agent.inventory)
                elif op == "tools":
                    reply(mid, tools=TOOL_SPECS)
                elif op == "recipes":
                    reply(mid, recipes={k: {"inputs": r.inputs, "output": r.output, "station": r.station,
                                            "ticks": r.ticks} for k, r in RECIPES.items()})
                else:
                    reply(mid, False, error="unknown_op",
                          detail="ops: hello, observe, act, tools, recipes, metrics, ping")
        finally:
            if agent is not None and self.conns.get(agent.id) is ws:
                del self.conns[agent.id]
                self.notify.pop(agent.id, None)
                self.sim.logout(agent)
                log.info("agent %s disconnected", agent.name)
            await asyncio.sleep(0.05)  # let queued replies drain
            wtask.cancel()

    async def run(self, host: str, port: int):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.stopping.set)
        ticker = asyncio.create_task(self.tick_loop())
        async with serve(self.handler, host, port, max_size=2**20, process_request=serve_http) as server:
            log.info("megastructure listening on ws://%s:%d (seed %d, tick %d) - open http://%s:%d/ to watch",
                     host, port, self.sim.seed, self.sim.tick, host, port)
            await self.stopping.wait()
            log.info("shutting down")
            server.close()
        ticker.cancel()
        self.sim.close()
        log.info("saved at tick %d", self.sim.tick)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--world", default="default")
    p.add_argument("--saves", default="saves")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7777)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--dev", action="store_true", help="enable dev_give for automated QA")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    gs = GameServer(Path(args.saves) / args.world, seed=args.seed, dev=args.dev)
    asyncio.run(gs.run(args.host, args.port))


if __name__ == "__main__":
    main()
