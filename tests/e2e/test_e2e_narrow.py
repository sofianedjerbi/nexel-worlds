"""Three things a reviewer's pictures showed wrong, each read off the picture:
a run of land one tile wide is ONE top (voxpaint.js quarters: it was a cap a tile, dark dashes between them);
a front in the shadow of land beside it is dark up to where the sun's line clears that land, the edge climbing the
wall from column to column (vox_light.js lit: a column was all dark or all lit by the shadow at its foot);
the mouse on the wall of a pit shows that wall's block down to its foot, the pointer in the box (mouse.js, mark.js:
the box was the far rim's top, a tile and a half over the pointer)."""
from test_e2e_mark import AT, mode

# the colours [r, g, b] at points of the land [x, y, ax, ay, lv] (tile, art px into it, levels up), all of one frame
PX = """(pts) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const S = TS(), [ox, oy] = screenOrigin(S);
  ok(pts.map(([x, y, ax, ay, lv]) => { const d = ctx.getImageData(Math.round((ox + x * S + ax * zoom) * DPR), Math.round((oy + (y + ay / 16) * S - shOf(lv) * zoom) * DPR), 1, 1).data; return [d[0], d[1], d[2]]; })); })))"""
lum = lambda c: .3 * c[0] + .59 * c[1] + .11 * c[2]


def ready(game, phase):
    game.js("(() => { setOpt('shader', 'off'); setOpt('depth', true); return 1; })()")
    game.rpc("dev_time", phase=phase)
    mode(game, "off")
    game.wait("dirtyTiles.length === 0", timeout=20000); game.sleep(900)


def test_a_wall_one_tile_wide_has_one_top_from_end_to_end(game):
    """Four tiles of land three high in a row, west to east, and four north to south: along the flat middle of the
    top, from the first tile's middle to the last one's, no px is darker than the flat green (no rim, no dash at a joint)."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(2, -4, ["...."], levels=["3333"]); game.stamp(-4, -3, ["."] * 4, levels=["3"] * 4)
    ready(game, .375)
    ew = game.js(PX, [[x + 2, y - 4, 8 + i, j + .5, 3] for j in (5, 6, 7) for i in range(49)])
    ns = game.js(PX, [[x - 4, y - 3, i + .5, 8 + j, 3] for i in (6, 8, 9) for j in range(49)])
    for name, row in (("west-east", ew), ("north-south", ns)):
        flat = sorted(lum(c) for c in row)[len(row) // 2]
        dark = [i for i, c in enumerate(row) if lum(c) < flat - 10]
        assert not dark, (name, flat, dark, [row[i] for i in dark[:6]])
    game.js("(() => { Curve.force = null; return 1; })()")


def test_a_shadow_climbs_a_front_to_one_edge_across_its_columns(game):
    """A wall four high facing you, a pillar nine high four tiles west of it in the row at its foot, the sun low in the
    west: the pillar's shadow lies along the wall's foot. In each of the wall's first two columns the front is dark low
    and lit high (not a column all dark, a column all lit), and the edge is higher in the column nearer the pillar."""
    game.clear_area(9)
    x, y = game.pos()
    game.stamp(0, -4, ["...."], levels=["4444"]); game.stamp(-4, -3, ["."], levels=["9"])
    ready(game, .68)
    assert game.js("Sun.given().dir[0]") > .5                    # (the sun is in the west: shadows fall east)
    rows = [5, 13, 21, 29]                                       # px up the front: one in each level, clear of its seam
    got = game.js(PX, [[x + c, y - 4, ax, 16, (h + .5) / 8] for c in (0, 1, 3) for h in rows for ax in (5, 7, 9, 11)])
    col = lambda n: [sum(lum(c) for c in got[n * 16 + k * 4:n * 16 + k * 4 + 4]) / 4 for k in range(4)]
    near, next_, far = col(0), col(1), col(2)
    lit = far[3]                                                 # (the far column's top level: the shadow is not that high there)
    darks = [sum(1 for v in c if v < lit - 6) for c in (near, next_)]
    assert 1 <= darks[1] <= darks[0] <= 3, (darks, near, next_, far)      # each: dark at its foot, lit at its top; higher nearer the pillar
    assert near[0] < lit - 6 and near[3] > lit - 6 and next_[0] < lit - 6 and next_[3] > lit - 6, (near, next_, far)
    game.rpc("dev_time", phase=.3); game.js("(() => { Curve.force = null; return 1; })()")


def test_the_mouse_on_a_pits_wall_shows_a_box_the_pointer_is_in(game):
    """A pit three deep; the mouse on its north wall's face, with nothing in hand and with earth: the box is that
    wall's block, from its top (earth: the cell that would be put on it) down to the pit's floor: the pointer is in it."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(-5, 0, [".."] * 2, levels=["cc"] * 2)
    ready(game, .3)
    game.give(dirt=3)
    px, py = game.js(AT, [x - 5, y - 1, 8, 16, -1.4])            # (on the face of the rim's block north of the pit, a level and a half down it)
    for item, top in ((None, 0), ("dirt", 1)):
        game.hold_item(item)
        game.page.mouse.move(px - 9, py - 7); game.page.mouse.move(px - 2, py - 1); game.page.mouse.move(px, py)
        game.wait("Marks.list.length === 1 && ['x', 'y', 'z0', 'z1'].every((f) => Math.abs(Marks.list[0][f] - Marks.list[0].to[f]) < .01)", timeout=4000)
        m = game.js("(() => { const m = Marks.list[0].to; return [m.x, m.y, m.z0, m.z1, !!m.flat]; })()")
        assert m == [x - 5, y - 1, -3, top, False], (item, m)
        x0, y0 = game.js(AT, [m[0], m[1], 0, 0, m[3]]); x1, y1 = game.js(AT, [m[0], m[1], 16, 16, m[2]])
        assert x0 <= px < x1 and y0 <= py < y1, (item, (px, py), (x0, y0, x1, y1))      # the pointer is in the box's picture
    game.page.mouse.move(5, 5); game.js("(() => { Curve.force = null; return 1; })()")
