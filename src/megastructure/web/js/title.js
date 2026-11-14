// The first screen: the classic menu (css/title.css). A list played with the arrows and Enter, or the mouse: who
// you are (Left and Right change it), Wake up, Just watch, Help, Sound. Your character stands in the window beside
// the field your name is written in, in the colour that name will have in the world (a colour comes from a name).
// The name used to float over a character standing outside the window: "player name position is awkward".

const TITLE = {rows: ["racepick", "join", "watch", "titlehelp", "titlesound"], at: 1};
const titleOpen = () => $("joinbox").style.display !== "none" && !me;
function titleDraw() {
  TITLE.rows.forEach((id, i) => $(id).classList.toggle("on", i === TITLE.at));
  $("titlesoundv").textContent = muted ? "off" : "on";
  document.body.classList.toggle("title", titleOpen());
}
function titleMe(now) {                                      // you, breathing, as the world will draw you
  const c = $("titleme");
  if (titleOpen() && IMG.character && IMG.character.complete && IMG.character.width) {
    const g = c.getContext("2d"); g.imageSmoothingEnabled = false; g.clearRect(0, 0, 24, 26);
    try { g.drawImage(wornSheet(agentTint($("name").value.trim() || "you"), null, myRace), (Math.floor(now / 140) % 8) * 48 + 12, 9, 24, 26, 0, 0, 24, 26); } catch (e) { /* sheets still loading */ }
  }
  requestAnimationFrame(titleMe);
}
function titleGo(i) {                                        // a row is chosen: by Enter on it, or a click
  TITLE.at = i; titleDraw();
  if (i === 1) { const n = $("name").value.trim(); if (n) joinGame(n); else { $("name").classList.add("need"); $("name").focus(); } }
  else if (i === 2) { $("joinbox").style.display = "none"; titleDraw(); }
  else if (i === 3) $("helpbtn").click();
  else if (i === 4) { setMuted(!muted); titleDraw(); }
}
function titleRace(d) { const keys = Races.RACES.map((r) => r.key); pickRace(keys[(keys.indexOf(myRace) + d + keys.length) % keys.length]); sfx("pick"); }
$("join").onclick = () => titleGo(1); $("watch").onclick = () => titleGo(2); $("titlehelp").onclick = () => titleGo(3); $("titlesound").onclick = () => titleGo(4);
TITLE.rows.forEach((id, i) => $(id).addEventListener("mouseenter", () => { TITLE.at = i; titleDraw(); }));
$("name").addEventListener("input", () => $("name").classList.remove("need"));
window.addEventListener("keydown", (e) => {                  // (before the game's keys, while the menu shows and the help does not)
  if (!titleOpen() || $("help").style.display === "block") return;
  const d = {ArrowUp: -1, ArrowDown: 1}[e.key], side = {ArrowLeft: -1, ArrowRight: 1}[e.key];
  if (d) { TITLE.at = (TITLE.at + d + TITLE.rows.length) % TITLE.rows.length; titleDraw(); sfx("pick"); }
  else if (side && TITLE.at === 0) titleRace(side);
  else if (e.key === "Enter") { if (TITLE.at === 0) TITLE.at = 1; titleGo(TITLE.at); }
  else return;
  e.preventDefault(); e.stopImmediatePropagation();
}, true);
new MutationObserver(titleDraw).observe($("joinbox"), {attributes: true, attributeFilter: ["style"]});   // (shown again by the brand, hidden by a join)
titleDraw(); requestAnimationFrame(titleMe);
if (!document.body.classList.contains("touch")) $("name").focus();      // (type your name at once; a phone's keyboard would cover the screen)
