// VOX: a chunk of columns as faces. A top wherever a solid cell has an empty one over it, a front wherever the cell
// south of it is empty. An upright east, west or north face is never in view (the eye looks north from above,
// straight), so a wall that faces west or east leans: under its top level each level stands out host.band(z) px
// more (cfg.bands levels at the most, then straight down), and what shows of each is real faces: a strip of its
// top beside the wall at its own height (a bank, wider the higher the wall), and its own narrow front where the
// wall ends south. Never toward water.
// A block has a shape (host.shape, host.profile): the px of its tile it leaves empty along the sides where the
// land is lower (a rounded corner, an edge set in). So that what is behind shows there: a top goes on `cfg.tuck` px
// under the higher blocks north, west and east of it; a front is only drawn where its block has px over it, and
// its foot ends where its block's shape does; a block whose south neighbour is set in at a side shows a sliver of
// its own front past it.
// Water (host.water) is one face at height 0, and what is under it is not drawn; a tile at height 0 beside water
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
  function build(ch, host, cfg, strip) {
    const N = cfg.size, T = cfg.cell, K = cfg.tuck, faces = [[]], add = (p, f) => (faces[p] || (faces[p] = [])).push(f), shapes = new Set();
    const solid = (x, y, z) => { const c = host.column(x, y); return !!c && has(c, z); };
    const rise = (x, y, z, most) => { let n = 0; while (n < most && solid(x, y, z + 1 + n)) n++; return n; };      // the solid cells of (x, y) over level z
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
    const slot = (x, y, z, lvl, floor = z) => {
      let best = 0; if (!(floor < cfg.dug)) return 0;
      for (const [dx, dy] of [[0, 1], [1, 0]]) {
        let w = 1, low = 1e9;
        for (const s of [-1, 1]) { let t = null, k = 1; for (; k <= 4 && t === null; k++) t = wall(x + s * dx * k, y + s * dy * k, lvl); if (t === null) { low = null; break; } w += k - 2; low = Math.min(low, t); }
        if (low !== null) { low = Math.min(low, cfg.dug); best = Math.max(best, Math.floor((low - z + 1) * Math.min(10, low - floor) / (4 * w * w))); }
      }
      return Math.max(0, Math.min(5, best));
    };
    const inward = (x, y, z) => {
      let best = 0, ways = 0;
      for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) for (let k = 1; k <= 4; k++) { const c = host.column(x + dx * k, y + dy * k); if (!c || has(c, z + 1)) break; if (c[c.length - 1] <= z + 1) { ways++; if (!best || k < best) best = k; break; } }
      return ways > 1 ? best : 0;
    };
    // how far the cell zc of (x, y) stands out toward dx (px): a band for each solid cell over it, cfg.bands at the
    // most. None where the land beside it is solid there, has land over it (a cave), is water or is not known
    const out = (x, y, zc, dx) => {
      const c = host.column(x + dx, y);
      if (!c || has(c, zc) || c[c.length - 1] > zc || host.water(x + dx, y) || !solid(x, y, zc)) return 0;
      const r = rise(x, y, zc, cfg.bands); let o = 0; for (let n = r - 1; n >= 0; n--) o += host.band(zc + n);
      // (never past its fair share of the tile it leans over: a quarter of it where the land on that tile's other
      // side is higher too (a way between two walls, a pit's floor: half of the ground is left), else half of it.
      // What is left of the wall goes straight down)
      const most = inset(x, y, zc, dx) + T / (solid(x + 2 * dx, y, c[c.length - 1] + 1) ? 4 : 2); clipped = o > most;
      return o && Math.min(o, most);
    };
    let clipped = false;                                        // (the last bank asked for did not fit: its wall is higher than it tells)
    // how far in from its tile's side toward dx the cell's shape starts (px), and where a bank's foot is: px past that side
    const prof = new Map(), inset = (x, y, z, dx) => { const id = shape(x, y, z); let pr = prof.get(id), i = 0; if (!pr) prof.set(id, pr = host.profile(id)); while (i < T && pr[dx < 0 ? i : T - 1 - i] >= T) i++; return i; };
    const reach = (x, y, zc, dx) => { const o = out(x, y, zc, dx); return o ? o - inset(x, y, zc, dx) : -K; };
    let sides = 0;
    for (let ly = 0; ly < N; ly++) for (let lx = 0; lx < N; lx++) {
      const x = ch.cx * N + lx, y = ch.cy * N + ly, c = host.column(x, y), X = lx * T, Y = ly * T;
      if (!c) continue;
      const wet = host.water(x, y);
      if (wet || (c.length === 1 && c[0] === 0 && [-1, 0, 1].some((dy) => [-1, 0, 1].some((dx) => host.water(x + dx, y + dy))))) {      // (water; a shore: the water under it)
        const tw = wet && solid(x - 1, y, 1) ? K : 0, te = wet && solid(x + 1, y, 1) ? K : 0, tn = wet && solid(x, y - 1, 1) ? K : 0;
        // (under a shore's top, and under what floats: a px lower, so that two faces are never at one depth)
        if (wet) add(0, [X - tw, Y - tn, 0, T + tw + te, T + tn, -tw, -tn, T, 0, 2, 0, 0, 0, 0]); else add(0, [X, Y - 1, -1, T, T + 1, 0, 0, T, 0, 2, 0, 0, 0, 0]);
      }
      if (wet) { if (ch.decor && ch.decor[ly * N + lx]) add(0, [X, Y + 1, 1, T, T, 0, 0, T, 128, 0, 0, 0, 0, 255]); continue; }
      const south = host.column(x, y + 1);
      for (let q = c.length - 1, p = 0; q >= 0; q -= 2, p++) {
        const z = c[q], open = q + 1 === c.length, over = (dx, dy) => solid(x + dx, y + dy, z + 1);
        const n = over(0, -1), w = over(-1, 0), e = over(1, 0), nc = host.column(x, y - 1);
        // (a cave's mouth: the floor in it ends where the walls' feet beside it do, and the ground before it goes on under it)
        // (...as far as that floor ends short, no more: two tops at one height, one over the other, were stripes when the cave is cut open)
        const tn = n ? K : open && !!nc && has(nc, z) && nc[nc.length - 1] > z ? cfg.inset : 0, cut = !open && south && south[south.length - 1] === z ? cfg.inset : 0;
        // round a top. 1 north, 2 west, 4 east: a block stands over it there (it goes on under it; the shadow at
        // that wall's foot). 8: land over it (a cave's floor, in the dark). 128: what floats on water
        const dark = open ? 0 : inward(x, y, z);                // (a floor out of doors is as it is painted, however deep: it is where you stand)
        const top = (x0, wd, y1, ux) => add(p, [x0, Y - tn, z * cfg.up, wd, y1 + tn, ux, -tn, T, (n ? 1 : 0) | (w ? 2 : 0) | (e ? 4 : 0) | (open ? 0 : 8), 0, strip(z + 1),
          (open && w ? Math.max(-K, reach(x - 1, y, z + 1, 1)) : -inset(x - 1, y, z + 1, 1)) + BIAS, (open && e ? Math.max(-K, reach(x + 1, y, z + 1, -1)) : -inset(x + 1, y, z + 1, -1)) + BIAS, n ? shape(x, y - 1, z + 1) : 0, shape(x, y, z), dark]);      // (its own shape, for the sun: under it the top's paint is its wall, vox_light.js; last: how dark, above)
        // (a mouth's floor goes on under the walls beside it only up to where the ground before the mouth goes on under them: K px
        // from its south end. Both were there at one height, in stripes)
        if (cut && (w || e)) { top(X, T, T - cut, 0); if (w) top(X - K, K, T - K, -K); if (e) top(X + T, K, T - K, T); }
        else top(X - (w ? K : 0), T + (w ? K : 0) + (e ? K : 0), T - cut, w ? -K : 0);
        // its banks, west and east, a level at a time down the wall: the strip of its top that the level over it
        // leaves in view (where it does not lean, over water: the px the level over it is set in more than it is),
        // and its front unless the wall goes on south at least as far out. (They start where the
        // block's own side is: its shape's.)
        for (const dx of [-1, 1]) for (let zc = z - 1, edge = inset(x, y, z, dx); zc > (q ? c[q - 1] : -1e9) && !solid(x + dx, y, zc); zc--) {
          const o = out(x, y, zc, dx), I = inset(x, y, zc, dx), b = Math.min(edge, I - o); if (!o && !(zc > 0 && host.water(x + dx, y))) break;      // (edge, b: px in from the tile's side: what is over this level reaches that far out; this level, to there)
          // (a bank that did not fit: the px of it furthest out is the wall's foot colour, 4: more wall than it tells goes straight down there)
          if (b < edge) { const cb = host.column(x + dx, y), dk = cb ? slot(x + dx, y, zc, zc, floorOf(cb, zc)) : 0; const bt = (dx > 0 ? 1 : 0) | (zc < z - 1 || (zc - 1 > (q ? c[q - 1] : -1e9) && !solid(x + dx, y, zc - 1)) ? 2 : 0), dark = o && (clipped || (zc - 1 > (q ? c[q - 1] : -1e9) && !solid(x + dx, y, zc - 1) && out(x, y, zc - 1, dx) && clipped)) ? 1 : 0, w = edge - b - dark;
            if (w > 0) add(0, [dx < 0 ? X + b + dark : X + T - edge, Y, zc * cfg.up, w, T, 0, 0, T, bt, 3, strip(zc), 0, 0, 0, 0, dk]);
            if (dark) add(0, [dx < 0 ? X + b : X + T - b - 1, Y, zc * cfg.up, 1, T, 0, 0, T, bt | 4, 3, strip(zc), 0, 0, 0, 0, dk]);
            sides++; }      // (1: it faces east; 2: of a wall two levels high or more. For the sun: vox_light.js)
          edge = b;
          if (o && south && !solid(x + dx, y + 1, zc) && out(x, y + 1, zc, dx) < o && !(zc <= 0 && host.water(x, y + 1)))
            add(0, [dx < 0 ? X + b : X + T - I, Y + T, zc * cfg.up, I - b, 0, 0, 0, cfg.up, (solid(x + dx, y, zc - 1) || solid(x, y + 1, zc - 1) ? 16 : 0) | (dx > 0 ? 32 : 0), 4, strip(zc), 0, 0, 0]);      // (32: it faces east: of the tile west of it, for the cut)
        }
        // down its cells: a front where the cell south is empty; a sliver of one where the block south is set in
        // at a side and this one is not (dx: which side)
        const bottom = q === 0 ? -1e9 : c[q - 1];
        if (!south) continue;                                   // (the land south is not known yet: its fronts come when it is)
        const sea = host.water(x, y + 1), low = Math.max(q === 0 ? south[0] : bottom, sea ? 0 : -1e9);      // (no front under the water's face)
        for (const dx of [-1, 1]) if (host.column(x + dx, y + 1)) for (let zc = z; zc > bottom && !solid(x + dx, y + 1, zc) && !(zc <= 0 && host.water(x + dx, y + 1)); zc--) {
          if (!has(south, zc) || !solid(x + dx, y, zc)) continue;
          const sid = shape(x, y + 1, zc);
          if (sid) add(p, [dx < 0 ? X : X + T - K, Y + T, zc * cfg.up, K, 0, dx < 0 ? 0 : T - K, 0, cfg.up, 0, 1, strip(zc), 0, sid, pick(x, y, zc, cfg.variants)]);
        }
        for (let zc = z; zc > low; zc--) {
          if (has(south, zc)) continue;
          // (8: it looks into a cave. 16: its foot, nothing of the front under it. 32, 64: a bank's front beside it, west, east: its foot is square there)
          add(p, [X, Y + T, zc * cfg.up, T, 0, 0, 0, cfg.up, (south[south.length - 1] > zc ? 8 : 0) | (zc - 1 <= low || has(south, zc - 1) ? 16 : 0) | (out(x, y, zc, -1) ? 32 : 0) | (out(x, y, zc, 1) ? 64 : 0), 1, strip(zc), shape(x, y, zc), 0, pick(x, y, zc, cfg.variants), 0, south[south.length - 1] > zc ? inward(x, y + 1, floorOf(south, zc)) : slot(x, y + 1, zc, zc, floorOf(south, zc))]);
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
  return {build, pack, upload, drop, has, pick, BIAS};
})();
