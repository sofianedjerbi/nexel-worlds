"""Down into water from a height in the HD look (body_place.js: the landing's lift, leap.js lift, kept for a swimmer;
swim.js drawSwimmer)."""

import pytest

from test_e2e_hd_behind import calm
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# every frame drawn while you go down: the top of your sprite on the screen (HdLook.art().body) and how you are drawn (BodyPlace mode)
LOG = """(() => { window.__fr = []; const f = () => { if (!window.__fr) return; const a = HdLook.art(), b = a && a.body, q = ents.get('agent' + myId); if (b && q) window.__fr.push([b.y, BodyPlace.of(q).mode]); requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
LOGGED = "(() => { const l = window.__fr; window.__fr = null; return l; })()"


@pytest.mark.realtime
def test_off_a_high_ledge_into_water_your_body_does_not_jump_up_the_screen(browser, server):
    """(#24) Off a ledge six high into a pond: the frame you came down in the water your body went 13 px up the screen
    (art y 112 to 99), the eye still a level and a half over the water, coming down. A landing on the ground is drawn
    from the level the eye is coming to (leap.js lift); the swimmer had no jump, so no lift. Now it has: from the last
    frame in the air to the first in the water, the body moves no more than the eye's glide."""
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
    g.js(LOG)
    g.page.keyboard.down("d")
    try:
        g.wait("(() => { const q = ents.get('agent' + myId); return q && BodyPlace.of(q).mode === 'swim'; })()", 4000)
    finally:
        g.page.keyboard.up("d")
    g.frames(3)
    fr = g.js(LOGGED)
    k = next(i for i, r in enumerate(fr) if r[1] == "swim")
    assert k > 0, fr
    up = fr[k - 1][0] - fr[k][0]                                             # px up the screen, into the water
    assert abs(up) < 6, fr[max(0, k - 5):k + 3]                              # (it was 13 up)
    g.rest()
    assert g.server()["swimming"] and not g.errors, g.errors
