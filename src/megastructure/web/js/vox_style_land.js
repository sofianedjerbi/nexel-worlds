// VOX: the 2.5D look's land as faces (vox_style.js draws them). No game global: the host is the engine's own.
// The land is kept in CHUNKS of 8 x 8 tiles, each its own lists of faces. A land asked for again (you walked a tile,
// a tile changed) makes only the chunks that are new or no longer good: the ones coming into view, the ones a tile
// changed in (touch). The rest are kept as they are: nothing of where you are is in a chunk's faces. What is good:
//   a chunk hangs on the world (its columns, its paints, host.chunkKey: what stands in it);
//   the far land and sea (o.sea), patches measured from you: made again each time, a list of their own (far).
// The lists are not cut to the rows and columns asked: the painter leaves out what is outside them (uniform cl).
//   VoxStyleLand.create(host, cfg, P) -> {steps(cx, cy, L, o) (a generator: a tile a step; its last
//     value: {parts: {main, model, shade, water, far, sea: Float32Array}, clip: [x0, x1, y0, y1], wet,
//     made: chunks made, space: your space's floors and classes a tile, win: [[x, y, lo, hi]...] the boxes of the x-ray window (vox_style_win.js)}), touch(x, y), clear()}
//   P (the paints, vox_style.js): {SL, C, slot(key, paint) -> its place, unslot(key), start(again), spill() -> did they run out}
const VoxStyleLand = (() => {
  const H = VoxStyleGLSL.H, C = 16, N = 10, CH = 8, KINDS = ["main", "model", "shade", "water"];
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
  // A WAY INTO THE LAND, SEEN FROM ANY SIDE: the eye looks north, so a cave's or a tunnel's mouth that opens north, east or west has its face hidden. Its shade is laid in the
  // paint of the tops round it (m, a top's mouth bits: 1 << d the ground in front of a mouth on its side d, 16 << d the land's top over a mouth that opens on side d; d 0 N, 1 E, 2 S, 3 W):
  // dark toward the mouth over the whole tile, in whole art px, four steps of a 2x2 dither, its corners lighter (a south mouth's ground too, as its face shows). Made with the paint, never by the frame.
  // (Of three tried, mockups "Cave mouths you can see from every side": the ground alone was hidden by the hill itself; a 6-px band on the top was too faint from the meadow)
  const MD = [[0, -1], [1, 0], [0, 1], [-1, 0]], MK = [.38, .52, .68, .84];
  function mouthShade(px, at, st, m) {
    for (let j = 0; j < C; j++) for (let i = 0; i < C; i++) { let k = 1;
      for (let d = 0; d < 4; d++) { if (!(m >> d & 17)) continue;
        const e = [j, 15 - i, 15 - j, i][d], a = d & 1 ? j : i, t = e + Math.max(0, Math.abs(a - 7.5) - 4.5), s = Math.floor(t / 4 + ((i >> 1) + (j >> 1) & 1) * .5);
        if (s < 4) k = Math.min(k, MK[s]); }
      if (k < 1) { const o = at + j * st + i, q = px[o], b = 1 - (1 - k) * .75;   // (a cool shade: its blue kept a little more)
        px[o] = (q & 0xff000000) | Math.round((q >>> 16 & 255) * b) << 16 | Math.round((q >>> 8 & 255) * k) << 8 | Math.round((q & 255) * k); } }
  }
  // a vertex's ten numbers onto a list: an array (a chunk being made) or a kept writer {f: Float32Array, n} (the frame's ghosts and shadows, vox_style.js), grown when full
  const emit = (dst, a, b, c, d, e, f, g, h, i, j) => { if (Array.isArray(dst)) { dst.push(a, b, c, d, e, f, g, h, i, j); return; } if (dst.n + N > dst.f.length) { const w = new Float32Array(dst.f.length * 2 + N); w.set(dst.f); dst.f = w; }
    const F = dst.f; let n = dst.n; F[n++] = a; F[n++] = b; F[n++] = c; F[n++] = d; F[n++] = e; F[n++] = f; F[n++] = g; F[n++] = h; F[n++] = i; F[n++] = j; dst.n = n; };
  const solidC = (c, z) => { if (!c) return false; for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  function create(host, cfg, P) {
    const SL = P.SL, store = new Map(), tops = new Map(), late = new Set(), farOf = new Map(), farDirty = []; let msh = null, making = false, stamp = 0, farN = 0, into = null, wantK = null, fars = 0;   // (farOf: the far land's patches made, by where they are: "bx,by" (8 tiles) -> "x,y,w,h" -> faces; farDirty: boxes of tiles changed since)
    const slot = (k, paint) => { const s = P.slot(k, paint); if (into && P.mk) into.push(s); return s; };   // (into: the places of the paints a chunk or a far patch being made names: kept with it, P.use)
    const lim = (z) => Math.max(cfg.levels[0], Math.min(cfg.levels[1], z)), ck = (x, y) => Math.floor(x / CH) + "," + Math.floor(y / CH);
    // what stands in the land as boxes (host.models: a bridge's deck and posts): a top and a south front each, its paint from the host's sheet px for px into a slot
    const paintOf = new WeakMap(), QC = new Float64Array(12);   // (model: a uv's paint name and painter; a face's four corners)
    const sheet = () => { if (!msh) { const q = host.modelSheet(); msh = q.px ? q : {px: new Uint32Array(q.getContext("2d").getImageData(0, 0, q.width, q.height).data.buffer), w: q.width}; } return msh; };
    const model = (x, y, b, dst) => { const X = x + b.x / C, Y = y + b.y / C, X1 = X + b.w / C, Y1 = Y + b.d / C, Z0 = b.z / cfg.up, Z1 = (b.z + b.h) / cfg.up, Zn = Z1 + (b.tilt ? b.tilt[0] / cfg.up : 0), Zs = Z1 + (b.tilt ? b.tilt[1] / cfg.up : 0);
      const face = (uv, w, h, k) => { if (!uv) return; w = Math.min(C, w); h = Math.min(C, h); const wi = b.win ? b.win[0] : 0, wj = b.win ? b.win[1] : 0, ins = b.shade ? .02 : 0, pw = b.win ? C : w, ph = b.win ? C : h, id = b.sheet ? b.sheet.id : "";
        const ob = typeof uv === "object"; let pk = ob ? paintOf.get(uv) : null; if (!pk || pk.id !== id || pk.pw !== pw || pk.ph !== ph) { const ms = b.sheet; pk = {id, pw, ph, k: "m" + id + uv + "," + pw + "," + ph, paint: (px, at, st) => { const m = ms || sheet(); for (let j = 0; j < ph; j++) for (let i = 0; i < pw; i++) px[at + j * st + i] = m.px[(uv[2] ? uv[1] : uv[1] + j) * m.w + (uv[2] ? uv[0] : uv[0] + i)]; }}; if (ob) paintOf.set(uv, pk); }   // (its paint's name and painter, kept by its uv: they were made again for every face of every shadow, each frame)
        const sl = slot(pk.k, pk.paint), u0 = (sl % SL) * C + wi, v0 = (sl / SL | 0) * C + wj, kind = b.shade ? 10 : b.ghost ? 9 : 8;
        for (let t = 0; t < 6; t++) { const n = TRI[t], o = n * 3; emit(dst, QC[o], QC[o + 2] * H, QC[o + 1], u0 + (n === 0 || n === 3 ? ins : w - ins), v0 + (n < 2 ? ins : h - ins), k, 1, kind, Z1, 0); } };   // (corners in QC: x, y, z each)
      const cq = (a, b2, c, d, e, f, g, h, i, j, k, l) => { QC[0] = a; QC[1] = b2; QC[2] = c; QC[3] = d; QC[4] = e; QC[5] = f; QC[6] = g; QC[7] = h; QC[8] = i; QC[9] = j; QC[10] = k; QC[11] = l; };
      cq(X, Y, Zn, X1, Y, Zn, X1, Y1, Zs, X, Y1, Zs); face(b.top, b.w, b.d, b.k || 1); const fh = b.fh || b.h; if (b.h) { cq(X, Y1, Zs, X1, Y1, Zs, X1, Y1, Z0, X, Y1, Z0); face(b.front, b.w, fh, .85);
        cq(X, Y, Zn, X, Y1, Zs, X, Y1, Z0, X, Y, Z0); face(b.west, b.d, fh, .68); cq(X1, Y1, Zs, X1, Y, Zn, X1, Y, Z0, X1, Y1, Z0); face(b.east, b.d, fh, .74); } };   // (b.sheet: a paint sheet of its own, {px, w, id}; west, east: its sides, d x h px; fh: its front and sides are that many rows of paint over its height; win: [i, j]: its paint is 16 x 16 px and the face shows it from px (i, j) on; a shade's paint is read a hair inside its edges: at an edge it took a px of the paint beside it in the atlas, a thin dark line on the ground; tilt: [n, s]: its top a slope: px its north and its south edge are over its height (a roof's pitch); k: its top's light)
    // a top's paint: the host's; the px it leaves see-through (a cap's inset sides and tucked corners: the classic picture shows the wall there) take the block's own wall tone, stone on stone
    // (they were one earth brown on every block: a brown strip down the west side of each stone step, brown corners, a mountain's terraces a lattice)
    const tones = new Map(), tmp = new Uint32Array(C * C);
    const tone = (lv) => { let v = tones.get(lv); if (v === undefined) { host.paintFront(lv, 0, tmp, 0, C); const n = new Map(); for (let i = 0; i < C * cfg.up; i++) n.set(tmp[i], (n.get(tmp[i]) || 0) + 1); v = [...n].sort((a, b) => b[1] - a[1])[0][0]; tones.set(lv, v); } return v; };
    function topPaint(x, y, z, px, at, st) { host.paintTop(x, y, z, px, at, st); if (!host.paintFront) return; let v = 0;
      for (let j = 0; j < C; j++) for (let i = 0; i < C; i++) if ((px[at + j * st + i] >>> 24) < 128) px[at + j * st + i] = v || (v = tone(lim(VoxMesh.rock(cfg, z, z, !host.rock || host.rock(x, y))))); }
    // a tile's own paints (its top at each height it was asked at): named by its tile, so a tile that changed gets new ones
    const topSlot = (x, y, z, paint, m) => { const k = x + "," + y + "," + z + (m ? "m" + m : ""); return slot(k, (px, at, st) => { const t = x + "," + y; let l = tops.get(t); if (!l) tops.set(t, l = []); if (!l.includes(k)) l.push(k); paint(px, at, st); }); };
    // a tile changed (its ground, its height, what stands as boxes on it): its paints, the paints of the tiles beside it (their rims and lips), and the chunks within six tiles of it (a block is stone by the land three tiles off; a cliff's shadow lies some tiles from it) are no longer good
    function touch(x, y) {
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const t = (x + dx) + "," + (y + dy), l = tops.get(t); if (l) { for (const k of l) P.unslot(k); tops.delete(t); } }
      for (let dy = -6; dy <= 6; dy += 6) for (let dx = -6; dx <= 6; dx += 6) { const k = ck(x + dx, y + dy); store.delete(k); if (making) late.add(k); }
      stamp++; farDirty.push([x, y, x, y]);
    }
    // every tile of a box touched, once: its paints and those round it, the chunks within six tiles of it (a block of land come in at once)
    function touchBox(x0, y0, x1, y1) {
      for (let y = y0 - 1; y <= y1 + 1; y++) for (let x = x0 - 1; x <= x1 + 1; x++) { const t = x + "," + y, l = tops.get(t); if (l) { for (const k of l) P.unslot(k); tops.delete(t); } }
      for (let by = Math.floor((y0 - 6) / CH); by <= Math.floor((y1 + 6) / CH); by++) for (let bx = Math.floor((x0 - 6) / CH); bx <= Math.floor((x1 + 6) / CH); bx++) { const k = bx + "," + by; store.delete(k); if (making) late.add(k); }
      stamp++; farDirty.push([x0, y0, x1, y1]);
    }
    // the far land's patches a changed tile reaches (what they read: the tiles round them, a tile's paint by its rock five tiles off) are made again; a patch is 8 tiles at most
    const farForget = () => { for (const [x0, y0, x1, y1] of farDirty) for (let by = Math.floor((y0 - 16) / CH); by <= Math.floor((y1 + 7) / CH); by++) for (let bx = Math.floor((x0 - 16) / CH); bx <= Math.floor((x1 + 7) / CH); bx++) { const m = farOf.get(bx + "," + by); if (m) { farN -= m.size; farOf.delete(bx + "," + by); } } farDirty.length = 0; };
    const farClear = () => { farOf.clear(); farDirty.length = 0; farN = 0; };
    // (each face's corners: the three cells beside a corner that darken it, worked out once: they were made again as small arrays for every corner of every face)
    const AOV = FACES.map((F) => F.q.map((q) => { const ax = F.n.map((a) => (a ? 0 : 1)), d = [q[0] * 2 - 1, q[1] * 2 - 1, q[2] * 2 - 1].map((v, j) => v * ax[j]);
      const t = [0, 1, 2].filter((j) => ax[j]), a = [0, 0, 0], b = [0, 0, 0]; a[t[0]] = d[t[0]]; b[t[1]] = d[t[1]]; return [a, b, [a[0] + b[0], a[1] + b[1], a[2] + b[2]]]; })), AOK = [1, .84, .72, .62], TRI = [0, 1, 2, 0, 2, 3], vq = new Float64Array(40);
    function quad(out, x, y, z, F, k, sky, kind, lv, e, s, solid, isTop) {
      const u0 = (s % SL) * C, v0 = (s / SL | 0) * C, top = isTop ? 0 : C - cfg.up, I = .01, A = AOV[FACES.indexOf(F)], ox = x + F.n[0], oy = y + F.n[1], oz = z + 1 + F.n[2];   // (read a hair inside its paint: at an edge a row of px took the paint beside it in the sheet: a bright line across a stone terrace)
      for (let i = 0; i < 4; i++) {
        const q = F.q[i], o = i * 10; let ao = 1;
        if (solid && !(isTop && sky && e & 262144)) { const [a, b, c] = A[i], s1 = +solid(ox + a[0], oy + a[1], oz + a[2]), s2 = +solid(ox + b[0], oy + b[1], oz + b[2]), cc = +solid(ox + c[0], oy + c[1], oz + c[2]); ao = AOK[s1 && s2 ? 3 : s1 + s2 + cc]; }
        vq[o] = x + q[0]; vq[o + 1] = (z + q[2]) * H; vq[o + 2] = y + q[1]; vq[o + 3] = u0 + (i === 0 || i === 3 ? I : C - I); vq[o + 4] = v0 + (i < 2 ? top + I : C - I); vq[o + 5] = k * ao; vq[o + 6] = sky; vq[o + 7] = kind; vq[o + 8] = lv; vq[o + 9] = e;
      }
      if (!sky) { const m = (vq[5] + vq[15] + vq[25] + vq[35]) / 4; vq[5] = vq[15] = vq[25] = vq[35] = m; }   // (a face of a cave: one tone a face. Its corners' shade ran in steps across each face: rows of dark spikes, a comb, along every cut edge)   // (a hole's floor (e 262144) has no corner shade: its walls' feet are shaded in the shader, px by px. The corners' shade was laid in steps of a twentieth across each of its tiles: nested flat squares in a pit's corners and along its north edge)
      for (const i of TRI) for (let j = i * 10; j < i * 10 + 10; j++) out.push(vq[j]);
    }
    // YOUR SPACE AND THE WINDOW ON IT (o.win: {reach, walk: on the surface, for a cave's mouth or a hole beside you: where you can walk and drop to, not the floors you came down from}). The land is made WHOLE, always: under the land you are seen through a window, a mask the painter makes from a few boxes
    // (vox_style_win.js), not through a hole cut in these faces: no chunk hangs on where you are. Here only the boxes are found: the tiles walked to from yours (reach steps), each from its floor to its ceiling.
    function* steps(cx, cy, L, o) {
      const cols = new Map(), r = o.r, deep = o.deep, pt = o.win || null, fresh = new Map(); let made = 0;
      const col = (x, y) => { const k = x * 1048576 + y; let c = cols.get(k); if (c === undefined) { c = host.column(x, y); cols.set(k, c); } return c; };   // (a number for a key: a string was made for each of the land's many looks)
      const inBox = (x, y) => Math.abs(x - cx) <= r && Math.abs(y - cy) <= r;
      const D = 2 * r + 1, NO = -32768, BIG = 32767, DIR = [[1, 0], [-1, 0], [0, 1], [0, -1]], at = (x, y) => (inBox(x, y) ? (y - cy + r) * D + x - cx + r : -1);
      const reachA = new Int16Array(D * D).fill(NO), farA = new Uint8Array(D * D), nearA = new Uint8Array(D * D), clsA = new Uint8Array(D * D), lowA = new Int16Array(D * D).fill(BIG), reached = [], win = [];
      const topOf = (x, y) => { const c = col(x, y); return c && c.length ? c[c.length - 1] : NO; };
      const hop = (x0, y0, x1, y1, h) => { const a = col(x0, y0), b = col(x1, y1); return !!a && !!b && solidC(a, h) && !solidC(a, h + 1) && !solidC(a, h + 2) && solidC(b, h + 1) && !solidC(b, h + 2); };   // (the game's own rule: from a floor at h a jump up one level, room over it and over your head)
      // where a step from (x0, y0) at f0 onto (x, y) lands, by the game's own walk: level, up one (hop), or down any drop with nothing in the way -> the floor's level (as a drop of two or more: + .5: no way back up), or null: a wall
      // (it was any floor within two levels: a stair's treads two levels over a dead end were "your space", lit and lipped as the next step)
      const floorOf = (x0, y0, x, y, f0) => { const c = col(x, y); if (!c || !c.length) return null; if (host.water && host.water(x, y) && host.waterTop) { const w = host.waterTop(x, y); if (w >= c[c.length - 1]) return Math.abs(w - f0) <= 1 ? w : null; }
        if (solidC(c, f0 + 1)) return hop(x0, y0, x, y, f0) || (host.water && host.water(x0, y0) && !solidC(c, f0 + 2)) ? f0 + 1 : null; for (let dz = 0; dz <= 8; dz++) if (solidC(c, f0 - dz)) return f0 - dz + (dz > 1 ? .5 : 0); return null; };
      // A MOUTH: from the open floor f on (ox, oy) a step by the game's own walk into (mx, my) lands under land (a roof over your head), and on from there, straight in, under land again:
      // a way in. A wall (no step in), a ledge of one tile over the ground (no way on from under it), water: none
      const inTo = (x0, y0, x, y, f) => { if (host.water && host.water(x, y)) return null; const g = floorOf(x0, y0, x, y, f); return g !== null && g % 1 === 0 && topOf(x, y) > g + 1 ? g : null; };
      const mouth = (ox, oy, f, mx, my) => { if (host.water && host.water(ox, oy)) return false; const g = inTo(ox, oy, mx, my, f); return g !== null && inTo(mx, my, 2 * mx - ox, 2 * my - oy, g) !== null; };
      const mouths = (x, y, z) => { let m = 0; for (let d = 0; d < 4; d++) { const X = x + MD[d][0], Y = y + MD[d][1], t = topOf(X, Y); if (t > z + 1 && mouth(x, y, z, X, Y)) m |= 1 << d; else if (d !== 2 && t < z - 1 && mouth(X, Y, t, x, y)) m |= 16 << d; } return m; };   // (this top under the sky: in front of a mouth on side d, or over one that opens on side d; the eye sees a south one's face)
      // from a floor at f0 on (x0, y0): the floors of (x, y) over it (up to 8 levels) from which a step lands on f0: the way you came down by
      const upsOf = (x0, y0, x, y, f0) => { const c = col(x, y), l = []; if (c) for (let j = 0; j < c.length; j += 2) { const f = c[j]; if (f > f0 && f <= f0 + 8) { const g = floorOf(x, y, x0, y0, f); if (g !== null && Math.floor(g) === f0) l.push(f); } } return l; };
      // YOUR SPACE, three passes: 1 where you can WALK, there and back; 2 from there where you can only drop to and on from there; 3 the floors you could have dropped FROM, and on from those (the stair over the room you
      // dropped into). The window is on all three, so a walk along one cave, down its drops, does not change it (it was 1 and 2 alone: the step off a stair into a room was another space, another hole, in one frame:
      // a quarter of the px). Only the LIGHT tells them apart (cls -> the painter's light of the space, vox_style.js: 1 warm, 2 dimmer, 3 cold), and that eases. A tile has ONE level: a floor under the land
      // before one under the sky (the meadow over a room is of your space too, by the stair's mouth: found first it kept the room shut till you were near), else the first found; the flood goes on through its other floors (treads over a passage)
      if (pt) { let L0 = L; const c0 = col(cx, cy); if (c0 && !(host.water && host.water(cx, cy))) for (let n = 0; n < 8 && !solidC(c0, L0); n++) L0--;   // (in the air, a jump, a fall: your space is the floor's under you. From a level in mid air the flood found another space for the frames of a fall: the picture flashed)
        const i0 = at(cx, cy), lim = pt.reach, nodes = [[cx, cy, L0, 0]], seenN = new Set([i0 * 2048 + L0 + 1024]); reachA[i0] = L0; clsA[i0] = 1; nearA[i0] = 1; reached.push(i0);
        for (const pass of pt.walk ? [1, 2] : [1, 2, 3]) { let fr = nodes.slice();
          for (let d = 1; d <= lim && fr.length; d++) { const nx = []; for (const [x, y, f0, o] of fr) { if (o > 4) continue; for (const [dx, dy] of DIR) { const X = x + dx, Y = y + dy, i = at(X, Y); if (i < 0) continue; const f1 = floorOf(x, y, X, Y, f0), l = pass > 2 ? upsOf(x, y, X, Y, f0) : [];   // (o: steps under the open sky since the last floor under the land: the flood stops five out on a meadow: it ran over the whole surface, 8 ms of one frame, for nothing: only what is under land is looked into)
            if (f1 !== null && (pass > 1 || f1 % 1 === 0)) l.push(Math.floor(f1));
            for (const f of l) { const k = i * 2048 + f + 1024; if (seenN.has(k)) continue; seenN.add(k); nx.push([X, Y, f, topOf(X, Y) <= f && !(host.sunk && host.sunk(X, Y, f)) ? o + 1 : 0]);
              if (reachA[i] === NO) { reachA[i] = f; clsA[i] = pass; reached.push(i); if (d > 2 || pass > 1) farA[i] = 1; if ((d <= 4 && pass === 1) || (pt.walk && Math.abs(X - cx) + Math.abs(Y - cy) <= 4)) nearA[i] = 1; } else if (farA[i] && topOf(X, Y) <= reachA[i] && topOf(X, Y) > f) { reachA[i] = f; clsA[i] = pass; } } } } for (const q of nx) nodes.push(q); fr = nx; } }
        for (const [x, y, f] of nodes) { const i = at(x, y); if (f < lowA[i] && reachA[i] - f <= 4) lowA[i] = f; } }   // (lowA: where a tile has two floors of your space near each other, treads over a passage: the lower: the window goes down to it whichever you stand on)
      if (pt) yield "flood";
      // THE WINDOW'S BOXES: a floor of your space under the land: from it (the lower of two near each other) up to its ceiling, six levels at most; under the open sky (a shaft, a trench, a gorge's floor) only
      // the sunk tiles within four steps of you, each up to the rim of the land beside it: what stands between the eye and you is looked through, the rest of the gorge is as it is;
      // the ones land hides (host.sunk) as far as your space goes (it was a square five tiles round you: the gorge's river was shut past it; four steps was a diamond: its stairs left notches of the cliff's top standing in the river)
      for (const i of reached) { const x = cx - r + i % D, y = cy - r + (i / D | 0), f = reachA[i], tp = topOf(x, y), c = col(x, y);
        if (pt.walk && (Math.abs(x - cx) + Math.abs(y - cy) > 2 || f < L - 3)) continue;   // (from the surface only what you are about to step into: two tiles off, three levels down at most: a tunnel was opened through its hill's front from four tiles away, a room from the hill over it)
        if (tp > f) { let z = f; while (z < f + 6 && !solidC(c, z + 1)) z++; win.push([x, y, Math.min(f, lowA[i]), Math.max(z, f + 1)]); }
        else if (nearA[i] || (clsA[i] === 1 && !!host.sunk && host.sunk(x, y, f))) { let h = f + 1, n = 0; for (const [dx, dy] of DIR) { const t = topOf(x + dx, y + dy); if (t >= f + 2) n++; h = Math.max(h, Math.min(f + 40, t)); } const hid = !!host.sunk && host.sunk(x, y, f); if (hid || (!farA[i] && !pt.walk)) win.push([x, y, f, n > 2 ? h : f + 2, 1]); } }   // (host.sunk(x, y, f): the HOST's one answer to "is this tile under the open sky IN the land": land hides it from the eye and stands north of it too: a pit, a trench, a gorge's floor; the ground behind a hill or a wall is not, and is never a box: standing on a small hill its top was opened onto the meadow behind it. When land hides you, also the tiles within two steps of you: one hole, not a patch a tile. Walls on three sides or four, a shaft: up to its rim, the window joins its mouth; else two levels: in a gorge the boxes stood as high as its banks, their long edges drawn down the far bank)
      // OTHER SPACES: a hollow beside the window (three tiles out at most, its floor near your floors' heights): the passage past a wall, the treads you cannot reach: the window is on it too. Its floor is not of your space:
      // the painter draws it cold, at its own height: it is seen where the way on is
      if (pt && !pt.walk) { const own = new Set(win.map((t) => t[0] + "," + t[1])); let fr = win.slice();
        for (let d = 0; d < 3 && fr.length; d++) { const nx = []; for (const [x, y, lo, hi] of fr) for (const [dx, dy] of DIR) { const X = x + dx, Y = y + dy, k = X + "," + Y, c = own.has(k) || !inBox(X, Y) ? null : col(X, Y); if (!c) continue;
          for (let j = 0; j + 2 < c.length; j += 2) if (c[j] >= lo - 4 && c[j] <= hi + 6) { own.add(k); const t = [X, Y, c[j], Math.min(c[j] + 6, c[j + 1])]; win.push(t); nx.push(t); break; } } fr = nx; } }
      const solidIn = (x, y, z) => { const c = col(x, y); if (!inBox(x, y)) return solidC(c, z); if (z <= L - deep) return true; return solidC(c, z); };
      const front = (x, y, z, top, two) => { const lv = lim(VoxMesh.rock(cfg, top, z, !host.rock || host.rock(x, y))), v = VoxMesh.pick(x, y, z, cfg.variants), b = host.built && host.built(x, y) ? 1 : 0; return slot((two ? "F" : "f") + lv + "," + v + (b ? "b" : ""), (px, at, st) => { host.paintFront(lv, v, px, at + (C - cfg.up) * st, st, b); if (two) host.paintFront(lv, v, px, at, st, b); }); };   // (two: its rows twice: a tile's whole top)
      const rx = Math.min(r, o.rx || r), X0 = cx - rx, X1 = cx + rx, Y0 = cy - r, Y1 = cy + Math.min(r, o.rs || r);
      const good = (ch, bx, by) => !!ch && ch.mk === (host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "") && (ch.low ? ch.L === L : ch.lo - 1 > L - deep);
      function* chunk(bx, by) {
        const out = {main: [], model: [], shade: [], water: []}; let lo = 1e9, low = false, wet = 0;
        const faces = (x, y, z, dst) => {
          const c = col(x, y), open = c[c.length - 1], top = VoxMesh.topOf(c, z);
          for (let f = 0; f < 6; f++) {
            const F = FACES[f], nx = x + F.n[0], ny = y + F.n[1], nz = z + F.n[2];
            if (f === 1 || solidIn(nx, ny, nz)) continue;
            const nc = col(nx, ny); let sky = (f === 0 ? z >= open : !nc || z > nc[nc.length - 1]) ? 1 : 0, s, kind = f === 0 ? 1 : 0, e = 0;
            if (f === 0) {
              const mo = sky ? mouths(x, y, z) : 0; s = topSlot(x, y, z, (px, at, st) => { topPaint(x, y, z, px, at, st); if (mo) mouthShade(px, at, st, mo); }, mo);
              { [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if (!solidIn(x + dx, y + dy, z) && (sky || solidIn(x + dx, y + dy, z - 1))) e |= b; });   // (a lip: under a roof only at a step of one level, one you can take; a drop of two or more has none)
                if (sky) [[0, -1, 64], [1, 0, 128], [-1, 0, 256], [0, 1, 2048]].forEach(([dx, dy, b]) => { if (!solidIn(x + dx, y + dy, z) && !solidIn(x + dx, y + dy, z - 1) && !solidIn(x + dx, y + dy, z - 2)) e |= b; });   // (a top under the sky: its edge over a drop of three levels or more, one that hurts: a dark rim, the shader's; a step has the light lip)
                if (!sky) [[0, -1, 64], [1, 0, 128], [-1, 0, 256]].forEach(([dx, dy, b]) => { if (!solidIn(x + dx, y + dy, z) && !solidIn(x + dx, y + dy, z - 1)) e |= b; });   // (a floor under a roof: its edge over a drop of two levels or more, north, east, west (its south one shows the wall's face): a thick dark rim: from above a wall that faces east or west is not seen at all)
                if (!sky) [[0, -1, 512], [1, 0, 1024], [0, 1, 2048], [-1, 0, 4096]].forEach(([dx, dy, b]) => { if (solidIn(x + dx, y + dy, z + 1) && !hop(x, y, x + dx, y + dy, z)) e |= b; });   // (a floor under a roof: a WALL at that edge (too high to jump, or no room to): its foot in shade; a step you can take has none)
                { const wl = DIR.map(([dx, dy]) => +solidIn(x + dx, y + dy, z + 1)), sunk = sky && ((wl[0] && wl[1]) || (wl[2] && wl[3]) || wl[0] + wl[1] + wl[2] + wl[3] >= 3); if (sunk) e |= 131072;   // (a top under the sky with walls on two sides that face each other, or on three: a trench's floor, a dug stair's tread, a shaft's: where it is of your space it is a floor as one under the land is: the same warm light. They were the sun's shade and the corners' on bare earth: grey squares, on the very stair whose covered treads were warm)
                  if (!sky || sunk) [[0, -1, 8192], [1, 0, 16384], [-1, 0, 65536]].forEach(([dx, dy, b]) => { if (hop(x, y, x + dx, y + dy, z)) e |= b; });
                  if (sky && DIR.filter(([dx, dy]) => { for (let d = 1; d <= 2; d++) if (topOf(x + dx * d, y + dy * d) > z) return true; return false; }).length >= 2) { e |= 262144; wl.forEach((w, i) => { if (w) e += 524288 * 2 ** i; }); } }   // (IN A HOLE: land over it within two tiles on two sides or more: a pit's, a trench's, a shaft's floor: a step darker than the ground round it, the shader's; and which of its edges are a wall's foot (524288 << i, DIR's E W S N): its shade there, px by px, the shader's)   // (the foot of a step UP you can take, north, east, west: a dark line there (the riser's foot): with the lit lip of the tread over it a step is a step)
              }   // (ONE floor rule under the land: every floor of your space the same warm light, a room's or a stair's (they were two, by how many tiles lay on one level: a floor changed its light as you walked); 64: a floor under the land that is NOT of your space, you cannot walk to it: bare rock, no light, no lip; 128: one you can only drop to: dimmer)
            } else { s = front(x, y, z, top); if (!sky && !solidC(c, z + 1) && hop(nx, ny, x, y, z - 1)) e |= 16; else if (sky && nc && top - nc[nc.length - 1] >= 3) e |= 64 * Math.min(3, (top - z) >> 1); }   // (64, 128: the face of a drop of three or more: darker every two levels down, three steps)   // (the riser of a step you can take: light, the tread's own tone; any other face is a wall)
            if (cfg.rock && VoxMesh.rock(cfg, top, top, !host.rock || host.rock(x, y)) >= cfg.rock.from) e += 8388608;   // (its ground is stone, as its walls are painted: the x-ray's cut shows it so, vox_style_glsl.js cut)
            quad(dst, x, y, z - 1, F, F.k, sky, kind, z, e, s, solidIn, f === 0);
          }
        };
        // (a cell under the lowest air of its own column and of the four beside it has no face: the levels start there, not 20 under your feet: a tenth of the cells)
        const lowOf = (x, y) => { const c = col(x, y); return c && c.length ? c[0] : -1e9; };
        for (let y = by * CH; y < by * CH + CH; y++) for (let x = bx * CH; x < bx * CH + CH; x++) {
          const c = col(x, y); if (!c) continue; yield; const cz = c[c.length - 1]; { const ms = host.models && host.models(x, y, cz); if (ms) for (const b of ms) model(x, y, b, b.shade ? out.shade : out.model); }   // (cz: the land's top there)
          const wt = host.water && host.water(x, y), wz = wt ? (host.waterTop ? host.waterTop(x, y) : 0) : null;
          const z0 = Math.min(lowOf(x, y), lowOf(x - 1, y), lowOf(x + 1, y), lowOf(x, y - 1), lowOf(x, y + 1)); if (z0 < lo) lo = z0; if (z0 - 1 <= L - deep) low = true;   // (low: the 20 levels under your feet cut it short: it hangs on your level)
          for (let z = Math.max(L - deep + 1, z0); z <= Math.max(cz, wt ? wz + 1 : -1e9); z++) {
            if (!solidIn(x, y, z)) { if (wt && z === wz + 1) { quad(out.water, x, y, z - 2, FACES[0], 1, 1, 3, z, Math.max(0, wz - c[c.length - 1]), 0, null, true); wet++; } continue; }   // (e: how deep the water is here, levels)
            faces(x, y, z, out.main);
          }
        }
        const ch = {mk: host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "", lo, low, L, wet}; for (const k of KINDS) ch[k] = new Float32Array(out[k]); return ch;
      }
      // past the box, to the horizon, in patches: the sea's flat face where the sea is (or nothing is known); where land is, the land at its height, a skirt south, west and east of it: no sea inland.
      // Their px are the land's own at the land's own size (the shader, kind 7): a top an 8 x 8 quarter of a tile's paint, which quarter and which way round by the tile it lies on; a skirt its rock's front (e: 9 a top, 10 a south skirt, 11 a west or east one). They were the paint's mean colour: flat slabs.
      // Patches are 4 tiles across for the first 16 tiles past the box, 8 beyond (8 everywhere: a mountain's flank one smooth slab a patch wide); a top's paint is a tile of the patch at its height with its four neighbours as high (its middle tile was often a rim: a stripe of the rim's brown and green over the whole patch)
      // THE PATCHES LIE ON THE WORLD'S OWN GRID (4 and 8 tiles: x, y multiples of them), cut only at the box's edges and the far edge: walking, the patches are the ones made a step before, kept (farOf).
      // (They were counted from you: a step east and every patch was 1 tile off the last one's, all made again, 3 steps in 4, with their tops' paints: half of a land's making at a sprint, and
      //  the far land changed at each step, each patch's height read from other tiles: the far hills shimmered as you walked)
      function* patches() { const fl = [], fs = []; if (o.sea === undefined) return [new Float32Array(0), new Float32Array(0)];
        const cut = (a, b, s, l = []) => { for (let v = a; v < b;) { const e = Math.min(b, (Math.floor(v / s) + 1) * s); l.push([v, e - v]); v = e; } return l; };
        const ax = (c, box, one) => { const lo = c - r - 40, hi = c + r + 41, a4 = Math.floor((c - r - 16) / 8) * 8, b4 = Math.ceil((c + r + 17) / 8) * 8;   // (along one axis round c: 8s past the 4s, the 4s from 16 past the box; box: the box's own span left out, or one: a tile a patch over it)
          const mid = box ? cut(a4, c - r, 4).concat(one ? cut(c - r, c + r + 1, 1) : [], cut(c + r + 1, b4, 4)) : cut(a4, b4, 4); return cut(lo, a4, 8).concat(mid, cut(b4, hi, 8)); };
        const out = ax(cx, false), side = ax(cx, true), one = ax(cx, true, true), b4 = Math.ceil((cy + r + 17) / 8) * 8;
        const rows = cut(cy - r - 40, Math.floor((cy - r - 16) / 8) * 8, 8).map((q) => [...q, out]).concat(cut(Math.floor((cy - r - 16) / 8) * 8, cy - r, 4).map((q) => [...q, out]), cut(cy - r, cy + r + 1, 4).map((q) => [...q, side]),
          cut(cy + r + 1, cy + r + 5, 1).map((q) => [...q, one]), cut(cy + r + 5, b4, 4).map((q) => [...q, out]), cut(b4, cy + r + 41, 8).map((q) => [...q, out]));   // (the first four rows south of the box a tile each, its own paint (e 8): tall land there stands at the screen's foot, a tile as big as a hand)
        const tz = (x, y) => { const c = host.column(x, y); return c && c.length ? c[c.length - 1] : null; }, flat = (x, y, z) => tz(x - 1, y) === z && tz(x + 1, y) === z && tz(x, y - 1) === z && tz(x, y + 1) === z;
        for (const [y, h, cols] of rows) { yield "far"; if (farDirty.length) farForget(); for (const [x, w] of cols) { const bk = Math.floor(x / CH) + "," + Math.floor(y / CH), fk = x + "," + y + "," + w + "," + h; let m = farOf.get(bk); const had = m && m.get(fk);
          if (had) { P.use(had[2]); if (had[0].length) fl.push(had[0]); if (had[1].length) fs.push(had[1]); continue; } const a = [], b = []; into = []; fars++; patch(x, y, w, h, a, b); const f = [new Float32Array(a), new Float32Array(b), into]; into = null; if (!m) farOf.set(bk, m = new Map()); m.set(fk, f); farN++; if (a.length) fl.push(f[0]); if (b.length) fs.push(f[1]); if (farN % 6 === 0) yield "far"; }   // (a step: six patches made, not a row of them: a slow phone's frame waited for 27)
          if (farN > 12000) farClear(); }   // (a patch's faces kept by where it is: walking, the patches 4, 8 tiles back are this one's; 4 ms of each land's 6 were the far land made again)
        return [cat(fl), cat(fs)];
        function patch(x, y, w, h, fl, fs) { let mx = x + (w >> 1), my = y + (h >> 1); const c = host.column(mx, my), land = c && c.length && !(host.water && host.water(mx, my));
          const Q = [[1, 1], [3, 1], [1, 3], [3, 3]].map(([a, b]) => [x + (w * a >> 2), y + (h * b >> 2)]).filter(([qx, qy]) => tz(qx, qy) !== null && !(host.water && host.water(qx, qy)));
          let z = land ? c[c.length - 1] : o.sea; if (land) for (const [qx, qy] of Q) z = Math.min(z, tz(qx, qy));   // (the lowest of five tiles: a patch as high as its highest stood over the land in front of it, a slab over a stair)
          if (land && !(tz(mx, my) === z && flat(mx, my, z))) { const q = Q.find(([qx, qy]) => tz(qx, qy) === z && flat(qx, qy, z)) || Q.find(([qx, qy]) => tz(qx, qy) === z); if (q) [mx, my] = q; }   // (a tile whose top is at z: one as high round it if there is one)
          const sl = land ? topSlot(mx, my, z, (px, at, st) => topPaint(mx, my, z, px, at, st)) : 0, fr = land && host.paintFront ? front(mx, my, z, z) : sl;
          const put = (q, k, s, e) => { const u0 = land ? (s % SL) * C : 0, v0 = land ? (s / SL | 0) * C : 0, dst = land ? fl : fs, kind = land ? 7 : 3; for (let t = 0; t < 6; t++) { const p = q[TRI[t]]; emit(dst, p[0], p[2] * H, p[1], u0, v0, k, 1, kind, z, e); } };   // (no vertex made as an array of its own)
          put([[x, y, z], [x + w, y, z], [x + w, y + h, z], [x, y + h, z]], 1, sl, w * h === 1 && tz(x, y) === z ? 8 : 9);
          if (land) { const lo = (t) => Math.min(z - 10, t === null ? o.sea : t), s = lo(tz(mx, y + h)), wz = lo(tz(x - 1, my)), ez = lo(tz(x + w, my));   // (each skirt down to the land beside it: ten levels were a mountain's patches hung in the air over the meadow, the sky under them)
            put([[x, y + h, z], [x + w, y + h, z], [x + w, y + h, s], [x, y + h, s]], .8, fr, 10); put([[x, y, z], [x, y + h, z], [x, y + h, wz], [x, y, wz]], .7, fr, 11); put([[x + w, y + h, z], [x + w, y, z], [x + w, y, ez], [x + w, y + h, ez]], .78, fr, 11); } } }
      const want = []; for (let by = Math.floor(Y0 / CH); by <= Math.floor(Y1 / CH); by++) for (let bx = Math.floor(X0 / CH); bx <= Math.floor(X1 / CH); bx++) want.push([bx, by]);
      if (P.start(!!o.again)) { store.clear(); farClear(); }   // (a land made with its paints from none keeps no chunk made before: they name places of paints that are gone. The land was wiped (eng.lost: forget) while one was being made, that one's chunks were kept, and the next, from none, drew them with other tiles' paints: grey and green squares on a meadow, the mean colour, a shadow's black blades on the grass)
      making = true; late.clear();   // (the paints and the land that names them change together: vox_style.js)
      try {
        const need = want.filter(([bx, by]) => !good(store.get(bx + "," + by), bx, by)); wantK = new Set(want.map(([bx, by]) => bx + "," + by)); yield "scan";
        for (const [bx, by] of want) { const ch = store.get(bx + "," + by); if (ch && !need.some((q) => q[0] === bx && q[1] === by)) P.use(ch.slots); }   // (the paints of the chunks kept: this land's too)
        for (const [bx, by] of need) { into = []; const ch = yield* chunk(bx, by); ch.slots = into; into = null; fresh.set(bx + "," + by, ch); made++; }
        const [fl, fs] = yield* patches();
        if (P.spill() && !o.again) { making = false; return yield* steps(cx, cy, L, Object.assign({}, o, {again: true})); }   // (the paints ran out while it was made: faces made before that had another face's paint (a meadow all earth, a black hole): once more, from none)
        const list = want.map(([bx, by]) => fresh.get(bx + "," + by) || store.get(bx + "," + by)).filter(Boolean), parts = {far: fl, sea: fs}; let wet = 0;
        const near = list.slice().reverse();   // (the land's own faces: the chunks nearest the eye first (the south ones), so the GPU drops the px of what is behind them before painting them; it was far to near: every hidden px painted, then painted over)
        for (const k of KINDS) { const l = k === "main" ? near : list; let n = 0; for (const ch of l) n += ch[k].length; const d = new Float32Array(n); n = 0; for (const ch of l) { d.set(ch[k], n); n += ch[k].length; } parts[k] = d; }
        for (const ch of list) wet += ch.wet;
        for (const [k, ch] of fresh) if (!late.has(k)) store.set(k, ch);   // (a tile changed in it while it was made: not kept, made again next time)
        if (store.size > 400) { const keep = new Set(want.map(([bx, by]) => bx + "," + by)); for (const k of store.keys()) if (!keep.has(k)) store.delete(k); }
        return {parts, clip: [X0, X1 + 1, Y0, Y1 + 1], wet, made, space: pt ? {x: cx - r, y: cy - r, D, lvl: reachA, cls: clsA} : null, win};
      } finally { making = false; }
    }
    return {steps, touch, touchBox, model, clear() { store.clear(); farClear(); }, evicted() { for (const k of [...store.keys()]) if (!wantK || !wantK.has(k)) store.delete(k); farClear(); },   // (paints given again: what was made with them and is not of this land goes)
      get stamp() { return stamp; }, get fars() { return fars; }};   // (fars: far patches made, all told: tests)
  }
  return {create, N, CH};
})();
