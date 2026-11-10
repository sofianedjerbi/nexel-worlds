// Underground (layers.py): each level below the surface is a region far east of the one above. Down there it's
// dark: you see a little way around you, around fires and torches, and where daylight falls down a ramp.
// Underground you see the part of the cave you're in, set in the level above (caveview.js); the level below shows
// only through holes (layers.js). Walking down a mouth, what's under it lights up and rises into place.

const LAYER = 1000000, LAYER_B = LAYER / B;
const depthOf = (x) => Math.max(0, Math.floor((x + LAYER / 2) / LAYER));
const clamp01 = (v) => Math.max(0, Math.min(1, v)), smooth = (v) => { v = clamp01(v); return v * v * (3 - 2 * v); };
let caveDark = null, lastDepth = null;

// The cave mouth down from here (its top tile) you're walking into, and how far: `cut` 0 a tile and a half before
// it .. 1 from its top on (how lit what's down it is)
function mouthNear(p) {
  if (!p) return null;
  const rx = Math.round(p.x), ry = Math.round(p.y);
  for (let dy = -2; dy <= 2; dy++) for (let dx = -1; dx <= 1; dx++) {
    const x = rx + dx, y = ry + dy;
    if (combAt(x, y) !== "O" || combAt(x, y + 1) !== "O" || combAt(x, y - 1) === "O" || p.y > y + 1.01) continue;
    const k = smooth((2 - Math.abs(p.x - x)) / 1.3);             // fading out sideways, away from its lane
    if (k > 0) return {x, y, cut: smooth((p.y - (y - 1.5)) / 1.5) * k};
  }
  return null;
}
// The hole a mouth makes: its two tiles, as "x,y" keys (x: on whichever level you want them)
const mouthHole = (x, y) => new Set([x + "," + y, x + "," + (y + 1)]);
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
function drawCave(vis, sx, sy, S, t, now) {
  const d = depthOf(cam.x);
  if (lastDepth !== null && d !== lastDepth) toast(d ? `Underground · depth ${d}` : "Back on the surface");
  lastDepth = d;
  const dark = d ? 1 : 0;
  if (dark <= 0.01) return d;
  if (!caveDark) caveDark = document.createElement("canvas");
  if (caveDark.width !== W || caveDark.height !== H) { caveDark.width = W; caveDark.height = H; }
  const g = caveDark.getContext("2d");
  g.globalCompositeOperation = "source-over";
  g.clearRect(0, 0, W, H);
  g.fillStyle = `rgba(14,10,18,${Math.min(.75, .55 + d * .04) * dark})`;   // the cave's own dark: darker deeper down
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
  if (region && regionCv) {                                        // (only over the part of the cave you're in)
    g.globalCompositeOperation = "destination-in"; g.imageSmoothingEnabled = false;
    g.drawImage(regionCv, sx(region.x0), sy(region.y0), (region.x1 - region.x0 + 1) * S, (region.y1 - region.y0 + 1) * S);
  }
  ctx.globalAlpha = smooth((now - revealAt) / REVEAL_MS); ctx.drawImage(caveDark, 0, 0, W, H); ctx.globalAlpha = 1;
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
