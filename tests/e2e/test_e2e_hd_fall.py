"""The HD look at a cliff and behind things (hd.js, vox_style_glsl.js, vox_style_land.js): the edge over a drop that
hurts has a dark rim (a step has none); walking off it the eye stays while you fall and then comes down to you, no
frame of it a jump; and what stands in front of you is one px in two round you, you behind it."""


import pytest
from test_e2e_hd_sun import hd

# a px of the land's top at (x, y, z), a tile's fraction in: the sum of r, g, b
PX = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = devicePixelRatio, d = HdLook.read(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data; return d[0] + d[1] + d[2]; }"""
REC = """(() => { window.__r = []; window.__on = true; const f = () => { const p = ents.get('agent' + myId), fl = falling(p, performance.now());
  __r.push([HdLook.level[0], HdLook.level[1], fl && fl.air ? 1 : 0]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""


def cliff(g):
    """You on a terrace 9 levels over the meadow north of you: three tiles wide, its rim a tile north."""
    x, y = g.pos()
    g.stamp(-3, -4, ["......."] * 7, levels=["0000000"] * 3 + ["0099900"] * 3 + ["0000000"])
    g.rpc("dev_teleport", x=x, y=y)
    g.arrive()
    return x, y


@pytest.mark.realtime
def test_the_edge_over_a_drop_that_hurts_has_a_dark_rim_and_a_step_has_none(browser, server):
    g = hd(browser, server)
    g.js("setOpt('shader', 'off'); setOpt('clouds', 0); setOpt('shadows', 0)")
    x, y = cliff(g)
    g.stamp(-2, -1, ["."], levels=["8"])                                # a step of one level down, west of the terrace
    g.rest()
    mid = g.js(PX, [x + 1.5, y - .5, 9])
    east, north = g.js(PX, [x + 1.97, y - .5, 9]), g.js(PX, [x + 1.5, y - .97, 9])
    step = g.js(PX, [x - .97, y - .5, 9])
    assert east < mid * .5 and north < mid * .5, (mid, east, north)     # the cliff's rim: dark
    assert step > mid * .7 and east < step * .65, (mid, step, east)     # the step's edge: the cap's own outline, no more (374 of 484; the rim 187)


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
    assert len(air) > 8, len(air)                                       # it fell, over some frames
    assert min(v[1] for v in air) >= 8.5, air                           # the eye stayed up while the body came down
    steps = [abs(b[1] - a[1]) for a, b in zip(r, r[1:])]
    assert max(steps) < 1.5, max(steps)                                 # (it was 9 levels in one frame: over 8 the eye went there at once)
    assert sum(1 for s in steps if s > .05) >= 12                       # down to you over a dozen frames or more


def test_a_tree_in_front_of_you_is_one_px_in_two_round_you(browser, server):
    g = hd(browser, server)
    g.stamp(0, 1, ["T"])
    g.rest()
    seen = g.js("HdLook.catSeen()")
    assert .3 < seen < .9, seen                                         # (a whole hole in the tree showed all of you: 1; the tree whole: under .3)
