"""Authoritative, deterministic tick simulation.

The simulation is synchronous and has no asyncio dependency: callers `submit()` an action
for an agent and call `step()` once per tick. Each action is a generator that yields once
per tick it consumes and returns a result dict; failures raise `ActionError`.
"""

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from . import tiles as T
from .pathfind import astar
from .tiles import BLOCKS, DIRS, GROUNDS, PLACEABLE, RECIPES
from .world import Store, World

TICK_HZ = 10


def sec(seconds: float) -> int:
    """Durations are specified in seconds and converted here, so the tick rate never changes game pace."""
    return max(1, round(seconds * TICK_HZ))


DAY_TICKS = sec(600)   # a 10-minute day
STEP = sec(0.2)        # walking speed: 5 tiles per second
VIEW_R = 10
SAY_R = 12
SHOUT_R = 48
EVENT_QUEUE = 60
MAX_TEXT = 200
CREATURE_ID0 = 1_000_000


class ActionError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code, detail)
        self.code, self.detail = code, detail


@dataclass
class Agent:
    id: int
    name: str
    x: int
    y: int
    persona: str = ""
    hp: int = 100
    hunger: int = 80
    energy: int = 100
    inventory: dict = field(default_factory=dict)
    deaths: int = 0
    stats: dict = field(default_factory=dict)
    spawn: list | None = None  # set by sleeping in a bed: you wake up there after dying
    sailing: bool = False      # in a boat: water is passable, land ends the trip
    # runtime only
    action: "Action | None" = field(default=None, repr=False)
    events: list = field(default_factory=list, repr=False)
    online: bool = False

    def to_json(self) -> dict:
        return {k: getattr(self, k) for k in
                ("id", "name", "x", "y", "persona", "hp", "hunger", "energy", "inventory", "deaths", "stats", "spawn", "sailing")}

    def count(self, item) -> int:
        return self.inventory.get(item, 0)

    def add(self, item, n=1):
        v = self.inventory.get(item, 0) + n
        if v < 0:
            raise ValueError(f"negative inventory {item}")
        if v:
            self.inventory[item] = v
        else:
            self.inventory.pop(item, None)

    def bump(self, stat, n=1):
        self.stats[stat] = self.stats.get(stat, 0) + n


@dataclass
class Creature:
    id: int
    kind: str  # chicken | cow | gloom
    x: int
    y: int
    hp: int
    cooldown: int = 0
    milked: int = 0     # tick of the last milking (cows)
    love: int = 0       # fed: shows hearts and (chickens) lays an egg soon, until this tick
    lay: int = 0        # next tick a chicken may lay an egg
    born: int = 0       # tick of birth (chicks and calves grow up)

    def to_json(self):
        return {"id": self.id, "kind": self.kind, "x": self.x, "y": self.y, "hp": self.hp,
                "milked": self.milked, "love": self.love, "lay": self.lay, "born": self.born}


CREATURES = {
    "chicken": {"hp": 10, "drops": {"meat": 1, "egg": 1}, "char": "c"},
    "cow": {"hp": 30, "drops": {"meat": 3, "milk": 1}, "char": "k"},
    "gloom": {"hp": 30, "drops": {"ore": 1}, "char": "G", "damage": 7},
    "chick": {"hp": 4, "drops": {"meat": 1}, "char": "c", "grows": ("chicken", 300)},
    "calf": {"hp": 12, "drops": {"meat": 1}, "char": "k", "grows": ("cow", 360)},
}


class Action:
    def __init__(self, agent: Agent, tool: str, args: dict, gen, on_done=None):
        self.agent, self.tool, self.args, self.gen = agent, tool, args, gen
        self.on_done = on_done
        self.started_tick = None
        self.ticks = 0
        self.result = None
        self.tiles: list = []
        self.snapshot = (dict(agent.inventory), agent.hp, agent.hunger, agent.energy, agent.x, agent.y)
        self.expected = 0  # ticks this action is expected to take (set by Simulation.wait)
        self.seen_events: list = []

    def finish(self, result: dict, sim: "Simulation"):
        a = self.agent
        inv0, hp0, hu0, en0, x0, y0 = self.snapshot
        inv = {}
        for k in set(inv0) | set(a.inventory):
            d = a.inventory.get(k, 0) - inv0.get(k, 0)
            if d:
                inv[k] = d
        changed = {}
        if inv:
            changed["inventory"] = inv
        for key, before, now in (("hp", hp0, a.hp), ("hunger", hu0, a.hunger), ("energy", en0, a.energy)):
            if now != before:
                changed[key] = now - before
        if (a.x, a.y) != (x0, y0):
            changed["pos"] = [a.x, a.y]
        if self.tiles:
            changed["tiles"] = self.tiles[-20:]
        result = {"tool": self.tool, "ticks": self.ticks, **result, "changed": changed}
        if self.seen_events:
            result["events"] = self.seen_events[-10:]
        self.result = result
        if a.action is self:
            a.action = None
        if self.on_done:
            self.on_done(result)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Simulation:
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
            self.agents[aid] = Agent(**json.loads(js))
            self.tokens[aid] = th
        self.by_name = {a.name: a for a in self.agents.values()}
        self.items: dict[tuple[int, int], dict] = {
            (x, y): json.loads(j) for x, y, j in store.db.execute("SELECT x, y, json FROM ground_items")}
        self.dirty_items: set = set()
        self.creatures: dict[int, Creature] = {}
        for cid, js in store.db.execute("SELECT id, json FROM creatures"):
            self.creatures[cid] = Creature(**json.loads(js))
        self.next_creature = max(self.creatures, default=CREATURE_ID0) + 1
        self.fires: dict[tuple, int] = {tuple(k): v for k, v in store.get_meta("fires", [])}
        self.timers: dict[tuple, list] = {(x, y): [t, kind] for x, y, t, kind in store.get_meta("timers", [])}
        self.pits: set = {tuple(p) for p in store.get_meta("pits", [])}
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
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "dir must be one of N, E, S, W")
        dx, dy = DIRS[d]
        return a.x + dx, a.y + dy

    def near_block(self, a: Agent, block: str, r: int = 2) -> bool:
        return any(self.world.block(a.x + dx, a.y + dy) == block
                   for dy in range(-r, r + 1) for dx in range(-r, r + 1))

    ENCLOSE = ("wood_wall", "stone_wall", "door", "gate")

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
        n = sec(seconds * (2 if a.energy <= 0 else 1))
        if a.action is not None:
            a.action.expected = max(a.action.expected, a.action.ticks - 1 + n)
        for _ in range(n - 1):
            yield

    def spend(self, a: Agent, energy: int):
        a.energy = max(0, a.energy - energy)

    # ------------------------------------------------------------- agents
    def login(self, name: str, token: str, persona: str = "") -> Agent:
        name = name.strip()[:24]
        if not name or not name.replace("_", "").replace("-", "").isalnum():
            raise ActionError("bad_name", "name must be 1-24 letters/digits/-/_")
        a = self.by_name.get(name)
        th = _hash_token(token)
        if a is None:
            aid = max(self.agents, default=0) + 1
            x, y = self.find_spawn(aid)
            a = Agent(aid, name, x, y, persona=persona[:200])
            self.agents[aid] = a
            self.by_name[name] = a
            self.tokens[aid] = th
            self.store.db.execute("INSERT INTO agents VALUES(?,?,?,?)", (aid, name, th, json.dumps(a.to_json())))
            self.emit("join", x, y, radius=SHOUT_R, name=name, new=True)
        elif self.tokens[a.id] != th:
            raise ActionError("bad_token", "name is taken and the token does not match")
        else:
            if persona:
                a.persona = persona[:200]
            self.emit("join", a.x, a.y, radius=SHOUT_R, name=name, new=False)
        a.online = True
        return a

    def logout(self, a: Agent):
        if a.action:
            self.interrupt(a, "disconnected")
        a.online = False
        self.emit("leave", a.x, a.y, radius=SHOUT_R, name=a.name)

    def find_spawn(self, salt: int) -> tuple[int, int]:
        r = random.Random(self.seed * 7919 + salt * 104729 + self.tick)
        for radius in (24, 48, 96, 192):
            for _ in range(200):
                x, y = r.randint(-radius, radius), r.randint(-radius, radius)
                if self.world.passable(x, y) and GROUNDS[self.world.get(x, y)[0]].name in ("dirt", "grass", "bridge"):
                    return x, y
        return 0, 0

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
        if a.action is not None:
            self.interrupt(a, f"replaced by {tool}")
        act = Action(a, tool, args, fn(a, args), on_done)
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

    def step_needs(self):
        t = self.tick
        for a in self.agents.values():
            if not a.online:
                continue
            if t % sec(10) == 0 and a.hunger > 0:
                a.hunger -= 1
            if t % sec(5) == 0:
                if a.hunger == 0:
                    self.damage(a, 1, "starvation")
                elif a.hunger > 40 and a.hp < 100:
                    a.hp += 1
            if t % sec(8) == 0 and a.action is None and a.energy < 100:
                a.energy += 1
            if (a.x, a.y) in self.fires and t % sec(1) == 0:
                self.damage(a, 3, "fire")

    def damage(self, target, n: int, cause: str, by: Agent | None = None):
        target.hp -= n
        if target.hp <= 0:
            if isinstance(target, Agent):
                self.kill_agent(target, cause, by)
            else:
                self.kill_creature(target, by)

    def kill_agent(self, a: Agent, cause: str, by: Agent | None):
        self.add_items(a.x, a.y, dict(a.inventory))
        dropped = dict(a.inventory)
        a.inventory.clear()
        a.deaths += 1
        self.stats["deaths"] += 1
        if by:
            by.bump("kills")
        self.emit("death", a.x, a.y, radius=SHOUT_R, name=a.name, cause=cause, by=by.name if by else None,
                  dropped=dropped)
        if a.action:
            self.interrupt(a, "you died")
        if a.sailing:
            self.world.set(a.x, a.y, block="boat")
            a.sailing = False
        bed = a.spawn
        if bed and self.world.block(*bed) == "bed":
            spots = [(bed[0] + dx, bed[1] + dy) for dx, dy in DIRS.values() if self.world.passable(bed[0] + dx, bed[1] + dy)]
            a.x, a.y = spots[0] if spots else self.find_spawn(a.id * 31 + a.deaths)
        else:
            a.spawn = None
            a.x, a.y = self.find_spawn(a.id * 31 + a.deaths)
        a.hp, a.hunger, a.energy = 100, 70, 80
        a.events.append({"tick": self.tick, "type": "respawn", "cause": cause,
                         "by": by.name if by else None, "x": a.x, "y": a.y})

    def kill_creature(self, c: Creature, by: Agent | None):
        self.creatures.pop(c.id, None)
        self.add_items(c.x, c.y, CREATURES[c.kind]["drops"])
        if by:
            by.bump(f"killed_{c.kind}")
        self.emit("creature_died", c.x, c.y, kind=c.kind, id=c.id, by=by.name if by else None)

    # ---------------------------------------------------------- creatures
    def step_creatures(self):
        online = [a for a in self.agents.values() if a.online]
        # spawning (deterministic via tick rng)
        if self.tick % sec(10) == 0 and online:
            animals = sum(1 for c in self.creatures.values() if c.kind in ("chicken", "cow", "chick", "calf"))
            if animals < min(40, 3 * len(online)):
                a = online[self.rng.randrange(len(online))]
                self._spawn_creature("chicken" if self.rng.random() < 0.6 else "cow", a, 12, 30)
            glooms = sum(1 for c in self.creatures.values() if c.kind == "gloom")
            if self.is_night() and glooms < len(online):
                a = online[self.rng.randrange(len(online))]
                self._spawn_creature("gloom", a, 14, 24)
        if not self.is_night() and self.tick % sec(5) == 0:
            for c in [c for c in self.creatures.values() if c.kind == "gloom"]:
                if self.rng.random() < 0.2:
                    del self.creatures[c.id]
        for cid in sorted(self.creatures):
            c = self.creatures.get(cid)
            if c is None:
                continue
            if c.kind == "chicken":
                if not c.lay:
                    c.lay = self.tick + sec(60) + self.rng.randrange(sec(60))
                elif self.tick >= c.lay:
                    c.lay = self.tick + sec(90) + self.rng.randrange(sec(90))
                    self.add_items(c.x, c.y, {"egg": 1})
                    self.timers[(c.x, c.y)] = [self.tick + sec(180), "hatch"]
                    self.emit("lay", c.x, c.y, id=c.id)
            grows = CREATURES[c.kind].get("grows")
            if grows and self.tick - c.born >= sec(grows[1]):
                c.kind = grows[0]
                c.hp = CREATURES[c.kind]["hp"]
                self.emit("grew_up", c.x, c.y, id=c.id, kind=c.kind)
            if c.cooldown > 0:
                c.cooldown -= 1
                continue
            if c.kind in ("chicken", "cow", "chick", "calf"):
                c.cooldown = sec(0.8) + self.rng.randrange(sec(1.2))
                d = list(DIRS.values())[self.rng.randrange(4)]
                self._creature_move(c, c.x + d[0], c.y + d[1])
            else:
                prey = min((a for a in online if abs(a.x - c.x) + abs(a.y - c.y) <= 10),
                           key=lambda a: (abs(a.x - c.x) + abs(a.y - c.y), a.id), default=None)
                c.cooldown = sec(0.4) - 1
                if prey is None:
                    d = list(DIRS.values())[self.rng.randrange(4)]
                    self._creature_move(c, c.x + d[0], c.y + d[1])
                elif max(abs(prey.x - c.x), abs(prey.y - c.y)) <= 1:
                    c.cooldown = sec(1.2)
                    self.emit("attack", c.x, c.y, attacker="a gloom", target=prey.name,
                              damage=CREATURES["gloom"]["damage"])
                    self.damage(prey, CREATURES["gloom"]["damage"], "gloom")
                else:
                    sx = (prey.x > c.x) - (prey.x < c.x)
                    sy = (prey.y > c.y) - (prey.y < c.y)
                    if sx and (not sy or self.rng.random() < 0.5):
                        if not self._creature_move(c, c.x + sx, c.y):
                            self._creature_move(c, c.x, c.y + sy)
                    elif not self._creature_move(c, c.x, c.y + sy):
                        self._creature_move(c, c.x + sx, c.y)

    def _creature_move(self, c, x, y) -> bool:
        # animals and glooms can't work doors or gates: houses keep glooms out, fenced pens keep animals in
        if self.world.block(x, y) in ("door", "gate"):
            return False
        if self.world.passable(x, y) and self.entity_at(x, y) is None:
            c.x, c.y = x, y
            return True
        return False

    def _spawn_creature(self, kind, near: Agent, rmin, rmax):
        for _ in range(10):
            x = near.x + self.rng.randint(-rmax, rmax)
            y = near.y + self.rng.randint(-rmax, rmax)
            if max(abs(x - near.x), abs(y - near.y)) < rmin:
                continue
            if self.world.passable(x, y) and self.entity_at(x, y) is None:
                c = Creature(self.next_creature, kind, x, y, CREATURES[kind]["hp"])
                self.next_creature += 1
                self.creatures[c.id] = c
                return c
        return None

    # -------------------------------------------------------- environment
    def ignite(self, x, y, by=None) -> bool:
        g, b = self.world.get(x, y)
        ground, block = GROUNDS[g], BLOCKS[b]
        if (x, y) in self.fires or not ground.walkable:
            return False
        if block.flammable or (block.name == "none" and ground.flammable):
            self.fires[(x, y)] = sec(5) + self.rng.randrange(sec(10))
            self.set_tile(x, y, block="fire", by=by, cause="fire")
            return True
        return False

    def step_environment(self):
        if self.fires:
            for pos in sorted(self.fires):
                x, y = pos
                self.fires[pos] -= 1
                for dx, dy in DIRS.values():
                    if self.rng.random() < 0.1 / TICK_HZ:
                        self.ignite(x + dx, y + dy)
                if self.fires[pos] <= 0:
                    del self.fires[pos]
                    self.set_tile(x, y, ground="ash", block="none", cause="burnt")
        if self.pits and self.tick % sec(1) == 0:
            for pos in sorted(self.pits):
                x, y = pos
                if self.world.ground(x, y) != "tilled":
                    self.pits.discard(pos)
                    continue
                near = {self.world.ground(x + dx, y + dy) for dx, dy in DIRS.values()}
                if not near & {"water", "deep_water"}:
                    self.pits.discard(pos)
                elif self.rng.random() < 0.25 and self.entity_at(x, y) is None:
                    # a hole dug next to water floods
                    self.pits.discard(pos)
                    self.set_tile(x, y, ground="water", cause="flood")
        if self.timers and self.tick % sec(2) == 0:
            for pos in sorted(self.timers):
                due, kind = self.timers[pos]
                if self.tick < due:
                    continue
                del self.timers[pos]
                if kind == "ripen" and self.world.block(*pos) in ("sprout", "crop"):
                    nxt = "crop" if self.world.block(*pos) == "sprout" else "ripe_crop"
                    dry = "tilled" if self.world.ground(*pos) == "wet_tilled" else None  # water is used up
                    self.set_tile(*pos, ground=dry, block=nxt, cause="grew")
                    if nxt == "crop":
                        self.timers[pos] = [self.tick + sec(150), "ripen"]
                elif kind == "hatch" and self.items.get(pos, {}).get("egg"):
                    pile = self.items[pos]
                    pile["egg"] -= 1
                    if not pile["egg"]:
                        del pile["egg"]
                    if not pile:
                        del self.items[pos]
                    self.dirty_items.add(pos)
                    chick = Creature(self.next_creature, "chick", *pos, CREATURES["chick"]["hp"], born=self.tick)
                    self.next_creature += 1
                    self.creatures[chick.id] = chick
                    self.emit("hatch", *pos, id=chick.id)
                elif kind == "fruit" and self.world.block(*pos) == "tree":
                    self.set_tile(*pos, block="fruit_tree", cause="grew")
                elif kind == "regrow" and self.world.block(*pos) == "none" and self.entity_at(*pos) is None \
                        and self.world.ground(*pos) in ("grass", "dirt"):
                    self.set_tile(*pos, block="tree", cause="grew")
        if self.tick % sec(20) == 0:
            for key in sorted(self.world.chunks):
                cx, cy = key
                x = cx * 32 + self.rng.randrange(32)
                y = cy * 32 + self.rng.randrange(32)
                if self.rng.random() < 0.1 and self.world.ground(x, y) == "grass" and self.world.block(x, y) == "none":
                    self.set_tile(x, y, block="berry_bush", cause="grew")

    # ------------------------------------------------------- persistence
    def flush(self):
        db = self.store.db
        for a in self.agents.values():
            db.execute("UPDATE agents SET json=? WHERE id=?", (json.dumps(a.to_json()), a.id))
        for pos in self.dirty_items:
            pile = self.items.get(pos)
            if pile:
                db.execute("INSERT OR REPLACE INTO ground_items VALUES(?,?,?)", (*pos, json.dumps(pile)))
            else:
                db.execute("DELETE FROM ground_items WHERE x=? AND y=?", pos)
        self.dirty_items.clear()
        db.execute("DELETE FROM creatures")
        db.executemany("INSERT INTO creatures VALUES(?,?)",
                       [(c.id, json.dumps(c.to_json())) for c in self.creatures.values()])
        self.store.set_meta("tick", self.tick)
        self.store.set_meta("fires", [[list(k), v] for k, v in self.fires.items()])
        self.store.set_meta("timers", [[x, y, t, k] for (x, y), (t, k) in self.timers.items()])
        self.store.set_meta("pits", [list(p) for p in self.pits])
        self.world.flush()
        if self.event_log:
            self.event_log.flush()

    def maintain(self):
        anchors = [(a.x, a.y) for a in self.agents.values() if a.online]
        return self.world.unload_far(anchors)

    def close(self):
        self.flush()
        if self.event_log:
            self.event_log.close()
        self.store.close()

    # -------------------------------------------------------- observation
    def observe(self, a: Agent, consume_events=True) -> dict:
        R = VIEW_R
        ents = {}
        out_ents = []
        for o in self.agents.values():
            if o is not a and o.online and abs(o.x - a.x) <= R and abs(o.y - a.y) <= R:
                ents[(o.x, o.y)] = "P"
                out_ents.append({"id": o.id, "kind": "agent", "name": o.name, "dx": o.x - a.x, "dy": o.y - a.y,
                                 "hp": o.hp, "holding": self.best_weapon(o) or "nothing",
                                 "doing": o.action.tool if o.action else "idle"})
        for c in self.creatures.values():
            if abs(c.x - a.x) <= R and abs(c.y - a.y) <= R:
                ents.setdefault((c.x, c.y), CREATURES[c.kind]["char"])
                out_ents.append({"id": c.id, "kind": c.kind, "dx": c.x - a.x, "dy": c.y - a.y, "hp": c.hp})
        out_ents.sort(key=lambda e: abs(e["dx"]) + abs(e["dy"]))
        grid, used = [], set()
        for y in range(a.y - R, a.y + R + 1):
            row = []
            for x in range(a.x - R, a.x + R + 1):
                if (x, y) == (a.x, a.y):
                    ch = "@"
                elif (x, y) in ents:
                    ch = ents[(x, y)]
                else:
                    ch = self.world.char(x, y)
                    if (x, y) in self.items and self.world.block(x, y) == "none":
                        ch = "$"
                used.add(ch)
                row.append(ch)
            grid.append("".join(row))
        items, signs = [], []
        for (x, y), pile in self.items.items():
            if abs(x - a.x) <= R and abs(y - a.y) <= R and pile:
                items.append({"dx": x - a.x, "dy": y - a.y, "items": pile})
        for (x, y), m in self.world.meta.items():
            if abs(x - a.x) <= R and abs(y - a.y) <= R and "text" in m:
                signs.append({"dx": x - a.x, "dy": y - a.y, "kind": self.world.block(x, y), "text": m["text"]})
        items.sort(key=lambda e: abs(e["dx"]) + abs(e["dy"]))
        events = a.events
        if consume_events:
            a.events = []
        here_g, here_b = self.world.ground(a.x, a.y), self.world.block(a.x, a.y)
        return {
            "tick": self.tick,
            "time": self.clock(),
            "self": {"id": a.id, "name": a.name, "x": a.x, "y": a.y, "hp": a.hp, "hunger": a.hunger,
                     "energy": a.energy, "inventory": dict(sorted(a.inventory.items())), "deaths": a.deaths,
                     "action": a.action.tool if a.action else None,
                     "spawn": a.spawn, "sailing": a.sailing,
                     "standing_on": here_g if here_b == "none" else f"{here_g}+{here_b}",
                     "sheltered": self.sheltered(a.x, a.y)},
            "grid": grid,
            "legend": {ch: LEGEND[ch] for ch in sorted(used) if ch in LEGEND},
            "entities": out_ents[:20],
            "items": items[:15],
            "signs": signs[:10],
            "events": events,
        }

    def best_weapon(self, a: Agent):
        best = max((w for w in T.WEAPONS if a.count(w)), key=lambda w: T.WEAPONS[w], default=None)
        return best

    # ============================================================== tools
    def can_enter(self, a: Agent, x: int, y: int) -> bool:
        """Walkers stay on land; a moored boat can be boarded; sailors move over water and may step ashore."""
        g, b = self.world.get(x, y)
        ground, block = GROUNDS[g], BLOCKS[b]
        if ground.liquid:
            return a.sailing or block.name == "boat"
        return ground.walkable and not block.solid

    def move(self, a: Agent, x: int, y: int):
        """Move to an adjacent tile, boarding or leaving a boat when crossing the shoreline."""
        if not a.sailing and self.world.block(x, y) == "boat":
            self.set_tile(x, y, block="none", by=a, cause="board")
            a.sailing = True
            self.emit("board", x, y, name=a.name)
        elif a.sailing and not GROUNDS[self.world.get(x, y)[0]].liquid:
            self.set_tile(a.x, a.y, block="boat", by=a, cause="moor")   # leave the boat where you got off
            a.sailing = False
            self.emit("moor", a.x, a.y, name=a.name)
        a.x, a.y = x, y
        self.arrive(a)

    def arrive(self, a: Agent):
        """Called after every move: walking over items picks them up."""
        pile = self.items.get((a.x, a.y))
        if not pile:
            return
        got = dict(pile)
        for k, n in got.items():
            a.add(k, n)
        del self.items[(a.x, a.y)]
        self.dirty_items.add((a.x, a.y))
        self.emit("pick_up", a.x, a.y, name=a.name, items=got)

    def stride(self, a: Agent, args) -> float:
        """Seconds per tile. Sprinting (`run: true`) is twice as fast and costs 1 energy per 4 tiles.
        Sailing is a steady 0.15 s per tile."""
        if a.sailing:
            return 0.15
        if args.get("run") and a.energy > 0:
            a.stats["run_tiles"] = a.stats.get("run_tiles", 0) + 1
            if a.stats["run_tiles"] % 4 == 0:
                self.spend(a, 1)
            return 0.1
        return 0.2

    def _tool_step(self, a, args):
        x, y = self.target(a, args)
        yield from self.wait(a, self.stride(a, args))
        if not self.can_enter(a, x, y):
            raise ActionError("blocked", f"{args['dir']} is {self.describe(x, y)}")
        self.move(a, x, y)
        return {}

    def _tool_walk(self, a, args):
        """Keep walking in a direction at a steady stride until blocked or replaced by another action
        (e.g. `stop`). Lets a held key move smoothly without a round trip per tile."""
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "dir must be one of N, E, S, W")
        dx, dy = DIRS[d]
        steps = 0
        while steps < 600:
            yield from self.wait(a, self.stride(a, args))
            if not self.can_enter(a, a.x + dx, a.y + dy):
                return {"steps": steps, "stopped": "blocked", "blocked_by": self.describe(a.x + dx, a.y + dy)}
            self.move(a, a.x + dx, a.y + dy)
            steps += 1
            yield  # one tile per stride: the stride's first tick is spent here
        return {"steps": steps, "stopped": "limit"}

    def _tool_stop(self, a, args):
        yield from ()  # completes at once; submitting it interrupts whatever was running
        return {}

    def _tool_move_to(self, a, args):
        try:
            gx, gy = int(args["x"]), int(args["y"])
        except (KeyError, TypeError, ValueError):
            raise ActionError("bad_args", "move_to needs integer x and y")
        replans = 0
        ok = lambda x, y: self.can_enter(a, x, y) and (a.sailing or self.world.block(x, y) != "boat" or (x, y) == (gx, gy))
        path = astar(ok, (a.x, a.y), (gx, gy))
        if path is None:
            far = abs(gx - a.x) + abs(gy - a.y) > 64
            raise ActionError("no_path", "target further than 64 tiles" if far else
                              f"no walkable path to ({gx},{gy}) from ({a.x},{a.y})")
        steps = 0
        while path:
            yield from self.wait(a, self.stride(a, args))
            nx, ny = path[0]
            if not self.can_enter(a, nx, ny):
                replans += 1
                path = astar(ok, (a.x, a.y), (gx, gy)) if replans <= 2 else None
                if path is None:
                    raise ActionError("blocked", f"path blocked at ({nx},{ny}); stopped at ({a.x},{a.y})")
                continue
            self.move(a, nx, ny)
            path.pop(0)
            steps += 1
        return {"steps": steps, "arrived": [a.x, a.y], "adjacent_only": (a.x, a.y) != (gx, gy)}

    def describe(self, x, y) -> str:
        g, b = self.world.ground(x, y), self.world.block(x, y)
        return g if b == "none" else f"{b} on {g}"

    def _tool_dig(self, a, args):
        x, y = self.target(a, args)
        g, b = self.world.get(x, y)
        block, ground = BLOCKS[b], GROUNDS[g]
        if block.name == "none":
            built = {"cobble": ("path", "dirt"), "floor": ("plank", "dirt"), "bridge": ("plank", "water")}
            if ground.name in built:                       # what you lay, you can take up again
                item, under = built[ground.name]
                if under == "water" and self.entity_at(x, y):
                    raise ActionError("occupied", "someone is standing on it")
                yield from self.wait(a, 0.5)
                a.add(item)
                self.set_tile(x, y, ground=under, by=a, cause="dig")
                return {"got": {item: 1}}
            if not ground.diggable or ground.name in ("tilled", "wet_tilled"):
                raise ActionError("cannot_dig", f"{ground.name} cannot be dug")
            yield from self.wait(a, 0.6)
            if self.world.block(x, y) != "none":
                raise ActionError("changed", "something was placed there")
            self.spend(a, 1)
            self.set_tile(x, y, ground="tilled", by=a, cause="dig")
            return {}
        if block.hardness <= 0:
            raise ActionError("cannot_dig", f"{block.name} cannot be dug")
        if block.needs_tool and not a.count(block.needs_tool):
            raise ActionError("need_tool", f"digging {block.name} needs a {block.needs_tool}")
        seconds = block.hardness / 10
        if block.tool and a.count(block.tool):
            seconds /= 2
        yield from self.wait(a, seconds)
        if self.world.get(x, y)[1] != b:
            raise ActionError("changed", "the block changed while digging")
        self.spend(a, 1)
        drops = dict(block.drops)
        if block.name == "ripe_crop":
            drops = {T.crop_species(x, y): 3, "seed": 2}
        if block.name == "chest":
            drops = self._merge(drops, self.world.meta.get((x, y), {}).get("items", {}))
        for k, n in drops.items():
            a.add(k, n)
        if block.name == "fruit_tree":
            # picking a fruit tree takes its fruit; the tree stays and fruits again later
            self.set_tile(x, y, block="tree", by=a, cause="pick")
            self.timers[(x, y)] = [self.tick + sec(240), "fruit"]
            a.bump("dug")
            return {"got": drops}
        after = "none"  # a felled tree leaves clean ground; it regrows there later
        self.set_tile(x, y, block=after, by=a, cause="dig")
        if block.name == "tree":
            self.timers[(x, y)] = [self.tick + sec(1200), "regrow"]
        a.bump("dug")
        return {"got": drops}

    @staticmethod
    def _merge(a: dict, b: dict) -> dict:
        out = dict(a)
        for k, n in b.items():
            out[k] = out.get(k, 0) + n
        return out

    def _tool_place(self, a, args):
        x, y = self.target(a, args)
        item = str(args.get("item", ""))
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}")
        g, b = self.world.ground(x, y), self.world.block(x, y)
        picked = b == "flower"   # flowers are decoration: building over one picks it for you
        if picked:
            b = "none"
        if item in T.FILLERS:
            options = T.FILLERS[item]
            if b != "none":
                raise ActionError("occupied", f"{args['dir']} has {b}")
            if g not in options:
                raise ActionError("bad_target", f"{item} goes on {', '.join(sorted(options))}, not {g}")
            yield from self.wait(a, 0.3)
            if self.world.ground(x, y) != g or self.world.block(x, y) not in ("none", "flower"):
                raise ActionError("changed", "the tile changed")
            if self.world.block(x, y) == "flower":
                a.add("flower")
            a.add(item, -1)
            self.set_tile(x, y, ground=options[g], by=a, cause="place")
            a.bump("placed")
            return {}
        if item not in PLACEABLE:
            raise ActionError("not_placeable", f"{item} cannot be placed. Placeable: "
                              f"{', '.join(sorted(PLACEABLE) + sorted(T.FILLERS))}")
        block = PLACEABLE[item]
        if b == "stump":
            b = "none"  # debris is junk: building over it clears it
        if b != "none":
            raise ActionError("occupied", f"{args['dir']} has {b}")
        if block == "boat":
            if g != "water":
                raise ActionError("bad_target", "boats go on shallow water next to you")
        elif not GROUNDS[T.G[g]].walkable:
            raise ActionError("bad_target", f"cannot place on {g}")
        if item == "seed" and g not in T.SEED_GROUNDS:
            raise ActionError("bad_target", "seeds only grow in tilled soil (dig the ground first)")
        if BLOCKS[T.B[block]].solid and self.entity_at(x, y):
            raise ActionError("occupied", "someone is standing there")
        yield from self.wait(a, 0.3)
        if self.world.block(x, y) not in ("none", "stump", "flower"):
            raise ActionError("changed", "tile was taken")
        if self.world.block(x, y) == "flower":
            a.add("flower")
        if BLOCKS[T.B[block]].solid and self.entity_at(x, y):
            raise ActionError("occupied", "someone stepped there")
        a.add(item, -1)
        self.set_tile(x, y, block=block, by=a, cause="place")
        if block == "sprout":
            self.timers[(x, y)] = [self.tick + sec(150), "ripen"]
        if block == "mailbox":
            self.world.set_meta(x, y, {"owner": a.name, "letters": []})
        if block == "flag":
            text = str(args.get("text") or f"claimed by {a.name}")[:MAX_TEXT]
            self.world.set_meta(x, y, {"text": text, "by": a.name})
        a.bump("placed")
        return {}

    def _tool_pick_up(self, a, args):
        yield from self.wait(a, 0.1)
        pile = self.items.get((a.x, a.y))
        if not pile:
            raise ActionError("nothing_here", "no items on your tile")
        want = args.get("item")
        got = {}
        for k in list(pile):
            if want and k != want:
                continue
            got[k] = pile.pop(k)
            a.add(k, got[k])
        if not pile:
            del self.items[(a.x, a.y)]
        self.dirty_items.add((a.x, a.y))
        if not got:
            raise ActionError("nothing_here", f"no {want} on your tile")
        self.emit("pick_up", a.x, a.y, name=a.name, items=got)
        return {"got": got}

    def _tool_drop(self, a, args):
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}")
        yield from self.wait(a, 0.1)
        n = min(n, a.count(item))
        a.add(item, -n)
        self.add_items(a.x, a.y, {item: n})
        self.emit("drop", a.x, a.y, name=a.name, items={item: n})
        return {}

    @staticmethod
    def _n(args) -> int:
        try:
            return max(1, int(args.get("n", 1)))
        except (TypeError, ValueError):
            raise ActionError("bad_args", "n must be a positive integer")

    def _tool_craft(self, a, args):
        name = str(args.get("recipe", args.get("item", "")))
        r = RECIPES.get(name)
        if r is None:
            raise ActionError("unknown_recipe", f"recipes: {', '.join(RECIPES)}")
        n = min(self._n(args), 20)
        if r.station and not self.near_block(a, r.station):
            raise ActionError("need_station", f"{name} must be crafted within 2 tiles of a {r.station}")
        missing = {k: v * n - a.count(k) for k, v in r.inputs.items() if a.count(k) < v * n}
        if missing:
            raise ActionError("missing_items", f"need {missing} more for {n}x {name}")
        yield from self.wait(a, r.ticks / 10 * n)
        if r.station and not self.near_block(a, r.station):
            raise ActionError("need_station", f"the {r.station} is gone")
        if any(a.count(k) < v * n for k, v in r.inputs.items()):
            raise ActionError("missing_items", "inputs changed while crafting")
        for k, v in r.inputs.items():
            a.add(k, -v * n)
        for k, v in r.output.items():
            a.add(k, v * n)
        self.spend(a, 1)
        self.stats["crafts"] += 1
        a.bump("crafted", n)
        self.emit("craft", a.x, a.y, radius=4, name=a.name, made={k: v * n for k, v in r.output.items()})
        return {"made": {k: v * n for k, v in r.output.items()}}

    def _find_target(self, tid):
        try:
            tid = int(tid)
        except (TypeError, ValueError):
            raise ActionError("bad_args", "target must be an entity id")
        t = self.agents.get(tid) or self.creatures.get(tid)
        if t is None or (isinstance(t, Agent) and not t.online):
            raise ActionError("no_target", f"no entity {tid} here")
        return t

    def _tool_attack(self, a, args):
        t = self._find_target(args.get("target"))
        if t is a:
            raise ActionError("bad_target", "you cannot attack yourself")
        if max(abs(t.x - a.x), abs(t.y - a.y)) > 1:
            raise ActionError("out_of_range", "target must be adjacent (including diagonals)")
        yield from self.wait(a, 0.4)
        if max(abs(t.x - a.x), abs(t.y - a.y)) > 1 or t.hp <= 0:
            raise ActionError("missed", "target moved away")
        weapon = self.best_weapon(a)
        dmg = T.WEAPONS.get(weapon, T.FIST_DAMAGE)
        self.spend(a, 2)
        name = t.name if isinstance(t, Agent) else f"{t.kind}#{t.id}"
        self.emit("attack", a.x, a.y, attacker=a.name, target=name, damage=dmg, weapon=weapon or "fists")
        a.bump("attacks")
        if isinstance(t, Creature):
            t.cooldown = 0
        before = t.deaths if isinstance(t, Agent) else 0
        self.damage(t, dmg, f"killed by {a.name}", by=a)
        killed = t.deaths > before if isinstance(t, Agent) else t.id not in self.creatures
        return {"target": name, "damage": dmg, "target_hp": 0 if killed else t.hp, "killed": killed}

    def _tool_give(self, a, args):
        t = self._find_target(args.get("target"))
        if not isinstance(t, Agent) or t is a:
            raise ActionError("bad_target", "you can only give to another agent")
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}")
        if max(abs(t.x - a.x), abs(t.y - a.y)) > 2:
            raise ActionError("out_of_range", "target must be within 2 tiles")
        yield from self.wait(a, 0.2)
        if a.count(item) < n or max(abs(t.x - a.x), abs(t.y - a.y)) > 2:
            raise ActionError("failed", "conditions changed")
        a.add(item, -n)
        t.add(item, n)
        self.stats["trades"] += 1
        a.bump("gave")
        self.emit("give", a.x, a.y, radius=SAY_R, **{"from": a.name}, to=t.name, items={item: n})
        return {"to": t.name}

    def _tool_eat(self, a, args):
        item = str(args.get("item", ""))
        if item not in T.FOOD:
            raise ActionError("not_food", f"food: {', '.join(T.FOOD)}")
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}")
        yield from self.wait(a, 0.3)
        if not a.count(item):
            raise ActionError("missing_item", "it's gone")
        a.add(item, -1)
        a.hunger = min(100, a.hunger + T.FOOD[item])
        return {}

    def _tool_water(self, a, args):
        """Water a planted tile with a watering can: it grows twice as fast until the next stage."""
        x, y = self.target(a, args)
        if not a.count("watering_can"):
            raise ActionError("need_tool", "you need a watering can (craft one at a workbench)")
        if self.world.block(x, y) not in ("sprout", "crop") or self.world.ground(x, y) not in ("tilled", "wet_tilled"):
            raise ActionError("bad_target", "water a growing crop in tilled soil")
        if self.world.ground(x, y) == "wet_tilled":
            raise ActionError("already", "it's already watered")
        yield from self.wait(a, 0.8)
        timer = self.timers.get((x, y))
        if timer and timer[1] == "ripen":
            timer[0] = self.tick + max(1, (timer[0] - self.tick) // 2)
        self.set_tile(x, y, ground="wet_tilled", by=a, cause="water")
        a.bump("watered")
        return {}

    def _creature_target(self, a, args, kind=None):
        t = self._find_target(args.get("target"))
        if not isinstance(t, Creature) or (kind and t.kind != kind):
            raise ActionError("bad_target", f"that is not a {kind or 'creature'}")
        if max(abs(t.x - a.x), abs(t.y - a.y)) > 1:
            raise ActionError("out_of_range", "stand next to it")
        return t

    def _tool_milk(self, a, args):
        cow = self._creature_target(a, args, "cow")
        if cow.milked and self.tick - cow.milked < sec(120):
            raise ActionError("not_ready", "this cow was milked recently; try again in a while")
        cow.cooldown = max(cow.cooldown, sec(1.5))  # stands still while being milked
        yield from self.wait(a, 1.2)
        cow.milked = self.tick
        a.add("milk")
        self.emit("milk", cow.x, cow.y, name=a.name, id=cow.id)
        return {"got": {"milk": 1}}

    def _tool_feed(self, a, args):
        """Feed an animal: it loves you for a while; a fed chicken lays an egg soon."""
        animal = self._creature_target(a, args)
        item = str(args.get("item", ""))
        if animal.kind == "gloom":
            raise ActionError("bad_target", "glooms don't eat that")
        if item not in T.FOOD or not a.count(item):
            raise ActionError("missing_item", "feed it something edible you carry")
        yield from self.wait(a, 0.5)
        a.add(item, -1)
        animal.love = self.tick + sec(8)
        if animal.kind == "cow":
            mate = next((o for o in self.creatures.values() if o is not animal and o.kind == "cow" and o.love > self.tick
                         and max(abs(o.x - animal.x), abs(o.y - animal.y)) <= 3), None)
            if mate:
                calf = Creature(self.next_creature, "calf", animal.x, animal.y, CREATURES["calf"]["hp"], born=self.tick)
                self.next_creature += 1
                self.creatures[calf.id] = calf
                animal.love = mate.love = 0
                self.emit("born", animal.x, animal.y, id=calf.id, kind="calf")
        if animal.kind == "chicken":
            animal.lay = min(animal.lay or self.tick + sec(3), self.tick + sec(3))
        self.emit("love", animal.x, animal.y, by=a.name, id=animal.id, kind=animal.kind)
        return {}

    def _tool_sleep(self, a, args):
        """Sleep in an adjacent bed: big energy and health gain, and you'll wake up here after dying."""
        x, y = self.target(a, args)
        if self.world.block(x, y) != "bed":
            raise ActionError("no_bed", f"{args.get('dir')} is {self.describe(x, y)}, not a bed")
        for _ in range(sec(3) - 1):
            yield
        a.energy = min(100, a.energy + 60)
        a.hp = min(100, a.hp + 10)
        a.spawn = [x, y]
        return {"spawn": [x, y]}

    def _mailbox(self, a, args):
        x, y = self.target(a, args)
        if self.world.block(x, y) != "mailbox":
            raise ActionError("no_mailbox", f"{args.get('dir')} is {self.describe(x, y)}, not a mailbox")
        return x, y, dict(self.world.meta.get((x, y)) or {"owner": None, "letters": []})

    def _tool_post(self, a, args):
        """Put a letter in an adjacent mailbox (for its owner; anyone can open it, though)."""
        x, y, m = self._mailbox(a, args)
        text = self._text(args)
        if len(m.get("letters", [])) >= 20:
            raise ActionError("full", "this mailbox is full")
        yield from self.wait(a, 0.5)
        m["letters"] = m.get("letters", []) + [{"from": a.name, "text": text, "tick": self.tick}]
        self.world.set_meta(x, y, m)
        self.emit("mail", x, y, radius=SHOUT_R, **{"from": a.name}, to=m.get("owner"))
        return {"owner": m.get("owner")}

    def _tool_open_mail(self, a, args):
        """Take every letter out of an adjacent mailbox (yours or not: anarchy)."""
        x, y, m = self._mailbox(a, args)
        yield from self.wait(a, 0.4)
        letters = m.get("letters", [])
        m["letters"] = []
        self.world.set_meta(x, y, m)
        if letters:
            self.emit("mail_opened", x, y, by=a.name, owner=m.get("owner"), n=len(letters))
        return {"owner": m.get("owner"), "letters": letters}

    def _tool_rest(self, a, args):
        bonus = self.near_block(a, "campfire") or self.sheltered(a.x, a.y)
        for _ in range(sec(2) - 1):
            yield
        gain = 25 if bonus else 15
        a.energy = min(100, a.energy + gain)
        return {"bonus": bool(bonus)}

    def _text(self, args) -> str:
        text = str(args.get("text", "")).strip()
        if not text:
            raise ActionError("bad_args", "text required")
        return text[:MAX_TEXT]

    def _tool_say(self, a, args):
        text = self._text(args)
        yield from self.wait(a, 0.1)
        self.stats["chat"] += 1
        a.bump("said")
        self.emit("say", a.x, a.y, radius=SAY_R, **{"from": a.name}, text=text)
        return {}

    def _tool_shout(self, a, args):
        text = self._text(args)
        if a.energy < 10:
            raise ActionError("too_tired", "shouting needs 10 energy")
        yield from self.wait(a, 0.1)
        self.spend(a, 10)
        self.stats["chat"] += 1
        a.bump("said")
        self.emit("shout", a.x, a.y, radius=SHOUT_R, **{"from": a.name}, text=text)
        return {}

    def _tool_write_sign(self, a, args):
        x, y = self.target(a, args)
        text = self._text(args)
        if self.world.block(x, y) not in ("sign", "flag"):
            raise ActionError("no_sign", f"{args['dir']} is {self.describe(x, y)}, not a sign")
        yield from self.wait(a, 0.5)
        if self.world.block(x, y) not in ("sign", "flag"):
            raise ActionError("no_sign", "the sign is gone")
        self.world.set_meta(x, y, {"text": text, "by": a.name})
        self.emit("sign", x, y, by=a.name, text=text)
        return {}

    def _tool_read_sign(self, a, args):
        x, y = self.target(a, args)
        yield from self.wait(a, 0.1)
        m = self.world.meta.get((x, y))
        if self.world.block(x, y) not in ("sign", "flag") or not m:
            raise ActionError("no_sign", f"no readable sign {args['dir']}")
        return {"text": m.get("text", ""), "by": m.get("by")}

    def _tool_look_far(self, a, args):
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "dir must be one of N, E, S, W")
        yield from self.wait(a, 0.2)
        fx, fy = DIRS[d]
        px, py = -fy, fx  # perpendicular
        rows, seen = [], []
        agents_at = {(o.x, o.y): o for o in self.agents.values() if o.online and o is not a}
        for dist in range(VIEW_R + 1, VIEW_R + 49, 2):
            row = []
            for side in range(-8, 9, 2):
                best = None
                for dd in (0, 1):
                    for ss in (0, 1):
                        x = a.x + fx * (dist + dd) + px * (side + ss)
                        y = a.y + fy * (dist + dd) + py * (side + ss)
                        if (x, y) in agents_at:
                            best = "P"
                            seen.append({"name": agents_at[(x, y)].name, "dx": x - a.x, "dy": y - a.y})
                        elif best is None or best in "~.,:'=o_":
                            ch = self.world.char(x, y)
                            if best is None or ch not in "~.,:'=o_":
                                best = ch
                row.append(best)
            rows.append("".join(row))
        return {"dir": d, "rows_near_to_far": rows,
                "note": f"each char = 2x2 tiles; rows start {VIEW_R + 1} tiles away, left-to-right "
                        f"is {'W->E' if d in 'NS' else 'N->S'}" + (" (reversed for S/W)" if d in "SW" else ""),
                "agents": seen}

    def _tool_ignite(self, a, args):
        x, y = self.target(a, args)
        has_torch = a.count("torch") > 0
        if not has_torch and not self.near_block(a, "campfire"):
            raise ActionError("need_fire", "ignite needs a torch or a heater within 2 tiles")
        yield from self.wait(a, 0.4)
        if not self.ignite(x, y, by=a):
            raise ActionError("wont_burn", f"{self.describe(x, y)} won't burn")
        if has_torch:
            a.add("torch", -1)
        a.bump("fires")
        return {}

    def _chest(self, a, args):
        x, y = self.target(a, args)
        if self.world.block(x, y) != "chest":
            raise ActionError("no_chest", f"{args['dir']} is {self.describe(x, y)}")
        return x, y

    def _tool_store(self, a, args):
        x, y = self._chest(a, args)
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}")
        yield from self.wait(a, 0.2)
        self._chest(a, args)
        n = min(n, a.count(item))
        m = dict(self.world.meta.get((x, y), {}))
        m["items"] = self._merge(m.get("items", {}), {item: n})
        a.add(item, -n)
        self.world.set_meta(x, y, m)
        self.emit("chest", x, y, radius=4, name=a.name, stored={item: n})
        return {"chest": m["items"]}

    def _tool_take(self, a, args):
        x, y = self._chest(a, args)
        yield from self.wait(a, 0.2)
        self._chest(a, args)
        m = dict(self.world.meta.get((x, y), {}))
        items = dict(m.get("items", {}))
        item = args.get("item")
        if not item:
            return {"chest": items}
        n = min(self._n(args), items.get(item, 0))
        if n <= 0:
            raise ActionError("missing_item", f"chest has no {item}; contents: {items}")
        items[item] -= n
        if not items[item]:
            del items[item]
        m["items"] = items
        self.world.set_meta(x, y, m)
        a.add(item, n)
        self.emit("chest", x, y, radius=4, name=a.name, took={item: n})
        return {"chest": items}


LEGEND = {
    "@": "you", "P": "person", "c": "chicken (food)", "k": "cow (food)", "G": "gloom (hostile, at night)",
    "$": "items on ground",
    **{g.char: g.name for g in GROUNDS},
    **{b.char: b.name for b in BLOCKS if b.name != "none"},
}

DIR_ARG = {"dir": "N|E|S|W"}
TOOL_SPECS = {
    "step": {"args": {**DIR_ARG, "run": "bool (optional, sprint: 2x speed, costs energy)"}, "desc": "move one tile"},
    "walk": {"args": {**DIR_ARG, "run": "bool (optional)"}, "desc": "keep walking in a direction until blocked or stopped"},
    "stop": {"args": {}, "desc": "stop the current action"},
    "move_to": {"args": {"x": "int", "y": "int", "run": "bool (optional)"}, "desc": "walk to absolute tile (pathfinding, <=64 tiles)"},
    "dig": {"args": DIR_ARG, "desc": "dig the adjacent block (tree, rock, bush, wall...) or till the ground"},
    "place": {"args": {**DIR_ARG, "item": "str", "text": "str (flags only, optional)"},
              "desc": "place an item: furniture/walls/etc. as blocks; dirt fills holes or water, path lays cobble, plank makes a bridge (water) or floor (land)"},
    "pick_up": {"args": {"item": "str (optional)"}, "desc": "pick up items on your tile"},
    "drop": {"args": {"item": "str", "n": "int"}, "desc": "drop items on your tile"},
    "craft": {"args": {"recipe": "str", "n": "int (optional)"}, "desc": "craft from the recipe book"},
    "attack": {"args": {"target": "entity id"}, "desc": "hit an adjacent agent or creature"},
    "give": {"args": {"target": "agent id", "item": "str", "n": "int"}, "desc": "hand items to an agent within 2 tiles"},
    "eat": {"args": {"item": "str"}, "desc": "eat food"},
    "rest": {"args": {}, "desc": "recover energy (better by a heater or under shelter)"},
    "say": {"args": {"text": "str"}, "desc": f"local chat, heard within {SAY_R} tiles"},
    "shout": {"args": {"text": "str"}, "desc": f"heard within {SHOUT_R} tiles, costs 10 energy"},
    "write_sign": {"args": {**DIR_ARG, "text": "str"}, "desc": "write on an adjacent sign or flag"},
    "read_sign": {"args": DIR_ARG, "desc": "read an adjacent sign or flag"},
    "look_far": {"args": DIR_ARG, "desc": "coarse view of the next 48 tiles in a direction"},
    "ignite": {"args": DIR_ARG, "desc": "set an adjacent flammable tile on fire (needs a torch or a nearby campfire)"},
    "water": {"args": DIR_ARG, "desc": "water a growing crop (needs a watering can): grows twice as fast"},
    "milk": {"args": {"target": "cow id"}, "desc": "milk an adjacent cow (every 2 minutes)"},
    "feed": {"args": {"target": "animal id", "item": "food"}, "desc": "feed an adjacent animal; fed chickens lay eggs"},
    "sleep": {"args": DIR_ARG, "desc": "sleep in an adjacent bed: restores energy, and you respawn there"},
    "post": {"args": {**DIR_ARG, "text": "str"}, "desc": "post a letter in an adjacent mailbox"},
    "open_mail": {"args": DIR_ARG, "desc": "take the letters out of an adjacent mailbox (anyone can)"},
    "store": {"args": {**DIR_ARG, "item": "str", "n": "int"}, "desc": "put items into an adjacent chest"},
    "take": {"args": {**DIR_ARG, "item": "str (omit to list)", "n": "int"}, "desc": "take items from an adjacent chest"},
}
