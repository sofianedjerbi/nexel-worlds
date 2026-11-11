// Underground (layers.py): each level below the surface is a region far east of the one above. Down there your own
// level's caves are dark: you see a little way around you, around fires and torches, and where daylight falls down
// a hole. What's above shows through the rock (caveview.js). You drop through holes and jump up out of them.

const LAYER = 1000000, LAYER_B = LAYER / B;
const depthOf = (x) => Math.max(0, Math.floor((x + LAYER / 2) / LAYER));
const clamp01 = (v) => Math.max(0, Math.min(1, v)), smooth = (v) => { v = clamp01(v); return v * v * (3 - 2 * v); };
let caveDark = null, caveMask = null, lastDepth = null, darkAt = -1e9;

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
  if (lastDepth !== null && d !== lastDepth) { toast(d ? `Underground · depth ${d}` : "Back on the surface"); darkAt = now; }
  lastDepth = d;
  if (!d) return d;
  if (!caveDark) caveDark = document.createElement("canvas");
  if (caveDark.width !== W || caveDark.height !== H) { caveDark.width = W; caveDark.height = H; }
  const g = caveDark.getContext("2d");
  g.globalCompositeOperation = "source-over";
  g.clearRect(0, 0, W, H);
  g.fillStyle = `rgba(14,10,18,${Math.min(.75, .55 + d * .04)})`;   // the cave's own dark: darker deeper down
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
  for (const b of vis) b.comb.forEach((c, i) => {                                 // daylight falling down each hole
    const x = b.bx * B + i % B, y = b.by * B + (i / B | 0);
    if (combAt(x - LAYER, y) === "O") light(sx(x) + S / 2, sy(y) + S / 2, S * 2.4);
  });
  for (const f of fireAt) light(sx(f.x) + S / 2, sy(f.y) + S / 2, S * 4);
  if (!caveMask) caveMask = document.createElement("canvas");          // (only over this level's caves: all its blocks
  if (caveMask.width !== W || caveMask.height !== H) { caveMask.width = W; caveMask.height = H; }   //  as one mask)
  const m = caveMask.getContext("2d"); m.clearRect(0, 0, W, H); m.imageSmoothingEnabled = false;
  for (const b of vis) if (b.canvas) m.drawImage(b.canvas, sx(b.bx * B), sy(b.by * B), B * S, B * S);
  g.globalCompositeOperation = "destination-in"; g.drawImage(caveMask, 0, 0);
  ctx.globalAlpha = smooth((now - darkAt) / 400); ctx.drawImage(caveDark, 0, 0, W, H); ctx.globalAlpha = 1;
  return d;
}

// Your own walk onto a hole (you drop to the level below) or out of one (a jump up onto the level above): you're on
// the other level now, as the server will say a moment later; the view, already showing it, simply carries on there.
function levelStep(x, y, fx, fy) {
  if (combAt(x, y) === "O") { let s = LAYER; while (combAt(x + s, y) === "O" && s < 64 * LAYER) s += LAYER; return s; }
  if (fx !== undefined && jumpUp(fx, fy, x, y)) return -LAYER;
  return 0;
}
// Someone the server has just put on the level above or below at about where we have them: their walk carries on
// there, no snap. True if so.
function levelShift(p, x, y, mine) {
  const lv = Math.round((x - p.tx) / LAYER) * LAYER;
  if (!lv || Math.abs(x - lv - p.tx) + Math.abs(y - p.ty) > 2) return false;
  p.x += lv; p.tx += lv;
  if (mine) { cam.x += lv; camT.x += lv; }
  return true;
}
// Called as your walk glides: on reaching the middle of a tile, through a hole or up out of one
function throughMouth(p, dir) {
  const x = Math.round(p.x), y = Math.round(p.y);
  if (Math.abs(p.y - y) > .02 || Math.abs(p.x - x) > .02) return;
  const [dx, dy] = DIRV[dir], shift = levelStep(x, y, x - dx, y - dy);
  if (!shift || (shift < 0 && depthOf(x) === 0)) return;
  if (shift < 0 && combAt(x, y) !== null && plainWalk(x, y)) return;          // (a jump only where it's rock here)
  p.x += shift; p.tx = x + shift; p.ty = y; cam.x += shift; camT.x += shift;
  pred = {x: p.tx, y: p.ty, until: performance.now() + 1500};
}
