// Keyboard: the whole game is playable without a mouse.
//   WASD / arrows walk (Shift sprints), Alt+direction turns on the spot, Space does the main action on the tile
//   you face and X the alternative one (milk, take down, till). 1-9 / Q pick what's in your hand, 0 empties it.
//   C crafting and B bag are navigated with the arrows, Enter uses, Esc closes.

const KEYDIR = {w: "N", arrowup: "N", s: "S", arrowdown: "S", a: "W", arrowleft: "W", d: "E", arrowright: "E"};
const CODEDIR = {KeyW: "N", ArrowUp: "N", KeyS: "S", ArrowDown: "S", KeyA: "W", ArrowLeft: "W", KeyD: "E", ArrowRight: "E"};
const keys = new Set();
let runKey = false;
let inputMode = "mouse";     // "keys" once you play with the keyboard: hints then follow the tile you face

function facingTile() {
  const p = ents.get("agent" + myId), s = myPos(); if (!p || !s) return null;
  return {x: s.x + (p.fx || 0), y: s.y + (p.fy || (p.fx ? 0 : 1))};
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
// you're fighting, then any gloom within reach; then the tile you face; then other creatures within reach; then
// anything next to you, preferring the direction you last walked. Falls back to a hint about the faced tile.
function facingIntent(alt) {
  const q = facingTile(), s = myPos(); if (!q || !s) return null;
  const reach = reachOf(inHand()), dist = (o) => Math.abs(o.tx - s.x) + Math.abs(o.ty - s.y);
  const near = alt ? [] : [...ents.values()]
    .filter((o) => o.e && !(o.e.kind === "agent" && o.e.id === myId) && Math.max(Math.abs(o.tx - s.x), Math.abs(o.ty - s.y)) <= reach)
    .sort((a, b) => dist(a) - dist(b));
  const hit = (o) => { const p = {x: o.tx, y: o.ty}, it = intent(p, false); return useful(it) && it.attack ? {p, it} : null; };
  if (foe && performance.now() < foe.until) {
    const o = ents.get(foe.key), r = o && near.includes(o) && hit(o);
    if (r) return r;
  }
  for (const o of near) if (o.e.kind === "gloom") { const r = hit(o); if (r) return r; }
  const faced = intent(q, alt);
  if (useful(faced)) return {p: q, it: faced};
  for (const o of near) { const p = {x: o.tx, y: o.ty}, it = intent(p, false); if (useful(it)) return {p, it}; }
  const p0 = ents.get("agent" + myId), dirs = [[p0.fx, p0.fy], [-p0.fx, -p0.fy], [p0.fy, p0.fx], [-p0.fy, -p0.fx]];
  for (const [dx, dy] of dirs) {
    if (!dx && !dy) continue;
    const p = {x: s.x + dx, y: s.y + dy}, it = intent(p, alt);
    if (useful(it)) return {p, it};
  }
  return faced && !faced.walk ? {p: q, it: faced} : null;
}
// The tile hints are drawn for: where the mouse points, or the tile you face when playing by keyboard.
function aimedTile() {
  if (!me) return null;
  if (inputMode === "keys") return facingIntent(false);
  if (!mouse.in) return null;
  const p = tileAtScreen(mouse.x, mouse.y);
  return {p, it: intent(p, keys.has("shift"))};
}
// Bottom right: what you can do right now, each with its key. Rebuilt every frame, written only when it changes.
let actionsHtml = "";
function availableActions() {
  if (!me || !meObs) return [];
  const s = myPos(), rows = [];
  const main = facingIntent(false), alt = facingIntent(true);
  if (main && !main.it.info && main.it.ok !== false) rows.push(["Space", main.it.text]);
  if (alt && !alt.it.info && alt.it.ok !== false && (!main || alt.it.text !== main.it.text)) rows.push(["X", alt.it.text]);
  if (selected && FOODS.includes(selected)) rows.push(["E", `Eat ${label(selected)}`]);
  if (s && groundItems.some(([x, y]) => x === s.x && y === s.y)) rows.push(["F", "Pick up"]);
  if (meObs.self.energy < 25) rows.push(["R", "Rest"]);
  return rows;   // only what you can do right here, right now (all the other keys are in the help, H)
}
function updateActions() {
  const html = availableActions().map(([k, t]) => `<div><span class="key">${esc(k)}</span>${esc(t)}</div>`).join("");
  if (html === actionsHtml) return;
  actionsHtml = html;
  const el = $("actions"); el.innerHTML = html; el.style.display = html ? "block" : "none";
}
function useFacing(alt) {
  const f = facingIntent(alt);
  if (!f || f.it.info) return toast(f ? f.it.text : "Nothing within reach.", !f);
  perform(f.p, f.it);
}
function turn(dir) {
  const p = ents.get("agent" + myId); if (!p) return;
  [p.fx, p.fy] = DIRV[dir];
}
function selectItem(name) {
  if (name !== selected) sfx("ui");
  selected = name; $("hotbar").dataset.sig = "";
  if (meObs) drawHotbar(meObs.self.inventory);
}
function cycleHand(step) {                       // Q: the next item of the hotbar in hand (then empty hands)
  if (!meObs) return;
  const order = slotOrder(meObs.self.inventory).slice(0, 9), have = order.filter(Boolean);
  if (!have.length) return;
  const i = have.indexOf(selected), j = i + step;
  selectItem(j < 0 ? have[have.length - 1] : j >= have.length ? null : have[j]);
  toast(selected ? `In hand: ${label(selected)}` : "Empty hands");
}
function closePanels() {
  for (const id of ["bag", "mail", "craft"]) $(id).style.display = "none";
  drawGoals();
}
function zoomBy(d) { zoom = Math.max(1, Math.min(6, zoom + d)); }

const SHORTCUTS = {        // key -> what it does (when no panel takes the key)
  " ": () => useFacing(false),
  x: () => useFacing(true),
  f: () => act("pick_up", {}),
  r: () => act("rest", {}),
  e: () => useSelected(),
  q: () => cycleHand(1),
  0: () => { selectItem(null); toast("Empty hands"); },
  "`": () => { selectItem(null); toast("Empty hands"); },
  c: () => { $("craftbtn").click(); if (isOpen("craft") && !craftFocus) craftKey("arrowright", {}); },
  b: () => toggleBag(),
  m: () => { muted = !muted; localStorage.setItem("megastructure-muted", muted ? "1" : "0"); toast(muted ? "Sound off (M)" : "Sound on (M)"); },
  h: () => $("helpbtn").click(),
  f3: () => { const d = $("debug"); d.style.display = d.style.display === "block" ? "none" : "block"; },
  t: () => openChat(),
  enter: () => openChat(),
  "/": () => openChat("/"),
  "+": () => zoomBy(1), "=": () => zoomBy(1), "-": () => zoomBy(-1),
};

addEventListener("keydown", (e) => {
  if (document.activeElement === $("name")) { if (e.key === "Enter") $("join").click(); return; }
  if (document.activeElement === $("say") || document.activeElement === $("letter") || !me) return;
  const k = e.key.toLowerCase();
  if (k === "shift") { keys.add("shift"); runKey = true; syncWalk(); return; }
  inputMode = "keys";
  if (k === "escape") { if (isOpen("craft") || isOpen("bag") || isOpen("mail")) closePanels(); else selectItem(null); return; }
  // an open panel takes the arrows, Enter and Space
  if (isOpen("craft") && craftKey(k, e)) { e.preventDefault(); return; }
  if (isOpen("bag") && bagKey(k, e)) { e.preventDefault(); return; }
  if (e.altKey && CODEDIR[e.code]) { e.preventDefault(); turn(CODEDIR[e.code]); return; }
  if (KEYDIR[k]) { e.preventDefault(); if (!e.repeat) { keys.delete(k); keys.add(k); } syncWalk(); return; }
  if (/^[1-9]$/.test(k) && meObs) { const n = slots[+k - 1]; if (n) selectItem(selected === n ? null : n); return; }
  const fn = SHORTCUTS[k];
  if (fn) { e.preventDefault(); if (!(e.repeat && k !== " " && k !== "x")) fn(); }
});
addEventListener("keyup", (e) => {
  const k = e.key.toLowerCase();
  keys.delete(k);
  if (k === "shift") { keys.delete("shift"); runKey = false; }
  syncWalk();
});
addEventListener("blur", () => { runKey = false; keys.clear(); syncWalk(); });

// held keys walk continuously on the server: one message when the direction or sprint changes, one to stop
let walking = null;   // {dir, run}
function syncWalk() {
  const k = [...keys].reverse().find((k) => KEYDIR[k]);
  const want = k && me ? {dir: KEYDIR[k], run: runKey} : null;
  if (want && walking && want.dir === walking.dir && want.run === walking.run) return;
  if (!want && !walking) return;
  const prev = walking;
  walking = want;
  const p = ents.get("agent" + myId);
  if (!want) {
    if (p) {
      p.walking = false;
      // a tap (or a release mid-step) completes the tile you're visibly entering, so nothing jumps back
      const [dx, dy] = DIRV[prev.dir];
      const nx = dx > 0 ? Math.ceil(p.x - .05) : dx < 0 ? Math.floor(p.x + .05) : Math.round(p.x);
      const ny = dy > 0 ? Math.ceil(p.y - .05) : dy < 0 ? Math.floor(p.y + .05) : Math.round(p.y);
      if ((nx !== p.tx || ny !== p.ty) && walkable(nx, ny)) {
        p.tx = nx; p.ty = ny; pred = {x: nx, y: ny, until: performance.now() + 600};
        rpc("act", {tool: "move_to", args: {x: nx, y: ny}});
        return;
      }
    }
    rpc("act", {tool: "stop", args: {}});
    return;
  }
  const [dx, dy] = DIRV[want.dir];
  if (p) {
    p.fx = dx; p.fy = dy; p.walking = true; p.running = want.run;
    p.moved = performance.now();
  }
  myAction = null;
  const mine = want;
  rpc("act", {tool: "walk", args: want.run ? {dir: want.dir, run: true} : {dir: want.dir}}).then((r) => {
    if (walking !== mine) return;              // replaced by a newer walk / stop
    walking = null; if (p) p.walking = false;
    if (r.ok && r.result.stopped === "blocked") { pred = null; const q = ents.get("agent" + myId); if (q) { q.fx = dx; q.fy = dy; } }
  });
}
