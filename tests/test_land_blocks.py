"""A block of the land dug out is that block in the pack, put back it is the land again, and the material is a craft
("breaked blocks should stay blocks in inventory: not items. blocks -> item should be a craft")."""

import pytest
from helpers import make, run

from megastructure.floors import KINDS
from megastructure.landblocks import LAND_BLOCKS, natural
from megastructure.prompts import RULES, recipes_text, tools_text
from megastructure.tiles import BLOCKS, FILLERS, PLACEABLE, RECIPES


def flat(sim, a, level, r=4):
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            sim.world.set(a.x + dx, a.y + dy, ground="grass", block="none", level=level)


@pytest.mark.parametrize("level, item", [(0, "dirt"), (1, "dirt"), (2, "stone_block"), (7, "stone_block"), (-1, "stone_block"), (-9, "stone_block")])
def test_a_dug_cell_is_its_block_and_goes_back(world, level, item):
    sim, a = world
    flat(sim, a, level)
    x, y = a.x + 1, a.y
    r = run(sim, a, "dig", {"dir": "E", "z": level})
    assert r["ok"] and r["got"] == {item: 1} and a.inventory == {item: 1} and sim.world.top(x, y) == level - 1
    assert run(sim, a, "place", {"dir": "E", "item": item})["ok"]
    assert sim.world.top(x, y) == level and not a.count(item) and not sim.placed.at      # the land as it was: nothing to remember
    assert run(sim, a, "dig", {"dir": "E", "z": level})["got"] == {item: 1}


def test_dig_down_and_a_tunnel_give_the_block(world):
    sim, a = world
    flat(sim, a, 3)
    r = run(sim, a, "dig_down", {})
    assert r["ok"] and r["got"] == {"stone_block": 1} and a.count("stone_block") == 1 and not a.count("stone")
    a.add("pickaxe")
    r = run(sim, a, "dig", {"dir": "E", "with": "pickaxe"})                # (the wall of the pit: the cell in front)
    assert r["ok"] and r["got"] == {"stone_block": 1} and a.count("stone_block") == 2 and not a.count("stone")


def test_a_block_put_where_the_land_is_the_other_kind_stays_itself(world):
    sim, a = world
    flat(sim, a, 0)
    a.add("stone_block", 2); a.add("dirt", 3)
    x, y = a.x + 1, a.y
    assert run(sim, a, "place", {"dir": "E", "item": "stone_block"})["ok"] and sim.world.top(x, y) == 1      # stone on the meadow
    assert sim.placed.kind(x, y, 1) == "stone_block" and natural(1) == "dirt"
    assert sim.store.db.execute("SELECT kind FROM placed WHERE x=? AND y=? AND z=1", (x, y)).fetchone() == ("stone_block",)    # in the save
    assert run(sim, a, "dig", {"dir": "E", "z": 1})["got"] == {"stone_block": 1} and not sim.placed.at
    assert not sim.store.db.execute("SELECT 1 FROM placed").fetchone()
    for _ in range(3):                                                    # earth piled three high: earth at every layer
        assert run(sim, a, "place", {"dir": "W", "item": "dirt"})["ok"]
    assert [run(sim, a, "dig", {"dir": "W", "z": z})["got"] for z in (3, 2, 1)] == [{"dirt": 1}] * 3
    assert a.count("stone_block") == 2 and a.count("dirt") == 3


def test_a_put_block_is_still_itself_in_the_world_opened_again(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    flat(sim, a, 0)
    a.add("stone_block")
    x, y = a.x + 1, a.y
    assert run(sim, a, "place", {"dir": "E", "item": "stone_block"})["ok"]
    sim.close()
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    assert sim.placed.kind(x, y, 1) == "stone_block" and run(sim, a, "dig", {"dir": "E", "z": 1})["got"] == {"stone_block": 1}
    sim.close()


def test_a_stone_block_fills_water_as_earth_does(world):
    sim, a = world
    sim.world.set(a.x + 1, a.y, ground="water")
    a.add("stone_block", 1)
    assert run(sim, a, "place", {"dir": "E", "item": "stone_block"})["ok"] and sim.world.ground(a.x + 1, a.y) == "dirt"
    assert FILLERS["stone_block"] == FILLERS["dirt"]
    assert run(sim, a, "place", {"dir": "N", "item": "stone_block"})["error"] == "missing_item"


def test_stones_are_made_of_a_block(world):
    sim, a = world
    a.add("stone_block", 3)
    r = run(sim, a, "craft", {"recipe": "stone", "n": 2})                 # by hand, no bench
    assert r["ok"] and r["made"] == {"stone": 4} and a.count("stone_block") == 1 and a.count("stone") == 4
    assert run(sim, a, "craft", {"recipe": "stone", "n": 2})["error"] == "missing_items"
    assert RECIPES["stone"].station is None and RECIPES["stone"].output == {"stone": 2}
    assert run(sim, a, "place", {"dir": "E", "item": "stone"})["error"] == "not_placeable"     # the material is not a block


def test_what_was_built_comes_back_as_itself():
    """Every piece you can place gives itself when dug (a campfire: its stone, the wood is burnt; a seed: what grew;
    hay: the bale is hay), and a block built over the ground is its own kind (sim/storeys.py take_block)."""
    odd = {"campfire": {"stone": 1}, "seed": {"seed": 1}, "hay": {"hay": 1}}
    for item, block in PLACEABLE.items():
        drops = next(b for b in BLOCKS if b.name == block).drops
        assert drops == odd.get(item, {item: 1}), item
    assert set(KINDS) <= set(RECIPES) and not set(LAND_BLOCKS) & set(PLACEABLE)


def test_an_old_pack_keeps_its_stone_and_dirt(tmp_path):
    """A save from before: `stone` was the material and still is, `dirt` was the block of earth and still is."""
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    flat(sim, a, 0)
    a.inventory.clear(); a.inventory.update({"stone": 7, "dirt": 4, "wood": 2})
    sim.close()
    sim = make(tmp_path)
    b = sim.login("Ash", "tok")
    assert b.inventory == {"stone": 7, "dirt": 4, "wood": 2}
    assert run(sim, b, "craft", {"recipe": "path"})["ok"] and b.count("stone") == 5       # old stones still make things
    assert run(sim, b, "place", {"dir": "E", "item": "dirt"})["ok"] and sim.world.top(b.x + 1, b.y) == 1
    sim.close()


def test_the_agents_are_told():
    tools, book = tools_text(), recipes_text()
    assert "stone_block" in tools and "not a material" in tools and "stone_block" in RULES
    assert "stone = 1 stone_block" in book
