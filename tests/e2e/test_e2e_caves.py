"""Caves as drawn: openings on each side of a hill, as wide and as high as the empty cells; the cave you're in seen
through the hill, shadowed along its edges, with its way out to the north; and being hidden behind a hill."""

# a pixel [r, g, b, a] of the caves as drawn: tile (x, y), art px (ax, ay) from the tile's corner at sea level (from
# whichever block's overlay has something there: an opening is drawn from its first tile's block)
PX = """([x, y, ax, ay]) => { for (const b of blocks.values()) { if (!b.caveOv) continue;
    const X = OV_M + (x - b.bx * B) * 16 + ax, Y = OV_M + (y - b.by * B) * 16 + ay;
    if (X < 0 || Y < 0 || X >= b.caveOv.width || Y >= b.caveOv.height) continue;
    const d = Array.from(b.caveOv.getContext('2d').getImageData(X, Y, 1, 1).data); if (d[3]) return d; }
  return [0, 0, 0, 0]; }"""
HOLE, DEEP = [0x2a, 0x1d, 0x28], [0x1d, 0x14, 0x1c]           # the hole, and its darker depth


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


def test_inside_the_cave_shows_through_the_hill_shadowed_along_its_edges(game):
    game.clear_area(9)
    x, y = game.pos()
    hill(game, -3, -8, 7, 7, {(i, j): 2 for i in (-1, 0, 1) for j in range(-6, -1)})      # a room 3 wide, open to the south
    px = lambda tx, ty, ax, ay: game.js(PX, [x + tx, y + ty, ax, ay])
    game.hold(["w"], 800)
    drawn(game)
    assert game.server()["in_cave"] and game.js("caveOpen") and game.js("openCave.size") == 15
    mid, west, east = px(0, -4, 8, 8), px(-1, -4, 0, 8), px(1, -4, 15, 8)
    assert mid[3] == 255 and west[3] == 255 and east[3] == 255                       # its floor, right to the tiles' edges
    assert sum(west[:3]) < sum(mid[:3]) - 60 and sum(east[:3]) < sum(mid[:3]) - 60    # darker along the rock
    assert px(-1, -4, 15, 8)[:3] == px(0, -4, 8, 8)[:3] or sum(px(-1, -4, 15, 8)[:3]) > sum(west[:3])   # not between its own tiles
    assert px(-2, -4, 8, 8)[3] == 0                                                   # the hill round it: untouched
    assert px(0, -6, 8, -4)[3] == 255                                                 # the wall at its back


def test_a_way_out_to_the_north_shows_under_the_hills_border_which_stays(game):
    game.clear_area(9)
    x, y = game.pos()
    hill(game, -3, 2, 7, 6, {(0, j): 2 for j in range(2, 6)})                         # a hill south of you, a tunnel in from its north side
    px = lambda tx, ty, ax, ay: game.js(PX, [x + tx, y + ty, ax, ay])
    game.js("window.seen = []; (function f() { const p = ents.get('agent' + myId); window.seen.push(liftOf(p)); requestAnimationFrame(f); })()")
    game.hold(["s"], 700)
    drawn(game)
    assert game.server()["in_cave"] and game.js("caveOpen") and game.js("Math.max(...window.seen)") < .5   # (never drawn up on the hill)
    assert px(0, 2, 8, -4)[3] == 0 or px(0, 2, 8, 8)[3] == 255                        # no wall across the way out
    assert px(0, 1, 8, 8)[3] == 255                                                   # the ground it opens onto: shown
    north = game.js("colsOf(hillSheet(4)).north")
    edge = px(0, 2, 8, -32 + north)                                                   # the hill's own border, over it
    assert edge[3] == 255 and edge[:3] == game.js(f"""(() => {{ const s = hillSheet(4), [cx, cy] = blobCell(maskOf({x}, {y + 2}, (c, g, tx, ty) => topAt(tx, ty) >= 4));
      const k = document.createElement('canvas'); k.width = k.height = 16; const q = k.getContext('2d'); q.drawImage(s, cx * 16, cy * 16, 16, 16, 0, 0, 16, 16);
      return Array.from(q.getImageData(8, {north}, 1, 1).data).slice(0, 3); }})()""")


def test_standing_behind_a_hill_it_hides_you(game):
    game.clear_area(9)
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
