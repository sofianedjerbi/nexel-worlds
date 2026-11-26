"""The HD look's paint sheet full (vox_style.js slot): a paint asked outside a land's making (a ghost, a moving shadow,
the window's section) gets a place of its own, never one the land shown uses nor the one another such paint has."""

import pytest

from test_e2e_hd_sun import hd, settled

pytestmark = pytest.mark.e2e

# fill the shown land's sheet: paints asked as a ghost asks them, between two frames, till it has no place left
FILL = """(() => { const solid = (px, at, st) => { for (let j = 0; j < 16; j++) px.fill(0xff0000ff, at + j * st, at + j * st + 16); }; let i = 0;
  for (; i < 5000; i++) { const q = HdLook.paints; if (q.n >= q.cap && !q.free) break; q.slot('test fill ' + i, solid); }
  const q = HdLook.paints; return [i, q.n, q.cap, q.free, HdLook.work.overs]; })()"""
# ...and on a later frame two more: [their places, the last place, are they the land's, the sheet's overflows they made, lands made from none]
MORE = """(() => { const q = HdLook.paints, solid = (px, at, st) => { for (let j = 0; j < 16; j++) px.fill(0xff00ff00, at + j * st, at + j * st + 16); };
  const o = HdLook.work.overs, a = q.slot('test ghost a', solid), b = q.slot('test ghost b', solid); return [a, b, q.cap, q.shown(a), q.shown(b), HdLook.work.overs - o, HdLook.work.wipes]; })()"""
# your shadow under you: the px round your feet of the colour under you
SHADOW = """(() => { const p = myPos(), a = HdLook.screenOf(p.x + .5, p.y + .92, topAt(p.x, p.y)), k = devicePixelRatio, X = Math.round(a[0] * k), Y = Math.round(a[1] * k);
  window.__mid = window.__mid || HdLook.read(X, Y, 1, 1).data; const mid = window.__mid, d = HdLook.read(X - 24 * k, Y - 9 * k, 48 * k, 18 * k).data; let n = 0;
  for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - mid[0]) + Math.abs(d[i + 1] - mid[1]) + Math.abs(d[i + 2] - mid[2]) < 12) n++; return n; })()"""


def test_a_paint_asked_while_the_sheet_is_full_gets_a_place_of_its_own(browser, server):
    """The shown land's sheet full (all its 4095 places given, none free) and two paints asked outside a land's making,
    on a frame after: two places, not the last one, not the land's. (They all took the last place: every such paint
    drew the paint of the last one to ask, your shadow a block of another's paint, dark over you till the land was made
    again from none: hd_sun's shadow lost all its px, #106.) All of it between frames, at the page's own pace: the same
    at 16 ms a frame as at 200."""
    g = hd(browser, server)
    try:
        g.hour(.9)                                           # (night: the shadow under you alone, no cloud, no sun)
        g.wait("Math.abs((clock.phase || 0) - .9) < .02")
        settled(g)
        before = g.js(SHADOW)
        n, used, cap, free, _ = g.js(FILL)
        assert used >= cap and free == 0 and n < 5000, (n, used, cap, free)
        g.frames(2)
        a, b, last, sa, sb, overs, wipes0 = g.js(MORE)
        assert a != b and last not in (a, b) and not sa and not sb, (a, b, last, sa, sb)
        assert overs == 2, overs                             # (both by the full sheet's way)
        g.frames(4)
        assert g.js("HdLook.work.wipes") == wipes0, "the land was made again from none"
        after = g.js(SHADOW)
        assert before > 60 and abs(after - before) <= 4, (before, after)
    finally:
        g.page.close()
