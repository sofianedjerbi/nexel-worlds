// THE POINTER on the HD look's picture (hd.js): the tile under it; a tile's boxes on the screen; and how much of you is seen (tests).
//   HdPick(K) (K: the look's {api, eng, seen, winMap, topAt, south, R, cv, Z}) -> {boxed(x, y, lo)}; it gives api.pick and api.catSeen
const HdPick = (K) => {
  const api = K.api;
  // the px a tile's boxes take on the screen (hd_things.js: a wall, a fence, a door): {x, y, w, h}, or null
  function boxed(x, y, lo) {   // (lo: only the boxes of the storey that starts at that height, px: the aim's corners went round a wall, the wall over it and the roof: two pairs of brackets a storey apart)
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const b of HdThings.at(x, y) || []) if (!b.shade && (lo === undefined || (b.z < lo + 20 && b.z + b.h > lo - 2))) for (let n = 0; n < 8; n++) { const p = api.screenOf(x + (b.x + (n & 1) * b.w) / 16, y + (b.y + (n >> 1 & 1) * b.d) / 16, (b.z + (n >> 2) * b.h) / RELIEF_STEP); if (p) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); } }
    return x1 > x0 ? {x: x0, y: y0, w: x1 - x0, h: y1 - y0} : null;
  }
  // -> the tile under the pointer: what the window shows first (your space's floors, the fronts of the walls north of them: the land over them is not drawn, so it is not pointed at); then from the K.south (the nearest) north, the first whose K.south front or whose top is under it (a front: face, down: levels under its top, as mouse.js). zf: its height, if not the land's as shown (build mode)
  api.pick = (mx, my, zf) => {
    if (!K.eng || !K.seen) return null;
    const inq = (P, q) => { let s = 0; for (let i = 0; i < 4; i++) { const a = q[i], b = q[(i + 1) % 4], c = (b[0] - a[0]) * (P[1] - a[1]) - (b[1] - a[1]) * (P[0] - a[0]); if (c && s && Math.sign(c) !== s) return false; if (c) s = Math.sign(c); } return true; };
    const wmp = K.winMap(), flr = (x, y) => { const b = wmp.get(x + "," + y), t = K.topAt(x, y); return b ? Math.min(t, b[0]) : t; }, zo = (x, y) => (zf ? zf(x, y) : Models.up(x, y) ? liftAt(x, y) / zoom / RELIEF_STEP : flr(x, y)), part = (q) => Math.max(0, Math.min(.999, (my - Math.min(q[0][1], q[1][1])) / Math.max(1, Math.max(q[2][1], q[3][1]) - Math.min(q[0][1], q[1][1]))));
    if (!zf && wmp.size) for (const [x, y, lo, hi] of K.eng.win.tiles.slice().sort((a, b) => b[1] - a[1])) { const q = [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]].map(([a, b]) => api.screenOf(a, b, lo)); if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: part(q)};
      if (!wmp.has(x + "," + (y - 1)) && K.topAt(x, y - 1) > lo) { const f = [[x, y, Math.min(hi, K.topAt(x, y - 1))], [x + 1, y, Math.min(hi, K.topAt(x, y - 1))], [x + 1, y, lo], [x, y, lo]].map((v) => api.screenOf(...v)); if (f.every((v) => v) && inq([mx, my], f)) return {x, y: y - 1, fy: .999, face: true, down: Math.floor(part(f) * (Math.min(hi, K.topAt(x, y - 1)) - lo))}; } }
    for (let y = K.seen.ty + K.south; y >= K.seen.ty - K.R; y--) for (let x = K.seen.tx - K.R; x <= K.seen.tx + K.R; x++) {
      if (!zf) { const c0 = combAt(x, y), pb = c0 && "W%+#g".includes(c0) && HdThings.is(c0, x, y) ? boxed(x, y) : null; if (pb && mx >= pb.x && mx <= pb.x + pb.w && my >= pb.y && my <= pb.y + pb.h) return {x, y, fy: .5}; }   // (a wall, a fence: what stands as boxes is pointed at where it is drawn: the pointer on a wall's front named the ground behind it)
      const z = zo(x, y), zs = zf ? z : zo(x, y + 1);
      if (zs < z) { const q = [[x, y + 1, z], [x + 1, y + 1, z], [x + 1, y + 1, zs], [x, y + 1, zs]].map((v) => api.screenOf(...v)); if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: .999, face: true, down: Math.floor(part(q) * (z - zs))}; }
      const q = [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]].map(([a, b]) => api.screenOf(a, b, z));
      if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: part(q)};
      // ITS SIDES, where the land beside it is lower and the side is turned to the eye (a top leans away from the picture's middle: its west side shows right of it, its east side left). The pointer on a hill's
      // or a cliff's side was on no tile: the classic picture's maths, asked last, named some tile for it
      if (!zf) for (const [X, dx] of [[x, -1], [x + 1, 1]]) { const zn = zo(x + dx, y); if (zn >= z) continue; const f = [[X, y, z], [X, y + 1, z], [X, y + 1, zn], [X, y, zn]].map((v) => api.screenOf(...v));
        if (f.every((v) => v) && (f[1][0] - f[2][0]) * dx < 0 && inq([mx, my], f)) return {x, y, fy: .5}; }
    }
    return null;
  };
  // how much of you is seen (tests): the share of your own drawn px that are on the screen as they are drawn; box [x0, y0, x1, y1] (CSS px): -> [that share, how many of them are seen outside the box]
  api.catSeen = (box) => {
    const s = K.seen && K.seen.me; if (!s || !K.eng) return 0; const a = K.eng.at(s.x, s.y, s.z); if (!a) return 0;
    const sg = s.canvas.getContext("2d").getImageData(0, 0, s.canvas.width, s.canvas.height).data, g = HdView.read(0, 0, K.cv.width, K.cv.height).data;
    let n = 0, ok = 0, out = 0; const B = box && box.map((v) => v * K.cv.width / innerWidth);
    for (let j = 0; j < s.canvas.height; j++) for (let i = 0; i < s.canvas.width; i++) { const o = (j * s.canvas.width + i) * 4; if (sg[o + 3] < 128) continue; n++;
      const X = Math.floor((Math.round(a[0]) - s.fx + i + .5) * K.Z()), Y = Math.floor((Math.round(a[1]) - s.fy + j + .5) * K.Z()), p = (Y * K.cv.width + X) * 4;
      if (X >= 0 && Y >= 0 && X < K.cv.width && Y < K.cv.height && Math.abs(g[p] - sg[o]) + Math.abs(g[p + 1] - sg[o + 1]) + Math.abs(g[p + 2] - sg[o + 2]) < 60) { ok++; if (B && (X < B[0] || X > B[2] || Y < B[1] || Y > B[3])) out++; } }
    return box ? [n ? ok / n : 0, out] : n ? ok / n : 0;
  };
  return {boxed};
};
