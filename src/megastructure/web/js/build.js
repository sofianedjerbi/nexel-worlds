// Building, as a plan and then the work. Placing was one tile at a time, the one you faced: to raise a wall you
// walked a step, turned, pressed, and again, and walled yourself in. Now you plan first and your character builds:
//   B          build mode, and out of it. What is in your hand is the piece: the bar's numbers; Q, the next piece.
//   arrows     move the cursor, a tile at a time (it is not you who walks: the view goes with the cursor)
//   Space      plan the piece here. Held while you move: a row. A door on a wall, a gate on a fence: in its place
//   X          take a plan back; on something built: plan to take it down. Held: a row
//   R, F       the cursor up a floor, and down (also PgUp, PgDn)
//   Esc        drop every plan (with none: out of the mode)
// The cursor has a height. It rides the ground nearest your own (the floor you stand on); R lifts it a storey, into
// the air over a room or onto the floor above, and there it stays as it moves, until F brings it down. What you plan
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
  const SWAP = {door: "W%", gate: "#"};                      // a piece that goes in the place of another: a door in a wall, a gate in a fence
  const S = {on: false, at: null, plane: null, plans: new Map(), hold: null, working: false, dir: null, timer: 0, pan: {x: 0, y: 0}};
  const now = () => performance.now(), UPMOST = 9;         // (how far over your own height the cursor goes: three floors)
  // The cursor's height: the plane it was lifted to, or the ground at its tile nearest your own height
  const ride = (p) => { const s = myPos(); return settleNear(p.x, p.y, s ? myZ(s.x, s.y) : topAt(p.x, p.y)); };
  const level = (p = S.at) => (S.plane !== null ? S.plane : p ? ride(p) : 0);
  const onIt = (p, L) => solidAt(p.x, p.y, L) && !solidAt(p.x, p.y, L + 1);        // the cursor is on something there (not in the air, not inside it)
  const key = (p, z = level(p)) => p.x + "," + p.y + "," + z;
  const BLOCK = (it) => it === "roof" || it === "plank";
  const planned = (x, y, z) => { const j = S.plans.get(x + "," + y + "," + z); return !!j && !j.take && j.up && BLOCK(j.item) && j.state !== "bad"; };     // a block that is only planned yet
  const piece = () => (selected && meObs && meObs.self.inventory[selected] && (PLACEABLE_BLOCK[selected] || FILLS[selected] || selected === "seed") ? selected : null);
  const todo = () => [...S.plans.values()].filter((j) => j.state !== "bad");

  // What planning the piece in hand at p would be: the game's own answer for that tile (intent.js), as a ghost,
  // said in a few words (they are written beside the bar: a long line ran under it)
  function hint(p) {
    const it = piece();
    if (!it) return {text: selected ? "Not a building piece" : "Pick a piece: 1-9, Q", ok: false};
    if (FOOT[PLACEABLE_BLOCK[it]]) return {text: "Put by hand: leave with B", ok: false, ghost: it};
    const have = meObs.self.inventory[it], used = todo().filter((j) => j.item === it).length, t = tile(p.x, p.y);
    const L = level(p), on = onIt(p, L), c = FLOORS ? Floors.get(p.x, p.y, L) : null, what = Floors.thingAt(p.x, p.y, L);
    if (used >= have) return {text: `All ${have} are planned`, ok: false, ghost: it};
    if (BLOCK(it) && (FLOORS || it === "roof") && !(it === "plank" && on && !c && t && FILLS.plank[t[1]] && GROUND.has(t[0]))) {     // a block, for a cell
      const z = !on ? L : it === "roof" ? L + Floors.STOREY : L + 1, why = S.plans.has(key(p, z)) ? "Planned" : Floors.fits(p.x, p.y, z, planned);
      return why ? {text: why, ok: false, ghost: it, z} : {text: `Plan ${label(it)}${on && it === "plank" ? " on top" : ""}`, ok: true, ghost: it, z};
    }
    if (S.plans.has(key(p, L))) return {text: "Planned", ok: false, ghost: it};
    if (!on) return {text: solidAt(p.x, p.y, L) ? "Nothing can go there" : "No floor there: lay one", ok: false, ghost: it, z: L};
    if (SWAP[it] && SWAP[it].includes(what)) return {text: `Plan ${label(it)} in its place`, ok: true, ghost: it, swap: true, ...(c ? {z: L} : {})};
    if (c) return what ? {text: "Something is there", ok: false, ghost: it, z: L} : Floors.UP.has(PLACEABLE_BLOCK[it]) ? {text: `Plan ${label(it)}`, ok: true, ghost: it, z: L} : {text: "It needs the ground", ok: false, ghost: it, z: L};
    const say = intent(p, false) || {text: "Nothing can go there", ok: false};
    return {...say, text: say.ok === false ? say.text.replace(/^Can't place .* here$/, "Can't go there") : say.text.replace(/^(Place|Lay|Build|Plant|Launch) /, "Plan ")};
  }
  // What X would take at p -> {z, what: its name, plan: the plan there}, or nothing. Where the piece in hand would
  // go first (a roof selected: the roof over the cursor), then what stands at the cursor's level, then the block it
  // is on, then what was laid in the ground; and, the cursor riding the ground with nothing there to take, the
  // lowest block over it (the roof over a room)
  function taking(p) {
    const t = tile(p.x, p.y), L = level(p), on = onIt(p, L), h = piece() ? hint(p) : {};
    const zs = [...new Set([selected === "roof" && on ? L + Floors.STOREY : undefined, h.z, L].filter((z) => z !== undefined))];
    for (const z of zs) { const j = S.plans.get(key(p, z)); if (j) return j.state === "doing" ? null : {z, what: "plan", plan: j}; }
    if (!t) return null;
    const built = (z) => { const c = FLOORS || z !== L ? Floors.get(p.x, p.y, z) : null; return c ? {z, what: c[1] ? label(CH[c[1]]) : c[0] === "roof" ? "roof" : "planks", up: true} : null; };
    for (const z of zs) if (built(z)) return built(z);
    if (on && L === standAt(p.x, p.y)) {
      if (!GROUND.has(t[0])) return "#W%+g".includes(t[0]) || Object.values(PLACEABLE_BLOCK).includes(t[0]) ? {z: L, what: label(CH[t[0]])} : null;
      if ("_n:".includes(t[1])) return {z: L, what: label(CH[t[1]])};
    }
    for (let z = L + 1; S.plane === null && z <= L + 3 * Floors.STOREY; z++) if (built(z)) return built(z);
    return null;
  }
  function plan(p) {
    const it = hint(p), z = it.z !== undefined ? it.z : level(p);
    if (!it.ghost || it.ok === false) return S.hold ? null : toast(it.text, true);
    if (BLOCK(selected) && S.hold && S.row !== undefined && S.row !== z) return;     // (a row of blocks is at one height: over a floor already laid it does not pile them up)
    S.row = z;
    S.plans.set(key(p, z), {x: p.x, y: p.y, z, item: selected, up: it.z !== undefined, ground: it.ghostGround || null, swap: !!it.swap, state: "todo"});
    sfx("pick"); work();
  }
  function take(p) {                                  // a plan back; or, of what is built there, a plan to take it down
    const hit = taking(p);
    if (!hit) return S.hold ? null : toast("Nothing built there", true);
    if (hit.plan) { S.plans.delete(key(p, hit.z)); return; }
    S.plans.set(key(p, hit.z), {x: p.x, y: p.y, z: hit.z, take: true, up: !!hit.up, state: "todo"});
    sfx("pick"); work();
  }
  // The work: the nearest plan, a place to stand beside it, the piece put (or the thing taken down); then the next
  async function work() {
    if (S.working) return;
    S.working = true;
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
    const wait = (j) => !j.take && j.up && (BLOCK(j.item) ? !!Floors.fits(j.x, j.y, j.z) : !Floors.get(j.x, j.y, j.z));
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
      for (const [dx, dy] of Object.values(DIRV)) { const n = {x: c.x + dx, y: c.y + dy}, k = flat(n); if (!seen.has(k) && !shut.has(k) && plainWalk(n.x, n.y)) { seen.add(k); line.push(n); } }
    }
    return false;
  }
  // Somewhere to stand at height h on tile q: on the ground, or on a built block with nothing solid on it
  const stands = (q, h) => { const c = FLOORS ? Floors.get(q.x, q.y, h) : null; return c ? !SOLID.has(c[1]) : h === standAt(q.x, q.y) && plainWalk(q.x, q.y); };
  async function build(j) {                           // -> why it could not be done (nothing: it is done)
    if (!j.take && !(meObs.self.inventory[j.item] > 0)) return `No ${label(j.item)} left`;
    const here = () => { const s = myPos(); return {...s, z: myZ(s.x, s.y)}; };
    // from (q, h): within the game's reach of it, height counted; and not where it goes (a block in your body, a wall on your feet)
    const ok = (q, h) => (q.x - j.x) ** 2 + (q.y - j.y) ** 2 + ((j.z - h) * LAYER) ** 2 <= (USE_R + .5) ** 2
      && !(q.x === j.x && q.y === j.y && (j.up ? j.z - h >= 0 && j.z - h <= 2 : true));
    if (!ok(here(), here().z) || (solid(j) && !wayOut(here(), j))) {
      const s = here(), spots = [];                    // (beside it for choice, on your own floor for choice)
      for (let dy = -USE_R; dy <= USE_R; dy++) for (let dx = -USE_R; dx <= USE_R; dx++) for (const h of surfacesAt(j.x + dx, j.y + dy)) {
        const q = {x: j.x + dx, y: j.y + dy, z: h, far: Math.abs(dx) + Math.abs(dy) > 1 ? 3 : 0};
        if (stands(q, h) && ok(q, h) && !entityAt(q)) spots.push(q);
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
    const was = Floors.thingAt(j.x, j.y, j.z), tool = (j.take || j.swap) && TOOL_FOR[was] && meObs.self.inventory[TOOL_FOR[was]] ? TOOL_FOR[was] : null;
    const went = (r) => (r && r.ok ? null : (r && (r.detail || r.error)) || "It could not be done");
    const z = FLOORS ? {z: j.z} : {}, dig = () => { actTarget = {x: j.x, y: j.y}; return act(FLOORS || !j.up ? "dig" : "unroof", {dir: "N", ...z, ...(tool ? {with: tool} : {})}, true); };
    if (j.swap && SWAP[j.item].includes(was)) {        // what is in its place comes down first (and back into your pack)
      const why = went(await dig());
      if (why) return why;
    }
    if (j.take) return went(await dig());
    actTarget = {x: j.x, y: j.y};
    return went(await act("place", {dir: "N", item: j.item, ...z}, true));
  }

  function toggle(on = !S.on) {
    if (on === S.on || (on && !me)) return;
    S.on = on; S.hold = null; S.plane = null; held(null);
    document.body.classList.toggle("building", on);
    if (on) { S.at = facingTile() || myPos(); toast("**Build mode**\nThe arrows move the cursor · `Space` plans, held: a row\n`R` up a floor"); work(); }
    else { S.pan = {x: 0, y: 0}; if (todo().length) toast(`${todo().length} plans wait: B to go on building`); }      // (the plans stay where they are)
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
  // R, F: the cursor up a storey (into the air over a room, onto the floor above), and down; back on the ground it rides again
  function lift(d) {
    const s = myPos(), base = ride(S.at), to = level() + d * Floors.STOREY;
    if (!FLOORS) return toast("Floors come when this world's server is restarted", true);
    if (!s || to > myZ(s.x, s.y) + UPMOST || (d < 0 && S.plane === null)) return sfx("buzz");
    S.plane = to <= base ? null : to;
    sfx("pick");
  }
  function nextPiece() {                              // Q: the next thing of your bar that is a piece
    const bar = slots.slice(0, BAR).filter((n) => n && meObs.self.inventory[n] && (PLACEABLE_BLOCK[n] || FILLS[n] || n === "seed"));
    if (!bar.length) return toast("Nothing to build with in your bar", true);
    selectItem(bar[(bar.indexOf(selected) + 1) % bar.length]);
  }
  // A key in build mode -> true: it was the mode's (the rest, the bar's numbers among them, go on as ever)
  function onKey(k, e) {
    if (!S.on) return false;
    if (k === "b") { if (!e.repeat) toggle(false); return true; }
    if (k === "escape") { if (!e.repeat) { if (todo().length) drop(); else toggle(false); } return true; }
    if (KEYDIR[k]) { if (!e.repeat) held(KEYDIR[k]); return true; }
    if (k === " " || k === "x") { if (!e.repeat) { S.hold = k; S.row = undefined; if (k === " ") plan(S.at); else take(S.at); } return true; }
    if (k === "r" || k === "pageup" || k === "pagedown") { if (!e.repeat) lift(k === "pagedown" ? -1 : 1); return true; }
    if (k === "f") { if (!e.repeat) lift(-1); return true; }
    if (k === "q") { if (!e.repeat) nextPiece(); return true; }
    return k === "e";                                 // (no eating by mistake while you plan)
  }
  addEventListener("keyup", (e) => { const k = e.key.toLowerCase(); if (k === S.hold) S.hold = null; if (KEYDIR[k] === S.dir) held(null); });
  addEventListener("blur", () => { S.hold = null; held(null); });
  function point(p) { if (S.on && tile(p.x, p.y)) S.at = {x: p.x, y: p.y}; }      // (the mouse: the cursor is where it points, at the cursor's height: mouse.js)
  function click(p, alt) { point(p); S.row = undefined; if (alt) take(S.at); else plan(S.at); }

  // What is drawn of it: every plan as a ghost of its piece (a red one: it could not be done), and the cursor
  function draw(sx, sy, Sz, t) {
    const z = zoom, top = (p, L) => sy(p.y) - shOf(L) * z;                 // (each at its own height)
    for (const [k, j] of S.plans) {
      if (j.state === "bad" && now() - j.t > BAD_MS) { S.plans.delete(k); continue; }
      const x = sx(j.x), y = top(j, j.z), a = j.state === "doing" ? .75 : .5, ch = PLACEABLE_BLOCK[j.item];
      if (j.take) { /* (what is there is seen: a cross over it, below) */ }
      else if (j.up && BLOCK(j.item)) Floors.cell(j.item, j.x, j.y, j.z, sx, sy, Sz, a);
      else if (j.up) Floors.thing(ch, j.x, j.y, j.z, sx, sy, Sz, t, 0, a);
      else if (Structures.WALLS.includes(ch || "-")) Structures.drawWall(ch, j.x, j.y, sx, sy, Sz, 0, a);
      else {
        const spr = j.ground ? groundPreview(j.ground, j.x, j.y) : j.item === "seed" ? [IMG.crops, 0, CROP_ROW[cropSpecies(j.x, j.y)] * 16, 16, 16, 0, -2] : objectSprite(ch, j.x, j.y, t);
        ctx.globalAlpha = a;
        if (spr) ctx.drawImage(spr[0], spr[1], spr[2], spr[3], spr[4], x + spr[5] * z, y + spr[6] * z, spr[3] * z, spr[4] * z);
        ctx.globalAlpha = 1;
      }
      ctx.fillStyle = j.state === "bad" ? "rgba(230,80,70,.4)" : j.take ? "rgba(255,150,60,.3)" : j.state === "doing" ? "rgba(255,241,168,.35)" : "rgba(140,190,255,.28)";
      ctx.fillRect(x, y, Sz, Sz);
      if (j.take) { ctx.fillStyle = "#b5532a"; for (let i = 4; i < 12; i++) { ctx.fillRect(x + i * z, y + i * z, z, z); ctx.fillRect(x + (15 - i) * z, y + i * z, z, z); } }     // (to come down: a cross)
    }
    if (S.on && !me) { S.plans.clear(); toggle(false); }                    // (you fell, or the game went: out of the mode)
    if (!S.on || !S.at) return;
    const L = level(), x = sx(S.at.x), y = top(S.at, L), c = 5 * z, w = 2 * z, blink = Math.floor(t * 3) % 2 ? "#fff1a8" : "#ffffff";
    if (!onIt(S.at, L) && !solidAt(S.at.x, S.at.y, L)) {      // in the air: its shadow on what is under it, and the line down to it
      const under = settleAt(S.at.x, S.at.y, L), y0 = top(S.at, under);
      ctx.fillStyle = "rgba(40,30,50,.22)"; ctx.fillRect(x + 2 * z, y0 + 2 * z, Sz - 4 * z, Sz - 4 * z);
      ctx.fillStyle = "rgba(91,63,54,.5)"; for (let yy = y + Sz; yy < y0 + Sz / 2; yy += 3 * z) ctx.fillRect(x + Sz / 2 - z / 2, yy, z, 2 * z);
    }
    ctx.fillStyle = "rgba(255,255,255,.14)"; ctx.fillRect(x, y, Sz, Sz);
    ctx.fillStyle = "#5b3f36";                        // the cursor: four corners, in the game's ink with a light line inside
    for (const [cx, cy, hx, hy] of [[x - w, y - w, 1, 1], [x + Sz + w, y - w, -1, 1], [x - w, y + Sz + w, 1, -1], [x + Sz + w, y + Sz + w, -1, -1]]) {
      ctx.fillRect(Math.min(cx, cx + hx * (c + w)), Math.min(cy, cy + hy * 2 * w), c + w, 2 * w); ctx.fillRect(Math.min(cx, cx + hx * 2 * w), Math.min(cy, cy + hy * (c + w)), 2 * w, c + w);
    }
    ctx.fillStyle = blink;
    for (const [cx, cy, hx, hy] of [[x, y, 1, 1], [x + Sz, y, -1, 1], [x, y + Sz, 1, -1], [x + Sz, y + Sz, -1, -1]]) {
      ctx.fillRect(Math.min(cx, cx + hx * c), Math.min(cy, cy + hy * w), c, w); ctx.fillRect(Math.min(cx, cx + hx * w), Math.min(cy, cy + hy * c), w, c);
    }
  }
  // The view, in build mode: half way from you to the cursor, eased (both stay on the screen)
  function pan(dt) {
    const s = myPos(), to = S.on && S.at && s ? {x: (S.at.x - s.x) / 2, y: (S.at.y - s.y) / 2} : {x: 0, y: 0}, k = Math.min(1, dt * 6);
    S.pan.x += (to.x - S.pan.x) * k; S.pan.y += (to.y - S.pan.y) * k;
    return S.pan;
  }
  // What the keys do just now, for the corner of the screen (keyboard.js): the mode's name first, then each key
  // that does something here, in a few words
  function rows() {
    const it = hint(S.at), n = todo().length, hit = taking(S.at), s = myPos(), up = S.plane === null || !s ? 0 : Math.round((S.plane - myZ(s.x, s.y)) / Floors.STOREY);
    const out = [["B", up ? `BUILD · floor ${up > 0 ? "+" : ""}${up} · leave` : "BUILD MODE · leave", "head"]];
    out.push(["Space", it.text, it.ok === false ? "bad" : ""]);
    if (FLOORS) out.push(["R", S.plane === null ? "Cursor up a floor" : "Up · F: down"]);
    if (hit) out.push(["X", hit.plan ? "Take the plan back" : hit.what === "roof" ? "Take the roof off" : `Take down ${hit.what}`]);
    if (n) out.push(["Esc", `Drop the ${n} plan${n > 1 ? "s" : ""}`]);
    return out;
  }
  const waiting = () => (!S.on && todo().length ? todo().length : 0);        // plans left on the ground, out of the mode
  return {S, toggle, onKey, click, point, draw, pan, rows, hint, waiting, level, get on() { return S.on; }, aim: () => ({p: S.at, it: hint(S.at)})};
})();
