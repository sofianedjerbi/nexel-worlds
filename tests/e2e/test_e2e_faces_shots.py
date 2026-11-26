"""Close-ups of every face kind (#4), for the owner's look: saved, never asserted. Run by the faces-shots workflow, not the suite."""
import os
from pathlib import Path

import pytest
from test_e2e_hd_sun import hd

OUT = Path(os.environ.get("FACES_OUT", "faces"))
pytestmark = pytest.mark.skipif(not os.environ.get("FACES_OUT"), reason="close-ups for the owner's look: FACES_OUT=<folder>")


def shot(g, name, x, y, z, w=360, h=260):
    """The picture round (x, y, z), w x h CSS px, at the page's own px."""
    OUT.mkdir(parents=True, exist_ok=True)
    p = g.js(f"HdLook.screenOf({x} + .5, {y} + .5, {z})")
    g.page.screenshot(path=str(OUT / f"{name}.png"), clip={"x": max(0, p[0] - w / 2), "y": max(0, p[1] - h / 2), "width": w, "height": h})


def scene(g, rows, levels, roofs=None, heads=None):
    g.stamp(-8, -8, rows, levels=levels, roofs=roofs or [], heads=heads or [])
    g.rest()


@pytest.mark.parametrize("hill", ["earth3", "stone7"])
def test_faces_shots(browser, server, hill):
    g = hd(browser, server)
    g.js("setOpt('names', false); setOpt('hints', false); setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    g.hour(.3, still=True)
    lv = "3" if hill == "earth3" else "7"
    x, y = g.pos()
    # a hill, a stepped edge on its south side (tops, fronts, a riser), and a room dug under it (the cut, its section, its first line)
    rows = ["." * 17] * 17
    levels = [(lv * 17 if j < 12 else "".join(str(max(0, int(lv) - (j - 11))) for _ in range(17))) for j in range(17)]
    scene(g, rows, levels)
    shot(g, f"{hill}-tops-fronts", x, y + 3, int(lv) - 1)
    room = [[x + i, y + j] for j in range(-2, 2) for i in range(-2, 3)]
    g.rpc("dev_col", tiles=room, col=[int(lv) - 4, int(lv) - 2, int(lv)])
    g.rest()
    g.rpc("dev_teleport", x=x, y=y, z=int(lv) - 4)
    g.arrive()
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=10000)
    g.rest()
    g.frames(8)
    shot(g, f"{hill}-cut-section", x, y - 2, int(lv) - 2, 420, 320)
    shot(g, f"{hill}-under-floor", x, y, int(lv) - 4)
    g.page.close()
