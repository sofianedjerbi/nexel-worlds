// Light in the place you are in, where it is seen through what hides it (xray.js). One model, for all of the place
// ("see how lightning is cut ? Uniformise it with a real lightning model, sun outside goes inside etc"; it was two:
// the floors and walls under a roof by their tile's light, and the earth cut through a flat shade darker, from the
// roof's edge on: a line down the wall where the roof starts):
// - Under the sky the place has the light outside (the day's, the night's: daylight.js), and nothing is put on it.
// - Under a roof the sun comes in at every way out and fades along the way, SUN_REACH tiles in; none at night.
// - You, anyone else there, a fire: each lights round it, less with the way from it, which is the longer of the
//   straight line and three quarters of the tiles walked: round a corner, not through the earth between two tunnels
//   ("if fire is here, player see it, so it should be visible": however far it is, it is lit).
// - A tile's light is the most of these; what is missing of it is its dark, DARKEST at the most.
// - The wall behind a room, and earth cut level between two parts of the place, are lit as the place beside them, wall
//   and floor one light: the earth had the sky's light alone, so it was darker than the hollow and its floor from the
//   second tile in, a stair of light and dark down a dug stair ("lightning show clear distinction with floor").
// - Every px of the place takes its dark from its tile and the tiles beside it: no squares, and no edge where a roof
//   starts.
const SUN_REACH = 6, DARKEST = .7, GLOW = {me: [4.5, .85], other: [3.5, .75], fire: [6, 1]};   // (tiles of reach, strength)
const sunNow = () => { const phase = clock.phase || 0; return 1 - Math.max(Math.max(0, Math.min(1, (phase - .70) / .05)), phase < .03 ? 1 - phase / .03 : 0); };
const tilesBeside = (k) => { const [x, y] = k.split(",").map(Number); return [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => [x + dx, y + dy, x, y]); };
// floor: the place's tiles under a roof ("x,y" -> height) -> "x,y" -> steps in from the nearest way out under the sky
// (a step from the floor onto ground with nothing over it, in the place shown or not: a cave's mouth twelve tiles
// from you is as bright as one beside you)
function underDepths(floor) {
  const depth = new Map(), queue = [];
  for (const [k, z] of floor) if (tilesBeside(k).some(([nx, ny, x, y]) => { const z2 = landAt(z, nx, ny, x, y); return z2 !== null && !coveredAt(nx, ny, z2); })) { depth.set(k, 1); queue.push(k); }
  for (let i = 0; i < queue.length; i++) for (const [nx, ny] of tilesBeside(queue[i])) { const n = nx + "," + ny; if (floor.has(n) && !depth.has(n)) { depth.set(n, depth.get(queue[i]) + 1); queue.push(n); } }
  return depth;
}
// The tiles walked from a tile of the place to each other one, as far as twelve (kept a picture: a fire stays put)
function stepsFrom(P, key) {
  if (!P.paths) P.paths = new Map();
  if (P.paths.has(key)) return P.paths.get(key);
  const steps = new Map([[key, 0]]), queue = [key];
  for (let i = 0; i < queue.length; i++) { const d = steps.get(queue[i]); if (d < 12) for (const [nx, ny] of tilesBeside(queue[i])) { const n = nx + "," + ny; if (P.place.has(n) && !steps.has(n)) { steps.set(n, d + 1); queue.push(n); } } }
  P.paths.set(key, steps);
  return steps;
}
// The picture's px that show ground under a roof (its floors, the walls behind them, the earth cut between its
// parts), made once a picture: P.under (their places), P.mask (a canvas of them: night's lights under a roof keep
// to it, daylight.js)
function underPx(P) {
  if (P.under) return P.under;
  P.under = [];
  const fl = new Uint8Array(P.rw * P.rh), m = new Uint32Array(P.w * P.h);
  for (const k of [...P.floor.keys(), ...P.cut]) { const [x, y] = k.split(",").map(Number), i = x - P.rx, j = y - P.ry; if (i >= 0 && i < P.rw && j >= 0 && j < P.rh) fl[j * P.rw + i] = 1; }
  for (let f = 0; f < P.seen.length; f++) if (P.seen[f]) {
    const i = Math.floor((P.x + f % P.w) / 16) - P.rx, j = Math.floor((P.y + (f / P.w | 0) + shOf(P.lev[f])) / 16) - P.ry;
    if (i >= 0 && i < P.rw && j >= 0 && j < P.rh && fl[j * P.rw + i]) { P.under.push(f); m[f] = 0xff000000; }
  }
  P.mask = pxCanvas(m, P.w, P.h);
  return P.under;
}
// ...and the px the light is worked out for: all of the place's own (P.deep: under a roof or not, seen through or
// not), each with where it is among the tiles (its tile's corner in the grid of tiles and how far along it is, across
// and down) P.shade, P.img: the dark put on them. Once a picture
function litPx(P) {
  if (P.lit) return P.lit;
  P.shade = document.createElement("canvas"); P.shade.width = P.w; P.shade.height = P.h; P.img = P.shade.getContext("2d").createImageData(P.w, P.h);
  const at = [], tw = P.rw + 2;
  for (let f = 0; f < P.deep.length; f++) if (P.deep[f]) at.push(f);
  P.lit = {f: Int32Array.from(at), q: new Int32Array(at.length), a: new Float32Array(at.length), b: new Float32Array(at.length)};
  at.forEach((f, n) => {
    const u = (P.x + f % P.w + .5) / 16 - P.rx + .5, v = (P.y + (f / P.w | 0) + .5 + shOf(P.lev[f])) / 16 - P.ry + .5, i = Math.max(0, Math.min(P.rw, Math.floor(u))), j = Math.max(0, Math.min(P.rh, Math.floor(v)));
    P.lit.q[n] = j * tw + i; P.lit.a[n] = Math.max(0, Math.min(1, u - i)); P.lit.b[n] = Math.max(0, Math.min(1, v - j));
    P.img.data[f * 4] = 14; P.img.data[f * 4 + 1] = 10; P.img.data[f * 4 + 2] = 18;
  });
  return P.lit;
}
// Drawn over the picture and whoever stands in it: the dark of each px of the place, as the land's px are (not smoothed).
// Worked out again only when a light has moved, a fire's flame has changed (its reach, a sixteenth of a tile) or the
// sun has: it was every frame, every px of the place written and the whole picture sent to the screen's memory again,
// standing still in the dark. A picture's tiles are read once (P.cells), its grids kept (P.dark).
function drawUnderDark(vis, sx, sy, t) {
  const P = xray.pic;
  if (xray.a <= .01 || !P || !P.floor.size || !P.deep || opt("above") === "circle") return;
  const sun = sunNow(), lights = [], tw = P.rw + 2, n = tw * (P.rh + 2);
  const sig = [sun], was = P.sig;                           // (all the dark is worked out from: the same numbers, the same dark)
  const lamp = (lx, ly, r, st) => { const k = Math.round(lx) + "," + Math.round(ly); lights.push([lx, ly, r, st, P.place.has(k) ? stepsFrom(P, k) : null]); sig.push(lx, ly, r, st); };
  for (const p of ents.values()) { const x = Math.round(p.x), y = Math.round(p.y); if (p.e && p.e.kind === "agent" && (p.e.id === myId || (P.floor.has(x + "," + y) && xrayShows(p) > 0))) lamp(p.x, p.y, ...(p.e.id === myId ? GLOW.me : GLOW.other)); }
  for (const b of vis) b.objs.forEach((c, i) => { if (c === "^" || c === "x") { const x = b.bx * B + i % B, y = b.by * B + (i / B | 0); if (P.place.has(x + "," + y)) lamp(x, y, GLOW.fire[0] * (.95 + .05 * Math.sin(t * 13 + x)), GLOW.fire[1]); } });
  if (!was || was.length !== sig.length || sig.some((v, i) => v !== was[i])) {
    P.sig = sig;
    if (!P.cells) {                                         // (its tiles inside the picture: where, the key, under a roof or not, how far in, its place in the grid)
      P.cells = []; P.dark = new Float32Array(n); P.own = new Float32Array(n);
      for (const k of P.place.keys()) { const [x, y] = k.split(",").map(Number); if (x >= P.rx && x < P.rx + P.rw && y >= P.ry && y < P.ry + P.rh) P.cells.push([x, y, k, P.floor.has(k), P.depth.get(k) || 99, (y - P.ry + 1) * tw + x - P.rx + 1]); }
    }
    const dark = P.dark.fill(-1), own = P.own, round = [-1, 1, -tw, tw, -tw - 1, -tw + 1, tw - 1, tw + 1];
    for (const [x, y, k, under, d, q] of P.cells) {
      if (!under) { dark[q] = 0; continue; }                // (under the sky: the light outside)
      let light = sun * Math.max(0, 1 - (d - 1) / SUN_REACH);
      for (const [lx, ly, r, st, steps] of lights) { const walked = steps ? steps.get(k) : 0; if (walked !== undefined) light = Math.max(light, st * Math.max(0, 1 - Math.max(Math.hypot(lx - x, ly - y), .75 * walked) / r)); }
      dark[q] = (1 - Math.min(1, light)) * DARKEST;
    }
    own.set(dark);                                          // (the earth round it and between its parts: as the tiles of the place beside it, so its edges don't fade)
    for (let q = tw; q < n - tw; q++) if (own[q] < 0) { let sum = 0, cnt = 0; for (const o of round) { const v = own[q + o]; if (v >= 0) { sum += v; cnt++; } } dark[q] = cnt ? sum / cnt : 0; }
    for (let q = 0; q < n; q++) if (dark[q] < 0) dark[q] = 0;
    const L = litPx(P), px = P.img.data, f = L.f, qs = L.q, as = L.a, bs = L.b;
    for (let i = 0; i < f.length; i++) { const q = qs[i], a = as[i], b = bs[i]; px[f[i] * 4 + 3] = 255 * ((dark[q] * (1 - a) + dark[q + 1] * a) * (1 - b) + (dark[q + tw] * (1 - a) + dark[q + tw + 1] * a) * b); }
    P.shade.getContext("2d").putImageData(P.img, 0, 0);
  }
  ctx.globalAlpha = xray.a; ctx.imageSmoothingEnabled = false;
  ctx.drawImage(P.shade, sx(0) + P.x * zoom, sy(0) + P.y * zoom, P.w * zoom, P.h * zoom);
  ctx.globalAlpha = 1;
}
