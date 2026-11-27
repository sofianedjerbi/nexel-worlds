"""What stands on the far land and who walks there are drawn as far as the land is (#380, hd_stands.js things, state.js
watch). The owner: "far trees and mobs aren't drawn until you're close enough, then appear at once". The land made round
you (HdLook.box) had its trees; the far land drawn past it to the horizon (HdLook.far, 40 tiles more) had none, and the
server told of who was on the land the picture showed half a second before: a far hill came up over the horizon bare,
its hens three frames after its land, its trees as it came into the box."""

import json

import pytest
from game import Game, new_name

# each frame, the hill's tiles whose top is on the picture (a top over all the nearer ones' in its column, on the land
# drawn: HdLook.far, the box round you) with a tree undrawn, or a hen not told of or undrawn -> [your y, trees seen,
# hens seen, [dy of an undrawn tree...], [dy of an undrawn hen...], HdLook.far]
SEEN = """([x0, x1, y1, hens]) => { const p = myPos(), tx = Math.round(p.x), ty = Math.round(p.y), W = innerWidth, H = innerHeight, f = HdLook.far, b = HdLook.box;
  const col = (x, y) => { const c = Voxels.host.column(x, y); return c && c.length ? c[c.length - 1] : null; };
  const drawn = new Set(HdLook.stands().map(([x, y]) => x + ',' + y)), seen = new Set(), trees = [], miss = [], hmiss = []; let hn = 0;
  for (let x = x0; x <= x1; x++) { let sky = 1e9; for (let y = ty + 10; y >= y1; y--) { const t = col(x, y), on = (f && x >= f[0] && x <= f[2] && y >= f[1] && y <= f[3]) || (b && x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]);
    if (t === null || !on) continue; const a = HdLook.screenOf(x + .5, y + .5, t); if (!a || a[1] >= sky) continue; sky = a[1];
    if (a[0] >= 0 && a[0] <= W && a[1] >= 0 && a[1] <= H) seen.add(x + ',' + y); } }
  for (const k of seen) { const [x, y] = k.split(',').map(Number); if (combAt(x, y) === 'T') { trees.push(k); if (!drawn.has(k)) miss.push(y - ty); } }
  for (const [x, y] of hens) if (seen.has(x + ',' + y)) { hn++; if (![...ents.values()].some((q) => q.e && q.e.kind === 'chicken' && Math.round(q.x) === x && Math.round(q.y) === y && HdLook.drawnAt(q) !== null)) hmiss.push(y - ty); }
  return [ty, trees.length, hn, miss, hmiss, f]; }"""


@pytest.mark.parametrize("w,h", [(1440, 900), (390, 844)])
def test_a_far_hill_past_the_land_round_you_has_its_trees_and_hens_on_every_frame_its_land_is_drawn(browser, server, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, **({"has_touch": True, "is_mobile": True, "device_scale_factor": 3} if w < h else {}))
    try:
        g = Game(ctx.new_page(), server)
        g.join(new_name("ft"), 2)
        g.js("setOpt('names', false); setOpt('hints', false); setOpt('view', 37)")   # (the land shows past the box round you: the far land's hills)
        g.rpc("dev_creatures", clear=120)
        g.rest()
        x, y = g.pos()
        f = g.js("HdLook.far")
        front = f[1] - y + 4                                  # (the hill's south row, 4 rows into the far land: past the box, a far hill)
        box = g.js("HdLook.box")
        assert y + front < box[1], (f, box, (x, y))
        g.stamp(-4, front, ["." * 9] * (-front))              # (a meadow up to it, to walk on)
        g.stamp(-10, front - 20, ["T.T.T.T.T.T.T.T.T.T.T" if i % 3 == 1 else "." * 21 for i in range(20)], levels=["9" * 21] * 20)
        hens = [(dx, front - 1 + dx % 2) for dx in range(-9, 10, 3)]
        ids = [g.rpc("dev_creatures", kind="chicken", dx=dx, dy=dy, still=100000)["spawned"] for dx, dy in hens]
        g.rest()
        # (the server tells of them while you stand there: their land is drawn, past the box)
        g.until(f"[{','.join(str(i) for i in ids)}].every((i) => ents.has('chicken' + i))", 300)
        args = [x - 10, x + 10, y + front - 20, [[x + dx, y + dy] for dx, dy in hens]]
        g.js("([a]) => { window._seen = []; const f0 = window._f0 = frame; frame = function (now) { f0(now); if (HdLook.live) window._seen.push((" + SEEN + ")(a)); }; return 1; }", [args])
        g.page.keyboard.down("Shift")
        g.page.keyboard.down("w")
        g.until(f"myPos().y <= {y + front + 12}", 1500)       # (walked till the hill is 12 rows off: it came into the box)
        g.page.keyboard.up("w")
        g.page.keyboard.up("Shift")
        rec = g.js("(() => { frame = window._f0; return window._seen; })()")
        trees, hn = [r for r in rec if r[1]], [r for r in rec if r[2]]
        assert trees and hn, f"the hill never on the picture: {len(rec)} frames, first {rec[:1]}, last {rec[-1:]}"
        bad = [r for r in rec if r[3] or r[4]]
        assert not bad, f"{len(bad)} of {len(rec)} frames with the hill's land drawn and a tree or hen on it not: " + json.dumps(bad[:6])
    finally:
        ctx.close()
