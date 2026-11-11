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
// where the empty cells of its hills show on their faces, and the open cave's floor with its rock rim and the wall
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
// One opening: `W` tiles wide from (x, y) along the face, its cells lo..hi empty. (X, Y): the first tile's corner at
// sea level, in art px. Always in the hill's wall: facing south a hole a layer high a cell, down the wall; facing east
// or west a hole in the side's wall (a layer of it a cell), open outward; where it opens at ground level (you can walk
// in) its shadow spills out. Facing north it is behind the hill: only that shadow, a square on the ground from under
// the hill's edge, fading.
function drawOpening(g, X, Y, x, y, dx, dy, W, lo, hi) {
  const top = topAt(x, y), front = topAt(x + dx, y + dy), walkIn = lo === front + 1, L = 16 * W, cols = colsOf(hillSheet(Math.max(1, top)));
  const rows = (y0, spans, col) => { g.fillStyle = col; spans.forEach(([a, e], k) => g.fillRect(X + a, Y + y0 + k, e - a, 1)); };
  const round = (n) => Array.from({length: n}, (_, k) => Math.max(0, 2 - Math.min(k, n - 1 - k)));   // 2, 1, 0... 0, 1, 2: a rounded end
  const spill = (wide, at) => {                           // its shadow out on the ground: rounded, in steps (at(k, half): a px line)
    for (const [d, al] of [[9, .17], [5, .17]]) {
      g.fillStyle = `rgba(${SHADE},${al})`;
      for (let k = 0; k < d; k++) at(k, Math.round(wide / 2 * Math.sqrt(1 - ((k + .5) / d) ** 2)));
    }
  };
  if (dy < 0) {                                           // north: its shadow only, cut to the edge tiles' own shape
    if (!walkIn) return;
    const low = cols.north - shOf(top) + 4;
    [.4, .28, .18, .09].forEach((al, k) => rows(low - 3 * (k + 1), [[1, L - 1], [1, L - 1], [1, L - 1]], `rgba(${SHADE},${al})`));
    for (let t = 0; t < W; t++) {
      const [cx, cy] = blobCell(maskOf(x + t, y, (cc, gg, tx, ty) => levelAt(tx, ty) >= top)), shape = cellAlpha(hillSheet(Math.max(1, top)), cx, cy);
      for (let j = 0; j < cols.north + 4; j++) for (let q = 0; q < 16; q++) if (shape[j * 16 + q]) g.clearRect(X + t * 16 + q, Y - shOf(top) + j, 1, 1);
    }
  } else if (dy > 0) {                                    // south: the wall's layers lo..hi (layer k: the RELIEF_STEP px under foot - shOf(k - 1))
    const foot = colsOf(hillSheet(Math.max(1, lo))).foot - shOf(lo - 1), h = shOf(hi - lo + 1) - 1, y0 = foot - h;
    const hole = Array.from({length: h}, (_, k) => [2 + Math.max(0, 2 - k), L - 2 - Math.max(0, 2 - k)]);   // (its top corners rounded)
    rows(y0 - 1, [hole[0], ...hole].map(([a, e]) => [a - 1, e + 1]), HOLE_RIM);
    rows(y0, hole, HOLE);
    rows(y0 + 1, hole.slice(1, Math.ceil(h / 2)).map(([a, e]) => [a + 1, e - 1]), HOLE_DEEP);
    if (walkIn) spill(L - 2, (k, half) => g.fillRect(X + L / 2 - half, Y + foot + k, 2 * half, 1));
  } else {                                                // east, west: the side wall's layers lo..hi (LEDGE px each, the lowest outermost)
    // (worked out for the west side, mirrored for the east) the side's wall runs from its foot in to the top's edge
    const m = ([a, e]) => (dx > 0 ? [16 - e, 16 - a] : [a, e]), Yg = -shOf(lo - 1);
    const out = cols.inset - LEDGE * (top - lo), w = LEDGE * (hi - lo + 1), hole = round(L - 4).map((q) => [out, out + Math.max(1, w - q)]);
    rows(Yg + 2, [m(hole[0])], HOLE_RIM); rows(Yg + L - 1, [m(hole[0])], HOLE_RIM);
    rows(Yg + 3, hole.map(m), HOLE);
    rows(Yg + 5, hole.slice(2, -2).map(([a, e]) => m([a + Math.ceil(w / 2), e])), HOLE_DEEP);
    if (walkIn) spill(L - 4, (k, half) => g.fillRect(X + (dx > 0 ? 16 - out + k : out - 1 - k), Y + Yg + 1 + L / 2 - half, 1, 2 * half));
  }
}
// The edge of the open cave's edge tiles (while the look is being chosen: CAVE_EDGE). "A": the stone sheet's rim, the
// hill's grass showing outside it; "B": the same rim, dark rock outside it; "C": the floor right to the tile's edge,
// walls on it (thin at the sides, a lip in front); "D": the floor to the edge, a shadow along it.
let CAVE_EDGE = "A";
const ROCK = "#4b434b", ROCK_LIT = "#8d8690", ROCK_DARK = "#2e282e";
function caveEdge(g, x, y, z, X, Y) {
  const inCave = (tx, ty) => inOpenCave(tx, ty) || (!roofAt(tx, ty) && Math.abs(topAt(tx, ty) - z) <= 1);
  const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, tx, ty) => inCave(tx, ty)));
  if (CAVE_EDGE === "A") return g.drawImage(edgeSheet("hill3"), cx * 16, cy * 16, 16, 16, X, Y, 16, 16);
  if (CAVE_EDGE === "B") {                                // the tile's shape (the soil sheet's own): rock outside it, the rim on it
    const shape = cellAlpha(IMG.soil, cx, cy);
    g.fillStyle = ROCK;
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) if (!shape[j * 16 + i]) g.fillRect(X + i, Y + j, 1, 1);
    return g.drawImage(edgeSheet("hill3"), cx * 16, cy * 16, 16, 16, X, Y, 16, 16);
  }
  const W = !inCave(x - 1, y), E = !inCave(x + 1, y), N = !inCave(x, y - 1), S = !inCave(x, y + 1);
  if (CAVE_EDGE === "C") {
    if (W) { g.fillStyle = ROCK; g.fillRect(X, Y, 3, 16); g.fillStyle = ROCK_DARK; g.fillRect(X + 3, Y, 1, 16); }
    if (E) { g.fillStyle = ROCK; g.fillRect(X + 13, Y, 3, 16); g.fillStyle = ROCK_DARK; g.fillRect(X + 12, Y, 1, 16); }
    if (S) { g.fillStyle = ROCK; g.fillRect(X, Y + 13, 16, 3); g.fillStyle = ROCK_LIT; g.fillRect(X, Y + 13, 16, 1); }
    if (N) { g.fillStyle = ROCK_DARK; g.fillRect(X, Y, 16, 1); }
  } else if (CAVE_EDGE === "D") {
    [.34, .24, .15, .08].forEach((al, k) => {
      g.fillStyle = `rgba(${SHADE},${al})`;
      if (W) g.fillRect(X + k, Y, 1, 16); if (E) g.fillRect(X + 15 - k, Y, 1, 16);
      if (N) g.fillRect(X, Y + k, 16, 1); if (S) g.fillRect(X, Y + 15 - k, 16, 1);
    });
  }
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
      for (let n = 1; n <= 3; n++) {                      // a way out to the north: the ground it opens onto is behind
        const ty = y - n, t = topAt(x, ty);              //  the hill; shown too, as far as the hill hides it
        if (roofAt(x, ty) || inOpenCave(x, ty) || Math.abs(t - z) > 1 || (topAt(x, y) - t) * RELIEF_STEP <= (n - 1) * 16) break;
        drawTile(x, ty, {g, ox: X, oy: Y - n * 16 - shOf(t)});
      }
      continue;
    }
    for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
      const px = dy ? 1 : 0, py = dy ? 0 : 1, top = topAt(x, y), front = topAt(x + dx, y + dy);
      for (const [lo, hi] of shownVoids(x, y, dx, dy)) {  // an opening: the same empty cells side by side along the face
        const same = (u, v) => topAt(u, v) === top && topAt(u + dx, v + dy) === front && shownVoids(u, v, dx, dy).some((r) => r[0] === lo && r[1] === hi);
        let back = 0; while (back < 60 && same(x - (back + 1) * px, y - (back + 1) * py)) back++;
        if (back % 6) continue;                           // (drawn from its first tile; a very long one, in lengths of 6)
        let W = 1; while (W < 6 && same(x + W * px, y + W * py)) W++;
        need(); drawOpening(g, X, Y, x, y, dx, dy, W, lo, hi);
      }
    }
  }
  return c;
}
// Called each frame after the ground: each block's caves, a picture a block (redrawn only when it changed)
function drawCaves(vis, sx, sy) {
  for (const b of vis) {
    if (!b.col || !b.relief) continue;
    const key = (b.ver || 0) + ":" + caveStamp + CAVE_EDGE;
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
