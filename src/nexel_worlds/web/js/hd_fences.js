// The HD look's fences and gates (hd_things.js): a post and its rails, a gate's leaf along a run north-south.
//   HdFences(S, T) (S: HdSheet; T: {UP, cast, doorOpen}) -> {fence, sideGate}
const HdFences = (S, T) => {
  const {pix, solid, cut, side, push, flat} = S, {UP, cast, doorOpen} = T;
  // ---- fences: a post, its rails east and west as the sprite has them (upright), its rails north and south as thin boxes of the rail's own colour
  function fence(out, x, y, base) {
    const spr = fenceSprite(x, y), P = pix(spr[0], spr[1], spr[2], 16, 16), dy = spr[6], f = (dx, ddy) => "#+g".includes(combAt(x + dx, y + ddy) || "-");
    const rail = P.px[8 * 16 + 7] || P.px[6 * 16 + 7], dark = P.px[12 * 16 + 5] || rail, Y1 = 12;
    // (a run north-south: a post on every other tile, the rails through between them: a post is 12 px high and a tile 9 px deep on the screen, a post a tile was one mush of posts)
    const run = f(0, -1) && f(0, 1) && !f(-1, 0) && !f(1, 0) && combAt(x, y) === "#", post = !run || !(y & 1), L = base / UP, sun = (r, h0, h1) => cast(out, x, y, L, r, h0, h1), FK = UP / 12;   // (FK: px of land a row of the post's 12: a post is a block high)
    if (post) { sun([4, Y1 - 5, 12, Y1 + 1], 0, UP); push(out, {x: 5, y: Y1 - 4, z: base, w: 6, d: 4, h: UP, fh: 12, top: cut(P, 5, 11, 2, 6), front: cut(P, 5, 11, 2, 14), west: side(P, 5, 11, 2, 14, 4, 0), east: side(P, 5, 11, 2, 14, 4, 1)}); }
    for (const [on, c0, c1] of [[f(-1, 0), 0, 5], [f(1, 0), 11, 16]]) if (on) { for (const rz of [3, 8]) sun([c0, Y1 - 3, c1, Y1 - 1], rz * FK, (rz + 2) * FK); push(out, {x: c0, y: Y1 - 3, z: base, w: c1 - c0, d: 2, h: UP, fh: 12, top: null, front: cut(P, c0, c1, 2, 14)}); }
    for (const [on, y0, y1] of post ? [[f(0, -1), 0, Y1 - 4], [f(0, 1), Y1, 16]] : [[true, 0, 16]]) if (on) for (const rz of [3, 8]) { sun([6, y0, 10, y1], rz * FK, (rz + 2) * FK);
      push(out, {x: 6, y: y0, z: base + rz * FK, w: 3, d: y1 - y0, h: 2 * FK, fh: 2, top: flat(rail, 3, y1 - y0, dark, "we"), west: flat(dark, Math.min(16, y1 - y0), 2, dark), east: flat(dark, Math.min(16, y1 - y0), 2, dark)}); }   // (a rail from above: its two edges dark, so it reads between the posts)
  }
  // a gate in a run north-south: its leaf along the run, a thin box as high as the posts beside it (open: none); the posts are the fences' own
  function sideGate(out, x, y, base) {
    if (doorOpen(x, y)) return; const P = pix(IMG.gates, 0, 0, 16, 16), lum = (v) => (v & 255) + (v >> 8 & 255) + (v >> 16 & 255); let wood = 0, dark = 0;
    for (let i = 0; i < 256; i++) { const v = P.px[i]; if (!solid(v)) continue; if (!wood || lum(v) > lum(wood)) wood = v; if (!dark || lum(v) < lum(dark)) dark = v; }      // (the gate's own lightest wood and its line)
    push(out, {x: 6, y: -4, z: base + 2 * UP / 12, w: 4, d: 24, h: 9 * UP / 12, fh: 9, top: flat(wood, 4, 24, dark, "wens"), front: flat(wood, 4, 9, dark, "wens"), west: flat(wood, 24, 9, dark, "ns"), east: flat(wood, 24, 9, dark, "ns")});
  }
  return {fence, sideGate};
};
