"""The HD look's paint sheet full (vox_style.js slot): a paint asked outside a land's making (a ghost, a moving shadow,
the window's section) gets a place of its own, never one the land shown uses, nor one the land being made has, nor the one
another such paint has."""

import pytest

from test_e2e_hd_sun import hd, settled

pytestmark = pytest.mark.e2e

# fill the shown land's sheet: paints asked as a ghost asks them, between two frames, till it has no place left
FILL = """((left) => { const solid = (px, at, st) => { for (let j = 0; j < 16; j++) px.fill(0xff0000ff, at + j * st, at + j * st + 16); }; const end = HdLook.paints.cap + 1; let i = 0;
  for (; i < end; i++) { const q = HdLook.paints; if (q.n >= q.cap - left && !q.free) break; q.slot('test fill ' + i, solid); }
  const q = HdLook.paints; return [i, end, q.n, q.cap, q.free]; })(%d)"""
# ...and on a later frame two more: [their places, the last place, are they the land's, the sheet's overflows they made, lands made from none]
MORE = """(() => { const q = HdLook.paints, solid = (px, at, st) => { for (let j = 0; j < 16; j++) px.fill(0xff00ff00, at + j * st, at + j * st + 16); };
  const o = HdLook.work.overs, a = q.slot('test ghost a', solid), b = q.slot('test ghost b', solid); return [a, b, q.cap, q.shown(a), q.shown(b), HdLook.work.overs - o, HdLook.work.wipes]; })()"""
# your shadow under you: the px round your feet of the colour under you
SHADOW = """(() => { const p = myPos(), a = HdLook.screenOf(p.x + .5, p.y + .92, topAt(p.x, p.y)), k = devicePixelRatio, X = Math.round(a[0] * k), Y = Math.round(a[1] * k);
  window.__mid = window.__mid || HdLook.read(X, Y, 1, 1).data; const mid = window.__mid, d = HdLook.read(X - 24 * k, Y - 9 * k, 48 * k, 18 * k).data; let n = 0;
  for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - mid[0]) + Math.abs(d[i + 1] - mid[1]) + Math.abs(d[i + 2] - mid[2]) < 12) n++; return n; })()"""


def test_a_paint_asked_while_the_sheet_is_full_gets_a_place_of_its_own(browser, server):
    """The shown land's sheet full (all its places given, none free) and two paints asked outside a land's making,
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
        n, end, used, cap, free = g.js(FILL % 0)       # (each new paint takes a place: cap + 1 asks fill it whatever the land holds)
        assert used >= cap and free == 0 and n < end, (n, end, used, cap, free)
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


# the land being made, held (HdLook.hold = 0), stepped by the test (HdLook.step) till it has a paint of its own (B, vox_style.js): [has it, the steps]
TILL_ITS_OWN = """(() => { let n = 0; while (!HdLook.paints.making && HdLook.step()) n++; return [HdLook.paints.making, n]; })()"""
# two paints asked as a ghost asks them, between two of its steps: [their places, are they the shown land's or the one being made's, the sheet's overflows they made]
GHOSTS = """(() => { const q = HdLook.paints, solid = (px, at, st) => { for (let j = 0; j < 16; j++) px.fill(0xff00ff00, at + j * st, at + j * st + 16); };
  const o = HdLook.work.overs, a = q.slot('test ghost c', solid), b = q.slot('test ghost d', solid); return [a, b, q.cap, q.held(a), q.held(b), HdLook.work.overs - o]; })()"""


def test_a_paint_asked_while_a_land_is_made_and_the_sheet_full_is_not_that_land_s(browser, server):
    """A land being made over frames has a copy of the sheet's paints (B: the shown ones', A's, and its own new ones),
    and only its new ones are sent to the GPU when it is shown. A paint asked outside the making while the shown sheet
    is full took a place of A's that the land being made still held: the GPU had the ghost's px there, the land drew its
    face with them once shown. Here the making is held (HdLook.hold) and stepped by the test (HdLook.step) in one call
    till it has a paint of its own, the shown sheet is then filled, and two paints are asked: their places are neither
    land's. All of it by the steps of the making and the sheet's state: the same at 16 ms a frame as at 200."""
    g = hd(browser, server)
    try:
        settled(g)
        g.js(FILL % 300)                                     # (all but 300: the land to be made has room for its new paints)
        g.js("HdLook.hold = 0")                              # (the next land is made only as the test steps it)
        g.stamp(-12, -6, ["M" + "." * 11 + "M" + "." * 11 + "M"])
        g.wait("HdLook.busy")
        own, steps = g.js(TILL_ITS_OWN)                      # (in one call: no frame between its steps)
        assert own, f"the land was made in {steps} steps with no paint of its own"
        n, end, used, cap, free = g.js(FILL % 0)              # (now the shown sheet full, as a ghost would fill it)
        assert used >= cap and free == 0 and n < end, (n, end, used, cap, free)
        g.frames(2)                                          # (asked on a frame of their own: the fill asked for every place it has)
        assert g.js("HdLook.paints.making && HdLook.busy"), "the making went on while held"
        a, b, last, ha, hb, overs = g.js(GHOSTS)
        assert overs == 2, overs                             # (both by the full sheet's way)
        assert a != b and last not in (a, b) and not ha and not hb, (a, b, last, ha, hb)
        wipes = g.js("HdLook.work.wipes")
        g.js("HdLook.hold = null")
        g.wait("!HdLook.busy")
        assert g.js("HdLook.work.wipes") == wipes, "the land was made again from none"
    finally:
        g.js("HdLook.hold = null")
        g.page.close()
