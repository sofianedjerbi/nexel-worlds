"""Mob spawning and the ticking area, after the sandbox classics.

- Ticking: creatures only live (move, lay, breed, hunt) in chunks within SIM_R tiles of someone awake; elsewhere
  the world waits, frozen, until a player comes back. Those chunks are kept loaded, loading one every other tick.
- Animals belong to the land: when a chunk is generated, a meadow may get a herd (persistent; they never despawn).
  Every PASSIVE_EVERY, a player whose surroundings hold fewer than PASSIVE_CAP animals may get one more herd.
- Glooms are spawned every second at night, in packs, in the dark (not near fire, not indoors), up to HOSTILE_CAP
  around each player; they despawn when far from everyone (at once past DESPAWN_FAR, by chance past DESPAWN_NEAR).
- Every spawn is out of sight (SPAWN_MIN tiles from everyone) and inside a ticking chunk; caps are per player,
  counted around that player, so a crowd in one place never starves another.
"""

import random

from ..gen import CHUNK
from .constants import sec
from .entities import CREATURES, Agent, Creature

SIM_R = 48                       # creatures tick within this many tiles of someone awake (whole chunks)
CAP_R = 40                       # caps count the creatures this close to a player
SPAWN_MIN, SPAWN_MAX = 16, 40    # spawns land at least this far from everyone, at most this far from the player
PASSIVE = ("chicken", "cow", "chick", "calf")
PASSIVE_CAP, PASSIVE_EVERY = 6, sec(45)
HOSTILE_CAP = 3
HERD = {"chicken": (2, 3), "cow": (1, 2)}
PACK = (1, 2)                    # glooms come alone or in twos
CHUNK_HERD = 0.2                 # the chance a newly generated chunk gets a herd (if it has a meadow for it)
DESPAWN_NEAR, DESPAWN_FAR = 32, 64
LIGHT, LIGHT_R = ("campfire", "fire"), 6


class Spawning:
    """Simulation mixin: which chunks tick, and creatures coming into (and out of) the world."""

    keep_loaded = True                                   # (unit tests switch it off: generating land is slow)

    def ticking_chunks(self, online: list[Agent]) -> set:
        r = SIM_R // CHUNK + 1
        return {(a.x // CHUNK + dx, a.y // CHUNK + dy) for a in online for dx in range(-r, r + 1) for dy in range(-r, r + 1)}

    def load_one(self, online: list[Agent]):
        missing = [k for k in self.ticking if k not in self.world.chunks]
        if missing:
            def gap(k):
                return min(max(abs(k[0] - a.x // CHUNK), abs(k[1] - a.y // CHUNK)) for a in online)
            self.world.prefetch(*min(missing, key=gap))     # (generated off the tick; in next time round)

    def ticks(self, c: Creature) -> bool:
        """Lives this tick: in the ticking area, with all its neighbouring chunks in memory (what it looks at around
        itself, a trough or a coop a few tiles off, must never make the world load or generate land mid-tick)."""
        cx, cy = c.x // CHUNK, c.y // CHUNK
        if (cx, cy) not in self.ticking:
            return False
        if not self.keep_loaded:                          # (unit tests: nobody keeps land loaded, so don't ask)
            return True
        return all((cx + dx, cy + dy) in self.world.chunks for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def step_spawning(self, online: list[Agent]):
        self.ticking = self.ticking_chunks(online)
        if self.keep_loaded and self.tick % 2 == 0:          # keep the ticking area loaded, nearest chunk first,
            self.load_one(online)                            # one at a time (generating one costs ~30 ms)
        fresh, self.world.fresh = self.world.fresh, []    # chunks generated since last tick: animals come with them
        for cx, cy in fresh:
            self.populate_chunk(cx, cy)
        if not online:
            return
        if self.tick % PASSIVE_EVERY == 0:
            for a in online:
                if self.count_near(a, PASSIVE) < PASSIVE_CAP:
                    self.spawn_pack(self.rng.choice(("chicken", "chicken", "cow")), a)
        if self.tick % sec(1) == 0 and self.is_night():
            a = online[(self.tick // sec(1)) % len(online)]
            if self.count_near(a, ("gloom",)) < HOSTILE_CAP:
                self.spawn_pack("gloom", a)
        if self.tick % sec(1) == 0:
            self.despawn_far(online)

    def count_near(self, a: Agent, kinds) -> int:
        return sum(1 for c in self.creatures.values() if c.kind in kinds and max(abs(c.x - a.x), abs(c.y - a.y)) <= CAP_R)

    def loaded_around(self, x: int, y: int, r: int = 8) -> bool:
        """Spawning only looks at land already in memory: it never makes the world generate or load a chunk."""
        return all(((x + dx) // CHUNK, (y + dy) // CHUNK) in self.world.chunks for dx in (-r, r) for dy in (-r, r))

    def spawn_spot_ok(self, kind: str, x: int, y: int, fresh=False) -> bool:
        if not fresh and not self.loaded_around(x, y):
            return False
        if not self.world.passable(x, y) or self.entity_at(x, y) is not None or (not fresh and self.sheltered(x, y)):
            return False
        if kind == "gloom":                                  # glooms keep to the dark
            return not any(self.world.block(x + dx, y + dy) in LIGHT
                           for dx in range(-LIGHT_R, LIGHT_R + 1) for dy in range(-LIGHT_R, LIGHT_R + 1))
        return self.world.ground(x, y) == "grass" and self.world.block(x, y) == "none"

    def spawn_pack(self, kind: str, near: Agent):
        """One attempt, as the classics do it: a random spot in the ring around a player, then a pack around it."""
        x, y = near.x + self.rng.randint(-SPAWN_MAX, SPAWN_MAX), near.y + self.rng.randint(-SPAWN_MAX, SPAWN_MAX)
        if (x // CHUNK, y // CHUNK) not in self.ticking:
            return
        if any(max(abs(x - a.x), abs(y - a.y)) < SPAWN_MIN for a in self.agents.values() if a.online):
            return
        lo, hi = PACK if kind == "gloom" else HERD[kind]
        self.place_pack(kind, x, y, self.rng.randint(lo, hi))

    def place_pack(self, kind: str, x: int, y: int, n: int, chunk=None) -> int:
        """Up to n of a kind around (x, y); with `chunk`, only inside that (freshly generated) chunk, so placing
        them never makes the world generate the next chunk over."""
        placed = 0
        for _ in range(n * 4):
            if placed >= n:
                break
            px, py = (x, y) if not placed else (x + self.rng.randint(-2, 2), y + self.rng.randint(-2, 2))
            if chunk and (px // CHUNK, py // CHUNK) != chunk or not self.spawn_spot_ok(kind, px, py, fresh=bool(chunk)):
                if not placed:
                    return 0                                 # the spot itself won't do: no pack this time
                continue
            c = Creature(self.next_creature, kind, px, py, CREATURES[kind]["hp"])
            self.next_creature += 1
            self.creatures[c.id] = c
            placed += 1
        return placed

    def populate_chunk(self, cx: int, cy: int):
        """A newly generated chunk: maybe a herd on its meadow (decided by the chunk's own dice)."""
        dice = random.Random(self.seed * 7_919 + cx * 104_729 + cy * 1_299_709)
        if dice.random() >= CHUNK_HERD:
            return
        kind = "chicken" if dice.random() < 0.6 else "cow"
        for _ in range(8):
            x, y = cx * CHUNK + dice.randrange(CHUNK), cy * CHUNK + dice.randrange(CHUNK)
            if any(max(abs(x - a.x), abs(y - a.y)) < SPAWN_MIN for a in self.agents.values() if a.online):
                continue
            if self.place_pack(kind, x, y, dice.randint(*HERD[kind]), chunk=(cx, cy)):
                return

    def despawn_far(self, online: list[Agent]):
        for c in [c for c in self.creatures.values() if c.kind == "gloom"]:
            d = min(max(abs(c.x - a.x), abs(c.y - a.y)) for a in online)
            if d > DESPAWN_FAR or (d > DESPAWN_NEAR and self.rng.random() < 1 / 40):
                del self.creatures[c.id]
