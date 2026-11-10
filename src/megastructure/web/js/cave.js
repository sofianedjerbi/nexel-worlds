// Underground (layers.py): each level below the surface is a region far east of the one above. Down there it's
// dark: you see a little way around you, around fires and torches, and where daylight falls down a ramp.
// The level below shows only through holes: down every mouth (layers.js), never under solid ground. Walking down
// one, what's under it is lit more and more (it's where you're going) and you change level on the slope, where both
// look the same; walking on into the cave, the land above fades away and the dark closes in. Coming up, backwards.

const LAYER = 1000000, LAYER_B = LAYER / B;
const depthOf = (x) => Math.max(0, Math.floor((x + LAYER / 2) / LAYER));
const clamp01 = (v) => Math.max(0, Math.min(1, v)), smooth = (v) => { v = clamp01(v); return v * v * (3 - 2 * v); };
let caveDark = null, lastDepth = null, thru = null;

// The cave mouth (its top tile) you're near and where along the way through it you are: a mouth down from this
// level (`down`; `cut`: how lit its room is, 1 from the mouth's top on) or a ramp up from it (`sky`: how much of
// the level above still shows around its room: 1 down to the ramp's foot, gone 2 tiles into the cave)
function mouthNear(p, d) {
  const rx = Math.round(p.x), ry = Math.round(p.y);
  for (let dy = -3; dy <= 3; dy++) for (let dx = -2; dx <= 2; dx++) {
    const x = rx + dx, y = ry + dy, c = combAt(x, y), down = c === "O";
    if (!(down || (c === "l" && d)) || combAt(x, y + 1) !== c || combAt(x, y - 1) === c) continue;
    if (down ? p.y > y + 1.01 : p.y < y - .01) continue;        // south of a mouth, or behind a ramp: not in it
    const k = smooth((2 - Math.abs(p.x - x)) / 1.3);             // fading out sideways, away from its lane
    if (k <= 0) continue;
    return down ? {x, y, down, cut: smooth((p.y - (y - 1.5)) / 1.5) * k, sky: 1}
      : {x, y, down, cut: 1, sky: (1 - smooth((p.y - (y + 1)) / 2)) * k};
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
// From below: the level above drawn over this one, all but the hole the ramp comes up through, `a` opaque
function drawAbove(m, a, sx, sy, S) {
  if (a <= 0.01) return;
  if (!thru) thru = document.createElement("canvas");
  if (thru.width !== W || thru.height !== H) { thru.width = W; thru.height = H; }
  const g = thru.getContext("2d");
  g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false;
  g.clearRect(0, 0, W, H);
  for (const b of otherBlocks(-LAYER_B, S)) g.drawImage(b.canvas, sx(b.bx * B + LAYER), sy(b.by * B), B * S, B * S);
  const px = (x) => Math.round(sx(x)), py = (y) => Math.round(sy(y));
  g.globalCompositeOperation = "destination-out";
  g.fillStyle = "#000"; g.beginPath();
  for (const k of mouthHole(m.x, m.y)) { const [x, y] = k.split(",").map(Number); g.rect(px(x), py(y), px(x + 1) - px(x), py(y + 1) - py(y)); }
  g.fill();
  ctx.globalAlpha = a; ctx.drawImage(thru, 0, 0); ctx.globalAlpha = 1;
}

function drawCave(vis, sx, sy, S, t, now) {
  const d = depthOf(cam.x), me_ = ents.get("agent" + myId);
  if (lastDepth !== null && d !== lastDepth) toast(d ? `Underground · depth ${d}` : "Back on the surface");
  lastDepth = d;
  // how dark it is here: 1 underground, 0 above; coming up a ramp to the surface, as much as the land has come back
  let dark = d ? 1 : 0;
  const m = me_ && mouthNear(me_, d);
  drawHoles(ctx, 0, sx, sy, S, m && m.down ? m : null);          // the levels below, down every mouth in view
  if (m && !m.down) { drawAbove(m, m.sky, sx, sy, S); if (d === 1) dark = 1 - m.sky; }
  if (me_) drawEntity(me_, sx, sy, S, t, now);                    // (you, over it)
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
