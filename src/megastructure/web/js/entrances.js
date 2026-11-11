// A hole's tunnels, seen from above (the design's cave entrances): where the floor below a hole goes on under solid
// ground, the way shows on the hole: toward the back an opening, dark, at the hole's far side; to the sides and the
// front the floor running on under the ground's edge into its shade. The level below is asked for if it isn't here.

const OPEN_BELOW = (x, y) => { const t = tile(x, y); return !!t && t[1] === "-" && t[0] !== "R" && t[0] !== "*"; };
function drawEntrances(g, x, y, ox, oy) {
  const bx = x + LAYER;
  if (!tile(bx, y)) {
    const k = bkey(Math.floor(bx / B), Math.floor(y / B));
    if (!(requested.get(k) > performance.now() - 3000)) { requested.set(k, performance.now()); sendSpec({op: "region", x: Math.floor(bx / B) * B, y: Math.floor(y / B) * B, w: B, h: B}); }
    return;
  }
  const way = (dx, dy) => OPEN_BELOW(bx + dx, y + dy) && combAt(x + dx, y + dy) !== "O";
  if (way(0, -1)) {                                   // the back: the foot of the opening in the wall (its top: below)
    g.fillStyle = "#504086"; g.fillRect(ox + 1, oy, 14, 4);
    g.fillStyle = "#342628"; g.fillRect(ox + 2, oy, 12, 2);
    g.fillStyle = "#62483c"; g.fillRect(ox + 2, oy + 2, 12, 2);
  }
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, 1]]) {   // the sides and the front: the floor goes on into the shade
    if (!way(dx, dy)) continue;
    for (let c = 0; c < 8; c++) {
      const a = Math.round((1 - c / 8) ** 1.4 * .75 * 4) / 4;
      if (!a) continue;
      g.fillStyle = `rgba(34,25,30,${a})`;
      for (let r = 1; r < 15; r++) {
        const dr = Math.max(0, 5 - r, r - 10), dc = Math.max(0, c - 3);
        if (dr * dr + dc * dc > 16) continue;
        if (dx) g.fillRect(ox + (dx < 0 ? c : 15 - c), oy + r, 1, 1); else g.fillRect(ox + r, oy + 15 - c, 1, 1);
      }
    }
  }
}

// On the tile behind a hole (its wall): the top of the opening, cut through the cliff face, if a tunnel goes on north
// from the hole below. Its corners rounded, the pack's ink round it.
function drawOpeningTop(g, x, y, ox, oy) {
  if (combAt(x, y + 1) !== "O" || combAt(x, y) === "O" || !OPEN_BELOW(x + LAYER, y) || !OPEN_BELOW(x + LAYER, y + 1)) return;
  g.fillStyle = "#504086"; g.fillRect(ox + 3, oy + 6, 10, 10); g.fillRect(ox + 2, oy + 7, 12, 9); g.fillRect(ox + 1, oy + 9, 14, 7);
  g.fillStyle = "#342628"; g.fillRect(ox + 4, oy + 7, 8, 9); g.fillRect(ox + 3, oy + 8, 10, 8); g.fillRect(ox + 2, oy + 10, 12, 6);
}
