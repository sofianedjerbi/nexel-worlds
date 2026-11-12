"""Walking, pathfinding and sailing: strides, steps, walks and move_to."""

from ..pathfind import astar
from ..tiles import BLOCKS, DIRS, GROUNDS
from .constants import FALL_HP, FALL_SAFE, SLOPE_DOWN, SLOPE_UP, sec
from .entities import ActionError, Agent


class Movement:
    """Simulation mixin: walking, pathfinding and sailing: strides, steps, walks and move_to."""

    # ============================================================== tools

    def can_enter(self, a: Agent, x: int, y: int) -> bool:
        """Walkers stay on land or swim (on top of the water, whatever its depth); a moored boat can be boarded; sailors
        move over the water faster and may step ashore."""
        g, b = self.world.get(x, y)
        ground, block = GROUNDS[g], BLOCKS[b]
        if ground.liquid:
            return a.sailing or block.name == "boat" or not block.solid
        return ground.walkable and not block.solid

    def swimming(self, a: Agent) -> bool:
        """In the water without a boat."""
        return not a.sailing and GROUNDS[self.world.get(a.x, a.y)[0]].liquid

    def height(self, a: Agent) -> int:
        """The height `a` stands at: the ground here at or under where they were (the lowest ground, if none is)."""
        s = self.world.surfaces(a.x, a.y)
        a.z = max((z for z in s if z <= a.z), default=s[0])
        return a.z

    def in_cave(self, a: Agent) -> bool:
        """Something solid over your head."""
        return self.world.covered(a.x, a.y, self.height(a))

    def landing(self, a: Agent, x: int, y: int) -> int | None:
        """The height a step to the neighbouring (x, y) lands at, or None (a wall). The world is cells: where the
        cell at your body's height is solid there you jump up onto it if it is ground (nothing over it, nor over your
        own head: under a low ceiling there is no jumping out through it); where it is
        empty you step in at your own height and come down on whatever ground is under you there (a fall, however
        far: Movement.fell)."""
        h = self.height(a)
        if self.world.solid(x, y, h + 1):                # (a jump: room over it, and over your own head to make it)
            return None if self.world.solid(x, y, h + 2) or self.world.solid(a.x, a.y, h + 2) else h + 1
        return max(z for z in self.world.surfaces(x, y) if z <= h)

    def can_go(self, a: Agent, x: int, y: int) -> bool:
        """From where `a` stands to the neighbouring (x, y): the tile can be entered, and isn't a wall."""
        return self.can_enter(a, x, y) and self.landing(a, x, y) is not None

    def why_not(self, a: Agent, x: int, y: int) -> str:
        if self.can_enter(a, x, y) and self.landing(a, x, y) is None:
            return "a wall, too high to jump (dig into it: dig with a pickaxe)"
        return self.describe(x, y)

    def fell(self, a: Agent, layers: int) -> dict:
        """Coming down `layers` at once: up to FALL_SAFE is nothing, each layer more hurts."""
        if layers <= FALL_SAFE:
            return {}
        hurt = (layers - FALL_SAFE) * FALL_HP
        self.emit("fall", a.x, a.y, name=a.name, layers=layers, damage=hurt)
        self.damage(a, hurt, "fell")
        return {"fell": layers, "damage": hurt}

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
        h0, land = self.height(a), self.landing(a, x, y)
        a.x, a.y = x, y
        if land is not None:
            a.z = land
        climb = self.height(a) - h0
        if climb and a.ready > self.tick:            # a jump up is hard going, a drop a little careful
            a.ready += round((a.ready - self.tick) * (SLOPE_UP if climb > 0 else SLOPE_DOWN))
        self.arrive(a)
        return self.fell(a, -climb)                  # (what the fall did to you, if it was one)

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
        """Seconds per tile: walking 0.2, sprinting (`run: true`) 0.1, sailing 0.15, swimming 0.2 (no sprinting in water)."""
        if a.sailing:
            return 0.15
        if self.swimming(a):
            return 0.2
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
            fall = self.move(a, a.x + dx, a.y + dy)
            steps += 1
            if fall:                                 # a fall that hurt: the walk ends where you landed
                return {"steps": steps, "stopped": "fell", **fall}
        return {"steps": steps, "stopped": "limit"}

    def _tool_stop(self, a, args):
        yield from ()  # completes at once; submitting it interrupts whatever was running
        return {}

    def _tool_move_to(self, a, args):
        try:
            gx, gy = int(args["x"]), int(args["y"])
        except (KeyError, TypeError, ValueError):
            raise ActionError("bad_args", "move_to needs integer x and y")
        replans = 0
        ok = lambda x, y: self.can_enter(a, x, y) and (a.sailing or self.world.block(x, y) != "boat" or (x, y) == (gx, gy))
        # the way goes up a layer at a time and never down a fall that hurts (except a single step you ask for: the
        # tile beside you, off an edge)
        drop = 99 if abs(gx - a.x) + abs(gy - a.y) == 1 else FALL_SAFE
        step = lambda p, q: any(-drop <= j - i <= 1 for i in self.world.surfaces(*p) for j in self.world.surfaces(*q))
        path = astar(ok, (a.x, a.y), (gx, gy), step=step)
        if path is None:
            far = abs(gx - a.x) + abs(gy - a.y) > 64
            raise ActionError("no_path", "target further than 64 tiles" if far else
                              f"no walkable path to ({gx},{gy}) from ({a.x},{a.y})")
        steps = 0
        while path:
            yield from self.pace(a, args)
            nx, ny = path[0]
            land = self.landing(a, nx, ny) if self.can_enter(a, nx, ny) else None
            if land is None or self.height(a) - land > drop:
                replans += 1
                path = astar(ok, (a.x, a.y), (gx, gy), step=step) if replans <= 2 else None
                if path is None:
                    raise ActionError("blocked", f"path blocked at ({nx},{ny}); stopped at ({a.x},{a.y})")
                continue
            self.move(a, nx, ny)
            path.pop(0)
            steps += 1
        return {"steps": steps, "arrived": [a.x, a.y], "adjacent_only": (a.x, a.y) != (gx, gy)}
