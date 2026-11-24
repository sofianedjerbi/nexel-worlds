"""The hob (sim/hob.py): made, set down, yours; it follows you and burns the wild things that come close."""

from helpers import clear, make, run
from test_wild import put

from nexel_worlds.sim import sec
from nexel_worlds.sim.hob import HOB_BURN


def hob_for(sim, a):
    """Make one at a workbench and set it down east of us."""
    a.add("wood", 4)
    assert run(sim, a, "craft", {"recipe": "workbench"})["ok"]
    assert run(sim, a, "place", {"dir": "N", "item": "workbench"})["ok"]
    a.add("stone", 8)
    a.add("campfire", 1)
    assert run(sim, a, "craft", {"recipe": "hob"})["ok"] and a.count("hob") == 1
    r = run(sim, a, "place", {"dir": "E", "item": "hob"})
    assert r["ok"] and a.count("hob") == 0
    hob = sim.creatures[r["hob"]]
    assert hob.kind == "hob" and hob.owner == a.id and (hob.x, hob.y) == (a.x + 1, a.y)
    return hob


def test_a_hob_is_made_set_down_and_yours(world):
    sim, a = world
    hob_for(sim, a)
    assert any(e["type"] == "hob_lit" for e in a.events)


def test_it_burns_the_wild_ones_that_come_close_and_they_run(world):
    sim, a = world
    hob = hob_for(sim, a)
    stump = put(sim, "grumblestump", hob.x + 2, hob.y)
    hen = put(sim, "chicken", hob.x, hob.y + 1)
    hp, stump_hp, hen_hp = a.hp, stump.hp, hen.hp
    for _ in range(sec(0.6)):                                     # (it looks about twice a second)
        sim.step()
        if hob.mode == "windup":
            break
    assert hob.mode == "windup"                                   # it saw it: it hunches, its fire draws in
    for _ in range(sec(0.7)):
        sim.step()
    assert stump.hp == stump_hp - HOB_BURN and stump.mode == "flee"   # burnt, and off it goes
    assert any(e["type"] == "flare" and ["grumblestump", stump.id] in e["burnt"] for e in a.events)
    assert hen.hp == hen_hp and a.hp == hp                        # never a person, never an animal


def test_it_follows_its_owner(world):
    sim, a = world
    hob = hob_for(sim, a)
    a.x += 6
    for _ in range(sec(5)):
        sim.step()
    assert max(abs(hob.x - a.x), abs(hob.y - a.y)) <= 2


def test_it_is_still_yours_after_a_restart(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    clear(sim, a)
    sim.keep_loaded = False
    hob = hob_for(sim, a)
    sim.flush()
    sim.close()
    again = make(tmp_path)
    assert again.creatures[hob.id].kind == "hob" and again.creatures[hob.id].owner == a.id
    again.close()
