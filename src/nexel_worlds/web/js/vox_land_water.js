// VOX: the land's WATER, still or running, as faces (vox_style_land.js asks it for each tile of a chunk being made: waterFaces).
// Split out of VoxStyleLand's create (#154): the same code, given what it reads (host: the world's water, flow and columns;
// emit and TRI: VoxStyleLand's vertex writer and a quad's two triangles).
//   VoxLandWater(host, emit, TRI) -> waterFaces(dst, x, y, col, solidAt, fromZ): the water's faces of tile (x, y) onto dst, how many
const VoxLandWater = (host, emit, TRI) => {
  const H = VoxStyleGLSL.H;
  // WATER, STILL OR RUNNING, DRAWN ONE WAY. A tile's water is its wet cells (wetOf: cell z -> level 1 to 8): the still water's (the sea, a river, a pond: its bed up to its face,
  // full) and what runs (flow.js: 1 to 7, 8 full). Over a still face the cells are water as high as the water beside it is full, and up to running water over it (flow.py keeps
  // nothing there: over the sea it is the sea. Filled, a river in a flood is no trench, a pond under it no second face, no light box).
  // A cell's water stands to z - 1 + v / 8 (full: to its top), so running water steps down a level's eighth a level (2 art px). Its faces: ONE top where the cell over it is
  // not water, and a side (south, east, west) down to the water or the cell's floor beside it, where that stands lower: no gap at a step, no face inside other water; the
  // painter leaves out a side turned from the eye (vox_style_glsl.js: s, its uv's u). So every px shows ONE face of water over what is under it (no tints stacked, no dark
  // sliver where an east or west side is missing).
  // Its tint (e) by how deep it is, its face over the floor, as the still water's: never under a level's (a film of running water is water, not a pale box; the levels
  // show by its height, the colour stays), and never over a pond's (2): the deeper bands are the still water's own, 3 a lake's, 4 the open sea's dark, OPAQUE (a pit filled 5 deep
  // under a river, a flood over the meadow: a flat navy slab). A still tile keeps its own depth; risen under a flood, a lake's at most.
  // Still water keeps its look: a side of its own only where running water lies beside it lower. Drawn as the sea's face, kind 3
  // ITS DEPTH AT EACH CORNER (#347, the owner's pick: "pixel bands"): a tile's one tint by its whole depth changed in a step at every tile's edge. A still tile's corner is
  // as deep as the still water's tiles that meet there, 1 to 4 levels, their mean: the same for every tile at that corner, so the depth runs on across tiles with no edge.
  // Carried in the uv's u past the side (s + depth / 10: under s + .5, read as the side as ever); the painter lays it in quarter levels, whole art px (vox_style_fs.js)
  const deep = (x, y) => { if (!(host.water && host.water(x, y))) return null; const c = host.column(x, y); return c && c.length ? Math.max(1, Math.min(4, (host.waterTop ? host.waterTop(x, y) : 0) - c[c.length - 1])) : null; };
  const corner = (X, Y) => { let n = 0, s = 0; for (const [i, j] of CORNER) { const d = deep(X + i, Y + j); if (d !== null) { s += d; n++; } } return n ? s / n : 1; };
  const CORNER = [[-1, -1], [0, -1], [-1, 0], [0, 0]];
  const wq = (dst, q, lv, e, s = 0, oc = 0, still = false) => { const d = q.map((p) => s + (still ? corner(p[0], p[1]) : Math.max(1, Math.min(4, e))) / 10);
    for (const t of TRI) { const p = q[t]; emit(dst, p[0], p[2] * H, p[1], d[t], oc, 1, 1, 3, lv, e); } };
  const SIDES = [[0, 1, 1, (x, y, a, b) => [[x, y + 1, a], [x + 1, y + 1, a], [x + 1, y + 1, b], [x, y + 1, b]]], [1, 0, 2, (x, y, a, b) => [[x + 1, y + 1, a], [x + 1, y, a], [x + 1, y, b], [x + 1, y + 1, b]]], [-1, 0, 3, (x, y, a, b) => [[x, y, a], [x, y + 1, a], [x, y + 1, b], [x, y, b]]]];
  const N4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  function wetOf(x, y, col) {
    const fw = host.flow && host.flow(x, y), still = host.water && host.water(x, y); if (!fw && !still) return null; const w = new Map(fw || []);
    if (still) { const wz = host.waterTop ? host.waterTop(x, y) : 0, c = col(x, y), bt = c && c.length ? c[c.length - 1] : wz - 1; let hi = wz; for (const z of w.keys()) if (z > hi) hi = z;
      for (let z = Math.min(wz, Math.max(bt + 1, wz - 8)); z <= wz; z++) w.set(z, 8);   // (its bed to its face, full: the face's own cell at least (clear water off, the bed is the ground))
      for (let z = wz + 1; z < wz + 64; z++) { if (w.has(z)) continue; if (z < hi || N4.some(([dx, dy]) => { const n = host.flow && host.flow(x + dx, y + dy); return n && n.get(z) === 8; })) w.set(z, 8); else break; } }
    return w; }
  // (the face of the water a cell is in: from cell z up to the last wet cell over it)
  const surf = (w, z) => { while (w.has(z + 1)) z++; return z - 1 + w.get(z) / 8; };
  // A TOP SEEN THROUGH THE WATER BESIDE IT: where the water south, east, west, south-east or south-west of a top stands higher, the eye sees the near part of this top through that water
  // too (two tints: a lighter band along every step down away from you). Each top says by how much each of the five stands over it (oc: eighths of a level, its uv's v); the painter
  // leaves out a px of it that the top beside it covers on the screen (vox_style_glsl.js): every px is seen through one face of water.
  function waterFaces(dst, x, y, col, solidAt, fromZ) { const w = wetOf(x, y, col); if (!w) return 0; let n = 0; const still = host.water && host.water(x, y), oc0 = still ? col(x, y) : null, own = still && oc0 && oc0.length ? (host.waterTop ? host.waterTop(x, y) : 0) - oc0[oc0.length - 1] : 0, runs = !!host.flow && (!!host.flow(x, y) || N4.some(([dx, dy]) => host.flow(x + dx, y + dy))),
      nb = SIDES.map(([dx, dy]) => (runs ? wetOf(x + dx, y + dy, col) : null)), nd = runs ? [wetOf(x + 1, y + 1, col), wetOf(x - 1, y + 1, col)] : [null, null];   // (the sea, a pond with nothing running by: its face alone, as it ever was, and as cheap)
    for (const [z, v] of w) { if (z < fromZ) continue; const full = w.has(z + 1), top = z - 1 + (full ? 1 : v / 8); let f = z; while (w.has(f - 1)) f--; const e = Math.max(1, Math.min(top - (f - 1), still ? Math.max(3, own) : 2));
      if (!full) { let oc = 0; [...nb, ...nd].forEach((o, i) => { if (!o) return; let c = z; if (!o.has(c)) { c = [...o.keys()].filter((k) => k > z).sort((a, b) => a - b)[0]; if (c === undefined) return; }
          oc += Math.max(0, Math.min(i < 3 ? 31 : 15, Math.round((surf(o, c) - top) * 8))) * (i < 3 ? 32 ** i : 32768 * 16 ** (i - 3)); });   // (south, east, west 5 bits each; south-east, south-west 4: 23 bits, whole in a float)
        wq(dst, [[x, y, top], [x + 1, y, top], [x + 1, y + 1, top], [x, y + 1, top]], z + 1, e, 0, oc, still); n++; }
      SIDES.forEach(([dx, dy, s, q], i) => { const X = x + dx, Y = y + dy; if (solidAt(X, Y, z) || (still && !(host.flow && host.flow(X, Y)))) return;
        const o = nb[i], ov = o && o.get(z), b = Math.max(z - 1, ov ? (o.has(z + 1) ? z : z - 1 + ov / 8) : z - 1);
        if (b < top - .01) { wq(dst, q(x, y, top, b), z + 1, e, s, 0, still); n++; } }); }
    return n; }
  return waterFaces;
};
