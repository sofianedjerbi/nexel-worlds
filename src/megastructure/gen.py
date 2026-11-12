"""Deterministic generation of an endless archipelago from a seed (pure Python value noise).

Everything is a pure function of (seed, x, y), so chunks can be generated in any order and
regenerated identically.
"""

import math
from array import array
from functools import lru_cache

from . import cavegen
from .tiles import B, G

# The world is cells, solid or empty. A tile's column is its 32 cells from the bottom (LOW) up, a bit each, set
# where the cell is solid; cell z is the block whose top is at height z, so land h high is solid up to cell h (0: sea
# level). Nothing else is kept about relief: a cave is empty cells with solid ones over them, a pit a column dug low.
LOW, HIGH = -16, 15


def col_solid(level: int) -> int:
    """A plain column: solid up to `level`."""
    return (1 << (max(LOW, min(HIGH, level)) - LOW + 1)) - 1


def col_cave(floor: int, head: int, top: int) -> int:
    """Land `top` high with `head` cells empty over a floor at `floor`."""
    return col_solid(top) & ~(col_solid(min(floor + head, top - 1)) ^ col_solid(floor)) if top > floor + 1 and head > 0 else col_solid(floor)


def col_top(col: int) -> int:
    """The highest solid cell: the land as seen from above."""
    return col.bit_length() - 1 + LOW


def col_floor(col: int) -> int:
    """The lowest ground: the top of the solid cells standing on the bottom."""
    return (~col & (col + 1)).bit_length() - 2 + LOW


def col_surfaces(col: int) -> list[int]:
    """Every height you can stand at in this column: a solid cell with an empty one over it. Lowest first."""
    tops = col & ~(col >> 1)
    return [z + LOW for z in range(tops.bit_length()) if tops >> z & 1]

CHUNK = 32


def _hash(seed: int, x: int, y: int, salt: int) -> float:
    h = (x * 374761393 + y * 668265263 + seed * 2246822519 + salt * 3266489917) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 0xFFFFFFFF


def _smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def value_noise(seed: int, x: float, y: float, scale: float, salt: int) -> float:
    fx, fy = x / scale, y / scale
    x0, y0 = math.floor(fx), math.floor(fy)
    tx, ty = _smooth(fx - x0), _smooth(fy - y0)
    a = _hash(seed, x0, y0, salt)
    b = _hash(seed, x0 + 1, y0, salt)
    c = _hash(seed, x0, y0 + 1, salt)
    d = _hash(seed, x0 + 1, y0 + 1, salt)
    top = a + (b - a) * tx
    return top + ((c + (d - c) * tx) - top) * ty


def fbm(seed: int, x: float, y: float, scale: float, salt: int, octaves: int = 3) -> float:
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * value_noise(seed, x, y, scale / (2**o), salt + o * 101)
        norm += amp
        amp *= 0.5
    return total / norm


def _picked(seed: int, x: int, y: int, cell: int, salt: int) -> tuple[bool, float]:
    """Jittered grid: exactly one tile per `cell`×`cell` square is a candidate, so features keep their
    distance from each other (no clumps, no tree touching tree). Returns (is candidate, roll)."""
    cx, cy = x // cell, y // cell
    k = int(_hash(seed, cx, cy, salt) * cell * cell)
    return (x - cx * cell) + (y - cy * cell) * cell == k, _hash(seed, cx, cy, salt + 1)


PEAK = 5             # from this level up: bare stone (the mountains)
TOP = 12             # the highest level


def _elev(seed: int, x: int, y: int) -> float:
    return fbm(seed, x, y, 90, 1) + max(0.0, 0.25 - math.hypot(x, y) / 400)


def _mount(seed: int, x: int, y: int) -> float:
    """Where the mountain ranges are: long ridges (two octaves, then sharpened), only well inland."""
    return fbm(seed, x, y, 150, 401, octaves=2)


def river(seed: int, x: int, y: int) -> bool:
    """Rivers: a winding line where a broad noise crosses its middle, two or three tiles wide, from the hills to the
    sea; they cut canyons through the high ground."""
    if math.hypot(x, y) < 18:
        return False
    v = fbm(seed, x, y, 170, 501, octaves=2)
    return abs(v - 0.5) < 0.011 and _elev(seed, x, y) > 0.43


def biome(seed: int, x: int, y: int, level: int) -> str:
    """plains, forest, highlands, dry, swamp or mountain: from moisture, ruggedness and height."""
    if level >= PEAK:
        return "mountain"
    moist = fbm(seed, x, y, 230, 301, octaves=2)
    near = max(0.0, 1 - math.hypot(x, y) / 90)                  # round spawn: plains, a forest's edge
    moist = moist * (1 - near) + min(0.53, max(0.44, moist)) * near
    if moist > 0.6 and level == 0 and _elev(seed, x, y) < 0.5:
        return "swamp"
    if moist > 0.54:
        return "forest"
    if moist < 0.37:
        return "dry"
    if fbm(seed, x, y, 180, 311, octaves=2) > 0.56:
        return "highlands"
    return "plains"


def gen_level(seed: int, x: int, y: int) -> int:
    """Height, 0-12. The sea, shores and the spawn meadow stay low; inland the land rolls up in steps of one layer
    (you jump them), steeper in the highlands, and the mountain ranges rise in stone terraces to 12 with cliffs you
    have to dig through. Rivers cut down to the water."""
    d = math.hypot(x, y)
    elev = _elev(seed, x, y)
    if d < 14 or elev < 0.43 or river(seed, x, y):
        return 0
    inland = min(1.0, (elev - 0.43) / 0.12) * min(1.0, (d - 14) / 30)       # (rising from the shore, and from spawn)
    rugged = fbm(seed, x, y, 180, 311, octaves=2)
    roll = fbm(seed, x, y, 40, 61, octaves=3)                                 # rolling ground
    h = max(0.0, roll - 0.42) * (5 + 10 * max(0.0, rugged - 0.45))
    m = _mount(seed, x, y)
    if m > 0.58:                                                              # a range: up to the peaks
        h += (m - 0.58) * 70 + fbm(seed, x, y, 16, 71, octaves=2) * 2
    return max(0, min(TOP, int(h * inland)))


def gen_cave(seed: int, x: int, y: int, level: int) -> tuple[int, int]:
    """Caves (cavegen.py): rooms and straight passages cut level into the hills, a mouth where a passage comes out.
    (floor, land over it): a cave where ROCK layers or more lie over the floor, an open cut where less; (level, 0): no cave."""
    floor = cavegen.floor_at(seed, x, y, _land, _hash, _dry)
    if floor is None:
        return level, 0
    if floor >= cavegen.OPEN:
        return min(level, floor - cavegen.OPEN), 0
    return (floor, level - floor) if level - floor >= cavegen.ROCK else (min(level, floor), 0)


def _dry(seed: int, x: int, y: int) -> bool:
    """Land you can stand on: not the sea, its shore or a river."""
    return _elev(seed, x, y) >= 0.43 and not river(seed, x, y)


@lru_cache(maxsize=1 << 17)
def _land(seed: int, x: int, y: int) -> int:
    return gen_level(seed, x, y)


def gen_tile(seed: int, x: int, y: int, level: int = 0) -> tuple[int, int]:
    d = math.hypot(x, y)
    elev = _elev(seed, x, y)
    if elev < 0.34:                   # the sea, deeper the further out
        return G["abyss" if elev < 0.27 else "deep_water"], B["none"]
    if elev < 0.41 or (level == 0 and river(seed, x, y)):
        return G["mid_water" if elev < 0.375 else "water"], B["none"]
    if elev < 0.425:
        return G["dirt"], B["none"]  # thin sandy shore
    if d < 6:
        return G["grass"], B["none"]  # a small clearing at spawn; trees and bushes are in view from the start
    kind = biome(seed, x, y, level)
    cand, roll = _picked(seed, x, y, 2, 11)
    cand3, roll3 = _picked(seed, x, y, 3, 81)
    cand4, roll4 = _picked(seed, x, y, 4, 13)
    cand11, roll11 = _picked(seed, x, y, 11, 23)
    grove = fbm(seed, x, y, 48, 4)
    if kind == "mountain":            # stone: boulders and ore here and there, nothing grows
        cand5, roll5 = _picked(seed, x, y, 5, 83)
        if cand5 and roll5 < 0.45 and fbm(seed, x, y, 12, 84) > 0.45:
            return G["grass"], B["ore"] if roll5 < 0.15 else B["rock"]
        return G["grass"], B["none"]
    if kind == "swamp":               # pools, thickets, mushrooms
        if fbm(seed, x, y, 9, 41) > 0.6:
            return G["water"], B["none"]
        if cand4 and roll4 < 0.5:
            return G["grass"], B["thicket"] if roll4 < 0.3 else B["mushroom"]
        if cand11 and roll11 < 0.3:
            return G["grass"], B["tree"]
        return G["grass"], B["none"]
    if kind == "forest":              # trees close together, fruit, berries and mushrooms under them
        if cand and roll < 0.55 + 0.4 * max(0.0, grove - 0.5):
            return G["grass"], (B["fruit_tree"] if _hash(seed, x, y, 29) < 0.12 else B["tree"])
        if cand4 and roll4 < 0.3:
            return G["grass"], B["berry_bush"] if roll4 < 0.18 else B["mushroom"]
        return G["grass"], B["none"]
    if kind == "dry":                 # bare earth with patches of grass, stones, the odd lone tree
        ground = G["dirt"] if fbm(seed, x, y, 20, 2) > 0.5 else G["grass"]
        if cand4 and roll4 < 0.22:
            return ground, B["rock"] if roll4 < 0.16 else B["ore"]
        if cand11 and roll11 < 0.2:
            return ground, B["tree"] if roll11 < 0.12 else B["berry_bush"]
        return ground, B["none"]
    # plains and highlands: meadows, flowers, groves here and there, boulders up high
    ground = G["grass"] if level or fbm(seed, x, y, 30, 2) > 0.3 else G["dirt"]
    if grove > 0.62 and cand and roll < min(0.9, (grove - 0.62) * 6):
        return G["grass"], (B["fruit_tree"] if _hash(seed, x, y, 29) < 0.15 else B["tree"])
    if 0.58 < grove <= 0.63 and cand4 and roll4 < 0.35:
        return G["grass"], B["berry_bush"]
    if kind == "highlands" and cand3 and roll3 < 0.08:
        return ground, B["rock"]
    if fbm(seed, x, y, 34, 5) > 0.76 and cand and roll < 0.6:
        return ground, (B["ore"] if _hash(seed, x, y, 19) < 0.18 else B["rock"])
    if ground == G["grass"] and fbm(seed, x, y, 14, 6) > 0.66 and _hash(seed, x, y, 31) < 0.2:
        return ground, B["flower"]
    if cand11:
        if roll11 < 0.18:
            return ground, B["tree"]
        if roll11 < 0.22:
            return ground, B["rock"]
        if roll11 < 0.26:
            return ground, B["berry_bush"]
    return ground, B["none"]


def gen_chunk(seed: int, cx: int, cy: int) -> tuple[bytearray, bytearray, array]:
    """Ground, blocks and columns (the cells, solid or empty) of one chunk."""
    ground = bytearray(CHUNK * CHUNK)
    block = bytearray(CHUNK * CHUNK)
    cols = array("I", bytes(4 * CHUNK * CHUNK))        # (a column of cells a tile, 32 bits: col_solid...)
    bx, by = cx * CHUNK, cy * CHUNK
    memo = {}

    def cave(x, y):                  # (floor, rock over it), with a margin round the chunk (rims look at neighbours)
        v = memo.get((x, y))
        if v is None:
            v = memo[(x, y)] = gen_cave(seed, x, y, gen_level(seed, x, y))
        return v

    def lv(x, y):
        return cave(x, y)[0]

    for ly in range(CHUNK):
        for lx in range(CHUNK):
            x, y, i = bx + lx, by + ly, ly * CHUNK + lx
            floor, roof = cave(x, y)
            g, b = gen_tile(seed, x, y, floor + roof)
            if roof or floor != gen_level(seed, x, y):
                g, b = G["dirt"], B["mushroom"] if _hash(seed, x, y, 93) < .01 else B["none"]   # a cave's floor
            rim = lv(x, y) and any(lv(x + dx, y + dy) < lv(x, y) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            ground[i], block[i] = g, B["none"] if rim else b     # nothing grows on a hill's rim
            cols[i] = col_cave(floor, 2 if roof >= 3 else 1, floor + roof) if roof else col_solid(floor)
    return ground, block, cols
