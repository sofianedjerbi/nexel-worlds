"""Water that runs (flow.py, sim/waters.py; drawn by flow.js, vox_style_land.js): a hole dug beside a river fills a
layer at a time on the screen too, and a can poured on flat ground is drawn by its levels, thinner as it runs out.
FLOWSHOTS=<dir>: the frames are kept there (to look at them)."""

import os

from test_e2e_hd_sun import hd
from test_e2e_hd_trench import TILE

SHOTS = os.environ.get("FLOWSHOTS")
blue = lambda c: c[2] - c[0]                       # (water: blue over red; earth and grass: red over blue)


def calm(g):
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer"):
        g.js(f"setOpt('{o}', 0)")
    g.js("(() => { WayShow.paint = () => {}; return 1; })()")


def tidy(g, x, y, r=12):
    """The meadow as it was round (x, y), and no water left there, running or poured (dev_creatures clear: flow.py
    clear_near): a puddle left behind swam the next test's player (test_e2e_swim.py) in the shared world."""
    g.rpc("dev_stamp", x=x - r, y=y - r, rows=["." * (2 * r + 1)] * (2 * r + 1), levels=["0" * (2 * r + 1)] * (2 * r + 1))
    g.rpc("dev_creatures", clear=2 * r)
    g.wait(f"!Flow.col({x}, {y}) && !Flow.col({x + 1}, {y}) && !Flow.col({x - 3}, {y - 4})", 8000)


def shot(g, name):
    if SHOTS:
        g.page.screenshot(path=os.path.join(SHOTS, name + ".png"))


def test_a_hole_dug_beside_a_river_fills_a_layer_at_a_time_on_the_screen(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    try:
        g.stamp(-6, -7, ["~"] * 7)                                                    # a river, north-south, west of you
        g.stamp(-4, -6, ["...."] * 4, levels=["cccc"] * 4)                            # a pit three deep, a bank left between
        g.rest()
        X, Y = x - 3, y - 4                                                           # the pit's middle
        dry = g.js(TILE, [X, Y, -.5])                                                 # (where the water's face will be: into the pit now)
        shot(g, "hole_0_dry")
        assert g.js(f"Flow.col({X}, {Y})") is None
        g.js(f"(() => {{ window.__seen = []; window.__watch = setInterval(() => window.__seen.push([0, -1, -2].map((z) => Flow.at({X}, {Y}, z)).join()), 20); return 1; }})()")
        g.stamp(-5, -5, ["."], levels=["a"])                                         # the bank cut: the river comes in
        for i in range(1, 7):
            g.sleep(400)
            shot(g, f"hole_{i}")
        g.wait(f"Flow.at({X}, {Y}, -1) === 8 && Flow.at({X}, {Y}, -2) === 8 && Flow.at({X}, {Y}, 0) > 0", 15000)
        g.rest()
        shot(g, "hole_full")
        seen = [list(map(int, s.split(","))) for s in dict.fromkeys(g.js("(() => { clearInterval(window.__watch); return window.__seen; })()"))]
        assert seen[0] == [0, 0, 0] and seen[-1][1:] == [8, 8], seen                 # dry, then full under the river's face
        assert any(s[2] and not s[0] for s in seen), seen                            # the floor wet before the top: a layer at a time
        wet = g.js(TILE, [X, Y, -.5])
        assert blue(wet) > blue(dry) + 20, (dry, wet)                                # and the screen shows water over the floor
        assert g.js("HdLook.raw ? HdLook.raw() : 0") == 0
    finally:
        tidy(g, x, y)


def test_a_can_poured_on_flat_ground_is_drawn_thinner_as_it_runs_out(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    try:
        g.give(watering_can=1)
        meadow = g.js(TILE, [x + 2, y - 3, 0])
        g.act("water", dir="E", **{"with": "watering_can", "pour": True})
        g.wait(f"Flow.at({x + 1}, {y}, 1) === 8 && Flow.at({x + 1}, {y - 6}, 1) === 2", 15000)
        g.rest()
        shot(g, "poured")
        levels = g.js(f"[0, 1, 2, 3, 4, 5, 6, 7].map((d) => Flow.at({x + 1}, {y} - d, 1))")
        assert levels == [8, 7, 6, 5, 4, 3, 2, 1], levels
        near, far = g.js(TILE, [x + 1, y - 2, 0.75]), g.js(TILE, [x + 1, y - 7, 0.12])
        assert blue(near) > blue(far) > blue(meadow) - 5, (near, far, meadow)       # deep water bluer than its thin end
    finally:
        tidy(g, x, y)
