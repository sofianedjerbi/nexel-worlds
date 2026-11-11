"""Relief: heights; a step down or a jump up a layer, no higher; digging into higher ground; old worlds."""

import zlib

from helpers import run
from megastructure.gen import CHUNK, PEAK, gen_chunk
from megastructure.tiles import B
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
    assert not r["ok"] and "cliff" in r["detail"]
    a.add("pickaxe")
    r = run(sim, a, "dig", {"dir": "N", "with": "pickaxe"})
    assert r["ok"] and sim.world.level(a.x, a.y - 1) == 1 and a.count("stone") == 1
    assert run(sim, a, "step", {"dir": "N"})["ok"] and sim.world.level(a.x, a.y) == 1


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
            levels |= {(v & 31) - 16 for v in lv}
            peaks += sum(1 for v in lv if (v & 31) - 16 >= PEAK)
    assert {0, 1, 2} <= levels and peaks > 0 and max(levels) < 16
    assert gen_chunk(7, 5, 1) == gen_chunk(7, 5, 1)          # deterministic


def test_land_saved_before_relief_stays_flat_and_old_stairs_are_ground():
    n = CHUNK * CHUNK
    c = Chunk.unpack(0, 0, zlib.compress(bytes(n) + bytes(n)))     # ground and blocks only
    assert len(c.level) == n and set(c.level) == {16}              # all at sea level
    assert Chunk.unpack(0, 0, c.pack()).level == c.level
    old = zlib.compress(bytes(n) + bytes([B["hole"], B["ladder"]]) + bytes(n - 2) + bytes([0x11]) + bytes(n - 1))
    c = Chunk.unpack(0, 0, old)         # level 1 with the old stairs flag, and an old hole: a pit a layer deep
    assert c.level[0] == 16 and c.level[1] == 16 and c.block[0] == c.block[1] == 0


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
                x, y, v = cx * CHUNK + i % CHUNK, cy * CHUNK + i // CHUNK, (v & 31) - 16
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
            assert floor + roof <= lv and floor >= min(lv, 1)
    assert kinds == {"plains", "forest", "highlands", "dry", "swamp", "mountain"} and top >= 8 and rivers and caves
    assert biome(7, 10, 10, gen_level(7, 10, 10)) == "plains"                      # spawn: plains
