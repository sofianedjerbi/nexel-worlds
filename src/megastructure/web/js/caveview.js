// Underground, the world is layers seen from above: the levels over you are drawn first, the meadow then each level
// down to yours, a shade dimmer each, and your own level over them. The rock of a level is drawn only as the stone
// sheet's own edges round its caves (tiles.js), so through it you see what's above: the caves over you, the meadow
// and its holes. Only your own level's caves are dark (cave.js), lit by you and torches.

const ABOVE_DIM = .22;                     // each level up, this much dimmer (still daylight up there)

// A level `k` above this one (k >= 1): its ground, then its things in depth order
function drawLevelAbove(k, sx, sy, S, t) {
  const out = otherBlocks(-k * LAYER_B, S), list = [];
  if (k === depthOf(cam.x) && waterPatterns) {             // the surface: its sea under it, as up there
    ctx.save(); ctx.translate(sx(0), sy(0)); ctx.scale(zoom, zoom);
    ctx.fillStyle = waterPatterns[Math.floor(t * 3) % 4];
    ctx.fillRect(-sx(0) / zoom - 16, -sy(0) / zoom - 16, W / zoom + 32, H / zoom + 32);
    ctx.restore();
  }
  for (const b of out) {
    ctx.drawImage(b.canvas, sx(b.bx * B + k * LAYER), sy(b.by * B), B * S, B * S);
    for (const [i, c] of b.objs) {
      if (c === "*") continue;                             // (ore in the rock up there: not seen)
      const x = b.bx * B + i % B, y = b.by * B + (i / B | 0), spr = objectSprite(c, x, y, t);
      if (spr) list.push({y, x, spr});
    }
  }
  list.sort((a, b) => a.y - b.y || a.x - b.x);
  for (const o of list) {
    const [img, a, b2, w, h, dx, dy] = o.spr;
    ctx.drawImage(img, a, b2, w, h, Math.round(sx(o.x + k * LAYER) + dx * zoom), Math.round(sy(o.y, o.x) + dy * zoom), w * zoom, h * zoom);
  }
}

// Called before this level's ground is drawn: underground, every level above it, from the top down
function drawLevelsAbove(sx, sy, S, t) {
  const d = depthOf(cam.x);
  if (!d || CAVE_STYLE !== "xray") return;
  for (let k = d; k >= 1; k--) {
    drawLevelAbove(k, sx, sy, S, t);
    ctx.fillStyle = `rgba(28,22,34,${ABOVE_DIM})`; ctx.fillRect(0, 0, W, H);
  }
}

// Going down, the roof comes off: the ground you were standing on stays on screen for a moment over the cave, then
// lifts away and fades, like the roof of a house popping off as you walk in. Coming up, the cave's dark lifts the
// same way off the daylight.
const ROOF_MS = 700;
let roof = {d: null, at: -1e9, dir: 0};
function drawRoof(sx, sy, S, t, now) {
  const d = depthOf(cam.x);
  if (roof.d !== null && d !== roof.d) { roof.at = now; roof.dir = d > roof.d ? 1 : -1; }
  roof.d = d;
  const p = (now - roof.at) / ROOF_MS;
  if (p >= 1 || !roof.dir) return;
  const e = smooth(p), s = 1 + .14 * e, lift = H * .1 * e;
  ctx.save();
  ctx.globalAlpha = 1 - e;
  ctx.translate(W / 2, H / 2); ctx.scale(s, s); ctx.translate(-W / 2, -H / 2 - lift);
  if (roof.dir > 0) {                                      // the level above, lifting off
    ctx.fillStyle = "rgba(20,14,22,.25)"; ctx.fillRect(0, H, W, H * .2);   // (its shadow, under its edge)
    drawLevelAbove(1, sx, sy, S, t);
  } else {                                                 // the cave's dark, lifting off the day
    if (p > .6) { ctx.restore(); return; }                // (shorter: daylight comes back quickly)
    ctx.fillStyle = "rgb(30,24,32)"; ctx.globalAlpha = (1 - p / .6) * .45; ctx.fillRect(-W, -H, W * 3, H * 3);
  }
  ctx.restore();
}
