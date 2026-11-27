"""The skeleton (sim/skeleton.py): a night walker that rattles, then swipes whoever is still beside it."""

from test_stump import day
from test_wild import night, put

from nexel_worlds.sim import CREATURES, sec
from nexel_worlds.sim.skeleton import SK_WARN
from nexel_worlds.sim.spawning import ROAMING, WILD_SPAWNS
from nexel_worlds.tiles import WEAPONS

COMES_BY = sec(5)                                                 # ticks: within this it has walked up and begun to rattle


def rattling(sim, sk):
    for _ in range(COMES_BY):
        sim.step()
        if sk.mode == "windup":
            return True
    return False


def test_it_walks_up_rattles_then_swipes_who_stays(world):
    sim, a = world
    night(sim)
    sk = put(sim, "skeleton", a.x + 4, a.y)
    assert rattling(sim, sk)
    assert max(abs(sk.x - a.x), abs(sk.y - a.y)) <= 1            # it walked up to us
    hp = a.hp
    for _ in range(sec(SK_WARN) - 2):
        sim.step()
    assert a.hp == hp                                             # the tell: nothing yet
    for _ in range(3):
        sim.step()
    assert a.hp == hp - CREATURES["skeleton"]["damage"]          # still beside it: swiped


def test_a_step_back_while_it_rattles_is_safe(world):
    sim, a = world
    night(sim)
    sk = put(sim, "skeleton", a.x + 1, a.y)
    assert rattling(sim, sk)
    a.x -= 2                                                      # back out of its reach
    hp = a.hp
    for _ in range(sec(SK_WARN) + 2):
        sim.step()
    assert a.hp == hp and sk.mode != "windup"


def test_by_day_it_is_gone(world):
    sim, a = world
    day(sim)
    sk = put(sim, "skeleton", a.x + 3, a.y)
    sim.step()
    assert sk.id not in sim.creatures
    assert any(e["type"] == "fade" and e.get("kind") == "skeleton" for e in a.events)


def test_it_comes_at_night_on_open_ground_three_spear_hits_and_leaves_bones(world):
    sim, a = world
    rule = WILD_SPAWNS["skeleton"]
    assert rule["night"] and "skeleton" in ROAMING
    x, y = a.x + 6, a.y + 6
    sim.set_tile(x, y, ground="grass", block="none")
    assert sim.spawn_spot_ok("skeleton", x, y, fresh=True)                  # open grass
    hp = CREATURES["skeleton"]["hp"]
    assert hp > 2 * WEAPONS["spear"] and hp <= 3 * WEAPONS["spear"]      # three hits of a spear
    assert ("bone", .9, 1, 3) in CREATURES["skeleton"]["drops"]
