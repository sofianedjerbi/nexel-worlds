"""The gustling: a little whirlwind that got a mind of its own. Rare, by day, on open grass (spawning.py).

It goes only for someone with something in their hand (a player's selected slot, `held`). Beside them it draws up and
spins (GUST_WINDUP, the warning: the client plays its snatch from here), then takes up to GUST_TAKE of what is still in
that hand and runs for GUST_FLEE seconds. Hit while it spins, it scatters at once; hit otherwise, it runs. Whatever it
carries falls where it dies (combat.py: `loot`). It never hurts anyone.
"""

from .constants import cheb, sec, toward

GUST_SEES, GUST_WINDUP, GUST_REST, GUST_FLEE, GUST_TAKE = 6, 0.6, 3.0, 6.0, 5
GUST_DRIFT, GUST_RUN = 0.4, 0.25                          # seconds a tile: about your walk; faster than it, running off


class Gust:
    """How the gustling behaves: Wild builds on it as on Boss, and steps it like the other wild ones."""

    def _gust_prey(self, c, online):
        """The nearest it sees with something in their hand."""
        return min((a for a in online if a.held and a.count(a.held) and cheb(a, c) <= GUST_SEES and self.level(c, a)),
                   key=lambda a: (cheb(a, c), a.id), default=None)

    def _step_gustling(self, c, online):
        if c.mode == "windup":                                # spun up: the snatch, if they are still beside it
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(GUST_REST)
                prey = next((a for a in online if cheb(a, c) <= 1 and a.held and a.count(a.held) and self.level(c, a)), None)
                if prey:
                    item = prey.held
                    n = min(prey.count(item), GUST_TAKE)
                    prey.add(item, -n)
                    c.loot[item] = c.loot.get(item, 0) + n
                    self.emit("snatch", c.x, c.y, id=c.id, kind=c.kind, target=prey.name, item=item, n=n)
                    self.flee_from(c, prey, GUST_FLEE)
            return
        if self.run_off(c, GUST_RUN):                         # off with it, away from whoever it fled
            return
        prey = self._gust_prey(c, online)
        if prey is None:                                      # nobody with anything to take: it wanders, restless
            self.stroll(c, 0.5, 1.0)
            return
        if cheb(prey, c) <= 1:
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), GUST_WINDUP)
            return
        c.cooldown = sec(GUST_DRIFT) - 1
        d = toward(c, prey)
        other = (0, (prey.y > c.y) - (prey.y < c.y)) if d[0] else ((prey.x > c.x) - (prey.x < c.x), 0)
        for step in (d, other):
            if step != (0, 0) and self._creature_move(c, c.x + step[0], c.y + step[1]):
                c.dir = step
                break

    def gust_struck(self, c, a, dmg):
        """A blow on a gustling: while it spins up it scatters at once (the blow is all of it); otherwise it runs."""
        if c.mode == "windup":
            self.emit("scatter", c.x, c.y, id=c.id, kind=c.kind)
            return c.hp
        self.flee_from(c, a, GUST_FLEE)
        return dmg
