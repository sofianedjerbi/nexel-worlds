// Keyboard: the whole game is playable without a mouse. Keys by place where it matters (options.js keyId: an AZERTY's ZQSD walk).
//   WASD / arrows walk (Shift sprints), Space jumps, Alt+direction turns on the spot. Two verbs, as in Minecraft (intent.js): E uses
//   what you face (open, talk, place, plant, feed, harvest; or eats, wears what you hold: facingNow), the key over A (A on an AZERTY), or X, breaks it.
//   The hand is a slot of the bar, always one, like Minecraft: 1-9 and 0 pick it (an empty one: empty hands), Tab and the wheel over
//   the bar the next one (Tab held: who is awake), ` the first empty one. (The keys are the settings': options.js KEY_ACTIONS.)
//   C crafting and I inventory: the arrows, Enter uses, Esc closes; their keys are their own (craft.js, bag.js) but BOOK_KEYS, none
//   acts on the world behind; one open at a time; each key's cap on its button (`kbd`) while you play by keys (body.bykeys).
//   Z (the key under A, by place) or B: build mode (build.js): the arrows move a cursor, Space plans, your character builds (keys its own).

const KEYDIR = {w: "N", arrowup: "N", s: "S", arrowdown: "S", a: "W", arrowleft: "W", d: "E", arrowright: "E"};
const CODEDIR = {KeyW: "N", ArrowUp: "N", KeyS: "S", ArrowDown: "S", KeyA: "W", ArrowLeft: "W", KeyD: "E", ArrowRight: "E"};
const keys = new Set();
let runKey = false;
const sprinting = () => runKey && !(meObs && meObs.self.hunger <= SPRINT_FOOD);   // (three pieces of food or fewer: no sprinting, as the server has it)
let inputMode = "mouse";     // "keys" once you play with the keyboard: hints then follow the tile you face

function facingTile() {
  const p = ents.get("agent" + myId), s = myPos(); if (!p || !s) return null;
  return {x: s.x + (p.fx || 0), y: s.y + (p.fy || (p.fx ? 0 : 1))};
}
// Things done in passing, without stopping: hits, picking flowers, mushrooms, berries, fruit and crops, small
// decorations (the server makes these instant: no tool and hardness <= 3, or picking), picking up items.
function isQuick(f) {
  if (f.it.attack || f.it.here) return true;
  const c = combAt(f.p.x, f.p.y);
  return !placingItem() && !!c && !!tileOf(c).quick;
}
const useful = (it) => it && !it.walk && !it.info && it.ok !== false;
// Who you're fighting: set when you hit someone or someone hits you, so X keeps hitting them, not the tree beside.
let foe = null;   // {key: entity key, until: ms}
const FOE_MS = 8000;
function entKey(name) {               // an attack event names agents by name and creatures as "kind#id"
  const m = /^(\w+)#(\d+)$/.exec(name || "");
  if (m) return m[1] + m[2];
  const a = [...ents.values()].find((q) => q.e && q.e.kind === "agent" && q.e.name === name);
  return a ? "agent" + a.e.id : null;
}
function noteFight(e) {
  if (e.attacker === me) foe = {key: entKey(e.target), until: performance.now() + FOE_MS};
  else if (e.target === me) foe = {key: entKey(e.attacker), until: performance.now() + FOE_MS};
}
// What E (alt = false) or X (alt = true) does, without having to turn first. X's fighting comes first: the one
// you're fighting, then any wild enemy within reach; then the tile you face; then other creatures within reach; then
// anything next to you, preferring the direction you last walked. Falls back to a hint about the faced tile.
// Holding something to place (a block, path, planks, dirt, seeds): E puts it on the tile in front of you, and
// only there (the ghost shows it, green or red). Walk to aim: a tap turns you and moves you a tile.
const placingItem = () => selected && placeable(selected);
// It is asked three times a frame (the corner's rows, the hint beside the tile, the aim): worked out once for a tick
// of the world, a place, a way faced, a thing in hand and a state of the land, and kept till one of them changes (it
// made a sixth of the memory the page went through: the collector's work).
const FACED = [{}, {}];
function facingIntent(alt) {
  const m = FACED[alt ? 1 : 0], p = ents.get("agent" + myId), s = myPos(), hot = !!foe && performance.now() < foe.until;
  if (p && s && m.clock === clock && m.obs === meObs && m.land === landVer && m.built === Floors.ver && m.sel === selected && m.x === s.x && m.y === s.y && m.fx === p.fx && m.fy === p.fy && m.foe === foe && m.hot === hot) return m.out;
  const out = facingNow(alt);
  Object.assign(m, {clock, obs: meObs, land: landVer, built: Floors.ver, sel: selected, x: s && s.x, y: s && s.y, fx: p && p.fx, fy: p && p.fy, foe, hot, out});
  return out;
}
// Food or clothes in hand, E eats or wears them, unless what you face takes that very thing (`uses`: intent.js)
const eatsInHand = () => { const w = inHand(); return w && (FOODS.includes(w) || RULES.wear[w]) ? w : null; };
function facingNow(alt) {
  const f = facingAny(alt), w = !alt && eatsInHand(), q = facingTile();
  if (!w || (f && f.it.uses && (f.it.uses !== "faced" || (q && f.p.x === q.x && f.p.y === q.y)))) return f;
  const s = myPos();
  return s && {p: {x: s.x, y: s.y}, it: {text: `${RULES.wear[w] ? "Wear" : "Eat"} ${label(w)}`, self: true, run: () => useSelected(w)}};
}
function facingAny(alt) {
  const q = facingTile(), s = myPos(); if (!q || !s) return null;
  if (!alt && placingItem()) {
    const it = intent(q, false);
    if (it && it.own) return it.none ? null : {p: it.own, it};          // (a ladder, facing a wall: it goes where you stand, against it: climbing.js)
    if (entityAt(q)) return {p: q, it: {text: "Something is in the way", ok: false, ghost: selected}};
    return it ? {p: q, it: it.ok === false || inReach(q, it) ? it : {...it, ok: false, text: TOO_HIGH}} : null;
  }
  const dist = (o) => Math.abs(o.tx - s.x) + Math.abs(o.ty - s.y);
  const near = [...ents.values()]                // (within reach: a circle, height counted: intent.js reaches)
    .filter((o) => o.e && !(o.e.kind === "agent" && o.e.id === myId) && reaches(o.tx, o.ty, reach("melee", inHand(), o.e && o.e.kind), standsAt(o)))
    .sort((a, b) => dist(a) - dist(b));
  const hit = (o) => { const p = {x: o.tx, y: o.ty}, it = intent(p, true); return useful(it) && it.attack ? {p, it} : null; };
  if (alt && foe && performance.now() < foe.until) {      // (X hits: E hits nobody, intent.js)
    const o = ents.get(foe.key), r = o && near.includes(o) && hit(o);
    if (r) return r;
  }
  if (alt) for (const o of near) if (WILD[o.e.kind] && o.e.kind !== "wisp") { const r = hit(o); if (r) return r; }
  const here = {x: s.x, y: s.y}, under = combAt(s.x, s.y);           // something growing under your feet
  if (!alt && under && !GROUND.has(under) && !SOLID.has(under)) { const it = intent(here, false); if (useful(it)) return {p: here, it}; }
  const faced = intent(q, alt);
  const hs = myZ(s.x, s.y), level = (t, it) => it.flat || it.ent || it.z !== undefined || it.at !== undefined || Math.abs(settleNear(t.x, t.y, hs) - hs) <= 2;   // (what grows on ground three levels over or under you is not offered: "Pick flower" from the bottom of a shaft, under the flower)
  if (useful(faced) && inReach(q, faced) && level(q, faced)) return {p: q, it: faced};
  // X and nothing else to take apart: the block you face, the one its box is on (it dug the one under you, with no mark:
  // "it should dig the selected highlighted block, not under the player"), with the pickaxe in hand or by hand (slower:
  // the server always allowed it). A wall at your feet: that cell; else the ground in front, a layer down. (Cutting
  // into a wall was a pickaxe's E: E digs nothing now, "why do I break rocks with E?")
  for (const o of near) { const p = {x: o.tx, y: o.ty}, it = intent(p, alt); if (useful(it) && inReach(p, it)) return {p, it}; }      // (a creature within reach before the ground: X hits the hen you pass, it did not dig)
  if (alt) { const d = digAhead(q, hs, s); if (d) return d; }
  // then anything within reach: nearest first, in front of you before behind
  const p0 = ents.get("agent" + myId), ring = [];
  for (let R = reach("use"), dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) {
    if ((!dx && !dy) || !reaches(s.x + dx, s.y + dy, R)) continue;
    ring.push({x: s.x + dx, y: s.y + dy, d: Math.max(Math.abs(dx), Math.abs(dy)) + Math.abs(dx) * .01 + Math.abs(dy) * .01 - (dx * p0.fx + dy * p0.fy) * .1});
  }
  ring.sort((a, b) => a.d - b.d);
  for (const q of ring) { const p = {x: q.x, y: q.y}, it = intent(p, alt); if (useful(it) && level(p, it) && inReach(p, it)) return {p, it}; }      // (inReach: not through the land: "Chop tree" from a tunnel four layers under it)
  // (what is in front of you but up a cliff or down one is not offered, and not refused in red either ("Out of
  // reach" for a flower three layers up): nothing is said of what your hand cannot get to)
  return faced && !faced.walk && !useful(faced) && inReach(q, faced) ? {p: q, it: faced} : null;
}
const facedOnly = (a) => (a && a.it.self ? null : a);      // (E eats what you hold: nothing you face is marked for it, target.js; its row is in the corner)
function digAhead(q, hs, s) {
  const wall = landSolid(q.x, q.y, hs + 1), z = wall ? hs + 1 : settleNear(q.x, q.y, hs), top = z === topAt(q.x, q.y), g = combAt(q.x, q.y);
  const elsewhere = wall && floorAt(q.x, q.y) !== z;      // (what stands on it stands elsewhere: on the hill over your tunnel)
  if (z < hs - 2 || entityAt(q) || (top && !elsewhere && !(g && GROUND.has(g) && !":n".includes(g) && !wet(g)))) return null;
  const pick = inHand() === "pickaxe";      // (its name: in a hole there is no hill; under the land the tunnel goes on)
  const text = !wall ? "Dig down" : s && topAt(s.x, s.y) > hs ? "Dig on" : s && inHole(s, q, hs) ? "Dig into the wall" : "Dig into the hill";
  return {p: q, it: {text, flat: true, cell: z, low: !wall, run: () => act("dig", {dir: dirTo(q), z, ...(pick ? {with: "pickaxe"} : {})})}};
}
// You stand in a hole: land at your body's height behind you too, or on both sides (a pit, a trench: not a hill's foot)
function inHole(s, q, h) {
  const dx = q.x - s.x, dy = q.y - s.y, wall = (x, y) => landSolid(s.x + x, s.y + y, h + 1);
  return wall(-dx, -dy) || (wall(dy, dx) && wall(-dy, -dx));
}
// The tile hints are drawn for: where the mouse points, or the tile you face when playing by keyboard.
function aimedTile() {
  if (!me) return null;
  if (Build.on) return Build.aim();                  // (build mode: the cursor's tile, whatever you play with)
  if (byKeys()) { const a = keyAim(); return a && wayHides(WayShow.offer(), a, "use") ? null : a; }      // (the way out is shown: no bracket on a wall to dig: "two brackets, two Space")
  if (!mouse.in) return null;
  return mouseAim();
}
const marked = (a) => !!a && !a.it.info && !a.it.walk;
// What a key acts on that is marked, its keys beside it: what you face first (E's, else X's: a tree, a rock, a wall),
// then E's (what you use) elsewhere, then X's. (X's "Dig down" on open meadow: its row in the corner, as it was)
function keyAim() {
  const m = facedOnly(facingIntent(false)), x0 = facingIntent(true), x = marked(x0) && x0.it.ok !== false && !x0.it.low ? x0 : null, q = facingTile();
  const at = (a) => !!a && !!q && a.p.x === q.x && a.p.y === q.y;
  const r = marked(m) && (at(m) || m.it.own || placingItem()) ? m : at(x) ? x : marked(m) ? m : x || m; return r && r === x ? {...r, brk: true} : r;      // (own: a ladder against the wall you face goes where you stand; brk: X's thing, its brackets orange: hd.js)
}
// Where the mouse points: what a right click there does (E's verb), else a left click (X's): mouse.js. alt: the left one's alone
function mouseAim(alt) {
  const p = tileAtScreen(mouse.x, mouse.y), b = clickIntent(p, "break");
  if (alt) return b;
  const u = clickIntent(p, "use");
  return u.it && !u.it.walk && !u.it.info ? u : b && {...b, brk: true};
}
// The keys are what you play with: once pressed, or while the mouse is not over the land (on arrival nothing was
// aimed until the first press or step, and E acted on the tile you face all the same)
const byKeys = () => inputMode === "keys" || !mouse.in;
// While the way out of the ground is shown (wayshow.js) nothing else is offered for what you face: "Space Dig into the
// wall" two levels under the grass, "Space Dig on / X Dig down" written on its dots, "Lay floor" in the pocket with a
// plank in hand. But what also gets you up: a ladder or stairs in hand, where they can go (the keys still do what
// they did: only the words are put away).
const wayHides = (way, f, key) => !!way && !(way.key !== key && f.it.ok !== false && /ladder|stairs/i.test(f.it.text));
// Bottom right: what you can do right now, each with its key. Rebuilt every frame, written only when it changes.
let actionsHtml = "", faceRows = [];               // (faceRows: what E and X do to what you face, beside it: prompts.js)
function availableActions() {
  if (!me || !meObs) return [];
  if (Build.on) return Build.rows();
  const s = myPos(), rows = [];
  const way = WayShow.offer(), m0 = facingIntent(false), a0 = facingIntent(true), main = m0 && wayHides(way, m0, "use") ? null : m0, alt = a0 && wayHides(way, a0, "alt") ? null : a0;
  if (way && way.key) rows.push([capOf(way.key), way.text, "way", true, true]);              // (the fifth: its cap is by its block; its word is in the corner, lit; a phone's button says it)
  const aim = keyAim(), on = (f) => !aim || (f.p.x === aim.p.x && f.p.y === aim.p.y);      // (beside what is marked: a key's row whose thing is elsewhere goes in the corner)
  if (main && main.it.self) rows.push([capOf("use"), main.it.text]);       // (eat, wear what you hold: in the corner, nothing faced is its)
  else if (main && !main.it.info && main.it.ok !== false) rows.push([capOf("use"), main.it.text, "", on(main)]);     // (the keys as the settings have them: options.js; true: what you face)
  else if (main && placingItem()) rows.push([capOf("use"), main.it.text, "bad", on(main)]);           // why it can't go there
  if (alt && !alt.it.info && alt.it.ok !== false && (!main || alt.it.text !== main.it.text)) rows.push([capOf("alt"), alt.it.text, "", on(alt)]);
  const up = way && way.key === "up" ? null : DigUp.aim();      // (the way out of a hole: the cell over your head, then the step: digup.js. Not hidden while the way out is shown: R digs all the same, and a phone's "Dig a step" was gone from under the finger)
  if (up) rows.push([capOf("up"), up.text, "", true]);
  if (!(way && way.key === "jump") && stepAhead()) rows.push([capOf("jump"), "Jump"]);      // (a step in front you can hop onto: walking into it stops you, walk.js)
  if (s && groundItems.some(([x, y]) => x === s.x && y === s.y)) rows.push([capOf("pick"), "Pick up"]);
  if (way) return rows;
  if (Build.waiting()) rows.push([capOf("build"), `Build: ${Build.waiting()} plans wait`]);      // (build.js: said where it helps, a piece in hand or plans left)
  else if (placingItem() && !FOOT[PLACEABLE_BLOCK[selected]]) rows.push([capOf("build"), "Build mode: plan a lot"]);
  return rows;   // only what you can do right here, right now (all the other keys are in the help, H)
}
// The corner: what is not beside what it acts on (prompts.js): in build mode its name and Esc; by keys, all but
// what you face
function updateActions() {
  const all = availableActions(), keys = byKeys(), aim = keys && !Build.on ? keyAim() : null;
  const beside = !!aim && !aim.it.info && !aim.it.walk;      // (something you face is marked: its keys go beside it. Nothing is: they stay in the corner. X's "Dig down" on open meadow was shown nowhere)
  faceRows = Build.on || !keys || !beside ? [] : all.filter((r) => r[3] && !r[4]);
  const corner = Build.on ? all.filter(([k]) => k === capOf("build") || k === "Esc") : keys && beside ? all.filter((r) => !r[3] || r[4]) : all;      // (the way out's key: on its block, and here with its word: "R Dig up": "which key ?")
  const html = corner.map(([k, t, cls]) => `<div class="${cls || ""}"><span class="key">${esc(k)}</span>${esc(t)}</div>`).join("");
  if (html === actionsHtml) return;
  actionsHtml = html;
  const el = $("actions"); el.innerHTML = html; el.style.display = html ? "block" : "none";
}
function useFacing(alt, again) {
  if (DigUp.route(alt ? "alt" : "use")) return;    // (the way out's next block is this key's: that block, whatever you hold or face: digup.js)
  WayShow.mine();
  const f = facingNow(alt);                        // (a key pressed: as things are this instant, not as kept)
  if (!f) return;                                  // (nothing there to act on: no row beside it, the button blank; it said "Nothing within reach." at each press, eight in a row in the chat)
  if (f.it.self) return again ? undefined : f.it.run();      // (eat, wear: walking or not; once a press, held or not)
  if (f.it.info) return f.it.quiet ? undefined : toast(f.it.text);      // (quiet: a rock under E: nothing done, nothing said)
  if (f.it.ok === false) return toast(f.it.text, true);
  if (walking && !isQuick(f)) return;             // E never stops you: work that takes time waits until you stand
  perform(f.p, f.it);
}
function turn(dir) {
  const p = ents.get("agent" + myId); if (!p) return;
  [p.fx, p.fy] = DIRV[dir];
}
function selectSlot(i) {                         // the bar's slot i in hand (ui.js handSync: what is in it, or empty hands)
  const was = selected; handSlot = ((i % BAR) + BAR) % BAR; localStorage.setItem("megastructure-hand", handSlot);
  handWant = null; handSync();
  if (selected !== was) sfx("pick");
  $("hotbar").dataset.sig = ""; if (meObs) drawHotbar(meObs.self.inventory);
}
function selectItem(name) {                      // a thing in hand: the slot it is in; null: empty hands (the first empty slot)
  const inv = meObs ? meObs.self.inventory : {};
  if (meObs) slotOrder(inv);
  if (!name) { const free = slots.slice(0, BAR).indexOf(null); if (free >= 0) selectSlot(free); return; }      // (none empty: nothing)
  const i = slots.indexOf(name);
  if (i < 0 || !inv[name]) { handWant = name; return; }      // (not come yet: taken in hand when it comes)
  const was = selected; handTo(i); handWant = null; handSync();
  if (selected !== was) sfx("pick");
  $("hotbar").dataset.sig = ""; drawHotbar(inv);
}
function cycleHand(step) {                       // Tab (and the wheel over the bar): the next slot, empty ones too, round
  if (!meObs) return;
  selectSlot(handSlot + step);      // (no line in the chat: the name over the bar says what is in hand: "no need to broadcast what the player have in hand in the chat")
}
let barWheel = 0;                                // (counted in distance: a mouse notch a slot, a trackpad swipe a few)
$("hotbar").addEventListener("wheel", (e) => { e.preventDefault(); barWheel += e.deltaY; if (Math.abs(barWheel) >= 50) { cycleHand(Math.sign(barWheel)); barWheel = 0; } }, {passive: false});
const BOOK_KEYS = new Set(["c", "i", "m", "h", "?", "g", "f3", "t", "/", "+", "=", "-"]);   // what still does its usual thing with the recipe book open
let capAt = null;
addEventListener("mousemove", (e) => {
  if (capAt && Math.abs(e.clientX - capAt.x) + Math.abs(e.clientY - capAt.y) > 4) document.body.classList.remove("bykeys");
  capAt = {x: e.clientX, y: e.clientY};
});
function closePanels() {
  for (const id of ["bag", "mail", "craft"]) $(id).style.display = "none";
  drawGoals();
}

const HELD = new Set(["e", "keyq", "x", "r"]);       // held down, these go on (a row of hits, of digs); the others act once a press
const SHORTCUTS = {        // key -> what it does (when no panel takes the key)
  e: (ev) => useFacing(false, ev && ev.repeat),      // (food, clothes in hand: eaten, worn: facingNow)
  keyq: () => useFacing(true), x: () => useFacing(true),       // (break: the key over A, by place; X too)
  r: () => DigUp.run(),
  " ": () => jumpKey(),                              // (walk.js: up onto the step in front, or a hop)
  f: () => act("pick_up", {}),
  keyy: (ev) => dropHeld(!!(ev && ev.shiftKey)),     // (drop: by place, options.js)
  tab: (ev) => cycleHand(ev && ev.shiftKey ? -1 : 1),
  "`": () => { selectItem(null); },
  c: () => { $("bag").style.display = "none"; toggleCraft(); },
  i: () => { if (isOpen("craft")) toggleCraft(); toggleBag(); },
  m: () => { setMuted(!muted); toast(`Sound **${muted ? "off" : "on"}** \`${capOf("mute")}\``); },
  h: () => $("helpbtn").click(), "?": () => $("helpbtn").click(),
  g: () => toggleGoals(),                            // (goals.js: the goals' card, or away again)
  keyz: () => Build.toggle(), b: () => Build.toggle(),       // (build.js: plan with a cursor, your character builds. keyz: the key under A, by place)
  v: () => nextView(),                               // (options.js: how what hides you is shown, the next way)
  f3: () => F3.toggle(),                             // (f3.js: the debug screen)
  t: () => openChat(),
  enter: () => openChat(),
  "/": () => openChat("/"),
};

addEventListener("keydown", (e) => {
  if (document.activeElement === $("name")) { if (e.key === "Enter") $("join").click(); return; }
  if (document.activeElement === $("say") || document.activeElement === $("letter") || !me) return;
  const k = keyId(e);                                 // (options.js: by place for walking, break, build, the numbers)
  if (k === "shift") { keys.add("shift"); if (Build.on) return; if (opt("sprint") === "hold") runKey = true; else if (!e.repeat) runKey = !runKey; syncWalk(); return; }      // (the settings' Sprint; in build mode your character walks by itself)
  inputMode = "keys"; document.body.classList.add("bykeys");
  if (k === " ") e.preventDefault();                   // (whatever it does: no scroll, no focused button pressed)
  if (k === "escape" && Build.on && !isOpen("craft") && !isOpen("bag") && !isOpen("mail")) { Build.onKey(k, e); return; }
  if (k === "escape") { if (isOpen("bag") && bagKey(k, e)) return; if (isOpen("craft") || isOpen("bag") || isOpen("mail")) closePanels(); else if (!isOpen("ask")) openMenu(); return; }      // (nothing to shut: the menu, menu.js)
  // an open panel takes the arrows, Enter and Space
  const u = usualKey(k);                              // (options.js: the key's action as the settings have it, by its usual key)
  if (isOpen("craft") && (craftKey(k, e) || !BOOK_KEYS.has(u))) { e.preventDefault(); return; }
  if (isOpen("bag") && (bagKey(k, e) || !BOOK_KEYS.has(u))) { e.preventDefault(); return; }      // (the inventory's keys are its own too: bag.js)
  if (Build.onKey(k, e)) { e.preventDefault(); return; }                  // (build mode: the cursor's keys are its own, build.js)
  if (e.altKey && CODEDIR[e.code]) { e.preventDefault(); turn(CODEDIR[e.code]); return; }
  if (KEYDIR[k]) {   // only a real press counts: a held key's auto-repeat must not cancel a chop in progress
    e.preventDefault();
    if (!e.repeat) { keys.delete(k); keys.add(k); syncWalk(); }
    return;
  }
  if (/^[0-9]$/.test(k) && meObs) { selectSlot((+k + 9) % 10); return; }      // a slot of your bar (0: the tenth), an empty one too
  if (k === "tab") { e.preventDefault(); if (!e.repeat) tabDown(u, e); return; }
  const fn = SHORTCUTS[u];
  if (fn) { e.preventDefault(); if (!e.repeat || HELD.has(u) || (u === " " && walking && !autoJump())) fn(e); }      // (Space held while walking: a jump each step, auto-jump off; on, a hop: walk.js)
});
// Tab: the next thing in hand at once; held, the day, you, who is awake (who.js, style.css), and the hand as it was
let tabWho = null; function tabDown(u, e) {
  const was = handSlot, who = () => { drawWho(); document.body.classList.add("tab"); };
  if (u !== "tab") return SHORTCUTS[u] ? SHORTCUTS[u](e) : who();      // (Tab given to another action, or none)
  SHORTCUTS.tab(e); clearTimeout(tabWho); tabWho = setTimeout(() => { tabWho = null; if (meObs && handSlot !== was) selectSlot(was); who(); }, 350);
}
addEventListener("keyup", (e) => {
  const k = keyId(e);
  if (k === " " && me && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) e.preventDefault();      // (Space is the jump: it presses no button that has the focus, scrolls nothing)
  keys.delete(k);
  if (k === "shift") { keys.delete("shift"); if (opt("sprint") === "hold") runKey = false; }
  if (k === "tab") { clearTimeout(tabWho); document.body.classList.remove("tab"); }
  syncWalk();
});
addEventListener("blur", () => { clearTimeout(tabWho); runKey = false; keys.clear(); document.body.classList.remove("tab"); syncWalk(); });
$("goalhide").onclick = $("goalhint").onclick = () => toggleGoals();
$("goals").onclick = (e) => { if (me && !e.target.closest(".gf")) { drawWho(); document.body.classList.toggle("tab"); } };   // (a phone has no Tab: a tap on the goals; who.js)
