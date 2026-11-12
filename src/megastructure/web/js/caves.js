// Caves (client). The land is cells (cells.js); a cave is empty cells under solid ones, and nothing more. From outside
// it is the hill over it; where its empty cells meet a face of the hill you can see, they show (an entry is only
// that). The cave you walk into is seen through the hill, like a house with its roof off. (The lifted ground: relief.js.)

// The cave you're in: from your tile, the tiles beside it you'd walk (or drop) onto under solid cells, and on from
// there (up to a few thousand). "x,y" -> the height of its floor there.
function caveOf(at) {
  const seen = new Map([[at.x + "," + at.y, at.z]]), stack = [[at.x, at.y, at.z]];
  while (stack.length && seen.size < 4000) {
    const [x, y, z] = stack.pop();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const k = (x + dx) + "," + (y + dy);
      if (seen.has(k)) continue;
      const z2 = landAt(z, x + dx, y + dy);
      if (z2 !== null && coveredAt(x + dx, y + dy, z2)) { seen.set(k, z2); stack.push([x + dx, y + dy, z2]); }
    }
  }
  return seen;
}
// Walking into a cave (or out): that cave is shown through the hill (or not) at once. Nothing of the land is redrawn:
// the open cave is an overlay, a canvas a block, drawn once (below).
let caveStamp = 0;                        // (goes up when the open cave changes: the overlays are redrawn)
function setCaveOpen() {
  const me = ents.get("agent" + myId);
  let into = null;                        // the cave tile you're stepping into: its cave opens as you set off, not half way
  if (me) {
    const x = Math.round(me.x), y = Math.round(me.y);        // (where you're seen, which runs ahead of the server's tile)
    if (!myAt || myAt.x !== x || myAt.y !== y) {             // your height, kept as the server keeps it (Movement.landing)
      let z = myAt && Math.abs(myAt.x - x) + Math.abs(myAt.y - y) === 1 ? landAt(myAt.z, x, y) : null;
      if (z === null) z = settleAt(x, y, meObs && meObs.self.z !== undefined ? meObs.self.z : 99);   // (woken, moved: where the server has you)
      myAt = {x, y, z};
    } else myAt.z = settleAt(x, y, myAt.z);                  // (the ground dug from under you: down you come)
    const ox = x + (me.x > x + .001 ? 1 : me.x < x - .001 ? -1 : 0), oy = y + (me.y > y + .001 ? 1 : me.y < y - .001 ? -1 : 0);
    if ((ox !== x) !== (oy !== y)) { const z = landAt(myAt.z, ox, oy); if (z !== null && coveredAt(ox, oy, z)) into = {x: ox, y: oy, z}; }
  }
  showXYZ();
  const here = myAt && coveredAt(myAt.x, myAt.y, myAt.z) ? myAt : into;
  if (!here === !caveOpen && (!here || openCave.get(here.x + "," + here.y) === here.z)) return;
  caveOpen = !!here; openCave = here ? caveOf(here) : new Map(); caveStamp++;
}
// Someone under a hill you're not in: not seen. (You: by the height you're at; the others, by the server's.)
function unseen(p) {
  const x = Math.round(p.x), y = Math.round(p.y);
  if (!roofAt(x, y) || inOpenCave(x, y)) return false;
  return coveredAt(x, y, p.e.kind === "agent" && p.e.id === myId && myAt ? settleNear(x, y, myAt.z) : p.e.z !== undefined ? p.e.z : floorAt(x, y));
}

// A block's caves as seen now, on one canvas in art px (with OV_M px round it), or null when there's nothing to see:
// where the empty cells of its hills show on their faces, and the open cave's floor, shadowed along its edges, with the wall
// at its back.
const OV_M = 128, HOLE = "#2a1d28", HOLE_DEEP = "#1d141c", HOLE_RIM = "rgba(48,30,34,.55)", SHADE = "30,20,28";
// The empty cells of the hill on (x, y) that show on its face toward (dx, dy): runs [lowest, highest] of cells above
// the ground in front of it and under its top. (None where that side isn't lower, or for the cave you're in.)
function shownVoids(x, y, dx, dy) {
  const c = colAt(x, y), top = colTop(c), front = topAt(x + dx, y + dy), out = [];
  if (front >= top || inOpenCave(x, y)) return out;
  for (let z = front + 1; z < top; z++) {
    if (c >>> (z - LOW) & 1) continue;
    const lo = z; while (z + 1 < top && !(c >>> (z + 1 - LOW) & 1)) z++;
    out.push([lo, z]);
  }
  return out;
}
const shownCell = (x, y, z, dx, dy) => !inOpenCave(x, y) && z > topAt(x + dx, y + dy) && z < topAt(x, y) && !solidAt(x, y, z);
// The openings on one face of a hill tile, a cell at a time: an opening is only the empty cells that show there, so
// cells side by side or one over the other (on this tile or the next along the face) run together into one hole of
// whatever shape they make. (X, Y): the tile's corner at sea level, in art px. Always in the hill's wall: facing south
// a layer of the wall a cell; facing east or west a layer of the side's wall a cell (the lowest outermost), open
// outward; under the lowest its shadow spills out (on the ground, or down the wall). Facing north it is behind the
// hill: only that shadow, on the ground from under the hill's edge, fading.
function drawFace(g, X, Y, x, y, dx, dy) {
  const top = topAt(x, y), front = topAt(x + dx, y + dy), cols = colsOf(hillSheet(Math.max(1, top))), px = dy ? 1 : 0, py = dy ? 0 : 1;
  const open = (z, side) => shownCell(x + side * px, y + side * py, z, dx, dy);      // the same cell, a tile along the face
  const fill = (col, ax, ay, w, h) => { if (w > 0 && h > 0) { g.fillStyle = col; g.fillRect(X + ax, Y + ay, w, h); } };
  const spill = (z, at) => {                              // its shadow: in steps, rounded off where the opening ends
    const ends = [open(z, -1) ? 1 : 0, open(z, 1) ? 1 : 0];
    for (const [d, al] of [[9, .17], [5, .17]]) for (let a = 0; a < 16; a++) {
      const f = a < 8 ? (ends[0] ? 1 : (a + .5) / 8) : ends[1] ? 1 : (15.5 - a) / 8;
      at(a, Math.round(d * Math.sqrt(1 - (1 - f) ** 2)), `rgba(${SHADE},${al})`);
    }
  };
  for (let z = front + 1; z < top; z++) {
    if (!shownCell(x, y, z, dx, dy)) continue;
    const a = open(z, -1) ? 0 : 2, e = open(z, 1) ? 0 : 2, roofed = !shownCell(x, y, z + 1, dx, dy), low = !shownCell(x, y, z - 1, dx, dy);
    if (dy < 0) {                                         // north: its shadow only, cut to the edge tile's own shape
      if (z !== front + 1) continue;
      const y0 = cols.north - shOf(top) + 4;
      [.4, .28, .18, .09].forEach((al, k) => fill(`rgba(${SHADE},${al})`, a ? 1 : 0, y0 - 3 * (k + 1), 16 - (a ? 1 : 0) - (e ? 1 : 0), 3));
      const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, tx, ty) => levelAt(tx, ty) >= top)), shape = cellAlpha(hillSheet(Math.max(1, top)), cx, cy);
      for (let j = 0; j < cols.north + 4; j++) for (let q = 0; q < 16; q++) if (shape[j * 16 + q]) g.clearRect(X + q, Y - shOf(top) + j, 1, 1);
    } else if (dy > 0) {                                  // south: the wall's layer z, the RELIEF_STEP px over foot - shOf(z - 1)
      const foot = colsOf(hillSheet(Math.max(1, z))).foot - shOf(z - 1), y0 = foot - RELIEF_STEP + (roofed ? 1 : 0);
      fill(HOLE_RIM, a - (a ? 1 : 0), y0 - (roofed ? 1 : 0), 16 - a - e + (a ? 1 : 0) + (e ? 1 : 0), foot - y0 + (roofed ? 1 : 0));    // its rim: a px round it, where it ends
      fill(HOLE, a, y0, 16 - a - e, foot - y0);
      if (roofed) { fill(HOLE_DEEP, a + (a ? 1 : 0), y0 + 1, 16 - a - e - (a ? 1 : 0) - (e ? 1 : 0), 3); for (const [q, n] of [[a, a && 2], [16 - e - 2, e && 2]]) if (n) { g.clearRect(X + q + (q === a ? -1 : 1), Y + y0 - 1, 2, 2); fill(HOLE_RIM, q + (q === a ? 0 : 1), y0, 1, 1); } }
      if (low) spill(z, (ax, d, col) => fill(col, ax, foot, 1, d));
    } else {                                              // east, west: the side wall's layer z (LEDGE px, the lowest outermost)
      const m = (ax, w) => (dx > 0 ? 16 - ax - w : ax), out = cols.inset - LEDGE * Math.min(top - z, SIDE_MAX), Yg = -shOf(front);   // (the side's wall shows SIDE_MAX layers at the most)
      fill(HOLE, m(out, LEDGE), Yg + 1 + a, LEDGE, 16 - a - e);
      if (a) fill(HOLE_RIM, m(out, LEDGE), Yg + a, LEDGE, 1);
      if (e) fill(HOLE_RIM, m(out, LEDGE), Yg + 17 - e, LEDGE, 1);
      if (roofed) fill(HOLE_DEEP, m(out + LEDGE - 1, 1), Yg + 2 + a, 1, 14 - a - e);
      if (low) spill(z, (ay, d, col) => fill(col, dx > 0 ? 16 - out : out - d, Yg + 1 + ay, d, 1));
    }
  }
}
// The edge of the open cave's edge tiles: its floor right to the tile's edge, a soft shadow along it where the rock is
function caveEdge(g, x, y, z, X, Y) {
  const inCave = (tx, ty) => inOpenCave(tx, ty) || (!roofAt(tx, ty) && Math.abs(topAt(tx, ty) - z) <= 1);
  const W = !inCave(x - 1, y), E = !inCave(x + 1, y), N = !inCave(x, y - 1), S = !inCave(x, y + 1);
  [.34, .24, .15, .08].forEach((al, k) => {
    g.fillStyle = `rgba(${SHADE},${al})`;
    if (W) g.fillRect(X + k, Y, 1, 16);
    if (E) g.fillRect(X + 15 - k, Y, 1, 16);
    if (N) g.fillRect(X, Y + k, 16, 1);
    if (S) g.fillRect(X, Y + 15 - k, 16, 1);
  });
}
function buildCaveOverlay(b) {
  let c = null, g = null;
  const need = () => { if (!c) { c = document.createElement("canvas"); c.width = c.height = B * 16 + 2 * OV_M; g = c.getContext("2d"); } };
  for (const key in b.col) {                              // (only its hollow tiles)
    const i = +key, x = b.bx * B + i % B, y = b.by * B + (i / B | 0), X = OV_M + (i % B) * 16, Y = OV_M + (i / B | 0) * 16;
    if (inOpenCave(x, y)) {                               // the cave you're in: its floor here, seen through the hill
      need();
      const z = openCave.get(x + "," + y), Yz = Y - shOf(z);
      if (!inOpenCave(x, y - 1) && (roofAt(x, y - 1) || Math.abs(topAt(x, y - 1) - z) > 1)) {   // the wall at its back, in the hill's own colours (none where it opens onto the ground: a way out)
        const bands = colsOf(hillSheet(Math.max(1, topAt(x, y)))).bands, h = Math.min(shOf(topAt(x, y) - z), 12);
        for (let j = 0; j < h; j++) { const col = bands[j === 0 ? 0 : j >= h - 2 ? 2 : 1]; g.fillStyle = `rgb(${col[0] * .8 | 0},${col[1] * .8 | 0},${col[2] * .8 | 0})`; g.fillRect(X, Yz - h + j, 16, 1); }
      }
      peekFloors = true; drawTile(x, y, {g, ox: X, oy: Yz}); peekFloors = false;
      caveEdge(g, x, y, z, X, Yz);
      for (let n = 1; n <= 3; n++) {                      // a way out to the north: the ground it opens onto is behind the hill;
        // shown too, as far as the hill hides it, right through the hill's border (one passage, out into the open)
        const ty = y - n, t = topAt(x, ty);
        if (roofAt(x, ty) || inOpenCave(x, ty) || Math.abs(t - z) > 1 || (topAt(x, y) - t) * RELIEF_STEP <= (n - 1) * 16) break;
        drawTile(x, ty, {g, ox: X, oy: Y - n * 16 - shOf(t)});
        [.34, .24, .15, .08].forEach((al, k) => {         // (shadowed along its sides like the cave)
          g.fillStyle = `rgba(${SHADE},${al})`;
          if (!inOpenCave(x - 1, y)) g.fillRect(X + k, Y - n * 16 - shOf(t), 1, 16);
          if (!inOpenCave(x + 1, y)) g.fillRect(X + 15 - k, Y - n * 16 - shOf(t), 1, 16);
        });
      }
      continue;
    }
    for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) if (shownVoids(x, y, dx, dy).length) { need(); drawFace(g, X, Y, x, y, dx, dy); }
  }
  return c;
}
// Called each frame after the ground: each block's caves, a picture a block (redrawn only when it changed)
function drawCaves(vis, sx, sy) {
  for (const b of vis) {
    if (!b.col || !b.relief) continue;
    const key = (b.ver || 0) + ":" + caveStamp;
    if (b.caveKey !== key) { b.caveKey = key; b.caveOv = buildCaveOverlay(b); }
    if (b.caveOv) ctx.drawImage(b.caveOv, sx(b.bx * B) - OV_M * zoom, sy(b.by * B) - OV_M * zoom, b.caveOv.width * zoom, b.caveOv.height * zoom);
  }
}
// Where you are, on screen: X, Y (the tile) and Z (the height you stand at)
let xyzText = "";
function showXYZ() {
  const t = myAt ? `X ${myAt.x}  Y ${myAt.y}  Z ${myAt.z}` : "";
  if (t !== xyzText) { xyzText = t; $("xyz").textContent = t; }
}
