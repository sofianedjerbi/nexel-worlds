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

TICK_HZ = 5
DAY_TICKS = 3000
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
    # runtime only
    action: "Action | None" = field(default=None, repr=False)
    events: list = field(default_factory=list, repr=False)
    online: bool = False

    def to_json(self) -> dict:
        return {k: getattr(self, k) for k in
                ("id", "name", "x", "y", "persona", "hp", "hunger", "energy", "inventory", "deaths", "stats")}

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
    kind: str  # skitter | sentinel
    x: int
    y: int
    hp: int
    cooldown: int = 0
    heading: int = 0
    built: int = 0

    def to_json(self):
        return {"id": self.id, "kind": self.kind, "x": self.x, "y": self.y, "hp": self.hp,
                "heading": self.heading, "built": self.built}


CREATURES = {
    "skitter": {"hp": 20, "drops": {"meat": 2, "hide": 1}, "char": "s"},
    "sentinel": {"hp": 30, "drops": {"circuit": 1, "alloy": 1}, "char": "S", "damage": 7},
    "accretor": {"hp": 200, "drops": {"core": 2, "cable": 3, "circuit": 2}, "char": "A"},
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
        """'Lights-out': the last quarter of every cycle, when sentinels patrol."""
        return self.time_of_day() >= 0.75

    def clock(self) -> str:
        day = self.tick // DAY_TICKS + 1
        minutes = int(self.time_of_day() * 24 * 60)
        return f"day {day}, {minutes // 60:02d}:{minutes % 60:02d}" + (" (lights-out)" if self.is_night() else "")

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
        if g == "breach":
            self.pits.add((x, y))
        if g in ("coolant", "void"):
            for dx, dy in DIRS.values():
                if self.world.ground(x + dx, y + dy) == "breach":
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

    def sheltered(self, x, y) -> bool:
        walls = sum(1 for dx, dy in DIRS.values() if BLOCKS[self.world.get(x + dx, y + dy)[1]].wall)
        return walls >= 3

    def wait(self, a: Agent, n: int):
        n = n * 2 if a.energy <= 0 else n
        for _ in range(max(1, n)):
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
                if self.world.passable(x, y) and GROUNDS[self.world.get(x, y)[0]].name in ("deck", "moss", "grating"):
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
            if t % 50 == 0 and a.hunger > 0:
                a.hunger -= 1
            if t % 25 == 0:
                if a.hunger == 0:
                    self.damage(a, 1, "starvation")
                elif a.hunger > 40 and a.hp < 100:
                    a.hp += 1
            if t % 40 == 0 and a.action is None and a.energy < 100:
                a.energy += 1
            if (a.x, a.y) in self.fires and t % 5 == 0:
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
        if self.tick % 50 == 0 and online:
            skitters = sum(1 for c in self.creatures.values() if c.kind == "skitter")
            if skitters < min(40, 3 * len(online)):
                a = online[self.rng.randrange(len(online))]
                self._spawn_creature("skitter", a, 12, 30)
            accretors = sum(1 for c in self.creatures.values() if c.kind == "accretor")
            if accretors < max(1, len(online) // 2):
                a = online[self.rng.randrange(len(online))]
                self._spawn_creature("accretor", a, 16, 30)
            sentinels = sum(1 for c in self.creatures.values() if c.kind == "sentinel")
            if self.is_night() and sentinels < len(online):
                a = online[self.rng.randrange(len(online))]
                self._spawn_creature("sentinel", a, 14, 24)
        if not self.is_night() and self.tick % 25 == 0:
            for c in [c for c in self.creatures.values() if c.kind == "sentinel"]:
                if self.rng.random() < 0.2:
                    del self.creatures[c.id]
        for cid in sorted(self.creatures):
            c = self.creatures.get(cid)
            if c is None:
                continue
            if c.cooldown > 0:
                c.cooldown -= 1
                continue
            if c.kind == "accretor":
                self._accrete(c)
            elif c.kind == "skitter":
                c.cooldown = 4 + self.rng.randrange(6)
                d = list(DIRS.values())[self.rng.randrange(4)]
                self._creature_move(c, c.x + d[0], c.y + d[1])
            else:
                prey = min((a for a in online if abs(a.x - c.x) + abs(a.y - c.y) <= 10),
                           key=lambda a: (abs(a.x - c.x) + abs(a.y - c.y), a.id), default=None)
                c.cooldown = 1
                if prey is None:
                    d = list(DIRS.values())[self.rng.randrange(4)]
                    self._creature_move(c, c.x + d[0], c.y + d[1])
                elif max(abs(prey.x - c.x), abs(prey.y - c.y)) <= 1:
                    c.cooldown = 5
                    self.emit("attack", c.x, c.y, attacker=f"sentinel#{c.id}", target=prey.name,
                              damage=CREATURES["sentinel"]["damage"])
                    self.damage(prey, CREATURES["sentinel"]["damage"], "sentinel")
                else:
                    sx = (prey.x > c.x) - (prey.x < c.x)
                    sy = (prey.y > c.y) - (prey.y < c.y)
                    if sx and (not sy or self.rng.random() < 0.5):
                        if not self._creature_move(c, c.x + sx, c.y):
                            self._creature_move(c, c.x, c.y + sy)
                    elif not self._creature_move(c, c.x, c.y + sy):
                        self._creature_move(c, c.x + sx, c.y)

    HEADINGS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    def _accrete(self, c: Creature):
        """Builder automaton: crawls along, extending walls on its left and patching the floor.

        It never overwrites anything: it only builds into empty tiles nobody stands on.
        """
        c.cooldown = 6
        hx, hy = self.HEADINGS[c.heading]
        lx, ly = c.x + hy, c.y - hx  # tile on the left
        if self.world.ground(c.x, c.y) == "breach":
            self.set_tile(c.x, c.y, ground="deck", cause="accretor")
        g, b = self.world.ground(lx, ly), self.world.block(lx, ly)
        if (b == "none" and g in ("deck", "moss", "grating", "slag", "plating")
                and self.entity_at(lx, ly) is None and (lx, ly) not in self.items
                and self.rng.random() < 0.6):
            c.built += 1
            kind = "conduit" if c.built % 7 == 0 else ("scrap_heap" if c.built % 19 == 0 else "structure")
            self.set_tile(lx, ly, block=kind, cause="accretor")
            # keep the left side free of new walls for a few steps, leaving doorways
            if c.built % 5 == 0:
                c.heading = (c.heading + 1) % 4
        if self._creature_move(c, c.x + hx, c.y + hy):
            if self.rng.random() < 0.05:
                c.heading = (c.heading + (1 if self.rng.random() < 0.5 else 3)) % 4
        else:
            c.heading = (c.heading + 1) % 4

    def _creature_move(self, c, x, y) -> bool:
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
            self.fires[(x, y)] = 25 + self.rng.randrange(50)
            self.set_tile(x, y, block="fire", by=by, cause="fire")
            return True
        return False

    def step_environment(self):
        if self.fires:
            for pos in sorted(self.fires):
                x, y = pos
                self.fires[pos] -= 1
                for dx, dy in DIRS.values():
                    if self.rng.random() < 0.02:
                        self.ignite(x + dx, y + dy)
                if self.fires[pos] <= 0:
                    del self.fires[pos]
                    self.set_tile(x, y, ground="slag", block="none", cause="burnt")
        if self.pits and self.tick % 5 == 0:
            for pos in sorted(self.pits):
                x, y = pos
                if self.world.ground(x, y) != "breach":
                    self.pits.discard(pos)
                    continue
                near = {self.world.ground(x + dx, y + dy) for dx, dy in DIRS.values()}
                spill = "coolant" if "coolant" in near else ("void" if "void" in near else None)
                if spill is None:
                    self.pits.discard(pos)
                elif self.rng.random() < 0.25:
                    # coolant floods a breach; a breach at a shaft edge collapses into the void
                    self.pits.discard(pos)
                    self.set_tile(x, y, ground=spill, cause="flood" if spill == "coolant" else "collapse")
                    victim = self.entity_at(x, y)
                    if spill == "void" and victim is not None:
                        self.damage(victim, 999, "fell into the void")
        if self.timers and self.tick % 10 == 0:
            for pos in sorted(self.timers):
                due, kind = self.timers[pos]
                if self.tick < due:
                    continue
                del self.timers[pos]
                if kind == "ripen" and self.world.block(*pos) == "spore_bed":
                    self.set_tile(*pos, block="ripe_bed", cause="grew")
                elif kind == "regrow" and self.world.block(*pos) == "debris":
                    self.set_tile(*pos, block="scrap_heap", cause="grew")
        if self.tick % 100 == 0:
            for key in sorted(self.world.chunks):
                cx, cy = key
                x = cx * 32 + self.rng.randrange(32)
                y = cy * 32 + self.rng.randrange(32)
                if self.rng.random() < 0.1 and self.world.ground(x, y) == "moss" and self.world.block(x, y) == "none":
                    self.set_tile(x, y, block="lichen", cause="grew")

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
    def _tool_step(self, a, args):
        x, y = self.target(a, args)
        yield from self.wait(a, 1)
        if not self.world.passable(x, y):
            raise ActionError("blocked", f"{args['dir']} is {self.describe(x, y)}")
        a.x, a.y = x, y
        return {}

    def _tool_move_to(self, a, args):
        try:
            gx, gy = int(args["x"]), int(args["y"])
        except (KeyError, TypeError, ValueError):
            raise ActionError("bad_args", "move_to needs integer x and y")
        replans = 0
        path = astar(self.world.passable, (a.x, a.y), (gx, gy))
        if path is None:
            far = abs(gx - a.x) + abs(gy - a.y) > 64
            raise ActionError("no_path", "target further than 64 tiles" if far else
                              f"no walkable path to ({gx},{gy}) from ({a.x},{a.y})")
        steps = 0
        while path:
            yield from self.wait(a, 1)
            nx, ny = path[0]
            if not self.world.passable(nx, ny):
                replans += 1
                path = astar(self.world.passable, (a.x, a.y), (gx, gy)) if replans <= 2 else None
                if path is None:
                    raise ActionError("blocked", f"path blocked at ({nx},{ny}); stopped at ({a.x},{a.y})")
                continue
            a.x, a.y = nx, ny
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
            if not ground.diggable or ground.name == "breach":
                raise ActionError("cannot_dig", f"{ground.name} cannot be dug")
            yield from self.wait(a, 6)
            if self.world.block(x, y) != "none":
                raise ActionError("changed", "something was placed there")
            self.spend(a, 1)
            item = "rubble"
            a.add(item)
            self.set_tile(x, y, ground="breach", by=a, cause="dig")
            return {"got": {item: 1}}
        if block.hardness <= 0:
            raise ActionError("cannot_dig", f"{block.name} cannot be dug")
        if block.needs_tool and not a.count(block.needs_tool):
            raise ActionError("need_tool", f"digging {block.name} needs a {block.needs_tool}")
        ticks = block.hardness
        if block.tool and a.count(block.tool):
            ticks = max(1, ticks // 2)
        yield from self.wait(a, ticks)
        if self.world.get(x, y)[1] != b:
            raise ActionError("changed", "the block changed while digging")
        self.spend(a, 1)
        drops = dict(block.drops)
        if block.name == "locker":
            drops = self._merge(drops, self.world.meta.get((x, y), {}).get("items", {}))
        for k, n in drops.items():
            a.add(k, n)
        after = "debris" if block.name == "scrap_heap" else "none"
        self.set_tile(x, y, block=after, by=a, cause="dig")
        if block.name == "scrap_heap":
            self.timers[(x, y)] = [self.tick + 6000, "regrow"]
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
        if item in T.FILLERS:
            covers, new = T.FILLERS[item]
            if b != "none":
                raise ActionError("occupied", f"{args['dir']} has {b}")
            if g not in covers:
                raise ActionError("bad_target", f"{item} can cover {', '.join(sorted(covers))}, not {g}")
            yield from self.wait(a, 2)
            if self.world.ground(x, y) != g or self.world.block(x, y) != "none":
                raise ActionError("changed", "the tile changed")
            a.add(item, -1)
            self.set_tile(x, y, ground=new, by=a, cause="place")
            a.bump("placed")
            return {}
        if item not in PLACEABLE:
            raise ActionError("not_placeable", f"{item} cannot be placed. Placeable: "
                              f"{', '.join(sorted(PLACEABLE) + sorted(T.FILLERS))}")
        block = PLACEABLE[item]
        if b == "debris":
            b = "none"  # debris is junk: building over it clears it
        if b != "none":
            raise ActionError("occupied", f"{args['dir']} has {b}")
        if not GROUNDS[T.G[g]].walkable:
            raise ActionError("bad_target", f"cannot place on {g}")
        if item == "spore" and g not in ("moss", "deck"):
            raise ActionError("bad_target", "spores only take on moss or deck")
        if BLOCKS[T.B[block]].solid and self.entity_at(x, y):
            raise ActionError("occupied", "someone is standing there")
        yield from self.wait(a, 2)
        if self.world.block(x, y) not in ("none", "debris"):
            raise ActionError("changed", "tile was taken")
        if BLOCKS[T.B[block]].solid and self.entity_at(x, y):
            raise ActionError("occupied", "someone stepped there")
        a.add(item, -1)
        self.set_tile(x, y, block=block, by=a, cause="place")
        if block == "spore_bed":
            self.timers[(x, y)] = [self.tick + 1500, "ripen"]
        if block == "beacon":
            text = str(args.get("text") or f"claimed by {a.name}")[:MAX_TEXT]
            self.world.set_meta(x, y, {"text": text, "by": a.name})
        a.bump("placed")
        return {}

    def _tool_pick_up(self, a, args):
        yield from self.wait(a, 1)
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
        yield from self.wait(a, 1)
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
        yield from self.wait(a, r.ticks * n)
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
        yield from self.wait(a, 2)
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
        yield from self.wait(a, 1)
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
        yield from self.wait(a, 2)
        if not a.count(item):
            raise ActionError("missing_item", "it's gone")
        a.add(item, -1)
        a.hunger = min(100, a.hunger + T.FOOD[item])
        return {}

    def _tool_rest(self, a, args):
        bonus = self.near_block(a, "heater") or self.sheltered(a.x, a.y)
        for _ in range(10):
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
        yield from self.wait(a, 1)
        self.stats["chat"] += 1
        a.bump("said")
        self.emit("say", a.x, a.y, radius=SAY_R, **{"from": a.name}, text=text)
        return {}

    def _tool_shout(self, a, args):
        text = self._text(args)
        if a.energy < 10:
            raise ActionError("too_tired", "shouting needs 10 energy")
        yield from self.wait(a, 1)
        self.spend(a, 10)
        self.stats["chat"] += 1
        a.bump("said")
        self.emit("shout", a.x, a.y, radius=SHOUT_R, **{"from": a.name}, text=text)
        return {}

    def _tool_write_sign(self, a, args):
        x, y = self.target(a, args)
        text = self._text(args)
        if self.world.block(x, y) not in ("sign", "beacon"):
            raise ActionError("no_sign", f"{args['dir']} is {self.describe(x, y)}, not a sign")
        yield from self.wait(a, 3)
        if self.world.block(x, y) not in ("sign", "beacon"):
            raise ActionError("no_sign", "the sign is gone")
        self.world.set_meta(x, y, {"text": text, "by": a.name})
        self.emit("sign", x, y, by=a.name, text=text)
        return {}

    def _tool_read_sign(self, a, args):
        x, y = self.target(a, args)
        yield from self.wait(a, 1)
        m = self.world.meta.get((x, y))
        if self.world.block(x, y) not in ("sign", "beacon") or not m:
            raise ActionError("no_sign", f"no readable sign {args['dir']}")
        return {"text": m.get("text", ""), "by": m.get("by")}

    def _tool_look_far(self, a, args):
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "dir must be one of N, E, S, W")
        yield from self.wait(a, 1)
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
        if not has_torch and not self.near_block(a, "heater"):
            raise ActionError("need_fire", "ignite needs a torch or a heater within 2 tiles")
        yield from self.wait(a, 2)
        if not self.ignite(x, y, by=a):
            raise ActionError("wont_burn", f"{self.describe(x, y)} won't burn")
        if has_torch:
            a.add("torch", -1)
        a.bump("fires")
        return {}

    def _locker(self, a, args):
        x, y = self.target(a, args)
        if self.world.block(x, y) != "locker":
            raise ActionError("no_locker", f"{args['dir']} is {self.describe(x, y)}")
        return x, y

    def _tool_store(self, a, args):
        x, y = self._locker(a, args)
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}")
        yield from self.wait(a, 1)
        self._locker(a, args)
        n = min(n, a.count(item))
        m = dict(self.world.meta.get((x, y), {}))
        m["items"] = self._merge(m.get("items", {}), {item: n})
        a.add(item, -n)
        self.world.set_meta(x, y, m)
        self.emit("locker", x, y, radius=4, name=a.name, stored={item: n})
        return {"locker": m["items"]}

    def _tool_take(self, a, args):
        x, y = self._locker(a, args)
        yield from self.wait(a, 1)
        self._locker(a, args)
        m = dict(self.world.meta.get((x, y), {}))
        items = dict(m.get("items", {}))
        item = args.get("item")
        if not item:
            return {"locker": items}
        n = min(self._n(args), items.get(item, 0))
        if n <= 0:
            raise ActionError("missing_item", f"locker has no {item}; contents: {items}")
        items[item] -= n
        if not items[item]:
            del items[item]
        m["items"] = items
        self.world.set_meta(x, y, m)
        a.add(item, n)
        self.emit("locker", x, y, radius=4, name=a.name, took={item: n})
        return {"locker": items}


LEGEND = {
    "@": "you", "P": "agent", "s": "skitter (vermin, meat)", "S": "sentinel (hostile automaton, lights-out)",
    "A": "accretor (builder automaton, extends the structure)",
    "$": "items on ground",
    **{g.char: g.name for g in GROUNDS},
    **{b.char: b.name for b in BLOCKS if b.name != "none"},
}

DIR_ARG = {"dir": "N|E|S|W"}
TOOL_SPECS = {
    "step": {"args": DIR_ARG, "desc": "move one tile"},
    "move_to": {"args": {"x": "int", "y": "int"}, "desc": "walk to absolute tile (pathfinding, <=64 tiles)"},
    "dig": {"args": DIR_ARG, "desc": "dig the adjacent block (tree, rock, wall...) or the ground into a pit"},
    "place": {"args": {**DIR_ARG, "item": "str", "text": "str (beacons only, optional)"},
              "desc": "place a block item; rubble fills breaches/coolant; alloy lays plating"},
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
    "ignite": {"args": DIR_ARG, "desc": "set an adjacent flammable tile on fire (needs torch or nearby heater)"},
    "store": {"args": {**DIR_ARG, "item": "str", "n": "int"}, "desc": "put items into an adjacent locker"},
    "take": {"args": {**DIR_ARG, "item": "str (omit to list)", "n": "int"}, "desc": "take items from an adjacent locker"},
}
