// Light under a roof (a cave under a hill, a tunnel or a room dug under the ground), where the place you are in is
// seen through what hides it (xray.js): you see what light shows you. Daylight from where the place is open to the
// sky, a few tiles in; you, a little round you; anyone else in there; a fire, more, however far it is: "if fire is
// here, player see it, so it should be visible". The rest of the place is there, dark. floor: its tiles under a roof
// ("x,y" -> height).
const SUN_REACH = 6, DARKEST = .7, GLOW = {me: [4.5, .85], other: [3.5, .75], fire: [6, 1]};   // (tiles of reach, strength)
const sunNow = () => { const phase = clock.phase || 0; return 1 - Math.max(Math.max(0, Math.min(1, (phase - .70) / .05)), phase < .03 ? 1 - phase / .03 : 0); };
// -> "x,y" -> steps in from the nearest way out under the sky (a step from the floor onto ground with nothing over
// it, in the place shown or not: a cave's mouth twelve tiles from you is as bright as one beside you)
function underDepths(floor) {
  const depth = new Map(), queue = [], near = (k) => { const [x, y] = k.split(",").map(Number); return [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => [x + dx, y + dy, x, y]); };
  for (const [k, z] of floor) if (near(k).some(([nx, ny, x, y]) => { const z2 = landAt(z, nx, ny, x, y); return z2 !== null && !coveredAt(nx, ny, z2); })) { depth.set(k, 1); queue.push(k); }
  for (let i = 0; i < queue.length; i++) for (const [nx, ny] of near(queue[i])) { const n = nx + "," + ny; if (floor.has(n) && !depth.has(n)) { depth.set(n, depth.get(queue[i]) + 1); queue.push(n); } }
  return depth;
}
// The picture's px that show ground under a roof (its floors, the walls behind them, the earth cut between its
// parts), made once a picture: P.under (their places), P.mask (a canvas of them: night's lights under a roof keep
// to it, daylight.js), P.shade and P.img (the dark put on them)
function underPx(P) {
  if (P.under) return P.under;
  P.shade = document.createElement("canvas"); P.shade.width = P.w; P.shade.height = P.h; P.img = P.shade.getContext("2d").createImageData(P.w, P.h); P.under = [];
  const fl = new Uint8Array(P.rw * P.rh), m = new Uint32Array(P.w * P.h);
  for (const k of [...P.floor.keys(), ...P.cut]) { const [x, y] = k.split(",").map(Number), i = x - P.rx, j = y - P.ry; if (i >= 0 && i < P.rw && j >= 0 && j < P.rh) fl[j * P.rw + i] = 1; }
  for (let f = 0; f < P.seen.length; f++) if (P.seen[f]) {
    const i = Math.floor((P.x + f % P.w) / 16) - P.rx, j = Math.floor((P.y + (f / P.w | 0) + shOf(P.lev[f])) / 16) - P.ry;
    if (i >= 0 && i < P.rw && j >= 0 && j < P.rh && fl[j * P.rw + i]) { P.under.push(f); m[f] = 0xff000000; P.img.data[f * 4] = 14; P.img.data[f * 4 + 1] = 10; P.img.data[f * 4 + 2] = 18; }
  }
  P.mask = pxCanvas(m, P.w, P.h);
  return P.under;
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
  const under = underPx(P), px = P.img.data;
  for (const f of under) {
    const u = (P.x + f % P.w + .5) / 16 - P.rx + .5, v = (P.y + (f / P.w | 0) + .5 + shOf(P.lev[f])) / 16 - P.ry + .5, i = Math.floor(u), j = Math.floor(v), a = u - i, b = v - j, q = j * tw + i;
    px[f * 4 + 3] = 255 * Math.max(0, (edge[q] * (1 - a) + edge[q + 1] * a) * (1 - b) + (edge[q + tw] * (1 - a) + edge[q + tw + 1] * a) * b);
  }
  P.shade.getContext("2d").putImageData(P.img, 0, 0);
  ctx.globalAlpha = xray.a; ctx.imageSmoothingEnabled = false;
  ctx.drawImage(P.shade, sx(0) + P.x * zoom, sy(0) + P.y * zoom, P.w * zoom, P.h * zoom);
  ctx.globalAlpha = 1;
}
