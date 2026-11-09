"""Authoritative, deterministic tick simulation.

The simulation is synchronous and has no asyncio dependency: callers `submit()` an action
for an agent and call `step()` once per tick. Each action is a generator that yields once
per tick it consumes and returns a result dict; failures raise `ActionError`."""

import json
import random
from dataclasses import fields
from pathlib import Path

from ..tiles import BLOCKS, DIRS
from ..world import Store, World
from .animals import Animals
from .building import Building
from .combat import Combat
from .constants import (
    CREATURE_ID0,
    DAY_TICKS,
    EVENT_QUEUE,
    MOVES,
    TARGET_R,
    VIEW_R,
    sec,
)
from .entities import Action, ActionError, Agent, Creature
from .environment import Environment
from .items import Items
from .movement import Movement
from .needs import Needs
from .observe import Observation
from .persistence import Persistence
from .sessions import Sessions
from .social import Social
from .specs import TOOL_SPECS


class Simulation(Persistence, Sessions, Movement, Building, Items, Combat, Animals, Needs, Social, Environment, Observation):
    """The world and everyone in it, advanced one tick at a time. Each mixin owns one domain."""

    ENCLOSE = ("wood_wall", "stone_wall", "door", "gate")   # what closes a room (shelter)

    def __init__(self, store: Store | str | Path, seed: int | None = None, event_log: Path | str | None = None):
        if not isinstance(store, Store):
            store = Store(store)
        self.store = store
        self.world = World(store, seed)
        self.seed = self.world.seed
        self.tick = store.get_meta("tick", 0)
        self.world.tick = self.tick
        self.agents: dict[int, Agent] = {}
        self.tokens: dict[int, str] = {}
        for aid, name, th, js in store.db.execute("SELECT id, name, token_hash, json FROM agents"):
            known = {f.name for f in fields(Agent)}            # saves from older versions may carry dropped fields
            self.agents[aid] = Agent(**{k: v for k, v in json.loads(js).items() if k in known})
            self.tokens[aid] = th
        self.by_name = {a.name: a for a in self.agents.values()}
        self.items: dict[tuple[int, int], dict] = {
            (x, y): json.loads(j) for x, y, j in store.db.execute("SELECT x, y, json FROM ground_items")}
        self.dirty_items: set = set()
        self.creatures: dict[int, Creature] = {}
        for cid, js in store.db.execute("SELECT id, json FROM creatures"):
            self.creatures[cid] = Creature(**json.loads(js))
        self.next_creature = max(self.creatures, default=CREATURE_ID0) + 1
        self._thin_herds()
        self.fires: dict[tuple, int] = {tuple(k): v for k, v in store.get_meta("fires", [])}
        self.timers: dict[tuple, list] = {(x, y): [t, kind] for x, y, t, kind in store.get_meta("timers", [])}
        self.pits: set = {tuple(p) for p in store.get_meta("pits", [])}
        for pos, pile in list(self.items.items()):   # eggs from old worlds that will never hatch: gone
            if set(pile) == {"egg"} and self.timers.get(pos, [0, ""])[1] != "hatch":
                del self.items[pos]
                self.dirty_items.add(pos)
        self.listeners: list = []  # callables(event) for spectators / logs
        self.event_log = open(event_log, "a") if event_log else None
        self.rng = random.Random()
        self.stats = {"tiles_changed": 0, "actions": 0, "deaths": 0, "chat": 0, "trades": 0, "crafts": 0}

    # ------------------------------------------------------------------ util

    def time_of_day(self) -> float:
        return (self.tick % DAY_TICKS) / DAY_TICKS

    def is_night(self) -> bool:
        """'Lights-out': the last quarter of every cycle, when glooms patrol."""
        return self.time_of_day() >= 0.75

    def clock(self) -> str:
        day = self.tick // DAY_TICKS + 1
        minutes = int(self.time_of_day() * 24 * 60)
        return f"day {day}, {minutes // 60:02d}:{minutes % 60:02d}" + (" (night)" if self.is_night() else "")

    def emit(self, type_: str, x: int, y: int, radius: int = VIEW_R, **data):
        ev = {"tick": self.tick, "type": type_, "x": x, "y": y, **data}
        for a in self.agents.values():
            if a.online and abs(a.x - x) <= radius and abs(a.y - y) <= radius:
                rel = dict(ev, dx=x - a.x, dy=y - a.y)
                del rel["x"], rel["y"]
                a.events.append(rel)
                if len(a.events) > EVENT_QUEUE:
                    del a.events[: len(a.events) - EVENT_QUEUE]
                if a.action is not None:
                    a.action.seen_events.append(rel)
        if self.event_log:
            self.event_log.write(json.dumps(ev, separators=(",", ":")) + "\n")
        for fn in self.listeners:
            fn(ev)
        return ev

    def set_tile(self, x, y, ground=None, block=None, by: Agent | None = None, cause=None):
        self.world.set(x, y, ground=ground, block=block)
        self.stats["tiles_changed"] += 1
        g, b = self.world.ground(x, y), self.world.block(x, y)
        if g == "tilled":
            self.pits.add((x, y))
        if g in ("water", "deep_water"):
            for dx, dy in DIRS.values():
                if self.world.ground(x + dx, y + dy) == "tilled":
                    self.pits.add((x + dx, y + dy))
        info = {"x": x, "y": y, "ground": g, "block": b}
        if by is not None and by.action is not None:
            by.action.tiles.append(info)
        self.emit("tile", x, y, ground=g, block=b, by=by.name if by else None, cause=cause)

    def add_items(self, x, y, items: dict):
        if not items:
            return
        pile = self.items.setdefault((x, y), {})
        for k, n in items.items():
            pile[k] = pile.get(k, 0) + n
        self.dirty_items.add((x, y))
        if "egg" in items and (x, y) not in self.timers:   # an egg left on the ground hatches
            self.timers[(x, y)] = [self.tick + sec(180), "hatch"]

    def entity_at(self, x, y):
        for a in self.agents.values():
            if a.online and a.hp > 0 and (a.x, a.y) == (x, y):
                return a
        for c in self.creatures.values():
            if (c.x, c.y) == (x, y):
                return c
        return None

    def target(self, a: Agent, args) -> tuple[int, int]:
        """The tile an action is aimed at: `dir` (the adjacent tile that way), or an absolute `x`, `y` within
        TARGET_R (a walking player's client may be up to a tile ahead of the server)."""
        if "x" in args and "y" in args and args.get("dir") is None:
            try:
                x, y = int(args["x"]), int(args["y"])
            except (TypeError, ValueError):
                raise ActionError("bad_args", "x and y must be integers")
            if max(abs(x - a.x), abs(y - a.y)) > TARGET_R:            # your own tile too (a flower underfoot)
                raise ActionError("out_of_range", f"({x},{y}) is not within {TARGET_R} tiles of you")
            return x, y
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "aim with dir (N, E, S or W) or with x and y")
        dx, dy = DIRS[d]
        return a.x + dx, a.y + dy

    def near_block(self, a: Agent, block: str, r: int = 2) -> bool:
        return any(self.world.block(a.x + dx, a.y + dy) == block
                   for dy in range(-r, r + 1) for dx in range(-r, r + 1))

    def sheltered(self, x, y) -> bool:
        """Inside a room: the area around (x, y) is closed off by walls/doors/gates within 160 tiles
        (same rule the client uses to draw roofs). Next to 3+ walls also counts, as before."""
        if sum(1 for dx, dy in DIRS.values() if BLOCKS[self.world.get(x + dx, y + dy)[1]].wall) >= 3:
            return True
        seen, stack = {(x, y)}, [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if len(seen) > 160:
                return False
            for dx, dy in DIRS.values():
                n = (cx + dx, cy + dy)
                if n not in seen and self.world.block(*n) not in self.ENCLOSE:
                    seen.add(n)
                    stack.append(n)
        xs, ys = [p[0] for p in seen], [p[1] for p in seen]
        w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        return w <= 14 and h <= 14 and len(seen) >= 0.6 * w * h   # same compactness rule as the client's roofs

    def wait(self, a: Agent, seconds: float):
        """Take `seconds` of game time (doubled when exhausted). The starting tick counts."""
        n = sec(seconds)
        if a.action is not None:
            a.action.expected = max(a.action.expected, a.action.ticks - 1 + n)
        for _ in range(n - 1):
            yield


    # ------------------------------------------------------------- agents

    def interrupt(self, a: Agent, why="interrupted"):
        act = a.action
        if act is not None:
            a.action = None
            act.gen.close()
            act.finish({"ok": False, "status": "interrupted", "error": "interrupted", "detail": why}, self)

    def submit(self, a: Agent, tool: str, args: dict | None = None, on_done=None) -> Action:
        args = args or {}
        fn = getattr(self, f"_tool_{tool}", None)
        if fn is None or tool not in TOOL_SPECS:
            act = Action(a, tool, args, iter(()), on_done)
            act.finish({"ok": False, "status": "failed", "error": "unknown_tool",
                        "detail": f"tools: {', '.join(TOOL_SPECS)}"}, self)
            return act
        act = Action(a, tool, args, fn(a, args), on_done)
        moving = a.action is not None and a.action.tool in MOVES
        if moving and tool not in MOVES and tool != "stop":
            # walking or running: try it right away; if it takes no time (picking a flower, picking up), it happens
            # on the move and the walk goes on. If it needs time (chopping), it replaces the walk as usual.
            walk, a.action = a.action, act
            act.started_tick, act.ticks = self.tick, 1
            self.passing = a
            try:
                next(act.gen)
            except StopIteration as stop:
                a.action = walk
                self.stats["actions"] += 1
                act.finish({"ok": True, "status": "done", **(stop.value or {})}, self)
                return act
            except ActionError as e:
                a.action = walk
                act.finish({"ok": False, "status": "failed", "error": e.code, "detail": e.detail}, self)
                return act
            finally:
                self.passing = None
            a.action = walk                           # it needs time: stop walking, then carry on with it
            self.interrupt(a, f"replaced by {tool}")
            a.action = act
            return act
        if a.action is not None:
            self.interrupt(a, f"replaced by {tool}")
        a.action = act
        return act

    # ------------------------------------------------------------- tick

    def step(self):
        self.tick += 1
        self.world.tick = self.tick
        self.rng.seed(self.seed * 1_000_003 + self.tick)
        for aid in sorted(self.agents):
            a = self.agents[aid]
            act = a.action
            if act is None or not a.online:
                continue
            if act.started_tick is None:
                act.started_tick = self.tick
            act.ticks += 1
            try:
                next(act.gen)
            except StopIteration as stop:
                self.stats["actions"] += 1
                act.finish({"ok": True, "status": "done", **(stop.value or {})}, self)
            except ActionError as e:
                self.stats["actions"] += 1
                act.finish({"ok": False, "status": "failed", "error": e.code, "detail": e.detail}, self)
        self.step_creatures()
        self.step_environment()
        self.step_needs()

    # ------------------------------------------------------- persistence


