// The build cursor beside you (build.js): how far it is over your head or under your feet, in layers, a tag at its
// side (hd.js writes it with the cursor's keys); level with you, nothing is written. (Its cell is a box in the land:
// target.js.)
const Keyhole = (() => {
  let marks = null;                                   // (the mark on you, where it is: tests)
  // how far the cursor is under you (or over you), in layers: a tag at its left (its keys are at its right: prompts.js)
  function tag(x, y, S, n, right) {                   // (right: at the cursor's right, with its E and Q: you stand at its left, prompts.js)
    const text = (n > 0 ? "+" : "") + n;
    ctx.font = "18px SproutPixel"; ctx.textAlign = "left";
    const w = Math.ceil(ctx.measureText(text).width) + 10, X = Math.round(right ? x + TS() + 3 * zoom + 2 : x - 3 * zoom - w - 2), Y = Math.round(y + S / 2 - 10);
    ctx.fillStyle = "#5b3f36"; ctx.fillRect(X - 2, Y - 2, w + 4, 24);
    ctx.fillStyle = "#7a5646"; ctx.fillRect(X, Y, w, 20);
    ctx.fillStyle = "#fff6e2"; ctx.fillText(text, X + 5, Y + 16);
  }
  // What is written of a cursor n layers over the floor you stand on: under it, how far; over it, how far over your
  // head: the block in front of your legs (1) and of your eyes (2) are level with you, nothing is written ("+1 mean
  // whaT ? +1 above player ?": it was the block in front of his legs). A storey up is +1: the floor over your head
  const rel = (n) => (n > 0 ? Math.max(0, n - 2) : n);
  // ...and on you, where the cursor is on a block near your height (in the ground; on it, over your floor): the layer
  // of you it is level with, between two marks (your legs, your head; over your head, under your feet), in its light
  function mark(x, y, h, n, cube, sx, sy, right) {
    if (rel(n)) tag(x, y, h, rel(n), right);
    const p = ents.get("agent" + myId), z = zoom;
    marks = null;
    if (!p || n > 4 || n < (cube ? -1 : 1)) return;
    const X = Math.round(bodyX(p, sx)), Y = Math.round(bodyY(p, sy)) + (16 - RELIEF_STEP * n) * z, H = RELIEF_STEP * z;
    marks = {n, x: X - 3 * z, y: Y, h: H, drawn: false};      // (no brackets on you: the cursor is a box in the land at its level, target.js)
  }
  return {tag, rel, mark, get marks() { return marks; }};
})();
