"""The grumblestump and the snapbloom (sim/stump.py): plants that are more than they look."""

from test_wild import night, put

from nexel_worlds.sim import CREATURES, sec
from nexel_worlds.sim.spawning import ROAMING, WILD_SPAWNS


def day(sim):
    sim.tick = (sim.tick // sec(1200)) * sec(1200) + sec(300)
    assert not sim.is_night()


def test_by_day_the_grumblestump_is_only_a_stump(world):
    sim, a = world
    day(sim)
    stump = put(sim, "grumblestump", a.x + 1, a.y)
    hp = a.hp
    for _ in range(sec(3)):
        sim.step()
    assert stump.mode == "sleep" and (stump.x, stump.y) == (a.x + 1, a.y) and a.hp == hp


def test_at_night_it_comes_raises_its_arms_and_slams_everyone_near(world):
    sim, a = world
    night(sim)
    stump = put(sim, "grumblestump", a.x + 3, a.y)
    for _ in range(sec(4)):
        sim.step()
        if stump.mode == "windup":
            break
    assert stump.mode == "windup" and max(abs(stump.x - a.x), abs(stump.y - a.y)) <= 1   # it shuffled up, arms going up
    hp = a.hp
    for _ in range(sec(0.5)):
        sim.step()
    assert a.hp == hp                                             # the warning, long: nothing yet
    for _ in range(sec(0.6)):
        sim.step()
    assert a.hp == hp - CREATURES["grumblestump"]["damage"]       # the arms came down: the ring hit us
    assert any(e["type"] == "slam" for e in a.events)


def test_two_tiles_away_when_the_arms_come_down_is_safe(world):
    sim, a = world
    night(sim)
    stump = put(sim, "grumblestump", a.x + 1, a.y)
    sim.step()
    assert stump.mode == "windup"
    a.x -= 3                                                      # out of the ring before it lands
    hp = a.hp
    for _ in range(sec(1.2)):
        sim.step()
    assert a.hp == hp and stump.mode != "windup"                 # it slammed the ground where we were


def test_the_snapbloom_bites_only_who_is_still_beside_it(world):
    sim, a = world
    day(sim)
    bloom = put(sim, "snapbloom", a.x + 1, a.y)
    sim.step()
    assert bloom.mode == "windup" and bloom.dir == (-1, 0)        # it rears back, facing us
    hp = a.hp
    for _ in range(sec(1)):
        sim.step()
    assert a.hp == hp - CREATURES["snapbloom"]["damage"]          # we stayed: bitten
    for _ in range(sec(2.5)):                                     # (it rests, then rears again)
        sim.step()
        if bloom.mode == "windup":
            break
    assert bloom.mode == "windup"
    a.y += 2                                                      # step aside during the warning
    hp = a.hp
    for _ in range(sec(1)):
        sim.step()
    assert a.hp == hp


def test_at_night_the_snapbloom_is_a_flower_like_the_others(world):
    sim, a = world
    night(sim)
    bloom = put(sim, "snapbloom", a.x + 1, a.y)
    hp = a.hp
    for _ in range(sec(3)):
        sim.step()
    assert bloom.mode != "windup" and a.hp == hp


def test_they_are_rare_and_keep_their_hours():
    assert WILD_SPAWNS["grumblestump"]["night"] and WILD_SPAWNS["snapbloom"]["day"]
    assert all(WILD_SPAWNS[k]["cap"] == 1 and WILD_SPAWNS[k]["every"] >= sec(300) for k in ("grumblestump", "snapbloom"))
    assert {"grumblestump", "snapbloom"} <= set(ROAMING)
