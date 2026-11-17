// What hides you, the views that are not a circle (options.js: VIEWS; the circle, and the picture itself: xray.js)

// Cut away, outline, faded: all of the picture (the ground under the rock in the way, its water as it is this
// frame), over the rock: whole, or a share of it; in the outline view the rock's edges over it, in the pack's ink
function drawXrayWhole(sx, sy) {
  const v = opt("above"), k = v === "faded" ? XRAY_FADED : 1, both = (xray.old ? [[xray.old, 1 - xray.mix], [xray.pic, xray.mix]] : [[xray.pic, 1]]).filter(([Q]) => Q.any);
  if (!both.length) return;
  for (const [Q] of both) {
    if (!Q.whole) { Q.whole = document.createElement("canvas"); Q.whole.width = Q.w; Q.whole.height = Q.h; }
    const g = Q.whole.getContext("2d");
    g.globalCompositeOperation = "source-over"; g.clearRect(0, 0, Q.w, Q.h); g.imageSmoothingEnabled = false;
    if (waterView) {
      g.drawImage(waterCv, Q.x - waterView.x, Q.y - waterView.y, Q.w, Q.h, 0, 0, Q.w, Q.h);
      g.globalCompositeOperation = "destination-in"; g.drawImage(Q.wet, 0, 0);
      g.globalCompositeOperation = "source-over";
    }
    g.drawImage(Q.over, 0, 0);
    if (v === "outline") g.drawImage(xrayEdges(Q), 0, 0);
  }
  // one picture, or the new one coming over the one before: the two added up, each for its share, then put on the
  // land once (each put on it faint, the land showed between them half way: a flash at every step)
  const x0 = Math.min(...both.map(([Q]) => Q.x)), y0 = Math.min(...both.map(([Q]) => Q.y)), w = Math.max(...both.map(([Q]) => Q.x + Q.w)) - x0, h = Math.max(...both.map(([Q]) => Q.y + Q.h)) - y0;
  const c = xray.cw || (xray.cw = document.createElement("canvas")); if (c.width < w || c.height < h) { c.width = Math.max(c.width, w); c.height = Math.max(c.height, h); }
  const g = c.getContext("2d");
  g.globalCompositeOperation = "source-over"; g.globalAlpha = 1; g.clearRect(0, 0, c.width, c.height); g.imageSmoothingEnabled = false;
  for (const [Q, share] of both) { g.globalAlpha = xray.old ? share : 1; g.drawImage(Q.whole, Q.x - x0, Q.y - y0); g.globalCompositeOperation = "lighter"; }
  ctx.globalAlpha = xray.a * k;
  ctx.drawImage(c, 0, 0, w, h, sx(0) + x0 * zoom, sy(0) + y0 * zoom, w * zoom, h * zoom);
  ctx.globalAlpha = 1;
}
// The outline, an art px wide, in ink, made once a picture. In the ground or under a roof: round the place itself,
// as one shape (xraycut.js says which px: its edge where it is dug, under a roof or cut, seen through or not, so a
// hole's open part is of it and no line crosses it; none where its floor goes on level with the ground outside. The
// line was round all that the ground in front was drawn over: a tile out from the cut, across a stair's wall, round
// the sliver of meadow a hill's side had covered). Behind a hill and no more: round what the hill was drawn over
function xrayEdges(Q) {
  if (Q.edges) return Q.edges;
  const m = new Uint32Array(Q.w * Q.h), W = Q.w, ink = 0xff604c75, s = Q.seen;   // (the walls' ink, #754c60: structures.js; as a little-endian px)
  if (Q.line) for (let f = 0; f < m.length; f++) { if (Q.line[f]) m[f] = ink; }
  else for (let y = 0; y < Q.h; y++) for (let x = 0; x < W; x++) {
    const f = y * W + x;
    if (s[f] && (x === 0 || y === 0 || x === W - 1 || y === Q.h - 1 || !s[f - 1] || !s[f + 1] || !s[f - W] || !s[f + W])) m[f] = ink;
  }
  return (Q.edges = pxCanvas(m, W, Q.h));
}
