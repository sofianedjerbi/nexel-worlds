// VOX: marks. A block of the land (or an empty cell of it) shown as what it is, a box: `view.marks`, drawn by the
// engine over the land with the land's own depth, so what is nearer and higher hides it, and where the land is
// (vox_curve.js: bent with it). Whoever uses the engine says which cells (what a click would dig, where a piece
// would go); nothing here knows why.
//   a mark: {x, y: its tile (fractions: it glides), z0, z1: its foot and its top, levels (cfg.up px each; the
//            same: a flat square), colour: [r, g, b], a: how strong (0 to 1), grow: px its corners stand out more
//            (it breathes), fill: how much of its colour lies on its top (0 to 1; its front, half of that)}
// What is drawn of a box is what the eye sees of a block: its top and its south front, as one outline. In the
// look of a selector: a bracket at each of its four outer corners (the top's two far ones, the front's two feet)
// and a tick where the top meets the front, a dark px under each, a thin wash of the colour on the faces. All in
// whole px of paint.
const VoxMark = (() => {
  const VS = `#version 300 es
in vec3 aPos; in vec2 aOff; in vec4 aCol;
uniform vec2 uRes, uO; uniform float uK, uRow, uCell;
out vec4 vCol;
` + VoxCurve.GLSL + `
void main() {
  vec2 f = uO + aPos.xy * uK; float past;
  float y = floor(curveY(f.y, aPos.z * uK, past) / uK + .5) * uK;      // (on a whole px of paint)
  vec2 p = vec2(f.x, y) + aOff * uK;
  float near = (aPos.y + aPos.z) / uCell + uRow - (2. * past + past * past / (uCurve.x - uCurve.y + 1.)) / (uK * uCell) + .2;      // (a hair in front of its own block's faces)
  gl_Position = vec4(p.x / uRes.x * 2. - 1., 1. - p.y / uRes.y * 2., clamp(-near / 700., -1., 1.), 1.);
  vCol = aCol;
}`;
  const FS = `#version 300 es\nprecision highp float; in vec4 vCol; out vec4 o; void main() { o = vCol; }`;
  const ARM = 4, INK = [.235, .157, .118, .45];
  let prog = null, vao = null, buf = null, bad = false;
  // -> the corners of a mark's faces: x, y (px of paint in its tile), z (px up), then a shift on the screen (px of paint), then its colour
  function build(m, cfg) {
    const T = cfg.cell, top = m.z1 * cfg.up, foot = m.z0 * cfg.up, g = m.grow || 0, out = [], flat = top - foot < .5;
    const rect = (x, y, z, ox, oy, w, h, c) => { for (const [i, j] of [[0, 0], [1, 0], [0, 1], [1, 0], [1, 1], [0, 1]]) out.push(x, y, z, ox + i * w, oy + j * h, c[0], c[1], c[2], c[3]); };
    // a face's wash: the top in strips north to south (it bends with the ground), the front one piece
    const wash = [m.colour[0], m.colour[1], m.colour[2], m.a * (m.fill || 0)];
    if (wash[3] > 0) {
      for (let k = 0; k < 4; k++) for (const [i, j] of [[0, 0], [1, 0], [0, 1], [1, 0], [1, 1], [0, 1]]) out.push(i * T, (k + j) * T / 4, top, 0, 0, ...wash);
      if (!flat) for (const [i, j] of [[0, 0], [1, 0], [0, 1], [1, 0], [1, 1], [0, 1]]) out.push(i * T, T, j ? foot : top, 0, 0, wash[0], wash[1], wash[2], wash[3] * .5);
    }
    // the brackets: a px of ink under each, then the colour. (sx, sy: which way its arms go from its corner)
    for (const [c, dy] of [[[INK[0], INK[1], INK[2], INK[3] * m.a], 1], [[m.colour[0], m.colour[1], m.colour[2], m.a], 0]]) {
      for (const [x, y, z, sx, sy] of [[0, 0, top, 1, 1], [T, 0, top, -1, 1], [0, T, foot, 1, -1], [T, T, foot, -1, -1]]) {
        const ox = sx > 0 ? -1 - g : 1 + g, oy = (sy > 0 ? -1 - g : 1 + g) + dy;      // (a px outside the box, and its breath)
        rect(x, y, z, sx > 0 ? ox : ox - ARM, sy > 0 ? oy : oy - 1, ARM, 1, c);       // along the edge
        rect(x, y, z, sx > 0 ? ox : ox - 1, sy > 0 ? oy : oy - ARM, 1, ARM, c);       // down (or up) the side
      }
      if (!flat) for (const [x, sx] of [[0, 1], [T, -1]]) rect(x, T, top, sx > 0 ? -1 - g : g - 1, dy, 2, 1, c);      // where the top meets the front
    }
    return out;
  }
  // The marks of a view, over what is drawn (the engine calls it last): v as engine.draw takes it, k px of the picture a px of paint
  function draw(v, k, cfg) {
    const gl = VoxGL.gl;
    if (bad || !gl || !v.marks || !v.marks.length) return;
    if (!prog) {
      try { prog = VoxGL.program(VS, FS); } catch (e) { bad = true; console.error(e); return; }
      vao = gl.createVertexArray(); buf = gl.createBuffer(); gl.bindVertexArray(vao); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      for (const [name, size, off] of [["aPos", 3, 0], ["aOff", 2, 12], ["aCol", 4, 20]]) { const loc = prog.at(name); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 36, off); }
    }
    const u = prog.u, cu = v.curve;
    gl.useProgram(prog.pr); gl.bindVertexArray(vao); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(false); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.uniform2f(u.uRes, v.w, v.h); gl.uniform1f(u.uK, k); gl.uniform1f(u.uCell, cfg.cell);
    gl.uniform4f(u.uCurve, cu ? cu.y0 : 0, cu ? cu.yh : 0, cu ? cu.ref : 0, cu ? cu.lean : 0);
    for (const m of v.marks) {
      if (!(m.a > 0)) continue;
      const data = new Float32Array(build(m, cfg));
      gl.uniform2f(u.uO, v.ox + m.x * v.tile, v.oy + m.y * v.tile); gl.uniform1f(u.uRow, m.y - v.row);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW); gl.drawArrays(gl.TRIANGLES, 0, data.length / 9);
    }
    gl.depthMask(true); gl.disable(gl.BLEND);
  }
  return {draw, build};
})();
