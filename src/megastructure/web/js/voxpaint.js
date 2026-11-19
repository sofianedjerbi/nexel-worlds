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
//   side: a wall that faces west or east leans out a little a level (the engine's bank). Its top is the wall's lit
//     colour, its front the wall's body; the line at a wall's foot: its dark; the shadow at its foot: the pack's
//     own (the see-through px round a hill sheet's cells), where the sheet has one.
const VoxPaint = (() => {
  const rgb = (c) => (255 << 24 | (c[2] | 0) << 16 | (c[1] | 0) << 8 | (c[0] | 0)) >>> 0;
  const bands = (z) => colsOf(hillSheet(z)).bands, sheetOf = (z) => hillSheet(z < 0 ? z : Math.max(1, z));
  const ids = new Map(), cells = [null];                        // a shape: a sheet's cell [sheet's data, cx, cy]; 0: the whole square
  function shape(x, y, z) {
    if (z < 0) return 0;                                        // (dug: cut square)
    let m = 0;
    for (let k = 0; k < 24; k += 3) {                             // (not lower: land not come yet, a solid cell, the water beside a shore)
      const nx = x + AROUND[k], ny = y + AROUND[k + 1];
      if (!blockOf(nx, ny) || (z <= 0 && wet(gndAt(nx, ny) || ".")) || colHas(colAt(nx, ny), z)) m |= AROUND[k + 2];
    }
    if (reduce(m) === 255) return 0;
    const sheet = sheetOf(z), [cx, cy] = blobCell(m), key = (z <= 2 ? 0 : z <= 4 ? 1 : 2) * 4096 + cy * 64 + cx;      // (the three sheets: tiles.js hillSheet)
    if (!ids.has(key)) { if (cells.length > 255) return 0; ids.set(key, cells.length); cells.push([cellAlpha(sheet, cx, cy), sheet, cx, cy]); }
    return ids.get(key);
  }
  function profile(id) {
    const out = new Uint8Array(16), a = id ? cells[id][0] : null;
    if (a) for (let i = 0; i < 16; i++) { let j = 15; while (j >= 0 && !a[j * 16 + i]) j--; out[i] = 15 - j; }
    return out;
  }
  // ...and its lip: down each px across, how many px from the tile's south end are not the top's ground but the
  // wall under it (what the sheet leaves empty, and the sheet's own px there that its plain cell has no colour of)
  function lip(id) {
    const out = new Uint8Array(16); if (!id) return out;
    const [a, sheet, cx, cy] = cells[id], d = sheetData(sheet), [ix, iy] = blobCell(255), plain = new Set();
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) plain.add(d.px[(iy * 16 + j) * d.w + ix * 16 + i]);
    for (let i = 0; i < 16; i++) { let j = 15; while (j >= 0 && (!a[j * 16 + i] || !plain.has(d.px[(cy * 16 + j) * d.w + cx * 16 + i]))) j--; out[i] = j < 0 ? 0 : 15 - j; }      // (a column with none of the ground: no lip, it is not a south edge)
    return out;
  }
  function rim(x, y, z, px, at, stride) {
    const id = shape(x, y, z); if (!id) return;
    const a = cells[id][0], d = sheetData(sheetOf(z)), [ix, iy] = blobCell(255), [L, M] = bands(z).map(rgb);
    let cx = 0, cy = 0; for (const [k, v] of ids) if (v === id) { cx = k % 64; cy = (k >> 6) % 64; }
    const north = colHas(colAt(x, y - 1), z) ? 0 : Math.min(2, z - 1 - topAt(x, y - 1));      // the far side of a drop of more than a level: its dark line that much thicker, a px a level
    for (let i = 0; i < 16; i++) {
      let last = 15; while (last >= 0 && !a[last * 16 + i]) last--;
      for (let j = 0, own = -1; j < 16; j++) {
        const o = at + j * stride + i;
        if (a[j * 16 + i]) {
          const v = d.px[(cy * 16 + j) * d.w + cx * 16 + i];
          if (own < 0) own = j;
          if (j > own && j <= own + north && j < 8) px[o] = d.px[(cy * 16 + own) * d.w + cx * 16 + i];
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
  const band = (z) => (z <= 0 ? 1 : 2);                         // (dug ground: a px, so a hole's floor is not narrowed)
  return {shape, profile, lip, rim, front, side, band, shadow};
})();
