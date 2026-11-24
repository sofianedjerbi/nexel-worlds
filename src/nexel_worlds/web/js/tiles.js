// The client's copy of the world: 32x32 blocks patched by tile events, and the ground layer renderer.

// =====================================================================================
//  Tile store: 32x32 blocks, filled from the server and patched by tile events
// =====================================================================================
const B = 32, P = 16;
const smooth = (v) => { v = Math.max(0, Math.min(1, v)); return v * v * (3 - 2 * v); };   // 0..1, eased
const blocks = new Map();
const bkey = (bx, by) => bx + "," + by;
// The block a tile is in. Tiles are asked for in runs (a tile and the eight round it, a row of a picture), so the
// last block found is kept: no key to put together, nothing to look up. Forgotten whenever the blocks change.
let hitB = null, hitX = NaN, hitY = NaN;
for (const m of ["set", "delete", "clear"]) { const o = blocks[m].bind(blocks); blocks[m] = (...a) => { hitX = NaN; return o(...a); }; }
function blockOf(x, y) {
  const bx = Math.floor(x / B), by = Math.floor(y / B);
  if (bx !== hitX || by !== hitY) { hitX = bx; hitY = by; hitB = blocks.get(bkey(bx, by)) || null; }
  return hitB;
}
function tile(x, y) {
  const b = blockOf(x, y);
  if (!b) return null;
  const i = (y - b.by * B) * B + (x - b.bx * B);
  return [b.comb[i], b.gnd[i]];
}
const combAt = (x, y) => { const b = blockOf(x, y); return b ? b.comb[(y - b.by * B) * B + (x - b.bx * B)] : null; };   // (no pair made: asked thousands of times a frame)
const gndAt = (x, y) => { const b = blockOf(x, y); return b ? b.gnd[(y - b.by * B) * B + (x - b.bx * B)] : null; };
const dirtyTiles = [];                 // tiles to redraw (x, y), processed within a per-frame budget
function touch(x, y) { for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) dirtyTiles.push(x + dx, y + dy); }
// picked plants: full -> bare (fruit flies to the picker); bare -> full when it grows back
const PICK = {F: "U", b: "v"};
// What a tile is made of, as the world says it (views.py mats and stones, a tile event's `mat`, landblocks.py): "s", "d": the block put on its top (matAt);
// "": none; then "~" and its highest stone cell, the generator's (stoneAt: for good, whatever is dug: chunks.py)
const NO_STONE = -32768;
function putMat(b, i, m0) {
  const [m, z] = String(m0 || "").split("~");
  if (z !== undefined) (b.stone || (b.stone = new Int16Array(B * B).fill(NO_STONE)))[i] = +z;
  if (m === "s" || m === "d") (b.mat || (b.mat = {}))[i] = m; else if (b.mat) delete b.mat[i];
}
const stonesOf = (d, from) => { const s = new Int16Array(B * B); for (let j = 0; j < B; j++) for (let i = 0; i < B; i++) s[j * B + i] = d.stones[j].charCodeAt(i) - from; return s; };
function setTile(x, y, comb, gnd, who = null, col = null, mat = null) {    // (col: its column of cells, when sent: cells.js; mat: what it is made of, when sent: putMat)
  const bx = Math.floor(x / B), by = Math.floor(y / B), b = blocks.get(bkey(bx, by));
  if (!b) return;
  b.edits = (b.edits || 0) + 1;              // (what the world changed in this block: xray.js's key. landVer counts drawing too: a block coming in moves it for a hundred frames)
  const i = (y - by * B) * B + (x - bx * B);
  const relief = col !== null && !colSame(col, colAt(x, y));
  if (mat !== null) putMat(b, i, mat);
  if (b.comb[i] === comb && b.gnd[i] === gnd && !relief) return;
  if (relief) {                              // the land changed: edges around redraw
    b.lv[i] = String.fromCharCode(SEA + colFloor(col));
    if (col.length > 1) (b.col || (b.col = {}))[i] = col; else if (b.col) delete b.col[i];
    for (let d = -2; d <= 2; d++) touch(x + d, y);
  }
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
  touch(x, y);
  landVer++;      // (the land is new from now, not from when its tile is drawn again in a frame to come: the way out (wayshow.js) kept, for that frame, the way found while a tunnel's end was shut)
}
function onRegion(d) {
  if (d.w !== B || d.h !== B || d.x % B || d.y % B) return;
  const bx = d.x / B, by = d.y / B, k = bkey(bx, by);
  const comb = [], gnd = [], lv = [], col = d.cols || null;     // (col: the hollow tiles' columns, by index)
  for (const i in col) col[i] = colIn(col[i]);
  const from = d.sea || 64;                                    // (what its heights' chars are counted from: a server from before, and the first screen's island, 64)
  for (let j = 0; j < B; j++) for (let i = 0; i < B; i++) { comb.push(d.rows[j][i]); gnd.push(d.ground[j][i]); lv.push(String.fromCharCode(d.levels ? d.levels[j].charCodeAt(i) - from + SEA : SEA)); }
  requested.delete(k);
  const old = blocks.get(k);
  if (old && old.drawn) {             // resync: only redraw what actually changed
    for (let i = 0; i < B * B; i++) {
      const c = col && col[i] !== undefined ? col[i] : colSolid(lv[i].charCodeAt(0) - SEA);
      if (old.comb[i] === comb[i] && old.gnd[i] === gnd[i] && colSame(c, colAt(bx * B + i % B, by * B + (i / B | 0)))) continue;
      setTile(bx * B + i % B, by * B + (i / B | 0), comb[i], gnd[i], null, c, (d.mats && d.mats[i]) || "");
    }
    if (d.stones) old.stone = stonesOf(d, from);
    Floors.load(old, d); Flow.load(old, d);
    old.at = performance.now(); return;
  }
  const b = {bx, by, comb, gnd, lv, col, mat: null, stone: d.stones ? stonesOf(d, from) : null, objs: new Map(), drawn: false, canvas: null, at: performance.now()};   // (no stones: the first screen's island, stoneAt guesses)
  for (const i in d.mats || {}) putMat(b, i, d.mats[i]);
  Floors.load(b, d); Flow.load(b, d);               // (what is built over its land: floors.js; water that runs: flow.js)
  comb.forEach((c, i) => { if (isObject(c)) b.objs.set(i, c); });
  blocks.set(k, b);
  // neighbours' edge tiles depend on this block for autotiling
  for (let i = 0; i < B; i++) { dirtyTiles.push(bx * B - 1, by * B + i, bx * B + B, by * B + i, bx * B + i, by * B - 1, bx * B + i, by * B + B); }
}

// =====================================================================================
//  Drawing one tile's ground layers into its block canvas (16 px cell)
// =====================================================================================
const isLand = (g) => g !== null && !wet(g) && g !== ":";
const isObject = (c) => "TFbM*#%+^&?!x\"wtCQ;fBhLpKrgWVXYJmqeyUvl".includes(c) && !GROUND.has(c);
const AROUND = [0, -1, N_, 1, 0, E_, 0, 1, S_, -1, 0, W_, 1, -1, NE, 1, 1, SE, -1, 1, SW, -1, -1, NW];
function maskOf(x, y, pred) {
  let m = 0;
  for (let k = 0; k < 24; k += 3) {                          // (N E S W, then the corners: straight from each one's block, nothing made)
    const nx = x + AROUND[k], ny = y + AROUND[k + 1], b = blockOf(nx, ny), i = b ? (ny - b.by * B) * B + (nx - b.bx * B) : 0;
    if (!b || pred(b.comb[i], b.gnd[i], nx, ny)) m |= AROUND[k + 2];
  }
  return m;
}
function hash(x, y, s = 0) {
  let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + Math.imul(s, 2246822519)) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
// ONE RULE FOR A SURFACE'S CELL: a ground laid on a tile is a cell of its sheet picked by which of the eight tiles round it are of
// the same ground (maskOf, blobCell: its rims and corners); a tile wholly in it, now and then (decor: how often) one of the sheet's
// speckled cells instead of the plain one (plainCell; a floor under the land too, hd.js)
function plainCell(sheet, x, y, decor) {
  if (!decor || hash(x, y, 3) >= decor) { const [cx, cy] = blobCell(255); return [cx * 16, cy * 16]; }
  return [Math.floor((decor > .3 && sheet !== IMG.grass ? hash(x, y, 4) ** 3 : hash(x, y, 4)) * (sheet === IMG.grass ? 6 : 5)) * 16, (5 + (hash(x, y, 5) < .5 ? 0 : 1)) * 16];      // (stone, earth: mostly their fine specks, the first three; their big pale blobs seldom)
}
function drawBlobLayer(g, sheet, x, y, pred, decor) {
  const m = maskOf(x, y, pred), [cx, cy] = blobCell(m);
  g.drawImage(sheet, ...(reduce(m) === 255 ? plainCell(sheet, x, y, decor) : [cx * 16, cy * 16]));
}
// The land is painted in the page, a px a number, and handed to the GPU whole, once (a block's ground: relief.js).
// Painted through canvases a piece at a time, a phone's GPU got it wrong where a desktop's did not.
// A sheet's px, read once: a Uint32 a px, its alpha on top.
const sheetPx = new Map();
function sheetData(sheet) {
  let m = sheetPx.get(sheet);
  if (!m) {
    const c = document.createElement("canvas"); c.width = sheet.width; c.height = sheet.height;
    const g = c.getContext("2d", {willReadFrequently: true}); g.drawImage(sheet, 0, 0);
    m = {px: new Uint32Array(g.getImageData(0, 0, c.width, c.height).data.buffer), w: c.width, solid: new Map()}; sheetPx.set(sheet, m);
  }
  return m;
}
// Is a sheet's 16 px cell drawn in full, every px of it solid? (what is under such a cell does not show)
function cellSolid(sheet, sx, sy) {
  const m = sheetData(sheet), key = sy * 4096 + sx; let v = m.solid.get(key);
  if (v === undefined) {
    v = true;
    for (let j = 0; j < 16 && v; j++) for (let i = 0; i < 16; i++) if (m.px[(sy + j) * m.w + sx + i] >>> 24 !== 255) { v = false; break; }
    m.solid.set(key, v);
  }
  return v;
}
// A px over another, as a canvas lays it (the sheets' shadows are see-through)
function pxOver(s, d) {
  const sa = (s >>> 24) / 255, da = (d >>> 24) / 255 * (1 - sa), a = sa + da;
  const ch = (k) => Math.round(((s >>> k & 255) * sa + (d >>> k & 255) * da) / a);
  return (Math.round(a * 255) << 24 | ch(16) << 16 | ch(8) << 8 | ch(0)) >>> 0;
}
// A sheet's cell laid on px (to, W wide, at o): a solid one copied a row at a time, another px by px over what is there
function layCell(to, o, W, sheet, sx, sy, solid) {
  const m = sheetData(sheet);
  for (let j = 0, s = sy * m.w + sx; j < 16; j++, s += m.w, o += W) {
    if (solid) { to.set(m.px.subarray(s, s + 16), o); continue; }
    for (let i = 0; i < 16; i++) { const v = m.px[s + i], a = v >>> 24; if (a === 255) to[o + i] = v; else if (a) to[o + i] = pxOver(v, to[o + i]); }
  }
}
// What a tile is made of is first noted, a sheet's cell after the other (LAID), then painted from the last cell that
// is solid all over: on a plateau twelve layers high, the one that shows and not the thirteen under it.
const LAID = {n: 0, img: [], at: [], drawImage(img, sx, sy) { this.img[this.n] = img; this.at[this.n++] = sy * 4096 + sx; }};
let landVer = 0;                                    // (goes up whenever a tile of the land is drawn again: what was worked out from the land is out of date)
function drawTile(x, y, to = null) {                 // (to: the px it is painted into, {px, o, w}: the HD look's top of it, voxels.js; none: the tile changed)
  const b = blockOf(x, y);
  if (!b || !(to || b.px)) return;
  if (!to) { b.ver = (b.ver || 0) + 1; landVer++; return; }   // (the HD look paints its own tops (to): what was worked out from the tile is out of date)
  const i = (y - b.by * B) * B + (x - b.bx * B), c = b.comb[i], gr = b.gnd[i], g = LAID, lv = levelAt(x, y);
  g.n = 0;
  // a tile up on the land: its level's hill sheet, a plain top (its rim is the land's, by its cells: voxpaint.js rim). Its ground and
  // what is laid on it by the one rule (drawBlobLayer): soil, the grass over it, then paths, fields, floors, ash, a hedge
  let k = lv;
  for (; k >= 1; k--) { drawBlobLayer(g, hillSheet(k), x, y, () => true, k < 3 ? .25 : k < 5 ? .1 : .45); if (cellSolid(g.img[g.n - 1], g.at[g.n - 1] % 4096, g.at[g.n - 1] >> 12)) break; }
  const hills = g.n, covered = k >= 1;
  if (!covered && isLand(gr)) {                       // (a bridge that runs onto this land: no shore between them)
    drawBlobLayer(g, IMG.soil, x, y, (_, gg, tx, ty) => isLand(gg) || Bridge.rests(x, y, tx, ty), .15);
    if (lv >= 0 && (gr === "." || gr === "_" || gr === "n")) drawBlobLayer(g, IMG.grass, x, y, (_, gg, tx, ty) => gg === "." || gg === "_" || gg === "n" || Bridge.rests(x, y, tx, ty), gr === "." ? .3 : 0);
  }
  const base = g.n;
  if (isLand(gr)) groundMarks(g, x, y, gr);
  if (c === "H") drawBlobLayer(g, IMG.hedge, x, y, (cc) => cc === "H", 0);
  const f = floatAt(x, y); if (f >= 0) g.drawImage(IMG.water_objects, FLOATS[f] * 16, 0);
  // in the order they lie: the ground, the hill's levels from the lowest (they were noted from the top down), then what is laid
  // on top. From the last one that hides all under it.
  const order = [];
  for (let j = hills; j < base; j++) order.push(j);
  for (let j = hills - 1; j >= 0; j--) order.push(j);
  for (let j = base; j < g.n; j++) order.push(j);
  let first = order.length - 1;
  while (first >= 0 && !cellSolid(g.img[order[first]], g.at[order[first]] % 4096, g.at[order[first]] >> 12)) first--;
  const at = (q) => [g.img[order[q]], g.at[order[q]] % 4096, g.at[order[q]] >> 12], px = to.px, W = to.w, o = to.o;
  if (first < 0) for (let j = 0; j < 16; j++) px.fill(0, o + j * W, o + j * W + 16);   // (nothing solid all over it: what was there must go first)
  for (let q = Math.max(0, first); q < order.length; q++) layCell(px, o, W, ...at(q), q === first);
  if (!wet(gr)) deepen(px, o, W, 16, lv, "floor");
}
// What floats on shore water (lily pads, reeds, little rocks): which of FLOATS (water_objects' cells), or -1. One answer for the top's paint and the bed's shade under it (waterbed.js)
const FLOATS = [8, 9, 10, 11, 6, 7, 0];
function floatAt(x, y) {
  const h = hash(x, y, 41); if (gndAt(x, y) !== "~" || h >= .09) return -1;
  return h < .015 || [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => isLand(gndAt(x + dx, y + dy))) ? Math.floor(hash(x, y, 42) * 7) : -1;
}
// What is laid on the ground, the same at any height: a layer each, a sheet laid by the one rule (on: the grounds that are of it), or a
// cell picked by its place (cell: paths, pavement.js; furrows, furrows.js: made to run on from tile to tile). Tilled soil: soil to its
// edges, its furrows (it was the pack's patch, a line 10 px inside its outer tiles, up on a hill, and furrows on the meadow: two fields by their height)
const SOIL = {cell: (x, y) => [IMG.soil, ...plainCell(IMG.soil, x, y, 0)]}, FURROWS = {cell: (x, y) => Furrows.cell(x, y)};
const MARKS = {o: [SOIL, FURROWS], u: [SOIL, FURROWS, {sheet: "tilled_wet", on: "u"}],
  "'": [{sheet: "ash", on: "'"}], n: [{cell: () => [IMG.house_walls, 16, 16]}], _: [{cell: (x, y) => Pave.cell(x, y)}]};   // (n: a floor, the pack's house floor, solid all over)
function groundMarks(g, x, y, gr) {
  for (const m of MARKS[gr] || []) if (m.cell) g.drawImage(...m.cell(x, y)); else drawBlobLayer(g, IMG[m.sheet], x, y, (_, gg) => m.on.includes(gg), 0);
}

// UNDER SEA LEVEL the land is the same earth, darker the deeper: ONE tone by depth, laid on the land's own paints (a floor's soil,
// tiles.js drawTile and hd.js under; a wall's front, voxpaint.js front): 1 at sea level and over, a step a level down to eight
// levels (as dark as it gets), still warm brown; a floor less than a wall: where you walk is told from what stops you.
// (It was a second family of sheets, the soil's and the hill's recoloured a copy a level: dugSheet.) No grass grows down there:
// a hole three deep with a grass floor looked like a raised table.
const DEEP = {wall: [[.075, .45], [.09, .38], [.11, .3]], floor: [[.0475, .62], [.054, .57], [.0625, .5]]};
const deepTone = (z, kind) => DEEP[kind].map(([k, lo]) => Math.max(lo, 1 - k * Math.min(8, Math.max(0, -z))));
function deepen(px, o, W, rows, z, kind) {            // rows of 16 px from o, W a row: their paint at depth z
  if (z >= 0) return; const [r, g, b] = deepTone(z, kind);
  for (let j = 0; j < rows; j++) for (let i = o + j * W; i < o + j * W + 16; i++) { const v = px[i]; px[i] = (v & 0xff000000 | ((v >>> 16 & 255) * b) << 16 | ((v >>> 8 & 255) * g) << 8 | (v & 255) * r) >>> 0; }
}
// Level k's sheet: grass (1-2), darker grass (3-4), stone above; each layer up a touch brighter, so terraces of the
// same sheet still read as steps
// (stone: a top a step darker each level under 12, .825 of the sheet's own at 5: light enough that the lowest top is far lighter than a wall; its wall: one tone,
// darker than the darkest top and cooler, so a top is told from the face under it by value and by hue: with the tops down to .75 and the wall at .88 the low terraces were one grey mass)
const hillSheets = {}, ROCK_TONE = {step: .025, wall: [.79, .81, .87]};
function hillSheet(k) {
  const rock = k === "rock"; if (!rock) k = Math.min(k, 12);      // (the mountains' top: one sheet for all that is built higher) ("rock": stone's wall, voxpaint.js)
  if (hillSheets[k]) return hillSheets[k];
  const img = IMG[k <= 2 ? "hill1" : k <= 4 ? "hill2" : "hill3"], f = k <= 4 ? [1.015, 1.03, 1.04, 1.06][k - 1] : rock ? 0 : 1 - ROCK_TONE.step * (12 - k);      // (the greens an even step lighter a level across the two sheets: level 3 was darker than level 2) (stone: the sheet's own at 12, the mountains' top, and a clear step darker each level down to 5, a touch cooler: never lighter than the sheet (at 12 its top was a blank pale plate, its rim bleached with it), and a terrace is told from the next by its top alone, from where no wall of it is seen. Its walls: one tone, voxpaint.js)
  if (f === 1) return hillSheets[k] = img;
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d"); g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height), px = d.data;
  for (let i = 0; i < px.length; i += 4) for (let j = 0; j < 3; j++) px[i + j] = Math.min(255, px[i + j] * (rock ? ROCK_TONE.wall[j] : j === 2 && f < 1 ? f ** .85 : f));
  g.putImageData(d, 0, 0);
  return hillSheets[k] = c;
}
// A block come in: none of it is painted (the HD look paints the tops it shows: hd.js, voxels.js), the block is there at once
// (its tiles' bookkeeping: voxels.js, hd.js wrap this)
const NOPX = new Uint32Array(0);
function arriveBlock(b) { b.px = NOPX; b.drawn = true; b.ver = (b.ver || 0) + 1; landVer++; }
