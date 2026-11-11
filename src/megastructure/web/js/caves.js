// Caves (client): a cave is drawn as the hill over it, like a house's roof; the one you walk into is opened. Its
// mouths show from outside. (Heights and roofs: tiles.js; the lifted ground: relief.js.)

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
// Walking into a cave (or out): that cave is shown through its roof (or not) at once. Nothing of the land is redrawn:
// the open cave is an overlay, a canvas a block, drawn once (below).
let caveStamp = 0;                        // (goes up when the open cave changes: the overlays are redrawn)
let myAt = null;                          // your tile and height: in a cave, or up on its roof (as Movement.landing)
function landZ(from, x, y) {             // as Movement.landing: the height a step from `from` {x, y, z} onto (x, y) lands at
  const f = floorAt(x, y), r = roofAt(x, y), inside = roofAt(from.x, from.y) > 0 && from.z === floorAt(from.x, from.y);
  const c = !r ? [f] : inside ? [f, f + r] : [f + r, f];
  return c.sort((p, q) => Math.abs(p - from.z) - Math.abs(q - from.z)).find((h) => Math.abs(h - from.z) <= 1);
}
function setCaveOpen() {
  const me = ents.get("agent" + myId);
  let into = null;                        // the cave tile you're stepping into: its cave opens as you set off, not half way
  if (me) {
    const x = Math.round(me.x), y = Math.round(me.y);        // (where you're seen, which runs ahead of the server's tile)
    if (!myAt || myAt.x !== x || myAt.y !== y) {
      let z = floorAt(x, y) + (meObs && meObs.self.atop ? roofAt(x, y) : 0);
      if (myAt && Math.abs(myAt.x - x) + Math.abs(myAt.y - y) === 1) { const pick = landZ(myAt, x, y); if (pick !== undefined) z = pick; }
      myAt = {x, y, z};
    }
    const ox = x + (me.x > x + .001 ? 1 : me.x < x - .001 ? -1 : 0), oy = y + (me.y > y + .001 ? 1 : me.y < y - .001 ? -1 : 0);
    if ((ox !== x) !== (oy !== y) && roofAt(ox, oy) > 0 && landZ(myAt, ox, oy) === floorAt(ox, oy)) into = {x: ox, y: oy};
  }
  showXYZ();
  const here = myAt && roofAt(myAt.x, myAt.y) > 0 && myAt.z === floorAt(myAt.x, myAt.y) ? myAt : into;
  if (!here === !caveOpen && (!here || openCave.has(here.x + "," + here.y))) return;
  caveOpen = !!here; openCave = here ? caveOf(here.x, here.y) : new Set(); caveStamp++;
}

// A block's caves as seen now, on one canvas in art px (with OV_M px round it), or null when there's nothing to see:
// the mouths of its closed caves, and the open cave's floor with its rock rim and the wall at its back.
// MOUTH (for now, while the look is being chosen): "A" the hole alone, "C" with a shadow on the ground before it,
// "D" with the ground before it going dark, "E" framed in stone.
let MOUTH = new URLSearchParams(location.search).get("mouth") || "A";
const OV_M = 96, HOLE = "#2a1d28", HOLE_DEEP = "#1d141c", HOLE_RIM = "rgba(48,30,34,.55)";
function buildCaveOverlay(b) {
  let c = null, g = null;
  const need = () => { if (!c) { c = document.createElement("canvas"); c.width = c.height = B * 16 + 2 * OV_M; g = c.getContext("2d"); } };
  for (let i = 0; i < B * B; i++) {
    if (!b.rf[i]) continue;
    const x = b.bx * B + i % B, y = b.by * B + (i / B | 0), f = floorAt(x, y), r = b.rf[i];
    const X = OV_M + (i % B) * 16, Y = OV_M + (i / B | 0) * 16 - shOf(f);       // the tile's corner at its floor's height
    if (inOpenCave(x, y)) {
      need();
      if (!inOpenCave(x, y - 1)) {                        // the wall at its back, in the hill's own colours
        const bands = colsOf(hillSheet(Math.max(1, f + r))).bands, h = Math.min(shOf(r), 12);
        for (let j = 0; j < h; j++) { const col = bands[j === 0 ? 0 : j >= h - 2 ? 2 : 1]; g.fillStyle = `rgb(${col[0] * .8 | 0},${col[1] * .8 | 0},${col[2] * .8 | 0})`; g.fillRect(X, Y - h + j, 16, 1); }
      }
      peekFloors = true; drawTile(x, y, {g, ox: X, oy: Y}); peekFloors = false;
      const [cx, cy] = blobCell(maskOf(x, y, (cc, gg, tx, ty) => inOpenCave(tx, ty) || (!roofAt(tx, ty) && Math.abs(floorAt(tx, ty) - f) <= 1)));
      g.drawImage(edgeSheet("hill3"), cx * 16, cy * 16, 16, 16, X, Y, 16, 16);     // its rock rim
      continue;
    }
    for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
      if (roofAt(x + dx, y + dy) || Math.abs(floorAt(x + dx, y + dy) - f) > 1) continue;
      need();
      // a mouth: a hole in whole art px. rows of [x0, x1) spans, top to bottom, from the tile's corner
      const side = LEDGE * (r - 1), up = shOf(r);
      const rows = (y0, spans, col) => { g.fillStyle = col; spans.forEach(([a, e], j) => g.fillRect(X + a, Y + y0 + j, e - a, 1)); };
      const grown = (spans, e) => [...Array(e).fill(spans[0]), ...spans, ...Array(e).fill(spans[spans.length - 1])].map(([a, q]) => [a - e, q + e]);
      const hole = (y0, spans) => {                       // its rim (a px round it; "E": a frame of stone), the hole, darker deeper in
        if (MOUTH === "E") { rows(y0 - 2, grown(spans, 2), "#7d7468"); rows(y0 - 1, grown(spans, 1), "#b8ae9e"); }
        else rows(y0 - 1, grown(spans, 1), HOLE_RIM);
        rows(y0, spans, HOLE);
        rows(y0 + 1, spans.slice(1, Math.ceil(spans.length / 2)).map(([a, e]) => [a + 1, e - 1]), HOLE_DEEP);
      };
      const n = (len, full, first = []) => [...first, ...Array(Math.max(0, len - first.length)).fill(full)];
      if (dy > 0) hole(16 - up + 2, n(up - 2, [2, 14], [[4, 12], [3, 13]]));                        // south: an arch in its face
      else if (dy < 0) hole(-up - 1, [[4, 12], [3, 13], [3, 13], [3, 13], [4, 12]]);                // north: on its rim
      else if (dx > 0) hole(3, [[15, 15 + side], ...n(10, [15, 16 + side]), [15, 15 + side]]);      // east: in its side
      else hole(3, [[1 - side, 1], ...n(10, [-side, 1]), [1 - side, 1]]);                           // west
      if (MOUTH !== "C" && MOUTH !== "D") continue;
      for (const [d, al] of MOUTH === "D" ? [[14, .28], [9, .24], [5, .24]] : [[9, .17], [5, .17]]) {   // the ground before it, in its shadow
        g.fillStyle = `rgba(30,20,28,${al})`;
        for (let k = 0; k < d; k++) {
          const half = Math.round((dx ? 6 : 7) * Math.sqrt(1 - ((k + .5) / d) ** 2));
          if (dy) g.fillRect(X + 8 - half, Y + (dy > 0 ? 16 + k : -up - 3 - k), 2 * half, 1);
          else g.fillRect(X + (dx > 0 ? 17 + side + k : -2 - side - k), Y + 9 - half, 1, 2 * half);
        }
      }
    }
  }
  return c;
}
// Called each frame after the ground: each block's caves, a picture a block (redrawn only when it changed)
function drawCaves(vis, sx, sy) {
  for (const b of vis) {
    if (!b.rf || !b.relief) continue;
    const key = (b.ver || 0) + ":" + caveStamp + ":" + MOUTH;
    if (b.caveKey !== key) { b.caveKey = key; b.caveOv = buildCaveOverlay(b); }
    if (b.caveOv) ctx.drawImage(b.caveOv, sx(b.bx * B) - OV_M * zoom, sy(b.by * B) - OV_M * zoom, b.caveOv.width * zoom, b.caveOv.height * zoom);
  }
}
// Where you are, on screen: X, Y (the tile) and Z (the height you stand at: in a cave its floor, on it its roof)
let xyzText = "";
function showXYZ() {
  const t = myAt ? `X ${myAt.x}  Y ${myAt.y}  Z ${myAt.z}` : "";
  if (t !== xyzText) { xyzText = t; $("xyz").textContent = t; }
}
