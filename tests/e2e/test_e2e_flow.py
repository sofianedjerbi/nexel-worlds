"""Water that runs (flow.py, sim/waters.py; drawn by flow.js, vox_style_land.js): a hole dug beside a river fills a
layer at a time on the screen too, and a can poured on flat ground is drawn by its levels, lower as it runs out, the
colour of water to its last tile; running water is one surface: one tint over its bed, no seam of another colour where
it steps down a level, no water drawn on the dry land beside it.
FLOWSHOTS=<dir>: the frames are kept there (to look at them)."""

import os

from test_e2e_hd_sun import hd
from test_e2e_hd_trench import TILE

SHOTS = os.environ.get("FLOWSHOTS")
blue = lambda c: c[2] - c[0]                       # (water: blue over red; earth and grass: red over blue)
TINT = (104, 204, 208)                             # (clear water's tint a level deep, waterbed.js TINT[1]: a film of running water has it too)


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
        # (its levels are its face's height; its thin end is water still, the tint of the rest: it was a film "hardly
        # tinted", a pale box at the end of every run, the owner's "light box over the sand")
        assert min(blue(near), blue(far)) > blue(meadow) + 25 and abs(blue(near) - blue(far)) < 15, (near, far, meadow)
    finally:
        tidy(g, x, y)


# the px of a box on the screen ([x0, y0, x1, y1] in CSS px), as [r, g, b] each (HdLook.read, the shared reader)
BOX = """([x0, y0, x1, y1]) => { const k = devicePixelRatio, a = Math.round(Math.min(x0, x1) * k), b = Math.round(Math.min(y0, y1) * k);
  const d = HdLook.read(a, b, Math.max(1, Math.round(Math.abs(x1 - x0) * k)), Math.max(1, Math.round(Math.abs(y1 - y0) * k))).data, out = [];
  for (let i = 0; i < d.length; i += 4) out.push([d[i], d[i + 1], d[i + 2]]); return out; }"""


# the px of a tile's top at height z as the screen has them (TILE's box, two px in): [r, g, b] each
TILEPX = """([x, y, z]) => { const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + a, y + b, z)), k = devicePixelRatio;
  const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 2 * zoom, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 2 * zoom, y0 = Math.ceil(c[0][1] * k) + 2 * zoom, y1 = Math.floor(c[2][1] * k) - 2 * zoom;
  if (x1 <= x0 || y1 <= y0) return []; const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data, out = []; for (let i = 0; i < d.length; i += 4) out.push([d[i], d[i + 1], d[i + 2]]); return out; }"""


def test_running_water_is_one_surface_stepping_down_with_no_seam_and_none_on_the_dry_land(browser, server):
    """A river comes to a plain a level under it (a flat shore): its water runs east a level less a tile (7 to 1) and
    stops (you up on the meadow south of it). The owner's picture: boxes of different tints laid over each other, a dark sliver at a step, a light box at
    the end. Now: the water over each tile is tinted as much as over the others (one surface, not stacked or thinned
    tints); across each step down there is no px of another colour (the bed's earth through a missing side); the dry
    plain past its end and the meadow up on its south bank are as they were dry; and running water three levels deep
    (a pit in the plain) is no darker than a still pond: see-through, never an opaque slab."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    try:
        g.stamp(-7, -8, ["." * 11] * 7, levels=["a" * 11] * 7)                        # the plain, a level down, north of you
        g.stamp(-3, -4, [".."] * 2, levels=["ff"] * 2)                                # a pit in it, five more down (water fills it full)
        g.stamp(5, -4, ["((("] * 3)                                                   # a still pond on the meadow east of it, for its deep tint
        g.rest()
        wet, rows = range(-6, 1), (-4, -3)                                            # (where it will run: 7 at -6 ... 1 at 0; its middle rows)
        face = lambda dx: -1 + (1 - dx) / 8                                           # (its face: cell 0 at level 1 - dx)
        dry = {(dx, dy): g.js(TILE, [x + dx, y + dy, face(dx)]) for dx in wet for dy in rows}
        past = {(dx, dy): g.js(TILE, [x + dx, y + dy, -1]) for dx in (1, 2, 3) for dy in rows}
        bank = {(dx, -1): g.js(TILE, [x + dx, y - 1, 0]) for dx in range(-6, 5) if abs(dx) > 1}   # (the meadow along its south bank; not under you)
        g.stamp(-7, -8, ["~"] * 7, levels=["0"] * 7)                                  # a river at the plain's west end, a level up
        g.wait(f"Flow.at({x}, {y - 4}, 0) === 1 && Flow.at({x}, {y - 3}, 0) === 1", 15000)
        g.sleep(1500)
        g.rest()
        shot(g, "plain")
        got = [g.js(f"[{','.join(f'Flow.at({x + dx}, {y + dy}, 0)' for dx in range(-6, 4))}]") for dy in rows]
        assert got == [[7, 6, 5, 4, 3, 2, 1, 0, 0, 0]] * 2, got
        # ONE SURFACE: how much of the water's tint lies over each tile (0: none, 1: all of it; wet = dry + k (tint - dry)),
        # alike over all of them, to the last. (The film's end was hardly tinted, k .1: "a light box"; tints laid over
        # each other were more than one's.) Not the tile beside the river (the river's deeper water covers its near part), nor the pit
        k = {}
        for key, d in dry.items():
            if key[0] in (-6, -3, -2):
                continue
            w, t = g.js(TILE, [x + key[0], y + key[1], face(key[0])]), [T - c for T, c in zip(TINT, d)]
            k[key] = sum((p - q) * r for p, q, r in zip(w, d, t)) / sum(r * r for r in t)
        assert min(k.values()) > .35 and max(k.values()) - min(k.values()) < .12, k
        # NO SEAM at a step down: across each tile's east edge, from its face down to the next one's, every px is water's
        # (the bed showed through there, untinted: a dark sliver; the east side was never drawn)
        for dx in (-6, -5, -1):
            for dy in rows:
                X, Y = x + dx + 1, y + dy
                a, b = g.js("([x, y, z]) => HdLook.screenOf(x, y, z)", [X, Y + .3, face(dx)]), g.js("([x, y, z]) => HdLook.screenOf(x, y, z)", [X, Y + .7, face(dx + 1)])
                px = g.js(BOX, [min(a[0], b[0]) - 3, a[1], max(a[0], b[0]) + 3, b[1]])
                bad = [p for p in px if p[2] - p[0] < 8]
                assert not bad, (dx, dy, bad[:6], len(px))
        # NONE ON THE DRY LAND: the plain past its end and the meadow up on its south bank as they were
        for k, was in {**past, **bank}.items():
            now = g.js(TILE, [x + k[0], y + k[1], -1 if k[1] < -1 else 0])
            assert max(abs(p - q) for p, q in zip(now, was)) <= 8, (k, was, now)
        # SEE-THROUGH, NEVER A SLAB: no px of running water darker than the still pond's darkest (the pit full under
        # the river was the open sea's dark band, opaque: a flat navy slab, as a flood over the meadow)
        def dark(dx, dy, z):                                                          # (a tile's darkest px but two, r + g + b)
            px = sorted(sum(p) for p in g.js(TILEPX, [x + dx, y + dy, z]))
            return px[2] if len(px) > 20 else None
        run = {(dx, dy): dark(dx, dy, face(dx)) for dx in range(-5, 1) for dy in rows}
        pond = {(dx, dy): dark(dx, dy, 0) for dx in (5, 6, 7) for dy in (-4, -3, -2)}
        assert run[(-3, -4)] is not None and run[(-2, -3)] is not None and pond[(6, -3)] is not None, (run, pond)   # (the pit and the pond's middle are read)
        assert min(v for v in run.values() if v) >= min(v for v in pond.values() if v), (run, pond)   # (the slab: 316 to 337, the pond 341, see-through 368)
        assert g.js("HdLook.raw ? HdLook.raw() : 0") == 0
    finally:
        tidy(g, x, y)
