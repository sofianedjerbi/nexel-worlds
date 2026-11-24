// VOX: what the HD look's land (vox_style_land.js) takes of a column of cells: the rock a cell is painted as, the top of
// the block a cell is in, one of n picked by a place.
const VoxMesh = (() => {
  const has = (c, z) => { for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };      // is a column's cell z solid?
  // One rock a block (cfg.rock: {from, lo, n}; none: a cell's paint is its level's): a block whose top is at level `from` or over has, in its
  // cells from `lo` up to there, the paint of the levels from `from` on, n of them in turn: stone down to the ground, not stone over earth.
  // top: its block's top (topOf: of the block the cell z of a column is in) -> the level whose strip of the sheets the cell has
  // (on: the host says its tile is rock, host.rock(x, y, z) (2: that cell is stone, whatever its height: a block of stone put on a meadow, the stone under a meadow's earth); not: a block as high that is no rock, a stair's step, a pillar: the paint of the last level under `from` up to its top)
  const rock = (cfg, top, z, on = true) => { const r = cfg.rock; return !r || (top < r.from && on !== 2) ? z : !on ? Math.min(z, r.from - 1) : z < r.from && z >= r.lo ? r.from + (z - r.lo) % r.n : z; };
  const topOf = (c, z) => { if (c) for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return c[i]; return z; };
  const pick = (x, y, z, n) => (Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791)) >>> 5 & (n - 1);      // one of n (a power of 2), the same each time
  // a column (the heights where it changes, from the bottom up: cells.js) without its cells over h (the land's cut under it: vox_style_land.js)
  function clip(c, h) {
    if (c[c.length - 1] <= h) return c;
    const out = [];
    for (let i = 0; i < c.length; i += 2) {
      if (i && c[i - 1] >= h) break;
      out.push(Math.min(c[i], h));
      if (c[i] >= h || i + 1 >= c.length) break;
      out.push(c[i + 1]);
    }
    if (out.length % 2 === 0) out.pop();
    return out;
  }
  return {has, pick, rock, topOf, clip};
})();
