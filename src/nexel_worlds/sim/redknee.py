"""The redknee (#366): a tarantula as big as a dog, a night ambusher (design/enemies/roster/redknee.py).

It comes out at dusk by the woods or in a cave (spawning.py) and is gone by dawn: dug in where it stood. It waits,
still, until someone is within RK_SEES tiles, then creeps closer. Within RK_LEAP tiles it rears up, fangs bared (the
warning, RK_WARN: its sheet's four warning frames), aimed at the tile you stand on, then pounces onto it. Still there,
you are bitten and pinned in silk for RK_SILK seconds: no step before that (your `ready`, as a stride's own wait).
Stepped off it, it lands short, on nothing, and settles for RK_REST: your time to hit it.
"""

from .constants import cheb, sec, toward
from .entities import ref

RK_SEES, RK_LEAP = 8, 3                  # tiles: it comes for you from this far; it pounces from this close
RK_WARN, RK_REST, RK_STEP = 0.8, 1.6, 0.45   # seconds: reared up; settling after a pounce; a step as it creeps up
RK_SILK = 1.5                            # seconds pinned in silk


class Redknee:
    """The redknee (stepped by Wild.step_wild)."""

    def _step_redknee(self, c, online):
        if not self.is_night():                               # dawn: it digs itself in
            del self.creatures[c.id]
            self.emit("fade", c.x, c.y, kind=c.kind, id=c.id)
            return
        if c.mode == "windup":                                # reared up: the pounce, onto where you stood
            if self.tick >= c.until:
                self.pounce(c, online)
            return
        if self.run_off(c, RK_STEP):
            return
        prey = self.nearest(c, online, RK_SEES)
        if prey is None:                                      # still, by its cover
            c.cooldown = sec(1) - 1
            return
        if cheb(prey, c) <= RK_LEAP:
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), RK_WARN)
                c.threat = (prey.x, prey.y)
            else:
                c.dir = toward(c, prey)
            return
        self.shuffle_at(c, prey, RK_STEP)

    def pounce(self, c, online):
        """Onto the tile it aimed at, or as far along the way to it as is free; whoever is still on it is bitten and
        pinned."""
        ax, ay = c.threat
        x, y, land = c.x, c.y, (c.x, c.y)
        while (x, y) != (ax, ay):
            x, y = x + (ax > x) - (ax < x), y + (ay > y) - (ay < y)
            if not self.stand(x, y) or (self.entity_at(x, y) not in (None, c) and (x, y) != (ax, ay)):
                break
            if self.entity_at(x, y) in (None, c):
                land = (x, y)
        self.emit("pounce", c.x, c.y, id=c.id, kind=c.kind, to=list(land))
        c.x, c.y = land
        c.mode, c.rest = "", self.tick + sec(RK_REST)
        for a in [a for a in online if (a.x, a.y) == (ax, ay)]:
            self.bite(c, a)
            if a.hp > 0:
                a.ready = max(a.ready, self.tick + sec(RK_SILK))
                self.emit("silk", a.x, a.y, whom=ref(a), name=a.name, seconds=RK_SILK)
