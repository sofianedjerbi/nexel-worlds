"""A hill's tunnel in the HD look (hd.js: the eye's pitch over land south of you, hd_level.js clear; the lift of a body in a
hole, hd_level.js lift): walking in and out of it, the eye's pitch goes one way and your body does not jump."""

from test_e2e_hd_behind import calm, go
from test_e2e_hd_sun import hd


# every frame drawn: the eye's pitch and the top of your sprite on the screen (hd.js; HdLook.art().body)
LOG = """(() => { window.__fr = []; const f = () => { if (!window.__fr) return; const a = HdLook.art(), b = a && a.body; window.__fr.push([HdLook.cam.pitch, b ? b.y : null]); requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
LOGGED = "(() => { const l = window.__fr; window.__fr = null; return l.filter((r) => r[1] !== null); })()"


def test_in_and_out_of_a_tunnel_under_a_hill_the_eye_and_your_body_do_not_jump(browser, server):
    """("When I go under a mountain the sprite stays up and glitches.") A hill eight high south of a meadow, a tunnel
    into it from the meadow. Walking south into it the eye was over the hill (78 degrees, hd_level.js clear); under its
    roof the surface's pitch went to 36 while the tilt from above had just begun: the eye fell to 49 and came back to 78,
    the land swinging. Walking out north, the eye's tilt held 300 ms after the roof: you were drawn lifted onto the
    hill's face as in a hole (hd_level.js lift), 57 px up, then dropped back. Now: the pitch goes one way, your body
    stays where you walk."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    hill = [[x + i, y + j] for j in range(2, 10) for i in range(-4, 5)]
    g.rpc("dev_col", tiles=hill, col=[8])
    g.rpc("dev_col", tiles=[[x, y + j] for j in range(2, 10)], col=[0, 2, 8])
    g.rest()
    try:
        go(g, x, y - 2)                                                    # on the meadow north of the hill
        g.js(LOG)
        g.hold(["s"], 1000)                                                # into the tunnel
        g.sleep(700)
        fr = g.js(LOGGED)
        p = [r[0] for r in fr]
        k = next(i for i, v in enumerate(p) if v > 70)                     # (over the hill: the eye looks down over it)
        assert min(p[k:]) > 70, [round(v) for v in p]                      # never back to the surface's on the way in (it was 49)
        go(g, x, y + 5, 0)                                                 # in the tunnel
        g.js(LOG)
        g.hold(["w"], 1000)                                                # out
        g.sleep(700)
        ys = [r[1] for r in g.js(LOGGED)]
        jumps = [abs(b - a) for a, b in zip(ys, ys[1:])]
        assert max(jumps) < 20, ys                                          # (a step's bob is 3 to 9 px: it was 43 up, then 43 down)
    finally:
        g.rpc("dev_col", tiles=hill, col=[0])
