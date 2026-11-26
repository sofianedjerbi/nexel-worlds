// The paint of a block's sides (the land as blocks: voxels.js hands these to the engine), all of it read off the
// level's own hill sheet (colsOf, relief.js: its wall's colours, its side's).
//   shape: a top has the shape of its sheet's cell for the sides where the land is lower (the rounded corners and
//     set-in edges of the pack; under sea level it is cut square).
//   rim: a top's lip: that cell of the sheet laid over the plain top. Outside its shape the px is left
//     see-through (what is behind shows, as round the pack's own hills); under its last px, down to the tile's
//     end, is the wall the front goes on with: lit along its top, then its body.
//   front: a south face, a level: the wall's body, a seam along its foot that swells a px here and there as the
//     sheet's scallops do, a few flecks; four variants a level.
//   One rock a wall: the pack has a wall for each of its three sheets (grass, levels 1-2: orange earth; dark grass,
//     3-4: grey-brown earth; stone, 5 and up). A wall four levels high was grey-brown over orange, two palettes down one face.
//     Earth is one rock here: every wall of levels 1 to 4 has the first sheet's wall (EARTH), and the px of wall in
//     the second sheet's caps (their lip, their sides) are painted in it too.
//   One tone a rock: a level's sheet is a touch brighter than the one under it (tiles.js hillSheet: terraces read as
//     steps), and that is for tops. A wall has its rock's one tone at every level (earth: EARTH's; stone: STONE's), its
//     lip in the top's paint too: on a cliff that runs on a slant each column is drawn two levels lower than the one
//     beside it, and a tone a level made it a grid of grey squares ("this wall look so weird"). And one rock from rim
//     to foot: a block whose top is stone is stone down to the ground (voxels.js cfg.rock: the engine picks a cell's
//     strip by its block's top), so stone never meets earth in a staircase along such a cliff.
const VoxPaint = (() => {
  const rgb = (c) => (255 << 24 | (c[2] | 0) << 16 | (c[1] | 0) << 8 | (c[0] | 0)) >>> 0;
  const EARTH = 2, STONE = "rock", wallOf = (z) => (z > 4 ? STONE : EARTH), bands = (z) => colsOf(hillSheet(wallOf(z))).bands, sheetOf = (z) => hillSheet(Math.max(1, z));
  // the px of wall (browns: more red than green) of a sheet whose wall is not EARTH's -> EARTH's, lightest to darkest
  const browns = (sheet) => { const d = sheetData(sheet), [cx, cy] = blobCell(N_ | E_ | W_ | NE | NW), set = new Set(); for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) { const v = d.px[(cy * 16 + j) * d.w + cx * 16 + i]; if (v >>> 24 === 255 && (v & 255) > (v >>> 8 & 255)) set.add(v); }
    return [...set].sort((a, b) => (a & 255) - (b & 255)); };
  const earths = new Map(), earth = (z) => { if (!(z > EARTH && z < 5)) return null; let m = earths.get(z); if (!m) { const to = browns(hillSheet(EARTH)); m = new Map(browns(hillSheet(z)).map((v, i) => [v, to[Math.min(i, to.length - 1)]])); earths.set(z, m); } return m; };
  // STONE OR EARTH IS THE CELL'S, AND THE WORLD SAYS IT (stoneAt: chunks.py keeps it, from when its land was laid out): a high hill stone at any height (2), lower land
  // earth on top and stone under, whatever is dug of it: a trench cut in a stone hill has stone walls and a stone floor, a hole in a meadow comes to stone. A block put
  // on its top is what was put (matAt). Nothing is guessed here.
  // (Not guessed from the heights: a mass of tiles 5 high or more, a low tile "cut in stone" by the stone round it, the column's own top: a cut would turn the tiles beside it
  // to earth, lighter boxes along it, and its own floor to a brown face in a grey hill.)
  // rocky: is the tile's cell at z stone (no z: its top); level: the level whose paint the block with its top at z has there (4: the highest earth). The engine: host.rock, voxels.js
  const rocky = (x, y, z) => { const top = topAt(x, y), m = matAt(x, y); if (z === undefined) z = top; return m && z >= top ? (m === "s" ? 2 : false) : z <= stoneAt(x, y) ? 2 : false; };
  const level = (x, y, z) => (z < 5 && rocky(x, y, z) === 2 ? 5 : z > 4 && !rocky(x, y, z) ? 4 : z);   // (stone under 5, a cut's floor in a stone hill: stone's lowest level, its darkest top, at any depth. Not 5 to 8 by its height: a floor a level down would be three tones lighter than the one over it)
  const ids = new Map(), cells = [null];                        // a shape: [what of it is drawn, its sheet, the sheet's cell (cx, cy) each quarter of it is: NW, NE, SW, SE]; 0: the whole square
  // A narrow top (a tile in no 2 x 2 of land as high: a pillar, a wall one tile wide, its ends, an L, a T, a plus, a ring): the
  // sheet's own cell for it is all rim (a pillar's top was a button, a ridge a hedge, a plus a muddle: the sheet's rim is 7 px a
  // side, a tile has 16). It is made of the sheet's straight edge cells instead, a quarter each, and the rim is slimmed: of
  // the edge cell's px from the outside in only SLIM are kept (west: the empty px, two of the wall, the dark green, one of the
  // mid green; north: the sheet's own four rows, its line that dips as on a wide top; then its flat middle), so a run one tile
  // wide is ONE top, 6 px of flat green across from end to end. A quarter: 'a' land goes on to its side (west or east): its north
  // or south edge; 'b' land goes on north or south: its side's edge; 'o' neither: an end's corner, the two edges mitred, the
  // corner's own px left out ('q': not left out: a step of a stair, flat-fronted); 'c' both: a joint's inner corner, each arm's
  // rim turning into the other's along the mitre. Else (a wide top) the sheet's cell, four times
  const QUARTER = [[N_, W_, NW, NE, SW], [N_, E_, NE, NW, SE], [S_, W_, SW, SE, NW], [S_, E_, SE, SW, NE]];      // (its two sides, its corner, then the corner past each side)
  const SLIM = {x: [0, 1, 3, 4, 5, 8, 8, 8], n: [0, 1, 2, 3, 6, 6, 6, 6], s: [6, 9, 10, 11, 12, 13, 14, 15], q: [6, 6, 6, 6, 9, 10, 14, 15]};      // (west: the px of the edge cell that px 0..7 is; north; south, px 8..15; q: a step's south: its tread goes on to two px of its edge, with none of the sheet's lip of wall: the riser under it is its wall)
  function quarters(m, step) {
    const r = reduce(m & 255), one = blobCell(r);
    if (r & 240) return [one, one, one, one];
    const q = QUARTER.map(([a, b, ab, pa, pb]) => ({k: r & a ? (r & b ? "c" : "b") : r & b ? "a" : step && a === S_ ? "q" : "o", A: blobCell(255 & ~(a | ab | pa)), B: blobCell(255 & ~(b | ab | pb))}));
    q.slim = true; return q;
  }
  // which px of the sheet a shape's px (i, j) is: [cell x, cell y, px, px] (null: none, an outer corner's own px), and that px in a sheet's data
  function cellAt(q, i, j) {
    const c = q[(j >> 3) * 2 + (i >> 3)];
    if (!q.slim) return [c[0], c[1], i, j];
    const si = i < 8 ? SLIM.x[i] : 15 - SLIM.x[15 - i], sj = j < 8 ? SLIM.n[j] : SLIM[c.k === "q" ? "q" : "s"][j - 8], ni = i < 8 ? i : 15 - i, nj = j < 8 ? j : 15 - j;
    let a = c.k === "a";
    if (c.k === "c") a = ni * (j < 8 ? 4 : 7) < nj * 5;      // (an inner corner: the rim there is the px near the corner, by the arm it goes on along)
    else if (c.k !== "b" && !a) { const di = ni - 2, dj = j < 8 ? j - 1 : nj - 2;      // (px in from where its side's edge starts, its north's, its south's)
      if (c.k === "o" && di + dj < 2) return null; a = j < 8 ? dj < di : dj <= di; }
    return a ? [c.A[0], c.A[1], i, sj] : [c.B[0], c.B[1], si, j];
  }
  const cellPx = (d, q, i, j) => { const c = cellAt(q, i, j); return c ? d.px[(c[1] * 16 + c[3]) * d.w + c[0] * 16 + c[2]] : 0; };
  // -> [what of the top of a tile whose neighbours are m is drawn (16 x 16), its quarters]: also what hides who stands behind it (behind.js)
  function cap(sheet, m) {
    const q = quarters(m, m & 256);
    if (!q.slim) return [cellAlpha(sheet, q[0][0], q[0][1]), q];
    const a = new Uint8Array(256); for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) { const c = cellAt(q, i, j); a[j * 16 + i] = c ? cellAlpha(sheet, c[0], c[1])[c[3] * 16 + c[2]] : 0; }
    return [a, q];
  }
  function shape(x, y, z) {
    if (z < 0) return 0;                                        // (under sea level: no grass, so no rim of it: cut square)
    let m = maskOf(x, y, (_, g, nx, ny) => (z <= 0 && wet(g)) || (colHas(colAt(nx, ny), z) && !(z > 0 && topAt(nx, ny) === z && wet(g))));   // (the one mask rule, tiles.js: not lower: land not come yet, a solid cell, the water beside a shore; water up on a hill, its face at this top's height: lower, the top has its rim along it: a bank)
    if (reduce(m) === 255) return 0;
    if (!(reduce(m) & 240) && m & N_ && !(m & S_) && topAt(x, y - 1) === z + 1 && topAt(x, y + 1) === z - 1) m |= 256;      // (a step of a stair one tile wide going up north: flat-fronted)
    const zz = level(x, y, z), sheet = sheetOf(zz), [cx, cy] = blobCell(m & 255), q = quarters(m, m & 256), key = (zz <= 2 ? 0 : zz <= 4 ? 1 : 2) * 4096 + (q.slim ? 2048 + reduce(m & 255) + (m & 256) : cy * 64 + cx);      // (the three sheets: tiles.js hillSheet)
    if (!ids.has(key)) { if (cells.length > 255) return 0; ids.set(key, cells.length); cells.push([cap(sheet, m)[0], sheet, q]); }
    return ids.get(key);
  }
  // a shape's lip: down each px across, how many px from the tile's south end are not the top's ground but the
  // wall under it (what the sheet leaves empty, and the sheet's own px there that its plain cell has no colour of)
  const lips = new Map();
  function lip(id) {
    const out = new Uint8Array(16); if (!id) return out;
    const [a, sheet, q] = cells[id], d = sheetData(sheet), [ix, iy] = blobCell(255), plain = new Set();
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) plain.add(d.px[(iy * 16 + j) * d.w + ix * 16 + i]);
    for (let i = 0; i < 16; i++) { let j = 15; while (j >= 0 && (!a[j * 16 + i] || !plain.has(cellPx(d, q, i, j)))) j--; out[i] = j < 0 ? 0 : 15 - j; }      // (a column with none of the ground: no lip, it is not a south edge)
    return out;
  }
  function rim(x, y, z, px, at, stride) {
    const id = shape(x, y, z); if (!id) return;
    const zz = level(x, y, z), a = cells[id][0], q = cells[id][2], d = sheetData(sheetOf(zz)), [ix, iy] = blobCell(255), [L, M, D] = bands(zz).map(rgb), map = earth(zz), own = (v) => (map && map.get(v)) || v;
    // (its lip, the sheet's own px of wall under the top's ground: in the wall's one tone, the same px of that rock's sheet)
    const ref = map || wallOf(zz) === zz ? null : sheetData(hillSheet(wallOf(zz))), lp = ref ? lips.get(id) || lips.set(id, lip(id)).get(id) : null;
    const drop = q.slim || colHas(colAt(x, y - 1), z) ? 0 : z - topAt(x, y - 1), north = Math.min(2, drop - 1);      // the far side of a drop of more than a level: its dark line that much thicker, a px a level
    const deep = !colHas(colAt(x, y - 1), z) && z - topAt(x, y - 1) >= 4, line = drop > 0 && zz > 4;      // (not a narrow top's: its rim is slimmed already, and the wall's dark was a salmon line across a stair's cap) (line: stone's far edge at any drop: its first px the wall's own dark: the sheet's pale edge there told no step from the north)
    for (let i = 0; i < 16; i++) {
      let last = 15; while (last >= 0 && !a[last * 16 + i]) last--;
      for (let j = 0, top = -1; j < 16; j++) {
        const o = at + j * stride + i;
        if (a[j * 16 + i]) {
          const v = lp && j > 15 - lp[i] ? cellPx(ref, q, i, j) : own(cellPx(d, q, i, j));
          if (top < 0) top = j;
          if (j === top && line && j < 8) px[o] = D;
          else if (j > top && j <= top + north && j < 8) px[o] = deep ? D : own(cellPx(d, q, i, top));      // (a drop of four levels or more, a gorge's near rim: the wall's own dark)
          else if (v !== d.px[(iy * 16 + j) * d.w + ix * 16 + i]) px[o] = v;
        } else px[o] = last < 0 || j < last ? 0 : j === last + 1 ? L : M;      // (outside its shape: see-through; but under its last px, down to the tile's end: its wall)
      }
    }
  }
  const {front} = VoxPaintFront.create({rgb, bands, wallOf, STONE});   // (a level's south face: voxpaint_front.js)
  return {shape, rim, front, rocky, level};
})();
