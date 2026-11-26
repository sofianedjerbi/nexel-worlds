// Nyxwing's death (nyxwing.js): a cry, its body shaking and flashing, its pixels going up into an eclipse.
//   NyxDeath(K) -> {dying, died}
const NyxDeath = (K) => {
  const {BEAT, HIT, canvas, cell, later, say, seen, st} = K;
  // its death: a cry, two beats of its body shaking and flashing, then its pixels leave it, edges first, and go up into
  // an eclipse that opens over it; the sky closes when the last is home. (Its Eclipse Core falls as any drop does: loot.js)
  const dying = new Map();
  function died(e) {
    const s = st(e.id), L = s.last, A = WILD.nyxwing;
    say("drake_death", e);
    later(6 * BEAT - HIT.drake_dissolve, () => say("drake_dissolve", e));
    later(6 * BEAT, () => say("drake_vanish", e));
    seen.delete(e.id);
    if (!L || !IMG.nyxwing) return;
    const body = cell(L.col, L.row), c = document.createElement("canvas"); c.width = A.cw; c.height = A.ch;
    const g = c.getContext("2d", {willReadFrequently: true}); g.drawImage(body, 0, 0);
    const white = canvas(`w${L.col},${L.row}`, A.cw, A.ch, (w) => { w.drawImage(body, 0, 0); w.globalCompositeOperation = "source-atop"; w.fillStyle = "#fff8e8"; w.fillRect(0, 0, A.cw, A.ch); });
    const d = g.getImageData(0, 0, A.cw, A.ch).data, left = [];
    for (let j = 0; j < A.ch; j += 2) for (let i = 0; i < A.cw; i += 2) {
      const k = (j * A.cw + i) * 4;
      if (d[k + 3] < 200) continue;                                          // (not its ground shadow)
      const far = Math.min(1, Math.hypot((i - A.cw / 2) / (A.cw / 2), (j - A.ch * .55) / (A.ch / 2)));
      left.push({i, j, c: `rgb(${d[k]},${d[k + 1]},${d[k + 2]})`, rel: 2 + 2.2 * (1 - far) + Math.random() * .2});
    }
    left.sort((a, b) => b.rel - a.rel);                                      // (the soonest last: popped first)
    dying.set(e.id, {at: performance.now(), x: L.x, y: L.y, body, white, canvas: c, g, left});
  }
  return {dying, died};
};
