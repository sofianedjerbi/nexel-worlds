// The earth itself in the picture of the place seen through what hides it (xray.js: xrayPicture): what was cut
// through to show it, and where the cut ends. Three things, a px each, laid over the land's own painting:
// 1. Earth left standing between two parts of the place under a roof or dug (two tunnels side by side, a pillar in a
//    room) is cut level with the floor behind it, and shows as that: earth, cut. (The land as drawn showed there: a
//    strip of meadow between two floors four layers down, the nearer tunnel a floor lying on the grass.)
// 2. Under a roof the wall behind the place goes up to the top of the land, cut open: the hollow's own back wall is
//    as it is; over that, where the roof was cut through, it is earth in the shade (a burrow in a bank).
// 3. Where the cut ends against the land beside it or in front of it, a line in the pack's ink and a shadow three px
//    in from it, in steps: a hole has an edge ("the borders are still abrupt, like cut without separation": dark
//    earth stopped square against the grass). Not over it where the land's own edge is (its grass hangs there), nor
//    toward ground that goes on level with it (a way out).
// c: the picture's {W, h (px), w (tiles), R (its rect of tiles), y (its top, art px), see, seen, floor, floors, place,
// rocks}. -> {px: what to lay over it, cut: the tiles of 1, more: the px it added to seen}
const CUT = {earth: 110, ink: [112, 70, 58], lip: [.34, .22, .11]};   // how dark earth cut through is (of 255); the edge's ink; its shadow, a px each
function xrayCut({W, h, w, R, y, see, seen, floor, floors, place, rocks}) {
  const n = W * h, px = new Uint32Array(n), al = new Float32Array(n), fill = new Uint8Array(n), cut = new Set(), sa = CUT.earth / 255;
  const soil = colsOf(hillSheet(0)).bands[1], earth = [0, 1, 2].map((q) => soil[q] * (1 - sa) + [30, 20, 28][q] * sa);
  let more = 0;
  for (let i = 0; i < w; i++) {                              // 1
    const x = R.x + i, under = (place.get(x) || []).filter((gy) => floors.get(x + "," + gy) < 0 || floor.has(x + "," + gy));
    for (let j = 0; under.length > 1 && j < R.h; j++) {
      const ty = R.y + j, north = under.filter((gy) => gy < ty);
      if (!rocks[j * w + i] || !north.length || !under.some((gy) => gy > ty)) continue;
      const lv = floors.get(x + "," + Math.max(...north)), Y = ty * 16 - shOf(lv) - y;
      for (let r = Math.max(0, Y); r < Math.min(h, Y + 16); r++) for (let f = r * W + i * 16, e = f + 16; f < e; f++) if (see.state[f] !== 1) { seen[f] = 1; more++; see.lev[f] = lv; fill[f] = 1; cut.add(x + "," + ty); }
    }
  }
  // (the tile a px shows: its own, or for a wall's band the one in front of it)
  const deepT = new Uint8Array(w * R.h), tileOf = (f, d = 0) => { const i = f % W >> 4, j = Math.floor((y + (f / W | 0) + shOf(see.lev[f]) + d) / 16) - R.y; return j >= 0 && j < R.h ? j * w + i : -1; };
  for (const [k, lv] of floors) if (lv < 0 || floor.has(k) || cut.has(k)) { const [x, ty] = k.split(",").map(Number), i = x - R.x, j = ty - R.y; if (i >= 0 && i < w && j >= 0 && j < R.h) deepT[j * w + i] = 1; }
  for (const k of cut) { const [x, ty] = k.split(",").map(Number); deepT[(ty - R.y) * w + x - R.x] = 1; }
  const deep = new Uint8Array(n), dist = new Uint8Array(n).fill(255), todo = [];
  for (let f = 0; f < n; f++) if (see.state[f] === 1 || fill[f]) {
    const t = tileOf(f, see.band[f] ? 4 : 0), ts = tileOf(f);   // (a band starts a px or two over the line between two tiles where a hill's edge is set in: it is of the tile in front all the same)
    if (t < 0 || !deepT[t]) continue;
    deep[f] = 1;
    if (ts >= 0 && seen[f] && see.band[f] && !fill[f] && floor.has((R.x + ts % w) + "," + (R.y + (ts / w | 0))) && landSolid(R.x + ts % w, R.y + (ts / w | 0), see.lev[f])) al[f] = sa;   // 2
  }
  // (q: beside f or under it: not of the place; and not the land's own edge, the top of a tile beside the place or
  // behind it, which has its rim or its grass there; nor, for a floor, ground that goes on level with it)
  const rimT = new Uint8Array(w * R.h);
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (!deepT[j * w + i] && ((i > 0 && deepT[j * w + i - 1]) || (i < w - 1 && deepT[j * w + i + 1]) || (j < R.h - 1 && deepT[(j + 1) * w + i]))) rimT[j * w + i] = 1;
  const out = (f, q) => {
    if (q < 0 || q >= n) return true;
    if (deep[q]) return false;
    if (see.state[q] !== 1) return true;
    if (!see.band[q] && rimT[Math.max(0, tileOf(q))]) return false;
    return see.band[f] || see.band[q] || see.lev[q] > see.lev[f];
  };
  for (let f = 0; f < n; f++) if (seen[f] && deep[f]) {       // 3: where the cut ends
    const x = f % W;
    if (x === 0 || x === W - 1 || out(f, f - 1) || out(f, f + 1) || out(f, f + W) || (f >= W && !deep[f - W] && see.state[f - W] !== 1)) { dist[f] = 0; todo.push(f); }
  }
  for (let i = 0; i < todo.length; i++) {                    // (and in from it, a step a px)
    const f = todo[i], d = dist[f] + 1, x = f % W;
    if (d > CUT.lip.length) continue;
    for (const q of [x ? f - 1 : -1, x < W - 1 ? f + 1 : -1, f - W, f + W]) if (q >= 0 && q < n && seen[q] && deep[q] && dist[q] > d) { dist[q] = d; todo.push(q); }
  }
  const pack = (c, a) => (Math.round(a * 255) << 24 | Math.round(c[2]) << 16 | Math.round(c[1]) << 8 | Math.round(c[0])) >>> 0;
  for (let f = 0; f < n; f++) {
    if (dist[f] === 0) { px[f] = pack(CUT.ink, 1); continue; }
    const lip = dist[f] <= CUT.lip.length ? CUT.lip[dist[f] - 1] : 0;
    if (fill[f]) px[f] = pack(earth.map((v, q) => v * (1 - lip) + [30, 20, 28][q] * lip), 1);
    else if (al[f] || lip) px[f] = pack([30, 20, 28], 1 - (1 - al[f]) * (1 - lip));
  }
  return {px, cut, more};
}
