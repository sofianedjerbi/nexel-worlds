"""Every face kind is painted as its cell is (#4, the face rule at the top of vox_style_land.js, point 2: one material).
On an earth hill (3 high: earth over stone) and a stone hill (7 high: stone at every height), by day: a top is its
ground, a front and a step's riser are the cell's own rock (earth brown, stone grey, never the grass over it), and a
floor dug under the land is its own rock."""

import pytest
from test_e2e_hd_sun import hd

# the colour of the picture at a place of the world (device px)
AT = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(HdLook.read(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data).slice(0, 3); }"""
green = lambda c: c[1] > c[0] + 12 and c[1] > c[2] + 20
brown = lambda c: c[0] > c[1] + 8 and c[0] > c[2] + 15
grey = lambda c: max(c) - min(c) < 26


def hill(g, lv):
    """A hill lv high north of you, its south edge stepping down a level a row to the meadow; you on the meadow."""
    rows = ["." * 17] * 17
    levels = [(str(lv) * 17 if j < 10 else "".join(str(max(0, lv - (j - 9))) for _ in range(17))) for j in range(17)]
    g.stamp(-8, -14, rows, levels=levels)
    g.rest()


@pytest.mark.parametrize("lv", [3, 7], ids=["earth", "stone"])
def test_faces_are_painted_as_their_cells(browser, server, lv):
    g = hd(browser, server)
    try:
        g.js("setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0); setOpt('shadows', 0)")
        g.hour(.3, still=True)
        x, y = g.pos()
        hill(g, lv)
        g.frames(6)
        top = g.js(AT, [x + .5, y - 5.5, lv])                       # (the top of the hill's edge row)
        front = g.js(AT, [x + .5, y - 4, lv - .5])                   # (the edge's south face, half a level under its top)
        riser = g.js(AT, [x + .5, y - 3, lv - 1.5])                  # (the next step down's south face)
        room = [[x + i, y - 9 + j] for j in range(-1, 2) for i in range(-1, 2)]
        g.rpc("dev_col", tiles=room, col=[lv - 4, lv - 2, lv])
        g.rest()
        g.rpc("dev_teleport", x=x, y=y - 9, z=lv - 4)
        g.arrive()
        g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=10000)
        g.rest()
        floor = g.js(AT, [x + 1.5, y - 7.5, lv - 4])                # (a tile of the room's floor beside you, not under your body)
        seen = {"lv": lv, "top": top, "front": front, "riser": riser, "floor": floor}
        if lv < 5:
            assert green(top), seen                                  # an earth hill's top: its grass
            assert brown(front) and brown(riser), seen               # its edge and its step: earth, not the grass over them
        else:
            assert grey(top) and not green(top), seen                # a stone hill's top: stone
            assert grey(front) and grey(riser), seen                 # its edge and its step: stone
        assert not green(floor), seen                                # a floor dug under the land: its rock, never grass (lit by your lantern: its tone is the light's)
        assert not g.errors
    finally:
        g.page.close()
