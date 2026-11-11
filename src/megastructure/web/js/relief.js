// Relief, stacked: each level is drawn STEP px higher than the one under it, with everything standing on it, so a
// two-layer drop looks taller than a one-layer one. A block's ground canvas is drawn as it is (level 1 in place),
// then for each level k >= 2 a copy of it cut to the tiles at least that high, lifted. Where a lifted level ends
// over lower ground its wall is painted down to the ground below: solid earth, a band per layer (lit along its top,
// darker at its foot), in the colours of that layer's own sheet, the pack's ink at the very foot.

const STEP = 6;                                       // art px a level
const shOf = (L) => (L > 1 ? STEP * (L - 1) : 0);     // how far up a level is drawn (levels 0 and 1: in place)
const WALL_M = STEP * 14 + 16;                        // room under a layer canvas for its walls

// Screen px something on tile (x, y) is drawn higher by
const liftAt = (x, y) => shOf(levelAt(x, y)) * zoom;
// ...and someone between two tiles: in proportion to how far along they are
function liftOf(p) {
  const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
  const f = ax === bx ? p.y - ay : p.x - ax, a = liftAt(ax, ay), b = liftAt(bx, by);
  return a + (b - a) * f;
}

// A sheet's south face, from its plain south-edge tile: the row it starts on, its colours [lit, mid, dark, ink], and
// for each blob cell which columns carry it (a rounded corner carries fewer)
const faces = new Map();
function faceOf(sheet) {
  if (faces.has(sheet)) return faces.get(sheet);
  const c = document.createElement("canvas"); c.width = sheet.width; c.height = sheet.height;
  const g = c.getContext("2d"); g.drawImage(sheet, 0, 0);
  const data = g.getImageData(0, 0, c.width, c.height).data, at = (x, y) => data.slice((y * c.width + x) * 4, (y * c.width + x) * 4 + 4);
  const [ex, ey] = blobCell(N_ | E_ | W_ | NE | NW), [ix, iy] = blobCell(255);
  let ink = 15; while (ink > 0 && at(ex * 16 + 8, ey * 16 + ink)[3] === 0) ink--;
  const top = at(ix * 16 + 8, iy * 16 + 8), l = at(ex * 16 + 8, ey * 16 + ink - 1), d = at(ex * 16 + 8, ey * 16 + ink - 2), k = at(ex * 16 + 8, ey * 16 + ink);
  const css = (a) => `rgb(${a[0] | 0},${a[1] | 0},${a[2] | 0})`;
  const f = {row: ink - 2, cols: [css(l), css([(d[0] + l[0]) / 2, (d[1] + l[1]) / 2, (d[2] + l[2]) / 2]), css(d), css(k)], masks: new Map(),
    columns(cx, cy) {
      const key = cx + "," + cy;
      if (!this.masks.has(key)) {
        const out = [];
        for (let i = 0; i < 16; i++) {
          const q = at(cx * 16 + i, cy * 16 + ink - 1);
          if (q[3] > 0 && Math.abs(q[0] - top[0]) + Math.abs(q[1] - top[1]) + Math.abs(q[2] - top[2]) > 24) out.push(i);
        }
        this.masks.set(key, out);
      }
      return this.masks.get(key);
    }};
  faces.set(sheet, f); return f;
}

// A wall's colour `r` px above its foot (dropping from level k to `low`): a band per layer counted from the ground up
// lit along its top row, dark along its foot row; the ink at the very foot. `light` < 1: in shade.
function wallColour(r, low, k, light) {
  const j = Math.floor(Math.max(0, r - 1) / STEP), lay = Math.min(k, low + 1 + j), [lit, mid, dark, ink] = faceOf(hillSheet(lay)).cols;
  if (r === 0) return ink;
  const pos = (r - 1) % STEP, c = pos === STEP - 1 ? lit : pos === 0 ? dark : mid;
  return light < 1 ? shade(c, light) : c;
}
const shadeMemo = new Map();
function shade(css, f) {
  const key = css + f;
  if (!shadeMemo.has(key)) { const [r, g, b] = css.match(/\d+/g).map(Number); shadeMemo.set(key, `rgb(${r * f | 0},${g * f | 0},${b * f | 0})`); }
  return shadeMemo.get(key);
}

// The lifted levels of a block, built when its ground canvas changed
function buildRelief(b) {
  let maxLv = 0;
  for (const c of b.lv) { const v = c >= "A" ? c.charCodeAt(0) - 65 : c.charCodeAt(0) - 48; if (v > maxLv) maxLv = v; }
  const layers = [];
  for (let k = 2; k <= maxLv; k++) {
    const c = document.createElement("canvas"); c.width = B * 16; c.height = B * 16 + WALL_M;
    const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) {      // its shape: the level's own sheet, edges and all
      const x = b.bx * B + lx, y = b.by * B + ly;
      if (levelAt(x, y) >= k) drawBlobLayer(g, hillSheet(k), x, y, (cc, gg, tx, ty) => levelAt(tx, ty) >= k, lx * 16, ly * 16, 0);
    }
    g.globalCompositeOperation = "source-in"; g.drawImage(b.canvas, 0, 0); g.globalCompositeOperation = "source-over";
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) {      // the walls of the tiles this high exactly
      const x = b.bx * B + lx, y = b.by * B + ly;
      if (levelAt(x, y) !== k) continue;
      const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, tx, ty) => levelAt(tx, ty) >= k)), f = faceOf(hillSheet(k));
      const low = levelAt(x, y + 1);                   // the front: under every column of the edge as drawn
      if (shOf(k) <= shOf(low)) continue;
      const d = shOf(k) - shOf(low), px = g.getImageData(lx * 16, ly * 16, 16, 16).data;
      for (let col = 0; col < 16; col++) {
        let last = -1;
        for (let r = 15; r >= 0; r--) if (px[(r * 16 + col) * 4 + 3] > 0) { last = r; break; }
        if (last < 8) continue;                        // (a rounded corner's far side: nothing over the drop there)
        const top = Math.max(f.row, last - 2), foot = last + d;   // the sheet's own face, then down to the ground
        for (let Y = top; Y <= foot; Y++) { g.fillStyle = wallColour(foot - Y, low, k, 1); g.fillRect(lx * 16 + col, ly * 16 + Y, 1, 1); }
      }
    }
    layers[k] = c;
  }
  b.relief = {layers, maxLv}; b.reliefDirty = false;
}
// A block's ground, with its levels stacked
function drawBlockRelief(b, sx, sy, S) {
  const X = sx(b.bx * B), Y = sy(b.by * B);
  ctx.drawImage(b.canvas, X, Y, B * S, B * S);
  if (!b.relief || b.reliefDirty) buildRelief(b);
  for (let k = 2; k <= b.relief.maxLv; k++) {
    const c = b.relief.layers[k];
    if (c) ctx.drawImage(c, X, Y - shOf(k) * zoom, B * S, (B * 16 + WALL_M) * zoom);
  }
}
