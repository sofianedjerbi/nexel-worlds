// Keyboard: walking, sprint, hotbar keys and shortcuts.

addEventListener("keydown", (e) => {
  if (document.activeElement === $("name")) { if (e.key === "Enter") $("join").click(); return; }
  if (document.activeElement === $("say") || !me) return;
  const k = e.key.toLowerCase();
  if (k === "shift") keys.add("shift");
  if (k === "escape") { $("bag").style.display = "none"; $("mail").style.display = "none"; selected = null; $("hotbar").dataset.sig = ""; if (meObs) drawHotbar(meObs.self.inventory); $("craft").style.display = "none"; }
  if (KEYDIR[k]) { e.preventDefault(); if (!e.repeat) { keys.delete(k); keys.add(k); } syncWalk(); return; }
  if (k === " ") { e.preventDefault(); interactFacing(); return; }
  if (k === "enter" || k === "t") { e.preventDefault(); openChat(); }
  else if (k === "/") { e.preventDefault(); openChat("/"); }
  else if (k === "f") act("pick_up", {});
  else if (k === "r") act("rest", {});
  else if (k === "e") useSelected();
  else if (k === "c") $("craftbtn").click();
  else if (k === "b") toggleBag();
  else if (k === "m") { muted = !muted; localStorage.setItem("megastructure-muted", muted ? "1" : "0"); toast(muted ? "Sound off (M)" : "Sound on (M)"); }
  else if (k === "h") $("helpbtn").click();
  else if (/^[1-9]$/.test(k) && meObs) { const n = slots[+k - 1]; if (n) { selected = selected === n ? null : n; $("hotbar").dataset.sig = ""; drawHotbar(meObs.self.inventory); } }
});
addEventListener("keyup", (e) => {
  keys.delete(e.key.toLowerCase()); if (e.key === "Shift") keys.delete("shift");
  const k = [...keys].find((k) => KEYDIR[k]);
  syncWalk();
});
let runKey = false;
addEventListener("keydown", (e) => { if (e.key === "Shift") { runKey = true; syncWalk(); } });
addEventListener("keyup", (e) => { if (e.key === "Shift") { runKey = false; syncWalk(); } });
addEventListener("blur", () => { runKey = false; keys.clear(); syncWalk(); });
function interactFacing() {                      // Space: do the obvious thing to the tile in front of you
  const p = ents.get("agent" + myId), s = myPos(); if (!p || !s) return;
  const q = {x: s.x + (p.fx || 0), y: s.y + (p.fy || (p.fx ? 0 : 1))};
  let it = intent(q, false);
  if (it && it.walk) it = {text: "Dig", near: 1, run: (d) => act("dig", inHand() ? {dir: d, with: inHand()} : {dir: d})};
  perform(q, it);
}
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
