"""Three things a reviewer's pictures showed wrong, each read off the picture:
a run of land one tile wide is ONE top (voxpaint.js quarters: it was a cap a tile, dark dashes between them);
a front in the shadow of land beside it has one tone, the shadow lying on the ground at its foot (vox_light.js lit:
a front takes no shadow; a column was all dark or all lit by the shadow at its foot, then wedges, then rectangles);
the mouse on the wall of a pit shows that wall's block down to its foot, the pointer in the box (mouse.js, mark.js:
the box was the far rim's top, a tile and a half over the pointer)."""
from test_e2e_mark import AT, mode

# the colours [r, g, b] at points of the land [x, y, ax, ay, lv] (tile, art px into it, levels up), all of one frame
PX = """(pts) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const S = TS(), [ox, oy] = screenOrigin(S);
  ok(pts.map(([x, y, ax, ay, lv]) => { const d = ctx.getImageData(Math.round((ox + x * S + ax * zoom) * DPR), Math.round((oy + (y + ay / 16) * S - shOf(lv) * zoom) * DPR), 1, 1).data; return [d[0], d[1], d[2]]; })); })))"""
lum = lambda c: .3 * c[0] + .59 * c[1] + .11 * c[2]


def ready(game, phase):
    game.js("(() => { setOpt('shader', 'off'); setOpt('depth', true); return 1; })()")
    mode(game, "off")
    game.hour(phase)                                             # (on the page, and the land drawn by it: the hour was asked for and 0.9 s slept)


def test_a_wall_one_tile_wide_has_one_top_from_end_to_end(game):
    """Four tiles of land three high in a row, west to east, and four north to south: along the flat middle of the
    top, from the first tile's middle to the last one's, no px is darker than the flat green (no rim, no dash at a joint)."""
    game.clear_area(8)
    x, y = game.pos()
    # (where no tile of the run has one of the grass's tufts on it, which the meadow puts on three tiles in ten by the
    # tile's own place, tiles.js drawBlobLayer: a tuft's darker green in the rows read was "a dash", where you woke
    # deciding: four runs in six once the players woke elsewhere. README.md rule 3)
    bare = "([x, y, dx, dy]) => [0, 1, 2, 3].every((k) => hash(x + k * dx, y + k * dy, 3) >= .3)"
    ex, ey = next((i, j) for j in (-4, -5, -3, -2, -1) for i in (2, 1, 3, 4) if game.js(bare, [x + i, y + j, 1, 0]))      # (twenty places and more: one is bare, but for one run in some hundreds)
    sx, sy = next((i, j) for i in (-4, -5, -6, -3, -7, -8) for j in (-3, -4, -2, -1) if game.js(bare, [x + i, y + j, 0, 1]))
    game.stamp(ex, ey, ["...."], levels=["3333"]); game.stamp(sx, sy, ["."] * 4, levels=["3"] * 4)
    ready(game, .375)
    ew = game.js(PX, [[x + ex, y + ey, 8 + i, j + .5, 3] for j in (5, 6, 7) for i in range(49)])
    ns = game.js(PX, [[x + sx, y + sy, i + .5, 8 + j, 3] for i in (6, 8, 9) for j in range(49)])
    for name, row in (("west-east", ew), ("north-south", ns)):
        flat = sorted(lum(c) for c in row)[len(row) // 2]
        dark = [i for i, c in enumerate(row) if lum(c) < flat - 10]
        assert not dark, (name, flat, dark, [row[i] for i in dark[:6]])
    game.js("(() => { Curve.force = null; return 1; })()")


def test_a_front_in_the_shadow_of_land_beside_it_is_one_tone_and_the_ground_at_its_foot_takes_the_shadow(game):
    """A wall four high facing you, a pillar nine high four tiles west of it in the row at its foot, the sun low in the
    west: the pillar's shadow lies along the wall's foot, on the ground. The front has one tone, column by column and
    level by level (the sun is never south: a front takes no shadow. A shadow that climbed it was a column all dark
    beside a column all lit, then a row of wedges, then lighter rectangles: vox_light.js)."""
    game.clear_area(9)
    x, y = game.pos()
    game.stamp(0, -4, ["...."], levels=["4444"]); game.stamp(-4, -3, ["."], levels=["9"])
    ready(game, .68)
    assert game.js("Sun.given().dir[0]") > .5                    # (the sun is in the west: shadows fall east)
    rows = [5, 13, 21, 29]                                       # px up the front: one in each level, clear of its seam
    got = game.js(PX, [[x + c, y - 4, ax, 16, (h + .5) / 8] for c in (0, 1, 3) for h in rows for ax in (5, 7, 9, 11)])
    tones = [sorted(lum(c) for c in got[k * 4:k * 4 + 4])[1] for k in range(12)]      # each column's four levels (the body's tone: not a fleck of the rock's own): near the pillar, next, far
    assert max(tones) - min(tones) < 1, tones                    # one face
    foot = game.js(PX, [[x + c, y - 3, 8, 8, 0] for c in (0, 3)] + [[x + 8, y - 3, 8, 8, 0]])
    assert min(lum(foot[0]), lum(foot[1])) < lum(foot[2]) - 6, foot      # the ground at its foot, where a shadow lies along it: dark


def test_the_mouse_on_a_pits_wall_shows_one_box_the_cell_acted_on_and_a_tick_where_it_points(game):
    """A pit three deep; the mouse on its north wall's face, with nothing in hand and with earth: ONE box, the cell the
    click acts on (the rim block's top; with earth the cell over it), and a tick on the wall's face at the cell the
    pointer is on. (A second box on the face was "two separate boxes: not one cell under the pointer".)"""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(-5, 0, [".."] * 2, levels=["cc"] * 2)
    ready(game, .3)
    game.give(dirt=3)
    px, py = game.js(AT, [x - 5, y - 1, 8, 16, -1.4])            # (on the face of the rim's block north of the pit, a level and a half down it)
    for item, cell in ((None, [x - 5, y - 1, 0, 0]), ("dirt", [x - 5, y - 1, 0, 1])):
        game.hold_item(item)
        game.page.mouse.move(px - 9, py - 7); game.page.mouse.move(px - 2, py - 1); game.page.mouse.move(px, py)
        game.wait("Marks.list.length >= 1 && Marks.list.every((k) => ['x', 'y', 'z0', 'z1'].every((f) => Math.abs(k[f] - k.to[f]) < .01))", timeout=4000)
        marks = game.js("Marks.list.map((k) => [k.to.x, k.to.y, k.to.z0, k.to.z1])")
        assert marks == [cell], (item, marks)
        tick = game.js("Marks.list[0].to.tick"); y0 = game.js(AT, [x - 5, y - 1, 8, 16, tick])[1]; y1 = game.js(AT, [x - 5, y - 1, 8, 16, tick - 1])[1]
        assert y0 <= py < y1, (item, tick, py, y0, y1)           # the tick's cell of the face is the one the pointer is on
    game.page.mouse.move(5, 5); game.js("(() => { Curve.force = null; return 1; })()")
