// The help (H, or ?): a window in the recipe book's manner, a page at a time. It was one small panel of four long lines,
// every key of the game run together with dots between. Now: five pages (Move, Do, Carry, Build, Talk), five rows at most
// on each, a row a key drawn as a key and a few words on one line. Left and Right (or a click on a tab) turn the page; H or
// Esc shuts it. Its looks are css/help.css.

// A key in a row: "{use}" the player's own key for the action (options.js capOf), "~keyq" a key by place as this keyboard
// types it (keyCap: ZQSD on an AZERTY), else as written (build mode's keys are its own: X, E)
const HELP = [
  ["Move", [[["~w", "~a", "~s", "~d"], "Walk"], [["Shift"], "Sprint: hold it"], [["{jump}"], "Jump: up a step"], [["Alt"], "Turn without walking"], [["G"], "Goals: show or hide"]]],
  ["See", [[["+", "−"], "Zoom (or the wheel)"], [["V"], "What is built over you"]]],
  ["Do", [[["{use}"], "Use: open, harvest, eat"], [["{alt}", "X"], "Break: mine, chop, hit"], [["{pick}"], "Pick up"],
    [["Left click"], "{alt} there, or walk"], [["Right click"], "{use} there"]]],
  ["Carry", [[["1-9", "{next}"], "Slot in hand"], [["{hands}"], "Empty your hands"], [["{use}"], "Place what you hold"],
    [["{drop}"], "Drop one. Shift: all"], [["{bag}", "{craft}"], "Inventory, craft"]]],
  ["Build", [[["{build}", "B"], "Build mode: in and out"], [["←", "→"], "Move the cursor, not you"], [["Space"], "Plan a piece. Held: row"], [["X"], "Break, take down, dig"],
    [["~keyq", "E"], "Cursor a layer down, up"]]],
  ["Talk", [[["Enter"], "Talk"], [["ABC"], "Shout: IN CAPITALS"], [["Tab"], "Hold: who is awake"],
    [["{mute}"], "Sound on or off"], [["Esc"], "Menu and settings"]]],
];
let helpPage = 0;
const helpOpen = () => $("help").style.display === "block";
function drawHelp() {
  const said = (what) => what.replace(/\{(\w+)\}/g, (m, a) => capOf(a));      // (a row that names a key in its words, "X there": the player's own key, as its cap says)
  const cap = (k) => (k[0] === "{" ? said(k) : k[0] === "~" ? keyCap(k.slice(1)) : k);
  const keys = (ks) => [...new Set(ks.map(cap))].map((k) => `<kbd>${k}</kbd>`).join("");      // (Break given X: one X)
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
