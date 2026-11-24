"""Behind a mountain, on the surface, its caves stay shut (vox_style_land.js: your space, the window, the cut; the owner:
"being behind a mountain shouldn't show the caves")."""

from test_e2e_hd_behind import calm, go
from test_e2e_hd_sun import hd

CUT = "([x, y]) => HdLook.cut(x, y) ?? null"


def test_behind_a_mountain_its_caves_stay_shut(browser, server):
    """On the surface behind a mountain (the land hides you, none is over your head), a cave in it, its mouth on your
    side, is not cut open: the land's cut is for being UNDER the land (the owner: "being behind a mountain shouldn't
    show the caves"). Inside the cave, it opens."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    hill = [[x + i, y + j] for j in range(1, 9) for i in range(-4, 5)]
    cave = [[x, y + j] for j in range(1, 6)] + [[x + i, y + 5] for i in range(-3, 4)]
    g.rpc("dev_col", tiles=hill, col=[8])                                  # a mountain of stone eight high, south of you ...
    g.rpc("dev_col", tiles=cave, col=[0, 2, 8])                            # ... a cave in it, its mouth at your feet, a hall across
    g.rest()
    try:
        go(g, x, y)                                                        # behind it, at the mouth
        cut = [t for t in cave + hill if g.js(CUT, t) is not None]
        assert not cut, cut                                                # nothing of the mountain cut: its cave shut
        far = [t[:2] for t in g.js("HdLook.win.tiles") if t[:2] in cave and abs(t[0] - x) + abs(t[1] - y) > 2]
        assert not far, far                                                # nor seen through: the window has the two tiles you step into, no more
        go(g, x - 3, y)
        assert not [t for t in g.js("HdLook.win.tiles") if t[:2] in cave]   # three tiles off its mouth: none of it
        go(g, x, y + 4, 0, "HdLook.win.a === 1 && !HdLook.busy")           # in the cave
        assert g.js(CUT, [x, y + 5]) is not None                           # under it: the cut is on
    finally:
        g.rpc("dev_col", tiles=hill, col=[0])
