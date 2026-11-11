// Relief, stacked: each level is drawn STEP px higher than the one under it (level 1 too: every +1 looks alike), with everything standing on it, so a
// two-layer drop looks taller than a one-layer one. A block's ground canvas is drawn as it is (level 1 in place),
// then for each level k >= 1 a copy of it cut to the tiles at least that high, lifted. Where a lifted level ends
// over lower ground its wall is painted down to the ground below: solid earth, a band per layer (lit along its top,
// darker at its foot), in the colours of that layer's own sheet, the pack's ink at the very foot.

const STEP = 6;                                       // art px a level
const shOf = (L) => (L > 0 ? STEP * L : 0);           // how far up a level is drawn: every layer the same step
const WALL_M = STEP * 14 + 16;                        // room under a layer canvas for its walls

// Screen px something on tile (x, y) is drawn higher by
const liftAt = (x, y) => shOf(levelAt(x, y)) * zoom;
// ...and someone between two tiles: in proportion to how far along they are
function liftOf(p) {
  const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
  const f = ax === bx ? p.y - ay : p.x - ax, a = liftAt(ax, ay), b = liftAt(bx, by);
  return a + (b - a) * f;
}

// A sheet's colours, read off its own tiles: its wall bands [lit, mid, dark] (its south face) and its side edge from
// the outside in (its west edge tile), which the ledges are drawn in; and its plain top
const sheetCols = new Map();
function colsOf(sheet) {
  if (sheetCols.has(sheet)) return sheetCols.get(sheet);
  const c = document.createElement("canvas"); c.width = sheet.width; c.height = sheet.height;
  const g = c.getContext("2d"); g.drawImage(sheet, 0, 0);
  const data = g.getImageData(0, 0, c.width, c.height).data, at = (x, y) => Array.from(data.slice((y * c.width + x) * 4, (y * c.width + x) * 4 + 4));
  const [ex, ey] = blobCell(N_ | E_ | W_ | NE | NW), [wx, wy] = blobCell(N_ | S_ | E_ | NE | SE), [ix, iy] = blobCell(255);
  let ink = 15; while (ink > 0 && at(ex * 16 + 8, ey * 16 + ink)[3] === 0) ink--;
  const l = at(ex * 16 + 8, ey * 16 + ink - 1), d = at(ex * 16 + 8, ey * 16 + ink - 2);
  let w0 = 0; while (w0 < 15 && at(wx * 16 + w0, wy * 16 + 8)[3] < 128) w0++;
  const side = [0, 1, 2, 3].map((i) => at(wx * 16 + w0 + i, wy * 16 + 8));
  const out = {bands: [l, [(d[0] + l[0]) / 2, (d[1] + l[1]) / 2, (d[2] + l[2]) / 2], d], side, top: at(ix * 16 + 8, iy * 16 + 8)};
  sheetCols.set(sheet, out); return out;
}

// Grow a shape (0/1 per px, w x h) n px to the left and right
function dilateH(m, w, h, n) {
  const out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    let last = -1e9;
    for (let x = 0; x < w; x++) { if (m[y * w + x]) last = x; if (x - last <= n) out[y * w + x] = 1; }
    last = 1e9;
    for (let x = w - 1; x >= 0; x--) { if (m[y * w + x]) last = x; if (last - x <= n) out[y * w + x] = 1; }
  }
  return out;
}

// The lifted levels of a block, built when its ground canvas changed. Each level k: its body (a 6 px wall band, lit
// at its top, dark at its foot), the ledge round the level above it (LEDGE px, in the sheet's own side-edge colours:
// a +3 shows three edges on every side), then its own tiles on top, where you stand. Worked out over the block and a
// tile round it, so ledges cross block borders.
const LEDGE = 3;
function buildRelief(b) {
  const M = 16, Wb = B * 16, Wm = Wb + 2 * M, Hb = Wb + WALL_M;
  let maxLv = 0;
  for (let ty = -1; ty <= B; ty++) for (let tx = -1; tx <= B; tx++) maxLv = Math.max(maxLv, levelAt(b.bx * B + tx, b.by * B + ty));
  const layers = [], shape = {};
  let above = null;
  for (let k = maxLv; k >= 1; k--) {                    // the shapes, from the top down: each grows round the one above
    const oc = document.createElement("canvas"); oc.width = oc.height = Wm;
    const og = oc.getContext("2d");
    for (let ty = -1; ty <= B; ty++) for (let tx = -1; tx <= B; tx++) {
      const x = b.bx * B + tx, y = b.by * B + ty;
      if (levelAt(x, y) >= k) drawBlobLayer(og, hillSheet(k), x, y, (cc, gg, ux, uy) => levelAt(ux, uy) >= k, (tx + 1) * 16, (ty + 1) * 16, 0);
    }
    const od = og.getImageData(0, 0, Wm, Wm).data, own = new Uint8Array(Wm * Wm);
    for (let i = 0; i < own.length; i++) own[i] = od[i * 4 + 3] > 128 ? 1 : 0;
    const sh = above ? dilateH(above, Wm, Wm, LEDGE) : new Uint8Array(Wm * Wm);
    for (let i = 0; i < own.length; i++) sh[i] = sh[i] || own[i];
    shape[k] = {own, sh, oc}; above = sh;
  }
  for (let k = 1; k <= maxLv; k++) {
    const {own, sh, oc} = shape[k], cols = colsOf(hillSheet(k)), img = new ImageData(Wb, Hb), d = img.data;
    const put = (x, y, c) => { const i = (y * Wb + x) * 4; d[i] = c[0]; d[i + 1] = c[1]; d[i + 2] = c[2]; d[i + 3] = 255; };
    for (let s = 0; s < STEP; s++) {                    // the body: its wall, a band, below every px of the shape
      const c = s === STEP - 1 ? cols.bands[0] : s === 0 ? cols.bands[2] : cols.bands[1], dy = STEP - s;
      for (let y = 0; y < Wb; y++) for (let x = 0; x < Wb; x++) if (sh[(y + M) * Wm + x + M]) put(x, y + dy, c);
    }
    for (let y = 0; y < Wb; y++) for (let x = 0; x < Wb; x++) {       // the ledge, where the shape is not its own tiles
      const i = (y + M) * Wm + x + M;
      if (!sh[i] || own[i]) continue;
      let ownL = false, ownR = false;
      for (let j = 1; j <= LEDGE; j++) { if (own[i - j]) ownL = true; if (own[i + j]) ownR = true; }
      if (ownL && ownR) { put(x, y, cols.top); continue; }   // (a sliver between two of its own edges: its top)
      let dd = 0;                                        // how far in from the ledge's outer side
      while (dd < 3 && sh[i - dd - 1] && sh[i + dd + 1]) dd++;
      put(x, y, cols.side[dd]);
    }
    const c = document.createElement("canvas"); c.width = Wb; c.height = Hb;
    const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    g.putImageData(img, 0, 0);
    const t = document.createElement("canvas"); t.width = Wb; t.height = Wb;   // its own tiles: the ground as drawn, cut
    const tg = t.getContext("2d"); tg.drawImage(oc, M, M, Wb, Wb, 0, 0, Wb, Wb);  //  to the level's own shape
    tg.globalCompositeOperation = "source-in"; tg.drawImage(b.canvas, 0, 0);
    g.drawImage(t, 0, 0);
    layers[k] = c;
  }
  b.relief = {layers, maxLv}; b.reliefDirty = false;
}
// A block's ground, with its levels stacked
function drawBlockRelief(b, sx, sy, S) {
  const X = sx(b.bx * B), Y = sy(b.by * B);
  ctx.drawImage(b.canvas, X, Y, B * S, B * S);
  if (!b.relief || b.reliefDirty) buildRelief(b);
  for (let k = 1; k <= b.relief.maxLv; k++) {
    const c = b.relief.layers[k];
    if (c) ctx.drawImage(c, X, Y - shOf(k) * zoom, B * S, (B * 16 + WALL_M) * zoom);
  }
}
