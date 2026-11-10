// Underground (layers.py): each level below the surface is a region far east of the one above. Down there it's
// dark: you see a little way around you, around fires and torches, and where daylight falls down a ramp.
// Through a cave mouth it's gradual, in three steps along about five tiles of walking: approaching, the cave starts
// to show through the ground around the mouth and the light dims; in the mouth itself the world narrows to a pool
// of light where both levels blend (the step between, like a short tunnel); past it, the pool opens out onto the
// other level. Every step depends only on where you stand, the same seen from either level, so the move to the
// other level (in the narrow step, where both look alike) can't be seen.

const LAYER = 1000000, LAYER_B = LAYER / B;
const POOL_IN = 1.9, POOL_OUT = 3.4, FEATHER = 1.6;     // the tunnel's pool of light and the reveal's soft edge (tiles)
const depthOf = (x) => Math.max(0, Math.floor((x + LAYER / 2) / LAYER));
const clamp01 = (v) => Math.max(0, Math.min(1, v)), smooth = (v) => { v = clamp01(v); return v * v * (3 - 2 * v); };
let caveDark = null, lastDepth = null, thru = null;

// The cave mouth (its top tile) you're near, on either level, and where along the way through it you are:
// `under` 0 above it .. 1 below it (the cave's share of what you see), `tunnel` 0..1 (1 in the mouth itself)
function mouthNear(p, d) {
  const want = d ? "l" : "O", rx = Math.round(p.x), ry = Math.round(p.y);
  for (let dy = -3; dy <= 3; dy++) for (let dx = -2; dx <= 2; dx++) {
    const x = rx + dx, y = ry + dy;
    if (combAt(x, y) !== want || combAt(x, y + 1) !== want || combAt(x, y - 1) === want) continue;
    if (!d && p.y > y + 1.01) return null;                       // south of a mouth, on the surface: not in it
    if (d && p.y < y - .01) return null;                         // behind a ramp, below: not on it
    const k = smooth((2 - Math.abs(p.x - x)) / 1.3);             // fading out sideways, away from its lane
    if (k <= 0) return null;
    const under = smooth((p.y - (y - 1.5)) / 3.5);                // from 1.5 tiles before its top to 1 tile past its foot
    const tunnel = smooth(Math.min((p.y - (y - 1.5)) / 1.5, (y + 2.5 - p.y) / 1.5));
    return {x, y, k, under: d ? 1 - (1 - under) * k : under * k, tunnel: tunnel * k};
  }
  return null;
}
// The blocks of the other level under (or over) the mouth: asked for, and drawn once they come
function otherBlocks(m, shift) {
  const out = [], now = performance.now();
  for (let by = Math.floor((m.y - 7) / B); by <= Math.floor((m.y + 7) / B); by++)
    for (let bx = Math.floor((m.x - 7) / B) + shift; bx <= Math.floor((m.x + 7) / B) + shift; bx++) {
      const k = bkey(bx, by), b = blocks.get(k);
      if (!b && !(requested.get(k) > now - 3000)) { requested.set(k, now); sendSpec({op: "region", x: bx * B, y: by * B, w: B, h: B}); }
      if (b && !b.drawn) renderBlock(b);
      if (b && b.canvas) out.push(b);
    }
  return out;
}
// The middle of the mouth, on screen: where the reveal and the tunnel's pool of light are centred
const mouthCentre = (m, sx, sy, S) => [sx(m.x) + S / 2, sy(m.y + .5) + S / 2];
// The other level, seen through the mouth: drawn over this one around the mouth, `a` opaque, its edge soft
function drawThrough(m, shift, a, sx, sy, S) {
  if (a <= 0.01) return;
  if (!thru) thru = document.createElement("canvas");
  if (thru.width !== W || thru.height !== H) { thru.width = W; thru.height = H; }
  const g = thru.getContext("2d"), [cx, cy] = mouthCentre(m, sx, sy, S);
  g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false;
  g.clearRect(0, 0, W, H);
  for (const b of otherBlocks(m, shift)) g.drawImage(b.canvas, sx(b.bx * B - shift * B), sy(b.by * B), B * S, B * S);
  g.globalCompositeOperation = "destination-in";             // keep a disc, full out to the pool's edge, then fading
  const gr = g.createRadialGradient(cx, cy, 0, cx, cy, (POOL_OUT + FEATHER) * S);
  gr.addColorStop(0, "#000"); gr.addColorStop(POOL_OUT / (POOL_OUT + FEATHER), "#000"); gr.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = gr; g.fillRect(0, 0, W, H);
  ctx.globalAlpha = a; ctx.drawImage(thru, 0, 0); ctx.globalAlpha = 1;
}
// The tunnel: dark closing in around the mouth until only a pool of light is left (`a` 1), then opening again
function drawTunnel(g, m, a, sx, sy, S) {
  if (a <= 0.01) return;
  const [cx, cy] = mouthCentre(m, sx, sy, S);
  const gr = g.createRadialGradient(cx, cy, POOL_IN * S, cx, cy, POOL_OUT * S);   // (beyond it, its last colour)
  gr.addColorStop(0, "rgba(10,7,14,0)"); gr.addColorStop(.6, `rgba(10,7,14,${.6 * a})`); gr.addColorStop(1, `rgba(10,7,14,${a})`);
  g.globalCompositeOperation = "source-over";
  g.fillStyle = gr; g.fillRect(0, 0, W, H);
}

function drawCave(vis, sx, sy, S, t, now) {
  const d = depthOf(cam.x), me_ = ents.get("agent" + myId);
  if (lastDepth !== null && d !== lastDepth) toast(d ? `Underground · depth ${d}` : "Back on the surface");
  lastDepth = d;
  // how dark it is here: 1 underground, 0 above; partway near a cave mouth
  let dark = d ? 1 : 0, tunnel = 0;
  const m = me_ && mouthNear(me_, d);
  if (m) {
    if (!d) drawThrough(m, LAYER_B, m.under, sx, sy, S);          // above: the cave shows through
    else drawThrough(m, -LAYER_B, 1 - m.under, sx, sy, S);        // below: the land outside does
    drawEntity(me_, sx, sy, S, t, now);                           // (you, over it)
    dark = m.under; tunnel = m.tunnel;
  }
  if (dark <= 0.01 && tunnel <= 0.01) return d;
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
  if (m) drawTunnel(g, m, tunnel, sx, sy, S);
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
