"""The x-ray window under the open sky stays YOUR space (vox_style_land.js hollow, hd.js hidAt): at a mountain's foot it is
your few tiles, not the meadow the mountain hides behind it, and walking along a ragged ridge it does not shut for a frame."""

import random

import pytest

from test_e2e_hd_behind import calm, go
from test_e2e_hd_sun import hd
from test_e2e_hd_xray import CHANGED


@pytest.mark.realtime
def test_at_a_mountain_s_foot_the_window_is_your_few_tiles_not_the_meadow_behind_it_and_it_does_not_flicker(browser, server):
    """Owner: "sometimes when moving the whole world disappears, like the camera goes behind the mountain x-raying
    everything". At a mountain's north foot every meadow tile behind it is hidden by it; the window ran through all of
    them (412 tiles, half the screen cut: the mountain gone). Only a hollow (land on two facing sides: a trench, a
    gorge, a strip under a cliff) carries your space on under the open sky (vox_style_land.js hollow). And walking along
    a ragged ridge, a column hiding a fifth of you (under PART) shut the window to your tile for a frame: it holds 300 ms.
    (At the game's own pace: every frame of a walk is looked at. On the tests' clock a land takes four times as much of
    the game's time to make (260 ms, four frames, the window the last land's meanwhile) and you walked two tiles on from
    the window: 15 of its tiles more than 5 from you, two runs in ten; at the game's pace, 10 runs in 10.)"""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    rnd, cols = random.Random(3), []
    for i in range(-12, 13):                                               # a ridge 6 deep, its columns 2 to 8 high, its first row lower here and there
        h = rnd.choice([2, 3, 4, 6, 8])
        for j in range(1, 7):
            cols.append(([x + i, y + j], max(1, h - (j == 1) * rnd.choice([0, 1, 2]))))
    try:
        for t, h in cols:
            g.rpc("dev_col", tiles=[t], col=[h])
        g.rest()
        go(g, x - 10, y)
        # (far: a tile of the window more than 5 from every place you stood in the last half second. The window drawn is the
        # one made for where you were when its land was begun: on a runner drawing every 133 ms that land takes frames, and
        # you were a tile or two on, "14" from where you stood that frame; the meadow behind the mountain is hundreds)
        g.js("""() => { window.__w = []; const was = []; const f = () => { const p = myPos(), w = HdLook.win, now = performance.now(); was.push([now, Math.round(p.x), Math.round(p.y)]); while (now - was[0][0] > 500) was.shift();
          let far = 0; for (const t of w.tiles) if (was.every(([, x, y]) => Math.abs(t[0] - x) + Math.abs(t[1] - y) > 5)) far++;
          window.__w.push([w.n, far]); if (window.__w.length < 3000) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }""")
        g.hold(["d"], 2500)                                                # east along its foot
        w = g.js("window.__w.splice(0)")
        assert len(w) > 20 and max(n for n, _ in w) <= 60 and max(f for _, f in w) <= 12, w      # the window: your tiles near you and a notch of the ridge you pass (it was 250 to 400, the meadow behind it)
        assert min(n for n, _ in w) > 2, w                                 # never shut to your own tile for a frame (the flicker)
        W, H = g.js("[innerWidth, innerHeight]")
        rows = g.js(CHANGED, [0, 0, W, H])
        assert sum(r.count("1") for r in rows) / sum(map(len, rows)) < .25    # the cut: a small part of the screen (it was half of it)
    finally:
        g.rpc("dev_col", tiles=[t for t, _ in cols], col=[0])
