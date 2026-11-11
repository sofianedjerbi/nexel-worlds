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

// The lifted levels of a block, built when its ground canvas changed
function buildRelief(b) {
  let maxLv = 0;
  for (const c of b.lv) { const v = c >= "A" ? c.charCodeAt(0) - 65 : c.charCodeAt(0) - 48; if (v > maxLv) maxLv = v; }
  const layers = [];
  for (let k = 2; k <= maxLv; k++) {
    const c = document.createElement("canvas"); c.width = B * 16; c.height = B * 16 + WALL_M;
    const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    g.fillStyle = "#000";
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) if (levelAt(b.bx * B + lx, b.by * B + ly) >= k) g.fillRect(lx * 16, ly * 16, 16, 16);
    g.globalCompositeOperation = "source-in"; g.drawImage(b.canvas, 0, 0); g.globalCompositeOperation = "source-over";
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) {      // the walls of the tiles this high exactly
      const x = b.bx * B + lx, y = b.by * B + ly;
      if (levelAt(x, y) !== k) continue;
      const low = levelAt(x, y + 1), tall = 3 + shOf(k) - shOf(low);
      if (shOf(k) <= shOf(low)) continue;
      const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, tx, ty) => levelAt(tx, ty) >= k)), f = faceOf(hillSheet(k));
      for (const col of f.columns(cx, cy)) for (let r = 0; r < tall; r++) {
        const lay = Math.max(low + 1, k - Math.floor(r / STEP)), [lit, mid, dark, ink] = faceOf(hillSheet(lay)).cols;
        g.fillStyle = r === tall - 1 ? ink : r % STEP === 0 ? lit : r % STEP === STEP - 1 ? dark : mid;
        g.fillRect(lx * 16 + col, ly * 16 + f.row + r, 1, 1);
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
