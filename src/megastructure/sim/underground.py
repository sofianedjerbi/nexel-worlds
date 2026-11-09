"""Digging down and climbing up between underground levels (see layers.py: a level is a region of the world)."""

from ..layers import LAYER, depth
from ..tiles import BLOCKS, GROUNDS
from .entities import ActionError, Agent


class Underground:
    """Simulation mixin: dig_down (a hole here, a ladder below, and you go down) and climb (up a ladder, down a hole)."""

    def _tool_dig_down(self, a: Agent, args):
        if self.held(a, args) != "pickaxe":
            raise ActionError("need_tool", "digging down needs a pickaxe in hand (with: pickaxe)"
                              + ("" if a.count("pickaxe") else "; craft one at a workbench"))
        g, b = self.world.get(a.x, a.y)
        if BLOCKS[b].name != "none" or GROUNDS[g].liquid or GROUNDS[g].name in ("bridge", "floor") or a.sailing:
            raise ActionError("cannot_dig", f"you can't dig down through {self.describe(a.x, a.y)}")
        yield from self.wait(a, 3.0)
        if self.world.block(a.x, a.y) != "none":
            raise ActionError("changed", "something is in the way now")
        x, y, below = a.x, a.y, a.x + LAYER
        self.set_tile(x, y, block="hole", by=a, cause="dig_down")
        for dy in (-1, 0, 1):                         # a small chamber at the foot of the ladder
            for dx in (-1, 0, 1):
                if self.world.block(below + dx, y + dy) in ("cave_wall", "ore"):
                    self.set_tile(below + dx, y + dy, ground="cave_floor", block="none", cause="dig_down")
        self.set_tile(below, y, ground="cave_floor", block="ladder", by=a, cause="dig_down")
        a.add("stone", 1)
        self._change_level(a, below, y)
        self.gain_xp(a, 2, below, y)
        return {"depth": depth(a.x)}

    def _tool_climb(self, a: Agent, args):
        here = self.world.block(a.x, a.y)
        if here == "ladder":
            to = a.x - LAYER
        elif here == "hole":
            to = a.x + LAYER
        else:
            raise ActionError("nothing_to_climb", "stand on a ladder to climb up, or on a hole to go down")
        yield from self.wait(a, 0.4)
        self._change_level(a, to, a.y)
        return {"depth": depth(a.x)}

    def _change_level(self, a: Agent, x: int, y: int):
        d0 = depth(a.x)
        self.emit("level", a.x, a.y, name=a.name, depth=depth(x))   # for whoever saw them go
        a.x, a.y = x, y
        self.emit("level", a.x, a.y, name=a.name, depth=depth(x), arrived=True, was=d0)
