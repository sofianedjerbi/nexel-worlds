"""Two plants that are more than they look: the grumblestump (a stump that walks at night and slams the ground) and the
snapbloom (a flower that creeps up by day and bites). Both warn before they hurt, as every wild one does (wild.py):
`mode` goes "windup" and the client plays the move from its first frame; the blow lands only on who is still in reach.

The grumblestump: by day a plain stump, eyes shut (`mode` "sleep": it does nothing). At night it shuffles at the nearest
person; beside them it raises its arms (STUMP_WINDUP, long: the time to step away), then slams the ground, and everyone
within STUMP_REACH tiles is hit. The snapbloom: by day it stands among the flowers and shuffles a tile closer now and
then; beside you it rears back with its mouth open (BLOOM_WINDUP), then lunges and bites if you are still beside it.
At night it sleeps, a flower like the others. A hob's burst sends either running (hob.py, Wild.run_off).
"""

from .constants import cheb, sec, toward

STUMP_SEES, STUMP_REACH, STUMP_WINDUP, STUMP_REST, STUMP_STEP = 8, 2, 0.84, 2.5, 0.9   # (the windup: its sheet's warning frames)
BLOOM_SEES, BLOOM_WINDUP, BLOOM_REST, BLOOM_STEP = 5, 0.86, 2.0, 1.6
SCARED_STRIDE = 0.5                                       # seconds a tile, running from a hob


class Stump:
    """The grumblestump (stepped by Wild.step_wild)."""

    def _step_grumblestump(self, c, online):
        if c.mode == "windup":                                # arms up: down they come; the ring hits all within reach
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(STUMP_REST)
                self.emit("slam", c.x, c.y, id=c.id, kind=c.kind)
                for a in [a for a in online if cheb(a, c) <= STUMP_REACH]:
                    self.bite(c, a)
            return
        if self.run_off(c, SCARED_STRIDE):
            return
        if not self.is_night():                               # by day it is only a stump
            c.mode, c.cooldown = "sleep", sec(2) - 1
            return
        c.mode = ""
        prey = self.nearest(c, online, STUMP_SEES)
        if prey is None:
            self.stroll(c, 2.0, 2.0)
            return
        if cheb(prey, c) <= 1:
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), STUMP_WINDUP)
            return
        self.shuffle_at(c, prey, STUMP_STEP)

    def shuffle_at(self, c, prey, stride):
        """A step toward prey along the longer way, or the other if that is blocked; then a wait of `stride` seconds."""
        c.cooldown = sec(stride) - 1
        d = toward(c, prey)
        other = (0, (prey.y > c.y) - (prey.y < c.y)) if d[0] else ((prey.x > c.x) - (prey.x < c.x), 0)
        for step in (d, other):
            if step != (0, 0) and self._creature_move(c, c.x + step[0], c.y + step[1]):
                c.dir = step
                return


class Bloom:
    """The snapbloom (stepped by Wild.step_wild)."""

    def _step_snapbloom(self, c, online):
        if c.mode == "windup":                                # reared back: the lunge, if you are still beside it
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(BLOOM_REST)
                prey = self.nearest(c, online, 1)
                if prey:
                    self.bite(c, prey)
            return
        if self.run_off(c, SCARED_STRIDE):
            return
        if self.is_night():                                   # closed for the night
            c.cooldown = sec(2) - 1
            return
        prey = self.nearest(c, online, BLOOM_SEES)
        if prey is None:
            c.cooldown = sec(1) - 1
            return
        if cheb(prey, c) <= 1:
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), BLOOM_WINDUP)
            return
        self.shuffle_at(c, prey, BLOOM_STEP)
