// VOX: the 2.5D look's land as faces (vox_style.js draws them). No game global: the host is the engine's own.
// The land is kept in CHUNKS of 8 x 8 tiles, each its own lists of faces. A land asked for again (you walked a tile,
// a tile changed) makes only the chunks that are new or no longer good: the ones coming into view, the ones a tile
// changed in (touch), the ones the open pit over your space changed on. The rest are kept as they are. What is good:
//   a chunk hangs on the world (its columns, its paints, host.chunkKey: what stands in it) and on the pit's numbers on its own tiles (steps);
//   the far land and sea (o.sea), patches measured from you: made again each time, a list of their own (far).
// The lists are not cut to the rows and columns asked: the painter leaves out what is outside them (uniform cl).
//   VoxStyleLand.create(host, cfg, P) -> {steps(cx, cy, L, o) (a generator: a tile a step; its last
//     value: {parts: {main, model, shade, water, far, sea: Float32Array}, clip: [x0, x1, y0, y1], wet,
//     made: chunks made, pit: {x, y, D, cut: a level a tile (-32768: whole), n: tiles cut}}), touch(x, y), clear()}
//   P (the paints, vox_style.js): {SL, C, slot(key, paint) -> its place, unslot(key), start(again), spill() -> did they run out}
const VoxStyleLand = (() => {
  const H = .5, C = 16, N = 10, CH = 8, KINDS = ["main", "model", "shade", "water"];
  const gp = (x, y, z) => [x, z * H, y];
  const FACES = [
    {n: [0, 0, 1], k: 1, q: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]},
    {n: [0, 0, -1], k: .45, q: [[0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 0, 0]]},
    {n: [0, 1, 0], k: .9, q: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]]},
    {n: [0, -1, 0], k: .62, q: [[1, 0, 1], [0, 0, 1], [0, 0, 0], [1, 0, 0]]},
    {n: [1, 0, 0], k: .78, q: [[1, 1, 1], [1, 0, 1], [1, 0, 0], [1, 1, 0]]},
    {n: [-1, 0, 0], k: .7, q: [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0]]},
  ];
  const solidC = (c, z) => { if (!c) return false; for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  function create(host, cfg, P) {
    const SL = P.SL, slot = P.slot, store = new Map(), tops = new Map(), late = new Set(); let msh = null, making = false, stamp = 0;
    const lim = (z) => Math.max(cfg.levels[0], Math.min(cfg.levels[1], z)), ck = (x, y) => Math.floor(x / CH) + "," + Math.floor(y / CH);
    // what stands in the land as boxes (host.models: a bridge's deck and posts): a top and a south front each, its paint from the host's sheet px for px into a slot
    const sheet = () => { if (!msh) { const q = host.modelSheet(); msh = q.px ? q : {px: new Uint32Array(q.getContext("2d").getImageData(0, 0, q.width, q.height).data.buffer), w: q.width}; } return msh; };
    const model = (x, y, b, dst) => { const X = x + b.x / C, Y = y + b.y / C, X1 = X + b.w / C, Y1 = Y + b.d / C, Z0 = b.z / cfg.up, Z1 = (b.z + b.h) / cfg.up, Zn = Z1 + (b.tilt ? b.tilt[0] / cfg.up : 0), Zs = Z1 + (b.tilt ? b.tilt[1] / cfg.up : 0);
      const face = (uv, w, h, q, k) => { if (!uv) return; w = Math.min(C, w); h = Math.min(C, h); const win = b.win || [0, 0], ins = b.shade ? .02 : 0, pw = b.win ? C : w, ph = b.win ? C : h, sl = slot("m" + (b.sheet ? b.sheet.id : "") + uv + "," + pw + "," + ph, (px, at, st) => { const m = b.sheet || sheet(); for (let j = 0; j < ph; j++) for (let i = 0; i < pw; i++) px[at + j * st + i] = m.px[(uv[2] ? uv[1] : uv[1] + j) * m.w + (uv[2] ? uv[0] : uv[0] + i)]; });
        const v = q.map((g3, n) => [...gp(...g3), (sl % SL) * C + win[0] + [ins, w - ins, w - ins, ins][n], (sl / SL | 0) * C + win[1] + [ins, ins, h - ins, h - ins][n], k, 1, b.shade ? 10 : b.ghost ? 9 : 8, Z1, 0]); for (const n of [0, 1, 2, 0, 2, 3]) dst.push(...v[n]); };
      face(b.top, b.w, b.d, [[X, Y, Zn], [X1, Y, Zn], [X1, Y1, Zs], [X, Y1, Zs]], b.k || 1); const fh = b.fh || b.h; if (b.h) { face(b.front, b.w, fh, [[X, Y1, Zs], [X1, Y1, Zs], [X1, Y1, Z0], [X, Y1, Z0]], .85);
        face(b.west, b.d, fh, [[X, Y, Zn], [X, Y1, Zs], [X, Y1, Z0], [X, Y, Z0]], .68); face(b.east, b.d, fh, [[X1, Y1, Zs], [X1, Y, Zn], [X1, Y, Z0], [X1, Y1, Z0]], .74); } };   // (b.sheet: a paint sheet of its own, {px, w, id}; west, east: its sides, d x h px; fh: its front and sides are that many rows of paint over its height; win: [i, j]: its paint is 16 x 16 px and the face shows it from px (i, j) on; a shade's paint is read a hair inside its edges: at an edge it took a px of the paint beside it in the atlas, a thin dark line on the ground; tilt: [n, s]: its top a slope: px its north and its south edge are over its height (a roof's pitch); k: its top's light)
    // a top's paint: the host's; the px it leaves see-through (a cap's inset sides and tucked corners: the classic picture shows the wall there) take the block's own wall tone, stone on stone
    // (they were one earth brown on every block: a brown strip down the west side of each stone step, brown corners, a mountain's terraces a lattice)
    const tones = new Map(), tmp = new Uint32Array(C * C);
    const tone = (lv) => { let v = tones.get(lv); if (v === undefined) { host.paintFront(lv, 0, tmp, 0, C); const n = new Map(); for (let i = 0; i < C * cfg.up; i++) n.set(tmp[i], (n.get(tmp[i]) || 0) + 1); v = [...n].sort((a, b) => b[1] - a[1])[0][0]; tones.set(lv, v); } return v; };
    function topPaint(x, y, z, px, at, st) { host.paintTop(x, y, z, px, at, st); if (!host.paintFront) return; let v = 0;
      for (let j = 0; j < C; j++) for (let i = 0; i < C; i++) if ((px[at + j * st + i] >>> 24) < 128) px[at + j * st + i] = v || (v = tone(lim(VoxMesh.rock(cfg, z, z, !host.rock || host.rock(x, y))))); }
    // a tile's own paints (its top at each height it was asked at): named by its tile, so a tile that changed gets new ones
    const topSlot = (x, y, z, paint) => { const k = x + "," + y + "," + z; return slot(k, (px, at, st) => { const t = x + "," + y; let l = tops.get(t); if (!l) tops.set(t, l = []); if (!l.includes(k)) l.push(k); paint(px, at, st); }); };
    // a tile changed (its ground, its height, what stands as boxes on it): its paints, the paints of the tiles beside it (their rims and lips), and the chunks within six tiles of it (a block is stone by the land three tiles off; a cliff's shadow lies some tiles from it) are no longer good
    function touch(x, y) {
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const t = (x + dx) + "," + (y + dy), l = tops.get(t); if (l) { for (const k of l) P.unslot(k); tops.delete(t); } }
      for (let dy = -6; dy <= 6; dy += 6) for (let dx = -6; dx <= 6; dx += 6) { const k = ck(x + dx, y + dy); store.delete(k); if (making) late.add(k); }
      stamp++;
    }
    function quad(out, x, y, z, F, k, sky, kind, lv, e, s, solid, isTop) {
      const u0 = (s % SL) * C, v0 = (s / SL | 0) * C, top = isTop ? 0 : C - cfg.up, I = .01, UV = [[I, top + I], [C - I, top + I], [C - I, C - I], [I, C - I]], vs = [];   // (read a hair inside its paint: at an edge a row of px took the paint beside it in the sheet: a bright line across a stone terrace)
      for (let i = 0; i < 4; i++) {
        const q = F.q[i]; let ao = 1;
        if (solid) {
          const ax = F.n.map((a) => (a ? 0 : 1)), d = [q[0] * 2 - 1, q[1] * 2 - 1, q[2] * 2 - 1].map((v, j) => v * ax[j]), o = [x + F.n[0], y + F.n[1], z + 1 + F.n[2]];
          const t = [0, 1, 2].filter((j) => ax[j]), a = [0, 0, 0], b = [0, 0, 0]; a[t[0]] = d[t[0]]; b[t[1]] = d[t[1]];
          const at = (v) => +solid(o[0] + v[0], o[1] + v[1], o[2] + v[2]), s1 = at(a), s2 = at(b), cc = at([a[0] + b[0], a[1] + b[1], a[2] + b[2]]);
          ao = [1, .84, .72, .62][s1 && s2 ? 3 : s1 + s2 + cc];
        }
        vs.push([...gp(x + q[0], y + q[1], z + q[2]), u0 + UV[i][0], v0 + UV[i][1], k * ao, sky, kind, lv, e]);
      }
      for (const i of [0, 1, 2, 0, 2, 3]) out.push(...vs[i]);
    }
    // THE OPEN PIT (o.pit: {k: levels the eye's line climbs a tile south, cap, reach, g: how far it has grown, tiles}). The land is drawn whole, as on the surface.
    // Your space: the tiles walked to from yours (reach steps, a floor step of 2). Over each the land is taken away from its ceiling up; south of each a level more
    // a tile (the eye's line: nothing stands between the eye and your floor), east and west a wall of two levels, then three a tile; north of it nothing: that wall stands whole.
    // Past cap tiles south the wall left is a checker round you (veil). One field of numbers, a tile a number: a chunk hangs on its own numbers alone.
    function* steps(cx, cy, L, o) {
      const cols = new Map(), r = o.r, deep = o.deep, pt = o.pit && o.pit.g > 0 ? o.pit : null, fresh = new Map(); let made = 0;
      const col = (x, y) => { const k = x + "," + y; if (!cols.has(k)) cols.set(k, host.column(x, y)); return cols.get(k); };
      const inBox = (x, y) => Math.abs(x - cx) <= r && Math.abs(y - cy) <= r;
      const D = 2 * r + 1, NO = -32768, BIG = 32767, DIR = [[1, 0], [-1, 0], [0, 1], [0, -1]], at = (x, y) => (inBox(x, y) ? (y - cy + r) * D + x - cx + r : -1);
      const reachA = new Int16Array(D * D).fill(NO), cutA = new Int16Array(D * D).fill(NO), veilA = new Int16Array(D * D).fill(NO), roomA = new Uint8Array(D * D), rowG = new Int16Array(D * D).fill(BIG), reached = [];
      const topOf = (x, y) => { const c = col(x, y); return c && c.length ? c[c.length - 1] : NO; };
      const floorOf = (x, y, f0) => { const c = col(x, y); if (!c || !c.length) return null; if (host.water && host.water(x, y) && host.waterTop) { const w = host.waterTop(x, y); if (w >= c[c.length - 1]) return Math.abs(w - f0) <= 2 ? w : null; }
        for (const dz of [0, 1, -1, 2, -2]) if (solidC(c, f0 + dz) && !solidC(c, f0 + dz + 1)) return f0 + dz; return null; };
      if (pt) { let fr = [[cx, cy, L]]; reachA[at(cx, cy)] = L; reached.push(at(cx, cy));
        for (let d = 1; d <= Math.min(pt.reach, pt.g) && fr.length; d++) { const nx = []; for (const [x, y, f0] of fr) for (const [dx, dy] of DIR) { const i = at(x + dx, y + dy); if (i < 0 || reachA[i] !== NO) continue; const f = floorOf(x + dx, y + dy, f0); if (f === null) continue; reachA[i] = f; reached.push(i); nx.push([x + dx, y + dy, f]); } fr = nx; } }
      const roofed = (i) => i >= 0 && reachA[i] !== NO && topOf(cx - r + i % D, cy - r + (i / D | 0)) > reachA[i], reachOf = (x, y) => { const i = at(x, y); return roofed(i) ? reachA[i] : undefined; }, isRoom = (x, y) => { const i = at(x, y); return i >= 0 && roomA[i] === 1; };
      const grp = new Uint8Array(D * D), next = (i, fn) => { const x = i % D, y = i / D | 0; for (const [dx, dy] of DIR) { const X = x + dx, Y = y + dy; if (X >= 0 && Y >= 0 && X < D && Y < D) fn(Y * D + X); } };   // (the floors of your space that are a room's: 4 or more tiles on one level together; the rest are treads and landings of a stair)
      for (const i0 of reached) { if (grp[i0]) continue; const g = [i0]; grp[i0] = 1; for (let n = 0; n < g.length; n++) next(g[n], (j) => { if (!grp[j] && reachA[j] === reachA[i0]) { grp[j] = 1; g.push(j); } }); if (g.length >= 4) for (const i of g) roomA[i] = 1; }
      const ext = pt ? Math.min(pt.cap, pt.g + 1) : 0, S = (d) => Math.floor((d - 1) * pt.k) - 1, box = [BIG, BIG, -BIG, -BIG];
      for (const i of reached) { const x = i % D, F = reachA[i]; for (let dx = -ext; dx <= ext; dx++) { const X = x + dx; if (X < 0 || X >= D) continue; const v = F + (dx ? 3 * Math.abs(dx) - 1 : 0), j = i + dx; if (v < rowG[j]) rowG[j] = v; } }
      // (land under the eye's line hides nothing: left whole; what is over it is cut a level under the line, so your floor's own edge shows)
      if (pt) for (let i = 0; i < D * D; i++) { const x = i % D, y = i / D | 0, tp = topOf(cx - r + x, cy - r + y); if (tp === NO) continue; let h = BIG, vl = BIG;
        for (let d = 0; d <= ext + 12 && y - d >= 0; d++) { const g = rowG[i - d * D]; if (g === BIG || (d && tp <= g + Math.max(0, S(d) + 1))) continue; const v = g + (d ? S(d) : 0); if (d <= ext) { if (v < h) h = v; } else if (v < vl) vl = v; }
        if (reachA[i] !== NO && reachA[i] > h + 2) reachA[i] = NO;   // (a tile walked to that stands over the eye's line to a lower one, the meadow over your own tunnel: land as any other)
        if (reachA[i] !== NO) { const c = col(cx - r + x, cy - r + y); let z = reachA[i] + 1; while (z <= tp && !solidC(c, z)) z++; h = z - 1; }   // (your space: from its ceiling up)
        if (h < tp) cutA[i] = h; else if (ext >= pt.cap && vl < tp) veilA[i] = vl; else continue;
        box[0] = Math.min(box[0], x); box[1] = Math.min(box[1], y); box[2] = Math.max(box[2], x); box[3] = Math.max(box[3], y); }
      for (const i of reached) if (reachA[i] !== NO && roofed(i)) { const x = i % D, y = i / D | 0; box[0] = Math.min(box[0], x); box[1] = Math.min(box[1], y); box[2] = Math.max(box[2], x); box[3] = Math.max(box[3], y); }
      const cutOf = (x, y, top) => { const i = at(x, y); return i >= 0 && cutA[i] !== NO ? cutA[i] : top; };
      const solidIn = (x, y, z) => { const c = col(x, y); if (!inBox(x, y)) return solidC(c, z); if (z <= L - deep) return true; return !!c && z <= cutOf(x, y, 1e9) && solidC(c, z); };
      const front = (x, y, z, top, two) => { const lv = lim(VoxMesh.rock(cfg, top, z, !host.rock || host.rock(x, y))), v = VoxMesh.pick(x, y, z, cfg.variants); return slot((two ? "F" : "f") + lv + "," + v, (px, at, st) => { host.paintFront(lv, v, px, at + (C - cfg.up) * st, st); if (two) host.paintFront(lv, v, px, at, st); }); };   // (two: its rows twice: a tile's whole top)
      const hop = (x0, y0, x1, y1, h) => { const a = col(x0, y0), b = col(x1, y1); return !!a && !!b && solidC(a, h) && !solidC(a, h + 1) && !solidC(a, h + 2) && solidC(b, h + 1) && !solidC(b, h + 2); };   // (the game's own rule: from a floor at h a jump up one level, room over it and over your head)
      const rx = Math.min(r, o.rx || r), X0 = cx - rx, X1 = cx + rx, Y0 = cy - r, Y1 = cy + Math.min(r, o.rs || r);
      // what a chunk hangs on of the pit: the numbers of its own tiles and the ring round them ("": the pit is not on it)
      const sigOf = (bx, by) => { const x0 = bx * CH - 1 - cx + r, y0 = by * CH - 1 - cy + r; if (box[0] > box[2] || x0 > box[2] || x0 + CH + 1 < box[0] || y0 > box[3] || y0 + CH + 1 < box[1]) return ""; let s = "";
        for (let y = y0; y <= y0 + CH + 1; y++) for (let x = x0; x <= x0 + CH + 1; x++) { const i = x >= 0 && y >= 0 && x < D && y < D ? y * D + x : -1; s += i < 0 ? ";" : (cutA[i] === NO ? "" : cutA[i]) + (veilA[i] === NO ? "" : "v" + veilA[i]) + (roofed(i) ? "r" + reachA[i] + (roomA[i] ? "R" : "") : "") + ";"; } return s; };
      const good = (ch, bx, by) => !!ch && ch.mk === (host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "") && ch.sig === sigOf(bx, by) && (ch.low ? ch.L === L : ch.lo - 1 > L - deep);
      function* chunk(bx, by) {
        const out = {main: [], model: [], shade: [], water: []}; let lo = 1e9, low = false, wet = 0;
        const faces = (x, y, z, dst, isC) => {
          const c = col(x, y), open = c[c.length - 1], top = VoxMesh.topOf(c, z), vi = at(x, y), vl = vi >= 0 && veilA[vi] !== NO && z > veilA[vi] ? 32 : 0;
          for (let f = 0; f < 6; f++) {
            const F = FACES[f], nx = x + F.n[0], ny = y + F.n[1], nz = z + F.n[2];
            if (f === 1 || solidIn(nx, ny, nz)) continue;
            const nc = col(nx, ny); let sky = (f === 0 ? z >= open : !nc || z > nc[nc.length - 1]) ? 1 : 0, s, kind = f === 0 ? 1 : 0, e = vl;
            if (f === 0) {
              const isCut = isC && solidC(c, z + 1), zt = isCut ? open : z; s = isCut ? front(x, y, z, top, true) : topSlot(x, y, zt, (px, at, st) => topPaint(x, y, zt, px, at, st));   // (a terrace of the pit shows the rock: its front's paint, no lip)
              if (isCut) { kind = 2; sky = 0; }
              else { [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if (!solidIn(x + dx, y + dy, z) && (sky || solidIn(x + dx, y + dy, z - 1))) e |= b; });   // (a lip: under a roof only at a step of one level, one you can take; a drop of two or more has none)
                if (!sky) [[0, -1, 512], [1, 0, 1024], [0, 1, 2048], [-1, 0, 4096]].forEach(([dx, dy, b]) => { if (solidIn(x + dx, y + dy, z + 1) && !hop(x, y, x + dx, y + dy, z)) e |= b; });   // (a floor under a roof: a WALL at that edge (too high to jump, or no room to): its foot in shade; a step you can take has none)
                if (reachOf(x, y) === z && !isRoom(x, y)) e |= 16; }   // (a stair's tread or a small landing: no glow on it, vox_style_glsl.js)
            } else { s = front(x, y, z, top); if (!sky && !solidC(c, z + 1) && hop(nx, ny, x, y, z - 1)) e |= 16; }   // (the riser of a step you can take: light, the tread's own tone; any other face is a wall)
            quad(dst, x, y, z - 1, F, F.k, sky, kind, z, e, s, solidIn, f === 0);
          }
        };
        // (a cell under the lowest air of its own column and of the four beside it has no face: the levels start there, not 20 under your feet: a tenth of the cells)
        const lowOf = (x, y) => { const c = col(x, y); return c && c.length ? Math.min(c[0], cutOf(x, y, 1e9)) : -1e9; };
        for (let y = by * CH; y < by * CH + CH; y++) for (let x = bx * CH; x < bx * CH + CH; x++) {
          const c = col(x, y); if (!c) continue; yield; const cz = cutOf(x, y, c[c.length - 1]); { const ms = host.models && host.models(x, y, cz); if (ms) for (const b of ms) model(x, y, b, b.shade ? out.shade : out.model); }   // (cz: the land's top there as it is drawn: what stands on land the pit took is the host's to leave out)
          const wt = host.water && host.water(x, y), wz = wt ? (host.waterTop ? host.waterTop(x, y) : 0) : null;
          const z0 = Math.min(lowOf(x, y), lowOf(x - 1, y), lowOf(x + 1, y), lowOf(x, y - 1), lowOf(x, y + 1)); if (z0 < lo) lo = z0; if (z0 - 1 <= L - deep) low = true;   // (low: the 20 levels under your feet cut it short: it hangs on your level)
          for (let z = Math.max(L - deep + 1, z0); z <= Math.max(cz, wt ? wz + 1 : -1e9); z++) {
            if (!solidIn(x, y, z)) { if (wt && z === wz + 1) { quad(out.water, x, y, z - 2, FACES[0], 1, 1, 3, z, Math.max(0, wz - c[c.length - 1]), 0, null, true); wet++; } continue; }   // (e: how deep the water is here, levels)
            faces(x, y, z, out.main, z === cz);
          }
        }
        const ch = {sig: sigOf(bx, by), mk: host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "", lo, low, L, wet}; for (const k of KINDS) ch[k] = new Float32Array(out[k]); return ch;
      }
      // past the box, to the horizon, in patches: the sea's flat face where the sea is (or nothing is known); where land is, the land's own tint at its height, flat, a skirt south of it: no sea inland
      function* patches() { const fl = [], fs = []; if (o.sea === undefined) return [fl, fs]; const seg = []; for (let s = -r; s <= r; s += 8) seg.push([s, Math.min(8, r + 1 - s), 1]); for (let k = 0; k < 5; k++) seg.push([r + 1 + 8 * k, 8, 0], [-r - 8 - 8 * k, 8, 0]);
        for (const [j, h, mj] of seg) { yield "far"; for (const [i, w, mi] of seg) { if (mi && mj) continue; const x = cx + i, y = cy + j, mx = x + (w >> 1), my = y + (h >> 1), c = host.column(mx, my), land = c && c.length && !(host.water && host.water(mx, my));
          const z = land ? c[c.length - 1] : o.sea, sl = land ? topSlot(mx, my, z, (px, at, st) => host.paintTop(mx, my, z, px, at, st)) : 0, u0 = land ? (sl % SL) * C + 8 : 0, v0 = land ? (sl / SL | 0) * C + 8 : 0;
          const put = (q, k) => { const v = q.map(([a, b, d]) => [...gp(a, b, d), u0, v0, k, 1, land ? 7 : 3, z, 9]); for (const n of [0, 1, 2, 0, 2, 3]) (land ? fl : fs).push(...v[n]); };
          put([[x, y, z], [x + w, y, z], [x + w, y + h, z], [x, y + h, z]], 1); if (land) put([[x, y + h, z], [x + w, y + h, z], [x + w, y + h, z - 10], [x, y + h, z - 10]], .8); } }
        return [fl, fs]; }
      const want = []; for (let by = Math.floor(Y0 / CH); by <= Math.floor(Y1 / CH); by++) for (let bx = Math.floor(X0 / CH); bx <= Math.floor(X1 / CH); bx++) want.push([bx, by]);
      if (o.again) store.clear();
      P.start(!!o.again); making = true; late.clear();   // (the paints and the land that names them change together: vox_style.js)
      try {
        const need = want.filter(([bx, by]) => !good(store.get(bx + "," + by), bx, by)); yield "scan";
        for (const [bx, by] of need) { fresh.set(bx + "," + by, yield* chunk(bx, by)); made++; }
        const [fl, fs] = yield* patches();
        if (P.spill() && !o.again) { making = false; return yield* steps(cx, cy, L, Object.assign({}, o, {again: true})); }   // (the paints ran out while it was made: faces made before that had another face's paint (a meadow all earth, a black hole): once more, from none)
        const list = want.map(([bx, by]) => fresh.get(bx + "," + by) || store.get(bx + "," + by)).filter(Boolean), parts = {far: new Float32Array(fl), sea: new Float32Array(fs)}; let wet = 0;
        const near = list.slice().reverse();   // (the land's own faces: the chunks nearest the eye first (the south ones), so the GPU drops the px of what is behind them before painting them; it was far to near: every hidden px painted, then painted over)
        for (const k of KINDS) { const l = k === "main" ? near : list; let n = 0; for (const ch of l) n += ch[k].length; const d = new Float32Array(n); n = 0; for (const ch of l) { d.set(ch[k], n); n += ch[k].length; } parts[k] = d; }
        for (const ch of list) wet += ch.wet;
        for (const [k, ch] of fresh) if (!late.has(k)) store.set(k, ch);   // (a tile changed in it while it was made: not kept, made again next time)
        if (store.size > 400) { const keep = new Set(want.map(([bx, by]) => bx + "," + by)); for (const k of store.keys()) if (!keep.has(k)) store.delete(k); }
        return {parts, clip: [X0, X1 + 1, Y0, Y1 + 1], wet, made, pit: {x: cx - r, y: cy - r, D, cut: cutA, n: reached.length ? cutA.reduce((a, v) => a + (v !== NO), 0) : 0}};
      } finally { making = false; }
    }
    return {steps, touch, model, clear() { store.clear(); }, get stamp() { return stamp; }};
  }
  return {create, N, CH};
})();
