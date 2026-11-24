// The cobbled ground. The pack's sheet holds a strip three tiles long each way, a square of four and one tile on
// its own: no turn, no crossing, nothing wider. Tiles were picked from it at random, and every tile cut its
// neighbour's stones at the edge.
// So the stones are laid again here, the pack's own (its three widths, its two greys, its little shadow under
// each), in rows as a paver lays them: one row flush with the tile, the next half a stone along, each stone a px
// or two off its place, over four tiles by four before the ground comes round.
// A stone of the half-along rows lies across two tiles. Each tile paints its part of it when both are cobbled (on
// the same level: a step up moves the ground); where the cobbles end the stone is pulled inside, the one beside it
// making room, and left out if there is none. No stone is ever cut.
// Sixteen tiles, each in four ways (cobbled to its west or not, to its east or not): one small sheet, made once.
const Pave = (() => {
  const N = 4, SLOT = 8, T = 16, SPAN = N * T;       // tiles before it comes round; a stone's place, in px; a tile
  let sheet = null, seed = 20;
  const dice = (n) => (seed = (Math.imul(seed, 1103515245) + 12345) >>> 0, Math.floor(seed / 65536) % n);      // (its own: the same ground on every machine)
  // Every stone of the ground, a row after the other, eight to a row: [x, y, w, h], in px
  function stones() {
    const out = [];
    for (let r = 0; r < SPAN / SLOT; r++) for (let c = 0; c < SPAN / SLOT; c++) {
      const w = [5, 6, 6, 7, 7][dice(5)], h = [5, 6, 6][dice(3)];
      out.push([c * SLOT + (r & 1 ? SLOT / 2 : 0) + dice(SLOT - w), r * SLOT + dice(SLOT - h), w, h]);         // (a px is always left to the next)
    }
    return out;
  }
  function stone(g, x, y, w, h, light, dark) {
    g.fillStyle = light; g.fillRect(x + 1, y, w - 2, 1); g.fillRect(x, y + 1, w, h - 3); g.fillRect(x + 1, y + h - 2, w - 2, 1);
    g.fillStyle = dark; g.fillRect(x, y + h - 2, 1, 1); g.fillRect(x + w - 1, y + h - 2, 1, 1); g.fillRect(x + 1, y + h - 1, w - 2, 1);
  }
  function make() {
    const c = document.createElement("canvas"); c.width = SPAN * 4; c.height = SPAN;
    const g = c.getContext("2d"), px = sheetData(IMG.cobble), css = (v) => `rgb(${v & 255},${v >> 8 & 255},${v >> 16 & 255})`;
    const light = css(px.px[6 * px.w + 3]), dark = css(px.px[9 * px.w + 3]), all = stones(), per = SPAN / SLOT;   // (the pack's two greys, off its sheet)
    for (let m = 0; m < 4; m++) for (let ty = 0; ty < N; ty++) for (let tx = 0; tx < N; tx++) {
      // a tile's stones, in its own px: its flush row's two, and of its half-along row the one inside it (b), the
      // one that comes in from the west (a) and the one that goes out to the east (c)
      const at = (r, k) => { const [x, y, w, h] = all[r * per + (tx * 2 + k + per) % per]; return [(x - tx * T + SPAN + T) % SPAN - T, y - ty * T, w, h]; };
      const laid = [at(ty * 2, 0), at(ty * 2, 1)], [a, b, c2] = [-1, 0, 1].map((k) => at(ty * 2 + 1, k));
      if (m & 1) laid.push(a);                         // cobbled to the west: our part of it
      if (m & 2) laid.push(b, c2);                     // and to the east
      else {                                           // not: it is pulled inside, the one beside it making room if it can
        const cx = T - c2[2], bx = Math.min(b[0], cx - 1 - b[2]);
        if (bx >= (m & 1 ? a[0] + a[2] + 1 : 0)) laid.push([bx, b[1], b[2], b[3]], [cx, c2[1], c2[2], c2[3]]); else laid.push(b);
      }
      g.save(); g.beginPath(); g.rect((m * N + tx) * T, ty * T, T, T); g.clip();
      for (const [lx, ly, w, h] of laid) stone(g, (m * N + tx) * T + lx, ty * T + ly, w, h, light, dark);
      g.restore();
    }
    return c;
  }
  // The cell of the sheet for the cobbled tile (x, y): [sheet, sx, sy]
  function cell(x, y) {
    const lv = levelAt(x, y), m = maskOf(x, y, (_, g, tx, ty) => g === "_" && levelAt(tx, ty) === lv);   // (the one mask rule, tiles.js: which tiles round it are of this ground; its stones cross only west and east)
    return [sheet || (sheet = make()), (((m & W_ ? 1 : 0) + (m & E_ ? 2 : 0)) * N + (x & N - 1)) * T, (y & N - 1) * T];
  }
  return {cell};
})();
