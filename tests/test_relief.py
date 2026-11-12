"""Relief: the land is cells, solid or empty. Heights; a jump up a layer, no higher; falling; digging cells out
(a step cut down, a tunnel, a pit); caves."""

import zlib

from helpers import run
from megastructure.gen import CHUNK, PEAK, col_cave, col_floor, col_solid, col_surfaces, col_top, gen_chunk
from megastructure.world import Chunk


def plateau(sim, a, h=1):
    """A 9x5 plateau (level h) two tiles north of you: its south edge row is a.y - 2."""
    for y in range(a.y - 6, a.y - 1):
        for x in range(a.x - 4, a.x + 5):
            sim.world.set(x, y, level=h)


def test_you_jump_up_a_layer_and_step_down(world):
    sim, a = world
    plateau(sim, a)
    assert run(sim, a, "step", {"dir": "N"})["ok"]                                   # under its south edge
    assert run(sim, a, "step", {"dir": "N"})["ok"] and sim.world.level(a.x, a.y) == 1   # a jump up
    assert run(sim, a, "step", {"dir": "N"})["ok"] and sim.world.level(a.x, a.y) == 1   # along the top
    assert run(sim, a, "step", {"dir": "S"})["ok"] and run(sim, a, "step", {"dir": "S"})["ok"]
    assert sim.world.level(a.x, a.y) == 0                                            # and back down
    c = sim.world                                            # animals don't jump: they keep to their level
    assert not c.can_step(a.x, a.y, a.x, a.y - 2) and c.can_step(a.x, a.y - 1, a.x, a.y - 2, hop=True)


def test_two_layers_up_is_a_wall_until_you_dig_into_it(world):
    sim, a = world
    plateau(sim, a, h=2)
    run(sim, a, "step", {"dir": "N"})
    r = run(sim, a, "step", {"dir": "N"})
    assert not r["ok"] and "wall" in r["detail"]
    a.add("pickaxe")
    r = run(sim, a, "dig", {"dir": "N", "with": "pickaxe"})          # the cell in front of you goes: a tunnel
    assert r["ok"] and sim.world.surfaces(a.x, a.y - 1) == [0, 2] and a.count("dirt") == 1
    assert run(sim, a, "step", {"dir": "N"})["ok"] and sim.height(a) == 0 and sim.in_cave(a)
    r = run(sim, a, "dig", {"dir": "N", "with": "pickaxe"})          # and on in, a cell at a time
    assert r["ok"] and run(sim, a, "step", {"dir": "N"})["ok"] and sim.in_cave(a)


def test_move_to_climbs_a_layer_at_a_time(world):
    sim, a = world
    plateau(sim, a)
    for y in range(a.y - 5, a.y - 3):
        for x in range(a.x - 1, a.x + 2):
            sim.world.set(x, y, level=2)                     # a second terrace on top
    top = (a.x, a.y - 5)
    r = run(sim, a, "move_to", {"x": top[0], "y": top[1]}, limit=800)
    assert r["ok"] and (a.x, a.y) == top and sim.world.level(*top) == 2


def test_going_up_is_slower_than_walking_on_the_level(world):
    sim, a = world
    plateau(sim, a)
    run(sim, a, "step", {"dir": "N"})
    assert run(sim, a, "step", {"dir": "N"})["ok"]           # a jump up
    up = a.ready - sim.tick
    assert run(sim, a, "step", {"dir": "N"})["ok"]           # on along the level
    assert up > a.ready - sim.tick


def test_generated_land_has_hills_and_peaks():
    levels, peaks = set(), 0
    for cx in range(4, 12):
        for cy in range(-4, 4):
            _, _, lv = gen_chunk(7, cx, cy)
            levels |= {col_top(v) for v in lv}
            peaks += sum(1 for v in lv if col_top(v) >= PEAK)
    assert {0, 1, 2} <= levels and peaks > 0 and max(levels) < 16
    assert gen_chunk(7, 5, 1) == gen_chunk(7, 5, 1)          # deterministic


def test_nothing_is_built_on_a_hills_rim(world):
    sim, a = world
    plateau(sim, a)
    assert sim.world.edge(a.x + 2, a.y - 2) and sim.world.rim(a.x + 4, a.y - 4) and not sim.world.rim(a.x + 2, a.y - 4)
    a.add("chest", 1)
    a.x, a.y = a.x + 2, a.y - 1                              # under the cliff: placing on its edge is refused
    assert run(sim, a, "place", {"dir": "N", "item": "chest"})["error"] == "cliff_edge"


def test_nothing_generates_on_a_rim():
    from megastructure.gen import gen_cave, gen_level
    for cx in range(4, 9):
        for cy in range(-3, 3):
            _, block, lv = gen_chunk(7, cx, cy)
            for i, v in enumerate(lv):
                x, y, v = cx * CHUNK + i % CHUNK, cy * CHUNK + i // CHUNK, col_floor(v)
                if v and any(gen_cave(7, x + dx, y + dy, gen_level(7, x + dx, y + dy))[0] < v for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    assert block[i] == 0, (x, y)


def test_the_land_has_biomes_mountains_rivers_and_caves():
    from megastructure.gen import biome, gen_cave, gen_level, river
    kinds, caves, rivers, top = set(), 0, 0, 0
    for y in range(-400, 400, 6):
        for x in range(-400, 400, 6):
            lv = gen_level(7, x, y)
            top = max(top, lv)
            kinds.add(biome(7, x, y, lv))
            rivers += river(7, x, y)
            floor, roof = gen_cave(7, x, y, lv)
            caves += roof > 0
            assert floor + roof <= lv and 0 <= floor
    assert kinds == {"plains", "forest", "highlands", "dry", "swamp", "mountain"} and top >= 8 and rivers and caves
    assert biome(7, 10, 10, gen_level(7, 10, 10)) == "plains"                      # spawn: plains


def test_you_walk_on_a_cave_or_in_under_it(world):
    """A cave is empty cells under solid ones: from its mouth you walk in under the hill; up on the hill you walk
    over it, and step off its end (a short drop: nothing)."""
    sim, a = world
    x, y = a.x, a.y
    for i in range(1, 4):                                    # east of you: a hill 2 high, hollow at the ground
        sim.world.set(x + i, y, level=0, roof=2)
        sim.world.set(x + i, y - 1, level=1)
    sim.world.set(x, y - 1, level=1)
    assert sim.world.surfaces(x + 1, y) == [0, 2] and not sim.world.solid(x + 1, y, 1) and sim.world.solid(x + 1, y, 2)
    assert run(sim, a, "step", {"dir": "E"})["ok"] and sim.in_cave(a) and sim.height(a) == 0     # in at its mouth
    assert run(sim, a, "step", {"dir": "W"})["ok"] and not sim.in_cave(a)                         # and out
    assert run(sim, a, "step", {"dir": "N"})["ok"] and run(sim, a, "step", {"dir": "E"})["ok"] and sim.height(a) == 1
    assert run(sim, a, "step", {"dir": "S"})["ok"] and sim.height(a) == 2 and not sim.in_cave(a)  # up onto the hill, over it
    assert run(sim, a, "step", {"dir": "E"})["ok"] and sim.height(a) == 2                         # along it
    assert run(sim, a, "step", {"dir": "E"})["ok"] and run(sim, a, "step", {"dir": "E"})["ok"]    # and off its end
    assert sim.height(a) == 0 and a.hp == 100


def test_you_fall_off_an_edge_and_a_long_fall_hurts(world):
    """Stepping off an edge you come down on the ground below, however far. Up to 3 layers is nothing; each layer
    more costs half a heart. A walk ends where a fall hurt; move_to never takes a fall that hurts, unless you ask
    for that one step."""
    sim, a = world
    x, y = a.x, a.y
    plateau(sim, a, h=3)
    a.x, a.y, a.z = x, y - 2, 3                              # on its south edge
    r = run(sim, a, "step", {"dir": "S"})
    assert r["ok"] and sim.height(a) == 0 and a.hp == 100 and "fell" not in r      # 3 layers: nothing
    a.x, a.y = x, y
    plateau(sim, a, h=6)
    a.x, a.y, a.z = x, y - 2, 6
    r = run(sim, a, "walk", {"dir": "S"})
    assert r["ok"] and r["stopped"] == "fell" and r["fell"] == 6 and r["damage"] == 15 and a.hp == 85
    assert (a.x, a.y) == (x, y - 1) and sim.height(a) == 0
    a.x, a.y, a.z = x, y - 2, 6
    r = run(sim, a, "move_to", {"x": x, "y": y})             # a way down that doesn't hurt: there is none
    assert not r["ok"] and (a.x, a.y) == (x, y - 2) and a.hp == 85
    assert run(sim, a, "move_to", {"x": x, "y": y - 4})["ok"] and run(sim, a, "move_to", {"x": x, "y": y - 2})["ok"]   # (along the top: fine)
    assert run(sim, a, "move_to", {"x": x, "y": y - 1})["ok"] and a.hp == 70       # the one step, asked for


def test_digging_down_into_a_hollow_drops_you_in(world):
    sim, a = world
    x, y = a.x, a.y
    sim.world.set(x, y, level=-6, roof=6, head=5)            # under your feet: a layer of ground over a deep hollow
    a.z = 0
    a.add("pickaxe")
    r = run(sim, a, "dig_down", {"with": "pickaxe"})
    assert r["ok"] and sim.height(a) == -6 and r["fell"] == 6 and a.hp == 85


def test_the_land_is_cells_and_is_saved_as_cells(world):
    """A column is its cells, solid or empty: nothing else is kept."""
    sim, a = world
    x, y = a.x + 2, a.y
    sim.world.set(x, y, level=0, roof=4)                     # (shorthand: a hill 4 high, hollow 2 cells over the ground)
    assert sim.world.col(x, y) == col_cave(0, 2, 4) and sim.world.surfaces(x, y) == [0, 4]
    assert [sim.world.solid(x, y, z) for z in range(-1, 6)] == [True, True, False, False, True, True, False]
    assert sim.world.covered(x, y, 0) and not sim.world.covered(x, y, 4) and sim.world.roof(x, y) == 4
    sim.world.set_cell(x, y, 3, False)                       # a cell more dug out of it
    assert sim.world.surfaces(x, y) == [0, 4] and not sim.world.solid(x, y, 3)
    sim.world.set_cell(x, y, 2, True)                        # one filled in: a ledge in the hollow
    assert sim.world.surfaces(x, y) == [0, 2, 4]
    sim.world.set_cell(x, y, 4, False)                       # its top taken off
    assert sim.world.top(x, y) == 2 and sim.world.level(x, y) == 0
    c = sim.world.chunk(x >> 5, y >> 5)
    assert Chunk.unpack(c.cx, c.cy, c.pack()).cols == c.cols
    assert Chunk.unpack(0, 0, zlib.compress(bytes(3 * CHUNK * CHUNK))) is None       # a save from before: made anew


def test_no_jumping_up_out_through_a_low_ceiling(world):
    """In a cave one cell high, the ground outside a layer up is not a way out: a jump needs room over your head.
    (You went out through the rock, at a place with no opening.)"""
    sim, a = world
    x, y = a.x, a.y
    sim.world.set(x, y - 1, level=0, roof=2)                 # a cave one cell high under a hill 2 high...
    sim.world.set(x, y - 2, level=1)                         # ...the ground behind it a layer up
    assert run(sim, a, "step", {"dir": "N"})["ok"] and sim.in_cave(a) and sim.height(a) == 0
    r = run(sim, a, "step", {"dir": "N"})
    assert not r["ok"] and (a.x, a.y) == (x, y - 1)          # the rock over your head: no jump
    sim.world.set_cell(x, y - 1, 2, False)                   # its roof taken off: now you can
    assert run(sim, a, "step", {"dir": "N"})["ok"] and sim.height(a) == 1
