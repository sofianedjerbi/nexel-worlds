// VOX: the sky behind the land, over the horizon of a curved world (vox_curve.js). Made of the land's own pixels
// (a px of it is a px of the paint): bands of colour from the horizon up with a checkered step between two, a sun
// or a moon, clouds that drift, stars, two rows of far hills. It knows nothing of hours: whoever uses the engine
// says the colours and where the sun is (the game: js/curve.js).
//   sky: {line: the horizon, px of the picture from its top: the sky's bands, the sun, the clouds count from it
//         edge: where the land ends, at the line or under it (from a hill top: the land ahead lower than the eye): the far hills stand on it, the sky's
//         lowest colour goes on down to it, under it the nearer hills' colour (defaults to the line)
//         t: seconds (clouds drift, stars twinkle); shift: paint px the far hills and clouds have slid sideways
//         top, low: the sky's colour high up and at the horizon; cloud, far, near: the clouds', the far hills', the
//         nearer hills'; orb: the sun's or the moon's colour; each [r, g, b]
//         at: [x, y, r] where the sun or the moon is: across the picture (0 to 1), up from the horizon (0 to 1 of
//         the way to the picture's top), its radius (paint px); stars: 0 to 1
//         audit: under the horizon, magenta (to count what the land leaves open)
//         mid, glow: the sky's middle colour, the horizon's; shade, rim: a cloud's shaded and lit px; dusk: the sunset's
//         share (0 to 1); day: false at night (the moon); moon: its phase, 0 new, .5 full (each defaults when not said)}
const VoxSky = (() => {
  const VS = `#version 300 es\nin vec2 p; void main() { gl_Position = vec4(p, .9998, 1.); }`;
  const HEAD = `#version 300 es
precision highp float;
uniform vec2 uRes; uniform float uPx, uK, uLine, uEdge, uT, uShift, uStars, uAudit, uDusk, uDay, uMoon; uniform vec3 uTop, uLow, uCloud, uFar, uNear, uOrb, uAt, uMid, uGlow, uShade, uRim, uInk; out vec4 o;
float hash(vec2 q) { return fract(sin(dot(q, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 q) { vec2 i = floor(q), f = fract(q); f = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1., 0.)), f.x), mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), f.x), f.y); }
float ridge(float x, float seed, float f) { return noise(vec2(x * f + seed, seed)) * .6 + noise(vec2(x * f * 2.7 + seed, 3.)) * .28 + noise(vec2(x * f * 6.1, seed)) * .12; }
float bayer(vec2 a) { float i = mod(a.x, 2.) + mod(a.y, 2.) * 2.; return i < .5 ? 0. : i < 1.5 ? .5 : i < 2.5 ? .75 : .25; }
float bands(float h, float n, vec2 a) { return min(n, floor(h * n + bayer(a) * .5)) / n; }      // n flat steps, the top of each checkered into the next
vec3 grad3(float h) { return h < .4 ? mix(uLow, uMid, h / .4) : mix(uMid, uTop, (h - .4) / .6); }
float fbm3(vec2 q) { return noise(q) * .55 + noise(q * 2.3 + 4.1) * .3 + noise(q * 5.1 + 9.) * .15; }
vec3 hills(vec3 c, float ax, float ax1, float band, float dn) {      // today's two rows of far hills
  float far = min(band, 36.), h1 = ridge(ax1, 11., .03), m1 = 2. + floor(far * .62 * h1), m2 = 1. + floor(far * .3 * ridge(ax, 47., .055));
  if (dn < m1) c = mix(uFar, uLow, dn < m1 * .45 ? .4 : .16);
  if (dn < m1 && dn > m1 - 3. && h1 > .56) c = mix(c, uCloud, .6);
  if (dn < m2) c = mix(uNear, uLow, .18);
  return c; }
`;
  const PRE = `
  vec2 a = floor(vec2(gl_FragCoord.x, uRes.y * uPx - gl_FragCoord.y) / uPx / uK);
  float line = floor(uLine / uK), up = line - a.y, band = max(line, 8.), ax = a.x + floor(uShift), dn = max(line, floor(uEdge / uK)) - a.y;
  float ax1 = a.x + floor(uShift * .6), axc = a.x + floor(uShift * .3), W = uRes.x / uK;
  if (dn <= 0.) { o = vec4(uAudit > .5 && dn < 0. ? vec3(1., 0., 1.) : mix(uNear, uLow, .18), 1.); return; }
  float h = clamp(up / band, 0., 1.), d4 = bayer(a); bool chk = mod(a.x + a.y, 2.) < .5;
  vec2 orb = vec2(floor(W * uAt.x), line - floor(band * uAt.y)); float disc = length(a + .5 - orb), r = uAt.z, sgn = orb.x > a.x ? 1. : -1., rd = disc - r + (d4 - .4) * 2.;   // (rd: px out from the disc's rim, dithered: rings with checkered edges)
`;
  // THE SKY, SUN, MOON AND STARS (the owner's pick of six looks, 2026-11-24): the sky's lights made much of: a sun with eight pixel rays, a moon with its phase (the game's day count) and three craters, stars of three
    // kinds (faint, bright twinkling, a few crosses) and a faint milky band at night where they crowd; fewer, thinner clouds, their tops rimmed with light
  const FS = HEAD + `
void main() {` + PRE + `
  r = floor(r * 1.4); rd = disc - r + (d4 - .4) * 2.;      // (the sun and the moon a size bigger: they are the point of this look)
  vec3 c = grad3(bands(pow(h, .7), 8., a));
  float mw = 0.;
  if (uStars > 0.) { float m = ((a.y - line * .4) + (a.x - W * .5) * .42) / max(line * .2, 6.); mw = exp(-m * m) * (.55 + .45 * noise(a * .09)) * step(2., up); c = mix(c, uGlow, bands(mw, 3., a) * .6 * uStars);
    float hs = hash(a); if (hs > .9965 - mw * .02) c += uStars * (.25 + .3 * hash(a + 3.)); if (hs > .9994) c += uStars * (.45 + .3 * sin(uT * 2. + a.x * 1.3));
    vec2 cell = floor(a / 23.), sp = cell * 23. + floor(vec2(hash(cell + 1.), hash(cell + 2.)) * 20.) + 1., dv = abs(a - sp);
    if (hash(cell + 7.) > .78 && up > 4.) { float on = .6 + .4 * sin(uT * 1.7 + hash(cell) * 6.28); if (dv.x + dv.y < .5) c = mix(c, vec3(1., .97, .86), uStars); else if (dv.x + dv.y < 1.5 && on > .5) c = mix(c, vec3(.9, .9, 1.), .7 * uStars); } }
  c = mix(c, uOrb, rd < 2. ? .2 : rd < 4. ? .08 : 0.);
  vec2 q = vec2(axc * .03 + uT * .012, up * .085);
  float cl = fbm3(q), ct = fbm3(vec2(q.x, (up + 1.) * .085));
  if (cl > .64) c = ct <= .64 ? uRim : mix(c, uCloud, .92); else if (cl > .6) c = mix(c, uShade, .65);
  if (uDay > .5) { vec2 v = a + .5 - orb; float k8 = atan(v.y, v.x) / .7853982, off = abs(k8 - floor(k8 + .5)) * .7853982 * disc, L = mod(floor(k8 + .5), 2.) < .5 ? 6. : 3.;
    if (off < .55 && disc > r + 1.5 && disc < r + 1.5 + L) c = mix(c, uOrb, .85);
    if (disc < r) c = uOrb; }
  else if (disc < r) { float k = 1. - abs(2. * uMoon - 1.); vec2 sh = orb + vec2((uMoon < .5 ? -2. : 2.) * r * k, 0.), v = floor(a - orb);
    if (length(a + .5 - sh) > r || k > .97) { c = uOrb; if (v == vec2(-2., -1.) || v == vec2(1., 1.) || v == vec2(0., -3.)) c = uOrb * .86; } else c = mix(c, uOrb, .16); }
  o = vec4(hills(c, ax, ax1, band, dn), 1.);
}`;
  let prog = null, quad = null, bad = false, gen = 0;
  // Drawn over the whole picture, behind everything (the caller has cleared it): w, h px of the picture, pw px of
  // the canvas across, k px of the picture a px of the paint
  function draw(sky, w, h, pw, k) {
    const gl = VoxGL.gl;
    if (bad || !gl) return;
    if (gen !== VoxGL.gen) { gen = VoxGL.gen; prog = null; quad = null; }   // (a new context, the old one lost: made again in it)
    if (!prog) { try { prog = VoxGL.program(VS, FS); } catch (e) { bad = true; console.error(e); return; } }
    if (!quad) {
      quad = {vao: gl.createVertexArray(), buf: gl.createBuffer()};
      gl.bindVertexArray(quad.vao); gl.bindBuffer(gl.ARRAY_BUFFER, quad.buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, -1, 1, 1, -1, 1]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(prog.at("p")); gl.vertexAttribPointer(prog.at("p"), 2, gl.FLOAT, false, 0, 0);
    }
    const u = prog.u, f1 = (n, v) => { if (u[n]) gl.uniform1f(u[n], v); };
    gl.useProgram(prog.pr); gl.disable(gl.DEPTH_TEST); gl.depthMask(false);
    gl.uniform2f(u.uRes, w, h); f1("uPx", pw / w); f1("uK", k); f1("uLine", sky.line); f1("uEdge", sky.edge || sky.line); f1("uT", sky.t % 3600); f1("uShift", sky.shift || 0);
    f1("uStars", sky.stars || 0); f1("uAudit", sky.audit ? 1 : 0); f1("uDusk", sky.dusk || 0); f1("uDay", sky.day === false ? 0 : 1); f1("uMoon", sky.moon ?? .5);
    const mid = sky.mid || sky.top.map((v, i) => (v + sky.low[i]) / 2);
    for (const [name, v] of [["uTop", sky.top], ["uLow", sky.low], ["uCloud", sky.cloud], ["uFar", sky.far], ["uNear", sky.near], ["uOrb", sky.orb], ["uAt", sky.at], ["uMid", mid], ["uGlow", sky.glow || sky.low], ["uShade", sky.shade || sky.cloud], ["uRim", sky.rim || sky.cloud], ["uInk", sky.ink || sky.far]]) if (u[name]) gl.uniform3f(u[name], v[0], v[1], v[2]);
    gl.bindVertexArray(quad.vao); gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
  }
  return {draw};
})();
