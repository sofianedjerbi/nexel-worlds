"""Bodies: whoever stands in the world, a person or a creature, stands on the same land in the same way.

The land is cells (world.py). A body has a tile and the height it stands at (z), and is one cell tall (the cell
z + 1: "1 block = player"). It goes from a tile to the next by one rule: a step in at its own height where that cell
is empty, coming down on the ground under it there (a fall, however far); a jump up a layer onto a step with room
over it (and over your own head to make it). A person jumps when they mean to (the `jump` tool, a key: walking into
a step stops you, as in Minecraft; stairs are walked up); a creature hops on its own. Under a hill it is in a cave,
at the height it walked in at.
Who may go where is each kind's own business (people: Movement, with water, boats and falls that hurt; creatures:
Animals, which take no door and no fall that would hurt them); where they end up, and how far they reach, is here."""

from ..gen import LOW
from ..tiles import DIRS
from .constants import FALL_SAFE, LAYER, TARGET_R
from .entities import ActionError


class Bodies:
    """Simulation mixin: a body on the land, a person's or a creature's: its height, its steps, its reach."""

    def height(self, b) -> int:
        """The height `b` stands at: the ground here at or under where it was (the lowest ground, if none is: where a
        body that has never moved starts)."""
        s = self.world.surfaces(b.x, b.y)
        b.z = max((z for z in s if z <= b.z), default=s[0])
        return b.z

    def in_cave(self, b) -> bool:
        """Land over its head (not a floor or a roof somebody built: storeys.py)."""
        return bool(self.land_col(b.x, b.y) >> (self.height(b) - LOW + 1))

    def landing(self, b, x: int, y: int, jump: bool | None = None) -> int | None:
        """The height a step to the neighbouring (x, y) lands at, or None (a wall). Where the cell at your body's height
        is solid it is a step: you jump up onto it if you jump (`jump`; None: a creature always does, a person when
        they sprang for that tile: springs) and the cell over it is empty, and the one over your own head (under a low
        ceiling there is no jumping out through it); where it is empty you step in at your own height and come down
        on whatever ground is under you (a fall, however far)."""
        person = hasattr(b, "inventory")
        if jump is None:
            jump = not person or self.springs(b, x, y)
        return self.lands(self.height(b), b.x, b.y, x, y, climbs=person, jump=jump)

    def springs(self, b, x: int, y: int) -> bool:
        """`b` jumped for the step onto (x, y) a moment ago (Movement._tool_jump: a.spring)."""
        return self.tick <= getattr(b, "spring", {}).get((x, y), -1)

    def lands(self, h: int, x0: int, y0: int, x: int, y: int, climbs: bool = False, jump: bool = True) -> int | None:
        """...the same, for anyone standing at height h on (x0, y0) (the way somewhere is worked out with it: `jump`,
        the way may jump). With `climbs` (people): on a ladder, where the step would be a wall or nowhere to stand, up
        it (climbing.py)."""
        w = self.world
        jump = jump or self.stairs_at(x, y, h + 1) or self.stairs_at(x0, y0, h)     # (stairs are walked up: onto a step of them, or off the top one)
        if w.solid(x, y, h + 1):                         # a step: a jump, with room over it and over your own head to make it
            land = h + 1 if jump and not w.solid(x, y, h + 2) and not w.solid(x0, y0, h + 2) else None
        else:                                            # in at your height, down onto the ground there (a fall)
            land = max(z for z in w.surfaces(x, y) if z <= h)
        if climbs and self.thing(x0, y0, h) == "ladder" and (land is None or not self.open_at(x, y, land)):
            up = self.climb_to(h, x0, y0, x, y)
            if up is not None:
                return up
        return land

    def stairs_at(self, x: int, y: int, z: int) -> bool:
        """A step of a flight of stairs is the built block at height z there (storeys.py)."""
        cell = self.floors.get(x, y, z)
        return cell is not None and cell[0] == "stairs"

    def safe_step(self, b, x: int, y: int) -> bool:
        """A step to the neighbouring (x, y) that is no wall and no fall that hurts: one a body takes of itself."""
        land = self.landing(b, x, y)
        return land is not None and self.height(b) - land <= FALL_SAFE

    def step_onto(self, b, x: int, y: int) -> int:
        """Put `b` on the neighbouring (x, y), where it lands. -> the layers it came down (under 0: it went up)."""
        h0, land = self.height(b), self.landing(b, x, y)
        b.x, b.y = x, y
        if land is not None:
            b.z = land
        return h0 - self.height(b)

    # ============================================================== reach

    def near(self, a, x: int, y: int, r: float, z: int | None = None) -> bool:
        """Is (x, y) within reach r of `a`? Reach is a circle round you, as the crow flies: r tiles, and the half tile
        to the far tile's edge. Height is distance too, a layer half a tile: what is too far up or down is out of
        reach, however near on the map. z: the height of what is there (someone's own: height(); a tile's, when not
        given: its ground nearest your own)."""
        h = self.height(a)
        if z is None:
            z = min(self.world.surfaces(x, y), key=lambda s: abs(s - h))
        return (x - a.x) ** 2 + (y - a.y) ** 2 + ((z - h) * LAYER) ** 2 <= (r + .5) ** 2

    def land_between(self, a, x: int, y: int, z: int) -> bool:
        """What stands at height z on (x, y) is behind the land for `a`: higher than it, its own tile is shut over its
        head on the way up to there; lower, the thing's tile is shut over the thing. (A hand goes up your own open
        column and over, or down the open one in front: a tree was chopped from a tunnel four layers under it.)"""
        h = self.height(a)
        if z > h:
            return any(self.world.solid(a.x, a.y, c) for c in range(h + 2, z + 2))
        return (x, y) != (a.x, a.y) and any(self.world.solid(x, y, c) for c in range(z + 1, h + 2))

    def reach(self, a, x: int, y: int, r: float = TARGET_R, z: int | None = None):
        if not self.near(a, x, y, r, z):
            raise ActionError("out_of_range", f"({x},{y}) is out of reach: {r} tiles round you, height counted "
                                              "(a layer is half a tile)")

    def target(self, a, args, flat=False) -> tuple[int, int]:
        """The tile an action is aimed at: `dir` (the adjacent tile that way), or an absolute `x`, `y`. Within reach
        (Movement.near: TARGET_R round you, a walking player's client being up to a tile ahead of the server; height
        counted, unless `flat`: a step, a wall you face)."""
        if "x" in args and "y" in args and args.get("dir") is None:
            try:
                x, y = int(args["x"]), int(args["y"])                 # (your own tile too: a flower underfoot)
            except (TypeError, ValueError):
                raise ActionError("bad_args", "x and y must be integers")
        else:
            d = str(args.get("dir", "")).upper()
            if d not in DIRS:
                raise ActionError("bad_args", "aim with dir (N, E, S or W) or with x and y")
            x, y = a.x + DIRS[d][0], a.y + DIRS[d][1]
        self.reach(a, x, y, z=self.height(a) if flat else None)
        return x, y
