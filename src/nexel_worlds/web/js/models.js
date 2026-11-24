// Models: what stands in the land as a solid thing of a few boxes (a bridge's deck and posts: bridge_model.js),
// the game's side. The engine draws them with the blocks (vox_models.js says what a box is); here is the one
// sheet their paint is in, and the list of the kinds of thing that are models. A kind is {start(), at(x, y), up(x, y)}:
// start paints its pieces into the sheet (once, before the first model is asked for), at gives the boxes of a
// tile (or null), up how many art px over its ground something on that tile stands (a deck is over the water).
const Models = (() => {
  const SIDE = 128, kinds = [];
  let cv = null, g = null, nx = 0, ny = 0, tall = 0;
  function sheet() {
    if (cv) return cv;
    cv = document.createElement("canvas"); cv.width = cv.height = SIDE; g = cv.getContext("2d");
    for (const k of kinds) k.start();
    return cv;
  }
  // room for w x h px in the sheet, painted by draw(g, u, v) -> [u, v]
  function room(w, h, draw) {
    if (nx + w > SIDE) { nx = 0; ny += tall; tall = 0; }
    const at = [nx, ny]; draw(g, nx, ny); nx += w; tall = Math.max(tall, h);
    return at;
  }
  // ...painted from rows of letters, a px a letter: pal says each letter's colour ("." or one not in it: nothing)
  const rows = (list, pal) => room(list[0].length, list.length, (q, u, v) => list.forEach((row, j) => [...row].forEach((ch, i) => { if (pal[ch]) { q.fillStyle = pal[ch]; q.fillRect(u + i, v + j, 1, 1); } })));
  function at(x, y) {
    sheet();
    let out = null;
    for (const k of kinds) { const l = k.at(x, y); if (l) out = out ? out.concat(l) : l; }
    return out;
  }
  const up = (x, y) => { let n = 0; for (const k of kinds) n = Math.max(n, k.up(x, y)); return n; };
  return {add: (k) => kinds.push(k), room, rows, at, up, sheet};
})();
