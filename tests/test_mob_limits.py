"""How many creatures there may be around a player, and which go when there are more (sim/spawning.py)."""

import json

from helpers import clear, run
from test_wild import put

from nexel_worlds.sim import Creature, sec
from nexel_worlds.sim.spawning import CAP_R, LIMITS, PASSIVE, SPAWN_MIN

ANIMALS = dict(LIMITS)[PASSIVE]


def animals(sim, a, r=CAP_R):
    return [c for c in sim.creatures.values() if c.kind in PASSIVE and max(abs(c.x - a.x), abs(c.y - a.y)) <= r]


def test_hens_do_not_breed_past_a_players_limit(world):
    """Three hens on a meadow, an hour and a half: they were a hundred and more (five hundred after three hours, and
    still growing: an egg hatched wherever three animals were not close by). An egg hatches only while whoever is
    near has room for one more animal."""
    sim, a = world
    clear(sim, a, r=45)
    for i in range(3):
        put(sim, "chicken", a.x + 3 + i, a.y + 2)
    hatched, most = [], 0
    sim.listeners.append(lambda e: e["type"] == "hatch" and hatched.append(e))
    for t in range(sec(5400)):
        sim.step()
        a.hp = a.hunger = 100
        if t % sec(10) == 0:
            most = max(most, len(animals(sim, a)))
    assert hatched and most <= ANIMALS + 3, (len(hatched), most)       # (they do breed; a herd that comes with new land may be over for a moment)
    assert len(sim.creatures) <= ANIMALS + 6


def test_an_egg_rots_where_nobody_is_or_where_there_are_enough_animals(world):
    sim, a = world
    clear(sim, a, r=45)
    hatched = []
    sim.listeners.append(lambda e: e["type"] == "hatch" and hatched.append((e["x"], e["y"])))
    sim.add_items(a.x + 2, a.y, {"egg": 1})                            # room: it hatches
    sim.add_items(a.x + CAP_R + 20, a.y, {"egg": 1})                   # nobody near: it rots
    for _ in range(sec(181)):
        sim.step()
    assert hatched == [(a.x + 2, a.y)] and (a.x + CAP_R + 20, a.y) not in sim.items
    sim.creatures.clear()
    for i in range(ANIMALS):                                           # as many as the limit, spread out (nowhere crowded)
        put(sim, "cow", a.x - 30 + 8 * i, a.y - 30, cooldown=10 ** 6)
    sim.add_items(a.x + 2, a.y + 20, {"egg": 1})
    for _ in range(sec(181)):
        sim.step()
    assert len(hatched) == 1 and (a.x + 2, a.y + 20) not in sim.items and len(animals(sim, a)) == ANIMALS


def test_the_ones_over_the_limit_go_out_of_sight_the_farthest_first(world):
    """Fifty chickens round a player (it was three hundred in the saved world, 54 on one screen): the ones in sight
    stay as long as they are, the others go down to the limit, the farthest first."""
    sim, a = world
    clear(sim, a, r=45)
    near = [put(sim, "chicken", a.x - 5 + i, a.y + 3, cooldown=10 ** 6) for i in range(10)]            # in sight
    far = [put(sim, "chicken", a.x + SPAWN_MIN + 2 + i // 2, a.y - 10 + 10 * (i % 2), cooldown=10 ** 6) for i in range(40)]
    for _ in range(sec(5)):
        sim.step()
    assert all(c.id in sim.creatures for c in near)
    assert not any(c.id in sim.creatures for c in far)                 # (ten in sight are more than the limit already)
    for c in near[4:]:
        del sim.creatures[c.id]
    ring = [put(sim, "chicken", a.x + SPAWN_MIN + 2 + 3 * i, a.y - 12, cooldown=10 ** 6) for i in range(5)]   # 4 + 5: three over
    for _ in range(sec(3)):
        sim.step()
    assert [c.id in sim.creatures for c in ring] == [True, True, False, False, False]
    assert len(animals(sim, a)) == ANIMALS


def test_nothing_goes_on_a_screen_and_a_named_or_a_housed_one_never_goes(world):
    sim, a = world
    clear(sim, a, r=45)
    put(sim, "chicken", a.x + 1, a.y, cooldown=10 ** 6)
    daisy = put(sim, "cow", a.x, a.y + 1, cooldown=10 ** 6)
    assert run(sim, a, "name", {"target": daisy.id, "text": "Daisy"})["error"] == "missing_item" and not daisy.name      # a name takes a name tag
    a.add("name_tag", 1)
    assert run(sim, a, "name", {"target": daisy.id, "text": "  Daisy   the cow of the long name "})["ok"] and daisy.name == "Daisy the cow of"
    assert a.inventory.get("name_tag", 0) == 0                          # (it stays on her)
    assert run(sim, a, "name", {"target": daisy.id, "text": " "})["error"] == "bad_args" and daisy.name == "Daisy the cow of"
    daisy.x, daisy.y = a.x + 30, a.y + 30                              # she wanders off
    sim.world.set(a.x - 30, a.y, block="coop")
    housed = [put(sim, "chicken", a.x - 30 + i, a.y + 2, cooldown=10 ** 6) for i in range(3)]
    watched = [put(sim, "chicken", a.x + 30 + i, a.y - 30, cooldown=10 ** 6) for i in range(3)]
    sim.screens = lambda: [(a.x + 28, a.y - 32, 10, 6)]                # someone watches that corner
    wild = [put(sim, "chicken", a.x + 20 + i, a.y + 20, cooldown=10 ** 6) for i in range(20)]
    wild += [put(sim, "tusker", a.x - 20, a.y - 30 + 3 * i, cooldown=10 ** 6) for i in range(5)]
    for _ in range(sec(5)):
        sim.step()
        a.hp = 100
    assert daisy.id in sim.creatures and all(c.id in sim.creatures for c in housed + watched)
    assert sum(c.id in sim.creatures for c in wild if c.kind == "chicken") == 0      # (the kept ones are more than the limit)
    assert sum(c.id in sim.creatures for c in wild if c.kind == "tusker") == dict(LIMITS)[("tusker", "pincer")]
    again = Creature(**json.loads(json.dumps(daisy.to_json())))        # a name is saved with the world
    assert again.name == daisy.name and "name" not in housed[0].to_json()


def test_a_world_saved_while_hens_bred_without_end_is_thinned_once(world):
    """Opened under these rules, a world from before: where anyone will wake up no more than a player's limit are left
    (any of them, not the nearest: nobody is there to see the others go), far from everyone one in five; the file is
    copied first."""
    sim, a = world
    sim.creatures.clear()
    sim.world.set(a.x + 10, a.y, block="trough")
    farm = [put(sim, "cow", a.x + 9 + i, a.y + 1) for i in range(3)]
    home = [put(sim, "chicken", a.x - 20 + i % 20, a.y - 10 + i // 20) for i in range(200)]
    wild = [put(sim, "chicken", a.x + 3 * CAP_R + i, a.y) for i in range(40)]
    sim.world.store.set_meta("spawn_rules", 2)
    sim.thin_wild(sim.world.store)
    left = [c for c in home if c.id in sim.creatures]
    assert all(c.id in sim.creatures for c in farm) and len(left) + len(farm) == ANIMALS
    assert max(max(abs(c.x - a.x), abs(c.y - a.y)) for c in left) > 4                 # (not the ones at your feet)
    assert 4 <= sum(c.id in sim.creatures for c in wild) <= 12
    assert sim.world.store.path.with_name(sim.world.store.path.stem + ".before-mob-limits.sqlite").exists()
    n = len(sim.creatures)
    put(sim, "chicken", a.x + 30, a.y + 30)
    sim.thin_wild(sim.world.store)
    assert len(sim.creatures) == n + 1                                 # only once
