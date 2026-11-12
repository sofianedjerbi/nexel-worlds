"""Generated caves (cavegen.py): rooms and straight passages level in the rock, shut in all round, with one way out
onto dry ground through a notch."""

from megastructure import cavegen
from megastructure.gen import _dry, _hash, _land, col_surfaces, gen_cave, gen_chunk

SEED = 12


def caves():
    for cy in range(-8, 8):
        for cx in range(-8, 8):
            c = cavegen._cached(SEED, cx, cy, _land, _hash, _dry)
            if c:
                yield c


def test_caves_are_level_roofed_sealed_and_open_onto_dry_ground():
    found = list(caves())
    assert len(found) >= 8
    for c in found:
        z = min(c.values())
        assert set(c.values()) <= {z, z + cavegen.OPEN} and len(c) >= 60          # one flat floor; a room at the least
        roofed = {t for t, v in c.items() if v == z}
        assert all(_land(SEED, *t) >= z + cavegen.ROCK for t in roofed)             # under the rock
        for (x, y) in roofed:                                                      # shut in: rock, or more cave, all round
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                n = (x + dx, y + dy)
                assert n in c or _land(SEED, *n) >= z + cavegen.ROCK - 1, (x, y, n)
        outs = [(x + dx, y + dy) for (x, y) in c for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
                if (x + dx, y + dy) not in c and _land(SEED, x + dx, y + dy) == z]
        assert outs and all(_dry(SEED, *t) for t in outs)                           # a way out, on dry ground, level with it


def test_a_cave_is_empty_cells_in_the_generated_land():
    c = next(caves())
    z = min(c.values())
    x, y = next(t for t, v in c.items() if v == z)
    floor, over = gen_cave(SEED, x, y, _land(SEED, x, y))
    assert floor == z and over >= cavegen.ROCK
    col = gen_chunk(SEED, x >> 5, y >> 5)[2][(y & 31) * 32 + (x & 31)]
    assert col_surfaces(col) == [z, z + over]                                       # its floor, and the hill over it
    ox, oy = next(t for t, v in c.items() if v > z)                                 # the notch: cut down to the floor
    assert gen_cave(SEED, ox, oy, _land(SEED, ox, oy)) == (z, 0)
