// THE VIEW: where a place of the world is on the screen, in ONE place. The HD look fills it once a frame (hd.js after):
//   View.at(x, y, z) -> [px, py], CSS px, as its camera has the place (tiles, levels), or null: nothing shown yet
//   View.u: CSS px an art px of the land (state.js artPx); View.snap(v): v on the land's pixel
//   View.of(q) -> a drawn body's own place, on the land's pixel, as its picture stands this frame (falling: with its
//     body), or null: not drawn. What is written over a body (its name, its bubble, an emote, a bar, a number) asks
//     this, by the body itself. (They asked "whose column is this x, whose row this y" of the frame's list: two bodies
//     in one row at two heights shared a height; a body the list had not: 16 x zoom px a tile where a tile is
//     16 x artPx.)
//   View.set(at, list): the frame's camera (art px) and what it drew
const View = (() => {
  let cam = null, list = [];
  const at = (x, y, z) => { const a = cam && cam(x, y, z), u = artPx(); return a ? [a[0] * u, a[1] * u] : null; }, snap = onArt;   // (state.js: the land's pixel, the one rounding to it)
  function of(q) { const s = list.find((c) => c.q === q), a = s && at(s.x, s.y, s.z); return a ? [snap(a[0]), snap(a[1]) + (s.fo || 0) * artPx()] : null; }
  return {at, snap, of, set(c, l) { cam = c; list = l; }, get u() { return artPx(); }};
})();
