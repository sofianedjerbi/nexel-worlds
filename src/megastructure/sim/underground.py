"""Digging down: the cell under your feet goes, and you come down onto whatever ground is under it: a layer lower
where the ground is solid, further where it was hollow (a fall: Movement.fell). On a hill that cuts into it; at sea
level and below it digs a pit (down to DEEPEST). You climb out a layer at a time, as up any step.
And a hole dug beside you: `dig` aimed at a tile's ground with its height (`z`) takes the top cell of the land there,
a layer at a time, by hand or faster with a pickaxe (build mode's X on bare ground: web/js/build.js). Or a cell inside
the land that is open on a side (beside a hole, a tunnel's end): it goes and what is over it stays, a roof. So a way
down is dug as a tunnel, the room to stand in a step at a time ("like minecraft ... l shape tunnels. this enforce me
to dig huge columns"): build mode's X with the cursor in the ground.
And up: `dig` with dir "up" takes the cell over your own head (dig_over). With the cell in front of you at your head's
height (`dig` with dir and z: your z + 2) that is a step: head room to jump, and the block to jump onto. So whoever
can dig is never shut in: a stair is cut up out of any hole, two cells a layer, by hand too ("how do i climb up?
why i cant??": under their own stair a pickaxe dug level and down, and nothing dug upward).
What is dug is the block itself, in your pack (take_land)."""

from ..gen import LOW
from ..tiles import BLOCKS, DEEPER, DEPTH, GROUNDS
from .entities import ActionError, Agent

DEEPEST = LOW                            # the bottom cell stays: the lowest ground is at its top (it was -12)


class Underground:
    """Simulation mixin: digging down."""

    def deepen(self, a: Agent, x: int, y: int):
        """Dig the bottom of the water at (x, y) a layer deeper (no water moves: there is only more of it here)."""
        deeper = DEEPER.get(self.world.ground(x, y))
        if deeper is None:
            raise ActionError("cannot_dig", "the water is as deep as it goes here")
        yield from self.wait(a, 1.2)
        if DEEPER.get(self.world.ground(x, y)) != deeper or self.world.block(x, y) != "none":
            raise ActionError("changed", "something changed there")
        a.add("dirt")
        self.set_tile(x, y, ground=deeper, by=a, cause="dig")
        return {"got": {"dirt": 1}, "depth": DEPTH[deeper]}

    def dig_land(self, a: Agent, args):
        """A `dig` at the land's own top at a tile, named by its height: the hole is a layer deeper. -> the action, or
        None (a block or a thing there, laid ground, water: building.py goes on with it)."""
        if "z" not in args:
            return None
        x, y = self.target(a, args, flat=True)
        z = self.surface(a, x, y, args["z"])
        if self.floors.get(x, y, z) is not None:
            return None
        if z not in self.world.surfaces(x, y):              # (inside the land: open on a side; shut in, not; air: not this)
            if self.open_cell(x, y, z):
                return self._lower(a, x, y, z, self.held(a, args) == "pickaxe", inside=True)
            if self.world.solid(x, y, z):
                raise ActionError("cannot_dig", "that is inside the land, with no air beside it: dig to it from next to it")
            return None
        if z == self.world.level(x, y):
            g, b = self.world.get(x, y)
            if BLOCKS[b].name not in ("none", "flower") or GROUNDS[g].liquid or GROUNDS[g].name in ("cobble", "floor", "bridge"):
                return None
        return self._lower(a, x, y, z, self.held(a, args) == "pickaxe")

    def dig_over(self, a: Agent, args):
        """`dig` with dir "up": the cell over your own head (your z + 2: the one that stops a jump). Land: it goes, what
        is over it stays. Something built (a floor, a step of stairs): it comes back into your pack, as from beside."""
        x, y, z = a.x, a.y, self.height(a) + 2
        if self.floors.get(x, y, z) is not None:
            return self.take_block(a, x, y, z, self.held(a, args))
        if not self.world.solid(x, y, z):
            raise ActionError("bad_target", f"nothing over your head to dig. For a step up: dig the block in front of you at "
                                            f"your head's height (dig with dir and z={z}), then step onto the block under it")
        return self._lower(a, x, y, z, self.held(a, args) == "pickaxe", inside=True)

    def take_land(self, a: Agent, x: int, y: int, z: int, cause: str = "dig") -> str:
        """The cell of the land goes into the pack as the block it is (earth, stone: landblocks.py), to be put back
        as it was; stones are made of a stone block (the recipe `stone`). -> the item."""
        got = self.placed.take(x, y, z)
        a.add(got)
        self.set_cell(x, y, z, False, by=a, cause=cause)
        return got

    def open_cell(self, x: int, y: int, z: int) -> bool:
        """A cell of the land with air on a side of it (over it, under it, beside it): it can be dug."""
        w = self.world
        return w.solid(x, y, z) and any(not w.solid(x + dx, y + dy, z + dz) for dx, dy, dz in
                                        ((0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)))

    def _lower(self, a: Agent, x: int, y: int, z: int, pick: bool, inside: bool = False):
        self.reach(a, x, y, z=z)
        h = self.height(a)
        over = (x, y, z) == (a.x, a.y, h + 2)                # (the cell over your own head: dig_over)
        if inside and not over and not (abs(x - a.x) + abs(y - a.y) == 1 and h <= z <= h + 2):   # (in front of you: not through the land)
            raise ActionError("out_of_range", "a cell inside the land is dug from beside it, from your feet to your head, "
                                              "or over your own head (dir: up)")
        for again in (False, True):
            if z <= DEEPEST:
                raise ActionError("cannot_dig", "this is as deep as it goes")
            if not self.world.solid(x, y, z) or (self.world.solid(x, y, z + 1) and not (inside and self.open_cell(x, y, z))):
                raise ActionError("changed", "something changed there")
            if any(self.height(b) == z for b in self.bodies_on(x, y)):
                raise ActionError("occupied", "someone is standing there")
            if not again:
                yield from self.wait(a, 0.8 if pick else 2.4)      # (by hand it is slow work)
        if z == self.world.level(x, y) and self.world.block(x, y) == "flower":
            a.add("flower")
            self.world.set(x, y, block="none")
        self.tire(a, "dig")
        got = self.take_land(a, x, y, z)
        a.bump("dug")
        return {"got": {got: 1}, "cell": [x, y, z], "level": max(s for s in self.world.surfaces(x, y) if s < z) if any(s < z for s in self.world.surfaces(x, y)) else z - 1}

    def _diggable_down(self, a: Agent) -> bool:
        g, b = self.world.get(a.x, a.y)
        return (BLOCKS[b].name == "none" and not GROUNDS[g].liquid and GROUNDS[g].name not in ("bridge", "floor")
                and self.height(a) > DEEPEST)

    def _tool_dig_down(self, a: Agent, args):
        pick = self.held(a, args) == "pickaxe"             # (by hand too, slower: "i should be able to break this block by putting myself in top of it then digging under my feets")
        x, y = a.x, a.y
        if self.swimming(a):                                # the bottom under you, from the surface
            if not pick:
                raise ActionError("need_tool", "digging the bottom needs a pickaxe in hand (with: pickaxe)"
                                  + ("" if a.count("pickaxe") else "; craft one at a workbench"))
            return (yield from self.deepen(a, x, y))
        if a.sailing or not self._diggable_down(a):
            raise ActionError("cannot_dig", "you need to stand on clear ground to dig down"
                              + (" (this is as deep as it goes)" if self.height(a) <= DEEPEST else ""))
        yield from self.wait(a, 1.5 if pick else 3.0)
        if not self._diggable_down(a) or (a.x, a.y) != (x, y):
            raise ActionError("changed", "something changed here")
        z = self.height(a)
        got = self.take_land(a, x, y, z, cause="dig_down")
        return {"got": {got: 1}, "level": self.height(a), **self.fell(a, z - self.height(a))}
