"""Roofs laid a tile at a time (sim/roofing.py): where one rests, taking it back, the save, and the old houses' own."""

from helpers import clear, make, run


def hut(s, x0, y0, w=5, h=4):
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + h):
            if x in (x0, x0 + w - 1) or y in (y0, y0 + h - 1):
                s.world.set(x, y, block="wood_wall")


def test_a_roof_rests_on_a_wall_or_on_the_roof_beside_it(world):
    s, a = world
    a.add("roof", 9)
    s.world.set(a.x + 1, a.y, block="wood_wall")
    r = run(s, a, "place", {"x": a.x, "y": a.y - 2, "item": "roof"})              # in the air: nothing beside it
    assert r["error"] == "bad_target" and "rests on a wall" in r["detail"]
    assert run(s, a, "place", {"x": a.x + 1, "y": a.y, "item": "roof"})["ok"]     # on the wall
    assert run(s, a, "place", {"dir": "N", "item": "roof"})["error"] == "bad_target"    # (north of you: not beside a roof yet)
    assert run(s, a, "place", {"x": a.x + 1, "y": a.y - 1, "item": "roof"})["ok"]  # beside that roof tile
    assert run(s, a, "place", {"dir": "N", "item": "roof"})["ok"]                 # ...and now it is
    assert {(a.x + 1, a.y), (a.x + 1, a.y - 1), (a.x, a.y - 1)} == s.roofed.at and a.count("roof") == 6
    assert run(s, a, "place", {"x": a.x + 1, "y": a.y, "item": "roof"})["error"] == "occupied"
    assert s.sheltered(a.x, a.y - 1) and not s.sheltered(a.x - 3, a.y)             # under it: sheltered
    assert s.world.block(a.x + 1, a.y) == "wood_wall"                              # what is under it is as it was
    assert run(s, a, "craft", {"recipe": "roof"})["error"] == "missing_items"
    a.add("wood", 1)
    assert run(s, a, "craft", {"recipe": "roof"})["ok"] and a.count("roof") == 8   # a log: two tiles of roof


def test_a_roof_tile_is_taken_back_and_kept_in_the_save(tmp_path):
    s = make(tmp_path)
    a = s.login("Ash", "tok")
    clear(s, a)
    s.world.set(a.x + 1, a.y, block="wood_wall")
    a.add("roof", 2)
    assert run(s, a, "place", {"dir": "E", "item": "roof"})["ok"] and run(s, a, "place", {"x": a.x, "y": a.y, "item": "roof"})["ok"]
    r = run(s, a, "unroof", {"x": a.x, "y": a.y})
    assert r["ok"] and r["changed"]["inventory"] == {"roof": 1} and a.count("roof") == 1
    assert run(s, a, "unroof", {"x": a.x, "y": a.y})["error"] == "bad_target"
    at = (a.x + 1, a.y)
    s.close()
    again = make(tmp_path)
    assert again.roofed.at == {at}
    again.close()


def test_a_house_from_before_gets_its_roof_once(tmp_path):
    """A world saved before roofs were laid by hand: its closed rooms (the ones the screen drew a roof over) are
    roofed when it is opened, room and walls; a second opening adds nothing."""
    s = make(tmp_path)
    a = s.login("Ash", "tok")
    clear(s, a, 9)
    hut(s, a.x + 2, a.y - 2)                                   # closed: 5 x 4 with its walls
    for x in range(a.x - 6, a.x - 2):                          # open: one side of a box
        s.world.set(x, a.y - 4, block="wood_wall")
    s.store.set_meta("roofs", 0)
    s.close()
    old = make(tmp_path)
    assert old.roofed.at == {(x, y) for x in range(a.x + 2, a.x + 7) for y in range(a.y - 2, a.y + 2)}
    old.roofed.set(a.x + 2, a.y - 2, False)                    # (a tile taken off stays off)
    old.close()
    last = make(tmp_path)
    assert len(last.roofed) == 19
    last.close()
