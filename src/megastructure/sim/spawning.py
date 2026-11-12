"""Mob spawning and the ticking area, after the sandbox classics.

- Ticking: creatures only live (move, lay, breed, hunt) in chunks within SIM_R tiles of someone awake; elsewhere
  the world waits, frozen, until a player comes back. Those chunks are kept loaded, loading one every other tick.
- Meeting a creature is meant to be rare: an event, not scenery.
- Animals belong to the land: when a chunk is generated, a meadow may get a herd (persistent; they never despawn),
  about one chunk in twenty. Every PASSIVE_EVERY, a player with fewer than PASSIVE_CAP animals around may get one more.
- Wild enemies (WILD_SPAWNS): a tusker now and then by day on a meadow, a pincer on a shore; one at a time per player.
  The strawman, the wisp, the wyrm and Old Mossback (with its sporelings) never spawn by themselves (for now).
- Tuskers and pincers despawn when far from everyone (at once past DESPAWN_FAR, by chance past DESPAWN_NEAR).
- Every spawn is out of sight (SPAWN_MIN tiles from everyone) and inside a ticking chunk; caps are per player,
  counted around that player, so a crowd in one place never starves another.
"""

import random
import sqlite3

from ..gen import CHUNK
from .constants import sec
from .entities import CREATURES, Agent, Creature

SIM_R = 48                       # creatures tick within this many tiles of someone awake (whole chunks)
CAP_R = 40                       # caps count the creatures this close to a player
SPAWN_MIN, SPAWN_MAX = 16, 40    # spawns land at least this far from everyone, at most this far from the player
PASSIVE = ("chicken", "cow", "chick", "calf")
PASSIVE_CAP, PASSIVE_EVERY = 2, sec(240)
HERD = {"chicken": (2, 3), "cow": (1, 2)}
PACK = (1, 1)                    # wild enemies come alone
CHUNK_HERD = 0.05                # the chance a newly generated chunk gets a herd (if it has a meadow for it)
# kind: how often it is tried, how many may be around a player, by day only, how many spots one try looks at
WILD_SPAWNS = {"tusker": dict(every=sec(120), cap=1, day=True, tries=1), "pincer": dict(every=sec(90), cap=1, day=False, tries=40)}
ROAMING = ("tusker", "pincer")   # these come and go; the rest stay where they are
RULES = 2                        # the spawn rules' version: a world saved under older ones is thinned once (thin_wild)
HOME_R, KEEP_ONE_IN = 24, 5      # ...sparing animals this close to anyone or their bed, and one in five of the rest
DESPAWN_NEAR, DESPAWN_FAR = 32, 64


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
        for kind, w in WILD_SPAWNS.items():
            if self.tick % w["every"] == 0 and not (w["day"] and self.is_night()):
                a = online[(self.tick // w["every"]) % len(online)]
                if self.count_near(a, (kind,)) < w["cap"]:
                    for _ in range(w["tries"]):
                        if self.spawn_pack(kind, a):
                            break
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
        if kind == "pincer":
            return self.shore(x, y)
        return self.world.ground(x, y) == "grass" and self.world.block(x, y) == "none"

    def spawn_pack(self, kind: str, near: Agent) -> int:
        """One attempt, as the classics do it: a random spot in the ring around a player, then a pack around it."""
        x, y = near.x + self.rng.randint(-SPAWN_MAX, SPAWN_MAX), near.y + self.rng.randint(-SPAWN_MAX, SPAWN_MAX)
        if (x // CHUNK, y // CHUNK) not in self.ticking:
            return 0
        if any(max(abs(x - a.x), abs(y - a.y)) < SPAWN_MIN for a in self.agents.values() if a.online):
            return 0
        lo, hi = HERD.get(kind, PACK)
        return self.place_pack(kind, x, y, self.rng.randint(lo, hi))

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
        for c in [c for c in self.creatures.values() if c.kind in ROAMING]:
            d = min(max(abs(c.x - a.x), abs(c.y - a.y)) for a in online)
            if d > DESPAWN_FAR or (d > DESPAWN_NEAR and self.rng.random() < 1 / 40):
                del self.creatures[c.id]

    def thin_wild(self, store):
        """Once, when a world saved under the old rules (animals everywhere) is first opened under these: most wild
        animals go. Those near anyone, or near anyone's bed, are taken for somebody's and stay; so does one in
        KEEP_ONE_IN of the rest. The world file is copied aside first (world.before-rare-mobs.sqlite)."""
        for cid in [c.id for c in self.creatures.values() if c.kind not in CREATURES]:
            del self.creatures[cid]                          # (a kind the game no longer has: the gloom)
        if store.get_meta("spawn_rules", 1) >= RULES:
            return
        homes = [p for a in self.agents.values() for p in ((a.x, a.y), tuple(a.spawn) if a.spawn else None) if p]
        gone = [c.id for c in self.creatures.values() if c.kind in PASSIVE and c.id % KEEP_ONE_IN
                and not any(max(abs(c.x - hx), abs(c.y - hy)) <= HOME_R for hx, hy in homes)]
        if gone:
            store.commit()
            copy = sqlite3.connect(store.path.with_name(store.path.stem + ".before-rare-mobs.sqlite"))
            store.db.backup(copy)
            copy.close()
            for cid in gone:
                del self.creatures[cid]
        store.set_meta("spawn_rules", RULES)
