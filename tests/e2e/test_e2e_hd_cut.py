"""A trench dug through a hill of steps (the owner's screenshot, 2026-11-23: an AI player dug one tile wide, north to
south, through several levels: "textures are a mess"). A cut is air in the land and nothing else: its floor and its
walls are drawn by the rules every face has (vox_style_land.js faces, voxpaint.js), whatever made the shape and
wherever you stand. It was a cut's own rules: its floor lit warm yellow while you stood in it, a step darker with its
walls' feet shaded px by px, its walls darkened with depth: a box per level, not one cut through one hill.
And the land's paint has one art px: a front's rows are the pack's own rows, one each (they were each laid twice: the
stone at the back of the screen read as px twice as tall as the rest)."""

import os

from test_e2e_hd_sun import hd

SHOT = os.environ.get("DIGTEX_SHOT")      # (a folder: the scene is saved there for a person to look at)

# terraces going down south: 8 levels at the back (stone), 2 a step, the meadow in front
TERR = [8] * 3 + [6] * 3 + [4] * 3 + [2] * 3
# the mean colour of each screen column across the middle of a tile's top (its north and south quarter left out, a tenth at each side: the wall beside it): [[r, g, b]...]
COLS = """([x, y, z]) => { const k = devicePixelRatio, a = HdLook.screenOf(x + .1, y + .3, z), b = HdLook.screenOf(x + .9, y + .7, z);
  const x0 = Math.round(a[0] * k), x1 = Math.round(b[0] * k), y0 = Math.round(a[1] * k), y1 = Math.round(b[1] * k), d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data, o = [];
  for (let i = 0; i < x1 - x0; i++) { const s = [0, 0, 0]; for (let j = 0; j < y1 - y0; j++) for (let c = 0; c < 3; c++) s[c] += d[(j * (x1 - x0) + i) * 4 + c]; o.push(s.map((v) => v / (y1 - y0))); } return o; }"""
# the mean colour of a cell's south face, cell z of (x, y) (the face from z - 1 up to z on the tile's south edge), a fifth in from its edges
FACE = """([x, y, z]) => { const k = devicePixelRatio, a = HdLook.screenOf(x + .2, y + 1, z - .2), b = HdLook.screenOf(x + .8, y + 1, z - .8);
  const d = HdLook.read(Math.round(a[0] * k), Math.round(a[1] * k), Math.round((b[0] - a[0]) * k), Math.round((b[1] - a[1]) * k)).data, s = [0, 0, 0];
  for (let i = 0; i < d.length; i += 4) for (let c = 0; c < 3; c++) s[c] += d[i + c]; return s.map((v) => v / (d.length / 4)); }"""
# of each level's front paint (earth 1 to 4, stone 5 to 8, four variants): how many of its rows are the row over it again, whole
TWICE = """() => { const px = new Uint32Array(256); let n = 0; for (let lv = 1; lv <= 8; lv++) for (let v = 0; v < 4; v++) { VoxPaint.front(lv, v, px, 0, 16, 0);
  for (let j = 1; j < 16; j++) { let same = true; for (let i = 0; i < 16; i++) if (px[j * 16 + i] !== px[(j - 1) * 16 + i]) { same = false; break; } if (same) n++; } } return n; }"""
lum = lambda c: c[0] + c[1] + c[2]


def hill(g):
    """The hill north of you, 13 tiles wide, and a trench one tile wide 3 east of you, a level under each terrace's top
    (as dug: the column's top a cell lower, nothing else). -> (x, y) where you stand"""
    x, y = g.pos()
    g.stamp(-6, -14, ["." * 13] * 14, levels=[str(v) * 13 for v in TERR] + ["0" * 13] * 2)
    for j, v in enumerate(TERR):
        g.rpc("dev_col", tiles=[[x + 3, y - 14 + j]], col=[v - 1])
    g.rest()
    return x, y


def go(g, x, y, z, shot=None):
    g.rpc("dev_teleport", x=x, y=y, z=z)
    g.arrive()
    g.rest()
    if SHOT and shot:
        g.page.screenshot(path=os.path.join(SHOT, shot + ".png"))


def even(cols):
    """a top's columns: the darkest of its quarter at each side against its middle half (1: as light at its sides as in its middle)"""
    n = len(cols)
    mid = sum(lum(c) for c in cols[n // 4:3 * n // 4]) / (n - 2 * (n // 4))
    return min(lum(c) for c in cols[:n // 4] + cols[3 * n // 4:]) / mid


def test_a_trench_dug_through_a_hill_of_steps_is_drawn_as_the_hill_is(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    g.js("setOpt('shadows', 0)")                                                  # (the walls' cast shadow on the floor is the sun's, the same for any land: not what is read here)
    x, y = hill(g)
    assert g.js(TWICE) == 0                                                       # one art px: no row of a front's paint laid twice
    # (the floor read: from the meadow the one at the terrace's front (the ones behind it its own wall hides from this eye); standing in
    # the cut, the one two tiles north of you (your own sprite is over the next one))
    for where, at, fy in (("outside", (x, y, 0), y - 3), ("in it", (x + 3, y - 3, 1), y - 5)):
        go(g, *at, shot="cut_" + where.replace(" ", "_"))
        cut, wide = g.js(COLS, [x + 3, fy, 1]), g.js(COLS, [x + 1, fy, 2])
        mc, mw = [sum(c[i] for c in cut) / len(cut) for i in range(3)], [sum(c[i] for c in wide) / len(wide) for i in range(3)]
        # the cut's floor: the same grass as the terrace beside it, one tone across (its corners' shade is the land's own,
        # by the walls over them, the same at its four corners): no foot of a wall shaded into it, no warm light of its own
        assert even(cut) > .93, (where, even(cut), cut)
        assert abs(mc[1] / mc[0] - mw[1] / mw[0]) < .08 and abs(mc[2] / mc[0] - mw[2] / mw[0]) < .08, (where, mc, mw)
        assert .6 < lum(mc) / lum(mw) < 1.02, (where, mc, mw)
        # its front where it steps down onto the meadow: the terrace's own front beside it, the same level, the same way
        f, t = g.js(FACE, [x + 3, y - 3, 1]), g.js(FACE, [x + 1, y - 3, 1])
        assert all(abs(a - b) < .08 * b for a, b in zip(f, t)), (where, f, t)
    assert not g.errors


def test_a_cut_does_not_change_the_stone_of_the_tiles_beside_it(browser, server):
    """A thin terrace of stone, five tiles by three, six high; a cut through its middle down to level 2. The tiles
    beside the cut are untouched: their fronts are the same px after as before. (Stone was a mass: with the cut no
    3 x 3 of high tiles was left, and the whole terrace turned earth: lighter boxes beside the cut.)"""
    g = hd(browser, server)
    g.hour(.3, still=True)
    g.js("setOpt('shadows', 0)")
    x, y = g.pos()
    g.stamp(-2, -6, ["." * 5] * 3, levels=["6" * 5] * 3)
    g.rest()
    read = lambda: [g.js(FACE, [x + dx, y - 4, z]) for dx in (-2, -1, 1, 2) for z in (6, 3)]
    was = read()
    assert all(max(c) - min(c) < 30 for c in was), was                            # (grey: stone to its foot)
    g.rpc("dev_col", tiles=[[x, y - 6 + j] for j in range(3)], col=[2])
    g.rest()
    if SHOT:
        g.page.screenshot(path=os.path.join(SHOT, "thin_terrace_cut.png"))
    assert read() == was
    assert not g.errors
