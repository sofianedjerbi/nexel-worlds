"""Digging down: holes you drop through, jumping back up a layer, the levels below."""

from helpers import run
from megastructure.layers import LAYER, depth, local_x


def test_dig_down_drops_you_through_and_you_jump_back_up(world):
    sim, a = world
    x0, y0 = a.x, a.y
    assert run(sim, a, "dig_down", {})["error"] == "need_tool"
    a.add("pickaxe")
    r = run(sim, a, "dig_down", {"with": "pickaxe"})
    assert r["ok"] and sim.world.block(x0, y0) == "hole"
    assert depth(a.x) == 1 and (local_x(a.x), a.y) == (x0, y0)                # straight down, under the hole
    assert sim.observe(a)["self"]["depth"] == 1 and sim.sheltered(a.x + 1, a.y)
    assert run(sim, a, "step", {"dir": "N"})["ok"]                            # a jump up beside the hole
    assert depth(a.x) == 0 and (a.x, a.y) == (x0, y0 - 1)


def test_walking_onto_a_hole_drops_you_and_holes_go_as_deep_as_you_dig(world):
    sim, a = world
    a.add("pickaxe")
    x0, y0 = a.x, a.y
    run(sim, a, "dig_down", {"with": "pickaxe"})
    run(sim, a, "step", {"dir": "E"})                        # out the other side
    assert depth(a.x) == 0 and (a.x, a.y) == (x0 + 1, y0)
    assert run(sim, a, "step", {"dir": "W"})["ok"] and depth(a.x) == 1      # back onto it: down you go
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["ok"] and depth(a.x) == 2


def test_underground_you_dig_through_rock_and_cannot_jump_where_theres_no_hole(world):
    sim, a = world
    a.add("pickaxe")
    run(sim, a, "dig_down", {"with": "pickaxe"})
    bx, y = a.x, a.y
    sim.set_tile(bx + 1, y, ground="cave_floor", block="cave_wall")
    sim.set_tile(bx + 2, y, ground="cave_floor", block="none")
    assert run(sim, a, "dig", {"dir": "E", "with": "pickaxe"}, limit=400)["ok"]   # a tunnel east
    assert run(sim, a, "step", {"dir": "E"})["ok"] and depth(a.x) == 1
    sim.set_tile(a.x, y + 1, ground="cave_floor", block="cave_wall")
    sim.set_tile(a.x, y - 1, ground="cave_floor", block="cave_wall")
    assert not run(sim, a, "step", {"dir": "N"})["ok"] and depth(a.x) == 1   # no hole over you: rock


def test_digging_down_on_a_hill_takes_it_down_a_layer(world):
    sim, a = world
    a.add("pickaxe")
    sim.world.set(a.x, a.y, level=2)
    r = run(sim, a, "dig_down", {"with": "pickaxe"})
    assert r["ok"] and sim.world.level(a.x, a.y) == 1 and depth(a.x) == 0 and a.count("stone") == 1


def test_underground_is_rock_with_caves_and_ore():
    from megastructure.gen import gen_chunk
    from megastructure.tiles import B
    for d in (1, 5):
        _, block, lv = gen_chunk(7, d * LAYER // 32, 0)
        kinds = set(block)
        assert B["cave_wall"] in kinds and B["none"] in kinds and not any(lv)


def test_people_on_other_levels_dont_see_each_other(world):
    sim, a = world
    b = sim.login("Bo", "tok2")
    b.x, b.y = a.x + 1, a.y
    assert any(e.get("name") == "Bo" for e in sim.observe(a)["entities"])
    a.add("pickaxe")
    run(sim, a, "dig_down", {"with": "pickaxe"})
    assert not any(e.get("name") == "Bo" for e in sim.observe(a)["entities"])
