"""The whole cave is open to you (#8; the owner: "the whole cave should show up to the player, not a small radius",
"the whole point of xray is to unlock the whole view of a cave entirely"). Under the land, your space is every floor
you can walk or drop to in the land made round you (as far as the view distance makes it), however far round the
cave winds: not 24 steps of it. A cave of 50 tiles, winding back on itself and branching, on the screen, is opened to
its far ends from one end of it."""

from test_e2e_hd_sun import hd

CUT = "([x, y]) => HdLook.cut(x, y) ?? null"
W = 15
# three rows of 15 joined at alternate ends (its far end 46 steps from the west end of the first), and a branch of 3
# south off the last one (42 steps): past 24 steps it was left shut, and past R (about 30 on this screen) by steps too
CAVE = ({(i, -2) for i in range(W)} | {(W - 1, -1)} | {(i, 0) for i in range(W)} | {(0, 1)} | {(i, 2) for i in range(W)}
        | {(7, j) for j in range(3, 6)})


def test_a_cave_winding_back_on_itself_is_opened_to_its_far_ends(browser, server):
    g = hd(browser, server)
    g.js("setOpt('view', 41)")
    x, y = g.pos()
    g.stamp(-6, -8, ["." * (W + 12)] * 17, levels=["4" * (W + 12)] * 17)          # a meadow at 4
    g.rest()
    rows = ["".join("." if (i, j) in CAVE else " " for i in range(W)) for j in range(-2, 6)]
    g.stamp(0, -2, rows, levels=["1" * W] * 8, roofs=["3" * W] * 8, heads=["2" * W] * 8)   # under it the cave, its floor at 1, two cells of air
    g.rpc("dev_teleport", x=x, y=y - 2, z=1)                                      # at the west end of its first row
    g.wait("HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=20000)
    g.rest()
    shut = [(i, j) for i, j in sorted(CAVE) if g.js(CUT, [x + i, y + j]) is None]
    assert not shut, shut                                                         # every floor of it open
    for t in ([x + 3, y + 5], [x + 11, y + 5]):                                   # the rock beside its branch, past the tile round it: drawn whole
        cut = g.js(CUT, t)                                                        # (a cut there, of a hollow beside the window, is at the land's top: none of it taken)
        assert cut is None or cut >= g.js(f"topAt({t[0]}, {t[1]})"), (t, cut)
    assert not g.errors
