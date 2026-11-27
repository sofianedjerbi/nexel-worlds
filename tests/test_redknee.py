"""The redknee (sim/redknee.py): a night tarantula that rears up, pounces on where you stood and pins you in silk."""

from test_stump import day
from test_wild import night, put

from nexel_worlds.sim import CREATURES, sec
from nexel_worlds.sim.redknee import RK_SILK, RK_WARN
from nexel_worlds.sim.spawning import ROAMING, WILD_SPAWNS


REAR_BY = sec(4)                                                  # ticks: within this it has crept up and reared


def reared(sim, rk):
    for _ in range(REAR_BY):
        sim.step()
        if rk.mode == "windup":
            return True
    return False


def test_it_rears_up_then_pounces_on_you_and_pins_you_in_silk(world):
    sim, a = world
    night(sim)
    rk = put(sim, "redknee", a.x + 3, a.y)
    assert reared(sim, rk)
    assert rk.threat == (a.x, a.y)                                # aimed at the tile you stand on
    hp = a.hp
    for _ in range(sec(RK_WARN) - 2):
        sim.step()
    assert a.hp == hp and rk.mode == "windup"                     # the warning: nothing yet
    for _ in range(3):
        sim.step()
    assert a.hp == hp - CREATURES["redknee"]["damage"]           # still there: bitten
    assert (rk.x, rk.y) == (a.x + 1, a.y)                         # it landed against you
    assert a.ready >= sim.tick + sec(RK_SILK) - 3                 # and pinned: no step for a moment
    assert any(e["type"] == "silk" for e in a.events) and any(e["type"] == "pounce" for e in a.events)


def test_stepping_off_your_tile_makes_it_land_on_nothing(world):
    sim, a = world
    night(sim)
    rk = put(sim, "redknee", a.x + 3, a.y)
    assert reared(sim, rk)
    aim = rk.threat
    a.y += 2                                                      # a sidestep while it rears
    hp, ready = a.hp, a.ready
    for _ in range(sec(RK_WARN) + 2):
        sim.step()
    assert a.hp == hp and a.ready == ready                       # missed: no bite, no silk
    assert (rk.x, rk.y) == aim and rk.mode == ""                  # it landed where you were, and settles


def test_by_day_it_is_gone(world):
    sim, a = world
    day(sim)
    rk = put(sim, "redknee", a.x + 3, a.y)
    sim.step()
    assert rk.id not in sim.creatures
    assert any(e["type"] == "fade" and e.get("kind") == "redknee" for e in a.events)


def test_it_comes_out_at_night_by_the_woods_or_in_a_cave_and_drops_its_silk(world):
    sim, a = world
    rule = WILD_SPAWNS["redknee"]
    assert rule["night"] and "redknee" in ROAMING
    x, y = a.x + 6, a.y + 6
    assert not sim.spawn_spot_ok("redknee", x, y, fresh=True)          # open grass: no
    sim.set_tile(x + 2, y, block="tree")
    sim.set_tile(x - 1, y + 2, block="tree")
    assert sim.spawn_spot_ok("redknee", x, y, fresh=True)              # two trees near: yes
    assert ("fiber", .9, 1, 3) in CREATURES["redknee"]["drops"]
