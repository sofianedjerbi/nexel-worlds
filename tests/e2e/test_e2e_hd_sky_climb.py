"""Climbing a hill, the sky's edge is where the eye's level puts it on every frame (#359). The edge (where the land ahead
ends, the far hills standing on it) was eased a quarter second after its place: up the owner's stone terraces the eye
rose two levels in under a second, the edge a second behind it, and between it and the land a strip of the backdrop's
flat far-land green across the horizon."""

import pytest

from test_e2e_hd_behind import calm
from test_e2e_hd_open_terrace import seed12  # noqa: F401 (the fixture: the owner's world, seed 12)
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# every frame: [the eye's level, the sky's line and edge as drawn (px), where this frame puts them (HdLook.line: art px), zoom]
REC = """() => { window.__sk = []; window.__skOn = true;
  const f = () => { const s = HdLook.sky(0), l = HdLook.line; if (l && s.edge !== undefined) __sk.push([HdLook.level[1], s.line, s.edge, l[1], l[2] === undefined ? s.line / zoom - 2 : l[2], zoom]);
    if (__skOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def test_climbing_a_hill_the_sky_s_edge_is_where_the_eye_puts_it_on_every_frame(browser, seed12):  # noqa: F811
    """Up the news clip's terraces (seed 12, x 13, from -76 to -72, two levels): on every frame the eye's level moved,
    the sky's edge is drawn where that frame puts it, and once you stand, there too (the sky's line keeps its own easing:
    a px a frame at most, test_e2e_hd_sky). Frame by frame, each
    frame against itself: the same at 16 ms a frame as at 200."""
    g = hd(browser, seed12)
    try:
        calm(g)
        g.rpc("dev_teleport", x=13, y=-76, z=3)
        g.arrive()
        g.rest()
        g.js(REC)
        g.frames(3)
        g.page.keyboard.down("ArrowDown")
        try:
            g.wait("myPos().y >= -72", 15000)
        finally:
            g.page.keyboard.up("ArrowDown")
        g.wait("myAt && HdLook.level[1] === myAt.z", 8000)
        g.frames(3)
        g.js("window.__skOn = false")
        rec = g.js("window.__sk")
        put = lambda r: round(max(r[1] / r[5], r[3] + 2)) * r[5]   # (the edge as hd_eye.js api.sky puts it: at the land's end, or the sky's line as drawn if lower)
        moving = [(i, r) for i, r in enumerate(rec) if i and r[0] != rec[i - 1][0]]
        assert len(moving) >= 3, f"the eye moved on {len(moving)} frames: {rec[:3]}"
        off = [(i, r[0], r[2], put(r)) for i, r in moving if r[2] != put(r)]
        assert not off, f"frames where the eye moved and the sky's edge was drawn elsewhere (frame, eye, drawn, put): {off[:6]}"
        last = rec[-1]
        assert last[2] == put(last), f"standing, the sky's edge drawn at {last[2]}, put at {put(last)}"
    finally:
        g.page.close()
