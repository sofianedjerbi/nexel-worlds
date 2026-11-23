"""A player's real jump (web/js/leap.js): "jumping + sprinting and jumping + directing yourself just like minecraft".

The screen works the jump out frame by frame: off the ground with the walk's speed, up and down as a thrown thing
goes (LEAP_G, LEAP_TOP), steered a little in the air, stopped by the land higher than its feet, down on whatever is
under it. As it goes it says each tile it comes over (`leap` with `path`), and where it lands (`leap` with `land`).
They go into the way the screen has walked (a.via, Movement.follow) as a flight, made in order after the tiles before
it, a tile a stride (the screen goes no faster): while it lasts the body keeps the height it left from
(Bodies.height), every tile is checked to be next to the one before and reachable by the arc (room for two cells
over a ground no higher than its top), the landing to be a ground of the tile it is on under the top, and there are
no more than LEAP_TILES. Then it comes down there (a fall that hurts, as a step off a ledge does). A flight that does
not hold, or whose end is not said in LEAP_WAIT, is given up: down on the ground where it is, and the screen comes
back to where the world has you (walk.js). (It was said only once the screen had landed: the world a whole jump
behind, the walk slowing down to wait for it at every step of a run of them.)"""

import math

from .constants import sec

LEAP_G = 950 / 16          # levels/s2: its weight (web/js/jump.js JUMP.g, in art px, 16 a level)
LEAP_TOP = 20 / 16         # levels over where it leaves at the top (JUMP.top: a block and a quarter)
LEAP_TILES = 12            # tiles a flight may go over at the most
LEAP_WAIT = 2.0            # seconds the world waits for the rest of a flight


def airtime(dz: float) -> float:
    """Seconds in the air for a jump from 0 to dz levels."""
    v = math.sqrt(2 * LEAP_G * LEAP_TOP)
    return v / LEAP_G + math.sqrt(2 * max(0.0, LEAP_TOP - dz) / LEAP_G)


class Leaping:
    """Simulation mixin: a player's jump through the air."""

    def _tool_leap(self, a, args):
        path, land, n = args.get("path") or [], args.get("land"), args.get("n")
        if not (isinstance(path, list) and len(path) <= LEAP_TILES and (land is None or type(land) is int) and type(n) is int
                and all(isinstance(t, (list, tuple)) and len(t) == 2 and all(type(v) is int for v in t) for t in path)):
            return self._leap_bad()
        run = bool(args.get("run")) and self.sprints(a, {"run": True})
        for x, y in path:                          # (now, as it is said: a walk said next replaces it before it starts, and makes them)
            a.via.append((x, y, n, {"run": run}))
        if land is not None:
            a.via.append((None, None, n, {"land": land}))
        return self._leap_go(a, args)

    def _leap_go(self, a, args):
        steps, fall = yield from self.follow(a, args)
        return {"steps": steps, "z": self.height(a), **fall}

    def _leap_bad(self):
        from .entities import ActionError
        raise ActionError("bad_args", "leap: path [[x, y], ...] (up to 12 tiles), land (int or null), n (int)")
        yield

    def fly(self, a):
        """Make the flight at the head of a.via (Movement.follow), as far as it is said: -> (tiles made, what the
        landing did). Waits for the rest (LEAP_WAIT); one that does not hold is given up with the rest of the way."""
        if a.flying is None:
            a.flying, a.flying_n, a.flying_at = self.height(a), 0, self.tick
        steps = 0
        while True:
            if not a.via or len(a.via[0]) < 4:
                if self.tick - a.flying_at > sec(LEAP_WAIT):   # (never told where it came down)
                    break
                yield
                continue
            x, y, n, f = a.via[0]
            if "land" in f:
                z0, land = a.flying, f["land"]
                a.via.pop(0)
                a.flying = None
                if land - z0 > LEAP_TOP or land not in self.world.surfaces(a.x, a.y) or self.world.solid(a.x, a.y, land + 1):
                    break
                a.z, a.via_done = land, n
                self.arrive(a)
                return steps, self.fell(a, z0 - land)
            top = a.flying + LEAP_TOP
            if abs(x - a.x) + abs(y - a.y) != 1 or a.flying_n >= LEAP_TILES or not any(
                    s <= top and not self.world.solid(x, y, s + 1) and not self.world.solid(x, y, s + 2) for s in self.world.surfaces(x, y)):
                break
            while self.tick < a.ready:
                yield
            a.ready = self.tick + sec(self.stride(a, {"run": f["run"]}))
            a.x, a.y = x, y
            a.via.pop(0)
            a.flying_n += 1
            a.flying_at = self.tick
            steps += 1
        self.via_drop(a)                                   # (given up: down where it is)
        return steps, {}
