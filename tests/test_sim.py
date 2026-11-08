import pytest

from megastructure.sim import Simulation
from megastructure.world import Chunk


def make(tmp_path, name="w"):
    return Simulation(tmp_path / f"{name}.sqlite", seed=7)


def clear(sim, a, r=6):
    """Flat empty deck around the agent, and no creatures, for predictable tests."""
    for y in range(a.y - r, a.y + r + 1):
        for x in range(a.x - r, a.x + r + 1):
            sim.world.set(x, y, ground="dirt", block="none")
    sim.creatures.clear()


def run(sim, a, tool, args=None, limit=500):
    act = sim.submit(a, tool, args or {})
    for _ in range(limit):
        if act.result is not None:
            return act.result
        sim.step()
    raise AssertionError(f"{tool} did not finish")


@pytest.fixture
def world(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    clear(sim, a)
    yield sim, a
    sim.close()


def test_chunk_pack_roundtrip():
    c = Chunk(1, -2, bytearray(range(256)) * 4, bytearray(b"\x03" * 1024))
    d = Chunk.unpack(1, -2, c.pack())
    assert d.ground == c.ground and d.block == c.block


def test_step_and_blocked(world):
    sim, a = world
    x, y = a.x, a.y
    assert run(sim, a, "step", {"dir": "E"})["ok"]
    assert (a.x, a.y) == (x + 1, y)
    sim.world.set(a.x + 1, a.y, block="rock")
    r = run(sim, a, "step", {"dir": "E"})
    assert not r["ok"] and r["error"] == "blocked"


def test_dig_tree_and_ground(world):
    sim, a = world
    sim.world.set(a.x, a.y - 1, block="tree")
    r = run(sim, a, "dig", {"dir": "N"})
    assert r["ok"] and r["changed"]["inventory"] == {"wood": 3}
    assert sim.world.block(a.x, a.y - 1) == "none"
    assert r["changed"]["tiles"][0]["block"] == "none"
    r = run(sim, a, "dig", {"dir": "S"})
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
    assert run(sim, a, "dig", {"dir": "N"})["ok"]
    for _ in range(400):
        sim.step()
        if sim.world.ground(a.x, a.y - 1) == "water":
            break
    assert sim.world.ground(a.x, a.y - 1) == "water"
    a.add("dirt", 1)
    assert run(sim, a, "place", {"dir": "N", "item": "dirt"})["ok"]
    assert sim.world.ground(a.x, a.y - 1) == "dirt"


def test_fire_spreads_and_burns_out(world):
    sim, a = world
    for dx in range(1, 4):
        sim.world.set(a.x + dx, a.y, block="fence")
    a.add("torch", 1)
    assert run(sim, a, "ignite", {"dir": "E"})["ok"]
    assert (a.x + 1, a.y) in sim.fires and sim.world.block(a.x + 1, a.y) == "fence"   # burning, still standing
    for _ in range(600):
        sim.step()
    assert not sim.fires
    assert sim.world.ground(a.x + 1, a.y) == "ash" and sim.world.block(a.x + 1, a.y) == "none"


def test_move_to_pathfinds_around_wall(world):
    sim, a = world
    for dy in range(-3, 4):
        sim.world.set(a.x + 2, a.y + dy, block="rock")
    gx, gy = a.x + 4, a.y
    r = run(sim, a, "move_to", {"x": gx, "y": gy})
    assert r["ok"] and (a.x, a.y) == (gx, gy) and r["steps"] > 4


def test_combat_death_and_drop(world):
    sim, a = world
    b = sim.login("Bryn", "tok2")
    b.x, b.y = a.x + 1, a.y
    b.add("wood", 5)
    a.add("spear", 1)
    b.hp = 18
    r = run(sim, a, "attack", {"target": b.id})              # bare fists: the spear stays in the bag
    assert r["ok"] and r["damage"] == 5 and not r["killed"]
    r = run(sim, a, "attack", {"target": b.id, "with": "spear"})
    assert r["ok"] and r["killed"]
    assert b.deaths == 1 and b.hp == 100 and not b.inventory
    assert sim.items[(a.x + 1, a.y)]["wood"] == 5
    r = run(sim, a, "step", {"dir": "E"})          # walking onto the pile picks it up
    assert r["ok"] and r["changed"]["inventory"]["wood"] == 5 and (a.x, a.y) not in sim.items


def test_give_and_chat_events(world):
    sim, a = world
    b = sim.login("Bryn", "tok2")
    b.x, b.y = a.x + 1, a.y
    a.add("berries", 3)
    assert run(sim, a, "give", {"target": b.id, "item": "berries", "n": 2})["ok"]
    assert b.count("berries") == 2 and a.count("berries") == 1
    sim.observe(b)
    run(sim, a, "say", {"text": "trade?"})
    ev = sim.observe(b)["events"]
    assert any(e["type"] == "say" and e["text"] == "trade?" and e["from"] == "Ash" for e in ev)


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


def test_interrupt(world):
    sim, a = world
    sim.world.set(a.x, a.y - 1, block="rock")
    first = sim.submit(a, "dig", {"dir": "N"})
    sim.step()
    sim.submit(a, "say", {"text": "never mind"})
    assert first.result["status"] == "interrupted"


def test_persistence_roundtrip(tmp_path):
    sim = make(tmp_path, "p")
    a = sim.login("Ash", "tok")
    clear(sim, a)
    a.add("wood", 4)
    sim.world.set(a.x, a.y - 1, block="sign")
    sim.world.set_meta(a.x, a.y - 1, {"text": "hello", "by": "Ash"})
    sim.add_items(a.x + 1, a.y, {"stone": 2})
    for _ in range(10):
        sim.step()
    pos, tick = (a.x, a.y), sim.tick
    sim.close()

    sim2 = make(tmp_path, "p")
    assert sim2.tick == tick
    with pytest.raises(Exception):
        sim2.login("Ash", "wrong")
    b = sim2.login("Ash", "tok")
    assert (b.x, b.y) == pos and b.count("wood") == 4
    assert sim2.world.block(b.x, b.y - 1) == "sign"
    assert sim2.world.meta[(b.x, b.y - 1)]["text"] == "hello"
    assert sim2.items[(b.x + 1, b.y)] == {"stone": 2}
    sim2.close()


def test_unload_and_reload_keeps_edits(tmp_path):
    sim = make(tmp_path, "u")
    sim.world.set(500, 500, block="stone_wall")
    sim.tick = sim.world.tick = 1000
    assert sim.world.unload_far([(0, 0)]) >= 1
    assert (500 >> 5, 500 >> 5) not in sim.world.chunks
    assert sim.world.block(500, 500) == "stone_wall"
    sim.close()


def test_determinism(tmp_path):
    def trace(name):
        sim = make(tmp_path, name)
        a = sim.login("Ash", "t")
        b = sim.login("Bryn", "t")
        out = []
        for i in range(1500):
            if i % 20 == 0:
                sim.submit(a, "step", {"dir": "NESW"[i // 20 % 4]})
                sim.submit(b, "dig", {"dir": "WSEN"[i // 20 % 4]})
            sim.step()
        out.append((a.x, a.y, b.x, b.y, dict(a.inventory), dict(b.inventory)))
        out.append(sorted((c.kind, c.x, c.y, c.hp) for c in sim.creatures.values()))
        out.append(sim.stats["tiles_changed"])
        sim.close()
        return out

    assert trace("d1") == trace("d2")


def test_observe_shape(world):
    sim, a = world
    o = sim.observe(a)
    assert len(o["grid"]) == 21 and all(len(r) == 21 for r in o["grid"])
    assert o["grid"][10][10] == "@" and o["legend"]["@"] == "you"
    assert o["self"]["hp"] == 100


def test_starvation_kills(world):
    sim, a = world
    a.hunger = 0
    a.hp = 2
    for _ in range(200):
        sim.step()
    assert a.deaths == 1


def test_animals_spawn_and_seeds_grow(world):
    sim, a = world
    clear(sim, a, r=30)
    for _ in range(600):
        sim.step()
    assert any(c.kind in ("chicken", "cow") for c in sim.creatures.values())
    # farming: till, plant, wait, harvest
    a.add("seed", 1)
    assert run(sim, a, "dig", {"dir": "N"})["ok"] and sim.world.ground(a.x, a.y - 1) == "tilled"
    assert run(sim, a, "place", {"dir": "N", "item": "seed"})["ok"]
    for _ in range(sim_ripen_ticks() + 40):
        sim.step()
    assert sim.world.block(a.x, a.y - 1) == "ripe_crop"
    r = run(sim, a, "dig", {"dir": "N"})
    assert r["changed"]["inventory"]["wheat"] == 3


def sim_ripen_ticks():
    from megastructure.sim import sec
    return 2 * sec(150) + sec(4)


def test_fruit_tree_regrows_fruit(world):
    sim, a = world
    from megastructure.sim import sec
    sim.world.set(a.x + 1, a.y, block="fruit_tree")
    r = run(sim, a, "dig", {"dir": "E"})
    assert r["changed"]["inventory"] == {"fruit": 3} and sim.world.block(a.x + 1, a.y) == "tree"
    for _ in range(sec(240) + sec(4)):
        sim.step()
    assert sim.world.block(a.x + 1, a.y) == "fruit_tree"


def test_sprint_is_faster_and_tiring(world):
    sim, a = world
    def pace(run_):          # ticks for 8 strides back and forth (the cooldown is what limits speed)
        t0 = sim.tick
        for i in range(8):
            run(sim, a, "step", {"dir": "E" if i % 2 else "W", "run": run_})
        return sim.tick - t0
    walk = pace(False)
    e0 = a.energy
    assert pace(True) < walk and a.energy < e0


def test_rapid_taps_keep_their_progress(world):
    """Interrupting a walk with another movement (fast key taps) must not throw the stride away."""
    sim, a = world
    x0 = a.x
    for _ in range(6):
        sim.submit(a, "walk", {"dir": "E"})
        sim.step()
        sim.submit(a, "move_to", {"x": a.x + 1, "y": a.y})
        sim.step()
    assert a.x - x0 >= 5


def test_walk_keeps_going_until_stopped(world):
    sim, a = world
    x0 = a.x
    act = sim.submit(a, "walk", {"dir": "E"})
    for _ in range(20):
        sim.step()
    assert a.x - x0 >= 4 and act.result is None
    sim.submit(a, "stop", {})
    sim.step()
    assert act.result["status"] == "interrupted"
    sim.world.set(a.x + 2, a.y, block="rock")
    r = run(sim, a, "walk", {"dir": "E"})
    assert r["stopped"] == "blocked" and r["steps"] == 1


def test_crop_species_watering_and_harvest(world):
    sim, a = world
    from megastructure.sim import sec
    from megastructure.tiles import crop_species
    a.add("seed", 1)
    a.add("watering_can", 1)
    run(sim, a, "dig", {"dir": "N"})
    run(sim, a, "place", {"dir": "N", "item": "seed"})
    assert sim.world.block(a.x, a.y - 1) == "sprout"
    assert run(sim, a, "water", {"dir": "N"})["ok"] and sim.world.ground(a.x, a.y - 1) == "wet_tilled"
    for _ in range(sec(75) + sec(3)):            # watered: half of 150 s
        sim.step()
    assert sim.world.block(a.x, a.y - 1) == "crop" and sim.world.ground(a.x, a.y - 1) == "tilled"
    for _ in range(sec(150) + sec(3)):
        sim.step()
    r = run(sim, a, "dig", {"dir": "N"})
    assert r["changed"]["inventory"][crop_species(a.x, a.y - 1)] == 3


def test_chickens_lay_cows_give_milk_and_beds_set_spawn(world):
    sim, a = world
    from megastructure.sim import Creature, sec
    hen = Creature(sim.next_creature, "chicken", a.x + 1, a.y, 10); sim.next_creature += 1
    cow = Creature(sim.next_creature, "cow", a.x, a.y + 1, 30); sim.next_creature += 1
    sim.creatures.update({hen.id: hen, cow.id: cow})
    hen.cooldown = cow.cooldown = 10**6  # keep them in place for the test
    a.add("berries", 1)
    assert run(sim, a, "feed", {"target": hen.id, "item": "berries"})["ok"]
    for _ in range(sec(5)):
        sim.step()
    assert any("egg" in pile for pile in sim.items.values())
    assert run(sim, a, "milk", {"target": cow.id})["changed"]["inventory"] == {"milk": 1}
    assert run(sim, a, "milk", {"target": cow.id})["error"] == "not_ready"
    sim.world.set(a.x - 1, a.y, block="bed")
    assert run(sim, a, "sleep", {"dir": "W"})["ok"] and a.spawn == [a.x - 1, a.y]
    a.hp = 1
    sim.kill_agent(a, "test", None)
    assert abs(a.x - (a.spawn[0])) + abs(a.y - a.spawn[1]) == 1


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


def test_eggs_hatch_and_chicks_grow_up(world):
    sim, a = world
    from megastructure.sim import sec
    sim.add_items(a.x + 3, a.y, {"egg": 1})
    sim.timers[(a.x + 3, a.y)] = [sim.tick + sec(1), "hatch"]
    for _ in range(sec(3)):
        sim.step()
    chicks = [c for c in sim.creatures.values() if c.kind == "chick"]
    assert len(chicks) == 1 and (a.x + 3, a.y) not in sim.items
    chicks[0].born -= sec(300)
    sim.step()
    assert chicks[0].kind == "chicken"


def test_boats_launch_board_sail_and_moor(world):
    sim, a = world
    for dx in range(1, 6):
        sim.world.set(a.x + dx, a.y, ground="water")
    sim.world.set(a.x + 6, a.y, ground="grass")
    a.add("boat", 1)
    assert run(sim, a, "place", {"dir": "E", "item": "boat"})["ok"] and sim.world.block(a.x + 1, a.y) == "boat"
    x0 = a.x
    assert run(sim, a, "step", {"dir": "E"})["ok"] and a.sailing and sim.world.block(a.x, a.y) == "none"
    run(sim, a, "move_to", {"x": x0 + 6, "y": a.y})
    assert a.x == x0 + 6 and not a.sailing and sim.world.block(x0 + 5, a.y) == "boat"


def test_mailbox_post_and_open(world):
    sim, a = world
    a.add("mailbox", 1)
    run(sim, a, "place", {"dir": "N", "item": "mailbox"})
    b = sim.login("Pen", "x")
    b.x, b.y = a.x + 1, a.y - 1
    assert run(sim, b, "post", {"dir": "W", "text": "meet me at the lake"})["owner"] == "Ash"
    r = run(sim, a, "open_mail", {"dir": "N"})
    assert r["letters"][0]["text"] == "meet me at the lake" and r["letters"][0]["from"] == "Pen"
    assert run(sim, a, "open_mail", {"dir": "N"})["letters"] == []


def test_doors_and_gates_stop_creatures(world):
    sim, a = world
    from megastructure.sim import Creature
    hen = Creature(sim.next_creature, "chicken", a.x + 2, a.y, 10); sim.next_creature += 1
    sim.creatures[hen.id] = hen
    sim.world.set(a.x + 3, a.y, block="gate")
    assert not sim._creature_move(hen, a.x + 3, a.y) and (hen.x, hen.y) == (a.x + 2, a.y)
    assert run(sim, a, "move_to", {"x": a.x + 4, "y": a.y})["ok"]     # people walk through


def test_ash_grows_back_into_grass(world):
    sim, a = world
    from megastructure.sim import sec
    sim.world.set(a.x + 1, a.y, ground="grass")
    assert sim.ignite(a.x + 1, a.y)
    for _ in range(sec(16)):
        sim.step()
    assert sim.world.ground(a.x + 1, a.y) == "ash"
    for _ in range(sec(244)):
        sim.step()
    assert sim.world.ground(a.x + 1, a.y) == "grass"


def test_glooms_fade_and_never_bite_by_day(world):
    sim, a = world
    from megastructure.sim import Creature, sec, DAY_TICKS
    sim.tick = (sim.tick // DAY_TICKS) * DAY_TICKS + DAY_TICKS // 3       # mid-morning
    g = Creature(sim.next_creature, "gloom", a.x + 1, a.y, 30); sim.next_creature += 1
    sim.creatures[g.id] = g
    hp = a.hp
    for _ in range(sec(8)):
        sim.step()
    assert a.hp == hp and g.id not in sim.creatures


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
    assert run(sim, a, "water", {"dir": "S"})["error"] == "empty"
    a.x += 1   # the well's right half is the well too
    assert run(sim, a, "water", {"dir": "N"})["can"] == 12
    a.x -= 1
    assert run(sim, a, "water", {"dir": "S"})["can"] == 11
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
    assert run(sim, a, "eat", {"item": "bread"})["picnic"] and a.hunger == 10 + 45
    a.y += 2
    a.add("basket", 1); a.add("fiber", 2)
    run(sim, a, "place", {"dir": "S", "item": "basket"})
    assert run(sim, a, "store", {"dir": "S", "item": "fiber", "n": 2})["ok"]
    assert run(sim, a, "dig", {"dir": "S"})["ok"] and a.count("fiber") == 2 and a.count("basket") == 1


def test_chickens_lay_into_the_coop(world):
    sim, a = world
    from megastructure.sim import Creature
    a.add("coop", 1)
    run(sim, a, "place", {"dir": "N", "item": "coop"})
    hen = Creature(sim.next_creature, "chicken", a.x + 3, a.y + 2, 10); sim.next_creature += 1
    hen.lay, hen.cooldown = sim.tick + 1, 10**6
    sim.creatures[hen.id] = hen
    sim.step(); sim.step()
    assert sim.items.get((a.x, a.y), {}).get("egg") == 1   # the coop's door tile is where we stand


def test_crowded_eggs_rot_and_old_herds_thin(world, tmp_path):
    sim, a = world
    from megastructure.sim import Creature, sec, CROWD_N
    for i in range(CROWD_N):
        hen = Creature(sim.next_creature, "chicken", a.x + 2 + i % 3, a.y + i // 3, 10, cooldown=10**6)
        sim.next_creature += 1
        sim.creatures[hen.id] = hen
    sim.add_items(a.x - 2, a.y, {"egg": 1})
    for _ in range(sec(181)):
        sim.step()
    assert (a.x - 2, a.y) not in sim.items                 # nobody collected it and there's no room: it rotted
    assert sum(c.kind == "chick" for c in sim.creatures.values()) == 0
    for i in range(50):                                    # an old world's chicken explosion
        sim.creatures[sim.next_creature] = Creature(sim.next_creature, "chicken", a.x, a.y, 10)
        sim.next_creature += 1
    sim._thin_herds()
    assert len(sim.creatures) <= 2 * CROWD_N


def test_trough_feeds_animals_and_hay_lasts(world):
    sim, a = world
    from megastructure.sim import Creature, sec
    a.add("trough", 1); a.add("hay", 1); a.add("wood", 1)
    run(sim, a, "place", {"dir": "E", "item": "trough"})
    assert run(sim, a, "store", {"dir": "E", "item": "wood", "n": 1})["error"] == "bad_item"
    assert run(sim, a, "store", {"dir": "E", "item": "hay", "n": 1})["ok"]
    cow = Creature(sim.next_creature, "cow", a.x + 3, a.y, 30, cooldown=10**6); sim.next_creature += 1
    sim.creatures[cow.id] = cow
    meals = 0
    for _ in range(sec(200)):
        sim.step()
        if cow.love == sim.tick + sec(8):
            meals += 1
    assert meals == 3                                      # one bale, three meals
    assert not sim.world.meta[(a.x + 1, a.y)]["items"]


def test_spread_bushes_are_tidied_on_load(world):
    sim, a = world
    from megastructure.gen import gen_tile
    from megastructure.tiles import B
    x, y = next((x, a.y) for x in range(a.x, a.x + 200) if gen_tile(sim.world.seed, x, a.y)[1] != B["berry_bush"])
    sim.world.set(x, y, block="berry_bush")
    sim.world.flush()
    del sim.world.chunks[(x >> 5, y >> 5)]
    assert sim.world.block(x, y) == "none"
