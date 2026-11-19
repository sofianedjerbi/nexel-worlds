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
// Where what is on row y, `lift` px up, is drawn: sy(y) - lift on the flat picture; in the bend of the curved world a
// height is part of where a thing is (curve.js: render.js's sy says it, sy.up)
const syUp = (sy, y, lift) => (sy.up ? sy.up(y, lift) : sy(y) - lift);
const bodyY = (p, sy) => syUp(sy, p.y, liftOf(p)) - STAND * zoom;      // a body's place on screen (the top of its tile, lifted with the ground it stands on, and STAND)

// Something flying off from a spot (a puff, a spark, debris): it keeps the height of where it started, however it
// drifts (it doesn't step up and down with the tiles it passes over)
function liftFrom(o) { if (o.lift === undefined) o.lift = liftOf({x: o.x, y: o.y}); return o.lift; }
// Screen px something on tile (x, y) is drawn higher by
const liftAt = (x, y) => (shOf(standAt(x, y)) + Models.up(x, y)) * zoom;      // (and on a model, a bridge's deck: on it, models.js)
// ...and someone between two tiles: in proportion to how far along they are (a body: at its own height, where a
// floor is built over a room: floors.js)
function liftOf(p) {
  const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
  const f = ax === bx ? p.y - ay : p.x - ax, a = (shOf(Floors.standOf(p, ax, ay)) + Models.up(ax, ay)) * zoom, b = (shOf(Floors.standOf(p, bx, by)) + Models.up(bx, by)) * zoom;
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
  const dd = Math.min(8, (sheet.dug || 1) - 1) / 8, seam = sheet.dug ? [1 + .1 * dd, .86 - .24 * dd] : [1, 1], out = {bands: [l.map((v, q) => (q < 3 ? Math.min(255, v * seam[0]) : v)), [(d[0] + l[0]) / 2, (d[1] + l[1]) / 2, (d[2] + l[2]) / 2], d.map((v, q) => (q < 3 ? v * seam[1] : v))], side, top: at(ix * 16 + 8, iy * 16 + 8),
               foot: ink + 1, inset: w0, north: n0};   // (in the tile: where its south face ends, its side edge and its far edge start) (seam: dug earth: the line between two layers is told from them, the more the deeper and darker it is: a wall's layers are counted)
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
