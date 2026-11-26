// Nyxwing's pictures, made once in whole art px (nyxwing.js): a cell of its sheet, the speck it is far off, its shadow,
// the eclipse it comes out of, the marker where it will fall.
//   NyxArt(K) -> {canvas, cell, speck, oval, eclipse, marker}
const NyxArt = (K) => {
  // ---- pictures made once, in whole art px
  const made = new Map();
  const canvas = (k, w, h, paint) => { if (!made.has(k)) { const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d"); g.imageSmoothingEnabled = false; paint(g); made.set(k, c); } return made.get(k); };
  const cell = (col, row) => canvas(`c${col},${row}`, WILD.nyxwing.cw, WILD.nyxwing.ch, (g) => g.drawImage(IMG.nyxwing, col * WILD.nyxwing.cw, row * WILD.nyxwing.ch, WILD.nyxwing.cw, WILD.nyxwing.ch, 0, 0, WILD.nyxwing.cw, WILD.nyxwing.ch));
  // far off: its picture made smaller by whole px (each n x n block one px, the colour most of it has: ui.js smallArt),
  // and darker with the distance (the night between)
  const speck = (col, n) => canvas(`s${col},${n}`, Math.ceil(WILD.nyxwing.cw / n), Math.ceil(WILD.nyxwing.ch / n), (g) => {
    const A = WILD.nyxwing, im = smallArt(IMG.nyxwing, col * A.cw, 0, A.cw, A.ch, Math.ceil(A.cw / n)), d = im.data, dark = {1: 0, 2: .3, 3: .55, 4: .8}[n];
    for (let o = 0; o < d.length; o += 4) for (let k = 0; k < 3; k++) d[o + k] = Math.round(d[o + k] * (1 - dark) + [10, 6, 28][k] * dark);
    g.putImageData(im, 0, 0);
  });
  const oval = (w, h, col) => canvas(`o${w},${h},${col}`, w, h, (g) => {     // a shadow on the ground: the game's soft purple
    g.fillStyle = col;
    for (let j = 0; j < h; j++) { const k = Math.sqrt(1 - ((j + .5 - h / 2) / (h / 2)) ** 2), half = Math.round(w / 2 * k); g.fillRect(w / 2 - half, j, 2 * half, 1); }
  });
  const eclipse = (r) => canvas(`e${r}`, 2 * r + 25, 2 * r + 25, (g) => {   // a dark moon over a gold sun, its corona
    const c = r + 12;
    for (let j = 0; j < 2 * c + 1; j++) for (let i = 0; i < 2 * c + 1; i++) {
      const d = Math.hypot(i - c, j - c), h = (i * 7 + j * 13) % 9;
      const col = d <= r - 1 ? "#05030a" : d <= r + .5 ? "#ffffff" : d <= r + 2 ? "#ffcf5a" : d <= r + 11 && h < 4 - (d - r) / 3 ? "#ffe08a" : null;
      if (col) { g.fillStyle = col; g.fillRect(i, j, 1, 1); }
    }
  });
  const marker = (r, locked) => canvas(`m${r}${locked}`, 2 * r + 3, r + 3, (g) => {    // where it will fall: a ring closing on you
    for (let a = 0; a < 48; a++) { if (a % 4 === 3) continue; const t = a / 48 * Math.PI * 2; g.fillStyle = locked ? "#e8484f" : a % 2 ? "#ffffff" : "#ffcf5a";
      g.fillRect(Math.round(r + 1 + Math.cos(t) * r), Math.round(r / 2 + 1 + Math.sin(t) * r / 2), 2, 1); }
  });
  return {canvas, cell, speck, oval, eclipse, marker};
};
