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
from .bodies import Bodies
from .building import Building
from .combat import Combat
from .constants import (
    CREATURE_ID0,
    DAY_TICKS,
    EVENT_QUEUE,
    ASIDE,
    MEANWHILE,
    MOVES,
    sec,
)
from .entities import CREATURES, Action, ActionError, Agent, Creature, failure
from .environment import Environment
from .hearing import hears
from .items import Items
from .movement import Movement
from .progress import Progress
from .climbing import Climbing
from .spawning import Spawning
from .storeys import Storeys
from .underground import Underground
from .wear import Wear
from .waters import Waters
from .wild import Wild
from .needs import Needs
from .observe import Observation
from .persistence import Persistence
from .sessions import Sessions, owners_of
from .social import Social
from .specs import TOOL_SPECS


class Simulation(Persistence, Sessions, Bodies, Movement, Progress, Spawning, Underground, Building, Storeys, Climbing, Items, Combat, Animals, Wild, Wear, Needs, Social, Environment, Waters, Observation):
    """The world and everyone in it, advanced one tick at a time. Each mixin owns one domain."""

    ENCLOSE = ("wood_wall", "stone_wall", "door", "gate")   # what closes a room (shelter)
    current = None                                      # the action being stepped right now (wait() marks its length on it)

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
        self.owners = owners_of(store.db)                      # (sessions.py)
        self.old_vitals(store.get_meta("vitals", 1) < 2)       # (saved when health and food were 0 to 100: needs.py)
        self.by_name = {a.name: a for a in self.agents.values()}
        self.ticking: set[tuple[int, int]] = set()        # chunks where creatures live this tick (spawning.py)
        self.screens = lambda: ()                         # the rectangles (x, y, w, h) the screens watch now: the server says (spawning.py: in_sight)
        self.item_since: dict[tuple[int, int], int] = {}   # when each pile last grew (the magnet waits a moment)
        self.item_left: dict[tuple[int, int], int] = {}    # a pile its dropper let go of: not drawn back to them while they stay by it (progress.py)
        self.items: dict[tuple[int, int], dict] = {
            (x, y): json.loads(j) for x, y, j in store.db.execute("SELECT x, y, json FROM ground_items")}
        self.dirty_items: set = set()
        self.creatures: dict[int, Creature] = {}
        for cid, js in store.db.execute("SELECT id, json FROM creatures"):
            self.creatures[cid] = Creature(**json.loads(js))
        self.next_creature = max(self.creatures, default=CREATURE_ID0) + 1
        self._thin_herds()
        self.open_floors(store)                            # (storeys.py: the blocks built over the ground; once, the old roofs)
        self.open_water(store)                             # (waters.py: water that flows; once, an old save's water made sources)
        self.thin_wild(store)                              # (spawning.py: once, when a world meets the rarer-mobs rules)
        self.fires: dict[tuple, int] = {tuple(k): v for k, v in store.get_meta("fires", [])}
        self.timers: dict[tuple, list] = {(x, y): [t, kind] for x, y, t, kind in store.get_meta("timers", [])}
        self.old_items()                                   # (an old save's: persistence.py)
        self.listeners: list = []  # callables(event) for spectators / logs
        self.event_log = open(event_log, "a") if event_log else None
        self.rng = random.Random()
        self.luck = 1.0                                    # what a creature's chances of leaving a thing are multiplied by (a dev tool: tests)
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

    def emit(self, type_: str, x: int, y: int, **data):
        """Something happened at (x, y): told to who perceives it (hearing.py: how far each kind carries), written
        in the world's log, and passed to the screens (views.py)."""
        ev = {"tick": self.tick, "type": type_, "x": x, "y": y, **data}
        for a in self.agents.values():
            if a.online and hears(a, ev):
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

    def mat(self, x, y, runs) -> str:
        """What a tile event tells a screen it is made of: the block put on its top (landblocks.py), "~", its highest
        stone cell (world.py made_of; web/js tiles.js putMat)."""
        return f"{self.placed.mat(x, y, runs)}~{self.world.stone(x, y)}"

    def set_cell(self, x, y, z, solid: bool, by: Agent | None = None, cause=None):
        """Fill or empty one cell of the land (digging, building up)."""
        self.world.set_cell(x, y, z, solid)
        self.set_tile(x, y, by=by, cause=cause)

    def set_tile(self, x, y, ground=None, block=None, by: Agent | None = None, cause=None, level=None, roof=None, head=None):
        if level is not None or roof is not None or head is not None:
            self.raze(x, y)                                # (the land laid out anew: what was built over it goes, and the water on it)
            self.water.clear(x, y)
        self.world.set(x, y, ground=ground, block=block, level=level, roof=roof, head=head)
        self.stats["tiles_changed"] += 1
        g, b = self.world.ground(x, y), self.world.block(x, y)
        info = {"x": x, "y": y, "ground": g, "block": b}
        if by is not None and by.action is not None:
            by.action.tiles.append(info)
        self.emit("tile", x, y, ground=g, block=b, by=by.name if by else None, cause=cause, col=(runs := self.land_runs(x, y)), mat=self.mat(x, y, runs))

    def add_items(self, x, y, items: dict):
        if not items:
            return
        pile = self.items.setdefault((x, y), {})
        for k, n in items.items():
            pile[k] = pile.get(k, 0) + n
        self.dirty_items.add((x, y))
        self.item_since[(x, y)] = self.tick
        if "egg" in items and (x, y) not in self.timers:   # an egg left on the ground hatches
            self.timers[(x, y)] = [self.tick + sec(180), "hatch"]

    def entity_at(self, x, y):
        for a in self.agents.values():
            if a.online and a.hp > 0 and (a.x, a.y) == (x, y):
                return a
        for c in self.creatures.values():
            if c.y == y and abs(c.x - x) <= CREATURES[c.kind].get("wide", 0):     # (the boss is three tiles wide)
                return c
        return None

    def sheltered(self, x, y) -> bool:
        """Inside a room: the area around (x, y) is closed off by walls/doors/gates within 160 tiles
        (same rule the client uses to draw roofs). Next to 3+ walls also counts, as before. In a cave too."""
        if self.world.roof(x, y):                          # (land over it, or a floor, a roof)
            return True
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
        act = self.current or a.action                       # (the action being stepped: it may be the hands', beside a walk)
        if act is not None:
            act.expected = max(act.expected, act.ticks - 1 + n)
        for _ in range(n - 1):
            yield

    # ------------------------------------------------------------- agents

    def interrupt(self, a: Agent, why="interrupted", way=False, hands=True):
        """(way: walking on. Otherwise the way a player's screen had walked (Movement.follow) is forgotten: dead,
        moved, doing something else, they are not going there any more. hands: what the hands were doing meanwhile
        (Agent.aside: eating) stops too: not for a walk.)"""
        for slot in ("action", "aside") if hands else ("action",):
            act = getattr(a, slot)
            if act is not None:
                setattr(a, slot, None)
                if not act.gen.gi_running: act.gen.close()   # (dying of a fall in your own step: that step runs; let go of, not closed from inside itself)
                act.finish({"ok": False, "status": "interrupted", "error": "interrupted", "detail": why}, self)
        if not way:
            self.via_drop(a)

    def submit(self, a: Agent, tool: str, args: dict | None = None, on_done=None) -> Action:
        args = args or {}
        fn = getattr(self, f"_tool_{tool}", None)
        if fn is None or tool not in TOOL_SPECS:
            act = Action(a, tool, args, iter(()), on_done)
            act.finish({"ok": False, "status": "failed", "error": "unknown_tool",
                        "detail": f"tools: {', '.join(TOOL_SPECS)}"}, self)
            return act
        if a.aside is not None and tool not in MEANWHILE:      # eating: the hands are full. You can walk on (and talk),
            act = Action(a, tool, args, iter(()), on_done)     # nothing else until it is eaten: no punch, no digging
            act.finish({"ok": False, "status": "failed", "error": "hands_full",
                        "detail": "you are eating: you can walk meanwhile, nothing else until it is eaten"}, self)
            return act
        if tool in ("walk", "stop"):                    # where a player's screen turned, or stopped (Movement.follow): kept
            if args.get("cut"):                         # now, were this replaced before it starts (`cut`: it turned
                self.via_drop(a)                        # back before the tile it had stopped on: not made after all)
            self.via_add(a, args.get("from" if tool == "walk" else "at"))
        act = Action(a, tool, args, fn(a, args), on_done)
        moving = a.action is not None and a.action.tool in MOVES
        if tool in ASIDE:                               # with the hands: a walk goes on (anything else stops for it)
            walk, a.action = (a.action, None) if moving else (None, a.action)
            self.interrupt(a, f"replaced by {tool}", way=True)       # (what they were doing)
            a.action, a.aside = walk, act
            return act
        if moving and tool not in MOVES and tool != "stop":
            # walking or running: try it right away; if it takes no time (picking a flower, picking up), it happens
            # on the move and the walk goes on. If it needs time (chopping), it replaces the walk as usual.
            walk, a.action = a.action, act
            act.started_tick, act.ticks = self.tick, 1
            self.passing, self.passed = a, walk           # (passed: the movement it came in on: Movement._tool_jump)
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
            self.interrupt(a, f"replaced by {tool}", way=tool in ("jump", "leap"))      # (a jump makes the way the screen walked first)
            a.action = act
            return act
        self.interrupt(a, f"replaced by {tool}", way=tool in ("walk", "stop", "jump", "leap"), hands=tool not in MEANWHILE)
        a.action = act
        return act

    # ------------------------------------------------------------- tick

    def step(self):
        self.tick += 1
        self.world.tick = self.tick
        self.rng.seed(self.seed * 1_000_003 + self.tick)
        for aid in sorted(self.agents):
            a = self.agents[aid]
            for act in (a.action, a.aside):               # what they are doing, and what their hands are doing meanwhile
                if act is None or not a.online:
                    continue
                if act.started_tick is None:
                    act.started_tick = self.tick
                act.ticks += 1
                self.current = act
                try:
                    next(act.gen)
                except StopIteration as stop:
                    self.stats["actions"] += 1
                    act.finish({"ok": True, "status": "done", **(stop.value or {})}, self)
                except Exception as e:                    # (a refusal; or a bug: the action fails, the world goes on)
                    self.stats["actions"] += 1
                    act.finish(failure(e), self)
                self.current = None
        self.step_creatures()
        self.step_environment()
        self.step_needs()
        self.attract_items()

    # ------------------------------------------------------- persistence


