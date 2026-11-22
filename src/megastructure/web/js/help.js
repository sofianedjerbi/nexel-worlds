// The help (H, or ?): a window in the recipe book's manner, a page at a time. It was one small panel of four long lines,
// every key of the game run together with dots between. Now: five pages (Move, Do, Carry, Build, Talk), five rows at most
// on each, a row a key drawn as a key and a few words on one line. Left and Right (or a click on a tab) turn the page; H or
// Esc shuts it. Its looks are css/help.css.

const HELP = [
  ["Move", [[["W", "A", "S", "D"], "Walk"], [["Shift"], "Sprint: hold it"], [["Space"], "Jump: up a step"], [["Alt"], "Turn without walking"], [["G"], "Goals: show or hide"]]],
  ["See", [[["+", "−"], "Zoom (or the wheel)"], [["V"], "What is built over you"]]],
  ["Do", [[["E"], "Use: open, harvest, eat"], [["X"], "Break: mine, chop, hit"], [["F"], "Pick up"],
    [["Left click"], "{alt} there, or walk"], [["Right click"], "{use} there"]]],
  ["Carry", [[["1-9", "Q"], "Slot in hand"], [["`"], "Empty your hands"], [["E"], "Place what you hold"],
    [["I"], "Inventory"], [["C"], "Craft"]]],
  ["Build", [[["Z"], "Build mode: in and out"], [["←", "→"], "Move the cursor, not you"], [["Space"], "Plan a piece. Held: row"], [["X"], "Break, take down, dig"],
    [["Q", "E"], "Cursor a layer down, up"]]],
  ["Talk", [[["Enter"], "Talk"], [["ABC"], "Shout: IN CAPITALS"], [["Tab"], "Hold: who is awake"],
    [["M"], "Sound on or off"], [["Esc"], "Menu and settings"]]],
];
const HELP_ACT = {E: "use", X: "alt", Space: "jump", F: "pick", Q: "next", "`": "hands", I: "bag", C: "craft", Z: "build", M: "mute"};
let helpPage = 0;
const helpOpen = () => $("help").style.display === "block";
function drawHelp() {
  const mine = HELP[helpPage][0] !== "Build";            // (build mode's keys are its own; the others as the settings have them: options.js)
  const said = (what) => what.replace(/\{(\w+)\}/g, (m, a) => capOf(a));      // (a row that names a key in its words, "X there": the player's own key, as its cap says)
  const keys = (ks) => ks.map((k) => `<kbd>${mine && HELP_ACT[k] ? capOf(HELP_ACT[k]) : k}</kbd>`).join("");
  $("help").innerHTML = `<div class="hh"><b>Help</b><span><kbd>H</kbd>close</span></div>`
    + `<div class="tabs">${HELP.map(([name], i) => `<div class="tab${i === helpPage ? " on" : ""}" data-i="${i}">${name}</div>`).join("")}</div>`
    + `<div class="well">${HELP[helpPage][1].map(([ks, what]) => `<div class="row"><div class="keys">${keys(ks)}</div><div class="what">${said(what)}</div></div>`).join("")}</div>`
    + `<div class="hf"><kbd>←</kbd><kbd>→</kbd>turn the page</div>`;
}
function turnHelp(to) { helpPage = (to + HELP.length) % HELP.length; drawHelp(); sfx("pick"); }
function toggleHelp() { const on = !helpOpen(); if (on) drawHelp(); $("help").style.display = on ? "block" : "none"; sfx(on ? "open" : "close"); }
$("helpbtn").onclick = toggleHelp;                        // (the brand's link, the goals' key, H: keyboard.js)
$("help").addEventListener("click", (e) => { const t = e.target.closest(".tab"); if (t) turnHelp(+t.dataset.i); else if (e.target.closest(".hh span")) toggleHelp(); });
window.addEventListener("keydown", (e) => {               // (before the game's keys: the arrows turn pages, they do not walk you)
  if (!helpOpen() || document.activeElement === $("say")) return;
  const d = {ArrowLeft: -1, ArrowRight: 1, ArrowUp: -1, ArrowDown: 1}[e.key];
  if (d) turnHelp(helpPage + d); else if (e.key === "Escape") toggleHelp(); else return;
  e.preventDefault(); e.stopImmediatePropagation();
}, true);
localStorage.removeItem("megastructure-help");            // (it used to open by itself at each join: a window in the middle does not)
