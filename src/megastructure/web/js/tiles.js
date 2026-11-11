// The client's copy of the world: 32x32 blocks patched by tile events, and the ground layer renderer.

// =====================================================================================
//  Tile store: 32x32 blocks, filled from the server and patched by tile events
// =====================================================================================
const B = 32, P = 16;
const smooth = (v) => { v = Math.max(0, Math.min(1, v)); return v * v * (3 - 2 * v); };   // 0..1, eased
const blocks = new Map();
const bkey = (bx, by) => bx + "," + by;
function tile(x, y) {
  const b = blocks.get(bkey(Math.floor(x / B), Math.floor(y / B)));
  if (!b) return null;
  const i = (y - b.by * B) * B + (x - b.bx * B);
  return [b.comb[i], b.gnd[i]];
}
const combAt = (x, y) => { const t = tile(x, y); return t ? t[0] : null; };
// Relief: a char per tile, 64 + its floor's height ("@" sea level, below it dug pits); and in caves the rock over each
// tile, in layers. A cave is drawn as the mountain over it (its roof), like a house: walk in and every cave's roof
// is off (you see the cave as a hole in the mountain). levelAt is the height drawn; floorAt the one you stand on.
const SEA = 64;
function tileIdx(x, y) { const b = blocks.get(bkey(Math.floor(x / B), Math.floor(y / B))); return b ? [b, (y - b.by * B) * B + (x - b.bx * B)] : null; }
const floorAt = (x, y) => { const t = tileIdx(x, y); return t ? t[0].lv[t[1]].charCodeAt(0) - SEA : 0; };
const roofAt = (x, y) => { const t = tileIdx(x, y); return t && t[0].rf ? t[0].rf[t[1]] : 0; };
let caveOpen = false;                       // you're in a cave: caves are drawn without their roof
const levelAt = (x, y) => { const t = tileIdx(x, y); if (!t) return 0; const f = t[0].lv[t[1]].charCodeAt(0) - SEA; return caveOpen || !t[0].rf ? f : f + t[0].rf[t[1]]; };
const hiddenAt = (x, y) => !caveOpen && roofAt(x, y) > 0;     // under a closed cave's roof: not seen
function rimAt(x, y) {                      // as World.rim: lower ground around it (nothing built)
  const lv = floorAt(x, y);
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if ((dx || dy) && floorAt(x + dx, y + dy) < lv) return true;
  return false;
}
// as World.can_step for people: on the level, a layer down, or a jump a layer up
const canStep = (x0, y0, x1, y1) => Math.abs(floorAt(x0, y0) - floorAt(x1, y1)) <= 1;
const gndAt = (x, y) => { const t = tile(x, y); return t ? t[1] : null; };
const dirtyTiles = [];                 // tiles to redraw (x, y), processed within a per-frame budget
function touch(x, y) { for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) dirtyTiles.push(x + dx, y + dy); }
// picked plants: full -> bare (fruit flies to the picker); bare -> full when it grows back
const PICK = {F: "U", b: "v"};
function setTile(x, y, comb, gnd, who = null, lv = null) {
  const bx = Math.floor(x / B), by = Math.floor(y / B), b = blocks.get(bkey(bx, by));
  if (!b) return;
  const i = (y - by * B) * B + (x - bx * B);
  const lc = lv === null ? b.lv[i] : String.fromCharCode(48 + (lv & 31)), rf = lv === null ? roofAt(x, y) : lv >> 5;
  if (b.comb[i] === comb && b.gnd[i] === gnd && b.lv[i] === lc && roofAt(x, y) === rf) return;
  if (rf !== roofAt(x, y)) { if (!b.rf) b.rf = new Array(B * B).fill(0); b.rf[i] = rf; }
  if (b.lv[i] !== lc || rf !== roofAt(x, y)) { b.lv[i] = lc; for (let d = -2; d <= 2; d++) touch(x + d, y); }   // relief changed: edges around redraw
  const old = b.comb[i], now = performance.now();
  if (PICK[old] === comb) picked(x, y, old, who, now);
  else if (old === "T" && comb !== "T") felled(x, y, who, now);
  else if (old !== comb && isObject(comb) && comb !== "x" && PICK[old] !== comb) pops.set(x + "," + y, now);
  const spr = old !== comb && old !== "T" && PICK[old] !== comb && isObject(old) && !isObject(comb) ? objectSprite(old, x, y, now / 1000) : null;
  if (spr && PLUCKED.includes(old)) plucked(x, y, spr, who, now);   // small plants come up and go to the picker
  else if (spr) {                              // anything else taken away falls apart into its own pixels
    shatter(x, y, spr);
    if ("M*%Y^".includes(old)) smoke(x, y + .25, 3, .3);   // stone kicks up a little dust
  } else if (old !== comb && !GROUND.has(old) && old !== "Z" && old !== "z") burst(x, y, old, 10);
  if (gnd === "o" && b.gnd[i] !== "o") debris(x, y, null, 6, {kind: "o", dust: true});
  b.comb[i] = comb; b.gnd[i] = gnd;
  b.objs.delete(i); if (isObject(comb)) b.objs.set(i, comb);
  if (ENCLOSE.has(old) || ENCLOSE.has(comb)) roomsDirty = true;
  touch(x, y);
}
function onRegion(d) {
  if (d.w !== B || d.h !== B || d.x % B || d.y % B) return;
  const bx = d.x / B, by = d.y / B, k = bkey(bx, by);
  const comb = [], gnd = [], lv = [], rf = d.roofs ? [] : null;
  for (let j = 0; j < B; j++) for (let i = 0; i < B; i++) { comb.push(d.rows[j][i]); gnd.push(d.ground[j][i]); lv.push(d.levels ? d.levels[j][i] : "@"); if (rf) rf.push(d.roofs[j].charCodeAt(i) - 48); }
  requested.delete(k);
  const old = blocks.get(k);
  if (old && old.drawn) {             // resync: only redraw what actually changed
    for (let i = 0; i < B * B; i++) {
      const r = rf ? rf[i] : 0;
      if (old.comb[i] === comb[i] && old.gnd[i] === gnd[i] && old.lv[i] === lv[i] && (old.rf ? old.rf[i] : 0) === r) continue;
      const raw = (lv[i].charCodeAt(0) - 48) | (r << 5);
      setTile(bx * B + i % B, by * B + (i / B | 0), comb[i], gnd[i], null, raw);
    }
    old.at = performance.now(); return;
  }
  const b = {bx, by, comb, gnd, lv, rf, objs: new Map(), drawn: false, canvas: null, at: performance.now()};
  comb.forEach((c, i) => { if (isObject(c)) b.objs.set(i, c); });
  blocks.set(k, b);
  // neighbours' edge tiles depend on this block for autotiling
  for (let i = 0; i < B; i++) { dirtyTiles.push(bx * B - 1, by * B + i, bx * B + B, by * B + i, bx * B + i, by * B - 1, bx * B + i, by * B + B); }
}

// =====================================================================================
//  Drawing one tile's ground layers into its block canvas (16 px cell)
// =====================================================================================
const isLand = (g) => g !== null && g !== "~" && g !== "=" && g !== ":";
const isObject = (c) => "TFbM*#%+^&?!x\"wtCQ;fBhLpKrgWVXYJmqeyUv".includes(c) && !GROUND.has(c);
function maskOf(x, y, pred) {
  let m = 0;
  const p = (dx, dy) => { const t = tile(x + dx, y + dy); return t === null ? true : pred(t[0], t[1], x + dx, y + dy); };
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
  b.reliefDirty = true;                              // (its stacked levels are rebuilt from this canvas: relief.js)
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
    groundMarks(g, x, y, gr, ox, oy);
  }
  // relief: each level lays its hill sheet (grass, darker grass, then stone) over the tiles at least that high; the
  // sheets' edge tiles carry the cliff face, so a plateau shows its south cliff and a soft rim round the rest
  const lv = levelAt(x, y);
  for (let k = 1; k <= lv; k++) drawBlobLayer(g, hillSheet(k), x, y, (cc, gg, tx, ty) => levelAt(tx, ty) >= k, ox, oy, k < 3 ? .25 : .1);
  if (lv && isLand(gr)) groundMarks(g, x, y, gr, ox, oy);           // paths, tilled soil, floors up on the hill
  if (gr === "-") drawBlobLayer(g, IMG.soil, x, y, (cc, gg) => gg === "-" && cc !== "R", ox, oy, .15);   // (old worlds)
  if (c === "R") drawBlobLayer(g, IMG.hill3, x, y, (cc) => cc === "R", ox, oy, .1);
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
// what's laid on the ground: tilled soil (wet or not), floors, ash, cobble
function groundMarks(g, x, y, gr, ox, oy) {
  if (gr === "o" || gr === "u") drawBlobLayer(g, IMG.tilled, x, y, (_, gg) => gg === "o" || gg === "u", ox, oy, 0);
  if (gr === "u") drawBlobLayer(g, IMG.tilled_wet, x, y, (_, gg) => gg === "u", ox, oy, 0);
  if (gr === "n") g.drawImage(IMG.bridge, 0, 32, 16, 16, ox, oy, 16, 16);
  if (gr === "'") drawBlobLayer(g, IMG.ash, x, y, (_, gg) => gg === "'", ox, oy, 0);
  if (gr === "_") g.drawImage(IMG.cobble, [16, 32, 0][Math.floor(hash(x, y, 9) * 3)], [16, 32, 48][Math.floor(hash(x, y, 10) * 3)], 16, 16, ox, oy, 16, 16);
}

// Level k's sheet: grass (1-2), darker grass (3-4), stone above; each layer up a touch brighter, so terraces of the
// same sheet still read as steps
const hillSheets = {};
function hillSheet(k) {
  if (hillSheets[k]) return hillSheets[k];
  const img = IMG[k <= 2 ? "hill1" : k <= 4 ? "hill2" : "hill3"], f = k <= 0 ? 1 : k <= 4 ? 1 + .04 * ((k - 1) % 2) : .92 + .024 * (k - 5);
  if (f === 1) return hillSheets[k] = img;
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d"); g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height), px = d.data;
  for (let i = 0; i < px.length; i += 4) for (let j = 0; j < 3; j++) px[i + j] = Math.min(255, px[i + j] * f);
  g.putImageData(d, 0, 0);
  return hillSheets[k] = c;
}
// A hill sheet with its top cleared: only its edges, rims and cliff faces (for holes, and the rock round caves)
// (the rock's own, underground: "rock", the stone sheet's edges a good deal darker, so a cave's rim reads as rock,
// not as a pale frame on the dark)
const EDGE_TOP = {hill1: [192, 212, 112], hill3: [193, 200, 185], rock: [193, 200, 185]}, edgeSheets = {};
function edgeSheet(name) {
  if (edgeSheets[name]) return edgeSheets[name];
  const img = IMG[name === "rock" ? "hill3" : name], c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d"); g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height), px = d.data, [r, gg, b] = EDGE_TOP[name];
  for (let i = 0; i < px.length; i += 4) {
    if (Math.abs(px[i] - r) + Math.abs(px[i + 1] - gg) + Math.abs(px[i + 2] - b) < 30) px[i + 3] = 0;
    else if (name === "rock") { px[i] *= .52; px[i + 1] *= .5; px[i + 2] *= .5; }
  }
  g.putImageData(d, 0, 0);
  return edgeSheets[name] = c;
}
function startBlock(b) {
  b.canvas = document.createElement("canvas"); b.canvas.width = B * 16; b.canvas.height = B * 16;
  b.ctx = b.canvas.getContext("2d"); b.drawn = true;
  for (let ly = B - 1; ly >= 0; ly--) for (let lx = B - 1; lx >= 0; lx--) dirtyTiles.push(b.bx * B + lx, b.by * B + ly);
}
function renderBlock(b) {
  b.canvas = document.createElement("canvas"); b.canvas.width = B * 16; b.canvas.height = B * 16;
  b.ctx = b.canvas.getContext("2d");
  for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly);
  b.drawn = true;
}
