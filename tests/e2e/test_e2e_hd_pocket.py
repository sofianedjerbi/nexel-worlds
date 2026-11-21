"""The HD look under ground shows the way (hd.js, vox_style_land.js, vox_style_glsl.js): a floor you cannot walk to from
where you are (a stair's treads two levels up, the passage past a wall) is drawn where it is, at its own height, cold
(grey-blue, no warm light); the floor over your head is a see-through checker of it; and going under a roof the eye
tilts over some 400 ms, never in a few frames."""

import pytest
from test_e2e_hd_sun import hd, settled

STEEP = 78.6        # the eye's pitch from above (hd.js api.steep: 68 when a level was 8 px; tan 78.6 = 2 tan 68)

# a tile's top as it is on the screen: [mean r, g, b, px warm (red well over blue), px cold (blue not under red)] of the px inside its four corners' box
TOP = """([x, y, z]) => { const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + a, y + b, z)), k = devicePixelRatio;
  const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 4, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 4, y0 = Math.ceil(c[0][1] * k) + 4, y1 = Math.floor(c[2][1] * k) - 4;
  const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data, s = [0, 0, 0, 0, 0], n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { s[0] += d[i] / n; s[1] += d[i + 1] / n; s[2] += d[i + 2] / n; if (d[i] > d[i + 2] + 40) s[3]++; else if (d[i + 2] >= d[i] - 6) s[4]++; }
  return s.map(Math.round); }"""


def pocket(g):
    """A passage 14 down, four tiles long; over its two east tiles a floor three levels up (a slab one level thick),
    which goes on east: the stair you cannot reach from under it. -> (x, y, z): the passage's east end"""
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    g.rpc("dev_col", tiles=[[x - 3, y], [x - 2, y]], col=[z - 14, z - 12, z])
    g.rpc("dev_col", tiles=[[x - 1, y], [x, y]], col=[z - 14, z - 12, z - 11, z - 9, z])
    g.rpc("dev_col", tiles=[[x + 1, y], [x + 2, y], [x + 3, y]], col=[z - 11, z - 9, z])
    g.sleep(800)
    g.rpc("dev_teleport", x=x, y=y, z=z - 14)
    g.wait("HdLook.win.a === 1 && HdLook.win.n >= 7 && !HdLook.busy && HdLook.cam.pitch > 67.5", timeout=6000)
    settled(g)
    return x, y, z


@pytest.mark.realtime
def test_in_a_pocket_under_a_higher_floor_that_floor_is_drawn_cold_and_the_one_over_you_is_a_checker(browser, server):
    g = hd(browser, server)
    g.rpc("dev_time", phase=.3)
    x, y, z = pocket(g)
    # the floor past the wall, three levels up: the window is on it too (a hollow beside your space, from its own floor to its own ceiling), and it is drawn cold
    assert g.js(f"[HdLook.winAt({x - 3}, {y}), HdLook.winAt({x + 1}, {y}), HdLook.winAt({x + 3}, {y})]") == [[z - 14, z - 12], [z - 11, z - 9], [z - 11, z - 9]]
    # (the way out is marked over these very tiles once it is found, a moment after you are trapped: the block to break under the next tread, cream and orange, its key, dots along the treads: warm px that are not
    # the floor's. Read before they came the test passed, after them it failed: it is the floors that are measured, so the marks are not painted)
    g.js("(() => { WayShow.paint = () => {}; return 1; })()")
    g.frames(3)
    mine, other = g.js(TOP, [x - 3, y, z - 14]), g.js(TOP, [x + 1, y, z - 11])
    assert mine[0] > mine[2] + 40, mine                               # your own floor: warm
    assert other[2] >= other[0] - 6 and other[3] == 0, other          # the other: no warm px at all
    assert sum(other[:3]) > 150, other                                # ... and not black: it is seen
    # the floor over the passage (the tile west of yours): one px in two of it, cold, the warm floor under it showing through
    over = g.js(TOP, [x - 1, y, z - 11])
    assert over[3] > 20 and over[4] > 20 and .2 < over[3] / over[4] < 3, over   # (both there: its cold px, and through it the warm wall and floor of your passage; its north px are under the window's section band, grey: more cold than warm; 14 deep the wall is darker now, fewer of its px count as warm: .2, was .3)
    assert g.js("HdLook.catSeen()") > .8


def test_going_under_a_roof_and_out_the_eye_tilts_over_many_frames(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[z - 14, z - 11, z])
    g.sleep(800)
    base = g.js("HdLook.cam.pitch")
    g.js("(() => { window.__p = []; const f = () => { __p.push(HdLook.cam.pitch); requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()")
    g.rpc("dev_teleport", x=x, y=y, z=z - 14)
    g.wait("HdLook.cam.pitch === HdLook.steep", timeout=6000)
    g.sleep(200)
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
