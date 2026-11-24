"""What a frame costs the script with things in the air (render.js frame: the game's step and the HD look's picture):
twelve creatures round you, and for five seconds chips, sparks, smoke, orbs and drops let go ten times a second.
A measure, with a generous bound: the machine counts as much as the code (README.md rule 6)."""

import json
import os

import pytest
from test_e2e_hd_sun import hd

# five seconds of it: every frame's ms in the page's own frame -> [ms...], and how many things were in the air at the most
BUSY = """() => new Promise((ok) => { const out = [], f0 = window.frame, p = myPos(), t0 = performance.now(); let last = 0, most = 0, done = false;
  window.frame = function (now) { if (done) return f0(now); const s = performance.now() - t0;
    if (s - last > 100) { last = s; const x = p.x + Math.round(Math.random() * 8 - 4), y = p.y + Math.round(Math.random() * 6 - 3);
      burst(x, y, 'spark', 12, {dy: -.4, g: 3}); burst(x + 1, y, 'dust', 8); smoke(x, y + 1, 6); spawnOrbs({x, y, n: 5, name: me}); dropLoot(x - 1, y, {wood: 1, stone: 1, plank: 1}, performance.now()); }
    const t = performance.now(); f0(now); out.push(performance.now() - t); most = Math.max(most, parts.length + puffs.length + orbs.length + loot.length);
    if (s > 5000) { done = true; window.frame = f0; ok([out, most]); } }; })"""


@pytest.mark.realtime
@pytest.mark.parametrize("w, h, zoom", [(1440, 900, 3), (844, 390, 2)])
def test_a_frame_with_things_in_the_air_costs_the_script_little(browser, server, w, h, zoom):
    from conftest import Game, new_name
    g = Game(browser.new_page(viewport={"width": w, "height": h}), server)
    g.join(new_name("cost"), zoom)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    for i in range(12):
        g.spawn("cow" if i % 2 else "chicken", -5 + i % 6 * 2, -3 + i // 6 * 5, still=10 ** 6)
    g.rest()
    runs = []
    for _ in range(3):                                       # (the best of three: one is enough on a quiet machine)
        ms, most = g.js(BUSY)
        ms = sorted(ms[5:])
        runs.append((len(ms), round(ms[len(ms) // 2], 2), round(ms[int(len(ms) * .99)], 2), round(ms[-1], 1), most))
        if runs[-1][2] < 12:
            break
    if os.environ.get("COST_TAG"):
        with open(f"/Users/sdjerbi/.claude/jobs/fa29ccbd/tmp/place-cost2-{os.environ['COST_TAG']}.jsonl", "a") as f:
            f.write(json.dumps({"size": [w, h], "load": round(os.getloadavg()[0], 1), "[frames, p50, p99, max, most in the air]": runs}) + "\n")
    best = min(runs, key=lambda r: r[2])
    assert best[0] > 100 and best[4] > 80, runs              # (frames came, and things were in the air)
    assert best[1] < 6 and best[2] < 16, runs                # (half the frames under 6 ms of script, 99 in 100 under a frame's 16)
    assert not g.errors
    g.page.close()
