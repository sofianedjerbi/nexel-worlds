"""Cave mouths: digging one, walking down into the level below and back up; the levels below."""

from helpers import run
from megastructure.layers import LAYER, depth, local_x


def test_dig_a_mouth_walk_down_and_back_up(world):
    sim, a = world
    x0, y0 = a.x, a.y
    assert run(sim, a, "dig_down", {})["error"] == "need_tool"
    a.add("pickaxe")
    r = run(sim, a, "dig_down", {"with": "pickaxe"})
    assert r["ok"] and depth(a.x) == 0 and (a.x, a.y) == (x0, y0)             # you stay at its top
    assert sim.world.block(x0, y0) == "hole" and sim.world.block(x0, y0 + 1) == "hole"
    assert run(sim, a, "step", {"dir": "S"})["ok"]                            # down the slope...
    assert depth(a.x) == 1 and (local_x(a.x), a.y) == (x0, y0 + 1)           # ...and you're below, at the ramp's foot
    assert sim.world.block(a.x, a.y) == "ladder" and sim.observe(a)["self"]["depth"] == 1 and sim.sheltered(a.x, a.y)
    assert run(sim, a, "step", {"dir": "S"})["ok"] and run(sim, a, "step", {"dir": "N"})["ok"]   # room to move below
    assert run(sim, a, "step", {"dir": "N"})["ok"] and depth(a.x) == 0 and (a.x, a.y) == (x0, y0)   # up and out


def test_a_mouth_is_entered_from_its_top_only(world):
    sim, a = world
    a.add("pickaxe")
    x0, y0 = a.x, a.y
    run(sim, a, "dig_down", {"with": "pickaxe"})
    a.x, a.y = x0, y0 + 2                                    # just south of the deep end: no climbing in from below
    assert not run(sim, a, "step", {"dir": "N"})["ok"] and depth(a.x) == 0
    a.x, a.y = x0, y0 - 1
    assert run(sim, a, "move_to", {"x": x0, "y": y0})["ok"] and run(sim, a, "step", {"dir": "S"})["ok"] and depth(a.x) == 1
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["error"] == "cannot_dig"     # (not on the ramp)
    run(sim, a, "step", {"dir": "S"})
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["ok"]                        # but as deep as you like
    run(sim, a, "step", {"dir": "S"})
    assert depth(a.x) == 2


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
    run(sim, a, "step", {"dir": "S"})
    assert not any(e.get("name") == "Bo" for e in sim.observe(a)["entities"])
