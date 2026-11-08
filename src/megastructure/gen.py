"""Deterministic generation of the endless structure from a seed.

The world is laid out on 8x8 cells. Each cell is a hall, a corridor junction, solid mass,
a void shaft (crossed by grating bridges) or a coolant cistern. Cell borders are walls with
doorways. Everything is a pure function of (seed, x, y), so chunks can be generated in any
order and regenerated identically.
"""

import math
from functools import lru_cache

from .tiles import B, G

CHUNK = 32
CELL = 8


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


@lru_cache(maxsize=65536)
def cell_kind(seed: int, cx: int, cy: int) -> str:
    if abs(cx) <= 2 and abs(cy) <= 2:
        return "hall"  # friendly spawn district
    density = fbm(seed, cx, cy, 6, 11)
    shaft = fbm(seed, cx, cy, 9, 12)
    r = _hash(seed, cx, cy, 13)
    if shaft < 0.28:
        return "void"
    if density > 0.68:
        return "mass"
    if r < 0.05:
        return "cistern"
    if density < 0.42 or r < 0.35:
        return "hall"
    return "corridor"


def _edge_gap(seed, cx, cy, side) -> tuple[float, int]:
    """(openness roll, doorway offset) of the west ('W') or north ('N') edge of a cell."""
    salt = 21 if side == "W" else 22
    return _hash(seed, cx, cy, salt), 2 + int(_hash(seed, cx, cy, salt + 10) * 3)


OPEN = ("hall", "corridor", "cistern")


def _border(seed, kind, other, cx, cy, side, along) -> bool:
    """True if this border tile is a wall."""
    if kind == "void" and other == "void":
        return False
    if kind in OPEN and other in OPEN:
        roll, gap = _edge_gap(seed, cx, cy, side)
        if roll < 0.3:
            return False  # fully open edge
        return not (gap <= along <= gap + 1)
    if "mass" in (kind, other):
        return True
    # void next to open: low railing of structure with a bridge gap
    roll, gap = _edge_gap(seed, cx, cy, side)
    return not (gap <= along <= gap + 1 and roll < 0.7)


def gen_tile(seed: int, x: int, y: int) -> tuple[int, int]:
    cx, cy = x // CELL, y // CELL
    lx, ly = x - cx * CELL, y - cy * CELL
    kind = cell_kind(seed, cx, cy)
    r = _hash(seed, x, y, 7)
    damp = fbm(seed, x, y, 20, 2)

    # walls on the west/north border of each cell (shared with the neighbour)
    if lx == 0 or ly == 0:
        if lx == 0 and ly == 0:
            return G["deck"], B["structure"]  # pillars at every corner
        if lx == 0:
            other, side, along = cell_kind(seed, cx - 1, cy), "W", ly
        else:
            other, side, along = cell_kind(seed, cx, cy - 1), "N", lx
        if _border(seed, kind, other, cx, cy, side, along):
            if r < 0.12:
                return G["deck"], B["conduit"]
            return G["deck"], B["structure"]
        if kind == "void" or other == "void":
            return G["grating"], B["none"]
        return (G["moss"] if damp > 0.6 else G["deck"]), B["none"]

    if kind == "mass":
        if r < 0.07:
            return G["deck"], B["node"]
        if r < 0.10:
            return G["deck"], B["conduit"]
        return G["deck"], B["structure"]
    if kind == "void":
        # bridges of grating cross the shaft through its middle
        bridge_x = _hash(seed, cx, cy, 31) < 0.5
        if (bridge_x and ly in (3, 4)) or (not bridge_x and lx in (3, 4)):
            return G["grating"], B["none"]
        return G["void"], B["none"]
    if kind == "cistern":
        if 2 <= lx <= 6 and 2 <= ly <= 6:
            return G["coolant"], B["none"]
        return G["grating"], B["none"]

    ground = G["moss"] if damp > 0.55 else (G["grating"] if r > 0.93 else G["deck"])
    if kind == "corridor":
        # a cross-shaped junction; the rest is dense structure with conduits
        if not (3 <= lx <= 5 or 3 <= ly <= 5):
            return G["deck"], (B["conduit"] if r < 0.15 else B["structure"])
    if lx == 4 and ly == 4 and kind == "hall" and _hash(seed, cx, cy, 41) < 0.4:
        return G["deck"], B["structure"]  # central pillar
    salvage = fbm(seed, x, y, 30, 3)
    heap_p = max(0.0, salvage - 0.45) * 0.8
    if r < heap_p:
        return ground, B["scrap_heap"]
    lichen_p = 0.12 if damp > 0.55 else 0.02
    if r < heap_p + lichen_p:
        return ground, B["lichen"]
    if r < heap_p + lichen_p + 0.03 and (lx in (1, 7) or ly in (1, 7)):
        return ground, B["terminal"]
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
