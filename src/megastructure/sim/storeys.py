"""Building up, a block at a time, as the land itself is made (cells: world.py).

A block (planks: a floor; shingles: a roof) fills one cell over the ground. It rests on the block under it (a step:
you jump up onto it as onto any ledge), or on a wall or a door standing right under it with a storey of room between
(STOREY: two cells to stand in, the block the third), or it holds to a block beside it at its own height, land or
built. You stand on it and build on it: walls, a door, a bed, and the next floor's blocks over those. So a second
floor is a floor laid on the walls, the way up is blocks one and two high beside it, and a roof is the same block in
shingles. (A roof was a tile laid over a tile by a rule of its own: over a wall or beside a roof, no further than
three tiles from a wall; nobody could stand on it, nothing could be built on it.)
What stands on a built block is kept with it (floors.py); the ground under it keeps its own. A block of earth on the
land is the land itself, a layer higher: nothing is kept of it but the cell."""

import sqlite3

from .. import tiles as T
from ..floors import KINDS, Floors
from ..gen import HIGH, LOW, col_floor, col_solid, col_top
from ..tiles import BLOCKS, DIRS, GROUNDS, PLACEABLE, B
from .entities import ActionError

STOREY = 3                                        # a floor is this many layers over the one under it
RESTS_ON = ("wood_wall", "stone_wall", "door")    # what holds a block up from under, a storey below it
UPSTAIRS = ("wood_wall", "stone_wall", "door", "fence", "gate", "chair", "table", "bed", "plant", "clock", "rug")
EARTH = "dirt"                                    # the piece that raises the land a layer


class Storeys:
    """Simulation mixin: blocks built over the ground, what stands on them, and the land raised a layer."""

    def open_floors(self, store):
        self.floors = Floors(store)
        if not store.get_meta("floors"):                # once: a world from when roofs were tiles over tiles
            self.old_roofs(store)
            store.set_meta("floors", 1)

    def old_roofs(self, store):
        """Each roof tile of the old kind (table `roofs`) becomes a roof block: each roof whole, a storey over the
        highest ground it covers."""
        try:
            tiles = {(x, y) for x, y in store.db.execute("SELECT x, y FROM roofs")}
        except sqlite3.OperationalError:
            return
        while tiles:
            part, stack = set(), [tiles.pop()]
            while stack:
                x, y = stack.pop()
                part.add((x, y))
                for dx, dy in DIRS.values():
                    if (x + dx, y + dy) in tiles:
                        tiles.discard((x + dx, y + dy))
                        stack.append((x + dx, y + dy))
            z = max(self.world.level(x, y) for x, y in part) + STOREY
            for x, y in part:
                if z <= HIGH and not self.world.solid(x, y, z):
                    self.world.set_cell(x, y, z, True)
                    self.floors.set(x, y, z, "roof")

    # ============================================================== what is where

    def land_col(self, x, y) -> int:
        """The tile's column without what was built in it: the land alone (what a screen paints as land)."""
        return self.world.col(x, y) & ~self.floors.mask(x, y)

    def land_roof(self, x, y) -> int:
        """How far up the land goes over the tile's lowest ground (a cave: 0 under the sky, or under a built floor)."""
        c = self.land_col(x, y)
        return col_top(c) - col_floor(c)

    def thing(self, x, y, z) -> str:
        """What stands at height z of the tile: on a built block, what was put on it; on the ground, the tile's own."""
        cell = self.floors.get(x, y, z)
        if cell is not None:
            return cell[1]
        return self.world.block(x, y) if z == self.world.level(x, y) else "none"

    def surface(self, a, x, y, z=None) -> int:
        """The height an action of `a` on the tile is about: the one it names, or the ground there nearest its own."""
        if z is not None:
            if type(z) is not int:
                raise ActionError("bad_args", "z must be an integer")
            return z
        h = self.height(a)
        return min(self.world.surfaces(x, y), key=lambda s: abs(s - h))

    def bodies_on(self, x, y) -> list:
        return [b for b in (*self.agents.values(), *self.creatures.values())
                if (b.x, b.y) == (x, y) and b.hp > 0 and getattr(b, "online", True)]

    def block_fits(self, x, y, z) -> str | None:
        """Why no block can go in the cell (x, y, z); None when one can."""
        w = self.world
        if not LOW < z <= HIGH - 2:
            return "nothing is built that high"
        if w.solid(x, y, z):
            return "there is a block there already"
        under = max(s for s in w.surfaces(x, y) if s < z)
        if under == z - 1:                               # on a block: it stacks
            if under == w.level(x, y) and GROUNDS[w.get(x, y)[0]].liquid and self.floors.get(x, y, under) is None:
                return "nothing stands on water: lay a bridge first"
            what = self.thing(x, y, under)
            return None if what == "none" else f"the {what.replace('_', ' ')} is in the way"
        if z - under < STOREY:
            return "too low over the floor: leave room to stand under it"
        if z - under == STOREY and self.thing(x, y, under) in RESTS_ON:
            return None                                  # on the wall under it
        if any(w.solid(x + dx, y + dy, z) for dx, dy in DIRS.values()):
            return None                                  # beside a block at its own height
        return "a block rests on the block or the wall under it, or holds to a block beside it"

    # ============================================================== the changes

    def set_block(self, x, y, z, kind, thing="none", by=None, cause="place"):
        """Build the cell (kind), change what stands on it (thing), or take the block away (kind None)."""
        self.world.set_cell(x, y, z, kind is not None)
        self.floors.set(x, y, z, kind, thing)
        self.stats["tiles_changed"] += 1
        self.emit("floor", x, y, z=z, kind=kind, thing=BLOCKS[B[thing]].char, by=by.name if by else None, cause=cause)

    def raze(self, x, y):
        """Everything built over the tile goes (the land there is being laid out anew: dev tools)."""
        for z in list(self.floors.at.get((x, y), {})):
            self.set_block(x, y, z, None, cause="dig")

    def lay_block(self, a, x, y, z, item):
        """Put a block of the pack in the cell (x, y, z)."""
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}")
        self.reach(a, x, y, z=z)
        for again in (False, True):
            why = self.block_fits(x, y, z)
            if why:
                raise ActionError("changed" if again else "bad_target", why)
            if any(1 <= z - self.height(b) <= 2 for b in self.bodies_on(x, y)):
                raise ActionError("occupied", "someone is standing there")
            if not again:
                yield from self.wait(a, 0.3)
        a.add(item, -1)
        self.set_block(x, y, z, item, by=a)
        a.bump("placed")
        return {"z": z}

    def put_on(self, a, x, y, z, item):
        """Stand a thing of the pack on the built block at (x, y, z)."""
        block = PLACEABLE.get(item)
        if block not in UPSTAIRS:
            raise ActionError("bad_target", f"a {item.replace('_', ' ')} needs the ground under it")
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}")
        self.reach(a, x, y, z=z)
        for again in (False, True):
            cell = self.floors.get(x, y, z)
            if cell is None or self.world.solid(x, y, z + 1):
                raise ActionError("bad_target", "there is no floor there to stand it on")
            if cell[1] != "none":
                raise ActionError("occupied", f"there is a {cell[1].replace('_', ' ')} there")
            if BLOCKS[B[block]].solid and any(self.height(b) == z for b in self.bodies_on(x, y)):
                raise ActionError("occupied", "someone is standing there")
            if not again:
                yield from self.wait(a, 0.3)
        a.add(item, -1)
        self.set_block(x, y, z, cell[0], block, by=a)
        a.bump("placed")
        return {"z": z}

    def take_block(self, a, x, y, z, tool=None):
        """Take back what is built at height z of the tile: what stands on the block first, then the block."""
        cell = self.floors.get(x, y, z)
        if cell is None:
            raise ActionError("bad_target", "nothing is built there")
        self.reach(a, x, y, z=z)
        kind, thing = cell
        if thing != "none":
            block = BLOCKS[B[thing]]
            yield from self.wait(a, block.hardness / 20 * (T.BY_HAND[block.tool] if block.tool and tool != block.tool else 1))
            if self.floors.get(x, y, z) != cell:
                raise ActionError("changed", "something changed there")
            for k, n in block.drops.items():
                a.add(k, n)
            self.tire(a, "dig")
            self.set_block(x, y, z, kind, by=a, cause="dig")
            a.bump("dug")
            return {"got": dict(block.drops)}
        for again in (False, True):
            if self.floors.get(x, y, z) != cell:
                raise ActionError("changed", "something changed there")
            if self.world.solid(x, y, z + 1):
                raise ActionError("bad_target", "take the block on top of it first")
            if not again:
                yield from self.wait(a, 0.3)
        a.add(kind)
        self.set_block(x, y, z, None, by=a, cause="dig")
        a.bump("dug")
        return {"got": {kind: 1}}

    def raise_land(self, a, x, y):
        """A block of earth on the land: the ground there comes up a layer, as digging takes it down one."""
        for again in (False, True):
            top = self.world.top(x, y)
            if self.world.col(x, y) != col_solid(top) or top >= HIGH - STOREY:
                raise ActionError("bad_target", "earth goes on open ground")
            if self.world.block(x, y) not in ("none", "flower"):
                raise ActionError("occupied", f"there is a {self.world.block(x, y).replace('_', ' ')} there")
            if self.bodies_on(x, y):
                raise ActionError("occupied", "someone is standing there")
            if not again:
                yield from self.wait(a, 0.3)
        if self.world.block(x, y) == "flower":
            a.add("flower")
            self.world.set(x, y, block="none")
        a.add(EARTH, -1)
        self.set_cell(x, y, top + 1, True, by=a, cause="place")
        a.bump("placed")
        return {"level": top + 1}

    # ============================================================== the tools' way in (building.py)

    def place_up(self, a, args):
        """A `place` that is not the ground's own: a block for a cell (planks, a roof: at `z`, or by hand on top of
        the built block you face, a roof a storey over the tile), a thing for a built block, earth for the land.
        -> the action, or None (building.py goes on)."""
        item = str(args.get("item", ""))
        if item not in KINDS and item not in PLACEABLE and item != EARTH:
            return None
        x, y = self.target(a, args, flat=True)
        s = self.surface(a, x, y, args.get("z"))         # (the height it is about: named, or the ground nearest your own)
        on_land = self.floors.get(x, y, s) is None       # ...which is the land's own, not a built block
        if item == EARTH:
            land = on_land and s == self.world.top(x, y) and self.world.block(x, y) in ("none", "flower")
            return self.raise_land(a, x, y) if land and self.world.ground(x, y) in T.LAND else None
        if item in KINDS:
            if item == "plank" and on_land and s == self.world.level(x, y):
                return None                              # (the ground itself: a floor laid in it, a bridge)
            if "z" in args:
                return self.lay_block(a, x, y, s, item)
            return self.lay_block(a, x, y, s + (STOREY if item == "roof" else 1), item)
        return None if on_land else self.put_on(a, x, y, s, item)

    def dig_up(self, a, args):
        """A `dig` at what is built over the ground: at `z`, or by hand the block in front of you (the highest your
        body meets, or the one you stand level with). -> the action, or None (building.py goes on)."""
        x, y = self.target(a, args, flat=True)
        h = self.height(a)
        z = self.surface(a, x, y, args["z"]) if "z" in args else next((c for c in (h + 2, h + 1, h) if self.floors.get(x, y, c)), None)
        return self.take_block(a, x, y, z, self.held(a, args)) if z is not None and self.floors.get(x, y, z) else None

    def _tool_unroof(self, a, args):
        """Take back the block over that tile (the lowest one over your head's height)."""
        x, y = self.target(a, args, flat=True)
        z = min((c for c in self.floors.at.get((x, y), {}) if c > self.height(a)), default=None)
        if z is None:
            raise ActionError("bad_target", "nothing is built over that tile")
        return (yield from self.take_block(a, x, y, z, self.held(a, args)))
