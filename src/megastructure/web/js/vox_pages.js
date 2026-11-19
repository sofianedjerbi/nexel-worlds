// VOX: the paint of the faces.
// A top's paint is a square of px the host paints (host.paintTop). A chunk keeps its tops as pages of px, a square
// a tile, laid out as the tiles are: page 0 holds every column's highest top (the land as seen from above), page 1
// the top under its first roof, and so on down. A page is made only where a chunk has such a top. The sides' paint is the host's too: small
// sheets for every level (fronts, below). A page is handed to the GPU whole, once, and again only when a tile of
// it was painted again.
const VoxPages = (() => {
  // A column's tops from the highest down: [height, page]. (A column: the heights where it changes, from the
  // bottom: solid up to c[0], empty up to c[1], solid up to c[2]...)
  const topsOf = (c) => { const out = []; for (let q = c.length - 1, p = 0; q >= 0; q -= 2, p++) out.push([c[q], p]); return out; };
  function page(ch, p, side) {
    if (!ch.pages[p]) ch.pages[p] = {px: new Uint32Array(side * side), tex: null, stale: true};
    return ch.pages[p];
  }
  // A tile's tops painted again, each on its page. cfg: {size (tiles a chunk's side), cell (px a tile's side)}
  function tile(ch, host, cfg, lx, ly) {
    const side = cfg.size * cfg.cell, x = ch.cx * cfg.size + lx, y = ch.cy * cfg.size + ly, c = host.column(x, y);
    if (!c) return;
    if (host.water(x, y)) {                                     // (water: what the host paints on it, if anything: what floats there)
      const pg = page(ch, 0, side), at = ly * cfg.cell * side + lx * cfg.cell; let any = 0;
      for (let j = 0; j < cfg.cell; j++) pg.px.fill(0, at + j * side, at + j * side + cfg.cell);
      host.paintTop(x, y, 0, pg.px, at, side);
      for (let j = 0; j < cfg.cell && !any; j++) for (let i = 0; i < cfg.cell; i++) if (pg.px[at + j * side + i] >>> 24) { any = 1; break; }
      (ch.decor || (ch.decor = new Uint8Array(cfg.size * cfg.size)))[ly * cfg.size + lx] = any; pg.stale = true;
      return;
    }
    for (const [z, p] of topsOf(c)) { const pg = page(ch, p, side); host.paintTop(x, y, z, pg.px, ly * cfg.cell * side + lx * cfg.cell, side); pg.stale = true; }
  }
  function upload(ch, cfg) {
    const side = cfg.size * cfg.cell;
    for (const pg of ch.pages) if (pg && pg.stale) { pg.tex = VoxGL.texture({px: pg.px, w: side, h: side}, pg.tex); pg.stale = false; }
  }
  // The sides' sheets for the levels lo to hi. The fronts': a level a row (`up` px), cfg.variants pictures of a
  // cell across, each painted by the host. The walls' (host.side(z) -> {band, foot, shadow, body}): a level a row of
  // four px: its bank's top, its foot's line, the shadow at its foot ([r, g, b, a]), its bank's front.
  // The shapes' (host.profile(id) -> for each px across, the px its block leaves empty at its south end): a
  // shape a row, filled in as shapes are met (VoxPages.shapes).
  const rgba = (c) => (Math.round((c.length > 3 ? c[3] : 1) * 255) << 24 | Math.round(c[2]) << 16 | Math.round(c[1]) << 8 | Math.round(c[0])) >>> 0;
  function fronts(host, cfg, lo, hi) {
    const n = hi - lo + 1, w = cfg.variants * cfg.cell, px = new Uint32Array(w * n * cfg.up), side = new Uint32Array(4 * n);
    for (let k = 0; k < n; k++) {
      for (let v = 0; v < cfg.variants; v++) host.paintFront(lo + k, v, px, k * cfg.up * w + v * cfg.cell, w);
      const s = host.side(lo + k); side.set([rgba(s.band), rgba(s.foot), rgba(s.shadow), rgba(s.body)], k * 4);
    }
    return {tex: VoxGL.texture({px, w, h: n * cfg.up}), sides: VoxGL.texture({px: side, w: 4, h: n}), n, lo, hi, prof: {px: new Uint32Array(cfg.cell * 256), seen: new Set(), tex: null, stale: true}};
  }
  function shapes(prof, host, cfg, ids) {
    for (const id of ids) if (!prof.seen.has(id)) { prof.seen.add(id); prof.px.set(host.profile(id), id * cfg.cell); prof.stale = true;
      if (host.lip) host.lip(id).forEach((v, i) => { prof.px[id * cfg.cell + i] |= v << 8; }); }      // (green: its lip, for the sun)
    if (prof.stale) { prof.tex = VoxGL.texture({px: prof.px, w: cfg.cell, h: 256}, prof.tex); prof.stale = false; }
  }
  function drop(ch) { const gl = VoxGL.gl; if (gl) for (const pg of ch.pages) if (pg && pg.tex) gl.deleteTexture(pg.tex); }
  return {topsOf, tile, upload, fronts, shapes, drop};
})();
