// The earth itself in the picture of the place seen through what hides it (xray.js: xrayPicture): what was cut
// through to show it, and where the cut ends. Three things, a px each, laid over the land's own painting:
// 1. Earth left standing between two parts of the place under a roof or dug (two tunnels side by side, a pillar in a
//    room) is cut level with the floor behind it, and shows as that: earth, cut. (The land as drawn showed there: a
//    strip of meadow between two floors four layers down, the nearer tunnel a floor lying on the grass.)
// 2. Under a roof the wall behind the place goes up to the top of the land, cut open: the hollow's own back wall is
//    as it is; over that, where the roof was cut through, it is earth in the shade (a burrow in a bank).
// 3. Where the cut ends against the land beside it or in front of it, a line in the pack's ink and a shadow three px
//    in from it, in steps: a hole has an edge ("the borders are still abrupt, like cut without separation": dark
//    earth stopped square against the grass). Not where the land's own edge is (round a hole open to the sky: its
//    grass hangs there), nor toward ground that goes on level with it (a way out).
// c: the picture's {W, h (px), w (tiles), R (its rect of tiles), y (its top, art px), see, seen, floor, floors, place,
// rocks, paint (its px as the land's painter left them)}. -> {px: what to lay over it, cut: the tiles of 1, more: the px it added to seen, line: the px of the
// outline round the place where it is under a roof, dug or cut (xrayviews.js; null: no such place, a hill in front and
// no more)}
const CUT = {earth: 110, ink: [112, 70, 58], lip: [.34, .22, .11]};   // how dark earth cut through is (of 255); the edge's ink; its shadow, a px each
function xrayCut({W, h, w, R, y, see, seen, floor, floors, place, rocks, paint}) {
  const n = W * h, px = new Uint32Array(n), al = new Float32Array(n), fill = new Uint8Array(n), cuts = new Map(), sa = CUT.earth / 255;
  const soil = colsOf(hillSheet(0)).bands[1], earth = [0, 1, 2].map((q) => soil[q] * (1 - sa) + [30, 20, 28][q] * sa);
  let more = 0;
  for (let i = 0; i < w; i++) {                              // 1
    const x = R.x + i, under = (place.get(x) || []).filter((gy) => floors.get(x + "," + gy) < 0 || floor.has(x + "," + gy));
    for (let j = 0; under.length > 1 && j < R.h; j++) {
      const ty = R.y + j, north = under.filter((gy) => gy < ty);
      if (!rocks[j * w + i] || !north.length || !under.some((gy) => gy > ty)) continue;
      const lv = floors.get(x + "," + Math.max(...north)), Y = ty * 16 - shOf(lv) - y;
      for (let r = Math.max(0, Y); r < Math.min(h, Y + 16); r++) for (let f = r * W + i * 16, e = f + 16; f < e; f++) if (see.state[f] !== 1) { seen[f] = 1; more++; see.lev[f] = lv; fill[f] = 1; cuts.set(x + "," + ty, lv); }
    }
  }
  // The place's own px (deep): for each of its tiles under a roof, dug or cut, its column on the screen from the top
  // of the wall behind it (the tile north of it, as high as the picture has it) down to the foot of its floor; of
  // that, what the picture painted but the land's own there (another tile's top, a hill's ledge beside it). A shape
  // of whole tiles: worked out a px at a time from what each px was painted as, a wall's top came out in hooks where
  // a hill steps down beside it. (Two px over the line a wall's band may start, where a hill's edge is set in.)
  const deepT = new Uint8Array(w * R.h), cutLv = new Map(), lvT = R.lk || R.lv, at = (i, j) => (j + 2) * (w + 4) + i + 2;
  const tileOf = (f, d = 0) => { const i = f % W >> 4, j = Math.floor((y + (f / W | 0) + shOf(see.lev[f]) + d) / 16) - R.y; return j >= 0 && j < R.h ? j * w + i : -1; };   // (the tile a px was painted as; d = 4: for a wall's band, the tile in front of it)
  for (const [k, lv] of floors) if (lv < 0 || floor.has(k)) { const [x, ty] = k.split(",").map(Number), i = x - R.x, j = ty - R.y; if (i >= 0 && i < w && j >= 0 && j < R.h) deepT[j * w + i] = 1; }
  for (const [k, lv] of cuts) { const [x, ty] = k.split(",").map(Number); deepT[(ty - R.y) * w + x - R.x] = 1; cutLv.set((ty - R.y) * w + x - R.x, lv); }
  const lvOf = (i, j) => (i >= 0 && i < w && j >= 0 && j < R.h && cutLv.has(j * w + i) ? cutLv.get(j * w + i) : lvT[at(i, j)]);
  const deep = new Uint8Array(n), dist = new Uint8Array(n).fill(255), todo = [], wall = new Map();
  const roofT = new Uint8Array(w * R.h), band = (k, m) => colsOf(hillSheet(k)).bands[m <= 0 ? 0 : m >= 7 ? 2 : 1];
  for (const k of floor.keys()) { const [x, ty] = k.split(",").map(Number), i = x - R.x, j = ty - R.y; if (i >= 0 && i < w && j >= 0 && j < R.h) roofT[j * w + i] = 1; }
  const rows = (i, j) => { const f0 = lvOf(i, j), Y = (R.y + j) * 16 - y; return [Y, Y - shOf(Math.max(f0, lvOf(i, j - 1))), Y - shOf(f0)]; };   // (a tile's line at sea level, the top of the wall behind it, the top of its floor)
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (deepT[j * w + i]) {
    const [Y, r0, top] = rows(i, j), t = j * w + i, roofed = roofT[t];
    for (let r = Math.max(0, r0 - 3); r < Math.min(h, top + 16); r++) for (let f = r * W + i * 16, e = f + 16; f < e; f++) {
      const back = roofed && r >= r0 && r < top, put = fill[f] || see.state[f] === 1;   // (back: over the floor of a tile under a roof: the wall behind it, whatever was painted)
      if ((!put && !back) || (r < r0 && see.band[f] !== 1)) continue;
      if (put && !fill[f]) {                                 // (of what was painted there: the place's floors, and the wall behind this tile, its bands and
        const ts = tileOf(f), tf = tileOf(f, 4);            //  what shows between them of the tile behind, painted a level down; not land that stands in front
        if (see.band[f] === 2 ? !back : see.band[f] === 1 ? tf !== t : ts < 0 || (!deepT[ts] && (ts !== t - w || see.lev[f] >= lvT[at(ts % w, ts / w | 0)]))) continue;   //  of it or beside it: its top, its wall, a ledge)
      }
      deep[f] = 1;
      if (!back || fill[f]) continue;
      // (a wall cut through is its bands, a layer each, and no more: where the land's painter put something else
      // there, a sliver of grass through the set-in edge of a hill that steps down beside it, the end of a ledge that
      // hung from the roof's side and the band under it, two px out of step: the band, as it paints it)
      const k = Math.ceil((Y - r) / 8);
      if (!put || see.band[f] !== 1 || !seen[f] || see.lev[f] !== k) { wall.set(f, band(k, r - (Y - shOf(k)))); if (!seen[f]) { seen[f] = 1; more++; } see.lev[f] = k; see.band[f] = 1; }
      if (landSolid(R.x + i, R.y + j, k)) al[f] = sa;        // 2
    }
  }
  // (and beside a tile under a roof, the wall of one open to the sky: the four px of it next to that tile had the same
  // leftovers of the roof's side: they are the wall's own px from further in, row for row)
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (deepT[j * w + i] && !roofT[j * w + i]) for (const d of [-1, 1]) {
    if (i + d < 0 || i + d >= w || !roofT[j * w + i + d]) continue;
    const [, r0, top] = rows(i, j);
    for (let r = Math.max(0, r0 - 2); r < Math.min(h, top); r++) for (let c = 0; c < 4; c++) {
      const col = d < 0 ? c : 15 - c, f = r * W + i * 16 + col, src = r * W + i * 16 + (d < 0 ? 4 : 11);
      if (!deep[src] || fill[src] || see.band[src] === 2) continue;
      const v = wall.get(src) || [paint[src] & 255, paint[src] >> 8 & 255, paint[src] >> 16 & 255];
      wall.set(f, v); deep[f] = 1; if (!seen[f]) { seen[f] = 1; more++; } see.lev[f] = see.lev[src]; see.band[f] = see.band[src];
    }
  }
  // (q: beside f, over it or under it: not of the place; and not the land's own edge, the top of a tile beside or
  // behind a part of the place that is open to the sky, which has its rim or its grass there; nor, for a floor,
  // ground that goes on level with it)
  const rimT = new Uint8Array(w * R.h), openT = new Uint8Array(w * R.h);
  for (const [k, lv] of floors) if (lv < 0 && !floor.has(k)) { const [x, ty] = k.split(",").map(Number), i = x - R.x, j = ty - R.y; if (i >= 0 && i < w && j >= 0 && j < R.h) openT[j * w + i] = 1; }
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (!deepT[j * w + i] && ((i > 0 && openT[j * w + i - 1]) || (i < w - 1 && openT[j * w + i + 1]) || (j < R.h - 1 && openT[(j + 1) * w + i]))) rimT[j * w + i] = 1;
  const out = (f, q, rim) => {
    if (q < 0 || q >= n) return true;
    if (deep[q]) return false;
    if (see.state[q] !== 1) return true;
    if (rim && !see.band[q] && rimT[Math.max(0, tileOf(q))]) return false;
    const ts = tileOf(q);                                    // (ground level with a floor: a tile's own top, not what shows of it a level down through its set-in edge)
    return see.band[f] || see.band[q] || see.lev[q] > see.lev[f] || ts < 0 || see.lev[q] < lvT[at(ts % w, ts / w | 0)];
  };
  // (line: the outline's px, xrayviews.js: every px of the place at its edge, seen through or not, and beside the
  // land's own rim too; not where its floor goes on level with the ground outside: "the line shouldn't show up at
  // intersections with same level", it closed a cave's doorway and both ends of a passage)
  const line = new Uint8Array(n);
  for (let f = 0; f < n; f++) if (deep[f]) {                  // 3: where the cut ends
    const x = f % W, side = x === 0 || x === W - 1;
    if (side || out(f, f - 1) || out(f, f + 1) || out(f, f + W) || out(f, f - W)) line[f] = 1;
    if (seen[f] && (side || out(f, f - 1, 1) || out(f, f + 1, 1) || out(f, f + W, 1) || out(f, f - W, 1))) { dist[f] = 0; todo.push(f); }
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
    const a = 1 - (1 - al[f]) * (1 - lip), own = fill[f] ? earth : wall.get(f);
    if (own) px[f] = pack(own.map((v, q) => v * (1 - a) + [30, 20, 28][q] * a), 1);
    else if (a) px[f] = pack([30, 20, 28], a);
  }
  return {px, cut: new Set(cuts.keys()), more, line: deep.includes(1) ? line : null};
}
