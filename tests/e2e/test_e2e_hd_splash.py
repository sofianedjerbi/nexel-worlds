"""Down into water from a height in the HD look (body_place.js: the landing's lift, leap.js lift, kept for a swimmer;
swim.js drawSwimmer)."""

import pytest

from test_e2e_hd_behind import calm
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# every frame drawn while you go down: the top of your body's own px on the screen, in art px (HdLook.art().body / u), how it is drawn (BodyPlace mode, up),
# the landing's lift (levels), the body's height (art px), the leap (L: in the air, G: the eye gliding after it), the row (tiles), the frame's time (ms),
# BodyPlace's [line, z, the jump's body, ground, pose], a fixed place of the pond's row (art px: the landing's shake moves it and you alike)
LOG = """(() => { window.__fr = []; const f = () => { if (!window.__fr) return; const a = HdLook.art(), b = a && a.body, q = ents.get('agent' + myId); if (b && q) { const pl = BodyPlace.of(q); window.__fr.push([Math.round(b.y / a.u * 10) / 10, pl.mode, pl.up, Math.round(Leap.lift(q) * 100) / 100, Math.round(b.h / a.u), Leap.on() ? 'L' : Leap.gliding() ? 'G' : '', Math.round(q.y * 100) / 100, Math.round(performance.now()), (() => { const pl = BodyPlace.of(q), j = pl.jump; return [pl.line, Math.round((pl.z || 0) * 100) / 100, j ? Math.round(j.body * 10) / 10 : null, j ? Math.round(j.ground * 10) / 10 : null, j ? j.pose : null]; })(), (() => { const r = window.__ref, w = r && HdLook.screenOf(r[0], r[1], 0); return w ? Math.round(w[1] / a.u * 10) / 10 : null; })()]); } requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
LOGGED = "(() => { const l = window.__fr; window.__fr = null; return l; })()"


@pytest.mark.realtime
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
    g.js(f"(() => {{ window.__ref = [{x + 3.5}, {y + .5}]; return 1; }})()")   # (a fixed place of the pond: its row on the screen each frame, r[8])
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
    # Against the pond (r[8]): a fall of six into water hurts (sim/movement.py fell), and the landing's shake moves the whole
    # picture, the pond and you alike, up to 10 px a frame (render.js fallShake): that is the game's own, not a jolt of yours)
    cap = lambda a, b: 6 * max(1, (b[7] - a[7]) / 16.67)
    rel = lambda r: r[0] - r[9]
    assert k < 2 or rel(fr[k]) - rel(fr[k - 1]) <= rel(fr[k - 1]) - rel(fr[k - 2]) + cap(fr[k - 1], fr[k]), str(fr[max(0, k - 4):k + 4])   # (into the water no faster than the fall's own last step: it sank 5 px at once, #193)
    jolts = [(a, b) for a, b in zip(fr[k:], fr[k + 1:]) if abs(rel(b) - rel(a)) > cap(a, b)]
    assert not jolts, str(jolts[:4])
    g.rest()
    assert g.server()["swimming"] and not g.errors, g.errors
