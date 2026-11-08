"""Deterministic generation of an endless archipelago from a seed (pure Python value noise).

Everything is a pure function of (seed, x, y), so chunks can be generated in any order and
regenerated identically.
"""

import math

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


def gen_tile(seed: int, x: int, y: int) -> tuple[int, int]:
    # big calm islands; the spawn area around the origin is lifted into an open meadow
    d = math.hypot(x, y)
    elev = fbm(seed, x, y, 90, 1) + max(0.0, 0.25 - d / 400)
    if elev < 0.34:
        return G["deep_water"], B["none"]
    if elev < 0.41:
        return G["water"], B["none"]
    if elev < 0.425:
        return G["dirt"], B["none"]  # thin sandy shore
    meadow = d < 18  # keep the spawn clearing empty
    ground = G["grass"] if fbm(seed, x, y, 30, 2) > 0.3 else G["dirt"]
    if meadow:
        return G["grass"], B["none"]

    grove = fbm(seed, x, y, 48, 4)
    stones = fbm(seed, x, y, 34, 5)
    # groves: trees on a 2x2 jittered grid, denser toward the grove centre
    cand, roll = _picked(seed, x, y, 2, 11)
    if grove > 0.6 and cand and roll < min(0.95, (grove - 0.6) * 6):
        return G["grass"], (B["fruit_tree"] if _hash(seed, x, y, 29) < 0.15 else B["tree"])
    # grove edges: berry bushes and the odd hedge, sparse
    cand4, roll4 = _picked(seed, x, y, 4, 13)
    if 0.56 < grove <= 0.61 and cand4:
        if roll4 < 0.35:
            return G["grass"], B["berry_bush"]
        if roll4 < 0.42:
            return G["grass"], B["thicket"]
    if grove > 0.6 and _hash(seed, x, y, 17) < 0.025:
        return G["grass"], B["mushroom"]
    # small boulder fields, a few with ore
    if stones > 0.76 and cand and roll < 0.6:
        return ground, (B["ore"] if _hash(seed, x, y, 19) < 0.18 else B["rock"])
    # lone features scattered over open meadow
    if ground == G["grass"] and fbm(seed, x, y, 14, 6) > 0.66 and _hash(seed, x, y, 31) < 0.22:
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


def gen_chunk(seed: int, cx: int, cy: int) -> tuple[bytearray, bytearray]:
    ground = bytearray(CHUNK * CHUNK)
    block = bytearray(CHUNK * CHUNK)
    bx, by = cx * CHUNK, cy * CHUNK
    for ly in range(CHUNK):
        for lx in range(CHUNK):
            g, b = gen_tile(seed, bx + lx, by + ly)
            i = ly * CHUNK + lx
            ground[i] = g
            block[i] = b
    return ground, block
