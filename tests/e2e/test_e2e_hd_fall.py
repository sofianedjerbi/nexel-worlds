"""The HD look at a cliff and behind things (hd.js, vox_style_glsl.js, vox_style_land.js): the edge over a drop that
hurts is drawn as a step's, no dark rim; walking off it the eye stays while you fall and then comes down to you, no
frame of it a jump; and what stands in front of you is one px in two round you, you behind it."""


import pytest
from test_e2e_hd_sun import hd

# a px of the land's top at (x, y, z), a tile's fraction in: the sum of r, g, b
PX = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = devicePixelRatio, d = HdLook.read(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data; return d[0] + d[1] + d[2]; }"""
REC = """(() => { window.__r = []; window.__on = true; const f = () => { const p = ents.get('agent' + myId), fl = falling(p, performance.now());
  __r.push([HdLook.level[0], HdLook.level[1], fl && fl.air ? 1 : 0, performance.now()]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""


def cliff(g):
    """You on a terrace 9 levels over the meadow north of you: three tiles wide, its rim a tile north."""
    x, y = g.pos()
    g.stamp(-3, -4, ["......."] * 7, levels=["0000000"] * 3 + ["0099900"] * 3 + ["0000000"])
    g.rpc("dev_teleport", x=x, y=y)
    g.arrive()
    return x, y


@pytest.mark.realtime
def test_the_edge_over_a_drop_that_hurts_has_no_dark_rim_as_a_step_has_none(browser, server):
    """It had a dark rim 2 px wide all along it, to tell a cliff from a step: "ugly dark borders on cliffs and above
    holes". The edge is drawn as a step's, the cap's own outline; the faces under it show the drop."""
    g = hd(browser, server)
    g.js("setOpt('shader', 'off'); setOpt('clouds', 0); setOpt('shadows', 0)")
    x, y = cliff(g)
    g.stamp(-2, -1, ["."], levels=["8"])                                # a step of one level down, west of the terrace
    g.rest()
    mid = g.js(PX, [x + 1.5, y - .5, 9])
    # (a tile's edge is a px of the screen's on the screen's way down only where the picture's pin puts it: .97 of a tile
    #  in, the north rim was read one px past the edge, on the meadow far below, by where the pin lay (hd.js pin: since it
    #  is made at your feet's level). The rim is a px and a half wide there: read .93 in, inside it wherever the pin is)
    east, north = g.js(PX, [x + 1.93, y - .5, 9]), g.js(PX, [x + 1.5, y - .93, 9])
    step = g.js(PX, [x - .93, y - .5, 9])
    assert step > mid * .7 and east > mid * .7 and north > mid * .7, (mid, step, east, north)   # the cliff's edge as the step's: the cap's own outline, no more (the rim was 187 of 484)


@pytest.mark.realtime
def test_off_a_cliff_the_eye_stays_while_you_fall_and_comes_down_with_no_jump(browser, server):
    g = hd(browser, server)
    x, y = cliff(g)
    g.wait("HdLook.level[1] === 9", timeout=4000)                       # (the eye come up to you)
    g.js(REC)
    g.page.keyboard.down("ArrowUp")
    g.wait(f"myPos().y <= {y - 2} && !falling(ents.get('agent' + myId), performance.now())", timeout=8000)
    g.page.keyboard.up("ArrowUp")
    g.wait("HdLook.level[1] === 0", timeout=4000)
    r = g.js("(() => { __on = false; return __r; })()")
    air = [v for v in r if v[2]]
    assert len(air) >= 3, len(air)                                      # it fell, over some frames (a desktop draws 9 or more of it, a renderer with no GPU 7)
    assert min(v[1] for v in air) >= 8.5, air                           # the eye stayed up while the body came down
    # the eye's way a 60th of a second, and how long it took to come down: it eases in time, and a slow frame holds more of it
    steps = [(abs(b[1] - a[1]) * 1000 / 60 / max(1000 / 60, b[3] - a[3]), a[3], b[3]) for a, b in zip(r, r[1:])]
    assert max(s for s, _, _ in steps) < 1.5, max(steps)                # (it was 9 levels in one frame: over 8 the eye went there at once)
    moving = [(t0, t1) for s, t0, t1 in steps if s > .05]
    assert moving and moving[-1][1] - moving[0][0] >= 180, moving       # down to you over a fifth of a second or more (a dozen frames on a desktop)


# frames that take `ms` each (a slow phone, a busy machine): the page spins that long in every frame; 0: no more
SLOW = """(ms) => { const on = window.__slow; window.__slow = ms; if (!on && ms) { const f = () => { const t = performance.now(); while (performance.now() - t < window.__slow) { /* spin */ }
  if (window.__slow) requestAnimationFrame(f); }; requestAnimationFrame(f); } return 1; }"""
EYE = """(() => { window.__r = []; window.__on = true; const f = () => { __r.push(HdLook.level[1]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""


@pytest.mark.realtime
def test_with_frames_of_any_length_the_eye_comes_to_you_and_never_past_and_the_window_is_right(browser, server):
    """(the eye's spring was stepped a frame at a time: with frames over 83 ms it swung wider at each one, to 40 levels
    off, then jumped. Its exact answer now, hd.js)"""
    g = hd(browser, server)
    x, y = cliff(g)
    z = g.js(f"topAt({x + 8}, {y + 6})")
    g.rpc("dev_col", tiles=[[x + 8 + i, y + 6 + j] for j in (-1, 0, 1) for i in (-1, 0, 1)], col=[z - 14, z - 11, z])   # a room under 11 levels of land
    g.wait("HdLook.level[1] === 9", timeout=4000)
    for ms in (20, 100, 250):
        g.js(SLOW, ms)
        for to, lv in (((x, y + 3), 0), ((x, y), 9)):                   # down to the meadow, up to the terrace: 9 levels each way
            g.js(EYE)
            g.rpc("dev_teleport", x=to[0], y=to[1])
            g.wait(f"HdLook.level[0] === {lv} && HdLook.level[1] === {lv}", timeout=15000)
            r = g.js("(() => { __on = false; return __r; })()")
            assert min(r) >= -.01 and max(r) <= 9.01, (ms, lv, min(r), max(r))      # (never past where it was or where it goes)
            turns = sum(1 for a, b, c in zip(r, r[1:], r[2:]) if (b - a) * (c - b) < -1e-6)
            assert turns == 0, (ms, lv, turns, r)                                  # (one way only: no swing)
    g.js(SLOW, 100)
    g.rpc("dev_teleport", x=x + 8, y=y + 6, z=z - 14)
    g.wait(f"HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch === HdLook.steep && HdLook.level[1] === {z - 14}", timeout=20000)
    g.js(SLOW, 0)
    g.rest()
    wins = g.js(f"[!!HdLook.winAt({x + 8}, {y + 6}), !!HdLook.winAt({x + 8}, {y + 6 - 2}), !!HdLook.winAt({x + 8 + 12}, {y + 6})]")
    assert wins == [True, False, False], wins                           # (the window on your room; no tile of it north of the room or far beside it)
    assert g.js("HdLook.level")[:3] == [z - 14, z - 14, z - 14] and g.js("HdLook.catSeen()") > .8


def test_a_tree_in_front_of_you_is_one_px_in_two_round_you(browser, server):
    g = hd(browser, server)
    g.stamp(0, 1, ["T"])
    g.rest()
    seen = g.js("HdLook.catSeen()")
    assert .3 < seen < .9, seen                                         # (a whole hole in the tree showed all of you: 1; the tree whole: under .3)
