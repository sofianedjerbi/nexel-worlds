// Underground, like being in a house: the level above stays on screen (dimmed: it's over you), and the part of the
// cave you're in shows in it, as a house shows its inside when you walk in. That part is the open cave joined to
// you (out to REGION_R tiles) and the rock around it, drawn with the earth floor's and the rock's own edge and corner
// tiles, so it reads as a place with walls, not a cut-out. Arriving on a level it fades in (the roof lifting);
// leaving it, it fades out. Down its holes, the level below (layers.js).

const REGION_R = 7, ABOVE_DIM = .3, REVEAL_MS = 400;
let region = null, regionCv = null, revealAt = -1e9, shownDepth = null, leaving = null;

// The open tiles joined to (px, py) on this level, within REGION_R, and the rock around them
function caveRegion(px, py) {
  const open = new Set(), q = [[px, py]], isOpen = (c) => c !== null && c !== "R" && c !== "*";
  while (q.length && open.size < 260) {
    const [x, y] = q.shift(), k = x + "," + y;
    if (open.has(k) || (x - px) ** 2 + (y - py) ** 2 > REGION_R * REGION_R || !isOpen(combAt(x, y))) continue;
    open.add(k);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) q.push([x + dx, y + dy]);
  }
  const all = new Set(open), ring = new Set();
  for (const k of open) {
    const [x, y] = k.split(",").map(Number);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const n = x + dx + "," + (y + dy);
      if (!open.has(n)) { ring.add(n); all.add(n); }
    }
  }
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const k of all) { const [x, y] = k.split(",").map(Number); x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  return {open, ring, all, x0, y0, x1, y1, key: px + "," + py, at: performance.now()};
}
// The region drawn once (art pixels, 16 a tile): earth under all of it, its edges the soil sheet's own; the rock
// round it as the stone sheet's, its outer edges and corners too; the mouths and ramps in it
function drawRegion(r) {
  const c = document.createElement("canvas");
  c.width = (r.x1 - r.x0 + 1) * 16; c.height = (r.y1 - r.y0 + 1) * 16;
  const g = c.getContext("2d"), inAll = (_, __, tx, ty) => r.all.has(tx + "," + ty), inRing = (_, __, tx, ty) => r.ring.has(tx + "," + ty);
  for (const k of r.all) {
    const [x, y] = k.split(",").map(Number), ox = (x - r.x0) * 16, oy = (y - r.y0) * 16;
    drawBlobLayer(g, IMG.soil, x, y, inAll, ox, oy, .15);
    const cc = combAt(x, y);
    if (cc === "O" || cc === "l") { const s = objectSprite(cc, x, y, 0); g.drawImage(s[0], s[1], s[2], 16, 16, ox, oy, 16, 16); }
  }
  for (const k of r.ring) { const [x, y] = k.split(",").map(Number); drawBlobLayer(g, IMG.hill3, x, y, inRing, (x - r.x0) * 16, (y - r.y0) * 16, .15); }
  return c;
}
const inRegion = (x, y) => !!region && region.all.has(Math.round(x) + "," + Math.round(y));

// The level above, as it would be drawn (ground, then its things in depth order), dimmed by `dim`
function drawAboveLevel(sx, sy, S, t, dim) {
  const out = otherBlocks(-LAYER_B, S), list = [];
  for (const b of out) {
    ctx.drawImage(b.canvas, sx(b.bx * B + LAYER), sy(b.by * B), B * S, B * S);
    for (const [i, c] of b.objs) {
      const x = b.bx * B + i % B, y = b.by * B + (i / B | 0), spr = objectSprite(c, x, y, t);
      if (spr) list.push({y, x, spr});
    }
  }
  list.sort((a, b) => a.y - b.y || a.x - b.x);
  for (const o of list) {
    const [img, a, b2, w, h, dx, dy] = o.spr;
    ctx.drawImage(img, a, b2, w, h, Math.round(sx(o.x + LAYER) + dx * zoom), Math.round(sy(o.y) + dy * zoom), w * zoom, h * zoom);
  }
  if (dim > .01) { ctx.fillStyle = `rgba(28,22,34,${dim})`; ctx.fillRect(0, 0, W, H); }
}

// Called after this level's ground is drawn. Underground: the level above, then the region you're in over it.
function drawCaveGround(sx, sy, S, t, now) {
  const d = depthOf(cam.x), me_ = ents.get("agent" + myId);
  if (shownDepth !== null && d !== shownDepth) {           // a level changed: what you leave fades out over the new
    leaving = region && shownDepth > d ? {r: region, c: regionCv, shift: (shownDepth - d) * LAYER} : null;
    region = null; revealAt = now;
  }
  shownDepth = d;
  const k = smooth((now - revealAt) / REVEAL_MS);
  if (d && me_) {
    const key = Math.round(me_.x) + "," + Math.round(me_.y);
    if (!region || region.key !== key || now - region.at > 600) { region = caveRegion(Math.round(me_.x), Math.round(me_.y)); regionCv = drawRegion(region); }
    drawAboveLevel(sx, sy, S, t, d > 1 ? .62 : ABOVE_DIM * (leaving ? 1 : k));   // (a cave above is in its dark)
    ctx.globalAlpha = k;
    ctx.drawImage(regionCv, sx(region.x0), sy(region.y0), (region.x1 - region.x0 + 1) * S, (region.y1 - region.y0 + 1) * S);
    ctx.globalAlpha = 1;
  } else region = null;
  if (leaving && k < 1) {                                  // (coming up: the cave you left, over the land)
    const r = leaving.r;
    if (!d) { ctx.fillStyle = `rgba(28,22,34,${ABOVE_DIM * (1 - k)})`; ctx.fillRect(0, 0, W, H); }
    ctx.globalAlpha = 1 - k;
    ctx.drawImage(leaving.c, sx(r.x0 - leaving.shift), sy(r.y0), (r.x1 - r.x0 + 1) * S, (r.y1 - r.y0 + 1) * S);
    ctx.globalAlpha = 1;
  } else if (k >= 1) leaving = null;
}
