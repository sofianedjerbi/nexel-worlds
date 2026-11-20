// VOX: the land under ground (the HD-2D look): when the land is over you, a slice through the earth round you, your
// space hollowed in it and lit by your lantern, the cut in natural wavy strata (earth near the meadow, stone deeper),
// a cool beam where it opens to the sky, a cave on another level a darker hollow. It names no global of the game: the
// host is the engine's own (vox_engine.js: column, paintTop, paintFront, rock, water, waterTop). Drawn at the art's
// own size (one px of the canvas = one art px; the game lays it on its canvas zoom times bigger), every face painted
// from the tileset: a top by paintTop, a side by paintFront (its cfg.up rows, never stretched).
//   VoxUnder.create(host, cfg) -> {build(x, y, L, ceil, o), draw(view) -> canvas, cost, faces, skies, holes, at(x, y, z)}
//   o (build): {r: tiles round, deep: levels under your feet}
//   view: {w, h, cam: {pitch, fov}, at: [x, y, z], light: {amb, lr, day, sk, fog: [near, far], fogc: [r, g, b], clear},
//          water: {canvas, x, y}, dep: levels of land over you, t, sprites: [{canvas, x, y, z, fx, fy}] (its foot at px (fx, fy))}
const VoxUnder = (() => {
  const H = .5, SL = 64, C = 16, AW = SL * C, N = 10;
  const VS = `#version 300 es
  in vec3 p; in vec2 uv; in vec4 a; in float e; uniform mat4 m; uniform vec3 ctr; uniform float bend; out vec2 vu; out vec4 va; out float ve; out vec3 wp;
  void main() { vec3 q = p; float dn = max(0., ctr.z - 1. - q.z); q.y -= bend * dn * dn; gl_Position = m * vec4(q, 1.); vu = uv; va = a; ve = e; wp = p; }`;
  const FS = `#version 300 es
  precision mediump float; in vec2 vu; in vec4 va; in float ve; in vec3 wp; uniform sampler2D t, wt; uniform vec3 lamp, eye, fogc;
  uniform float dep, sk, lr, day, amb, fn, ff, tm; uniform vec4 wv; out vec4 o;
  uniform vec2 vp; float hsh(vec2 v) { return fract(sin(dot(v, vec2(12.99, 78.23))) * 43758.5); }
  float bit(float v, float k) { return mod(floor(v / k), 2.); }
  vec3 rk(vec2 g, float d0, float kd) {   // natural strata: bands of uneven thickness and tone, earth near the meadow, stone deeper (g.y down = deeper)
    float b = g.y + floor(3. * sin(g.x * .09 + floor(g.y / 23.)) + 2. * sin(g.x * .031 + 1.7)), bd = floor(b / 11.), lb = b - bd * 11.;
    if (lb < (hsh(vec2(bd, 1.)) - .5) * 8.) { bd -= 1.; lb += 11.; } else if (lb >= 11. + (hsh(vec2(bd + 1., 1.)) - .5) * 8.) { bd += 1.; lb -= 11.; }
    float bdep = d0 + bd * 11. * kd, bn = hsh(vec2(bd, 3.));
    float st = step(bn, clamp((bdep - 1.) / 8., 0., .85)), sh = hsh(vec2(bd, 5.)), hu = hsh(vec2(bd, 6.));
    sh = floor(sh * 5.) / 4. + (hsh(g) > .92 ? .2 : 0.) - (hsh(g + 3.) > .95 ? .15 : 0.);
    vec3 ea = mix(vec3(.62, .41, .24), vec3(.36, .23, .14), sh), sa = mix(vec3(.56, .51, .45), vec3(.28, .27, .29), sh) * (hu < .33 ? vec3(1.08, .96, .84) : hu < .66 ? vec3(.92, .97, 1.06) : vec3(1.));
    vec3 col = mix(ea, sa, st); float lo = lb - (hsh(vec2(bd, 1.)) - .5) * 8.;
    if (lo < 1. && hsh(vec2(bd, 9.)) > .4 && hsh(vec2(floor((g.x + bd * 7.) / 6.), bd)) > .35) col *= .62;   // a seam: on some boundaries only, broken
    vec2 pc = floor(g / 7.); float ph = hsh(pc); vec2 pp = mod(g, 7.) - floor(vec2(hsh(pc + 7.), hsh(pc + 9.)) * 4. + 1.);
    if (ph > .68 && pp.x >= 0. && pp.x < 2. && pp.y >= 0. && pp.y < 2. - step(.84, ph)) col = (st > .5 ? vec3(.58, .55, .5) : vec3(.66, .52, .37)) * (pp.y < 1. ? 1.1 : .78);   // a pebble
    return col;
  }
  void main() {
    float kind = va.z; vec2 lu = mod(vu, 16.);
    vec4 c = texture(t, vu / ${AW}.); if (c.a < .5) c = vec4(.42, .32, .25, 1.);
    float d = distance(wp, lamp) / lr, lan = clamp(1.15 - d * d, 0., 1.);
    float l = max(va.y * day, amb + (1. - amb) * lan) * va.x;
    vec3 warm = mix(vec3(1.), vec3(1.1, .97, .8), lan * (1. - va.y));
    vec3 col = c.rgb * l * warm;
    if (kind < 2.5) {                                    // under ground: a slice through the earth, your space hollowed in it
      if (kind > 1.5) {                                          // the cut: dark earth near the surface, stone deeper, in strata
        vec2 g = floor(wp.xz * 16.); col = rk(g, dep + (5. - lamp.z * 16.) / 16. * 1.6, 1.6 / 16.);
        vec2 sc = gl_FragCoord.xy / vp - .5; col *= .7 * (1. - .9 * dot(sc, sc));                // darker and flat, darker to the screen's edges
        if (bit(ve, 16.) > .5) col = c.rgb * .13 * (mod(g.x + g.y, 2.) < 1. ? 1. : .8) + vec3(.02);   // a cave on another level: dark, its floor faint
        if ((bit(ve, 32.) > .5 && lu.y < 2.) || (bit(ve, 64.) > .5 && lu.x > 14.) || (bit(ve, 128.) > .5 && lu.y > 14.) || (bit(ve, 256.) > .5 && lu.x < 2.)) col = vec3(.85, .68, .48);
        float r = 0.; if (bit(ve, 1.) > .5 && lu.y < 1.) r = 1.; if (bit(ve, 2.) > .5 && lu.x > 15.) r = 1.; if (bit(ve, 4.) > .5 && lu.y > 15.) r = 1.; if (bit(ve, 8.) > .5 && lu.x < 1.) r = 1.;
        col = mix(col, vec3(.95, .75, .5) * (.5 + lan), r * .8);
      } else if (kind < .5) { col = rk(floor(vec2((wp.x + wp.z) * 16., -wp.y * 16.)), dep + (lamp.y - .6) / .5, 1. / 8.) * l * warm * .6; }   // a wall: the strata in world height (one band pattern, not per level)
      else {                                                      // a floor: a step down has a lit lip, a step up shades its foot
        float ue = min(min(mix(9., lu.y, bit(ve, 512.)), mix(9., 15. - lu.x, bit(ve, 1024.))), min(mix(9., 15. - lu.y, bit(ve, 2048.)), mix(9., lu.x, bit(ve, 4096.))));
        if (ue < 3.) col *= .45 + .15 * floor(ue);
        if (va.w > (lamp.y - .6) / .5 - 3. && ((bit(ve, 1.) > .5 && lu.y < 1.) || (bit(ve, 2.) > .5 && lu.x > 15.) || (bit(ve, 4.) > .5 && lu.y > 15.) || (bit(ve, 8.) > .5 && lu.x < 1.))) col = mix(col, vec3(1., .9, .7), .6);   // (only near your level: no lines far below)
      }
      if (va.y > .5 && kind < 1.5) col = mix(col, c.rgb * vec3(.9, 1., 1.15) * .85, .6);   // the daylight of the way up
    }
    if (kind > 2.5 && kind < 3.5) {                              // water: the game's own picture of it over a tint
      vec2 w = (vec2(wp.x, wp.z) * 16. - wv.xy) / wv.zw; vec4 wc = wv.z > 0. ? texture(wt, w) : vec4(0.);
      vec3 sea = vec3(.36, .64, .8) * max(l, .6);
      col = mix(sea, wc.rgb, wc.a * .8); o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye))), .62); return;
    }
    col = mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)));
    o = vec4(col, 1.);
  }`;
  const SV = `#version 300 es
  in vec3 p; in vec2 uv; out vec2 vu; void main() { gl_Position = vec4(p, 1.); vu = uv; }`;
  const SF = `#version 300 es
  precision mediump float; in vec2 vu; uniform sampler2D t; uniform float sil; out vec4 o; void main() { vec4 c = texture(t, vu); if (c.a < .5) discard; o = sil > .5 ? vec4(.95, .8, .55, .4) : c; }`;
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
    let el = null, skies = [], holes = [], lastM = null, gl = null, pr = null, sp = null, tex = null, wtx = null, bufs = {}, stale = true, cost = 0;
    const atlas = new Uint32Array(AW * AW), slots = new Map(), cnt = {main: 0, water: 0}, U = {};
    function slot(key, paint) {
      let s = slots.get(key); if (s !== undefined) return s;
      if (slots.size >= SL * SL) { slots.clear(); atlas.fill(0); }
      s = slots.size; slots.set(key, s); const at = (s / SL | 0) * C * AW + (s % SL) * C; paint(atlas, at, AW); stale = true; return s;
    }
    function start() {
      if (gl) return true;
      el = document.createElement("canvas"); gl = el.getContext("webgl2", {antialias: false, depth: true, preserveDrawingBuffer: true}); if (!gl) return false;
      const prog = (vs, fs) => { const p = gl.createProgram(); for (const [ty, s] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) { const sh = gl.createShader(ty); gl.shaderSource(sh, s); gl.compileShader(sh); if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); gl.attachShader(p, sh); } gl.linkProgram(p); return p; };
      pr = prog(VS, FS); sp = prog(SV, SF); tex = gl.createTexture(); wtx = gl.createTexture();
      for (const k of ["main", "water", "spr"]) bufs[k] = gl.createBuffer();
      return true;
    }
    const lim = (z) => Math.max(cfg.levels[0], Math.min(cfg.levels[1], z));
    function build(cx, cy, L, ceil, o) {
      const t0 = performance.now(), cols = new Map(), r = o.r, deep = o.deep;
      const col = (x, y) => { const k = x + "," + y; if (!cols.has(k)) cols.set(k, host.column(x, y)); return cols.get(k); };
      const inBox = (x, y) => Math.abs(x - cx) <= r && Math.abs(y - cy) <= r;
      const floorOf = (x, y, f0) => { const c = col(x, y); if (!c) return null; let best = null;   // (the floor nearest the one you come from, 2 levels up or down at the most, under the land's top)
        for (let f = f0 - 2; f <= f0 + 2; f++) if (f + 1 < c[c.length - 1] && solidC(c, f) && !solidC(c, f + 1) && (best === null || Math.abs(f - f0) < Math.abs(best - f0))) best = f; return best; };
      const reach = new Map(), st = [[cx, cy, L, 0]];   // (your own space: tiles walked to from you, a step or a short drop each, 8 tiles at the most: each cut just over its own floor, nothing of its roof kept)
      while (st.length) { const [x, y, f0, d] = st.shift(), k = x + "," + y; if (reach.has(k) || d > 8) continue; const f = floorOf(x, y, f0); if (f === null) continue;
        reach.set(k, f); for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) st.push([x + dx, y + dy, f, d + 1]); }
      const front = new Map(); for (const [k, f] of reach) { const [x, y] = k.split(",").map(Number);   // (the camera's side: rock south of your space cut to its floor, you are never hidden)
        for (let j = 1; j <= 2; j++) { const n = x + "," + (y + j); if (!reach.has(n)) front.set(n, Math.min(front.has(n) ? front.get(n) : 1e9, f)); } }
      const cuts = new Map(), cutOf = (x, y, top) => {   // (elsewhere a column with air near your level is cut at that air's own top)
        if (top > 1e8) return top; const k = x + "," + y; if (cuts.has(k)) return cuts.get(k);
        if (reach.has(k)) { cuts.set(k, reach.get(k) + 1); return reach.get(k) + 1; } if (front.has(k)) { cuts.set(k, front.get(k)); return front.get(k); } const c = col(x, y); let v = top;
        if (c) for (let z = L - 2; z <= L + 3; z++) if (!solidC(c, z)) { v = z; while (v < L + 6 && !solidC(c, v + 1)) v++; break; }
        cuts.set(k, v); return v; };
      const solidIn = (x, y, z, top) => { top = cutOf(x, y, top); if (!inBox(x, y)) return z <= top && solidC(col(x, y), z); if (z <= L - deep) return true; return z <= top && solidC(col(x, y), z); };
      const out = {main: [], water: []}; skies = []; holes = [];
      const hol = (x, y) => { const c = col(x, y); if (!c) return null; const open = c[c.length - 1], cz = cutOf(x, y, ceil);   // (a cave on another level: the level you would stand at)
        for (let z = L; z <= cz; z++) if (!solidC(c, z)) return null;
        for (let z = L - 8; z < open && z <= cz + 8; z++) if ((z < L || z > cz) && !solidC(c, z)) return z; return null; };
      const airNear = (x, y, z) => { const c = col(x, y); if (!c) return true; for (let k = L; k <= z; k++) if (!solidC(c, k)) return true; return false; };
      const faces = (x, y, z, solid, dst, cut) => {
        const c = col(x, y), open = c[c.length - 1], top = VoxMesh.topOf(c, z);
        for (let f = 0; f < 6; f++) {
          const F = FACES[f], nx = x + F.n[0], ny = y + F.n[1], nz = z + F.n[2];
          if (f === 1 || solid(nx, ny, nz)) continue;
          const nc = col(nx, ny); let sky = (f === 0 ? z >= open : !nc || z > nc[nc.length - 1]) ? 1 : 0;
          let s, kind = f === 0 ? 1 : 0, e = 0;
          if (f === 0) {
            const isCut = cut && solidC(c, z + 1), zt = isCut ? open : z; s = slot(x + "," + y + "," + zt, (px, at, st) => host.paintTop(x, y, zt, px, at, st));
            [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if (!solid(x + dx, y + dy, z)) e |= b; });
            if (isCut) kind = 2;
            else [[0, -1, 512], [1, 0, 1024], [0, 1, 2048], [-1, 0, 4096]].forEach(([dx, dy, b]) => { if (solid(x + dx, y + dy, z + 1)) e |= b; });   // (a step up at that edge: its foot in shade)
            if (isCut) sky = 0;
            if (isCut) [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if ((e & b) && !airNear(x + dx, y + dy, z)) e &= ~b; });   // (a lit rim only where your space is, not on a step of the cut)
            const hz = isCut ? hol(x, y) : null;
            if (hz !== null) { e |= 16; holes.push([x, y, hz]); [[0, -1, 32], [1, 0, 64], [0, 1, 128], [-1, 0, 256]].forEach(([dx, dy, b]) => { if (hol(x + dx, y + dy) === null) e |= b; }); }
            if (sky && !isCut) skies.push([x, y, z]);
          } else {
            const lv = lim(VoxMesh.rock(cfg, top, z, !host.rock || host.rock(x, y))), v = VoxMesh.pick(x, y, z, cfg.variants);
            s = slot("f" + lv + "," + v, (px, at, st) => host.paintFront(lv, v, px, at + (C - cfg.up) * st, st));
          }
          quad(dst, x, y, z - 1, F, F.k, sky, kind, z, e, s, solid, f === 0);
        }
      };
      for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) {
        const c = col(x, y); if (!c) continue;
        const wet = host.water && host.water(x, y), wz = wet ? (host.waterTop ? host.waterTop(x, y) : 0) : null;
        const solid = (a, b, z) => solidIn(a, b, z, ceil);
        const cz = cutOf(x, y, ceil);
        if (Math.abs(x - cx) <= 8 && Math.abs(y - cy) <= 6 && !solidC(c, L + 1)) for (let z = L + 2, sd = false; z <= Math.max(ceil, cz) + 8 && z < c[c.length - 1]; z++) { if (solidC(c, z - 1) && z - 1 > L) sd = true; if (sd && !solidC(c, z) && solidC(c, z - 1)) { holes.push([x, y, z, 1]); break; } }   // (a cave over your own space: its outline)
        for (let z = L - deep + 1; z <= Math.max(ceil, cz); z++) {
          if (!solid(x, y, z)) { if (wet && z === wz + 1) quad(out.water, x, y, z - 1, FACES[0], 1, 1, 3, z, 0, 0, null, true); continue; }
          faces(x, y, z, solid, out.main, z === cz);
        }
      }
      if (start()) for (const k in out) { const d = new Float32Array(out[k]); cnt[k] = d.length / N; gl.bindBuffer(gl.ARRAY_BUFFER, bufs[k]); gl.bufferData(gl.ARRAY_BUFFER, d, gl.STATIC_DRAW); }
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
      const p = c.pitch * Math.PI / 180, dir = [0, Math.sin(p), Math.cos(p)];
      const t = Math.tan(c.fov * Math.PI / 360), d = RH / (32 * t), eye = at.map((a, i) => a + dir[i] * d), n = .5, f = 200;
      const P = new Float32Array(16); P[0] = 1 / t / (RW / RH); P[5] = 1 / t; P[10] = (f + n) / (n - f); P[11] = -1; P[14] = 2 * f * n / (n - f);
      return {m: mul(P, look(eye, at)), eye};
    }
    const project = (m, x, y, z) => { const p = gp(x, y, z), r = [0, 1, 2, 3].map((j) => m[j] * p[0] + m[4 + j] * p[1] + m[8 + j] * p[2] + m[12 + j]); return [r[0] / r[3], r[1] / r[3], r[2] / r[3]]; };
    function pass(k, U2) {
      if (!cnt[k]) return; gl.bindBuffer(gl.ARRAY_BUFFER, bufs[k]); const S = N * 4;
      for (const [nm, sz, off] of [["p", 3, 0], ["uv", 2, 12], ["a", 4, 20], ["e", 1, 36]]) { const l = gl.getAttribLocation(pr, nm); if (l < 0) continue; gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, sz, gl.FLOAT, false, S, off); }
      if (U2) U2(); gl.drawArrays(gl.TRIANGLES, 0, cnt[k]);
    }
    function draw(v) {
      if (!start()) return null;
      const t0 = performance.now(), L = v.light, RW = v.w, RH = v.h;
      if (el.width !== RW || el.height !== RH) { el.width = RW; el.height = RH; }
      gl.viewport(0, 0, RW, RH); gl.clearColor(...L.clear, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.disable(gl.CULL_FACE); gl.disable(gl.BLEND); gl.depthMask(true);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
      const near = (t) => { for (const [a, b] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, a, b); };
      if (stale) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, AW, AW, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(atlas.buffer)); near(); stale = false; }
      const W = v.water; gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, wtx);
      if (W && W.canvas && W.canvas.width) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, W.canvas); near(); }
      gl.activeTexture(gl.TEXTURE0);
      const {m, eye} = matrix(v); lastM = m; const lamp = gp(...v.at);
      gl.useProgram(pr); const u = (n) => U[n] || (U[n] = gl.getUniformLocation(pr, n));
      gl.uniformMatrix4fv(u("m"), false, m); gl.uniform1i(u("t"), 0); gl.uniform1i(u("wt"), 2); gl.uniform3fv(u("lamp"), [lamp[0], lamp[1] + .6, lamp[2]]); gl.uniform3fv(u("eye"), eye);
      gl.uniform3fv(u("ctr"), lamp); gl.uniform1f(u("bend"), v.bend || 0); gl.uniform3fv(u("fogc"), L.fogc); gl.uniform2fv(u("vp"), [RW, RH]);
      for (const [n, x] of [["lr", L.lr], ["day", L.day], ["amb", L.amb], ["fn", L.fog[0]], ["ff", L.fog[1]], ["dep", v.dep || 0], ["sk", L.sk], ["tm", v.t || 0]]) gl.uniform1f(u(n), x);
      gl.uniform4fv(u("wv"), W && W.canvas && W.canvas.width ? [W.x, W.y, W.canvas.width, W.canvas.height] : [0, 0, 0, 0]);
      pass("main");
      // the sprites: px for px, their foot snapped to a whole px, over everything (you are never lost under ground)
      if (v.sprites) for (const s of v.sprites) {
        const f = project(m, s.x, s.y, s.z), fx = Math.round((f[0] * .5 + .5) * RW), fy = Math.round((.5 - f[1] * .5) * RH);
        const x0 = fx - s.fx, y0 = fy - s.fy, w = s.canvas.width, h = s.canvas.height, X = (px) => px / RW * 2 - 1, Y = (py) => 1 - py / RH * 2, z = project(m, s.x, s.y + .45, s.z + .3)[2];
        const d = [X(x0), Y(y0), z, 0, 0, X(x0 + w), Y(y0), z, 1, 0, X(x0 + w), Y(y0 + h), z, 1, 1, X(x0), Y(y0), z, 0, 0, X(x0 + w), Y(y0 + h), z, 1, 1, X(x0), Y(y0 + h), z, 0, 1];
        gl.useProgram(sp); gl.activeTexture(gl.TEXTURE1); const st = s.tex || (s.tex = gl.createTexture()); gl.bindTexture(gl.TEXTURE_2D, st);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, s.canvas); near(); gl.uniform1i(gl.getUniformLocation(sp, "t"), 1);
        gl.bindBuffer(gl.ARRAY_BUFFER, bufs.spr); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(d), gl.STREAM_DRAW);
        for (const [nm, sz, off] of [["p", 3, 0], ["uv", 2, 12]]) { const l = gl.getAttribLocation(sp, nm); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, sz, gl.FLOAT, false, 20, off); }
        const sil = gl.getUniformLocation(sp, "sil"); gl.uniform1f(sil, 0);
        { gl.disable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.uniform1f(sil, 1); gl.drawArrays(gl.TRIANGLES, 0, 6); gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.uniform1f(sil, 0); }   // (hidden by a wall: a faint shape of you)
        gl.drawArrays(gl.TRIANGLES, 0, 6); gl.enable(gl.DEPTH_TEST); gl.activeTexture(gl.TEXTURE0); gl.useProgram(pr);
      }
      gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
      pass("water");
      gl.depthMask(true); gl.disable(gl.BLEND);
      cost = performance.now() - t0;
      return el;
    }
    return {build, draw, forget() { slots.clear(); atlas.fill(0); stale = true; }, get cost() { return cost; }, get skies() { return skies; }, get holes() { return holes; },
      at(x, y, z) { if (!lastM) return null; const f = project(lastM, x, y, z); return [(f[0] * .5 + .5) * el.width, (.5 - f[1] * .5) * el.height]; }, get faces() { return cnt.main / 6; }};
  }
  return {create};
})();
