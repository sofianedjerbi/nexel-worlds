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
//     the second sheet's caps (their lip, their sides) are painted in it too.
//   One tone a rock: a level's sheet is a touch brighter than the one under it (tiles.js hillSheet: terraces read as
//     steps), and that is for tops. A wall has its rock's one tone at every level (earth: EARTH's; stone: STONE's), its
//     lip in the top's paint too: on a cliff that runs on a slant each column is drawn two levels lower than the one
//     beside it, and a tone a level made it a grid of grey squares ("this wall look so weird"). And one rock from rim
//     to foot: a block whose top is stone is stone down to the ground (voxels.js cfg.rock: the engine picks a cell's
//     strip by its block's top), so stone never meets earth in a staircase along such a cliff.
const VoxPaint = (() => {
  const rgb = (c) => (255 << 24 | (c[2] | 0) << 16 | (c[1] | 0) << 8 | (c[0] | 0)) >>> 0;
  const EARTH = 2, STONE = "rock", wallOf = (z) => (z > 4 ? STONE : z > 0 ? EARTH : z), bands = (z) => colsOf(hillSheet(wallOf(z))).bands, sheetOf = (z) => hillSheet(z < 0 ? z : Math.max(1, z));
  // the px of wall (browns: more red than green) of a sheet whose wall is not EARTH's -> EARTH's, lightest to darkest
  const browns = (sheet) => { const d = sheetData(sheet), [cx, cy] = blobCell(N_ | E_ | W_ | NE | NW), set = new Set(); for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) { const v = d.px[(cy * 16 + j) * d.w + cx * 16 + i]; if (v >>> 24 === 255 && (v & 255) > (v >>> 8 & 255)) set.add(v); }
    return [...set].sort((a, b) => (a & 255) - (b & 255)); };
  const earths = new Map(), earth = (z) => { if (!(z > EARTH && z < 5)) return null; let m = earths.get(z); if (!m) { const to = browns(hillSheet(EARTH)); m = new Map(browns(hillSheet(z)).map((v, i) => [v, to[Math.min(i, to.length - 1)]])); earths.set(z, m); } return m; };
  // Stone is a mass, not a height: a block is stone where its top is at level 5 or over AND its tile is in a 3 x 3 of tiles all that high (`core`: a mountain, a plateau, a terrace
  // along one), or joined to one by three tiles as high at the most (a mountain's tip, the end of a cliff that runs on a slant, a stair up its flank). A stair that climbs past level 4
  // on its own, a pillar, a wall one or two tiles thick stay earth to their top, grass on it: a staircase's fifth step was a grey column, two objects.
  // rocky: is the tile's high block stone; level: the level whose paint the block with its top at z has there (4: the highest earth). The engine: host.rock, voxels.js
  let seen = -1; const mass = new Map(), cores = new Map(), REACH = 3;
  function core(x, y) {
    const k = x + "," + y; let r = cores.get(k); if (r !== undefined) return r;
    r = false; for (let oy = -2; oy <= 0 && !r; oy++) for (let ox = -2; ox <= 0 && !r; ox++) { r = true; for (let j = 0; j < 3 && r; j++) for (let i = 0; i < 3 && r; i++) r = topAt(x + ox + i, y + oy + j) > 4; }
    cores.set(k, r); return r;
  }
  function rocky(x, y) {
    const m = matAt(x, y); if (m) return m === "s" ? 2 : false;   // (a block put there: stone at any height (2), earth on a mountain: what was put, not what the height says)
    if (topAt(x, y) < 5) return false;
    if (seen !== landVer) { mass.clear(); cores.clear(); seen = landVer; }
    const k = x + "," + y; let r = mass.get(k); if (r !== undefined) return r;
    r = core(x, y);
    for (let at = [x, y], d = 0, met = new Set([k]); !r && d < REACH; d++) { const next = [];
      for (let i = 0; i < at.length && !r; i += 2) for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const nx = at[i] + dx, ny = at[i + 1] + dy, nk = nx + "," + ny; if (met.has(nk) || topAt(nx, ny) < 5) continue; met.add(nk); if (core(nx, ny)) { r = true; break; } next.push(nx, ny); }
      at = next; }
    mass.set(k, r); return r;
  }
  const level = (x, y, z) => (z < 5 && rocky(x, y) === 2 ? 5 + (z + 512) % 4 : z > 4 && !rocky(x, y) ? 4 : z);   // (a stone block put low: the stone level the engine gives its sides, vox_mesh.js rock)
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
    if (z < 0) return 0;                                        // (dug: cut square)
    let m = 0;
    for (let k = 0; k < 24; k += 3) {                             // (not lower: land not come yet, a solid cell, the water beside a shore)
      const nx = x + AROUND[k], ny = y + AROUND[k + 1];
      if (!blockOf(nx, ny) || (z <= 0 && wet(gndAt(nx, ny) || ".")) || (colHas(colAt(nx, ny), z) && !(z > 0 && topAt(nx, ny) === z && wet(gndAt(nx, ny) || ".")))) m |= AROUND[k + 2];      // (water up on a hill, its face at this top's height: lower, the top has its rim along it: a bank)
    }
    if (reduce(m) === 255) return 0;
    if (!(reduce(m) & 240) && m & N_ && !(m & S_) && topAt(x, y - 1) === z + 1 && topAt(x, y + 1) === z - 1) m |= 256;      // (a step of a stair one tile wide going up north: flat-fronted)
    const zz = level(x, y, z), sheet = sheetOf(zz), [cx, cy] = blobCell(m & 255), q = quarters(m, m & 256), key = (zz <= 2 ? 0 : zz <= 4 ? 1 : 2) * 4096 + (q.slim ? 2048 + reduce(m & 255) + (m & 256) : cy * 64 + cx);      // (the three sheets: tiles.js hillSheet)
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
  return {shape, profile, crown, lip, rim, front, side, shadow, cap, rocky, level};
})();
