"""Nyxwing, the boss of "Sugar rush" (sim/nyxwing.py)."""

from test_wild import put

from nexel_worlds.sim import CREATURES, sec
from nexel_worlds.sim.nyxwing import ARRIVE, BEAT, LEAVES, REST, RAGE_REST, SKY, WARN


def run(sim, seconds):
    for _ in range(sec(seconds)):
        sim.step()


def landed(sim, a, dx=6, dy=0):
    """One that has made its entrance, dx, dy from a."""
    c = put(sim, "nyxwing", a.x + dx, a.y + dy)
    sim.step()
    c.mode, c.until, c.rest = "", 1, sim.tick + sec(60)        # (down, and not attacking until a test says so)
    return c


def events(a, kind, what=None):
    return [e for e in a.events if e["type"] == kind and (what is None or e.get("what") == what)]


def test_it_comes_down_out_of_the_sky_on_the_drop_and_nothing_touches_it_meanwhile(world):
    sim, a = world
    c = put(sim, "nyxwing", a.x + 6, a.y)
    sim.step()
    assert c.mode == "arrive" and events(a, "boss", "arrive")
    sim.damage(c, sim.shell(c, 10), "test", by=a)                # (a blow, as combat.py lands one)
    assert c.hp == CREATURES["nyxwing"]["hp"]
    run(sim, ARRIVE - 1)
    assert c.mode == "arrive"
    run(sim, 1.1)
    assert c.mode == "" and events(a, "boss", "land")           # 32 beats: the end of the song's rise, its drop


def test_it_is_three_tiles_wide_and_flies_over_anything(world):
    sim, a = world
    c = landed(sim, a, 6, 0)
    assert all(sim.entity_at(c.x + i, c.y) is c for i in (-1, 0, 1)) and sim.entity_at(c.x + 2, c.y) is None
    assert sim._nyx_fly(c, c.x, c.y + 1) and c.y == a.y + 1      # (no ground it needs: it flies)


def test_between_attacks_it_circles_whoever_it_hunts(world):
    sim, a = world
    c = landed(sim, a, 6, 0)
    seen = set()
    for _ in range(sec(6)):
        sim.step()
        seen.add((c.x - a.x > 0, c.y - a.y > 0))
        assert max(abs(c.x - a.x), abs(c.y - a.y)) >= 2            # round you, not onto you
    assert len(seen) >= 3                                         # it went round


def test_it_warns_a_beat_and_a_half_then_breathes_a_cone_four_tiles_long(world):
    sim, a = world
    c = landed(sim, a, -4, 0)                                     # you, four tiles to its east, in its line
    c.rest = sim.tick
    sim.step()
    assert c.mode in ("breath", "storm") and events(a, "windup")
    c.mode, c.dir, c.until = "breath", (1, 0), sim.tick + sec(WARN)
    hp = a.hp
    run(sim, WARN - 0.05)
    assert a.hp == hp                                             # the warning hurts nobody
    run(sim, 0.1)
    assert a.hp == hp - CREATURES["nyxwing"]["damage"] and events(a, "boss", "breath")


def test_out_of_the_cone_the_breath_misses(world):
    sim, a = world
    c = landed(sim, a, -2, 3)                                     # two along, three across: out of it
    c.mode, c.dir, c.until = "breath", (1, 0), sim.tick
    hp = a.hp
    sim.step()
    assert a.hp == hp


def test_three_rings_of_stars_on_three_beats_and_the_gaps_are_safe(world):
    sim, a = world
    c = landed(sim, a, -5, 0)                                     # due east of it, five tiles: on a star of rings 0 and 2,
    c.mode, c.until, c.left = "storm", sim.tick, 0               # in a gap of ring 1 (turned half a gap)
    hp = a.hp
    run(sim, 2 * BEAT + 0.1)
    assert len(events(a, "boss", "ring")) == 3 and c.mode == ""
    assert a.hp == hp - 2 * CREATURES["nyxwing"]["star"]


def test_the_sweep_hurts_everyone_near_and_throws_them_back(world):
    sim, a = world
    c = landed(sim, a, -2, 0)
    c.mode, c.until = "sweep", sim.tick
    x, hp = a.x, a.hp
    sim.step()
    assert a.hp == hp - CREATURES["nyxwing"]["sweep"] and a.x == x + 1


def test_the_dive_goes_up_hunts_you_with_its_shadow_and_falls_on_you(world):
    sim, a = world
    c = landed(sim, a, -6, 0)
    c.mode, c.until = "dive", sim.tick
    sim.step()
    assert c.mode == "sky" and events(a, "boss", "up")
    hp = a.hp
    sim.damage(c, sim.shell(c, 10), "test", by=a)                # nothing reaches it up there
    assert c.hp == CREATURES["nyxwing"]["hp"]
    run(sim, SKY + 0.2)
    assert events(a, "boss", "crash") and c.mode == ""
    assert abs(c.x - a.x) <= 2 and a.hp == hp - CREATURES["nyxwing"]["crash"]     # its shadow caught up: it fell on you


def test_below_half_it_roars_once_and_attacks_twice_as_often(world):
    sim, a = world
    c = landed(sim, a, 5, 0)
    c.hp, c.rest = CREATURES["nyxwing"]["hp"] // 2 - 1, sim.tick
    sim.step()
    assert c.mode == "rush"
    run(sim, WARN + 0.1)
    assert events(a, "boss", "roar") and c.awake == 1
    assert c.rest - sim.tick <= sec(RAGE_REST) < sec(REST)
    c.rest = sim.tick
    sim.step()
    assert c.mode not in ("", "rush")                             # it roars once only


def test_alone_it_goes_back_to_the_night(world):
    sim, a = world
    c = landed(sim, a, 6, 0)
    a.x += 60
    run(sim, LEAVES + 1)
    assert c.id not in sim.creatures                              # (nobody near to hear it go)


def test_killed_it_leaves_its_eclipse_core(world):
    sim, a = world
    c = landed(sim, a, 3, 0)
    sim.damage(c, c.hp, "test", by=a)
    assert c.id not in sim.creatures
    died = events(a, "creature_died")
    assert died and died[-1]["kind"] == "nyxwing" and died[-1]["drops"] == {"eclipse_core": 1}
