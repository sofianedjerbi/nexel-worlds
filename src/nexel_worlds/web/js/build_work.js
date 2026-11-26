// Build mode's work (build.js): the nearest plan, a place to stand beside it, and whether you can still walk away from it.
//   BuildWork(S, K) -> {work, nearest, solid, wayOut}
const BuildWork = (S, K) => {
  const BLOCK = (...a) => K.BLOCK(...a), build = (...a) => K.build(...a), key = (...a) => K.key(...a), landFits = (...a) => K.landFits(...a), now = (...a) => K.now(...a), open = (...a) => K.open(...a);   // (another part's, looked up when called: build.js K)
  // The work: the nearest plan, a place to stand beside it, the piece put (or the thing taken down); then the next
  async function work() {
    if (S.working) return; S.working = true;
    try {
      for (let j; me && S.on && (j = nearest());) {
        j.state = "doing";
        const why = await build(j);
        if (!why) S.plans.delete(key(j, j.z));
        else if (!S.on) j.state = "todo";                                     // (you left the mode and walked off: it waits)
        else if (!j.tried) { j.tried = true; j.state = "todo"; }             // once more, after the others: what was in the way may be gone
        else { j.state = "bad"; j.why = why; j.t = now(); toast(why, true); }
      }
    } finally { S.working = false; }
  }
  function nearest() {
    const s = myPos(); if (!s) return null;
    // (what you can walk on first, a floor, a door: then what closes the way, the nearest first; a block that
    // nothing holds yet, or a thing whose floor is not laid yet, after what is to hold it)
    const wait = (j) => (j.dig ? S.plans.has(j.x + "," + j.y + "," + (j.z + 1)) || (j.tunnel && !open(j.x, j.y, j.z)) : !j.take && j.up && (LAND_BLOCKS.has(j.item) ? !!landFits(j.x, j.y, j.z, () => false) : BLOCK(j.item) ? !!Floors.fits(j.x, j.y, j.z) : !Floors.get(j.x, j.y, j.z)));
    const far = (j) => (j.tried ? 1000 : 0) + (wait(j) ? 5000 : 0) + (solid(j) ? 500 : 0) + Math.abs(j.x - s.x) + Math.abs(j.y - s.y) + Math.abs(j.z - myZ(s.x, s.y));
    return [...S.plans.values()].filter((j) => j.state === "todo").sort((a, b) => far(a) - far(b))[0];
  }
  const solid = (j) => !j.take && !j.up && SOLID.has(PLACEABLE_BLOCK[j.item] || ".");      // (what shuts the way on the ground)
  // From q, with every solid plan built: can you still walk away (ten tiles off)? Not from inside the walls you plan
  function wayOut(q, j) {
    const flat = (c) => c.x + "," + c.y, shut = new Set([...S.plans.values()].filter(solid).map(flat)), seen = new Set([flat(q)]), line = [q];
    for (let i = 0; i < line.length && i < 400; i++) {
      const c = line[i];
      if (Math.max(Math.abs(c.x - j.x), Math.abs(c.y - j.y)) >= 10) return true;
      for (const [dx, dy] of Object.values(DIRV)) { const n = {x: c.x + dx, y: c.y + dy}, k = flat(n); if (!seen.has(k) && !shut.has(k) && stand(n.x, n.y)) { seen.add(k); line.push(n); } }
    }
    return false;
  }
  return {work, nearest, solid, wayOut};
};
