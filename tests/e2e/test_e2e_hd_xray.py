"""The x-ray window's shape and its cut edges in the HD look (vox_style_glsl.js PORT and the window's section, vox_style_land.js):
the window is your WHOLE space, a cave's every branch as far as the screen goes (a separate cave stays under the stone), its sides
in whole art px, no checker (HdLook.edge "B": the kept land's last 3 px over your space in solid steps of opacity); under the open sky no dark arc at its top (a gorge's far cliff); a pit's floor shaded by its own walls, no
flat squares of corner shade; down a passage a level floor has no band across it, a step up shows its riser, a step down its lip."""

from test_e2e_hd_sun import LIGHT, hd
from test_e2e_hd_window import PX

# the picture with the window and without it (HdLook.nowin): which px it changes, in the box of CSS px [x0, y0, x1, y1] -> rows of 0/1
CHANGED = """async ([x0, y0, x1, y1]) => { const k = devicePixelRatio, X0 = Math.round(x0 * k), Y0 = Math.round(y0 * k), W = Math.round((x1 - x0) * k), H = Math.round((y1 - y0) * k), frame = () => new Promise(requestAnimationFrame);
  const shot = async (off) => { HdLook.nowin = off; for (let i = 0; i < 90 && HdLook.win.a !== (off ? 0 : 1); i++) await frame(); for (let i = 0; i < 4; i++) await frame(); return HdLook.read(X0, Y0, W, H).data; };
  const a = await shot(true), b = await shot(false), rows = [];
  for (let y = 0; y < H; y++) { let r = ""; for (let x = 0; x < W; x++) { const i = 4 * (y * W + x); r += Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 30 ? "1" : "0"; } rows.push(r); }
  return rows; }"""
SCR = "(([x, y, z]) => HdLook.screenOf(x, y, z))"
# the picture in the look `e` (HdLook.edge), a colour an art px, rows of the box of CSS px [x0, y0, x1, y1] an art px apart
ROWS = """async ([e, x0, y0, x1, y1]) => { HdLook.edge = e; const frame = () => new Promise(requestAnimationFrame); for (let i = 0; i < 4; i++) await frame();
  const k = devicePixelRatio, z = zoom, out = []; for (let y = Math.round(y0 / z) * z + z / 2; y < y1; y += z) { const r = []; for (let x = Math.round(x0 / z) * z + z / 2; x < x1; x += z) r.push([...HdLook.read(Math.round(x * k), Math.round(y * k), 1, 1).data.slice(0, 3)]); out.push(r); }
  HdLook.edge = "B"; for (let i = 0; i < 3; i++) await frame(); return out; }"""
calm = lambda g: [g.hour(.3, still=True)] + [g.js(f"setOpt('{o}', 0)") for o in ("clouds", "rays", "shimmer")]
far = lambda a, b: sum(abs(p - q) for p, q in zip(a, b))
lum = lambda c: .3 * c[0] + .59 * c[1] + .11 * c[2]


def quiet(g):
    g.js("(() => { WayShow.paint = () => {}; Target.off = true; return 1; })()")
    g.rest()


# a plateau of stone 5 high; in it, floors at 0 under two cells of air: a corridor west to east, a branch north, two south, a room
# north-east, and a separate cave south-west no way joins (dx, dy from where you were)
CAVE = {(dx, -2) for dx in range(-8, 9)} | {(0, dy) for dy in range(-6, -2)} | {(dx, dy) for dx in (-5, 5) for dy in range(-1, 3)} | \
       {(dx, dy) for dx in range(6, 10) for dy in range(-6, -3)} | {(8, -3)}
APART = {(dx, dy) for dx in (-9, -8) for dy in (2, 3)}


def test_the_window_opens_the_whole_cave_you_are_in_and_not_another(browser, server):
    """The owner in a cave under a stone plateau, the porthole round him: "the whole point of x-ray is to unlock the whole view
    of a cave entirely, not a little circle. I'm blind in that cave!" Every floor of the cave you are in, its branches and its
    room, is seen where the screen shows it; a cave no way joins stays under the stone; its sides are cut in whole art px, no checker
    (owner: "that x-ray you did created awful borders": a 4x4 dither down every side)."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    rows = ["".join("-" if (dx, dy) in CAVE | APART else "." for dx in range(-10, 11)) for dy in range(-7, 9)]     # (the plateau 4 rows past the other cave: from 58 degrees its south face stood where that cave's floor projects)
    g.stamp(-10, -7, ["." * 21] * 16, levels=["5" * 21] * 16)
    g.stamp(-10, -7, rows, levels=[r.replace("-", "0").replace(".", "5") for r in rows], roofs=[r.replace("-", "5").replace(".", "0") for r in rows],
            heads=[r.replace("-", "2").replace(".", "0") for r in rows])
    g.rpc("dev_teleport", x=x, y=y - 2, z=0)
    g.wait("HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=8000)
    quiet(g)
    W, H = g.js("[innerWidth, innerHeight]")
    stone = g.js(PX, [x - 1.5, y + 2.5, 5])                                 # (the plateau's top, far from the caves)
    on = lambda p: 8 < p[0] < W - 8 and 8 < p[1] < H - 60
    shut, opened = [], []
    for dx, dy in sorted(CAVE | APART):
        if not on(g.js(SCR, [x + dx + .5, y + dy + .5, 0])):
            continue
        c, w = g.js(PX, [x + dx + .5, y + dy + .5, 0]), g.js(f"HdLook.winAt({x + dx}, {y + dy})")
        if (dx, dy) in APART and (w is not None or not (max(c) - min(c) < 20 and lum(c) > 50)):     # (opened: in the window, or not stone's grey. It was within 40 of one px of the top's stone: the plateau's top has its darker px, [142, 150, 143] against [159, 165, 157])
            opened.append(((dx, dy), c, w))
        elif (dx, dy) in CAVE and (w is None or far(c, stone) <= 40):
            shut.append(((dx, dy), c, w))
    seen = [t for t in CAVE if on(g.js(SCR, [x + t[0] + .5, y + t[1] + .5, 0]))]
    assert len(seen) >= 30, seen                                             # (most of the cave is on the screen)
    assert not shut, (shut, stone)                                            # every floor of it is seen, in the window (it was a circle 4 tiles round you: the branches under the stone)
    assert not opened, (opened, stone)                                        # the other cave: no window on it, the plateau's top over it
    # the side: across the corridor's west end (its floor at dx -8), art px by art px, in each look
    a, b = g.js(SCR, [x - 10, y - 2, 0]), g.js(SCR, [x - 6, y - 1.4, 0])
    rows = {e: g.js(ROWS, [e, a[0], a[1], b[0], b[1]]) for e in ("B", "C", "A")}
    for e, rs in rows.items():
        bad = [(j, i) for j, r in enumerate(rs) for i in range(len(r) - 3)
               if far(r[i], r[i + 2]) < 12 and far(r[i + 1], r[i + 3]) < 12 and far(r[i], r[i + 1]) > 40]
        assert not bad, (e, bad[:5], [r[max(0, bad[0][1] - 3):bad[0][1] + 6] for r in rs] if bad else None)        # no checker: no px alternating with another along a row (the dither did, a px each)
    diff = [[i for i in range(len(rb)) if far(rb[i], rc[i]) > 30] for rb, rc in zip(rows["B"], rows["C"])]
    first = [(j, [i for n, i in enumerate(d) if i - d[0] == n]) for j, d in enumerate(diff) if d]                     # (the first run of px B changes, from the kept land in: the fade; the floor's foot shade further in is each look's own)
    assert len(first) >= len(diff) // 2 and all(1 <= len(f) <= 4 for _, f in first), diff     # B: the kept land comes back over 3 px or so, side by side (solid steps of opacity), crisp in C
    # (the fade starts where the kept stone is: the px before it is stone's grey. It was within 40 of one px of the top's
    #  stone, the row's fifth: the cut's side is that stone a step darker a level, with its seams (99 against 159), and
    #  which of them is just before the fade is by where you woke: 4 runs in 5)
    grey = lambda c: max(c) - min(c) < 20 and lum(c) > 50
    assert all(grey(rows["B"][j][f[0] - 1]) for j, f in first), [(j, rows["B"][j][f[0] - 1]) for j, f in first]
    assert g.js("HdLook.edge") == "B"


# the owner's gorge (doben8, caves -11,-40): cliffs 12 high, a river in two depths and a cliff's corner in it
GORGE = ["C" * 19] * 2 + ["C" * 10 + "b" * 9, "C" + "a" * 10 + "b" * 8, "a" * 2 + "b" * 17, "b" * 19, "b" * 6 + "a" * 13, "a" * 7 + "C" * 12] + ["C" * 19] * 5


def test_in_a_gorge_the_window_has_no_dark_arc_at_its_top(browser, server):
    """doben8 in the gorge: a dark brown arc at the window's top: the section over its boxes' north edge (a roof's depth band) laid on
    the far cliff's face, which hides nothing, and that face's foot darkened as a hole's wall. Under the open sky neither is drawn."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.stamp(-9, -6, ["." * 19] * 13, levels=GORGE)
    g.stamp(-9, -6, ["".join("." if c == "C" else "~" for c in r) for r in GORGE], levels=GORGE)
    g.rpc("dev_teleport", x=x, y=y)
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=8000)
    quiet(g)
    a, b = g.js(SCR, [x - 3, y - 4, 0]), g.js(SCR, [x + 3, y + .5, 0])     # (the window's upper half: the river to the far cliff's foot, and over it as far as the window goes)
    ch = g.js(CHANGED, [a[0], 0, b[0], b[1]])
    k = g.js("devicePixelRatio")
    d = g.js(f"Array.from(HdLook.read({round(a[0] * k)}, 0, {round((b[0] - a[0]) * k)}, {round(b[1] * k)}).data)")
    W = round((b[0] - a[0]) * k)
    px = [d[4 * (r * W + c):4 * (r * W + c) + 3] for r, row in enumerate(ch) for c, v in enumerate(row) if v == "1" and 4 * (r * W + c) + 3 <= len(d)]
    brown = [c for c in px if c[0] > c[2] + 25 and c[0] > c[1] and lum(c) < 110]
    black = [c for c in px if lum(c) < 40]
    assert len(brown) < 20 and len(black) < 40, (len(brown), len(black), brown[:5], black[:5])


def test_a_pit_s_floor_is_shaded_by_its_walls_not_in_tile_squares(browser, server):
    """A pit 3 x 3, 2 deep, shadows off: its corners and its north edge were flat darker squares (the corners' shade of each tile,
    in steps). The floor's shade is the land's own corner shade, the one every top has (vox_style_land.js AO): it runs on across
    a tile's edge, no step there; along a wall's foot it is darker than in the middle."""
    g = hd(browser, server)
    calm(g)
    g.js("setOpt('shadows', 0)")
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in (-1, 0, 1) for i in (-1, 0, 1)], col=[-2])
    g.rpc("dev_teleport", x=x, y=y, z=-2)
    g.wait("!HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=8000)
    quiet(g)
    for row, n in ((1.5, 56), (-.45, 19)):                                    # (across the south row, west to east past two tiles' edges; the north one to past its first, short of your body)
        r = [lum(g.js(PX, [x - .9 + i * .05, y + row, -2])) for i in range(n)]
        jumps = [abs(b - a) / max(a, b) for a, b in zip(r, r[1:])]
        assert max(jumps) < .1, f"{row} {max(jumps):.2f} {[round(v) for v in r]}"   # no step at a tile's edge: no squares
    mid = lum(g.js(PX, [x + .5, y + .5, -2]))
    foot = lum(g.js(PX, [x + .5, y - 1 + .04, -2]))
    assert foot < mid * .9, (foot, mid)                                       # at the north wall's foot: its shade


def test_down_a_passage_a_level_floor_has_no_band_a_step_up_its_riser_a_step_down_its_lip(browser, server):
    """doben1: "see the line in the path in front of me? I am unable to tell whether it goes up or down." Three passages north
    from your corridor: one level, one a level up, one a level down."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    lv = {(dx, -1): "0" for dx in range(-6, 7)}
    for dy in range(-6, -1):
        lv[(-4, dy)], lv[(0, dy)], lv[(4, dy)] = "0", "0" if dy > -4 else "1", "0" if dy > -4 else "a"
    rows = ["".join("-" if (dx, dy) in lv else "." for dx in range(-8, 9)) for dy in range(-7, 2)]
    g.stamp(-8, -7, ["." * 17] * 9, levels=["5" * 17] * 9)
    g.stamp(-8, -7, rows, levels=["".join(lv.get((dx, dy), "5") for dx in range(-8, 9)) for dy in range(-7, 2)],
            roofs=[r.replace("-", "5").replace(".", "0") for r in rows], heads=[r.replace("-", "2").replace(".", "0") for r in rows])
    g.rpc("dev_teleport", x=x, y=y - 1, z=0)
    g.wait("HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=8000)
    quiet(g)
    col = lambda dx, z: [g.js(PX, [x + dx + .5, y - 1 + .5 - i * .05, z]) for i in range(70)]
    level = [lum(c) for c in col(-4, 0)]
    med = sorted(level)[len(level) // 2]
    assert min(level) > med * .8, (med, level)                                # level: no band across it
    up = col(0, 0)[30:54]                                                     # (the step's edge is at y - 3.5 .. y - 4: its riser over the lower floor)
    assert any(far(c, up[0]) > 40 for c in up), up                            # a step up: its riser, another tone than the floor
    down = [lum(g.js(PX, [x + 4.5, y - 3 + .01 + i * .015, 0])) for i in range(5)]
    near, low = lum(g.js(PX, [x + 4.5, y - 3 + .2, 0])), lum(g.js(PX, [x + 4.5, y - 4.5, -1]))
    assert max(down) > near * 1.15 and max(down) > low * 1.3, (down, near, low)   # a step down: the near floor's edge, lit, over the lower floor, darker (its lip was one row of paint: left out at this pitch)


def test_a_strip_under_a_plateau_is_open_to_its_back_corners(browser, server):
    """doben1 on a strip of meadow at the foot of a stone plateau south of him: the window showed his strip through the plateau, but
    the plateau's top-left corner block still stood over the strip's west end ("x-ray should also apply to left/right back corners"):
    a corner leans over the floor beside it as the eye sees it, and only land straight south counted. No px of the plateau (cobble,
    its sides) over any px of the strip's floor, from one end past its corners to the other."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    rows = ["." * 21] * 6 + ["." * 6 + "_" * 9 + "." * 6] * 6                   # (his strip as it is: the cliff north of it too. A meadow open to the north is no strip: only your few
    g.stamp(-10, -5, rows, levels=["C" * 21] * 2 + [r.replace(".", "0").replace("_", "8") for r in rows[2:]])   #  tiles are opened there, test_e2e_hd_behind.py, the mountain's foot)
    g.rpc("dev_teleport", x=x, y=y, z=0)
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=8000)
    quiet(g)
    W, H = g.js("[innerWidth, innerHeight]")
    bad = []
    for dy in (0, -1):
        for dx in range(-8, 9):
            if dx == 0:
                continue                                                      # (your own body stands there)
            for i in range(4):
                for j in range(4):
                    p = [x + dx + .15 + .23 * i, y + dy + .15 + .23 * j, 0]
                    a = g.js(SCR, p)
                    if not (8 < a[0] < W - 8 and 8 < a[1] < H - 60):
                        continue
                    c = g.js(PX, p)
                    if max(c) - min(c) < 35 or c[0] > c[1] + 15:                  # (grey cobble, its brown and grey sides; grass and its flowers are neither)
                        bad.append(((dx, dy), i, j, c))
    # (a tile is the plateau's when 3 of its 16 px are: one px is not the ground (the meadow's own specks by the tile's place:
    #  one at [153, 153, 124], one run in six); a corner over the strip covers most of a tile)
    tiles = {}
    for t, *_ in bad:
        tiles[t] = tiles.get(t, 0) + 1
    assert not [t for t, n in tiles.items() if n >= 3], (len(bad), bad[:8])   # the strip is grass edge to edge: nothing of the plateau's corners over it
    g.stamp(-10, -5, ["." * 21] * 12, levels=["0" * 21] * 12)                     # (the meadow again: the cliff left standing shaded the next test's cave)


def test_under_the_open_sky_the_opened_strip_keeps_the_cut_land_s_sun_shade(browser, server):
    """doben1 on his strip of meadow between a cliff 12 high north of it and a plateau south of it, the morning sun: the meadow in
    the cliff's shade, the strip the window opens lit, a bright band. The shadow is the world's, the cut is only for the eye: the
    strip in the window is as dark as the meadow beside it, out of the window."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    rows = ["." * 21] * 10 + ["." * 6 + "_" * 9 + "." * 6] * 6
    g.stamp(-10, -9, rows, levels=["C" * 21] * 4 + [r.replace(".", "0").replace("_", "8") for r in rows[4:]])
    g.rpc("dev_teleport", x=x, y=y, z=0)
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=8000)
    quiet(g)
    strip, meadow = [x + 2, y - 1], [x - 9, y - 1]                          # (the strip's own row, west past what the plateau hides from 58 degrees: in the cliff's shade, out of the window)
    assert g.js(f"HdLook.winAt({strip[0]}, {strip[1]})") and not g.js(f"HdLook.winAt({meadow[0]}, {meadow[1]})")
    out = []
    for much in (100, 0):
        g.js(f"setOpt('shadows', {much})")
        g.rest()
        out.append([g.js(LIGHT, [*strip, 0]), g.js(LIGHT, [*meadow, 0])])
    g.js("setOpt('shadows', 100)")
    (s1, m1), (s0, m0) = out
    assert m1 < m0 * .9, out                                                 # (the meadow is in the plateau's shade)
    assert abs(s1 / s0 - m1 / m0) < .04, out                                 # the strip as shaded as the meadow (it was lit: no shade in the window)


def test_a_shaft_at_a_passage_s_end_is_a_level_floor_not_a_band(browser, server):
    """doben1's cave: a passage north from his corridor ends in a shaft open to the sky, its floor level with the passage's. It was a
    dark band across the way (a mouth's shade laid on it, the hole's step of shade): "up or down?". Up the passage into the shaft
    no row is much darker than the passage: a level floor reads level."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    lv = {(dx, -1): "0" for dx in range(-6, 7)} | {(0, dy): "0" for dy in range(-5, -1)}
    rows = ["".join("-" if (dx, dy) in lv else "." for dx in range(-8, 9)) for dy in range(-7, 2)]
    covered = lambda dx, dy: (dx, dy) in lv and dy > -5                     # (the shaft: (0, -5), open to the sky, land north, east, west of it)
    g.stamp(-8, -7, ["." * 17] * 9, levels=["4" * 17] * 9)
    g.stamp(-8, -7, rows, levels=["".join(lv.get((dx, dy), "4") for dx in range(-8, 9)) for dy in range(-7, 2)],
            roofs=["".join("4" if covered(dx, dy) else "0" for dx in range(-8, 9)) for dy in range(-7, 2)],
            heads=["".join("2" if covered(dx, dy) else "0" for dx in range(-8, 9)) for dy in range(-7, 2)])
    g.rpc("dev_teleport", x=x, y=y - 1, z=0)
    g.wait("HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=8000)
    quiet(g)
    # (up the passage's middle, y - 1.1 to y - 4, then the shaft's floor to y - 4.55, short of its north wall's foot: that wall's
    #  foot shade (vox_style_glsl.js, 7 px out in three steps) ends 5.8 px out, at y - 4.64, and the last px read at y - 4.65 was
    #  in it or not by a part of a px, by where you woke: 140 against 173, one run in five)
    way = [lum(g.js(PX, [x + .5, y - 1.1 - i * .05, 0])) for i in range(70)]
    passage, shaft = way[:56], way[62:]
    med = sorted(passage)[len(passage) // 2]
    assert min(shaft) > med * .7 and max(shaft) - min(shaft) < .05 * med, f"{med} {' '.join(str(round(v)) for v in way)}"   # no band: one tone across the shaft's floor, lit by your lantern as the passage is (it was 51 against 173, darkest at the passage's end: the walls' corner shade, the sun's, a mouth's).
    # (.7: the shaft's floor is its own tile's paint under the sky, the passage's the soil under the land: a little darker, the same light)


def test_in_a_gorge_a_bank_s_corner_far_east_of_the_river_is_cut(browser, server):
    """doben8 in the gorge: the south bank's corner, 13 levels over the river, stood in the window at its west edge, a half-faded
    grey block in the water. From the eye the bank's top leans west, three tiles past the river tiles beside it: it hides them and
    is cut. No px of the bank's grey top on the river's floor, as far west as the screen goes."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    lv = ["C" * 25] * 3 + ["a" * 25] * 2 + ["a" * 7 + "K" * 18] + ["K" * 25] * 3   # (the river at dy -1 and 0, west to dx -6 at dy 1; the south bank 20 high, its corner at dx -5)
    g.stamp(-12, -4, ["." * 25] * 9, levels=lv)
    g.stamp(-12, -4, ["".join("~" if c == "a" else "." for c in r) for r in lv], levels=lv)
    g.rpc("dev_teleport", x=x, y=y - 1)
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=8000)
    quiet(g)
    W, H = g.js("[innerWidth, innerHeight]")
    bad = []
    for dy in (-1, 0):
        for dx in range(-12, 0):
            for i in range(3):
                p = [x + dx + .2 + .3 * i, y + dy + .5, -1]
                a = g.js(SCR, p)
                if not (8 < a[0] < W - 8 and 8 < a[1] < H - 60):
                    continue
                c = g.js(PX, p)
                if c[2] < c[0] + 8:                                           # (the bank's stone, grey or pale; the river and its shallows are blue, blue-green)
                    bad.append(((dx, dy), i, c))
    assert not bad, (len(bad), bad[:8])
