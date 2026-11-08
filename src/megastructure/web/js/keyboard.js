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
// What Space (alt = false) or X (alt = true) would do on the tile you face; nothing for plain walkable ground.
function facingIntent(alt) {
  const q = facingTile(); if (!q) return null;
  const it = intent(q, alt);
  return it && !it.walk ? {p: q, it} : null;
}
// The tile hints are drawn for: where the mouse points, or the tile you face when playing by keyboard.
function aimedTile() {
  if (!me) return null;
  if (inputMode === "keys") return facingIntent(false);
  if (!mouse.in) return null;
  const p = tileAtScreen(mouse.x, mouse.y);
  return {p, it: intent(p, keys.has("shift"))};
}
// The keyboard prompt above the hotbar: what Space and X would do right now.
let promptText = "";
function updatePrompt() {
  let text = "";
  if (me && inputMode === "keys") {
    const main = facingIntent(false), alt = facingIntent(true);
    const parts = [];
    if (main) parts.push(`<b>Space</b> ${esc(main.it.text)}`);
    if (alt && (!main || alt.it.text !== main.it.text)) parts.push(`<b>X</b> ${esc(alt.it.text)}`);
    text = parts.join("<i>·</i>");
  }
  if (text === promptText) return;
  promptText = text;
  const el = $("prompt"); el.innerHTML = text; el.style.display = text ? "block" : "none";
}
function useFacing(alt) {
  const f = facingIntent(alt);
  if (!f) return toast(alt ? "Nothing to do there." : "Nothing there. Face something (Alt+direction turns).", true);
  perform(f.p, f.it);
}
function turn(dir) {
  const p = ents.get("agent" + myId); if (!p) return;
  [p.fx, p.fy] = DIRV[dir];
}
function selectItem(name) {
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
