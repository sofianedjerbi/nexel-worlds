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
