"""Digging down, dropping through holes and jumping up: the world in layers, as in a world of blocks.

Up top, the land has heights (world.level): dig_down where you stand lowers it a layer (you go down with it). On the
lowest ground (level 0, or a cave floor) it digs a hole straight through: you drop into the level below (layers.py:
a level is a region of the world, LAYER tiles east), onto a floor cut for you right under the hole. Walking onto any
hole drops you the same way. Back up: you jump, a layer at a time. Up top onto ground one level higher; underground,
standing under a hole, onto any open ground beside it on the level above."""

from ..layers import LAYER, depth
from ..tiles import BLOCKS, GROUNDS
from .entities import ActionError, Agent

HOLE = "hole"
OPEN_BELOW = ("cave_wall", "ore", "ladder", "mushroom")


class Underground:
    """Simulation mixin: digging down, holes, and jumping up out of them."""

    def _diggable_down(self, x, y) -> bool:
        g, b = self.world.get(x, y)
        return BLOCKS[b].name == "none" and not GROUNDS[g].liquid and GROUNDS[g].name not in ("bridge", "floor")

    def _tool_dig_down(self, a: Agent, args):
        if self.held(a, args) != "pickaxe":
            raise ActionError("need_tool", "digging down needs a pickaxe in hand (with: pickaxe)"
                              + ("" if a.count("pickaxe") else "; craft one at a workbench"))
        x, y = a.x, a.y
        if a.sailing or not self._diggable_down(x, y):
            raise ActionError("cannot_dig", "you need to stand on clear ground to dig down")
        yield from self.wait(a, 1.5)
        if not self._diggable_down(x, y) or (a.x, a.y) != (x, y):
            raise ActionError("changed", "something changed here")
        a.add("stone" if depth(x) or self.world.level(x, y) > 1 else "dirt", 1)
        self.gain_xp(a, 2, x, y)
        lv = self.world.level(x, y)
        if lv:                                       # up on the heights: the ground goes down a layer, you with it
            self.set_tile(x, y, level=lv - 1, by=a, cause="dig_down")
            return {"level": lv - 1}
        self.open_below(x, y)
        self.set_tile(x, y, block=HOLE, by=a, cause="dig_down")
        self.drop(a)
        return {"hole": [x, y], "depth": depth(a.x)}

    def open_below(self, x, y):
        """The tile under (x, y) on the level below: a floor to land on."""
        bx = x + LAYER
        if self.world.block(bx, y) in OPEN_BELOW or self.world.ground(bx, y) != "cave_floor":
            self.set_tile(bx, y, ground="cave_floor", block="none", cause="dig_down")

    def drop(self, a: Agent):
        """On a hole: down through it to the level below (and on down, through holes under holes)."""
        n = 0
        while self.world.block(a.x, a.y) == HOLE and n < 64:
            self.open_below(a.x, a.y)
            self._change_level(a, a.x + LAYER)
            n += 1

    def jump_up(self, a: Agent, x: int, y: int) -> bool:
        """Underground, under a hole: onto open ground beside it on the level above. (x, y): the tile beside you,
        on your own level. True if you can (and the tile you'd land on is the one above it)."""
        if not depth(a.x) or abs(x - a.x) + abs(y - a.y) != 1 or self.world.block(a.x - LAYER, a.y) != HOLE:
            return False
        ux = x - LAYER
        return (self.can_enter(a, ux, y) and self.world.block(ux, y) != HOLE
                and (depth(ux) or self.world.level(ux, y) == 0))

    def _change_level(self, a: Agent, x: int):
        d0 = depth(a.x)
        self.emit("level", a.x, a.y, name=a.name, depth=depth(x))
        a.x = x
        self.emit("level", a.x, a.y, name=a.name, depth=depth(x), arrived=True, was=d0)
