// Relief, stacked: each level is drawn RELIEF_STEP px higher than the one under it (sea level in place, a pit's floor
// lower), with everything standing on it, so a two-layer drop looks taller than a one-layer one. A block's ground
// canvas is drawn at its lowest level, then for each level above a copy of it cut to the tiles at least that high. Where a lifted level ends
// over lower ground its wall is painted down to the ground below: solid earth, a band per layer (lit along its top,
// darker at its foot), in the colours of that layer's own sheet, the pack's ink at the very foot.

const RELIEF_STEP = 6;                                       // art px a level
const shOf = (L) => RELIEF_STEP * L;                          // how far up a level is drawn (a pit's, down): every layer the same step
const WALL_M = RELIEF_STEP * 14 + 16;                        // room under a layer canvas for its walls

// Something flying off from a spot (a puff, a spark, debris): it keeps the height of where it started, however it
// drifts (it doesn't step up and down with the tiles it passes over)
function liftFrom(o) { if (o.lift === undefined) o.lift = liftOf({x: o.x, y: o.y}); return o.lift; }
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

// The lifted levels of a block, built when its ground canvas changed. Each level k: its body (a 6 px wall band, lit
// at its top, dark at its foot), the ledge round the level above it (LEDGE px, in the sheet's own side-edge colours:
// a +3 shows three edges on every side), then its own tiles on top, where you stand. Worked out over the block and a
// tile round it, so ledges cross block borders.
const LEDGE = 3;
function* reliefSteps(b) {                             // (a step a level, so no frame waits on a whole block)
  const M = 16, Wb = B * 16, Wm = Wb + 2 * M, Hb = Wb + WALL_M;
  let maxLv = -99, minLv = 0;                          // (the block's ground canvas is drawn at its lowest level)
  for (let ty = -1; ty <= B; ty++) for (let tx = -1; tx <= B; tx++) {
    const l = levelAt(b.bx * B + tx, b.by * B + ty); maxLv = Math.max(maxLv, l); minLv = Math.min(minLv, l);
  }
  const layers = {}, shape = {};
  let above = null;
  for (let k = maxLv; k > minLv; k--) {                    // the shapes, from the top down: each grows round the one above
    const own = new Uint8Array(Wm * Wm), sheet = hillSheet(k);
    for (let ty = -1; ty <= B; ty++) for (let tx = -1; tx <= B; tx++) {    // its own tiles' shape, from the sheet's cells
      const x = b.bx * B + tx, y = b.by * B + ty;
      if (levelAt(x, y) < k) continue;
      const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, ux, uy) => levelAt(ux, uy) >= k)), a = cellAlpha(sheet, cx, cy);
      const ox = (tx + 1) * 16, oy = (ty + 1) * 16;
      for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) if (a[j * 16 + i]) own[(oy + j) * Wm + ox + i] = 1;
    }
    const sh = above ? dilateH(above, Wm, Wm, LEDGE) : new Uint8Array(Wm * Wm);
    for (let i = 0; i < own.length; i++) sh[i] = sh[i] || own[i];
    shape[k] = {own, sh}; above = sh;
    yield;
  }
  for (let k = minLv + 1; k <= maxLv; k++) {
    const {own, sh} = shape[k], cols = colsOf(hillSheet(k));
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
    const mc = document.createElement("canvas"); mc.width = mc.height = Wb; mc.getContext("2d").putImageData(mask, 0, 0);
    const c = document.createElement("canvas"); c.width = Wb; c.height = Hb;
    const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    const tint = document.createElement("canvas"); tint.width = tint.height = Wb; const tg0 = tint.getContext("2d");
    for (let s = 0; s < RELIEF_STEP; s++) {                    // the body: its wall, a band, under the whole shape
      const col = s === RELIEF_STEP - 1 ? cols.bands[0] : s === 0 ? cols.bands[2] : cols.bands[1];
      tg0.globalCompositeOperation = "source-over"; tg0.clearRect(0, 0, Wb, Wb);
      tg0.fillStyle = `rgb(${col[0] | 0},${col[1] | 0},${col[2] | 0})`; tg0.fillRect(0, 0, Wb, Wb);
      tg0.globalCompositeOperation = "destination-in"; tg0.drawImage(mc, 0, 0);
      g.drawImage(tint, 0, RELIEF_STEP - s);
    }
    const lc = document.createElement("canvas"); lc.width = lc.height = Wb; lc.getContext("2d").putImageData(ledge, 0, 0);
    g.drawImage(lc, 0, 0);
    const t = document.createElement("canvas"); t.width = t.height = Wb;   // its own tiles: the ground as drawn, cut to
    const tg = t.getContext("2d"); tg.putImageData(ownM, 0, 0);                   //  the level's own shape
    tg.globalCompositeOperation = "source-in"; tg.drawImage(b.canvas, 0, 0);
    g.drawImage(t, 0, 0);
    layers[k] = c;
    yield;
  }
  b.relief = {layers, maxLv, minLv};
}
let reliefBudgetAt = 0, reliefSpent = 0, freshThisFrame = false;
function buildRelief(b) { for (const _ of reliefSteps(b)); b.reliefDirty = false; }   // (all at once: tests, tools)
// A block's ground, with its levels stacked
function drawBlockRelief(b, sx, sy, S) {
  const X = sx(b.bx * B), Y = sy(b.by * B);
  // built in steps, within a few ms a frame across all blocks. A block never built isn't shown until it is (never its
  // flat ground, which would then jump up); one rebuilt keeps showing what it was until the new one is ready.
  if (!b.relief && !b.reliefGen) b.reliefGen = reliefSteps(b);
  else if (b.relief && b.reliefDirty) { b.reliefGen = reliefSteps(b); }
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
  for (let k = b.relief.minLv + 1; k <= b.relief.maxLv; k++) {
    const c = b.relief.layers[k];
    if (c) ctx.drawImage(c, X, Y - shOf(k) * zoom, B * S, (B * 16 + WALL_M) * zoom);
  }
}

// The cave you're in: its roofed tiles joined to yours (up to a few thousand)
function caveOf(x0, y0) {
  const seen = new Set([x0 + "," + y0]), stack = [[x0, y0]];
  while (stack.length && seen.size < 4000) {
    const [x, y] = stack.pop();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const k = (x + dx) + "," + (y + dy);
      if (!seen.has(k) && roofAt(x + dx, y + dy) > 0) { seen.add(k); stack.push([x + dx, y + dy]); }
    }
  }
  return seen;
}
// Walking into a cave (or out): that cave's roof comes off (goes back on) at once, like a house's. The blocks with
// caves, and those beside them (their edges), are redrawn there and then: on screen in full, the rest as they come.
let myAt = null;                          // your tile and height: in a cave, or up on its roof (as Movement.landing)
function setCaveOpen(vis) {
  const me = ents.get("agent" + myId);
  if (me) {
    const x = Math.round(me.tx), y = Math.round(me.ty);
    if (!myAt || myAt.x !== x || myAt.y !== y) {
      const f = floorAt(x, y), r = roofAt(x, y);
      let z = f + (meObs && meObs.self.atop ? r : 0);
      if (myAt && Math.abs(myAt.x - x) + Math.abs(myAt.y - y) === 1) {
        const inside = roofAt(myAt.x, myAt.y) > 0 && myAt.z === floorAt(myAt.x, myAt.y);
        const c = !r ? [f] : inside ? [f, f + r] : [f + r, f], pick = c.sort((p, q) => Math.abs(p - myAt.z) - Math.abs(q - myAt.z)).find((h) => Math.abs(h - myAt.z) <= 1);
        if (pick !== undefined) z = pick;
      }
      myAt = {x, y, z};
    }
  }
  const open = !!myAt && roofAt(myAt.x, myAt.y) > 0 && myAt.z === floorAt(myAt.x, myAt.y);
  if (open === caveOpen && (!open || openCave.has(myAt.x + "," + myAt.y))) return;
  const key = open ? caveOf(myAt.x, myAt.y) : null;
  const was = openCave;
  caveOpen = open; openCave = open ? key : new Set();
  const touched = new Set([...was, ...openCave].map((k) => { const [x, y] = k.split(",").map(Number); return bkey(Math.floor(x / B), Math.floor(y / B)); }));
  const shown = new Set(vis);
  for (const b of blocks.values()) {
    if (!b.drawn || ![[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => touched.has(bkey(b.bx + dx, b.by + dy)))) continue;
    if (shown.has(b)) { renderBlock(b); buildRelief(b); b.reliefGen = null; }
    else { b.drawn = false; b.reliefDirty = true; }
  }
}
// In a cave, the high ground south of a tunnel is drawn up over it: its floor is drawn again on top, so the whole
// cave shows through the rock in front of it (and nothing else changes)
function drawCaveFloors(vis, sx, sy, S) {
  for (const b of vis) {
    if (!b.rf || !b.relief) continue;
    for (let i = 0; i < B * B; i++) {
      if (!b.rf[i]) continue;
      const x = b.bx * B + i % B, y = b.by * B + (i / B | 0);
      if (!openCave.has(x + "," + y)) continue;
      const f = floorAt(x, y), Y = sy(y) - shOf(f) * zoom;
      ctx.drawImage(b.canvas, (i % B) * 16, (i / B | 0) * 16, 16, 16, sx(x), Y, S, S);
      const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, tx, ty) => openCave.has(tx + "," + ty) || Math.abs(floorAt(tx, ty) - f) <= 1));
      ctx.drawImage(edgeSheet("hill3"), cx * 16, cy * 16, 16, 16, sx(x), Y, S, S);     // (its rock rim)
    }
  }
}
// A cave seen from outside: a dark opening in the hill's face where it meets the ground (its mouth)
function drawCaveMouths(vis, sx, sy, S) {
  ctx.fillStyle = "#2b2328";
  for (const b of vis) {
    if (!b.rf || !b.relief) continue;
    for (let i = 0; i < B * B; i++) {
      if (!b.rf[i]) continue;
      const x = b.bx * B + i % B, y = b.by * B + (i / B | 0), f = floorAt(x, y);
      if (inOpenCave(x, y) || roofAt(x, y + 1) || Math.abs(floorAt(x, y + 1) - f) > 1) continue;   // (opening south)
      const mouth = (u) => roofAt(u, y) && !roofAt(u, y + 1) && Math.abs(floorAt(u, y + 1) - floorAt(u, y)) <= 1;
      const L = mouth(x - 1) ? 0 : 1, R = mouth(x + 1) ? 0 : 1;          // (a wide mouth: one opening)
      const top = sy(y + 1) - shOf(f + roofAt(x, y)) * zoom, bot = sy(y + 1) - shOf(f) * zoom, r = 3 * zoom;
      const x0 = sx(x) + L * zoom, x1 = sx(x + 1) - R * zoom;
      ctx.beginPath(); ctx.moveTo(x0, bot); ctx.lineTo(x0, top + r * L);
      ctx.quadraticCurveTo(x0, top, x0 + r * L, top); ctx.lineTo(x1 - r * R, top);
      ctx.quadraticCurveTo(x1, top, x1, top + r * R); ctx.lineTo(x1, bot); ctx.fill();
    }
  }
}
