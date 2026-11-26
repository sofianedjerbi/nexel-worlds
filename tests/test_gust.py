"""The gustling (sim/gust.py): a little whirlwind that snatches what is in your hand, and runs."""

from helpers import clear, run
from test_wild import put

from nexel_worlds.sim import sec

def holding(a, item="wood", n=10):
    a.add(item, n)
    a.held = item


def test_the_gustling_spins_up_then_snatches_what_is_in_your_hand_and_runs(world):
    sim, a = world
    clear(sim, a)
    holding(a)
    gust = put(sim, "gustling", a.x + 1, a.y)
    sim.step()
    assert gust.mode == "windup" and gust.dir == (-1, 0)          # the warning: it draws up and spins, facing you
    assert any(e["type"] == "windup" and e["id"] == gust.id for e in a.events)
    assert a.count("wood") == 10                                  # nothing taken yet: time to hit it, or step away
    for _ in range(sec(0.7)):
        sim.step()
    assert a.count("wood") == 5 and gust.loot == {"wood": 5}      # it took five of what you held
    assert gust.mode == "flee" and any(e["type"] == "snatch" and e["item"] == "wood" for e in a.events)
    for _ in range(sec(2)):
        sim.step()
    assert max(abs(gust.x - a.x), abs(gust.y - a.y)) >= 4         # and ran off with it
    assert a.hp == 20                                             # it never hurts anyone (tests/e2e/test_e2e_wild.py's gustling)


def test_an_empty_hand_is_left_alone(world):
    sim, a = world
    clear(sim, a)
    a.add("wood", 10)                                             # in the bag, not in the hand
    gust = put(sim, "gustling", a.x + 1, a.y)
    for _ in range(sec(3)):
        sim.step()
    assert a.count("wood") == 10 and not gust.loot
    assert not any(e["type"] == "windup" and e.get("id") == gust.id for e in a.events)


def test_step_away_during_the_spin_and_it_takes_nothing(world):
    sim, a = world
    clear(sim, a)
    holding(a)
    gust = put(sim, "gustling", a.x + 1, a.y)
    sim.step()
    assert gust.mode == "windup"
    a.x -= 2                                                      # out of its reach before it lands
    for _ in range(sec(0.7)):
        sim.step()
    assert a.count("wood") == 10 and not gust.loot


def test_hit_while_it_spins_it_scatters_and_drops_what_it_carried(world):
    sim, a = world
    clear(sim, a)
    holding(a)
    gust = put(sim, "gustling", a.x + 1, a.y, loot={"egg": 2})   # it has been at someone else already
    sim.step()
    assert gust.mode == "windup"
    assert run(sim, a, "attack", {"target": gust.id})["ok"]        # one blow, bare fists: it blows apart
    assert gust.id not in sim.creatures
    assert any(e["type"] == "scatter" for e in a.events)
    assert sim.items.get((gust.x, gust.y), {}).get("egg") == 2     # what it carried falls where it was
    assert a.count("wood") == 10


def test_hit_any_other_time_it_runs(world):
    sim, a = world
    clear(sim, a)
    gust = put(sim, "gustling", a.x + 1, a.y)                     # nothing in your hand: it was only passing
    assert run(sim, a, "attack", {"target": gust.id})["ok"]
    assert gust.id in sim.creatures and gust.mode == "flee"


def test_gustlings_are_rare_roaming_day_spawns():
    from nexel_worlds.sim.spawning import ROAMING, WILD_SPAWNS
    w = WILD_SPAWNS["gustling"]
    assert w["day"] and w["cap"] == 1 and w["every"] >= sec(300)  # by day, one at a time, a long while between tries
    assert "gustling" in ROAMING                                  # it comes and goes like the tusker
