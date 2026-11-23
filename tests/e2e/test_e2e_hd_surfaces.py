"""Every surface of the land is painted by one rule (tiles.js drawTile, drawBlobLayer, MARKS; the owner: "same for textures.
many many many little bugs"): a ground's cell by which tiles round it are of the same ground, what is laid on it (a path, a
field, ash, a floor) the same at any height, nothing left unpainted, one art px. Tilled soil was the pack's patch up on a
hill and furrows on the meadow: two fields by their height."""

import os

from test_e2e_hd_sun import hd

SHOT = os.environ.get("DIGTEX_SHOT")      # (a folder: the scenes are saved there for a person to look at)

# the land north of you, 19 wide: a hill (level 2) with a path and a field on it, the path and a field on the meadow too, ash,
# bare dirt, a floor in a house of wooden walls, water with a bridge on the path's line
ROWS = ["." * 5 + "_" + "..." + "oouu" + "......"] * 4 + [
    "....._..." + "...." + "......",
    "....._..." + "oouu" + "..',,,",
    "....._..." + "oouu" + ".'',,,",
    "....._..." + "...." + "......",
    "WWWW._..." + "...." + "......",
    "WnnW._..." + "...." + "......",
    "WnnW._..." + "...." + "......",
    "~~~~~:~~~" + "~~~~" + "~~~~~~",
    "~~~~~:~~~" + "~~~~" + "~~~~~~",
]
LEVELS = ["2" * 19] * 4 + ["0" * 19] * 9
# the cells laid on a tile's top past its ground (paths, fields, ash, floors), as the land's painter has them: [sheet, cell]
MARKS = """([x, y, z]) => { Voxels.host.paintTop(x, y, z, new Uint32Array(256), 0, 16); const base = new Set([IMG.soil, IMG.grass]); for (let k = 1; k <= 12; k++) base.add(hillSheet(k));
  const out = []; for (let i = 0; i < LAID.n; i++) { const im = LAID.img[i]; if (!base.has(im)) out.push([Object.keys(IMG).find((k) => IMG[k] === im) || im.width + "x" + im.height, LAID.at[i]]); } return out; }"""
# px of a tile's ground left unpainted (not solid), its paint asked for over a marker colour (the ground and what is laid on it, drawTile:
# not the land's rim over it, whose see-through px are its shape, the wall behind them the land's)
BARE = """([x, y]) => { const px = new Uint32Array(256).fill(0xffff00ff); drawTile(x, y, {px, o: 0, w: 16}); let n = 0; for (const v of px) if (v >>> 24 < 255 || v === 0xffff00ff) n++; return n; }"""
# of the picture's rows over the scene: the lengths of runs of one colour that are not a whole number of art px (device px)
RUNS = """([y0, y1]) => { const k = devicePixelRatio, u = artPx() * k, w = Math.floor(innerWidth * k), d = HdLook.read(0, Math.round(y0 * k), w, Math.round((y1 - y0) * k)).data, h = d.length / 4 / w; let bad = 0, all = 0;
  for (let j = 0; j < h; j += 5) { let n = 1; for (let i = 1; i <= w; i++) { const a = (j * w + i) * 4, b = a - 4; if (i < w && d[a] === d[b] && d[a + 1] === d[b + 1] && d[a + 2] === d[b + 2]) { n++; continue; } if (i < w && i - n > 0) { all++; if (n % u) bad++; } n = 1; } } return [bad, all]; }"""


def scene(g):
    x, y = g.pos()
    g.stamp(-9, -14, ROWS, levels=LEVELS)
    return x, y


def test_every_surface_is_one_rule_at_any_height_painted_whole_at_one_art_px(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    x, y = scene(g)
    x0, y0 = x - 9, y - 14
    # what is laid on the ground is the same cells on the hill (level 2) as on the meadow: the path, dry and wet fields
    for (hx, hy), (mx, my) in (((5, 1), (5, 5)), ((9, 1), (9, 5)), ((11, 2), (11, 6))):
        hill, meadow = g.js(MARKS, [x0 + hx, y0 + hy, 2]), g.js(MARKS, [x0 + mx, y0 + my, 0])
        assert hill and [m[0] for m in hill] == [m[0] for m in meadow], (hx, hill, meadow)
    # nothing of a ground left unpainted, on every tile of land of the scene with land all round it: every seam of a hill's, a path's,
    # a field's, ash's, dirt's, a floor's ground with another's (a bank's px over the water are the water's: the land's rim there)
    land = lambda i, j: not (0 <= j < len(ROWS) and 0 <= i < 19) or ROWS[j][i] not in "~:"
    bare = {(i, j): g.js(BARE, [x0 + i, y0 + j]) for j, row in enumerate(ROWS) for i, ch in enumerate(row)
            if ch not in "~:W" and all(land(i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1))}
    assert not any(bare.values()), {k: v for k, v in bare.items() if v}
    assert g.js("HdLook.raw()") == 0
    # one art px on the screen: every run of one colour across the land is a whole number of art px
    top, bot = g.js(f"HdLook.screenOf({x0}, {y0}, 2)")[1], g.js(f"HdLook.screenOf({x0}, {y}, 0)")[1]
    bad, n = g.js(RUNS, [max(0, top), bot])
    assert n > 500 and bad == 0, (bad, n)
    if SHOT:
        for name, at in (("meadow", (x, y, 0)), ("path_hill", (x0 + 5, y0 + 6, 0)), ("bridge", (x0 + 5, y0 + 10, 0)),
                         ("field", (x0 + 10, y0 + 8, 0)), ("house", (x0 + 4, y0 + 9, 0))):
            g.rpc("dev_teleport", x=at[0], y=at[1], z=at[2])
            g.arrive()
            g.rest()
            g.page.screenshot(path=os.path.join(SHOT, "surf_" + name + ".png"))
    assert not g.errors
