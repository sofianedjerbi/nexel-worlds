// VOX: the land cut open is a section through blocks (view.cut, vox_engine.js: a level a tile, nothing of the tile
// higher than that is drawn). A chunk's faces (vox_mesh.js) are the ones between a solid cell and an empty one; a cut
// goes through solid cells, and what a knife would leave there has no face of the chunk's: this file makes them, a
// small mesh for the tiles of the cut, made again when the cut changes. As the land is drawn: the same corners, the
// same program, one depth.
//   the sliced top: a tile cut at a level where its column is solid and was solid over it: a top at that level,
//     kind 5, the earth of that level as its fronts have it, in its block's shape, with a line (bits: 1 north, 2 west, 4 east, 16 south) along each side where what is
//     left of the tile beside it is lower: a drop
//   the walls of the hole: the tile north of a cut one is solid over the cut and still stands there (to its own top,
//     or its own cut), and the cut tile was solid there too (no face of the chunk's): its south face, a front a
//     level, the host's own paint of that level (kind 1, the whole square; bit 8: in a cave's dark), its foot's line
//     on the lowest (bit 16)
//   west and east: such a wall shows its thin side as every wall of the land does (vox_mesh.js): a strip (kind 3) on
//     the cut tile, and its front (kind 4) where the wall or the hole ends south of it
// Water is left alone. A wall is made `DEEP` levels up from the cut at the most (more is never in one view).
const VoxSection = (() => {
  const DEEP = 64;
  // cut: {x, y, w, h, px} (vox_engine.js) -> {data, pages, n, tops, fronts, banks}: its corners, px from the cut's corner tile
  function build(host, cfg, strip, cut) {
    const T = cfg.cell, U = cfg.up, has = VoxMesh.has, list = [], out = {tops: 0, fronts: 0, banks: 0, shapes: new Set()};
    const strip0 = strip; strip = (z, c) => strip0(VoxMesh.rock(cfg, VoxMesh.topOf(c, z), z));      // (a cell's strip: by its block's top, as the land's faces have it: vox_mesh.js)
    const shape = (x, y, z) => { const id = host.shape(x, y, z); out.shapes.add(id); return id; };
    const W = cut.w + 2, cols = new Array(W * (cut.h + 2)), col = (x, y) => { const k = (y - cut.y + 1) * W + x - cut.x + 1; let c = cols[k]; if (c === undefined) cols[k] = c = host.water(x, y) ? null : host.column(x, y); return c; };      // (the cut's tiles and the ring round them)
    // the level a tile is cut down to (1e9: it is not), and is its cell z still there
    const lv = (x, y) => { const i = x - cut.x, j = y - cut.y; if (i < 0 || j < 0 || i >= cut.w || j >= cut.h) return 1e9; const o = (j * cut.w + i) * 4; return cut.px[o + 2] ? cut.px[o] + cut.px[o + 1] * 256 - 32768 : 1e9; };
    const left = (x, y, z) => { const c = col(x, y); return !!c && z <= lv(x, y) && has(c, z); };
    // One wall, one light. Along the north side of a row of tiles the faces that are seen side by side are one wall
    // (a cut tile's: the tile north of it stands over the cut; another's: it stands over that tile's own top, a
    // front of the land's, out of doors). Where such a wall has a part out of doors, all of it takes the day's
    // light (lit: a cut tile whose north wall does; the engine tells the land's own fronts there); a hole with no
    // wall out of doors keeps the cave's dark (bit 8)
    // (a tile down a hole one tile wide, in the ground: walls right beside it north and south, or west and east: its walls are in the hole's own dark, vox_mesh.js)
    const up2 = (x, y, z) => { const c = col(x, y); return !!c && has(c, z + 2); }, shaft = (x, y, z) => z < cfg.dug && ((up2(x, y - 1, z) && up2(x, y + 1, z)) || (up2(x - 1, y, z) && up2(x + 1, y, z)));
    const lit = new Uint8Array(cut.w * cut.h), room = new Uint8Array(cut.w * cut.h), stands = (x, y) => { const c = col(x, y); return c ? Math.min(c[c.length - 1], lv(x, y)) : -1e9; };
    for (let j = 0; j < cut.h; j++) for (let i = -1, run = [], day = false; i <= cut.w + 1; i++) {
      const x = cut.x + i, y = cut.y + j, mine = i <= cut.w ? col(x, y) : null, north = mine && col(x, y - 1);
      if (north && stands(x, y - 1) > stands(x, y)) { run.push(i); day = day || (stands(x, y - 1) > mine[mine.length - 1] && !shaft(x, y, mine[mine.length - 1])); continue; }
      if (day && run.some((k) => k >= 0 && k < cut.w && lv(cut.x + k, cut.y + j) < 1e8)) lit.fill(1);      // (...and so every wall of that hole: its steps' fronts are as its back wall)
      run = []; day = false;
    }
    // (a cut tile with a room over its floor, its roof lifted off: how high that room is. A cut with none is out of doors, all of it)
    for (let j = 0, any = false; j < cut.h; j++) for (let i = 0; i < cut.w; i++) {
      const c = lv(cut.x + i, cut.y + j), mine = c < 1e8 ? col(cut.x + i, cut.y + j) : null, q = mine ? mine.indexOf(c) : -1;
      if (q >= 0 && q % 2 === 0 && q + 1 < mine.length) { room[j * cut.w + i] = Math.min(100, mine[q + 1] - c); any = true; }
      if (j === cut.h - 1 && i === cut.w - 1 && !any) lit.fill(1);
    }
    for (let j = 0; j < cut.h; j++) for (let i = 0; i < cut.w; i++) {
      const x = cut.x + i, y = cut.y + j, c = lv(x, y), mine = col(x, y), X = i * T, Y = j * T, dark = lit[j * cut.w + i] ? 0 : 8;
      if (c > 1e8 || !mine) continue;
      const top = mine[mine.length - 1];
      if (has(mine, c) && has(mine, c + 1)) {
        list.push([X, Y, c * U, T, T, 0, 0, T, (left(x, y - 1, c) ? 0 : 1) | (left(x - 1, y, c) ? 0 : 2) | (left(x + 1, y, c) ? 0 : 4) | (left(x, y + 1, c) ? 0 : 16), 5, strip(c, mine), shape(x, y, c), 0, VoxMesh.pick(x, y, c, cfg.variants)]); out.tops++;      // (its block's shape there: a hill's edge is set in)
      }
      const north = col(x, y - 1);
      if (north) for (let z = c + 1, to = Math.min(north[north.length - 1], lv(x, y - 1), c + DEEP); z <= to; z++) if (has(north, z) && has(mine, z)) {
        list.push([X, Y, z * U, T, 0, 0, 0, U, dark | (z === c + 1 && has(mine, c) ? 16 : 0), 1, strip(z, north), 0, 0, VoxMesh.pick(x, y - 1, z, cfg.variants)]); out.fronts++;
      }
      for (const dx of [-1, 1]) {
        const wall = col(x + dx, y); if (!wall) continue;
        const to = Math.min(wall[wall.length - 1], lv(x + dx, y), c + DEEP);
        // (its side, as the land's walls have it, vox_mesh.js: cfg.side px on the cut tile, the outer px its dark line (bit 4):
        // a strip at the height of the wall's highest cell there, a front a level where neither the hole's wall nor the land goes on south)
        const S = cfg.side, cell = (zc) => zc <= to && has(wall, zc) && (has(mine, zc) || top > zc);      // (open air beside it: the chunk's own side is there)
        for (let zc = to; zc > c; zc--) {
          if (!cell(zc)) continue;
          for (const [a, w, b4] of [[dx < 0 ? S - 1 : 0, 1, 4], [dx < 0 ? 0 : 1, S - 1, 0]]) {
            if (w > 0 && !cell(zc + 1)) { list.push([(dx < 0 ? X : X + T - S) + a, Y, zc * U, w, T, 0, 0, T, (dx < 0 ? 1 : 0) | 2 | dark | b4, 3, strip(zc, wall), 0, 0, 0]); out.banks += b4 ? 1 : 0; }
            // (cfg.inset px into the wall's tile: the land's own front leaves its side's px empty at a cave's mouth)
            if (w > 0 && !left(x, y + 1, zc) && !left(x + dx, y + 1, zc)) list.push([b4 ? (dx < 0 ? X + S - 1 : X + T - S) : dx < 0 ? X - cfg.inset : X + T - S + 1, Y + T, zc * U, b4 ? 1 : S - 1 + cfg.inset, 0, 0, 0, U, dark | (zc === c + 1 && shape(x + dx, y, zc) ? 16 : 0) | (dx < 0 ? 32 : 0) | b4, 4, strip(zc, wall), 0, 0, 0]);
          }
        }
      }
    }
    return {...VoxMesh.pack([list]), ...out, lit, room};
  }
  // The engine's part of it (vox_engine.js draw). The cut's picture as the GPU takes it: its fourth byte says of a cut
  // tile: 128, its north wall is in the day's light; and how high its room is over its floor (levels; 0: none)
  function hand(gl, open, sec, tex) {
    gl.activeTexture(gl.TEXTURE5); tex = tex || gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
    const px = open.px.slice(); sec.lit.forEach((v, i) => { px[i * 4 + 3] = (v ? 128 : 0) + sec.room[i]; });
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, open.w, open.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, px);
    for (const [k, val] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, val);
    return tex;
  }
  // The faces of the cut, after the land's; a sliced top wins over a top of the land at its own height. at(): the light's place for them
  function draw(gl, u, v, open, sec, at) {
    gl.uniform2f(u.uO, v.ox + open.x * v.tile, v.oy + open.y * v.tile); gl.uniform1f(u.uRow, open.y - v.row); gl.uniform2f(u.uChunk, 0, 0); at();
    gl.uniform1f(u.uSec, 1);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(-1, -2); gl.bindVertexArray(sec.vao);
    for (const [, first, count] of sec.ranges) gl.drawArrays(gl.TRIANGLES, first, count);
    gl.disable(gl.POLYGON_OFFSET_FILL); gl.uniform1f(u.uSec, 0);
  }
  // The colour `earth` on the px where land was left out and nothing at all is behind: all(): draws the land; fill: the program of one colour
  let quad = null;
  function fill(gl, u, v, earth, all, prog) {
    gl.enable(gl.STENCIL_TEST); gl.stencilMask(255); gl.clearStencil(0); gl.clear(gl.STENCIL_BUFFER_BIT);
    gl.stencilFunc(gl.ALWAYS, 1, 255); gl.stencilOp(gl.KEEP, gl.KEEP, gl.REPLACE); gl.colorMask(false, false, false, false); gl.depthMask(false); gl.disable(gl.DEPTH_TEST);
    gl.uniform1f(u.uCut, 1); all();
    gl.colorMask(true, true, true, true); gl.enable(gl.DEPTH_TEST); gl.stencilFunc(gl.EQUAL, 1, 255); gl.stencilOp(gl.KEEP, gl.KEEP, gl.KEEP);
    if (!quad) { quad = {vao: gl.createVertexArray(), buf: gl.createBuffer()}; gl.bindVertexArray(quad.vao); gl.bindBuffer(gl.ARRAY_BUFFER, quad.buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, -1, 1, 1, -1, 1]), gl.STATIC_DRAW); gl.enableVertexAttribArray(prog.at("p")); gl.vertexAttribPointer(prog.at("p"), 2, gl.FLOAT, false, 0, 0); }
    gl.useProgram(prog.pr); gl.uniform3f(prog.u.uCol, earth[0] * v.light[0], earth[1] * v.light[1], earth[2] * v.light[2]);
    // (with a horizon, only under the line where level ground meets the sky: over it, where a cut leaves nothing, the sky is what is behind: over the top of a cave's far wall that stands at the horizon)
    if (v.curve) { const dh = gl.drawingBufferHeight; gl.enable(gl.SCISSOR_TEST); gl.scissor(0, 0, gl.drawingBufferWidth, Math.max(0, Math.round(dh - v.curve.line * dh / v.h))); }
    gl.bindVertexArray(quad.vao); gl.drawArrays(gl.TRIANGLES, 0, 6); gl.disable(gl.SCISSOR_TEST);
    gl.depthMask(true); gl.disable(gl.STENCIL_TEST);
  }
  return {build, hand, draw, fill, DEEP};
})();
