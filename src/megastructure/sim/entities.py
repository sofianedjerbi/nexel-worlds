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
    energy: int = 100
    inventory: dict = field(default_factory=dict)
    deaths: int = 0
    stats: dict = field(default_factory=dict)
    spawn: list | None = None  # set by sleeping in a bed: you wake up there after dying
    sailing: bool = False      # in a boat: water is passable, land ends the trip
    can: int = 12              # waterings left in the watering can; refill at a well or any water
    # runtime only
    action: "Action | None" = field(default=None, repr=False)
    ready: int = field(default=0, repr=False)   # first tick the next stride may start (movement cooldown)
    events: list = field(default_factory=list, repr=False)
    online: bool = False

    def to_json(self) -> dict:
        return {k: getattr(self, k) for k in
                ("id", "name", "x", "y", "persona", "hp", "hunger", "energy", "inventory", "deaths", "stats", "spawn", "sailing", "can")}

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
    scared: int = 0     # hit: runs away from `threat` until this tick (runtime only)
    threat: tuple = (0, 0)

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
