"""What a build is and what it holds (#42): one reading of a room for the shelter rule, the AI player's judge and any
screen that shows a player their house. Facts only, no score: whether it is closed and where it is open, its doors and
walls, how much of it is roofed, the light and the things inside. Pure: the world in, a dict out."""

from collections import Counter

from ..tiles import BLOCKS, DIRS
from .wild import LIGHT, LIGHT_R

ENCLOSE = ("wood_wall", "stone_wall", "door", "gate")      # what closes a room (shelter)
CAP = 160                                                   # tiles: a space larger than this is the open land
SIDE, COMPACT = 14, 0.6                                     # a room is at most this wide and fills this share of its box
_SOLID = {b.name: b.solid for b in BLOCKS}


def inside(world, x, y) -> set | None:
    """The tiles a flood fill from (x, y) reaches without crossing an ENCLOSE piece, or None: it ran past CAP."""
    seen, stack = {(x, y)}, [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if len(seen) > CAP:
            return None
        for dx, dy in DIRS.values():
            n = (cx + dx, cy + dy)
            if n not in seen and world.block(*n) not in ENCLOSE:
                seen.add(n)
                stack.append(n)
    return seen


def compact(tiles: set) -> bool:
    """Room-shaped: at most SIDE a side, and filling COMPACT of its box (the client's roof rule too)."""
    xs, ys = [p[0] for p in tiles], [p[1] for p in tiles]
    w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    return w <= SIDE and h <= SIDE and len(tiles) >= COMPACT * w * h


def report(world, x, y) -> dict:
    """The build around (x, y). Closed: {"closed": True, "area", "box": (w, h), "doors", "walls": {piece: n},
    "roofed": share of the inside under a roof or land, "lights": light sources inside or within LIGHT_R of its middle,
    "contents": {block: n} inside}. Open: {"closed": False}."""
    tiles = inside(world, x, y)
    if tiles is None or not compact(tiles):
        return {"closed": False}
    edge = {}
    for cx, cy in tiles:
        for dx, dy in DIRS.values():
            n = (cx + dx, cy + dy)
            if n not in tiles:
                edge[n] = world.block(*n)
    pieces = Counter(edge.values())
    xs, ys = [p[0] for p in tiles], [p[1] for p in tiles]
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    contents = Counter(b for b in (world.block(*p) for p in tiles) if b != "none")
    lights = sum(1 for (px, py) in _around(mx, my, LIGHT_R) if world.block(px, py) in LIGHT)
    return {"closed": True, "area": len(tiles), "box": (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1),
            "doors": sum(n for k, n in pieces.items() if not _SOLID.get(k, True)),
            "walls": {k: n for k, n in pieces.items() if _SOLID.get(k, True)},
            "roofed": round(sum(1 for p in tiles if world.roof(*p)) / len(tiles), 3),
            "lights": lights, "contents": dict(contents)}


def _around(mx, my, r):
    return [(int(mx) + dx, int(my) + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if dx * dx + dy * dy <= r * r]
