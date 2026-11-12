// Water: a see-through layer over a bottom that has depth (tiles.py DEPTH: one to four layers under the surface).
// Under everything else in a block (land is drawn over it), in three parts:
//   the bottom   sand, darker and bluer the deeper it lies, with a shaded step wherever it drops a layer
//   the water    a tint that thickens with depth, blended smoothly from tile to tile (no hard squares)
//   the light    two nets of caustics drifting across each other on the bottom, the game's own ripples on the
//                surface, and a line of foam that breathes along every shore
// Nothing flows: the water is where the world says it is. The static parts are kept per block and redone when it changes.

const WATER = {
  sand: ["#e6d5a3", "#e6d5a3", "#cdbb8c", "#a99c7c", "#8a8571"],                         // the bottom, by depth (0: under a shore's edge)
  tint: [[122, 212, 204, .38], [122, 212, 204, .4], [70, 176, 200, .6], [44, 128, 186, .76], [24, 80, 148, .88]],
  step: "rgba(52, 44, 60, .3)", caustics: [.17, .1], ripples: .28, foam: "#ffffff",
};
const depthAt = (x, y) => DEPTH_OF[gndAt(x, y)] || 0;
let causticPat = null;
function causticPattern() {                        // a net of light, tileable: lines where three waves cancel
  const n = 64, c = document.createElement("canvas"); c.width = c.height = n;
  const g = c.getContext("2d"), img = g.createImageData(n, n), k = 2 * Math.PI / n;
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const v = Math.sin(k * (2 * x + 3 * Math.sin(k * 2 * y))) + Math.sin(k * (3 * y + 2 * Math.sin(k * 3 * x))) + Math.sin(k * (x + y) * 2);
    const a = Math.max(0, 1 - Math.abs(v) / .3);
    img.data.set([255, 255, 255, Math.round(255 * a * a)], (y * n + x) * 4);
  }
  g.putImageData(img, 0, 0);
  return ctx.createPattern(c, "repeat");
}
function waterLayer(b) {
  if (b.water && b.water.ver === b.ver) return b.water;
  const n = B * 16, x0 = b.bx * B, y0 = b.by * B, foam = [];
  const c = (b.water && b.water.canvas) || document.createElement("canvas");
  c.width = c.height = n;
  const g = c.getContext("2d");
  let any = false;
  const under = (x, y) => {                        // the depth drawn at a tile: a land tile by the water has shallows under its edge
    const d = depthAt(x, y);
    if (d) return d;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (depthAt(x + dx, y + dy)) return -1;
    return 0;
  };
  for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) {
    const x = x0 + lx, y = y0 + ly, u = under(x, y), d = Math.abs(u), ox = lx * 16, oy = ly * 16;
    if (!u) continue;
    any = true;
    g.fillStyle = WATER.sand[u < 0 ? 0 : d];
    g.fillRect(ox, oy, 16, 16);
    for (let k = 0; k < 6; k++) {                  // grains and small stones
      g.fillStyle = hash(x, y, 60 + k) < .5 ? "rgba(255,255,255,.22)" : "rgba(70,60,60,.2)";
      g.fillRect(ox + Math.floor(hash(x, y, 70 + k) * 15), oy + Math.floor(hash(x, y, 80 + k) * 15), hash(x, y, 90 + k) < .3 ? 2 : 1, 1);
    }
    if (u > 1 && hash(x, y, 55) < .07) {           // a tuft of weed on the deeper bottom
      g.fillStyle = "rgba(58,120,96,.75)";
      for (const [wx, wy, h] of [[6, 9, 4], [8, 7, 6], [10, 10, 3]]) g.fillRect(ox + wx, oy + wy, 1, h);
    }
    if (u < 0) continue;
    const up = (dx, dy) => { const o = under(x + dx, y + dy); return o && Math.abs(o) < d; };      // a shallower neighbour: a step down to here
    g.fillStyle = WATER.step;
    if (up(0, -1)) { g.fillRect(ox, oy, 16, 3); g.fillRect(ox, oy + 3, 16, 1); }                   // its face is in shade
    if (up(-1, 0)) g.fillRect(ox, oy, 2, 16);
    if (up(1, 0)) g.fillRect(ox + 14, oy, 2, 16);
    if (up(0, 1)) { g.fillStyle = "rgba(255,255,255,.12)"; g.fillRect(ox, oy + 15, 16, 1); }
    for (const [dx, dy, side] of [[0, -1, 0], [1, 0, 1], [0, 1, 2], [-1, 0, 3]]) if (isLand(gndAt(x + dx, y + dy))) foam.push([lx, ly, side, hash(x, y, 30 + side)]);
  }
  if (any) {                                       // the water over it: one pixel a tile, blown up smooth
    const s = document.createElement("canvas"); s.width = s.height = B + 2;
    const sg = s.getContext("2d"), img = sg.createImageData(B + 2, B + 2);
    for (let j = 0; j < B + 2; j++) for (let i = 0; i < B + 2; i++) {
      const u = under(x0 + i - 1, y0 + j - 1), [r, gg, bb, a] = WATER.tint[u < 0 ? 0 : u || 1];
      img.data.set([r, gg, bb, Math.round(255 * a)], (j * (B + 2) + i) * 4);
    }
    sg.putImageData(img, 0, 0);
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
    g.drawImage(s, .5, .5, B + 1, B + 1, -8, -8, n + 16, n + 16);
  }
  return (b.water = {ver: b.ver, canvas: c, any, foam});
}
function drawWater(vis, ox, oy, t) {
  if (!causticPat) causticPat = causticPattern();
  ctx.save(); ctx.translate(ox, oy); ctx.scale(zoom, zoom);
  ctx.imageSmoothingEnabled = false;
  for (const b of vis) {
    if (!b.canvas || !b.gnd) continue;
    const w = waterLayer(b), n = B * 16, X = b.bx * n, Y = b.by * n;
    if (!w.any) continue;
    ctx.drawImage(w.canvas, X, Y);
    ctx.globalCompositeOperation = "lighter";      // light through the surface
    [[t * 5, t * 3], [-t * 4, t * 6]].forEach(([dx, dy], i) => {
      const mx = ((dx % 64) + 64) % 64, my = ((dy % 64) + 64) % 64;
      ctx.globalAlpha = WATER.caustics[i];
      ctx.save(); ctx.translate(mx, my); ctx.fillStyle = causticPat; ctx.fillRect(X - mx, Y - my, n, n); ctx.restore();
    });
    ctx.globalCompositeOperation = "source-over";
    if (waterPatterns) { ctx.globalAlpha = WATER.ripples; ctx.fillStyle = waterPatterns[Math.floor(t * 3) % 4]; ctx.fillRect(X, Y, n, n); }
    ctx.fillStyle = WATER.foam;
    for (const [lx, ly, side, h] of w.foam) {      // foam along the shore, coming in and going out
      const wave = Math.sin(t * 1.4 + h * 6.28), inset = wave > .2 ? 2 : 1, px = X + lx * 16, py = Y + ly * 16;
      ctx.globalAlpha = .45 + .35 * wave;
      const a = 2 + Math.floor(h * 5), len = 16 - a - Math.floor(h * 3);          // not a ruled line: it starts and stops
      if (side === 0) ctx.fillRect(px + a, py + inset - 1, len, 1);
      else if (side === 2) ctx.fillRect(px + a, py + 16 - inset, len, 1);
      else if (side === 3) ctx.fillRect(px + inset - 1, py + a, 1, len);
      else ctx.fillRect(px + 16 - inset, py + a, 1, len);
    }
    ctx.globalAlpha = 1;
  }
  ctx.restore();
}
