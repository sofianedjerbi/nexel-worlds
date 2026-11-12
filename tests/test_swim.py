"""Swimming: shallow water can be crossed without a boat, at walking speed; deep water cannot."""

from helpers import run


def test_you_swim_through_shallow_water_but_not_deep(world):
    sim, a = world
    for i in range(1, 4):
        sim.world.set(a.x + i, a.y, ground="water", block="none")
    sim.world.set(a.x + 4, a.y, ground="deep_water", block="none")
    assert not sim.swimming(a)
    r = run(sim, a, "walk", {"dir": "E"})
    assert r["steps"] == 3 and r["stopped"] == "blocked"              # three tiles of shallows, then the deep stops you
    assert sim.swimming(a) and sim.observe(a)["self"]["swimming"] and not a.sailing
    assert sim.stride(a, {"run": True}) == 0.2                          # no sprinting in water
    assert run(sim, a, "walk", {"dir": "W"})["steps"] >= 3 and not sim.swimming(a)      # and back out onto land


def test_a_swimmer_can_climb_into_a_boat(world):
    sim, a = world
    sim.world.set(a.x + 1, a.y, ground="water", block="none")
    sim.world.set(a.x + 2, a.y, ground="water", block="boat")
    run(sim, a, "step", {"dir": "E"})
    assert sim.swimming(a)
    run(sim, a, "step", {"dir": "E"})
    assert a.sailing and not sim.swimming(a)
