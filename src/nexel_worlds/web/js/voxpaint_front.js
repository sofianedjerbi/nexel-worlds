// A level's south face (voxpaint.js front): the wall's body laid from the pack's own cliff px, a seam at its foot, and
// what its rock has: earth a stratum and pebbles, laid stone blocks their courses and joints, natural stone a cliff.
//   VoxPaintFront.create(K) -> {front(z, v, px, at, stride, built)}: a level z's face, variant v, into px at `at`
//   K: {rgb, bands(z), wallOf(z), STONE} (voxpaint.js: a colour as a px; a level's wall's bands; its rock)
// the pack's own cliff px: the two rows of a sheet's south edge cell over its foot (its wall: light and mid in blobs, the darkest in
// them), and its lightest and darkest px. A front's body is laid from them (not one flat tone with a fleck in twelve px: a slab)
// A CLIFF (natural stone's south face, a level): no courses, no seam across its foot. One or two fracture planes run
// down it, wandering a px now and then, at no fixed place: each its dark px with the lit edge of the plane east of it,
// the facets between them stepped in (darker) or out; a ledge or two, short (2 or 3 px: a lit lip over its undercut)
// at rows 5 to 7, some levels none; a lit run along its top now and then; a crack. A level's foot all dark was a line
// under every level: courses again, stripes on a far face. Laid blocks (a stone block put down: `built`) keep their
// courses: what was built is told from what was there.
const VoxPaintFront = (() => {
  function create(K) {
    const {rgb, bands, wallOf, STONE} = K;
    const mots = new Map(), lum = (v) => (v & 255) * .3 + (v >>> 8 & 255) * .59 + (v >>> 16 & 255) * .11;
    function mottle(z) {
      const sheet = hillSheet(wallOf(z)); let m = mots.get(sheet); if (m) return m;
      const d = sheetData(sheet), [cx, cy] = blobCell(N_ | E_ | W_ | NE | NW), f = colsOf(sheet).foot, rows = [], seen = new Set();
      for (const j of [f - 3, f - 2]) { const r = new Uint32Array(16); for (let i = 0; i < 16; i++) { r[i] = d.px[(cy * 16 + j) * d.w + cx * 16 + i]; if (r[i] >>> 24 === 255) seen.add(r[i]); else r[i] = 0; } rows.push(r); }
      const cols = [...seen].sort((a, b) => lum(b) - lum(a)), M0 = rgb(bands(z)[1]);
      for (const r of rows) for (let i = 0; i < 16; i++) if (!r[i]) r[i] = cols[1] || M0;
      m = {rows, light: cols[0] || M0, dark: cols[cols.length - 1] || M0}; mots.set(sheet, m); return m;
    }
    const dim = (v, k) => (255 << 24 | ((v >>> 16 & 255) * k) << 16 | ((v >>> 8 & 255) * k) << 8 | (v & 255) * k) >>> 0;
    function cliff(z, v, put, get, h, m, n) {
      const J = dim(m.dark, .82), U = dim(m.dark, .72), ins = (c) => dim(c, .88), fx = [], k = 1 + (h(0, 9, 80) < .6 ? 1 : 0);
      for (let f = 0; f < k; f++) { let x = ((f * 8 + 2 + h(f, 9, 81) * 6) | 0) & 15; const j0 = h(f, 9, 82) < .2 ? 1 + ((h(f, 9, 83) * 3) | 0) : 0, col = []; for (let j = 0; j < n; j++) { if (j > j0 && h(f, j, 84) < .25) x += h(f, j, 85) < .5 ? -1 : 1; col.push(j >= j0 ? x : -9); } fx.push(col); }
      for (let j = 0; j < n; j++) for (let i = 0; i < 16; i++) { let face = 0; for (const c of fx) if (c[j] >= 0 && i > c[j]) face++; const c = get(i, j); put(i, j, (face + v + z) & 1 ? ins(c) : c); }
      if (h(5, 9, 86) < .6) { const a = (h(6, 9, 87) * 12) | 0, w = 3 + ((h(7, 9, 88) * 3) | 0); for (let i = a; i < a + w; i++) put(i, 0, m.light); }
      for (const c of fx) for (let j = 0; j < n; j++) if (c[j] >= 0) { put(c[j], j, J); put(c[j] + 1, j, m.light); if (h(c[j], j, 89) < .4) put(c[j] - 1, j, ins(ins(get(c[j] - 1, j)))); }
      const nl = h(8, 9, 90) < .25 ? 0 : h(8, 9, 91) < .6 ? 1 : 2;
      for (let l = 0; l < nl; l++) { const a = (h(l, 10, 92) * 14) | 0, w = nl > 1 ? 2 : 2 + (h(l, 10, 93) < .5), r = 5 + ((h(l, 10, 94) * Math.max(3, n - 8)) | 0); for (let i = a; i < a + w; i++) { put(i, r - 1, m.light); put(i, r, U); } }
      if (h(1, 9, 95) < .5) { let i = (h(2, 9, 96) * 14) | 0, j = 2 + ((h(3, 9, 97) * 2) | 0); const dx = h(4, 9, 98) < .5 ? 1 : -1; for (let s = 0; s < 3; s++) { put(i, j, J); i += dx; j++; } }
    }
    function front(z, v, px, at, stride, built) {
      const [L, M, D] = bands(z).map(rgb), n = RELIEF_STEP, h = (i, j, s) => hash(i + v * 16, j + z * 8, s), m = mottle(z), stone = wallOf(z) === STONE, put = (i, j, c) => { if (i >= 0 && i < 16 && j >= 0 && j < n) px[at + j * stride + i] = c; };
      const sh = Array.from({length: n >> 1}, (_, k) => (h(k, 0, 64) * 16) | 0), row = (i, j) => m.rows[j & 1][(i + sh[(j >> 1) % sh.length]) & 15];   // (a shift for every pair of rows of the level: no pattern repeats down a cube's 16)
      for (let j = 0; j < n; j++) for (let i = 0; i < 16; i++) {      // the body: the pack's two rows, a pair of rows from its own place across, a blob a few px wide
        let c = row(i, j);
        if (j === n - 1) c = D; else if (j === n - 2 && h(i >> 1, 0, 61) < .3) c = D;      // the seam at a level's foot (levels are counted), it swells, two px wide
        else if (j === 0 && !stone && h(i >> 1, 0, 62) < .85) c = L;      // (earth: its top row lit, broken here and there: a block's edge over the seam of the one on it: a cube is counted)
        px[at + j * stride + i] = c;
      }
      if (stone && !built) cliff(z, v, put, row, h, m, n);
      else if (stone) {      // STONE BLOCKS (laid): two joints a level, a level's joints half a block from the one over it; each block lit along its top and its west edge; a crack now and then
        const J = dim(m.dark, .82);   // (each course 8 rows: its foot the joints' dark, all across: the stone sheet's darkest band is its body's tone, a level had no line under it and its only lines were its 1-px upright joints: streaks. A cube is two courses, the joints of one half a block from the other's)
        for (let c0 = 0; c0 < n; c0 += 8) { const x0 = (v * 5 + ((z * 2 + (c0 >> 3)) & 1) * 4 + 3) % 8, c1 = Math.min(n, c0 + 8); for (let i = 0; i < 16; i++) put(i, c1 - 1, J);
          for (let i = 0; i < 16; i++) { if (h(i, c0, 70) < .8) put(i, c0, m.light); if ((i - x0 + 16) % 8 === 0) for (let j = c0; j < c1 - 1; j++) { put(i, j, J); put(i + 1, j, m.light); } } }
        for (let k = 0; k < 2; k++) if (h(k, 1, 71) < .45) { let i = (h(k, 2, 72) * 16) | 0, j = 2; while (j < n - 2) { put(i, j, J); i += h(i, j, 73) < .5 ? 1 : 0; j++; } }
      } else {      // EARTH: a stratum (a wavy line of the darkest, now and then broken), pebbles (two px of the lightest over two of the darkest)
        for (let k = 0; k < n; k += 8) if (h(k, 1, 65) < .6) { const st = k + 2 + ((h(k, 2, 66) * 3) | 0); for (let i = 0; i < 16; i++) if (h(i >> 2, 3 + k, 67) < .85) put(i, st + (h(i >> 2, 4 + k, 68) < .35 ? 1 : 0), m.dark); }   // (a stratum in each half of a cube, or none, at its own row)
        for (let j = 1; j < n - 3; j++) for (let i = 0; i < 15; i += 2) if (h(i, j, 69) < .07) { put(i + (j & 1), j, L); put(i + (j & 1) + 1, j, L); put(i + (j & 1), j + 1, D); put(i + (j & 1) + 1, j + 1, m.dark); }
        deepen(px, at, stride, n, z, "wall");   // (under sea level: the same earth, darker the deeper, tiles.js)
      }
    }
    return {front};
  }
  return {create};
})();
