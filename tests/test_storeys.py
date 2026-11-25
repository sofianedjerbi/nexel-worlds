"""Building up a block at a time (sim/storeys.py): where a block rests, standing and building on it, the way up, what
is taken back, the save, the land raised, and the roofs of the worlds from before."""

from helpers import clear, make, run


def hut(s, x0, y0, w=5, h=4):
    """Walls round w x h tiles, a door in the middle of the south one."""
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + h):
            if x in (x0, x0 + w - 1) or y in (y0, y0 + h - 1):
                s.world.set(x, y, block="door" if (x, y) == (x0 + w // 2, y0 + h - 1) else "wood_wall")


def test_a_block_rests_on_a_wall_or_holds_to_the_block_beside_it(world):
    s, a = world
    a.add("roof", 9)
    s.world.set(a.x + 1, a.y, block="wood_wall")
    r = run(s, a, "place", {"x": a.x, "y": a.y - 2, "item": "roof"})              # in the air: nothing under it, nothing beside it
    assert r["error"] == "bad_target" and "rests on the block or the wall under it" in r["detail"]
    assert run(s, a, "place", {"x": a.x + 1, "y": a.y, "item": "roof"})["ok"]     # on the wall: a storey up
    assert s.floors.get(a.x + 1, a.y, 3) == ["roof", "none"] and s.world.solid(a.x + 1, a.y, 3) and not s.world.solid(a.x + 1, a.y, 2)
    assert run(s, a, "place", {"dir": "N", "item": "roof"})["error"] == "bad_target"    # (north of you: no block beside it yet)
    assert run(s, a, "place", {"x": a.x + 1, "y": a.y - 1, "item": "roof"})["ok"]  # beside that block
    assert run(s, a, "place", {"dir": "N", "item": "roof"})["ok"]                 # ...and now there is one
    assert set(s.floors.at) == {(a.x + 1, a.y), (a.x + 1, a.y - 1), (a.x, a.y - 1)} and a.count("roof") == 6
    assert run(s, a, "place", {"x": a.x + 1, "y": a.y, "item": "roof", "z": 3})["error"] == "bad_target"   # a block is there
    assert run(s, a, "place", {"x": a.x, "y": a.y - 1, "item": "roof", "z": 2})["error"] == "bad_target"   # no room left to stand under it
    assert s.sheltered(a.x, a.y - 1) and not s.sheltered(a.x - 3, a.y)             # under it: sheltered
    assert s.world.block(a.x + 1, a.y) == "wood_wall" and s.world.level(a.x + 1, a.y) == 0    # what is under it is as it was
    assert not s.in_cave(a) and s.land_col(a.x + 1, a.y) == s.land_col(a.x - 3, a.y)    # ...and the land: no hill, no cave
    assert run(s, a, "craft", {"recipe": "roof"})["error"] == "missing_items"
    a.add("wood", 1)
    assert run(s, a, "craft", {"recipe": "roof"})["ok"] and a.count("roof") == 8   # a log: two blocks of roof


def test_a_second_floor_is_stood_on_and_built_on_by_steps_of_blocks(world):
    """Walls, a floor of planks over them, two blocks for steps (one high, then two): up you walk, a jump a block;
    upstairs a wall is put, shuts the way, and is taken back; the room under is as it was."""
    s, a = world
    x, y = a.x, a.y
    hut(s, x + 2, y - 2, 5, 5)                                   # rooms x+3..x+5, y-1..y+1; the door at (x+4, y+2)
    a.add("plank", 40)
    a.add("wood_wall", 3)
    a.x, a.y = x + 4, y                                          # in the middle of the room
    for j in range(y - 2, y + 3):
        for i in range(x + 2, x + 7):
            if (i, j) not in ((x + 3, y), (x + 3, y + 1)):       # (the stairwell: left open)
                assert run(s, a, "place", {"x": i, "y": j, "item": "plank", "z": 3})["ok"], (i - x, j - y)
    assert run(s, a, "place", {"x": x + 3, "y": y + 1, "item": "plank"})["ok"]     # the room's floor, laid in the ground as ever
    assert s.world.ground(x + 3, y + 1) == "floor" and s.world.level(x + 3, y + 1) == 0
    assert run(s, a, "place", {"x": x + 3, "y": y + 1, "item": "plank", "z": 1})["ok"]    # a step: a block on the floor
    assert run(s, a, "place", {"x": x + 3, "y": y, "item": "plank", "z": 1})["ok"]
    assert run(s, a, "place", {"x": x + 3, "y": y, "item": "plank", "z": 2})["ok"]        # ...and one two blocks high
    assert s.world.surfaces(x + 3, y) == [2] and s.world.surfaces(x + 4, y) == [0, 3]
    r = run(s, a, "move_to", {"x": x + 3, "y": y - 1})                             # the tile north of the steps: reached under the floor
    assert r["ok"] and s.height(a) == 0 and s.sheltered(a.x, a.y)
    a.x, a.y = x + 4, y + 1
    for d, z in (("W", 1), ("N", 2), ("N", 3), ("E", 3)):                         # up the steps (a jump each: blocks, not stairs) and onto the floor
        assert run(s, a, "jump" if z > s.height(a) else "step", {"dir": d})["ok"] and s.height(a) == z, (d, z)
    assert (a.x, a.y) == (x + 4, y - 1)
    assert run(s, a, "place", {"dir": "E", "item": "wood_wall"})["ok"]            # a wall on the floor you stand on
    assert s.floors.get(x + 5, y - 1, 3) == ["plank", "wood_wall"] and s.world.block(x + 5, y - 1) == "none"
    assert run(s, a, "step", {"dir": "E"})["error"] == "blocked"
    assert run(s, a, "place", {"dir": "E", "item": "wood_wall"})["error"] == "occupied"
    assert run(s, a, "place", {"dir": "S", "item": "chest"})["error"] in ("bad_target", "missing_item")
    r = run(s, a, "dig", {"dir": "E", "with": "axe"})                               # taken back: the wall first
    assert r["ok"] and s.floors.get(x + 5, y - 1, 3) == ["plank", "none"] and a.count("wood_wall") == 3
    assert run(s, a, "step", {"dir": "E"})["ok"] and s.height(a) == 3
    a.z = 0                                                                         # someone in the room under you, by the door
    a.x, a.y = x + 4, y + 1
    assert s.height(a) == 0 and run(s, a, "step", {"dir": "S"})["ok"] and (a.x, a.y) == (x + 4, y + 2)
    # the way somewhere is worked out with heights: from outside, up to the floor over the room (by the door, the steps)
    a.x, a.y = x + 4, y + 3
    r = run(s, a, "move_to", {"x": x + 5, "y": y})
    assert r["ok"] and (a.x, a.y) == (x + 5, y) and s.height(a) == 0               # (the room is nearer than the floor over it)


def test_a_block_is_taken_back_top_first_and_kept_in_the_save(tmp_path):
    s = make(tmp_path)
    a = s.login("Ash", "tok")
    clear(s, a)
    s.world.set(a.x + 1, a.y, block="wood_wall")
    a.add("roof", 2)
    a.add("plank", 3)
    a.add("chair", 1)
    assert run(s, a, "place", {"dir": "E", "item": "roof"})["ok"] and run(s, a, "place", {"x": a.x, "y": a.y, "item": "roof"})["ok"]
    r = run(s, a, "unroof", {"x": a.x, "y": a.y})
    assert r["ok"] and r["changed"]["inventory"] == {"roof": 1} and a.count("roof") == 1
    assert run(s, a, "unroof", {"x": a.x, "y": a.y})["error"] == "bad_target"
    assert run(s, a, "place", {"dir": "W", "item": "plank"})["ok"]                 # a floor in the ground...
    assert run(s, a, "place", {"dir": "W", "item": "plank", "z": 1})["ok"]         # a block on it, a block on that
    assert run(s, a, "place", {"dir": "W", "item": "plank", "z": 2})["ok"]
    assert run(s, a, "dig", {"dir": "W", "z": 1})["error"] == "bad_target"         # not from under the one on top
    assert run(s, a, "dig", {"dir": "W"})["ok"] and not s.world.solid(a.x - 1, a.y, 2) and a.count("plank") == 1    # by hand: the top one
    assert run(s, a, "place", {"dir": "W", "item": "chair", "z": 1})["ok"]         # a chair on the block left
    at, step = (a.x + 1, a.y), (a.x - 1, a.y)
    s.close()
    again = make(tmp_path)
    assert again.floors.at == {at: {3: ["roof", "none"]}, step: {1: ["plank", "chair"]}}
    assert again.world.solid(*at, 3) and again.world.level(*step) == 1 and again.thing(*step, 1) == "chair"
    b = again.login("Ash", "tok")
    assert run(again, b, "dig", {"dir": "W"})["ok"] and b.count("chair") == 1      # the chair, then the block
    assert run(again, b, "dig", {"dir": "W"})["ok"] and again.world.level(*step) == 0 and b.count("plank") == 2
    again.close()


def test_earth_raises_the_land_a_layer(world):
    s, a = world
    a.add("dirt", 3)
    s.world.set(a.x + 1, a.y, ground="grass")
    assert run(s, a, "place", {"dir": "E", "item": "dirt"})["ok"]
    assert s.world.level(a.x + 1, a.y) == 1 and s.world.ground(a.x + 1, a.y) == "grass" and not s.floors.at   # the land itself, a layer up
    assert run(s, a, "jump", {"dir": "E"})["ok"] and s.height(a) == 1              # a jump up onto it
    assert run(s, a, "place", {"x": a.x, "y": a.y, "item": "dirt"})["error"] == "occupied"    # not under your own feet
    s.world.set(a.x + 1, a.y, block="rock")
    assert run(s, a, "place", {"dir": "E", "item": "dirt"})["error"] in ("occupied", "bad_target")


def test_a_roof_from_before_becomes_a_block_once(tmp_path):
    """A world saved when roofs were tiles over tiles (table `roofs`): each is a roof block now, a storey over its
    ground, the whole roof at one height; a second opening adds nothing."""
    s = make(tmp_path)
    a = s.login("Ash", "tok")
    clear(s, a, 9)
    hut(s, a.x + 2, a.y - 2)
    tiles = [(x, y) for x in range(a.x + 2, a.x + 7) for y in range(a.y - 2, a.y + 2)]
    s.store.db.execute("CREATE TABLE roofs(x INTEGER, y INTEGER, PRIMARY KEY(x, y))")
    s.store.db.executemany("INSERT INTO roofs VALUES(?,?)", tiles)
    s.store.set_meta("floors", 0)
    s.close()
    old = make(tmp_path)
    assert old.floors.at == {t: {3: ["roof", "none"]} for t in tiles} and all(old.world.solid(*t, 3) for t in tiles)
    b = old.login("Ash", "tok")
    assert run(old, b, "unroof", {"x": a.x + 2, "y": a.y - 2})["ok"]               # (a block taken off stays off)
    old.close()
    last = make(tmp_path)
    assert len(last.floors) == 19
    last.close()


def test_the_way_goes_up_the_steps_to_the_floor_asked_for(world):
    """move_to with a height: that tile on that floor. Without one: the nearest place on the tile."""
    s, a = world
    x, y = a.x, a.y
    hut(s, x + 2, y - 2, 5, 5)
    a.add("plank", 40)
    a.x, a.y = x + 4, y
    for j in range(y - 2, y + 3):
        for i in range(x + 2, x + 7):
            if (i, j) not in ((x + 3, y), (x + 3, y + 1)):
                assert run(s, a, "place", {"x": i, "y": j, "item": "plank", "z": 3})["ok"]
    for i, j, z in ((x + 3, y + 1, 1), (x + 3, y, 1), (x + 3, y, 2)):
        s.world.set(i, j, ground="floor")
        assert run(s, a, "place", {"x": i, "y": j, "item": "plank", "z": z})["ok"]
    a.x, a.y = x + 4, y + 3                                                       # outside, south of the door
    r = run(s, a, "move_to", {"x": x + 5, "y": y - 1, "z": 3})
    assert r["ok"] and (a.x, a.y, s.height(a)) == (x + 5, y - 1, 3) and r["steps"] == 7      # in by the door, up the steps, across the floor
    r = run(s, a, "move_to", {"x": x + 5, "y": y + 1})                            # ...and down again (no height asked: the nearest)
    assert r["ok"] and (a.x, a.y) == (x + 5, y + 1)


def test_an_agent_sees_the_roof_it_laid(world):
    """The observation's roofs: 1 where something is over the tile, as a screen draws the roof (sent only when any)."""
    from helpers import run
    from nexel_worlds.sim.constants import VIEW_R
    sim, a = world
    assert "roofs" not in sim.observe(a)
    x, y = a.x - 1, a.y - 1
    for dx in range(-1, 4):
        for dy in range(-1, 4):
            if dx in (-1, 3) or dy in (-1, 3):
                sim.world.set(x + dx, y + dy, block="stone_wall")
    a.add("roof", 30)
    for dx in range(-1, 4):
        for dy in range(-1, 4):
            assert run(sim, a, "place", {"item": "roof", "x": x + dx, "y": y + dy})["ok"]
    roofs = sim.observe(a)["roofs"]
    assert roofs[VIEW_R][VIEW_R] == "1" and roofs[VIEW_R - 4][VIEW_R] == "0"
