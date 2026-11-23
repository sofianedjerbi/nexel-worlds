"""Water that flows (flow.py, sim/waters.py): down first, then sideways a level less a tile; dries without a source;
any block stops it; a hole dug beside a river floods a layer at a time; old saves; a bounded step."""

from pathlib import Path

from helpers import clear, make, run

from megastructure.flow import BUDGET, FALL, FULL, MAXD, NOHEAD, SOURCE
from megastructure.sim.constants import CAN_SIZE


def steps(sim, n):
    """n steps of the water (four a second: 2.5 ticks each)."""
    for _ in range(n * 5 // 2 + 1):
        sim.step()


def dig_hole(sim, xs, y, floor):
    for x in xs:
        for z in range(floor + 1, 1):
            sim.world.set_cell(x, y, z, False)


def lv(sim, x, y, z):
    return sim.water.lv(x, y, z)


def test_a_hole_beside_a_river_fills_a_layer_at_a_time(world):
    sim, a = world
    rx, y = a.x + 2, a.y + 3
    for j in (-1, 0, 1):
        sim.world.set(rx, y + j, ground="water")
    sim.world.set_cell(rx + 1, y, 0, True)                 # (a wall left to the river)
    dig_hole(sim, range(rx + 2, rx + 6), y, -3)
    steps(sim, 6)
    assert not sim.water.at                                 # walled off: dry
    sim.world.set_cell(rx + 1, y, 0, False)                 # the wall cut
    steps(sim, 1)
    assert lv(sim, rx + 1, y, 0) == FALL                    # in at once, a level under the river
    seen_bottom_first = False
    for _ in range(20):
        steps(sim, 1)
        if lv(sim, rx + 4, y, -2) and not lv(sim, rx + 4, y, 0):
            seen_bottom_first = True                        # the floor is wet while the top is not yet
    assert seen_bottom_first
    assert all(lv(sim, x, y, z) == FULL for x in range(rx + 2, rx + 6) for z in (-2, -1))   # under the river's face: full
    top = [lv(sim, x, y, 0) for x in range(rx + 1, rx + 6)]
    assert top == sorted(top, reverse=True) and top[0] == FALL and top[-1] < FALL         # at its face: it sinks away from the river
    assert lv(sim, rx + 6, y, 1) == 0                        # nothing over the bank


def test_a_wide_pit_and_a_tunnel_under_the_river_flood_whole_and_dry_when_dammed(world):
    sim, a = world
    rx, y = a.x + 2, a.y + 4
    sim.world.set(rx, y, ground="water")
    sim.world.set_cell(rx + 1, y, 0, False)                 # the cut, one deep
    for x in range(rx + 2, rx + 14):                        # a pit 12 wide, 3 across, 2 under the river
        dig_hole(sim, [x], y, -3)
        dig_hole(sim, [x], y + 1, -3)
        dig_hole(sim, [x], y - 1, -3)
    steps(sim, 60)
    pit = [(x, j, z) for x in range(rx + 2, rx + 14) for j in (y - 1, y, y + 1) for z in (-2, -1)]
    assert all(lv(sim, *c) == FULL for c in pit)             # wall to wall, past the seven tiles running water goes
    for x in range(rx + 14, rx + 30):                        # a tunnel dug on from its foot, a cell at a time: it follows
        sim.world.set_cell(x, y, -2, False)
        steps(sim, 1)
    steps(sim, 4)
    assert lv(sim, rx + 29, y, -2) == FULL
    sim.world.set_cell(rx + 1, y, -1, True)                 # (the cut is one deep: its floor) ...
    sim.world.set_cell(rx + 1, y, 0, True)                  # a dam in the cut
    steps(sim, MAXD + 40)
    assert not sim.water.at                                  # cut off from the river: it all drained


def test_flat_ground_spreads_seven_to_one_and_stops(world):
    sim, a = world
    a.can = CAN_SIZE
    a.add("watering_can")
    x, y = a.x + 1, a.y
    assert run(sim, a, "water", {"dir": "E", "with": "watering_can", "pour": True})["ok"] and a.can == 0
    steps(sim, 12)
    assert lv(sim, x, y, 1) == SOURCE
    for d in range(1, 8):
        assert lv(sim, x + d, y, 1) == SOURCE - d and lv(sim, x, y - d, 1) == SOURCE - d
    assert lv(sim, x + 8, y, 1) == 0
    assert sum(len(c) for c in sim.water.at.values()) == 1 + sum(4 * k for k in range(1, 8))     # a diamond, no more


def test_down_first_a_waterfall_off_a_step(world):
    sim, a = world
    ty = a.y - 4
    for x in range(a.x - 3, a.x + 1):
        sim.world.set(x, ty, level=2)                       # a terrace two up, west of a.x + 1
    edge, low = a.x, a.x + 1
    sim.water.pour(a.x - 3, ty, 3)
    steps(sim, 20)
    assert lv(sim, edge, ty, 3) == SOURCE - 3               # it ran to the edge...
    assert lv(sim, low, ty, 3) == SOURCE - 4 and lv(sim, low, ty, 2) == FALL and lv(sim, low, ty, 1) == FALL     # ...over it, and fell
    assert lv(sim, low + 1, ty, 3) == 0 and lv(sim, low + 1, ty, 2) == 0           # nothing runs sideways in the air
    assert lv(sim, low + 1, ty, 1) == FALL - 1                                      # it spreads again at the foot


def test_water_with_no_source_dries_up(world):
    sim, a = world
    a.add("watering_can")
    a.can = CAN_SIZE
    x, y = a.x + 1, a.y
    assert run(sim, a, "water", {"dir": "E", "with": "watering_can", "pour": True})["ok"]
    a.y += 9                                                  # (out of it: it would carry you off)
    steps(sim, 10)
    assert len(sim.water.at) > 50
    a.y -= 9
    assert run(sim, a, "water", {"x": x, "y": y, "with": "watering_can"})["ok"] and a.can == CAN_SIZE     # taken back up
    a.y += 9
    steps(sim, 20)
    assert not sim.water.at


def test_a_block_dams_it_and_the_tunnel_behind_dries(world):
    sim, a = world
    rx, y = a.x + 2, a.y + 3
    sim.world.set(rx, y, ground="water")
    dig_hole(sim, range(rx + 1, rx + 6), y, -1)             # a trench one deep from the river
    steps(sim, 12)
    assert all(lv(sim, x, y, 0) for x in range(rx + 1, rx + 6))
    a.add("dirt")
    a.x, a.y = rx + 1, y - 1                                  # (beside the cut)
    r = run(sim, a, "place", {"x": rx + 1, "y": y, "z": 0, "item": "dirt"})
    assert r["ok"], (r["error"], r.get("detail"))           # a dam in the cut
    assert lv(sim, rx + 1, y, 0) == 0
    steps(sim, 20)
    assert not any(lv(sim, x, y, 0) for x in range(rx + 2, rx + 6))


def test_a_flooded_tunnel_floods_on_as_it_is_dug(world):
    sim, a = world
    rx, y = a.x + 2, a.y + 3
    sim.world.set(rx, y, ground="water")
    dig_hole(sim, range(rx + 1, rx + 3), y, -2)
    steps(sim, 10)
    assert lv(sim, rx + 2, y, -1) and not lv(sim, rx + 3, y, -1)
    for x in range(rx + 3, rx + 6):                          # dug on, a cell at a time: the water follows into each
        sim.world.set_cell(x, y, -1, False)
        steps(sim, 2)
        assert lv(sim, x, y, -1)


def test_deep_running_water_is_swum_and_carries_you(world):
    sim, a = world
    x, y = a.x, a.y
    sim.water._put(x, y, 1, (FALL, NOHEAD, 1))               # running water over your feet
    sim.water._put(x + 1, y, 1, (FALL - 1, NOHEAD, 2))
    sim.water._put(x + 2, y, 1, (FALL - 2, NOHEAD, 3))
    assert sim.swimming(a) and sim.stride(a, {}) == 0.4
    sim.world.set_cell(x - 1, y, 1, True)
    sim.water.due.clear()
    sim.water.poke = lambda *c: None                         # (held still: only the carrying is looked at here)
    for _ in range(12):
        sim.step()
    assert (a.x, a.y) != (x, y) and a.x > x                  # carried along it, downstream


def test_water_runs_only_where_someone_is(world):
    sim, a = world
    far = a.x + 400
    for i in range(far - 40, far + 40):
        for j in range(a.y - 2, a.y + 3):
            sim.world.set(i, j, ground="dirt", level=0)
    sim.water.pour(far, a.y, 1)
    steps(sim, 8)
    assert len(sim.water.at) == 1                            # nobody near: it waits
    a.x = far - 2
    steps(sim, 30)
    assert len(sim.water.at) > 1


def test_a_step_looks_at_a_bounded_number_of_cells(world):
    sim, a = world
    sim.step()                                               # (the ticking area: round whoever is online)
    for i in range(-30, 31):
        for j in range(-30, 31):
            sim.water.due.add((a.x + i, a.y + j, 1))
    assert sim.water.step(sim.near_water) == BUDGET and len(sim.water.due) > 0


def test_an_old_save_keeps_its_water_as_sources_and_its_dug_holes_flood(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    clear(sim, a)
    rx, y = a.x + 2, a.y + 3
    sim.world.set(rx, y, ground="water")
    sim.water.at.clear()
    sim.close()
    import sqlite3
    db = sqlite3.connect(tmp_path / "w.sqlite")             # as a save from before water flowed: no flag, no water table
    db.execute("DELETE FROM meta WHERE key='flow'")
    db.execute("DROP TABLE water")
    db.commit()
    db.close()
    sim = make(tmp_path)
    sim.world.set_cell(rx + 1, y, 0, False)                 # (a hole dug beside it before: as the save had it)
    sim.close()
    db = sqlite3.connect(tmp_path / "w.sqlite")
    db.execute("DELETE FROM meta WHERE key IN ('flow', 'water_due')")
    db.commit()
    db.close()
    sim = make(tmp_path)
    assert Path(tmp_path / "w.before-flow.sqlite").exists()
    assert sim.world.ground(rx, y) == "water" and sim.water.lv(rx, y, 0) == SOURCE
    assert (rx + 1, y, 0) in sim.water.due
    a = sim.by_name["Ash"]
    sim.keep_loaded = False
    a.online = True
    steps(sim, 3)
    assert sim.water.lv(rx + 1, y, 0) == FALL
    sim.close()
