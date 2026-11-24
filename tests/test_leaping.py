"""A player's real jump through the air (sim/leaping.py, web/js/leap.js): the screen says the tiles it went over and
where it landed; the world checks them against the same arc and makes them, in the air over a gap, down on the far
side, up onto a step; a flight the arc cannot make is given up."""

from helpers import run
from nexel_worlds.sim.leaping import LEAP_TOP, airtime


def gap(sim, a, width=2):
    """A pit `width` tiles wide, three deep, starting a tile east of you, across a strip 3 tiles wide."""
    for dx in range(1, width + 1):
        for dy in (-1, 0, 1):
            sim.world.set(a.x + dx, a.y + dy, level=-3)


def test_a_sprint_jump_crosses_a_two_tile_gap_in_the_air(world):
    sim, a = world
    x, y = a.x, a.y
    gap(sim, a)
    r = run(sim, a, "leap", {"path": [[x + 1, y], [x + 2, y], [x + 3, y]], "land": 0, "n": 1, "run": True})
    assert r["ok"] and (a.x, a.y, sim.height(a)) == (x + 3, y, 0), r        # over it, never down in it
    assert a.flying is None and a.via_done == 1


def test_a_walk_said_in_the_air_goes_on_after_the_flight(world):
    """The screen lands and walks on at once: its walk replaces the leap before the world is down. The flight goes
    on (in the air over the pit, never in it), then the walk."""
    sim, a = world
    x, y = a.x, a.y
    gap(sim, a)
    sim.submit(a, "leap", {"path": [[x + 1, y], [x + 2, y], [x + 3, y]], "land": 0, "n": 1, "run": True})
    sim.step()
    sim.step()
    sim.submit(a, "walk", {"dir": "E", "run": True})
    lows = []
    for _ in range(12):
        sim.step()
        lows.append(sim.height(a))
    assert min(lows) == 0 and a.x >= x + 4, (lows, a.x)


def test_a_walking_jump_lands_on_a_step_up(world):
    sim, a = world
    x, y = a.x, a.y
    sim.world.set(x + 1, y, level=1)
    r = run(sim, a, "leap", {"path": [[x + 1, y]], "land": 1, "n": 2})
    assert r["ok"] and (a.x, sim.height(a)) == (x + 1, 1), r


def test_a_flight_the_arc_cannot_make_is_given_up(world):
    sim, a = world
    x, y = a.x, a.y
    gap(sim, a, 4)
    r = run(sim, a, "leap", {"path": [[x, y + i] for i in range(1, 14)], "land": 0, "n": 3})   # thirteen tiles: too far
    assert not r["ok"] and (a.x, a.y) == (x, y) and sim.height(a) == 0, r
    sim.world.set(x + 1, y, level=2)                       # two up: a wall
    sim.world.set(x + 2, y, level=2)
    r = run(sim, a, "leap", {"path": [[x + 1, y]], "land": 2, "n": 4})
    assert (a.x, a.y) == (x, y), r
    r = run(sim, a, "leap", {"path": [[x + 2, y]], "land": 0, "n": 5})        # not next to you
    assert (a.x, a.y) == (x, y), r


def test_a_flight_said_a_tile_at_a_time_is_made_as_it_comes_and_lands_when_told(world):
    """The screen says each tile as it comes over it, then where it landed: the world is never a whole jump behind."""
    sim, a = world
    x, y = a.x, a.y
    gap(sim, a)
    for i in (1, 2, 3):
        sim.submit(a, "leap", {"path": [[x + i, y]], "n": 1, "run": True})
        for _ in range(2):
            sim.step()
        assert (a.x, sim.height(a), a.flying) == (x + i, 0, 0), (i, a.x, sim.height(a))   # over the pit at the height it left from
    r = run(sim, a, "leap", {"land": 0, "n": 2})
    assert r["ok"] and a.flying is None and sim.height(a) == 0 and a.via_done == 2


def test_a_flight_never_told_its_end_comes_down_where_it_is(world):
    sim, a = world
    x, y = a.x, a.y
    gap(sim, a)
    sim.submit(a, "leap", {"path": [[x + 1, y]], "n": 1})
    for _ in range(30):
        sim.step()
    assert a.flying is None and a.x == x + 1 and sim.height(a) == -3


def test_the_arc_is_the_screens():
    """The same weight and top as the screen's (web/js/jump.js JUMP: 950 art px/s2, 20 art px, 16 a level)."""
    assert abs(LEAP_TOP - 1.25) < 1e-9 and abs(airtime(0) - .41) < .01 and airtime(1) < airtime(0) < airtime(-1)


def test_a_walk_said_after_a_flight_down_a_long_way_goes_on_past_where_it_landed(world):
    """"sprinting [down the mountain] my character ends up getting into the floor and glitching, facing the north
    direction (while I was sprinting south)": the screen jumped from 9 levels up, came down 9 lower (a fall that hurts)
    and walked on. The walk made the flight first (the way the screen had gone) and ended where its landing hurt, as a
    walk ends at a fall of its own: the world stopped a tile behind the screen, which was put back on it, turned round by
    that step back. That walk was said after the landing: it goes on from there (the fall still hurts)."""
    sim, a = world
    x, y = a.x, a.y
    for dx in range(-2, 12):
        for dy in (-1, 0, 1):
            sim.world.set(x + dx, y + dy, level=9 if dx == 0 else 0)
    a.z = 9
    sim.submit(a, "leap", {"path": [[x + 1, y], [x + 2, y], [x + 3, y]], "land": 0, "n": 1, "run": True})
    sim.step()
    sim.submit(a, "walk", {"dir": "E", "run": True})
    for _ in range(14):
        sim.step()
    assert a.hp < 20 and a.x >= x + 5 and sim.height(a) == 0, (a.hp, a.x - x, sim.height(a))
