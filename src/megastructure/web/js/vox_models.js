// VOX: models. What is not a block of the land but stands in it as a solid thing: a bridge's deck and posts, and
// whatever else the host says. A model is a few boxes (low-poly: a deck is a box a plank, a post is one box), each
// with a top and a south front, the two faces of a box the eye sees (it looks north from above: an east, west or
// north face is never in view). They are drawn with the land's own program into the same depth buffer, so land
// hides a model and a model hides land as their places say, and the window (view.window) opens them alike.
//
//   host.models(x, y) -> null, or the boxes that belong to tile (x, y): [{x, y, z, w, d, h, top, front}...]
//       x, y: the box's north-west corner, px of paint from the tile's (it may reach out of its tile)
//       z: its foot, px up from height 0 (cfg.up px a level); w, d, h: px east, south and up (h 0: a flat thing)
//       top, front: the paint of the face, [u, v]: where its first px is in the sheet; the face takes w x d px
//           (a top) or w x h px (a front: its top row first) from there, a px of the sheet a px of paint, never
//           scaled. [u, v, 1]: that one px all over it (a flat colour). Left out: the face is not made.
//           A see-through px of the sheet is a hole in the face. A half see-through one is laid over the water's
//           picture (a shadow on the water: only for faces that lie on water).
//   host.modelSheet() -> the sheet: a canvas, or {px, w, h} (a Uint32 a px). Asked for once, when first drawn.
//
// The boxes of a chunk's tiles are one buffer of the chunk, made again with its faces (engine.touch). Boxes must
// not run into each other or into the land: the depth is a point's own (south and up are in front), right for
// things that are apart.
// A corner is 14 bytes: x, y, z (px in the chunk, shorts), where it is in the sheet (half px, shorts), then as the
// land's corners: bits (none), kind (7), nothing.
const VoxModels = (() => {
  const BYTES = 14, STRIPS = 4;                                // (a top is that many pieces north to south, so that it bends with the ground: vox_curve.js)
  // -> {data, n}: the faces of the boxes of a chunk's tiles
  function build(ch, host, cfg) {
    const N = cfg.size, T = cfg.cell, faces = [];
    if (host.models) for (let ly = 0; ly < N; ly++) for (let lx = 0; lx < N; lx++) {
      const list = host.models(ch.cx * N + lx, ch.cy * N + ly);
      if (!list) continue;
      for (const b of list) {
        const X = lx * T + b.x, Y = ly * T + b.y;
        if (b.top) faces.push([X, Y, b.z + b.h, b.w, b.d, 0, b.top]);
        if (b.front && b.h > 0) faces.push([X, Y + b.d, b.z + b.h, b.w, b.h, 1, b.front]);
      }
    }
    const quads = faces.reduce((s, f) => s + (f[5] ? 1 : STRIPS), 0), data = new ArrayBuffer(quads * 6 * BYTES), view = new DataView(data);
    let at = 0;
    for (const [X, Y, Z, w, t, front, [u, v, flat]] of faces) {
      // a top lies flat (its far edge, then its near one); a front hangs from its top edge
      const corner = (dx, q) => {                               // (q: px along it from its far edge, or down from its top)
        view.setInt16(at, X + dx * w, true); view.setInt16(at + 2, front ? Y : Y + q, true); view.setInt16(at + 4, front ? Z - q : Z, true);
        view.setInt16(at + 6, flat ? u * 2 + 1 : (u + dx * w) * 2, true); view.setInt16(at + 8, flat ? v * 2 + 1 : (v + q) * 2, true);
        view.setUint8(at + 10, 0); view.setUint8(at + 11, 7); view.setUint8(at + 12, 0);
        at += BYTES;
      };
      for (let k = 0, m = front ? 1 : STRIPS; k < m; k++) { const a = Math.round(t * k / m), b = Math.round(t * (k + 1) / m); corner(0, a); corner(1, a); corner(0, b); corner(1, a); corner(1, b); corner(0, b); }
    }
    return {data, n: faces.length, quads};
  }
  // A chunk's models made again and handed to the GPU (a buffer of their own: none where a chunk has no model)
  function make(ch, host, cfg, prog) {
    const gl = VoxGL.gl, mesh = build(ch, host, cfg);
    let m = ch.models;
    if (!mesh.n) { if (m) m.n = 0; return; }
    if (!m) {
      m = ch.models = {vao: gl.createVertexArray(), buf: gl.createBuffer(), n: 0};
      gl.bindVertexArray(m.vao); gl.bindBuffer(gl.ARRAY_BUFFER, m.buf);
      for (const [name, size, type, off] of [["aPos", 3, gl.SHORT, 0], ["aLoc", 2, gl.SHORT, 6], ["aMeta", 3, gl.UNSIGNED_BYTE, 10]]) {
        const loc = prog.at(name); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, type, false, BYTES, off);
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, m.buf); gl.bufferData(gl.ARRAY_BUFFER, mesh.data, gl.STATIC_DRAW);
    m.n = mesh.n; m.quads = mesh.quads;
  }
  // Before a frame's chunks: the sheet, on the fourth texture unit (`keep`: where the engine keeps it)
  function bind(host, keep, u) {
    const gl = VoxGL.gl;
    if (!host.modelSheet) return;
    if (!keep.sheet) { const s = host.modelSheet(); keep.sheet = {tex: (gl.activeTexture(gl.TEXTURE6), VoxGL.texture(s)), w: s.w || s.width, h: s.h || s.height}; }
    gl.activeTexture(gl.TEXTURE6); gl.bindTexture(gl.TEXTURE_2D, keep.sheet.tex);      // (unit 6: the land has 0 to 5)
    gl.uniform1i(u.uModel, 6); gl.uniform2f(u.uModelSize, keep.sheet.w, keep.sheet.h);
    gl.activeTexture(gl.TEXTURE0);
  }
  // A chunk's models drawn (its place is set: the land's faces were just drawn). A hair nearer than their place:
  // a flat thing lying on the water or on a top is over it, whichever chunk is drawn first.
  function draw(ch) {
    const gl = VoxGL.gl, m = ch.models;
    if (!m || !m.n) return;
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(-1, -2);
    gl.bindVertexArray(m.vao); gl.drawArrays(gl.TRIANGLES, 0, m.quads * 6);
    gl.disable(gl.POLYGON_OFFSET_FILL);
  }
  function drop(ch) { const gl = VoxGL.gl, m = ch.models; if (gl && m) { gl.deleteVertexArray(m.vao); gl.deleteBuffer(m.buf); } ch.models = null; }
  const count = (ch) => (ch.models ? ch.models.n : 0);
  return {build, make, bind, draw, drop, count};
})();
