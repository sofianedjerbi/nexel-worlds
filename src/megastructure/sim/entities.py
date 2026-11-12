"""Agents, creatures and in-flight actions."""

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Simulation


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
    inventory: dict = field(default_factory=dict)
    deaths: int = 0
    stats: dict = field(default_factory=dict)
    spawn: list | None = None  # set by sleeping in a bed: you wake up there after dying
    sailing: bool = False      # in a boat: water is passable, land ends the trip
    z: int = 0                 # the height you stand at (over a cave: on the hill, or in under it)
    xp: int = 0                # experience (sim/progress.py)
    can: int = 12              # waterings left in the watering can; refill at a well or any water
    worn: dict = field(default_factory=dict)   # what you wear: slot -> item (sim/wear.py)
    race: str = "cat"          # cat, bunny, bear, frog or duck (tiles.RACES): looks only
    # runtime only
    action: "Action | None" = field(default=None, repr=False)
    aside: "Action | None" = field(default=None, repr=False)   # what the hands are doing meanwhile (constants.ASIDE: eating): it runs beside `action`
    ready: int = field(default=0, repr=False)   # first tick the next stride may start (movement cooldown)
    via: list = field(default_factory=list, repr=False)   # (x, y, n): tiles a player's screen has already walked to, to make in order (Movement.follow)
    via_done: int = field(default=0, repr=False)   # the number of the last of them reached (or given up)
    swing_ready: int = field(default=0, repr=False)   # first tick the next attack may land
    events: list = field(default_factory=list, repr=False)
    online: bool = False

    def to_json(self) -> dict:
        return {k: getattr(self, k) for k in
                ("id", "name", "x", "y", "z", "persona", "hp", "hunger", "inventory", "deaths", "stats", "spawn", "sailing", "can", "xp", "worn", "race")}

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
    kind: str  # chicken | cow | chick | calf | tusker | pincer | strawman | wisp | wyrm | mossback | sporeling
    x: int
    y: int
    hp: int
    z: int = -99        # the height it stands at, as a person's (sim/bodies.py); -99: nobody has said: the lowest ground
    cooldown: int = 0
    milked: int = 0     # tick of the last milking (cows)
    love: int = 0       # fed: shows hearts and (chickens) lays an egg soon, until this tick
    lay: int = 0        # next tick a chicken may lay an egg
    born: int = 0       # tick of birth (chicks and calves grow up)
    scared: int = 0     # hit: runs away from `threat` until this tick (runtime only)
    threat: tuple = (0, 0)
    mode: str = ""      # wild enemies (wild.py): "windup", "charge", "stun" (runtime only, like the next four)
    until: int = 0      # the tick the current mode ends
    dir: tuple = (0, 1)   # the way it faces, or charges
    rest: int = 0       # no new attack before this tick
    left: int = 0       # tiles left in a charge (Old Mossback: the tick until which its neck is out)
    awake: int = 0      # Old Mossback: it stays up until this tick

    def to_json(self):
        return {"id": self.id, "kind": self.kind, "x": self.x, "y": self.y, "z": self.z, "hp": self.hp,
                "milked": self.milked, "love": self.love, "lay": self.lay, "born": self.born}

CREATURES = {
    "chicken": {"hp": 10, "drops": {"meat": 1, "egg": 1}, "char": "c"},
    "cow": {"hp": 30, "drops": {"meat": 3, "milk": 1}, "char": "k"},
    "chick": {"hp": 4, "drops": {"meat": 1}, "char": "c", "grows": ("chicken", 300)},
    "calf": {"hp": 12, "drops": {"meat": 1}, "char": "k", "grows": ("cow", 360)},
    "tusker": {"hp": 40, "drops": {"meat": 2}, "char": "D", "damage": 14},
    "pincer": {"hp": 14, "drops": {"meat": 1}, "char": "I", "damage": 5},
    "strawman": {"hp": 50, "drops": {"hay": 2}, "char": "S", "damage": 10},
    "wisp": {"hp": 1, "drops": {}, "char": "i"},
    "wyrm": {"hp": 60, "drops": {"meat": 4}, "char": "E", "damage": 18},
    "mossback": {"hp": 300, "drops": {"shell_plate": 5, "meat": 6, "fruit": 4, "mushroom": 3}, "char": "G", "damage": 22, "snap": 28},   # the first boss (boss.py)
    "sporeling": {"hp": 1, "drops": {}, "char": "s", "damage": 3},
}


class Action:
    def __init__(self, agent: Agent, tool: str, args: dict, gen, on_done=None):
        self.agent, self.tool, self.args, self.gen = agent, tool, args, gen
        self.on_done = on_done
        self.started_tick = None
        self.ticks = 0
        self.result = None
        self.tiles: list = []
        self.snapshot = (dict(agent.inventory), agent.hp, agent.hunger, agent.x, agent.y)
        self.expected = 0  # ticks this action is expected to take (set by Simulation.wait)
        self.seen_events: list = []

    def finish(self, result: dict, sim: "Simulation"):
        a = self.agent
        inv0, hp0, hu0, x0, y0 = self.snapshot
        inv = {}
        for k in set(inv0) | set(a.inventory):
            d = a.inventory.get(k, 0) - inv0.get(k, 0)
            if d:
                inv[k] = d
        changed = {}
        if inv:
            changed["inventory"] = inv
        for key, before, now in (("hp", hp0, a.hp), ("hunger", hu0, a.hunger)):
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
        if a.aside is self:
            a.aside = None
        if self.on_done:
            self.on_done(result)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
