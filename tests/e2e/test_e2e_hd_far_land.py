"""(probe #193: run beside hd_splash) Land coming in at the view distances (hd.js viewOf, state.js viewRect: the land box is the view): teleported onto land nobody has seen,
at each setting, zoomed in and out, the land made tile by tile comes at once and is drawn whole. A file of its own: it
makes land at eight places, and the land the server is then left to keep and put away slowed the next tests' ticks
(test_e2e_hd_sky's sky line, run after it on the same server)."""

import pytest
from test_e2e_hd_far import VIEWS, view
from test_e2e_hd_sun import hd

# every block of the land made tile by tile (HdLook.box) has come
BOXED = """() => { const b = HdLook.box; for (let by = Math.floor(b[1] / B); by <= Math.floor(b[3] / B); by++) for (let bx = Math.floor(b[0] / B); bx <= Math.floor(b[2] / B); bx++) if (!blocks.has(bkey(bx, by))) return false; return true; }"""


# ...those of its rows up to the horizon and some (what can be seen on level ground)
SEENED = """() => { const b = HdLook.box, y0 = myPos().y - HdLook.view.n - 6; for (let by = Math.floor(Math.max(b[1], y0) / B); by <= Math.floor(b[3] / B); by++) for (let bx = Math.floor(b[0] / B); bx <= Math.floor(b[2] / B); bx++) if (!blocks.has(bkey(bx, by))) return false; return true; }"""
# ms (the machine's) from a teleport onto (x, y) to the blocks of the land made tile by tile up to the horizon, and to all of them
COME = """async ([x, y]) => { const t0 = performance.now(); await rpc('dev_teleport', {x, y});
  return await new Promise((ok) => { const f = () => { const p = myPos(), b = HdLook.box, at = p && Math.abs(p.x - x) < 2 && Math.abs(p.y - y) < 2 && b && Math.abs(b[0] + b[2] - 2 * x) < 4;
    if (at && seen < 0 && (""" + SEENED + """)()) seen = performance.now() - t0;
    if ((at && (""" + BOXED + """)()) || performance.now() - t0 > 8000) ok([Math.round(seen < 0 ? 9999 : seen), Math.round(performance.now() - t0)]); else requestAnimationFrame(f); }; let seen = -1; f(); }); }"""


@pytest.mark.realtime                                       # (it times the machine: how soon the land comes)
def test_after_a_sprint_onto_new_land_all_of_it_comes_and_is_painted(browser, server):
    """Onto land nobody has seen, at each view distance and zoomed in and out: every block of the land made tile by tile
    comes within 4 s, up to the horizon within 3.5 (0.2 to 2.8 here; its north rows, past the flat picture's own, were asked for as far land
    only: 3.2 to 6.4 s), and at rest no px of the land is half drawn (HdLook.raw: the farthest water's face stood over
    nothing at the horizon, the sky through it: 300 to 1237 px at Very far, zoomed out)."""
    g = hd(browser, server)
    x, y = g.pos()
    for i, (v, _) in enumerate(VIEWS):
        for j, z in enumerate((2, 4)):
            view(g, v, z)
            tx, ty = x + 600 * (2 * i + j + 1), y - 300                         # land not made yet
            ms, all_ms = g.js(COME, [tx, ty])
            assert ms < 3500 and all_ms < 4000, (v, z, ms, all_ms, g.js("[HdLook.box, [...blocks.keys()]]"))
            g.page.keyboard.down("Shift"); g.page.keyboard.down("w")            # and a sprint north on it
            g.sleep(600)
            g.page.keyboard.up("w"); g.page.keyboard.up("Shift")
            g.page.wait_for_function(BOXED, timeout=1500)
            g.rest()
            assert g.js("HdLook.raw()") == 0 and g.js("HdLook.bare()") == 0, (v, z, g.js("HdLook.raw()"), g.js("HdLook.bare()"), g.js("[HdLook.box, myPos()]"))
    g.js("setOpt('view', OPT_DEFAULT.view); zoom = ZOOM.to = 3")
    # (back home, and all the far land there come: the server's one maker of land is not left with a queue of the
    #  far places' land for the next test's (test_e2e_hd_sky's sky line moved as its far land came late))
    g.rpc("dev_teleport", x=x, y=y)
    g.arrive()
    g.wait(ALLFAR, 30000)


ALLFAR = """() => { const f = HdLook.far; if (!f) return false; for (let by = Math.floor(f[1] / B); by <= Math.floor(f[3] / B); by++) for (let bx = Math.floor(f[0] / B); bx <= Math.floor(f[2] / B); bx++) if (!blocks.has(bkey(bx, by))) return false; return true; }"""
