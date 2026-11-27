"""The skeleton (#366): a night walker with an ember in each eye (design/enemies/roster/skeleton.py).

It comes out at dusk on open ground (spawning.py) and is gone by dawn. It walks straight up to whoever is nearest; beside
them it gives its tell (SK_WARN: its jaw drops, it rises a px, its skull rattles, arms out: its sheet's four warning
frames), then swipes, and only who is still beside it is hit. Step back while it rattles, then hit it: three hits of a
spear (its hp: entities.py).
"""

from .constants import cheb, sec, toward

SK_SEES, SK_WARN, SK_REST, SK_STEP = 8, 0.6, 1.4, 0.6   # tiles it comes from; seconds rattling; between swipes; a step


class Skeleton:
    """The skeleton (stepped by Wild.step_wild)."""

    def _step_skeleton(self, c, online):
        if not self.is_night():                               # dawn: it is gone
            del self.creatures[c.id]
            self.emit("fade", c.x, c.y, kind=c.kind, id=c.id)
            return
        if c.mode == "windup":                                # rattling: then the swipe, on who is still beside it
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(SK_REST)
                prey = self.nearest(c, online, 1)
                if prey:
                    self.bite(c, prey)
            return
        if self.run_off(c, SK_STEP):
            return
        prey = self.nearest(c, online, SK_SEES)
        if prey is None:
            self.stroll(c, 2.0, 2.0)
            return
        if cheb(prey, c) <= 1:
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), SK_WARN)
            return
        self.shuffle_at(c, prey, SK_STEP)
