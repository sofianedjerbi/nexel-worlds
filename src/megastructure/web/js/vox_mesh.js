// VOX: a chunk of columns as faces. A top wherever a solid cell has an empty one over it, a front wherever the cell
// south of it is empty. An upright east, west or north face is never in view (the eye looks north from above,
// straight), so a wall that faces west or east shows a thin side instead: cfg.side px wide for its whole height
// (its outer px a dark line), in the px its block's cap leaves empty along that side, so the block is no wider than
// its tile: a box seen a little from both sides. Not at the water's own level.
// A block has a shape (host.shape, host.profile): the px of its tile it leaves empty along the sides where the
// land is lower (a rounded corner, an edge set in). So that what is behind shows there: a top goes on `cfg.tuck` px
// under the higher blocks north, west and east of it; a front is only drawn where its block has px over it, and
// its foot ends where its block's shape does; a block whose south neighbour is set in at a side shows a sliver of
// its own front past it.
// Water (host.water) is one face at the level host.waterTop says (0 if it has none) in place of its tile's top; under
// it its tile is a block as any other (its sides, where the land beside it is lower); seen through (vox_water.js) a
// column that ends under the face is its bed: a top, bit 64; a tile at height 0 beside water
// has the water's face under its top as well (a host may leave a shore see-through), and a water tile whose paint
// is not empty (ch.decor: vox_pages.js) has a top over its water.
// A corner of a face is 16 bytes: x, y (px in the chunk), z (px up: cfg.up a level), then where it is in its tile
// (px, BIAS more: under a neighbour is before 0; a front: px down from its top), what is round it (bits), its kind
// (0 top, 1 front, 2 water, 3 a bank's top, 4 a bank's front), its strip of the sheets (a top: the level over it), how dark it is by where it is (a top, a front: `slot`, `inward` below),
// then: a top, where the feet of the walls west and east of it are (px in from its side, BIAS more) and the shape of the block north of it; a front, its block's shape, the shape it is a sliver past
// (0: none) and its variant.
const VoxMesh = (() => {
  const BYTES = 16, BIAS = 8, STRIPS = 4;
  const has = (c, z) => { for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };      // is a column's cell z solid?
  // One rock a block (cfg.rock: {from, lo, n}; none: a cell's paint is its level's): a block whose top is at level `from` or over has, in its
  // cells from `lo` up to there, the paint of the levels from `from` on, n of them in turn: stone down to the ground, not stone over earth.
  // top: its block's top (topOf: of the block the cell z of a column is in) -> the level whose strip of the sheets the cell has
  // (on: the host says its tile is rock, host.rock(x, y); not: a block as high that is no rock, a stair's step, a pillar: the paint of the last level under `from` up to its top)
  const rock = (cfg, top, z, on = true) => { const r = cfg.rock; return !r || top < r.from ? z : !on ? Math.min(z, r.from - 1) : z < r.from && z >= r.lo ? r.from + (z - r.lo) % r.n : z; };
  const topOf = (c, z) => { if (c) for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return c[i]; return z; };
  const pick = (x, y, z, n) => (Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791)) >>> 5 & (n - 1);      // one of n (a power of 2), the same each time
  // Lists of faces, a list a page -> {data, pages: [[page, first corner, corners]...], n}: their corners as the GPU takes them
  function pack(faces, cfg) {
    // (a face that lies on the ground, a top, a bank's, the water, is STRIPS pieces north to south, so that it bends with the ground: vox_curve.js)
    const quads = (list) => list.reduce((s, f) => s + (f[4] ? STRIPS : 1), 0);
    const n = faces.reduce((s, f) => s + (f ? f.length : 0), 0), data = new ArrayBuffer(faces.reduce((s, f) => s + (f ? quads(f) : 0), 0) * 6 * BYTES), i16 = new Int16Array(data), u8 = new Uint8Array(data), pages = [];      // (low byte first, as every machine a browser runs on has it)
    // a face: its corner (X, Y, Z), w px across, d px deep (lying: a top) or `tall` px down (hanging: a front); (ux, uy): where in its tile its corner is
    let at = 0;
    faces.forEach((list, p) => {
      if (!list || !list.length) return;
      pages.push([p, at / BYTES, quads(list) * 6]);
      for (const f of list) {
        const X = f[0], Y = f[1], Z = f[2], w = f[3], d = f[4], ux = f[5] + BIAS, uy = f[6] + BIAS, len = d || f[7], m = d ? STRIPS : 1, own = f[14] || 0;
        // (a piece: its six corners; t: px along it from its far edge, or down from its top)
        for (let k = 0; k < m; k++) for (let c = 0, a = Math.round(len * k / m), b = Math.round(len * (k + 1) / m); c < 6; c++, at += BYTES) {
          const x = c === 1 || c > 2 && c < 5 ? w : 0, t = c < 2 || c === 3 ? a : b, h = at >> 1;
          i16[h] = X + x; i16[h + 1] = d ? Y + t : Y; i16[h + 2] = d ? Z : Z - t;
          u8[at + 6] = ux + x; u8[at + 7] = uy + t; u8[at + 8] = f[8]; u8[at + 9] = f[9]; u8[at + 10] = f[10]; u8[at + 11] = f[15] || 0; u8[at + 12] = f[11]; u8[at + 13] = f[12]; u8[at + 14] = f[13]; u8[at + 15] = own;
        }
      }
    });
    return {data, pages, n};
  }
  // -> {data, pages: [[page, first corner, corners]...], n, sides, shapes}: the tops and their fronts page by page;
  // water goes with page 0. shapes: the shapes met (the engine asks the host for their profiles)
  function build(ch, host, cfg, strip0) {
    const N = cfg.size, T = cfg.cell, K = cfg.tuck, faces = [[]], add = (p, f) => (faces[p] || (faces[p] = [])).push(f), shapes = new Set();
    const solid = (x, y, z) => { const c = host.column(x, y); return !!c && has(c, z); };
    const isRock = (x, y) => !host.rock || host.rock(x, y); let rk = true;      // (rk: the tile whose faces are being made)
    const strip = (zc, top = zc, on = rk) => strip0(rock(cfg, top, zc, on)), stripAt = (x, y, zc) => strip(zc, topOf(host.column(x, y), zc), isRock(x, y));      // (a cell's strip: by its block's top)
    const shape = (x, y, z) => { const s = host.shape(x, y, z); shapes.add(s); return s; };
    // How dark a face is by where it is (a corner's twelfth byte; the engine's shader lays the dark of a cave on by it).
    // Out of doors, `slot`: how deep down a narrow hole the level z of (x, y) is, in steps (5 at the most). Along the
    // way north-south or the way east-west there are walls (solid at lvl) on both sides within four tiles: how far
    // under the lower wall's top z is, times how deep the hole is there (its floor: `floor`; ten at the most), a step
    // for every four of that, over the square of the tiles of the way between the walls: a shaft one tile wide and eight deep is two steps
    // dark at its first level, five by its third (seen from outside its wall goes down into the dark); a pit three
    // deep one step at its second level; a pit three wide, none before it is six deep. Of walls alone: a floor is as it
    // is painted. Only in a hole in the ground: its floor under cfg.dug,
    // and counted from there down (a way between two hills is in the day's light). Under a roof, `inward`: how far in from the open the floor
    // z of (x, y) is (tiles, 1 to 4; 0: further in, or walled in): the nearest tile north, south, west or east
    // whose land is no higher than a step over that floor, with no wall on the way, if it is open two ways or more
    // (an overhang, a way through: light comes in; a cave with one mouth is dark from its mouth on).
    const floorOf = (c, z) => { let f = c[0]; for (let i = 2; i < c.length && c[i] < z; i += 2) f = c[i]; return f; };      // (a column's floor under its cell z)
    const wall = (x, y, lvl) => { const c = host.column(x, y); if (c) for (let i = 0; i < c.length; i += 2) if (lvl <= c[i]) return i === 0 || lvl > c[i - 1] ? c[i] : null; return null; };
    const shut = (x, y, floor) => { let n = 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (dx || dy) for (let k = 1; k <= 6; k++) { const c = host.column(x + dx * k, y + dy * k); if (c && c[c.length - 1] >= floor + cfg.gorge) { n++; break; } } return n >= 6; };
    const slot = (x, y, z, lvl, floor = z) => {
      let best = 0; const dug = floor < cfg.dug; if (!dug && !(cfg.gorge && shut(x, y, floor))) return 0;      // (cfg.gorge: a natural hole too, a canyon: where walls that many levels over its floor shut six or more of the eight ways off it, each within six tiles: little sky is seen from there; counted from the lower wall's top)
      for (const [dx, dy] of [[0, 1], [1, 0]]) {
        let w = 1, low = 1e9;
        for (const s of [-1, 1]) { let t = null, k = 1; for (; k <= (dug ? 4 : 6) && t === null; k++) t = wall(x + s * dx * k, y + s * dy * k, lvl); if (t === null) { low = null; break; } w += k - 2; low = Math.min(low, t); }
        if (low !== null) { if (dug) low = Math.min(low, cfg.dug); best = Math.max(best, Math.floor((low - z + 1) * Math.min(10, low - floor) / (4 * (dug ? w * w : 9)))); }      // (a gorge: by its depth alone, as one three tiles wide: its width changes tile by tile, and its wall was a patchwork)
      }
      return Math.max(0, Math.min(5, best));
    };
    const inward = (x, y, z) => {
      let best = 0, ways = 0;
      for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) for (let k = 1; k <= 4; k++) { const c = host.column(x + dx * k, y + dy * k); if (!c || has(c, z + 1)) break; if (c[c.length - 1] <= z + 1) { ways++; if (!best || k < best) best = k; break; } }
      return ways > 1 ? best : 0;
    };
    // How dark the front of the cell zc of (x, y) is. It looks into a cave: `inward`. Down a hole that was dug: `slot`, level by level.
    // A gorge's wall: none (its floor has the gorge's dark, a top's above). By its level, how far under the rim, a cliff that runs on a slant
    // (each column two levels lower on the screen than the last) was a grid of squares; darker at each column's own foot instead, a square at
    // every foot. (A wall under water seen through: none, the water's tint is its dark.)
    const foot = (x, y, zc) => {
      const s = host.column(x, y + 1); if (!s) return 0;
      if (s[s.length - 1] > zc) return inward(x, y + 1, floorOf(s, zc));
      if (host.water(x, y + 1) && clear) return 0;
      const f = floorOf(s, zc); return f < cfg.dug ? slot(x, y + 1, zc, zc, f) : 0;
    };
    // does the cell zc of (x, y) show a side toward dx: cfg.side px of it (0: none)? Where the land beside it is not
    // solid there and has no land over it (a cave); none where that land is not known, and none at the water's own
    // level (a shore has its own edge; a cliff over water has its side)
    const out = (x, y, zc, dx) => {
      const c = host.column(x + dx, y);
      return !c || has(c, zc) || c[c.length - 1] > zc || (host.water(x + dx, y) && zc <= wtop(x + dx, y)) || !solid(x, y, zc) ? 0 : cfg.side;
    };
    // how far in from its tile's side toward dx the cell's shape starts (px), and where a bank's foot is: px past that side
    const prof = new Map(), inset = (x, y, z, dx) => { const id = shape(x, y, z); let pr = prof.get(id), i = 0; if (!pr) prof.set(id, pr = host.profile(id)); while (i < T && pr[dx < 0 ? i : T - 1 - i] >= T) i++; return i; };
    const reach = (x, y, zc, dx) => { const o = out(x, y, zc, dx); return o ? o - inset(x, y, zc, dx) : -K; };
    // the level a water tile's face is at, and the level under which nothing of what is beside it is seen (its face; or its bed, where the water is seen through: vox_water.js)
    const clear = VoxWater.on(cfg), wtop = (x, y) => (host.waterTop ? host.waterTop(x, y) : 0), wfloor = (x, y) => { const c = host.column(x, y); return clear && c ? Math.min(wtop(x, y), c[c.length - 1]) : wtop(x, y); };
    let sides = 0;
    for (let ly = 0; ly < N; ly++) for (let lx = 0; lx < N; lx++) {
      const x = ch.cx * N + lx, y = ch.cy * N + ly, c = host.column(x, y), X = lx * T, Y = ly * T;
      if (!c) continue;
      rk = isRock(x, y);
      const south0 = host.column(x, y + 1);
      const wet = host.water(x, y), wz = wet ? wtop(x, y) : 0, bed = wet && VoxWater.bed(cfg, wz - c[c.length - 1]);      // (bed: seen through, its column ends under its face: the bottom, drawn as land is)
      const ct = c[c.length - 1]; if (wet || [-1, 0, 1].some((dy) => [-1, 0, 1].some((dx) => host.water(x + dx, y + dy) && wtop(x + dx, y + dy) === ct))) {      // (water; a shore: the water under it)
        const tw = wet && solid(x - 1, y, wz + 1) ? K : 0, te = wet && solid(x + 1, y, wz + 1) ? K : 0, tn = wet && solid(x, y - 1, wz + 1) ? K : 0;
        // (under a shore's top, and under what floats: a px lower, so that two faces are never at one depth)
        if (wet) add(clear ? VoxWater.PAGE : 0, [X - tw, Y - tn, wz * cfg.up, T + tw + te, T + tn, -tw, -tn, T, VoxWater.near(host, cfg, x, y), 2, 0, ...VoxWater.deep(host, cfg, x, y)]);
        else {      // (not along a side where the land is lower and no water, a pit beside the shore: its rim leaves px see-through there, and the water showed in them: a pale line along the pit floor's edge)
          const dry = (dx, dy) => { const n = host.column(x + dx, y + dy); return !!n && n[n.length - 1] < ct && !host.water(x + dx, y + dy) ? K : 0; }, dn = dry(0, -1), dw = dry(-1, 0), de = dry(1, 0), far = host.water(x, y - 1) ? 0 : 1, nw = Math.max(dw, far * dry(-1, -1)), ne = Math.max(de, far * dry(1, -1)), sv = VoxWater.shore(host, cfg, x, y);
          // (lower land only past a north corner: that corner's px, no more. All of its north rows left out, a ridge a tile wide between a pond and a drop showed the bed's sand in them, bare: cream tabs along the pond's sides)
          const piece = (x0, y0, w, h) => { const f = [X + x0, Y - 1 + y0, ct * cfg.up - 1, w, h, x0, y0, T, 0, 2, 0, sv, 0, 0]; add(0, f); if (clear) add(VoxWater.PAGE, f); };      // (seen through: once more, with those faces)
          if (dn || (nw === dw && ne === de)) piece(dw, dn, T - dw - de, T + 1 - dn); else { piece(nw, 0, T - nw - ne, K); piece(dw, K, T - dw - de, T + 1 - K); }
        }
      }
      // (the water's own side, seen through: where the land south of it is lower than its face and no water, a bank dug away: a face down to its bed. vox_water.js: its last byte 255)
      if (wet && clear && south0 && !host.water(x, y + 1) && Math.max(ct, south0[south0.length - 1]) < wz) add(VoxWater.PAGE, [X, Y + T, wz * cfg.up, T, 0, 0, 0, (wz - Math.max(ct, south0[south0.length - 1])) * cfg.up, 0, 2, 0, wz - ct, 0, 0, 255]);
      // (water has no top of its own but its face; under that its tile is a block as the land's are: its sides where what is beside it is lower; its bed)
      if (wet && ch.decor && ch.decor[ly * N + lx]) add(0, [X, Y + 1, wz * cfg.up + 1, T, T, 0, 0, T, 128, 0, 0, 0, 0, 255]);
      const south = south0;
      for (let q = c.length - 1, p = bed ? 1 : 0; q >= 0; q -= 2, p++) {      // (a bed's paint: a page on, its tile's first is what floats: vox_pages.js)
        const z = c[q], open = q + 1 === c.length, over = (dx, dy) => solid(x + dx, y + dy, z + 1);
        const n = over(0, -1), w = over(-1, 0), e = over(1, 0), nc = host.column(x, y - 1);
        // (a cave's mouth: the floor in it ends where the walls' feet beside it do, and the ground before it goes on under it)
        // (...as far as that floor ends short, no more: two tops at one height, one over the other, were stripes when the cave is cut open)
        const tn = n ? K : open && !!nc && has(nc, z) && nc[nc.length - 1] > z ? cfg.inset : 0, cut = !open && south && south[south.length - 1] === z ? cfg.inset : 0;
        // round a top. 1 north, 2 west, 4 east: a block stands over it there (it goes on under it; the shadow at
        // that wall's foot). 8: land over it (a cave's floor, in the dark). 128: what floats on water
        const dark = open ? (cfg.gorge && z >= cfg.dug ? Math.min(2, slot(x, y, z + 1, z + 1, z)) : 0) : inward(x, y, z);                // (a floor out of doors is as it is painted, however deep: it is where you stand; a gorge's, two steps at the most: it was as bright as the plateau over it, "a rug on the plateau")
        const top = (x0, wd, y1, ux) => add(p, [x0, Y - tn, z * cfg.up, wd, y1 + tn, ux, -tn, T, (n ? 1 : 0) | (w ? 2 : 0) | (e ? 4 : 0) | (open ? 0 : 8) | (bed ? 64 : 0), 0, strip(z + 1, z + 1, rk || !cfg.rock || z < cfg.rock.from),      // (a high top that is no rock: the last earth level's strip, so the light knows it: vox_light.js deep)
          (open && w ? Math.max(-K, reach(x - 1, y, z + 1, 1)) : -inset(x - 1, y, z + 1, 1)) + BIAS, (open && e ? Math.max(-K, reach(x + 1, y, z + 1, -1)) : -inset(x + 1, y, z + 1, -1)) + BIAS, n ? shape(x, y - 1, z + 1) : 0, shape(x, y, z), dark]);      // (its own shape, for the sun: under it the top's paint is its wall, vox_light.js; last: how dark, above)
        // (a mouth's floor goes on under the walls beside it only up to where the ground before the mouth goes on under them: K px
        // from its south end. Both were there at one height, in stripes)
        if (wet && !bed && open) { /* the water's face is its top */ } else if (cut && (w || e)) { top(X, T, T - cut, 0); if (w) top(X - K, K, T - K, -K); if (e) top(X + T, K, T - K, T); }
        else top(X - (w ? K : 0), T + (w ? K : 0) + (e ? K : 0), T - cut, w ? -K : 0);
        // its sides, west and east: a strip beside its top at the top's own height (kind 3; from where its cap starts:
        // host.crown, a rounded corner) and, where the wall ends south, a front a level down to its foot (kind 4).
        // Each is two faces: its outer px (bit 4: the wall's dark line) and the rest (the wall). The line is the block's
        // outline: only where what is seen beside it is lower land. Where the wall goes on a tile further north on that
        // side (a cliff that runs on a slant: each of its columns set back a tile), what is beside the side is that
        // column's front, the same rock: there the side's px are front (kind 1), that column's own levels going on to meet this
        // block, then this block's: one face with its seams, lit as a front is (a line down every column, or a side lit as a side, made a cliff a grid of crates).
        for (const dx of [-1, 1]) for (let zc = z, I = inset(x, y, z, dx), o = out(x, y, z, dx); o && zc > (q ? c[q - 1] : -1e9) && out(x, y, zc, dx); zc--) {
          const cb = host.column(x + dx, y), two = zc - 1 > (q ? c[q - 1] : -1e9) && out(x, y, zc - 1, dx) ? 2 : 0, x0 = dx < 0 ? X + I - o : X + T - I, lined = [[dx < 0 ? 0 : o - 1, 1, 4], [dx < 0 ? 1 : 0, o - 1, 0]];
          // (...a column that stands lower than this block is no part of its face: a nearer block, taller, has its line over the farther front: a stair's front ran into the plateau's a tile nearer)
          // (what is seen beside the side at level lv of the row r's south edge: going north on that side, a tile two levels up the picture, the first column
          // that stands as high as the eye's line there: its front, rock; or one whose top the line meets: lower land. However far north the wall goes on: a cliff that runs two tiles south a tile east had its lines)
          const beside = (lv, r = y - 1) => { for (let k = 0; k < 8; k++) { const cn = host.column(x + dx, r - k); if (!cn) return false; const t = host.water(x + dx, r - k) ? Math.max(wtop(x + dx, r - k), cn[cn.length - 1]) : cn[cn.length - 1]; if (t >= lv - 2 * k) return t >= z - 2 * (y - 1 - r + k); if (t >= lv - 2 * k - 2) return false; } return false; };
          // (1: it faces east; 2: of a wall two levels high or more. For the sun: vox_light.js)
          if (zc === z) { const cr = host.crown ? host.crown(shape(x, y, z))[dx < 0 ? 0 : 1] : 0, dk = cb ? slot(x + dx, y, z, z, floorOf(cb, z)) : 0;
            // (...and under a higher block north of this one, that block's own front a level more: its foot ends two px short of the tile's edge there, and nothing was behind them: a dark dot at the corner)
            if (beside(z) && beside(z - 1) && !solid(x + dx, y, z - 1)) for (const lv of n ? [z + 1, z, z - 1] : [z, z - 1]) add(0, [x0, Y, lv * cfg.up, o, 0, x0 - X, 0, cfg.up, 0, 1, lv > z ? stripAt(x, y - 1, lv) : strip(lv, z), 0, 0, pick(lv > z ? x : x + dx, y - 1, lv, cfg.variants), 0, foot(x, y, lv)]);
            // (under a higher block north of it the side goes on K px as its top does: that block's front ends its foot short of the tile's edge, and the two px of the side there were a hole, a dark dot at the corner)
            else for (const [a, w, b4] of lined) if (w > 0) add(0, [x0 + a, Y + (n ? -K : cr), z * cfg.up, w, T - (n ? -K : cr), 0, n ? -K : cr, T, (dx > 0 ? 1 : 0) | two | b4, 3, strip(z), 0, 0, 0, 0, dk]);
            sides++; }
          if (south && !solid(x + dx, y + 1, zc) && !out(x, y + 1, zc, dx) && !(host.water(x, y + 1) && zc <= wfloor(x, y + 1)))
            if (beside(zc, y)) add(0, [x0, Y + T, zc * cfg.up, o, 0, x0 - X, 0, cfg.up, solid(x + dx, y, zc - 1) || solid(x, y + 1, zc - 1) ? 16 : 0, 1, strip(zc, z), 0, 0, pick(x, y, zc, cfg.variants), 0, foot(x, y, zc)]);
            else for (const [a, w, b4] of lined) if (w > 0) add(0, [x0 + a, Y + T, zc * cfg.up, w, 0, 0, 0, cfg.up, (solid(x + dx, y, zc - 1) || solid(x, y + 1, zc - 1) ? 16 : 0) | (dx > 0 ? 32 : 0) | b4, 4, strip(zc, z), 0, 0, 0]);      // (32: it faces east: of the tile west of it, for the cut)
        }
        // down its cells: a front where the cell south is empty; a sliver of one where the block south is set in
        // at a side and this one is not (dx: which side)
        const bottom = q === 0 ? -1e9 : c[q - 1];
        if (!south) continue;                                   // (the land south is not known yet: its fronts come when it is)
        const sea = host.water(x, y + 1), low = Math.max(q === 0 ? south[0] : bottom, sea ? wfloor(x, y + 1) : -1e9);      // (no front under the water's face)
        for (const dx of [-1, 1]) if (host.column(x + dx, y + 1)) for (let zc = z; zc > bottom && !solid(x + dx, y + 1, zc) && !(host.water(x + dx, y + 1) && zc <= wfloor(x + dx, y + 1)); zc--) {
          if (!has(south, zc) || !solid(x + dx, y, zc)) continue;
          const sid = shape(x, y + 1, zc);
          if (sid) add(p, [dx < 0 ? X : X + T - K, Y + T, zc * cfg.up, K, 0, dx < 0 ? 0 : T - K, 0, cfg.up, 0, 1, strip(zc, z), 0, sid, pick(x, y, zc, cfg.variants), 0, foot(x, y, zc)]);
        }
        for (let zc = z; zc > low; zc--) {
          if (has(south, zc)) continue;
          // (8: it looks into a cave. 16: its foot, nothing of the front under it. 32, 64: a bank's front beside it, west, east: its foot is square there)
          add(p, [X, Y + T, zc * cfg.up, T, 0, 0, 0, cfg.up, (south[south.length - 1] > zc ? 8 : 0) | (zc - 1 <= low || has(south, zc - 1) ? 16 : 0) | (out(x, y, zc, -1) ? 32 : 0) | (out(x, y, zc, 1) ? 64 : 0), 1, strip(zc, z), shape(x, y, zc), 0, pick(x, y, zc, cfg.variants), 0, foot(x, y, zc)]);
        }
      }
    }
    return {...pack(faces, cfg), sides, shapes};
  }
  // The faces handed to the GPU (the chunk's own buffer, filled again when its land changed)
  function upload(ch, mesh, prog) {
    const gl = VoxGL.gl;
    if (!ch.vao) {
      ch.vao = gl.createVertexArray(); ch.buf = gl.createBuffer();
      gl.bindVertexArray(ch.vao); gl.bindBuffer(gl.ARRAY_BUFFER, ch.buf);
      for (const [name, size, type, off] of [["aPos", 3, gl.SHORT, 0], ["aLoc", 2, gl.UNSIGNED_BYTE, 6], ["aMeta", 4, gl.UNSIGNED_BYTE, 8], ["aMore", 4, gl.UNSIGNED_BYTE, 12]]) {
        const loc = prog.at(name); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, type, false, BYTES, off);
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, ch.buf); gl.bufferData(gl.ARRAY_BUFFER, mesh.data, gl.STATIC_DRAW);
    ch.ranges = mesh.pages; ch.faces = mesh.n; ch.sides = mesh.sides;
  }
  function drop(ch) { const gl = VoxGL.gl; if (gl && ch.vao) { gl.deleteVertexArray(ch.vao); gl.deleteBuffer(ch.buf); } }
  return {build, pack, upload, drop, has, pick, rock, topOf, BIAS};
})();
