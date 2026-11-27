"""The HD look under ground shows the way (hd.js, vox_style_land.js, vox_style_glsl.js): a floor you cannot walk to from
where you are (a stair's treads two levels up, the passage past a wall) is drawn where it is, at its own height, cold
(grey-blue, no warm light); and going under a roof the eye tilts over some 400 ms, never in a few frames. (The land
over your head is not drawn near you: test_e2e_hd_cutaway.py.)"""

from test_e2e_hd_sun import hd

STEEP = 58          # the eye's pitch from above (hd.js STEEP: 78.6 till the x-ray cut what hides you, 68 when a level was 8 px)

# a tile's top as it is on the screen: [mean r, g, b, px warm (red well over blue), px cold (blue not under red)] of the px inside its four corners' box
TOP = """([x, y, z]) => { const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + a, y + b, z)), k = devicePixelRatio;
  const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 4, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 4, y0 = Math.ceil(c[0][1] * k) + 4, y1 = Math.floor(c[2][1] * k) - 4;
  const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data, s = [0, 0, 0, 0, 0], n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { s[0] += d[i] / n; s[1] += d[i + 1] / n; s[2] += d[i + 2] / n; if (d[i] > d[i + 2] + 40) s[3]++; else if (d[i + 2] >= d[i] - 6) s[4]++; }
  return s.map(Math.round); }"""


def test_going_under_a_roof_and_out_the_eye_tilts_over_many_frames(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[z - 14, z - 11, z])
    g.rest()                                                  # (the pocket made and drawn)
    base = g.js("HdLook.cam.pitch")
    g.js("(() => { window.__p = []; const f = () => { __p.push(HdLook.cam.pitch); requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()")
    g.rpc("dev_teleport", x=x, y=y, z=z - 14)
    g.until("HdLook.cam.pitch === HdLook.steep")              # (a tilt is frames, at least 12: capped in frames)
    g.frames(2)
    p = g.js("__p.splice(0)")
    mid = sorted(set(round(v, 2) for v in p if base + .01 < v < STEEP - .01))
    steps = [b - a for a, b in zip(p, p[1:])]
    assert len(mid) >= 10, (len(mid), mid)                           # (it was most of the way in 8 frames)
    assert min(steps) >= 0 and max(steps) < (STEEP - base) / 6, max(steps)      # (one way, no jump)
    g.rpc("dev_teleport", x=x + 12, y=y, z=z)                        # out: it waits a moment (a roof's edge walked along does not tilt the eye at every tile), then eases back
    g.wait(f"HdLook.cam.pitch === {base}", timeout=6000)
    p = g.js("__p.splice(0)")
    mid = sorted(set(round(v, 2) for v in p if base + .01 < v < STEEP - .01))
    steps = [b - a for a, b in zip(p, p[1:])]
    assert len(mid) >= 10 and max(steps) <= 0 and min(steps) > -(STEEP - base) / 6, (len(mid), min(steps))
