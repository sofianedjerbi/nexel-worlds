"""You and your marks in and round holes, in the HD look (audit A8: hd_level.js `steep`, `raise`, `cut`; target.js; vox_style.js).
ONE answer to "where are you and your marks drawn": a mark is drawn with you (lifted as your body is in a hole seen from
above), never over your body; any dug space, a room five wide too, is seen from above with you inside its opening; behind
land the disc round you is opened and you are in it whole (it was a checker cat for as long as you stood there)."""

from test_e2e_hd_behind import STATE, calm, go, tidy
from test_e2e_hd_sun import hd

STEEP = 58          # the eye's pitch from above (hd.js STEEP: 78.6 till the x-ray cut what hides you, 68 when a level was 8 px)


def test_a_box_is_never_drawn_over_your_body(browser, server):
    """Build mode facing a wall two high north of you: X's box is the wall's cell over your head, drawn on the screen
    where your body is (two levels up is a tile north). It covered all of the cat: the box goes behind you."""
    g = hd(browser, server)
    calm(g)
    g.give(dirt=2)
    g.clear_area(6)
    g.stamp(-1, -1, ["..."], levels=["222"])
    g.rest()
    g.face(0, -1)
    g.hold_item("dirt")
    g.press("z")
    g.wait("Build.on", 3000)
    g.frames(3)
    drew = g.js("Target.drew.map((d) => [d.key, d.kind, d.r ? 1 : 0])")
    assert ["alt", "break", 1] in drew, drew
    seen = g.js("HdLook.catSeen()")
    assert seen > .9, (seen, drew)                                         # (it was under the box's hatch, when boxes were hatched)
    g.press("z")
    g.wait("!Build.on", 3000)
    assert not g.errors


def test_in_a_shaft_six_deep_the_marks_are_where_their_cells_are(browser, server):
    """Shaft six deep, seen from above: its south wall hides you, the x-ray window is on you (hd_level.js hides); you are
    drawn at your level, and every box of yours is the cell's own box where it is, in the window with you. (You were
    lifted to the rim's line and the boxes with you: hd_level.js lift, raise; at a cliff's foot that drew you on its top.)"""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.give(pickaxe=1)
    g.rpc("dev_col", tiles=[[x + 3, y]], col=[-6])
    g.rest()
    go(g, x + 3, y, -6, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep")
    g.hold_item("pickaxe")
    g.frames(3)
    L, _, _, lift, rim = g.js("HdLook.level")
    assert L == -6 and rim == 0 and lift == 0 and g.js("HdLook.win.a") == 1, (L, lift, rim)
    drew = g.js("Target.drew.filter((d) => d.px).map((d) => ({x: d.x, y: d.y, z: d.z, px: d.px}))")
    assert drew, "a box is drawn"
    for d in drew:
        want = g.js("([x, y, z]) => HdLook.screenOf(x, y, z)", [d["x"], d["y"], d["z"]])
        assert abs(want[0] - d["px"][0]) < .01 and abs(want[1] - d["px"][1]) < .01, (d, want)
    tidy(g, x, y)


def test_in_a_shaft_three_deep_a_box_in_the_south_wall_is_inside_the_opening(browser, server):
    """Shaft three deep (dug down with X), facing its south wall: you are hardly lifted, and the boxes of the cells in
    that wall (Space's, R's "Dig a step": the way's block) lay on the grass south of the rim: that wall's face turned to
    you faces away from the eye. They are drawn as that face folded up into the opening (hd_level.js wallAt): every px
    of every box lies inside the hole's opening on the screen."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.give(pickaxe=1)
    g.rpc("dev_col", tiles=[[x + 3, y]], col=[-3])
    g.rest()
    go(g, x + 3, y, -3, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep")
    g.hold_item("pickaxe")
    g.face(0, 1)
    g.frames(3)
    L, _, _, lift, rim = g.js("HdLook.level")
    assert L == -3 and rim == 0 and lift == 0, (L, lift, rim)
    assert g.js("HdLook.win.a") == 1                                       # (from 58 degrees its south wall hides you: cut, hd.js PART; the boxes in it are drawn where their cells are, in the cut)
    nw, se = g.js(f"HdLook.screenOf({x + 3}, {y}, 0)"), g.js(f"HdLook.screenOf({x + 4}, {y + 2}, -3)")
    boxes = g.js("Target.drew.filter((d) => d.r && d.y > %d).map((d) => d.r).concat(WayShow.block && WayShow.cur.next.y > %d ? [WayShow.block] : [])" % (y, y))
    assert boxes, "a box in the south wall is drawn"
    u = g.js("zoom")
    for r in boxes:
        assert nw[1] - u <= r["y"] and r["y"] + r["h"] <= se[1] + u and nw[0] - u <= r["x"] and r["x"] + r["w"] <= se[0] + u, (r, nw, se)
    tidy(g, x, y)


def test_a_room_five_by_four_four_deep_is_seen_from_above_with_you_inside_it(browser, server):
    """A room 5 x 4 dug 4 deep (open to the sky): the eye looks from above (the old ring two tiles out lay inside the
    room: side-on, 36), and on its south row your body is inside its opening on the screen, not a checker on the grass."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + 2 + i, y + 2 + j] for j in range(4) for i in range(5)], col=[-3])     # (three blocks deep)
    g.rest()
    for ty in (y + 3, y + 5):                                              # (its middle, its south row)
        s = go(g, x + 4, ty, -3, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep")
        assert s["pitch"] == STEEP and s["seen"] > .9, s                     # (from 58 degrees the south wall hides you: cut, hd.js PART)
        nw, se, u = g.js(f"HdLook.screenOf({x + 2}, {y + 2}, 0)"), g.js(f"HdLook.screenOf({x + 7}, {y + 6}, -3)"), g.js("zoom")
        seen, out = g.js("(b) => HdLook.catSeen(b)", [nw[0] - u, nw[1] - u, se[0] + u, se[1] + u])
        assert (seen > .8 and out == 0) if ty == y + 3 else (seen > .7 and out <= 8), (ty - y, seen, out)     # (on its south row its rim, three over your feet, hides your feet, as the land is: you were lifted out of it, hd_level.js lift, gone)
    tidy(g, x, y)


def test_in_a_room_four_deep_the_marks_are_inside_its_opening_and_none_on_you(browser, server):
    """A room 5 x 4 dug 4 deep, you on its middle row: the way out's block to break is in its south wall, and it lay
    on the grass south of the rim (the wall's face turned to you faces away from the eye; it was folded into the
    opening only while you were lifted): it is drawn on that wall's face inside the opening (hd_level.js wall). Facing
    north, the floor cell there is under your head from above: its box was a white square round your head; a box
    that shares much of your sprite's box is not drawn, and nothing of one is drawn in it (target.js)."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + 2 + i, y + 2 + j] for j in range(4) for i in range(5)], col=[-4])
    g.rest()
    go(g, x + 4, y + 4, -4, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep")
    g.stamp(0, -1, ["r"], levels=["d"])                                                      # (a rug north of you: X rolls it up, a box)
    g.rest()
    g.wait("WayShow.cur && WayShow.cur.next && WayShow.block", timeout=8000)
    nw, se, u = g.js(f"HdLook.screenOf({x + 2}, {y + 2}, 0)"), g.js(f"HdLook.screenOf({x + 7}, {y + 7}, -4)"), g.js("zoom")     # (the room as the eye sees it, its south wall cut: down to its floor's south edge, the wall's row in)
    nxt, blk = g.js("WayShow.cur.next"), g.js("WayShow.block")
    assert nxt["y"] > y + 4, nxt                                                              # (in the south wall)
    assert nw[1] - u <= blk["y"] and blk["y"] + blk["h"] <= se[1] + u and nw[0] - u <= blk["x"] and blk["x"] + blk["w"] <= se[0] + u, (blk, nw, se)
    for f in ((0, -1), (0, 1)):
        g.face(*f)
        g.frames(3)
        body = g.js("HdLook.art().body")
        assert body, "your sprite's box"
        for d in g.js("Target.drew"):
            r = d.get("r")
            if not r:
                continue
            assert nw[1] - u <= r["y"] and r["y"] + r["h"] <= se[1] + u, (f, d, nw, se)
            ov = max(0, min(r["x"] + r["w"], body["x"] + body["w"]) - max(r["x"], body["x"])) * max(0, min(r["y"] + r["h"], body["y"] + body["h"]) - max(r["y"], body["y"]))
            assert ov <= .4 * min(r["w"] * r["h"], body["w"] * body["h"]), (f, d, body)   # (no box round your head)
        b = g.js("WayShow.block")
        assert not (b["x"] < body["x"] + body["w"] and body["x"] < b["x"] + b["w"] and b["y"] < body["y"] + body["h"] and body["y"] < b["y"] + b["h"]), (b, body)
        if f == (0, -1):
            assert g.js(f"Target.drew.some((d) => d.y === {y + 3})"), g.js("Target.drew")   # (facing north: the rug's box, put away or drawn clear of your head: the assert above)
    tidy(g, x, y)


def test_behind_a_slab_you_are_whole(browser, server):
    """Behind land five high (the owner's gorge at -58,47; the canyon's foot at 26,-36 on seed 12): you are drawn
    whole, the eye looking down over the slab (hd_level.js clear). It was one px in two of you in the disc's own px: a checker cat, always."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    slab = [[x + i, y + j] for j in range(1, 6) for i in range(-3, 4)]
    g.rpc("dev_col", tiles=slab, col=[5])
    g.rest()
    try:
        go(g, x, y)
        g.wait("HdLook.catSeen() > .9", timeout=4000)                      # (it was .41)
        assert g.js("HdLook.cam.pitch") > 36.1
    finally:
        g.rpc("dev_col", tiles=slab, col=[0])
        tidy(g, x, y)


def test_in_a_room_the_eye_looks_down_no_steeper_than_steep_and_what_hides_you_is_cut(browser, server):
    """The owner: "the camera's inclination makes it hard to build" (78.6 degrees, nearly straight down, in every hole). The eye
    now looks down no steeper than hd.js STEEP, and land between it and you is cut (the x-ray) as soon as it hides a quarter of
    you (hd.js PART). In a room 4 deep, at 64 degrees, its south wall hid half of you: no window, you a checker of one px in two,
    the floor at your feet under the wall. At STEEP and at 64 alike: the window open, all of you seen."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.stamp(-3, -2, ["BnnnLh", "nnnrnn", "nnnnnn", "KnnnnC"], levels=["dddddd"] * 4)        # a room 4 deep, 6 x 4, you on its third row
    try:
        s = go(g, x, y, -4, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep && HdLook.win.a === 1")
        assert s["pitch"] == STEEP and s["seen"] > .95 and s["n"] > 0, s
        g.js("HdLook.steep = 64")
        g.wait("HdLook.cam.pitch === 64 && !HdLook.busy", timeout=6000)
        g.sleep(700)
        g.rest()
        s = g.js(STATE)
        assert s["a"] == 1 and s["n"] > 0 and s["seen"] > .95, s
    finally:
        g.js(f"HdLook.steep = {STEEP}")
        tidy(g, x, y)


def test_a_click_on_the_sky_is_no_walk(browser, server):
    """The pointer on the sky is on no tile (mouse.js tileAtScreen: the HD camera's own answer, or none). Where the
    camera had none the classic flat picture's maths answered: a click on the sky was a walk to a tile far north."""
    from test_e2e_hd_sun import hd
    g = hd(browser, server)
    x, y = g.pos()
    assert g.js("HdLook.sky(0).line") > 60                          # (there is sky at the top of the picture)
    assert g.js("tileAtScreen(480, 20)") is None
    g.page.mouse.move(480, 20)
    g.page.mouse.click(480, 20)
    g.page.mouse.click(480, 20, button="right")
    g.sleep(700)
    assert g.pos() == (x, y) and g.js("!walking") and not g.errors
    q = g.js(f"(() => {{ const a = HdLook.screenOf({x + 2.5}, {y + 1.5}, 0); return tileAtScreen(a[0], a[1]); }})()")
    assert q and (q["x"], q["y"]) == (x + 2, y + 1), q             # (and the land under the pointer is that tile)


# a grid of screen points (CSS px), each: [mx, my, its px is clear sky (blue over green over red), the tile under it or null, does that tile's drawn box (its top down to the lowest land beside it) hold the point]
SWEEP = """([x0, y0, x1, y1, step]) => { const k = devicePixelRatio, out = [], S = HdLook.screenOf;
  for (let my = y0; my <= y1; my += step) for (let mx = x0; mx <= x1; mx += step) { const d = HdLook.read(Math.round(mx * k), Math.round(my * k), 1, 1).data, sky = d[2] > d[1] + 12 && d[1] > d[0] + 12, q = tileAtScreen(mx, my); let ok = null;
    if (q) { const t = topAt(q.x, q.y), lo = Math.min(t, topAt(q.x, q.y + 1), topAt(q.x + 1, q.y), topAt(q.x - 1, q.y)) - 1, pts = [];
      for (const z of [t, lo]) for (const [a, b] of [[0, 0], [1, 0], [1, 1], [0, 1]]) { const p = S(q.x + a, q.y + b, z); if (p) pts.push(p); }
      ok = pts.length === 8 && mx >= Math.min(...pts.map((p) => p[0])) - 2 && mx <= Math.max(...pts.map((p) => p[0])) + 2 && my >= Math.min(...pts.map((p) => p[1])) - 2 && my <= Math.max(...pts.map((p) => p[1])) + 2; }
    out.push([mx, my, sky, q && [q.x, q.y], ok]); } return out; }"""
# the middle of every top, and of every side turned south, east or west, of the land round (x, y) as the picture has it: [which, dx, dy, mx, my, the tile under that point or null]
FACES = """([x, y]) => { const out = [], S = HdLook.screenOf; for (let j = -8; j <= 6; j++) for (let i = -11; i <= 11; i++) { const X = x + i, Y = y + j, t = topAt(X, Y);
  const add = (k, px, py, pz) => { const a = S(px, py, pz); if (a && a[0] > 8 && a[0] < innerWidth - 8 && a[1] > 8 && a[1] < innerHeight - 110) { const q = tileAtScreen(a[0], a[1]); out.push([k, i, j, a[0], a[1], q && [q.x, q.y]]); } };
  add('top', X + .5, Y + .5, t); if (topAt(X, Y + 1) < t) add('south', X + .5, Y + 1, t - .5); if (topAt(X + 1, Y) < t) add('east', X + 1, Y + .5, t - .5); if (topAt(X - 1, Y) < t) add('west', X, Y + .5, t - .5); } return out; }"""


# the made land (HdLook.box) and, of each of its tiles whose top's middle is on the picture and two px tall or more: [x, y, mx, my, is a tile under that point]
BOXTOPS = """(() => { const B = HdLook.box, S = HdLook.screenOf, out = []; for (let y = B[1]; y <= B[3]; y++) for (let x = B[0]; x <= B[2]; x++) { const t = topAt(x, y), a = S(x + .5, y + .5, t), n = S(x + .5, y, t), f = S(x + .5, y + 1, t);
  if (a && n && f && f[1] - n[1] >= 2 && a[0] > 8 && a[0] < innerWidth - 8 && a[1] > 8 && a[1] < innerHeight - 110) out.push([x, y, Math.round(a[0]), Math.round(a[1]), !!tileAtScreen(a[0], a[1])]); } return [B, out]; })()"""


def test_every_px_of_the_land_is_on_a_tile_and_the_sky_on_none(browser, server):
    """A hill, a cliff, a pit and steps round you. The pointer anywhere on the land, a top, a front, a side turned east
    or west, is on a tile, and that tile's drawn box holds the pointer; on the clear sky it is on none. (The HD camera
    had no answer on a hill's or a cliff's side, and the classic flat picture's maths, asked last, named a tile for
    those and for the sky alike.)"""
    from test_e2e_hd_sun import hd
    g = hd(browser, server)
    g.hour(.3, still=True)
    g.clear_area(30)
    x, y = g.pos()
    g.stamp(-9, -8, ["....."] * 4, levels=["33333"] * 4)                 # a hill three high, north-west
    g.stamp(4, -9, ["......"] * 3, levels=["777777"] * 3)                # a cliff seven high, north-east
    g.stamp(-6, 2, ["..."] * 3, levels=["bbb"] * 3)                      # a pit two deep, south-west
    g.stamp(3, 2, ["...."] * 2, levels=["1111", "2222"])                 # steps up, south-east
    g.rest(); g.frames(3)
    g.page.mouse.move(5, 5)
    edge = g.js("HdLook.sky(0).edge")
    r = g.js(SWEEP, [12, 12, 948, 430, 24])
    assert not [p for p in r if p[3] is not None and not p[4]], [p for p in r if p[3] is not None and not p[4]][:8]     # a tile named: its box holds the point
    under = [p for p in r if p[1] > edge + 4]
    assert len(under) > 150 and not [p for p in under if p[3] is None], [p for p in under if p[3] is None][:8]         # under the land's edge all is land: a tile each
    sky = [p for p in r if p[2] and p[1] < edge - 4]
    assert len(sky) > 30 and sum(1 for p in sky if p[3] is not None) <= 2, [p for p in sky if p[3] is not None][:8]     # the clear sky: none (a point on a cliff's very edge aside)
    faces = g.js(FACES, [x, y])
    kinds = {k: sum(1 for f in faces if f[0] == k) for k in ("top", "south", "east", "west")}
    assert kinds["top"] > 200 and kinds["south"] >= 8 and kinds["east"] >= 6 and kinds["west"] >= 6, kinds
    assert not [f for f in faces if f[5] is None], [f for f in faces if f[5] is None][:8]                               # every top and every side shown: a tile
    sides = [f for f in faces if (f[0] == "east" and f[1] < -1) or (f[0] == "west" and f[1] > 1)]                       # (the sides turned to the picture's middle: the others are behind their own land)
    assert len(sides) >= 6 and sum(1 for f in sides if f[5] == [x + f[1], y + f[2]]) >= .7 * len(sides), sides[:8]     # a side shown is its own tile's (a few are behind land nearer the eye)
    # FAR and VERY FAR (the view setting, and zoomed out): the land made is HdLook.box, wider and deeper: the top of every tile of it that is on the picture (two px
    # tall or more) answers. (The pick looked 24 tiles each way whatever was made: past that a click on land you see did nothing. At zoom 3 on this screen no top
    # past 21 tiles is two px tall, at any setting: zoomed out at Very far they are, to 38.)
    try:
        for view, z, past in ((25, 3, 0), (37, 1, 20)):
            g.js(f"(() => {{ setOpt('view', {view}); zoom = ZOOM.to = {z}; return 1; }})()")
            g.rest(); g.frames(3)
            box, tops = g.js(BOXTOPS)
            far = [t for t in tops if max(abs(t[0] - x), abs(t[1] - y)) > 24]
            assert y - box[1] > 24 and len(tops) > 400 and len(far) >= past, (view, z, len(tops), len(far), box)       # (the land made goes more than 24 tiles north of you)
            assert not [t for t in tops if not t[4]], (view, z, box, [t for t in tops if not t[4]][:8])
    finally:
        g.js("(() => { setOpt('view', OPT_DEFAULT.view); zoom = ZOOM.to = 3; return 1; })()")
    assert not g.errors
