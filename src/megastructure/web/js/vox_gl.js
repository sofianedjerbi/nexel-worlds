// VOX, a small engine that draws a world of cells as blocks: the four files js/vox_*.js (gl, pages, mesh, engine).
// It is a layer of its own, as a library is: it knows nothing of the game, and no global of the game is named in
// these files (tests/test_vox_layer.py holds them to it; they are side by side with the game's files only
// because the server hands out no folder under js/). Whoever uses it hands it the world as columns of cells and the paint of their faces, and tells it
// each frame where the world is on the screen (vox_engine.js says how; the game's side of it is js/voxels.js).
//
// This file: the canvas the GPU draws on and the few things every part needs of WebGL 2. One context, made the
// first time it is asked for. If the machine has none, or loses it, `ok` says no.
const VoxGL = (() => {
  let el = null, gl = null, bad = false;
  function start() {
    if (gl || bad) return gl;
    el = document.createElement("canvas");
    try { gl = el.getContext("webgl2", {alpha: false, antialias: false, depth: true, stencil: true}); } catch (e) { gl = null; }
    if (!gl) { bad = true; el = null; return null; }
    el.addEventListener("webglcontextlost", (e) => { e.preventDefault(); bad = true; gl = null; });
    return gl;
  }
  // A program: its uniforms by name, its attributes' places
  function program(vs, fs) {
    const pr = gl.createProgram();
    for (const [type, text] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
      const s = gl.createShader(type); gl.shaderSource(s, text); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      gl.attachShader(pr, s);
    }
    gl.linkProgram(pr);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
    const u = {};
    for (let i = 0; i < gl.getProgramParameter(pr, gl.ACTIVE_UNIFORMS); i++) { const n = gl.getActiveUniform(pr, i).name; u[n] = gl.getUniformLocation(pr, n); }
    return {pr, u, at: (n) => gl.getAttribLocation(pr, n)};
  }
  // A picture for the GPU, never smoothed (a px of it is a px of the art). src: a canvas or an image, or
  // {px, w, h} (a Uint32 a px, red in its low byte). Given a texture, that one is filled again.
  function texture(src, t = null) {
    t = t || gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    if (src.px) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, src.w, src.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(src.px.buffer, src.px.byteOffset, src.w * src.h * 4));
    else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
    for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    return t;
  }
  function fit(w, h) { if (el && (el.width !== w || el.height !== h)) { el.width = w; el.height = h; } }      // the canvas, that many px
  return {start, program, texture, fit, get gl() { return gl; }, get el() { return el; }, get ok() { return !bad; }};
})();
