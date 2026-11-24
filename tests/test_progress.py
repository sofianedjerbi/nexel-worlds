"""Experience (mining ore, crafting, hunting) and the item magnet."""

from helpers import run
from nexel_worlds.sim import Creature
from nexel_worlds.sim.constants import sec
from nexel_worlds.sim.progress import MAGNET_DELAY, level_of


def test_levels_get_longer():
    assert level_of(0) == (0, 0, 7)
    assert level_of(7) == (1, 0, 10)
    assert level_of(16) == (1, 9, 10)
    assert level_of(17)[0] == 2


def test_ore_and_hunting_give_experience_and_other_blocks_none(world):
    sim, a = world
    a.add("pickaxe")
    a.add("axe")
    for block, tool in (("tree", "axe"), ("rock", "pickaxe"), ("stump", "axe"), ("ripe_crop", None)):     # (they gave 2, 1, 1, 2)
        sim.world.set(a.x + 1, a.y, block=block)
        assert run(sim, a, "dig", {"dir": "E", **({"with": tool} if tool else {})})["ok"]
        assert a.xp == 0, block
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["ok"] and a.xp == 0                              # (2)
    sim.world.set(a.x + 1, a.y, block="ore")
    assert run(sim, a, "dig", {"dir": "E", "with": "pickaxe"})["ok"]
    assert a.xp == 4
    hen = Creature(sim.next_creature, "chicken", a.x + 1, a.y, 10); sim.next_creature += 1
    sim.creatures[hen.id] = hen
    sim.kill_creature(hen, a)
    assert a.xp == 6
    assert sim.observe(a)["self"]["level"] == 0


def test_items_next_to_you_come_to_you_after_a_moment(world):
    sim, a = world
    sim.add_items(a.x + 1, a.y + 1, {"stone": 2})
    sim.add_items(a.x + 3, a.y, {"wood": 1})                 # too far
    sim.step()
    assert a.count("stone") == 0                             # it has to land first
    for _ in range(MAGNET_DELAY + 2):
        sim.step()
    assert a.count("stone") == 2 and (a.x + 1, a.y + 1) not in sim.items
    for _ in range(sec(3)):
        sim.step()
    assert a.count("wood") == 0 and (a.x + 3, a.y) in sim.items


def test_what_you_drop_stays_down_until_you_step_away_and_back(world):
    """A drop came straight back by the magnet (1.2 s): now it lies there for F, or for anyone else."""
    sim, a = world
    a.add("stone", 3)
    run(sim, a, "drop", {"item": "stone", "n": 2})
    for _ in range(MAGNET_DELAY + sec(2)):
        sim.step()
    assert a.count("stone") == 1 and sim.items[(a.x, a.y)] == {"stone": 2}
    run(sim, a, "pick_up", {})
    assert a.count("stone") == 3 and (a.x, a.y) not in sim.items
    run(sim, a, "drop", {"item": "stone", "n": 1})
    at, a.x = (a.x, a.y), a.x + 4                            # away...
    sim.step(); sim.step()
    a.x = at[0]                                              # ...and back: it comes to you as any pile does
    for _ in range(MAGNET_DELAY + 4):
        sim.step()
    assert a.count("stone") == 3 and at not in sim.items
    if sim.can_go(a, a.x + 1, a.y):                          # with dir: on the tile in front, if you could step there
        run(sim, a, "drop", {"item": "stone", "n": 1, "dir": "E"})
        assert sim.items[(a.x + 1, a.y)] == {"stone": 1} and (a.x, a.y) not in sim.items


def test_every_thing_that_can_be_made_has_a_line_about_it():
    """The recipe book says a word about each thing (web/js/blurbs.js): one for every recipe, no two alike, short enough
    for its two lines."""
    import re
    from pathlib import Path

    from nexel_worlds.tiles import RECIPES
    text = (Path(__file__).parent.parent / "src/nexel_worlds/web/js/blurbs.js").read_text()
    blurbs = dict(re.findall(r'^  (\w+): "((?:[^"\\]|\\.)*)",$', text, re.M))
    found = {"wood", "stone", "fiber", "ore", "dirt", "stone_block", "seed", "berries", "fruit", "mushroom", "egg", "milk", "meat", "wheat", "pumpkin", "cauliflower", "lettuce",
             "eggplant", "carrot", "flower", "shell_plate"}          # what is not made has its line too (the inventory shows it)
    assert set(blurbs) == set(RECIPES) | found, (set(RECIPES) | found - set(blurbs), set(blurbs) - set(RECIPES) - found)
    assert len(set(blurbs.values())) == len(blurbs)
    assert all(8 <= len(b) <= 50 and b[-1] in ".?!" for b in blurbs.values()), [b for b in blurbs.values() if not 8 <= len(b) <= 50]


def test_a_creature_does_not_leave_the_same_thing_every_time(world):
    """A chicken always left a meat and an egg. Now its usual drops are by chance, and once in a long while it leaves
    something rare; the boss's drops are sure."""
    import random

    from nexel_worlds.sim import CREATURES
    from nexel_worlds.sim.entities import roll_drops
    sim, a = world
    rng, n = random.Random(3), 2000
    got = [roll_drops("chicken", rng) for _ in range(n)]
    meat, egg, rare = (sum(1 for d in got if k in d) / n for k in ("meat", "egg", "heart_charm"))
    assert .55 < meat < .65 and .11 < egg < .19 and .008 < rare < .035
    assert sum(1 for d in got if not d) > n / 4                              # often nothing at all
    for kind, c in CREATURES.items():
        assert all(0 < ch <= 1 and 1 <= lo <= hi for _, ch, lo, hi in c["drops"]), kind
        if kind not in ("wisp", "chick", "calf", "mossback"):
            assert min(ch for _, ch, _, _ in c["drops"]) <= .1, kind         # each has its rare one
    assert roll_drops("mossback", rng) == {"shell_plate": 5, "meat": 6, "fruit": 4, "mushroom": 3}
    sim.luck = 1000                                                          # (the tests' switch: every line)
    hen = Creature(sim.next_creature, "chicken", a.x + 3, a.y, 10); sim.next_creature += 1
    sim.creatures[hen.id] = hen
    seen = []
    sim.listeners.append(lambda e: e["type"] == "creature_died" and seen.append(e["drops"]))
    sim.kill_creature(hen, a)
    assert seen == [{"meat": 1, "egg": 1, "heart_charm": 1}] == [sim.items[(a.x + 3, a.y)]]


def test_a_pile_is_taken_one_way_and_what_you_can_make_is_said_once(world):
    """Items.take_pile (walked over, drawn in, picked up) and tiles.can_craft (the craft, and what you are told)."""
    from nexel_worlds.tiles import RECIPES, can_craft
    sim, a = world
    a.add("stone", 2)
    if sim.can_go(a, a.x + 1, a.y):
        run(sim, a, "drop", {"item": "stone", "n": 1, "dir": "E"})
        run(sim, a, "step", {"dir": "E"})                    # onto what you let go of: it stays down (it came straight back)
        assert a.count("stone") == 1 and sim.items[(a.x, a.y)] == {"stone": 1}
        assert run(sim, a, "pick_up", {"item": "wood"})["error"] == "nothing_here" and run(sim, a, "pick_up", {})["got"] == {"stone": 1}
    sim.add_items(a.x, a.y - 1, {"wood": 5})
    run(sim, a, "step", {"dir": "N"})                        # somebody else's, or the land's: walked over, taken
    assert a.count("wood") == 5 and (a.x, a.y) not in sim.items
    axe = RECIPES["axe"]
    assert can_craft(axe, {"wood": 5, "stone": 2, "fiber": 1}) == {"ok": False, "n": 1, "missing": {}, "station": "workbench"}
    assert can_craft(axe, {"wood": 5, "stone": 2}, ["workbench"], 2) == {"ok": False, "n": 0, "missing": {"stone": 2, "fiber": 2}, "station": None}
    me = sim.observe(a)["self"]
    assert me["stations"] == [] and me["craftable"]["plank"] == 5 and "axe" not in me["craftable"]
    sim.world.set(a.x + 1, a.y, block="workbench")
    a.add("fiber", 1)
    assert sim.observe(a)["self"]["stations"] == ["workbench"] and sim.observe(a)["self"]["craftable"]["axe"] == 1
    assert run(sim, a, "craft", {"recipe": "axe", "n": 2})["error"] == "missing_items" and run(sim, a, "craft", {"recipe": "axe"})["made"] == {"axe": 1}
