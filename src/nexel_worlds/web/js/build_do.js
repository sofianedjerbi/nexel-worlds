// Build mode's one plan done (build.js): walk to it, put the piece or take the thing down; why it could not be.
//   BuildDo(S, K) -> {build}
const BuildDo = (S, K) => {
  const key = (...a) => K.key(...a), open = (...a) => K.open(...a), solid = (...a) => K.solid(...a), swaps = (...a) => K.swaps(...a), wayOut = (...a) => K.wayOut(...a);   // (another part's, looked up when called: build.js K)
  async function build(j) {                           // -> why it could not be done (nothing: it is done)
    if (!j.take && !(meObs.self.inventory[j.item] > 0)) return `No ${label(j.item)} left`;
    const at = myPos(); if (j.dig && !j.up && at && at.x === j.x && at.y === j.y && myZ(at.x, at.y) === j.z) { const r = await act("dig_down", bestTool("pickaxe") ? {with: bestTool("pickaxe")} : {}, true); return r && r.ok ? null : (r && errorText(r)) || "It could not be done"; }   // (the block you stand on: from on it, you come down with it)
    for (let i = 0; j.tunnel && !j.tried && i < 24 && !open(j.x, j.y, j.z); i++) await new Promise((done) => setTimeout(done, 25));   // (the hole dug before it may be on your screen a moment after it is dug)
    if (j.tunnel && !open(j.x, j.y, j.z)) return "It could not be reached";     // (what was to open it is gone: it could not be done)
    const here = () => { const s = myPos(); return {...s, z: myZ(s.x, s.y)}; };
    // from (q, h): within the game's reach of it, height counted; and not where it goes (a block in your body, a wall on your feet)
    const ok = (q, h) => (q.x - j.x) ** 2 + (q.y - j.y) ** 2 + ((j.z - h) * RULES.layer) ** 2 <= (reach("use") + .5) ** 2
      && !(q.x === j.x && q.y === j.y && (j.up ? j.z - h >= 0 && j.z - h <= 2 : true))
      && !(j.steps || []).some(([x, y]) => x === q.x && y === q.y)             // (not where a flight of stairs goes)
      && (!j.tunnel || (Math.abs(q.x - j.x) + Math.abs(q.y - j.y) === 1 && j.z >= h && j.z <= h + 2));      // (a tunnel: from beside it, feet to head)
    if (!ok(here(), here().z) || (solid(j) && !wayOut(here(), j))) {
      const s = here(), spots = [];                    // (beside it for choice, on your own floor for choice)
      for (let R = reach("use"), dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) for (const h of surfacesAt(j.x + dx, j.y + dy)) {
        const q = {x: j.x + dx, y: j.y + dy, z: h, far: Math.abs(dx) + Math.abs(dy) > 1 ? 3 : 0};
        if (stand(q.x, q.y, h) && ok(q, h) && !entityAt(q)) spots.push(q);
      }
      const cost = (q) => (solid(j) && !wayOut(q, j) ? 200 : 0) + ([...S.plans.values()].some((o) => o.x === q.x && o.y === q.y) ? 60 : 0) + q.far + Math.abs(q.z - s.z) * 2 + Math.abs(q.x - s.x) + Math.abs(q.y - s.y);     // (not walled in, for choice)
      spots.sort((a, b) => cost(a) - cost(b));
      let there = false;
      for (const q of spots.slice(0, 6)) {
        const r = await act("move_to", {x: q.x, y: q.y, ...(FLOORS ? {z: q.z} : {})}, true);
        // (the walk is over on the server a moment before your screen has you there: wait for it)
        for (let i = 0; r && r.ok && i < 40 && !(myPos().x === q.x && myPos().y === q.y); i++) await new Promise((done) => setTimeout(done, 25));
        if (r && r.ok && ok(here(), here().z)) { there = true; break; }
        if (!S.plans.has(key(j, j.z))) return null;
      }
      if (!there) return "No way to get near it";
    }
    if (!S.plans.has(key(j, j.z))) return null;       // (taken back meanwhile)
    const was = Floors.thingAt(j.x, j.y, j.z), inv = meObs.self.inventory;
    const tool = j.dig ? bestTool("pickaxe") : (j.take || j.swap) && TOOL_FOR[was] ? bestTool(TOOL_FOR[was]) || (inv[TOOL_FOR[was]] ? TOOL_FOR[was] : null) : null;   // (a hole: your best pickaxe if you have one; a thing: your best tool of its kind, vocab.js)
    const went = (r) => (r && r.ok ? null : (r && errorText(r)) || "It could not be done");
    const z = FLOORS || j.dig ? {z: j.z} : {}, dig = () => { actTarget = {x: j.x, y: j.y}; return act(FLOORS || !j.up ? "dig" : "unroof", {dir: "N", ...z, ...(tool ? {with: tool} : {})}, true); };
    if (j.swap && swaps(j.item, was)) {        // what is in its place comes down first (and back into your pack)
      const why = went(await dig());
      if (why) return why;
    }
    if (j.take) return went(await dig());
    actTarget = {x: j.x, y: j.y};
    return went(await act("place", {dir: "N", item: j.item, ...z}, true));
  }

  return {build};
};
