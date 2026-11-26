// Build mode's cursor height (build.js): the plane E lifted it to, the ground nearest your own, a layer in the ground;
// and the heights Q and E take it to.
//   BuildCursor(S, K) -> {ride, under, level, buried, onIt, key, stops, lift}
const BuildCursor = (S, K) => {
  const {UPMOST, DEEPEST, LOWEST} = K;
  const piece = (...a) => K.piece(...a);   // (another part's, looked up when called: build.js K)
  // The cursor's height: the plane E lifted it to, or the ground at its tile nearest your own height
  const ride = (p) => { if (p.z !== undefined && solidAt(p.x, p.y, p.z)) return p.z; const s = myPos(); return settleNear(p.x, p.y, s ? myZ(s.x, s.y) : topAt(p.x, p.y)); };   // (p.z: the block the pointer is on, mouse.js rayHit: a side of a cliff, a ledge under an overhang)
  const under = (p, t) => (solidAt(p.x, p.y, t) ? t : settleAt(p.x, p.y, t));      // (sunk to t: in the ground there, or on what is under it)
  const level = (p = S.at) => (S.plane !== null ? S.plane : !p ? 0 : S.deep !== null ? under(p, S.deep) : ride(p));
  const buried = (p, L) => landSolid(p.x, p.y, L) && landSolid(p.x, p.y, L + 1);  // (a block in the ground, land over it: X digs it, the one whose top is at L. Not the air under a room's roof)
  const onIt = (p, L) => solidAt(p.x, p.y, L) && !solidAt(p.x, p.y, L + 1);        // the cursor is on something there (not in the air, not inside it)
  const key = (p, z = level(p)) => p.x + "," + p.y + "," + z;
  // E, Q: the cursor to the next height it can be at on its tile, up or down: in the ground a layer at a time, or what
  // is under it (a floor, a cave's floor, a pit's); on the ground; in the air, a storey at a time
  function stops(p) {
    const s = myPos(), me = myZ(s.x, s.y), r = ride(p), out = [];
    for (let t = Math.max(LOWEST, me - DEEPEST); t < r; t++) { const z = under(p, t); if (z < r && out[out.length - 1] !== z) out.push(z); }
    out.push(r);
    const one = LAND_BLOCKS.has(piece());      // (earth, stone in hand: a level a press, the ghost goes up by one block, not a storey: no wall is two high)
    for (let z = r + 1; z <= me + UPMOST; z++) if (landSolid(p.x, p.y, z) || (FLOORS && (one ? z > r + 1 : (z - r) % Floors.STOREY === 0) && !landSolid(p.x, p.y, z + 1))) out.push(z);   // (over it: in the ground a layer at a time, as under it: a tunnel's roof, the block over that; in the air a storey at a time, where there is room over it. Never a storey at a time through the rock: E from a tunnel's floor would go three layers up into it, "going up in tunnel really isn't intuitive")
    return out;
  }
  function lift(d) {
    if (!myPos()) return sfx("buzz");
    const L = level(), all = stops(S.at), to = d < 0 ? all.filter((z) => z < L).pop() : all.find((z) => z > L), r = ride(S.at);
    if (to === undefined) return d > 0 && !FLOORS ? toast("Floors come when this world's server is restarted", true) : sfx("buzz");
    S.plane = to > r ? to : null; S.deep = to < r ? to : null;
    sfx("pick");
  }
  return {ride, under, level, buried, onIt, key, stops, lift};
};
