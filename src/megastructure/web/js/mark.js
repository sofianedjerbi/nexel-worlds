// What you aim at, shown as the block it is ("block selection is messy. it is still 2d. make the hint highlight
// the 3d block properly"). The land is blocks; a click digs a cell or puts something in one. So the hint is that
// cell, as a box, drawn by the engine with the land (vox_mark.js: the curved world bends it; what nearer land
// hides of it is dotted through the land): the block a dig or a use would touch, its top and its front down to
// the land before it (on level ground its front is behind that land: its top alone, a tile's top); a side that
// is a bank in view, its edge; the empty cell a piece would stand in, on the surface it will stand on; each step
// of a flight of stairs; in build mode, the cursor's own cell, and when it is up in the air a dotted line down to
// the ground under it and a small square there ("it reads as a shadow, not a cell": it was a dark square and a
// pole). What stands (a tree, a chest, someone) keeps its own selector, round its picture (selector.js).
// It glides from one cell to the next, breathes by a px, fades in and out, and is red when it cannot be done, as
// that selector does.
const Marks = (() => {
  const WHITE = [1, .973, .91], RED = [.91, .376, .31], GREEN = [.6, .9, .55], TALL = 2;      // (TALL: levels a thing that stands takes: a tile)
  let shown = [], at = 0, forced = null;
  const lv = (x, y) => aimLift(x, y) / zoom / RELIEF_STEP;      // the level a tile is aimed at (on a bridge's deck: half a level and a bit)
  // -> the cells of an aim {p, it}: [{x, y, z0, z1, colour}], or none
  function cells(p, it) {
    const out = [], thing = it.ghost && !it.ghostGround && it.ghost !== "seed" && !FILLS[it.ghost], slab = it.ghost === "roof" || it.ghost === "plank";
    for (const [x, y, g, t] of it.steps || []) out.push({x, y, z0: g, z1: t, colour: it.ok === false ? RED : GREEN, fill: 0});      // (stairs: each step's cell, from the ground it stands on to its top, its edges alone: the flight is drawn in it, climbing.js)
    for (const q of it.steps ? [] : it.foot || [p]) {
      const bad = it.ok === false || (it.bad || []).some((b) => b.x === q.x && b.y === q.y), L = Build.on ? Build.level() : null;
      const surf = it.z !== undefined ? it.z : L !== null ? L : lv(q.x, q.y), deck = it.z === undefined && L === null && Models.up(q.x, q.y) > 0;
      const front = deck ? surf - .25 : Math.min(surf - 1, Math.max(lv(q.x, q.y + 1), surf - 12));      // a block's front: down to the land before it
      let z0 = front, z1 = surf, drop, flat = false;
      const side = (dx) => { const n = z1 - Math.max(z0, lv(q.x + dx, q.y)); return n > 0 && z1 === surf && drop === undefined ? Math.min(n, 5) * 2 : 0; };      // (a block of the land with a bank that way: voxpaint.js, 2 px a level, 5 levels)
      if (slab && it.z !== undefined) z0 = surf - 1;                                    // a block built: its own cell
      else if (L !== null && !solidAt(q.x, q.y, surf)) { z0 = surf - 1; drop = settleAt(q.x, q.y, surf - 1); }      // the build cursor in the air: its cell there, and the ground under it
      else if (L !== null && landSolid(q.x, q.y, surf + 1)) z0 = surf - 1;              // ...in the ground: the block it is on
      else if (thing || (it.ghost === "dirt" && it.z === undefined && L === null && !FILLS.dirt[gndAt(q.x, q.y)])) { z0 = surf; z1 = surf + (thing ? TALL : 1); }   // what will stand there, or the ground raised: the cell over the surface
      else if (!deck && lv(q.x, q.y + 1) >= surf) flat = true;                            // level ground, or higher land before it: its front is not seen, its top alone
      out.push({x: q.x, y: q.y, z0, z1, colour: bad ? RED : it.ghost ? GREEN : WHITE, west: side(-1), east: side(1), drop, flat, ...(drop !== undefined ? {fill: .4} : {})});      // (a cell in the air: washed more, its front darker: a box at a glance; it read as a flat square)
    }
    return out;
  }
  // Once a frame (render.js): what is aimed at now, or nothing; `tile`: it is a tile or a block (not something that stands)
  function aim(a, tile, now) {
    // (the mouse over ground you would only walk to, nothing in hand for it: its tile's top all the same, faint: where the pointer is in the land, in a pit, on a hill)
    const walk = !!(a && a.it && a.it.walk && !a.it.ghost && !Build.on), faint = walk && typeof inputMode !== "undefined" && inputMode === "mouse" && mouse.in;
    const dt = Math.min(.1, (now - (at || now)) / 1000), want = forced || (faint ? [{x: a.p.x, y: a.p.y, z0: lv(a.p.x, a.p.y), z1: lv(a.p.x, a.p.y), colour: WHITE, flat: true, fill: 0, most: .4}] : a && a.it && (Build.on || tile || a.it.ghost) && !walk ? cells(a.p, a.it) : []);
    at = now;
    const grow = Math.sin(now / 1000 * 4.5) > .3 ? 1 : 0, k = 1 - Math.exp(-dt * 22);
    if (want.length) {
      const one = want.length === 1 && shown.length === 1 && shown[0].a > .05 && Math.abs(want[0].x - shown[0].x) + Math.abs(want[0].y - shown[0].y) <= 4;
      const a0 = shown.length ? shown[0].a : 0;
      shown = want.map((w) => { const m = {...w, a: Math.min(w.most || 1, a0 + dt * 8), grow, fill: w.fill ?? .16, to: w}; if (one) for (const f of ["x", "y", "z0", "z1"]) m[f] = shown[0][f] + (w[f] - shown[0][f]) * k; return m; });
    } else { for (const m of shown) m.a -= dt * 6; shown = shown.filter((m) => m.a > 0); }
  }
  return {aim, cells, get list() { return shown; }, set force(v) { forced = v; }};
})();
