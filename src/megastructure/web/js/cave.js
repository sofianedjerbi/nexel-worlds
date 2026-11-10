// Underground (layers.py): each level below the surface is a region far east of the one above. Down there it's
// dark: you see a little way around you, around fires and torches, and where daylight falls down a ramp.
// Through a cave mouth it's gradual, like walking into a house, then on into the dark:
//   1. approaching the mouth, the cave room under it appears, cut out of the land like a house seen from inside
//      (the room and its rock walls), the land around it still in daylight;
//   2. on the mouth's slope you see both at once: the room below, the land around it (here you change level);
//   3. walking on into the cave, the land around fades away and the dark closes in: the real underground.
// Every step depends only on where you stand, and step 2 looks the same from either level, so the change of level
// can't be seen. Coming up, the same backwards.

const LAYER = 1000000, LAYER_B = LAYER / B;
const depthOf = (x) => Math.max(0, Math.floor((x + LAYER / 2) / LAYER));
const clamp01 = (v) => Math.max(0, Math.min(1, v)), smooth = (v) => { v = clamp01(v); return v * v * (3 - 2 * v); };
let caveDark = null, lastDepth = null, thru = null;

// The cave mouth (its top tile) you're near, on either level, and where along the way through it you are:
// `cut` how much the room below shows through the land (1 from the mouth's top on), `sky` how much of the land
// around is still there (1 down to the mouth's foot, gone 2 tiles into the cave)
function mouthNear(p, d) {
  const want = d ? "l" : "O", rx = Math.round(p.x), ry = Math.round(p.y);
  for (let dy = -3; dy <= 3; dy++) for (let dx = -2; dx <= 2; dx++) {
    const x = rx + dx, y = ry + dy;
    if (combAt(x, y) !== want || combAt(x, y + 1) !== want || combAt(x, y - 1) === want) continue;
    if (!d && p.y > y + 1.01) return null;                       // south of a mouth, on the surface: not in it
    if (d && p.y < y - .01) return null;                         // behind a ramp, below: not on it
    const k = smooth((2 - Math.abs(p.x - x)) / 1.3);             // fading out sideways, away from its lane
    if (k <= 0) return null;
    const cut = smooth((p.y - (y - 1.5)) / 1.5), sky = 1 - smooth((p.y - (y + 1)) / 2);
    return {x, y, cut: d ? 1 : cut * k, sky: d ? sky * k : 1};
  }
  return null;
}
// The cave room under a mouth: its open tiles joined to the ramp (a few tiles around), and the rock walls around
// them, as "x,y" keys on the cave's level (cx: the cave level's x of the mouth)
function caveRoom(cx, y) {
  const open = new Set(), q = [[cx, y], [cx, y + 1]], room = new Set();
  const isOpen = (c) => c !== null && c !== "R" && c !== "*";
  while (q.length && open.size < 70) {
    const [x, yy] = q.shift(), k = x + "," + yy;
    if (open.has(k) || Math.abs(x - cx) > 5 || yy < y - 1 || yy > y + 6 || !isOpen(combAt(x, yy))) continue;
    open.add(k);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) q.push([x + dx, yy + dy]);
  }
  for (const k of open) {
    const [x, yy] = k.split(",").map(Number);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) room.add(x + dx + "," + (yy + dy));
  }
  return room;
}
// The other level's blocks over the whole view: asked for, and drawn once they come
function otherBlocks(shift, S) {
  const out = [], now = performance.now(), hw = W / S / 2 + 2, hh = H / S / 2 + 3;
  for (let by = Math.floor((cam.y - hh) / B); by <= Math.floor((cam.y + hh) / B); by++)
    for (let bx = Math.floor((cam.x - hw) / B) + shift; bx <= Math.floor((cam.x + hw) / B) + shift; bx++) {
      const k = bkey(bx, by), b = blocks.get(k);
      if (!b && !(requested.get(k) > now - 3000)) { requested.set(k, now); sendSpec({op: "region", x: bx * B, y: by * B, w: B, h: B}); }
      if (b && !b.drawn) renderBlock(b);
      if (b && b.canvas) out.push(b);
    }
  return out;
}
// The other level drawn over this one, `a` opaque: inside the cave room (from above) or outside it (from below)
function drawThrough(m, shift, a, inside, sx, sy, S) {
  if (a <= 0.01) return;
  if (!thru) thru = document.createElement("canvas");
  if (thru.width !== W || thru.height !== H) { thru.width = W; thru.height = H; }
  const g = thru.getContext("2d");
  g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false;
  g.clearRect(0, 0, W, H);
  for (const b of otherBlocks(shift, S)) g.drawImage(b.canvas, sx(b.bx * B - shift * B), sy(b.by * B), B * S, B * S);
  const cx = shift > 0 ? m.x + LAYER : m.x, off = shift > 0 ? LAYER : 0;    // the room is found on the cave's level
  g.globalCompositeOperation = inside ? "destination-in" : "destination-out";
  const room = caveRoom(cx, m.y), px = (x) => Math.round(sx(x - off)), py = (y) => Math.round(sy(y));
  g.fillStyle = "#000"; g.beginPath();
  for (const k of room) { const [x, y] = k.split(",").map(Number); g.rect(px(x), py(y), px(x + 1) - px(x), py(y + 1) - py(y)); }
  g.fill();
  ctx.globalAlpha = a; ctx.drawImage(thru, 0, 0);
  // the cut's edge: a one-art-pixel outline in the pack's ink, just inside the room, like the edge of a wall
  const lw = Math.max(2, Math.round(S / 16));
  ctx.fillStyle = "#4a3530";
  for (const k of room) {
    const [x, y] = k.split(",").map(Number), x0 = px(x), x1 = px(x + 1), y0 = py(y), y1 = py(y + 1);
    if (!room.has(x + "," + (y - 1))) ctx.fillRect(x0, y0, x1 - x0, lw);
    if (!room.has(x + "," + (y + 1))) ctx.fillRect(x0, y1 - lw, x1 - x0, lw);
    if (!room.has(x - 1 + "," + y)) ctx.fillRect(x0, y0, lw, y1 - y0);
    if (!room.has(x + 1 + "," + y)) ctx.fillRect(x1 - lw, y0, lw, y1 - y0);
  }
  ctx.globalAlpha = 1;
}

function drawCave(vis, sx, sy, S, t, now) {
  const d = depthOf(cam.x), me_ = ents.get("agent" + myId);
  if (lastDepth !== null && d !== lastDepth) toast(d ? `Underground · depth ${d}` : "Back on the surface");
  lastDepth = d;
  // how dark it is here: 1 underground, 0 above; near a cave mouth, as much as the land outside has faded
  let dark = d ? 1 : 0;
  const m = me_ && mouthNear(me_, d);
  if (m) {
    if (!d) drawThrough(m, LAYER_B, m.cut, true, sx, sy, S);       // above: the room below, cut out of the land
    else drawThrough(m, -LAYER_B, m.sky, false, sx, sy, S);       // below: the land around the room
    drawEntity(me_, sx, sy, S, t, now);                           // (you, over it)
    if (d) dark = 1 - m.sky;
  }
  if (dark <= 0.01) return d;
  if (!caveDark) caveDark = document.createElement("canvas");
  if (caveDark.width !== W || caveDark.height !== H) { caveDark.width = W; caveDark.height = H; }
  const g = caveDark.getContext("2d");
  g.globalCompositeOperation = "source-over";
  g.clearRect(0, 0, W, H);
  g.fillStyle = `rgba(14,10,18,${Math.min(.94, .82 + Math.max(1, d) * .02) * dark})`;   // darker deeper down
  g.fillRect(0, 0, W, H);
  g.globalCompositeOperation = "destination-out";
  const light = (x, y, r) => {
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, "rgba(0,0,0,1)"); gr.addColorStop(.55, "rgba(0,0,0,.75)"); gr.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2);
  };
  for (const p of ents.values()) if (p.e && p.e.kind === "agent") light(sx(p.x) + S / 2, sy(p.y) + S / 2, S * 4.5);
  for (const b of vis) for (const [i, c] of b.objs) {
    const x = b.bx * B + i % B, y = b.by * B + (i / B | 0);
    if (c === "^" || c === "x") light(sx(x) + S / 2, sy(y) + S / 2, S * (5 + .3 * Math.sin(t * 13 + x)));
  }
  for (const b of vis) b.comb.forEach((c, i) => {                                 // daylight falling down each ramp
    if (c === "l") light(sx(b.bx * B + i % B) + S / 2, sy(b.by * B + (i / B | 0)) + S / 2, S * 2.2);
  });
  for (const f of fireAt) light(sx(f.x) + S / 2, sy(f.y) + S / 2, S * 4);
  ctx.drawImage(caveDark, 0, 0, W, H);
  return d;
}

// Your own walk onto a mouth's deep end (going down) or a ramp's top (coming up): you're on the other level now, as
// the server will say a moment later; the view, already showing it, simply carries on there.
function mouthShift(x, y, dir) {
  if (dir === "S" && combAt(x, y) === "O" && combAt(x, y - 1) === "O") return LAYER;
  if (dir === "N" && depthOf(x) && combAt(x, y) === "l" && combAt(x, y + 1) === "l") return -LAYER;
  return 0;
}
// Someone the server has just put on the level above or below (through a cave mouth) at about where we have them:
// their walk carries on there, no snap. True if so.
function levelShift(p, x, y, mine) {
  const lv = Math.round((x - p.tx) / LAYER) * LAYER;
  if (!lv || Math.abs(x - lv - p.tx) + Math.abs(y - p.ty) > 2) return false;
  p.x += lv; p.tx += lv;
  if (mine) { cam.x += lv; camT.x += lv; }
  return true;
}
function throughMouth(p, dir, x = Math.round(p.x), y = Math.round(p.y)) {
  if (Math.abs(p.y - y) > .02 && x === Math.round(p.x)) return;
  const shift = mouthShift(x, y, dir);
  if (!shift) return;
  p.x += shift; p.tx = x + shift; p.ty = y; cam.x += shift; camT.x += shift;
  pred = {x: p.tx, y: p.ty, until: performance.now() + 1500};
}
