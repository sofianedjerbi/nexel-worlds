"""Digging down, the levels below, and climbing back up."""

from helpers import run
from megastructure.layers import LAYER, depth, local_x


def test_dig_down_and_climb_back_up(world):
    sim, a = world
    x0, y0 = a.x, a.y
    assert run(sim, a, "dig_down", {})["error"] == "need_tool"
    a.add("pickaxe")
    r = run(sim, a, "dig_down", {"with": "pickaxe"})
    assert r["ok"] and depth(a.x) == 1 and (local_x(a.x), a.y) == (x0, y0)
    assert sim.world.block(x0, y0) == "hole" and sim.world.block(a.x, a.y) == "ladder"
    assert sim.observe(a)["self"]["depth"] == 1 and sim.sheltered(a.x, a.y)
    assert all(sim.world.passable(a.x + dx, a.y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))  # a chamber
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["error"] == "cannot_dig"     # (not through the ladder)
    run(sim, a, "step", {"dir": "E"})
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["ok"] and depth(a.x) == 2    # as deep as you like
    run(sim, a, "climb", {})
    assert depth(a.x) == 1 and sim.world.block(a.x, a.y) == "hole"
    run(sim, a, "step", {"dir": "W"})
    assert run(sim, a, "climb", {})["ok"] and (a.x, a.y) == (x0, y0) and depth(a.x) == 0


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
