"""Caves, laid out: rooms and straight passages cut level into the rock of the hills, with a mouth where a passage
comes out onto the ground. (Not noise: a cave you can read. Flat floor, two tiles wide at the least, fully under the
hill but for its mouth.)

The world is cut into CELL x CELL squares; a square whose hills are high enough holds one cave, worked out from the
seed alone (so any tile can ask). A layout is {(x, y): floor height}."""

from functools import lru_cache

CELL = 40          # tiles: a cave a square at the most
REACH = 26         # how far a passage may run to find the open air
ROCK = 3           # layers of hill needed over a cave's floor where it is dug
_DIRS = ((0, 1), (1, 0), (-1, 0), (0, -1))
OPEN = 100         # added to a tile's floor in a layout: cut open to the sky there (the notch before a mouth)


def layout(seed: int, cx: int, cy: int, level, rnd, dry) -> dict:
    """The cave of square (cx, cy), or {}. level(seed, x, y): the land's height; rnd(seed, x, y, salt): a number 0-1;
    dry(seed, x, y): land you can stand on (not water)."""
    land, level = level, lambda x, y: land(seed, x, y)
    r = lambda salt: rnd(seed, cx, cy, 700 + salt)
    if r(0) > 0.7:
        return {}
    x0, y0 = cx * CELL, cy * CELL
    for attempt in range(8):                                  # a spot well up in a hill, and a way straight out of it
        hx, hy = x0 + 8 + int(r(10 + attempt) * (CELL - 16)), y0 + 8 + int(r(20 + attempt) * (CELL - 16))
        top = level(hx, hy)
        if top < ROCK + 2:
            continue
        for k in range(4):
            dx, dy = _DIRS[(k + int(r(30 + attempt) * 4)) % 4]
            run = next((n for n in range(3, REACH) if level(hx + dx * n, hy + dy * n) <= top - ROCK), None)
            if run is None:
                continue
            floor = level(hx + dx * run, hy + dy * run)       # the ground it comes out onto: the cave is level with it
            out = [(hx + dx * (run + n) - dy * side, hy + dy * (run + n) + dx * side) for n in (0, 1) for side in (0, 1)]
            if any(level(*t) != floor or not dry(seed, *t) for t in out):
                continue                                      # (onto water, or a slope: not a way out)
            cave, w, h = {}, 3 + int(r(40) * 3), 2 + int(r(41) * 3)
            if not room(cave, hx, hy, w, h, floor, level):
                continue                                      # (the hill is too thin for a room here)
            edge = (w if dx else h) + 3                       # the passage stays under the rock a way past the room
            if any(level(hx + dx * n - dy * side, hy + dy * n + dx * side) < floor + ROCK for n in range(edge) for side in (0, 1)):
                continue
            passage(cave, hx, hy, dx, dy, run, floor, level, mouth=True)
            sx, sy = -dy, dx                                  # a second room, off to one side, joined by a passage
            if r(42) < 0.5:
                sx, sy = -sx, -sy
            far = 7 + int(r(43) * 7)
            if all(level(hx + sx * n, hy + sy * n) >= floor + ROCK for n in range(far + 3)):
                side = dict(cave)
                passage(side, hx, hy, sx, sy, far, floor, level)
                if room(side, hx + sx * far, hy + sy * far, 2 + int(r(44) * 2), 2 + int(r(45) * 2), floor, level):
                    cave = side
            if sealed(cave, set(out), floor, level, (hx, hy)):
                return cave
    return {}


def sealed(cave: dict, out: set, floor: int, level, start) -> bool:
    """Is the cave shut in the rock all round but for its way out (no wall broken through onto lower ground beside
    it), and does it hold together from its room to that way out?"""
    for (x, y) in cave:
        for dx, dy in _DIRS:
            n = (x + dx, y + dy)
            if cave[(x, y)] < OPEN and n not in cave and n not in out and level(*n) < floor + ROCK - 1:
                return False                                  # (a roofed tile with low ground beside it: a hole in its side)
    seen, stack = {start}, [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in _DIRS:
            n = (x + dx, y + dy)
            if n in out:
                return True
            if n in cave and n not in seen:
                seen.add(n)
                stack.append(n)
    return False


def room(cave: dict, x: int, y: int, w: int, h: int, floor: int, level) -> bool:
    """A room 2w+1 by 2h+1 round (x, y), if the hill has rock enough over all of it (and a tile round it)."""
    if any(level(x + i, y + j) < floor + ROCK for j in range(-h - 1, h + 2) for i in range(-w - 1, w + 2)):
        return False
    for j in range(-h, h + 1):
        for i in range(-w, w + 1):
            cave.setdefault((x + i, y + j), floor)
    return True


def passage(cave: dict, x: int, y: int, dx: int, dy: int, n: int, floor: int, level, mouth: bool = False):
    """A passage two tiles wide from (x, y), n tiles along (dx, dy). Toward its mouth the hill thins out over it: from
    where either of its two tiles has less than ROCK layers left, it is an open cut down to the floor (OPEN: a notch
    through the slope, both tiles together), so you walk in on the level and the cave opens in one face, ROCK high or
    more, at the back of the notch."""
    cut = False
    for k in range(n):
        pair = [(x + dx * k - dy * side, y + dy * k + dx * side) for side in (0, 1)]
        if any(level(*t) < floor + ROCK for t in pair):
            if not mouth:
                return                                        # (the hill gives out: the passage ends here)
            cut = True
        for t in pair:
            if level(*t) > floor and t not in cave:
                cave[t] = floor + OPEN if cut else floor


@lru_cache(maxsize=512)
def _cached(seed: int, cx: int, cy: int, level, rnd, dry) -> dict:
    return layout(seed, cx, cy, level, rnd, dry)


def floor_at(seed: int, x: int, y: int, level, rnd, dry) -> int | None:
    """The floor of the cave on (x, y), if one is dug there (+ OPEN where it is cut open to the sky). (A cave may
    reach into the squares round its own.)"""
    cx, cy = x // CELL, y // CELL
    for j in (0, -1, 1):
        for i in (0, -1, 1):
            z = _cached(seed, cx + i, cy + j, level, rnd, dry).get((x, y))
            if z is not None:
                return z
    return None
