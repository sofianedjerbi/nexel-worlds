"""PROBE, not for merge (#47): why test_e2e_hd's house test reads you 0.60 seen in the room for 8 s, one run in many.
The same house, the same steps, at the hour every test starts at (join's .3) and at noon, four times
each: in the room, every ~0.4 s for 4 s, the hour, the share of you seen, how much of what is seen is below your
middle (catSeen's box: the px seen outside the box over it), the x-ray window. Fails on purpose, to print."""

import pytest
from test_e2e_hd import AT, PUT, ROOF
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

READ = """() => { const me = ents.get('agent' + myId), m = HdLook.screenOf(me.x + .5, me.y + .5, 0);
  const [all] = HdLook.catSeen([0, 0, innerWidth, innerHeight]), [, low] = HdLook.catSeen([0, 0, innerWidth, m ? m[1] / (cv.width / innerWidth) : 0]);
  return [Math.round(((clock.phase || 0) % 1) * 1000) / 1000, Math.round(all * 100) / 100, low, HdLook.win && HdLook.win.n, HdLook.win && HdLook.win.a,
    !!(HdThings.at(Math.round(me.x), Math.round(me.y) + 1) || []).length]; }"""


# catSeen's own inputs, as it reads them (the sprite's px, then the screen's), and the place your sprite fits the screen
# best (art px, by Z = artPx() * DPR): the share there (catSeen's own, if found), which rows of the sprite fail, and
# some failing (sprite rgb, screen rgb) pairs: a uniform darkening is a shade, a band missing is a cut, all off is a place
DUMP = """() => { const P = CanvasRenderingContext2D.prototype, gi = P.getImageData, r0 = HdView.read; let sp = null, sc = null, share;
  P.getImageData = function (...a) { const d = gi.apply(this, a); if (!sp) sp = {w: this.canvas.width, h: this.canvas.height, d: d.data}; return d; };
  HdView.read = (...a) => { const d = r0(...a); sc = {w: a[2], h: a[3], d: d.data}; return d; };
  try { share = HdLook.catSeen(); } finally { P.getImageData = gi; HdView.read = r0; }
  if (!sp || !sc) return {share, none: [!!sp, !!sc]};
  const Z = artPx() * DPR, me = ents.get('agent' + myId), k = cv.width / innerWidth, m = HdLook.screenOf(me.x + .5, me.y + .5, me.z || 0);
  const gx = Math.round(m[0] * k / Z), gy = Math.round(m[1] * k / Z), ok = (A, B, i, j) => { const o = (j * sp.w + i) * 4,
    X = Math.floor((A + i + .5) * Z), Y = Math.floor((B + j + .5) * Z), p = (Y * sc.w + X) * 4;
    return X >= 0 && Y >= 0 && X < sc.w && Y < sc.h && Math.abs(sc.d[p] - sp.d[o]) + Math.abs(sc.d[p + 1] - sp.d[o + 1]) + Math.abs(sc.d[p + 2] - sp.d[o + 2]) < 60 ? p : -1 - p; };
  let best = [-1, 0, 0], n = 0; for (let j = 0; j < sp.h; j++) for (let i = 0; i < sp.w; i++) if (sp.d[(j * sp.w + i) * 4 + 3] >= 128) n++;
  for (let A = gx - sp.w; A <= gx + 8; A++) for (let B = gy - sp.h; B <= gy + 8; B++) { let c = 0;
    for (let j = 0; j < sp.h; j++) for (let i = 0; i < sp.w; i++) if (sp.d[(j * sp.w + i) * 4 + 3] >= 128 && ok(A, B, i, j) >= 0) c++;
    if (c > best[0]) best = [c, A, B]; }
  const [, A, B] = best, rows = [], bad = [];
  for (let j = 0; j < sp.h; j++) { let f = 0, t = 0; for (let i = 0; i < sp.w; i++) { const o = (j * sp.w + i) * 4; if (sp.d[o + 3] < 128) continue; t++;
    const p = ok(A, B, i, j); if (p < 0) { f++; const q = -1 - p; if (bad.length < 20 && (i + j) % 2 === 0) bad.push([i, j, [sp.d[o], sp.d[o + 1], sp.d[o + 2]], [sc.d[q], sc.d[q + 1], sc.d[q + 2]]]); } }
    if (t) rows.push(j + ':' + f + '/' + t); }
  const tint = [...new Set([...Array(sp.w * sp.h).keys()].filter((q) => sp.d[q * 4 + 3] >= 128).map((q) => sp.d[q * 4] + ',' + sp.d[q * 4 + 1] + ',' + sp.d[q * 4 + 2]))].slice(0, 12);
  return {name: me.e && me.e.name, tint, share, best_share: n ? best[0] / n : 0, at: [A, B], guess: [gx, gy], Z, dpr: DPR, sprite: [sp.w, sp.h], fail_rows: rows.join(' '), bad}; }"""


@pytest.mark.parametrize("hour", [None])
@pytest.mark.parametrize("n", range(10))
def test_probe_the_house(browser, server, hour, n):
    g = hd(browser, server)
    try:
        if hour is not None:
            g.hour(hour)                                                      # (None: the hour join gives every test, .3, game.py)
        x, y = g.pos()
        x0, y0 = x - 1, y - 5
        g.stamp(-1, -5, ["WWWW", "WnnW", "W+WW"])
        g.rpc("dev_give", items={"roof": 12})
        room = [[x0 + 1, y0 + 1, 0], [x0 + 2, y0 + 1, 0]]
        assert g.js(PUT, [[[x0 + i, y0 + j, 3, "roof"] for j in (2, 1, 0) for i in range(4)], room]) == []
        g.rpc("dev_teleport", x=x, y=y, z=0); g.arrive()
        g.js(AT, [x0 + 1.5, y0 + 1.5, 3])
        g.rpc("dev_teleport", x=x0 + 1, y=y0 + 1, z=0); g.arrive()
        rows = []
        for _ in range(10):
            rows.append(g.js(READ))
            g.page.wait_for_timeout(400)
        rows.append(["dump", g.js(DUMP)])
        rows.append(["roof over", g.js(ROOF, [x0 + 1, y0 + 1])])
        raise AssertionError(("PROBE", hour, n, rows))
    finally:
        g.page.close()
