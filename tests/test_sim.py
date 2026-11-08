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
    assert sim.world.block(a.x, a.y - 1) == "stump"
    assert r["changed"]["tiles"][0]["block"] == "stump"
    r = run(sim, a, "dig", {"dir": "S"})
    assert r["ok"] and sim.world.ground(a.x, a.y + 1) == "tilled" and a.count("dirt") == 1


def test_node_needs_drill(world):
    sim, a = world
    sim.world.set(a.x + 1, a.y, block="ore")
    r = run(sim, a, "dig", {"dir": "E"})
    assert r["error"] == "need_tool"


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
    assert run(sim, a, "place", {"dir": "N", "item": "dirt"})["ok"]
    assert sim.world.ground(a.x, a.y - 1) == "dirt"


def test_fire_spreads_and_burns_out(world):
    sim, a = world
    for dx in range(1, 4):
        sim.world.set(a.x + dx, a.y, block="fence")
    a.add("torch", 1)
    assert run(sim, a, "ignite", {"dir": "E"})["ok"]
    assert sim.world.block(a.x + 1, a.y) == "fire"
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
    r = run(sim, a, "attack", {"target": b.id})
    assert r["ok"] and r["killed"]
    assert b.deaths == 1 and b.hp == 100 and not b.inventory
    assert sim.items[(a.x + 1, a.y)]["wood"] == 5
    assert run(sim, a, "step", {"dir": "E"})["ok"]
    assert run(sim, a, "pick_up")["changed"]["inventory"]["wood"] == 5


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
    return sec(300)
