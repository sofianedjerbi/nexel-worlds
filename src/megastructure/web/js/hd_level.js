// The HD look (hd.js): WHERE YOU ARE, as its picture has it. Three answers, each from the land's own shape and the height the game keeps for you (caves.js `myAt`, as the server does):
//   track(p, now), once a frame (hd.js after) -> HdLevel.place: where YOUR BODY is, {tx, ty: the column it is drawn in (BodyPlace.of: on a ladder's rungs, over its foot: dx, dy), L, Lf: its level (of)},
//     and HdLevel.cover = cover(place): THE LAND OVER IT, from the cells alone {top, dep: levels of land over L, roof: any (there, and only there, is the x-ray window), rim}. All that asks where you are and what is over you
//     reads these two: the light and your lantern, the x-ray window (hd.js), your room (hd_things.js), the veil over floors (floors.js), your footsteps (characters.js). A ladder is a height in it. (Each asked on its own,
//     from the tile you were rounded to: half way up a ladder that was the cliff's, "under a roof": the window opened)
//   of(p, now, cl) -> [L, Lf]: the level you stand at (your tile's), and the same between two tiles: on the straight line between their heights (the game's own line, relief.js liftOf: a hop is an arc over it).
//   over(x, y, L, k) -> LEVELS OF LAND OVER THE EYE'S LINE to the feet of somebody on (x, y) at L (k: levels the line climbs a tile south, relief.js eyeRise): 0: seen through the open air (or a cave's mouth);
//     .5: half a body hidden; 1 or more: all of it (a level is a body's height) (99: the line runs into a ceiling, or into anything when a roof is over the feet: nothing of a body shows). A block somebody put (a wall you built) is not land. EVERY question of "does land hide this" is asked here (they were three: hd.js `hidden`, the land search's own, the tilt's walls).
//   hides(tx, ty, L, k, px) -> land under the open sky between the eye and you hides you whole: the x-ray window opens on your space as under a roof (hd.js). (It was `lift`: you drawn up at the rim south of you)
//   own(place, roof, cov) -> the boxes of the x-ray window that are yours whatever the search for your space has found yet: your tile, floor to ceiling, and the covered tiles you just came from (vox_style.js adds the ones its window lacks)
const HdLevel = (() => {
  // WHERE IN ITS TILE A DRAWN THING'S FOOT IS, tiles from the tile's corner [east, south]: its place in the picture, and so what it stands in front of (the frame's one order: hd.js byY, north to south,
  // and the land's depth). ONE table for all that is drawn in the land. (Each was a number typed where the thing was put in the frame's list: .5, .7, .42, .08, .12, .9, .45, .3, 1.)
  //   body: its tile's middle; shade, pileShade: the shadow under a body, under a pile; pile: what lies on the ground; ladder: by what it leans on (north, south, beside);
  //   stood: what stands at its tile's south edge (a falling tree, a plucked plant, a flame); chip, puff: a little over the ground where they came out
  const DRAW_AT = {body: [.5, .5], shade: [0, .42], pileShade: [0, .08], pile: [.5, .7], ladderN: [.5, .12], ladderS: [.5, .9], ladder: [.5, .5], stood: [.5, 1], chip: [0, .45], puff: [0, .3]};
  const foot = (kind, x, y) => [x + DRAW_AT[kind][0], y + DRAW_AT[kind][1]];
  const col = (x, y) => Voxels.host.column(x, y), topAt = (x, y) => { const c = col(x, y); return c && c.length ? c[c.length - 1] : 0; };
  const solid = (c, z) => { if (!c) return false; for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  let trail = [], place = null, cov = null;
  // (yours: the level you are drawn from goes a px a frame at the most through a jump and after it: leap.js cam. In the air, the level the view takes you at is where your feet are, to the nearest level,
  // not the ground under you: sprint-jumping south up a hill the step ahead, a level over the ground you left, stood between the eye and that ground: the eye tilted up as if under the land. Your shadow keeps the ground: leap.js level)
  function track(p, now) {   // (p.free: the first screen's eye, nobody's body)
    const b = !p.free && BodyPlace.of(p), [L, Lf] = p.free ? [p.z, p.z] : of(p, now);
    place = {tx: b ? b.tx : Math.round(p.x), ty: b ? b.ty : Math.round(p.y), L, Lf, free: !!p.free}; cov = p.free ? {top: L, dep: 0, roof: false, rim: rim(place.tx, place.ty, L)} : cover(place); return place;
  }
  function cover({tx, ty, L}) { const top = topAt(tx, ty); return {top, dep: Math.max(0, top - L), roof: top > L, rim: rim(tx, ty, L)}; }
  function of(p, now) { const r = of0(p, now); if (!(p.e && p.e.kind === "agent" && p.e.id === myId)) return r; const a = Leap.state; return [a ? Math.max(r[0], Math.floor(a.z + .5)) : r[0], Leap.cam(r[1], now)]; }
  function of0(p, now) {
    const H0 = Voxels.host, rx = Math.round(p.x), ry = Math.round(p.y), near = typeof myAt !== "undefined" && myAt && Math.abs(myAt.x - rx) + Math.abs(myAt.y - ry) <= 2;
    const at = (x, y) => { const t = topAt(x, y), s = near ? Floors.standOf(p, x, y) : t; return s >= t && H0.water && H0.water(x, y) && H0.waterTop ? Math.max(s, H0.waterTop(x, y)) : s; };   // (in water: at its face)
    const pl = BodyPlace.of(p), cl = pl.climb; if (cl) return [Math.floor(cl.h), cl.h];   // (on a ladder's rungs: as high as you have climbed)
    const lp = p.e && p.e.id === myId && p.e.kind === "agent" ? Leap.level() : null; if (lp) return lp;   // (in the air: drawn from the level you left, the ground under you yours: leap.js)
    const lz = p.leapAt ? Leap.landedOn(p) : null; if (lz !== null) return [lz, lz];   // (come down from a jump off a tile's middle: on that tile)
    const L = at(rx, ry), ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y); if ((ax === bx && ay === by) || pl.fall) return [L, L];
    const la = at(ax, ay), lb = at(bx, by), f = ax === bx ? p.y - ay : p.x - ax;
    const fw = mineWalking(p) && DIRV[walking.dir][0] + DIRV[walking.dir][1] > 0;
    if (mineWalking(p) && (fw ? lb > la && Leap.leapable(ax, ay, la, bx, by) : la > lb && Leap.leapable(bx, by, lb, ax, ay))) return [L, Math.min(la, lb)];   // (yours, walking up to a step: your own level until you jump up it, leap.js)
    return [L, Math.abs(la - lb) >= FALL.from ? L : la + (lb - la) * f];   // (a fall: the eye and the body have their own way down, hd.js)
  }
  function over(x, y, L, k, n = 20) { let m = 0; for (let d = 1; d <= n; d++) { const c = col(x, y + d), e = L + (d - .5) * k; if (!c || !c.length || matAt(x, y + d)) continue; for (let i = 0; i < c.length; i += 2) if (c[i] > e && (i ? c[i - 1] : -1e9) < e + k) m = Math.max(m, i && c[i - 1] > e ? 99 : c[i] - e); } return m > 0 && topAt(x, y) > L ? 99 : m; }
  function own({tx, ty, L}, roof, cov) {
    if (!cov) { trail = []; return trail; }
    const c = col(tx, ty); let hi = L + 1; if (roof) while (hi < L + 6 && !solid(c, hi + 1)) hi++;
    const b = roof ? [tx, ty, L, hi] : [tx, ty, L, L + 1, 1], l = trail[trail.length - 1]; if (l && l[0] === tx && l[1] === ty && l[2] === L) return trail;
    trail = trail.filter((t) => t.length < 5 && (t[0] !== tx || t[1] !== ty) && Math.abs(t[0] - tx) + Math.abs(t[1] - ty) <= 3).slice(-3).concat([b]); return trail;   // (behind you: only what was under a roof; under the open sky the land there is as it is)
  }
  const rim = (tx, ty, L) => Math.max(L, topAt(tx, ty), topAt(tx + 1, ty), topAt(tx - 1, ty), topAt(tx, ty - 1), topAt(tx, ty + 1));   // (the level of the land round your hole: its rim)
  // hides(tx, ty, L, k, px) -> the land south of you over the eye's line (k: its climb a tile) hides all of you that shows (a body is a level; px: art px of it under your feet's line, a swimmer's sink): the x-ray window (hd.js).
  // ONE answer for any wall between the eye and you under the open sky: a shaft's south wall, a gorge's bank, a cliff over a river. (You were LIFTED to the rim south of you instead: in a river at a cliff 12 high, drawn on its top edge)
  const hides = (tx, ty, L, k, px = 0, part = 1) => over(tx, ty, L, k) >= part - px / 16;   // (part: how much of you hidden is enough: all of you, or a quarter where the eye looks down no steeper, hd.js PART)
  // veils(x, y, L, at) -> land south of (x, y) hides ANY of its floor at L, AS DRAWN (at(x, y, z): the picture's px of a place, hd.js eng.at: the eye's own perspective and the bend): the north edge of a top over
  // L + 1 is higher on the screen than the floor's south edge. Such a tile of your space is in the window (hd.js host.sunk). (It was hides, whole, by the eye's mean climb: a tile the cliff's top covered
  // in part stayed out, and that part of the cliff's top stood in the window, its dark rim over the river: "an outline floating in the water", the river shown again past it)
  // ANY land south of the floor, the columns beside its own too (the back corners south-west and south-east: a plateau's corner leans over the floor beside it as the eye sees it): its top's box on the
  // screen over the floor's box. (It was straight south alone: the plateau's top-left corner block stood over the west end of doben1's strip, "x-ray should also apply to left/right back corners")
  const box = (at, x, y, z) => { let b = null; for (const [i, j] of [[0, 0], [1, 0], [0, 1], [1, 1]]) { const p = at(x + i, y + j, z); if (!p) return null; b = b ? [Math.min(b[0], p[0]), Math.min(b[1], p[1]), Math.max(b[2], p[0]), Math.max(b[3], p[1])] : [p[0], p[1], p[0], p[1]]; } return b; };
  // The columns asked: two each way, and on the side away from the eye's middle as far as a top that tall LEANS as the eye sees it (lw: tiles a level, sideways; the eye's perspective: a cliff
  // 13 high ten tiles west of you leans three tiles further west. It was two tiles each way: the gorge's south bank, its corner three tiles east of the river it hid, stood in the window: a half-faded grey block in the river)
  function veils(x, y, L, at) { const f = box(at, x, y, L), a = at(x, y, L), b = at(x, y, L + 1), c = at(x + 1, y, L); if (!f || !b || !c) return false;
    const lw = (b[0] - a[0]) / Math.max(1e-6, c[0] - a[0]);   // (< 0: tops lean west here, the columns east of the floor lean onto it)
    for (let d = 1; d <= 20; d++) for (let i = -12; i <= 12; i++) { if (Math.abs(i) > 2 && (i * lw > 0 || Math.abs(i) > 2 + Math.abs(lw) * (topAt(x + i, y + d) - L))) continue;
      const t = topAt(x + i, y + d); if (t > L + 1 && !matAt(x + i, y + d)) { const q = box(at, x + i, y + d, t); if (q && q[1] < f[3] - .5 && q[2] > f[0] + .5 && q[0] < f[2] - .5) return true; } } return false; }
  // THE WALL BETWEEN THE EYE AND YOU: wall(x, y, z, s) -> the face a cell (z: its top) of the land south of you is drawn on, or null (drawn where it is). Seen from above (s.top: the eye looks down
  // into your hole, room or shaft;), a cell over your feet in the land south of you is in a wall whose face turned to you faces away from the eye: its own place projects onto
  // the grass south of the rim (a shaft 3 deep: R's "Dig a step" box lay outside the hole; a room 4 deep: the way's block and its key on the meadow: seen from above).
  // {y: the row of that wall (the first land south of you as high as the cell), T: its top}. wallAt: a place of such a cell, drawn on that face as you see it, stood in the opening on its top
  // edge: its foot (your floor's level) on that edge, each level up a step north into the opening (at most the eye's own cot 68°, all of the wall's height inside one tile); its depth into the wall: none.
  // (It was folded down from that edge, its foot farthest north: in a room the block at your floor's level lay on your body, cut away whole)
  // A cell at or under your feet south of you whose top that wall hides from the eye (the floor at its foot: X's box on it lay on the grass) is on the same face, under the wall's foot: B, the face's foot
  function wall(x, y, z, s) {
    if (!s || !s.top || y <= s.ty) return null;
    if (z > s.L) { for (let j = s.ty + 1; j <= y; j++) { const T = topAt(x, j); if (T >= z) return j === y && T > z ? {y: j, T, B: s.L} : null; } return null; }   // (only a cell IN that wall, land over it: one past it is nearer the eye, and a wall's top cell is seen, both drawn where they are. The build cursor on the plateau round a 1-deep dip was folded onto the dip's rim: a squashed box by your feet, nothing where you pointed)
    for (let j = y + 1; j <= y + 3; j++) { const T = topAt(x, j); if (T > z && T - z > (j - y - 1) * (s.ks || 2.5)) return {y: j, T, B: z - 1}; }   // (ks: levels the eye's line climbs a tile)
    return null;
  }
  const wallAt = (x, y, z, s, f) => { const d = Math.max(1, f.T - f.B); return [x, f.y - Math.max(0, Math.min(d, z - f.B)) * Math.min(.4, 1 / d), f.T]; };
  // cut(g, me, a, zs): nothing drawn on g after it (till g.restore) lies on your body: its own px are cut out of the marks (me: your sprite {canvas, fx, fy}, a: its foot on g, zs: g's units an art px). A box at your tile covered all of you
  // body(me, a, zs) -> your sprite's box on g ({x, y, w, h}: the bounds of its own px): no key's box is drawn in it, and one it covers most of is not drawn at all (target.js: it framed your head)
  const runs = new WeakMap(), poses = new Map();
  function runsOf(c) {   // (a sprite's own px: runs of a row [x, y, n, ...], and their bounds b [x0, y0, x1, y1])
    if (!c || !c.width) return null; let r = runs.get(c); if (r && r.v === c._v) return r;
    const pk = c._h === undefined ? null : c.width + "x" + c.height + ":" + c._h, kept = pk && poses.get(pk);   // (a picture made by the same calls as one read before (canvas._h, hd.js): the same px. A walk's eight poses were read back from the canvas at every change: an eighth of a phone's sprint)
    if (kept) { runs.set(c, r = {v: c._v, l: kept.l, b: kept.b}); return r; }
    const w = c.width, d = c.getContext("2d", {willReadFrequently: true}).getImageData(0, 0, w, c.height).data, l = [], b = [1e9, 1e9, -1, -1];
    for (let j = 0; j < c.height; j++) { let i0 = -1; for (let i = 0; i <= w; i++) { const on = i < w && d[(j * w + i) * 4 + 3] >= 128; if (on && i0 < 0) i0 = i; else if (!on && i0 >= 0) { l.push(i0, j, i - i0); b[0] = Math.min(b[0], i0); b[1] = Math.min(b[1], j); b[2] = Math.max(b[2], i); b[3] = Math.max(b[3], j + 1); i0 = -1; } } }
    runs.set(c, r = {v: c._v, l, b: b[2] >= 0 ? b : null}); if (pk) { if (poses.size > 400) poses.clear(); poses.set(pk, r); } return r;
  }
  function cut(g, me, a, zs) {
    const r = me && a && runsOf(me.canvas); if (!r) return;
    const x0 = Math.round(a[0] / zs) - me.fx, y0 = Math.round(a[1] / zs) - me.fy; g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); for (let i = 0; i < r.l.length; i += 3) g.rect((x0 + r.l[i]) * zs, (y0 + r.l[i + 1]) * zs, r.l[i + 2] * zs, zs); g.clip("evenodd");
  }
  const body = (me, a, zs) => { const r = me && a && runsOf(me.canvas); if (!r || !r.b) return null; const x0 = Math.round(a[0] / zs) - me.fx, y0 = Math.round(a[1] / zs) - me.fy; return {x: (x0 + r.b[0]) * zs, y: (y0 + r.b[1]) * zs, w: (r.b[2] - r.b[0]) * zs, h: (r.b[3] - r.b[1]) * zs}; };
  // behind(x, y, Z0, k) -> is a body on (x, y) at level Z0 hidden to its head by what stands south of it, as the eye sees it: the land, and what is built (a house's walls and roof, HdThings' boxes, levels over the tile's floor)?
  // (bubbles.js: what someone says is not hung over a roof they are behind. Heights kept half a second: a tile's boxes are not made again each frame)
  const tall = new Map(); let tallAt = 0;
  const standing = (x, y) => { const key = x + "," + y; let t = tall.get(key); if (t === undefined) { t = topAt(x, y); for (const b of HdThings.at(x, y) || []) t = Math.max(t, floorAt(x, y) + (b.z + (b.h || 0)) / RELIEF_STEP); tall.set(key, t); } return t; };
  function behind(x, y, Z0, k) {   // (k: levels the eye's line climbs a tile)
    if (performance.now() - tallAt > 500) { tall.clear(); tallAt = performance.now(); }
    const z = Z0 + 1, x0 = Math.floor(x), y0 = Math.floor(y);
    for (let d = 1; d <= 8; d++) if (standing(x0, y0 + d) > z + (y0 + d - y) * k) return true;
    return false;
  }
  // covered(list, at) -> something that STANDS south of you (a tree, a bush, a rock: the frame's list, hd.js; at: the camera's art px of a place) covers your body on the screen: its own px' box over
  // a quarter of your body's or more. Then you show through what is in front of you, one px in two (hd.js hid). (It was "anything standing within two rows south and a column each side": a flower
  // at your feet made you show through the land in front, a wide crown three tiles off that covered you did not)
  function covered(list, at) {
    const me = list.find((s) => s.top), a = me && at(me.x, me.y, me.z), B = a && body(me, [Math.round(a[0]), Math.round(a[1])], 1); if (!B) return false;
    for (const s of list) { if (s.tx === undefined || s.lie || !(s.y > me.y)) continue; const p = at(s.x, s.y, s.z), r = p && runsOf(s.canvas); if (!r || !r.b) continue;
      const x0 = Math.round(p[0]) - s.fx + r.b[0], y0 = Math.round(p[1]) - s.fy + r.b[1], w = Math.min(x0 + r.b[2] - r.b[0], B.x + B.w) - Math.max(x0, B.x), h = Math.min(y0 + r.b[3] - r.b[1], B.y + B.h) - Math.max(y0, B.y);
      if (w > 0 && h > 0 && w * h >= .25 * B.w * B.h) return true; }
    return false;
  }
  return {track, foot, DRAW_AT, own, over, hides, behind, covered, veils, wall, wallAt, cut, body, get place() { return place; }, get cover() { return cov; }, coverOf: cover};
})();
