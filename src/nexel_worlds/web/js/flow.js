// Water that runs (the server's flow.py): in the land's empty cells, each at a level, 1 to 7 as it runs, 8 where a can
// was poured. The sea, rivers and lakes are not here (a water ground: water.js, waterbed.js): this is the water that
// fills a hole dug beside them a layer at a time, a puddle poured on flat ground, a waterfall down a step.
// Kept a block of tiles at a time (b.flow: tile index -> Map(height -> level)), as a region comes (`load`) and as it
// changes (`set`, the event "water", a few cells a step, four steps a second). A change makes the HD look make the
// chunk of the tile again (HdLook.wet: that chunk alone).
// The HD look draws it (vox_style_land.js): a face at the water's own height in its cell, z - 1 + level / 8, so
// shallow water lies lower and is drawn thinner (its tint by how deep it is: a film of 1 or 2 hardly tinted), a full
// cell under water to its top; and a south side where it stands higher than what is in front of it (a waterfall's
// face, a pool's edge seen from the south).
const Flow = (() => {
  let ver = 0;
  const colOf = (x, y) => { const b = blockOf(x, y); return b && b.flow ? b.flow.get((y - b.by * B) * B + (x - b.bx * B)) : undefined; };
  function put(b, i, z, v) { let c = b.flow.get(i); if (v) { if (!c) b.flow.set(i, c = new Map()); c.set(z, v); } else if (c) { c.delete(z); if (!c.size) b.flow.delete(i); } }
  function load(b, d) {                               // a region's water: [index, height, level] each
    const was = b.flow ? [...b.flow.keys()] : []; b.flow = new Map();
    for (const [i, z, v] of d.water || []) put(b, i, z, v);
    if (was.length || b.flow.size) { ver++; if (typeof HdLook !== "undefined" && HdLook.wet) for (const i of new Set([...was, ...b.flow.keys()])) HdLook.wet(b.bx * B + i % B, b.by * B + (i / B | 0)); }   // (a block come again, a resync: what changed in it)
  }
  function set(cells) {                               // the event "water": [x, y, z, level] each (0: dry now)
    const seen = new Set();
    for (const [x, y, z, v] of cells) { const t = tileIdx(x, y); if (!t) continue; if (!t[0].flow) t[0].flow = new Map(); put(t[0], t[1], z, v); seen.add(x + "," + y); }
    if (seen.size) ver++;
    if (typeof HdLook !== "undefined" && HdLook.wet) for (const k of seen) { const [x, y] = k.split(",").map(Number); HdLook.wet(x, y); }
  }
  const col = (x, y) => colOf(x, y) || null;               // the tile's cells with water: Map(height -> level), or null
  const at = (x, y, z) => { const c = colOf(x, y); return c ? c.get(z) || 0 : 0; };
  return {load, set, col, at, get ver() { return ver; }};
})();
