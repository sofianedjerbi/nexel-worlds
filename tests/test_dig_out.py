"""Out of any hole you can dig into ("how do i climb up? why i cant??"): `dig` takes the cell over your own head
(dir: up) and the cell in front of you at your head's height (dir and z): a step. The owner's pocket, dug under
their own stair's treads, is rebuilt here from the columns of their world."""

import pytest
from helpers import run

from megastructure.gen import LOW

# The owner's world round (-26, -3), as saved: each column's runs (gen.col_runs: solid up to the first height, empty
# up to the next, solid...), rows y = -6..-2, columns x = -31..-22. The hill over it (its last run, 4 to 9) is cut
# level at 0 here. The stair comes down from the east along y = -3 (-22: -9 ... -28: -12), two cells of air over each
# tread; its foot was dug out (-29: -14, -30: -15): no step is left up to the treads, and a pocket a cell high
# was dug under them (-26, -3: floor -13, the tread at -11 over your head).
X0, Y0 = -31, -6
RUNS = [
    [[], [], [], [], [], [-13, -12], [-13, -12], [], [], []],
    [[], [], [], [], [], [-13, -12], [-13, -12], [], [], []],
    [[], [], [], [-14, -13], [-14, -13], [-13, -12], [], [], [], []],
    [[-15, -14], [-15, -12], [-14, -11], [-14, -13, -12, -9], [-14, -12, -11, -9], [-13, -12, -11, -9], [-11, -9], [-11, -9], [-10, -8], [-9, -7]],
    [[-15, -14], [-15, -14], [-15, -14, -13, -12], [], [], [], [], [], [], []],
]


def pocket(s, a, at=(-26, -3, -13)):
    """The pocket in solid land up to 0, the agent in it."""
    for y in range(Y0 - 4, Y0 + 9):
        for x in range(X0 - 4, X0 + 30):
            s.world.set(x, y, ground="dirt", block="none", level=0)
    for j, row in enumerate(RUNS):
        for i, runs in enumerate(row):
            for k in range(0, len(runs), 2):
                for z in range(runs[k] + 1, runs[k + 1] + 1):
                    s.world.set_cell(X0 + i, Y0 + j, z, False)
    a.x, a.y, a.z = at
    assert s.height(a) == at[2]
    return s.world


def out(s, a):
    return not s.world.covered(a.x, a.y, s.height(a))


def climb(s, a, d, tool=True, limit=80):
    """Cut steps up, one way: the cell over your head, the cell in front at your head's height, a step. -> actions"""
    from megastructure.tiles import DIRS
    n, args = 0, {"with": "pickaxe"} if tool else {}
    while s.height(a) < 0 and n < limit:
        h, fx, fy = s.height(a), a.x + DIRS[d][0], a.y + DIRS[d][1]
        assert s.world.solid(fx, fy, h + 1), "a way that goes down: not this test's"
        if s.world.solid(a.x, a.y, h + 2):
            r = run(s, a, "dig", {"dir": "up", **args})
            assert r["ok"] and r["cell"] == [a.x, a.y, h + 2], r
        elif s.world.solid(fx, fy, h + 2):
            r = run(s, a, "dig", {"dir": d, "z": h + 2, **args})
            assert r["ok"] and r["cell"] == [fx, fy, h + 2], r
        else:
            assert run(s, a, "step", {"dir": d})["ok"] and s.height(a) == h + 1
        n += 1
    return n


def test_the_owners_pocket_is_shut_and_a_pickaxe_cuts_steps_up_out_of_it(world):
    s, a = world
    w = pocket(s, a)
    a.add("pickaxe")
    assert w.surfaces(-26, -3)[:2] == [-13, -11] and w.surfaces(-25, -3)[0] == -11       # the stair's tread over your head, a wall two high east
    r = run(s, a, "step", {"dir": "E"})
    assert not r["ok"] and "dig dir=up" in r["detail"] and "z=-11" in r["detail"]        # the refusal says what makes a step of it
    cols = {(x, y): w.col(x, y) for x in range(-33, -19) for y in range(-8, 1)}
    r = run(s, a, "dig", {"dir": "up", "with": "pickaxe"})                               # the tread over your head: that cell, no other
    assert r["ok"] and r["cell"] == [-26, -3, -11] and r["got"] == {"stone_block": 1}
    assert w.col(-26, -3) == cols[-26, -3] & ~(1 << (-11 - LOW))
    r = run(s, a, "dig", {"dir": "E", "z": -11, "with": "pickaxe"})                      # the wall at your head's height: that cell
    assert r["ok"] and r["cell"] == [-25, -3, -11] and w.col(-25, -3) == cols[-25, -3] & ~(1 << (-11 - LOW))
    assert all(w.col(*t) == c for t, c in cols.items() if t not in ((-26, -3), (-25, -3)))   # and nothing else moved
    assert run(s, a, "step", {"dir": "E"})["ok"] and (a.x, s.height(a)) == (-25, -12)   # the step
    n = 3 + climb(s, a, "E")
    assert out(s, a) and s.height(a) == 0 and n == 30, n                         # three actions a layer at the most: bounded
    assert all(w.col(x, y) == c for (x, y), c in cols.items() if y != -3)                # the stair cut is a tile wide
    assert a.hp == 20


def test_from_the_stairs_dug_out_foot_the_way_back_onto_the_treads_is_two_digs(world):
    """Where the owner stood stuck: on the dug-out foot (-29, -3) at -14, the tread at -12 two up. The ledge south
    is a hop; from it the cell over your head, the cell at your head's height east, and the stair is a step away."""
    s, a = world
    pocket(s, a, at=(-29, -3, -14))
    a.add("pickaxe")
    assert run(s, a, "step", {"dir": "E"})["ok"] and s.height(a) == -14                  # east: under the tread, not onto it
    assert run(s, a, "step", {"dir": "W"})["ok"]
    assert run(s, a, "step", {"dir": "S"})["ok"] and s.height(a) == -13
    r = run(s, a, "dig", {"dir": "up", "with": "pickaxe"})
    assert r["ok"] and r["cell"] == [-29, -2, -11]
    r = run(s, a, "dig", {"dir": "E", "z": -11, "with": "pickaxe"})
    assert r["ok"] and r["cell"] == [-28, -2, -11]
    assert run(s, a, "step", {"dir": "E"})["ok"] and s.height(a) == -12
    assert run(s, a, "step", {"dir": "N"})["ok"] and (a.x, a.y, s.height(a)) == (-28, -3, -12)   # on the tread
    for want in (-11, -11, -11, -11, -10, -9):
        assert run(s, a, "step", {"dir": "E"})["ok"] and s.height(a) == want             # and up the owner's stair


def test_a_ladder_takes_you_onto_the_tread_once_there_is_head_room(world):
    """A ladder on the dug-out foot, against the tread two up: the land over the foot is a cell too low for it
    ("Needs something taller behind"). With head room over it, it stands, and climbs onto the tread."""
    s, a = world
    w = pocket(s, a, at=(-30, -3, -15))
    for x, y in ((-30, -3), (-30, -2), (-29, -2)):
        w.set_cell(x, y, -14, True)                                                      # (the foot level with what is round it: nothing stands on an edge)
    a.add("ladder")
    assert s.height(a) == -14
    assert run(s, a, "place", {"dir": "E", "item": "ladder", "z": -14})["error"] == "bad_target"
    w.set_cell(-29, -3, -10, False)                                                      # head room: the foot's own column open a cell higher
    assert run(s, a, "place", {"dir": "E", "item": "ladder", "z": -14})["ok"] and w.block(-29, -3) == "ladder"
    assert run(s, a, "step", {"dir": "E"})["ok"] and s.height(a) == -14
    assert run(s, a, "step", {"dir": "E"})["ok"] and (a.x, s.height(a)) == (-28, -12)   # up the ladder, onto the tread


@pytest.mark.parametrize("tool", [True, False])
def test_out_of_a_one_tile_shaft_six_deep_with_a_pickaxe_or_bare_hands_and_no_ladder(world, tool):
    s, a = world
    x, y = a.x, a.y
    if tool:
        a.add("pickaxe")
    for _ in range(6):
        assert run(s, a, "dig_down", {"with": "pickaxe"} if tool else {})["ok"]
    assert s.height(a) == -6 and all(not run(s, a, "step", {"dir": d})["ok"] for d in "NESW")
    before = {(i, j): s.world.col(i, j) for i in range(x - 2, x + 9) for j in range(y - 2, y + 3)}
    n = climb(s, a, "E", tool)
    assert s.height(a) == 0 and a.x == x + 6 and n == 15, n                               # the first step: its cell, a step; then three actions a layer (two for the last: the sky is over it)
    dug = {(i - x, z) for (i, j), c in before.items() for z in range(-8, 2) if (c >> (z - LOW)) & 1 and not s.world.solid(i, j, z)}
    assert all(s.world.col(i, j) == c for (i, j), c in before.items() if j != y)
    want = {(k, k - 5) for k in range(1, 6)} | {(k, k - 4) for k in range(1, 5)}          # each step's head room: over it, and over the one before
    assert dug == want, sorted(dug ^ want)                                                # the cells aimed at, no other


def test_the_cell_over_your_head_is_not_dug_from_under_someone_nor_where_there_is_none(world):
    from megastructure.sim import Creature
    s, a = world
    x, y = a.x, a.y
    a.add("pickaxe")
    r = run(s, a, "dig", {"dir": "up", "with": "pickaxe"})
    assert r["error"] == "bad_target" and "z=2" in r["detail"]                           # open sky: what to dig for a step, said
    s.world.set_cell(x, y, 2, True)
    s.creatures[99] = Creature(99, "chicken", x, y, 4, z=2)
    assert run(s, a, "dig", {"dir": "up", "with": "pickaxe"})["error"] == "occupied"     # a hen on it: it would fall on you
    del s.creatures[99]
    s.world.set_cell(x, y, 3, True); s.world.set_cell(x, y, 4, True)
    assert run(s, a, "dig", {"x": x, "y": y, "z": 3, "with": "pickaxe"})["error"] == "out_of_range"   # two over your head, in the land: not from here
    r = run(s, a, "dig", {"x": x, "y": y, "z": 2, "with": "pickaxe"})                    # (by its place, as a screen sends it)
    assert r["ok"] and r["cell"] == [x, y, 2] and s.world.solid(x, y, 3) and not s.world.solid(x, y, 2)


def test_nothing_is_reached_through_the_land(world):
    """"Chop tree (slow)" from a tunnel four layers under the tree: the wall in front of you has a tree on top. It
    was within reach as the crow flies (a layer is half a tile). Under the sky, at a cliff's foot, it still is."""
    s, a = world
    x, y = a.x, a.y
    s.world.set(x + 1, y, level=4, block="flower")
    assert run(s, a, "dig", {"dir": "E"})["ok"] and a.count("flower") == 1               # a ledge, the sky over you: your hand goes up
    s.world.set(x + 1, y, block="tree")
    for z in (2, 3, 4):
        s.world.set_cell(x, y, z, True)                                                  # land over your head: a tunnel
    r = run(s, a, "dig", {"dir": "E"})
    assert r["error"] == "out_of_range" and s.world.block(x + 1, y) == "tree"
    a.add("pickaxe")
    assert run(s, a, "dig", {"dir": "E", "with": "pickaxe"})["ok"] and not s.world.solid(x + 1, y, 1)   # the wall itself: dug on
    assert s.world.block(x + 1, y) == "tree"
    s.world.set(x - 1, y, level=-4, block="flower")                                      # a flower at the bottom of a pit beside you: open over it
    assert run(s, a, "dig", {"dir": "W"})["ok"] and a.count("flower") == 2
