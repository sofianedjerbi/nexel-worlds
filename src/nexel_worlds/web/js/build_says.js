// Build mode's word on the cursor (build.js): what Space would plan there, the game's own answer, in a few words.
//   BuildSays(S, K) -> {hint, says}
const BuildSays = (S, K) => {
  const BLOCK = (...a) => K.BLOCK(...a), key = (...a) => K.key(...a), landFits = (...a) => K.landFits(...a), level = (...a) => K.level(...a), onIt = (...a) => K.onIt(...a), piece = (...a) => K.piece(...a), planned = (...a) => K.planned(...a), swaps = (...a) => K.swaps(...a), todo = (...a) => K.todo(...a);   // (another part's, looked up when called: build.js K)
  // What planning the piece in hand at p would be: the game's own answer for that tile (intent.js), as a ghost,
  // said in a few words (they are written beside the bar: a long line ran under it). Where nothing holds it (nothing beside
  // it, built or planned; stairs with nothing higher beside them): far, its box dotted (target.js), nothing said, Space does
  // nothing: the dotted box means one thing, out of reach yet, as for X (the owner: "show, don't tell"; it said in red "Nothing holds it")
  function hint(p) { const h = says(p); return h.ok === false && Floors.UNHELD.has(h.why) ? {...h, text: "", far: true} : h; }
  function says(p) {
    const it = piece();
    if (!it) return {text: selected ? "Pick a block to place" : "Pick a piece", key: "1-9", ok: selected ? undefined : false};      // (a pickaxe in hand: you came to break. It said "Not a building piece" in red, the cursor red)
    if (FOOT[PLACEABLE_BLOCK[it]]) return {text: "Put by hand: leave with B", ok: false, ghost: it};
    const have = meObs.self.inventory[it], used = todo().filter((j) => j.item === it).length, t = tile(p.x, p.y);
    const L = level(p), on = onIt(p, L), c = FLOORS ? Floors.get(p.x, p.y, L) : null, what = Floors.thingAt(p.x, p.y, L);
    if (used >= have) return {text: `All ${have} are planned`, ok: false, ghost: it};
    if (it === "stairs" || it === "ladder") {          // (a flight, a ladder: as they will be, climbing.js)
      if (S.plans.has(key(p, L))) return {text: "Planned", ok: false, ghost: it};
      const say = Climb.intent(p, false) || {text: "Nothing can go there", ok: false};
      return {...say, z: say.ok === false && Floors.UNHELD.has(say.why) ? L + 1 : L};      // (nothing to lean on: the cell its first step would fill, dotted)
    }
    if (LAND_BLOCKS.has(it) && FLOORS) {              // earth, stone: the cell on top of what the cursor is on; the cursor in the air: the cell it is in ("why cant i place block in that mode also ??")
      const F = p.side && p.side !== "T" ? DIRV[p.side] : null, q = F ? {x: p.x + F[0], y: p.y + F[1]} : p, at = F ? {at: q} : {};    // (the mouse on a block's side: the cell beside that face, Minecraft's way, mouse.js rayHit; keys: the cell on the cursor)
      const z = S.hold === " " && S.row !== undefined ? S.row : BuildGhost.cell(q, F ? p.cz ?? L : p.side ? (p.cz ?? L) + 1 : on ? L + 1 : L, planned), why = landFits(q.x, q.y, z);     // (on the one you planned there: the next one on top, no height key. A row, Space held: at the height of its first, so a roof is a row begun on a wall's top)
      return why ? Floors.no(why, {ghost: it, z, ...at}) : {text: `Place ${label(it)}`, ok: true, ghost: it, z, ...at};
    }
    if (BLOCK(it) && (FLOORS || it === "roof") && !(it === "plank" && on && !c && t && FILLS.plank[t[1]] && GROUND.has(t[0]))) {     // a block, for a cell
      const z = !on ? L : it === "roof" ? L + Floors.STOREY : L + 1, why = S.plans.has(key(p, z)) ? "planned" : Floors.fits(p.x, p.y, z, planned);
      return why ? Floors.no(why, {ghost: it, z}) : {text: `Place ${label(it)}${on && it === "plank" ? " on top" : ""}`, ok: true, ghost: it, z};
    }
    if (S.plans.has(key(p, L))) return {text: "Planned", ok: false, ghost: it};
    if (!on) return {text: solidAt(p.x, p.y, L) ? "Nothing can go there" : "No floor there: lay one", ok: false, ghost: it, z: L};
    if (swaps(it, what)) return {text: `Place ${label(it)} in its place`, ok: true, ghost: it, swap: true, ...(c ? {z: L} : {})};
    if (c) return what ? {text: "Something is there", ok: false, ghost: it, z: L} : tileOf(PLACEABLE_BLOCK[it]).upstairs ? {text: `Place ${label(it)}`, ok: true, ghost: it, z: L} : {text: "It needs the ground", ok: false, ghost: it, z: L};
    const say = intent(p, false) || {text: "Nothing can go there", ok: false};
    return {...say, text: say.ok === false ? say.text.replace(/^Can't place .* here$/, "Can't go there") : say.text};
  }
  return {hint, says};
};
