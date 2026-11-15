"""Roofs, laid a tile at a time. A house was walls, and its roof came by itself the moment they closed. Now a roof is
built as the rest is: a piece (`roof`, from wood) placed on a wall or beside a roof tile, and taken back the same way.
It shelters whoever is under it."""

from ..roofs import Roofs
from ..tiles import B, DIRS
from .entities import ActionError

WALLS = ("wood_wall", "stone_wall", "door")       # what a roof rests on
ROOF_SPAN = 3                                    # tiles from a wall, at most: further, it would hang in the air


class Roofing:
    """Simulation mixin: laying roof tiles, taking them back, and the roofs of the houses built before there were any."""

    def open_roofs(self, store):
        self.roofed = Roofs(store)
        if not store.get_meta("roofs"):                # once: a world from before roofs were laid by hand
            for x, y in self.old_rooms(store):
                self.roofed.set(x, y, True)
            store.set_meta("roofs", 1)

    def old_rooms(self, store) -> set:
        """Every tile the old, automatic roofs covered: over each closed, compact room with a wooden wall (the rule
        the screen drew them by), the box of the room and its walls."""
        wall, seeds = B["wood_wall"], []
        for cx, cy in list(store.db.execute("SELECT cx, cy FROM chunks")):
            c = store.load_chunk(cx, cy)
            seeds += [(cx * 32 + i % 32, cy * 32 + i // 32) for i, b in enumerate(c.block) if b == wall]
        seen, out = set(), set()
        for wx, wy in seeds:
            for dx, dy in DIRS.values():
                start = (wx + dx, wy + dy)
                if start in seen or self.world.block(*start) in self.ENCLOSE:
                    continue
                cells, stack, shut, wood = {start}, [start], True, False
                while stack and shut:
                    cx, cy = stack.pop()
                    for ex, ey in DIRS.values():
                        n = (cx + ex, cy + ey)
                        b = self.world.block(*n)
                        if b in self.ENCLOSE:
                            wood = wood or b == "wood_wall"
                        elif n not in cells:
                            cells.add(n)
                            stack.append(n)
                            shut = len(cells) <= 160
                seen |= cells
                xs, ys = [p[0] for p in cells], [p[1] for p in cells]
                w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
                if shut and wood and w <= 14 and h <= 14 and len(cells) >= .6 * w * h:
                    out |= {(i, j) for i in range(min(xs) - 1, max(xs) + 2) for j in range(min(ys) - 1, max(ys) + 2)}
        return out

    def roof_rests(self, x, y) -> bool:
        """A roof tile here would rest on something: on a wall, or beside a wall or a roof tile; and no further than
        ROOF_SPAN tiles from a wall."""
        held = self.world.block(x, y) in WALLS or any(
            (x + dx, y + dy) in self.roofed or self.world.block(x + dx, y + dy) in WALLS for dx, dy in DIRS.values())
        r = ROOF_SPAN
        return held and any(self.world.block(x + i, y + j) in WALLS for j in range(-r, r + 1) for i in range(-r, r + 1))

    def set_roof(self, x, y, on: bool, by=None):
        self.roofed.set(x, y, on)
        self.stats["tiles_changed"] += 1
        self.emit("roof", x, y, on=on, by=by.name if by else None)

    def lay_roof(self, a, args):
        x, y = self.target(a, args, flat=True)
        if not a.count("roof"):
            raise ActionError("missing_item", "you have no roof")
        if (x, y) in self.roofed:
            raise ActionError("occupied", "there is a roof there already")
        if not self.roof_rests(x, y):
            raise ActionError("bad_target", f"a roof rests on a wall, or on the roof beside it, no further than {ROOF_SPAN} tiles from a wall")
        yield from self.wait(a, 0.3)
        if (x, y) in self.roofed or not self.roof_rests(x, y):
            raise ActionError("changed", "something changed there")
        a.add("roof", -1)
        self.set_roof(x, y, True, by=a)
        a.bump("placed")
        return {}

    def _tool_unroof(self, a, args):
        x, y = self.target(a, args, flat=True)
        if (x, y) not in self.roofed:
            raise ActionError("bad_target", "there is no roof there")
        yield from self.wait(a, 0.3)
        if (x, y) not in self.roofed:
            raise ActionError("changed", "the roof is gone")
        self.set_roof(x, y, False, by=a)
        a.add("roof")
        return {"got": {"roof": 1}}
