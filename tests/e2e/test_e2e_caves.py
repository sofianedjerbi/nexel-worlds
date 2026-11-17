"""Caves as drawn: openings on each side of a hill, as wide and as high as the empty cells; the cave you're in seen
through the hill as anywhere you are hidden; and being hidden behind a hill."""

import pytest

# a pixel [r, g, b, a] of the caves as drawn: tile (x, y), art px (ax, ay) from the tile's corner at sea level (from
# whichever block's overlay has something there: an opening is drawn from its first tile's block)
PX = """([x, y, ax, ay]) => { for (const b of blocks.values()) { if (!b.caveOv) continue;
    const X = OV_M + (x - b.bx * B) * 16 + ax, Y = OV_M + (y - b.by * B) * 16 + ay;
    if (X < 0 || Y < 0 || X >= b.caveOv.width || Y >= b.caveOv.height) continue;
    const d = Array.from(b.caveOv.getContext('2d').getImageData(X, Y, 1, 1).data); if (d[3]) return d; }
  return [0, 0, 0, 0]; }"""
HOLE, DEEP = [0x2a, 0x1d, 0x28], [0x1d, 0x14, 0x1c]           # the hole, and its darker depth

pytestmark = pytest.mark.usefixtures("circle_view")      # (the circle's tests: the view that has it, conftest.py)


def hill(game, x0, y0, w, h, caves, top=4):
    """A hill `top` high with its top-left at (x0, y0) from you; caves: {(dx, dy): empty cells over the ground}."""
    cells = [[(i, j) for i in range(x0, x0 + w)] for j in range(y0, y0 + h)]
    game.stamp(x0, y0, ["." * w] * h, levels=["".join("0" if c in caves else str(top) for c in r) for r in cells],
               roofs=["".join(str(top) if c in caves else "0" for c in r) for r in cells],
               heads=["".join(str(caves.get(c, 0)) for c in r) for r in cells])
    drawn(game)


def drawn(game):
    """Give the frame time to draw the caves as they are now (the overlay is made as the frame draws)."""
    game.sleep(500)
    game.wait("!dirtyTiles.length", 8000)
    game.sleep(900)


def test_an_opening_is_as_wide_and_as_high_as_the_empty_cells_on_each_side(game):
    game.clear_area(9)
    x, y = game.pos()
    # a hill 7x7 north of you; in it: two tiles wide and two cells high to the south, one by one to the east, to the
    # west, and one to the north
    caves = {(-1, -3): 2, (0, -3): 2, (-1, -4): 2, (0, -4): 2, (3, -6): 1, (2, -6): 1, (-3, -6): 1, (-2, -6): 1, (0, -9): 1, (0, -8): 1}
    hill(game, -3, -9, 7, 7, caves)
    px = lambda tx, ty, ax, ay: game.js(PX, [x + tx, y + ty, ax, ay])
    assert game.js(f"shownVoids({x - 1}, {y - 3}, 0, 1)") == [[1, 2]] and game.js(f"shownVoids({x + 3}, {y - 6}, 1, 0)") == [[1, 1]]
    assert game.js(f"shownVoids({x}, {y - 9}, 0, -1)") == [[1, 1]] and game.js(f"shownVoids({x + 1}, {y - 3}, 0, 1)") == []
    foot = game.js("colsOf(hillSheet(1)).foot")
    # south: one hole across both tiles (dark over their seam), two layers high (16 px), not three; shadow in front
    assert px(-1, -3, 15, foot - 4)[:3] == HOLE and px(0, -3, 0, foot - 4)[:3] == HOLE and px(0, -3, 8, foot - 12)[:3] in (HOLE, DEEP)
    assert px(0, -3, 8, foot - 20)[3] == 0 and px(1, -3, 8, foot - 4)[3] == 0
    assert 0 < px(0, -3, 0, foot + 2)[3] < 255
    # east and west: a hole in the side's wall (outside the tile's top), its shadow beyond; nothing on the hill's top
    inset, side = game.js("colsOf(hillSheet(4)).inset"), 4 * 2      # (the side wall shows two layers at the most)
    assert px(3, -6, 16 - inset + side - 2, 8)[:3] == HOLE and px(-3, -6, inset - side + 1, 8)[:3] == HOLE
    assert 0 < px(3, -6, 16 - inset + side + 3, 8)[3] < 255 and px(3, -6, 8, 8 - 32)[3] == 0
    # north: no hole, only a shadow on the ground from under the hill's edge
    assert 0 < px(0, -9, 8, -32 - 4)[3] < 255 and px(0, -9, 8, 8)[3] == 0


SEEN = "xray.a > .95 && !xray.job && xray.pic && xray.pic.any > 0"
# a px of the picture seen through what hides you: of tile (x, y) as drawn at height lv, (ax, ay) art px from its
# corner -> [seen, r, g, b]
PIC = """([x, y, lv, ax, ay]) => { const P = xray.pic, X = x * 16 + ax - P.x, Y = y * 16 - shOf(lv) + ay - P.y;
  if (X < 0 || Y < 0 || X >= P.w || Y >= P.h) return [0, 0, 0, 0];
  return [P.seen[Y * P.w + X], ...Array.from(P.over.getContext('2d').getImageData(X, Y, 1, 1).data).slice(0, 3)]; }"""


def test_in_a_cave_you_are_seen_through_the_hill_as_anywhere_you_are_hidden(game):
    """A cave had a view of its own: opened for good while you were in it, its floor flat in the hill's top, shadowed
    along its edges. "everything should have the same view ! ... an unique 'player is hided, xray on' view": in a cave
    you are hidden by the hill over you, and seen through it as behind a hill or down a hole (xray.js): the room, its
    wall behind it up to the top of the hill (its own back wall; over that the roof, cut through), the hill round it
    whole. Its mouth is not drawn on a hill that is seen through."""
    game.js("setOpt('above', 'cut')")
    game.clear_area(9)
    x, y = game.pos()
    hill(game, -3, -8, 7, 7, {(i, j): 2 for i in (-1, 0, 1) for j in range(-6, -1)})      # a room 3 wide, open to the south
    assert game.js(f"shownVoids({x}, {y - 2}, 0, 1)") == [[1, 2]] and game.js("xray.a") < .01   # outside: the hill, its mouth in it
    assert game.js(f"[standAt({x}, {y - 4}), hiddenAt({x}, {y - 4})]") == [4, True]
    game.hold(["w"], 800)
    game.wait(SEEN, 20000); game.sleep(400)
    assert game.server()["in_cave"] and game.js("xray.pic.floor.size") == 15
    assert game.js(f"[standAt({x}, {y - 4}), standAt({x - 1}, {y - 4}), standAt({x - 2}, {y - 4}), hiddenAt({x}, {y - 6})]") == [0, 0, 4, False]
    assert game.js(f"shownVoids({x}, {y - 2}, 0, 1)") == []
    px = lambda *a: game.js(PIC, list(a))
    floor, back, roof = px(x, y - 5, 0, 8, 8), px(x, y - 6, 0, 8, -4), px(x, y - 6, 0, 8, -20)
    assert floor[0] and floor[2] > floor[1]                                           # its floor: the meadow's
    assert back[0] and back[1] > back[2] and roof[0]                                  # its back wall, earth; over it the roof, cut through
    lit = lambda *a: game.js("""([x, y, lv, ax, ay]) => { frame(performance.now()); const P = xray.pic, f = (y * 16 - shOf(lv) + ay - P.y) * P.w + x * 16 + ax - P.x;
      return [P.solid[f], +(P.img.data[f * 4 + 3] / 255).toFixed(3)]; }""", list(a))
    assert lit(x, y - 6, 0, 8, -4)[0] == 0 and lit(x, y - 6, 0, 8, -20)[0] == 1       # (earth that was cut through: the light says how dark, cavelight.js)
    assert not px(x - 2, y - 4, 4, 8, 8)[0]                                           # the hill beside it: as it is (it was drawn again with an edge toward the room: "it goes under the background tiles")
    ink = game.js("CUT.ink")                                # the cut's edge (xraycut.js): a line along the room's side,
    assert px(x - 1, y - 3, 0, 0, 8)[1:] == ink and px(x - 1, y - 5, 0, 0, 8)[1:] == ink and px(x, y - 2, 0, 8, 15)[1:] != ink   # none across its way out
    line = lambda *a: game.js("""([x, y, lv, ax, ay]) => { const P = xray.pic, X = x * 16 + ax - P.x, Y = y * 16 - shOf(lv) + ay - P.y;
      return xrayEdges(P).getContext('2d').getImageData(X, Y, 1, 1).data[3] > 0; }""", list(a))
    # the outline (the usual view): along its side and the top of its wall; not across its way out, where its floor
    # goes on level with the meadow ("the line shouldn't show up at intersections with same level")
    assert line(x - 1, y - 4, 0, 0, 8) and line(x, y - 6, 4, 8, 0) and not line(x, y - 2, 0, 8, 15) and not line(x, y - 2, 0, 8, 14)


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


def test_a_cave_wider_than_the_circle_is_seen_whole_its_mouth_in_daylight_however_far(game):
    """The picture was as wide as the circle (nine tiles) unless the ground was dug: a cave eighteen tiles wide showed
    nine of them, a square hole in its hill. And daylight came in only where the ground outside the mouth was near
    you: a mouth eleven tiles off was dark."""
    game.js("setOpt('above', 'cut')")
    game.clear_area(14)
    x, y = game.pos()
    game.stamp(-10, -9, ["." * 20] * 7, levels=["4" * 20] * 7)                        # a hill, a cave 18 x 5 in it,
    game.stamp(-9, -8, ["." * 18] * 5, levels=["0" * 18] * 5, roofs=["4" * 18] * 5, heads=["2" * 18] * 5)
    game.stamp(-9, -3, ["."], levels=["0"], roofs=["4"], heads=["2"])                 # its mouth south, at its west end
    game.rpc("dev_teleport", x=x + 2, y=y - 6, z=0)                                   # eleven tiles east of its mouth
    game.wait(f"myAt && myAt.x === {x + 2} && myAt.y === {y - 6}", 8000)
    game.wait("dirtyTiles.length === 0", 20000); game.wait(SEEN, 20000); game.sleep(400)
    assert game.js("xray.pic.floor.size") == 91
    assert game.js(PIC, [x - 9, y - 6, 0, 8, 8])[0] and game.js(PIC, [x + 8, y - 6, 0, 8, 8])[0]   # its two ends
    dark = f"""([X, Y]) => {{ const P = xray.pic, f = (Y * 16 + 8 - P.y) * P.w + X * 16 + 8 - P.x; return [!!P.deep[f], +(P.img.data[f * 4 + 3] / 255).toFixed(2)]; }}"""
    mouth, deep, me = (game.js(dark, [X, Y]) for X, Y in ((x - 9, y - 3), (x - 3, y - 6), (x + 2, y - 6)))
    assert mouth[0] and deep[0] and me[0] and mouth[1] < .1 and me[1] < .2 and deep[1] > .4, (mouth, deep, me)


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


def test_an_opening_higher_up_a_south_wall_still_casts_its_shadow(game):
    """A cave whose floor is a layer above the ground in front: its opening is up the wall, its shadow under it."""
    game.clear_area(9)
    x, y = game.pos()
    game.stamp(-2, -6, ["....."] * 4, levels=["44444", "44144", "44144", "44144"], roofs=["00000", "00300", "00300", "00300"])
    drawn(game)
    px = lambda ax, ay: game.js(PX, [x, y - 3, ax, ay])
    assert game.js(f"shownVoids({x}, {y - 3}, 0, 1)") == [[2, 3]]
    foot = game.js("colsOf(hillSheet(2)).foot") - 8          # the hole's foot: a layer up the wall
    assert px(8, foot - 4)[:3] == HOLE and 0 < px(8, foot + 2)[3] < 255 and px(8, foot + 12)[3] == 0
