// Underground, the world is layers seen from above: the levels over you are drawn first, the meadow then each level
// down to yours, a shade dimmer each, and your own level over them. The rock of a level is drawn only as the stone
// sheet's own edges round its caves (tiles.js), so through it you see what's above: the caves over you, the meadow
// and its holes. Only your own level's caves are dark (cave.js), lit by you and torches.

const ABOVE_DIM = .12, ABOVE_VEIL = .6;    // each level up this much dimmer; then all of it veiled, faded: it's over you

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
    ctx.drawImage(img, a, b2, w, h, Math.round(sx(o.x + k * LAYER) + dx * zoom), Math.round(sy(o.y) + dy * zoom), w * zoom, h * zoom);
  }
}

// Called before this level's ground is drawn: underground, every level above it, from the top down
function drawLevelsAbove(sx, sy, S, t) {
  const d = depthOf(cam.x);
  if (!d) return;
  ctx.filter = "saturate(.35)";                            // (faded: what's above is not where you are)
  for (let k = d; k >= 1; k--) {
    drawLevelAbove(k, sx, sy, S, t);
    ctx.fillStyle = `rgba(28,22,34,${ABOVE_DIM})`; ctx.fillRect(0, 0, W, H);
  }
  ctx.filter = "none";
  ctx.fillStyle = `rgba(22,18,30,${ABOVE_VEIL})`; ctx.fillRect(0, 0, W, H);
}
