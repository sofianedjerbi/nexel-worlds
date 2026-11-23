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
//         audit: under the horizon, magenta (to count what the land leaves open)}
const VoxSky = (() => {
  const VS = `#version 300 es\nin vec2 p; void main() { gl_Position = vec4(p, .9998, 1.); }`;
  const FS = `#version 300 es
precision highp float;
uniform vec2 uRes; uniform float uPx, uK, uLine, uEdge, uT, uShift, uStars, uAudit; uniform vec3 uTop, uLow, uCloud, uFar, uNear, uOrb, uAt; out vec4 o;
float hash(vec2 q) { return fract(sin(dot(q, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 q) { vec2 i = floor(q), f = fract(q); f = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1., 0.)), f.x), mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), f.x), f.y); }
float ridge(float x, float seed, float f) { return noise(vec2(x * f + seed, seed)) * .6 + noise(vec2(x * f * 2.7 + seed, 3.)) * .28 + noise(vec2(x * f * 6.1, seed)) * .12; }
void main() {
  vec2 a = floor(vec2(gl_FragCoord.x, uRes.y * uPx - gl_FragCoord.y) / uPx / uK);      // this px of the paint, from the picture's top left
  float line = floor(uLine / uK), up = line - a.y, band = max(line, 8.), ax = a.x + floor(uShift), dn = max(line, floor(uEdge / uK)) - a.y;      // (dn: px over the land's edge)
  // (the far hills, the further ones and the clouds slide past as you go, each slower than the one before it, by whole px;
  // under the line, where no land is known: the nearer hills' own colour, not a pale band)
  float ax1 = a.x + floor(uShift * .6), axc = a.x + floor(uShift * .3);
  if (dn <= 0.) { o = vec4(uAudit > .5 && dn < 0. ? vec3(1., 0., 1.) : mix(uNear, uLow, .18), 1.); return; }      // (the first px under the line is the hills' still: the land's last row is on the land's own px, up to half a px off the line)
  // the sky's colour: seven flat bands, the top of each checkered into the next
  float g = pow(clamp(up / band, 0., 1.), .7) * 6., i = mod(a.x, 2.) + mod(a.y, 2.) * 2., dither = i < .5 ? 0. : i < 1.5 ? .5 : i < 2.5 ? .75 : .25;
  vec3 c = mix(uLow, uTop, min(6., floor(g + dither * .5)) / 6.);
  c += step(.9975, hash(a)) * uStars * (.6 + .4 * sin(uT * 3. + a.x));
  // the sun, or the moon: a disc and two rings of its light
  vec2 orb = vec2(floor(uRes.x / uK * uAt.x), line - floor(band * uAt.y));
  float disc = length(a + .5 - orb), r = uAt.z;
  c += uOrb * (step(disc, r + 3.) * .1 + step(disc, r + 8.) * .06);
  // clouds: a body and a darker edge round it; the sun (the moon) is in front of them, the hills in front of it
  vec2 q = vec2(axc * .03 + uT * .012, up * .085);            // (the same clouds whatever the sky's height: from a tower it is the whole picture)
  float cl = noise(q) * .55 + noise(q * 2.3 + 4.1) * .3 + noise(q * 5.1 + 9.) * .15;
  if (cl > .6) c = mix(c, uCloud, .92); else if (cl > .56) c = mix(c, uCloud * .86, .7);
  if (disc < r) c = uOrb;
  // far hills in two rows, the far one with snow on its heights
  float far = min(band, 36.), h1 = ridge(ax1, 11., .03), m1 = 2. + floor(far * .62 * h1), m2 = 1. + floor(far * .3 * ridge(ax, 47., .055));      // (as tall from a mountain, where the sky is wide, as from the plain)
  if (dn < m1) c = mix(uFar, uLow, dn < m1 * .45 ? .4 : .16);
  if (dn < m1 && dn > m1 - 3. && h1 > .56) c = mix(c, uCloud, .6);
  if (dn < m2) c = mix(uNear, uLow, .18);
  o = vec4(c, 1.);
}`;
  let prog = null, quad = null, bad = false, gen = 0;
  // Drawn over the whole picture, behind everything (the caller has cleared it): w, h px of the picture, pw px of
  // the canvas across, k px of the picture a px of the paint
  function draw(sky, w, h, pw, k) {
    const gl = VoxGL.gl;
    if (bad || !gl) return;
    if (!prog || gen !== VoxGL.gen) {   // (a new context, the old one lost: made again in it)
      gen = VoxGL.gen; try { prog = VoxGL.program(VS, FS); } catch (e) { bad = true; console.error(e); return; }
      quad = {vao: gl.createVertexArray(), buf: gl.createBuffer()};
      gl.bindVertexArray(quad.vao); gl.bindBuffer(gl.ARRAY_BUFFER, quad.buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, -1, 1, 1, -1, 1]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(prog.at("p")); gl.vertexAttribPointer(prog.at("p"), 2, gl.FLOAT, false, 0, 0);
    }
    const u = prog.u;
    gl.useProgram(prog.pr); gl.disable(gl.DEPTH_TEST); gl.depthMask(false);
    gl.uniform2f(u.uRes, w, h); gl.uniform1f(u.uPx, pw / w); gl.uniform1f(u.uK, k); gl.uniform1f(u.uLine, sky.line); gl.uniform1f(u.uEdge, sky.edge || sky.line);gl.uniform1f(u.uT, sky.t % 3600); gl.uniform1f(u.uShift, sky.shift || 0);
    gl.uniform1f(u.uStars, sky.stars || 0); gl.uniform1f(u.uAudit, sky.audit ? 1 : 0);
    for (const [name, v] of [["uTop", sky.top], ["uLow", sky.low], ["uCloud", sky.cloud], ["uFar", sky.far], ["uNear", sky.near], ["uOrb", sky.orb], ["uAt", sky.at]]) gl.uniform3f(u[name], v[0], v[1], v[2]);
    gl.bindVertexArray(quad.vao); gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
  }
  return {draw};
})();
