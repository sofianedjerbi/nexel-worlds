// VOX: the X-RAY WINDOW of the 2.5D look (vox_style.js draws with it). No game global.
// Under the land nothing is taken out of the land's faces: the land is whole, as on the surface. What lets you see in is a MASK: the air of your space
// (a box a tile: its floor up to its ceiling; vox_style_land.js `win`) seen from the eye, drawn first into a picture of its own, a px a px of the land's:
// how far from the eye the nearest of those boxes is (two numbers a px: the boxes as they are, and the same a tile wider: the window's rim).
// The land's painter (vox_style_glsl.js) then leaves out what is nearer than that: you look through a hole of your cave's own shape, straight to its floor
// and walls; outside it the world is untouched. Walking moves nothing but the eye; a space that changed changes these few boxes, never the land.
//   VoxStyleWin.create(gl) -> {set(tiles: [[x, y, lo, hi, sky: 1 under the open sky]...]), n, ver, tiles, pass(m, ctr, bend, w, h): the mask's picture is made (unit 4 holds it after), back(rgb): what is behind the land taken away}
const VoxStyleWin = (() => {
  const H = .5, FAR = "255.9";
  const MV = `#version 300 es
  in vec3 p; uniform mat4 m; uniform vec3 ctr; uniform float bend; out highp float vw;
  void main() { vec3 q = p; float dn = max(0., ctr.z - 1. - q.z); q.y -= bend * dn * dn; gl_Position = m * vec4(q, 1.); vw = gl_Position.w; }`;   // (bent north of you as the land is)
  const MF = `#version 300 es
  precision highp float; in highp float vw; out vec4 o;
  void main() { float f = clamp(vw, 0., ${FAR}) * 256., hi = floor(f / 256.), lo = floor(f - hi * 256.); o = vec4(hi / 255., lo / 255., hi / 255., lo / 255.); }`;   // (tiles from the eye, a 256th of a tile exact, in two bytes)
  const BV = `#version 300 es
  in vec3 p; void main() { gl_Position = vec4(p.xy, .9999, 1.); }`;
  const BF = `#version 300 es
  precision mediump float; uniform sampler2D mk; uniform vec3 bc; out vec4 o;
  void main() { vec4 k = texelFetch(mk, ivec2(gl_FragCoord.xy), 0); if (k.b + k.a == 0.) discard; o = vec4(bc, 1.); }`;
  function create(gl) {
    const prog = (vs, fs) => { const p = gl.createProgram(); for (const [ty, s] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) { const sh = gl.createShader(ty); gl.shaderSource(sh, s); gl.compileShader(sh); if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); gl.attachShader(p, sh); } gl.bindAttribLocation(p, 0, "p"); gl.linkProgram(p); return p; };
    const mp = prog(MV, MF), bp = prog(BV, BF), U = {}, u = (p, n) => U[n] || (U[n] = gl.getUniformLocation(p, n));
    const buf = gl.createBuffer(), vao = gl.createVertexArray(), fb = gl.createFramebuffer(), tx = gl.createTexture(), rb = gl.createRenderbuffer();
    gl.bindVertexArray(vao); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 12, 0); gl.bindVertexArray(null);
    let w = 0, h = 0, n = 0, tiles = [], ver = 0;
    // a tile's box, g tiles wider each way: its top and its four sides (the eye never comes in from under it)
    function box(d, o, x, y, lo, hi, g, sky) {   // (sky: a tile under the open sky: wider to the south only: north and beside it stand the walls of its hole, seen and not looked through: the rim lay on a gorge's far cliff)
      const x0 = x - (sky ? 0 : g), x1 = x + 1 + (sky ? 0 : g), y0 = y - (sky ? 0 : g), y1 = y + 1 + g, a = lo * H, b = hi * H, q = (...c) => { for (const i of [0, 1, 2, 0, 2, 3]) { d[o++] = c[i][0]; d[o++] = c[i][1]; d[o++] = c[i][2]; } };
      q([x0, b, y0], [x1, b, y0], [x1, b, y1], [x0, b, y1]); q([x0, b, y1], [x1, b, y1], [x1, a, y1], [x0, a, y1]); q([x0, b, y0], [x1, b, y0], [x1, a, y0], [x0, a, y0]);
      q([x0, b, y0], [x0, b, y1], [x0, a, y1], [x0, a, y0]); q([x1, b, y0], [x1, b, y1], [x1, a, y1], [x1, a, y0]); return o;
    }
    function set(list) {
      tiles = list; n = list.length * 30; ver++; const d = new Float32Array(18 + n * 6); let o = 0;
      for (const i of [0, 1, 2, 0, 2, 3]) { d[o++] = [-1, 1, 1, -1][i]; d[o++] = [1, 1, -1, -1][i]; d[o++] = 0; }   // (the whole picture, for `back`)
      for (const g of [0, .5]) for (const [x, y, lo, hi, sky] of list) o = box(d, o, x, y, lo, hi, g, sky);
      gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, d, gl.DYNAMIC_DRAW);
    }
    function pass(m, ctr, bend, W, Hh) {
      gl.activeTexture(gl.TEXTURE4); gl.bindTexture(gl.TEXTURE_2D, tx); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      if (W !== w || Hh !== h) { w = W; h = Hh; gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null); for (const a of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, a, gl.NEAREST);
        gl.bindRenderbuffer(gl.RENDERBUFFER, rb); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w, h);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tx, 0); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb); }
      gl.viewport(0, 0, w, h); gl.disable(gl.BLEND); gl.disable(gl.STENCIL_TEST); gl.disable(gl.CULL_FACE); gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LESS); gl.depthMask(true); gl.colorMask(true, true, true, true);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.useProgram(mp); gl.uniformMatrix4fv(u(mp, "m"), false, m); gl.uniform3fv(u(mp, "ctr"), ctr); gl.uniform1f(u(mp, "bend"), bend); gl.bindVertexArray(vao);
      gl.colorMask(true, true, false, false); gl.drawArrays(gl.TRIANGLES, 6, n);                                      // the boxes as they are: the nearest of them a px
      gl.clear(gl.DEPTH_BUFFER_BIT); gl.colorMask(false, false, true, true); gl.drawArrays(gl.TRIANGLES, 6 + n, n);   // and a tile wider: the rim
      gl.colorMask(true, true, true, true); gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.activeTexture(gl.TEXTURE0);
    }
    // behind land that was left out and has nothing behind it (rock has no faces inside): the dark of the earth, as far as anything
    function back(rgb) { gl.useProgram(bp); gl.uniform1i(u(bp, "mk"), 4); gl.uniform3fv(u(bp, "bc"), rgb); gl.bindVertexArray(vao); gl.drawArrays(gl.TRIANGLES, 0, 6); }
    return {set, pass, back, get n() { return tiles.length; }, get ver() { return ver; }, get tiles() { return tiles; }};
  }
  return {create};
})();
