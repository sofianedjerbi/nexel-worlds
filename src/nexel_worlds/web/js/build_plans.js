// Build mode's plans (build.js): what is planned where, what a block of the land needs to go in a cell, what X would take,
// a plan made, taken back, dropped.
//   BuildPlans(S, K) -> {digs, open, BLOCK, planned, landFits, piece, todo, taking, plan, take, drop}
const BuildPlans = (S, K) => {
  const buried = (...a) => K.buried(...a), key = (...a) => K.key(...a), level = (...a) => K.level(...a), onIt = (...a) => K.onIt(...a), hint = (...a) => K.hint(...a), work = (...a) => K.work(...a);   // (another part's, looked up when called: build.js K)
  const digs = (x, y, z) => { const j = S.plans.get(x + "," + y + "," + z); return !!j && !!j.dig && j.state !== "bad"; }, open = (x, y, z, soon) => landSolid(x, y, z) && [[0, 0, 1], [0, 0, -1], ...Object.values(DIRV).map(([dx, dy]) => [dx, dy, 0])].some(([dx, dy, dz]) => !solidAt(x + dx, y + dy, z + dz) || (soon && digs(x + dx, y + dy, z + dz)));   // (air beside it: it can be dug, sim/underground.py; soon: or will be, once what is planned beside it is dug)
  const BLOCK = (it) => it === "roof" || it === "plank";
  const planned = (x, y, z) => { const j = S.plans.get(x + "," + y + "," + z); return !!j && !j.take && j.up && (BLOCK(j.item) || LAND_BLOCKS.has(j.item)) && j.state !== "bad"; };     // a block that is only planned yet
  // A block of the land (earth, stone) for the cell (x, y, z): why it cannot go there, or nothing (as the server's put_land: empty, something solid beside it; or a block planned there)
  const landFits = (x, y, z, soon = planned) => { const s = myPos(); return solidAt(x, y, z) ? "taken" : s && s.x === x && s.y === y && z > myZ(x, y) && z <= myZ(x, y) + 2 ? "you_there"
    : ((N) => N.some(([i, j, k]) => solidAt(x + i, y + j, z + k) || soon(x + i, y + j, z + k)) && N.some(([i, j, k]) => !solidAt(x + i, y + j, z + k)))([[0, 0, -1], [0, 0, 1], ...Object.values(DIRV).map(([dx, dy]) => [dx, dy, 0])]) ? "" : "unheld"; };   // (held: something beside it, or planned there; reached: air beside it)     // (a few words: the ghost says it, red where it cannot go: buildghost.js, not a red line across the screen)
  const piece = () => (selected && meObs && meObs.self.inventory[selected] && placeable(selected) ? selected : null);
  const todo = () => [...S.plans.values()].filter((j) => j.state !== "bad");
  // What X would take at p -> {z, what: its name, plan: the plan there}, or nothing. Where the piece in hand would
  // go first (a roof selected: the roof over the cursor), then what stands at the cursor's level, then the block it
  // is on, then what was laid in the ground; and, the cursor riding the ground with nothing there to take, the
  // lowest block over it (the roof over a room)
  function taking(p) {
    const t = tile(p.x, p.y), L = level(p), on = onIt(p, L), h = piece() ? hint(p) : {};
    const zs = [...new Set([selected === "roof" && on ? L + Floors.STOREY : undefined, h.z !== undefined && planned(p.x, p.y, h.z - 1) ? h.z - 1 : undefined, h.z, L].filter((z) => z !== undefined))];
    for (const z of zs) { const j = S.plans.get(key(p, z)); if (j) return j.state === "doing" ? null : {z, what: "plan", plan: j}; }
    if (!t) return null;
    if (buried(p, L)) return {z: L, what: "ground", dig: true, tunnel: true, shut: !open(p.x, p.y, L, true)};   // (a block in the ground: air beside it, or a hole planned there?)
    const built = (z) => { const c = FLOORS || z !== L ? Floors.get(p.x, p.y, z) : null; return c ? {z, what: c[1] ? label(CH[c[1]]) : c[0] === "roof" ? "roof" : c[0] === "stairs" ? "the step" : "planks", up: true} : null; };
    for (const z of zs) if (built(z)) return built(z);
    if (on && L === groundAt(p.x, p.y)) {               // on the land: whatever stands there; what is laid in it; else the ground itself
      if (!GROUND.has(t[0])) { const c = "Zz".includes(t[0]) ? (structAt(p.x, p.y) || {c: t[0]}).c : t[0]; return {z: L, what: label(CH[c]), verb: Object.values(PLACEABLE_BLOCK).includes(c) ? "" : (HARVEST[c] || "").replace(/ \(.*$/, "")}; }   // (what grows: its own verb)
      if ("_n:".includes(t[1])) return {z: L, what: label(CH[t[1]])};
      if (!wet(t[1]) && L > LOW) return {z: L, what: "ground", dig: true};
    }
    if (on && landSolid(p.x, p.y, L) && L > LOW) return {z: L, what: "ground", dig: true};      // (a tunnel's floor)
    for (let z = L + 1; S.plane === null && z <= L + 3 * Floors.STOREY; z++) if (built(z)) return built(z);
    return null;
  }
  function plan(p) {
    const it = hint(p), z = it.z !== undefined ? it.z : level(p), q = it.at || p;
    if (it.far) return;                               // (out of reach yet: its box is dotted; nothing is said)
    if (!it.ghost || it.ok === false) return S.hold ? null : toast(it.text, true);
    if (BLOCK(selected) && S.hold && S.row !== undefined && S.row !== z) return;     // (a row of blocks is at one height: over a floor already laid it does not pile them up)
    S.row = z; S.plans.set(key(q, z), {x: q.x, y: q.y, z, item: selected, up: it.z !== undefined && !it.draw, ground: it.ghostGround || null, swap: !!it.swap, steps: it.steps || null, state: "todo"});
    sfx("pick"); work();
  }
  function take(p) {                                  // a plan back; or, of what is built there, a plan to take it down
    const hit = taking(p);
    if (!hit) return S.hold ? null : toast("Nothing built there", true);
    if (hit.plan) { S.plans.delete(key(p, hit.z)); return; }
    if (hit.shut) return;                             // (out of reach yet: its box is dotted, target.js; nothing is said: the owner wanted it "clear to the user without adding a ... hint")
    S.plans.set(key(p, hit.z), {x: p.x, y: p.y, z: hit.z, take: true, up: !!hit.up, dig: !!hit.dig, tunnel: !!hit.tunnel, state: "todo"});   // (tunnel: a block in the ground, dug from beside it: what is over it stays)
    sfx("pick"); work();
  }
  function drop() { const n = todo().length; for (const [k, j] of S.plans) if (j.state !== "doing") S.plans.delete(k); toast(`${n} plans dropped`); }
  return {digs, open, BLOCK, planned, landFits, piece, todo, taking, plan, take, drop};
};
