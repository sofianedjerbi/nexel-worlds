"""Digging, tools, placing, crafting and structures."""

from helpers import run


def test_dig_tree_and_ground(world):
    sim, a = world
    sim.world.set(a.x, a.y - 1, block="tree")
    r = run(sim, a, "dig", {"dir": "N"})
    assert r["ok"] and r["changed"]["inventory"] == {"wood": 3}
    assert sim.world.block(a.x, a.y - 1) == "stump"                    # a felled tree leaves its stump
    assert r["changed"]["tiles"][0]["block"] == "stump"
    assert run(sim, a, "dig", {"dir": "N"})["changed"]["inventory"] == {"wood": 1}
    assert sim.world.block(a.x, a.y - 1) == "none"
    assert run(sim, a, "dig", {"dir": "S"})["error"] == "need_tool"          # tilling needs a hoe in hand
    a.add("hoe", 1)
    r = run(sim, a, "dig", {"dir": "S", "with": "hoe"})
    assert r["ok"] and sim.world.ground(a.x, a.y + 1) == "tilled" and not a.count("dirt")

def test_node_needs_drill(world):
    sim, a = world
    sim.world.set(a.x + 1, a.y, block="ore")
    r = run(sim, a, "dig", {"dir": "E"})
    assert r["error"] == "need_tool"
    a.add("pickaxe", 1)
    assert run(sim, a, "dig", {"dir": "E"})["error"] == "need_tool"      # in the bag is not in hand
    assert run(sim, a, "dig", {"dir": "E", "with": "pickaxe"})["ok"]

def test_craft_and_place(world):
    sim, a = world
    a.add("wood", 10)
    r = run(sim, a, "craft", {"recipe": "workbench"})
    assert r["ok"] and a.count("workbench") == 1 and a.count("wood") == 6
    assert run(sim, a, "place", {"dir": "N", "item": "workbench"})["ok"]
    assert sim.world.block(a.x, a.y - 1) == "workbench"
    r = run(sim, a, "craft", {"recipe": "axe"})
    assert r["error"] == "missing_items"
    a.add("stone", 2)
    a.add("fiber", 1)
    assert run(sim, a, "craft", {"recipe": "axe"})["ok"] and a.count("axe") == 1

def test_station_required(world):
    sim, a = world
    a.add("meat", 1)
    assert run(sim, a, "craft", {"recipe": "cooked_meat"})["error"] == "need_station"

def test_fill_breach_and_flood(world):
    sim, a = world
    # coolant to the north-north; dig the tile between -> it floods
    sim.world.set(a.x, a.y - 2, ground="water")
    a.add("hoe", 1)
    assert run(sim, a, "dig", {"dir": "N", "with": "hoe"})["ok"]
    for _ in range(400):
        sim.step()
        if sim.world.ground(a.x, a.y - 1) == "water":
            break
    assert sim.world.ground(a.x, a.y - 1) == "water"
    a.add("dirt", 1)
    assert run(sim, a, "place", {"dir": "N", "item": "dirt"})["ok"]
    assert sim.world.ground(a.x, a.y - 1) == "dirt"

def test_placement_rules_are_one_item_one_result(world):
    sim, a = world
    a.add("stone", 1); a.add("path", 1); a.add("plank", 2)
    assert run(sim, a, "place", {"dir": "N", "item": "stone"})["error"] == "not_placeable"
    assert run(sim, a, "place", {"dir": "N", "item": "path"})["ok"] and sim.world.ground(a.x, a.y - 1) == "cobble"
    assert run(sim, a, "place", {"dir": "E", "item": "plank"})["ok"] and sim.world.ground(a.x + 1, a.y) == "floor"
    sim.world.set(a.x, a.y + 1, ground="water")
    assert run(sim, a, "place", {"dir": "S", "item": "plank"})["ok"] and sim.world.ground(a.x, a.y + 1) == "bridge"

def test_flowers_are_picked_when_building_and_floors_come_back_up(world):
    sim, a = world
    sim.world.set(a.x, a.y - 1, block="flower")
    a.add("chair", 1); a.add("path", 1)
    assert run(sim, a, "place", {"dir": "N", "item": "chair"})["ok"] and a.count("flower") == 1
    assert run(sim, a, "place", {"dir": "E", "item": "path"})["ok"]
    r = run(sim, a, "dig", {"dir": "E"})
    assert r["changed"]["inventory"] == {"path": 1} and sim.world.ground(a.x + 1, a.y) == "dirt"

def test_a_walled_room_is_sheltered(world):
    sim, a = world
    for dx in range(-2, 3):
        for dy in (-2, 2):
            sim.world.set(a.x + dx, a.y + dy, block="wood_wall")
    for dy in range(-1, 2):
        sim.world.set(a.x - 2, a.y + dy, block="wood_wall")
        sim.world.set(a.x + 2, a.y + dy, block="door" if dy == 0 else "wood_wall")
    assert sim.sheltered(a.x, a.y)
    sim.world.set(a.x + 2, a.y, block="none")      # an open doorway is not a room
    assert not sim.sheltered(a.x, a.y)

def test_well_is_two_by_two_and_fills_the_can(world):
    sim, a = world
    a.add("well", 1)
    r = run(sim, a, "place", {"dir": "N", "item": "well"})
    assert r["ok"] and r["at"] == [a.x, a.y - 1]
    assert {sim.world.block(a.x + i, a.y - 1 - j) for i in (0, 1) for j in (0, 1)} == {"well", "part"}
    assert not sim.world.passable(a.x + 1, a.y - 2)
    a.add("watering_can", 1)
    a.can = 0
    sim.world.set(a.x, a.y + 1, ground="tilled", block="sprout")
    assert run(sim, a, "water", {"dir": "S", "with": "watering_can"})["error"] == "empty"
    a.x += 1   # the well's right half is the well too
    assert run(sim, a, "water", {"dir": "N", "with": "watering_can"})["can"] == 12
    a.x -= 1
    assert run(sim, a, "water", {"dir": "S", "with": "watering_can"})["can"] == 11
    a.add("pickaxe", 1)
    a.x += 1
    assert run(sim, a, "dig", {"dir": "N"})["ok"] and a.count("well") == 1
    assert all(sim.world.block(a.x - 1 + i, a.y - 1 - j) == "none" for i in (0, 1) for j in (0, 1))

def test_structure_needs_room_and_you_outside(world):
    sim, a = world
    a.add("picnic_blanket", 1)
    sim.world.set(a.x + 1, a.y - 2, block="rock")       # blanket 3x2 centred on the N tile hits it
    assert run(sim, a, "place", {"dir": "N", "item": "picnic_blanket"})["error"] == "occupied"
    sim.world.set(a.x + 1, a.y - 2, block="none")
    assert run(sim, a, "place", {"dir": "N", "item": "picnic_blanket"})["ok"]
    assert sim.world.block(a.x - 1, a.y - 1) == "picnic_blanket" and sim.world.passable(a.x + 1, a.y - 2)

def test_picnic_and_basket(world):
    sim, a = world
    a.add("picnic_blanket", 1)
    run(sim, a, "place", {"dir": "N", "item": "picnic_blanket"})
    a.y -= 2                                              # sit on the back row (a part tile)
    a.hunger, a.inventory["bread"] = 10, 1
    assert run(sim, a, "eat", {"item": "bread"})["picnic"] and a.hunger == 10 + 75     # bread 50, x1.5 on a blanket
    a.y += 2
    a.add("basket", 1); a.add("fiber", 2)
    run(sim, a, "place", {"dir": "S", "item": "basket"})
    assert run(sim, a, "store", {"dir": "S", "item": "fiber", "n": 2})["ok"]
    assert run(sim, a, "dig", {"dir": "S"})["ok"] and a.count("fiber") == 2 and a.count("basket") == 1

def test_structures_extend_away_from_the_placer(world):
    sim, a = world
    a.add("well", 2)
    assert run(sim, a, "place", {"dir": "S", "item": "well"})["at"] == [a.x, a.y + 2]   # facing south: grows south
    assert run(sim, a, "place", {"dir": "W", "item": "well"})["at"] == [a.x - 2, a.y]   # facing west: grows west

def test_bare_hands_are_slow_on_wood_and_stone(world):
    sim, a = world
    a.add("axe", 1); a.add("pickaxe", 1)
    def time(block, **args):
        sim.world.set(a.x + 1, a.y, block=block)
        return run(sim, a, "dig", {"dir": "E", **args})["ticks"]
    assert time("tree", **{"with": "axe"}) * 3 < time("tree")            # 4x by hand
    assert time("rock", **{"with": "pickaxe"}) * 5 < time("rock")        # 6x by hand
    assert time("berry_bush") <= 4                                      # soft things stay quick

def test_sign_and_locker(world):
    sim, a = world
    a.add("sign", 1)
    a.add("chest", 1)
    a.add("ore", 2)
    run(sim, a, "place", {"dir": "N", "item": "sign"})
    run(sim, a, "write_sign", {"dir": "N", "text": "keep out"})
    assert run(sim, a, "read_sign", {"dir": "N"})["text"] == "keep out"
    assert run(sim, a, "place", {"dir": "E", "item": "chest"})["ok"]
    assert run(sim, a, "store", {"dir": "E", "item": "ore", "n": 2})["chest"] == {"ore": 2}
    # anyone can break it open and loot the contents
    b = sim.login("Thief", "x")
    b.x, b.y = a.x + 2, a.y
    r = run(sim, b, "dig", {"dir": "W"})
    assert r["ok"] and b.count("ore") == 2 and b.count("chest") == 1
