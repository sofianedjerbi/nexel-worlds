// The earth itself in the picture of the place seen through what hides it (xray.js: xrayPicture): what was cut
// through to show it, and where the cut ends. Seven things (4 to 7: where they are laid), a px each, laid over the land's own painting:
// 1. Earth left standing between two parts of the place, in front of a part open to the sky (a pit), is cut level
//    with the floor behind it, and shows as that: earth, cut. (The land as drawn showed there: a strip of meadow
//    between two floors four layers down.) Not in front of a part under a roof: there it is that room's back wall
//    (2), as high as the room, and what is over it is not cut (two tunnels side by side: the earth between them was
//    sliced level with their floors, a row nobody dug shown as gone).
// 2. Under a roof the wall behind the place goes up to the top of the room and no further: the hollow's own back
//    wall, its bands. The land over the room is not cut: it is there, and stays as it is drawn (a window the size of
//    what was dug).
// 3. Where the cut ends against the land beside it or in front of it, a line in the pack's ink and a shadow three px
//    in from it, in steps: a hole has an edge ("the borders are still abrupt, like cut without separation": dark
//    earth stopped square against the grass). Not where the land's own edge is (round a hole open to the sky: its
//    grass hangs there), nor where you can walk off a floor onto the ground beside it (a way out, a stair's top step).
// c: the picture's {W, h (px), w (tiles), R (its rect of tiles), y (its top, art px), see, seen, floor, floors, place,
// rocks, paint (its px as the land's painter left them)}. -> {px: what to lay over it, cut: the tiles of 1, more: the px it added to seen, line: the px of the
// outline round the place where it is under a roof, dug or cut, and of the edges in it nobody climbs (xrayviews.js; null: no
// such place, a hill in front and no more), deep: the place's own px, fronts: the tiles a floor's front is drawn on (4),
// also: the tiles drawn with their other room too, "x,y" -> its floors (6: who stands on one is in the place)}
const CUT = {ink: [112, 70, 58], lip: [.34, .22, .11], rim: 1.35};   // the edge's ink; its shadow, a px each; how much lighter a floor's brink is (7)
function xrayCut({W, h, w, R, y, see, seen, floor, floors, place, rocks, paint, ground, by, at: me}) {
  const n = W * h, px = new Uint32Array(n), fill = new Uint8Array(n), cuts = new Map(), earth = colsOf(hillSheet(0)).bands[1];
  let more = 0;
  for (let i = 0; i < w; i++) {                              // 1
    const x = R.x + i, under = (place.get(x) || []).filter((gy) => floors.get(x + "," + gy) < 0 || floor.has(x + "," + gy));
    for (let j = 0; under.length > 1 && j < R.h; j++) {
      const ty = R.y + j, north = under.filter((gy) => gy < ty), south = under.filter((gy) => gy > ty);
      if (!rocks[j * w + i] || !north.length || !south.length || floor.has(x + "," + Math.min(...south))) continue;   // (in front of a room under a roof it stands: that room's back wall, 2)
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
  const deep = new Uint8Array(n), own = new Int16Array(n), dist = new Uint8Array(n).fill(255), todo = [], wall = new Map();   // (own: the tile a px of the place is of, + 1)
  const roofT = new Uint8Array(w * R.h), band = (k, m) => colsOf(hillSheet(k)).bands[m <= 0 ? 0 : m >= 7 ? 2 : 1];
  for (const k of floor.keys()) { const [x, ty] = k.split(",").map(Number), i = x - R.x, j = ty - R.y; if (i >= 0 && i < w && j >= 0 && j < R.h) roofT[j * w + i] = 1; }
  const rows = (i, j) => { const f0 = lvOf(i, j), Y = (R.y + j) * 16 - y; return [Y, Y - shOf(Math.max(f0, lvOf(i, j - 1))), Y - shOf(f0)]; };   // (a tile's line at sea level, the top of the wall behind it, the top of its floor)
  // (a px of a wall cut through, f on row r: its band. Y: the line at sea level of the tile it stands behind, F: that tile's floor)
  const lay = (f, r, Y, F) => {
    const rr = r < Y + 6 ? r + 2 : r, k = Math.ceil((Y - rr) / 8), foot = k <= F || (r >= Y + 6 && r < Y + 8), lv = foot ? Math.max(F + 1, 0) : k;
    wall.set(f, foot ? band(lv, 3) : band(k, rr - (Y - shOf(k)))); if (!seen[f]) { seen[f] = 1; more++; } see.lev[f] = lv; see.band[f] = 1;
  };
  const r0T = new Int32Array(w * R.h), rcT = new Int32Array(w * R.h), lid = [], over = new Uint8Array(n), cols = new Map(), face = new Uint8Array(n), fronts = new Set();                                    // (a tile of the place -> its column in the picture: [px across, its wall's first row, the foot of its floor]: a light's reach, daylight.js)
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (deepT[j * w + i]) {
    const [Y, r0, top] = rows(i, j), t = j * w + i, roofed = roofT[t], F = lvOf(i, j);
    // (under a roof the wall behind stops at the top of the room, its first row rc: the land over the room is not
    // cut, it stays as it is drawn. It went up to the top of the land: one block dug under a mountain and its whole
    // column was gone from the picture, seventeen layers of rock that are still there, "im breaking only 1 bloc why
    // the whole column is deleted ??". The band of the room's top layer starts two px over its line above the sea)
    const c = roofed ? ceilAt(R.x + i, R.y + j, F) : 0, rc = roofed ? Math.min(top, Math.max(r0, Y - shOf(c) - (c >= 0 ? 2 : 0))) : r0;
    cols.set((R.x + i) + "," + (R.y + j), [i * 16, roofed ? rc : r0 - 3, top + 16]); r0T[t] = r0; rcT[t] = rc;
    for (let r = Math.max(0, r0 - 3); r < Math.min(h, top + 16); r++) for (let f = r * W + i * 16, e = f + 16; f < e; f++) {
      if (roofed && r >= r0 && r < rc) { lid.push(f); continue; }
      const back = roofed && r >= rc && r < top, put = fill[f] || see.state[f] === 1;   // (back: over the floor of a tile under a roof: the wall behind it, whatever was painted)
      if ((!put && !back) || (r < r0 && (roofed || see.band[f] !== 1))) continue;       // (over a tile's line: the set-in top of a wall the land painted, of a tile open to the sky; under a roof the cut starts on the line)
      if (put && !fill[f]) {                                 // (of what was painted there: the place's floors, and the wall behind this tile, its bands and
        const ts = tileOf(f), tf = tileOf(f, 4);            //  what shows between them of the tile behind, painted a level down; not land that stands in front
        if (see.band[f] === 1 ? tf !== t : see.band[f] === 0 && (ts < 0 || (!deepT[ts] && (ts !== t - w || see.lev[f] >= lvT[at(ts % w, ts / w | 0)])))) continue;   //  of it: its top, its wall. A ledge down the tile's side is of the place: the line is on the tile's edge, not two px in, "this border is weird")
      }
      deep[f] = 1; own[f] = t + 1;
      if (!back || fill[f]) continue;
      // (a wall cut through is its bands, a layer each, and no more, whatever the land's painter put there: a sliver
      // of grass through the set-in edge of a hill that steps down beside it, the end of a ledge that hung from the
      // roof's side. Laid as that painter lays the wall of a hole open to the sky: the bands over the sea's level
      // two px up, where a hill's edge is set in (so the first is two px short under a roof, which starts on the
      // tile's line), then two px of the foot of the tile behind before the first band under the sea's level, or
      // before the floor. They were all on the tiles' lines: two px out of step with the wall of a pit beside the
      // roof, every line of it broken where the roof starts, "still got a weird tileset jump")
      lay(f, r, Y, F);
    }
  }
  // (and beside a tile under a roof, the wall of one open to the sky: the four px of it next to that tile had the same
  // leftovers of the roof's side: they are the wall's own px from further in, row for row)
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (deepT[j * w + i] && !roofT[j * w + i]) for (const d of [-1, 1]) {
    if (i + d < 0 || i + d >= w || !roofT[j * w + i + d]) continue;
    const [, r0, top] = rows(i, j);
    for (let r = Math.max(0, r0 - 2, rcT[j * w + i + d]); r < Math.min(h, top); r++) for (let c = 0; c < 4; c++) {   // (as far up as that room goes: over it the land is whole, its side as it is drawn)
      const col = d < 0 ? c : 15 - c, f = r * W + i * 16 + col, src = r * W + i * 16 + (d < 0 ? 4 : 11);
      if (!deep[src] || fill[src] || see.band[src] === 2) continue;
      const v = wall.get(src) || [paint[src] & 255, paint[src] >> 8 & 255, paint[src] >> 16 & 255];
      wall.set(f, v); deep[f] = 1; own[f] = j * w + i + 1; if (!seen[f]) { seen[f] = 1; more++; } see.lev[f] = see.lev[src]; see.band[f] = see.band[src];
    }
  }
  // 4. A floor higher than the one beside it (east, west), rock in front of it: its front shows, down to that floor's
  // level, the layers it stands on (open onto that room or not: a tunnel three layers over the room beside it, rock
  // between the two, was drawn as the next tile of that room's floor, "i dont see how to go up, where to dig").
  // Height is how far up the screen a floor is drawn, and nothing else said it: a tunnel that goes down a layer a
  // tile was a strip of earth going up across the screen, the floor two layers over yours a tile on along it ("why
  // can't i go up ? why cant i climb right ?"; told in words it was "explicit guiding.. it should be intuitive,
  // visible"). A stair seen from its side has its steps' fronts.
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (deepT[j * w + i]) {
    const t = j * w + i, F = lvOf(i, j), beside = (d) => (i + d >= 0 && i + d < w && deepT[t + d] && lvOf(i + d, j) < F ? lvOf(i + d, j) : F);
    const low = Math.max(F - APART, Math.min(beside(-1), beside(1))), [Y, , top] = rows(i, j), end = Math.min(h, top + 16 + shOf(F) - shOf(low));
    // (...under what is seen of the floor's own foot: not where ground that is not cut stands in front of it, a step up out of a hole: the front lay on the meadow)
    const foot = top + 15 < 0 || top + 15 >= h ? -1 : (top + 15) * W + i * 16;
    for (let r = Math.max(0, top + 16); foot >= 0 && r < end; r++) for (let c = 0, f = r * W + i * 16; c < 16; c++, f++) if (!deep[f] && deep[foot + c] && own[foot + c] === t + 1 && !see.band[foot + c]) { deep[f] = 1; own[f] = t + 1; face[f] = 1; lay(f, r, Y + 16, low); }
    if (low < F && foot >= 0) { cols.get((R.x + i) + "," + (R.y + j))[2] = end; fronts.add((R.x + i) + "," + (R.y + j + 1)); }
  }
  // 5. The floor you stand on is seen, whatever of the place is drawn over it: a floor two layers or more over yours
  // and in front of it is drawn a tile further up the screen a pair of layers, on your own tile, on the wall behind
  // you (down a hole at the north end of a tunnel you stood on the tunnel's floor, to look at). Your tile's own px.
  const own0 = new Map(), t0 = (me[1] - R.y) * w + me[0] - R.x;
  if (me[0] >= R.x && me[0] < R.x + w && me[1] >= R.y && me[1] < R.y + R.h && deepT[t0]) {
    const i = t0 % w, j = t0 / w | 0, F = lvOf(i, j), [, , top] = rows(i, j);
    for (let r = Math.max(0, top); r < Math.min(h, top + 16); r++) for (let c = 0; c < 16; c++) {
      const f = r * W + i * 16 + c, u = own[f] - 1;
      if (!deep[f] || u < 0 || u === t0 || lvOf(u % w, u / w | 0) < F + 2) continue;
      own[f] = t0 + 1; face[f] = 0; wall.delete(f); see.band[f] = 0; see.lev[f] = F; own0.set(f, ground[(j * 16 + r - top) * W + i * 16 + c]);
    }
  }
  // 6. A tile with two rooms of the place, one over the other (xray.js xrayPlace: by): both are drawn, as the column
  // is, cut along its south side: the upper room's wall and floor, the front of the rock between the two, and under
  // it what shows of the lower room through its opening, a layer of it eight px (a room one layer high: the south
  // half of its floor). A tile was of the place at one height: a block dug out under a tunnel's floor and that tile
  // of the tunnel went from the picture, the new room in its place ("digged another block and topology changed !!
  // what the hell"). Not where the upper room would be drawn over a floor of another tile that you walk to from where
  // you stand, a step or a drop at a time (a room north of the two): that floor is seen, the upper room is not.
  const xl = new Int16Array(n).fill(-9999), also = new Map(), k0 = me.join(), went = new Set([k0 + "," + floors.get(k0)]), go = [[me[0], me[1], floors.get(k0)]];
  while (go.length) {
    const [x, ty, lv] = go.pop();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const k = (x + dx) + "," + (ty + dy), z = floors.has(k) ? landAt(lv, x + dx, ty + dy, x, ty) : null; if (z !== null && !went.has(k + "," + z)) { went.add(k + "," + z); go.push([x + dx, ty + dy, z]); } }
  }
  const walked = (t) => went.has((R.x + t % w) + "," + (R.y + (t / w | 0)) + "," + lvOf(t % w, t / w | 0));
  const put = (f, t, lv, c) => {                            // (a px of a tile's other room: its level; c: a floor's px, none: a wall's, laid)
    deep[f] = 1; own[f] = t + 1; xl[f] = lv; face[f] = 0;
    if (c !== undefined) { own0.set(f, c); wall.delete(f); see.band[f] = 0; see.lev[f] = lv; if (!seen[f]) { seen[f] = 1; more++; } }
  };
  for (const [k, hs] of by) {
    const [x, ty] = k.split(",").map(Number), i = x - R.x, j = ty - R.y, t = j * w + i;
    if (i < 0 || i >= w || j < 0 || j >= R.h || !roofT[t]) continue;
    const F = lvOf(i, j), Y = (R.y + j) * 16 - y, gpx = (r, top, c) => ground[(j * 16 + r - top) * W + i * 16 + c];
    const up = Math.min(...hs.filter((v) => v > F && coveredAt(x, ty, v))), dn = Math.max(...hs.filter((v) => v < F));   // (the room over this one, the room under it)
    if (up < Infinity) {
      const c1 = ceilAt(x, ty, F), c2 = ceilAt(x, ty, up), a = Math.max(0, Y - shOf(c2) - (c2 >= 0 ? 2 : 0)), b = Y - shOf(up), d = Math.min(h, Y + 16 - shOf(c1));
      let free = true;
      for (let r = a; r < d && free; r++) for (let c = 0, f = r * W + i * 16; c < 16; c++, f++) if (deep[f] && own[f] !== t + 1 && !see.band[f] && walked(own[f] - 1)) { free = false; break; }
      for (let r = a; free && r < d; r++) for (let c = 0, f = r * W + i * 16; c < 16; c++, f++) {
        if (r >= b && r < b + 16) put(f, t, up, gpx(r, b, c)); else { lay(f, r, r < b ? Y : Y + 16, r < b ? up : c1); put(f, t, up); }
      }
      if (free) { cols.get(k)[1] = Math.min(cols.get(k)[1], a); also.set(k, [up]); }
    }
    if (dn > -Infinity) {
      const c1 = ceilAt(x, ty, dn), top = Y - shOf(F), foot = top + 15 < 0 || top + 15 >= h ? -1 : (top + 15) * W + i * 16, d = Y + 16 - shOf(c1), e = Math.min(h, Y + 16 - shOf(dn)), t1 = Y - shOf(dn);
      for (let r = Math.max(0, top + 16); foot >= 0 && r < e; r++) for (let c = 0, f = r * W + i * 16; c < 16; c++, f++) {
        const o = own[f] - 1;
        if (!(deep[foot + c] && own[foot + c] === t + 1 && !see.band[foot + c]) || (deep[f] && !(o === t ? face[f] : (o / w | 0) < j))) continue;   // (under the floor's own foot, where it is seen; over what is behind it, not over what stands in front)
        if (r >= d && r >= t1) put(f, t, dn, gpx(r, t1, c)); else { lay(f, r, r < d ? Y + 16 : Y, r < d ? c1 : dn); put(f, t, r < d ? F : dn); }
      }
      if (foot >= 0) { cols.get(k)[2] = Math.max(cols.get(k)[2], e); fronts.add(x + "," + (ty + 1)); also.set(k, [...(also.get(k) || []), dn]); }
    }
  }
  for (const f of lid) if (!deep[f]) { over[f] = 1; if (seen[f]) { seen[f] = 0; more--; } }   // (the land over a room: as it is drawn, unless another tile of the place is seen there)
  // (q: beside f, over it or under it: not of the place; and not the land's own edge, the top of a tile beside or
  // behind a part of the place that is open to the sky, which has its rim or its grass there...)
  const rimT = new Uint8Array(w * R.h), openT = new Uint8Array(w * R.h);
  for (const [k, lv] of floors) if (lv < 0 && !floor.has(k)) { const [x, ty] = k.split(",").map(Number), i = x - R.x, j = ty - R.y; if (i >= 0 && i < w && j >= 0 && j < R.h) openT[j * w + i] = 1; }
  for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) if (!deepT[j * w + i] && ((i > 0 && openT[j * w + i - 1]) || (i < w - 1 && openT[j * w + i + 1]) || (j < R.h - 1 && openT[(j + 1) * w + i]))) rimT[j * w + i] = 1;
  // ...nor, for a floor, where you can walk off it that way, onto the tile beside it: level with it, a step up, a drop
  // ("there shouldn't be a line where player can travel to outside (outside notion isn't really to be taken as
  // it..)": a stair's top step was lined off from the meadow it is stepped onto from; first the rule was ground on
  // the same level, which closed a cave's doorway until it was there)
  const walk = new Int8Array(w * R.h * 4).fill(-1);
  const out = (f, q, d, dx, dy) => {
    if (q < 0 || q >= n) return true;
    if (deep[q]) return false;
    const t = own[f] - 1, i = t % w, j = t / w | 0, ti = i + dx, tj = j + dy;
    // (the land's own rim: behind this tile; beside it, as far down as that tile's top is drawn; and whatever tile's top q is)
    if (t >= 0 && dy <= 0 && ti >= 0 && ti < w && tj >= 0 && rimT[tj * w + ti] && (dy < 0 || (f / W | 0) < (R.y + tj) * 16 - y - shOf(lvT[at(ti, tj)]) + 16)) return false;
    if (see.state[q] === 1 && !see.band[q] && rimT[Math.max(0, tileOf(q))]) return false;
    if (over[q] && t >= 0 && !roofT[t]) return false;         // (nor beside a part open to the sky where the land over a room starts: it is drawn there with its own rim toward the hole)
    if (dx && t >= 0 && xl[f] === -9999 && (f / W | 0) < r0T[t]) return false;    // (nor down the side of a wall's top where it is set in over its tile's line, two px: beside a roof they were two px of ink up into the pit's rim)
    if (see.band[f] || fill[f] || t < 0) return true;         // (a wall, earth that was cut: no way through)
    if (see.state[q] === 1 && !see.band[q]) {                // (the ground beside it is of a tile a row on from the one stepped onto that way: the tile in
      const tq = tileOf(q);                                   //  front of this one, whose edge hangs over the floor: the way out is that way; any other: ground
      if ((tq / w | 0) > j + dy) { if (tq !== t + w) return true; d = 2; dx = 0; dy = 1; }   //  that stands in front, and the cut goes through it)
    }
    if (xl[f] > -9999) return landAt(xl[f], R.x + i + dx, R.y + j + dy, R.x + i, R.y + j) === null;   // (of a tile's other room: from its own floor)
    if (walk[t * 4 + d] < 0) walk[t * 4 + d] = landAt(lvOf(i, j), R.x + i + dx, R.y + j + dy, R.x + i, R.y + j) === null ? 0 : 1;
    return !walk[t * 4 + d];
  };
  // (line: the outline's px, xrayviews.js: the same edge, of every px of the place, seen through or not. One edge:
  // the land's own rim where it has one, round a hole open to the sky, the line elsewhere; it ran under that rim too,
  // along its curved foot, "upper is weird here")
  // (...and inside the place, the edge of a floor, or of its front, two layers or more over the floor beside it or
  // in front of it: nobody climbs that. A line is where you do not pass)
  const lvs = new Int16Array(w * R.h + 1).fill(-9999); for (let t = 0; t < w * R.h; t++) if (deepT[t]) lvs[t + 1] = lvOf(t % w, t / w | 0);
  const lvP = (f) => (xl[f] > -9999 ? xl[f] : lvs[own[f]]);                           // (a px of the place: its tile's level; past the picture's ends deep is not set)
  // (shut: of a floor and a lower floor of the place beside it, in front of it or behind it: 0 you climb from that one onto this
  // one, as the world has it, cells.js landAt; 1 it is too high; 2 no way between them at all, the lower room stops
  // under this floor: a step of one layer is not climbed from a room one layer high, a jump needs room over your head,
  // and the picture showed the step, as from the room beside it that is three high: "why i can't go up bu i cna climb
  // from the left ?")
  const shut = new Int8Array(w * R.h * 4).fill(-1);
  const edge = (lv, t, q, other) => {                       // (other: f or q is of a tile's other room, 6: asked each time, by its own level)
    if (!deep[q]) return 0;
    const u = own[q] - 1, d = lv - lvP(q), k = u === t - 1 ? 0 : u === t + 1 ? 1 : u === t + w ? 2 : u === t - w ? 3 : -1;
    if (u === t || d < 1 || k < 0) return d > 1 && u !== t ? 1 : 0;      // (not beside each other, drawn side by side: two layers and more)
    const way = () => { const ux = R.x + u % w, uy = R.y + (u / w | 0); return landAt(lv - d, R.x + t % w, R.y + (t / w | 0), ux, uy) === lv ? 0 : ceilAt(ux, uy, lv - d) > lv ? 1 : 2; };
    if (other || xl[q] > -9999) return way();
    if (shut[t * 4 + k] < 0) shut[t * 4 + k] = way();
    return shut[t * 4 + k];
  };
  const ledge = (f) => { if (see.band[f] && !face[f]) return 0; const t = own[f] - 1, lv = lvP(f), o = xl[f] > -9999; return Math.max(edge(lv, t, f - 1, o), edge(lv, t, f + 1, o), edge(lv, t, f + W, o), edge(lv, t, f - W, o)); };
  const line = new Uint8Array(n), high = new Int16Array(n).fill(-9999);   // (high: of a px in the shadow of such an edge, the level it is the edge of: its shadow falls on what is lower, the foot of it, not on the floor it is the edge of)
  for (let f = 0; f < n; f++) if (deep[f]) {                  // 3: where the cut ends
    const x = f % W;
    if (x === 0 || x === W - 1 || out(f, f - 1, 0, -1, 0) || out(f, f + 1, 1, 1, 0) || out(f, f + W, 2, 0, 1) || out(f, f - W, 3, 0, -1)) { line[f] = 1; if (seen[f]) { dist[f] = 0; todo.push(f); } }
    else { const e = ledge(f); if (e) { line[f] = 1; if (e === 1) high[f] = lvP(f); if (seen[f]) { dist[f] = 0; todo.push(f); } } }   // (too high: its shadow on the lower floor; no way at all: the edge of two holes, as where the cut ends)
  }
  for (let i = 0; i < todo.length; i++) {                    // (and in from it, a step a px)
    const f = todo[i], d = dist[f] + 1, x = f % W;
    if (d > CUT.lip.length) continue;
    for (const q of [x ? f - 1 : -1, x < W - 1 ? f + 1 : -1, f - W, f + W]) if (q >= 0 && q < n && seen[q] && deep[q] && dist[q] > d && (high[f] === -9999 || lvP(q) < high[f])) { dist[q] = d; high[q] = high[f]; todo.push(q); }
  }
  // 7. Under a roof the brink of a floor is lit, a px of it: where it drops to its own front or to the wall of the
  // room south of it, and down its side where the floor of the tile beside it is lower. A stair is seen as steps, a
  // ledge as a ledge (of six pictures of his cave on the mockup page he took this one: "go with 4"). Not where the
  // line is (an edge nobody climbs: xrayviews.js), nor on land open to the sky, which is drawn as it is.
  const brink = (f) => {                                    // (f: a px of a floor of the place)
    const t = own[f], q = f + W, x = f % W;
    if (!roofT[t - 1]) return false;
    if (q < n && see.band[q] && deep[q] && (own[q] === t || own[q] === t + w)) return true;
    return (x > 0 && own[f - 1] === t - 1 && deep[f - 1] && lvP(f - 1) < lvP(f)) || (x < W - 1 && own[f + 1] === t + 1 && deep[f + 1] && lvP(f + 1) < lvP(f));
  };
  const pack = (c, a) => (Math.round(a * 255) << 24 | Math.round(c[2]) << 16 | Math.round(c[1]) << 8 | Math.round(c[0])) >>> 0;
  for (let f = 0; f < n; f++) {
    if (!deep[f]) continue;                                   // (all that is laid is of the place: two look-ups a px for the rest of the picture, three quarters of it)
    if (dist[f] === 0) { px[f] = pack(CUT.ink, 1); continue; }
    const lip = dist[f] <= CUT.lip.length ? CUT.lip[dist[f] - 1] : 0;
    const c0 = own0.get(f); let own = fill[f] ? earth : c0 !== undefined ? [c0 & 255, c0 >> 8 & 255, c0 >> 16 & 255] : wall.get(f);
    if (!see.band[f] && !fill[f] && paint[f] >>> 24 && brink(f)) own = (own || [paint[f] & 255, paint[f] >> 8 & 255, paint[f] >> 16 & 255]).map((v) => Math.min(255, v * CUT.rim));
    if (own) px[f] = pack(own.map((v, q) => v * (1 - lip) + [30, 20, 28][q] * lip), 1);
    else if (lip) px[f] = pack([30, 20, 28], lip);
  }
  return {px, cut: new Set(cuts.keys()), more, line: deep.includes(1) ? line : null, deep, cols, fronts, also};
}
