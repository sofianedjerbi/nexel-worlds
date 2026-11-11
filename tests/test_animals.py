"""Animals and glooms: spawning, laying, breeding limits, coops, troughs, fleeing."""

from helpers import clear, run, sim_ripen_ticks


def test_animals_spawn_and_seeds_grow(world):
    sim, a = world
    from megastructure.sim.spawning import PASSIVE_EVERY
    clear(sim, a, r=30)
    for _ in range(PASSIVE_EVERY * 12):                      # animals are rare: a herd turns up now and then, not at once
        sim.step()
        if any(c.kind in ("chicken", "cow") for c in sim.creatures.values()):
            break
    assert any(c.kind in ("chicken", "cow") for c in sim.creatures.values())
    # farming: till, plant, wait, harvest
    a.add("seed", 1); a.add("hoe", 1)
    assert run(sim, a, "dig", {"dir": "N", "with": "hoe"})["ok"] and sim.world.ground(a.x, a.y - 1) == "tilled"
    assert run(sim, a, "place", {"dir": "N", "item": "seed"})["ok"]
    for _ in range(sim_ripen_ticks() + 40):
        sim.step()
    assert sim.world.block(a.x, a.y - 1) == "ripe_crop"
    r = run(sim, a, "dig", {"dir": "N"})
    assert r["changed"]["inventory"]["wheat"] == 3

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
    assert any("egg" in pile for pile in sim.items.values()) or a.count("egg")   # laid (the magnet may bring it)
    assert run(sim, a, "milk", {"target": cow.id})["changed"]["inventory"] == {"milk": 1}
    assert run(sim, a, "milk", {"target": cow.id})["error"] == "not_ready"
    sim.world.set(a.x - 1, a.y, block="bed")
    assert run(sim, a, "sleep", {"dir": "W"})["ok"] and a.spawn == [a.x - 1, a.y]
    a.hp = 1
    sim.kill_agent(a, "test", None)
    assert abs(a.x - (a.spawn[0])) + abs(a.y - a.spawn[1]) == 1

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

def test_doors_and_gates_stop_creatures(world):
    sim, a = world
    from megastructure.sim import Creature
    hen = Creature(sim.next_creature, "chicken", a.x + 2, a.y, 10); sim.next_creature += 1
    sim.creatures[hen.id] = hen
    sim.world.set(a.x + 3, a.y, block="gate")
    assert not sim._creature_move(hen, a.x + 3, a.y) and (hen.x, hen.y) == (a.x + 2, a.y)
    assert run(sim, a, "move_to", {"x": a.x + 4, "y": a.y})["ok"]     # people walk through

def test_glooms_fade_and_never_bite_by_day(world):
    sim, a = world
    from megastructure.sim import DAY_TICKS, Creature, sec
    sim.tick = (sim.tick // DAY_TICKS) * DAY_TICKS + DAY_TICKS // 3       # mid-morning
    g = Creature(sim.next_creature, "gloom", a.x + 1, a.y, 30); sim.next_creature += 1
    sim.creatures[g.id] = g
    hp = a.hp
    for _ in range(sec(8)):
        sim.step()
    assert a.hp == hp and g.id not in sim.creatures

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
    from megastructure.sim import CROWD_N, Creature, sec
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
    here = [c for c in sim.creatures.values() if abs(c.x - a.x) <= 4 and abs(c.y - a.y) <= 4]   # (wild herds roam further out)
    assert len(here) <= 2 * CROWD_N

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

def test_hit_animals_run_away(world):
    sim, a = world
    from megastructure.sim import Creature, sec
    hen = Creature(sim.next_creature, "chicken", a.x + 1, a.y, 10); sim.next_creature += 1
    sim.creatures[hen.id] = hen
    assert run(sim, a, "attack", {"target": hen.id})["ok"]
    for _ in range(sec(2)):
        sim.step()
    assert abs(hen.x - a.x) + abs(hen.y - a.y) >= 4                     # it ran, it didn't stay to be hit again


def test_new_land_comes_with_herds_and_only_land_near_players_lives(world, monkeypatch):
    sim, a = world
    from megastructure.gen import CHUNK
    from megastructure.sim import sec, spawning
    from megastructure.sim.spawning import SIM_R
    monkeypatch.setattr(spawning, "CHUNK_HERD", 0.5)         # (herds are rare: make them common enough to find in a dozen chunks)
    before = len(sim.creatures)
    for i in range(12):                                      # explore: a row of new chunks far away
        sim.world.block((i + 10) * CHUNK, 40 * CHUNK)
    sim.step()
    far = [c for c in sim.creatures.values() if c.y // CHUNK == 40]
    assert len(sim.creatures) > before and far              # some of them got a herd...
    assert len({c.kind for c in far} - {"chicken", "cow"}) == 0
    spot = {c.id: (c.x, c.y) for c in far}
    for _ in range(sec(20)):
        sim.step()
    assert all((c.x, c.y) == spot[c.id] for c in far if c.id in sim.creatures)   # ...frozen: nobody is there
    assert not sim.ticks(far[0]) and max(abs(far[0].x - a.x), abs(far[0].y - a.y)) > SIM_R


def test_glooms_come_at_night_in_the_dark_up_to_a_cap(world):
    sim, a = world
    from megastructure.sim import DAY_TICKS
    from megastructure.sim import sec
    from megastructure.sim.spawning import HOSTILE_CAP
    sim.tick = (sim.tick // DAY_TICKS + 1) * DAY_TICKS - sec(140)  # early in the night
    assert sim.is_night()
    for _ in range(sec(130)):
        sim.step()
    glooms = [c for c in sim.creatures.values() if c.kind == "gloom"]
    assert 1 <= len(glooms) <= HOSTILE_CAP                  # they come one at a time, and few


def test_a_campfire_keeps_the_dark_away(world):
    sim, a = world
    from megastructure.gen import CHUNK
    for cx in range(a.x // CHUNK - 2, a.x // CHUNK + 3):     # the land around you, in memory
        for cy in range(a.y // CHUNK - 2, a.y // CHUNK + 3):
            sim.world.chunk(cx, cy)
    sim.creatures.clear()                                    # (the new land brought herds: none in the way)
    sim.world.set(a.x + 20, a.y, block="campfire")
    sim.world.set(a.x + 22, a.y, ground="grass", block="none")
    sim.world.set(a.x + 30, a.y, ground="grass", block="none")
    assert not sim.spawn_spot_ok("gloom", a.x + 22, a.y)     # in the firelight
    assert sim.spawn_spot_ok("gloom", a.x + 30, a.y)         # out in the dark


def test_animals_eat_what_grows_not_eggs_or_meat(world):
    sim, a = world
    from megastructure.sim import Creature
    hen = Creature(sim.next_creature, "chicken", a.x + 1, a.y, 10, cooldown=10**6); sim.next_creature += 1
    sim.creatures[hen.id] = hen
    for food in ("egg", "meat", "cooked_meat", "milk"):
        a.add(food, 1)
        assert run(sim, a, "feed", {"target": hen.id, "item": food})["ok"] is False
    a.add("wheat", 1)
    assert run(sim, a, "feed", {"target": hen.id, "item": "wheat"})["ok"]
