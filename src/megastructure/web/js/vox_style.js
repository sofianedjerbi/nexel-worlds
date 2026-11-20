// VOX: the land under ground in a "2.5D" look (a mockup: style25.js picks one of five, ?style25=1..5). It names no
// global of the game: the host is the engine's own (vox_engine.js: column, paintTop, paintFront, rock, water, waterTop).
// Drawn at the art's own size (one px of the canvas = one art px; the game lays it on its canvas zoom times bigger),
// every face painted from the tileset: a top by paintTop, a side by paintFront (its cfg.up rows, never stretched).
//   VoxStyle.create(host, cfg) -> {build(x, y, L, ceil, o), draw(view) -> canvas, cost, faces}
//   o (build): {r: tiles round, deep: levels under your feet, box: the place is a block cut out of the land (its
//              outside is air), under: the cut drawn as rock in strata (light.under too), over: tiles round of the land over ceil to keep (a veil), 0: none}
//   view: {w, h, cam: {kind: "persp"|"iso"|"obl", pitch, fov, yaw}, at: [x, y, z], bend, light: {amb, lr, day,
//          fog: [near, far], fogc: [r, g, b], clear, roof, rim, strata, dither, veil, checker}, water: {canvas, x, y},
//          t, sprites: [{canvas, x, y, z, fx, fy}] (its foot at px (fx, fy) of its canvas, drawn px for px),
//          hour: {wash: [r, g, b, a], lit: canvas} the hour's light, laid here over what was drawn and not over the air}
const VoxStyle = (() => {
  const H = .5, SL = 64, C = 16, AW = SL * C, N = 10;
  const {VS, FS, SV, SF} = VoxStyleGLSL;      // (the shaders: vox_style_glsl.js)
  function mul(a, b) { const r = new Float32Array(16); for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; r[i * 4 + j] = s; } return r; }
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm = (a) => { const l = Math.hypot(...a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }, dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  function look(e, c) { const z = norm(sub(e, c)), x = norm(cross([0, 1, 0], z)), y = cross(z, x); return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1]); }
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
  function create(host, cfg) {
    let el = null, skies = [], holes = [], lastM = null, lastB = [0, 0], msh = null, gl = null, pr = null, sp = null, tex = null, wtx = null, htx = null, bufs = {}, stale = true, cost = 0, spill = false, hold = false, wipe = false;
    const atlas = new Uint32Array(AW * AW), slots = new Map(), cnt = {main: 0, model: 0, shade: 0, shade2: 0, ghost: 0, water: 0, over: 0}, U = {};
    function slot(key, paint) {
      let s = slots.get(key); if (s !== undefined) return s;
      if (slots.size >= SL * SL) { slots.clear(); atlas.fill(0); spill = true; }   // (full: all its paints go; the land being made is made again, steps)
      s = slots.size; slots.set(key, s); const at = (s / SL | 0) * C * AW + (s % SL) * C; paint(atlas, at, AW); stale = true; return s;
    }
    function start() {
      if (gl) return true;
      el = document.createElement("canvas"); gl = el.getContext("webgl2", {antialias: false, depth: true, preserveDrawingBuffer: true}); if (!gl) return false;
      const prog = (vs, fs) => { const p = gl.createProgram(); for (const [ty, s] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) { const sh = gl.createShader(ty); gl.shaderSource(sh, s); gl.compileShader(sh); if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); gl.attachShader(p, sh); } gl.linkProgram(p); return p; };
      pr = prog(VS, FS); sp = prog(SV, SF); tex = gl.createTexture(); wtx = gl.createTexture(); htx = gl.createTexture();
      for (const k of ["main", "model", "shade", "shade2", "ghost", "water", "over", "spr"]) bufs[k] = gl.createBuffer();
      return true;
    }
    const lim = (z) => Math.max(cfg.levels[0], Math.min(cfg.levels[1], z));
    // what stands in the land as boxes (host.models: a bridge's deck and posts): a top and a south front each, its paint from the host's sheet px for px into a slot
    const sheet = () => { if (!msh) { const q = host.modelSheet(); msh = q.px ? q : {px: new Uint32Array(q.getContext("2d").getImageData(0, 0, q.width, q.height).data.buffer), w: q.width}; } return msh; };
    const model = (x, y, b, dst) => { const X = x + b.x / C, Y = y + b.y / C, X1 = X + b.w / C, Y1 = Y + b.d / C, Z0 = b.z / cfg.up, Z1 = (b.z + b.h) / cfg.up;
      const face = (uv, w, h, q, k) => { if (!uv) return; w = Math.min(C, w); h = Math.min(C, h); const sl = slot("m" + (b.sheet ? b.sheet.id : "") + uv + "," + w + "," + h, (px, at, st) => { const m = b.sheet || sheet(); for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) px[at + j * st + i] = m.px[(uv[2] ? uv[1] : uv[1] + j) * m.w + (uv[2] ? uv[0] : uv[0] + i)]; });
        const v = q.map((g3, n) => [...gp(...g3), (sl % SL) * C + [0, w, w, 0][n], (sl / SL | 0) * C + [0, 0, h, h][n], k, 1, b.shade ? 10 : b.ghost ? 9 : 8, Z1, 0]); for (const n of [0, 1, 2, 0, 2, 3]) dst.push(...v[n]); };
      face(b.top, b.w, b.d, [[X, Y, Z1], [X1, Y, Z1], [X1, Y1, Z1], [X, Y1, Z1]], 1); const fh = b.fh || b.h; if (b.h) { face(b.front, b.w, fh, [[X, Y1, Z1], [X1, Y1, Z1], [X1, Y1, Z0], [X, Y1, Z0]], .85);
        face(b.west, b.d, fh, [[X, Y, Z1], [X, Y1, Z1], [X, Y1, Z0], [X, Y, Z0]], .68); face(b.east, b.d, fh, [[X1, Y1, Z1], [X1, Y, Z1], [X1, Y, Z0], [X1, Y1, Z0]], .74); } };   // (b.sheet: a paint sheet of its own, {px, w, id}; west, east: its sides, d x h px; fh: its front and sides are that many rows of paint over its height)
    function build(...a) { for (const _ of steps(...a)); }
    function* steps(cx, cy, L, ceil, o) {   // (?hd: the same, a row of tiles a step: the caller spreads it over frames)
      const t0 = performance.now(), cols = new Map(), r = o.r, deep = o.deep; spill = false;
      // (the paints and the land that names them change together: while a land is being made, over frames, the one still drawn keeps the paints it was made with. They were wiped at once, forget(), and sent as they were painted: the land shown turned to bare earth and to other tiles' paints until the new one was done: each time land came in as you walked)
      hold = true; if (wipe) { slots.clear(); atlas.fill(0); wipe = false; }
      const col = (x, y) => { const k = x + "," + y; if (!cols.has(k)) cols.set(k, host.column(x, y)); return cols.get(k); };
      const inBox = (x, y) => Math.abs(x - cx) <= r && Math.abs(y - cy) <= r;
      const cut = new Map();   // (under: the slice height, one field: a tile of your space its floor + 2, a rock tile the nearest space tile's (ties: the lower))
      const inR = (x, y) => !o.cut || (y - cy >= -o.cut.n && y - cy <= o.cut.s && Math.abs(x - cx) <= o.cut.w);   // (?hd: the slice only in a box round you; outside it the whole land)
      const cutOf = (x, y, top) => { if (o.under && top < 1e8 && !inR(x, y)) { const c = col(x, y); return c ? c[c.length - 1] : top; } if (!o.under || top > 1e8 || !cut.size) return top; x = Math.max(cx - r, Math.min(cx + r, x)); y = Math.max(cy - r, Math.min(cy + r, y)); const v = cut.get(x + "," + y); return v === undefined ? top : v; };
      const floorOf = (x, y) => { const c = col(x, y); if (!c || !inBox(x, y)) return null; const t = c[c.length - 1];   // (a hollow's floor near your level, if the tile is one)
        for (let z = L - deep + 1; z <= L + 6 && z < t; z++) if (!solidC(c, z)) return z - 1; return null; };
      const reach = new Map(), st = [[cx, cy, L]];   // (your own space: tiles walked to from you, a step or a short drop, their floors)
      while (o.under && st.length) { const [x, y, f0] = st.pop(), k = x + "," + y; if (reach.has(k)) continue; const f = floorOf(x, y); if (f === null || Math.abs(f - f0) > 2) continue; reach.set(k, f); for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) st.push([x + dx, y + dy, f]); }
      let fr = [...reach].map(([k, f]) => [k, f + 2]), dd = 0; const dist = new Map(); for (const [k, v] of fr) { cut.set(k, v); dist.set(k, 0); }
      while (fr.length) { const nx = new Map(); for (const [k, v] of fr) { const [x, y] = k.split(",").map(Number);
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const n = (x + dx) + "," + (y + dy); if (cut.has(n) || !inBox(x + dx, y + dy)) continue; nx.set(n, Math.min(v, nx.has(n) ? nx.get(n) : 1e9)); } }
        fr = [...nx]; dd++; for (const [k, v] of fr) { cut.set(k, v); dist.set(k, dd); } }
      const far = (x, y) => !o.cut && (dist.get(x + "," + y) ?? 9) > 2;   // (beyond 2 tiles: one flat height for the whole box, the lowest cut near you: no edges far off)
      for (const [k, d] of dist) if (d > 0 && d <= 2) { const [x, y] = k.split(",").map(Number);   // (the camera's side: rock south of your space cut at its floor, the treads show)
        for (let j = 1; j <= 2; j++) { const f = reach.get(x + "," + (y - j)); if (f !== undefined) { cut.set(k, Math.min(cut.get(k), f)); break; } } }
      for (const [k, d] of dist) if (d > 2) cut.set(k, L + 2); else if (d === 2 && !reach.has(k)) cut.set(k, Math.max(L, Math.min(L + 4, cut.get(k))));   // (far: one height, your ceiling; the ring by it within 2 levels of it)
      const solidIn = (x, y, z, top) => { top = cutOf(x, y, top); if (!inBox(x, y)) return !o.box && z <= top && solidC(col(x, y), z); if (z <= L - deep) return !o.box; return z <= top && solidC(col(x, y), z); };
      const out = {main: [], model: [], shade: [], water: [], over: []}; skies = []; holes = [];
      const hol = (x, y) => { if (!o.under || !inR(x, y)) return null; const c = col(x, y); if (!c) return null; const open = c[c.length - 1], cz = cutOf(x, y, ceil);   // (a cave on another level: the level you would stand at)
        for (let z = L; z <= cz; z++) if (!solidC(c, z)) return null;
        for (let z = L - 8; z < open && z <= cz + 8; z++) if ((z < L || z > cz) && !solidC(c, z)) return z; return null; };
      const airNear = (x, y, z) => { const c = col(x, y); if (!c) return true; for (let k = L; k <= z; k++) if (!solidC(c, k)) return true; return false; };
      const front = (x, y, z, top) => { const lv = lim(VoxMesh.rock(cfg, top, z, !host.rock || host.rock(x, y))), v = VoxMesh.pick(x, y, z, cfg.variants); return slot("f" + lv + "," + v, (px, at, st) => host.paintFront(lv, v, px, at + (C - cfg.up) * st, st)); };
      const faces = (x, y, z, solid, dst, cut, box) => {
        const c = col(x, y), open = c[c.length - 1], top = VoxMesh.topOf(c, z);
        for (let f = 0; f < 6; f++) {
          const F = FACES[f], nx = x + F.n[0], ny = y + F.n[1], nz = z + F.n[2];
          if (f === 1 || solid(nx, ny, nz)) continue;
          const nc = col(nx, ny); let sky = (f === 0 ? z >= open : !nc || z > nc[nc.length - 1]) ? 1 : 0;
          let s, kind = f === 0 ? 1 : 0, e = 0;
          if (f === 0) {
            const isCut = cut && solidC(c, z + 1), zt = isCut ? open : z; s = isCut && o.cut ? front(x, y, z, top) : slot(x + "," + y + "," + zt, (px, at, st) => host.paintTop(x, y, zt, px, at, st));   // (?hd: the cut shows the rock: its front's paint)
            [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if (!solid(x + dx, y + dy, z)) e |= b; });
            if (isCut) kind = 2;
            else if (o.under) [[0, -1, 512], [1, 0, 1024], [0, 1, 2048], [-1, 0, 4096]].forEach(([dx, dy, b]) => { if (solid(x + dx, y + dy, z + 1)) e |= b; });   // (a step up at that edge: its foot in shade)
            if (isCut) sky = o.under ? 0 : 1;
            if (isCut) [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if ((e & b) && !(o.under ? reach.has((x + dx) + "," + (y + dy)) : airNear(x + dx, y + dy, z))) e &= ~b; });   // (a gold edge only on the edge of your own space)   // (a lit rim only where your space is, not on a step of the cut)
            const hz = isCut && !o.cut ? hol(x, y) : null;
            if (hz !== null) { e |= 16; holes.push([x, y, hz]); [[0, -1, 32], [1, 0, 64], [0, 1, 128], [-1, 0, 256]].forEach(([dx, dy, b]) => { if (hol(x + dx, y + dy) === null) e |= b; }); }
            if (o.under && sky && !isCut) skies.push([x, y, z]);
          } else {
            s = front(x, y, z, top);
            if (box && !inBox(nx, ny)) kind = 6;
          }
          if (o.under && (far(x, y) || (f > 1 && far(nx, ny)))) e |= 8192; if (o.under && f > 1 && inR(x, y) && reach.get(x + "," + y) === z) e |= 16384;   // (far: flat rock; a step's riser: dark)
          quad(dst, x, y, z - 1, F, F.k, sky, kind, z, e, s, solid, f === 0);
        }
      };
      for (let y = cy - r; y <= cy + r; y++) { yield; for (let x = cx - r; x <= cx + r; x++) {
        const c = col(x, y); if (!c) continue; { const ms = host.models && host.models(x, y); if (ms) for (const b of ms) model(x, y, b, b.shade ? out.shade : out.model); }
        const wet = host.water && host.water(x, y), wz = wet ? (host.waterTop ? host.waterTop(x, y) : 0) : null;
        const solid = (a, b, z) => solidIn(a, b, z, ceil);
        const cz = cutOf(x, y, ceil);
        if (o.under && Math.abs(x - cx) <= 8 && Math.abs(y - cy) <= 6 && !solidC(c, L + 1)) for (let z = L + 2, sd = false; z <= Math.max(ceil, cz) + 8 && z < c[c.length - 1]; z++) { if (solidC(c, z - 1) && z - 1 > L) sd = true; if (sd && !solidC(c, z) && solidC(c, z - 1)) { holes.push([x, y, z, 1]); break; } }   // (a cave over your own space: its outline)
        for (let z = L - deep + 1; z <= Math.max(ceil, cz, wet ? wz + 1 : -1e9); z++) {   // (?hd: a pond whose face is over the cut still has its face)
          if (!solid(x, y, z)) { if (wet && z === wz + 1) quad(out.water, x, y, z - 2, FACES[0], 1, 1, 3, z, Math.max(0, wz - c[c.length - 1]), 0, null, true); continue; }   // (e: how deep the water is here, levels)
          faces(x, y, z, solid, out.main, z === cz, o.box);
        }
        if (o.over && Math.abs(x - cx) <= o.over && Math.abs(y - cy) <= o.over) {
          const so = (a, b, z) => z > ceil && solidIn(a, b, z, 1e9) && Math.abs(a - cx) <= o.over && Math.abs(b - cy) <= o.over;
          for (let z = ceil + 1; z <= c[c.length - 1]; z++) if (so(x, y, z)) faces(x, y, z, so, out.over, false, false);
        }
      } }
      if (o.sea !== undefined) { const seg = []; for (let s = -r; s <= r; s += 8) seg.push([s, Math.min(8, r + 1 - s), 1]); for (let k = 0; k < 5; k++) seg.push([r + 1 + 8 * k, 8, 0], [-r - 8 - 8 * k, 8, 0]);
        // (?hd: past the box, to the horizon, in patches: the sea's flat face where the sea is (or nothing is known); where land is, the land's own tint at its height, flat, a skirt south of it: no sea inland)
        for (const [j, h, mj] of seg) for (const [i, w, mi] of seg) { if (mi && mj) continue; const x = cx + i, y = cy + j, mx = x + (w >> 1), my = y + (h >> 1), c = host.column(mx, my), land = c && c.length && !(host.water && host.water(mx, my));
          const z = land ? c[c.length - 1] : o.sea, sl = land ? slot(mx + "," + my + "," + z, (px, at, st) => host.paintTop(mx, my, z, px, at, st)) : 0, u0 = land ? (sl % SL) * C + 8 : 0, v0 = land ? (sl / SL | 0) * C + 8 : 0;
          const put = (q, k) => { const v = q.map(([a, b, d]) => [...gp(a, b, d), u0, v0, k, 1, land ? 7 : 3, z, 9]); for (const n of [0, 1, 2, 0, 2, 3]) (land ? out.main : out.water).push(...v[n]); };
          put([[x, y, z], [x + w, y, z], [x + w, y + h, z], [x, y + h, z]], 1); if (land) put([[x, y + h, z], [x + w, y + h, z], [x + w, y + h, z - 10], [x, y + h, z - 10]], .8); } }
      if (spill && !o.again) { slots.clear(); atlas.fill(0); yield* steps(cx, cy, L, ceil, Object.assign({}, o, {again: true})); return; }   // (the paints ran out while it was made: faces made before that had another face's paint (a meadow all earth, a black hole): once more, from none)
      if (start()) for (const k in out) { const d = new Float32Array(out[k]); cnt[k] = d.length / N; gl.bindBuffer(gl.ARRAY_BUFFER, bufs[k]); gl.bufferData(gl.ARRAY_BUFFER, d, gl.STATIC_DRAW); }
      hold = false; stale = true;
      cost = performance.now() - t0;
    }
    function quad(out, x, y, z, F, k, sky, kind, lv, e, s, solid, isTop) {
      const u0 = (s % SL) * C, v0 = (s / SL | 0) * C, top = isTop ? 0 : C - cfg.up, UV = [[0, top], [C, top], [C, C], [0, C]], vs = [];
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
    // the camera: px of the canvas a tile is across at the eye's target = 16 (one art px a px)
    function matrix(v) {
      const c = v.cam, at = gp(...v.at), RW = v.w, RH = v.h;
      if (c.kind === "obl") return {m: new Float32Array([32 / RW, 0, 0, 0, 0, 32 / RH, -1 / 60, 0, 0, -32 / RH, -1 / 60, 0, -32 / RW * at[0], 32 / RH * (at[2] - at[1]), (at[2] + at[1]) / 60, 1]), eye: [at[0], at[1] + 40, at[2] + 40]};
      const yaw = (c.yaw || 0) * Math.PI / 180, p = c.pitch * Math.PI / 180, dir = [Math.sin(yaw) * Math.cos(p), Math.sin(p), Math.cos(yaw) * Math.cos(p)];
      if (c.kind === "iso") {
        const eye = at.map((a, i) => a + dir[i] * 60), hw = RW / 32, hh = RH / 32;
        return {m: mul(new Float32Array([1 / hw, 0, 0, 0, 0, 1 / hh, 0, 0, 0, 0, -2 / 119, 0, 0, 0, -121 / 119, 1]), look(eye, at)), eye};
      }
      const t = Math.tan(c.fov * Math.PI / 360), d = RH / (32 * t), eye = at.map((a, i) => a + dir[i] * d), n = .5, f = 200;
      const P = new Float32Array(16); P[0] = 1 / t / (RW / RH); P[5] = 1 / t; P[10] = (f + n) / (n - f); P[11] = -1; P[14] = 2 * f * n / (n - f);
      return {m: mul(P, look(eye, at)), eye};
    }
    const project = (m, x, y, z) => { const dn = Math.max(0, lastB[1] - 1 - y), p = gp(x, y, z - lastB[0] * dn * dn / H),   // (sunk with the bend north of you, as the shader sinks the land: what stands there stood in the air past the bend, and the aim was off)
 r = [0, 1, 2, 3].map((j) => m[j] * p[0] + m[4 + j] * p[1] + m[8 + j] * p[2] + m[12 + j]); return [r[0] / r[3], r[1] / r[3], r[2] / r[3]]; };
    function pass(k, U2) {
      if (!cnt[k]) return; gl.bindBuffer(gl.ARRAY_BUFFER, bufs[k]); const S = N * 4;
      for (const [nm, sz, off] of [["p", 3, 0], ["uv", 2, 12], ["a", 4, 20], ["e", 1, 36]]) { const l = gl.getAttribLocation(pr, nm); if (l < 0) continue; gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, sz, gl.FLOAT, false, S, off); }
      if (U2) U2(); gl.drawArrays(gl.TRIANGLES, 0, cnt[k]);
    }
    function draw(v) {
      if (!start()) return null;
      const t0 = performance.now(), L = v.light, RW = v.w, RH = v.h;
      if (el.width !== RW || el.height !== RH) { el.width = RW; el.height = RH; }
      gl.viewport(0, 0, RW, RH); gl.clearColor(...L.clear, L.ca ?? 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.disable(gl.CULL_FACE); gl.disable(gl.BLEND); gl.depthMask(true);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
      const near = (t) => { for (const [a, b] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, a, b); };
      if (stale && !hold) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, AW, AW, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(atlas.buffer)); near(); stale = false; }
      const W = v.water; gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, wtx);
      if (W && W.canvas && W.canvas.width) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, W.canvas); near(); }
      gl.activeTexture(gl.TEXTURE0);
      const {m, eye} = matrix(v); lastM = m; lastB = [v.bend || 0, v.at[1]]; const lamp = gp(...v.at);
      gl.useProgram(pr); const u = (n) => U[n] || (U[n] = gl.getUniformLocation(pr, n));
      gl.uniformMatrix4fv(u("m"), false, m); gl.uniform1i(u("t"), 0); gl.uniform1i(u("wt"), 2); gl.uniform3fv(u("lamp"), [lamp[0], lamp[1] + .6, lamp[2]]); gl.uniform3fv(u("eye"), eye);
      gl.uniform3fv(u("ctr"), lamp); gl.uniform1f(u("bend"), v.bend || 0); gl.uniform3fv(u("fogc"), L.fogc); gl.uniform2fv(u("vp"), [RW, RH]);
      for (const [n, x] of [["lr", L.lr], ["day", L.day], ["amb", L.amb], ["fn", L.fog[0]], ["ff", L.fog[1]], ["roof", L.roof], ["rim", L.rim], ["strata", L.strata || 0], ["dith", L.dither ? 1 : 0], ["und", L.under ? 1 : 0],  ["wa", L.wa ?? .62], ["dep", v.dep || 0], ["veil", 0], ["sk", L.sk], ["ovd", L.ovd || 1], ["chk", 0], ["tm", v.t || 0], ["dk", L.dark || 0], ["rd", 0]]) gl.uniform1f(u(n), x);
      gl.uniform4fv(u("wtn[0]"), L.wtint || new Float32Array(20)); gl.uniform4fv(u("ub"), L.ub || [0, 0, 0, 0]); gl.uniform4fv(u("wv"), W && W.canvas && W.canvas.width ? [W.x, W.y, W.canvas.width, W.canvas.height] : [0, 0, 0, 0]);
      { const d = [], sd = []; for (const [x, y, b] of v.ghosts || []) model(x, y, b, b.shade ? sd : d); cnt.ghost = d.length / N; cnt.shade2 = sd.length / N; for (const [k, l] of [["ghost", d], ["shade2", sd]]) if (l.length) { gl.bindBuffer(gl.ARRAY_BUFFER, bufs[k]); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(l), gl.STREAM_DRAW); }
        if (stale && !hold) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, AW, AW, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(atlas.buffer)); stale = false; } }   // (view.ghosts: [[x, y, box]...], what is only planned, and the shadows of what moves: made each frame)
      pass("main"); pass("model"); pass("ghost"); gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false); pass("shade"); pass("shade2"); gl.depthMask(true); gl.disable(gl.BLEND);
      // the sprites: px for px, their foot snapped to a whole px, over everything (you are never lost under ground)
      const me = (v.sprites || []).find((s) => s.top), mf = me && project(m, me.x, me.y, me.z), PX = (f) => [(f[0] * .5 + .5) * RW, (.5 - f[1] * .5) * RH], mp = mf && PX(mf), disc = mp ? [mp[0], RH - mp[1] + 1, 12] : [0, 0, 0];   // (the disc round you: what covers you is seen through there only)
      const spr = (s) => {   // (?hd: you (top) are drawn after the water: you stand in it, not under it; what stands south of you after you, and where it covers you a checker of it)
        const f = project(m, s.x, s.y, s.z), fx = Math.round((f[0] * .5 + .5) * RW), fy = Math.round((.5 - f[1] * .5) * RH), w = s.canvas.width, h = s.canvas.height;
        const x0 = fx - s.fx, y0 = fy - s.fy, X = (px) => px / RW * 2 - 1, Y = (py) => 1 - py / RH * 2, z = s.d ? f[2] - .0004 : L.under ? project(m, s.x, s.y + .45, s.z + .3)[2] : f[2] - .002;
        let q = [[X(x0), Y(y0), z], [X(x0 + w), Y(y0), z], [X(x0 + w), Y(y0 + h), z], [X(x0), Y(y0 + h), z]], box = [x0, y0, x0 + w, y0 + h];
        if (s.flat) { q = [[-s.fx, s.fy], [w - s.fx, s.fy], [w - s.fx, s.fy - h], [-s.fx, s.fy - h]].map(([a, b]) => project(m, s.x + a / C, s.y, s.z + b / cfg.up)); const a = PX(q[0]), b = PX(q[2]); box = [a[0], a[1], b[0], b[1]]; q.forEach((c) => { c[2] -= .0004; }); }   // (a standing face in the land: its sprite a px of paint an art px of the land, as the land's own fronts)
        const d = [0, 1, 2, 0, 2, 3].flatMap((i) => [...q[i], [0, 1, 1, 0][i], [0, 0, 1, 1][i]]), over = mp && s !== me && s.y > me.y && box[0] < mp[0] + 6 && box[2] > mp[0] - 6 && box[1] < mp[1] - 2 && box[3] > mp[1] - 15;
        gl.useProgram(sp); gl.activeTexture(gl.TEXTURE1); const st = s.canvas._t || (s.canvas._t = gl.createTexture()); gl.bindTexture(gl.TEXTURE_2D, st);
        if (!s.still || !s.canvas._up) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, s.canvas); near(); s.canvas._up = 1; }   // (?hd: a still billboard is sent once)
        gl.uniform1i(gl.getUniformLocation(sp, "t"), 1);
        gl.bindBuffer(gl.ARRAY_BUFFER, bufs.spr); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(d), gl.STREAM_DRAW);
        for (const [nm, sz, off] of [["p", 3, 0], ["uv", 2, 12]]) { const l = gl.getAttribLocation(sp, nm); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, sz, gl.FLOAT, false, 20, off); }
        const sil = gl.getUniformLocation(sp, "sil"); gl.uniform1f(sil, over ? 2 : 0); gl.uniform3fv(gl.getUniformLocation(sp, "mc"), disc);
        if (L.under && !s.d && !s.top) { gl.disable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.uniform1f(sil, 1); gl.drawArrays(gl.TRIANGLES, 0, 6); gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.uniform1f(sil, 0); }   // (hidden by a wall: a faint shape of you)
        if ((!L.under && !s.d) || s.top) gl.disable(gl.DEPTH_TEST); gl.drawArrays(gl.TRIANGLES, 0, 6); gl.enable(gl.DEPTH_TEST); gl.activeTexture(gl.TEXTURE0); gl.useProgram(pr);
      };
      const late = (s) => !!me && s.y > me.y;
      if (v.sprites) for (const s of v.sprites) if (!s.top && !late(s)) spr(s);
      gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
      pass("water"); gl.depthMask(true); gl.disable(gl.BLEND);
      if (me) { spr(me); pass("model", () => { gl.uniform1f(u("rd"), 1); gl.uniform3fv(u("mc"), disc); }); gl.uniform1f(u("rd"), 0); } if (v.sprites) for (const s of v.sprites) if (!s.top && late(s)) spr(s);
      if (L.veil || L.checker) { gl.enable(gl.BLEND); gl.depthMask(false); pass("over", () => { gl.uniform1f(u("veil"), L.veil || 1); gl.uniform1f(u("chk"), L.checker ? 1 : 0); gl.uniform1f(u("roof"), 1); }); gl.depthMask(true); gl.disable(gl.BLEND); }
      if (v.hour) {   // the hour's light, here and not on a canvas of the page's (it was four of them laid on each other every frame, the last cut out by this picture: slow on a phone, and a phone has drawn such chains wrong): a wash of the hour's colour where something is drawn, then all of it times the light's picture (the lamps in it)
        const hr = v.hour, a = hr.wash[3], quad = (sf, df) => { near(); gl.blendFuncSeparate(sf, df, gl.ZERO, gl.ONE); gl.drawArrays(gl.TRIANGLES, 0, 6); };
        gl.useProgram(sp); gl.disable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, htx); gl.uniform1i(gl.getUniformLocation(sp, "t"), 1); gl.uniform1f(gl.getUniformLocation(sp, "sil"), 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, bufs.spr); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, 1, 2, 0, 2, 3].flatMap((i) => [[-1, 1], [1, 1], [1, -1], [-1, -1]][i].concat(0, [0, 1, 1, 0][i], [0, 0, 1, 1][i]))), gl.STREAM_DRAW);
        for (const [nm, sz, off] of [["p", 3, 0], ["uv", 2, 12]]) { const l = gl.getAttribLocation(sp, nm); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, sz, gl.FLOAT, false, 20, off); }
        if (a > .004) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([hr.wash[0] * a, hr.wash[1] * a, hr.wash[2] * a, 255])); gl.blendColor(0, 0, 0, a); quad(gl.DST_ALPHA, gl.ONE_MINUS_CONSTANT_ALPHA); }
        if (hr.lit) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, hr.lit); quad(gl.DST_COLOR, gl.ZERO); }
        gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.activeTexture(gl.TEXTURE0); gl.useProgram(pr);
      }
      cost = performance.now() - t0;
      return el;
    }
    return {build, steps, get water() { return cnt.water; }, draw, forget() { wipe = true; }, get cost() { return cost; }, get skies() { return skies; }, get holes() { return holes; },
      at(x, y, z) { if (!lastM) return null; const f = project(lastM, x, y, z); return [(f[0] * .5 + .5) * el.width, (.5 - f[1] * .5) * el.height]; }, get faces() { return (cnt.main + cnt.model + cnt.over) / 6; }, get models() { return cnt.model / 6; }};
  }
  return {create};
})();
