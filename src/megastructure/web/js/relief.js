// Relief, stacked: each level is drawn RELIEF_STEP px higher than the one under it (sea level in place, a pit's floor
// lower), with everything standing on it, so a two-layer drop looks taller than a one-layer one. A block's ground
// canvas is drawn at its lowest level; over it goes one more picture, its raised levels: for each level above, a
// copy of the ground cut to the tiles at least that high, painted one over the other when the block is built (not
// each frame: a level a canvas was ten canvases a block, and eight screens of paint a frame). Where a lifted level
// ends over lower ground its wall is painted down to the ground below: solid earth, a band per layer (lit along its
// top, darker at its foot), in the colours of that layer's own sheet, the pack's ink at the very foot.

// A layer is half a tile high: two layers, one tile (a cave two blocks high is as tall as you are)
const RELIEF_STEP = 8;                                       // art px a level
const shOf = (L) => RELIEF_STEP * L;                          // how far up a level is drawn (a pit's, down): every layer the same step

// Where a body stands in its tile, a person or a creature alike: STAND art px higher than its sheet puts it. The
// sheets put the feet 2 px over the tile's bottom: the shadow on the line between two tiles, hanging off a ledge's
// brink, a tile short of a wall to the north. So: feet 5 px over the bottom, in line with the rocks and crops beside
// it, the body in the middle of its tile. UP: the same in tiles (its dust, what flies to it, where it is looked for).
const STAND = 3, UP = STAND / 16;
const bodyY = (p, sy) => sy(p.y, p.x) - STAND * zoom;         // a body's place on screen (the top of its tile, lifted with its ground, and STAND)

// Something flying off from a spot (a puff, a spark, debris): it keeps the height of where it started, however it
// drifts (it doesn't step up and down with the tiles it passes over)
function liftFrom(o) { if (o.lift === undefined) o.lift = liftOf({x: o.x, y: o.y}); return o.lift; }
// Screen px something on tile (x, y) is drawn higher by
const liftAt = (x, y) => shOf(standAt(x, y)) * zoom;
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
  const [nx, ny] = blobCell(S_ | E_ | W_ | SE | SW);
  let n0 = 0; while (n0 < 15 && at(nx * 16 + 8, ny * 16 + n0)[3] < 128) n0++;
  const out = {bands: [l, [(d[0] + l[0]) / 2, (d[1] + l[1]) / 2, (d[2] + l[2]) / 2], d], side, top: at(ix * 16 + 8, iy * 16 + 8),
               foot: ink + 1, inset: w0, north: n0};   // (in the tile: where its south face ends, its side edge and its far edge start)
  sheetCols.set(sheet, out); return out;
}

// A sheet cell's shape: 1 where its pixel is drawn (16x16)
const cellAlphas = new Map();
function cellAlpha(sheet, cx, cy) {
  let m = cellAlphas.get(sheet);
  if (!m) {
    const c = document.createElement("canvas"); c.width = sheet.width; c.height = sheet.height;
    const g = c.getContext("2d"); g.drawImage(sheet, 0, 0);
    m = {data: g.getImageData(0, 0, c.width, c.height).data, w: c.width, cells: new Map()}; cellAlphas.set(sheet, m);
  }
  const key = cx * 100 + cy;
  if (!m.cells.has(key)) {
    const a = new Uint8Array(256);
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) a[j * 16 + i] = m.data[((cy * 16 + j) * m.w + cx * 16 + i) * 4 + 3] > 128 ? 1 : 0;
    m.cells.set(key, a);
  }
  return m.cells.get(key);
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

// The lifted levels of a block, built when its ground canvas changed. Each level k: its body (a wall band a layer high, lit
// at its top, dark at its foot), the ledge round the level above it (LEDGE px, in the sheet's own side-edge colours:
// a +3 shows three edges on every side), then its own tiles on top, where you stand. Worked out over the block and a
// tile round it, so ledges cross block borders.
const LEDGE = 4, SIDE_MAX = 2;
// A level's shape in a block and a tile round it (a byte a px, 1 where it is): `own`, its own tiles, from its sheet's
// cells; `sh`, that and the ledges of the levels above it (shape: those, already worked out)
function levelShape(b, k, shape) {
  const M = 16, Wm = B * 16 + 2 * M, own = new Uint8Array(Wm * Wm), sheet = hillSheet(k);
  for (let ty = -1; ty <= B; ty++) for (let tx = -1; tx <= B; tx++) {
    const x = b.bx * B + tx, y = b.by * B + ty;
    if (levelAt(x, y) < k) continue;
    const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, ux, uy) => levelAt(ux, uy) >= k)), a = cellAlpha(sheet, cx, cy);
    const ox = (tx + 1) * 16, oy = (ty + 1) * 16;
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) if (a[j * 16 + i]) own[(oy + j) * Wm + ox + i] = 1;
  }
  // (round it, the layers over it stick out a ledge each: SIDE_MAX of them at the most, so a cliff's side never
  // reaches further than half a tile onto the ground beside it, where people stand)
  const sh = new Uint8Array(own);
  for (let n = 1; n <= SIDE_MAX; n++) if (shape[k + n]) { const d = dilateH(shape[k + n].own, Wm, Wm, LEDGE * n); for (let i = 0; i < sh.length; i++) sh[i] = sh[i] || d[i]; }
  return {own, sh};
}
function* reliefSteps(b) {                             // (a step a level, so no frame waits on a whole block)
  const M = 16, Wb = B * 16, Wm = Wb + 2 * M;
  let maxLv = -99, minLv = 0;                          // (the block's ground canvas is drawn at its lowest level)
  for (let ty = -1; ty <= B; ty++) for (let tx = -1; tx <= B; tx++) {
    const l = levelAt(b.bx * B + tx, b.by * B + ty); maxLv = Math.max(maxLv, l); minLv = Math.min(minLv, l);
  }
  const shape = {};
  for (let k = maxLv; k > minLv; k--) { shape[k] = levelShape(b, k, shape); yield; }   // the shapes, from the top down: each grows round the one above
  // the raised levels, painted lowest first into one picture: `up` px taller than the block at its top (the highest
  // level's lift), the lowest level's worth at its foot
  const up = shOf(maxLv), flat = maxLv > minLv ? document.createElement("canvas") : null, fg = flat && flat.getContext("2d");
  if (flat) { flat.width = Wb; flat.height = Wb + up - shOf(minLv); fg.imageSmoothingEnabled = false; }
  const [mc, tint, lc, t] = reliefScratch(Wb), tg0 = tint.getContext("2d"), tg = t.getContext("2d");
  for (let k = minLv + 1; k <= maxLv; k++) {
    const {own, sh} = shape[k], cols = colsOf(hillSheet(k)), off = up - shOf(k);
    const mask = new ImageData(Wb, Wb), md = mask.data, ledge = new ImageData(Wb, Wb), ld = ledge.data, ownM = new ImageData(Wb, Wb), od = ownM.data;
    for (let y = 0; y < Wb; y++) for (let x = 0; x < Wb; x++) {
      const i = (y + M) * Wm + x + M, o = (y * Wb + x) * 4;
      if (!sh[i]) continue;
      md[o + 3] = 255;
      if (own[i]) { od[o + 3] = 255; continue; }                              // the ledge, where the shape is not its own tiles
      let ownL = false, ownR = false;
      for (let j = 1; j <= LEDGE; j++) { if (own[i - j]) ownL = true; if (own[i + j]) ownR = true; }
      let c;
      if (ownL && ownR) c = cols.top;                    // (a sliver between two of its own edges: its top)
      else { let dd = 0; while (dd < 3 && sh[i - dd - 1] && sh[i + dd + 1]) dd++; c = cols.side[dd]; }
      ld[o] = c[0]; ld[o + 1] = c[1]; ld[o + 2] = c[2]; ld[o + 3] = 255;
    }
    mc.getContext("2d").putImageData(mask, 0, 0);
    for (let s = 0; s < RELIEF_STEP; s++) {                    // the body: its wall, a band, under the whole shape
      const col = s === RELIEF_STEP - 1 ? cols.bands[0] : s === 0 ? cols.bands[2] : cols.bands[1];
      tg0.globalCompositeOperation = "source-over"; tg0.clearRect(0, 0, Wb, Wb);
      tg0.fillStyle = `rgb(${col[0] | 0},${col[1] | 0},${col[2] | 0})`; tg0.fillRect(0, 0, Wb, Wb);
      tg0.globalCompositeOperation = "destination-in"; tg0.drawImage(mc, 0, 0);
      fg.drawImage(tint, 0, off + RELIEF_STEP - s);
    }
    lc.getContext("2d").putImageData(ledge, 0, 0);
    fg.drawImage(lc, 0, off);
    tg.globalCompositeOperation = "source-over"; tg.putImageData(ownM, 0, 0);   // its own tiles: the ground as drawn, cut to
    tg.globalCompositeOperation = "source-in"; tg.drawImage(b.canvas, 0, 0);    //  the level's own shape
    fg.drawImage(t, 0, off);
    yield;
  }
  // where that picture has anything in it (a small hill in a wide plain: the rest is not painted, frame after frame):
  // the raised tiles, their ledges beside them, their walls down to the lowest ground
  let box = null;
  if (flat) {
    let x0 = Wb, y0 = flat.height, x1 = 0, y1 = 0;
    for (let ty = -1; ty <= B; ty++) for (let tx = -1; tx <= B; tx++) {
      const l = levelAt(b.bx * B + tx, b.by * B + ty); if (l <= minLv) continue;
      x0 = Math.min(x0, tx * 16 - LEDGE * SIDE_MAX); x1 = Math.max(x1, tx * 16 + 16 + LEDGE * SIDE_MAX);
      y0 = Math.min(y0, ty * 16 + up - shOf(l)); y1 = Math.max(y1, ty * 16 + 17 + up - shOf(minLv));
    }
    x0 = Math.max(0, x0); y0 = Math.max(0, y0); x1 = Math.min(Wb, x1); y1 = Math.min(flat.height, y1);
    if (x1 > x0 && y1 > y0) box = [x0, y0, x1 - x0, y1 - y0];
  }
  b.relief = {flat: box && flat, up, maxLv, minLv, box};
}
// Where a block's ground from level `from` up is drawn, in one colour: the same shapes, the same lifts as its picture
// (rel: its relief), so it is that ground to the pixel, rounded edges, ledges and walls. (xray.js: to someone standing
// lower, that is the rock the circle looks through.) Built the same way, a step a level.
function* rockSteps(b, from, rel) {
  const M = 16, Wb = B * 16, Wm = Wb + 2 * M, c = document.createElement("canvas"), shape = {};
  c.width = Wb; c.height = Wb + rel.up - shOf(rel.minLv);
  const g = c.getContext("2d"), mc = reliefScratch(Wb)[0];
  for (let k = rel.maxLv; k >= Math.max(from, rel.minLv + 1); k--) {
    const sh = (shape[k] = levelShape(b, k, shape)).sh, mask = new ImageData(Wb, Wb), md = mask.data;
    for (let y = 0; y < Wb; y++) for (let x = 0; x < Wb; x++) if (sh[(y + M) * Wm + x + M]) md[(y * Wb + x) * 4 + 3] = 255;
    mc.getContext("2d").putImageData(mask, 0, 0);
    for (let s = 0; s <= RELIEF_STEP; s++) g.drawImage(mc, 0, rel.up - shOf(k) + s);   // its top, and its wall under it
    yield;
  }
  return c;
}
// ...kept on the block while it's asked for (-> null while it is being worked out: a few ms a frame)
function rockOf(b, from) {
  const rel = b.relief;
  if (b.rock && b.rock.of === rel && b.rock.from === from) return b.rock.canvas;
  if (!b.rockGen || b.rockGen.of !== rel || b.rockGen.from !== from) { b.rockGen = rockSteps(b, from, rel); b.rockGen.of = rel; b.rockGen.from = from; }
  for (const t0 = performance.now(); performance.now() - t0 < 4;) {
    const r = b.rockGen.next();
    if (r.done) { b.rock = {of: rel, from, canvas: r.value}; b.rockGen = null; return r.value; }
  }
  return b.rock && b.rock.from === from ? b.rock.canvas : null;      // (its land just changed: the one from before, meanwhile)
}
let scratch = null;                                    // (canvases to build a level on, kept: one set for every block)
function reliefScratch(Wb) {
  if (!scratch) scratch = [0, 1, 2, 3].map(() => { const c = document.createElement("canvas"); c.width = c.height = Wb; return c; });
  return scratch;
}
let reliefBudgetAt = 0, reliefSpent = 0, freshThisFrame = false;
function buildRelief(b) { for (const _ of reliefSteps(b)); b.reliefDirty = false; }   // (all at once: tests, tools)
// A block's ground, with its levels stacked
function drawBlockRelief(b, sx, sy, S) {
  const X = sx(b.bx * B), Y = sy(b.by * B);
  // built in steps, within a few ms a frame across all blocks. A block never built isn't shown until it is (never its
  // flat ground, which would then jump up); one rebuilt keeps showing what it was until the new one is ready.
  // (Its ground redrawn while it is being built, the first time too: the block beside it arriving changes its edge.
  // It is built again from the start, what it had read being out of date: dropped, that left a column of flat
  // ground along the edge.)
  if (b.reliefDirty || (!b.relief && !b.reliefGen)) b.reliefGen = reliefSteps(b);
  b.reliefDirty = false;
  const now = performance.now();
  if (now - reliefBudgetAt > 8) { reliefBudgetAt = now; reliefSpent = 0; }
  while (b.reliefGen && reliefSpent < 6 && !freshThisFrame) {
    const t0 = performance.now(), r = b.reliefGen.next();
    reliefSpent += performance.now() - t0;
    if (r.done) b.reliefGen = null;
  }
  if (!b.relief) return;
  ctx.drawImage(b.canvas, X, Y - shOf(b.relief.minLv) * zoom, B * S, B * S);
  const f = b.relief.flat, [fx, fy, fw, fh] = b.relief.box || [];
  if (f) ctx.drawImage(f, fx, fy, fw, fh, X + fx * zoom, Y + (fy - b.relief.up) * zoom, fw * zoom, fh * zoom);
}
// A sheet cell as a top edge: for each of its 16 px columns, the first row that is drawn (16: none of it)
const cellTops = new Map();
function cellTop(sheet, cx, cy) {
  let m = cellTops.get(sheet); if (!m) cellTops.set(sheet, m = new Map());
  const key = cx * 100 + cy;
  if (!m.has(key)) {
    const a = cellAlpha(sheet, cx, cy), top = new Uint8Array(16).fill(16);
    for (let i = 0; i < 16; i++) for (let j = 0; j < 16; j++) if (a[j * 16 + i]) { top[i] = j; break; }
    m.set(key, top);
  }
  return m.get(key);
}
// Someone standing behind higher ground (it is south of them, drawn up over where they stand) is behind it: what of
// them is under its top edge isn't drawn. Called before drawing them: clips the canvas down to that edge and returns
// true (restore after); false when nothing hides them. Nothing of the land is redrawn. The edge is the ground's own,
// an art px column at a time: each of its layers in its own shape, set in a little from the tile's side and rounded
// at its corners (cut straight across a tile, the sprite was gone where a corner lets the ground behind it show).
// (Not in the cave you're in: that one is seen through the hill.)
function clipBehind(p, sx, sy, S) {
  const x = Math.round(p.x), y = Math.round(p.y);
  if (inOpenCave(x, y) || (caveOpen && p.e.kind === "agent" && p.e.id === myId)) return false;   // (you, going in or out: no flicker)
  const L = standAt(x, y);                                // (between two tiles: the ground they are over: past its edge, a jump is on the higher one)
  const x0 = Math.floor(p.x) - 2, x1 = Math.ceil(p.x) + 2, feet = sy(p.y + 1) - shOf(L) * zoom + (4 - STAND) * zoom, cols = [];
  let any = false;
  for (let tx = x0; tx <= x1; tx++) {
    const edge = new Array(16).fill(Infinity);            // the top of the higher ground in front, at each px of this column
    for (let ty = Math.floor(p.y) + 1; ty <= Math.floor(p.y) + 8; ty++) {
      const lv = levelAt(tx, ty);
      if (lv <= L || inOpenCave(tx, ty)) continue;
      for (let k = L + 1; k <= lv; k++) {
        const top = cellTop(hillSheet(k), ...blobCell(maskOf(tx, ty, (cc, gg, ux, uy) => levelAt(ux, uy) >= k))), Y = sy(ty) - shOf(k) * zoom;
        for (let i = 0; i < 16; i++) if (top[i] < 16) edge[i] = Math.min(edge[i], Y + top[i] * zoom);
      }
    }
    cols.push(edge); any = any || edge.some((e) => e < feet);                           // (reaching up to their feet, or their shadow)
  }
  if (!any) return false;
  ctx.save(); ctx.beginPath();
  ctx.rect(-1e4, -1e4, sx(x0) + 1e4, 2e4); ctx.rect(sx(x1 + 1), -1e4, 1e4, 2e4);
  cols.forEach((edge, c) => {
    for (let i = 0, j; i < 16; i = j) {                    // (a run of px with the same edge: one strip)
      for (j = i + 1; j < 16 && edge[j] === edge[i]; j++);
      ctx.rect(sx(x0 + c) + i * zoom, -1e4, (j - i) * zoom, (edge[i] === Infinity ? 1e4 : edge[i]) + 1e4);
    }
  });
  ctx.clip();
  return true;
}
// Is the spot (x, y: tiles, with fractions) behind higher ground drawn up over it? (Dust and sparks there aren't shown.)
// Higher ground: on the level nothing is behind anything. (It compared 0 with less than 0 there, and a row too far:
// every puff of dust, spark and splash that wasn't on the very top line of its tile went unseen, everywhere.)
function behindHill(x, y) {
  const tx = Math.floor(x), fy = Math.floor(y);
  if (inOpenCave(tx, fy)) return false;
  const L = standAt(tx, fy);
  for (let ty = fy + 1; ty <= fy + 7; ty++) {
    const up = (levelAt(tx, ty) - L) * RELIEF_STEP;        // art px its top is drawn up over the ground the spot is on
    if (up > 0 && up >= (ty - y) * 16) return true;
  }
  return false;
}
