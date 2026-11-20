// VOX: the 2.5D look's land as faces (vox_style.js draws them). No game global: the host is the engine's own.
// The land is kept in CHUNKS of 8 x 8 tiles, each its own lists of faces. A land asked for again (you walked a tile,
// a tile changed) makes only the chunks that are new or no longer good: the ones coming into view, the ones a tile
// changed in (touch), the ones the cut round you lies on. The rest are kept as they are. What is good:
//   a chunk away from the cut hangs on the world alone (its columns, its paints, host.chunkKey: what stands in it);
//   a chunk the cut touches (o.cut's box, your own space) hangs on where you are too: made again each time;
//   the far land and sea (o.sea), patches measured from you: made again each time, a list of their own (far).
// The lists are not cut to the rows and columns asked: the painter leaves out what is outside them (uniform cl).
//   VoxStyleLand.create(host, cfg, P) -> {steps(cx, cy, L, ceil, o) (a generator: a tile a step; its last
//     value: null, or {parts: {main, model, shade, water, over, far, sea: Float32Array}, clip: [x0, x1, y0, y1], wet,
//     skies, holes, made: chunks made}), touch(x, y), clear()}
//   P (the paints, vox_style.js): {SL, C, slot(key, paint) -> its place, unslot(key), start(again), spill() -> did they run out}
const VoxStyleLand = (() => {
  const H = .5, C = 16, N = 10, CH = 8, KINDS = ["main", "model", "shade", "water", "over"];
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
    function* steps(cx, cy, L, ceil, o) {
      const cols = new Map(), r = o.r, deep = o.deep, whole = !!o.box || !o.cut || !!o.over, fresh = new Map(); let made = 0;   // (whole: a caller with no box round you (underground.js): the cut is the whole land: every chunk each time)
      const col = (x, y) => { const k = x + "," + y; if (!cols.has(k)) cols.set(k, host.column(x, y)); return cols.get(k); };
      const inBox = (x, y) => Math.abs(x - cx) <= r && Math.abs(y - cy) <= r;
      // (under: the slice height, one field over the box round you: a tile of your space its floor + 2, a rock tile the nearest space tile's (ties: the lower). In rows of numbers, a tile a number: they were lists by name, made again for 2400 tiles each time: 4 ms of one step)
      const D = 2 * r + 1, NO = -32768, DIR = [[1, 0], [-1, 0], [0, 1], [0, -1]], at = (x, y) => (Math.abs(x - cx) <= r && Math.abs(y - cy) <= r ? (y - cy + r) * D + x - cx + r : -1);
      const reachA = new Int16Array(D * D).fill(NO), cutA = new Int16Array(D * D).fill(NO), distA = new Uint8Array(D * D).fill(255), roomA = new Uint8Array(D * D), reached = [];
      const reachOf = (x, y) => { const i = at(x, y); return i < 0 || reachA[i] === NO ? undefined : reachA[i]; }, isRoom = (x, y) => { const i = at(x, y); return i >= 0 && roomA[i] === 1; };
      const inR = (x, y) => !o.cut || (y - cy >= -o.cut.n && y - cy <= o.cut.s && Math.abs(x - cx) <= o.cut.w);   // (?hd: the slice only in a box round you; outside it the whole land)
      const cutOf = (x, y, top) => { if (o.under && top < 1e8 && !inR(x, y)) { const c = col(x, y); return c ? c[c.length - 1] : top; } if (!o.under || top > 1e8 || !reached.length) return top; const v = cutA[at(Math.max(cx - r, Math.min(cx + r, x)), Math.max(cy - r, Math.min(cy + r, y)))]; return v === NO ? top : v; };
      const floorOf = (x, y) => { const c = col(x, y); if (!c || !inBox(x, y)) return null; const t = c[c.length - 1];   // (a hollow's floor near your level, if the tile is one)
        for (let z = L - deep + 1; z <= L + 6 && z < t; z++) if (!solidC(c, z)) return z - 1; return null; };
      const st = [cx, cy, L];   // (your own space: tiles walked to from you, a step or a short drop, their floors)
      while (o.under && st.length) { const f0 = st.pop(), y = st.pop(), x = st.pop(), i = at(x, y); if (i < 0 || reachA[i] !== NO) continue; const f = floorOf(x, y); if (f === null || Math.abs(f - f0) > 2) continue; reachA[i] = f; reached.push(i); for (const [dx, dy] of DIR) st.push(x + dx, y + dy, f); }
      const grp = new Uint8Array(D * D), next = (i, fn) => { const x = i % D, y = i / D | 0; for (const [dx, dy] of DIR) { const X = x + dx, Y = y + dy; if (X >= 0 && Y >= 0 && X < D && Y < D) fn(Y * D + X); } };   // (the floors of your space that are a room's: 4 or more tiles on one level together; the rest are treads and landings of a stair)
      for (const i0 of reached) { if (grp[i0]) continue; const g = [i0]; grp[i0] = 1; for (let n = 0; n < g.length; n++) next(g[n], (j) => { if (!grp[j] && reachA[j] === reachA[i0]) { grp[j] = 1; g.push(j); } }); if (g.length >= 4) for (const i of g) roomA[i] = 1; }
      let fr = reached.slice(), dd = 0; const nv = new Int16Array(D * D).fill(32767); for (const i of fr) { cutA[i] = reachA[i] + 2; distA[i] = 0; }
      while (fr.length) { const nx = []; for (const i of fr) { const v = cutA[i]; next(i, (j) => { if (distA[j] !== 255) return; if (nv[j] === 32767) nx.push(j); if (v < nv[j]) nv[j] = v; }); }
        fr = nx; dd++; for (const j of fr) { cutA[j] = nv[j]; distA[j] = dd; } }
      const far = (x, y) => { const i = at(x, y); return !o.cut && (i < 0 || distA[i] === 255 ? 9 : distA[i]) > 2; };   // (beyond 2 tiles: one flat height for the whole box, the lowest cut near you: no edges far off)
      if (reached.length) for (let i = 0; i < D * D; i++) if (distA[i] > 0 && distA[i] <= 2) { const x = i % D, y = i / D | 0;   // (the camera's side: rock south of your space cut at its floor, the treads show)
        for (let j = 1; j <= 2; j++) { const f = y - j >= 0 ? reachA[i - j * D] : NO; if (f !== NO) { cutA[i] = Math.min(cutA[i], f); break; } } }
      if (reached.length) for (let i = 0; i < D * D; i++) { const d = distA[i]; if (d === 255) continue; if (d > 2) cutA[i] = L + 2; else if (d === 2 && reachA[i] === NO) cutA[i] = Math.max(L, Math.min(L + 4, cutA[i])); }   // (far: one height, your ceiling; the ring by it within 2 levels of it)
      const solidIn = (x, y, z, top) => { top = cutOf(x, y, top); if (!inBox(x, y)) return !o.box && z <= top && solidC(col(x, y), z); if (z <= L - deep) return !o.box; return z <= top && solidC(col(x, y), z); };
      const front = (x, y, z, top) => { const lv = lim(VoxMesh.rock(cfg, top, z, !host.rock || host.rock(x, y))), v = VoxMesh.pick(x, y, z, cfg.variants); return slot("f" + lv + "," + v, (px, at, st) => host.paintFront(lv, v, px, at + (C - cfg.up) * st, st)); };
      const rx = Math.min(r, o.rx || r), X0 = cx - rx, X1 = cx + rx, Y0 = cy - r, Y1 = cy + Math.min(r, o.rs || r), sig = [cx, cy, L, ceil, o.cut ? [o.cut.n, o.cut.s, o.cut.w] : ""].join();
      // is a chunk on the cut: the cut's box, or a tile of your own space, within a tile of it
      const onCut = (bx, by) => { const x0 = bx * CH - 1, y0 = by * CH - 1, x1 = x0 + CH + 1, y1 = y0 + CH + 1; if (o.cut && o.cut.n > -9 && x1 >= cx - o.cut.w && x0 <= cx + o.cut.w && y1 >= cy - o.cut.n && y0 <= cy + o.cut.s) return true;
        for (const i of reached) { const x = cx - r + i % D, y = cy - r + (i / D | 0); if (x >= x0 && x <= x1 && y >= y0 && y <= y1) return true; } return false; };
      const good = (ch, bx, by) => !!ch && ch.mk === (host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "") && (whole || onCut(bx, by) ? ch.sig === sig : ch.sig === "" && (ch.low ? ch.L === L : ch.lo - 1 > L - deep));
      function* chunk(bx, by) {
        const out = {main: [], model: [], shade: [], water: [], over: []}, skies = [], holes = [], on = whole || onCut(bx, by); let lo = 1e9, low = false, wet = 0;
        const hol = (x, y) => { if (!o.under || !inR(x, y)) return null; const c = col(x, y); if (!c) return null; const open = c[c.length - 1], cz = cutOf(x, y, ceil);   // (a cave on another level: the level you would stand at)
          for (let z = L; z <= cz; z++) if (!solidC(c, z)) return null;
          for (let z = L - 8; z < open && z <= cz + 8; z++) if ((z < L || z > cz) && !solidC(c, z)) return z; return null; };
        const airNear = (x, y, z) => { const c = col(x, y); if (!c) return true; for (let k = L; k <= z; k++) if (!solidC(c, k)) return true; return false; };
        const faces = (x, y, z, solid, dst, isC, box) => {
          const c = col(x, y), open = c[c.length - 1], top = VoxMesh.topOf(c, z);
          for (let f = 0; f < 6; f++) {
            const F = FACES[f], nx = x + F.n[0], ny = y + F.n[1], nz = z + F.n[2];
            if (f === 1 || solid(nx, ny, nz)) continue;
            const nc = col(nx, ny); let sky = (f === 0 ? z >= open : !nc || z > nc[nc.length - 1]) ? 1 : 0;
            let s, kind = f === 0 ? 1 : 0, e = 0;
            if (f === 0) {
              const isCut = isC && solidC(c, z + 1), zt = isCut ? open : z; s = isCut && o.cut ? front(x, y, z, top) : topSlot(x, y, zt, (px, at, st) => topPaint(x, y, zt, px, at, st));   // (?hd: the cut shows the rock: its front's paint)
              [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if (!solid(x + dx, y + dy, z)) e |= b; });
              if (isCut) kind = 2;
              else if (o.under) [[0, -1, 512], [1, 0, 1024], [0, 1, 2048], [-1, 0, 4096]].forEach(([dx, dy, b]) => { if (solid(x + dx, y + dy, z + 1)) e |= b; });   // (a step up at that edge: its foot in shade)
              if (isCut) sky = o.under ? 0 : 1;
              if (isCut) [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if ((e & b) && !(o.under ? reachOf(x + dx, y + dy) !== undefined : airNear(x + dx, y + dy, z))) e &= ~b; });   // (a lit rim only where your space is, not on a step of the cut)
              const hz = isCut && !o.cut ? hol(x, y) : null;
              if (hz !== null) { e |= 16; holes.push([x, y, hz]); [[0, -1, 32], [1, 0, 64], [0, 1, 128], [-1, 0, 256]].forEach(([dx, dy, b]) => { if (hol(x + dx, y + dy) === null) e |= b; }); }
              if (o.under && !isCut && reachOf(x, y) === z && !isRoom(x, y)) e |= 16384;   // (a stair's tread or a small landing: no glow on it, vox_style_glsl.js)
              if (o.under && sky && !isCut) skies.push([x, y, z]);
            } else {
              s = front(x, y, z, top);
              if (box && !inBox(nx, ny)) kind = 6;
            }
            if (o.under && (far(x, y) || (f > 1 && far(nx, ny)))) e |= 8192; if (o.under && f > 1 && inR(x, y) && reachOf(x, y) === z) e |= 16384;   // (far: flat rock; a step's riser: dark)
            quad(dst, x, y, z - 1, F, F.k, sky, kind, z, e, s, solid, f === 0);
          }
        };
        // (a cell under the lowest air of its own column and of the four beside it has no face: the levels start there, not 20 under your feet: a tenth of the cells)
        const lowOf = (x, y) => { const c = col(x, y); return c && c.length ? Math.min(c[0], cutOf(x, y, ceil)) : -1e9; };
        for (let y = by * CH; y < by * CH + CH; y++) for (let x = bx * CH; x < bx * CH + CH; x++) { {
          const c = col(x, y); if (!c) continue; yield; { const ms = host.models && host.models(x, y); if (ms) for (const b of ms) model(x, y, b, b.shade ? out.shade : out.model); }
          const wt = host.water && host.water(x, y), wz = wt ? (host.waterTop ? host.waterTop(x, y) : 0) : null;
          const solid = (a, b, z) => solidIn(a, b, z, ceil);
          const cz = cutOf(x, y, ceil);
          if (o.under && Math.abs(x - cx) <= 8 && Math.abs(y - cy) <= 6 && !solidC(c, L + 1)) for (let z = L + 2, sd = false; z <= Math.max(ceil, cz) + 8 && z < c[c.length - 1]; z++) { if (solidC(c, z - 1) && z - 1 > L) sd = true; if (sd && !solidC(c, z) && solidC(c, z - 1)) { holes.push([x, y, z, 1]); break; } }   // (a cave over your own space: its outline)
          const z0 = o.box ? -1e9 : Math.min(lowOf(x, y), lowOf(x - 1, y), lowOf(x + 1, y), lowOf(x, y - 1), lowOf(x, y + 1)); if (z0 < lo) lo = z0; if (z0 - 1 <= L - deep) low = true;   // (low: the 20 levels under your feet cut it short: it hangs on your level)
          for (let z = Math.max(L - deep + 1, z0); z <= Math.max(ceil, cz, wt ? wz + 1 : -1e9); z++) {   // (?hd: a pond whose face is over the cut still has its face)
            if (!solid(x, y, z)) { if (wt && z === wz + 1) { quad(out.water, x, y, z - 2, FACES[0], 1, 1, 3, z, Math.max(0, wz - c[c.length - 1]), 0, null, true); wet++; } continue; }   // (e: how deep the water is here, levels)
            faces(x, y, z, solid, out.main, z === cz, o.box);
          }
          if (o.over && Math.abs(x - cx) <= o.over && Math.abs(y - cy) <= o.over) {
            const so = (a, b, z) => z > ceil && solidIn(a, b, z, 1e9) && Math.abs(a - cx) <= o.over && Math.abs(b - cy) <= o.over;
            for (let z = ceil + 1; z <= c[c.length - 1]; z++) if (so(x, y, z)) faces(x, y, z, so, out.over, false, false);
          }
        } }
        const ch = {sig: on ? sig : "", mk: host.chunkKey ? host.chunkKey(bx * CH, by * CH, CH) : "", lo, low, L, wet, skies, holes}; for (const k of KINDS) ch[k] = new Float32Array(out[k]); return ch;
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
        if (P.spill() && !o.again) { making = false; return yield* steps(cx, cy, L, ceil, Object.assign({}, o, {again: true})); }   // (the paints ran out while it was made: faces made before that had another face's paint (a meadow all earth, a black hole): once more, from none)
        const list = want.map(([bx, by]) => fresh.get(bx + "," + by) || store.get(bx + "," + by)).filter(Boolean), parts = {far: new Float32Array(fl), sea: new Float32Array(fs)}; let wet = 0;
        const near = list.slice().reverse();   // (the land's own faces: the chunks nearest the eye first (the south ones), so the GPU drops the px of what is behind them before painting them; it was far to near: every hidden px painted, then painted over)
        for (const k of KINDS) { const l = k === "main" ? near : list; let n = 0; for (const ch of l) n += ch[k].length; const d = new Float32Array(n); n = 0; for (const ch of l) { d.set(ch[k], n); n += ch[k].length; } parts[k] = d; }
        for (const ch of list) wet += ch.wet;
        for (const [k, ch] of fresh) if (!late.has(k)) store.set(k, ch);   // (a tile changed in it while it was made: not kept, made again next time)
        if (store.size > 400) { const keep = new Set(want.map(([bx, by]) => bx + "," + by)); for (const k of store.keys()) if (!keep.has(k)) store.delete(k); }
        return {parts, clip: [X0, X1 + 1, Y0, Y1 + 1], wet, made, skies: list.flatMap((ch) => ch.skies), holes: list.flatMap((ch) => ch.holes)};
      } finally { making = false; }
    }
    return {steps, touch, model, clear() { store.clear(); }, get stamp() { return stamp; }};
  }
  return {create, N, CH};
})();
