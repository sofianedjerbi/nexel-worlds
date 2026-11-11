"""Walking, pathfinding and sailing: strides, steps, walks and move_to."""

from ..pathfind import astar
from ..tiles import BLOCKS, DIRS, GROUNDS
from ..layers import LAYER
from .constants import SLOPE_DOWN, SLOPE_UP, sec
from .entities import ActionError, Agent


class Movement:
    """Simulation mixin: walking, pathfinding and sailing: strides, steps, walks and move_to."""

    # ============================================================== tools

    def can_enter(self, a: Agent, x: int, y: int) -> bool:
        """Walkers stay on land; a moored boat can be boarded; sailors move over water and may step ashore."""
        g, b = self.world.get(x, y)
        ground, block = GROUNDS[g], BLOCKS[b]
        if ground.liquid:
            return a.sailing or block.name == "boat"
        return ground.walkable and not block.solid

    def can_go(self, a: Agent, x: int, y: int) -> bool:
        """From where `a` stands to the neighbouring (x, y): the tile can be entered and is at most a layer up or
        down; or, underground under a hole, there's open ground beside it on the level above (a jump up)."""
        return (self.can_enter(a, x, y) and self.world.can_step(a.x, a.y, x, y, hop=True)) or self.jump_up(a, x, y)

    def why_not(self, a: Agent, x: int, y: int) -> str:
        if self.can_enter(a, x, y) and not self.world.can_step(a.x, a.y, x, y, hop=True):
            up = self.world.level(x, y) > self.world.level(a.x, a.y)
            return "a cliff, too high to jump (dig into it: dig with a pickaxe)" if up else "a drop of more than a layer"
        return self.describe(x, y)

    def move(self, a: Agent, x: int, y: int):
        """Move to an adjacent tile, boarding or leaving a boat when crossing the shoreline."""
        if not a.sailing and self.world.block(x, y) == "boat":
            self.set_tile(x, y, block="none", by=a, cause="board")
            a.sailing = True
            self.emit("board", x, y, name=a.name)
        elif a.sailing and not GROUNDS[self.world.get(x, y)[0]].liquid:
            self.set_tile(a.x, a.y, block="boat", by=a, cause="moor")   # leave the boat where you got off
            a.sailing = False
            self.emit("moor", a.x, a.y, name=a.name)
        jump = not self.can_enter(a, x, y) and self.jump_up(a, x, y)
        climb = 1 if jump else self.world.level(x, y) - self.world.level(a.x, a.y)
        if jump:
            self._change_level(a, a.x - LAYER)       # (out of the hole, onto the level above)
            x -= LAYER
        a.x, a.y = x, y
        self.drop(a)                                  # onto a hole: down through it
        if climb and a.ready > self.tick:            # a jump up is hard going, a drop a little careful
            a.ready += round((a.ready - self.tick) * (SLOPE_UP if climb > 0 else SLOPE_DOWN))
        self.arrive(a)

    def arrive(self, a: Agent):
        """Called after every move: walking over items picks them up."""
        pile = self.items.get((a.x, a.y))
        if not pile:
            return
        got = dict(pile)
        for k, n in got.items():
            a.add(k, n)
        del self.items[(a.x, a.y)]
        self.dirty_items.add((a.x, a.y))
        self.emit("pick_up", a.x, a.y, name=a.name, items=got)

    def stride(self, a: Agent, args) -> float:
        """Seconds per tile: walking 0.2, sprinting (`run: true`) 0.1, sailing 0.15."""
        if a.sailing:
            return 0.15
        return 0.1 if args.get("run") else 0.2

    def pace(self, a: Agent, args):
        """Step first, then cool down: wait only until the previous stride is over, then claim this one.
        A movement interrupted by another (rapid key taps) keeps the progress it made instead of starting a
        fresh wait, while the speed limit stays exactly one tile per stride."""
        while self.tick < a.ready:
            yield
        a.ready = self.tick + sec(self.stride(a, args))

    def _tool_step(self, a, args):
        x, y = self.target(a, args)
        if not self.can_go(a, x, y):
            raise ActionError("blocked", f"{args['dir']} is {self.why_not(a, x, y)}")
        yield from self.pace(a, args)
        if not self.can_go(a, x, y):
            raise ActionError("blocked", f"{args['dir']} is {self.why_not(a, x, y)}")
        self.move(a, x, y)
        return {}

    def _tool_walk(self, a, args):
        """Keep walking in a direction at a steady stride until blocked or replaced by another action
        (e.g. `stop`). Lets a held key move smoothly without a round trip per tile."""
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "dir must be one of N, E, S, W")
        dx, dy = DIRS[d]
        steps = 0
        while steps < 600:
            if not self.can_go(a, a.x + dx, a.y + dy):
                return {"steps": steps, "stopped": "blocked", "blocked_by": self.why_not(a, a.x + dx, a.y + dy)}
            yield from self.pace(a, args)
            if not self.can_go(a, a.x + dx, a.y + dy):
                return {"steps": steps, "stopped": "blocked", "blocked_by": self.why_not(a, a.x + dx, a.y + dy)}
            self.move(a, a.x + dx, a.y + dy)
            steps += 1
        return {"steps": steps, "stopped": "limit"}

    def _tool_stop(self, a, args):
        yield from ()  # completes at once; submitting it interrupts whatever was running
        return {}

    def _tool_move_to(self, a, args):
        try:
            gx, gy = int(args["x"]), int(args["y"])
        except (KeyError, TypeError, ValueError):
            raise ActionError("bad_args", "move_to needs integer x and y")
        if abs(gx - a.x) + abs(gy - a.y) == 1 and self.jump_up(a, gx, gy):      # the tile beside you: a jump up
            yield from self.pace(a, args)
            if not self.can_go(a, gx, gy):
                raise ActionError("blocked", f"({gx},{gy}) is {self.why_not(a, gx, gy)}")
            self.move(a, gx, gy)
            return {"steps": 1, "arrived": [a.x, a.y], "adjacent_only": False}
        replans = 0
        ok = lambda x, y: self.can_enter(a, x, y) and (a.sailing or self.world.block(x, y) != "boat" or (x, y) == (gx, gy))
        step = lambda p, q: self.world.can_step(*p, *q, hop=True) and (self.world.block(*q) != "hole" or q == (gx, gy))
        path = astar(ok, (a.x, a.y), (gx, gy), step=step)
        if path is None:
            far = abs(gx - a.x) + abs(gy - a.y) > 64
            raise ActionError("no_path", "target further than 64 tiles" if far else
                              f"no walkable path to ({gx},{gy}) from ({a.x},{a.y})")
        steps = 0
        while path:
            yield from self.pace(a, args)
            nx, ny = path[0]
            if not self.can_go(a, nx, ny):
                replans += 1
                path = astar(ok, (a.x, a.y), (gx, gy), step=step) if replans <= 2 else None
                if path is None:
                    raise ActionError("blocked", f"path blocked at ({nx},{ny}); stopped at ({a.x},{a.y})")
                continue
            self.move(a, nx, ny)
            path.pop(0)
            steps += 1
        return {"steps": steps, "arrived": [a.x, a.y], "adjacent_only": (a.x, a.y) != (gx, gy)}
