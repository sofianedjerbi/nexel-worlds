"""The ways up: ladders and stairs.

A ladder stands on a tile (on the ground, or on a floor somebody built) against something taller beside it: a wall
with a floor on it, a terrace, a roof, a cliff. Walk into that taller thing from the ladder and you climb: you come
out on the lowest place up there you can stand on, if the ladder's own tile is open all the way (a floor over the
ladder needs a hole in it, a hatch). Walk off the top onto the ladder and you climb down: no fall, however high.
Only people climb; animals don't. Placed while you face a wall two layers or more higher than you (a pit's side,
a cliff's foot), it goes on your own tile, against that wall (ladder_spot); else on the tile you aim at.

Stairs are a flight of steps, laid with one press: put them on a tile beside a higher place (a floor's edge, a
terrace, a ledge, 2 to 7 layers up) and they go down from it towards you, a step a tile and a layer lower each,
until the last one is a step up from the ground. Each step is a column of built blocks (floors.py, kind `stairs`)
standing on the ground there; walking up them is a hop a step, as up any ledge. A step costs one `stairs`; taking a
step back gives it back, the whole column."""

from ..tiles import BLOCKS, DIRS, GROUNDS, B
from .entities import ActionError

LADDER, STAIRS = "ladder", "stairs"
CLIMB = 12                       # how far up a ladder goes, in layers
RISE = (2, 7)                    # how much higher than its foot a flight of stairs can lead: less is a hop, more too long


class Climbing:
    """Simulation mixin: ladders and stairs."""

    def open_at(self, x, y, z) -> bool:
        """Someone could stand at height z on (x, y): ground or a block there, room for a body over it, nothing in
        the way on it."""
        w = self.world
        if z not in w.surfaces(x, y) or w.solid(x, y, z + 2):
            return False
        cell = self.floors.get(x, y, z)
        if cell is not None:
            return not BLOCKS[B[cell[1]]].solid
        if z != w.level(x, y):
            return True
        g, b = w.get(x, y)
        return GROUNDS[g].walkable and not BLOCKS[b].solid

    def climb_to(self, h, x0, y0, x, y) -> int | None:
        """From a ladder at height h on (x0, y0), climbing into the tile (x, y): the height you come out at, or None.
        The lowest place up there you can stand on, the ladder's tile open all the way to it."""
        for s in self.world.surfaces(x, y):
            if s <= h or s > h + CLIMB:
                continue
            if any(self.world.solid(x0, y0, c) for c in range(h + 1, s + 3)):
                return None                               # (the way up is shut: nothing higher either)
            if self.open_at(x, y, s):
                return s
        return None

    def leans(self, x, y, z) -> bool:
        """A ladder at height z on (x, y) has something to climb onto: two layers up or more."""
        return any((s := self.climb_to(z, x, y, x + dx, y + dy)) is not None and s >= z + 2 for dx, dy in DIRS.values())

    def ladder_spot(self, a, x, y) -> bool:
        """A ladder in hand, a wall in front of you two layers or more higher than where you stand (and no more than
        a ladder goes): the ladder goes on YOUR OWN tile, against that wall, whichever of the four ways it is. (It
        went on the tile you faced only: at the bottom of your own one-tile shaft every way is a wall, and you were
        shut in with a ladder in your hand.)"""
        h = self.height(a)
        if abs(x - a.x) + abs(y - a.y) != 1 or not self.world.solid(x, y, h + 1):
            return False
        s = self.climb_to(h, a.x, a.y, x, y)
        return s is not None and s >= h + 2

    def stand_ladder(self, a):
        """The ladder put where you stand (ladder_spot): on the ground of your tile, or on the built block under you."""
        x, y, h = a.x, a.y, self.height(a)
        if self.floors.get(x, y, h) is not None:
            return (yield from self.put_on(a, x, y, h, LADDER))
        if not a.count(LADDER):
            raise ActionError("missing_item", "you have no ladder")
        for again in (False, True):
            if h != self.world.level(x, y) or GROUNDS[self.world.get(x, y)[0]].liquid:
                raise ActionError("bad_target", "a ladder's foot needs the tile's own ground")
            if self.world.block(x, y) not in ("none", "flower"):
                raise ActionError("occupied", f"there is a {self.world.block(x, y).replace('_', ' ')} where you stand")
            if (a.x, a.y, self.height(a)) != (x, y, h) or not self.leans(x, y, h):
                raise ActionError("changed", "something changed there")
            if not again:
                yield from self.wait(a, 0.3)
        if self.world.block(x, y) == "flower":
            a.add("flower")
        a.add(LADDER, -1)
        self.set_tile(x, y, block=LADDER, by=a, cause="place")
        a.bump("placed")
        return {"at": [x, y], "z": h}

    def on_ladder(self, x0, y0, h0, x, y, h) -> bool:
        """A step from (x0, y0, h0) to (x, y, h) taken on a ladder (climbing or coming down it): no fall."""
        return self.thing(x0, y0, h0) == LADDER or self.thing(x, y, h) == LADDER

    # ============================================================== stairs

    def flight(self, a, x, y) -> list:
        """The steps of a flight of stairs put at (x, y): [(x, y, ground, top)], the one at (x, y) first. Up to the
        higher place beside it (looked for north, east, south, west), straight out from it, or along it where
        that way is shut (someone stands there: whoever lays them, as often as not)."""
        base, why = self.surface(a, x, y), None
        for dx, dy in DIRS.values():
            for top in self.world.surfaces(x + dx, y + dy):
                if base + RISE[0] <= top <= base + RISE[1] and self.open_at(x + dx, y + dy, top):
                    for way in ((-dx, -dy), (dy, dx), (-dy, -dx)):     # straight out from it; else along it, one way or the other
                        steps = self._steps(x, y, *way, top)
                        if isinstance(steps, list):
                            return steps
                        why = why or steps
                    break
        raise ActionError("bad_target", why or "stairs lead up to something beside them: a floor, a terrace, a ledge, 2 to 7 layers up")

    def _steps(self, x, y, dx, dy, top):
        """Down from `top`, a step a tile in (dx, dy): the steps, or why they can't be."""
        out, t = [], top - 1
        while True:
            under = [s for s in self.world.surfaces(x, y) if s < t]
            g = max(under, default=None)
            if g is None or t <= g:
                return out or "the ground there is as high"
            if any(self.world.solid(x, y, c) for c in range(g + 1, t + 3)):
                return "no room for the stairs there (leave the floor open over them)"
            cell = self.floors.get(x, y, g)
            what = cell[1] if cell is not None else self.world.block(x, y) if g == self.world.level(x, y) else "none"
            if what not in ("none", "flower") or (cell is None and not GROUNDS[self.world.get(x, y)[0]].walkable):
                return f"the {what.replace('_', ' ')} is in the way" if what not in ("none", "flower") else "stairs need ground under them"
            if self.bodies_on(x, y):
                return "someone is standing where the stairs go"
            out.append((x, y, g, t))
            if t - g <= 1:
                return out
            if len(out) >= RISE[1]:
                return "too far down"
            t, x, y = t - 1, x + dx, y + dy

    def lay_stairs(self, a, x, y):
        steps = self.flight(a, x, y)
        if a.count(STAIRS) < len(steps):
            raise ActionError("missing_item", f"the flight takes {len(steps)} stairs: you have {a.count(STAIRS)}")
        if any(self.bodies_on(sx, sy) for sx, sy, _, _ in steps):
            raise ActionError("occupied", "someone is standing where the stairs go")
        yield from self.wait(a, 0.3 * len(steps))
        if self.flight(a, x, y) != steps or a.count(STAIRS) < len(steps):
            raise ActionError("changed", "something changed there")
        for sx, sy, g, t in steps:
            if self.floors.get(sx, sy, g) is None and self.world.block(sx, sy) == "flower" and g == self.world.level(sx, sy):
                a.add("flower")
                self.world.set(sx, sy, block="none")
            for z in range(g + 1, t + 1):
                self.set_block(sx, sy, z, STAIRS, by=a)
        a.add(STAIRS, -len(steps))
        a.bump("placed")
        return {"steps": [[sx, sy, t] for sx, sy, _, t in steps]}

    def take_stairs(self, a, x, y, z):
        """A step taken back: its whole column, from the top down. -> what you got."""
        top = z
        while self.floors.get(x, y, top + 1) and self.floors.get(x, y, top + 1)[0] == STAIRS:
            top += 1
        if self.world.solid(x, y, top + 1):
            raise ActionError("bad_target", "take the block on top of it first")
        yield from self.wait(a, 0.3)
        while (cell := self.floors.get(x, y, top)) is not None and cell[0] == STAIRS:
            self.set_block(x, y, top, None, by=a, cause="dig")
            top -= 1
        a.add(STAIRS)
        a.bump("dug")
        return {"got": {STAIRS: 1}}
