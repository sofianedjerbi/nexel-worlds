"""Ladders and stairs (sim/climbing.py): up a ladder and down it unhurt, a flight of stairs laid with one press."""

from helpers import run


def test_a_ladder_is_climbed_up_and_down_without_a_fall(world):
    s, a = world
    x, y = a.x, a.y
    for i in (-1, 0, 1):
        s.world.set(x + i, y - 2, level=6)                     # a cliff six layers high, two tiles north
    a.add("ladder", 2)
    assert run(s, a, "place", {"x": x - 3, "y": y, "item": "ladder"})["error"] == "bad_target"     # in the open: nothing to lean on
    assert run(s, a, "place", {"dir": "N", "item": "ladder"})["ok"] and s.world.block(x, y - 1) == "ladder"
    assert run(s, a, "step", {"dir": "N"})["ok"] and s.height(a) == 0
    hp = a.hp
    assert run(s, a, "step", {"dir": "N"})["ok"] and (a.y, s.height(a)) == (y - 2, 6)   # up the ladder, onto the cliff
    assert run(s, a, "step", {"dir": "S"})["ok"] and (a.y, s.height(a)) == (y - 1, 0)   # and down it: no fall
    assert a.hp == hp
    a.x, a.y, a.z = x + 1, y - 2, 6                            # off the cliff where there is no ladder: a fall that hurts
    assert run(s, a, "step", {"dir": "S"})["ok"] and a.hp < hp
    a.hp = hp
    a.x, a.y, a.z = x, y + 1, 0
    r = run(s, a, "move_to", {"x": x - 1, "y": y - 2})         # the way to the cliff's top goes up the ladder
    assert r["ok"] and (a.x, a.y, s.height(a)) == (x - 1, y - 2, 6)


def test_only_people_climb_and_a_ladder_needs_its_tile_open(world):
    s, a = world
    x, y = a.x, a.y
    s.world.set(x, y - 2, level=6)
    s.world.set(x, y - 1, block="ladder")
    from megastructure.sim import Creature
    hen = Creature(99, "chicken", x, y - 1, 4, z=0)
    assert s.landing(hen, x, y - 2) is None                    # a hen on the ladder: the cliff is a wall
    s.world.set_cell(x, y - 1, 4, True)                         # something over the ladder: no way up through it
    a.x, a.y, a.z = x, y - 1, 0
    assert run(s, a, "step", {"dir": "N"})["error"] == "blocked"


def test_stairs_are_a_flight_laid_with_one_press(world):
    """A floor three layers up on a wall: stairs put beside it are two steps, down towards you."""
    s, a = world
    x, y = a.x, a.y
    a.add("plank", 4)
    a.add("stairs", 1)
    for i in range(3):
        s.world.set(x - 1 + i, y - 3, block="wood_wall")
        assert run(s, a, "place", {"x": x - 1 + i, "y": y - 3, "item": "plank", "z": 3})["ok"]
    r = run(s, a, "place", {"x": x + 2, "y": y, "item": "stairs"})
    assert r["error"] == "bad_target" and "stairs lead up" in r["detail"]          # nothing higher beside it
    r = run(s, a, "place", {"x": x, "y": y - 2, "item": "stairs"})
    assert r["error"] == "missing_item" and "2 stairs" in r["detail"]              # two steps, one in hand
    a.add("stairs", 3)
    r = run(s, a, "place", {"x": x, "y": y - 2, "item": "stairs"})
    assert r["ok"] and a.count("stairs") == 2
    assert s.world.surfaces(x, y - 2) == [2] and s.world.surfaces(x, y - 1) == [1]   # two layers high by the floor, one below it
    assert [s.floors.get(x, y - 2, z) for z in (1, 2)] == [["stairs", "none"]] * 2
    for d, z in (("N", 1), ("N", 2), ("N", 3)):                 # up them, a hop a step, onto the floor
        assert run(s, a, "step", {"dir": d})["ok"] and s.height(a) == z
    a.x, a.y, a.z = x + 1, y, 0
    r = run(s, a, "dig", {"x": x, "y": y - 2, "z": 1})         # a step taken back: its whole column, one stairs
    assert r["ok"] and a.count("stairs") == 3 and s.world.surfaces(x, y - 2) == [0]
    s.world.set_cell(x + 1, y - 1, 3, True)                     # a floor over where the flight would come down: it runs along the wall
    r = run(s, a, "place", {"x": x + 1, "y": y - 2, "item": "stairs"})
    assert r["ok"] and s.world.surfaces(x + 1, y - 2) == [2] and s.world.surfaces(x, y - 2) == [1]
    s.world.set_cell(x - 1, y - 2, 4, True)                     # a floor over the first step: no room for it, whichever way
    r = run(s, a, "place", {"x": x - 1, "y": y - 2, "item": "stairs"})
    assert r["error"] == "bad_target" and "no room" in r["detail"]


def test_a_way_down_is_dug_as_a_tunnel_and_what_is_over_it_stays(world):
    """"like minecraft you know when you go donw you do l shape tunnels. this enforce me to dig huge columns": a cell
    inside the land with air on a side of it is dug, and the land over it stays, a roof. A step down at a time, the
    room to stand in (two cells), and you walk down it; a cell with no air beside it is not dug."""
    s, a = world
    x, y = a.x, a.y
    a.add("pickaxe")
    dig = lambda dx, z: run(s, a, "dig", {"x": x + dx, "y": y, "z": z, "with": "pickaxe"})
    assert dig(1, 0)["ok"] and run(s, a, "step", {"dir": "E"})["ok"] and s.height(a) == -1       # a step, open
    assert dig(2, 0)["ok"] and dig(2, -1)["ok"] and run(s, a, "step", {"dir": "E"})["ok"] and s.height(a) == -2
    r = dig(3, -1)                                             # in front, at your body's height: under the ground
    assert r["ok"] and s.world.solid(x + 3, y, 0) and not s.world.solid(x + 3, y, -1)
    assert dig(3, -2)["ok"] and s.world.surfaces(x + 3, y) == [-3, 0]                  # the room to stand in, a roof over it
    assert run(s, a, "step", {"dir": "E"})["ok"] and (a.x, s.height(a)) == (x + 3, -3) and s.world.covered(x + 3, y, -3)
    assert dig(5, -2)["ok"] is False and s.world.solid(x + 5, y, -2)                  # no air beside it: not dug
    r = run(s, a, "jump", {"dir": "W"})
    assert r["ok"] and s.height(a) == -2, r                                          # and back up, a jump a step


def test_a_hole_is_dug_beside_you_a_layer_at_a_time(world):
    """`dig` aimed at a tile's ground with its height: the ground there comes down a layer (by hand, slowly; with a
    pickaxe, faster). Without the height it is the old dig (tilling wants a hoe). Not under someone."""
    s, a = world
    x, y = a.x, a.y
    s.world.set(x + 1, y, ground="grass")
    assert run(s, a, "dig", {"dir": "E"})["error"] == "need_tool"                 # (no height: tilling, as ever)
    r = run(s, a, "dig", {"dir": "E", "z": 0})                                    # by hand
    assert r["ok"] and s.world.surfaces(x + 1, y) == [-1] and a.count("dirt") == 1 and s.world.ground(x + 1, y) == "grass"
    a.add("pickaxe")
    t0 = s.tick
    r = run(s, a, "dig", {"dir": "E", "z": -1, "with": "pickaxe"})               # a layer deeper, quicker
    assert r["ok"] and s.world.surfaces(x + 1, y) == [-2] and s.tick - t0 < 15
    s.world.set(x - 1, y, block="rock")
    assert run(s, a, "dig", {"dir": "W", "z": 0, "with": "pickaxe"})["ok"] and s.world.block(x - 1, y) == "none"   # a thing on it: the thing first
    assert s.world.surfaces(x - 1, y) == [0]
    from megastructure.sim import Creature
    s.creatures[99] = Creature(99, "chicken", x, y + 1, 4, z=0)
    assert run(s, a, "dig", {"dir": "S", "z": 0, "with": "pickaxe"})["error"] == "occupied"


import pytest


@pytest.mark.parametrize("d", ["N", "E", "S", "W"])
@pytest.mark.parametrize("deep", [2, 3, 4, 7, 12])
def test_a_ladder_facing_a_wall_goes_on_your_own_tile_and_takes_you_out(world, d, deep):
    """At the bottom of your own one-tile shaft, a ladder in hand: facing any of the four walls it is put where you
    stand, against that wall, and walking into the wall climbs out onto its top."""
    from megastructure.tiles import DIRS
    s, a = world
    x, y = a.x, a.y
    s.world.set(x, y, level=-deep)
    a.z = -deep
    a.add("ladder")
    r = run(s, a, "place", {"dir": d, "item": "ladder"})
    assert r["ok"] and r["at"] == [x, y] and r["z"] == -deep
    assert s.world.block(x, y) == "ladder" and a.count("ladder") == 0
    dx, dy = DIRS[d]
    hp = a.hp
    assert run(s, a, "step", {"dir": d})["ok"] and (a.x, a.y, s.height(a)) == (x + dx, y + dy, 0)
    assert run(s, a, "step", {"dir": {"N": "S", "S": "N", "E": "W", "W": "E"}[d]})["ok"] and s.height(a) == -deep and a.hp == hp


def test_a_ladder_on_your_own_tile_is_refused_when_nothing_is_taller(world):
    s, a = world
    x, y = a.x, a.y
    a.add("ladder", 3)
    s.world.set(x + 1, y, level=1)                              # a step: hopped, no ladder (and none on top of it either)
    assert run(s, a, "place", {"dir": "E", "item": "ladder"})["error"] == "bad_target"
    assert run(s, a, "place", {"dir": "W", "item": "ladder"})["error"] == "bad_target"      # flat ground, nothing beside it
    s.world.set(x, y - 1, level=13)                             # higher than a ladder goes
    assert run(s, a, "place", {"dir": "N", "item": "ladder"})["error"] == "bad_target"
    assert s.world.block(x, y) == "none" and a.count("ladder") == 3
    s.world.set(x, y - 1, level=2)
    s.world.set(x, y, block="chair")                            # something where you stand: no room for its foot
    assert run(s, a, "place", {"dir": "N", "item": "ladder"})["error"] == "occupied"
    s.world.set(x, y, block="flower")                           # a flower there is picked
    assert run(s, a, "place", {"dir": "N", "item": "ladder"})["ok"] and a.count("flower") == 1 and s.world.block(x, y) == "ladder"


def test_what_is_on_a_tile_is_reached_at_its_own_ground(world):
    """A flower at the bottom of a pit beside you, eight layers down: out of reach (the tile's ground nearest your
    height was what counted: any ledge of that tile near you would do)."""
    s, a = world
    x, y = a.x, a.y
    s.world.set(x + 1, y, level=-8, block="flower")
    assert run(s, a, "dig", {"dir": "E"})["error"] == "out_of_range"
    s.world.set(x + 1, y, level=-2, block="flower")
    assert run(s, a, "dig", {"dir": "E"})["ok"] and a.count("flower") == 1
