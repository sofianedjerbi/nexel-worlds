"""You and your marks in and round holes, in the HD look (audit A8: hd_level.js `steep`, `raise`, `cut`; target.js; vox_style.js).
ONE answer to "where are you and your marks drawn": a mark is drawn with you (lifted as your body is in a hole seen from
above), never over your body; any dug space, a room five wide too, is seen from above with you inside its opening; behind
land the disc round you is opened and you are in it whole (it was a checker cat for as long as you stood there)."""

from test_e2e_hd_behind import calm, go, tidy
from test_e2e_hd_sun import hd


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
    assert seen > .9, (seen, drew)                                         # (it was under the box's hatch)
    g.press("z")
    g.wait("!Build.on", 3000)
    assert not g.errors


def test_in_a_shaft_six_deep_the_marks_are_lifted_with_you(browser, server):
    """Shaft six deep, seen from above: you are drawn lifted to the rim's line (hd_level.js lift); every box of yours is
    the cell's own box with that same lift at your feet's level, none at the rim (raise): R's step box lay faint on the
    grass south-west of the hole, a level-and-a-half below your feet on the screen."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.give(pickaxe=1)
    g.rpc("dev_col", tiles=[[x + 3, y]], col=[-6])
    g.rest()
    go(g, x + 3, y, -6, "!HdLook.busy && HdLook.cam.pitch === 68")
    g.hold_item("pickaxe")
    g.frames(3)
    L, _, _, lift, rim = g.js("HdLook.level")
    assert L == -6 and rim == 0 and lift > 2, (L, lift, rim)
    drew = g.js("Target.drew.filter((d) => d.px).map((d) => ({x: d.x, y: d.y, z: d.z, px: d.px}))")
    assert drew, "a box is drawn"
    for d in drew:
        want = g.js("([x, y, z]) => HdLook.screenOf(x, y, z)", [d["x"], d["y"], d["z"] + lift * min(1, max(0, (rim - d["z"]) / (rim - L)))])
        assert abs(want[0] - d["px"][0]) < .01 and abs(want[1] - d["px"][1]) < .01, (d, want)
    rim_line = g.js(f"HdLook.screenOf({x + 3}, {y + 1}, 0)")[1]
    mids = [g.js("([x, y, z]) => HdLook.markOf(x, y, z)", [d["x"] + .5, d["y"] + .5, d["z"]])[1] for d in drew]
    assert all(t <= rim_line + g.js("zoom") for t in mids), (mids, rim_line)          # (a box's top is where your feet are, at the rim's line: it lay a tile down the grass)
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
    go(g, x + 3, y, -3, "!HdLook.busy && HdLook.cam.pitch === 68")
    g.hold_item("pickaxe")
    g.face(0, 1)
    g.frames(3)
    L, _, _, lift, rim = g.js("HdLook.level")
    assert L == -3 and rim == 0 and 0 < lift < 1, (L, lift, rim)
    nw, se = g.js(f"HdLook.screenOf({x + 3}, {y}, 0)"), g.js(f"HdLook.screenOf({x + 4}, {y + 1}, 0)")
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
    g.rpc("dev_col", tiles=[[x + 2 + i, y + 2 + j] for j in range(4) for i in range(5)], col=[-4])
    g.rest()
    for ty in (y + 3, y + 5):                                              # (its middle, its south row)
        s = go(g, x + 4, ty, -4, "!HdLook.busy && HdLook.cam.pitch === 68")
        assert s["pitch"] == 68 and s["n"] == 0, s
        nw, se, u = g.js(f"HdLook.screenOf({x + 2}, {y + 2}, 0)"), g.js(f"HdLook.screenOf({x + 7}, {y + 6}, 0)"), g.js("zoom")
        seen, out = g.js("(b) => HdLook.catSeen(b)", [nw[0] - u, nw[1] - u, se[0] + u, se[1] + u])
        assert seen > .8 and out == 0, (ty - y, seen, out)
    tidy(g, x, y)


def test_behind_a_slab_you_are_whole_in_the_disc(browser, server):
    """Behind land five high (the owner's gorge at -58,47; the canyon's foot at 26,-36 on seed 12): the disc is opened
    round you and you are drawn whole in it. It was one px in two of you in the disc's own px: a checker cat, always."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    slab = [[x + i, y + j] for j in range(1, 6) for i in range(-3, 4)]
    g.rpc("dev_col", tiles=slab, col=[5])
    g.rest()
    try:
        go(g, x, y)
        g.wait("HdLook.catSeen() > .9", timeout=4000)                      # (the disc opens over 120 ms; it was .41)
        assert g.js("HdLook.cam.pitch") < 36.1 and g.js("HdLook.win.n") == 0
    finally:
        g.rpc("dev_col", tiles=slab, col=[0])
        tidy(g, x, y)
