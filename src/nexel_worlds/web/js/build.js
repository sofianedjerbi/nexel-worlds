// Building, as a plan and then the work. Placing was one tile at a time, the one you faced: to raise a wall you
// walked a step, turned, pressed, and again, and walled yourself in. Now you plan first and your character builds:
//   Z          build mode, and out of it (by place: W on an AZERTY; B too, its first key: "'b' key is a bad choice. switching takes time from
//              WASD": Z is under A, the hand stays; every other key round WASD was taken, and a held Ctrl or Alt is
//              the browser's: Ctrl W shuts the page). What is in your hand is the piece: the bar's numbers.
//   arrows     move the cursor, a tile at a time (it is not you who walks: the view goes with the cursor)
//   Space      plan the piece here. Held while you move: a row. A door on a wall, a gate on a fence: in its place
//   X          break what is at the cursor: a plan back; a thing, a tree, a rock, a wall, a step, a floor: down; bare
//              ground: a hole, a layer deeper each time (a pickaxe digs faster); in the ground: that block. Held: a row
//   Q E        the cursor a layer down, and up (also PgDn, PgUp); Q by place: the key over A (A on an AZERTY)
//   Esc        drop every plan (with none: out of the mode)
// The cursor has a height. It starts on the block in front of you, at your own height ("show the most pertinent block first: in front of the player, direction where he's facing at his exact level"): a wall there, the block in front of your eyes ("default block to dig should be the one at player eye-level": it was the one in front of your legs; that one gone, of your legs); else the ground there (it rode the top of the land over the wall, a mountain's seventeen
// layers up, and Q brought it down a layer a press). It rides the ground nearest your own (the floor you stand on); E lifts it a storey, into the air over a room or onto the floor above, and there it stays as it moves, until Q brings it down. Below your
// own floor Q sinks it to what is under it: the floor under yours (the ground floor from upstairs), a cave's floor,
// or, in the ground, a layer at a time: there it is on a block, and X digs that block and no other, where air is beside it; what is over it stays ("like minecraft ... this enforce me to dig huge columns": it dug the whole column over it; then the room to stand in, two blocks at once from the lower one: "why am i unable to break block at my eye level ? why do i
// need to target the one down to dig both at once ?"). Blocks are planned as far ahead as you like: each where the one before it will have made room (it was refused until that one was dug). The block you stand on is dug from on it: you come down with it ("i should be able to break this block by putting myself in top of it then digging under my
// feets"). How deep is written beside it. (Q, E: after R F and Shift ↑ ↓, "not natural".) What you plan
// goes where the cursor is: a thing (a wall, a door, a bed) on what the cursor is on; a block (planks, a roof) on
// top of it, or, the cursor in the air, in the cell it is in, where a wall under it or a block beside it holds it.
// Planks on bare ground are a floor laid in it, as ever; a roof goes a storey over what the cursor is on (over your
// head, not at your feet), so a house is roofed without a key more. All that is over the cursor's level is faint.
// Every plan is a ghost on the ground. In build mode your character goes to the nearest, stands within reach of it
// and builds it (the game's own moves: walk there, place; the server checks each as it always did), then the next,
// block by block. Out of the mode it is yours to walk again, and the plans wait where they are till you come back.
// A plan that cannot be done (no way there, someone standing on it) turns red, says why, and goes.
// By mouse, in build mode: the cursor is where you point, a click plans, a drag plans a row, shift or the right
// button takes. The whole of it by keys alone. A piece bigger than a tile (a well, a coop) is still put by hand.
const Build = (() => {
  const REACH = 10, FIRST_MS = 230, STEP_MS = 75, BAD_MS = 2600;   // how far from you the cursor goes; a held arrow: its wait, then its pace; how long a failed plan shows
  const SWAP = {door: ["wood_wall", "stone_wall"], gate: ["fence"]};   // a piece that goes in the place of another: a door in a wall, a gate in a fence
  const swaps = (it, c) => !!SWAP[it] && SWAP[it].some((n) => CHAR[n] === c);
  const S = {on: false, at: null, plane: null, deep: null, plans: new Map(), hold: null, working: false, dir: null, timer: 0, pan: {x: 0, y: 0}};
  const now = () => performance.now(), UPMOST = 9, DEEPEST = 12, LOWEST = LOW;   // (how far over your own height the cursor goes: three floors; under it, layers; the deepest ground there is: the top of the bottom cell, sim/underground.py)
  // The cursor's height: the plane it was lifted to, or the ground at its tile nearest your own height
  const ride = (p) => { if (p.z !== undefined && solidAt(p.x, p.y, p.z)) return p.z; const s = myPos(); return settleNear(p.x, p.y, s ? myZ(s.x, s.y) : topAt(p.x, p.y)); };   // (p.z: the block the pointer is on, mouse.js rayHit: a side of a cliff, a ledge under an overhang)
  const under = (p, t) => (solidAt(p.x, p.y, t) ? t : settleAt(p.x, p.y, t));      // (sunk to t: in the ground there, or on what is under it)
  const level = (p = S.at) => (S.plane !== null ? S.plane : !p ? 0 : S.deep !== null ? under(p, S.deep) : ride(p));
  const buried = (p, L) => landSolid(p.x, p.y, L) && landSolid(p.x, p.y, L + 1);  // (a block in the ground, land over it: X digs it, the one whose top is at L. Not the air under a room's roof)
  const digs = (x, y, z) => { const j = S.plans.get(x + "," + y + "," + z); return !!j && !!j.dig && j.state !== "bad"; }, open = (x, y, z, soon) => landSolid(x, y, z) && [[0, 0, 1], [0, 0, -1], ...Object.values(DIRV).map(([dx, dy]) => [dx, dy, 0])].some(([dx, dy, dz]) => !solidAt(x + dx, y + dy, z + dz) || (soon && digs(x + dx, y + dy, z + dz)));   // (air beside it: it can be dug, sim/underground.py; soon: or will be, once what is planned beside it is dug)
  const onIt = (p, L) => solidAt(p.x, p.y, L) && !solidAt(p.x, p.y, L + 1);        // the cursor is on something there (not in the air, not inside it)
  const key = (p, z = level(p)) => p.x + "," + p.y + "," + z;
  const BLOCK = (it) => it === "roof" || it === "plank";
  const planned = (x, y, z) => { const j = S.plans.get(x + "," + y + "," + z); return !!j && !j.take && j.up && (BLOCK(j.item) || LAND_BLOCKS.has(j.item)) && j.state !== "bad"; };     // a block that is only planned yet
  // A block of the land (earth, stone) for the cell (x, y, z): why it cannot go there, or nothing (as the server's put_land: empty, something solid beside it; or a block planned there)
  const landFits = (x, y, z, soon = planned) => { const s = myPos(); return solidAt(x, y, z) ? "Something is there" : s && s.x === x && s.y === y && z > myZ(x, y) && z <= myZ(x, y) + 2 ? "You stand there"
    : ((N) => N.some(([i, j, k]) => solidAt(x + i, y + j, z + k) || soon(x + i, y + j, z + k)) && N.some(([i, j, k]) => !solidAt(x + i, y + j, z + k)))([[0, 0, -1], [0, 0, 1], ...Object.values(DIRV).map(([dx, dy]) => [dx, dy, 0])]) ? "" : "Nothing holds it"; };   // (held: something beside it, or planned there; reached: air beside it)     // (a few words: the ghost says it, red where it cannot go: buildghost.js. It was a red line across the screen: "Nothing holds it: put it against a block")
  const piece = () => (selected && meObs && meObs.self.inventory[selected] && placeable(selected) ? selected : null);
  const todo = () => [...S.plans.values()].filter((j) => j.state !== "bad");

  // What planning the piece in hand at p would be: the game's own answer for that tile (intent.js), as a ghost,
  // said in a few words (they are written beside the bar: a long line ran under it). Where nothing holds it (nothing beside
  // it, built or planned; stairs with nothing higher beside them): far, its box dotted (target.js), nothing said, Space does
  // nothing: the dotted box means one thing, out of reach yet, as for X (the owner: "show, don't tell"; it said in red "Nothing holds it")
  const UNHELD = new Set(["Nothing holds it", "Needs a wall under it", "Stairs go up to something higher beside them", "Needs something taller behind"]);
  function hint(p) { const h = says(p); return h.ok === false && UNHELD.has(h.text) ? {...h, text: "", far: true} : h; }
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
      return {...say, z: say.ok === false && UNHELD.has(say.text) ? L + 1 : L};      // (nothing to lean on: the cell its first step would fill, dotted)
    }
    if (LAND_BLOCKS.has(it) && FLOORS) {              // earth, stone: the cell on top of what the cursor is on; the cursor in the air: the cell it is in ("why cant i place block in that mode also ??")
      const F = p.side && p.side !== "T" ? DIRV[p.side] : null, q = F ? {x: p.x + F[0], y: p.y + F[1]} : p, at = F ? {at: q} : {};    // (the mouse on a block's side: the cell beside that face, Minecraft's way, mouse.js rayHit; keys: the cell on the cursor)
      const z = S.hold === " " && S.row !== undefined ? S.row : BuildGhost.cell(q, F ? p.cz ?? L : p.side ? (p.cz ?? L) + 1 : on ? L + 1 : L, planned), why = landFits(q.x, q.y, z);     // (on the one you planned there: the next one on top, no height key. A row, Space held: at the height of its first, so a roof is a row begun on a wall's top)
      return why ? {text: why, ok: false, ghost: it, z, ...at} : {text: `Place ${label(it)}`, ok: true, ghost: it, z, ...at};
    }
    if (BLOCK(it) && (FLOORS || it === "roof") && !(it === "plank" && on && !c && t && FILLS.plank[t[1]] && GROUND.has(t[0]))) {     // a block, for a cell
      const z = !on ? L : it === "roof" ? L + Floors.STOREY : L + 1, why = S.plans.has(key(p, z)) ? "Planned" : Floors.fits(p.x, p.y, z, planned);
      return why ? {text: why, ok: false, ghost: it, z} : {text: `Place ${label(it)}${on && it === "plank" ? " on top" : ""}`, ok: true, ghost: it, z};
    }
    if (S.plans.has(key(p, L))) return {text: "Planned", ok: false, ghost: it};
    if (!on) return {text: solidAt(p.x, p.y, L) ? "Nothing can go there" : "No floor there: lay one", ok: false, ghost: it, z: L};
    if (swaps(it, what)) return {text: `Place ${label(it)} in its place`, ok: true, ghost: it, swap: true, ...(c ? {z: L} : {})};
    if (c) return what ? {text: "Something is there", ok: false, ghost: it, z: L} : tileOf(PLACEABLE_BLOCK[it]).upstairs ? {text: `Place ${label(it)}`, ok: true, ghost: it, z: L} : {text: "It needs the ground", ok: false, ghost: it, z: L};
    const say = intent(p, false) || {text: "Nothing can go there", ok: false};
    return {...say, text: say.ok === false ? say.text.replace(/^Can't place .* here$/, "Can't go there") : say.text};
  }
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
  async function build(j) {                           // -> why it could not be done (nothing: it is done)
    if (!j.take && !(meObs.self.inventory[j.item] > 0)) return `No ${label(j.item)} left`;
    const at = myPos(); if (j.dig && !j.up && at && at.x === j.x && at.y === j.y && myZ(at.x, at.y) === j.z) { const r = await act("dig_down", bestTool("pickaxe") ? {with: bestTool("pickaxe")} : {}, true); return r && r.ok ? null : (r && (r.detail || r.error)) || "It could not be done"; }   // (the block you stand on: from on it, you come down with it)
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
    const went = (r) => (r && r.ok ? null : (r && (r.detail || r.error)) || "It could not be done");
    const z = FLOORS || j.dig ? {z: j.z} : {}, dig = () => { actTarget = {x: j.x, y: j.y}; return act(FLOORS || !j.up ? "dig" : "unroof", {dir: "N", ...z, ...(tool ? {with: tool} : {})}, true); };
    if (j.swap && swaps(j.item, was)) {        // what is in its place comes down first (and back into your pack)
      const why = went(await dig());
      if (why) return why;
    }
    if (j.take) return went(await dig());
    actTarget = {x: j.x, y: j.y};
    return went(await act("place", {dir: "N", item: j.item, ...z}, true));
  }

  function toggle(on = !S.on) {
    if (on === S.on || (on && !me)) return;
    S.on = on; S.hold = null; S.plane = null; S.deep = null; held(null); document.body.classList.toggle("building", on);
    if (on) { S.at = facingTile() || myPos(); const s = myPos(), z = s ? myZ(s.x, s.y) : 0, c = s ? [z + 2, z + 1].find((t) => landSolid(S.at.x, S.at.y, t)) : undefined, r = ride(S.at); if (c < r) S.deep = c; else if (c > r) S.plane = c; work(); }   // (in front of you, at your own height: see above; its keys are by the cursor: prompts.js)
    else { S.pan = {x: 0, y: 0}; if (todo().length && !TOUCH) toast(`${todo().length} plans wait: ${capOf("build")} to go on building`); }      // (a phone has no B: its Build button stays up while plans wait, touch.js; the plans stay where they are)
  }
  function drop() { const n = todo().length; for (const [k, j] of S.plans) if (j.state !== "doing") S.plans.delete(k); toast(`${n} plans dropped`); }
  function move(dir) {
    const s = myPos(), [dx, dy] = DIRV[dir], x = S.at.x + dx, y = S.at.y + dy;
    if (!s || !tile(x, y) || Math.max(Math.abs(x - s.x), Math.abs(y - s.y)) > REACH) { sfx("buzz"); return false; }      // (as far as it goes: said, not silent)
    S.at = {x, y};
    if (S.hold === " ") plan(S.at); else if (S.hold === "x") take(S.at);
    return true;
  }
  // An arrow held: a step at once, then, after a short wait, at the cursor's own pace (not the keyboard's repeat,
  // which starts late and differs from one machine to the next)
  function held(dir) {
    clearTimeout(S.timer); S.dir = dir;
    if (!dir) return;
    move(dir);
    const again = () => { if (S.on && S.dir === dir && move(dir)) S.timer = setTimeout(again, STEP_MS); };
    S.timer = setTimeout(again, FIRST_MS);
  }
  // E, Q: the cursor to the next height it can be at on its tile, up or down: in the ground a layer at a time, or what
  // is under it (a floor, a cave's floor, a pit's); on the ground; in the air, a storey at a time
  function stops(p) {
    const s = myPos(), me = myZ(s.x, s.y), r = ride(p), out = [];
    for (let t = Math.max(LOWEST, me - DEEPEST); t < r; t++) { const z = under(p, t); if (z < r && out[out.length - 1] !== z) out.push(z); }
    out.push(r);
    const one = LAND_BLOCKS.has(piece());      // (earth, stone in hand: a level a press, the ghost goes up by one block. It went a storey: "E jumped to +2", no wall two high)
    for (let z = r + 1; z <= me + UPMOST; z++) if (landSolid(p.x, p.y, z) || (FLOORS && (one ? z > r + 1 : (z - r) % Floors.STOREY === 0) && !landSolid(p.x, p.y, z + 1))) out.push(z);   // (over it: in the ground a layer at a time, as under it: a tunnel's roof, the block over that; in the air a storey at a time, where there is room over it. It was a storey at a time through the rock: E from a tunnel's floor went three layers up into it, "going up in tunnel really isn't intuitive")
    return out;
  }
  function lift(d) {
    if (!myPos()) return sfx("buzz");
    const L = level(), all = stops(S.at), to = d < 0 ? all.filter((z) => z < L).pop() : all.find((z) => z > L), r = ride(S.at);
    if (to === undefined) return d > 0 && !FLOORS ? toast("Floors come when this world's server is restarted", true) : sfx("buzz");
    S.plane = to > r ? to : null; S.deep = to < r ? to : null;
    sfx("pick");
  }
  // A key in build mode -> true: it was the mode's (the rest, the bar's numbers among them, go on as ever)
  function onKey(k, e) {
    if (!S.on) return false;
    if (k === "b" || k === keyOf("build")) { if (!e.repeat) toggle(false); return true; }
    if (k === "escape") { if (!e.repeat) { if (todo().length) drop(); else toggle(false); } return true; }
    if (KEYDIR[k]) { if (!e.repeat) held(KEYDIR[k]); return true; }
    if (k === " " || k === "x") { if (!e.repeat) { S.hold = k; S.row = undefined; if (k === " ") plan(S.at); else take(S.at); } return true; }
    if (k === "e" || k === "keyq" || k === "q" || k === "pageup" || k === "pagedown") { if (!e.repeat) lift(k === "e" || k === "pageup" ? 1 : -1); return true; }
    return false;
  }
  addEventListener("keyup", (e) => { const k = keyId(e); if (k === S.hold) S.hold = null; if (KEYDIR[k] === S.dir) held(null); });
  addEventListener("blur", () => { S.hold = null; held(null); });
  function point(p) { if (S.on && tile(p.x, p.y)) { S.at = {x: p.x, y: p.y}; if (p.z !== undefined && p.z !== ride(S.at)) S.at.z = p.z; if (p.side) Object.assign(S.at, {side: p.side, cz: p.cz}); } }      // (the mouse: the cursor is where it points, the block under it (z, when not the ground nearest you there: it follows the land as it is dug and built), or at the cursor's height: mouse.js)
  function click(p, alt) { point(p); S.row = undefined; if (alt) take(S.at); else plan(S.at); }

  // Once a frame (render.js): a plan that could not be done is shown red a while, then goes; out of the mode when you are gone.
  // (What is planned, and the cursor, are drawn by the HD look in the land: hd.js written, pieces; target.js)
  function tick() {
    for (const [k, j] of S.plans) if (j.state === "bad" && now() - j.t > BAD_MS) S.plans.delete(k);
    if (S.on && !me) { S.plans.clear(); toggle(false); }                    // (you fell, or the game went: out of the mode)
  }
  // The view, in build mode: half way from you to the cursor, eased (both stay on the screen)
  function pan(dt) {
    const s = myPos(), to = S.on && S.at && s ? {x: (S.at.x - s.x) / 2, y: (S.at.y - s.y) / 2} : {x: 0, y: 0}, k = Math.min(1, dt * 6);
    S.pan.x += (to.x - S.pan.x) * k; S.pan.y += (to.y - S.pan.y) * k;
    return S.pan;
  }
  // What the keys do just now, for the corner of the screen (keyboard.js): the mode's name first, then each key
  // that does something here, in a few words
  const LAYER_CAP = () => keyCap("keyq") + " E";      // (the key over A, as this keyboard types it, and E)
  function rows() {
    const it = hint(S.at), n = todo().length, hit = taking(S.at), s = myPos(), up = s ? Keyhole.rel(level() - myZ(s.x, s.y)) : 0, sign = (v) => (v > 0 ? "+" : "") + v;
    const out = [[capOf("build"), up ? `BUILD · ${sign(up)} · leave` : "BUILD MODE · leave", "head"]];
    if (!it.far) out.push([it.key || "Space", it.text, it.ok === false && !it.key ? "bad" : ""]);
    out.push([LAYER_CAP(), "A layer down, up"]);
    if (hit && !hit.shut) out.push(["X", hit.plan ? "Take the plan back" : hit.dig ? "Break" : hit.verb || `Break ${hit.what}`]);   // (out of reach yet: no row, its box is dotted)
    if (n) out.push(["Esc", `Drop the ${n} plan${n > 1 ? "s" : ""}`]);
    return out;
  }
  const waiting = () => (!S.on && todo().length ? todo().length : 0);        // plans left on the ground, out of the mode
  return {S, LAYER_CAP, toggle, onKey, ways: () => { const L = level(), all = S.at && myPos() ? stops(S.at) : []; return {up: all.some((z) => z > L), down: all.some((z) => z < L)}; }, click, point, tick, pan, rows, hint, taking, waiting, level, landFits, get on() { return S.on; }, aim: () => { const it = hint(S.at); return {p: S.at, it: it.ghost || it.z !== undefined ? it : {...it, z: level()}}; }};
})();
