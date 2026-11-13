"""Experience (mining ore, crafting, hunting) and the item magnet."""

from helpers import run
from megastructure.sim import Creature
from megastructure.sim.constants import sec
from megastructure.sim.progress import MAGNET_DELAY, level_of


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


def test_every_thing_that_can_be_made_has_a_line_about_it():
    """The recipe book says a word about each thing (web/js/blurbs.js): one for every recipe, no two alike, short enough
    for its two lines."""
    import re
    from pathlib import Path

    from megastructure.tiles import RECIPES
    text = (Path(__file__).parent.parent / "src/megastructure/web/js/blurbs.js").read_text()
    blurbs = dict(re.findall(r'^  (\w+): "((?:[^"\\]|\\.)*)",$', text, re.M))
    assert set(blurbs) == set(RECIPES), (set(RECIPES) - set(blurbs), set(blurbs) - set(RECIPES))
    assert len(set(blurbs.values())) == len(blurbs)
    assert all(8 <= len(b) <= 50 and b[-1] in ".?!" for b in blurbs.values()), [b for b in blurbs.values() if not 8 <= len(b) <= 50]
