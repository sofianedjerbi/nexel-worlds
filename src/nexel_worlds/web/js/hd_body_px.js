// A body's own px (hd.js ent, the marks drawn over the picture): which px of a sprite are its own, read from what it is
// drawn from, never read back from the drawn picture mid-frame. HdLevel hands these on (hd_level.js).
//   HdBodyPx.drawsOf(c, g, draw), runsOf(c), cut(g, me, a, zs), body(me, a, zs)
const HdBodyPx = (() => {
  // cut(g, me, a, zs): nothing drawn on g after it (till g.restore) lies on your body: its own px are cut out of the marks (me: your sprite {canvas, fx, fy}, a: its foot on g, zs: g's units an art px). A box at your tile covered all of you
  // body(me, a, zs) -> your sprite's box on g ({x, y, w, h}: the bounds of its own px): no key's box is drawn in it, and one it covers most of is not drawn at all (target.js: it framed your head)
  const runs = new WeakMap(), poses = new Map();
  // WHAT A BODY IS DRAWN FROM (hd.js ent): drawsOf(c, g, draw) runs draw with g's drawImage calls kept on c (_draws: [source, its
  // arguments, the transform then]); any other painting call, or a see-through alpha, and the picture's shape is read back from c
  // instead (_draws null). A body's shape is had from its sources' px, each read ONCE (alphaOf): reading the body back, on a CPU
  // renderer, waited for the GPU's frame: 1 to 7 s a pose, by a fire under the land (#67)
  const PAINTS = ["fillRect", "strokeRect", "fill", "stroke", "fillText", "strokeText", "putImageData"];
  function drawsOf(c, g, draw) {
    if (!g._kept) { g._kept = true; const di = g.drawImage; g.drawImage = function (src, ...a) { if (c._draws) { if (this.globalAlpha < 1) c._draws = null; else c._draws.push([src, a, this.getTransform()]); } return di.call(this, src, ...a); };
      for (const k of PAINTS) { const f = g[k]; g[k] = function (...a) { c._draws = null; return f.apply(this, a); }; } }
    c._draws = []; try { draw(); } finally { if (c._draws) c._draws = c._draws.slice(); c._kept = c._draws; c._draws = null; }
  }
  const alphas = new WeakMap();   // (a source's alpha, a byte a px: read once for each picture it is (its _v), not each pose)
  function alphaOf(src) {
    const v = src._v ?? 0, k = alphas.get(src); if (k && k.v === v) return k;
    const w = src.width, h = src.height, cx = src.getContext ? src.getContext("2d", {willReadFrequently: true}) : null; if (!cx || !w || !h) return null;
    const d = cx.getImageData(0, 0, w, h).data, a = new Uint8Array(w * h); for (let i = 0; i < w * h; i++) a[i] = d[i * 4 + 3] >= 128 ? 1 : 0;
    const r = {v, w, h, a}; alphas.set(src, r); return r;
  }
  // the px of c its kept draws cover (1: opaque), or null: one it cannot tell (a source that is no canvas, a turned transform)
  function maskOf(c) {
    const W = c.width, H = c.height, m = new Uint8Array(W * H);
    for (const [src, a, t] of c._kept) {
      if (t.b || t.c || !t.a || !t.d) return null; const A = alphaOf(src); if (!A) return null;
      const [sx, sy, sw, sh, dx, dy, dw, dh] = a.length >= 8 ? a : a.length >= 4 ? [0, 0, A.w, A.h, a[0], a[1], a[2], a[3]] : [0, 0, A.w, A.h, a[0], a[1], A.w, A.h];
      const x0 = t.a * dx + t.e, x1 = t.a * (dx + dw) + t.e, y0 = t.d * dy + t.f, y1 = t.d * (dy + dh) + t.f;
      const X0 = Math.max(0, Math.floor(Math.min(x0, x1))), X1 = Math.min(W, Math.ceil(Math.max(x0, x1))), Y0 = Math.max(0, Math.floor(Math.min(y0, y1))), Y1 = Math.min(H, Math.ceil(Math.max(y0, y1)));
      for (let Y = Y0; Y < Y1; Y++) { const ly = (Y + .5 - t.f) / t.d; if (ly < dy || ly >= dy + dh) continue; const v = Math.floor(sy + (ly - dy) * sh / dh); if (v < 0 || v >= A.h) continue;
        for (let X = X0; X < X1; X++) { const lx = (X + .5 - t.e) / t.a; if (lx < dx || lx >= dx + dw) continue; const u = Math.floor(sx + (lx - dx) * sw / dw); if (u >= 0 && u < A.w && A.a[v * A.w + u]) m[Y * W + X] = 1; } } }
    return m;
  }
  function runsOf(c) {   // (a sprite's own px: runs of a row [x, y, n, ...], and their bounds b [x0, y0, x1, y1])
    if (!c || !c.width) return null; let r = runs.get(c); if (r && r.v === c._v) return r;
    const pk = c._h === undefined ? null : c.width + "x" + c.height + ":" + c._h, kept = pk && poses.get(pk);   // (a picture made by the same calls as one read before (canvas._h, hd.js): the same px. A walk's eight poses were read back from the canvas at every change: an eighth of a phone's sprint)
    if (kept) { runs.set(c, r = {v: c._v, l: kept.l, b: kept.b}); return r; }
    const w = c.width, mk = c._kept ? maskOf(c) : null, d = mk ? null : c.getContext("2d", {willReadFrequently: true}).getImageData(0, 0, w, c.height).data, l = [], b = [1e9, 1e9, -1, -1];
    const opaque = mk ? (i, j) => mk[j * w + i] === 1 : (i, j) => d[(j * w + i) * 4 + 3] >= 128;
    for (let j = 0; j < c.height; j++) { let i0 = -1; for (let i = 0; i <= w; i++) { const on = i < w && opaque(i, j); if (on && i0 < 0) i0 = i; else if (!on && i0 >= 0) { l.push(i0, j, i - i0); b[0] = Math.min(b[0], i0); b[1] = Math.min(b[1], j); b[2] = Math.max(b[2], i); b[3] = Math.max(b[3], j + 1); i0 = -1; } } }
    runs.set(c, r = {v: c._v, l, b: b[2] >= 0 ? b : null}); if (pk) { if (poses.size > 400) poses.clear(); poses.set(pk, r); } return r;
  }
  function cut(g, me, a, zs) {
    const r = me && a && runsOf(me.canvas); if (!r) return;
    const x0 = Math.round(a[0] / zs) - me.fx, y0 = Math.round(a[1] / zs) - me.fy; g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); for (let i = 0; i < r.l.length; i += 3) g.rect((x0 + r.l[i]) * zs, (y0 + r.l[i + 1]) * zs, r.l[i + 2] * zs, zs); g.clip("evenodd");
  }
  const body = (me, a, zs) => { const r = me && a && runsOf(me.canvas); if (!r || !r.b) return null; const x0 = Math.round(a[0] / zs) - me.fx, y0 = Math.round(a[1] / zs) - me.fy; return {x: (x0 + r.b[0]) * zs, y: (y0 + r.b[1]) * zs, w: (r.b[2] - r.b[0]) * zs, h: (r.b[3] - r.b[1]) * zs}; };
  return {drawsOf, runsOf, cut, body};
})();
