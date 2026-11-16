// Light in the cave you're in. Daylight comes in at its openings and dies away a few tiles in; past that it is dark,
// but for what gives light: you and anyone else in there (a little), and fires (more). Drawn over the cave's floor
// and whoever stands on it, a shade a tile; nothing outside the cave is touched.
const SUN_REACH = 6, DARKEST = .7, GLOW = {me: [4.5, .85], other: [3.5, .75], fire: [6, 1]};   // (tiles of reach, strength)
let caveDarkC = null, caveMaskC = null, caveLightC = null, caveDepth = new Map();                  // "x,y" -> steps in from the nearest opening onto ground under the sky
function caveDepths() {
  const depth = new Map(), queue = [];
  for (const [k, z] of openCave) {
    const [x, y] = k.split(",").map(Number);
    if ([[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => { const z2 = landAt(z, x + dx, y + dy); return z2 !== null && !coveredAt(x + dx, y + dy, z2); })) { depth.set(k, 1); queue.push([x, y]); }
  }
  for (let i = 0; i < queue.length; i++) {
    const [x, y] = queue[i], d = depth.get(x + "," + y);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const k = (x + dx) + "," + (y + dy); if (openCave.has(k) && !depth.has(k)) { depth.set(k, d + 1); queue.push([x + dx, y + dy]); } }
  }
  return depth;
}
const sunNow = () => { const phase = clock.phase || 0; return 1 - Math.max(Math.max(0, Math.min(1, (phase - .70) / .05)), phase < .03 ? 1 - phase / .03 : 0); };
function drawCaveDark(vis, sx, sy, S, t) {
  if (!caveOpen) return;
  const sun = sunNow(), lights = [];
  for (const p of ents.values()) if (p.e && p.e.kind === "agent" && inOpenCave(Math.round(p.x), Math.round(p.y))) lights.push([p.x, p.y, ...(p.e.id === myId ? GLOW.me : GLOW.other)]);
  for (const b of vis) for (const [i, c] of b.objs) if (c === "^" || c === "x") { const x = b.bx * B + i % B, y = b.by * B + (i / B | 0); if (inOpenCave(x, y)) lights.push([x, y, GLOW.fire[0] * (.95 + .05 * Math.sin(t * 13 + x)), GLOW.fire[1]]); }
  // a light map, a px a tile (the tiles round the cave take their neighbour's light, so its edges don't fade), drawn
  // stretched and smoothed over the cave: no squares. On its own canvas, then cut to the cave's floor as drawn
  // (caves.js: rounded corners and all), so no rock is shaded.
  const [vx, vy, vw, vh0] = viewRect(2), vh = vh0 + 6, n = (vw + 3) * (vh + 3), dark = new Float32Array(n).fill(-1), at = (x, y) => (y - vy + 1) * (vw + 3) + x - vx + 1;
  let lift = 0;
  for (const [k, z] of openCave) {
    const [x, y] = k.split(",").map(Number);
    if (x < vx || x > vx + vw || y < vy || y > vy + vh) continue;
    let light = sun * Math.max(0, 1 - ((caveDepth.get(k) || 99) - 1) / SUN_REACH);
    for (const [lx, ly, r, st] of lights) light = Math.max(light, st * Math.max(0, 1 - Math.hypot(lx - x, ly - y) / r));
    dark[at(x, y)] = (1 - Math.min(1, light)) * DARKEST; lift = shOf(z) * zoom;
  }
  if (!caveLightC) caveLightC = document.createElement("canvas");
  if (caveLightC.width !== vw + 3 || caveLightC.height !== vh + 3) { caveLightC.width = vw + 3; caveLightC.height = vh + 3; }
  const lg = caveLightC.getContext("2d"), img = lg.createImageData(vw + 3, vh + 3);
  for (let i = 0; i < n; i++) {
    let d = dark[i];
    const tx = vx - 1 + i % (vw + 3), ty = vy - 1 + (i / (vw + 3) | 0);
    if (d < 0 && !roofAt(tx, ty)) d = 0;                  // (open ground beside the cave: daylight)
    if (d < 0) { let sum = 0, cnt = 0; for (const o of [-1, 1, -(vw + 3), vw + 3, -(vw + 4), -(vw + 2), vw + 2, vw + 4]) if (dark[i + o] >= 0) { sum += dark[i + o]; cnt++; } d = cnt ? sum / cnt : 0; }
    img.data[i * 4] = 14; img.data[i * 4 + 1] = 10; img.data[i * 4 + 2] = 18; img.data[i * 4 + 3] = d * 255;
  }
  lg.putImageData(img, 0, 0);
  if (!caveDarkC) caveDarkC = document.createElement("canvas");
  if (caveDarkC.width !== cv.width || caveDarkC.height !== cv.height) { caveDarkC.width = cv.width; caveDarkC.height = cv.height; }
  const g = caveDarkC.getContext("2d");
  g.setTransform(DPR, 0, 0, DPR, 0, 0); g.globalCompositeOperation = "source-over"; g.clearRect(0, 0, W, H);
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(caveLightC, sx(vx - 1), sy(vy - 1) - lift, (vw + 3) * S, (vh + 3) * S);
  if (!caveMaskC) caveMaskC = document.createElement("canvas");
  if (caveMaskC.width !== cv.width || caveMaskC.height !== cv.height) { caveMaskC.width = cv.width; caveMaskC.height = cv.height; }
  const m = caveMaskC.getContext("2d");
  m.setTransform(DPR, 0, 0, DPR, 0, 0); m.clearRect(0, 0, W, H); m.imageSmoothingEnabled = false;
  for (const b of vis) if (b.caveOv) m.drawImage(b.caveOv, sx(b.bx * B) - OV_M * zoom, sy(b.by * B) - OV_M * zoom, b.caveOv.width * zoom, b.caveOv.height * zoom);
  g.globalCompositeOperation = "destination-in"; g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(caveMaskC, 0, 0);
  ctx.drawImage(caveDarkC, 0, 0, W, H);
}

// The same light under ground that was dug (a tunnel, a room under the meadow), where the place you are in is seen
// through its roof (xray.js): you see what light shows you. Daylight from where the place is open to the sky, a few
// tiles in; you, a little round you; a fire, more, however far it is: "if fire is here, player see it, so it should
// be visible". The rest of the place is there, dark. ("there's no gradient": it was all as bright as day, and cut
// off four tiles from you.) floor: its tiles under a roof ("x,y" -> height); place: all its tiles.
// -> "x,y" -> steps in from the nearest tile of the place under the sky
function underDepths(floor, place) {
  const depth = new Map(), queue = [], near = (k) => { const [x, y] = k.split(",").map(Number); return [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => (x + dx) + "," + (y + dy)); };
  for (const k of floor.keys()) if (near(k).some((n) => place.has(n) && !floor.has(n))) { depth.set(k, 1); queue.push(k); }
  for (let i = 0; i < queue.length; i++) for (const n of near(queue[i])) if (floor.has(n) && !depth.has(n)) { depth.set(n, depth.get(queue[i]) + 1); queue.push(n); }
  return depth;
}
// Drawn over the picture seen through the roof and whoever stands in it: a shade a px of the floors and walls under
// the roof, each from its tile's light and the tiles' beside it (no squares), as the land's px are (not smoothed)
function drawUnderDark(vis, sx, sy, t) {
  const P = xray.pic;
  if (xray.a <= .01 || !P || !P.floor.size || opt("above") === "circle") return;
  const sun = sunNow(), lights = [], tw = P.rw + 2, dark = new Float32Array(tw * (P.rh + 2)).fill(-1), at = (x, y) => (y - P.ry + 1) * tw + x - P.rx + 1, inPic = (x, y) => x >= P.rx && x < P.rx + P.rw && y >= P.ry && y < P.ry + P.rh;
  for (const p of ents.values()) { const x = Math.round(p.x), y = Math.round(p.y); if (p.e && p.e.kind === "agent" && (p.e.id === myId || (P.floor.has(x + "," + y) && xrayShows(p) > 0))) lights.push([p.x, p.y, ...(p.e.id === myId ? GLOW.me : GLOW.other)]); }
  for (const b of vis) for (const [i, c] of b.objs) if (c === "^" || c === "x") { const x = b.bx * B + i % B, y = b.by * B + (i / B | 0); if (P.place.has(x + "," + y)) lights.push([x, y, GLOW.fire[0] * (.95 + .05 * Math.sin(t * 13 + x)), GLOW.fire[1]]); }
  for (const k of P.place.keys()) {                        // (its tiles under the sky: daylight)
    const [x, y] = k.split(",").map(Number); if (!inPic(x, y)) continue;
    let light = P.floor.has(k) ? sun * Math.max(0, 1 - ((P.depth.get(k) || 99) - 1) / SUN_REACH) : 1;
    for (const [lx, ly, r, st] of lights) light = Math.max(light, st * Math.max(0, 1 - Math.hypot(lx - x, ly - y) / r));
    dark[at(x, y)] = (1 - Math.min(1, light)) * DARKEST;
  }
  const edge = dark.slice();                               // (the rock round it: as dark as the floor beside it, so its edges don't fade)
  for (let q = tw; q < dark.length - tw; q++) if (dark[q] < 0) { let sum = 0, cnt = 0; for (const o of [-1, 1, -tw, tw, -tw - 1, -tw + 1, tw - 1, tw + 1]) if (dark[q + o] >= 0) { sum += dark[q + o]; cnt++; } edge[q] = cnt ? sum / cnt : 0; }
  if (!P.shade) {                                          // (once a picture: its px that show ground under a roof)
    P.shade = document.createElement("canvas"); P.shade.width = P.w; P.shade.height = P.h; P.img = P.shade.getContext("2d").createImageData(P.w, P.h); P.under = [];
    const fl = new Uint8Array(P.rw * P.rh); for (const k of P.floor.keys()) { const [x, y] = k.split(",").map(Number); if (inPic(x, y)) fl[(y - P.ry) * P.rw + x - P.rx] = 1; }
    for (let f = 0; f < P.seen.length; f++) if (P.seen[f]) {
      const i = Math.floor((P.x + f % P.w) / 16) - P.rx, j = Math.floor((P.y + (f / P.w | 0) + shOf(P.lev[f])) / 16) - P.ry;
      if (i >= 0 && i < P.rw && j >= 0 && j < P.rh && fl[j * P.rw + i]) { P.under.push(f); P.img.data[f * 4] = 14; P.img.data[f * 4 + 1] = 10; P.img.data[f * 4 + 2] = 18; }
    }
  }
  const px = P.img.data;
  for (const f of P.under) {
    const u = (P.x + f % P.w + .5) / 16 - P.rx + .5, v = (P.y + (f / P.w | 0) + .5 + shOf(P.lev[f])) / 16 - P.ry + .5, i = Math.floor(u), j = Math.floor(v), a = u - i, b = v - j, q = j * tw + i;
    px[f * 4 + 3] = 255 * Math.max(0, (edge[q] * (1 - a) + edge[q + 1] * a) * (1 - b) + (edge[q + tw] * (1 - a) + edge[q + tw + 1] * a) * b);
  }
  P.shade.getContext("2d").putImageData(P.img, 0, 0);
  ctx.globalAlpha = xray.a; ctx.imageSmoothingEnabled = false;
  ctx.drawImage(P.shade, sx(0) + P.x * zoom, sy(0) + P.y * zoom, P.w * zoom, P.h * zoom);
  ctx.globalAlpha = 1;
}
