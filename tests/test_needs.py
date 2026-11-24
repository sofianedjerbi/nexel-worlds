"""Health and food as the sandbox classic has them (sim/needs.py): half hearts, half pieces, saturation, tiredness."""

import pytest
from helpers import make, run

from nexel_worlds.sim import CREATURES, sec
from nexel_worlds.sim.constants import FOOD_MAX, HP_MAX, SPRINT_FOOD, TIRES


def test_food_does_not_go_down_by_itself_and_walking_uses_little(world):
    """It went down a piece every 100 s whatever you did: the bar was empty after 17 minutes. Standing costs nothing;
    walking, a point every thousand tiles; sprinting, every three hundred and some."""
    sim, a = world
    a.hunger, a.sat = 20, 0.0
    for _ in range(sec(1800)):                                # half an hour, standing
        sim.step()
    assert a.hunger == 20
    for _ in range(999):
        sim.tire(a, "walk")
    assert a.hunger == 20
    sim.tire(a, "walk")
    assert a.hunger == 19 and a.tired < .01
    for _ in range(334):
        sim.tire(a, "sprint")
    assert a.hunger == 18
    assert TIRES["sprint"] == 3 * TIRES["walk"] and TIRES["heal"] == 6                 # (healing is what costs)


def test_walking_and_sprinting_tire_you_a_tile_at_a_time(world):
    sim, a = world
    x = a.x
    assert run(sim, a, "step", {"dir": "E"})["ok"] and a.tired == pytest.approx(TIRES["walk"])
    assert run(sim, a, "step", {"dir": "E", "run": True})["ok"] and a.tired == pytest.approx(TIRES["walk"] + TIRES["sprint"]) and a.x == x + 2


def test_the_reserve_goes_first_then_the_food(world):
    sim, a = world
    a.hunger, a.sat = 10, 2.0
    for want in ((10, 1.0), (10, 0.0), (9, 0.0)):
        sim.tire(a, "heal", 4 / 6)                            # (4: a point)
        assert (a.hunger, a.sat) == want


def test_you_heal_when_fed_fast_with_a_full_bar_and_a_reserve(world):
    sim, a = world
    a.hp, a.hunger, a.sat = 10, 17, 0.0
    for _ in range(sec(30)):
        sim.step()
    assert a.hp == 10                                         # under nine pieces: not at all
    a.hunger = 20
    for _ in range(sec(8)):
        sim.step()
    assert a.hp == 12 and a.hunger == 17 and a.tired == 0     # half a heart every 4 s, a point and a half of food each
    for _ in range(sec(8)):
        sim.step()
    assert a.hp == 12                                         # ...until the food is under nine pieces
    a.hp, a.hunger, a.sat = 10, 20, 6.0
    for _ in range(sec(2)):
        sim.step()
    assert a.hp == 14 and a.sat == 0 and a.hunger == 20       # every half second while the reserve lasts...
    for _ in range(sec(4)):
        sim.step()
    assert a.hp == 15 and a.hunger == 19                      # ...then as before, on the food
    a.hp = HP_MAX
    for _ in range(sec(8)):
        sim.step()
    assert a.hp == HP_MAX and a.hunger == 19                  # whole: nothing spent


def test_starving_takes_half_a_heart_every_four_seconds(world):
    sim, a = world
    a.hp, a.hunger = 20, 0
    for _ in range(sec(8)):
        sim.step()
    assert a.hp == 18 and a.deaths == 0


def test_no_sprinting_on_three_pieces_of_food(world):
    sim, a = world
    a.hunger = SPRINT_FOOD
    assert sim.stride(a, {"run": True}) == sim.stride(a, {}) == 0.2
    a.hunger = SPRINT_FOOD + 1
    assert sim.stride(a, {"run": True}) == 0.1


def test_food_fills_the_bar_and_good_food_the_reserve(world):
    sim, a = world
    a.hunger, a.sat = 4, 0.0
    a.add("berries")
    a.add("cooked_meat", 2)
    assert run(sim, a, "eat", {"item": "berries"})["ok"] and (a.hunger, a.sat) == (6, pytest.approx(1.2))      # 2, and 2 x 2 x 0.3
    assert run(sim, a, "eat", {"item": "cooked_meat"})["ok"] and (a.hunger, a.sat) == (14, pytest.approx(14.0))   # 8, and 12.8: no more than the bar
    assert run(sim, a, "eat", {"item": "cooked_meat"})["ok"] and a.hunger == FOOD_MAX
    assert run(sim, a, "eat", {"item": "cooked_meat"})["error"] in ("full", "missing_item")


def test_a_blow_is_in_half_hearts_and_armor_turns_it_to_the_half(world):
    sim, a = world
    assert [CREATURES[k]["damage"] for k in ("tusker", "pincer", "strawman", "wyrm", "sporeling")] == [3, 1, 2, 3.5, 0.5]
    a.worn = {"head": "iron_helmet", "top": "iron_chestplate"}            # 20 percent
    assert sim.armor(a) == 20 and sim.guarded(a, 3) == 2.5 and sim.guarded(a, 0.5) == 0.5
    sim.damage(a, sim.guarded(a, 3), "test")
    assert a.hp == 17.5 and sim.observe(a)["self"]["hp"] == 17.5


def test_a_world_saved_on_the_old_scale_is_converted_once(tmp_path):
    sim = make(tmp_path, "old")
    a = sim.login("Ash", "tok")
    a.hp, a.hunger = 85, 40                                    # as saved before: 0 to 100
    sim.close()
    sim.world.store.db = None
    import sqlite3
    db = sqlite3.connect(tmp_path / "old.sqlite")
    db.execute("INSERT OR REPLACE INTO meta VALUES('vitals', '1')")
    db.commit()
    db.close()
    sim = make(tmp_path, "old")
    a = sim.by_name["Ash"]
    assert (a.hp, a.hunger, a.sat) == (17, 8, 5.0)
    sim.close()
    sim = make(tmp_path, "old")
    assert sim.by_name["Ash"].hp == 17 and sim.world.store.get_meta("vitals") == 2      # only once
    sim.close()


def test_a_server_that_dies_before_saving_leaves_the_world_to_be_converted(tmp_path):
    """The play world was opened by a second server that could not have its port: it marked the save converted and
    died before saving the players. The mark is written with the players now, and numbers over full are the old scale
    whatever the mark says."""
    import sqlite3
    sim = make(tmp_path, "w")
    a = sim.login("Ash", "tok")
    a.hp, a.hunger = 100, 66
    sim.close()                                                # (saved: marked 2, by the save)
    db = sqlite3.connect(tmp_path / "w.sqlite")
    assert db.execute("SELECT value FROM meta WHERE key='vitals'").fetchone() == ("2",)   # marked, and 100 and 66 in it: as the play world was left
    db.close()
    sim = make(tmp_path, "w")
    a = sim.by_name["Ash"]
    assert (a.hp, a.hunger) == (20, 13)                        # over full: the old scale
    sim.world.store.db.execute("INSERT OR REPLACE INTO meta VALUES('vitals', '1')")
    sim.world.store.commit()
    a.hp, a.hunger = 85, 40
    sim.flush()
    sim.world.store.db.execute("INSERT OR REPLACE INTO meta VALUES('vitals', '1')")     # an old save again...
    sim.world.store.commit()
    sim.world.store.close()                                    # ...opened, and the server dies: nothing saved
    dead = make(tmp_path, "w")
    assert dead.by_name["Ash"].hp == 17
    dead.world.store.db.rollback()
    dead.world.store.db.close()
    db = sqlite3.connect(tmp_path / "w.sqlite")
    assert db.execute("SELECT value FROM meta WHERE key='vitals'").fetchone() == ("1",)   # not marked: the next one converts it
    db.close()
