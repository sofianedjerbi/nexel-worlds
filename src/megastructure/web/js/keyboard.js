// Keyboard: the whole game is playable without a mouse.
//   WASD / arrows walk (Shift sprints), Alt+direction turns on the spot, Space does the main action on the tile
//   you face and X the alternative one (milk, take down, till). 1-9 / Q pick what's in your hand, 0 empties it.
//   C crafting and I inventory are navigated with the arrows, Enter uses, Esc closes. 1-9 and 0: the ten slots of
//   your bar (an empty one: empty hands), ` empty hands.
//   While the recipe book is open the keys are its own (craft.js): none of them acts on the world behind it (X took
//   down what you faced, a number changed what you hold), but for the ones in BOOK_KEYS. One of the book and the
//   inventory is open at a time. What a key does there is written on it (a cap on the button, `kbd`) while you
//   play by keys (body.bykeys), and put away when the mouse moves.
//   B: build mode (build.js): the arrows move a cursor, Space plans the piece in hand, your character builds.

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
const INSTANT_DIG = "bFQf;\"w?!rmqyp";
function isQuick(f) {
  if (f.it.attack || f.it.here) return true;
  const c = combAt(f.p.x, f.p.y);
  return !placingItem() && !!c && INSTANT_DIG.includes(c);
}
const useful = (it) => it && !it.walk && !it.info && it.ok !== false;
// Who you're fighting: set when you hit someone or someone hits you, so Space keeps hitting them, not the tree beside.
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
// What Space (alt = false) or X (alt = true) does, without having to turn first. Fighting comes first: the one
// you're fighting, then any wild enemy within reach; then the tile you face; then other creatures within reach; then
// anything next to you, preferring the direction you last walked. Falls back to a hint about the faced tile.
// Holding something to place (a block, path, planks, dirt, seeds): Space puts it on the tile in front of you, and
// only there (the ghost shows it, green or red). Walk to aim: a tap turns you and moves you a tile.
const placingItem = () => selected && (PLACEABLE_BLOCK[selected] || FILLS[selected] || selected === "seed");
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
function facingNow(alt) {
  const q = facingTile(), s = myPos(); if (!q || !s) return null;
  if (!alt && placingItem()) {
    const it = intent(q, false);
    if (it && it.own) return it.none ? null : {p: it.own, it};          // (a ladder, facing a wall: it goes where you stand, against it: climbing.js)
    if (entityAt(q)) return {p: q, it: {text: "Something is in the way", ok: false, ghost: selected}};
    return it ? {p: q, it: it.ok === false || inReach(q, it) ? it : {...it, ok: false, text: TOO_HIGH}} : null;
  }
  const reach = reachOf(inHand()), dist = (o) => Math.abs(o.tx - s.x) + Math.abs(o.ty - s.y);
  const near = alt ? [] : [...ents.values()]                // (within reach: a circle, height counted: intent.js reaches)
    .filter((o) => o.e && !(o.e.kind === "agent" && o.e.id === myId) && reaches(o.tx, o.ty, reach, standsAt(o)))
    .sort((a, b) => dist(a) - dist(b));
  const hit = (o) => { const p = {x: o.tx, y: o.ty}, it = intent(p, false); return useful(it) && it.attack ? {p, it} : null; };
  if (foe && performance.now() < foe.until) {
    const o = ents.get(foe.key), r = o && near.includes(o) && hit(o);
    if (r) return r;
  }
  for (const o of near) if (WILD[o.e.kind] && o.e.kind !== "wisp") { const r = hit(o); if (r) return r; }
  const here = {x: s.x, y: s.y}, under = combAt(s.x, s.y);           // something growing under your feet
  if (!alt && under && !GROUND.has(under) && !SOLID.has(under)) { const it = intent(here, false); if (useful(it)) return {p: here, it}; }
  const faced = intent(q, alt);
  const hs = myZ(s.x, s.y), level = (t, it) => it.flat || it.ent || it.z !== undefined || it.at !== undefined || Math.abs(settleNear(t.x, t.y, hs) - hs) <= 2;   // (what grows on ground three levels over or under you is not offered: "Pick flower" from the bottom of a shaft, under the flower)
  if (useful(faced) && inReach(q, faced) && level(q, faced)) return {p: q, it: faced};
  // a pickaxe in hand, facing higher ground with nothing on it: cut into it (it comes down a layer)
  // (Space only. It took X too, and came before X's own "dig down": in a hole every second X cut the wall at your
  // feet and not the floor: two presses a layer, nothing to see on the odd one.) Its name: in a hole there is no hill
  if (!alt && inHand() === "pickaxe" && landSolid(q.x, q.y, hs + 1) && (GROUND.has(combAt(q.x, q.y)) || floorAt(q.x, q.y) !== hs + 1))      // (...or what is on it stands elsewhere: on the hill over your tunnel)
    return {p: q, it: {text: topAt(s.x, s.y) > hs ? "Dig on" : inHole(s, q, hs) ? "Dig into the wall" : "Dig into the hill", flat: true, cell: hs + 1,   // (under the land there is no hill: the tunnel goes on)
      run: () => act("dig", {dir: dirTo(q), with: "pickaxe"})}};
  // X with a pickaxe and nothing else to use it on: dig down where you stand
  if (alt && inHand() === "pickaxe" && under && GROUND.has(under) && !":n".includes(under))
    return {p: here, it: {text: "Dig down", here: true, run: () => act("dig_down", {with: "pickaxe"})}};
  for (const o of near) { const p = {x: o.tx, y: o.ty}, it = intent(p, false); if (useful(it) && inReach(p, it)) return {p, it}; }
  // then anything within reach (USE_R): nearest first, in front of you before behind
  const p0 = ents.get("agent" + myId), ring = [];
  for (let dy = -USE_R; dy <= USE_R; dy++) for (let dx = -USE_R; dx <= USE_R; dx++) {
    if ((!dx && !dy) || !reaches(s.x + dx, s.y + dy, USE_R)) continue;
    ring.push({x: s.x + dx, y: s.y + dy, d: Math.max(Math.abs(dx), Math.abs(dy)) + Math.abs(dx) * .01 + Math.abs(dy) * .01 - (dx * p0.fx + dy * p0.fy) * .1});
  }
  ring.sort((a, b) => a.d - b.d);
  for (const q of ring) { const p = {x: q.x, y: q.y}, it = intent(p, alt); if (useful(it) && level(p, it) && inReach(p, it)) return {p, it}; }      // (inReach: not through the land: "Chop tree" from a tunnel four layers under it)
  // (what is in front of you but up a cliff or down one is not offered, and not refused in red either ("Out of
  // reach" for a flower three layers up): nothing is said of what your hand cannot get to)
  return faced && !faced.walk && !useful(faced) && inReach(q, faced) ? {p: q, it: faced} : null;
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
  if (inputMode === "keys") { const a = facingIntent(false); return a && wayHides(WayShow.offer(), a, "use") ? null : a; }      // (the way out is shown: no bracket on a wall to dig: "two brackets, two Space")
  if (!mouse.in) return null;
  const p = aimAt(tileAtScreen(mouse.x, mouse.y), keys.has("shift")), it = intent(p, keys.has("shift"));
  return {p: (it && it.own) || p, it};
}
// While the way out of the ground is shown (wayshow.js) nothing else is offered for what you face: "Space Dig into the
// wall" two levels under the grass, "Space Dig on / X Dig down" written on its dots, "Lay floor" in the pocket with a
// plank in hand. But what also gets you up: a ladder or stairs in hand, where they can go (the keys still do what
// they did: only the words are put away).
const wayHides = (way, f, key) => !!way && !(way.key !== key && f.it.ok !== false && /ladder|stairs/i.test(f.it.text));
// Bottom right: what you can do right now, each with its key. Rebuilt every frame, written only when it changes.
let actionsHtml = "", faceRows = [];               // (faceRows: what Space and X do to what you face, beside it: prompts.js)
function availableActions() {
  if (!me || !meObs) return [];
  if (Build.on) return Build.rows();
  const s = myPos(), rows = [];
  const way = WayShow.offer(), m0 = facingIntent(false), a0 = facingIntent(true), main = m0 && wayHides(way, m0, "use") ? null : m0, alt = a0 && wayHides(way, a0, "alt") ? null : a0;
  if (way && way.key) rows.push([capOf(way.key), way.text, "way", true, true]);              // (the fifth: its cap is by its block; its word is in the corner, lit; a phone's button says it)
  if (main && !main.it.info && main.it.ok !== false) rows.push([capOf("use"), main.it.text, "", true]);      // (the keys as the settings have them: options.js; true: what you face)
  else if (main && placingItem()) rows.push([capOf("use"), main.it.text, "bad", true]);           // why it can't go there
  if (alt && !alt.it.info && alt.it.ok !== false && (!main || alt.it.text !== main.it.text)) rows.push([capOf("alt"), alt.it.text, "", true]);
  const up = way ? null : DigUp.aim();                                   // (the way out of a hole: the cell over your head, then the step: digup.js)
  if (up) rows.push([capOf("up"), up.text, "", true]);
  if (selected && FOODS.includes(selected)) rows.push([capOf("eat"), `Eat ${label(selected)}`]);
  if (selected && WEAR[selected]) rows.push([capOf("eat"), `Wear ${label(selected)}`]);
  if (s && groundItems.some(([x, y]) => x === s.x && y === s.y)) rows.push([capOf("pick"), "Pick up"]);
  if (way) return rows;
  if (Build.waiting()) rows.push([capOf("build"), `Build: ${Build.waiting()} plans wait`]);      // (build.js: said where it helps, a piece in hand or plans left)
  else if (placingItem() && !FOOT[PLACEABLE_BLOCK[selected]]) rows.push([capOf("build"), "Build mode: plan a lot"]);
  return rows;   // only what you can do right here, right now (all the other keys are in the help, H)
}
// The corner: what is not beside what it acts on (prompts.js): in build mode its name and Esc; by keys, all but
// what you face
function updateActions() {
  const all = availableActions(), keys = inputMode === "keys", aim = keys && !Build.on ? facingIntent(false) : null;
  const beside = !!aim && !aim.it.info && !aim.it.walk;      // (something you face is marked: its keys go beside it. Nothing is: they stay in the corner. X's "Dig down" on open meadow was shown nowhere)
  faceRows = Build.on || !keys || !beside ? [] : all.filter((r) => r[3] && !r[4]);
  const corner = Build.on ? all.filter(([k]) => k === capOf("build") || k === "Esc") : keys && beside ? all.filter((r) => !r[3] || r[4]) : all;      // (the way out's key: on its block, and here with its word: "R Dig up": "which key ?")
  const html = corner.map(([k, t, cls]) => `<div class="${cls || ""}"><span class="key">${esc(k)}</span>${esc(t)}</div>`).join("");
  if (html === actionsHtml) return;
  actionsHtml = html;
  const el = $("actions"); el.innerHTML = html; el.style.display = html ? "block" : "none";
}
function useFacing(alt) {
  if (DigUp.route(alt ? "alt" : "use")) return;    // (the way out's next block is this key's: that block, whatever you hold or face: digup.js)
  WayShow.mine();
  const f = facingNow(alt);                        // (a key pressed: as things are this instant, not as kept)
  if (!f) return;                                  // (nothing there to act on: no row beside it, the button blank; it said "Nothing within reach." at each press, eight in a row in the chat)
  if (f.it.info) return toast(f.it.text);
  if (f.it.ok === false) return toast(f.it.text, true);
  if (walking && !isQuick(f)) return;             // Space never stops you: work that takes time waits until you stand
  perform(f.p, f.it);
}
function turn(dir) {
  const p = ents.get("agent" + myId); if (!p) return;
  [p.fx, p.fy] = DIRV[dir];
}
function selectItem(name) {
  if (name !== selected) sfx("pick");
  selected = name; $("hotbar").dataset.sig = "";
  if (meObs) drawHotbar(meObs.self.inventory);
}
function cycleHand(step) {                       // Q: the next item of the hotbar in hand (then empty hands)
  if (!meObs) return;
  const order = slotOrder(meObs.self.inventory).slice(0, BAR), have = order.filter(Boolean);
  if (!have.length) return;
  const i = have.indexOf(selected), j = i + step;
  selectItem(j < 0 ? have[have.length - 1] : j >= have.length ? null : have[j]);
  toast(selected ? `In hand: **${label(selected)}**` : "Empty hands");
}
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

const SHORTCUTS = {        // key -> what it does (when no panel takes the key)
  " ": () => useFacing(false),
  x: () => useFacing(true),
  r: () => DigUp.run(),
  f: () => act("pick_up", {}),
  e: () => useSelected(),
  q: () => cycleHand(1),
  "`": () => { selectItem(null); toast("Empty hands"); },
  c: () => { $("bag").style.display = "none"; toggleCraft(); },
  i: () => { if (isOpen("craft")) toggleCraft(); toggleBag(); },
  m: () => { setMuted(!muted); toast(`Sound **${muted ? "off" : "on"}** \`${capOf("mute")}\``); },
  h: () => $("helpbtn").click(), "?": () => $("helpbtn").click(),
  g: () => toggleGoals(),                            // (goals.js: the goals' card, or away again)
  z: () => Build.toggle(),                           // (build.js: plan with a cursor, your character builds)
  b: () => Build.toggle(),                           // (its first key, still)
  v: () => nextView(),                               // (options.js: how what hides you is shown, the next way)
  f3: () => { const d = $("debug"); d.style.display = d.style.display === "block" ? "none" : "block"; },
  t: () => openChat(),
  enter: () => openChat(),
  "/": () => openChat("/"),
};

addEventListener("keydown", (e) => {
  if (document.activeElement === $("name")) { if (e.key === "Enter") $("join").click(); return; }
  if (document.activeElement === $("say") || document.activeElement === $("letter") || !me) return;
  const k = e.key.toLowerCase();
  if (k === "shift") { keys.add("shift"); if (Build.on) return; if (opt("sprint") === "hold") runKey = true; else if (!e.repeat) runKey = !runKey; syncWalk(); return; }      // (the settings' Sprint; in build mode your character walks by itself)
  inputMode = "keys"; document.body.classList.add("bykeys");
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
  if (/^[0-9]$/.test(k) && meObs) {                 // a slot of your bar (0: the tenth); an empty one, or the one in hand again: empty hands
    const n = slots[(+k + 9) % 10]; selectItem(n && selected !== n ? n : null); if (!selected) toast("Empty hands"); return;
  }
  if (k === "tab") { e.preventDefault(); if (!e.repeat) { drawWho(); document.body.classList.add("tab"); } return; }   // held: the day, you, who is awake (style.css)
  const fn = SHORTCUTS[u];
  if (fn) { e.preventDefault(); if (!(e.repeat && u !== " " && u !== "x" && u !== "r")) fn(); }
});
addEventListener("keyup", (e) => {
  const k = e.key.toLowerCase();
  keys.delete(k);
  if (k === "shift") { keys.delete("shift"); if (opt("sprint") === "hold") runKey = false; }
  if (k === "tab") document.body.classList.remove("tab");
  syncWalk();
});
addEventListener("blur", () => { runKey = false; keys.clear(); document.body.classList.remove("tab"); syncWalk(); });
$("goalhide").onclick = $("goalhint").onclick = () => toggleGoals();
$("goals").onclick = (e) => { if (me && !e.target.closest(".gf")) { drawWho(); document.body.classList.toggle("tab"); } };   // (a phone has no Tab: a tap on the goals; who.js)
