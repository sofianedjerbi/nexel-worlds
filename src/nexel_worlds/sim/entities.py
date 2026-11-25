"""Agents, creatures and in-flight actions."""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Simulation


class ActionError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code, detail)
        self.code, self.detail = code, detail


def failure(e: Exception) -> dict:
    """An action that stopped on an exception -> what it answers. A refusal (ActionError) says why; anything else is
    a bug: written to the log, and the action only fails (never the whole world's clock with it)."""
    if isinstance(e, ActionError):
        return {"ok": False, "status": "failed", "error": e.code, "detail": e.detail}
    logging.getLogger(__name__).exception("an action broke")
    return {"ok": False, "status": "failed", "error": "bug", "detail": f"something went wrong in the game ({type(e).__name__})"}


@dataclass
class Agent:
    id: int
    name: str
    x: int
    y: int
    persona: str = ""
    hp: float = 20             # health, in half hearts: 20 is ten hearts (constants.HP_MAX); a half is the least there is
    hunger: int = 20           # food, in half pieces: 20 is the bar full; high is fed, 0 is starving
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
    sat: float = 5.0           # saturation: food in reserve, unseen (needs.py)
    tired: float = 0.0         # tiredness, 0 to 4 (needs.py)
    # runtime only
    action: "Action | None" = field(default=None, repr=False)
    held: str | None = field(default=None, repr=False)   # what is in the hand: a player's selected slot (server op `hold`): the others see it in the paw (views.py)
    aside: "Action | None" = field(default=None, repr=False)   # what the hands are doing meanwhile (constants.ASIDE: eating): it runs beside `action`
    ready: int = field(default=0, repr=False)   # first tick the next stride may start (movement cooldown)
    via: list = field(default_factory=list, repr=False)   # (x, y, n): tiles a player's screen has already walked to, to make in order (Movement.follow)
    via_done: int = field(default=0, repr=False)
    flying: int | None = field(default=None, repr=False)   # in the air (leaping.py): the height it left from, kept until it lands
    flying_n: int = field(default=0, repr=False)          # ...the tiles of its flight made so far, and the tick of the last
    flying_at: int = field(default=0, repr=False)   # the number of the last of them reached (or given up)
    spring: dict = field(default_factory=dict, repr=False)   # (x, y) -> until tick: the steps they jumped for (Movement._tool_jump)
    swing_ready: int = field(default=0, repr=False)   # first tick the next attack may land
    events: list = field(default_factory=list, repr=False)
    online: bool = False

    @property
    def bot(self) -> bool:
        """An AI player: any persona but "human" (a person's page says "human"; none given counts as a person)."""
        return bool(self.persona) and self.persona != "human"

    def to_json(self) -> dict:
        return {k: getattr(self, k) for k in
                ("id", "name", "x", "y", "z", "persona", "hp", "hunger", "inventory", "deaths", "stats", "spawn", "sailing", "can", "xp", "worn", "race", "sat", "tired")}

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
    kind: str  # chicken | cow | chick | calf | tusker | pincer | strawman | wisp | wyrm | gustling | grumblestump | snapbloom | mossback | sporeling | hob
    x: int
    y: int
    hp: int
    z: int = -99        # the height it stands at, as a person's (sim/bodies.py); -99: nobody has said: the lowest ground
    cooldown: int = 0
    milked: int = 0     # tick of the last milking (cows)
    love: int = 0       # fed: shows hearts and (chickens) lays an egg soon, until this tick
    lay: int = 0        # next tick a chicken may lay an egg
    born: int = 0       # tick of birth (chicks and calves grow up)
    name: str = ""      # given by someone (/name): it is theirs, and never goes away (spawning.py)
    scared: int = 0     # hit: runs away from `threat` until this tick (runtime only)
    threat: tuple = (0, 0)
    mode: str = ""      # wild enemies (wild.py): "windup", "charge", "stun" (runtime only, like the next four)
    until: int = 0      # the tick the current mode ends
    dir: tuple = (0, 1)   # the way it faces, or charges
    rest: int = 0       # no new attack before this tick
    left: int = 0       # tiles left in a charge (Old Mossback: the tick until which its neck is out)
    awake: int = 0      # Old Mossback: it stays up until this tick
    angry: int = 0      # a tusker that was hit: angry until this tick, at `foe` (wild.py; runtime only)
    foe: int = 0        # ...the id of whoever hit it
    loot: dict = field(default_factory=dict)   # what a gustling snatched: it falls where it dies (wild.py; runtime only)
    owner: int = 0      # a hob: the id of whoever set it down (hob.py; saved)

    def __post_init__(self):                       # (one saved on the old scale, 30 for a cow: no more than its kind has)
        self.hp = min(self.hp, CREATURES.get(self.kind, {}).get("hp", self.hp))

    def to_json(self):
        return {"id": self.id, "kind": self.kind, "x": self.x, "y": self.y, "z": self.z, "hp": self.hp,
                "milked": self.milked, "love": self.love, "lay": self.lay, "born": self.born, **({"name": self.name} if self.name else {}),
                **({"owner": self.owner} if self.owner else {})}

# hp: in half hearts, as a person's (a chicken has one heart, a cow three, a tusker four, Old Mossback thirty: a fifth
# of what they were on their own old scale, so each takes the same number of blows). damage: what it does to you, in half
# hearts. drops: what one leaves when it dies, a line for each thing: (item, chance, at least, at most). The first lines are
# its usual drop, less sure than it was (a chicken always left a meat and an egg, a cow three meat and a milk: the
# same thing every time); the last is a rare one, something you would otherwise have to make. The boss's are sure.
CREATURES = {
    "chicken": {"hp": 2, "drops": (("meat", .6, 1, 1), ("egg", .15, 1, 1), ("heart_charm", .02, 1, 1)), "char": "c"},
    "cow": {"hp": 6, "drops": (("meat", .8, 1, 2), ("milk", .15, 1, 1), ("leather_boots", .03, 1, 1)), "char": "k"},
    "chick": {"hp": 1, "drops": (("meat", .3, 1, 1),), "char": "c", "grows": ("chicken", 300)},
    "calf": {"hp": 3, "drops": (("meat", .5, 1, 1),), "char": "k", "grows": ("cow", 360)},
    "tusker": {"hp": 8, "drops": (("meat", .8, 1, 2), ("leather_vest", .05, 1, 1)), "char": "D", "damage": 3},
    "pincer": {"hp": 3, "drops": (("meat", .5, 1, 1), ("shell_plate", .05, 1, 1)), "char": "I", "damage": 1},
    "strawman": {"hp": 10, "drops": (("hay", 1, 1, 2), ("straw_hat", .1, 1, 1)), "char": "S", "damage": 2},
    # untouchable: a light, a hand goes through it (sim/combat.py refuses the blow)
    "wisp": {"hp": 1, "drops": (), "char": "i", "untouchable": True},
    "gustling": {"hp": 3, "drops": (("seed", .5, 1, 2), ("leaf_charm", .05, 1, 1)), "char": "j"},   # (and what it stole: its `loot`)
    "grumblestump": {"hp": 14, "drops": (("wood", .9, 2, 4), ("spore_charm", .05, 1, 1)), "char": "N", "damage": 4},
    "snapbloom": {"hp": 6, "drops": (("seed", .6, 1, 2), ("flower_charm", .05, 1, 1)), "char": "d", "damage": 2},
    "hob": {"hp": 20, "drops": (("stone", 1, 3, 5), ("flame_charm", .1, 1, 1)), "char": "a"},     # an ally (hob.py)
    "wyrm": {"hp": 12, "drops": (("meat", 1, 2, 4), ("frost_charm", .1, 1, 1)), "char": "E", "damage": 3.5},
    "mossback": {"hp": 60, "drops": (("shell_plate", 1, 5, 5), ("meat", 1, 6, 6), ("fruit", 1, 4, 4), ("mushroom", 1, 3, 3)), "char": "G", "damage": 4.5, "snap": 5.5, "wide": 1},   # (wide: a tile each side of its own)   # the first boss (boss.py)
    "sporeling": {"hp": 1, "drops": (("mushroom", .05, 1, 1),), "char": "s", "damage": 0.5},
}


def roll_drops(kind: str, rng, luck: float = 1.0) -> dict:
    """What one of this kind leaves this time: each line of its table by its chance (times `luck`: a dev tool makes
    every line sure, for tests)."""
    out = {}
    for item, chance, lo, hi in CREATURES[kind]["drops"]:
        if rng.random() < chance * luck:
            out[item] = out.get(item, 0) + rng.randint(lo, hi)
    return out


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
        if self.result is not None:                  # (already ended: interrupted while it ran, it comes back once more)
            return
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
