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
    sim.world.set(a.x + 1, a.y, block="rock")                          # a rock gives two stones (tests/e2e/test_e2e_build.py's X)
    a.add("pickaxe", 1)
    assert run(sim, a, "dig", {"dir": "E", "with": "pickaxe"})["changed"]["inventory"] == {"stone": 2}
    assert sim.world.block(a.x + 1, a.y) == "none"
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
    # water to the north-north; dig the cell between -> the water runs into it (flow.py), a level under the river
    sim.world.set(a.x, a.y - 2, ground="water")
    a.add("pickaxe", 1)
    assert run(sim, a, "dig", {"dir": "N", "z": 0, "with": "pickaxe"})["ok"]
    for _ in range(40):
        sim.step()
        if sim.water.lv(a.x, a.y - 1, 0):
            break
    assert sim.water.lv(a.x, a.y - 1, 0) == 7
    got = next(k for k in ("dirt", "stone_block") if a.count(k))
    assert run(sim, a, "place", {"dir": "N", "item": got})["ok"]          # put back: the water there is gone
    assert sim.world.level(a.x, a.y - 1) == 0 and not sim.water.lv(a.x, a.y - 1, 0)
    a.add("dirt", 1)
    assert run(sim, a, "place", {"x": a.x, "y": a.y - 2, "item": "dirt"})["ok"]     # and the river's own tile filled
    assert sim.world.ground(a.x, a.y - 2) == "dirt"


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
    assert not sim.stand(a.x + 1, a.y - 2)
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
    assert sim.world.block(a.x - 1, a.y - 1) == "picnic_blanket" and sim.stand(a.x + 1, a.y - 2)

def test_picnic_and_basket(world):
    sim, a = world
    a.add("picnic_blanket", 1)
    run(sim, a, "place", {"dir": "N", "item": "picnic_blanket"})
    a.y -= 2                                              # sit on the back row (a part tile)
    a.hunger, a.inventory["bread"] = 2, 1
    assert run(sim, a, "eat", {"item": "bread"})["picnic"] and a.hunger == 2 + 15      # bread 10, x1.5 on a blanket
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
    a.add("sign", 1)                                                   # a sign goes up with its words ("write when placing")
    assert run(sim, a, "place", {"dir": "W", "item": "sign", "text": "  fresh eggs  "})["ok"]
    assert run(sim, a, "read_sign", {"dir": "W"})["text"] == "fresh eggs"
    assert run(sim, a, "place", {"dir": "E", "item": "chest"})["ok"]
    assert run(sim, a, "store", {"dir": "E", "item": "ore", "n": 2})["chest"] == {"ore": 2}
    # anyone can break it open and loot the contents
    b = sim.login("Thief", "x")
    b.x, b.y = a.x + 2, a.y
    r = run(sim, b, "dig", {"dir": "W"})
    assert r["ok"] and b.count("ore") == 2 and b.count("chest") == 1


def test_aimed_by_x_and_y_a_refusal_is_said_and_a_bug_never_stops_the_world(world):
    """Placing by x, y on a tile that has something said `args['dir']` and broke the tick: the world's clock stopped
    for good, in silence. Now it is said as any refusal; and an action that breaks only fails, the world goes on."""
    s, a = world
    x, y = a.x + 1, a.y
    s.world.set(x, y, block="rock")
    a.add("chair", 1)
    r = run(s, a, "place", {"x": x, "y": y, "item": "chair"})
    assert r["error"] == "occupied" and "that tile" in r["detail"]
    for tool in ("read_sign", "step"):
        assert run(s, a, tool, {"x": x, "y": y})["ok"] is False
    act = s.submit(a, "move_to", {"x": a.x - 20, "y": a.y})       # (a long action, its insides swapped for a bug)

    def broken():
        raise KeyError("boom")
        yield
    act.gen, t = broken(), s.tick
    s.step()
    s.step()
    assert s.tick == t + 2 and act.result["error"] == "bug"


def test_what_is_stored_in_a_chest_is_taken_back_out(world):
    """The world's half of tests/e2e/test_e2e_building.py::test_chest_store_and_take: 5 stone stored, then taken
    back with empty hands (`take` with no item: everything)."""
    sim, a = world
    a.add("chest", 1); a.add("stone", 5)
    assert run(sim, a, "place", {"dir": "E", "item": "chest"})["ok"]
    assert run(sim, a, "store", {"dir": "E", "item": "stone", "n": 5})["ok"]
    assert a.count("stone") == 0
    assert run(sim, a, "take", {"dir": "E"})["ok"]
    assert a.count("stone") == 5


def test_meat_is_cooked_at_a_campfire(world):
    """The world's half of tests/e2e/test_e2e_world.py::test_cooking_at_a_campfire: a campfire set down beside you,
    and the meat is cooked there."""
    sim, a = world
    a.add("campfire", 1); a.add("meat", 1)
    assert run(sim, a, "place", {"dir": "E", "item": "campfire"})["ok"]
    r = run(sim, a, "craft", {"recipe": "cooked_meat"})
    assert r["ok"] and a.count("cooked_meat") == 1
