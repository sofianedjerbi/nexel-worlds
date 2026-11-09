// Underground (layers.py): each level below the surface is a region far east of the one above. Down there it's
// dark: you see a little way around you, around fires and torches, and where daylight falls down a ramp.
// Through a cave mouth it's gradual, like walking into a house: going down the slope, the ground around the mouth
// gives way to the cave under it (house-sized, around the mouth) and the dark closes in; coming up, the daylight
// and the land outside come back. The move to the other level happens at the bottom, when the view already shows it.

const LAYER = 1000000, LAYER_B = LAYER / B, REVEAL_R = 4.5;
const depthOf = (x) => Math.max(0, Math.floor((x + LAYER / 2) / LAYER));
let caveDark = null, lastDepth = null;

// The cave mouth (its top tile, A) you're in or next to, and how far down it you are: 0 above it, 1 at its foot
function mouthNear(p, d) {
  const want = d ? "l" : "O", rx = Math.round(p.x), ry = Math.round(p.y);
  for (let dy = -2; dy <= 2; dy++) for (let dx = -1; dx <= 1; dx++) {
    const x = rx + dx, y = ry + dy;
    if (combAt(x, y) === want && combAt(x, y + 1) === want) {
      if (Math.abs(p.x - x) > 1.2) return null;
      return {x, y, t: Math.max(0, Math.min(1, (p.y - (y - 1)) / 2))};
    }
  }
  return null;
}
// The blocks of the other level under (or over) the mouth: asked for, and drawn once they come
function otherBlocks(m, shift) {
  const out = [], now = performance.now();
  for (let by = Math.floor((m.y - 6) / B); by <= Math.floor((m.y + 6) / B); by++)
    for (let bx = Math.floor((m.x - 6) / B) + shift; bx <= Math.floor((m.x + 6) / B) + shift; bx++) {
      const k = bkey(bx, by), b = blocks.get(k);
      if (!b && !(requested.get(k) > now - 3000)) { requested.set(k, now); sendSpec({op: "region", x: bx * B, y: by * B, w: B, h: B}); }
      if (b && !b.drawn) renderBlock(b);
      if (b && b.canvas) out.push(b);
    }
  return out;
}
// The other level, seen through the mouth: drawn over this one, around the mouth, `a` opaque
function drawThrough(m, shift, a, sx, sy, S) {
  if (a <= 0.01) return;
  const cx = sx(m.x) + S / 2, cy = sy(m.y + 1) + S / 2;
  ctx.save();
  ctx.beginPath(); ctx.arc(cx, cy, REVEAL_R * S, 0, 7); ctx.clip();
  ctx.globalAlpha = a;
  for (const b of otherBlocks(m, shift)) ctx.drawImage(b.canvas, sx(b.bx * B - shift * B), sy(b.by * B), B * S, B * S);
  ctx.globalAlpha = 1;
  ctx.restore();
}

function drawCave(vis, sx, sy, S, t, now) {
  const d = depthOf(cam.x), me_ = ents.get("agent" + myId);
  if (lastDepth !== null && d !== lastDepth) toast(d ? `Underground · depth ${d}` : "Back on the surface");
  lastDepth = d;
  // how dark it is here: 1 underground, 0 above; partway in a cave mouth
  let dark = d ? 1 : 0;
  const m = me_ && mouthNear(me_, d);
  if (m) {
    if (!d) { drawThrough(m, LAYER_B, m.t, sx, sy, S); dark = m.t; }          // going down: the cave appears
    else { drawThrough(m, -LAYER_B, 1 - m.t, sx, sy, S); dark = m.t; }        // coming up: the land outside does
    if (me_) drawEntity(me_, sx, sy, S, t, now);                               // (you, over it)
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
function throughMouth(p, dir, x = Math.round(p.x), y = Math.round(p.y)) {
  if (Math.abs(p.y - y) > .02 && x === Math.round(p.x)) return;
  const shift = mouthShift(x, y, dir);
  if (!shift) return;
  p.x += shift; p.tx = x + shift; p.ty = y; cam.x += shift; camT.x += shift;
  pred = {x: p.tx, y: p.ty, until: performance.now() + 1500};
}
