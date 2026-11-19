// The paint of a block's sides (the land as blocks: voxels.js hands these to the engine), all of it read off the
// level's own hill sheet (colsOf, relief.js: its wall's colours, its side's).
//   shape, profile: a block's cell has the shape of its sheet's cell for the sides where the land is lower (the
//     rounded corners and set-in edges of the pack; dug ground is cut square). Its profile: down each px across,
//     how much of the tile's south end the sheet leaves empty.
//   rim: a top's lip: that cell of the sheet laid over the plain top. Outside its shape the px is left
//     see-through (what is behind shows, as round the pack's own hills); under its last px, down to the tile's
//     end, is the wall the front goes on with: lit along its top, then its body.
//   front: a south face, a level: the wall's body, a seam along its foot that swells a px here and there as the
//     sheet's scallops do, a few flecks; four variants a level.
//   side: a wall that faces west or east shows a thin side (the engine's: a dark line and a px of wall). Its light
//     and its body are the wall's; the line at a wall's foot: its dark; the shadow at its foot: the pack's
//     own (the see-through px round a hill sheet's cells), where the sheet has one.
//   One rock a wall: the pack has a wall for each of its three sheets (grass, levels 1-2: orange earth; dark grass,
//     3-4: grey-brown earth; stone, 5 and up). A wall four levels high was grey-brown over orange, two palettes down one face.
//     Earth is one rock here: every wall of levels 1 to 4 has the first sheet's wall (EARTH), and the px of wall in
//     the second sheet's caps (their lip, their sides) are painted in it too; stone over earth is a real layer, at
//     one height all along a cliff.
const VoxPaint = (() => {
  const rgb = (c) => (255 << 24 | (c[2] | 0) << 16 | (c[1] | 0) << 8 | (c[0] | 0)) >>> 0;
  const EARTH = 2, bands = (z) => colsOf(hillSheet(z > EARTH && z < 5 ? EARTH : z)).bands, sheetOf = (z) => hillSheet(z < 0 ? z : Math.max(1, z));
  // the px of wall (browns: more red than green) of a sheet whose wall is not EARTH's -> EARTH's, lightest to darkest
  const browns = (sheet) => { const d = sheetData(sheet), [cx, cy] = blobCell(N_ | E_ | W_ | NE | NW), set = new Set(); for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) { const v = d.px[(cy * 16 + j) * d.w + cx * 16 + i]; if (v >>> 24 === 255 && (v & 255) > (v >>> 8 & 255)) set.add(v); }
    return [...set].sort((a, b) => (a & 255) - (b & 255)); };
  const earths = new Map(), earth = (z) => { if (!(z > EARTH && z < 5)) return null; let m = earths.get(z); if (!m) { const to = browns(hillSheet(EARTH)); m = new Map(browns(hillSheet(z)).map((v, i) => [v, to[Math.min(i, to.length - 1)]])); earths.set(z, m); } return m; };
  const ids = new Map(), cells = [null];                        // a shape: [what of it is drawn, its sheet, the sheet's cell (cx, cy) each quarter of it is: NW, NE, SW, SE]; 0: the whole square
  // A narrow top (no land as high west and east of it, or north and south): the sheet's own cell for it is all rim (a
  // pillar's top was a button, a ridge a hedge: the sheet's rim is 7 px a side, a tile has 16). It is made of the sheet's edge cells instead, a quarter each, each as if the land went on on its far
  // sides, and across the narrow way the rim is slimmed: of the edge cell's px from the outside in only SLIM are
  // kept (the empty px, one of the wall, the dark green, one of the mid green; then its flat middle), so a top one
  // tile wide has 6 px of its own flat green across. An outer corner is its two edge cells mitred, the corner's own
  // px left out (the sheet's corner cell is rounded six px: four of them were a ball). Else the sheet's cell, four times
  const QUARTER = [[N_, W_, NW, NE, SW], [N_, E_, NE, NW, SE], [S_, W_, SW, SE, NW], [S_, E_, SE, SW, NE]];      // (its two sides, its corner, then the corner past each side)
  const SLIM = {x: [0, 1, 3, 4, 5, 8, 8, 8], n: [0, 2, 3, 6, 6, 6, 6, 6], s: [6, 9, 10, 11, 12, 13, 14, 15]};      // (west: the px of the edge cell that px 0..7 is; north; south, px 8..15)
  function quarters(m) {
    const r = reduce(m), one = blobCell(m), nx = !(r & (W_ | E_)), ny = !(r & (N_ | S_));
    if (!(nx || ny)) return [one, one, one, one];
    const q = QUARTER.map(([a, b, ab, pa, pb]) => { const na = 255 & ~(a | ab | pa), nb = 255 & ~(b | ab | pb);
      return r & (a | b) ? blobCell((r & a ? 255 : na) & (r & b ? 255 : nb) & ~(r & ab ? 0 : ab)) : [...blobCell(na), ...blobCell(nb)]; });      // (an outer corner: the cell of each of its two edges)
    q.nx = nx; q.ny = ny; return q;
  }
  // which px of the sheet a shape's px (i, j) is: [cell x, cell y, px, px] (null: none, an outer corner's own px), and that px in a sheet's data
  function cellAt(q, i, j) {
    const c = q[(j >> 3) * 2 + (i >> 3)], si = !q.nx ? i : i < 8 ? SLIM.x[i] : 15 - SLIM.x[15 - i], sj = !q.ny ? j : j < 8 ? SLIM.n[j] : SLIM.s[j - 8];
    if (c.length < 4) return [c[0], c[1], si, sj];
    const di = (i < 8 ? i : 15 - i) - 2, dj = j < 8 ? j - 1 : 15 - j - 2;      // (px in from where its side's edge starts, its north's, its south's)
    return di + dj < 2 ? null : (j < 8 ? dj < di : dj <= di) ? [c[0], c[1], i, sj] : [c[2], c[3], si, j];
  }
  const cellPx = (d, q, i, j) => { const c = cellAt(q, i, j); return c ? d.px[(c[1] * 16 + c[3]) * d.w + c[0] * 16 + c[2]] : 0; };
  // -> [what of the top of a tile whose neighbours are m is drawn (16 x 16), its quarters]: also what hides who stands behind it (behind.js)
  function cap(sheet, m) {
    const q = quarters(m);
    if (q[0] === q[3]) return [cellAlpha(sheet, q[0][0], q[0][1]), q];
    const a = new Uint8Array(256); for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) { const c = cellAt(q, i, j); a[j * 16 + i] = c ? cellAlpha(sheet, c[0], c[1])[c[3] * 16 + c[2]] : 0; }
    return [a, q];
  }
  function shape(x, y, z) {
    if (z < 0) return 0;                                        // (dug: cut square)
    let m = 0;
    for (let k = 0; k < 24; k += 3) {                             // (not lower: land not come yet, a solid cell, the water beside a shore)
      const nx = x + AROUND[k], ny = y + AROUND[k + 1];
      if (!blockOf(nx, ny) || (z <= 0 && wet(gndAt(nx, ny) || ".")) || colHas(colAt(nx, ny), z)) m |= AROUND[k + 2];
    }
    if (reduce(m) === 255) return 0;
    const sheet = sheetOf(z), [cx, cy] = blobCell(m), q = quarters(m), key = (z <= 2 ? 0 : z <= 4 ? 1 : 2) * 4096 + (q[0] === q[3] ? cy * 64 + cx : 2048 + reduce(m));      // (the three sheets: tiles.js hillSheet)
    if (!ids.has(key)) { if (cells.length > 255) return 0; ids.set(key, cells.length); cells.push([cap(sheet, m)[0], sheet, q]); }
    return ids.get(key);
  }
  function profile(id) {
    const out = new Uint8Array(16), a = id ? cells[id][0] : null;
    if (a) for (let i = 0; i < 16; i++) { let j = 15; while (j >= 0 && !a[j * 16 + i]) j--; out[i] = 15 - j; }
    return out;
  }
  // ...its crown: [west, east]: the px its first px across from that side leaves empty at its north end (a rounded
  // corner: the wall's side beside it starts that far down)
  function crown(id) {
    const a = id ? cells[id][0] : null, out = [0, 0]; if (!a) return out;
    for (const k of [0, 1]) for (let n = 0; n < 16; n++) { const i = k ? 15 - n : n; let j = 0; while (j < 16 && !a[j * 16 + i]) j++; if (j < 16) { out[k] = j; break; } }
    return out;
  }
  // ...and its lip: down each px across, how many px from the tile's south end are not the top's ground but the
  // wall under it (what the sheet leaves empty, and the sheet's own px there that its plain cell has no colour of)
  function lip(id) {
    const out = new Uint8Array(16); if (!id) return out;
    const [a, sheet, q] = cells[id], d = sheetData(sheet), [ix, iy] = blobCell(255), plain = new Set();
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) plain.add(d.px[(iy * 16 + j) * d.w + ix * 16 + i]);
    for (let i = 0; i < 16; i++) { let j = 15; while (j >= 0 && (!a[j * 16 + i] || !plain.has(cellPx(d, q, i, j)))) j--; out[i] = j < 0 ? 0 : 15 - j; }      // (a column with none of the ground: no lip, it is not a south edge)
    return out;
  }
  function rim(x, y, z, px, at, stride) {
    const id = shape(x, y, z); if (!id) return;
    const a = cells[id][0], q = cells[id][2], d = sheetData(sheetOf(z)), [ix, iy] = blobCell(255), [L, M, D] = bands(z).map(rgb), map = earth(z), own = (v) => (map && map.get(v)) || v;
    const north = colHas(colAt(x, y - 1), z) ? 0 : Math.min(2, z - 1 - topAt(x, y - 1));      // the far side of a drop of more than a level: its dark line that much thicker, a px a level
    const deep = !colHas(colAt(x, y - 1), z) && z - topAt(x, y - 1) >= 4;
    for (let i = 0; i < 16; i++) {
      let last = 15; while (last >= 0 && !a[last * 16 + i]) last--;
      for (let j = 0, top = -1; j < 16; j++) {
        const o = at + j * stride + i;
        if (a[j * 16 + i]) {
          const v = own(cellPx(d, q, i, j));
          if (top < 0) top = j;
          if (j > top && j <= top + north && j < 8) px[o] = deep ? D : own(cellPx(d, q, i, top));      // (a drop of four levels or more, a gorge's near rim: the wall's own dark)
          else if (v !== d.px[(iy * 16 + j) * d.w + ix * 16 + i]) px[o] = v;
        } else px[o] = last < 0 || j < last ? 0 : j === last + 1 ? L : M;      // (outside its shape: see-through; but under its last px, down to the tile's end: its wall)
      }
    }
  }
  function front(z, v, px, at, stride) {
    const [L, M, D] = bands(z).map(rgb), n = RELIEF_STEP, h = (i, j, s) => hash(i + v * 16, j + z * 8, s);
    for (let j = 0; j < n; j++) for (let i = 0; i < 16; i++) {
      let c = j === n - 1 ? D : M;
      if (j === n - 2 && h(i >> 1, 0, 61) < .3) c = D;            // the seam swells, two px wide
      else if (j > 0 && j < n - 2 && h(i - (i + j) % 3, j, 62) < .08) c = h(i - (i + j) % 3, j, 63) < .6 ? L : D;      // flecks: three px, light or dark
      px[at + j * stride + i] = c;
    }
  }
  // (the pack's shadow: the see-through px at the foot of hill1's south edge, as dark as it is there)
  let ink = null;
  function shadow() {
    if (ink) return ink;
    const d = sheetData(IMG.hill1), [ex, ey] = blobCell(N_ | E_ | W_ | NE | NW);
    for (let j = 15; j >= 0 && !ink; j--) { const v = d.px[(ey * 16 + j) * d.w + ex * 16 + 8], a = v >>> 24; if (a && a < 255) ink = [v & 255, v >>> 8 & 255, v >>> 16 & 255, a / 255]; }
    return ink || (ink = [80, 64, 134, .25]);
  }
  const side = (z) => { const b = bands(z), s = shadow(); return {band: b[0], body: b[1], foot: b[2], shadow: z > 4 || z <= 0 ? [s[0], s[1], s[2], 0] : s}; };      // (the stone sheet has no shadow px; nor has a hole's wall)
  return {shape, profile, crown, lip, rim, front, side, shadow, cap};
})();
