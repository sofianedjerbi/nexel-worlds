"""Authoritative game server: fixed-rate tick loop + WebSocket Agent API.

    uv run python -m nexel_worlds.server --world default --port 7777
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
from websockets.exceptions import ConnectionClosed

from .admin import Admins
from .devtools import dev_op
from .gate import Gate
from .limits import LIMITS, RateLimiter
from .rules import rules_table
from .sim import DAY_TICKS, TICK_HZ, TOOL_SPECS, ActionError, Simulation
from .tiles import RECIPES
from .ticking import Ticking
from .views import Views
from .web_static import serve_http, set_bundle, web_stamp

log = logging.getLogger("nexel_worlds")
PROTOCOL = 1
RULES_TABLE = rules_table()


def rss_mb() -> float:
    # macOS reports ru_maxrss in bytes (peak resident set)
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


class GameServer(Views, Ticking):
    def __init__(self, world_dir: Path, seed: int | None = None, dev: bool = False, accounts: str = "", admins=()):
        self.dev = dev  # enables dev_give (QA only; never on a public server)
        world_dir.mkdir(parents=True, exist_ok=True)
        self.gate = Gate(accounts, world_dir) if accounts else None   # a world that asks who you are (gate.py)
        self.sim = Simulation(world_dir / "world.sqlite", seed=seed, event_log=world_dir / "events.jsonl")
        if self.sim.store.get_meta("tick", None) is None:   # a new world starts in the morning (a fifth of a day in), not at sunrise: its first picture was the rose-blue of dawn, which reads as dusk
            self.sim.tick = self.sim.world.tick = DAY_TICKS // 5
        self.conns: dict[int, object] = {}  # agent id -> connection
        self.notify: dict[int, object] = {}  # agent id -> callable(dict) pushing a message to that agent
        self.spectators: dict = {}  # queue -> watched rect (x, y, w, h) or None
        self.players: dict = {}     # queue -> the id of who plays on that screen (the page says: `me`), for what it hears (views.py)
        self.behind: set = set()    # spectators that missed events (Views._broadcast)
        self.sim.listeners.append(self._broadcast)
        self.sim.screens = lambda: [r for r in self.spectators.values() if r]   # (nothing comes or goes on a screen: spawning.py)
        self.tick_ms = collections.deque(maxlen=250)
        self.tick_parts = collections.deque(maxlen=250)      # (each tick's parts: its step's ms, whether it flushed the world to disk)
        self.init_clock()              # (the world's ticks on the wall's clock, till a test's page drives them: ticking.py)
        self.started = time.time()
        self.stopping = asyncio.Event()
        self.admin = Admins(self, world_dir, admins)      # (an operator, out of the world: the server's /commands, admin.py)

    # ---------------------------------------------------------------- tick
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
            "tick_worst": dict(zip(("tick", "ms", "step_ms", "flushed"), max(self.tick_parts, key=lambda t: t[1], default=(0, 0, 0, False)))),   # (the slowest of them, and what it was)
            "rss_peak_mb": round(rss_mb(), 1),
            **self.sim.stats,
        }

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
            await ws.send(json.dumps({"type": "hello", "tick": self.sim.tick, "protocol": PROTOCOL, "web": web_stamp(), "swim_sprint": True, "floors": True, "rules": RULES_TABLE}))      # (the world's rules, for a screen: rules.py)
            async for raw in ws:
                msg = json.loads(raw)
                op = msg.get("op")
                if op == "watch":
                    self.spectators[q] = (int(msg["x"]), int(msg["y"]), min(int(msg["w"]), 200), min(int(msg["h"]), 200))
                    continue
                if op == "me":
                    self.players[q] = msg.get("id")
                    continue
                if op == "region":
                    a = (int(msg["x"]), int(msg["y"]), int(msg.get("w", 64)), int(msg.get("h", 48)))
                    near = not msg.get("far") or self.far_near(self.spectators.get(q), *a)
                    out = self.region(*a) if near and (not msg.get("far") or self.far_ready(*a)) else {"later": True, "x": a[0], "y": a[1], "out": not near}   # (views.py far_near, far_ready. out: past what this page is given far: it never comes, state.js farLeft)
                elif op == "metrics":
                    out = self.metrics()
                elif op == "who" and self.gate:                # the name this account already plays here, if any
                    account = await asyncio.to_thread(self.gate.account, str(msg.get("ticket", "")), ws.request.headers.get("Host", ""))
                    out = {"who": True, "name": self.sim.agents[self.sim.owners[account]].name if account in self.sim.owners else None}
                elif op == "agents":
                    out = {"agents": [dict(a.to_json(), online=a.online, **({"admin": True} if self.admin.is_admin(a) else {})) for a in self.sim.agents.values()]}
                else:
                    out = {"error": "unknown op"}
                await ws.send(json.dumps({"type": "reply", "id": msg.get("id"), **out}))
        finally:
            self.spectators.pop(q, None)
            self.players.pop(q, None)
            pumper.cancel()

    async def agent_session(self, ws):
        out: asyncio.Queue = asyncio.Queue()

        def reply(mid, ok=True, **kw):
            out.put_nowait(json.dumps({"id": mid, "ok": ok, **kw}, separators=(",", ":")))

        async def writer():
            while True:
                await ws.send(await out.get())

        wtask = asyncio.create_task(writer())
        agent, account, refused = None, None, 0
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
                    name, token, race = str(msg.get("name", "")), str(msg.get("token", "")), str(msg.get("race", ""))
                    try:
                        if self.gate:                          # a ticket (a person) or this world's key (a local program)
                            account = await asyncio.to_thread(self.gate.who, msg, ws.request.headers.get("Host", ""))
                        agent = (self.sim.enter(account, name, token, race) if account
                                 else self.sim.login(name, token, str(msg.get("persona", "")), race))
                    except ActionError as e:
                        reply(mid, False, error=e.code, detail=e.detail)
                        refused += 1
                        if refused >= 10:                      # (nobody honest is turned away ten times)
                            break
                        continue
                    if self.admin.refuse(agent):                   # a banned name (admin.py)
                        reply(mid, False, error="banned", detail="You are banned from this world"); break  # noqa: E702
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
                elif op == "hold":                                 # what is in your hand (the bar's selected slot): the others see it in your paw (views.py)
                    agent.held = str(msg["item"])[:40] if msg.get("item") else None; reply(mid, held=agent.held)  # noqa: E702
                elif op in ("dev_lockstep", "dev_step") and self.dev and not account:   # (the browser tests' one clock: ticking.py)
                    self.dev_clock(ws, op, msg, lambda r, mid=mid: reply(mid, **r))
                elif op.startswith("dev_") and self.dev and not account:  # QA tools, only with --dev, never for who came by ticket
                    t0 = self.sim.tick
                    reply(mid, **dev_op(self.sim, agent, op, msg))
                    self.jumped(t0)
                elif op in ("cmd", "cmds") and limits.allow("act"):     # the chat line's /commands (admin.py)
                    t0 = self.sim.tick
                    reply(mid, **(self.admin.run(agent, str(msg.get("line", ""))) if op == "cmd" else self.admin.cmds(agent)))
                    self.jumped(t0)
                elif op == "tools":
                    reply(mid, tools=TOOL_SPECS)
                elif op == "recipes":
                    reply(mid, recipes={k: {"inputs": r.inputs, "output": r.output, "station": r.station,
                                            "ticks": r.ticks} for k, r in RECIPES.items()})
                else:
                    reply(mid, False, error="unknown_op", detail="ops: hello, observe, act, hold, tools, recipes, metrics, ping")
        finally:
            if self.driver is ws:                                 # (a driver gone: the world back on the wall's clock, never left frozen)
                self.lockstep(ws, {"on": False})
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
        async with serve(self.handler, host, port, max_size=2**20,
                         process_request=lambda c, r: serve_http(c, r, self.gate and self.gate.url)) as server:
            log.info("nexel_worlds listening on ws://%s:%d (seed %d, tick %d) - open http://%s:%d/ to watch",
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
    p.add_argument("--accounts", default="", help="ask who players are: the account service, e.g. http://127.0.0.1:7780")
    p.add_argument("--admin", action="append", default=[], help="NAME is an admin (repeatable; also saves/<world>/admins.txt, /op)")
    p.add_argument("--bundle", action="store_true", help="send the client as few files (web_bundle.py): for a phone or a far player")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    set_bundle(args.bundle)
    gs = GameServer(Path(args.saves) / args.world, seed=args.seed, dev=args.dev, accounts=args.accounts, admins=args.admin)
    asyncio.run(gs.run(args.host, args.port))


if __name__ == "__main__":
    main()
