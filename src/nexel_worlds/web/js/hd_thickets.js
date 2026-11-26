// The HD look's thickets (hd_things.js): a thicket is boxes in the land ("thicket are ugly", #277: it was the hedge
// painted flat on the grass, a wall with no height), painted px for px from the pack's bush sheet (hedge.png: its
// 3 x 3 hedge, rows 0-47; its lone bush, rows 48-63 at column 48). An overgrown hedge, picked 2026-11-26:
//   a dark foot (the hedge's darkest rows), set in two px where no thicket is beside it, on under a run of them;
//   a canopy of leaves over it, its top the hedge's middle with the hedge's outline along each open edge, its
//   front and sides the hedge's own lip, lit to dark; and on most crowns a lump of the lone bush's leaves.
//   (P: art px a tile, art.js; Hg: the hedge's px, 64 x 64; B: the lone bush's, a tile)
//   HdThickets(S, T) (S: HdSheet; T: {UP, cast}) -> {thicket(out, x, y, base)}
const HdThickets = (S, T) => {
  const {pix, cut, side, push, room} = S, {UP, cast} = T, FOOT = 5, CAN = 9;
  const is = (x, y) => combAt(x, y) === "H";
  // the canopy's top: the hedge's middle cell, its outline (and the dark px in from it) along each edge with no thicket past it
  const top = (Hg, x, y) => { const n = !is(x, y - 1), s = !is(x, y + 1), w = !is(x - 1, y), e = !is(x + 1, y), line = Hg.px[9], ink = Hg.px[64 + 9];
    return room(Hg.key + "t" + [n, s, w, e], P, P, (put) => { for (let j = 0; j < P; j++) for (let i = 0; i < P; i++) {
      const edge = (n && j === 0) || (s && j === 15) || (w && i === 0) || (e && i === 15);
      put(i, j, edge ? line : (n && j === 1) || (w && i === 1) ? ink : Hg.px[(P + j) * 64 + P + i]); } }); };
  function thicket(out, x, y, base) {
    const Hg = pix(IMG.hedge, 0, 0, 64, 64), B = pix(IMG.hedge, 48, 48, P, P), r = (k) => hash(x, y, 70 + k);
    const x0 = is(x - 1, y) ? 0 : 2, x1 = is(x + 1, y) ? P : 14, y0 = is(x, y - 1) ? 0 : 2, y1 = is(x, y + 1) ? P : 14;
    cast(out, x, y, base / UP, [0, 0, P, P], 0, FOOT + CAN);
    push(out, {x: x0, y: y0, z: base, w: x1 - x0, d: y1 - y0, h: FOOT, fh: FOOT, top: null, front: cut(Hg, P + x0, P + x1, 42, 47), west: side(Hg, 0, P, 42, 47, y1 - y0, 0), east: side(Hg, 32, 48, 42, 47, y1 - y0, 1)});
    push(out, {x: 0, y: 0, z: base + FOOT, w: P, d: P, h: CAN, fh: CAN, top: top(Hg, x, y), front: cut(Hg, P, 32, 48 - CAN, 48), west: side(Hg, 0, P, 48 - CAN, 48, P, 0), east: side(Hg, 32, 48, 48 - CAN, 48, P, 1)});
    if (r(0) < .7) { const bx = 2 + (r(1) * 7 | 0), by = 2 + (r(2) * 6 | 0);
      push(out, {x: bx, y: by, z: base + FOOT + CAN, w: 7, d: 6, h: 3, fh: 3, top: cut(B, 4, 11, 3, 9), front: cut(B, 4, 11, 11, 14), west: side(B, 0, 8, 11, 14, 6, 0), east: side(B, 8, P, 11, 14, 6, 1)}); }
  }
  return {thicket};
};
