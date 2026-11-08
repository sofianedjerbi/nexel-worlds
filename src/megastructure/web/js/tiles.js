// The client's copy of the world: 32x32 blocks patched by tile events, and the ground layer renderer.

// =====================================================================================
//  Tile store: 32x32 blocks, filled from the server and patched by tile events
// =====================================================================================
const B = 32, P = 16;
const blocks = new Map();
const bkey = (bx, by) => bx + "," + by;
function tile(x, y) {
  const b = blocks.get(bkey(Math.floor(x / B), Math.floor(y / B)));
  if (!b) return null;
  const i = (y - b.by * B) * B + (x - b.bx * B);
  return [b.comb[i], b.gnd[i]];
}
const combAt = (x, y) => { const t = tile(x, y); return t ? t[0] : null; };
const gndAt = (x, y) => { const t = tile(x, y); return t ? t[1] : null; };
const dirtyTiles = [];                 // tiles to redraw (x, y), processed within a per-frame budget
function touch(x, y) { for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) dirtyTiles.push(x + dx, y + dy); }
function setTile(x, y, comb, gnd) {
  const bx = Math.floor(x / B), by = Math.floor(y / B), b = blocks.get(bkey(bx, by));
  if (!b) return;
  const i = (y - by * B) * B + (x - bx * B);
  if (b.comb[i] === comb && b.gnd[i] === gnd) return;
  const old = b.comb[i], now = performance.now();
  if (old === "F" && comb === "T") dropping.set(x + "," + y, now);
  else if (old === "T" && comb !== "T") falls.push({x, y, t0: now});
  else if (old !== comb && isObject(comb) && comb !== "x") pops.set(x + "," + y, now);
  const spr = old !== comb && old !== "T" && isObject(old) && !isObject(comb) ? objectSprite(old, x, y, now / 1000) : null;
  if (spr) {                                   // taken away: it squashes down and fades, shedding its own colours
    gones.push({x, y, spr, t0: now});
    const cols = spriteColors(spr);
    for (let k = 0; k < 9; k++) parts.push({x: x + .2 + Math.random() * .6, y: y + .2 + Math.random() * .5, vx: (Math.random() - .5) * 2.2,
      vy: -Math.random() * 2.2 - .4, g: 7, life: .35 + Math.random() * .3, age: 0, c: cols[k % cols.length], s: 1});
  } else if (old !== comb && !GROUND.has(old)) burst(x, y, old, 10);
  if (gnd === "o" && b.gnd[i] !== "o") burst(x, y, "o", 8);
  b.comb[i] = comb; b.gnd[i] = gnd;
  b.objs.delete(i); if (isObject(comb)) b.objs.set(i, comb);
  if (ENCLOSE.has(old) || ENCLOSE.has(comb)) roomsDirty = true;
  touch(x, y);
}
function onRegion(d) {
  if (d.w !== B || d.h !== B || d.x % B || d.y % B) return;
  const bx = d.x / B, by = d.y / B, k = bkey(bx, by);
  const comb = [], gnd = [];
  for (let j = 0; j < B; j++) for (let i = 0; i < B; i++) { comb.push(d.rows[j][i]); gnd.push(d.ground[j][i]); }
  requested.delete(k);
  const old = blocks.get(k);
  if (old && old.drawn) {             // resync: only redraw what actually changed
    for (let i = 0; i < B * B; i++) if (old.comb[i] !== comb[i] || old.gnd[i] !== gnd[i]) setTile(bx * B + i % B, by * B + (i / B | 0), comb[i], gnd[i]);
    old.at = performance.now(); return;
  }
  const b = {bx, by, comb, gnd, objs: new Map(), drawn: false, canvas: null, at: performance.now()};
  comb.forEach((c, i) => { if (isObject(c)) b.objs.set(i, c); });
  blocks.set(k, b);
  // neighbours' edge tiles depend on this block for autotiling
  for (let i = 0; i < B; i++) { dirtyTiles.push(bx * B - 1, by * B + i, bx * B + B, by * B + i, bx * B + i, by * B - 1, bx * B + i, by * B + B); }
}

// =====================================================================================
//  Drawing one tile's ground layers into its block canvas (16 px cell)
// =====================================================================================
const isLand = (g) => g !== null && g !== "~" && g !== "=" && g !== ":";
const isObject = (c) => "TFbM*#%+^&?!x\"wtCQ;fBhLpKrgWVXYJmqey".includes(c) && !GROUND.has(c);
function maskOf(x, y, pred) {
  let m = 0;
  const p = (dx, dy) => { const t = tile(x + dx, y + dy); return t === null ? true : pred(t[0], t[1]); };
  if (p(0, -1)) m |= N_; if (p(1, 0)) m |= E_; if (p(0, 1)) m |= S_; if (p(-1, 0)) m |= W_;
  if (p(1, -1)) m |= NE; if (p(1, 1)) m |= SE; if (p(-1, 1)) m |= SW; if (p(-1, -1)) m |= NW;
  return m;
}
function hash(x, y, s = 0) {
  let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + Math.imul(s, 2246822519)) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
function drawBlobLayer(g, sheet, x, y, pred, ox, oy, decor) {
  const m = maskOf(x, y, pred), [cx, cy] = blobCell(m);
  let sx = cx * 16, sy = cy * 16;
  if (decor && reduce(m) === 255 && hash(x, y, 3) < decor) {       // plain interior: sprinkle decor variants
    sx = Math.floor(hash(x, y, 4) * (sheet === IMG.grass ? 6 : 5)) * 16; sy = (5 + (hash(x, y, 5) < .5 ? 0 : 1)) * 16;
  }
  g.drawImage(sheet, sx, sy, 16, 16, ox, oy, 16, 16);
}
function drawTile(x, y) {
  const b = blocks.get(bkey(Math.floor(x / B), Math.floor(y / B)));
  if (!b || !b.canvas) return;
  const lx = x - b.bx * B, ly = y - b.by * B, i = ly * B + lx, g = b.ctx, ox = lx * 16, oy = ly * 16;
  const c = b.comb[i], gr = b.gnd[i];
  g.clearRect(ox, oy, 16, 16);
  if (gr === "=") drawBlobLayer(g, IMG.deep_mask, x, y, (_, gg) => gg === "=", ox, oy, 0);   // rounded deep areas
  if (gr === ":") {                                  // bridge planks run across the direction of travel
    const ew = [-1, 1].some((d) => { const q = gndAt(x + d, y); return q === ":" || isLand(q); });
    g.drawImage(IMG.bridge, ew ? 0 : 32, 32, 16, 16, ox, oy, 16, 16);
  }
  if (isLand(gr)) {
    drawBlobLayer(g, IMG.soil, x, y, (_, gg) => isLand(gg), ox, oy, .15);
    if (gr === "." || hasGrassNeighbour(x, y)) {
      if (gr === "." || gr === "_" || gr === "n") drawBlobLayer(g, IMG.grass, x, y, (_, gg) => gg === "." || gg === "_" || gg === "n", ox, oy, gr === "." ? .3 : 0);
    }
    if (gr === "o" || gr === "u") drawBlobLayer(g, IMG.tilled, x, y, (_, gg) => gg === "o" || gg === "u", ox, oy, 0);
    if (gr === "u") drawBlobLayer(g, IMG.tilled_wet, x, y, (_, gg) => gg === "u", ox, oy, 0);
    if (gr === "n") g.drawImage(IMG.bridge, 0, 32, 16, 16, ox, oy, 16, 16);
    if (gr === "'") drawBlobLayer(g, IMG.ash, x, y, (_, gg) => gg === "'", ox, oy, 0);
    if (gr === "_") g.drawImage(IMG.cobble, [16, 32, 0][Math.floor(hash(x, y, 9) * 3)], [16, 32, 48][Math.floor(hash(x, y, 10) * 3)], 16, 16, ox, oy, 16, 16);
  }
  // flat things that live in the ground layer
  if (c === "H") drawBlobLayer(g, IMG.hedge, x, y, (cc) => cc === "H", ox, oy, 0);
  const hd = hash(x, y, 41);
  if (gr === "~" && hd < .09) {                      // shore water: lily pads, reeds, little rocks
    const shore = [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => isLand(gndAt(x + dx, y + dy)));
    if (shore || hd < .015) {
      const pick = Math.floor(hash(x, y, 42) * 7), col = [8, 9, 10, 11, 6, 7, 0][pick];
      g.drawImage(IMG.water_objects, col * 16, 0, 16, 16, ox, oy, 16, 16);
    }
  }
}
const hasGrassNeighbour = () => true;
function renderBlock(b) {
  b.canvas = document.createElement("canvas"); b.canvas.width = B * 16; b.canvas.height = B * 16;
  b.ctx = b.canvas.getContext("2d");
  for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly);
  b.drawn = true;
}
