"""The hob: a walking clay hearth, the one creature on your side. You make it (a recipe: tiles.py) and set it down
(`place` with a hob in hand: building.py), and it is yours (`owner`): it follows you, and it never goes away.

It keeps a ring of light round itself: when a wild one comes within HOB_GUARD tiles it flares. The warning is its own
(it hunches and its fire draws in: HOB_WINDUP, its sheet's warning frames), then its firebox bursts: every wild one
within HOB_REACH tiles is burnt (HOB_BURN) and runs. It never hurts a person or an animal, and it never chases.
"""

from .constants import cheb, sec, toward
from .entities import CREATURES, ActionError, Creature

FOES = ("tusker", "pincer", "strawman", "wyrm", "gustling", "grumblestump", "snapbloom", "sporeling")   # (not the boss)
HOB_GUARD, HOB_REACH, HOB_WINDUP, HOB_REST, HOB_BURN = 3, 2, 0.58, 2.6, 3
HOB_FOLLOW, HOB_LEASH, HOB_STEP, HOB_SCARES = 2, 30, 0.45, 4.0     # tiles; seconds a tile; seconds what it burnt runs


class Hob:
    """How the hob behaves (stepped by Wild.step_wild), and how one is set down."""

    def _step_hob(self, c, online):
        if c.mode == "windup":                                # the burst: what is close is burnt and runs
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(HOB_REST)
                burnt = [f for f in self.creatures.values() if f.kind in FOES and cheb(f, c) <= HOB_REACH and self.level(c, f)]
                self.emit("flare", c.x, c.y, id=c.id, kind=c.kind, burnt=[[f.kind, f.id] for f in burnt])
                owner = self.agents.get(c.owner)
                for f in burnt:
                    self.flee_from(f, c, HOB_SCARES)
                    f.rest = max(f.rest, self.tick + sec(HOB_SCARES))
                    self.damage(f, HOB_BURN, "burnt", by=owner, who=c)
            return
        foe = min((f for f in self.creatures.values() if f.kind in FOES and cheb(f, c) <= HOB_GUARD and self.level(c, f)),
                  key=lambda f: (cheb(f, c), f.id), default=None)
        if foe and self.tick >= c.rest:
            self.wind_up(c, toward(c, foe), HOB_WINDUP)
            return
        owner = self.agents.get(c.owner)
        if owner and owner.online and HOB_FOLLOW < cheb(owner, c) <= HOB_LEASH:
            self.shuffle_at(c, owner, HOB_STEP)              # (stump.py: a step along the longer way)
        else:
            c.cooldown = sec(0.5) - 1

    def _place_hob(self, a, x, y):
        """Set a hob down on open ground beside you: it is lit, and it is yours."""
        if self.world.block(x, y) not in ("none", "flower") or not self.stand(x, y) or self.entity_at(x, y) is not None:
            raise ActionError("occupied", "a hob needs a clear spot of open ground")
        yield from self.wait(a, 0.5)
        if self.entity_at(x, y) is not None or not a.count("hob"):
            raise ActionError("changed", "the spot is taken")
        a.add("hob", -1)
        c = Creature(self.next_creature, "hob", x, y, CREATURES["hob"]["hp"], owner=a.id)
        self.next_creature += 1
        self.creatures[c.id] = c
        a.bump("placed")
        self.emit("hob_lit", x, y, id=c.id, kind="hob", owner=a.name)
        return {"hob": c.id}
