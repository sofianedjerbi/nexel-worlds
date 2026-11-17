// What is behind higher ground: someone standing there is cut at its edge (relief.js draws that ground)

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
// The top edge of the higher ground drawn up from in front of a tile (south of row `row`, in column tx), at each of
// the column's 16 px, in art px of the world (Infinity: none there). Every layer of that ground in its own shape
// (cellTop), from the layer over `from` (the height it is seen from) up; only ground at least `least` high counts;
// `far`: the rows looked at; skip: tiles that don't count (the rock the x-ray circle sees through).
// Kept until the land changes (landVer, tiles.js) or, with `skip`, what is seen through does: it was worked out again
// for every body and every tree behind a hill in every frame, five columns of eight rows each: most of the memory
// the page made (12 to 23 MB a second as a phone: the collector's work). The array is the cache's own: not to be written in.
const FLAT_TOP = new Uint8Array(16), EDGES = [new Map(), new Map()];
let edgesAt = -1, edgesPic = null, edgesOn = false;
function frontEdge(tx, row, from, least, far, skip) {
  if (edgesAt !== landVer || EDGES[0].size > 6000) { edgesAt = landVer; EDGES[0].clear(); EDGES[1].clear(); }
  if (edgesPic !== xray.pic || edgesOn !== xray.a > .01) { edgesPic = xray.pic; edgesOn = xray.a > .01; EDGES[1].clear(); }   // (what xrayGone goes by)
  const memo = far === 8 ? EDGES[skip ? 1 : 0] : null, key = ((tx + 524288) * 1048576 + row + 524288) * 4096 + (from + 32) * 64 + least + 32;
  const kept = memo && memo.get(key);
  if (kept) return kept;
  const edge = new Float64Array(16).fill(Infinity);
  for (let ty = row + 1; ty <= row + far; ty++) {
    const lv = levelAt(tx, ty);
    if (lv < least || (skip && skip(tx, ty))) continue;
    for (let k = from + 1; k <= lv; k++) {
      const top = k < 0 ? FLAT_TOP : cellTop(hillSheet(k), ...blobCell(maskOf(tx, ty, (cc, gg, ux, uy) => levelAt(ux, uy) >= k))), Y = ty * 16 - shOf(k);   // (dug: cut square, relief.js)
      for (let i = 0; i < 16; i++) if (top[i] < 16) edge[i] = Math.min(edge[i], Y + top[i]);
    }
  }
  if (memo) memo.set(key, edge);
  return edge;
}
// Someone standing behind higher ground (it is south of them, drawn up over where they stand) is behind it: what of
// them is under its top edge isn't drawn. Called before drawing them: clips the canvas down to that edge and returns
// true (restore after); false when nothing hides them. Nothing of the land is redrawn. The edge is the ground's own,
// an art px column at a time: each of its layers in its own shape, set in a little from the tile's side and rounded
// at its corners (cut straight across a tile, the sprite was gone where a corner lets the ground behind it show).
// part (in the x-ray circle, xray.js): 1: behind the ground that is not seen through alone; 2: only what of them the
// rock seen through hides (drawn a second time, as faint as the circle is there)
const CLIP_TO = [], CLIP_FROM = [];                        // (a body's columns, written over each time: nothing made a frame)
function clipBehind(p, sx, sy, S, part = 0) {
  const x = Math.round(p.x), y = Math.round(p.y);
  const L = hollow(x, y) ? Floors.standOf(p, x, y) : standAt(x, y);   // (between two tiles: the ground they are over: past its edge, a jump is on the higher one; under a roof: the floor they are on, behind the ground in front as in a hole)
  const x0 = Math.floor(p.x) - 2, x1 = Math.ceil(p.x) + 2, feet = sy(p.y + 1) - shOf(L) * zoom + (4 - STAND) * zoom, row = Math.floor(p.y), base = sy(0), n = x1 - x0 + 1;
  const at = (e) => (e === Infinity ? 1e4 : base + e * zoom);   // (an edge, in art px of the world: where it is on the screen)
  let any = part === 2;
  for (let c = 0; c < n; c++) {                           // (the top of the higher ground in front, at each px of each column)
    const to = CLIP_TO[c] = frontEdge(x0 + c, row, L, L + 1, 8, part ? xrayGone : null);
    CLIP_FROM[c] = part === 2 ? frontEdge(x0 + c, row, L, L + 1, 8, null) : null;
    for (let i = 0; i < 16 && !any; i++) any = at(to[i]) < feet;                        // (reaching up to their feet, or their shadow)
  }
  if (!any) return false;
  ctx.save(); ctx.beginPath();
  if (part < 2) { ctx.rect(-1e4, -1e4, sx(x0) + 1e4, 2e4); ctx.rect(sx(x1 + 1), -1e4, 1e4, 2e4); }
  for (let c = 0; c < n; c++) {
    const to = CLIP_TO[c], from = CLIP_FROM[c];
    for (let i = 0, j; i < 16; i = j) {                    // (a run of px with the same edge: one strip)
      for (j = i + 1; j < 16 && to[j] === to[i] && (!from || from[j] === from[i]); j++);
      const top = from ? at(from[i]) : -1e4, foot = at(to[i]);
      if (foot > top) ctx.rect(sx(x0 + c) + i * zoom, top, (j - i) * zoom, foot - top);
    }
  }
  ctx.clip();
  return true;
}
// Drawn behind the ground in front of it, and through the rock the x-ray circle sees through (xray.js): as hidden as
// ever, and over that what the rock hides of it, as faint as the circle is there (whole in its clear middle).
// draw(a): draws it, a: how strong
function drawBehind(p, sx, sy, S, draw) {
  const shows = xrayShows(p), cut = clipBehind(p, sx, sy, S, shows > .98 ? 1 : 0);
  draw(1);
  if (cut) ctx.restore();
  if (cut && shows > .02 && shows <= .98) { clipBehind(p, sx, sy, S, 2); draw(shows); ctx.restore(); }
}
// What stands or lies on a tile (a tree, a rock, a fence, things dropped) is behind higher ground as anybody is, and
// cut at its edge the same way. Most of it is behind nothing: which tiles are is kept a block, until the land changes,
// so a frame asks nothing for the rest.
function tileBehind(x, y) {
  const b = blocks.get(bkey(Math.floor(x / B), Math.floor(y / B))); if (!b) return false;
  if (b.behindAt !== landVer) { b.behindAt = landVer; b.behind = new Map(); }
  const i = (y - b.by * B) * B + x - b.bx * B;
  let v = b.behind.get(i);
  if (v === undefined) {
    v = false; const L = standAt(x, y);
    for (let tx = x - 1; tx <= x + 1 && !v; tx++) for (let ty = y + 1; ty <= y + 8 && !v; ty++) v = (levelAt(tx, ty) - L) * RELIEF_STEP > (ty - y - 1) * 16;
    b.behind.set(i, v);
  }
  return v;
}
// Is the spot (x, y: tiles, with fractions) behind higher ground drawn up over it? (Dust and sparks there aren't shown.)
// Higher ground: on the level nothing is behind anything. (It compared 0 with less than 0 there, and a row too far:
// every puff of dust, spark and splash that wasn't on the very top line of its tile went unseen, everywhere.)
function behindHill(x, y) {
  const tx = Math.floor(x), fy = Math.floor(y);
  const L = standAt(tx, fy), through = xrayAt(x - .5, y - .5 - shOf(L) / 16) > .5;   // (in the x-ray circle, xray.js: the rock it sees through hides nothing)
  for (let ty = fy + 1; ty <= fy + 7; ty++) {
    const up = (levelAt(tx, ty) - L) * RELIEF_STEP;        // art px its top is drawn up over the ground the spot is on
    if (up > 0 && up >= (ty - y) * 16 && !(through && xrayGone(tx, ty))) return true;
  }
  return false;
}
