"""Part of the world gone: the land on the screen not drawn, the backdrop's flat colours in its place ("sometimes part of the
world disappears", rare). Each frame drawn, the blocks of the land the picture is made of (HdLook.box) that the page has not
got: one missing for long is a hole on the screen, a strip a block wide at the side you go to.

Cause found (state.js): land far off (HdLook.far, to the horizon) is asked for four blocks a tenth of a second; the server
answers "later" when it has not made it yet (views.py far_ready), and the page asked for that block again 3 s on. The land
on the screen waited those 3 s too: running toward new land, or zooming out, a block came into the picture asked for as far
land a moment before, and was not asked for again. Seen: 5400 px of a 600 x 400 picture, the side of the screen for 2.5 s."""

import os

import pytest
from game import Game, new_name

pytestmark = pytest.mark.realtime                 # (it times how long a block is missing, in ms of the page's own clock)

# each drawn frame, the blocks of the land box not there (of its part the page asks for as land on the screen, viewRect: the box's north
# rows past it are far land only, a question of how far the land goes, not this one): how long each has been missing (worst: the longest, the hole on the
# screen: the server's making of new land is in it, a second on a busy machine), and how long each has been missing with no
# ask for it as land on the screen out (unasked: the page's own share; it was the 3 s a far ask kept it from being asked for)
HUNT = """() => { const fresh = !window.__holes, H = window.__holes = {frames: 0, worst: 0, unasked: 0, at: null, since: new Map(), un: new Map(), near: window.__holes ? window.__holes.near : new Map()}; if (!fresh) return 1;
  const s0 = spec.send.bind(spec); spec.send = (d) => { const m = JSON.parse(d); if (m.op === 'region' && !m.far) window.__holes.near.set(bkey(Math.floor(m.x / B), Math.floor(m.y / B)), performance.now()); return s0(d); };
  const f0 = frame; frame = function (now) { f0(now); const H = window.__holes; if (!HdLook.live || HdLook.held || !HdLook.box) return; H.frames++; const L = HdLook.box, v = viewRect(6), b = [Math.max(L[0], v[0]), Math.max(L[1], v[1]), Math.min(L[2], v[0] + v[2]), Math.min(L[3], v[1] + v[3] + 6)], t = performance.now(), here = new Set(), un = new Set();
    for (let by = Math.floor(b[1] / B); by <= Math.floor(b[3] / B); by++) for (let bx = Math.floor(b[0] / B); bx <= Math.floor(b[2] / B); bx++) { const k = bkey(bx, by); if (blocks.get(k)) continue;
      here.add(k); if (!H.since.has(k)) H.since.set(k, t); const ms = t - H.since.get(k); if (ms > H.worst) { H.worst = ms; H.at = [k, zoom, requested.get(k)]; }
      if (!(t - H.near.get(k) < 3000)) { un.add(k); if (!H.un.has(k)) H.un.set(k, t); H.unasked = Math.max(H.unasked, t - H.un.get(k)); } }
    for (const k of [...H.since.keys()]) if (!here.has(k)) H.since.delete(k); for (const k of [...H.un.keys()]) if (!un.has(k)) H.un.delete(k); };
  return 1; }"""


def test_land_you_come_to_is_asked_for_at_once_though_it_was_asked_for_as_far_land(browser, server):
    """Woken on land nobody has been to (the server makes it as it is asked for), then zoomed out at once: the blocks that
    come into the picture were asked for a moment before as far land, answered "later". Each is asked for again as land on
    the screen at once (within the page's tenth of a second): before, missing and not asked for 2 to 3 s."""
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    try:
        g = Game(page, server)
        g.join(new_name(), 4)
        g.js(HUNT)                                       # (the page's asks watched from before it is taken away: what it asks on arriving counts)
        x0 = 6000 + (os.getpid() % 997) * 160            # (land no test of this server has made: one place a worker)
        for n, (dx, dy) in enumerate(((0, 0), (0, 160), (160, 0))):
            g.rpc("dev_teleport", x=x0 + dx, y=-x0 + dy)
            g.wait("HdLook.live && !HdLook.held", 15000)
            g.js(HUNT)
            g.page.wait_for_timeout(400)                  # (the far land asked for meanwhile, four blocks a tenth of a second)
            g.page.keyboard.press("Minus")
            g.page.wait_for_timeout(200)
            g.page.keyboard.press("Minus")                # (4 -> 2: the picture twice as wide)
            g.page.wait_for_timeout(3500)
            h = g.js("(() => { const H = window.__holes; return {frames: H.frames, worst: Math.round(H.worst), unasked: Math.round(H.unasked), at: H.at}; })()")
            assert g.js("zoom") == 2, g.js("zoom")
            assert h["frames"] > 30, h
            assert h["unasked"] < 2000, (n, h)           # (a block of the picture's land missing and not asked for: state.js asks ten times a second, mostly there in 0.1 s, at worst 1.3 s seen on a busy machine; not the 3 s of a far ask: 2.86 to 3.12 s before, four runs)
            g.page.keyboard.press("Equal")
            g.page.keyboard.press("Equal")
            g.page.wait_for_timeout(400)
        assert not g.errors
    finally:
        page.close()
