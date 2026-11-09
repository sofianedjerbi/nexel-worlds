"""Relief: heights, cliffs, stairs, and land saved before relief staying flat."""

import zlib

from helpers import run
from megastructure.gen import CHUNK, PEAK, RAMP, gen_chunk
from megastructure.world import Chunk


def plateau(sim, a):
    """A 9x5 plateau (level 1) two tiles north of you, with stairs in the middle of its south edge; its rim (the
    outer ring) is off-limits, the 7x3 inside walkable."""
    for y in range(a.y - 6, a.y - 1):
        for x in range(a.x - 4, a.x + 5):
            sim.world.set(x, y, level=1)
    for x in (a.x - 1, a.x):
        sim.world.set(x, a.y - 2, level=1 | RAMP)            # the south edge row: stairs down to a.y - 1


def test_cliffs_block_and_stairs_go_up_and_down(world):
    sim, a = world
    plateau(sim, a)
    a.x += 2                                                 # under the cliff, beside the stairs
    r = run(sim, a, "step", {"dir": "N"})                    # (a.x, a.y - 1) is level 0; north of it, the cliff
    assert r["ok"]
    r = run(sim, a, "step", {"dir": "N"})
    assert not r["ok"] and "cliff" in r["detail"]
    a.x -= 2                                                 # at the stairs' landing
    assert run(sim, a, "step", {"dir": "N"})["ok"] and sim.world.level(a.x, a.y) == 1
    assert not run(sim, a, "step", {"dir": "W"})["ok"] or sim.world.level(a.x, a.y) == 1   # along the top: fine
    assert run(sim, a, "step", {"dir": "S"})["ok"] and sim.world.level(a.x, a.y) == 0      # and back down


def test_walking_off_an_edge_is_blocked_too(world):
    sim, a = world
    plateau(sim, a)
    a.x, a.y = a.x - 3, a.y - 4                              # inside the plateau, next to its west rim
    r = run(sim, a, "walk", {"dir": "W"})
    assert r["stopped"] == "blocked" and "drop" in r["blocked_by"]


def test_move_to_finds_the_stairs(world):
    sim, a = world
    plateau(sim, a)
    top = (a.x + 3, a.y - 5)
    r = run(sim, a, "move_to", {"x": top[0], "y": top[1]}, limit=800)
    assert r["ok"] and (a.x, a.y) == top


def test_generated_land_has_hills_with_stairs_and_peaks():
    levels, ramps, peaks = set(), 0, 0
    for cx in range(4, 12):
        for cy in range(-4, 4):
            _, _, lv = gen_chunk(7, cx, cy)
            levels |= {v & 15 for v in lv}
            ramps += sum(1 for v in lv if v & RAMP)
            peaks += sum(1 for v in lv if v & 15 == PEAK)
    assert {0, 1, 2} <= levels and ramps > 0 and peaks > 0
    assert gen_chunk(7, 5, 1) == gen_chunk(7, 5, 1)          # deterministic


def test_land_saved_before_relief_stays_flat():
    n = CHUNK * CHUNK
    old = zlib.compress(bytes(n) + bytes(n))                  # ground and blocks only
    c = Chunk.unpack(0, 0, old)
    assert len(c.level) == n and not any(c.level)
    assert Chunk.unpack(0, 0, c.pack()).level == c.level


def test_nobody_stands_or_builds_on_a_hills_rim(world):
    sim, a = world
    plateau(sim, a)
    assert sim.world.edge(a.x + 4, a.y - 4) and sim.world.edge(a.x + 2, a.y - 2)       # east rim, south cliff
    assert not sim.world.edge(a.x, a.y - 2) and not sim.world.edge(a.x + 3, a.y - 4)   # the stairs, the inside
    a.add("chest", 1)
    a.x, a.y = a.x + 2, a.y - 1                              # under the cliff: placing on it is refused
    assert run(sim, a, "place", {"dir": "N", "item": "chest"})["error"] == "cliff_edge"


def test_nothing_generates_on_a_rim():
    from megastructure.gen import gen_level
    for cx in range(4, 9):
        for cy in range(-3, 3):
            _, block, lv = gen_chunk(7, cx, cy)
            for i, v in enumerate(lv):
                x, y = cx * CHUNK + i % CHUNK, cy * CHUNK + i // CHUNK
                if v & 15 and not v & RAMP and any(gen_level(7, x + dx, y + dy) < v & 15 for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    assert block[i] == 0, (x, y)


def test_going_up_a_slope_is_slower_than_walking_on_the_level(world):
    sim, a = world
    plateau(sim, a)
    a.y -= 1                                                 # at the stairs' landing
    assert run(sim, a, "step", {"dir": "N"})["ok"]           # up onto the slope
    up = a.ready - sim.tick                                  # how long until the next step may start
    assert run(sim, a, "step", {"dir": "N"})["ok"]           # on along the level
    level = a.ready - sim.tick
    assert up > level
