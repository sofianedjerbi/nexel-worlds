"""Farming, fire, growth and regrowth."""

from helpers import run


def test_fire_spreads_and_burns_out(world):
    sim, a = world
    for dx in range(1, 4):
        sim.world.set(a.x + dx, a.y, block="fence")
    a.add("torch", 1)
    assert run(sim, a, "ignite", {"dir": "E", "with": "torch"})["ok"]
    assert (a.x + 1, a.y) in sim.fires and sim.world.block(a.x + 1, a.y) == "fence"   # burning, still standing
    for _ in range(600):
        sim.step()
    assert not sim.fires
    assert sim.world.ground(a.x + 1, a.y) == "ash" and sim.world.block(a.x + 1, a.y) == "none"


def test_fruit_tree_regrows_fruit(world):
    sim, a = world
    from nexel_worlds.sim import sec
    sim.world.set(a.x + 1, a.y, block="fruit_tree")
    r = run(sim, a, "dig", {"dir": "E"})
    assert r["changed"]["inventory"] == {"fruit": 3} and sim.world.block(a.x + 1, a.y) == "bare_fruit_tree"
    for _ in range(sec(240) + sec(4)):
        sim.step()
    assert sim.world.block(a.x + 1, a.y) == "fruit_tree"

def test_picked_bush_stays_and_grows_berries_back(world):
    sim, a = world
    from nexel_worlds.sim import sec
    sim.world.set(a.x + 1, a.y, block="berry_bush")
    r = run(sim, a, "dig", {"dir": "E"})
    assert r["changed"]["inventory"] == {"berries": 2, "seed": 1} and sim.world.block(a.x + 1, a.y) == "bare_bush"
    for _ in range(sec(184)):
        sim.step()
    assert sim.world.block(a.x + 1, a.y) == "berry_bush"
    run(sim, a, "dig", {"dir": "E"})
    assert run(sim, a, "dig", {"dir": "E"})["changed"]["inventory"] == {"fiber": 2}   # cutting the bare bush
    assert sim.world.block(a.x + 1, a.y) == "none"

def test_crop_species_watering_and_harvest(world):
    sim, a = world
    from nexel_worlds.sim import sec
    from nexel_worlds.tiles import crop_species
    a.add("seed", 1)
    a.add("watering_can", 1)
    a.add("hoe", 1)
    run(sim, a, "dig", {"dir": "N", "with": "hoe"})
    run(sim, a, "place", {"dir": "N", "item": "seed"})
    assert sim.world.block(a.x, a.y - 1) == "sprout"
    assert run(sim, a, "water", {"dir": "N", "with": "watering_can"})["ok"] and sim.world.ground(a.x, a.y - 1) == "wet_tilled"
    for _ in range(sec(75) + sec(3)):            # watered: half of 150 s
        sim.step()
    assert sim.world.block(a.x, a.y - 1) == "crop" and sim.world.ground(a.x, a.y - 1) == "tilled"
    for _ in range(sec(150) + sec(3)):
        sim.step()
    r = run(sim, a, "dig", {"dir": "N"})
    assert r["changed"]["inventory"][crop_species(a.x, a.y - 1)] == 3

def test_ash_grows_back_into_grass(world):
    sim, a = world
    from nexel_worlds.sim import sec
    sim.world.set(a.x + 1, a.y, ground="grass")
    assert sim.ignite(a.x + 1, a.y)
    for _ in range(sec(16)):
        sim.step()
    assert sim.world.ground(a.x + 1, a.y) == "ash"
    for _ in range(sec(244)):
        sim.step()
    assert sim.world.ground(a.x + 1, a.y) == "grass"
