"""The HD look in whole art px, never unpainted (audit 8: "cheap 3D, not pixel art"; things floating on a void; holes
that glow; steps dug in stone drawn as earth).

- A side's paint is laid in whole art px: a level shows as many rows of it as the picture has, its lit top row and
  its seam at its foot on EVERY level (vox_style_glsl.js `whole`). It was the nearest row: a level 6.5 px tall lost its
  seam here and there, and the paint's 1-px columns stood as streaks.
- Nothing blurs the picture: the land's picture is put on the screen as it is (hd_view.js: the lens's soft far rows
  and its bloom made every rim and far wall a smear on a desktop).
- After a teleport no frame shows the land unpainted (hd.js `held`: the last picture stays until the land is made).
- A floor sunk in the land is darker than the ground round it, at night too (it glowed lavender).
- A trench cut in a stone mass is stone (voxpaint.js `cut`)."""

import math

import pytest

from test_e2e_hd_sun import hd

# mean luminance of each art row of the HD picture between columns x0..x1 (art px), rows y0..y1
ROWS = """([x0, x1, y0, y1]) => { const el = HdView.el, d = el.getContext('2d').getImageData(x0, y0, x1 - x0, y1 - y0).data, w = x1 - x0, out = [];
  for (let j = 0; j < y1 - y0; j++) { let s = 0; for (let i = 0; i < w; i++) { const o = (j * w + i) * 4; s += .3 * d[o] + .59 * d[o + 1] + .11 * d[o + 2]; } out.push(s / w); } return out; }"""
# luminances of the art px of the HD picture in a box (art px), sorted
LUMS = """([x0, x1, y0, y1]) => { const d = HdView.el.getContext('2d').getImageData(x0, y0, x1 - x0, y1 - y0).data, out = [];
  for (let i = 0; i < d.length; i += 4) out.push(.3 * d[i] + .59 * d[i + 1] + .11 * d[i + 2]); return out.sort((a, b) => a - b); }"""
ART = "([x, y, z]) => { const a = HdLook.screenOf(x, y, z); return [a[0] / zoom, a[1] / zoom]; }"


def scene(g, phase=.375):
    g.js("setOpt('shader', 'off'); setOpt('clouds', 0); setOpt('shadows', 0)")
    g.hour(phase)
    return g.pos()


def made(g):
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    g.frames(2)


@pytest.mark.quick
def test_a_stone_wall_shows_its_seam_on_every_level_and_nothing_blurs_the_picture(browser, server):
    g = hd(browser, server)
    x, y = scene(g)
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in (-7, -6, -5) for i in range(-3, 5)], col=[9])   # stone: nine high, 8 x 3, its south face on row y - 4
    made(g)
    (ax, _), (bx, _) = g.js(ART, [x - 2, y - 4, 0]), g.js(ART, [x + 4, y - 4, 0])
    x0, x1, seams = int(ax) + 2, int(bx) - 2, []
    for z in range(9, 0, -1):                                        # each level: from its top line to the next one's
        top, bot = g.js(ART, [x, y - 4, z])[1], g.js(ART, [x, y - 4, z - 1])[1]
        r0, r1 = math.ceil(top - .5), math.ceil(bot - .5)            # (the rows whose middle is in it)
        rows = g.js(ROWS, [x0, x1, r0, r1])
        mean = sum(rows[:-1]) / (len(rows) - 1)
        seams.append((z, len(rows), min(range(len(rows)), key=lambda i: rows[i]), round(rows[-1] / mean, 2), rows[0] > rows[1]))
    # every level: its last row the seam (its darkest, well under the rest), its first one lit (it was the nearest row: a level 6.4 px tall lost one or the other here and there)
    assert all(d == n - 1 and k < .85 and lit for _, n, d, k, lit in seams), seams
    # the picture on the screen is the land's own, px for px, under the sky (the marks aside: a share of them at most)
    diff = g.js("""(() => { const el = HdView.el, p = HdView.pic, w = el.width, h = el.height, c = document.createElement('canvas'); c.width = w; c.height = h;
      const q = c.getContext('2d'); q.drawImage(p, 0, 0); const a = q.getImageData(0, 0, w, h).data, b = el.getContext('2d').getImageData(0, 0, w, h).data; let n = 0, m = 0;
      for (let i = 0; i < a.length; i += 4) if (a[i + 3] === 255) { n++; if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 3) m++; } return [n, m]; })()""")
    assert diff[0] > 1000 and diff[1] < .02 * diff[0], diff


@pytest.mark.realtime
def test_no_frame_shows_the_land_unpainted_after_a_teleport(browser, server):
    g = hd(browser, server)
    x, y = scene(g)
    cdp = g.page.context.new_cdp_session(g.page)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})          # (a slower machine: the land takes frames to come)
    try:
        g.js("""(() => { window.__v = []; window.__vo = true; const f = () => { const el = HdView.el, B = HdView.backdrop; if (el && B) { const y0 = Math.floor(el.height * .45), d = el.getContext('2d').getImageData(0, y0, el.width, el.height - y0).data; let n = 0;
          for (let i = 0; i < d.length; i += 4) for (const b of B) if (Math.abs(d[i] - b[0]) < 3 && Math.abs(d[i + 1] - b[1]) < 3 && Math.abs(d[i + 2] - b[2]) < 3) n++; __v.push(n); } if (__vo) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()""")
        for tx, ty in ((x + 150, y + 120), (x - 160, y + 90)):
            g.rpc("dev_teleport", x=tx, y=ty)
            g.arrive()
            g.wait("!HdLook.busy && !HdLook.held", 20000)
            g.frames(10)
        v = g.js("(() => { __vo = false; return __v; })()")
    finally:
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    assert len(v) > 30 and max(v) <= 50, (len(v), [n for n in v if n > 50][:10])


def test_a_pit_floor_is_darker_than_the_meadow_by_day_and_by_night(browser, server):
    g = hd(browser, server)
    x, y = scene(g)
    g.stamp(-6, -6, ["." * 5] * 5, levels=["00000", "0bbb0", "0bbb0", "0bbb0", "00000"])   # a pit 3 x 3, two deep, its middle at (x - 4, y - 4): five tiles from your lantern
    out = []
    for phase in (.375, .9):
        g.hour(phase)
        made(g)
        (ax, ay), (bx, by) = g.js(ART, [x - 5, y - 5, -2]), g.js(ART, [x - 2, y - 4, -2])   # (its north row: the south rim hides the rest from this eye)
        floor = g.js(LUMS, [int(ax) + 1, int(bx) - 1, int(ay) + 1, int(by) - 1])
        (gx, gy), (hx, hy) = g.js(ART, [x + 2, y - 5, 0]), g.js(ART, [x + 6, y - 2, 0])
        grass = g.js(LUMS, [int(gx), int(hx), int(gy), int(hy)])
        out.append((phase, round(floor[int(len(floor) * .8)]), round(grass[len(grass) // 2]), len(floor)))
    # the floor's light px (its 80th) a step under the meadow's middle one, by day and by night (it was .83 of it: pale dug earth, lavender at night)
    assert all(n > 20 and f < .75 * m for _, f, m, n in out), out


def test_a_trench_cut_in_stone_is_stone(browser, server):
    g = hd(browser, server)
    x, y = scene(g)
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-9, -3) for i in range(-4, 5) if abs(i) > 1], col=[8])   # stone eight high, 9 x 6, a trench 3 wide through it north to south
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-9, -3) for i in (-1, 0, 1)], col=[3])                   # its floor at 3: under stone's 5, cut in stone
    made(g)
    assert g.js(f"VoxPaint.rocky({x}, {y - 6})") == 2
    (ax, ay), (bx, by) = g.js(ART, [x - 1, y - 6, 3]), g.js(ART, [x + 2, y - 4, 3])
    px = g.js("""([x0, x1, y0, y1]) => { const d = HdView.el.getContext('2d').getImageData(x0, y0, x1 - x0, y1 - y0).data, n = new Map(); for (let i = 0; i < d.length; i += 4) { const c = d[i] + ',' + d[i + 1] + ',' + d[i + 2]; n.set(c, (n.get(c) || 0) + 1); }
      return [...n].sort((p, q) => q[1] - p[1]).slice(0, 3).map((p) => p[0]); }""", [int(ax) + 2, int(bx) - 2, int(ay) + 1, int(by) - 1])
    r, gg, b = map(int, px[0].split(","))
    assert abs(r - gg) < 25 and b - r > -12, px                     # stone's grey, not earth's brown (r over b by 40 and more)


@pytest.mark.quick
def test_natural_stone_is_a_cliff_and_a_laid_stone_block_has_courses(browser, server):
    """The land's own stone (a mountain, a gorge's wall) is a cliff: no course line across every level's foot (it was
    laid masonry, a mortar line under each course: "natural rock as bricks"); a stone block put down keeps its courses."""
    g = hd(browser, server)
    scene(g)
    # each level 5..12, variant 0..3, natural then laid: [spread of its foot row's luminance, of its middle row's]
    rows = g.js("""(() => { const out = [], L = (v) => .3 * (v & 255) + .59 * (v >>> 8 & 255) + .11 * (v >>> 16 & 255), sd = (a) => { const m = a.reduce((s, x) => s + x, 0) / a.length; return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / a.length); };
      for (const built of [0, 1]) for (let z = 5; z <= 12; z++) for (let v = 0; v < 4; v++) { const px = new Uint32Array(16 * 8); VoxPaint.front(z, v, px, 0, 16, built);
        const row = (j) => [...px.slice(j * 16, j * 16 + 16)].map(L); out.push([built, z, v, sd(row(7)), Math.min(...row(7)), Math.max(...row(7))]); } return out; })()""")
    natural, laid = [r for r in rows if not r[0]], [r for r in rows if r[0]]
    assert all(s > 6 for _, _, _, s, _, _ in natural), [r for r in natural if r[3] <= 6]       # a cliff's foot: broken, a ledge's undercut here, the rock there
    assert all(s < .5 for _, _, _, s, _, _ in laid), [r for r in laid if r[3] >= .5]          # a laid block's: one joint line, all across
