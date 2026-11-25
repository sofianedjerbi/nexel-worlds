"""The land's ores and the tools' tiers (ores.py, stone.py ore, sim/underground.py): ores lie in veins in their own
heights, from the seed alone; a pickaxe of the ore's tier or better keeps it, a lower one (or bare hands) breaks the
cell all the same and the ore crumbles (nobody is shut in by a vein); a higher tier digs faster; smelting takes coal;
an old save's generic ore and ingot are the iron ones; agents are told of the ore they can see."""

import collections

import pytest
from helpers import make, run

from nexel_worlds.ores import ORE_OF, ORES, TOOLS


def stone_under(sim, a, ore=None):
    """You on a stone column (laid five high: stone all down), and the cell under your feet that ore (or none)."""
    sim.set_tile(a.x, a.y, level=5)
    a.z = 5
    cell = (a.x, a.y, 5)
    sim.world.ore = lambda x, y, z: ORE_OF[ore] if ore and (x, y, z) == cell else None
    return cell


def test_ores_lie_in_their_own_heights_in_veins_and_come_from_the_seed_alone(world, tmp_path):
    sim, _ = world
    w, seen = sim.world, collections.Counter()
    for z in range(4, -513, -4):
        for x in range(0, 32, 2):
            for y in range(0, 32, 2):
                o = w.ore(x, y, z)
                if o:
                    assert o.bottom <= z <= o.top, (o.name, z)
                    seen[o.name] += 1
    assert set(seen) == {o.name for o in ORES}, seen                         # every ore is somewhere
    assert seen["titanium"] < seen["iron"] and seen["gold"] < seen["iron"]     # the precious ones rarer
    twin = make(tmp_path, "twin")                                             # another world of the same seed: the same ore, nothing kept
    assert [w.ore(5, 9, z) for z in range(0, -300, -1)] == [twin.world.ore(5, 9, z) for z in range(0, -300, -1)]
    twin.close()


@pytest.mark.parametrize("ore, tool, kept", [
    ("coal", None, False), ("coal", "wood_pickaxe", True),
    ("iron_ore", "wood_pickaxe", False), ("iron_ore", "pickaxe", True),
    ("titanium_ore", "pickaxe", False), ("titanium_ore", "iron_pickaxe", True), ("gold_ore", "titanium_pickaxe", True)])
def test_a_pickaxe_of_the_ores_tier_keeps_it_a_lower_one_breaks_it_and_it_crumbles(world, ore, tool, kept):
    sim, a = world
    stone_under(sim, a, ore)
    if tool:
        a.add(tool)
    r = run(sim, a, "dig_down", {"with": tool} if tool else {})
    assert r["ok"] and sim.height(a) < 5                                      # the cell went, whatever the tool: you came down
    assert (a.count(ore) == 1) == kept, r
    assert ("lost" in r) != kept and r["got"] == ({ore: 1} if kept else {}), r


def test_a_higher_tier_digs_faster(world):
    sim, a = world
    took = {}
    for tool in ("wood_pickaxe", "pickaxe", "iron_pickaxe", "titanium_pickaxe"):
        stone_under(sim, a)
        a.add(tool)
        t0 = sim.tick
        assert run(sim, a, "dig_down", {"with": tool})["ok"]
        took[tool] = sim.tick - t0
    assert took["wood_pickaxe"] > took["pickaxe"] > took["iron_pickaxe"] > took["titanium_pickaxe"], took
    assert all(TOOLS[t][0] == "pickaxe" for t in took)


def test_smelting_takes_an_ore_and_coal_at_a_fire_and_gold_is_coins(world):
    sim, a = world
    sim.set_tile(a.x + 1, a.y, block="campfire")
    a.add("iron_ore", 1); a.add("gold_ore", 1); a.add("coal", 2)
    assert run(sim, a, "craft", {"recipe": "iron_ingot"})["ok"] and a.count("iron_ingot") == 1
    assert run(sim, a, "craft", {"recipe": "gold_coin"})["ok"] and a.count("gold_coin") == 3
    assert a.count("coal") == 0 and not run(sim, a, "craft", {"recipe": "copper_ingot"})["ok"]   # (no copper, no coal left)


def test_an_old_saves_ore_and_ingot_are_the_iron_ones(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Old", "tok")
    a.inventory.update({"ore": 3, "ingot": 2, "iron_ore": 1})
    sim.items[(a.x + 2, a.y)] = {"ore": 1}
    sim.dirty_items.add((a.x + 2, a.y))
    sim.flush(); sim.close()
    sim = make(tmp_path)
    a = sim.by_name["Old"]
    assert a.inventory.get("iron_ore") == 4 and a.inventory.get("iron_ingot") == 2 and "ore" not in a.inventory
    assert sim.items[(a.x + 2, a.y)] == {"iron_ore": 1}
    sim.close()


def test_an_agent_is_told_of_the_ore_it_can_see_not_what_is_shut_in_the_rock(world):
    sim, a = world
    stone_under(sim, a)
    for i in range(1, 4):
        for j in (-1, 0, 1):
            sim.set_tile(a.x + i, a.y + j, level=5)                           # stone east of you, five high: its top cells open to the sky
    shown, hidden = (a.x + 1, a.y, 5), (a.x + 2, a.y, 3)                     # (the second: stone on every side of it)
    sim.world.ore = lambda x, y, z: ORE_OF["iron_ore"] if (x, y, z) in (shown, hidden) else None
    ores = sim.observe(a)["ores"]
    assert ores == [{"dx": 1, "dy": 0, "z": 5, "ore": "iron_ore"}], ores
