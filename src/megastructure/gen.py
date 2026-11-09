"""Deterministic generation of an endless archipelago from a seed (pure Python value noise).

Everything is a pure function of (seed, x, y), so chunks can be generated in any order and
regenerated identically.
"""

import math

from .layers import LAYER, depth
from .tiles import B, G

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


RAMP = 0x10          # in a level byte: stairs down to the south from this tile (with its east or west twin)
PEAK = 3             # the highest level: bare stone, no stairs up


def _elev(seed: int, x: int, y: int) -> float:
    return fbm(seed, x, y, 90, 1) + max(0.0, 0.25 - math.hypot(x, y) / 400)


def gen_level(seed: int, x: int, y: int) -> int:
    """Height, 0-3: terraced hills inland, rising to stone peaks; shores, water and the spawn meadow stay low."""
    if depth(x):
        return 0                     # underground is flat (its walls are cave rock)
    d = math.hypot(x, y)
    elev = _elev(seed, x, y)
    if d < 14 or elev < 0.46:
        return 0
    h = fbm(seed, x, y, 56, 61, octaves=2) + (elev - 0.46) * 0.6     # two octaves: long, straight-ish cliffs
    return 0 if h < 0.65 else 1 if h < 0.73 else 2 if h < 0.81 else PEAK    # ~65% low, 15% / 12% terraces, 8% peaks


def _ramp_fits(seed: int, x: int, y: int, lv) -> bool:
    up = lv(x, y)
    if not 1 <= up < PEAK or any(lv(x + i, y) != up for i in (-1, 1, 2)) or any(lv(x + i, y + 1) != up - 1 for i in (0, 1)):
        return False
    if any(lv(x + i, y - j) != up for i in (-1, 0, 1, 2) for j in (1, 2)):
        return False                 # the hilltop behind the slope is clear of the rim, so you can walk on from it
    return all(gen_tile(seed, x + i, y + 1, up - 1)[1] == B["none"] for i in (0, 1))


def _is_ramp(seed: int, x: int, y: int, lv) -> bool:
    """Stairs: a pair of tiles (x, x+1) along a south cliff that goes on either side (the stairs are cut into it),
    the landing below clear. Rare: one cliff row in five, one slope per 24 tiles of it, the first place that fits from a hashed start;
    (x, x+1) stays inside its stretch, so pairs never touch. `lv(x, y)` gives levels."""
    if (y + int(_hash(seed, x // 24, 0, 73) * 5)) % 5:
        return False                             # rare: only one cliff row in five may have slopes...
    cell = x // 24
    start = int(_hash(seed, cell, y, 71) * 22)
    for k in range(22):                          # ...and one per 24 tiles of it ((x, x+1) never touch the next)
        cx = cell * 24 + (start + k) % 22
        if _ramp_fits(seed, cx, y, lv):
            return cx == x
    return False


def ramp_at(seed: int, x: int, y: int, lv) -> bool:
    """This tile is either half of a pair of stairs."""
    return _is_ramp(seed, x, y, lv) or _is_ramp(seed, x - 1, y, lv)


def gen_cave(seed: int, x: int, y: int, d: int) -> tuple[int, int]:
    """Underground, `d` levels down: solid rock with caves, larger the deeper you go, ore richer too, the odd
    mushroom on a cave floor."""
    lx, s = x - d * LAYER, seed + 7919 * d
    open_ = fbm(s, lx, y, 7 + 4 * min(d, 8), 91) > 0.63 - 0.004 * min(d, 8)
    if open_:
        return G["cave_floor"], B["mushroom"] if _hash(s, lx, y, 93) < .005 else B["none"]
    return G["cave_floor"], B["ore"] if _hash(s, lx, y, 92) < .03 + .015 * min(d, 10) else B["cave_wall"]


def gen_tile(seed: int, x: int, y: int, level: int = 0) -> tuple[int, int]:
    d0 = depth(x)
    if d0:
        return gen_cave(seed, x, y, d0)
    # big calm islands; the spawn area around the origin is lifted into an open meadow
    d = math.hypot(x, y)
    elev = _elev(seed, x, y)
    if elev < 0.34:
        return G["deep_water"], B["none"]
    if elev < 0.41:
        return G["water"], B["none"]
    if elev < 0.425:
        return G["dirt"], B["none"]  # thin sandy shore
    if level >= PEAK:                # stone peaks: boulders and ore, nothing grows
        cand, roll = _picked(seed, x, y, 3, 81)
        return G["grass"], (B["ore"] if roll < 0.25 else B["rock"]) if cand and roll < 0.55 else B["none"]
    meadow = d < 6  # a small clearing at spawn; trees and bushes are in view from the start
    ground = G["grass"] if level or fbm(seed, x, y, 30, 2) > 0.3 else G["dirt"]   # hills are grassy
    if meadow:
        return G["grass"], B["none"]

    grove = fbm(seed, x, y, 48, 4)
    stones = fbm(seed, x, y, 34, 5)
    # groves: trees on a 2x2 jittered grid, denser toward the grove centre
    cand, roll = _picked(seed, x, y, 2, 11)
    if grove > 0.6 and cand and roll < min(0.95, (grove - 0.6) * 6):
        return G["grass"], (B["fruit_tree"] if _hash(seed, x, y, 29) < 0.15 else B["tree"])
    # grove edges: berry bushes, sparse
    cand4, roll4 = _picked(seed, x, y, 4, 13)
    if 0.56 < grove <= 0.61 and cand4 and roll4 < 0.35:
        return G["grass"], B["berry_bush"]
    if grove > 0.6 and _hash(seed, x, y, 17) < 0.025:
        return G["grass"], B["mushroom"]
    # small boulder fields, a few with ore
    if stones > 0.76 and cand and roll < 0.6:
        return ground, (B["ore"] if _hash(seed, x, y, 19) < 0.18 else B["rock"])
    # lone features scattered over open meadow
    if ground == G["grass"] and fbm(seed, x, y, 14, 6) > 0.68 and _hash(seed, x, y, 31) < 0.16:
        return ground, B["flower"]
    cand11, roll11 = _picked(seed, x, y, 11, 23)
    if cand11:
        if roll11 < 0.18:
            return ground, B["tree"]
        if roll11 < 0.22:
            return ground, B["rock"]
        if roll11 < 0.26:
            return ground, B["berry_bush"]
    return ground, B["none"]


def gen_chunk(seed: int, cx: int, cy: int) -> tuple[bytearray, bytearray, bytearray]:
    """Ground, blocks and levels (with the RAMP flag) of one chunk."""
    ground = bytearray(CHUNK * CHUNK)
    block = bytearray(CHUNK * CHUNK)
    level = bytearray(CHUNK * CHUNK)
    bx, by = cx * CHUNK, cy * CHUNK
    memo = {}

    def lv(x, y):                    # levels, including a margin around the chunk (stairs look at their neighbours)
        v = memo.get((x, y))
        if v is None:
            v = memo[(x, y)] = gen_level(seed, x, y)
        return v

    for ly in range(CHUNK):
        for lx in range(CHUNK):
            x, y, i = bx + lx, by + ly, ly * CHUNK + lx
            ramp = ramp_at(seed, x, y, lv)
            g, b = gen_tile(seed, x, y, lv(x, y))
            rim = lv(x, y) and any(lv(x + dx, y + dy) < lv(x, y) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            ground[i], block[i] = g, B["none"] if ramp or rim else b     # nothing grows on a slope or a hill's rim
            level[i] = lv(x, y) | (RAMP if ramp else 0)
    return ground, block, level
