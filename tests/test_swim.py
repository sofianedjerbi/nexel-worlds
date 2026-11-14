"""Swimming and the depth of water: you swim on top of any water; its bottom can be dug down and filled back up."""

import pytest
from helpers import run

from megastructure.gen import gen_tile
from megastructure.sim.constants import SPRINT_FOOD, TIRES
from megastructure.tiles import DEPTH, GROUNDS


def pond(sim, a, kinds):
    for i, kind in enumerate(kinds, 1):
        sim.world.set(a.x + i, a.y, ground=kind, block="none")


def test_you_swim_on_any_water_whatever_its_depth(world):
    sim, a = world
    pond(sim, a, ["water", "mid_water", "deep_water", "abyss"])
    sim.world.set(a.x + 5, a.y, block="rock")
    assert not sim.swimming(a)
    r = run(sim, a, "walk", {"dir": "E"})
    assert r["steps"] == 4                                             # across all four depths, to the rock on the far side
    assert sim.swimming(a) and sim.observe(a)["self"]["swimming"] and not a.sailing
    assert sim.stride(a, {}) == 0.4 and sim.stride(a, {"run": True}) == 0.2     # in the water: half the speed of the land, swimming or at a sprint...
    tired = a.tired
    assert run(sim, a, "step", {"dir": "W", "run": True})["ok"] and a.tired - tired == pytest.approx(TIRES["dash"])   # ...and it tires three times a swim
    assert run(sim, a, "step", {"dir": "E"})["ok"] and a.tired - tired == pytest.approx(TIRES["dash"] + TIRES["swim"])
    a.hunger = SPRINT_FOOD
    assert sim.stride(a, {"run": True}) == 0.4                          # (not on three pieces of food)
    assert run(sim, a, "walk", {"dir": "W"})["steps"] >= 4 and not sim.swimming(a)      # and back out onto land


def test_a_swimmer_can_climb_into_a_boat(world):
    sim, a = world
    pond(sim, a, ["water", "water"])
    sim.world.set(a.x + 2, a.y, block="boat")
    run(sim, a, "step", {"dir": "E"})
    assert sim.swimming(a)
    run(sim, a, "step", {"dir": "E"})
    assert a.sailing and not sim.swimming(a)


def test_the_bottom_can_be_dug_deeper_and_filled_back(world):
    sim, a = world
    pond(sim, a, ["water"])
    for deeper in ("mid_water", "deep_water", "abyss"):                 # from the shore, a layer at a time
        r = run(sim, a, "dig", {"dir": "E"})
        assert r["ok"] and sim.world.ground(a.x + 1, a.y) == deeper and r["depth"] == DEPTH[deeper]
    assert not run(sim, a, "dig", {"dir": "E"})["ok"] and a.count("dirt") == 3       # as deep as it goes
    for back in ("deep_water", "mid_water", "water", "dirt"):           # dirt brings it back up, then makes land
        assert run(sim, a, "place", {"dir": "E", "item": "dirt"})["ok"] or back == "dirt"
        assert sim.world.ground(a.x + 1, a.y) == back or back == "dirt"
    a.add("pickaxe")
    pond(sim, a, ["water"])
    run(sim, a, "step", {"dir": "E"})
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["ok"] and sim.world.ground(a.x, a.y) == "mid_water"   # and from the surface


def test_the_sea_gets_deeper_away_from_the_shore():
    seen = {GROUNDS[gen_tile(7, x, y)[0]].name for x in range(-300, 300, 3) for y in range(-300, 300, 3)}
    assert set(DEPTH) <= seen


def test_eating_halves_your_speed_and_the_water_halves_it_again(world):
    """ "eating things should also slow down player by half. accumulation possible with water slow movements" """
    sim, a = world
    assert sim.stride(a, {}) == 0.2 and sim.stride(a, {"run": True}) == 0.1
    pond(sim, a, ["water", "water"])
    a.aside = object()                                                 # (the hands are busy: eating)
    assert sim.stride(a, {}) == 0.4 and sim.stride(a, {"run": True}) == 0.2
    a.aside = None
    assert run(sim, a, "step", {"dir": "E"})["ok"] and sim.swimming(a)
    a.aside = object()
    assert sim.stride(a, {}) == 0.8 and sim.stride(a, {"run": True}) == 0.4
    a.aside = None
    assert sim.stride(a, {}) == 0.4
