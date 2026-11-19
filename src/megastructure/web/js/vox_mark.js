// VOX: marks. A block of the land (or an empty cell of it) shown as what it is, a box: `view.marks`, drawn by the
// engine over the land with the land's own depth, and where the land is (vox_curve.js: bent with it). Whoever uses
// the engine says which cells (what a click would dig, where a piece would go); nothing here knows why.
//   a mark: {x, y: its tile (fractions: it glides), z0, z1: its foot and its top, levels (cfg.up px each; the
//            same, or `flat`: its top alone, a tile's top), colour: [r, g, b], a: how strong (0 to 1), grow: px it stands out
//            more (it breathes), fill: how much of its colour lies on its top (0 to 1),
//            west, east: (if given) px of paint its side that way leans out at its foot (a bank in view: its edge;
//            step: px a level of it, 2 if not said),
//            drop: (if given) the level of the ground under a cell in the air: a dotted line down to it and a small
//            square on it}
// What is drawn of a box is what the eye sees of a block, so that it reads as one at a glance: the four edges of
// its top, a px wide; the two upright edges of its south front and the front's foot; its top washed with the
// colour and its front with a darker tone of it; a px of ink under each level line. A top alone (a tile of level
// ground: its front is behind the land before it): its four edges and a line of shade inside them, south and east.
// What nearer land hides is not left out: its edges are drawn through the land, dotted (a px on, a px off), so
// where you aim is always seen. All in whole px of paint.
const VoxMark = (() => {
  const VS = `#version 300 es
in vec3 aPos; in vec2 aOff; in vec4 aCol; in float aDot;
uniform vec2 uRes, uO, uAt; uniform float uK, uRow, uCell;
out vec4 vCol; out float vDot;
` + VoxCurve.VS + `
void main() {
  vec2 f = uO + (uAt + aPos.xy) * uK; float past;      // (uO: the land's own corner, so its px are the land's; uAt: the mark's tile, px of paint from there)
  float y = rollY(f.y, aPos.z * uK, past);      // (on a whole px of paint, as the land)
  vec2 p = vec2(f.x, y) + aOff * uK;
  float near = (aPos.y + aPos.z) / uCell + uRow - (2. * past + past * past / (uCurve.x - uCurve.y + 1.)) / (uK * uCell) + .2;      // (a hair in front of its own block's faces)
  gl_Position = vec4(p.x / uRes.x * 2. - 1., 1. - p.y / uRes.y * 2., clamp(-near / 700., -1., 1.), 1.);
  vCol = aCol; vDot = aDot;
}`;
  // (vDot: -1 a wash, 0 an edge, 1 an edge that is dotted wherever it is; uHid: this is what the land hides: no
  // wash, every edge dotted and fainter. A dot: a px of paint in two, counted on the land's own px)
  const FS = `#version 300 es
precision highp float; in vec4 vCol; in float vDot; uniform vec2 uRes, uO; uniform float uK, uPx, uHid; out vec4 o;
void main() {
  if (uHid > .5 && vDot < -.5) discard;
  if (uHid > .5 || vDot > .5) { vec2 a = floor((vec2(gl_FragCoord.x, uRes.y * uPx - gl_FragCoord.y) / uPx - uO) / uK); if (mod(a.x + a.y, 2.) < 1.) discard; }
  o = vec4(vCol.rgb, vCol.a * (uHid > .5 ? .85 : 1.));
}`;
  const INK = [.235, .157, .118], SIX = [[0, 0], [1, 0], [0, 1], [1, 0], [1, 1], [0, 1]], N = 10;
  let prog = null, vao = null, buf = null, bad = false;
  // -> the corners of a mark's faces: x, y (px of paint in its tile), z (px up), then a shift on the screen (px of paint), its colour, is it dotted
  function build(m, cfg) {
    const T = cfg.cell, top = m.z1 * cfg.up, foot = m.z0 * cfg.up + (m.lift || 0), g = -(m.grow || 0), out = [], flat = !!m.flat || top - foot < .5, [r, gr, b] = m.colour;
    // a piece between two points of the land a and b ([x, y, z]), from the shift (ox, oy) at a to (ox, oy + oh) at b, w px across
    const piece = (a, b2, ox, oy, w, oh, c, dot = 0) => { for (const [i, j] of SIX) { const q = j ? b2 : a; out.push(q[0], q[1], q[2], ox + i * w, oy + j * oh, c[0], c[1], c[2], c[3], dot); } };
    const rect = (q, ox, oy, w, h, c, dot = 0) => piece(q, q, ox, oy, w, h, c, dot);
    // a face's wash: the top in strips north to south (it bends with the ground), the front one piece, darker
    const wa = m.a * (m.fill || 0);
    if (wa > 0) {
      for (let k = 0; k < 4; k++) piece([0, k * T / 4, top], [0, (k + 1) * T / 4, top], 0, 0, T, 0, [r, gr, b, wa], -1);
      if (!flat) piece([0, T, top], [0, T, foot], 0, 0, T, 0, [r * .55, gr * .55, b * .55, Math.min(1, wa * 1.6)], -1);
    }
    const ink = [INK[0], INK[1], INK[2], .45 * m.a], col = [r, gr, b, m.a], dim = [r * .9, gr * .9, b * .9, m.a], nw = [0, 0, top], sw = [0, T, top], fw = [0, T, foot];
    // a level line (west to east) at a point, and an upright or lengthwise one between two, each a px
    const level = (q, oy, c, dot) => rect(q, -g, oy, T + 2 * g, 1, c, dot), edge = (a, b2, ox, c, o0 = -g, o1 = g, dot = 0) => piece(a, b2, ox, o0, 1, o1 - o0, c, dot);
    // (every line is in the box: its tile across, from its top's far edge to its foot. A px out as it breathed and the ink under its foot were an overhang and a double line on a block's edge)
    if (m.tick !== undefined) rect([T / 2 - 2, T, m.tick * cfg.up - cfg.up / 2], 0, 0, 4, 1, [r, gr, b, m.a * .8]);      // (the place on a wall's face that is pointed at, where the box is the cell over it: a dash)
    if (flat) { level(sw, -3, [INK[0], INK[1], INK[2], .3 * m.a]); edge([T, 0, top], [T, T, top], -2, [INK[0], INK[1], INK[2], .3 * m.a], 1, -3); }      // (a top alone: shade inside it, south and east)
    level(nw, -g + 1, ink); level(flat ? sw : fw, g - 1, ink);                                   // ink under the far edge and under the foot
    level(nw, -g, col); level(sw, flat ? g - 2 : g - 1, flat ? col : dim);                       // the top: its far edge, its near one (where it meets the front)
    edge(nw, sw, -g, col); edge([T, 0, top], [T, T, top], g - 1, col);                           // ...its west and its east
    if (!flat) { edge(sw, fw, -g, dim, g, g); edge([T, T, top], [T, T, foot], g - 1, dim, g, g); level(fw, g - 2, dim); }      // the front: its two uprights, its foot
    // a side in view (a bank beside the wall, a step of `m.step` px a level down to `west` or `east` px at its foot): its
    // edge, stepped as the bank is, at the block's far end and at its near one, and the line of its foot on the land beside it
    for (const [w, x, sg] of [[m.west, 0, -1], [m.east, T, 1]]) if (w > 0 && !flat) {
      const at = (j) => (sg < 0 ? -Math.min(w, (m.step || 2) * j) - g : Math.min(w, (m.step || 2) * j) - 1 + g), n = Math.ceil((top - foot) / cfg.up);
      for (const y of [0, T]) for (let j = 1; j <= n; j++) edge([x, y, top - (j - 1) * cfg.up], [x, y, Math.max(foot, top - j * cfg.up)], at(j), dim, y ? g : -g, y ? g : -g);
      edge([x, 0, foot], [x, T, foot], at(n), dim);
    }
    // a cell in the air: a dotted line down from the middle of its foot to the ground under it, and a small square there
    if (m.drop !== undefined && m.drop < m.z0) {
      const d = m.drop * cfg.up, c = [r, gr, b, m.a * .9], h = 0;      // (a thin whole line, and the cell's whole footprint on the ground: a dotted line to a small square read as a block floating at the horizon)
      piece([T / 2, T, foot], [T / 2, T, d], 0, g + 1, 1, -g - 1, c, 0);
      rect([h, h, d], 0, 0, T - 2 * h, 1, c); rect([h, T - h, d], 0, -1, T - 2 * h, 1, c); edge([h, h, d], [h, T - h, d], 0, c, 0, 0); edge([T - h, h, d], [T - h, T - h, d], -1, c, 0, 0);
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
      for (const [name, size, off] of [["aPos", 3, 0], ["aOff", 2, 12], ["aCol", 4, 20], ["aDot", 1, 36]]) { const loc = prog.at(name); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, N * 4, off); }
    }
    const u = prog.u, cu = v.curve;
    gl.useProgram(prog.pr); gl.bindVertexArray(vao); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(false); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.uniform2f(u.uRes, v.w, v.h); gl.uniform1f(u.uK, k); gl.uniform1f(u.uCell, cfg.cell); gl.uniform1f(u.uPx, v.pw / v.w);
    gl.uniform4f(u.uCurve, cu ? cu.y0 : 0, cu ? cu.yh : 0, cu ? cu.ref : 0, cu ? cu.lean : 0); gl.uniform1f(u.uFloor, cu ? cu.floor || 0 : 0);
    for (const m of v.marks) {
      if (!(m.a > 0)) continue;
      const data = new Float32Array(build(m, cfg));
      gl.uniform2f(u.uO, v.ox, v.oy); gl.uniform2f(u.uAt, m.x * cfg.cell, m.y * cfg.cell); gl.uniform1f(u.uRow, m.y - v.row);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
      gl.depthFunc(gl.LEQUAL); gl.uniform1f(u.uHid, 0); gl.drawArrays(gl.TRIANGLES, 0, data.length / N);      // what is in view
      gl.depthFunc(gl.GREATER); gl.uniform1f(u.uHid, 1); gl.drawArrays(gl.TRIANGLES, 0, data.length / N);     // what the land hides: dotted, through it
    }
    gl.depthFunc(gl.LEQUAL); gl.depthMask(true); gl.disable(gl.BLEND);
  }
  return {draw, build};
})();
