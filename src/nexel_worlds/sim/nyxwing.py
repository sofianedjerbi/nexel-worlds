"""Nyxwing, the boss of "Sugar rush": a dragon made of the night sky (design/enemies/roster/nyxwing.py).

It never lands. Three tiles wide, like Old Mossback (Simulation.entity_at knows), it flies over anything at a tile
every FLY seconds, circling whoever it hunts between attacks. Everything is counted in beats of its song (156 BPM), so
that what the client plays lands with the music: a warning is a beat and a half, every strike falls on a beat.
  arrive  its entrance: it comes down out of the night sky and lands on the music's drop, 32 beats on; nothing touches it
  breath  dark light at its jaws, then a cone of dark fire four tiles long, the way it faces
  storm   it climbs and spins: a ring of stars on each of three beats; a star a tile wide, the gaps between them safe
  sweep   its tail coils, then whips round: everyone within four tiles is hurt and thrown back
  dive    it shoots up out of sight ("sky": nothing touches it), its shadow hunts you, locks a beat before, and it
          crashes down on the beat: hard under it, less out to four tiles
  rush    once, below half health: it roars, and from then on rests half as long between attacks
It leaves, healed of nothing, when nobody has been near it for LEAVES seconds. Nothing here makes one appear: /summon
does (admin_cmds.py), and nothing calls it down by itself yet.
"""

import math

from .constants import sec
from .entities import CREATURES

BEAT = 60 / 156
ARRIVE = 32 * BEAT                 # its entrance, to the drop of its song (web/js/boss.js plays it)
WARN = 1.5 * BEAT                  # every warning
REST, RAGE_REST = 4 * BEAT, 2 * BEAT       # from the end of one attack to the next warning (below half: twice as often)
FLY, RAGE_FLY = 0.14, 0.1          # seconds a tile
SEES, LEAVES = 16, 30.0            # tiles; seconds alone before it goes
ORBIT_X, ORBIT_Y = 6, 3            # tiles: the ellipse it circles on, round whoever it hunts
CONE, SWEEP_R, CRASH_R = 4, 4, 4   # tiles: the breath's length, the sweep's reach, the crash's
RINGS, STARS, STAR_W, RING_R = 3, 18, 0.6, 8     # rings, stars a ring, how near a star's line hits (tiles), how far a ring goes
SKY, LOCK = 4.5 * BEAT, 1.0 * BEAT                # in the sky after the warning; the shadow stops this long before the crash


def sign(v) -> int:
    return (v > 0) - (v < 0)


class Nyxwing:
    """Simulation mixin: Nyxwing (dispatched from Wild.step_wild). Of its fields, `left` counts the rings of a storm,
    `awake` is 1 once it has raged (rush), `born` the tick it last saw someone."""

    def untouchable(self, c) -> bool:
        """Coming down out of the night, or up in the sky: no blow reaches it (combat.py, through Boss.shell)."""
        return c.kind == "nyxwing" and c.mode in ("arrive", "sky")

    def _step_nyxwing(self, c, online):
        t, raged = self.tick, c.awake == 1
        if c.mode == "" and c.until == 0:                    # it has just come: its entrance
            c.mode, c.until, c.born = "arrive", t + sec(ARRIVE), t
            self.emit("boss", c.x, c.y, what="arrive", id=c.id, kind=c.kind)
            return
        if c.mode == "arrive":
            if t >= c.until:
                c.mode, c.rest = "", t + sec(2 * BEAT)
                self.emit("boss", c.x, c.y, what="land", id=c.id, kind=c.kind)
            return
        if c.mode == "sky":
            return self._nyx_sky(c, online)
        if c.mode:                                             # a warning, or a storm between its rings
            if t >= c.until:
                getattr(self, "_nyx_" + c.mode)(c, online)
            return
        near = [a for a in online if max(abs(a.x - c.x), abs(a.y - c.y)) <= SEES and self.level(c, a)]
        if not near:
            if t - c.born >= sec(LEAVES):                       # nobody comes: it goes back to the night
                del self.creatures[c.id]
                self.emit("boss", c.x, c.y, what="leave", id=c.id, kind=c.kind)
            return
        c.born = t
        prey = min(near, key=lambda a: (max(abs(a.x - c.x), abs(a.y - c.y)), a.id))
        dx, dy = prey.x - c.x, prey.y - c.y
        ahead = (sign(dx), 0) if abs(dx) >= abs(dy) else (0, sign(dy))
        if t >= c.rest:
            d = max(abs(dx), abs(dy))
            if not raged and c.hp * 2 < CREATURES["nyxwing"]["hp"]:
                move = "rush"
            elif d < SWEEP_R:
                move = "sweep"
            elif d > ORBIT_X:
                move = "dive"
            else:
                move = "breath" if min(abs(dx), abs(dy)) <= 1 and self.rng.random() < 0.7 else "storm"
            c.mode, c.until, c.dir, c.left = move, t + sec(WARN), ahead, 0
            self.emit("windup", c.x, c.y, id=c.id, kind=c.kind, dir=list(ahead), move=move)
            return
        self._nyx_circle(c, prey, raged)

    def _nyx_circle(self, c, prey, raged):
        """Between attacks: round whoever it hunts, on an ellipse, a tile at a time (diagonals too: it flies)."""
        spin = 1 if c.id % 2 else -1
        a = math.atan2((c.y - prey.y) / ORBIT_Y, (c.x - prey.x) / ORBIT_X) + spin * 0.6
        tx, ty = prey.x + round(ORBIT_X * math.cos(a)), prey.y + round(ORBIT_Y * math.sin(a))
        c.cooldown = sec(RAGE_FLY if raged else FLY) - 1
        step = (sign(tx - c.x), sign(ty - c.y))
        for s in (step, (step[0], 0), (0, step[1])):
            if s != (0, 0) and self._nyx_fly(c, c.x + s[0], c.y + s[1]):
                c.dir = (s[0], 0) if s[0] else (0, s[1])
                break

    def _nyx_fly(self, c, x, y) -> bool:
        """Over anything: only nobody may be under it (all three tiles of it)."""
        for i in (-1, 0, 1):
            if self.entity_at(x + i, y) not in (None, c):
                return False
        c.x, c.y, c.z = x, y, self.world.surfaces(x, y)[-1]    # (over the highest ground there)
        return True

    def _nyx_done(self, c):
        c.mode, c.rest = "", self.tick + sec(RAGE_REST if c.awake == 1 else REST)

    def _nyx_breath(self, c, online):
        self.emit("boss", c.x, c.y, what="breath", id=c.id, dir=list(c.dir))
        fx, fy = c.dir
        for a in online:
            along, across = (a.x - c.x) * fx + (a.y - c.y) * fy, abs((a.x - c.x) * fy + (a.y - c.y) * fx)
            if 1 <= along <= CONE and across <= 1 + along // 2:
                self.bite(c, a)
        self._nyx_done(c)

    def _nyx_storm(self, c, online):
        k = c.left
        self.emit("boss", c.x, c.y, what="ring", id=c.id, ring=k)
        for a in online:                                       # a star's line passing within STAR_W of you hits you
            dx, dy = a.x - c.x, a.y - c.y
            d = math.hypot(dx, dy)
            if 1 <= d <= RING_R:
                gap = (math.atan2(dy, dx) - k * math.pi / STARS) % (2 * math.pi / STARS)
                if min(gap, 2 * math.pi / STARS - gap) * d <= STAR_W:
                    self.bite(c, a, CREATURES["nyxwing"]["star"])
        c.left = k + 1
        if c.left < RINGS:
            c.until = self.tick + sec(BEAT)
        else:
            self._nyx_done(c)

    def _nyx_sweep(self, c, online):
        self.emit("boss", c.x, c.y, what="sweep", id=c.id)
        for a in online:
            if max(abs(a.x - c.x), abs(a.y - c.y)) <= SWEEP_R:
                deaths = a.deaths
                self.bite(c, a, CREATURES["nyxwing"]["sweep"])
                x, y = a.x + sign(a.x - c.x), a.y + sign(a.y - c.y)
                if a.deaths == deaths and (x, y) != (a.x, a.y) and self.can_go(a, x, y) and self.entity_at(x, y) is None:
                    a.z = self.landing(a, x, y)                # thrown back a tile
                    a.x, a.y = x, y
        self._nyx_done(c)

    def _nyx_rush(self, c, online):
        self.emit("boss", c.x, c.y, what="roar", id=c.id)
        c.awake = 1
        self._nyx_done(c)

    def _nyx_dive(self, c, online):
        """The warning is over: up out of sight."""
        c.mode, c.until = "sky", self.tick + sec(SKY)
        self.emit("boss", c.x, c.y, what="up", id=c.id)

    def _nyx_sky(self, c, online):
        """Its shadow hunts the nearest one until a beat before, then it falls where the shadow is."""
        if self.tick >= c.until:
            return self._nyx_crash(c, online)
        if self.tick >= c.until - sec(LOCK):
            return
        prey = min(online, key=lambda a: (max(abs(a.x - c.x), abs(a.y - c.y)), a.id), default=None)
        if prey is None or (prey.x, prey.y) == (c.x, c.y):
            return
        c.cooldown = sec(FLY * 1.2) - 1
        self._nyx_fly(c, c.x + sign(prey.x - c.x), c.y + sign(prey.y - c.y))

    def _nyx_crash(self, c, online):
        self.emit("boss", c.x, c.y, what="crash", id=c.id)
        for a in online:
            d = max(abs(a.x - c.x) - 1, abs(a.y - c.y), 0)         # (from its body, three tiles wide)
            if d <= CRASH_R:
                self.bite(c, a, CREATURES["nyxwing"]["crash" if d <= 1 else "blast"])
        self._nyx_done(c)
