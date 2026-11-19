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
//   west and east: such a wall leans as every wall of the land does: a bank a level (kind 3), on the cut tile, and
//     the bank's front (kind 4) where the wall or the hole ends south of it
// Water is left alone. A wall is made `DEEP` levels up from the cut at the most (more is never in one view).
const VoxSection = (() => {
  const DEEP = 64;
  // cut: {x, y, w, h, px} (vox_engine.js) -> {data, pages, n, tops, fronts, banks}: its corners, px from the cut's corner tile
  function build(host, cfg, strip, cut) {
    const T = cfg.cell, U = cfg.up, has = VoxMesh.has, list = [], out = {tops: 0, fronts: 0, banks: 0, shapes: new Set()};
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
    const lit = new Uint8Array(cut.w * cut.h), stands = (x, y) => { const c = col(x, y); return c ? Math.min(c[c.length - 1], lv(x, y)) : -1e9; };
    for (let j = 0; j < cut.h; j++) for (let i = -1, run = [], day = false; i <= cut.w + 1; i++) {
      const x = cut.x + i, y = cut.y + j, mine = i <= cut.w ? col(x, y) : null, north = mine && col(x, y - 1);
      if (north && stands(x, y - 1) > stands(x, y)) { run.push(i); day = day || stands(x, y - 1) > mine[mine.length - 1]; continue; }
      if (day && run.some((k) => k >= 0 && k < cut.w && lv(cut.x + k, cut.y + j) < 1e8)) lit.fill(1);      // (...and so every wall of that hole: its steps' fronts are as its back wall)
      run = []; day = false;
    }
    for (let j = 0; j < cut.h; j++) for (let i = 0; i < cut.w; i++) {
      const x = cut.x + i, y = cut.y + j, c = lv(x, y), mine = col(x, y), X = i * T, Y = j * T, dark = lit[j * cut.w + i] ? 0 : 8;
      if (c > 1e8 || !mine) continue;
      const top = mine[mine.length - 1];
      if (has(mine, c) && has(mine, c + 1)) {
        list.push([X, Y, c * U, T, T, 0, 0, T, (left(x, y - 1, c) ? 0 : 1) | (left(x - 1, y, c) ? 0 : 2) | (left(x + 1, y, c) ? 0 : 4) | (left(x, y + 1, c) ? 0 : 16), 5, strip(c), shape(x, y, c), 0, VoxMesh.pick(x, y, c, cfg.variants)]); out.tops++;      // (its block's shape there: a hill's edge is set in)
      }
      const north = col(x, y - 1);
      if (north) for (let z = c + 1, to = Math.min(north[north.length - 1], lv(x, y - 1), c + DEEP); z <= to; z++) if (has(north, z) && has(mine, z)) {
        list.push([X, Y, z * U, T, 0, 0, 0, U, dark | (z === c + 1 && has(mine, c) ? 16 : 0), 1, strip(z), 0, 0, VoxMesh.pick(x, y - 1, z, cfg.variants)]); out.fronts++;
      }
      for (const dx of [-1, 1]) {
        const wall = col(x + dx, y); if (!wall) continue;
        const to = Math.min(wall[wall.length - 1], lv(x + dx, y), c + DEEP);
        // (how far the wall's cell zc stands out: a band for each cell of it left over that one, as the land's walls;
        // a quarter of the tile at the most: a hole is narrow; an eighth where a wall stands on its other side too: a
        // way one tile wide, the floor is the main thing)
        const most = stands(x - dx, y) > c + 1 ? T / 8 : T / 4, reach = (zc) => { let o = 0; for (let n = 0; n < cfg.bands && zc + 1 + n <= to && has(wall, zc + 1 + n); n++) o += host.band(zc + n); return Math.min(o, most); };
        for (let zc = to - 1, edge = 0; zc > c; zc--) {
          if (!has(wall, zc) || !has(wall, zc + 1)) { edge = 0; continue; }
          if (!has(mine, zc) && top <= zc) { edge = 0; continue; }      // (open air beside it: the chunk's own bank is there)
          const o = reach(zc), w = o - edge, x0 = dx < 0 ? X + edge : X + T - o, bits = (dx < 0 ? 1 : 0) | 2 | dark;
          if (w > 0) { list.push([x0, Y, zc * U, w, T, 0, 0, T, bits, 3, strip(zc), 0, 0, 0]); out.banks++; }
          // (its front, where neither the hole's wall nor the land goes on south of it at that level)
          if (o > 0 && !left(x, y + 1, zc) && !(left(x + dx, y + 1, zc) && left(x + dx, y + 1, zc + 1))) list.push([dx < 0 ? X - cfg.inset : X + T - o, Y + T, zc * U, o + cfg.inset, 0, 0, 0, U, dark | (zc === c + 1 && shape(x + dx, y, zc) ? 16 : 0), 4, strip(zc), 0, 0, 0]);      // (cfg.inset px into the wall's tile: the land's own front leaves its side's px empty at a cave's mouth)
          edge = o;
        }
      }
    }
    return {...VoxMesh.pack([list]), ...out, lit};
  }
  return {build, DEEP};
})();
