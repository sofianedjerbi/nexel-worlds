"""Digging down: the ground where you stand goes down a layer, you with it, as in a world of blocks. Up on the heights
that cuts into the hill; at sea level and below it digs a pit (down to DEEPEST). You climb out a layer at a time,
as up any step."""

from ..tiles import BLOCKS, GROUNDS
from .entities import ActionError, Agent

DEEPEST = -12


class Underground:
    """Simulation mixin: digging down."""

    def _diggable_down(self, x, y) -> bool:
        g, b = self.world.get(x, y)
        return (BLOCKS[b].name == "none" and not GROUNDS[g].liquid and GROUNDS[g].name not in ("bridge", "floor")
                and self.world.level(x, y) > DEEPEST)

    def _tool_dig_down(self, a: Agent, args):
        if self.held(a, args) != "pickaxe":
            raise ActionError("need_tool", "digging down needs a pickaxe in hand (with: pickaxe)"
                              + ("" if a.count("pickaxe") else "; craft one at a workbench"))
        x, y = a.x, a.y
        if a.sailing or not self._diggable_down(x, y):
            raise ActionError("cannot_dig", "you need to stand on clear ground to dig down"
                              + (" (this is as deep as it goes)" if self.world.level(x, y) <= DEEPEST else ""))
        yield from self.wait(a, 1.5)
        if not self._diggable_down(x, y) or (a.x, a.y) != (x, y):
            raise ActionError("changed", "something changed here")
        lv, roof = self.world.level(x, y), self.world.roof(x, y)
        a.add("stone" if lv < 0 or lv > 1 or a.atop else "dirt", 1)
        self.gain_xp(a, 2, x, y)
        if a.atop:                                   # on a cave's roof: it comes down a layer (onto the cave: in)
            self.set_tile(x, y, roof=roof - 1, by=a, cause="dig_down")
            a.atop = roof > 1
            return {"level": lv + roof - 1}
        self.set_tile(x, y, level=lv - 1, roof=roof + 1 if roof else None, by=a, cause="dig_down")   # (in a cave: its roof stays)
        return {"level": lv - 1}
