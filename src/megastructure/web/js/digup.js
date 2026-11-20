// Digging up: the way out of a hole ("how do i climb up? why i cant??": in a pocket under their own stair, a pickaxe
// in hand, Space dug level, X dug down, and nothing dug upward; a ladder had no head room).
// A step up needs two cells gone: the one over your own head (room to jump) and the one in front of you at your
// head's height (room to land); the block under that one is the step. R (the settings' "Dig up") takes them in
// that order, one a press, then you walk up: a stair out of any hole, a layer each time. The server's rule:
// sim/underground.py dig_over, and `dig` with a height. Offered where it is the way out: a pickaxe in hand, facing
// a wall of land you cannot hop onto, in a hole or under the land (at a hill's foot Space cuts into the hill).
// The cell it will take is marked as the block it is, at its own height (mark.js).
const DigUp = (() => {
  // -> the cell R would dig right now {x, y, z, text}, or null
  function aim() {
    const s = typeof myPos === "function" ? myPos() : null, w = s && WayShow.want(), q = w ? w.q : s && facingTile();   // (the way out is shown and its next block is R's: that one, whichever way you face: wayshow.js)
    if (!q || !meObs || Build.on || inHand() !== "pickaxe") return null;
    const h = myZ(s.x, s.y), roof = solidAt(s.x, s.y, h + 2), wall = solidAt(q.x, q.y, h + 2);
    if (!landSolid(q.x, q.y, h + 1) || (!roof && !wall)) return null;            // (no wall; or one you hop onto as it is)
    if (!(topAt(s.x, s.y) > h || inHole(s, q, h))) return null;
    if (roof) return landSolid(s.x, s.y, h + 2) ? {x: s.x, y: s.y, z: h + 2, text: "Dig up"} : null;       // (a floor somebody built over you: build mode's X takes it)
    return landSolid(q.x, q.y, h + 2) ? {x: q.x, y: q.y, z: h + 2, text: "Dig a step"} : null;
  }
  function run() {
    const c = aim();
    if (!c || walking || myAction || pendingAct) return;
    const w = WayShow.want(); if (w) turn(w.d);
    actTarget = {x: c.x, y: c.y};
    act("dig", {dir: "N", z: c.z, with: "pickaxe"});
  }
  return {aim, run};
})();
