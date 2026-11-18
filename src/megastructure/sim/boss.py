"""Old Mossback, the first boss, and its sporelings.

A tortoise with a garden on its shell. Asleep it is a hill with a tree on it; hit it and it stands up. It is three
tiles wide (Simulation.entity_at knows), slow, and its shell turns most of a blow. Three attacks, each a `mode` that
lasts as long as its warning, then lands:
  stomp   it rises, then drops: everyone near is hurt and thrown back a tile
  snap    the head shoots out along the way it faces; for a moment after, the neck is out and blows land in full
  shake   three sporelings fall off its back
It goes back to sleep, healed, when nobody has been near for a while. Nothing here spawns by itself.
"""

from .constants import sec
from .entities import CREATURES, Creature

ATTACKS = {"stomp": 0.7, "snap": 0.6, "shake": 0.95}      # seconds of warning: where the strike sits in each animation
MOSS_SEES, MOSS_AWAKE, MOSS_REST, MOSS_STEP = 10, 20.0, 2.2, 1.1     # tiles; seconds awake with nobody near; between attacks; a step
STOMP_X, STOMP_Y, SNAP_REACH = 2, 2, 3                    # tiles from its body the stomp reaches; tiles past its head the snap does
EXPOSED, SHELL = 1.6, 4                                   # seconds the neck stays out; a blow on the shell is divided by this
BROOD, BROOD_R = 6, 10                                    # sporelings it will have around at once
SPORE_SEES, SPORE_STEP, SPORE_PUFF, SPORE_REST, SPORE_LIFE = 8, 0.45, 0.3, 3.0, 20.0


def sign(v) -> int:
    return (v > 0) - (v < 0)


class Boss:
    """Simulation mixin: Old Mossback and its sporelings (dispatched from Wild.step_wild)."""

    def shell(self, c, dmg: int) -> int:
        """What a blow of `dmg` does to creature c: Old Mossback's shell turns most of it, unless its neck is out."""
        if c.kind != "mossback" or self.tick < c.left:
            return dmg
        return max(1, dmg // SHELL)

    def _moss_gap(self, c, a) -> tuple:
        """How far a is from its body (three tiles wide), across and along."""
        return max(0, abs(a.x - c.x) - 1), abs(a.y - c.y)

    def _step_mossback(self, c, online):
        full = CREATURES["mossback"]["hp"]
        if c.mode in ATTACKS:
            if self.tick >= c.until:
                getattr(self, "_moss_" + c.mode)(c, online)
                c.mode, c.rest = "", self.tick + sec(MOSS_REST * (0.5 if c.hp * 2 < full else 1))   # hurt, it does not wait
            return
        if self.tick >= c.awake:                              # asleep: a hill with a tree on it
            if c.mode == "sleep" and c.hp < full:             # someone hit it
                c.mode, c.awake, c.rest = "", self.tick + sec(MOSS_AWAKE), self.tick + sec(1.5)
                self.emit("boss", c.x, c.y, what="wake", id=c.id)
            elif c.mode != "sleep":
                c.mode, c.hp = "sleep", full
                self.emit("boss", c.x, c.y, what="sleep", id=c.id)
            return
        near = [a for a in online if max(self._moss_gap(c, a)) <= MOSS_SEES and self.level(c, a)]      # (and near its own height: wild.py)
        if not near:
            return
        prey = min(near, key=lambda a: (sum(self._moss_gap(c, a)), a.id))
        c.awake = self.tick + sec(MOSS_AWAKE)
        gx, gy = self._moss_gap(c, prey)
        dx, dy = prey.x - c.x, prey.y - c.y
        ahead = (sign(dx), 0) if abs(dx) >= abs(dy) else (0, sign(dy))
        if self.tick >= c.rest:
            brood = sum(1 for o in self.creatures.values() if o.kind == "sporeling" and max(abs(o.x - c.x), abs(o.y - c.y)) <= BROOD_R)
            in_line = (dy == 0 and 1 <= gx <= SNAP_REACH) or (dx == 0 and 1 <= gy <= SNAP_REACH)
            close = gx <= STOMP_X and gy <= STOMP_Y
            move = "snap" if in_line else "shake" if brood < 3 and (not close or self.rng.random() < 0.3) else "stomp" if close else None
            if move:
                c.mode, c.until, c.dir = move, self.tick + sec(ATTACKS[move]), ahead
                self.emit("windup", c.x, c.y, id=c.id, kind=c.kind, dir=list(ahead), move=move)
                return
        c.cooldown = sec(MOSS_STEP) - 1                       # it comes on, a tile at a time
        if gx + gy > 1:
            for step in (ahead, (0, sign(dy)) if ahead[0] else (sign(dx), 0)):
                if step != (0, 0) and self._moss_move(c, c.x + step[0], c.y + step[1]):
                    c.dir = step
                    break

    def _moss_move(self, c, x, y) -> bool:
        """All three tiles of it must fit."""
        for i in (-1, 0, 1):
            if not self.world.passable(x + i, y) or self.world.block(x + i, y) in ("door", "gate") or self.entity_at(x + i, y) not in (None, c):
                return False
        if not self.world.can_step(c.x, c.y, x, y):
            return False
        c.x, c.y = x, y
        return True

    def _moss_stomp(self, c, online):
        self.emit("boss", c.x, c.y, what="stomp", id=c.id)
        for a in online:
            gx, gy = self._moss_gap(c, a)
            if gx > STOMP_X or gy > STOMP_Y:
                continue
            deaths = a.deaths
            self.bite(c, a)
            x, y = a.x + sign(a.x - c.x), a.y + (sign(a.y - c.y) or (0 if a.x != c.x else 1))
            if a.deaths == deaths and self.can_go(a, x, y) and self.entity_at(x, y) is None:      # thrown back a tile
                a.z = self.landing(a, x, y)
                a.x, a.y = x, y

    def _moss_snap(self, c, online):
        self.emit("boss", c.x, c.y, what="snap", id=c.id)
        c.left = self.tick + sec(EXPOSED)                     # the neck is out: its soft spot
        sx, sy = c.dir
        reach = [(c.x + sx * (1 + k), c.y) if sx else (c.x, c.y + sy * k) for k in range(1, SNAP_REACH + 1)]
        for a in online:
            if (a.x, a.y) in reach:
                self.bite(c, a, CREATURES["mossback"]["snap"])

    def _moss_shake(self, c, online):
        self.emit("boss", c.x, c.y, what="shake", id=c.id)
        brood = sum(1 for o in self.creatures.values() if o.kind == "sporeling" and max(abs(o.x - c.x), abs(o.y - c.y)) <= BROOD_R)
        for x, y in ((c.x - 2, c.y), (c.x + 2, c.y), (c.x, c.y + 1)):      # where they fall in its animation
            if brood >= BROOD or not self.world.passable(x, y) or self.entity_at(x, y) is not None:
                continue
            s = Creature(self.next_creature, "sporeling", x, y, CREATURES["sporeling"]["hp"], born=self.tick,
                         mode="land", until=self.tick + sec(0.7))
            self.next_creature += 1
            self.creatures[s.id] = s
            brood += 1

    # ------------------------------------------------------------- sporeling: lands, waddles at you, puffs

    def _step_sporeling(self, c, online):
        if c.mode == "land":
            if self.tick >= c.until:
                c.mode = ""
                self.emit("boss", c.x, c.y, what="land", id=c.id)
            return
        if c.mode == "puff":
            if self.tick >= c.until:
                c.mode, c.rest = "", self.tick + sec(SPORE_REST)
                self.emit("boss", c.x, c.y, what="puff", id=c.id)
                for a in online:
                    if max(abs(a.x - c.x), abs(a.y - c.y)) <= 1:
                        self.bite(c, a)
            return
        if c.born and self.tick - c.born >= sec(SPORE_LIFE):  # its time is up: it roots where it stands, a mushroom to pick
            del self.creatures[c.id]
            if self.world.block(c.x, c.y) == "none" and self.world.ground(c.x, c.y) in ("grass", "dirt"):
                self.set_tile(c.x, c.y, block="mushroom")
            self.emit("fade", c.x, c.y, kind=c.kind, id=c.id)
            return
        prey = self.nearest(c, online, SPORE_SEES)
        if prey is None:
            self.stroll(c, 0.8, 1.2)
        elif max(abs(prey.x - c.x), abs(prey.y - c.y)) <= 1:
            if self.tick >= c.rest:
                c.mode, c.until = "puff", self.tick + sec(SPORE_PUFF)
                self.emit("windup", c.x, c.y, id=c.id, kind=c.kind, dir=list(c.dir), move="puff")
        else:
            c.cooldown = sec(SPORE_STEP) - 1
            dx, dy = prey.x - c.x, prey.y - c.y
            first = (sign(dx), 0) if abs(dx) >= abs(dy) else (0, sign(dy))
            for step in (first, (0, sign(dy)) if first[0] else (sign(dx), 0)):
                if step != (0, 0) and self._creature_move(c, c.x + step[0], c.y + step[1]):
                    c.dir = step
                    break
