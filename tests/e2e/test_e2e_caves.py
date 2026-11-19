"""Caves as drawn: an opening in a hill's south face, as wide and as high as the empty cells; the cave you're in seen
through the hill as anywhere you are hidden; and being hidden behind a hill. (The land is blocks, voxels.js: an
opening is where the hill has no block, and what is seen of it is read off the screen.)"""

import pytest

from test_e2e_digging import LAND, SEEN, cut, earth

green = lambda c: c[1] > c[0] + 6 and c[1] > c[2] + 30      # the meadow, in the open or in a cave's dark

pytestmark = pytest.mark.usefixtures("circle_view")      # (the view that had a circle when the land was painted flat: built roofs still go by it, conftest.py)


def hill(game, x0, y0, w, h, caves, top=4):
    """A hill `top` high with its top-left at (x0, y0) from you; caves: {(dx, dy): empty cells over the ground}."""
    cells = [[(i, j) for i in range(x0, x0 + w)] for j in range(y0, y0 + h)]
    game.stamp(x0, y0, ["." * w] * h, levels=["".join("0" if c in caves else str(top) for c in r) for r in cells],
               roofs=["".join(str(top) if c in caves else "0" for c in r) for r in cells],
               heads=["".join(str(caves.get(c, 0)) for c in r) for r in cells])
    drawn(game)


def drawn(game):
    """Give the frame time to draw the caves as they are now (the land's blocks are made again as the frame draws)."""
    game.sleep(500)
    game.wait("!dirtyTiles.length", 8000)
    game.sleep(900)


def test_an_opening_is_as_wide_and_as_high_as_the_empty_cells_on_each_side(game):
    """A hill four high north of you, a cave in its south face two tiles wide and two cells high: on the screen the
    face is open there, a cave's dark mouth, across both tiles (no wall at their seam), two layers high, not three;
    beside it and over it the hill's front, earth. (A hill's east, west and north sides have no face of their
    own with blocks: an opening there does not show from outside.)"""
    game.clear_area(9)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    # a hill 7x7 north of you; in it: two tiles wide and two cells high to the south, one by one to the east, to the
    # west, and one to the north
    caves = {(-1, -3): 2, (0, -3): 2, (-1, -4): 2, (0, -4): 2, (3, -6): 1, (2, -6): 1, (-3, -6): 1, (-2, -6): 1, (0, -9): 1, (0, -8): 1}
    hill(game, -3, -9, 7, 7, caves)
    assert game.js(f"[surfacesAt({x - 1}, {y - 3}), surfacesAt({x}, {y - 3}), surfacesAt({x + 1}, {y - 3})]") == [[0, 4], [0, 4], [4]] and game.js("xray.a") < .01
    px = lambda *spots: game.js(LAND, [[x + tx, y - 3, 0, ax, ay] for tx, ax, ay in spots])     # (the face's foot row: art px from the tile's corner at the ground's level)
    inside = px((-1, 8, 12), (-1, 15, 12), (0, 0, 12), (0, 8, 12), (0, 8, 2))
    assert all(cut(c) for c in inside), inside               # the mouth, dark: both tiles, their seam, up to two layers
    over, beside, far = px((0, 8, -4), (1, 8, 12), (-2, 8, 12))
    assert earth(over) and earth(beside) and earth(far), (over, beside, far)     # the third layer over it, and the face on each side of it


def test_in_a_cave_you_are_seen_through_the_hill_as_anywhere_you_are_hidden(game):
    """A cave had a view of its own: opened for good while you were in it, its floor flat in the hill's top, shadowed
    along its edges. "everything should have the same view ! ... an unique 'player is hided, xray on' view": in a cave
    you are hidden by the hill over you, and seen through it as behind a hill or down a hole (xray.js): the room's
    floor is where things on it stand, and on the screen it is its floor, where you are and beside you; the hill
    beside the room is still where things on it stand."""
    game.clear_area(9)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    hill(game, -3, -8, 7, 7, {(i, j): 2 for i in (-1, 0, 1) for j in range(-6, -1)})      # a room 3 wide, open to the south
    assert game.js("xray.a") < .01                                                    # outside: the hill
    assert game.js(f"[standAt({x}, {y - 4}), hiddenAt({x}, {y - 4})]") == [4, True]
    game.hold(["w"], 800)
    game.wait(SEEN, 20000); game.sleep(400)
    assert game.server()["in_cave"] and game.js("xray.pic.floor.size") == 15
    assert game.js(f"[standAt({x}, {y - 4}), standAt({x - 1}, {y - 4}), standAt({x - 2}, {y - 4}), hiddenAt({x}, {y - 6})]") == [0, 0, 4, False]
    my = game.pos()[1]
    floor = game.js(LAND, [[x, my, 0, 8, 8], [x - 1, my, 0, 8, 8], [x + 1, my, 0, 8, 8], [x, my - 1, 0, 8, 8]])
    assert all(green(c) for c in floor), floor                                        # its floor: the meadow's, under you, beside you, behind you
    top = game.js(LAND, [[x - 2, my, 4, 8, 8]])[0]
    assert green(top) and sum(top) > 1.2 * sum(floor[0]), (top, floor[0])             # past its side the hill stands, whole: its top, up in the light


def test_walking_into_a_hill_from_behind_it_you_stay_on_the_ground_and_in_sight(game):
    game.js("setOpt('above', 'cut')")
    game.clear_area(9)
    x, y = game.pos()
    hill(game, -3, 2, 7, 6, {(0, j): 2 for j in range(2, 6)})                         # a hill south of you, a tunnel in from its north side
    game.js("window.seen = []; (function f() { const p = ents.get('agent' + myId); window.seen.push([liftOf(p), unseen(p)]); requestAnimationFrame(f); })()")
    game.hold(["s"], 700)
    game.wait(SEEN, 20000); game.sleep(400)
    assert game.server()["in_cave"] and game.js("Math.max(...window.seen.map((s) => s[0]))") < .5 and not game.js("window.seen.some((s) => s[1])")   # (never drawn up on the hill, never gone)
    assert game.js(f"[seenUnder({x}, {y + 2}), seenUnder({x}, {y + 5}), seenUnder({x + 1}, {y + 3})]") == [0, 0, None]
    assert game.js("xrayShows(ents.get('agent' + myId))") > .9                        # you, through the hill in front
    assert game.js(f"xrayGone({x}, {y + 6})") and not game.js(f"xrayGone({x + 3}, {y + 5})")   # the hill in front of the tunnel is seen through; where it hides nothing of the place, it stays


def test_a_cave_wider_than_the_screen_round_you_is_seen_whole_and_who_is_at_its_far_end(game):
    """What was seen of a cave was as wide as the circle (nine tiles) unless the ground was dug: a cave eighteen tiles
    wide showed nine of them, a square hole in its hill. All of the place you are in is seen: every tile of its floor
    is of it, its two ends are on the screen, its floor, and who stands at its far end is seen."""
    game.clear_area(14)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-10, -9, ["." * 20] * 7, levels=["4" * 20] * 7)                        # a hill, a cave 18 x 5 in it,
    game.stamp(-9, -8, ["." * 18] * 5, levels=["0" * 18] * 5, roofs=["4" * 18] * 5, heads=["2" * 18] * 5)
    game.stamp(-9, -3, ["."], levels=["0"], roofs=["4"], heads=["2"])                 # its mouth south, at its west end
    game.rpc("dev_teleport", x=x - 1, y=y - 6, z=0)                                   # in its middle
    game.wait(f"myAt && myAt.x === {x - 1} && myAt.y === {y - 6}", 8000)
    game.wait("dirtyTiles.length === 0", 20000); game.wait(SEEN, 20000); game.sleep(400)
    assert game.js("xray.pic.floor.size") == 91
    ends = game.js(LAND, [[x - 9, y - 6, 0, 8, 8], [x + 8, y - 6, 0, 8, 8], [x - 9, y - 4, 0, 8, 8], [x + 8, y - 8, 0, 8, 8]])
    assert all(green(c) for c in ends), ends                                          # its two ends, its corners: its floor
    who = game.js(f"[{x - 9}, {x + 8}].map((X) => {{ const p = {{x: X, y: {y - 6}, e: {{kind: 'chicken', id: -1}}, zAt: {{x: X, y: {y - 6}, z: 0}}}}; return [xrayShows(p) > .9, unseen(p)]; }})")
    assert who == [[True, False], [True, False]], who


def test_standing_behind_a_hill_it_hides_you(game):
    """(As it hides anyone: you yourself are shown through it, in a circle (xray.js, turned off here; its own test is
    in test_e2e_relief.py).)"""
    game.clear_area(9)
    game.js("(() => { XRAY.from = 1e9; XRAY.full = 2e9; return 1; })()")
    x, y = game.pos()
    game.stamp(-3, 1, ["......."] * 4, levels=["4444444"] * 4)                         # a hill just south of you
    game.sleep(900)
    game.rpc("dev_time", phase=.4)
    # where your body is on screen, the hill's top is drawn (as beside you), not you
    at = lambda dx, dy=.6: game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S), c = document.querySelector('canvas');
      const px = Math.round((ox + ({x + dx} + .5) * S) * DPR), py = Math.round((oy + ({y} + {dy}) * S) * DPR);
      return Array.from(c.getContext('2d').getImageData(px, py, 1, 1).data).slice(0, 3); }})()""")
    assert game.js(f"(4 - standAt({x}, {y})) * RELIEF_STEP > 0") and max(abs(a - b) for a, b in zip(at(0), at(2))) < 45   # (grass, give or take its tufts: not you, not a wall)
    for dy in (1.2, 1.8, 2.4, 3.0):                          # ...and nothing but its top further down it (no wall painted on it)
        assert max(abs(a - b) for a, b in zip(at(0, dy), at(2, dy))) < 45, dy
    game.hold(["w"], 500)                                    # two tiles north: out from behind it
    game.sleep(400)
    x2, y2 = game.pos()
    assert y2 < y - 1


def test_an_opening_higher_up_a_south_wall_is_up_the_wall(game):
    """A cave whose floor is a layer above the ground in front: its opening is up the wall: a layer of the hill's front
    under it, the cave's dark mouth, the front again over it."""
    game.clear_area(9)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-2, -6, ["....."] * 4, levels=["44444", "44144", "44144", "44144"], roofs=["00000", "00300", "00300", "00300"])
    drawn(game)
    assert game.js(f"surfacesAt({x}, {y - 3})") == [1, 4]
    under, inside, over, beside = game.js(LAND, [[x, y - 3, 0, 8, 12], [x, y - 3, 0, 8, 2], [x, y - 3, 0, 8, -12], [x + 1, y - 3, 0, 8, 2]])
    assert earth(under) and cut(inside) and earth(over) and earth(beside), (under, inside, over, beside)
