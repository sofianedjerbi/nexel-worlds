"""Down into water from a height in the HD look (body_place.js: the landing's lift, leap.js lift, kept for a swimmer;
swim.js drawSwimmer)."""

import pytest

from test_e2e_hd_behind import calm
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# every frame drawn while you go down: the top of your body's own px on the screen, in art px (HdLook.art().body / u), how it is drawn (BodyPlace mode, up),
# the landing's lift (levels), the body's height (art px), the leap (L: in the air, G: the eye gliding after it), the row (tiles), the frame's time (ms),
# your feet's place (art px: where the HD look stands your body, hd_stands.js, less BodyPlace's up: what a pose does not move), a fixed place of the pond's row (art px: the landing's shake moves it and you alike)
LOG = """(() => { window.__fr = []; const f = () => { if (!window.__fr) return; const a = HdLook.art(), b = a && a.body, q = ents.get('agent' + myId); if (b && q) { const pl = BodyPlace.of(q); window.__fr.push([Math.round(b.y / a.u * 10) / 10, pl.mode, pl.up, Math.round(Leap.lift(q) * 100) / 100, Math.round(b.h / a.u), Leap.on() ? 'L' : Leap.gliding() ? 'G' : '', Math.round(q.y * 100) / 100, Math.round(performance.now()), (() => { const P = HdLevel.place, w = P && HdLook.screenOf(q.x + .5, q.y + .5, P.Lf); return w ? Math.round((w[1] / a.u - pl.up) * 10) / 10 : null; })(), (() => { const r = window.__ref, w = r && HdLook.screenOf(r[0], r[1], 0); return w ? Math.round(w[1] / a.u * 10) / 10 : null; })()]); } requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
LOGGED = "(() => { const l = window.__fr; window.__fr = null; return l; })()"


@pytest.mark.stepped
def test_off_a_high_ledge_into_water_your_body_does_not_jump_up_the_screen(browser, server):
    """(#24) Off a ledge six high into a pond: the frame you came down in the water your body went 13 px up the screen
    (art y 112 to 99), the eye still a level and a half over the water, coming down. A landing on the ground is drawn
    from the level the eye is coming to (leap.js lift); the swimmer had no jump, so no lift. Now it has: it goes into the
    water, under it, and comes up as the eye comes down to it, never up the screen at once."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.stamp(-3, -1, ["...."] * 3, levels=["6666"] * 3)                      # the ledge, you on its east end
    g.stamp(1, -1, ["~~~~~"] * 3)                                            # the pond under it
    g.rpc("dev_teleport", x=x, y=y, z=6)
    g.arrive()
    g.face(1, 0)
    g.wait("!HdLook.busy", timeout=8000)
    g.rest()
    g.js(f"(() => {{ window.__ref = [{x + 3.5}, {y + .5}]; return 1; }})()")   # (a fixed place of the pond: its row on the screen each frame, r[9])
    g.js(LOG)
    g.page.keyboard.down("d")
    try:
        g.wait("(() => { const q = ents.get('agent' + myId); return q && BodyPlace.of(q).mode === 'swim'; })()", 4000)
    finally:
        g.page.keyboard.up("d")
    g.wait("(() => { const q = ents.get('agent' + myId); return q && !Leap.lift(q); })()", 4000)       # (the eye down at the water)
    g.frames(8)
    fr = g.js(LOGGED)
    k = next(i for i, r in enumerate(fr) if r[1] == "swim")
    assert k > 0, fr
    assert fr[k][0] - fr[k - 1][0] > -3, str(fr[max(0, k - 4):k + 4])      # into the water it never goes up the screen (it was 13 px up)
    # (and then, in the water, going under and coming up as the eye comes down to it, no frame moves it more than the land
    # may move after a landing on the ground: 6 art px in a 60th of a second, by the frame's own time: test_e2e_leap_terrain.
    # From the first frame in the water: the frame before is the end of a fall of six, faster than that, and checked above.
    # Against the pond (r[9]): a fall of six into water hurts (sim/movement.py fell), and the landing's shake moves the whole
    # picture, the pond and you alike, up to 10 px a frame (render.js fallShake): that is the game's own, not a jolt of yours)
    cap = lambda a, b: 6 * max(1, (b[7] - a[7]) / 16.67)
    rel, foot, pose = (lambda r: r[0] - r[9]), (lambda r: r[8] - r[9]), (lambda r: r[0] - r[8])
    # (stepped: every frame a 60th of a second of the page's time, whatever the machine draws it in, clock.py STEP: the same
    # frames on a runner at 200 ms a frame as at 16. Your feet go into the water at the fall's own step, a px or two of
    # rounding aside: the jump's place and the swimmer's are one, BodyPlace up. Then the picture changes over them, the
    # fall's pose to the swimmer's, as far as the swimmer sinks under the water's face and a stroke's bob, a frame: swim.js
    # SWIM.sink, #193)
    assert k < 2 or -3 < foot(fr[k]) - foot(fr[k - 1]) <= foot(fr[k - 1]) - foot(fr[k - 2]) + 3, str(fr[max(0, k - 4):k + 4])
    sink = g.js("SWIM.sink") + 1
    poses = [(a, b) for a, b in zip(fr[k - 1:], fr[k:]) if abs(pose(b) - pose(a)) > sink]
    assert not poses, str(poses[:4])
    jolts = [(a, b) for a, b in zip(fr[k:], fr[k + 1:]) if max(abs(rel(b) - rel(a)), abs(foot(b) - foot(a))) > cap(a, b)]
    assert not jolts, str(jolts[:4])
    g.rest()
    assert g.server()["swimming"] and not g.errors, g.errors


# every frame drawn: how you are drawn (BodyPlace mode), how far over your line (art px: below it, < 0), and how many of
# your own px are on your picture's last row (its canvas, HdLook.art sprite: there is a tile of rows under your foot,
# so a body that reaches that row is a body cut by it), your place
EDGE = """(() => { window.__cut = []; const f = () => { if (!window.__cut) return; const a = HdLook.art(), c = a && a.sprite, q = ents.get('agent' + myId);
  if (c && q) { const d = c.getContext('2d').getImageData(0, c.height - 1, c.width, 1).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 127) n++;
    const pl = BodyPlace.of(q); window.__cut.push([pl.mode, pl.up, n, Math.round(q.x * 100) / 100, c.height]); }
  requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
EDGED = "(() => { const l = window.__cut; window.__cut = null; return l; })()"


@pytest.mark.stepped
def test_off_a_ledge_into_a_pond_your_legs_are_drawn_all_the_way_down(browser, server):
    """(#355) Off a ledge nine high into a pond, coming down, your legs went: the eye still high, you are drawn from the
    level it is coming to (body_place.js up < 0: down to 20 art px under your line), and your picture's canvas had no
    rows under your foot for that: the legs past its bottom were cut, in the air over the water, the bank behind you.
    Now the canvas has as many rows under your foot as you are drawn under it (hd.js ent): no frame cuts you."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.stamp(-3, -1, ["...."] * 3, levels=["9999"] * 3)                      # the ledge, you on its east end
    g.stamp(1, -1, ["~~~~~"] * 3)                                            # the pond under it
    g.rpc("dev_teleport", x=x, y=y, z=9)
    g.arrive()
    g.face(1, 0)
    g.wait("!HdLook.busy", timeout=8000)
    g.rest()
    g.js(EDGE)
    g.page.keyboard.down("d")
    try:
        g.wait("(() => { const q = ents.get('agent' + myId); return q && BodyPlace.of(q).mode === 'swim'; })()", 4000)
    finally:
        g.page.keyboard.up("d")
    g.wait("(() => { const q = ents.get('agent' + myId); return q && !Leap.lift(q); })()", 4000)       # (the eye down at the water)
    g.frames(2)
    fr = g.js(EDGED)
    low = [r for r in fr if r[1] <= -16]
    assert low and {r[0] for r in low} >= {"jump"}, str(fr)               # (drawn a tile and more under your line, in the air: what cut you)
    cut = [r for r in fr if r[2]]
    assert not cut, str(cut)                                               # nothing of you on your picture's last row, jumping or swimming
