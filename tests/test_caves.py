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


def test_the_showcase_is_built_and_newcomers_start_beside_it(tmp_path):
    """showcase.py: the demo's world. Every kind of entry is there, walkable from the field, and you start by it."""
    from megastructure import showcase
    from megastructure.sim import Simulation

    sim = Simulation(tmp_path / "w.sqlite", seed=SEED)
    showcase.build(sim)
    w = sim.world
    assert w.surfaces(-52, 54) == [0, 5] and w.surfaces(-52, 59) == [0, 5] and w.top(-52, 60) == 0    # a room, its south mouth
    assert w.surfaces(-27, 59) == [0, 5] and w.top(-26, 59) == 0 and w.top(-27, 60) == 0            # the outer corner: two faces
    assert w.surfaces(-35, 55) == [0, 5] and w.surfaces(-34, 56) == [0, 5] and w.top(-35, 56) == 0  # the inner corner
    assert w.top(-13, 51) == 0 and w.top(-13, 50) == 6                                              # the shaft
    assert w.surfaces(-55, 69) == [-3, 0] and [w.top(x, 68) for x in (-51, -50, -49, -48)] == [-3, -2, -1, 0]   # the hollow, its steps
    a = sim.login("newcomer", "t")
    assert max(abs(a.x - showcase.SPAWN[0]), abs(a.y - showcase.SPAWN[1])) <= 3 and sim.height(a) == 0
    sim.close()


def test_land_is_made_a_row_at_a_time_where_there_are_no_threads(tmp_path, monkeypatch):
    """The in-browser demo: prefetch starts a chunk, World.work goes on with it between ticks, and it is the same
    land as made in one go."""
    import time

    from megastructure import world as world_mod
    from megastructure.gen import gen_chunk
    from megastructure.sim import Simulation

    monkeypatch.setattr(world_mod, "THREADS", False)
    sim = Simulation(tmp_path / "w.sqlite", seed=SEED)
    w = sim.world
    assert not w.prefetch(40, 40) and (40, 40) not in w.chunks
    w.work(time.perf_counter())                                # (no time to spare: nothing more is made)
    w.tick += 10
    assert not w.prefetch(40, 40)                              # due, but not made yet: it waits, nothing stalls
    w.work(time.perf_counter() + 5)
    assert w.prefetch(40, 40) and bytes(w.chunks[(40, 40)].cols) == bytes(gen_chunk(SEED, 40, 40)[2])
    assert not w.prefetch(41, 40) and w.chunk(41, 40) is w.chunks[(41, 40)]     # asked for at once: finished on the spot
    sim.close()
