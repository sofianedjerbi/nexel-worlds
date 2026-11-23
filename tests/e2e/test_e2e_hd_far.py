"""The HD look far from the world's middle (vox_style.js `draw`: the fog's and the lantern's uniforms): 150 tiles from
where you woke the land round you is drawn in the colours it has there, not in the air's haze. (The calls that give the
shader the eye and the lamp sat inside a trailing note: both stayed at the world's origin: the fog began 44 tiles from it
and 60 tiles out the whole meadow was flat sky blue, on any screen, shader and curve on or off.)"""


import pytest
from test_e2e_hd_phone import phone
from test_e2e_hd_sun import hd

# the mean colour of the meadow round you as the screen shows it: 3 x 2 tiles' tops beside you, [r, g, b]
MEADOW = """([x, y, z]) => { const s = [0, 0, 0]; let n = 0, k = devicePixelRatio;
  for (const [i, j] of [[2, 0], [3, 0], [4, 0], [2, 1], [3, 1], [4, 1], [-3, 0], [-4, 0]]) {
    const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + i + a, y + j + b, z));
    const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 1, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 1, y0 = Math.ceil(c[0][1] * k) + 1, y1 = Math.floor(c[2][1] * k) - 1;
    const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data; for (let q = 0; q < d.length; q += 4) { s[0] += d[q]; s[1] += d[q + 1]; s[2] += d[q + 2]; n++; } }
  return s.map((v) => v / n); }"""


@pytest.mark.quick
def test_150_tiles_from_where_you_woke_the_land_is_drawn_in_its_own_colours(browser, server):
    g = hd(browser, server)
    g.js("setOpt('shader', 'off'); setOpt('clouds', 0); setOpt('shadows', 0)")
    g.hour(.375)
    x, y = g.pos()
    near = g.js(MEADOW, [x, y, g.js(f"topAt({x}, {y})")])
    assert near[1] > near[2] + 40, near                              # a meadow: green, not blue
    for dx, dy in ((150, 0), (-150, 150)):
        g.rpc("dev_teleport", x=x + dx, y=y + dy)
        g.arrive()
        # the same flat meadow as where you woke, out to 30 tiles: the world's own hills 13 tiles south of a far place stood
        # in front of the meadow beside you (the eye looks down on you over them: pitch 40.7) and their grey stone was read
        # as its colour, [149, 160, 126] for [193, 213, 113], one run in eight by where the test took you
        g.clear_area(30)
        g.rpc("dev_teleport", x=x + dx, y=y + dy)
        g.arrive()
        fx, fy = g.pos()
        assert abs(fx - x - dx) + abs(fy - y - dy) < 8, (fx, fy)
        far = g.js(MEADOW, [fx, fy, g.js(f"topAt({fx}, {fy})")])
        # (in the haze every channel went to the air's: red +60, blue +120)
        assert all(abs(a - b) < 12 for a, b in zip(near, far)), (dx, dy, near, far)


# THE VIEW DISTANCE (the Picture page's "View distance", hd.js viewOf): level ground meets the sky that many tiles off
VIEWS = (("near", 9), ("normal", None), ("far", 25), ("veryfar", 37))      # (Normal: the bend as it was, .03)
# where level ground at your level meets the sky, as the picture has it: the farthest row north of you drawn higher than every nearer one
SEEN = """() => { const p = myPos(), L = HdLook.level[1]; let m = 1e9, at = 0;
  for (let dn = 1; dn <= 160; dn++) { const a = HdLook.screenOf(p.x + .5, p.y - dn + .5, L); if (a && a[1] < m) { m = a[1]; if (a[1] >= 0) at = dn; } }
  return at; }"""
# what is past the land drawn, under the sky's line (the hd_horizon test's): px of the backdrop's colours, px where no land is drawn; and the land made
# tile by tile reaching past the picture's sides at every row up to the horizon (its coarse far patches never at its sides: "dark blue walls" zoomed out)
EDGES = """() => { const el = HdView.el, c = document.createElement('canvas'); c.width = el.width; c.height = el.height; const g = c.getContext('2d'); g.drawImage(el, 0, 0);
  const W = el.width, H = el.height, d = g.getImageData(0, 0, W, H).data, line = Math.max(0, Math.round(HdLook.sky(0).line / zoom)), bk = new Set((HdView.backdrop || []).map((q) => q[0] << 16 | q[1] << 8 | q[2]));
  let back = 0; for (let y = line; y < H; y++) for (let x = 0; x < W; x++) { const i = (y * W + x) * 4; if (bk.has(d[i] << 16 | d[i + 1] << 8 | d[i + 2])) back++; }
  const p = myPos(), b = HdLook.box, L = HdLook.level[1], side = [];
  for (let dn = 0; dn <= HdLook.view.n; dn++) for (const x of [b[0], b[2] + 1]) { const a = HdLook.screenOf(x, p.y - dn, L); if (a && a[0] / zoom > 0 && a[0] / zoom < W && a[1] / zoom > line && a[1] / zoom < H) side.push([x - p.x, dn]); }
  return {back, bare: HdLook.bare(), line, H, side: side.slice(0, 4), n: HdLook.view.n}; }"""


def view(g, v, z):
    g.js(f"(() => {{ setOpt('view', '{v}'); zoom = ZOOM.to = {z}; return 1; }})()")
    g.rest()


def test_each_view_distance_puts_the_horizon_that_far_at_any_zoom_and_its_land_comes(browser, server):
    """Near, Normal, Far, Very far: level ground meets the sky 9, 13 to 17 (the bend as it was), 25, 37 tiles north of you (the bend's facets end
    there), whatever the zoom; the land is made tile by tile past it, and the far land's blocks the server is asked for all
    come (views.py far_near: it gives far land only near what a page watches). (One bend for all, it was 13 tiles on a desk.)"""
    g = hd(browser, server)
    seen = {}
    for v, d in VIEWS:
        for z in (2, 3, 5):
            view(g, v, z)
            n, capped = g.js("[HdLook.view.n, HdLook.view.capped]")
            assert g.js(SEEN) == n, (v, z, n, g.js(SEEN))
            # (a sixteenth of the picture stays sky: zoomed in, or Very far, a short picture shows less far)
            assert (d is None and g.js("HdLook.view.b") == .03 and 9 <= n <= 17) or n == d or (capped and 13 <= n < d and g.js("HdLook.sky(0).line / zoom") >= .05 * g.js("cv.height / (zoom * DPR)")), (v, z, n)
            assert g.js("HdLook.box[1]") <= g.pos()[1] - n - 8, (v, z, g.js("HdLook.box"))
            seen.setdefault(z, []).append(n)
    for z, l in seen.items():
        assert l == sorted(l) and (z != 2 or len(set(l)) == 4), (z, l)          # (each farther; zoomed in on this short picture Far and Very far meet the sixteenth of sky)
    g.wait("(() => { const f = HdLook.far; for (let by = Math.floor(f[1] / B); by <= Math.floor(f[3] / B); by++) for (let bx = Math.floor(f[0] / B); bx <= Math.floor(f[2] / B); bx++) if (!blocks.has(bkey(bx, by))) return false; return true; })()", 30000)
    g.js("setOpt('view', 'normal'); zoom = ZOOM.to = 3")


def test_nothing_past_the_drawn_land_is_seen_at_any_zoom_or_view_distance(browser, server):
    """Zoomed out on a lake (the owner's island in the sea): no px of the backdrop under the sky's line, no px with no land,
    and the land made tile by tile reaches past the picture's sides up to the horizon: never the sea's far patches standing
    as dark walls at its sides (the land made tile by tile was 24 tiles across at the most: zoomed out, the picture was wider)."""
    g = hd(browser, server)
    x, y = g.pos()
    g.stamp(-40, -22, ["~" * 81] * 20)                       # a lake north, east and west of you, out past the land made tile by tile
    try:
        for v, _ in VIEWS:
            for z in (2, 3, 4, 6):
                view(g, v, z)
                out = g.js(EDGES)
                assert out["back"] < 200 and out["bare"] == 0 and not out["side"], ("desk", v, z, out)
        ctx, p = phone(browser, server)                      # and on a phone held upright, at the same place
        try:
            p.rpc("dev_teleport", x=x, y=y)
            p.arrive()
            for v, _ in VIEWS:
                for z in (2, 3, 4):
                    view(p, v, z)
                    out = p.js(EDGES)
                    assert out["back"] < 200 and out["bare"] == 0 and not out["side"], ("phone", v, z, out)
            assert not p.errors, p.errors
        finally:
            ctx.close()
    finally:
        g.stamp(-40, -22, ["." * 81] * 20)
        g.js("setOpt('view', 'normal'); zoom = ZOOM.to = 3")
