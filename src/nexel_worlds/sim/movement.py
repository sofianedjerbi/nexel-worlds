"""Walking, pathfinding and sailing: strides, steps, walks and move_to."""

from ..pathfind import astar
from ..tiles import DIRS, GROUNDS
from .leaping import Leaping
from .constants import CLIMB_S, EAT_PACE, PACE, FALL_HP, FALL_SAFE, SLOPE_DOWN, SLOPE_UP, SPRING_S, SPRINT_FOOD, SWIM_PACE, VIA_FAR, VIA_MAX, sec
from .entities import ActionError, Agent


class Movement(Leaping):
    """Simulation mixin: walking, pathfinding and sailing: strides, steps, walks and move_to."""

    # ============================================================== tools

    def swimming(self, a: Agent) -> bool:
        """In the water without a boat (not on something built over it), or in running water deep enough (waters.py)."""
        return not a.sailing and (GROUNDS[self.world.get(a.x, a.y)[0]].liquid and self.floors.get(a.x, a.y, self.height(a)) is None or self.wading(a))

    def can_go(self, a: Agent, x: int, y: int, jump: bool | None = None) -> bool:
        """From where `a` stands to the neighbouring (x, y): it isn't a wall, and where they'd land can be entered.
        (jump: Bodies.landing)"""
        land = self.landing(a, x, y, jump)
        return land is not None and self.stand(x, y, land, swims=True, sails=a.sailing)

    def why_not(self, a: Agent, x: int, y: int, jump: bool | None = None) -> str:
        land = self.landing(a, x, y, jump)
        if land is None and self.stand(x, y, swims=True, sails=a.sailing):
            h, w = self.height(a), self.world               # (what would make a way of it, said with the cells: an agent reads this)
            d = next((k for k, v in DIRS.items() if v == (x - a.x, y - a.y)), "that way")
            if w.solid(a.x, a.y, h + 2):
                return ("a step with no room over your head to jump (dig dir=up takes the block over your head; "
                        f"then the block in front at z={h + 2} if there is one; then jump dir={d})")
            if not w.solid(x, y, h + 2):
                return f"a step up: jump onto it (jump dir={d}); walking into it stops you"
            return (f"a wall, too high to jump (a step up: dig the block in front at your head's height, z={h + 2}, "
                    f"then jump dir={d}; or dig into it at your own height: dig with a pickaxe)")
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
        a.spring.pop((x, y), None)                   # (a jump is for one step)
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
        self.take_pile(a, (a.x, a.y))

    def stride(self, a: Agent, args) -> float:
        """Seconds per tile: walking 0.2, sprinting (`run: true`) 0.1, sailing 0.15. In the water, from the tile you
        swim in, twice as long (SWIM_PACE): 0.4 swimming, 0.2 at a sprint. Eating meanwhile, twice as long again
        (EAT_PACE), on land and in the water: 0.8 for a tile swum with your mouth full."""
        if a.sailing:
            return 1 / PACE["sail"]
        return 1 / PACE["sprint" if self.sprints(a, args) else "walk"] * (SWIM_PACE if self.swimming(a) else 1) * (EAT_PACE if a.aside is not None else 1)

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
            raise ActionError("blocked", f"{args.get('dir') or 'that tile'} is {self.why_not(a, x, y)}")
        yield from self.pace(a, args)
        if not self.can_go(a, x, y):
            raise ActionError("blocked", f"{args.get('dir') or 'that tile'} is {self.why_not(a, x, y)}")
        self.move(a, x, y)
        return {}

    def _tool_jump(self, a, args):
        """Jump: up a layer onto the step `dir` of you (the cell over it empty, and over your head). On the level, or
        with no dir, a hop where you stand: nothing changes (as in Minecraft). With `at` ([x, y]: a player's screen,
        the step it jumps for): while walking that way it is said at once and the walk takes the step when it comes to
        it (a.spring, SPRING_S); otherwise the way the screen walked is made first (it may be behind it: a stop's `at`
        still on its way), then the jump. A tap is never lost to a world a stride behind the screen."""
        at = args.get("at")
        if isinstance(at, (list, tuple)) and len(at) == 2 and all(type(v) is int for v in at):
            x, y = at
            if abs(x - a.x) + abs(y - a.y) > VIA_FAR:
                raise ActionError("out_of_range", "that step is too far to jump for")
        elif args.get("dir") is not None:
            x, y = self.target(a, args, flat=True)
        else:
            x = y = None
        self.emit("jump", a.x, a.y, name=a.name, step=x is not None)   # (step: up onto a step, its own arc as it goes; not a hop where it stands first: client state.js)
        if x is None:
            return {"hopped": True}
        came = getattr(self, "passed", None) if getattr(self, "passing", None) is a else None
        if came is not None and came.tool == "walk":     # (walking: the walk takes it)
            a.spring = {k: t for k, t in a.spring.items() if t >= self.tick}      # (several: a step on is jumped for before the first is reached)
            a.spring[(x, y)] = self.tick + sec(SPRING_S)
            return {"spring": [x, y]}
        _, fall = yield from self.follow(a, args)        # (the way the screen walked, first: Movement.follow)
        if fall:
            return fall
        if abs(x - a.x) + abs(y - a.y) != 1 or not self.world.solid(x, y, self.height(a) + 1):
            return {"hopped": True}                      # (no step there: a hop on the spot)
        def room():                                      # (before the stride and after it)
            if (a.x, a.y) == (x, y) or not self.can_go(a, x, y, jump=True):
                raise ActionError("blocked", f"{args.get('dir') or 'that tile'} is {self.why_not(a, x, y, jump=True)}")
        room()
        yield from self.pace(a, args)
        room()
        a.spring[(x, y)] = self.tick
        fall = self.move(a, x, y)
        return {"jumped": True, "z": self.height(a), **fall}

    def _tool_walk(self, a, args):
        """Keep walking in a direction at a steady stride until blocked or replaced by another action
        (e.g. `stop`). Lets a held key move smoothly without a round trip per tile."""
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "dir must be one of N, E, S, W")
        dx, dy = DIRS[d]
        steps, fall = yield from self.follow(a, args)            # (first, the way your screen has already walked: `from`)
        # (a fall on that way, the screen's before this walk, hurts, and the walk goes on: test_leaping.py)
        j = True if args.get("jump") else None                   # (auto-jump: a player's screen walks up every step it comes to)
        # (a player's held key, `push`, against a step a jump would take: it goes on pushing, as in Minecraft, and the
        # jump key's spring takes the step at once: a walk that ended there had the world a stride behind the screen)
        against = lambda: args.get("push") and self.can_go(a, a.x + dx, a.y + dy, jump=True)
        # (`ledge`: a player's screen goes off a ledge as high as a fall through the air itself (web/js/leap.js dropDue) and says so
        # (`stop` at its edge, then `leap`): the walk waits at the edge for it, a second at the most. It went off first, the world a
        # stride ahead of the screen walking from a standstill, the walk ended by the fall: the screen's drop was not its own)
        ledge, waited = bool(args.get("ledge")), 0
        a.walked = [(a.x, a.y, self.height(a))]
        def at_ledge():                                  # (the screen's own answer: web/js/leap.js ledge, by the same cells. Where it walked on, the world waiting there was a second behind it)
            if not ledge or waited >= sec(1.0) or a.sailing:
                return False
            w, h, x, y = self.world, self.height(a), a.x + dx, a.y + dy
            if w.solid(x, y, h + 1) or w.solid(x, y, h + 2):
                return False
            land = self.landing(a, x, y, j)
            return land is not None and h - land >= FALL_SAFE and not self.on_ladder(a.x, a.y, h, x, y, land)   # (down a ladder: climbed, move)
        while steps < 600:
            if not self.can_go(a, a.x + dx, a.y + dy, j):
                if against():
                    yield
                    continue
                return {"steps": steps, "stopped": "blocked", "blocked_by": self.why_not(a, a.x + dx, a.y + dy)}
            yield from self.pace(a, args)
            if not self.can_go(a, a.x + dx, a.y + dy, j):
                if against():
                    continue
                return {"steps": steps, "stopped": "blocked", "blocked_by": self.why_not(a, a.x + dx, a.y + dy)}
            if at_ledge():
                waited += 1
                yield
                continue
            if j:
                a.spring[(a.x + dx, a.y + dy)] = self.tick       # (Bodies.landing in move: the step is jumped)
            fall = self.move(a, a.x + dx, a.y + dy)
            steps += 1
            a.walked = [*a.walked[-2:], (a.x, a.y, self.height(a))] if not fall else []
            if fall:                                 # a fall that hurt: the walk ends where you landed
                return {"steps": steps, "stopped": "fell", **fall}
        return {"steps": steps, "stopped": "limit"}

    def _tool_stop(self, a, args):
        """Submitting it interrupts whatever was running. With `at` (a player's screen: the tile it stopped on), the
        way there is made first; a tile the walk just went past (its screen's frames late), gone back to (#131)."""
        walked, a.walked, at = a.walked, [], tuple(args["at"][:2]) if isinstance(args.get("at"), list) else None
        back = walked and (a.x, a.y) == walked[-1][:2] and next((t for t in walked[:-1] if t[:2] == at), None)
        if back:
            a.x, a.y, a.z = back
            self.via_drop(a)
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
        a.flying = None                                          # (a flight given up: down on the ground where it is)
        if a.via:
            a.via_done = a.via[-1][2]
            a.via.clear()

    def follow(self, a: Agent, args):
        """Make the way in a.via. -> (steps made, what a fall did to you). A tile that isn't straight ahead, or too
        far, or behind a wall: the way is given up (the screen then comes back to where the world has you)."""
        steps, j = 0, True if args.get("jump") else None         # (`jump`: the screen walks up steps by itself: auto-jump)
        while a.via:
            if len(a.via[0]) > 3:                                # a jump through the air (leaping.py): made, or given up
                n, fall = yield from self.fly(a)
                steps += n
                if fall:
                    return steps, fall
                continue
            x, y, n = a.via[0]
            dx, dy = x - a.x, y - a.y
            if not dx and not dy:
                a.via.pop(0)
                a.via_done = n
                continue
            to = (a.x + (dx > 0) - (dx < 0), a.y + (dy > 0) - (dy < 0))
            if (dx and dy) or abs(dx) + abs(dy) > VIA_FAR or not self.can_go(a, *to, j):
                self.via_drop(a)
                break
            yield from self.pace(a, args)
            if not self.can_go(a, *to, j):
                self.via_drop(a)
                break
            if j:
                a.spring[to] = self.tick
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
        ok = lambda x, y, z: self.stand(x, y, z, swims=True, sails=a.sailing) and (a.sailing or self.world.block(x, y) != "boat" or (x, y) == (gx, gy))
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
            land = self.landing(a, nx, ny, jump=True)          # (a way asked for jumps where it goes up: moves, lands)
            if land is None or (self.height(a) - land > drop and not self.on_ladder(a.x, a.y, self.height(a), nx, ny, land)) or not ok(nx, ny, land):
                replans += 1
                path = way() if replans <= 2 else None
                if path is None:
                    raise ActionError("blocked", f"path blocked at ({nx},{ny}); stopped at ({a.x},{a.y})")
                continue
            a.spring[(nx, ny)] = self.tick                       # (the way jumps where it goes up)
            self.move(a, nx, ny)
            path.pop(0)
            steps += 1
        return {"steps": steps, "arrived": [a.x, a.y], "adjacent_only": (a.x, a.y) != (gx, gy)}
