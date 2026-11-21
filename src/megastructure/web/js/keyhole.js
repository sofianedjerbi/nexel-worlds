// What is under the build cursor where the ground hides it (build.js): its own tile, and nothing else, is seen
// through, a keyhole. Down in a hole the grass in front of it is drawn over its floor; in the ground (Q), or under a
// cave's roof, the earth is over it. There its column is drawn as if cut open in front: the wall behind, a band a
// layer as relief.js paints walls, from the top of the hole down to the floor the cursor is at, dug earth as deep as
// it is (tiles.js: dugSheet). In the ground: the block the cursor is on and no more (what X would dig: its top,
// faint: not dug yet; under a roof, the room that is dug, its floor and its wall), the land over it left as it is (it
// was the whole column from the top of the land: a strip seventeen layers high under a mountain). Nothing where the
// place you are in is seen through already (xray.js). The cursor over
// it, and beside the cursor how far it is over your head or under your feet, in layers; level with you, nothing is
// written: the layer of you it is level with is marked on you (mark). (A floor drawn alone, three layers down, showed a
// tile and a half south of its hole, on the grass.) The user's pick of five, 2026-11-16, "1 · Earth and a keyhole":
// the x-ray circle that went round the cursor showed the grass round the hole too, and the cursor seemed on it.
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
    const X = Math.round(sx(p.x)), Y = Math.round(bodyY(p, sy)) + (16 - RELIEF_STEP * n) * z, S = TS(), H = RELIEF_STEP * z;
    marks = {n, x: X - 3 * z, y: Y, h: H, drawn: !HdLook.on};
    if (HdLook.on) return;      // (the HD look: the cursor is a box in the land at its level, target.js; brackets round your own cat were a fourth mark for two cells)
    for (const [col, g] of [["#5b3f36", z], ["#fff1a8", 0]]) {
      ctx.fillStyle = col;
      for (const [bx, d] of [[X - 3 * z, 1], [X + S + 2 * z, -1]]) {
        ctx.fillRect(bx - g, Y - g, z + 2 * g, H + 2 * g);
        ctx.fillRect(Math.min(bx, bx + d * 2 * z) - g, Y - g, 3 * z + 2 * g, z + 2 * g); ctx.fillRect(Math.min(bx, bx + d * 2 * z) - g, Y + H - z - g, 3 * z + 2 * g, z + 2 * g);
      }
    }
  }
  return {tag, rel, mark, get marks() { return marks; }};
})();
