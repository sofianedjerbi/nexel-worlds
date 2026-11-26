// The HD look's paint sheet (hd_things.js): one 1024 x 1024 sheet of px that every box of a thing is painted from, rooms in it
// filled once, the px of a piece of a picture, the game's own painters at zoom 1, and a box cut into the engine's 16 px slots.
//   HdSheet() -> {sheet, SW, room, pix, painted, shotOf, solid, cut, side, push, span, flat}
const HdSheet = () => {
  const SW = 1024, SH = 1024, sheet = {px: new Uint32Array(SW * SH), w: SW, id: "hd"}, rooms = new Map(), pixs = new Map();
  let nx = 0, ny = 0, tall = 0, ids = 0, scratch = null;
  // room for w x h px of paint in the sheet, filled once by fill(put(i, j, px)) -> [u, v]
  function room(key, w, h, fill) {
    let p = rooms.get(key); if (p) return p;
    if (nx + w > SW) { nx = 0; ny += tall; tall = 0; }
    if (ny + h > SH) { rooms.clear(); sheet.px.fill(0); nx = ny = tall = 0; sheet.id = "hd" + (++ids); }   // (full: from none, under a new name so the engine paints its slots again)
    p = [nx, ny]; const ox = nx, oy = ny; fill((i, j, v) => { if (i >= 0 && j >= 0 && i < w && j < h) sheet.px[(oy + j) * SW + ox + i] = v; });
    nx += w; tall = Math.max(tall, h); rooms.set(key, p); return p;
  }
  // the px of a piece of a picture (an image or a canvas): {px, w, h, key}
  function pix(img, sx, sy, w, h) {
    if (!img._hd) img._hd = ++ids; const key = img._hd + "|" + sx + "," + sy + "," + w + "," + h; let p = pixs.get(key); if (p) return p;
    scratch = scratch || document.createElement("canvas"); scratch.width = w; scratch.height = h; const g = scratch.getContext("2d", {willReadFrequently: true});
    g.clearRect(0, 0, w, h); g.drawImage(img, sx, sy, w, h, 0, 0, w, h); p = {px: new Uint32Array(g.getImageData(0, 0, w, h).data.buffer.slice(0)), w, h, key}; pixs.set(key, p); return p;
  }
  // one of the game's own painters on a canvas of its own at zoom 1 (as hd.js draws a body)
  function painted(w, h, fn) {
    const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    drawOn(g, 1, () => { try { fn(g); } catch (e) { /* (nothing to draw) */ } });
    return c;
  }
  const shotOf = (key, w, h, fn) => { let p = pixs.get(key); if (!p) { p = pix(painted(w, h, fn), 0, 0, w, h); p.key = key; pixs.set(key, p); } return p; };   // (...and its px, kept under a name)
  const solid = (v) => (v >>> 24) >= 128;
  // paints cut out of P: rows r0..r1 of its columns c0..c1 (rep: row r0 that many times); a side: each row's px a px in from that edge (w px wide)
  const cut = (P, c0, c1, r0, r1, rep) => room(P.key + "c" + [c0, c1, r0, r1, rep], c1 - c0, rep || r1 - r0, (put) => { for (let j = 0; j < (rep || r1 - r0); j++) for (let i = c0; i < c1; i++) put(i - c0, j, P.px[(rep ? r0 : r0 + j) * P.w + i]); });
  const side = (P, c0, c1, r0, r1, w, east) => room(P.key + "s" + [c0, c1, r0, r1, w, east], w, r1 - r0, (put) => { for (let j = r0; j < r1; j++) { let v = 0, n = 0;
    for (let i = east ? c1 - 1 : c0; i >= c0 && i < c1 && n < 2; i += east ? -1 : 1) if (solid(P.px[j * P.w + i])) { v = P.px[j * P.w + i]; n++; }      // (the second solid px in: past the outline)
    for (let i = 0; i < w; i++) put(i, j - r0, v); } });
  // a box into the list, in pieces a slot of the engine can hold (16 px a side)
  function push(out, b) {
    for (let i = 0; i < b.w; i += 16) for (let j = 0; j < b.d; j += 16) for (let k = 0; k < (b.fh ? 1 : Math.max(1, b.h)); k += 16) {      // (fh: its front is that many rows of paint, whatever its height: one piece)
      const w = Math.min(16, b.w - i), d = Math.min(16, b.d - j), h = b.fh ? b.h : Math.min(16, b.h - k), o = (p, a, c) => (p ? [p[0] + a, p[1] + c] : null);
      out.push({x: b.x + i, y: b.y + j, z: b.z + b.h - k - h, w, d, h, fh: b.fh, shade: b.shade, tilt: b.tilt, k: b.k, sheet, top: k === 0 ? o(b.top, i, j) : null, front: j + 16 >= b.d ? o(b.front, i, k) : null, west: i === 0 ? o(b.west, j, k) : null, east: i + 16 >= b.w ? o(b.east, j, k) : null});
    }
  }
  const span = (P, r0, r1) => { let c0 = P.w, c1 = 0; for (let j = Math.max(0, r0); j < Math.min(P.h, r1); j++) for (let i = 0; i < P.w; i++) if (solid(P.px[j * P.w + i])) { c0 = Math.min(c0, i); c1 = Math.max(c1, i + 1); } return c1 > c0 ? [c0, c1] : [0, P.w]; };
  const flat = (v, w, h, inkv, edges = "") => room("f" + [v, w, h, inkv, edges], w, h, (put) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) put(i, j, (edges.includes("n") && !j) || (edges.includes("s") && j === h - 1) || (edges.includes("w") && !i) || (edges.includes("e") && i === w - 1) ? inkv : v); });
  return {sheet, SW, room, pix, painted, shotOf, solid, cut, side, push, span, flat};
};
