// Tilled soil. The pack's sheet is a patch with a line round it, drawn 10 px inside its outer tiles: made to lie on
// grass, with nothing planted on its rim. Here every tilled tile is planted, and at sea level it lies on bare soil
// of the patch's own colour: all that showed of the patch was its line, a rounded box floating inside the field
// with a row of crops outside it. Tilled soil is furrows now, over the whole of each tile: a darker line every
// 4 px, the light of the ridge under it, both broken here and there as a hoe leaves them, in the sheet's own two
// tones, and running on from tile to tile (four tiles by four before they come round).
// (Up on a hill the ground under is the hill's grass, and there the patch is the pack's own look: tiles.js keeps it.)
const Furrows = (() => {
  const N = 4, T = 16, SPAN = N * T;
  let sheet = null, seed = 11;
  const dice = (n) => (seed = (Math.imul(seed, 1103515245) + 12345) >>> 0, Math.floor(seed / 65536) % n);      // (its own: the same field on every machine)
  function make() {
    const c = document.createElement("canvas"); c.width = c.height = SPAN;
    const g = c.getContext("2d"), m = sheetData(IMG.tilled), tans = new Set();
    for (const v of m.px) if (v >>> 24 === 255 && (v & 255) > 200) tans.add(v & 0xffffff);                     // the sheet's soil tones (not its grass)
    const tone = [...tans].sort((a, b) => (a & 255) - (b & 255)).map((v) => `rgb(${v & 255},${v >> 8 & 255},${v >> 16 & 255})`);
    const line = (y, colour, on, off) => {            // a row of dashes: `on` px drawn (and up to as many again), `off` left
      g.fillStyle = colour;
      for (let x = dice(on); x < SPAN;) { const w = on + dice(on); g.fillRect(x, y, Math.min(w, SPAN - x), 1); x += w + off + dice(off); }
    };
    for (let y = 0; y < SPAN; y += 4) { line(y + 3, tone[0], 5, 1); line(y, tone[tone.length - 1], 3, 3); }
    return c;
  }
  return {cell: (x, y) => [sheet || (sheet = make()), (x & N - 1) * T, (y & N - 1) * T]};
})();
