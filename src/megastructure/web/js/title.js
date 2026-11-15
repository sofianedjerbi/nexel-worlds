// The first screen: the classic menu (css/title.css). A list played with the arrows and Enter, or the mouse: who
// you are (Left and Right change it), Wake up, Just watch, Help, Sound. Your character stands in the window beside
// the field your name is written in, in the colour that name will have in the world (a colour comes from a name).
// The name used to float over a character standing outside the window: "player name position is awkward".
// A world that asks who you are (account.js) shows two steps before that one, one at a time: your email, then the
// code mailed to it. Each step has its own field and its own rows; the others are not on the screen.

const TITLE = {at: 1, step: "me", first: {me: "join", mail: "sendcode", code: "login"}, field: {me: "name", mail: "email", code: "code"},
  steps: {me: ["racepick", "join", "watch", "titlehelp", "titlesound", "logout"], mail: ["sendcode", "watch", "titlehelp", "titlesound"],
    code: ["login", "startover", "watch", "titlehelp", "titlesound"]},
  get rows() { return this.steps[this.step].filter((id) => id !== "logout" || ACCOUNT.session); }};
const titleOpen = () => $("joinbox").style.display !== "none" && !me;
function titleDraw() {
  const rows = TITLE.rows;
  document.querySelectorAll("#racepick, #joinbox .item").forEach((e) => e.classList.toggle("on", e.id === rows[TITLE.at]));
  $("titlesoundv").textContent = muted ? "off" : "on";
  $("logoutv").textContent = ACCOUNT.email;
  document.body.classList.toggle("title", titleOpen());
}
function titleStep() {                                       // the step the account is at: its field, its first row
  const step = accountStep(), moved = step !== TITLE.step || !$("joinbox").dataset.step;
  TITLE.step = $("joinbox").dataset.step = step;
  if (moved) {
    TITLE.at = TITLE.rows.indexOf(TITLE.first[step]);
    if (step === "mail") $("email").value = ACCOUNT.email;
    if (!document.body.classList.contains("touch")) $(TITLE.field[step]).focus();   // (type at once; a phone's keyboard would cover the screen)
  }
  titleDraw();
}
function titleMe(now) {                                      // you, breathing, as the world will draw you
  const c = $("titleme");
  if (titleOpen() && TITLE.step === "me" && IMG.character && IMG.character.complete && IMG.character.width) {
    const g = c.getContext("2d"); g.imageSmoothingEnabled = false; g.clearRect(0, 0, 24, 26);
    try { g.drawImage(wornSheet(agentTint($("name").value.trim() || "you"), null, myRace), (Math.floor(now / 140) % 8) * 48 + 12, 9, 24, 26, 0, 0, 24, 26); } catch (e) { /* sheets still loading */ }
  }
  requestAnimationFrame(titleMe);
}
const TITLE_GO = {
  racepick() { TITLE.at = TITLE.rows.indexOf("join"); titleGo(TITLE.at); },
  join() { const n = $("name").value.trim(); if (n) joinGame(n); else { $("name").classList.add("need"); $("name").focus(); } },
  watch() { $("joinbox").style.display = "none"; titleDraw(); },
  titlehelp() { $("helpbtn").click(); },
  titlesound() { setMuted(!muted); titleDraw(); },
  sendcode: accountCode, login: accountLogin, startover: accountOver, logout: accountOut,
};
function titleGo(i) {                                        // a row is chosen: by Enter on it, or a click
  TITLE.at = i; titleDraw();
  TITLE_GO[TITLE.rows[i]]();
}
function titleRace(d) { const keys = Races.RACES.map((r) => r.key); pickRace(keys[(keys.indexOf(myRace) + d + keys.length) % keys.length]); sfx("pick"); }
Object.keys(TITLE_GO).forEach((id) => {
  if (id !== "racepick") $(id).onclick = () => titleGo(TITLE.rows.indexOf(id));
  $(id).addEventListener("mouseenter", () => { TITLE.at = TITLE.rows.indexOf(id); titleDraw(); });
});
["name", "email", "code"].forEach((id) => $(id).addEventListener("input", () => $(id).classList.remove("need")));
$("code").addEventListener("input", () => { if ($("code").value.replace(/\D/g, "").length === 6) accountLogin(); });   // six digits: that is the code, no key to press
window.addEventListener("keydown", (e) => {                  // (before the game's keys, while the menu shows and the help does not)
  if (!titleOpen() || $("help").style.display === "block") return;
  const rows = TITLE.rows, d = {ArrowUp: -1, ArrowDown: 1}[e.key], side = {ArrowLeft: -1, ArrowRight: 1}[e.key];
  if (d) { TITLE.at = (TITLE.at + d + rows.length) % rows.length; titleDraw(); sfx("pick"); }
  else if (side && rows[TITLE.at] === "racepick") titleRace(side);
  else if (e.key === "Enter") titleGo(TITLE.at);
  else return;
  e.preventDefault(); e.stopImmediatePropagation();
}, true);
new MutationObserver(titleDraw).observe($("joinbox"), {attributes: true, attributeFilter: ["style"]});   // (shown again by the brand, hidden by a join)
titleStep(); requestAnimationFrame(titleMe); accountWho();
