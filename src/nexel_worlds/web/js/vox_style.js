// VOX: the land in a "2.5D" look (the game's HD look, hd.js). It names no global of the game: the host is the
// engine's own (vox_engine.js: column, paintTop, paintFront, rock, water, waterTop; chunkKey(x0, y0, n): what stands in a chunk hangs on; sunk(x, y, f): a tile under the open sky, its floor at f, is in a hole of the land and hidden from the eye: the window is on it).
// Drawn at the art's own size (one px of the canvas = one art px; the page shows that canvas zoom times bigger),
// every face painted from the tileset: a top by paintTop, a side by paintFront (its cfg.up rows, never stretched).
//   VoxStyle.create(host, cfg) -> {build(x, y, L, o), steps(...) (the same over frames), touch(x, y), draw(view) -> canvas, win, cost, faces, fresh, calls}
//   o (build): {r: tiles round, rx, rs: columns across and rows south shown, deep: levels under your feet, sea: the far sea's level,
//              win: {reach}: land hides you: your space is looked for, and the boxes of the x-ray window on it (vox_style_land.js), or none}
//   view: {w, h, cam: {kind: "persp"|"iso"|"obl", pitch, fov, yaw}, at: [x, y, z], bend, dep: levels of land over your floor, light: {amb, lr, day,
//          fog: [near, far], fogc: [r, g, b], clear, rim, sun: how dark the sun's shadows are, 0..1}, water: {canvas, x, y, ver},
//          own: [[x, y, lo, hi, sky]...] boxes of the window that are yours whatever the search found (your tile, where you came from), rim: the level of the land round your hole (the depth told in the window, vox_style_glsl.js), sky: land under the open sky hides you (its tiles of your space are in the window), behind: 0..1: land taller than you stands in front of you (the disc round you is opened in it, as in a roof or a tree), hid: 0: what land hides of you is not drawn at all (in a hole seen from above you are drawn at its rim: hd.js lift); behind land with the disc open you are drawn WHOLE in it (it was one px in two of you in a disc one px in two of the land, the same px: a checker cat for as long as you stood there), hole: 0..1: you are in a hole of the land looked at from above (its open walls get the strata too),
//          t, sprites: [{canvas, x, y, z, fx, fy, on: stands on the land, lie: lies flat on the land at level z (its canvas a px an art px of it), drawn after the water, zh: the level its depth is taken at, if not z}] (its foot at px (fx, fy) of its canvas, drawn px for px; canvas._v: goes up when its picture changed),
//          way: {on: Map "x,y" -> level, dim, key} | null (a way shown: `light`; its floors are in the window too), win: 0 | 1: the x-ray window shut or open (it goes there over 100 ms), sect: [ink, , , the dark behind the land]: the tone its rim is darkened to,
//          hour: {wash: [r, g, b, a], lit: canvas | tint: [r, g, b]} the hour's light, laid here over what was drawn and not over the air}
// What a frame costs the GPU: the land is ONE list (the chunks' faces, what stands, the far land, the frame's ghosts at its end), the shadows one, the water one;
// the sprites are one list from one sheet of their pictures (a picture is sent when it changed, not each frame); a frame that is the last one again is not drawn at all (fresh: false).
const VoxStyle = (() => {
  const H = VoxStyleGLSL.H, C = 16, AW = VoxStyleGLSL.AW, SL = AW / C, N = VoxStyleLand.N, SW = 1024, SV6 = 8, SECT = [[.17, .12, .13], [.5, .35, .26], [.43, .41, .42], [.21, .17, .18]];
  const {VS, FS, SV, SF} = VoxStyleGLSL;      // (the shaders: vox_style_glsl.js)
  function mul(a, b) { const r = new Float32Array(16); for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; r[i * 4 + j] = s; } return r; }
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm = (a) => { const l = Math.hypot(...a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }, dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  function look(e, c) { const z = norm(sub(e, c)), x = norm(cross([0, 1, 0], z)), y = cross(z, x); return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1]); }
  const gp = (x, y, z) => [x, z * H, y], same = (a, b) => { if (!a || !b || a.length !== b.length) return false; for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false; return true; };
  const sameN = (a, an, b, bn) => { if (!a || !b || an !== bn) return false; for (let i = 0; i < an; i++) if (a[i] !== b[i]) return false; return true; }, sameW = (a, b) => !!b && sameN(a.f, a.n, b.f, b.n);   // (the first n numbers of two kept buffers; a writer {f, n})
  const firstOff = (a, b) => { for (let i = 0; i < a.n; i++) if (!b || i >= b.n || a.f[i] !== b.f[i]) return i; return -1; };
  function create(host, cfg) {
    let el = null, lastM = null, lastB = [0, 0], gl = null, pr = null, sp = null, tex = null, wtx = null, htx = null, ltx = null, atx = null, stx = null, sver = 0, sorg = [0, 0, 1], sAt = 0, sBusy = false, sWay = null, cdv = 0, cdAt = 0, sPx = null, sOrg = null, space = null, cutM = null, W_ = null, wxr = 0, wAt = 0, wKey = "", sectAt = [0, 0, 0, 0], winL = [], winN = 0, winJ = "", stale = true, cost = 0, spill = false, wipe = false, mk = false, lost = false, wat = null, fresh = true, calls = 0, why = "";
    let wmap = new Map(), wrim = 0, over = false, mean = [.6, .66, .38], clip = [-1e9, 1e9, -1e9, 1e9], wet = 0, far = new Float32Array(0), made = 0, again = true, lastU = null, lastS = null, lastG = null, lastD = null, hk = "", lk = "";
    // (a frame's numbers into kept writers {f, n}, two of each, the one the last frame drawn is not: the ghosts', the moving shadows', the painter's uniforms (ub, uq: the one being written))
    const wr = (k) => [{f: new Float32Array(k), n: 0}, {f: new Float32Array(k), n: 0}], GW = wr(4096), DW = wr(4096), UB = wr(512), NOBODY = new Float32Array(12).fill(-9999), Z40 = new Float32Array(40), NOTINT = [-1, -1, -1], LP = [null, null];
    let ub = UB[0].f, uq = 0, lastSn = 0, mver = 0; const uP = (x) => { ub[uq++] = x; }, uA = (a) => { for (let i = 0; i < a.length; i++) ub[uq++] = a[i]; };
    const dirty = [], row = new Uint32Array(AW * C), glow = new Map(), U = {}, units = {}, cnt ={main: 0, model: 0, far: 0, ghost: 0, shade: 0, shade2: 0, water: 0}, bufs = {};
    // the paints: A the ones the land now drawn was made with (and what is drawn each frame over it: shadows, ghosts), B the ones of a land being made (A's and its new ones; after a wipe from none); B becomes A when that land is done
    // (B is made when the land being made first asks for a paint A has not: a land made again with nothing new in it copies nothing)
    // (FULL while a land is made: the places of the paints that land does not use (used: the ones it asked for and the ones of the chunks it keeps) are given again, theirs first wiped; the chunks
    // and far patches made with them are let go (land.evicted). It was all of them wiped and the whole land made again from none, every second or so walking: 4096 places, a land some 2000)
    // (CAP: the places the land's paints may take; the last one, CAP itself, is kept for a paint asked for when the sheet shown is full
    //  (overs): it took the last place a face of the land shown still named, drawn with another paint until the land was made again)
    const CAP = SL * SL - 1; let wipes = 0, spills = 0, overs = 0, A = {slots: new Map(), px: new Uint32Array(AW * AW), n: 0, free: []}, B = null, spare = new Uint32Array(AW * AW), fromNone = false, used = new Set();
    function evict() { land.farKeep(); for (const [k, v] of B.slots) if (!used.has(v)) B.slots.delete(k); B.free = []; for (let i = CAP - 1; i >= 0; i--) if (!used.has(i)) B.free.push(i); B.full = true; land.evicted((v) => used.has(v)); }   // (the far patches of this land kept with their places: vox_style_land.js farKeep)
    function slot(key, paint) {
      if (mk && !B) { const s0 = fromNone ? undefined : A.slots.get(key); if (s0 !== undefined) { used.add(s0); return s0; }
        if (fromNone) { spare.fill(0); B = {slots: new Map(), px: spare, add: [], full: true, n: 0, free: []}; } else { spare.set(A.px); B = {slots: new Map(A.slots), px: spare, add: [], full: false, n: A.n, free: A.free.slice()}; } }
      const S = mk ? B : A; let s = S.slots.get(key); if (s !== undefined) { if (mk) used.add(s); return s; }   // (mk: the land being made is asking)
      if (S.n >= CAP && !mk && S.free.length) { s = S.free.pop(); const at = (s / SL | 0) * C * AW + (s % SL) * C; for (let j = 0; j < C; j++) S.px.fill(0, at + j * AW, at + j * AW + C); }   // (a place given again: see evict)
      else if (S.n >= CAP && !mk) { overs++; s = CAP; for (const [k0, v0] of S.slots) if (v0 === s) { S.slots.delete(k0); break; } if (!over) over = lost = true; }   // (the sheet of the land now SHOWN is full, and a paint is asked for outside a land's making (the window's section, a ghost): it takes the last place, and the land is made again from none behind the picture (lost). It was all its paints wiped at once: every face of the land shown read an empty paint for the second the making took: the painter drew that as one earth brown: "the whole meadow brown, seen once")
      else { if (S.n >= CAP && !S.free.length) evict();
        if (S.n < CAP) s = S.n++; else if (S.free.length) { s = S.free.pop(); const at = (s / SL | 0) * C * AW + (s % SL) * C; for (let j = 0; j < C; j++) S.px.fill(0, at + j * AW, at + j * AW + C); }
        else { spills++; S.slots.clear(); S.px.fill(0); S.n = 0; spill = true; B.full = true; s = S.n++; } used.add(s); }   // (the land being made uses all 4096: its own paints go, never the shown land's; it is made again, steps)
      S.slots.set(key, s); const at = (s / SL | 0) * C * AW + (s % SL) * C; paint(S.px, at, AW); { const q = S.px[at + 7 * AW + 7]; if ((q >>> 24) > 127) for (let i = 0; i < 3; i++) mean[i] += ((q >> 8 * i & 255) / 255 - mean[i]) * .03; } if (!mk) dirty.push(s); else B.add.push(s); return s;   // (a new paint is sent alone: the whole sheet, a million px, was sent again for each)
    }
    const land = VoxStyleLand.create(host, cfg, {SL, C, slot, unslot(k) { A.slots.delete(k); if (B) B.slots.delete(k); }, use(l) { for (const v of l) used.add(v); }, get mk() { return mk; }, start(ag) { fromNone = wipe || ag; wipe = false; if (fromNone) wipes++; B = null; spill = false; used = new Set(); return fromNone; }, spill: () => spill});
    // A LOST CONTEXT (a phone's tab put away, its GPU's memory wanted, the GPU reset): a new canvas and context, made the next frame (then once a second till one is given), everything sent again
    // from what is kept here (the faces' lists, the paints' px): the land comes back as it was. It was the land gone for good, the sky and the names left ("sometimes the map disappears")
    let was = false, tried = 0;
    function start() {
      if (gl && gl.isContextLost()) { gl = null; was = true; tried = 0; }   // (lost before its event came: not a frame drawn on a dead canvas)
      if (gl) return true; if (was && performance.now() - tried < 1000) return false;
      const c = document.createElement("canvas"), g = c.getContext("webgl2", {antialias: false, depth: true, stencil: true, preserveDrawingBuffer: true}); if (!g) { tried = performance.now(); return false; }
      c.addEventListener("webglcontextlost", (e) => { e.preventDefault(); if (gl === g) { gl = null; was = true; tried = 0; } }); el = c; gl = g;
      const keep = was ? {land: bufs.land.stat, shade: bufs.shade.stat, water: bufs.water.stat} : null; for (const k in U) delete U[k];
      const prog = (vs, fs, names) => { const p = gl.createProgram(); for (const [ty, s] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) { const sh = gl.createShader(ty); gl.shaderSource(sh, s); gl.compileShader(sh); if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); gl.attachShader(p, sh); } names.forEach((n, i) => gl.bindAttribLocation(p, i, n)); gl.linkProgram(p); return p; };
      pr = prog(VS, FS, ["p", "uv", "a", "e"]); sp = prog(SV, SF, ["p", "uv", "s", "k"]); W_ = VoxStyleWin.create(gl); [tex, wtx, htx, ltx, atx, stx] = [0, 0, 0, 0, 0, 0].map(() => gl.createTexture());
      // a list of faces on the GPU: what was made (stat) and after it room for what changes by the frame (its tail)
      for (const k of ["land", "shade", "water", "spr"]) { const b = bufs[k] = {buf: gl.createBuffer(), vao: gl.createVertexArray(), n: 0, cap: 0, stat: new Float32Array(0)}; gl.bindVertexArray(b.vao); gl.bindBuffer(gl.ARRAY_BUFFER, b.buf);
        (k === "spr" ? [[3, 0], [2, 12], [1, 20], [2, 24]] : [[3, 0], [2, 12], [4, 20], [1, 36]]).forEach(([sz, off], i) => { gl.enableVertexAttribArray(i); gl.vertexAttribPointer(i, sz, gl.FLOAT, false, (k === "spr" ? SV6 : N) * 4, off); }); }
      gl.bindVertexArray(null); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, atx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, SW, SW, 0, gl.RGBA, gl.UNSIGNED_BYTE, null); near(); gl.activeTexture(gl.TEXTURE0);
      if (keep) { fill(bufs.land, keep.land, far); fill(bufs.shade, keep.shade, new Float32Array(0)); fill(bufs.water, keep.water, new Float32Array(0)); cnt.ghost = cnt.shade2 = 0;
        stale = true; again = true; wat = null; sPx = null; sBusy = true; wKey = ""; lastU = lastS = lastG = lastD = null; shelf.x = shelf.y = shelf.h = 0; shelf.ep++; }
      return true;
    }
    const near = () => { for (const [a, b] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, a, b); };
    function fill(b, stat, tail) {   // (stat: null: as it was, only its tail changed)
      gl.bindBuffer(gl.ARRAY_BUFFER, b.buf); if (stat) b.stat = stat; b.n = b.stat.length;
      if (stat || b.n + tail.length > b.cap) { b.cap = b.n + tail.length + 8192; gl.bufferData(gl.ARRAY_BUFFER, b.cap * 4, gl.DYNAMIC_DRAW); gl.bufferSubData(gl.ARRAY_BUFFER, 0, b.stat); }
      if (tail.length) gl.bufferSubData(gl.ARRAY_BUFFER, b.n * 4, tail);
    }
    const cat = (...l) => { let n = 0; for (const a of l) n += a.length; const d = new Float32Array(n); n = 0; for (const a of l) { d.set(a, n); n += a.length; } return d; };
    function build(...a) { for (const _ of steps(...a)); }
    function* steps(...a) {   // (a tile a step: the caller spreads it over frames; only while it runs do the paints asked for go to the land being made)
      const t0 = performance.now(), g = land.steps(...a); let r;
      for (let u0 = t0, what = "first";;) { mk = true; try { r = g.next(); } finally { mk = false; } const u1 = performance.now(); units[what] = Math.max(units[what] || 0, u1 - u0); if (r.done) break; yield; u0 = performance.now(); what = r.value || "tile"; }   // (units: the longest step of each kind, ms: what a frame can be held by)
      const tS = performance.now(), R = r.value, q = R.parts; space = R.space; cutM = R.cut || null; { const wj = R.win.join(); if (wj !== winJ) { winJ = wj; winL = R.win; winN++; } } sBusy = true; clip = R.clip; wet = R.wet; far = q.far; made = R.made;   // (the window's boxes: all that changes when your space does, and sent only then; no face of the land is made again for it)
      if (start()) { fill(bufs.land, cat(q.main, q.model), far); fill(bufs.shade, q.shade, new Float32Array(0)); fill(bufs.water, cat(q.water, q.sea), new Float32Array(0)); }
      Object.assign(cnt, {main: q.main.length / N, model: q.model.length / N, far: far.length / N, shade: q.shade.length / N, water: (q.water.length + q.sea.length) / N});
      if (B) { spare = A.px; if (B.full || B.add.length > 500) stale = true; else dirty.push(...B.add); A = {slots: B.slots, px: B.px, n: B.n, free: B.free}; B = null; over = false; }   // (only the paints this land added are sent)
      again = true; lastG = lastD = null; cost = performance.now() - t0; units.send = Math.max(units.send || 0, performance.now() - tS);
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
      const m = mul(P, look(eye, at)); if (!v.pin) return {m, eye};
      // (v.pin(pr) -> [dx, dy]: px to move the whole picture by, land and sprites alike, pr(x, y, z): a place's px as drawn without it. The caller puts the land on whole px with it)
      const [dx, dy] = v.pin((x, y, z) => { const q = gp(x, y, z), w = m[3] * q[0] + m[7] * q[1] + m[11] * q[2] + m[15]; return [((m[0] * q[0] + m[4] * q[1] + m[8] * q[2] + m[12]) / w * .5 + .5) * RW, (.5 - (m[1] * q[0] + m[5] * q[1] + m[9] * q[2] + m[13]) / w * .5) * RH]; });
      const kx = 2 * dx / RW, ky = 2 * dy / RH; for (const i of [0, 4, 8, 12]) { m[i] += kx * m[i + 3]; m[i + 1] -= ky * m[i + 3]; } return {m, eye};
    }
    const PJ = new Float64Array(3);   // (projTo: a place's clip coordinates into PJ, no array made (a few hundred a frame); project: the same as a new array, for a caller that keeps it)
    const projTo = (m, x, y, z, eye) => { const p0 = x, p1 = (z - lastB[0] * (eye ? VoxStyleGLSL.sink(lastB[1] - 1 - y) : VoxStyleGLSL.sinkAt(lastB[1] - 1, y)) / H) * H, p2 = y,   // (sunk with the bend north of you, as the shader sinks the land: what stands there stood in the air past the bend, and the aim was off)
      w = m[3] * p0 + m[7] * p1 + m[11] * p2 + m[15]; PJ[0] = (m[0] * p0 + m[4] * p1 + m[8] * p2 + m[12]) / w; PJ[1] = (m[1] * p0 + m[5] * p1 + m[9] * p2 + m[13]) / w; PJ[2] = (m[2] * p0 + m[6] * p1 + m[10] * p2 + m[14]) / w; return PJ; };
    const project = (m, x, y, z) => { projTo(m, x, y, z); return [PJ[0], PJ[1], PJ[2]]; };
    // the sprites' sheet: each canvas has a place in it (shelves), its picture sent there when it is new or changed (canvas._v); full: all places given again
    const shelf = {x: 0, y: 0, h: 0, ep: 1};
    function place(c) {
      let a = c._a; if (a && a.ep === shelf.ep && a.w === c.width && a.h === c.height) return a;
      if (shelf.x + c.width + 1 > SW) { shelf.x = 0; shelf.y += shelf.h + 1; shelf.h = 0; }
      if (shelf.y + c.height + 1 > SW) return null;
      a = c._a = {x: shelf.x, y: shelf.y, w: c.width, h: c.height, ep: shelf.ep, v: -1}; shelf.x += c.width + 1; shelf.h = Math.max(shelf.h, c.height); return a;
    }
    // a sprite that stands in the window (a body, a chest, a mushroom in your room): as dim as the floor under it (the painter's own numbers for a floor, vox_style_glsl.js: by how deep it lies under the rim, and past 2.5 and 4.5 tiles from you); you: never
    // (in a dim deep room they glowed: full day's colours on a floor at .6)
    function dimOf(s, v) { if (!wmap.size) return 1; const b = wmap.get(s.tx === undefined ? Math.floor(s.x) + "," + Math.floor(s.y) : s.tx + "," + s.ty); if (!b || s.z < b[0] - 1 || s.z > b[1]) return 1; const D = Math.max(0, Math.min(16, wrim - s.z)), pd = Math.hypot(s.x - v.at[0], s.y - v.at[1]); return Math.max(.7, (1 - .025 * Math.min(6, D)) * (1 - .25 * Math.max(0, Math.min(1, (D - 3) / 9)) * (pd < 2.5 ? 0 : pd < 4.5 ? .5 : 1))); }   // (never under .7: it is still read)
    // this frame's sprites as one list of vertices (x, y, z, u, v, sil, dim, fade: how much of it is there, 0..1: a 2x2 dither in four steps) and its runs: [first vertex, count, how: 0 as the land hides it, 1 you: whole where nothing hides you, one px in two where land does]
    // (TWO BUFFERS, swapped: a frame's vertices go into the one the last frame drawn (lastS) is not, grown only when too small; the lists, runs and corners are kept and written over.
    //  It was a new Float32Array and a few small arrays a sprite, each frame: 8 to 11 MB in 3 s standing still for the collector to take back, a phone's stutter)
    const SB = [new Float32Array(4096), new Float32Array(4096)], ORD = [[], [], [], []], ON = [0, 0, 0, 0], RUN = [[], [], [], []], UPS = [], QX = new Float64Array(4), QY = new Float64Array(4), QZ = new Float64Array(4), BX = new Float64Array(4);
    const S6 = [0, 1, 2, 0, 2, 3], CU = [0, 1, 1, 0], CV = [0, 0, 1, 1], QA = [-1, 1, 1, -1], QB = [1, 1, -1, -1], SR = {d: SB[0], n: 0, runs: RUN, rn: [0, 0, 0, 0], ups: UPS, un: 0, quad: 0, me: null};
    function sprites(v, m, L, mp) {
      const RW = v.w, RH = v.h, all = v.sprites || []; let me = null; for (const s of all) if (s.top) { me = s; break; }
      const late = (s) => !!me && (s.ty !== undefined && !s.flat ? s.ty > Math.floor(me.y) : s.y > me.y);
      ON[0] = ON[1] = ON[2] = ON[3] = 0; for (const s of all) { const g = s.lie ? 3 : s.top ? 1 : late(s) ? 2 : 0; ORD[g][ON[g]++] = s; }   // (?hd: you (top) are drawn after the water: you stand in it, not under it; what stands south of you after you, and where it covers you a checker of it)   // (lie: on the water's face: after it (not tinted by it), before you (you are over it))
      const need = (ON[0] + ON[1] + ON[2] + ON[3] + 1) * 6 * SV6, bi = lastS === SB[0] ? 1 : 0; if (SB[bi].length < need) SB[bi] = new Float32Array(Math.ceil(need * 1.5));
      const d = SB[bi], rn = SR.rn; rn[0] = rn[1] = rn[2] = rn[3] = 0; let n = 0, un = 0;
      for (let g = 0; g < 4; g++) for (let si = 0; si < ON[g]; si++) { const s = ORD[g][si];
        const a = place(s.canvas); if (!a) return null; const dm = s.top ? 1 : dimOf(s, v), ver = s.canvas._v !== undefined ? s.canvas._v : s.still ? 0 : NaN; if (a.v !== ver) { UPS[un++] = s.canvas; a.v = ver; }   // (a still billboard is sent once; one with no _v and not still: each frame)
        projTo(m, s.x, s.y, s.z); const fx = Math.round((PJ[0] * .5 + .5) * RW), fy = Math.round((.5 - PJ[1] * .5) * RH), f2 = PJ[2], w = s.canvas.width, h = s.canvas.height;
        const x0 = fx - s.fx, y0 = fy - s.fy, z = s.d ? f2 - .0004 : projTo(m, s.x, s.y + .4, (s.zh ?? s.z) + 2)[2];   // (you: as far as the top of your own head, a hair south: the roof over your own tile and its floor's edge never hide you, a wall two levels high on the next tile does)
        const xa = x0 / RW * 2 - 1, xb = (x0 + w) / RW * 2 - 1, ya = 1 - y0 / RH * 2, yb = 1 - (y0 + h) / RH * 2;
        QX[0] = xa; QY[0] = ya; QX[1] = xb; QY[1] = ya; QX[2] = xb; QY[2] = yb; QX[3] = xa; QY[3] = yb; QZ[0] = QZ[1] = QZ[2] = QZ[3] = z; BX[0] = x0; BX[1] = y0; BX[2] = x0 + w; BX[3] = y0 + h;
        if (s.flat || s.lie) { const lie = !!s.lie;   // (flat: a standing face in the land, its sprite a px of paint an art px of the land, as the land's own fronts; lie: lying on the land at level z, as its own tops: a swimmer's wake on the water)
          for (let c = 0; c < 4; c++) { const i = CU[c] ? w - s.fx : -s.fx; if (lie) projTo(m, s.x + i / C, s.y + (CV[c] ? h - s.fy : -s.fy) / C, s.z); else projTo(m, s.x + i / C, s.y, s.z + (CV[c] ? s.fy - h : s.fy) / cfg.up); QX[c] = PJ[0]; QY[c] = PJ[1]; QZ[c] = PJ[2] - (lie ? .0002 : .0004); }
          BX[0] = (QX[0] * .5 + .5) * RW; BX[1] = (.5 - QY[0] * .5) * RH; BX[2] = (QX[2] * .5 + .5) * RW; BX[3] = (.5 - QY[2] * .5) * RH; }
        const over = mp && s !== me && !s.lie && late(s) && BX[0] < mp[0] + 6 && BX[2] > mp[0] - 6 && BX[1] < mp[1] - 2 && BX[3] > mp[1] - 15, how = s.top ? 1 : 0;
        const r = RUN[g], k = rn[g]; if (k && r[k - 1] === how) r[k - 2] += 6; else { r[k] = n / SV6; r[k + 1] = 6; r[k + 2] = how; rn[g] = k + 3; }   // (runs: first vertex, count, how: three numbers a run)
        for (let t = 0; t < 6; t++) { const i = S6[t]; d[n++] = QX[i]; d[n++] = QY[i]; d[n++] = QZ[i]; d[n++] = (a.x + CU[i] * a.w) / SW; d[n++] = (a.y + CV[i] * a.h) / SW; d[n++] = s.ghost ? 3 : over ? 2 : 0; d[n++] = dm; d[n++] = s.fade === undefined ? 1 : s.fade; }
      }
      const quad = n / SV6; for (let t = 0; t < 6; t++) { const i = S6[t]; d[n++] = QA[i]; d[n++] = QB[i]; d[n++] = 0; d[n++] = CU[i]; d[n++] = CV[i]; d[n++] = 0; d[n++] = 1; d[n++] = 1; }   // (the last six: the whole picture, for the hour's light)
      for (let g = 0; g < 4; g++) ORD[g].fill(null, ON[g]); UPS.fill(null, un);   // (nothing of an earlier frame held on to)
      SR.d = d; SR.n = n; SR.un = un; SR.quad = quad; SR.me = me; return SR;
    }
    // THE LIGHT OF YOUR SPACE: a number a tile (glow: tile -> [its floor's level, warm 0..1, dim 0..1]) the land's painter reads for each floor under the land (a small picture, a px a tile: stx). It goes to what the last land found
    // (space.cls: 1 walked to: warm; 2 dropped to: warm and dim; else cold) over 300 ms in six steps: a floor that joins your space warms, one that leaves it cools. It was baked in the faces: every floor flipped in one frame
    // view.way (a way shown through the land, its floors "x,y" -> level): they are lit as your space's; way.dim: the floors off it that are not your space, darker (cdv, over 300 ms)
    function light(now, way) {
      { const tg = way ? way.dim || 0 : 0, d = Math.min(.1, Math.max(0, now - cdAt)) / .3; cdAt = now; cdv += Math.max(-d, Math.min(d, tg - cdv)); } if ((way && way.key) !== sWay) { sWay = way && way.key; sBusy = true; }
      if (!sBusy) return; const k = Math.min(.1, Math.max(0, now - sAt)) / .3, sp = space, first = !glow.size, D = sp ? sp.D : sorg[2]; sAt = now; sBusy = false; if (sp) sorg = [sp.x, sp.y, D];
      const cls = (i, j, lv) => { if (!sp || i < 0 || j < 0 || i >= D || j >= D) return 0; const c = sp.cls[j * D + i]; return (c === 1 || c === 2) && sp.lvl[j * D + i] === lv ? c : 0; };
      // (each tile's name worked out once a space (sp._keys), each glow's place kept in it ([lv, warm, dim, x, y]), the picture into the one of two kept buffers not sent last, and sent only when
      //  it is not that one: tile names, split names and a string of the whole picture were made again each frame the light moved, walking: 2 MB in 2 s)
      if (sp) { const K = sp._keys || (sp._keys = new Array(D * D)); for (let i = 0; i < D * D; i++) { const lv = sp.lvl[i], c = cls(i % D, i / D | 0, lv); if (!c) continue; const key = K[i] || (K[i] = (sp.x + i % D) + "," + (sp.y + (i / D | 0))), g = glow.get(key); if (!g || g[0] !== lv) glow.set(key, [lv, first ? 1 : 0, first && c === 2 ? 1 : 0, sp.x + i % D, sp.y + (i / D | 0)]); } }
      if (way) for (const [key, lv] of way.on) { const g = glow.get(key), [x, y] = key.split(",").map(Number); if (!g || (g[0] !== lv && !cls(x - sorg[0], y - sorg[1], g[0]))) glow.set(key, [lv, 0, 0, x, y]); }
      const lb = LP[0] === sPx ? 1 : 0; if (!LP[lb] || LP[lb].length !== D * D * 4) LP[lb] = new Uint8Array(D * D * 4); else LP[lb].fill(0); const px = LP[lb];
      glow.forEach((g, key) => { const i = g[3] - sorg[0], j = g[4] - sorg[1], on = cls(i, j, g[0]) || (way && way.on.get(key) === g[0] ? 1 : 0), w = on ? 1 : 0, d = on === 2 ? 1 : 0;
        g[1] += Math.max(-k, Math.min(k, w - g[1])); g[2] += Math.max(-k, Math.min(k, d - g[2])); if (g[1] !== w || g[2] !== d) sBusy = true; if (!on && g[1] <= 0) { glow.delete(key); return; }
        if (i >= 0 && j >= 0 && i < D && j < D) { const o = (j * D + i) * 4; px[o] = Math.round(g[1] * 6) * 42.5; px[o + 1] = (g[0] + 1024) % 256; px[o + 2] = Math.round(g[2] * 6) * 42.5; } });
      if (sPx && sPx.length === px.length && sOrg && sOrg[0] === sorg[0] && sOrg[1] === sorg[1] && sOrg[2] === sorg[2] && sameN(px, px.length, sPx, sPx.length)) return; sPx = px; sOrg = sorg; sver++;   // (the picture sent last, and where)
      gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, stx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, D, D, 0, gl.RGBA, gl.UNSIGNED_BYTE, px); near(); gl.activeTexture(gl.TEXTURE0);
    }
    function draw(v) {
      if (!start()) return was ? false : null; light(v.t || 0, v.way || null);   // (false: lost, none given yet: the host keeps its last picture, hd.js lost; null: no WebGL 2 at all)
      const t0 = performance.now(), L = v.light, RW = v.w, RH = v.h, W = v.water, hr = v.hour, sized = el.width !== RW || el.height !== RH;
      if (sized) { el.width = RW; el.height = RH; }
      const {m, eye} = matrix(v); if (!sameN(m, 16, lastM, 16) || lastB[0] !== (v.bend || 0) || lastB[1] !== v.at[1]) mver++; lastM = m; lastB = [v.bend || 0, v.at[1]]; const lamp = gp(...v.at);   // (mver: goes up when where a place is drawn (at) changes: marks drawn from it are kept till then)
      // what this frame is made of, before anything is sent: the ghosts and the moving shadows (view.ghosts: [[x, y, box]...], made each frame), the sprites, every number the painter takes
      const gh = GW[lastG === GW[0] ? 1 : 0], sd = DW[lastD === DW[0] ? 1 : 0]; gh.n = sd.n = 0; for (const g of v.ghosts || []) land.model(g[0], g[1], g[2], g[2].shade ? sd : gh);   // (into the writer the last frame drawn is not in: GW, DW)
      const mef = (v.sprites || []).find((s) => s.top), mf = mef && project(m, mef.x, mef.y, mef.z), mp = mf && [(mf[0] * .5 + .5) * RW, (.5 - mf[1] * .5) * RH], disc = mp ? [mp[0], RH - mp[1] + 1, 12] : [0, 0, 0];   // (the disc round you: what covers you is seen through there only)
      // (the window's cut sides (vox_style_glsl.js PORT): view.edge "A" crisp, a brown line and a shade; "B" the kept land fading in steps; "C" a shade on your floor)
      const pw = [{A: 1, B: 2, C: 3}[v.edge] || 2, 0, 1, 0];
      const wup = !!(W && W.canvas && W.canvas.width && wet && (!wat || (W.ver !== undefined ? W.ver !== wat[5] : Math.abs((v.t || 0) - wat[4]) > .1 || !v.t)));   // (the water's picture: when the host made a new one (ver), ten times a second; with no water in the land, never)
      const wv = W && W.canvas && W.canvas.width && wet ? (wup ? [W.x, W.y, W.canvas.width, W.canvas.height] : wat.slice(0, 4)) : [0, 0, 0, 0];
      const own = (v.own || []).filter((b) => (v.sky || !b[4]) && !winL.some((t) => t[0] === b[0] && t[1] === b[1] && t[2] <= b[2] && t[3] > b[2])), winA = (own.length ? winL.concat(own) : winL).filter((t) => v.sky || !t[4]);   // (a tile of your space under the open sky only while land hides you there (v.sky, hd_level.js hides): the shaft you stepped out of had its south wall cut away, its floor drawn where it projects, south of its rim: "a drawer")   // (view.own: boxes that are yours whatever the last land's search found: your tile, where you came from: the window is on you the frame land covers you, not when the search is done)
      const rimz = v.rim === undefined ? v.at[2] - .5 : v.rim, cpx = cfg.up * Math.cos(v.cam.pitch * Math.PI / 180), sn = 16 * Math.sin(v.cam.pitch * Math.PI / 180), per = (t) => Math.max(1, Math.min(48, (rimz - t[3]) * cpx)) / sn, gn = rimz + "," + cpx;
      // (view.rim: the level of the land round your hole. DEPTH: the section over a tile's north edge is as tall as the ground over its ceiling really is, seen from this eye: cpx px a level (8.5 from 58 degrees, hd.js STEEP), 48 px at most (the shader's search, vox_style_glsl.js: 5 levels and more from 58), up to the surface's own line, as the north wall of a dug pit would stand: a room 14 down has a wall 48 px tall over it, one 4 down 8.
      //  It was a band of 8 to 20 rows whatever the depth, and half the floor at most: 6 deep and 14 deep read 1 to 3 deep)
      const wk = winN + "|" + (v.way ? v.way.key : "") + "|" + own.join() + "|" + gn, now = v.t || 0; if (wk !== wKey && (winA.length || wxr <= 0)) { wKey = wk; wmap = new Map(winA.map((t) => [t[0] + "," + t[1], [t[2], t[3]]])); const roofed = (x, y, lv) => { const c = host.column(x, y); return !!c && c.length > 0 && c[c.length - 1] > lv; }; W_.set(v.way && winA.length ? winA.concat([...v.way.on].map(([k, lv]) => { const [x, y] = k.split(",").map(Number); return [x, y, lv, lv + 2]; }).filter((b) => roofed(b[0], b[1], b[2]))) : winA, per); }   // (shut: the last window stays while it fades) (the way's floors under the land only: under the open sky its marks are seen as they are. Along a river in a gorge they were a path of boxes one tile wide through the bank: slivers of it left standing in the hole)
      { const d = Math.min(.1, Math.max(0, now - wAt)) / .1; wAt = now; wxr = W_.n ? Math.max(0, Math.min(1, wxr + (v.win && winA.length ? d : -d))) : 0; if (v.win && own.length && v.dep > 0) wxr = Math.max(wxr, .5); }   // (a roof over you and the search not done: half its px that very frame, the rest in three: it was all of it in one frame, a pop)
      const ct = cutM && cutM.size ? 1 : 0;   // (the land really cut under it, vox_style_land.js: the window paints no section, no strata on its walls: they are the land's own blocks)
      wrim = rimz; let S = sprites(v, m, L, mp); if (!S) { shelf.x = shelf.y = shelf.h = 0; shelf.ep++; S = sprites(v, m, L, mp); if (!S) return el; }
      { const fr = cfg.rock ? cfg.rock.from : cfg.levels[1], top = Math.round(v.at[2] - .5 + (v.dep || 0)), cl = (z) => Math.max(cfg.levels[0], Math.min(cfg.levels[1], z)), ws = (lv) => slot("f" + lv + ",0", (px, at, st) => host.paintFront(lv, 0, px, at + (C - cfg.up) * st, st));   // (the window's section: the wall paints of the ground it is cut in, earth and stone (the land's own slots for them): the painter lays their rows over the window's north edge)
        const e = host.paintFront ? ws(cl(Math.min(top, fr - 1))) : 0, r = host.paintFront ? ws(cl(Math.max(top, fr))) : 0; sectAt = [(e % SL) * C, (e / SL | 0) * C, (r % SL) * C, (r / SL | 0) * C]; }
      const bd = NOBODY;   // (nobody: a body on the land over the window is not drawn at all now, hd.js; it was drawn with the ground under its feet kept one px in two)
      const un = UB[lastU === UB[0] ? 1 : 0]; ub = un.f; uq = 0;   // (every number the painter takes, into the buffer the last frame drawn is not in)
      uP(RW); uP(RH); uA(bd); uA(m); uA(eye); uA(lamp); uP(v.bend || 0); uA(L.fogc); uP(L.lr); uP(L.day); uP(L.amb); uP(L.fog[0]); uP(L.fog[1]); uP(L.rim); uP(L.wa ?? .62); uP(v.dep || 0); uP(L.sun ?? 1);
      uA(L.wtint || Z40); uA(wv); uA(disc); uA(pw); uA(clip); uA(L.clear); uP(L.ca ?? 1); uP(sver); uA(sorg); uP(wxr); uP(W_.ver); uA(sectAt); uP(rimz); uP(cpx); uP(v.behind || 0); uP(v.under || 0);
      if (hr) { uP(1); uA(hr.wash); uA(hr.tint || NOTINT); uP(hr.lit ? (hr.lit._v === undefined ? NaN : hr.lit._v) : -1); } else uP(0); un.n = uq;
      const gSame = sameW(gh, lastG), dSame = sameW(sd, lastD);
      why = again ? "land" : sized ? "size" : stale || dirty.length ? "paints" : S.un ? "pictures" : wup ? "water" : !gSame ? "ghosts" : !dSame ? "shadows" : !sameN(S.d, S.n, lastS, lastSn) ? "sprites" : !sameW(un, lastU) ? "view " + firstOff(un, lastU) : "";   // (why this frame is drawn again; "": it is the last one)
      if (!why) { fresh = false; cost = performance.now() - t0; return el; }   // (nothing changed: the picture drawn last frame is this frame's)
      again = false; fresh = true; lastU = un; lastS = S.d; lastSn = S.n; calls = 0;
      if (!gSame) { fill(bufs.land, null, cat(far, gh.f.subarray(0, gh.n))); lastG = gh; cnt.ghost = gh.n / N; } if (!dSame) { fill(bufs.shade, null, sd.f.subarray(0, sd.n)); lastD = sd; cnt.shade2 = sd.n / N; }
      if (wxr > 0) W_.pass(m, lamp, v.bend || 0, RW, RH);
      gl.viewport(0, 0, RW, RH); gl.clearColor(...L.clear, L.ca ?? 1); gl.clearStencil(0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT | gl.STENCIL_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.disable(gl.CULL_FACE); gl.disable(gl.BLEND); gl.depthMask(true); if (wxr > 0) W_.back((v.sect || SECT)[3] || [.1, .08, .1]);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
      if (stale) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, AW, AW, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(A.px.buffer)); near(); stale = false; dirty.length = 0; }
      if (dirty.length) { const rows = new Map(); for (const sl of dirty) { const j = sl / SL | 0, i = sl % SL, r = rows.get(j); if (r) { r[0] = Math.min(r[0], i); r[1] = Math.max(r[1], i); } else rows.set(j, [i, i]); }   // (new paints: each row of the sheet's slots in one piece, not a piece a paint)
        for (const [j, [i0, i1]] of rows) { const w = (i1 - i0 + 1) * C; for (let k = 0; k < C; k++) row.set(A.px.subarray((j * C + k) * AW + i0 * C, (j * C + k) * AW + i0 * C + w), k * w); gl.texSubImage2D(gl.TEXTURE_2D, 0, i0 * C, j * C, w, C, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(row.buffer, 0, w * C * 4)); } dirty.length = 0; }
      if (wup) { gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, wtx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, W.canvas); near(); wat = [W.x, W.y, W.canvas.width, W.canvas.height, v.t || 0, W.ver]; }   // (with where it was then)
      gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, stx); gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, wtx); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, atx);
      for (let i = 0; i < S.un; i++) { const c = S.ups[i]; gl.texSubImage2D(gl.TEXTURE_2D, 0, c._a.x, c._a.y, gl.RGBA, gl.UNSIGNED_BYTE, c); }
      gl.activeTexture(gl.TEXTURE0);
      gl.useProgram(pr); const u = (n) => U[n] || (U[n] = gl.getUniformLocation(pr, n)), us = (n) => U["s" + n] || (U["s" + n] = gl.getUniformLocation(sp, n));
      gl.uniformMatrix4fv(u("m"), false, m); gl.uniform1i(u("t"), 0); gl.uniform1i(u("wt"), 2); gl.uniform1i(u("gw"), 3); gl.uniform1i(u("mk"), 4); gl.uniform1f(u("xr"), wxr); gl.uniform1f(u("ct"), ct); gl.uniform3fv(u("sc"), (v.sect || SECT)[0]); gl.uniform4fv(u("sp"), sectAt); gl.uniform1f(u("rf"), cfg.rock ? cfg.rock.from : 1e9); gl.uniform3fv(u("go"), sorg); gl.uniform3fv(u("lamp"), [lamp[0], lamp[1] + .6, lamp[2]]); gl.uniform3fv(u("eye"), eye);   // ("gw", not "st": the sprites' names are kept under "s" + name)
      gl.uniform3fv(u("em"), mean); gl.uniform3fv(u("ctr"), lamp); gl.uniform1f(u("bend"), v.bend || 0); gl.uniform2f(u("vpx"), RW, RH); gl.uniform3fv(u("fogc"), L.fogc); gl.uniform4fv(u("cl"), clip);
      { const f1 = (n, x) => gl.uniform1f(u(n), x); f1("lr", L.lr); f1("day", L.day); f1("amb", L.amb); f1("fn", L.fog[0]); f1("ff", L.fog[1]); f1("rim", L.rim); f1("wa", L.wa ?? .62); f1("dep", v.dep || 0); f1("rd", 0); f1("sun", L.sun ?? 1); f1("shp", 0); f1("cd", cdv); f1("rz", rimz); f1("cp", cpx); f1("bh", v.behind || 0); f1("ud", v.under || 0); }
      gl.uniform4fv(u("wtn[0]"), L.wtint || Z40); gl.uniform4fv(u("wv"), wv); gl.uniform3fv(u("mc"), disc); gl.uniform3fv(u("bd[0]"), bd); gl.uniform4fv(u("pw"), pw); gl.uniform1f(u("bp"), 0);
      gl.useProgram(sp); gl.uniform1i(us("t"), 1); gl.uniform1i(us("mk"), 4); gl.uniform2f(us("nf"), .5, 200); gl.uniform3fv(us("mc"), disc); gl.uniform4fv(us("pw"), pw); gl.useProgram(pr);
      const go = (b, from, n) => { if (n > 0) { gl.bindVertexArray(b.vao); gl.drawArrays(gl.TRIANGLES, from, n); calls++; } };
      go(bufs.land, 0, cnt.main + cnt.model + cnt.far + cnt.ghost);   // (the land, what stands in it as boxes, the far land, the ghosts: one list)
      if (wxr > 0 && pw[0] === 2) { gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false); gl.uniform1f(u("bp"), 1); go(bufs.land, 0, cnt.main + cnt.model); gl.uniform1f(u("bp"), 0); gl.depthMask(true); gl.disable(gl.BLEND); }   // (B: the kept land's last px along a cut's side, over your space, in steps of opacity)
      gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
      // the shadows: each px of the land shaded once, however many lie on it (a stencil): first all their full px, then their soft rims where no full one lies
      gl.enable(gl.STENCIL_TEST); gl.stencilFunc(gl.NOTEQUAL, 1, 1); gl.stencilOp(gl.KEEP, gl.KEEP, gl.REPLACE);
      for (let rimp = 0; rimp < 2; rimp++) { gl.uniform1f(u("shp"), rimp); go(bufs.shade, 0, cnt.shade + cnt.shade2); } gl.disable(gl.STENCIL_TEST);
      gl.depthMask(true); gl.disable(gl.BLEND);
      // the sprites: px for px, their foot snapped to a whole px (you are never lost: under the land the window is on you, behind it you show through it)
      gl.bindBuffer(gl.ARRAY_BUFFER, bufs.spr.buf); gl.bufferData(gl.ARRAY_BUFFER, S.d, gl.STREAM_DRAW, 0, S.n);   // (its first S.n numbers: the buffer is kept, and longer)
      const run = (g) => { const R = S.runs[g], rn = S.rn[g]; if (!rn) return; gl.useProgram(sp); gl.uniform1f(us("xr"), g === 1 ? 0 : wxr); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, atx);
        for (let ri = 0; ri < rn; ri += 3) { const from = R[ri], n = R[ri + 1], how = R[ri + 2];
          if (how === 1 && v.hid !== 0) { gl.depthMask(false); gl.depthFunc(gl.GREATER); gl.uniform1f(us("hid"), wxr > 0 ? 2 : v.behind > 0 ? 0 : 1); go(bufs.spr, from, n); gl.uniform1f(us("hid"), 0); gl.depthFunc(gl.LEQUAL); }   // (YOU ARE BEHIND what is in front of you: where land hides you (a hill, a wall, a cliff: whatever the window is not on) one px in two of you, a little dimmer, the land's px between them; the rest of you whole. It was all of you over everything: behind a wall you stood on it)
          go(bufs.spr, from, n); gl.depthMask(true); }
        gl.activeTexture(gl.TEXTURE0); gl.useProgram(pr); };
      run(0);
      gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
      go(bufs.water, 0, cnt.water);
      gl.blendFuncSeparate(gl.ONE_MINUS_DST_ALPHA, gl.ONE, gl.ONE_MINUS_DST_ALPHA, gl.ONE); gl.uniform1f(u("wu"), 1); go(bufs.water, 0, cnt.water); gl.uniform1f(u("wu"), 0);   // (and under what it left half there: whole where nothing is behind it, vox_style_glsl.js)
      gl.depthMask(true); gl.disable(gl.BLEND); run(3);
      if (S.me) { run(1); if (cnt.model) { gl.uniform1f(u("rd"), 1); go(bufs.land, cnt.main, cnt.model); gl.uniform1f(u("rd"), 0); } } run(2);   // (rd: what stands as boxes south of you and over your feet, again over you: one px in two, in the disc)
      if (hr) {   // the hour's light, here and not on a canvas of the page's (it was four of them laid on each other every frame, the last cut out by this picture: slow on a phone, and a phone has drawn such chains wrong): a wash of the hour's colour where something is drawn, then all of it times the light's picture (the lamps in it)
        const a = hr.wash[3], quad = (t, sf, df) => { gl.bindTexture(gl.TEXTURE_2D, t); gl.blendFuncSeparate(sf, df, gl.ZERO, gl.ONE); go(bufs.spr, S.quad, 6); }, one = (t, c, k) => { if (k !== t._k) { gl.bindTexture(gl.TEXTURE_2D, t); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([c[0], c[1], c[2], 255])); near(); t._k = k; } };
        gl.useProgram(sp); gl.uniform1f(us("xr"), 0); gl.disable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.activeTexture(gl.TEXTURE1);
        if (a > .004) { one(htx, [hr.wash[0] * a, hr.wash[1] * a, hr.wash[2] * a], hr.wash.join()); gl.blendColor(0, 0, 0, a); quad(htx, gl.DST_ALPHA, gl.ONE_MINUS_CONSTANT_ALPHA); }
        if (hr.lit) { const k = "c" + hr.lit._v; if (hr.lit._v === undefined || ltx._k !== k) { gl.bindTexture(gl.TEXTURE_2D, ltx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, hr.lit); near(); ltx._k = k; } quad(ltx, gl.DST_COLOR, gl.ZERO); }
        else if (hr.tint) { one(ltx, hr.tint, hr.tint.join()); quad(ltx, gl.DST_COLOR, gl.ZERO); }   // (hour.tint: the light one colour all over)
        gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.activeTexture(gl.TEXTURE0); gl.useProgram(pr);
      }
      gl.bindVertexArray(null); cost = performance.now() - t0;
      return el;
    }
    return {build, steps, start, touch: land.touch, touchBox: land.touchBox, wet: land.wet, get water() { return cnt.water; }, draw, forget() { wipe = true; land.clear(); }, get lost() { const l = lost; lost = false; return l; }, get cost() { return cost; }, cut: (x, y) => (cutM ? cutM.get(x * 1048576 + y) : undefined),   // (the land's cut under it: its cells over that height not drawn, vox_style_land.js)
      get win() { return {n: W_ ? W_.n : 0, a: wxr, tiles: W_ ? W_.tiles : []}; },   // (the x-ray window: its boxes [x, y, lo, hi], how open it is 0..1)
      spaceAt(x, y) { const sp = space, i = sp ? x - sp.x : -1, j = sp ? y - sp.y : -1; return sp && i >= 0 && j >= 0 && i < sp.D && j < sp.D && sp.cls[j * sp.D + i] && sp.lvl[j * sp.D + i] !== -32768 ? [sp.lvl[j * sp.D + i], sp.cls[j * sp.D + i]] : null; },   // (tests: a tile of your space: [its floor's level, 1 walked to | 2 dropped to | 3 dropped from])
      get stamp() { return land.stamp; }, get work() { return {wipes, spills, overs, fars: land.fars}; }, get part() { return land.part; },   // (work: lands made again from none, far patches made: tests)
      get made() { return made; }, get fresh() { return fresh; }, get calls() { return calls; }, get why() { return why; }, units,
      bare(y0) { const w = el ? el.width : 0, h = el ? el.height - y0 : 0; if (!gl || w <= 0 || h <= 0) return 0; const b = new Uint8Array(w * h * 4); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, b); let n = 0; for (let i = 3; i < b.length; i += 4) if (!b[i]) n++; return n; },   // (tests: px of the picture from row y0 down where no land is drawn: the backdrop shows there)
      raw() { const w = el ? el.width : 0, h = el ? el.height : 0; if (!gl || w <= 0 || h <= 0) return 0; const b = new Uint8Array(w * h * 4); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, b); let n = 0; for (let i = 3; i < b.length; i += 4) if (b[i] > 235 && b[i] < 255) n++; return n; }, blank() { A.px.fill(0); stale = true; },   // (tests: px of the picture drawn from a paint that is not there (the painter marks them: vox_style_glsl.js `raw`); blank: the shown land's paints taken away, as a lost sheet would be)
      at(x, y, z, eye) { if (!lastM) return null;   /* (eye: bent as from a corner row of the bend, vox_style_glsl.js sink: the sky's line, hd_eye.js, still as you walk) */ const f = projTo(lastM, x, y, z, eye); return [(f[0] * .5 + .5) * el.width, (.5 - f[1] * .5) * el.height]; }, get mver() { return mver; }, get faces() { return (cnt.main + cnt.model) / 6; }, get models() { return cnt.model / 6; }};
  }
  return {create};
})();
