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
// Relief: a level char per tile, a digit (the height) or a capital letter where stairs lead down to the south.
function lvChar(x, y) {
  const b = blocks.get(bkey(Math.floor(x / B), Math.floor(y / B)));
  return b ? b.lv[(y - b.by * B) * B + (x - b.bx * B)] : null;
}
const levelAt = (x, y) => { const c = lvChar(x, y); return c === null ? 0 : c >= "A" ? c.charCodeAt(0) - 65 : c.charCodeAt(0) - 48; };
const rampAt = (x, y) => { const c = lvChar(x, y); return c !== null && c >= "A"; };
function edgeAt(x, y) {                     // as World.edge: a hill's rim (a lower tile around it), stairs excepted
  const lv = levelAt(x, y);
  if (!lv || rampAt(x, y)) return false;
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if ((dx || dy) && levelAt(x + dx, y + dy) < lv) return true;
  return false;
}
function canStep(x0, y0, x1, y1) {          // as World.can_step: on the level, or up and down stairs; cliffs can't be climbed
  const l0 = levelAt(x0, y0), l1 = levelAt(x1, y1);
  if (l0 === l1) return true;
  if (x0 !== x1 || Math.abs(l0 - l1) !== 1) return false;
  const [ux, uy] = l0 > l1 ? [x0, y0] : [x1, y1];
  return rampAt(ux, uy) && Math.max(y0, y1) === uy + 1;
}
const gndAt = (x, y) => { const t = tile(x, y); return t ? t[1] : null; };
const dirtyTiles = [];                 // tiles to redraw (x, y), processed within a per-frame budget
function touch(x, y) { for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) dirtyTiles.push(x + dx, y + dy); }
// picked plants: full -> bare (fruit flies to the picker); bare -> full when it grows back
const PICK = {F: "U", b: "v"};
function setTile(x, y, comb, gnd, who = null, lv = null) {
  const bx = Math.floor(x / B), by = Math.floor(y / B), b = blocks.get(bkey(bx, by));
  if (!b) return;
  const i = (y - by * B) * B + (x - bx * B);
  const lc = lv === null ? b.lv[i] : String.fromCharCode(((lv & 16) ? 65 : 48) + (lv & 15));
  if (b.comb[i] === comb && b.gnd[i] === gnd && b.lv[i] === lc) return;
  if (b.lv[i] !== lc) { b.lv[i] = lc; for (let d = -2; d <= 2; d++) touch(x + d, y); }   // relief changed: edges around redraw
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
  const comb = [], gnd = [], lv = [];
  for (let j = 0; j < B; j++) for (let i = 0; i < B; i++) { comb.push(d.rows[j][i]); gnd.push(d.ground[j][i]); lv.push(d.levels ? d.levels[j][i] : "0"); }
  requested.delete(k);
  const old = blocks.get(k);
  if (old && old.drawn) {             // resync: only redraw what actually changed
    for (let i = 0; i < B * B; i++) {
      if (old.comb[i] === comb[i] && old.gnd[i] === gnd[i] && old.lv[i] === lv[i]) continue;
      const c = lv[i].charCodeAt(0), raw = c >= 65 ? (c - 65) | 16 : c - 48;
      setTile(bx * B + i % B, by * B + (i / B | 0), comb[i], gnd[i], null, raw);
    }
    old.at = performance.now(); return;
  }
  const b = {bx, by, comb, gnd, lv, objs: new Map(), drawn: false, canvas: null, at: performance.now()};
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
  // relief: each level lays its hill sheet (grass, darker grass, stone peaks) over the tiles at least that high; the
  // sheets' edge tiles carry the cliff face, so a plateau shows its south cliff and a soft rim round the rest
  const lv = levelAt(x, y);
  // (on a slope tile, every tile under the slope's pair counts as up there too, diagonals included, so no cliff face
  // or corner is drawn where the slope goes through; the slope piece draws its own sides)
  const onSlope = rampAt(x, y);
  const high = (k) => (c, gg, tx, ty) => levelAt(tx, ty) >= k || (onSlope && ty === y + 1 && rampAt(tx, y));
  for (let k = 1; k <= lv; k++) drawBlobLayer(g, IMG["hill" + k], x, y, high(k), ox, oy, k < 3 ? .25 : .1);
  if (lv && isLand(gr)) groundMarks(g, x, y, gr, ox, oy);           // paths, tilled soil, floors up on the hill
  drawStairs(g, x, y, ox, oy);
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
// what's laid on the ground: tilled soil (wet or not), floors, ash, cobble
function groundMarks(g, x, y, gr, ox, oy) {
  if (gr === "o" || gr === "u") drawBlobLayer(g, IMG.tilled, x, y, (_, gg) => gg === "o" || gg === "u", ox, oy, 0);
  if (gr === "u") drawBlobLayer(g, IMG.tilled_wet, x, y, (_, gg) => gg === "u", ox, oy, 0);
  if (gr === "n") g.drawImage(IMG.bridge, 0, 32, 16, 16, ox, oy, 16, 16);
  if (gr === "'") drawBlobLayer(g, IMG.ash, x, y, (_, gg) => gg === "'", ox, oy, 0);
  if (gr === "_") g.drawImage(IMG.cobble, [16, 32, 0][Math.floor(hash(x, y, 9) * 3)], [16, 32, 48][Math.floor(hash(x, y, 10) * 3)], 16, 16, ox, oy, 16, 16);
}
// Slopes: a 32x32 piece (tools/derived_art.py ramp_art) through a south cliff: its top half on the pair of slope
// tiles, its bottom half on the landing below them. Drawn a quarter per tile, so redrawing any one tile keeps it whole.
function drawStairs(g, x, y, ox, oy) {
  const up = rampAt(x, y), ry = up ? y : y - 1;
  if (!up && !rampAt(x, ry)) return;
  const west = rampAt(x + 1, ry), x0 = west ? x : x - 1;             // this column is the pair's west half or east
  const sheet = levelAt(x, ry) >= 2 ? IMG.ramp2 : IMG.ramp1;        // each terrace its own grass
  const variant = Math.floor(hash(x0, ry, 77) * 4) * 32;            // dashes, tufts, two grass steps, curved
  g.drawImage(sheet, variant + (west ? 0 : 16), up ? 0 : 16, 16, 16, ox, oy, 16, 16);
}
function renderBlock(b) {
  b.canvas = document.createElement("canvas"); b.canvas.width = B * 16; b.canvas.height = B * 16;
  b.ctx = b.canvas.getContext("2d");
  for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly);
  b.drawn = true;
}
