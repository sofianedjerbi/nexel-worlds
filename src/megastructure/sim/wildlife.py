"""Wildlife: farm animals roam in small herds around everyone who's awake, and glooms come out at night."""

from .constants import ANIMAL_MAX, sec
from .entities import Agent, Creature

FARM_KINDS = ("chicken", "cow", "chick", "calf")
HERD_NEAR, HERD_R = 16, 20       # keep about this many farm animals within this many tiles of each player (a few a screen)
HERD_SIZE = {"chicken": (2, 4), "cow": (2, 3)}
GLOOMS_NEAR, GLOOM_R = 3, 24     # at night, up to this many glooms around each player
FAR = HERD_R + 8                 # animals this far from everyone awake may make room for new ones
KEEP = ("coop", "trough", "fence", "gate", "barn")   # ...unless someone's keeping them (a pen, a coop, a trough)


class Wildlife:
    """Simulation mixin: spawning herds and glooms near players, and making room for them."""

    def step_wildlife(self, online: list[Agent]):
        if not online:
            return
        if self.tick % sec(3) == 0:
            a = online[(self.tick // sec(3)) % len(online)]        # one player a turn
            near = [c for c in self.creatures.values() if c.kind in FARM_KINDS
                    and max(abs(c.x - a.x), abs(c.y - a.y)) <= HERD_R]
            if len(near) < HERD_NEAR:
                total = sum(1 for c in self.creatures.values() if c.kind in FARM_KINDS)
                if total < ANIMAL_MAX or self._make_room(online):
                    self._spawn_herd("chicken" if self.rng.random() < 0.6 else "cow", a)
        if self.tick % sec(5) == 0 and self.is_night():
            a = online[self.rng.randrange(len(online))]
            glooms = sum(1 for c in self.creatures.values()
                         if c.kind == "gloom" and max(abs(c.x - a.x), abs(c.y - a.y)) <= GLOOM_R)
            if glooms < GLOOMS_NEAR:
                self._spawn_creature("gloom", a, 14, GLOOM_R)

    def _spawn_herd(self, kind: str, near: Agent):
        """A few of a kind together, just out of sight, so they wander in."""
        lead = self._spawn_creature(kind, near, 14, HERD_R - 2)
        if lead is None:
            return
        lo, hi = HERD_SIZE[kind]
        for _ in range(self.rng.randint(lo, hi) - 1):
            for _ in range(6):
                x, y = lead.x + self.rng.randint(-2, 2), lead.y + self.rng.randint(-2, 2)
                if self.world.passable(x, y) and self.entity_at(x, y) is None:
                    self.creatures[self.next_creature] = Creature(self.next_creature, kind, x, y, lead.hp)
                    self.next_creature += 1
                    break

    def _make_room(self, online: list[Agent]) -> bool:
        """The world is full: the farthest animal from everyone, that nobody keeps, wanders off for good."""
        def gap(c):
            return min(max(abs(c.x - a.x), abs(c.y - a.y)) for a in online)
        for c in sorted((c for c in self.creatures.values() if c.kind in FARM_KINDS), key=gap, reverse=True):
            if gap(c) < FAR:
                return False
            if c.love > self.tick or c.milked:
                continue
            if any(self.world.block(c.x + dx, c.y + dy) in KEEP for dx in range(-4, 5) for dy in range(-4, 5)):
                continue
            del self.creatures[c.id]
            return True
        return False
