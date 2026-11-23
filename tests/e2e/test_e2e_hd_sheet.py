"""The HD look's sheet of paints on a desk (vox_style_glsl.js AW, vox_style.js slot): sprinting about a desk's big
screen, every face is drawn with its own paint. The owner, sprinting up the spawn hill on a desk: "all textures are
fucked up": grass tops drawn as stone, stone fronts as grass, rows of the same tuft. The land asked for more than the
sheet's 4096 paints: the sheet was emptied and made again from none over and over (spills), a paint was put in a place
the land shown still named (overs), and faces were drawn with other paints. A sheet of 16384 on a screen of more than a
million CSS px: none of that, and the land made again from none is the land as it was, px for px."""

import pytest

from conftest import Game, new_name

# the share of the land's px that differ between the picture as it is and as it was (window.__was)
DIFF = """(() => { const a = window.__was, b = HdLook.read(0, 0, cv.width, cv.height).data; let n = 0;
  for (let i = 0; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 24) n++; return n / (a.length / 4); })()"""


@pytest.mark.realtime
def test_sprinting_about_on_a_desk_every_face_keeps_its_own_paint(browser, server):
    g = Game(browser.new_page(viewport={"width": 1920, "height": 1080}), server)
    g.join(new_name(), 3)
    g.js("setOpt('names', false); setOpt('hints', false); setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    g.rpc("dev_creatures", clear=60)
    g.hour(.3, still=True)
    g.rest()
    for key in ("d", "w", "a", "s"):                              # (a run each way: new land comes in at every step)
        g.hold(["Shift", key], 2500)
        g.rest()
    w = g.js("HdLook.work")
    assert w["spills"] == 0 and w["overs"] == 0 and w["wipes"] == 0, w
    assert g.js("HdLook.raw()") == 0                               # (no px from an empty paint)
    g.rpc("dev_creatures", clear=60)
    g.rest()
    g.js("(() => { window.__was = HdLook.read(0, 0, cv.width, cv.height).data; return 1; })()")
    g.js("HdLook.forget()")                                        # the land made again, its paints from none
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    g.frames(3)
    d = g.js(DIFF)
    assert d < .01, d                                             # the same land, px for px (a face drawn with another paint: a tile's worth of px each)
    assert not g.errors
