// Digging up: the way out of a hole ("how do i climb up? why i cant??": in a pocket under their own stair, a pickaxe
// in hand, Space dug level, X dug down, and nothing dug upward; a ladder had no head room).
// A step up needs two cells gone: the one over your own head (room to jump) and the one in front of you at your
// head's height (room to land); the block under that one is the step. R (the settings' "Dig up") takes them in
// that order, one a press, then you jump up (J): a stair out of any hole, a layer each time. The server's rule:
// sim/underground.py dig_over, and `dig` with a height. Offered where it is the way out: a pickaxe in hand, facing
// a wall of land you cannot hop onto, in a hole or under the land (at a hill's foot Space cuts into the hill).
// The cell it will take is marked as the block it is, at its own height (mark.js).
// While the way out is shown (wayshow.js) the key on its next block breaks THAT block (`route`), whatever you hold
// and whichever way you face: "Grey boxes. No key works" with a plank in hand, or nothing. The pickaxe is used if
// you carry one anywhere (the server asks only that you have it); with none it is dug by hand, three times as long
// (the server always allowed it). So nobody who is shut in is left without a key that does something.
const DigUp = (() => {
  // -> the cell R would dig right now {x, y, z, text}, or null
  function aim() {
    const s = typeof myPos === "function" ? myPos() : null, q = s && facingTile(), w = s && WayShow.offer(), way = !!w;
    if (w && w.key === "up") { const n = WayShow.cur.now; return {x: n.x, y: n.y, z: n.z, text: w.text, way}; }      // (the way out is shown and its next block is R's: that one, whichever way you face)
    if (!q || !meObs || Build.on || toolKind(inHand()) !== "pickaxe") return null;
    const h = myZ(s.x, s.y), roof = solidAt(s.x, s.y, h + 2), wall = solidAt(q.x, q.y, h + 2);
    if (!landSolid(q.x, q.y, h + 1) || (!roof && !wall)) return null;            // (no wall; or one you hop onto as it is)
    if (!(topAt(s.x, s.y) > h || inHole(s, q, h))) return null;
    if (roof) return landSolid(s.x, s.y, h + 2) ? {x: s.x, y: s.y, z: h + 2, text: "Dig up", way} : null;       // (a floor somebody built over you: build mode's X takes it)
    return landSolid(q.x, q.y, h + 2) ? {x: q.x, y: q.y, z: h + 2, text: "Dig a step", way} : null;      // (way: the way out is shown: its marks alone, mark.js)
  }
  // One dig at a time, the block named by its own place. (It was named by `actTarget`, read by act() after its wait for
  // the server to come to where you stopped: a second press during that wait sent a second dig with no place, which
  // took the first one's turn: in the river at a cliff's foot, where the server is slow to come, Space dug nothing.)
  let going = false;
  const send = (tool, args) => { going = true; act(tool, args).finally(() => { going = false; }); };
  // The way's next block, by its key ("up" R; "alt" X: dig on, or dig down where you stand) -> true: the press was the way's (done, or waiting for your hands)
  function route(key) {
    const c = WayShow.cur, n = c && c.now;
    if (!n || n.key !== key || Build.on || !meObs) return false;
    if (walking || myAction || pendingAct || going) return true;
    const tool = bestTool("pickaxe") ? {with: bestTool("pickaxe")} : {};
    if (n.d) turn(n.d);
    send(n.down ? "dig_down" : "dig", n.down ? tool : {x: n.x, y: n.y, z: n.z, ...tool});
    return true;
  }
  function run() {
    if (route("up")) return;
    const c = aim();
    if (!c || walking || myAction || pendingAct || going) return;
    WayShow.mine(); send("dig", {x: c.x, y: c.y, z: c.z, with: bestTool("pickaxe") || "pickaxe"});
  }
  return {aim, run, route};
})();
