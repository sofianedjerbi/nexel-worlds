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


# the land's picture, kept (window.__p[name]), from under the sky's line down (the sky's clouds drift: not the land's);
# and how many of its px are not the kept one's
KEEP = """(n) => { (window.__p = window.__p || {})[n] = HdLook.read(0, Math.round(cv.height * .42), cv.width, Math.round(cv.height * .58)).data; return 1; }"""
OFF = """(n) => { const a = window.__p[n], b = HdLook.read(0, Math.round(cv.height * .42), cv.width, Math.round(cv.height * .58)).data; let k = 0; for (let i = 0; i < a.length; i += 4) if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2]) k++; return k; }"""
# blocks of the land taken from the page and kept from being asked for again; the land made from none without them
DROP = """(ks) => { for (const k of ks) { blocks.delete(k); requested.set(k, 1e15); } HdLook.forget(); return 1; }"""


def test_the_land_is_the_same_px_whatever_order_its_blocks_came_in(browser, server):
    """A top's paint and a face's look are its column and the columns beside it, nothing further and nothing of when:
    the land round a corner of four blocks, a stone plateau across it, is made with three of them not come, then they
    come (asked of the server, the game's own way in) in one order, then in the other: each time the picture is the
    first one's, px for px. (Stone was decided by the land five tiles off: a paint made before that land had come was
    kept: earth for stone until the tile changed.)"""
    g = hd(browser, server)
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer", "shadows"):
        g.js(f"setOpt('{o}', 0)")
    x, y = g.pos()
    X, Y = round(x / 32) * 32, round(y / 32) * 32                                 # the nearest corner of four blocks
    g.rpc("dev_teleport", x=X - 3, y=Y + 3, z=0)
    g.arrive()
    g.clear_area(12)
    # stone, level 6, across the corner north of you and down its east side: two tiles of it in the north-west block, the rest in the others
    g.stamp(1, -11, ["." * 14] * 12, levels=["6" * 14] * 8 + ["0" * 9 + "6" * 5] * 4)
    g.rest()
    g.js("(() => { HdLook.landOnly = true; return 1; })()")                       # (the land alone: nothing that stands or walks)
    g.rest()
    g.js(KEEP, "all")
    if SHOT:
        g.page.screenshot(path=os.path.join(SHOT, "order_0.png"))
    bx, by = X // 32, Y // 32

    def made():                                                                    # (the land made with what is there: rest() waits for all of the screen's land to have come)
        g.frames(3)
        g.wait("!HdLook.busy && dirtyTiles.length === 0", timeout=15000)
        g.frames(3)
    others = [f"{bx},{by - 1}", f"{bx - 1},{by - 1}", f"{bx},{by}"]              # north-east, north-west, south-east of the corner (yours: south-west)
    for order in (others, others[::-1]):
        g.js(DROP, others)
        made()
        assert g.js(OFF, "all") > 1000                                              # (without them the picture is another)
        for k in order:
            g.js("(k) => { requested.delete(k); return 1; }", k)
            g.wait(f"blocks.get('{k}') && blocks.get('{k}').drawn", timeout=15000)
            made()
        g.rest()
        if SHOT:
            g.page.screenshot(path=os.path.join(SHOT, f"order_{order[0]}.png"))
        assert g.js(OFF, "all") == 0, (order, g.js(OFF, "all"))
    assert not g.errors


# the mean colour of a level's front paint (its four variants): {z: [r, g, b]} for z 2 down to -10; and the tone the land has for a wall that deep
FRONTS = """() => { const o = {}; for (let z = 2; z >= -10; z--) { const s = [0, 0, 0]; for (let v = 0; v < 4; v++) { const px = new Uint32Array(256); VoxPaint.front(z, v, px, 0, 16, 0);
  for (const q of px) { s[0] += q & 255; s[1] += q >>> 8 & 255; s[2] += q >>> 16 & 255; } } o[z] = s.map((c) => c / 1024); } return [o, Object.fromEntries(Object.keys(o).map((z) => [z, deepTone(+z, 'wall')]))]; }"""
# the mean colour of a tile's ground paint (drawTile)
GROUND = """([x, y]) => { const px = new Uint32Array(256), s = [0, 0, 0]; drawTile(x, y, {px, o: 0, w: 16}); for (const q of px) { s[0] += q & 255; s[1] += q >>> 8 & 255; s[2] += q >>> 16 & 255; } return s.map((c) => c / 256); }"""


def test_under_sea_level_the_land_is_the_same_earth_one_tone_darker_a_level(browser, server):
    """One continuous tone by depth on the land's own paints (tiles.js deepTone), not a second family of sheets: a wall at
    sea level is the earth of the levels over it, each level under it that earth times the depth's tone, down to eight;
    a floor the soil times the floor's tone."""
    g = hd(browser, server)
    fronts, tones = g.js(FRONTS)
    near = lambda a, b, k: all(abs(p - q) <= k * q for p, q in zip(a, b))
    assert near(fronts["0"], fronts["1"], .03) and near(fronts["1"], fronts["2"], .03), fronts      # no step at sea level: one earth
    for z in range(-1, -11, -1):
        want = [c * t for c, t in zip(fronts["0"], tones[str(z)])]
        assert near(fronts[str(z)], want, .04), (z, fronts[str(z)], want)
        assert sum(fronts[str(z)]) < sum(fronts[str(z + 1)]) or z < -8, (z, fronts)             # darker each level, to eight down
    x, y = g.pos()
    g.stamp(2, -4, [",,,,"], levels=["0abc"])                                         # bare earth at sea level, then 1, 2, 3 under it
    g.rest()
    base = g.js(GROUND, [x + 2, y - 4])
    for d in (1, 2, 3):
        got, tone = g.js(GROUND, [x + 2 + d, y - 4]), g.js(f"deepTone({-d}, 'floor')")
        assert near(got, [c * t for c, t in zip(base, tone)], .05), (d, got, base, tone)
    g.stamp(2, -4, ["...."], levels=["0000"])
    assert not g.errors


# the lengths of the runs of one colour along the rows of a block's water tint (its canvas, a px an art px), the first and the last of a row left out, that are not whole steps of 4
TINT = """([x, y]) => { const b = tileIdx(x, y)[0], c = b.water.canvas, n = c.width, d = c.getContext('2d').getImageData(0, 0, n, n).data, bad = []; let runs = 0;
  for (let j = 0; j < n; j++) { let k = 1, first = true; for (let i = 1; i < n; i++) { const a = (j * n + i) * 4; if (d[a] === d[a - 4] && d[a + 1] === d[a - 3] && d[a + 2] === d[a - 2] && d[a + 3] === d[a - 1]) { k++; continue; }
    if (!first) { runs++; if (k % 4) bad.push(k); } first = false; k = 1; } } return [runs, bad.slice(0, 8)]; }"""


def test_water_a_bridge_and_a_wall_have_one_paint_each_in_whole_art_px(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    px, py = x + 3 - max(0, (x + 3) % 32 + 8 - 32), y - 6 - max(0, (y - 6) % 32 + 4 - 32)   # (a pond inside one block)
    g.stamp(px - x, py - y, ["~~==))~~", "~~==))~~", "~~:=))~~", "~~==))~~"])       # shallow, deep, abyss: three tints side by side; a bridge tile
    g.rest()
    runs, bad = g.js(TINT, [px, py])
    assert runs > 20 and not bad, (runs, bad)                                        # the water's tint goes from a depth's to the next's in whole steps of 4 art px (it was a smooth ramp)
    # a bridge: its model's paint alone (nothing laid flat on its tile); a wall: its look is data the land's painter lays, no painter of its own
    assert g.js(f"(() => {{ drawTile({px + 2}, {py + 2}, {{px: new Uint32Array(256), o: 0, w: 16}}); return [LAID.n, typeof Bridge.lay, typeof Structures.drawWall, Models.at({px + 2}, {py + 2}).length > 0]; }})()") == [0, "undefined", "undefined", True]
    look = g.js("['W', '%'].map((c) => { const l = Structures.look(c); return [l.ink >>> 24, l.cap >>> 24, l.front[0].width > 0]; })")
    assert look == [[255, 255, True]] * 2, look
    g.stamp(px - x, py - y, ["........"] * 4)
    assert not g.errors
