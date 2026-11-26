"""A hill's tunnel in the HD look (hd.js: the eye's pitch over land south of you, hd_level.js clear; the lift of a body in a
hole, hd_level.js lift): walking in and out of it, the eye's pitch goes one way and your body does not jump."""

from test_e2e_hd_behind import calm, go
from test_e2e_hd_sun import hd


# every frame drawn: the eye's pitch and the top of your sprite on the screen (hd.js; HdLook.art().body)
LOG = """(() => { window.__fr = []; const f = () => { if (!window.__fr) return; const a = HdLook.art(), b = a && a.body; window.__fr.push([HdLook.cam.pitch, b ? b.y : null]); requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
LOGGED = "(() => { const l = window.__fr; window.__fr = null; return l.filter((r) => r[1] !== null); })()"


def test_in_and_out_of_a_tunnel_under_a_hill_the_eye_and_your_body_do_not_jump(browser, server):
    """("When I go under a mountain the sprite stays up and glitches.") A hill eight high south of a meadow, a tunnel
    into it from the meadow. Walking south into it the eye was over the hill (78 degrees then, 58 now: hd.js STEEP, hd_level.js clear); under its
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
        # (each walk held till you are there and the eye has come to rest, not 1 s held and 0.7 s: a runner's walk of 1 s
        # was short of the tunnel, #47)
        g.page.keyboard.down("s")                                          # into the tunnel
        g.wait(f"myPos().y >= {y + 3}", timeout=8000)
        g.page.keyboard.up("s")
        g.rest()
        fr = g.js(LOGGED)
        p = [r[0] for r in fr]
        top = g.js("HdLook.steep") - 1                                     # (the steepest the eye looks down, hd.js STEEP: 58; it was 78)
        k = next(i for i, v in enumerate(p) if v > top)                    # (over the hill: the eye looks down over it)
        assert min(p[k:]) > top, [round(v) for v in p]                     # never back to the surface's on the way in (it was 49)
        go(g, x, y + 5, 0)                                                 # in the tunnel
        g.js(LOG)
        g.page.keyboard.down("w")                                          # out
        g.wait(f"myPos().y <= {y + 1}", timeout=8000)
        g.page.keyboard.up("w")
        g.rest()
        ys = [r[1] for r in g.js(LOGGED)]
        jumps = [abs(b - a) for a, b in zip(ys, ys[1:])]
        assert max(jumps) < 20, ys                                          # (a step's bob is 3 to 9 px: it was 43 up, then 43 down)
    finally:
        g.rpc("dev_col", tiles=hill, col=[0])


# how dark the picture is at a place of the world: the light of its px (0..255)
LUM = """([x, y, z]) => { const a = HdLook.screenOf(x, y, z), k = devicePixelRatio, d = HdLook.read(Math.round(a[0] * k), Math.round(a[1] * k), 1, 1).data; return .3 * d[0] + .59 * d[1] + .11 * d[2]; }"""


def test_in_a_hill_s_tunnel_the_hill_s_face_outside_is_stone_not_black(browser, server):
    """(The owner: "a big black stepped region where the cliff should be".) In a tunnel the walls within six tiles of
    you went dark by the depth of the land over your floor (vox_style_glsl.js ho, hd_level.js shut), as a shaft's walls
    do: but the hill's own face over the meadow outside is no wall of yours: it was black under its first level, a
    stepped slab round the mouth. Under a roof the hole's dark is not laid: the window tells the depth inside."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    hill = [[x + i, y + j] for j in range(-9, -1) for i in range(-6, 7)]
    g.rpc("dev_col", tiles=hill, col=[8])
    g.rpc("dev_col", tiles=[[x, y + j] for j in range(-9, -1)], col=[0, 2, 8])
    g.rest()
    try:
        go(g, x, y - 4, 0, "HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1")    # in the tunnel, 3 tiles in
        face = [[x + i + .5, y - 1, z + .5] for i in (-4, -3, -2, 2, 3, 4) for z in range(0, 7)]   # the hill's face over the meadow, beside the mouth
        lum = [g.js(LUM, p) for p in face]
        black = [p for p, v in zip(face, lum) if v < 20]
        assert len(black) <= 2, (black, [round(v) for v in lum])        # stone (it was black: 0 to 10, most of it)
    finally:
        g.rpc("dev_col", tiles=hill, col=[0])
