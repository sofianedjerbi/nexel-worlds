"""Walking, pathfinding and sailing: strides, steps, walks and move_to."""

from ..pathfind import astar
from ..tiles import BLOCKS, DIRS, GROUNDS, B
from .constants import CLIMB_S, EAT_PACE, FALL_HP, FALL_SAFE, SLOPE_DOWN, SLOPE_UP, SPRINT_FOOD, SWIM_PACE, VIA_FAR, VIA_MAX, sec
from .entities import ActionError, Agent


class Movement:
    """Simulation mixin: walking, pathfinding and sailing: strides, steps, walks and move_to."""

    # ============================================================== tools

    def can_enter(self, a: Agent, x: int, y: int, z: int | None = None) -> bool:
        """Walkers stay on land or swim (on top of the water, whatever its depth); a moored boat can be boarded; sailors
        move over the water faster and may step ashore. z: the height they would stand at there: on a built block
        (storeys.py), what stands on that block is what counts, not the ground under it."""
        cell = self.floors.get(x, y, z) if z is not None else None
        if cell is not None:
            return not BLOCKS[B[cell[1]]].solid
        g, b = self.world.get(x, y)
        ground, block = GROUNDS[g], BLOCKS[b]
        if ground.liquid:
            return a.sailing or block.name == "boat" or not block.solid
        return ground.walkable and not block.solid

    def swimming(self, a: Agent) -> bool:
        """In the water without a boat (not on something built over it)."""
        return not a.sailing and GROUNDS[self.world.get(a.x, a.y)[0]].liquid and self.floors.get(a.x, a.y, self.height(a)) is None

    def can_go(self, a: Agent, x: int, y: int) -> bool:
        """From where `a` stands to the neighbouring (x, y): it isn't a wall, and where they'd land can be entered."""
        land = self.landing(a, x, y)
        return land is not None and self.can_enter(a, x, y, land)

    def why_not(self, a: Agent, x: int, y: int) -> str:
        land = self.landing(a, x, y)
        if land is None and self.can_enter(a, x, y):
            return "a wall, too high to jump (dig into it: dig with a pickaxe)"
        return self.thing(x, y, land).replace("_", " ") if land is not None and self.floors.get(x, y, land) else self.describe(x, y)

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
        x0, y0, h0 = a.x, a.y, self.height(a)
        climb = -self.step_onto(a, x, y)             # (Bodies: where you land there)
        if not a.sailing:                            # a tile on foot tires a little, at a sprint more, a jump up more still (needs.py)
            fast = bool(a.action) and self.sprints(a, a.action.args)
            self.tire(a, ("dash" if fast else "swim") if self.swimming(a) else "sprint" if fast else "walk")
            if climb > 0:
                self.tire(a, "jump")
        if climb and a.ready > self.tick:            # a jump up is hard going, a drop a little careful
            a.ready += round((a.ready - self.tick) * (SLOPE_UP if climb > 0 else SLOPE_DOWN))
        self.arrive(a)
        if self.on_ladder(x0, y0, h0, x, y, self.height(a)):
            if abs(climb) > 1:                       # (a ladder is climbed rung by rung: the next step waits for the top, or the foot)
                a.ready = max(a.ready, self.tick + sec(abs(climb) * CLIMB_S))
            return {}                                # (down a ladder: climbed, not fallen)
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
        """Seconds per tile: walking 0.2, sprinting (`run: true`) 0.1, sailing 0.15. In the water, from the tile you
        swim in, twice as long (SWIM_PACE): 0.4 swimming, 0.2 at a sprint. Eating meanwhile, twice as long again
        (EAT_PACE), on land and in the water: 0.8 for a tile swum with your mouth full."""
        if a.sailing:
            return 0.15
        return (0.1 if self.sprints(a, args) else 0.2) * (SWIM_PACE if self.swimming(a) else 1) * (EAT_PACE if a.aside is not None else 1)

    def sprints(self, a: Agent, args) -> bool:
        """Asked to run, and fed enough for it (three pieces of food or fewer: no sprinting)."""
        return bool(args.get("run")) and a.hunger > SPRINT_FOOD

    def pace(self, a: Agent, args):
        """Step first, then cool down: wait only until the previous stride is over, then claim this one.
        A movement interrupted by another (rapid key taps) keeps the progress it made instead of starting a
        fresh wait, while the speed limit stays exactly one tile per stride."""
        while self.tick < a.ready:
            yield
        a.ready = self.tick + sec(self.stride(a, args))

    def _tool_step(self, a, args):
        x, y = self.target(a, args, flat=True)
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
        steps, fall = yield from self.follow(a, args)            # (first, the way your screen has already walked: `from`)
        if fall:
            return {"steps": steps, "stopped": "fell", **fall}
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
        """Submitting it interrupts whatever was running. With `at` (a player's screen: the tile it stopped on), the
        way there is made first."""
        if "at" not in args:
            self.via_drop(a)
            return {}
        steps, fall = yield from self.follow(a, args)
        return {"steps": steps, **fall}

    # A player's screen walks ahead of the world (web/js/walk.js: it doesn't wait for an answer, which may come late)
    # and says where it went: the tiles it turned at (`walk`'s `from`) and stopped on (`stop`'s `at`), each [x, y, n],
    # n counting up. They are kept in order (a.via) and made first, a stride a tile, in straight lines, so the world
    # ends where the screen is. a.via_done says how far it got (the screen is told: views.py).

    def via_add(self, a: Agent, tile):
        if isinstance(tile, (list, tuple)) and len(tile) in (2, 3) and all(type(v) is int for v in tile) and len(a.via) < VIA_MAX:
            a.via.append((tile[0], tile[1], tile[2] if len(tile) == 3 else a.via_done))

    def via_drop(self, a: Agent):
        if a.via:
            a.via_done = a.via[-1][2]
            a.via.clear()

    def follow(self, a: Agent, args):
        """Make the way in a.via. -> (steps made, what a fall did to you). A tile that isn't straight ahead, or too
        far, or behind a wall: the way is given up (the screen then comes back to where the world has you)."""
        steps = 0
        while a.via:
            x, y, n = a.via[0]
            dx, dy = x - a.x, y - a.y
            if not dx and not dy:
                a.via.pop(0)
                a.via_done = n
                continue
            to = (a.x + (dx > 0) - (dx < 0), a.y + (dy > 0) - (dy < 0))
            if (dx and dy) or abs(dx) + abs(dy) > VIA_FAR or not self.can_go(a, *to):
                self.via_drop(a)
                break
            yield from self.pace(a, args)
            if not self.can_go(a, *to):
                self.via_drop(a)
                break
            fall = self.move(a, *to)
            steps += 1
            if fall:
                self.via_drop(a)
                return steps, fall
        return steps, {}

    def _tool_move_to(self, a, args):
        try:
            gx, gy = int(args["x"]), int(args["y"])
        except (KeyError, TypeError, ValueError):
            raise ActionError("bad_args", "move_to needs integer x and y")
        replans = 0
        ok = lambda x, y, z: self.can_enter(a, x, y, z) and (a.sailing or self.world.block(x, y) != "boat" or (x, y) == (gx, gy))
        # the way is worked out with heights (a floor over a room is another place than the room): up a layer at a
        # time, by the steps there are, and never down a fall that hurts (except a single step you ask for: the tile
        # beside you, off an edge). A tile nobody can stand on: to beside it
        drop = 99 if abs(gx - a.x) + abs(gy - a.y) == 1 else FALL_SAFE

        def moves(n):
            for dx, dy in DIRS.values():
                land = self.lands(n[2], n[0], n[1], n[0] + dx, n[1] + dy, climbs=True)
                if land is not None and (n[2] - land <= drop or self.on_ladder(*n, n[0] + dx, n[1] + dy, land)) and ok(n[0] + dx, n[1] + dy, land):
                    yield (n[0] + dx, n[1] + dy, land)
        gz = args.get("z") if type(args.get("z")) is int and args["z"] in self.world.surfaces(gx, gy) else None     # (z: that tile at that height: the floor over a room)
        beside = not any(ok(gx, gy, z) for z in ([gz] if gz is not None else self.world.surfaces(gx, gy)))
        way = lambda: astar((a.x, a.y, self.height(a)), (gx, gy) if gz is None else (gx, gy, gz), moves, beside=beside)
        path = way()
        if path is None:
            far = abs(gx - a.x) + abs(gy - a.y) > 64
            raise ActionError("no_path", "target further than 64 tiles" if far else
                              f"no walkable path to ({gx},{gy}) from ({a.x},{a.y})")
        steps = 0
        while path:
            yield from self.pace(a, args)
            nx, ny = path[0][:2]
            land = self.landing(a, nx, ny)
            if land is None or (self.height(a) - land > drop and not self.on_ladder(a.x, a.y, self.height(a), nx, ny, land)) or not ok(nx, ny, land):
                replans += 1
                path = way() if replans <= 2 else None
                if path is None:
                    raise ActionError("blocked", f"path blocked at ({nx},{ny}); stopped at ({a.x},{a.y})")
                continue
            self.move(a, nx, ny)
            path.pop(0)
            steps += 1
        return {"steps": steps, "arrived": [a.x, a.y], "adjacent_only": (a.x, a.y) != (gx, gy)}
