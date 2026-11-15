// Building, as a plan and then the work. Placing was one tile at a time, the one you faced: to raise a wall you
// walked a step, turned, pressed, and again, and walled yourself in. Now you plan first and your character builds:
//   B          build mode, and out of it (Esc too). What is in your hand is the piece: the bar's numbers, Q.
//   arrows     move the cursor, a tile at a time (it is not you who walks: the view goes with the cursor)
//   Space      plan the piece here. Held while you move: a row of them
//   X          take a plan back; on something built: plan to take it down. Held while you move: a row
// Every plan is a ghost on the ground. Your character goes to the nearest, stands beside it and builds it (the
// game's own moves: walk there, place; the server checks each as it always did), then the next, block by block.
// A plan that cannot be done (no way there, someone standing on it) turns red, says why, and goes.
// By mouse, in build mode: a click plans, a drag plans a row, shift or the right button takes.
// The whole of it by keys alone. One piece a tile; a piece bigger than a tile (a well, a coop) is still put by hand.
const Build = (() => {
  const REACH = 8, STEP_MS = 110, BAD_MS = 2600;            // how far from you the cursor goes; its pace when a key is held; how long a failed plan shows
  const S = {on: false, at: null, plans: new Map(), hold: null, working: false, moved: 0, pan: {x: 0, y: 0}};
  const key = (p) => p.x + "," + p.y, now = () => performance.now();
  const piece = () => (selected && meObs && meObs.self.inventory[selected] && (PLACEABLE_BLOCK[selected] || FILLS[selected] || selected === "seed") ? selected : null);
  const todo = () => [...S.plans.values()].filter((j) => j.state !== "bad");

  // What planning the piece in hand at p would be: the game's own answer for that tile (intent.js), as a ghost
  function hint(p) {
    const it = piece();
    if (!it) return {text: selected ? `${label(selected)} is not something to build with` : "Nothing in hand: pick a piece (1-9, Q)", ok: false};
    if (FOOT[PLACEABLE_BLOCK[it]]) return {text: `The ${label(it)} is put by hand: leave build mode (B)`, ok: false, ghost: it};
    const have = meObs.self.inventory[it], used = todo().filter((j) => j.item === it).length;
    if (S.plans.has(key(p))) return {text: "Planned", ok: false, ghost: it};
    if (used >= have) return {text: `No more ${label(it)}: all ${have} are planned`, ok: false, ghost: it};
    return intent(p, false) || {text: "Nothing can go there", ok: false};
  }
  function plan(p) {
    const it = hint(p);
    if (!it.ghost || it.ok === false) return S.hold ? null : toast(it.text, true);
    S.plans.set(key(p), {x: p.x, y: p.y, item: selected, ground: it.ghostGround || null, state: "todo"});
    sfx("pick"); work();
  }
  function take(p) {                                  // a plan back; or, of something built there, a plan to take it down
    const j = S.plans.get(key(p));
    if (j) { if (j.state !== "doing") S.plans.delete(key(p)); return; }
    const t = tile(p.x, p.y); if (!t) return;
    const built = !GROUND.has(t[0]) ? "#W%+g".includes(t[0]) || !!Object.values(PLACEABLE_BLOCK).includes(t[0]) : "_n:".includes(t[1]);
    if (!built) return S.hold ? null : toast("Nothing built there to take down", true);
    S.plans.set(key(p), {x: p.x, y: p.y, take: true, state: "todo"});
    work();
  }
  // The work: the nearest plan, a place to stand beside it, the piece put (or the thing taken down); then the next
  async function work() {
    if (S.working) return;
    S.working = true;
    try {
      for (let j; me && (j = nearest());) {
        j.state = "doing";
        const why = await build(j);
        if (!why) S.plans.delete(key(j));
        else if (!j.tried) { j.tried = true; j.state = "todo"; }             // once more, after the others: what was in the way may be gone
        else { j.state = "bad"; j.why = why; j.t = now(); toast(why, true); }
      }
    } finally { S.working = false; }
  }
  function nearest() {
    const s = myPos(); if (!s) return null;
    // (what you can walk on first, a floor, a door: then what closes the way, the nearest first)
    const far = (j) => (j.tried ? 1000 : 0) + (solid(j) ? 500 : 0) + Math.abs(j.x - s.x) + Math.abs(j.y - s.y);
    return [...S.plans.values()].filter((j) => j.state === "todo").sort((a, b) => far(a) - far(b))[0];
  }
  const solid = (j) => !j.take && SOLID.has(PLACEABLE_BLOCK[j.item] || ".");
  // From q, with every solid plan built: can you still walk away (ten tiles off)? Not from inside the walls you plan
  function wayOut(q, j) {
    const shut = new Set([...S.plans.values()].filter(solid).map(key)), seen = new Set([key(q)]), line = [q];
    for (let i = 0; i < line.length && i < 400; i++) {
      const c = line[i];
      if (Math.max(Math.abs(c.x - j.x), Math.abs(c.y - j.y)) >= 10) return true;
      for (const [dx, dy] of Object.values(DIRV)) { const n = {x: c.x + dx, y: c.y + dy}, k = key(n); if (!seen.has(k) && !shut.has(k) && plainWalk(n.x, n.y)) { seen.add(k); line.push(n); } }
    }
    return false;
  }
  async function build(j) {                           // -> why it could not be done (nothing: it is done)
    if (!j.take && !(meObs.self.inventory[j.item] > 0)) return `No ${label(j.item)} left`;
    const on = () => { const s = myPos(); return s.x === j.x && s.y === j.y; };
    const here = myPos();                             // not beside it (or beside it, but inside what it would close): to a free tile beside it
    if (on() || !reaches(j.x, j.y, 1) || (solid(j) && !wayOut(here, j))) {
      const s = myPos(), beside = Object.values(DIRV).map(([dx, dy]) => ({x: j.x + dx, y: j.y + dy})).filter((q) => plainWalk(q.x, q.y) && !entityAt(q));
      const cost = (q) => (solid(j) && !wayOut(q, j) ? 200 : 0) + (S.plans.has(key(q)) ? 60 : 0) + Math.abs(q.x - s.x) + Math.abs(q.y - s.y);     // (not walled in, for choice)
      beside.sort((a, b) => cost(a) - cost(b));
      let there = false;
      for (const q of beside) {
        const r = await act("move_to", {x: q.x, y: q.y}, true);
        // (the walk is over on the server a moment before your screen has you there: wait for it)
        for (let i = 0; r && r.ok && i < 40 && !(myPos().x === q.x && myPos().y === q.y); i++) await new Promise((ok) => setTimeout(ok, 25));
        if (r && r.ok && !on() && reaches(j.x, j.y, 1)) { there = true; break; }
        if (!S.plans.has(key(j))) return null;
      }
      if (!there) return "No way to get beside it";
    }
    if (!S.plans.has(key(j))) return null;            // (taken back meanwhile)
    actTarget = {x: j.x, y: j.y};
    const t = tile(j.x, j.y), tool = j.take && TOOL_FOR[t[0]] && meObs.self.inventory[TOOL_FOR[t[0]]] ? TOOL_FOR[t[0]] : null;
    const r = await act(j.take ? "dig" : "place", j.take ? {dir: "N", ...(tool ? {with: tool} : {})} : {dir: "N", item: j.item}, true);
    return r && r.ok ? null : (r && (r.detail || r.error)) || "It could not be done";
  }

  function toggle(on = !S.on) {
    if (on === S.on || (on && !me)) return;
    S.on = on; S.hold = null;
    document.body.classList.toggle("building", on);
    if (on) { S.at = facingTile() || myPos(); toast("Build: arrows move the cursor · Space plans what is in your hand (hold it for a row) · X takes · B when done"); }
    else { for (const [k, j] of S.plans) if (j.state !== "doing") S.plans.delete(k); S.pan = {x: 0, y: 0}; }      // (what was not begun is dropped)
  }
  function move(dir) {
    const s = myPos(), [dx, dy] = DIRV[dir], x = S.at.x + dx, y = S.at.y + dy;
    if (!s || !tile(x, y) || Math.max(Math.abs(x - s.x), Math.abs(y - s.y)) > REACH) return;
    S.at = {x, y};
    if (S.hold === " ") plan(S.at); else if (S.hold === "x") take(S.at);
  }
  // A key in build mode -> true: it was the mode's (the rest, the bar's numbers and Q among them, go on as ever)
  function onKey(k, e) {
    if (!S.on) return false;
    if (k === "b" || k === "escape") { if (!e.repeat) toggle(false); return true; }
    if (KEYDIR[k]) { if (!e.repeat || now() - S.moved >= STEP_MS) { S.moved = now(); move(KEYDIR[k]); } return true; }
    if (k === " " || k === "x") { if (!e.repeat) { S.hold = k; if (k === " ") plan(S.at); else take(S.at); } return true; }
    return k === "f" || k === "e";                    // (no picking up nor eating by mistake while you plan)
  }
  addEventListener("keyup", (e) => { if (e.key.toLowerCase() === S.hold || e.key === S.hold) S.hold = null; });
  addEventListener("blur", () => { S.hold = null; });
  function click(p, alt) { S.at = p; if (alt) take(p); else plan(p); }

  // What is drawn of it: every plan as a ghost of its piece (a red one: it could not be done), and the cursor
  function draw(sx, sy, Sz, t) {
    const z = zoom;
    for (const [k, j] of S.plans) {
      if (j.state === "bad" && now() - j.t > BAD_MS) { S.plans.delete(k); continue; }
      const x = sx(j.x), y = sy(j.y, j.x);
      const spr = j.take ? null : j.ground ? groundPreview(j.ground, j.x, j.y) : j.item === "seed" ? [IMG.crops, 0, CROP_ROW[cropSpecies(j.x, j.y)] * 16, 16, 16, 0, -2] : objectSprite(PLACEABLE_BLOCK[j.item], j.x, j.y, t);
      ctx.globalAlpha = j.state === "doing" ? .75 : .5;
      if (spr) ctx.drawImage(spr[0], spr[1], spr[2], spr[3], spr[4], x + spr[5] * z, y + spr[6] * z, spr[3] * z, spr[4] * z);
      ctx.globalAlpha = 1;
      ctx.fillStyle = j.state === "bad" || j.take ? "rgba(230,80,70,.35)" : j.state === "doing" ? "rgba(255,241,168,.35)" : "rgba(140,190,255,.28)";
      ctx.fillRect(x, y, Sz, Sz);
    }
    if (!S.on || !S.at) return;
    const x = sx(S.at.x), y = sy(S.at.y, S.at.x), c = 4 * z, w = z, blink = Math.floor(t * 3) % 2 ? "#fff1a8" : "#ffffff";
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
  // What the keys do just now, for the corner of the screen (keyboard.js)
  function rows() {
    const it = hint(S.at), left = todo().length, j = S.plans.get(key(S.at));
    return [["Space", it.ok === false ? it.text : `Plan: ${it.text}`, it.ok === false ? "bad" : ""], ["X", j ? "Take the plan back" : "Plan to take down"], ["B", left ? `Done (${left} to build)` : "Done"]];
  }
  return {S, toggle, onKey, click, draw, pan, rows, hint, get on() { return S.on; }, aim: () => ({p: S.at, it: hint(S.at)})};
})();
