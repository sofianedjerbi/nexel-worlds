"""Wild creatures: the tusker (a boar that charges), the pincer (a shore crab that snaps), the strawman (a scarecrow that
walks), the wisp (a light that leads you on) and the wyrm (a sea serpent that lunges).

Each one warns before it hurts: `mode` goes "windup" for a moment (the client plays the wind-up), then the blow lands
only if you are still there. The tusker's blow is a charge in a straight line: step aside and it runs past, or into
a tree, and stands stunned.
"""

from ..tiles import DIRS
from .constants import sec
from .boss import Boss
from .entities import CREATURES

WILD = ("tusker", "pincer", "strawman", "wisp", "wyrm", "mossback", "sporeling")       # (the last two: boss.py)
TUSKER_SEES, TUSKER_WINDUP, TUSKER_RUN = 4, 0.7, 8        # tiles; seconds pawing the ground; tiles it charges
TUSKER_STUN, TUSKER_REST = 2.5, 3.0                       # seconds stunned after ramming something; between charges
PINCER_SEES, PINCER_WINDUP, PINCER_REST = 3, 0.6, 1.2
STRAW_SEES, STRAW_WINDUP, STRAW_REST, STRAW_STEP = 14, 0.5, 1.5, 0.9
WISP_SEES, WISP_LEAD, WISP_CALL = 9, 4, 6.0               # tiles; it keeps this far ahead of you; seconds between calls
WYRM_SEES, WYRM_REACH, WYRM_WINDUP, WYRM_REST = 7, 2, 0.5, 2.0
LIGHT, LIGHT_R = ("campfire", "fire"), 6


def cheb(a, c) -> int:
    return max(abs(a.x - c.x), abs(a.y - c.y))


def toward(c, a) -> tuple:
    """One step along the longer axis from c to a."""
    dx, dy = a.x - c.x, a.y - c.y
    return ((dx > 0) - (dx < 0), 0) if abs(dx) >= abs(dy) else (0, (dy > 0) - (dy < 0))


class Wild(Boss):
    """Simulation mixin: how the wild enemies behave (and, from Boss, Old Mossback and its sporelings)."""

    def step_wild(self, c, online):
        getattr(self, "_step_" + c.kind)(c, online)

    def nearest(self, c, online, r):
        return min((a for a in online if cheb(a, c) <= r), key=lambda a: (cheb(a, c), a.id), default=None)

    def bite(self, c, prey, dmg=None):
        dmg = dmg or CREATURES[c.kind]["damage"]
        self.emit("attack", c.x, c.y, attacker=f"a {c.kind}", target=prey.name, damage=dmg, id=c.id)
        self.damage(prey, dmg, c.kind)

    def wind_up(self, c, direction, seconds):
        c.mode, c.until, c.dir = "windup", self.tick + sec(seconds), direction
        self.emit("windup", c.x, c.y, id=c.id, kind=c.kind, dir=list(direction))

    def stroll(self, c, slow, spread, ok=lambda x, y: True):
        c.cooldown = sec(slow) + self.rng.randrange(sec(spread))
        d = list(DIRS.values())[self.rng.randrange(4)]
        if ok(c.x + d[0], c.y + d[1]) and self._creature_move(c, c.x + d[0], c.y + d[1]):
            c.dir = d

    # ------------------------------------------------------------- tusker: paws the ground, then charges straight

    def _step_tusker(self, c, online):
        if c.mode == "stun":
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(TUSKER_REST)
            return
        if c.mode == "windup":
            if self.tick >= c.until:
                c.mode, c.left = "charge", TUSKER_RUN
            return
        if c.mode == "charge":                                # a tile every tick: twice a running player's pace
            x, y = c.x + c.dir[0], c.y + c.dir[1]
            hit = next((a for a in online if (a.x, a.y) == (x, y)), None)
            if hit:
                self.bite(c, hit)
                c.mode, c.until = "stun", self.tick + sec(1)
            elif not self._creature_move(c, x, y):            # a tree, a wall, a fence, water: it rams it
                c.mode, c.until = "stun", self.tick + sec(TUSKER_STUN)
                self.emit("bonk", c.x, c.y, id=c.id, kind=c.kind)
            else:
                c.left -= 1
                if c.left <= 0:
                    c.mode, c.rest = "", self.tick + sec(TUSKER_REST)
            return
        prey = self.nearest(c, online, TUSKER_SEES)
        if prey and self.tick >= c.rest:
            self.wind_up(c, toward(c, prey), TUSKER_WINDUP)
        else:
            self.stroll(c, 1.2, 2.0)

    # ------------------------------------------------------------- pincer: guards its bit of shore, sideways

    def _step_pincer(self, c, online):
        if c.mode == "windup":
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(PINCER_REST)
                prey = self.nearest(c, online, 1)
                if prey:
                    self.bite(c, prey)
            return
        prey = self.nearest(c, online, PINCER_SEES)
        if prey and cheb(prey, c) <= 1:
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), PINCER_WINDUP)
        elif prey:                                            # quick sideways, slow forward
            sx = (prey.x > c.x) - (prey.x < c.x)
            sy = (prey.y > c.y) - (prey.y < c.y)
            if sx and self._creature_move(c, c.x + sx, c.y):
                c.cooldown, c.dir = sec(0.25) - 1, (sx, 0)
            elif sy and self._creature_move(c, c.x, c.y + sy):
                c.cooldown, c.dir = sec(0.8), (0, sy)
        else:                                                 # it keeps to the shore
            c.cooldown = sec(1.5) + self.rng.randrange(sec(2.5))
            sx = self.rng.choice((-1, 1))
            if self.shore(c.x + sx, c.y) and self._creature_move(c, c.x + sx, c.y):
                c.dir = (sx, 0)

    def shore(self, x, y) -> bool:
        """Bare earth right beside water."""
        return (self.world.ground(x, y) == "dirt" and self.world.block(x, y) == "none"
                and any(self.world.ground(x + dx, y + dy) in ("water", "deep_water") for dx, dy in DIRS.values()))

    # ------------------------------------------------------------- strawman: a scarecrow by day, walks in the dark

    def _step_strawman(self, c, online):
        if c.mode == "windup":
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(STRAW_REST)
                prey = self.nearest(c, online, 1)
                if prey:
                    self.bite(c, prey)
            return
        c.cooldown = sec(STRAW_STEP) - 1
        if not self.is_night() or self.lit(c.x, c.y):         # daylight or firelight: it is only a scarecrow
            return
        prey = self.nearest(c, online, STRAW_SEES)
        if prey is None:
            return
        if cheb(prey, c) <= 1:
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), STRAW_WINDUP)
            return
        d = toward(c, prey)
        other = (0, (prey.y > c.y) - (prey.y < c.y)) if d[0] else ((prey.x > c.x) - (prey.x < c.x), 0)
        for step in (d, other):
            if step != (0, 0) and self._creature_move(c, c.x + step[0], c.y + step[1]):
                c.dir = step
                break

    # ------------------------------------------------------------- wisp: a light that keeps just ahead of you

    def _step_wisp(self, c, online):
        if c.mode == "windup":                                # calling: it flares (the client plays it), nothing more
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(WISP_CALL)
            return
        prey = self.nearest(c, online, WISP_SEES) if self.is_night() else None
        if prey is None:                                      # by day, or alone: it drifts about
            c.cooldown = sec(1.0) + self.rng.randrange(sec(1.5))
            d = list(DIRS.values())[self.rng.randrange(4)]
            self.float_to(c, c.x + d[0], c.y + d[1])
        elif cheb(prey, c) < WISP_LEAD:                       # you are coming: it slips away, the way you were heading
            c.cooldown = sec(0.3) - 1
            back = toward(c, prey)
            self.float_to(c, c.x - back[0], c.y - back[1])
        elif self.tick >= c.rest:                             # you hang back: it calls
            self.wind_up(c, toward(c, prey), 0.5)

    def float_to(self, c, x, y) -> bool:
        """It flies: over water, fences and walls alike. Only another body stops it."""
        if self.entity_at(x, y) is not None:
            return False
        c.dir, c.x, c.y = (x - c.x, y - c.y), x, y
        return True

    # ------------------------------------------------------------- wyrm: deep water only; lunges along its line

    def _step_wyrm(self, c, online):
        if c.mode == "windup":
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(WYRM_REST)
                reach = [(c.x + c.dir[0] * k, c.y + c.dir[1] * k) for k in range(1, WYRM_REACH + 1)]
                prey = next((a for a in online if (a.x, a.y) in reach), None)
                if prey:
                    self.bite(c, prey)
            return
        prey = self.nearest(c, online, WYRM_SEES)
        if prey is None:
            c.cooldown = sec(0.6) + self.rng.randrange(sec(1.0))
            d = list(DIRS.values())[self.rng.randrange(4)]
            self.swim_to(c, c.x + d[0], c.y + d[1])
            return
        dx, dy = prey.x - c.x, prey.y - c.y
        if (dx == 0 or dy == 0) and cheb(prey, c) <= WYRM_REACH:        # you are on its line, in reach: it rears back
            if self.tick >= c.rest:
                self.wind_up(c, toward(c, prey), WYRM_WINDUP)
            return
        c.cooldown = sec(0.4) - 1
        d = toward(c, prey)
        other = (0, (dy > 0) - (dy < 0)) if d[0] else ((dx > 0) - (dx < 0), 0)
        for step in (d, other):
            if step != (0, 0) and self.swim_to(c, c.x + step[0], c.y + step[1]):
                break

    def swim_to(self, c, x, y) -> bool:
        """It never comes into the shallows: the shore is safe."""
        if self.world.ground(x, y) != "deep_water" or self.world.block(x, y) != "none" or self.entity_at(x, y) is not None:
            return False
        c.dir, c.x, c.y = (x - c.x, y - c.y), x, y
        return True

    def lit(self, x, y) -> bool:
        return any(self.world.block(x + dx, y + dy) in LIGHT
                   for dx in range(-LIGHT_R, LIGHT_R + 1) for dy in range(-LIGHT_R, LIGHT_R + 1))
