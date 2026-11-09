"""Cave mouths: the way between a level and the one below it (see layers.py: a level is a region of the world).

dig_down cuts a mouth two tiles long, sloping down to the south: its top (A) where you stand, its deep end (B) just
south. Below, the same two tiles are a ramp up (A' under A, B' under B) at the foot of a small chamber. You walk in:
stepping from A down onto B takes you to B' below; stepping from B' up onto A' brings you out at A. The client
reveals the cave around the mouth as you go down (and the daylight as you come up), so it never looks like a jump."""

from ..layers import LAYER, depth
from ..tiles import BLOCKS, GROUNDS
from .entities import ActionError, Agent

MOUTH, RAMP_UP = "hole", "ladder"


class Underground:
    """Simulation mixin: digging a cave mouth, and walking through one."""

    def _diggable_down(self, x, y) -> bool:
        g, b = self.world.get(x, y)
        return BLOCKS[b].name == "none" and not GROUNDS[g].liquid and GROUNDS[g].name not in ("bridge", "floor")

    def _tool_dig_down(self, a: Agent, args):
        if self.held(a, args) != "pickaxe":
            raise ActionError("need_tool", "digging down needs a pickaxe in hand (with: pickaxe)"
                              + ("" if a.count("pickaxe") else "; craft one at a workbench"))
        x, y = a.x, a.y
        if a.sailing or not (self._diggable_down(x, y) and self._diggable_down(x, y + 1)) or self.entity_at(x, y + 1):
            raise ActionError("cannot_dig", "a cave mouth needs clear ground where you stand and just south of you")
        yield from self.wait(a, 3.0)
        if not (self.world.block(x, y) == "none" and self._diggable_down(x, y + 1)):
            raise ActionError("changed", "something is in the way now")
        bx = x + LAYER
        for dy in (-1, 0, 1, 2, 3):                   # the chamber below: the ramp's two tiles and room round its foot
            for dx in (-1, 0, 1):
                if self.world.block(bx + dx, y + dy) in ("cave_wall", "ore"):
                    self.set_tile(bx + dx, y + dy, ground="cave_floor", block="none", cause="dig_down")
        for dx in (-1, 1):                            # the ramp has rock either side of its top
            self.set_tile(bx + dx, y, ground="cave_floor", block="cave_wall", cause="dig_down")
        self.set_tile(bx, y, ground="cave_floor", block=RAMP_UP, by=a, cause="dig_down")
        self.set_tile(bx, y + 1, ground="cave_floor", block=RAMP_UP, by=a, cause="dig_down")
        self.set_tile(x, y, block=MOUTH, by=a, cause="dig_down")
        self.set_tile(x, y + 1, block=MOUTH, by=a, cause="dig_down")
        a.add("stone", 1)
        self.gain_xp(a, 2, x, y)
        return {"mouth": [x, y], "below": depth(x) + 1}

    def mouth_ok(self, x0, y0, x1, y1) -> bool:
        """A mouth's deep end is entered only from its top, a ramp's top only from its foot."""
        b = self.world.block(x1, y1)
        if b == MOUTH and self.world.block(x1, y1 - 1) == MOUTH:
            return (x0, y0) == (x1, y1 - 1)
        if b == RAMP_UP and self.world.block(x1, y1 + 1) == RAMP_UP:
            return (x0, y0) == (x1, y1 + 1)
        return True

    def through_mouth(self, a: Agent):
        """Called after a move: down onto a mouth's deep end, you're below; up onto a ramp's top, you're above."""
        b = self.world.block(a.x, a.y)
        if b == MOUTH and self.world.block(a.x, a.y - 1) == MOUTH:
            self._change_level(a, a.x + LAYER)
        elif b == RAMP_UP and self.world.block(a.x, a.y + 1) == RAMP_UP and depth(a.x):
            self._change_level(a, a.x - LAYER)

    def _change_level(self, a: Agent, x: int):
        d0 = depth(a.x)
        self.emit("level", a.x, a.y, name=a.name, depth=depth(x))
        a.x = x
        self.emit("level", a.x, a.y, name=a.name, depth=depth(x), arrived=True, was=d0)
