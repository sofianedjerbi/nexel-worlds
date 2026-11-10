// Layers: the level below shows through every hole, and only there: down a cave mouth you see what's under its two
// tiles, a shade darker, its top edge in shadow and sunk a little lower on the screen (in this 3/4 view, lower is
// further down); if a hole down there lines up, the level below that, darker and lower again; and so on, DEEP levels
// down. Solid ground is solid: nothing shows under it. Walking down a mouth, what's under it lights up and rises
// into place as you go.

const DEEP = 4, SHADE = .3, DROP = .3;               // a level down: this much darker, this many tiles lower
const layerCv = [], holeCv = [];

function layerCanvas(k, pool = layerCv) {
  if (!pool[k]) pool[k] = document.createElement("canvas");
  const c = pool[k];
  if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
  return c;
}
// The mouths (their top tiles) on the level k below this one, in view, in that level's own coordinates
function mouthsOn(k, S) {
  const L = k * LAYER, hw = W / S / 2 + 2, hh = H / S / 2 + 3, out = [];
  for (let y = Math.floor(cam.y - hh); y <= Math.ceil(cam.y + hh); y++)
    for (let x = Math.floor(cam.x - hw) + L; x <= Math.ceil(cam.x + hw) + L; x++)
      if (combAt(x, y) === "O" && combAt(x, y + 1) === "O" && combAt(x, y - 1) !== "O") out.push([x, y]);
  return out;
}
// Level k below this one as seen from here (k >= 1), with the levels under it down its own mouths
function renderLevel(k, sx, sy, S) {
  const c = layerCanvas(k), g = c.getContext("2d");
  g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false;
  g.clearRect(0, 0, W, H);
  for (const b of otherBlocks(k * LAYER_B, S)) g.drawImage(b.canvas, sx(b.bx * B - k * LAYER), sy(b.by * B), B * S, B * S);
  if (k < DEEP) drawHoles(g, k, sx, sy, S, null);
  return c;
}
// Onto g (level k below this one; 0: this one) the level under it, down each of its mouths. `near`: the mouth
// you're walking down, whose room is lit more the further in you are (as it will be when you're there).
function drawHoles(g, k, sx, sy, S, near) {
  const ms = mouthsOn(k, S);
  if (!ms.length) return;
  const below = renderLevel(k + 1, sx, sy, S), off = (k + 1) * LAYER;
  const px = (x) => Math.round(sx(x - off)), py = (y) => Math.round(sy(y));
  const rooms = ms.map(([x, y]) => {
    const mine = near && k === 0 && x === near.x && y === near.y, f = mine ? 1 - near.cut : 1;   // (the one you're in)
    const room = mouthHole(x + LAYER, y);                      // only the hole itself: never under solid ground
    return {room, shade: SHADE * f, drop: Math.round(DROP * S * f)};
  });
  // each hole: the level below sunk by its drop, cut to the hole (in this level's place)
  const hole = layerCanvas(k, holeCv), hg = hole.getContext("2d");
  hg.globalCompositeOperation = "source-over"; hg.clearRect(0, 0, W, H);
  const all = new Set(); for (const r of rooms) for (const t of r.room) all.add(t);
  const tiles = (set, f) => { for (const t of set) { const [x, y] = t.split(",").map(Number); f(x, y, px(x), px(x + 1), py(y), py(y + 1)); } };
  const shape = (c, set) => { c.beginPath(); tiles(set, (x, y, x0, x1, y0, y1) => c.rect(x0, y0, x1 - x0, y1 - y0)); };
  for (const r of rooms) {
    hg.save(); shape(hg, r.room); hg.clip(); hg.drawImage(below, 0, r.drop);
    if (r.shade > .01) { hg.fillStyle = `rgba(14,10,18,${r.shade})`; hg.fillRect(0, 0, W, H); }   // a shade darker
    tiles(r.room, (x, y, x0, x1, y0, y1) => {                // in shadow under its top edge and its sides
      const n = !r.room.has(x + "," + (y - 1)), w = !r.room.has(x - 1 + "," + y), e = !r.room.has(x + 1 + "," + y);
      if (n) { const gr = hg.createLinearGradient(0, y0, 0, y0 + S * .6); gr.addColorStop(0, "rgba(14,10,18,.5)"); gr.addColorStop(1, "rgba(14,10,18,0)"); hg.fillStyle = gr; hg.fillRect(x0, y0, x1 - x0, S * .6); }
      if (w) { const gr = hg.createLinearGradient(x0, 0, x0 + S * .3, 0); gr.addColorStop(0, "rgba(14,10,18,.3)"); gr.addColorStop(1, "rgba(14,10,18,0)"); hg.fillStyle = gr; hg.fillRect(x0, y0, S * .3, y1 - y0); }
      if (e) { const gr = hg.createLinearGradient(x1, 0, x1 - S * .3, 0); gr.addColorStop(0, "rgba(14,10,18,.3)"); gr.addColorStop(1, "rgba(14,10,18,0)"); hg.fillStyle = gr; hg.fillRect(x1 - S * .3, y0, S * .3, y1 - y0); }
    });
    hg.restore();
  }
  g.drawImage(hole, 0, 0);
  const lw = Math.max(2, Math.round(S / 16));                 // the cut's edge: one art pixel of the pack's ink
  g.fillStyle = "#4a3530";
  tiles(all, (x, y, x0, x1, y0, y1) => {
    if (!all.has(x + "," + (y - 1))) g.fillRect(x0, y0, x1 - x0, lw);
    if (!all.has(x + "," + (y + 1))) g.fillRect(x0, y1 - lw, x1 - x0, lw);
    if (!all.has(x - 1 + "," + y)) g.fillRect(x0, y0, lw, y1 - y0);
    if (!all.has(x + 1 + "," + y)) g.fillRect(x1 - lw, y0, lw, y1 - y0);
  });
}
