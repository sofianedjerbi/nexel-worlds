"""Close-ups of every face kind (#4), for the owner's look: saved, never asserted. Run by the faces-shots workflow, not the suite."""
import base64
import os
from pathlib import Path

import pytest
from test_e2e_hd_sun import hd

OUT = Path(os.environ.get("FACES_OUT", "faces"))
pytestmark = pytest.mark.skipif(not os.environ.get("FACES_OUT"), reason="close-ups for the owner's look: FACES_OUT=<folder>")


# the land's own picture (#hd: an art px a px, under the HUD's canvas) round (x, y, z), w x h art px, as a PNG
CROP = """([x, y, z, w, h]) => { const a = HdLook.screenOf(x + .5, y + .5, z), u = artPx(), src = document.getElementById('hd'), c = document.createElement('canvas');
  c.width = w; c.height = h; c.getContext('2d').drawImage(src, Math.round(a[0] / u - w / 2), Math.round(a[1] / u - h / 2), w, h, 0, 0, w, h); return c.toDataURL('image/png'); }"""


def shot(g, name, x, y, z, w=140, h=100):
    """The land round (x, y, z), w x h art px, from its own canvas: nothing of the HUD over it."""
    OUT.mkdir(parents=True, exist_ok=True)
    url = g.js(CROP, [x, y, z, w, h])
    (OUT / f"{name}.png").write_bytes(base64.b64decode(url.split(",", 1)[1]))


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
    g.rpc("dev_teleport", x=x, y=y + 1, z=int(lv))
    g.arrive()
    g.rest()
    g.frames(6)
    shot(g, f"{hill}-tops-fronts", x, y + 4, int(lv) - 2, 160, 110)        # (the hill's top, then its south edge stepping down: tops, fronts, risers)
    room = [[x + i, y + j] for j in range(-2, 2) for i in range(-2, 3)]
    g.rpc("dev_col", tiles=room, col=[int(lv) - 4, int(lv) - 2, int(lv)])
    g.rest()
    g.rpc("dev_teleport", x=x, y=y, z=int(lv) - 4)
    g.arrive()
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=10000)
    g.rest()
    g.frames(8)
    shot(g, f"{hill}-cut-section", x, y - 2, int(lv) - 2, 160, 120)
    shot(g, f"{hill}-under-floor", x, y, int(lv) - 4)
    g.page.close()
