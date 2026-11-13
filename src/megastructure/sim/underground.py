"""Digging down: the cell under your feet goes, and you come down onto whatever ground is under it: a layer lower
where the ground is solid, further where it was hollow (a fall: Movement.fell). On a hill that cuts into it; at sea
level and below it digs a pit (down to DEEPEST). You climb out a layer at a time, as up any step."""

from ..tiles import BLOCKS, DEEPER, DEPTH, GROUNDS
from .entities import ActionError, Agent

DEEPEST = -12


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

    def _diggable_down(self, a: Agent) -> bool:
        g, b = self.world.get(a.x, a.y)
        return (BLOCKS[b].name == "none" and not GROUNDS[g].liquid and GROUNDS[g].name not in ("bridge", "floor")
                and self.height(a) > DEEPEST)

    def _tool_dig_down(self, a: Agent, args):
        if self.held(a, args) != "pickaxe":
            raise ActionError("need_tool", "digging down needs a pickaxe in hand (with: pickaxe)"
                              + ("" if a.count("pickaxe") else "; craft one at a workbench"))
        x, y = a.x, a.y
        if self.swimming(a):                                # the bottom under you, from the surface
            return (yield from self.deepen(a, x, y))
        if a.sailing or not self._diggable_down(a):
            raise ActionError("cannot_dig", "you need to stand on clear ground to dig down"
                              + (" (this is as deep as it goes)" if self.height(a) <= DEEPEST else ""))
        yield from self.wait(a, 1.5)
        if not self._diggable_down(a) or (a.x, a.y) != (x, y):
            raise ActionError("changed", "something changed here")
        z = self.height(a)
        a.add("stone" if z < 0 or z > 1 else "dirt", 1)
        self.set_cell(x, y, z, False, by=a, cause="dig_down")
        return {"level": self.height(a), **self.fell(a, z - self.height(a))}
