"""Bodies: a creature stands on the land, and goes up and down it, as a person does (sim/bodies.py)."""

import json

from helpers import run
from test_wild import put

from megastructure.sim import CREATURES, Creature, sec


def test_a_creature_jumps_up_a_layer_and_comes_down_as_a_person_does(world):
    """(They kept to the level they were on: a single step in the ground was a wall to them.)"""
    sim, a = world
    cow = put(sim, "cow", a.x + 2, a.y + 3)
    x, y = cow.x, cow.y
    sim.world.set(x + 1, y, level=1)
    sim.world.set(x + 2, y, level=3)
    assert sim._creature_move(cow, x + 1, y) and sim.height(cow) == 1          # a layer up: a jump
    assert not sim._creature_move(cow, x + 2, y)                               # two more: a wall, as to you
    assert sim._creature_move(cow, x, y) and sim.height(cow) == 0              # and down again
    sim.world.set(x, y, level=3)                                               # the ground under it, three layers up
    assert sim.height(cow) == 3
    assert sim._creature_move(cow, x - 1, y) and sim.height(cow) == 0          # down three: it lands, unhurt
    sim.world.set(x, y, level=0)
    sim._creature_move(cow, x, y)
    sim.world.set(x, y, level=4)
    assert not sim._creature_move(cow, x - 1, y) and (cow.x, cow.y) == (x, y)  # four would hurt: it doesn't take it


def test_a_creature_walks_in_under_a_hill_or_over_it(world):
    """A cave is empty cells under solid ones: from the ground you walk in, at your height; from the hill, over it."""
    sim, a = world
    x, y = a.x + 2, a.y + 3
    sim.world.set(x + 1, y, level=0, roof=4)                                   # a hollow under a hill four high
    low = put(sim, "chicken", x, y)
    assert sim._creature_move(low, x + 1, y) and sim.height(low) == 0 and sim.in_cave(low)
    sim.world.set(x + 2, y, level=4)
    high = put(sim, "chicken", x + 2, y)
    assert sim.height(high) == 4
    sim.creatures.pop(low.id)                                                  # (nobody in the way on that tile)
    assert sim._creature_move(high, x + 1, y) and sim.height(high) == 4 and not sim.in_cave(high)


def test_a_tusker_runs_up_a_step_to_get_you(world):
    """You on ground a layer higher: its charge takes the step (it rammed it, stunned, as if it were a tree)."""
    sim, a = world
    for dx in range(-1, 3):
        for dy in range(-1, 2):
            sim.world.set(a.x + dx, a.y + dy, level=1)
    assert sim.height(a) == 1
    boar = put(sim, "tusker", a.x + 4, a.y)
    hp = a.hp
    for _ in range(sec(2.5)):
        sim.step()
    assert a.hp <= hp - CREATURES["tusker"]["damage"] + 2 and boar.mode != "stun"


def test_a_creature_keeps_its_height_when_the_world_is_saved(world):
    sim, a = world
    sim.world.set(a.x + 2, a.y, level=0, roof=4)
    hen = put(sim, "chicken", a.x + 2, a.y)
    hen.z = 4                                                                  # on the hill, not in the hollow under it
    again = Creature(**json.loads(json.dumps(hen.to_json())))
    assert sim.height(again) == 4
    old = {k: v for k, v in hen.to_json().items() if k != "z"}                 # one saved before creatures had a height:
    assert sim.height(Creature(**old)) == 0                                    # on the lowest ground, as they all were
    assert "z" in a.to_json()
