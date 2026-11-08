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


def gen_tile(seed: int, x: int, y: int) -> tuple[int, int]:
    # islands: elevation, lifted near the origin so everyone starts on land
    d = math.hypot(x, y)
    elev = fbm(seed, x, y, 56, 1) + max(0.0, 0.22 - d / 300)
    if elev < 0.36:
        return G["deep_water"], B["none"]
    if elev < 0.44:
        return G["water"], B["none"]
    moist = fbm(seed, x, y, 40, 2)
    rocky = fbm(seed, x, y, 22, 3)
    r = _hash(seed, x, y, 7)
    beach = elev < 0.47
    ground = G["dirt"] if beach or moist < 0.36 else G["grass"]
    if beach:
        return ground, (B["rock"] if r < 0.015 else B["none"])
    if rocky > 0.66:  # rocky outcrops, with ore veins inside
        if rocky > 0.72 and r < 0.12:
            return G["dirt"], B["ore"]
        return G["dirt"], (B["rock"] if r < 0.8 else B["none"])
    forest = max(0.0, moist - 0.5) * 1.6
    if r < forest:
        return ground, B["tree"]
    if r < forest + 0.025:
        return ground, B["berry_bush"]
    if r < forest + 0.035 + forest * 0.08:
        return ground, B["thicket"]
    if r < forest + 0.045 + forest * 0.1:
        return ground, B["mushroom"] if moist > 0.5 else B["none"]
    if r < forest + 0.05:
        return ground, B["rock"]
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
