// VOX: the 2.5D look's land as faces (vox_style.js draws them). No game global: the host is the engine's own.
// The land is kept in CHUNKS of 8 x 8 tiles, each its own lists of faces. A land asked for again (you walked a tile,
// a tile changed) makes only the chunks that are new or out of date: the ones coming into view, the ones a tile
// changed in (touch). The rest are kept as they are: nothing of where you are is in a chunk's faces. What is good:
//   a chunk hangs on the world (its columns, its paints, host.chunkKey: what stands in it);
//   the far land and sea (o.sea), patches measured from you: made again each time, a list of their own (far).
// The lists are not cut to the rows and columns asked: the painter leaves out what is outside them (uniform cl).
//   VoxStyleLand.create(host, cfg, P) -> {steps(cx, cy, L, o) (a generator: a tile a step; its last
//     value: {parts: {main, model, shade, water, far, sea: Float32Array}, clip: [x0, x1, y0, y1], wet,
//     made: chunks made, space: your space's floors and classes a tile, win: [[x, y, lo, hi]...] the boxes of the x-ray window (vox_style_win.js)}), touch(x, y), clear()}
//   P (the paints, vox_style.js): {SL, C, slot(key, paint) -> its place, unslot(key), start(again), spill() -> did they run out}
// THE FACE RULE (#4): every face the land is drawn with obeys these, and a face that does not is a fault to fix here, not a case of its own.
//   1. WHICH FACES: a cell's face is drawn where it is solid and the cell beside it, as the land is shown, is not (solidIn: the real column, or the
//      x-ray cut's, VoxMesh.clip): its top (kind 1) where the cell over it is open, its four sides (kind 0) where the one beside is open. Nothing else
//      of a cell is drawn: no face between two solid cells, none of the rock inside. What stands (models, kind 8 to 10), water (3) and the far land (7)
//      are their own faces, below.
//   2. ONE MATERIAL: a cell is stone at and under its tile's stone height, earth over it (the world's own rule, stone.py made_of; here
//      VoxPaint.rocky, a block put there by somebody: its own). Every face of a cell is painted as that cell is: a top with its ground (grass,
//      sand, snow, a floor) only where it is the land's top under the sky or a floor; the side of a cell, the cut's section and the cut's first line
//      with the cell's own material, earth or stone, never the grass over it.
//   3. WHOLE ART PX: a face shows its paint px for px, 16 of them a tile, a level's 16 rows a level: never stretched. Where the eye sees fewer
//      px than the paint has (a face seen aslant, a level foreshortened), whole rows or columns are left out (vox_style_glsl.js pick, whole),
//      never squeezed.
//   4. NOTHING HIDDEN SHOWS: no face of a cell the eye cannot see (shut in the rock, behind the cut's kept land), no ore on a face that only the
//      cut has opened, no px of a paint that is not there (raw, em).
//   5. LIGHT, NOT PAINT, TELLS DEPTH AND PLACE: lips, feet, mouths' shadows, the window's dimming and the strata's steps are light laid over a
//      face's own paint (flags in e, vox_style_glsl.js), never another paint in its place.
// Where the code still breaks it (to route through the rule, then strike from this list): the cut's section takes stone or earth from the
// surface's top cell and your height, not from each cell it shows (vox_style.js sectAt, flag 8388608); its first line is the land's own
// top px, grass on a meadow (vox_style_glsl.js wn 11);
// a fence's 12 rows of paint over a whole level's height (hd_fences.js, 4/3); a roof's rows over its pitched face, longer than
// they are (hd_blocks.js: flat roofs, or roof art with a row for each px of the slope).
const VoxStyleLand = (() => {
  const H = VoxStyleGLSL.H, C = 16, N = 10, CH = 8, KINDS = ["main", "model", "shade", "water"], TRI = [0, 1, 2, 0, 2, 3];   // (TRI: a quad's two triangles)
  const gp = (x, y, z) => [x, z * H, y];
  const FACES = [
    {n: [0, 0, 1], k: 1, q: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]},
    {n: [0, 0, -1], k: .45, q: [[0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 0, 0]]},
    {n: [0, 1, 0], k: .9, q: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]]},
    {n: [0, -1, 0], k: .62, q: [[1, 0, 1], [0, 0, 1], [0, 0, 0], [1, 0, 0]]},
    {n: [1, 0, 0], k: .78, q: [[1, 1, 1], [1, 0, 1], [1, 0, 0], [1, 1, 0]]},
    {n: [-1, 0, 0], k: .7, q: [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0]]},
  ];
  const cat = (l) => { let n = 0; for (const a of l) n += a.length; const d = new Float32Array(n); n = 0; for (const a of l) { d.set(a, n); n += a.length; } return d; };
  // a vertex's ten numbers onto a list: an array (a chunk being made) or a kept writer {f: Float32Array, n} (the frame's ghosts and shadows, vox_style.js), grown when full
  const emit = (dst, a, b, c, d, e, f, g, h, i, j) => { if (Array.isArray(dst)) { dst.push(a, b, c, d, e, f, g, h, i, j); return; } if (dst.n + N > dst.f.length) { const w = new Float32Array(dst.f.length * 2 + N); w.set(dst.f); dst.f = w; }
    const F = dst.f; let n = dst.n; F[n++] = a; F[n++] = b; F[n++] = c; F[n++] = d; F[n++] = e; F[n++] = f; F[n++] = g; F[n++] = h; F[n++] = i; F[n++] = j; dst.n = n; };
  const solidC = (c, z) => { if (!c) return false; for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  function create(host, cfg, P) {
    const SL = P.SL, store = new Map(), tops = new Map(), late = new Set(), far = VoxLandFar({P, CH}); let making = false, stamp = 0, into = null, wantK = null, partN = 0, partOf = 0;   // (far: the far land's patches, kept: vox_land_far.js)
    const slot = (k, paint) => { const s = P.slot(k, paint); if (into && P.mk) into.push(s); return s; };   // (into: the places of the paints a chunk or a far patch being made names: kept with it, P.use)
    const lim = (z) => Math.max(cfg.levels[0], Math.min(cfg.levels[1], z)), ck = (x, y) => Math.floor(x / CH) + "," + Math.floor(y / CH);
    // what stands in the land as boxes (host.models): vox_land_model.js
    const model = VoxLandModel({host, cfg, slot, SL, C, emit, TRI, FACES});
    // a top's paint: the host's; the px it leaves see-through (a cap's inset sides and tucked corners: the classic picture shows the wall there) take the block's own wall tone, stone on stone
    // (not one earth brown for every block: that shows a brown strip down the west side of each stone step, brown corners, a mountain's terraces a lattice)
    const tones = new Map(), tmp = new Uint32Array(C * C);
    const tone = (lv) => { let v = tones.get(lv); if (v === undefined) { host.paintFront(lv, 0, tmp, 0, C); const n = new Map(); for (let i = 0; i < C * cfg.up; i++) n.set(tmp[i], (n.get(tmp[i]) || 0) + 1); v = [...n].sort((a, b) => b[1] - a[1])[0][0]; tones.set(lv, v); } return v; };
    function topPaint(x, y, z, px, at, st) { host.paintTop(x, y, z, px, at, st); if (!host.paintFront) return; let v = 0;
      for (let j = 0; j < C; j++) for (let i = 0; i < C; i++) if ((px[at + j * st + i] >>> 24) < 128) px[at + j * st + i] = v || (v = tone(lim(VoxMesh.rock(cfg, z, z, !host.rock || host.rock(x, y, z))))); }
    // a tile's own paints (its top at each height asked for): named by its tile, so a tile that changed gets new ones
    const topSlot = (x, y, z, paint, m) => { const k = x + "," + y + "," + z + (m ? "m" + m : ""); return slot(k, (px, at, st) => { const t = x + "," + y; let l = tops.get(t); if (!l) tops.set(t, l = []); if (!l.includes(k)) l.push(k); paint(px, at, st); }); };
    // a tile changed (its ground, its height, what stands as boxes on it): its paints, the paints of the tiles beside it (their rims and lips), and the chunks within six tiles of it (a block is stone by the land three tiles off; a cliff's shadow lies some tiles from it) are out of date
    function touch(x, y) {
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const t = (x + dx) + "," + (y + dy), l = tops.get(t); if (l) { for (const k of l) P.unslot(k); tops.delete(t); } }
      for (let dy = -6; dy <= 6; dy += 6) for (let dx = -6; dx <= 6; dx += 6) { const k = ck(x + dx, y + dy); store.delete(k); if (making) late.add(k); }
      stamp++; far.dirty(x, y, x, y);
    }
    // every tile of a box touched, once: its paints and those round it, the chunks within six tiles of it (a block of land come in at once)
    function touchBox(x0, y0, x1, y1) {
      for (let y = y0 - 1; y <= y1 + 1; y++) for (let x = x0 - 1; x <= x1 + 1; x++) { const t = x + "," + y, l = tops.get(t); if (l) { for (const k of l) P.unslot(k); tops.delete(t); } }
      for (let by = Math.floor((y0 - 6) / CH); by <= Math.floor((y1 + 6) / CH); by++) for (let bx = Math.floor((x0 - 6) / CH); bx <= Math.floor((x1 + 6) / CH); bx++) { const k = bx + "," + by; store.delete(k); if (making) late.add(k); }
      stamp++; far.dirty(x0, y0, x1, y1);
    }
    // water that ran into a tile (flow.js): its chunk is made again, and the chunk beside it where it lies on a chunk's edge (the sides of the water beside it look at it)
    function wet(x, y) { for (const k of new Set([[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => ck(x + dx, y + dy)))) { store.delete(k); if (making) late.add(k); } stamp++; }
    // WATER, STILL OR RUNNING, DRAWN ONE WAY: vox_land_water.js (a tile's water faces: waterFaces)
    const waterFaces = VoxLandWater(host, emit, TRI);
    // the far land's patches, kept, and when they go (a tile changed, the sheet full): vox_land_far.js
    // (each face's corners: the three cells beside a corner that darken it, worked out once and kept, not made as small arrays for every corner of every face)
    const AOV = FACES.map((F) => F.q.map((q) => { const ax = F.n.map((a) => (a ? 0 : 1)), d = [q[0] * 2 - 1, q[1] * 2 - 1, q[2] * 2 - 1].map((v, j) => v * ax[j]);
      const t = [0, 1, 2].filter((j) => ax[j]), a = [0, 0, 0], b = [0, 0, 0]; a[t[0]] = d[t[0]]; b[t[1]] = d[t[1]]; return [a, b, [a[0] + b[0], a[1] + b[1], a[2] + b[2]]]; })), AOK = [1, .84, .72, .62], vq = new Float64Array(40);
    function quad(out, x, y, z, F, k, sky, kind, lv, e, s, solid, isTop) {
      const u0 = (s % SL) * C, v0 = (s / SL | 0) * C, top = isTop ? 0 : C - cfg.up, I = .01, A = AOV[FACES.indexOf(F)], ox = x + F.n[0], oy = y + F.n[1], oz = z + 1 + F.n[2];   // (read a hair inside its paint: at an edge a row of px took the paint beside it in the sheet: a bright line across a stone terrace)
      for (let i = 0; i < 4; i++) {
        const q = F.q[i], o = i * 10; let ao = 1;
        if (solid) { const [a, b, c] = A[i], s1 = +solid(ox + a[0], oy + a[1], oz + a[2]), s2 = +solid(ox + b[0], oy + b[1], oz + b[2]), cc = +solid(ox + c[0], oy + c[1], oz + c[2]); ao = AOK[s1 && s2 ? 3 : s1 + s2 + cc]; }
        vq[o] = x + q[0]; vq[o + 1] = (z + q[2]) * H; vq[o + 2] = y + q[1]; vq[o + 3] = u0 + (i === 0 || i === 3 ? I : C - I); vq[o + 4] = v0 + (i < 2 ? top + I : C - I); vq[o + 5] = k * ao; vq[o + 6] = sky; vq[o + 7] = kind; vq[o + 8] = lv; vq[o + 9] = e;
      }
      if (!sky) { const m = (vq[5] + vq[15] + vq[25] + vq[35]) / 4; vq[5] = vq[15] = vq[25] = vq[35] = m; }   // (a face of a cave: one tone a face. Its corners' shade ran in steps across each face: rows of dark spikes, a comb, along every cut edge)
      for (const i of TRI) for (let j = i * 10; j < i * 10 + 10; j++) out.push(vq[j]);
    }
    // YOUR SPACE AND THE WINDOW ON IT (o.win: {reach: steps out, none under the land: as far as the box of land made round you goes (inBox), the whole cave however it winds (#8, the owner: "the whole cave should show up to the player, not a small radius"), walk: on the surface, for a cave's mouth or a hole beside you: where you can walk and drop to, not the floors you came down from}). The land is made WHOLE, always: under the land you are seen through a window, a mask the painter makes from a few boxes
    // (vox_style_win.js), not through a hole cut in these faces: no chunk hangs on where you are. Here only the boxes are found: the tiles walked to from yours (reach steps), each from its floor to its ceiling.
    function* steps(cx, cy, L, o) {
      const cols = new Map(), r = o.r, deep = o.deep, pt = o.win || null, fresh = new Map(); let made = 0; far.box(cx, cy, r);
      const cached = (m, fn) => (x, y) => { const k = x * 1048576 + y; let c = m.get(k); if (c === undefined) { c = fn(x, y); m.set(k, c); } return c; };
      // real: the land as it is (where you can walk, what covers you, the window, the light); col: as it is drawn, its faces: under the land, the cut (cutH) leaves out
      // its cells over your space, and south of it those high enough to hide it from the eye (the owner: "underground view should show the real blocks around the player")
      const cutH = new Map(), real = cached(cols, host.column), col = cached(new Map(), (x, y) => { const c = real(x, y), h = cutH.get(x * 1048576 + y); return c && h !== undefined ? VoxMesh.clip(c, h) : c; });
      const inBox = (x, y) => Math.abs(x - cx) <= r && Math.abs(y - cy) <= r;
      const D = 2 * r + 1, NO = -32768, BIG = 32767, DIR = [[1, 0], [-1, 0], [0, 1], [0, -1]], at = (x, y) => (inBox(x, y) ? (y - cy + r) * D + x - cx + r : -1);
      const topOf = (x, y) => { const c = real(x, y); return c && c.length ? c[c.length - 1] : NO; };
      const S = VoxLandSpace({host, real, topOf, inBox, at, cx, cy, r, L, pt, D, NO, BIG, DIR, solidC}), {hop, inTo, mouth, reachA, clsA, win} = S;   // (your space and the cut: vox_land_space.js)
      S.flood();
      // (under the open sky yourself (behind a mountain, in a pit): a cave is not your space past the two tiles you are about to step into; the owner: "being behind a mountain shouldn't show the caves")
      if (pt) yield "flood";
      if (pt) S.boxes();
      S.cut(cutH);
      const solidIn = (x, y, z) => { const c = col(x, y); if (!inBox(x, y)) return solidC(c, z); if (z <= L - deep) return true; return solidC(c, z); };
      // (a mouth that opens onto a floor walled on two facing sides or on three (a pit's, a trench's): the top over it has no shade: a stair dug west from a 1x2 pit left a dark smudge on the terrace over it, "shadow shouldn't appear here")
      const walled = (x, y, z) => { const wl = DIR.map(([dx, dy]) => +solidIn(x + dx, y + dy, z + 1)); return (wl[0] && wl[1]) || (wl[2] && wl[3]) || wl[0] + wl[1] + wl[2] + wl[3] >= 3; };
      const front = (x, y, z, top, two, ore) => { const lv = lim(VoxMesh.rock(cfg, top, z, !host.rock || host.rock(x, y, z))), v = VoxMesh.pick(x, y, z, cfg.variants), b = host.built && host.built(x, y) ? 1 : 0; return slot((two ? "F" : "f") + lv + "," + v + (b ? "b" : "") + (ore ? "o" + ore : ""), (px, at, st) => { host.paintFront(lv, v, px, at + (C - cfg.up) * st, st, b); if (two) host.paintFront(lv, v, px, at, st, b); if (ore) OrePaint.nuggets(px, at + (C - cfg.up) * st, st, C, cfg.up, ore, v * 7 + 3); }); };   // (two: its rows twice: a tile's whole top)
      const {mark, shadow} = VoxLandMouth.of({topOf, mouth, inTo, walled}), faces = VoxLandFaces({host, cfg, C, FACES, solidC, real, col, topOf, solidIn, walled, hop, mark, shadow, topSlot, topPaint, front, quad});   // (a cell's faces and the mouths on them: vox_land_faces.js)
      const rx = Math.min(r, o.rx || r), X0 = cx - rx, X1 = cx + rx, Y0 = cy - r, Y1 = cy + Math.min(r, o.rs || r);
      const good = (ch, bx, by) => !!ch && ch.mk === (host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "") && (ch.low ? ch.L === L : ch.lo - 1 > L - deep);
      function* chunk(bx, by) {
        const out = {main: [], model: [], shade: [], water: []}; let lo = 1e9, low = false, wet = 0;
        // (a cell under the lowest air of its own column and of the four beside it has no face: the levels start there, not 20 under your feet: a tenth of the cells)
        const lowOf = (x, y) => { const c = col(x, y); return c && c.length ? c[0] : -1e9; };
        for (let y = by * CH; y < by * CH + CH; y++) for (let x = bx * CH; x < bx * CH + CH; x++) {
          const c = col(x, y); if (!c) continue; yield; const cz = c[c.length - 1]; { const ms = host.models && host.models(x, y, cz); if (ms) for (const b of ms) model(x, y, b, b.shade ? out.shade : out.model); }   // (cz: the land's top there)
          const wt = host.water && host.water(x, y), wz = wt ? (host.waterTop ? host.waterTop(x, y) : 0) : null;
          const z0 = Math.min(lowOf(x, y), lowOf(x - 1, y), lowOf(x + 1, y), lowOf(x, y - 1), lowOf(x, y + 1)); if (z0 < lo) lo = z0; if (z0 - 1 <= L - deep) low = true;   // (low: the 20 levels under your feet cut it short: it hangs on your level)
          for (let z = Math.max(L - deep + 1, z0); z <= Math.max(cz, wt ? wz + 1 : -1e9); z++) {
            if (!solidIn(x, y, z)) continue;
            faces(x, y, z, out.main);
          }
          wet += waterFaces(out.water, x, y, col, solidIn, L - deep);   // (still and running: one way)
        }
        const ch = {mk: host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "", lo, low, L, wet}; for (const k of KINDS) ch[k] = new Float32Array(out[k]); return ch;
      }
      // past the box, to the horizon, in patches: the sea's flat face where the sea is (or nothing is known); where land is, the land at its height, a skirt south, west and east of it: no sea inland.
      // Their px are the land's own at the land's own size (the shader, kind 7): a top an 8 x 8 quarter of a tile's paint, which quarter and which way round by the tile it lies on; a skirt its rock's front (e: 9 a top, 10 a south skirt, 11 a west or east one). Not the paint's mean colour: that reads as flat slabs.
      // Patches are 4 tiles across for the first 16 tiles past the box, 8 beyond (8 everywhere: a mountain's flank one smooth slab a patch wide); a top's paint is a tile of the patch at its height with its four neighbours as high (its middle tile was often a rim: a stripe of the rim's brown and green over the whole patch)
      // THE PATCHES LIE ON THE WORLD'S OWN GRID (4 and 8 tiles: x, y multiples of them), cut only at the box's edges and the far edge: walking, the patches are the ones made a step before, kept (vox_land_far.js).
      // (Not counted from you: then a step east puts every patch 1 tile off the last one's, all made again, 3 steps in 4, with their tops' paints: half of a land's making at a sprint, and
      //  the far land changes at each step, each patch's height read from other tiles: the far hills shimmer as you walk)
      function* patches() { const fl = [], fs = []; if (o.sea === undefined) return [new Float32Array(0), new Float32Array(0)];
        const cut = (a, b, s, l = []) => { for (let v = a; v < b;) { const e = Math.min(b, (Math.floor(v / s) + 1) * s); l.push([v, e - v]); v = e; } return l; };
        const ax = (c, box, one) => { const lo = c - r - 40, hi = c + r + 41, a4 = Math.floor((c - r - 16) / 8) * 8, b4 = Math.ceil((c + r + 17) / 8) * 8;   // (along one axis round c: 8s past the 4s, the 4s from 16 past the box; box: the box's own span left out, or one: a tile a patch over it)
          const mid = box ? cut(a4, c - r, 4).concat(one ? cut(c - r, c + r + 1, 1) : [], cut(c + r + 1, b4, 4)) : cut(a4, b4, 4); return cut(lo, a4, 8).concat(mid, cut(b4, hi, 8)); };
        const out = ax(cx, false), side = ax(cx, true), one = ax(cx, true, true), b4 = Math.ceil((cy + r + 17) / 8) * 8;
        const rows = cut(cy - r - 40, Math.floor((cy - r - 16) / 8) * 8, 8).map((q) => [...q, out]).concat(cut(Math.floor((cy - r - 16) / 8) * 8, cy - r, 4).map((q) => [...q, out]), cut(cy - r, cy + r + 1, 4).map((q) => [...q, side]),
          cut(cy + r + 1, cy + r + 5, 1).map((q) => [...q, one]), cut(cy + r + 5, b4, 4).map((q) => [...q, out]), cut(b4, cy + r + 41, 8).map((q) => [...q, out]));   // (the first four rows south of the box a tile each, its own paint (e 8): tall land there stands at the screen's foot, a tile as big as a hand)
        const tz = (x, y) => { const c = host.column(x, y); return c && c.length ? c[c.length - 1] : null; }, flat = (x, y, z) => tz(x - 1, y) === z && tz(x + 1, y) === z && tz(x, y - 1) === z && tz(x, y + 1) === z;
        const made = (x, y, w, h, a, b) => { into = []; patch(x, y, w, h, a, b); const s = into; into = null; return s; };   // (a patch drawn: the places of the paints it names, kept with it)
        yield* far.rows(rows, made, fl, fs);
        return [cat(fl), cat(fs)];
        function patch(x, y, w, h, fl, fs) { let mx = x + (w >> 1), my = y + (h >> 1); const c = host.column(mx, my), land = c && c.length && !(host.water && host.water(mx, my));
          const Q = [[1, 1], [3, 1], [1, 3], [3, 3]].map(([a, b]) => [x + (w * a >> 2), y + (h * b >> 2)]).filter(([qx, qy]) => tz(qx, qy) !== null && !(host.water && host.water(qx, qy)));
          let z = land ? c[c.length - 1] : c && c.length && host.waterTop ? host.waterTop(mx, my) : o.sea; if (land) for (const [qx, qy] of Q) z = Math.min(z, tz(qx, qy));   // (the lowest of five tiles: a patch as high as its highest stood over the land in front of it, a slab over a stair) (the far sea at its own face, not o.sea, a level over it: that shows a step up past the land made tile by tile)
          if (land && !(tz(mx, my) === z && flat(mx, my, z))) { const q = Q.find(([qx, qy]) => tz(qx, qy) === z && flat(qx, qy, z)) || Q.find(([qx, qy]) => tz(qx, qy) === z); if (q) [mx, my] = q; }   // (a tile whose top is at z: one as high round it if there is one)
          const sl = land ? topSlot(mx, my, z, (px, at, st) => topPaint(mx, my, z, px, at, st)) : 0, fr = land && host.paintFront ? front(mx, my, z, z) : sl;
          const put = (q, k, s, e) => { const u0 = land ? (s % SL) * C : 0, v0 = land ? (s / SL | 0) * C : 0, dst = land ? fl : fs, kind = land ? 7 : 3; for (let t = 0; t < 6; t++) { const p = q[TRI[t]]; emit(dst, p[0], p[2] * H, p[1], u0, v0, k, 1, kind, z, e); } };   // (no vertex made as an array of its own)
          put([[x, y, z], [x + w, y, z], [x + w, y + h, z], [x, y + h, z]], 1, sl, w * h === 1 && tz(x, y) === z ? 8 : 9);
          if (land) { const lo = (t) => Math.min(z - 10, t === null ? o.sea : t), s = lo(tz(mx, y + h)), wz = lo(tz(x - 1, my)), ez = lo(tz(x + w, my));   // (each skirt down to the land beside it: ten levels were a mountain's patches hung in the air over the meadow, the sky under them)
            // (each skirt its cells' own rock, face rule 2: earth from the top down to the middle tile's stone, its stone under that, split at a whole level)
            let st = null; if (host.rock) for (let q = z; q > z - 64 && st === null; q--) if (host.rock(mx, my, q) === 2) st = q;
            const fs2 = st !== null && st < z && host.paintFront ? front(mx, my, st, z) : fr, sk = (q, lo, k, e) => { if (st === null || st >= z || st <= lo) { put(q(z, lo), k, st !== null && st >= z ? fs2 : fr, e); return; } put(q(z, st), k, fr, e); put(q(st, lo), k, fs2, e); };
            sk((a, b) => [[x, y + h, a], [x + w, y + h, a], [x + w, y + h, b], [x, y + h, b]], s, .8, 10); sk((a, b) => [[x, y, a], [x, y + h, a], [x, y + h, b], [x, y, b]], wz, .7, 11); sk((a, b) => [[x + w, y + h, a], [x + w, y, a], [x + w, y, b], [x + w, y + h, b]], ez, .78, 11); } } }
      const want = []; for (let by = Math.floor(Y0 / CH); by <= Math.floor(Y1 / CH); by++) for (let bx = Math.floor(X0 / CH); bx <= Math.floor(X1 / CH); bx++) want.push([bx, by]);
      if (P.start(!!o.again)) { store.clear(); far.clear(); }   // (a land made with its paints from none keeps no chunk made before: they name places of paints that are gone. The land was wiped (eng.lost: forget) while one was being made, that one's chunks were kept, and the next, from none, drew them with other tiles' paints: grey and green squares on a meadow, the mean colour, a shadow's black blades on the grass)
      making = true; late.clear();   // (the paints and the land that names them change together: vox_style.js)
      try {
        const need = want.filter(([bx, by]) => !good(store.get(bx + "," + by), bx, by)); wantK = new Set(want.map(([bx, by]) => bx + "," + by)); partN = 0; partOf = need.length + 1; yield "scan";   // (part: how much of this land is made, the chunks and then the far land: the first screen's wait, index.html #boot)
        for (const [bx, by] of want) { const ch = store.get(bx + "," + by); if (ch && !need.some((q) => q[0] === bx && q[1] === by)) P.use(ch.slots); }   // (the paints of the chunks kept: this land's too)
        for (const [bx, by] of need) { into = []; const ch = yield* chunk(bx, by); ch.slots = into; into = null; fresh.set(bx + "," + by, ch); made++; partN++; }
        const [fl, fs] = yield* patches(); partN = partOf;
        if (P.spill() && (!o.again || o.r > 6)) { making = false; return yield* steps(cx, cy, L, Object.assign({}, o, {again: true, r: o.again ? Math.max(6, o.r - 4) : o.r})); }   // (and from none it ran out again: a land 4 tiles narrower each time, till it fits. Never shown half made: faces made before the sheet was emptied name places of other paints)   // (the paints ran out while making it: faces made before that had another face's paint (a meadow all earth, a black hole): once more, from none)
        const list = want.map(([bx, by]) => fresh.get(bx + "," + by) || store.get(bx + "," + by)).filter(Boolean), parts = {far: fl, sea: fs}; let wet = 0;
        const near = list.slice().reverse();   // (the land's own faces: the chunks nearest the eye first (the south ones), so the GPU drops the px of what is behind them before painting them; far to near would paint every hidden px, then paint over it)
        for (const k of KINDS) { const l = k === "main" ? near : list; let n = 0; for (const ch of l) n += ch[k].length; const d = new Float32Array(n); n = 0; for (const ch of l) { d.set(ch[k], n); n += ch[k].length; } parts[k] = d; }
        for (const ch of list) wet += ch.wet;
        for (const [k, ch] of fresh) if (!late.has(k)) store.set(k, ch);   // (a tile changed in it while being made: not kept, made again next time)
        if (store.size > 400) { const keep = new Set(want.map(([bx, by]) => bx + "," + by)); for (const k of store.keys()) if (!keep.has(k)) store.delete(k); }
        return {parts, clip: [X0, X1 + 1, Y0, Y1 + 1], wet, made, space: pt ? {x: cx - r, y: cy - r, D, lvl: reachA, cls: clsA} : null, win, cut: cutH};
      } finally { making = false; }
    }
    return {steps, touch, touchBox, wet, model, clear() { store.clear(); far.clear(); }, farKeep: () => far.keep(), evicted(kept) { for (const k of [...store.keys()]) if (!wantK || !wantK.has(k)) store.delete(k); if (kept) far.free(kept); else far.clear(); },   // (paints given again: what was made with them and is not of this land goes)
      get stamp() { return stamp; }, get fars() { return far.fars; }, get part() { return partOf ? partN / partOf : 0; }};   // (fars: far patches made, all told: tests)
  }
  return {create, N, CH};
})();
