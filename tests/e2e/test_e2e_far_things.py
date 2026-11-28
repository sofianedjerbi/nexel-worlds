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
        try:
            g.rpc("dev_creatures", clear=120)              # (its hens and cows stood still on the far land, which a later test's page is told of too: drawn there, a phone's frame drew once more)
        except Exception:
            pass
        ctx.close()


# each frame, what stands past the horizon (a tree, a stone, a creature) whose top is on the picture over the land in front of it (its sprite's top, px
# for px; a creature's, a sprite cell (CELL) over its feet: the most a body is tall), higher than every drawn top between you and it in its column, and that
# is not drawn -> [your y, tops seen, [[what, dy, its top's y, the land's line]...]]
CROWNS = """([x0, x1, y0, y1, ids]) => { const p = myPos(), tx = Math.round(p.x), ty = Math.round(p.y), H = innerHeight, W = innerWidth, f = HdLook.far, b = HdLook.box, u = View.u;
  const on = (x, y) => (f && x >= f[0] && x <= f[2] && y >= f[1] && y <= f[3]) || (b && x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]);
  const top = (x, y) => { const c = Voxels.host.column(x, y); return c && c.length ? c[c.length - 1] : 0; };
  const line = (x, y) => { let l = 1e9; for (let yy = y + 1; yy <= ty; yy++) if (on(x, yy)) { const q = HdLook.screenOf(x + .5, yy + .5, top(x, yy)); if (q) l = Math.min(l, q[1]); } return l; };
  const drawn = new Set(HdLook.stands().map(([x, y]) => x + ',' + y)), miss = []; let n = 0;
  const look = (what, x, y, z, tall, isDrawn) => { const a = HdLook.screenOf(x + .5, y + .5, z); if (!a) return; const t = a[1] - tall * u, l = line(x, y);
    if (t < Math.min(l, H) - u && a[0] >= 0 && a[0] <= W) { n++; if (!isDrawn()) miss.push([what, y - ty, Math.round(t), Math.round(l)]); } };
  for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) { const c = combAt(x, y); if (c !== 'T' && c !== 'M') continue; const s = objectSprite(c, x, y, 0, []); if (s && s[0]) look(c, x, y, top(x, y), s[4], () => drawn.has(x + ',' + y)); }
  for (const i of ids) { const q = ents.get('cow' + i); if (q) look('cow', Math.round(q.x), Math.round(q.y), q.e && typeof q.e.z === 'number' ? q.e.z : top(Math.round(q.x), Math.round(q.y)), CELL, () => HdLook.drawnAt(q) !== null); }
  return [ty, n, miss]; }"""


@pytest.mark.parametrize("w,h", [(1440, 900), (390, 844)])
def test_what_stands_past_the_horizon_is_drawn_from_the_first_frame_its_top_shows(browser, server, w, h):
    """The owner: far trees and mobs "still appear out of nowhere; they should be visible as soon as the horizon shows up":
    all that stands on the land is drawn as soon as any px of it could be seen, its sprite's highest point included. Tall
    trees, stones and cows on flat land past the horizon, the land bending away under it: walking to them, a top shows over
    the land in front of it before its own tile's row does. On every frame any px of a top is over that land on the picture,
    what it is the top of is drawn. Each frame reads its own picture: the same at 16 ms a frame as at 300."""
    ctx = browser.new_context(viewport={"width": w, "height": h}, **({"has_touch": True, "is_mobile": True, "device_scale_factor": 3} if w < h else {}))
    try:
        g = Game(ctx.new_page(), server)
        g.join(new_name("fc"), 2)
        g.js("setOpt('names', false); setOpt('hints', false); setOpt('view', 37)")
        g.rpc("dev_creatures", clear=120)
        g.rest()
        x, y = g.pos()
        far = g.js("HdLook.far")[1] - y                        # (the far land's last row, from you)
        g.stamp(-6, far + 4, ["." * 13] * (-far - 4))          # (flat meadow up to it)
        g.stamp(-6, far - 8, ["T.M.T.M.T.M.T" if i % 4 == 0 else "." * 13 for i in range(36)])   # (trees and stones on it, from 8 rows past the far land's last row to 27 in: past the horizon)
        cows = [g.rpc("dev_creatures", kind="cow", dx=dx, dy=far + 6 + 4 * k, still=100000)["spawned"] for k, dx in enumerate((-5, 1, 5))]
        g.rest()
        g.until(f"[{','.join(str(i) for i in cows)}].every((i) => ents.has('cow' + i))", 300)
        args = [x - 6, x + 6, y + far - 8, y + far + 28, cows]
        g.js("([a]) => { window._cr = []; const f0 = window._f0 = frame; frame = function (now) { f0(now); if (HdLook.live) window._cr.push((" + CROWNS + ")(a)); }; return 1; }", [args])
        g.page.keyboard.down("Shift")
        g.page.keyboard.down("w")
        g.until(f"myPos().y <= {y + far + 40}", 1500)
        g.page.keyboard.up("w")
        g.page.keyboard.up("Shift")
        rec = g.js("(() => { frame = window._f0; return window._cr; })()")
        assert [r for r in rec if r[1]], f"no top ever on the picture: {len(rec)} frames, first {rec[:1]}, last {rec[-1:]}"
        bad = [r for r in rec if r[2]]
        assert not bad, f"{len(bad)} of {len(rec)} frames with a top over the land in front and what it is the top of not drawn: " + json.dumps(bad[:6])
    finally:
        try:
            g.rpc("dev_creatures", clear=120)              # (its hens and cows stood still on the far land, which a later test's page is told of too: drawn there, a phone's frame drew once more)
        except Exception:
            pass
        ctx.close()
