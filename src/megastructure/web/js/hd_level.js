// The HD look (hd.js): WHERE YOU ARE, as its picture has it. Three answers, each from the land's own shape and the height the game keeps for you (caves.js `myAt`, as the server does):
//   of(p, now)  -> [L, Lf]: the level you stand at (your tile's), and the same between two tiles: on the straight line between their heights (the game's own line, relief.js liftOf: a hop is an arc over it).
//     (L was the land's TOP unless the classic x-ray had opened (xray.a): that one never opens during a hop, and a stair is hop after hop: all the way down a covered stair you were drawn on the grass over it, the window shut,
//      "the game thinks the player is still out". And your body went a whole level at each tile's middle: 16 px down the screen and back, every step of a stair.)
//   over(x, y, L, k) -> LEVELS OF LAND OVER THE EYE'S LINE to the feet of somebody on (x, y) at L (k: levels the line climbs a tile south, relief.js eyeRise): 0: seen through the open air (or a cave's mouth);
//     .5: half a body hidden; 1 or more: all of it (a level is a body's height) (99: the line runs into a ceiling, or into anything when a roof is over the feet: nothing of a body shows). A block somebody put (a wall you built) is not land. EVERY question of "does land hide this" is asked here (they were three: hd.js `hidden`, the land search's own, the tilt's walls).
//   under(x, y, L) -> a roof over it (land over its floor): there, and only there, the x-ray window is. Under the open sky nothing is cut: from above a hole's own south wall hides what is
//     behind it and its floor lies inside its rim (the window under the sky cut that wall away and drew the floor where it projects, south of the rim: "a drawer pulled out onto the grass"; a veil
//     of the meadow laid over it did not mend it). Behind land you show through it one px in two (vox_style.js).
//   steep(tx, ty, L, ver) -> is the eye to look from above (hd.js api.steep). ONE rule for every hole, pit, stair, trench, shaft, room, cave, tunnel: your feet a level (your height) or more under the
//     land round you: ten of sixteen ways out from you (straight lines, 6 tiles long) run into land a level over L. A room of any width up to twelve, a gorge, a shaft alike; a wall or two beside you on the surface is not "round you".
//     (It was "no tile of your floor shows from the side": a pit you fell into stayed side-on, a 3-wide stair tipped at its floor only. The land's shape, not a clock: hd.js holds 300 ms.)
//   lift(tx, ty, L, pitch) -> levels your body is drawn higher in a hole seen from above (hd.js, times the tilt): the land of the tile just south of you over the eye's line to your feet (0..the rim): your feet on
//     that rim's line, the rim cutting you. (Behind it you were one px in two on the meadow south of a shaft or a 1-wide stair: no pitch below 90 puts a deep 1x1 floor inside its rim. Not the floor: only you.)
//   own(tx, ty, L, cov) -> the boxes of the x-ray window that are yours whatever the search for your space has found yet: your tile, floor to ceiling, and the covered tiles you just came from (vox_style.js adds the ones its window lacks)
const HdLevel = (() => {
  const col = (x, y) => Voxels.host.column(x, y), topAt = (x, y) => { const c = col(x, y); return c && c.length ? c[c.length - 1] : 0; };
  const solid = (c, z) => { if (!c) return false; for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  let trail = [];
  function of(p, now) {
    const H0 = Voxels.host, rx = Math.round(p.x), ry = Math.round(p.y), near = typeof myAt !== "undefined" && myAt && Math.abs(myAt.x - rx) + Math.abs(myAt.y - ry) <= 2;
    const at = (x, y) => { const t = topAt(x, y), s = near ? Floors.standOf(p, x, y) : t; return s >= t && H0.water && H0.water(x, y) && H0.waterTop ? Math.max(s, H0.waterTop(x, y)) : s; };   // (in water: at its face)
    const cl = Climb.climbOf(p); if (cl) return [Math.floor(cl.h), cl.h];   // (on a ladder's rungs: as high as you have climbed)
    const L = at(rx, ry), ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y); if ((ax === bx && ay === by) || falling(p, now)) return [L, L];
    const la = at(ax, ay), lb = at(bx, by), f = ax === bx ? p.y - ay : p.x - ax; return [L, Math.abs(la - lb) >= FALL.from ? L : la + (lb - la) * f];   // (a fall: the eye and the body have their own way down, hd.js)
  }
  function over(x, y, L, k, n = 20) { let m = 0; for (let d = 1; d <= n; d++) { const c = col(x, y + d), e = L + (d - .5) * k; if (!c || !c.length || matAt(x, y + d)) continue; for (let i = 0; i < c.length; i += 2) if (c[i] > e && (i ? c[i - 1] : -1e9) < e + k) m = Math.max(m, i && c[i - 1] > e ? 99 : c[i] - e); } return m > 0 && topAt(x, y) > L ? 99 : m; }
  const under = (x, y, L) => topAt(x, y) > L;
  // clear(tx, ty, L, n) -> the pitch (degrees) at which the eye's line to your feet passes over the land of the n tiles south of you, counting land as it rises over your head (a tile a level over it
  //   counts whole, one at your head's height not at all, between in proportion: no jump in the pitch as you walk; .4 a level over your feet's line: your feet and their shadow, not the land's lip on them); 0: none over your head
  function clear(tx, ty, L, n) { let m = 0; for (let d = 1; d <= n; d++) { const t = topAt(tx, ty + d) - L, w = Math.max(0, Math.min(1, t - 1)); if (w > 0 && !matAt(tx, ty + d)) m = Math.max(m, w * (t + .4) / (d - .5)); } return m ? Math.atan(m * RELIEF_STEP / 16) * 180 / Math.PI : 0; }
  let sk = "", sv = 0;
  const RAYS = Array.from({length: 16}, (_, a) => Array.from({length: 6}, (__, d) => [Math.round(Math.cos(a * Math.PI / 8) * (d + 1)), Math.round(Math.sin(a * Math.PI / 8) * (d + 1))]));
  function steep(tx, ty, L, ver) {   // (sv: how many of the 16 ways out of here run into land two levels over your feet within 6 tiles. It was a ring two tiles away: a room five wide stayed side-on, you a ghost on the grass south of it)
    const key = [tx, ty, L, ver].join(); if (key !== sk) { sk = key; sv = 0; for (const r of RAYS) if (r.some(([i, j]) => !matAt(tx + i, ty + j) && topAt(tx + i, ty + j) >= L + 1)) sv++; }
    return sv >= 10;
  }
  function own(tx, ty, L, cov) {
    if (!cov) { trail = []; return trail; }
    const c = col(tx, ty), roof = topAt(tx, ty) > L; let hi = L + 1; if (roof) while (hi < L + 6 && !solid(c, hi + 1)) hi++;
    const b = roof ? [tx, ty, L, hi] : [tx, ty, L, L + 1, 1], l = trail[trail.length - 1]; if (l && l[0] === tx && l[1] === ty && l[2] === L) return trail;
    trail = trail.filter((t) => t.length < 5 && (t[0] !== tx || t[1] !== ty) && Math.abs(t[0] - tx) + Math.abs(t[1] - ty) <= 3).slice(-3).concat([b]); return trail;   // (behind you: only what was under a roof; under the open sky the land there is as it is)
  }
  const rim = (tx, ty, L) => Math.max(L, topAt(tx, ty), topAt(tx + 1, ty), topAt(tx - 1, ty), topAt(tx, ty - 1), topAt(tx, ty + 1));   // (the level of the land round your hole: its rim)
  // (px: art px of you that are drawn under your feet's line and are what shows of you: a swimmer's head and its waterline, swim.js SWIM.sink. A body is lifted whole; a swimmer was lifted as a walker and
  //  the rim cut its head at the eyes, all that showed of it ears: "no x-ray" at a cliff's foot in a river. Only when the rim hides you at all: in open water the swimmer is as it is)
  const lift = (tx, ty, L, pitch, px = 0) => { const o = over(tx, ty, L, eyeRise(pitch), 1); return Math.min(Math.max(0, rim(tx, ty, L) - L), o > 0 ? o + px / (RELIEF_STEP * Math.cos(pitch * Math.PI / 180)) : 0); };
  // shut(tx, ty, L, k) -> the floor of your hole is HIDDEN from the eye: the open ground through your tile from north to south (tiles under L + 1: lower than your head), times k (levels the eye's line climbs a tile), is less than
  // the hole's depth under its rim. Only then do its walls tell its depth by going dark (vox_style_glsl.js ho): a shaft, a pit one or two wide across. A gorge five wide whose floor and far wall are seen
  // kept that dark too: its north wall black under its first level within six tiles of you, a black stepped slab, whenever you stood at its south bank (the rim, from the tiles beside you, 12 there)
  // An OPEN hole only: under a roof (a tunnel, a cave) the window tells the depth inside, and the dark fell on whatever wall stood within six tiles of you: walking a tunnel
  // into a hill, the hill's own face over the meadow outside went black under its first level, a black stepped slab round the mouth (as by a river beside its cliffs)
  function shut(tx, ty, L, k) { const d = rim(tx, ty, L) - L; if (d <= 0 || under(tx, ty, L)) return false; let w = 1; for (const s of [-1, 1]) for (let j = 1; j <= 12 && topAt(tx, ty + s * j) < L + 1; j++) w++; return w * k < d; }
  // WHERE YOUR MARKS ARE DRAWN: with you. raise(z, s): a level of a cell a key acts on, as drawn while you are lifted (s: hd.js `seen`: L, lift, rim): your feet's level goes up by the lift, the rim's by none, the hole between
  // squeezed (the boxes and the way's block lay where the cell projects: on the grass south of a deep hole, faint, while you stood at its rim)
  const raise = (z, s) => (!s || !(s.lift > 0) ? z : z + s.lift * Math.max(0, Math.min(1, (s.rim - z) / Math.max(.001, s.rim - s.L))));
  // THE WALL BETWEEN THE EYE AND YOU: wall(x, y, z, s) -> the face a cell (z: its top) of the land south of you is drawn on, or null (drawn where it is). Seen from above (s.top: the eye looks down
  // into your hole, room or shaft; or you are lifted), a cell over your feet in the land south of you is in a wall whose face turned to you faces away from the eye: its own place projects onto
  // the grass south of the rim (a shaft 3 deep: R's "Dig a step" box lay outside the hole; a room 4 deep: the way's block and its key on the meadow: it was only while you were lifted).
  // {y: the row of that wall (the first land south of you as high as the cell), T: its top}. wallAt: a place of such a cell, drawn on that face as you see it, stood in the opening on its top
  // edge: its foot (your floor's level) on that edge, each level up a step north into the opening (at most the eye's own cot 68°, all of the wall's height inside one tile); its depth into the wall: none.
  // (It was folded down from that edge, its foot farthest north: in a room the block at your floor's level lay on your body, cut away whole)
  // A cell at or under your feet south of you whose top that wall hides from the eye (the floor at its foot: X's box on it lay on the grass) is on the same face, under the wall's foot: B, the face's foot
  function wall(x, y, z, s) {
    if (!s || !(s.lift > 0 || s.top) || y <= s.ty) return null;
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
  return {of, steep, own, rim, over, under, clear, lift, shut, raise, wall, wallAt, cut, body, get shows() { return sv; }};
})();
