// The game's menu (Esc) and its settings: a window in the help's manner (css/menu.css). First a short list (back to the
// game, settings, help, leave); the settings are four pages of rows, a row a name and what it is set to. The world does
// not stop behind it (others are in it). What a setting is and where it is kept: js/options.js.
//   Up, Down: a row · Left, Right: change it · Enter: flip it, or change a key · Tab: the next page · R: this page
//   as it came · Esc: back. Or the mouse: a click on a row, a drag on a bar.

const MENU = {open: false, view: "main", page: 0, at: 0, grab: null, drag: null, said: ""};
const menuOpen = () => MENU.open;
// The kinds of row. Each: {name, kind, get(), set(v), def} and what its kind needs.
const kept = (key) => ({get: () => opt(key), set: (v) => setOpt(key, v), def: OPT_DEFAULT[key]});
const slider = (name, key, more = {}) => ({name, kind: "slider", min: 0, max: 100, step: 10, unit: "%", hear: key, ...(typeof key === "string" ? kept(key) : {}), ...more});
const toggle = (name, key, more = {}) => ({name, kind: "toggle", ...(typeof key === "string" ? kept(key) : key), ...more});
const choice = (name, key, list) => ({name, kind: "choice", list, ...kept(key)});
const debugRow = (name, what) => toggle(name, {get: () => DEBUG[what], set: (v) => { DEBUG[what] = v; localStorage.setItem("megastructure-" + what, v ? "1" : "0"); }, def: false});
const f3Row = () => toggle("Debug screen (F3)", {get: () => F3.on, set: (v) => F3.set(v), def: false});      // (f3.js: where you are and what a frame costs, one screen)
const lo = (r) => (typeof r.min === "function" ? r.min() : r.min);
// The rows of the shader that is on: its colours, and what only it has (an old screen's lines, its bulge...)
const LOOK_HAS = [["scan", "Lines"], ["curve", "Screen bulge"], ["mask", "Colour stripes"], ["shift", "Colour fringe"], ["tape", "Tape wobble"], ["grid", "Pixel grid"]];
function lookRows(look) {
  if (!look) return [];
  const row = (name, what, more = {}) => slider("· " + name, null, {get: () => lookOpt(what, more.def ?? 100), set: (v) => setLookOpt(what, v, more.def ?? 100), def: 100, max: 200, step: 20, hear: null, ...more});
  return [...(look.pal ? [] : [row("Colour", "sat"), row("Warmth", "warm", {min: -100, max: 100, def: 0, unit: ""})]), row("Contrast", "con"), row("Haze", "haze", {min: 0, max: 100, def: 0}),
    ...LOOK_HAS.filter(([what]) => look[what]).map(([what, name]) => row(name, what))];
}
const pageRows = (i) => { const rows = MENU_PAGES[i][1]; return typeof rows === "function" ? rows() : rows; };
const HEAR = {master: "pick", steps: "step", work: "chop", fights: "hit", animals: "cluck", world: "water", ui: "pick"};      // a sound of the family, at its new level
const MENU_PAGES = [
  ["Sound", [
    toggle("Sound", {get: () => !muted, set: (v) => setMuted(!v), def: true}),
    slider("Everything", "master"), slider("Music", "music"),
    choice("Music plays", "often", [["often", "Often"], ["normal", "Now and then"], ["rarely", "Rarely"]]),
    slider("Footsteps", "steps"), slider("Tools and building", "work"), slider("Fights", "fights"), slider("Animals", "animals"),
    slider("The world", "world"), slider("Voices", "voices"), slider("Menus and clicks", "ui")]],
  ["Picture", [
    slider("Zoom", null, {get: () => (ZOOM.busy ? ZOOM.to : zoom), set: (v) => zoomBy(v - (ZOOM.busy ? ZOOM.to : zoom)), min: () => zoomLeast(), max: ZOOM.max, step: 1, unit: "", def: 3, hear: null}),
    choice("Sharpness", "sharp", [["auto", "Auto"], ["full", "Full"], ["light", "Light"]]),
    slider("Light at night", "night", {hear: null}),
    choice("Particles", "particles", [["all", "All"], ["fewer", "Fewer"], ["none", "None"]]),
    choice("Look", "look", [["hd", "HD"], ["classic", "Classic"]]), choice("Curved world", "curve", [["off", "Off"], ["near", "Near"], ["far", "Far"]]), toggle("Depth", "depth"), toggle("Clear water", "clearwater"), toggle("Water shimmer", "shimmer"), toggle("Shake on a hard fall", "shake"), toggle("Smooth zoom", "glide"), toggle("Hearts and gains over heads", "floats"),
    choice("What hides you", "above", VIEWS.map((v) => [v.key, v.name]))]],
  // (shader.js, sun.js) Which shader, then that shader's own settings (they change with it, and each shader keeps
  // its own), then what all of them share: how much of each thing, 0 (none) to 200
  ["Shaders", () => [
    choice("Shader", "shader", [["off", "Off"], ...Object.entries(SHADERS).map(([k, v]) => [k, v.name])]),
    ...lookRows(SHADERS[opt("shader")]),
    slider("Strength", "shaderk", {hear: null}), ...[["Glow", "glow"], ["Shadows", "shadows"], ["Shadow length", "shadowlen"]].map(([name, key]) => slider(name, key, {max: 200, step: 20, hear: null})),
    toggle("Land shadows", "landshade"), ...[["Water reflections", "reflect"],
      ["Light on water", "waterlight"], ["Sun rays", "rays"], ["Cloud shadows", "clouds"], ["Dark corners", "corners"]].map(([name, key]) => slider(name, key, {max: 200, step: 20, hear: null}))]],
  ["Screen", [
    toggle("Speech bubbles", "bubbles"), toggle("Names over heads", "names"),
    choice("A chat line stays", "chat", [[5, "5 seconds"], [10, "10 seconds"], [30, "30 seconds"], [600, "10 minutes"]]),
    toggle("Key hints", "hints"), toggle("Mouse tips", "tips"),
    toggle("Goals card", {get: () => !goalsOff, set: (v) => { goalsOff = !v; localStorage.setItem("megastructure-goals-off", v ? "0" : "1"); drawGoals(); }, def: false}),
    f3Row(), debugRow("Tile grid", "grid")]],
  ["Keys", [
    choice("Sprint", "sprint", [["hold", "Hold Shift"], ["toggle", "Shift once"]]),
    ...Object.entries(KEY_ACTIONS).map(([action, [, name]]) => ({name, kind: "key", action, get: () => keyOf(action), set: () => {}, def: KEY_ACTIONS[action][0]}))]],
];
const MENU_MAIN = [
  ["Back to the game", "Esc", () => closeMenu()],
  ["Settings", "", () => menuShow("opts")],
  ["Help", "H", () => { closeMenu(); toggleHelp(); }],
  ["Leave the world", "", () => location.reload()],
];
const menuRows = () => (MENU.view === "main" ? MENU_MAIN : pageRows(MENU.page));
function drawMenu() {
  const el = $("menu"), well = el.querySelector(".well"), top = well ? well.scrollTop : 0;
  if (MENU.view === "main") {
    el.innerHTML = `<div class="win small"><div class="hh"><b>Menu</b><span data-go="close"><kbd>Esc</kbd>back</span></div><div class="well">`
      + MENU_MAIN.map(([name, key], i) => `<div class="row big${i === MENU.at ? " on" : ""}${name === "Help" ? " konly" : ""}" data-i="${i}"><div class="name">${name}</div>${key ? `<kbd>${key}</kbd>` : ""}</div>`).join("")
      + `</div><div class="hf">The world does not stop</div></div>`;
    return;
  }
  const ctl = (r) => {
    const v = r.get();
    if (r.kind === "slider") return `<div class="bar"><i style="width:${(v - lo(r)) / (r.max - lo(r)) * 100}%"></i></div><div class="val">${v}${r.unit}</div>`;
    if (r.kind === "toggle") return `<div class="sw${v ? " yes" : ""}">${v ? "On" : "Off"}</div>`;
    if (r.kind === "choice") return `<div class="pick"><b data-d="-1">&lt;</b><span>${(r.list.find(([k]) => k === v) || r.list[0])[1]}</span><b data-d="1">&gt;</b></div>`;
    return MENU.grab === r.action ? `<div class="pick"><span>press a key</span></div>` : `<kbd>${keyCap(v)}</kbd>`;
  };
  el.innerHTML = `<div class="win"><div class="hh"><b>Settings</b><span data-go="back"><kbd>Esc</kbd>back</span></div>`
    + `<div class="tabs">${MENU_PAGES.map(([name], i) => `<div class="tab${i === MENU.page ? " on" : ""}${name === "Keys" ? " konly" : ""}" data-page="${i}">${name}</div>`).join("")}</div>`
    + `<div class="well">${menuRows().map((r, i) => `<div class="row${i === MENU.at ? " on" : ""}${JSON.stringify(r.get()) !== JSON.stringify(r.def) ? " own" : ""}" data-i="${i}"><div class="name">${r.name}</div><div class="ctl">${ctl(r)}</div></div>`).join("")}</div>`
    + `<div class="hf">${MENU.said || `<kbd>←</kbd><kbd>→</kbd><i class="konly">change</i><kbd>Tab</kbd><i class="konly">next page</i><span data-go="reset"><kbd>R</kbd>as it came</span>`}</div></div>`;
  const now = el.querySelector(".well"), on = now.querySelector(".row.on");
  now.scrollTop = top;
  if (on) { const a = on.offsetTop - now.offsetTop, b = a + on.offsetHeight; if (a < now.scrollTop) now.scrollTop = a - 4; else if (b > now.scrollTop + now.clientHeight) now.scrollTop = b - now.clientHeight + 4; }
}
function menuShow(view, page = MENU.page) { MENU.view = view; MENU.page = page; MENU.at = 0; MENU.grab = null; MENU.said = ""; drawMenu(); const w = $("menu").querySelector(".well"); if (w) w.scrollTop = 0; sfx("pick"); }
function openMenu(view = "main") {
  if (MENU.open) return;
  MENU.open = true; MENU.back = view;                      // (opened on the settings, from the first screen: Esc shuts it)
  if (typeof keys !== "undefined") { keys.clear(); runKey = false; if (me) syncWalk(); }      // (nobody goes on walking behind the menu)
  $("menu").style.display = "flex"; sfx("open");
  menuShow(view);
}
function closeMenu() { if (!MENU.open) return; MENU.open = false; MENU.grab = null; $("menu").style.display = "none"; sfx("close"); if (typeof titleDraw === "function") titleDraw(); }
function menuBack() { if (MENU.view === "opts" && MENU.back === "main") menuShow("main"); else closeMenu(); }
// A row is changed: d -1 or 1 (the arrows, a click on < or >), 0 (Enter, a click on the row), or `to` (a bar dragged)
function menuChange(i, d, to) {
  const r = menuRows()[i]; if (!r) return;
  MENU.at = i; MENU.said = "";
  if (MENU.view === "main") { if (d === 0) r[2](); else drawMenu(); return; }
  const v = r.get();
  if (r.kind === "slider") {
    const next = Math.max(lo(r), Math.min(r.max, to !== undefined ? Math.round(to / r.step) * r.step : v + (d || 1) * r.step));
    if (next !== v) { r.set(next); if (r.hear) sfx(HEAR[r.hear] || "pick"); }
  } else if (r.kind === "toggle") { if (d === 0 || (d > 0) !== v) { r.set(!v); sfx("pick"); } }
  else if (r.kind === "choice") { const n = r.list.length, at = Math.max(0, r.list.findIndex(([k]) => k === v)); r.set(r.list[(at + (d || 1) + n) % n][0]); sfx("pick"); }
  else if (d === 0) MENU.grab = r.action;                  // (a key: the next one pressed is it)
  drawMenu();
}
function menuReset() {                                      // this page as it came
  for (const r of pageRows(MENU.page)) if (r.kind !== "key" && JSON.stringify(r.get()) !== JSON.stringify(r.def)) r.set(r.def);
  if (MENU_PAGES[MENU.page][0] === "Keys") setOpt("keys", {});
  MENU.said = ""; sfx("pick"); drawMenu();
}
window.addEventListener("keydown", (e) => {                 // (before every other key of the game: none of them acts behind the menu)
  if (!MENU.open) return;
  e.stopImmediatePropagation();
  if (e.metaKey || e.ctrlKey) return;
  e.preventDefault();
  const k = e.key.toLowerCase(), n = menuRows().length;
  if (MENU.grab) {                                          // a key is being chosen
    if (["shift", "control", "alt", "meta"].includes(k)) return;
    const action = MENU.grab; MENU.grab = null;
    if (k !== "escape") MENU.said = bindKey(action, k) ? "" : `${keyCap(k)} is a key of the game's own: another one`;
    sfx(MENU.said ? "close" : "pick");
    return drawMenu();
  }
  if (k === "escape") return menuBack();
  if (k === "arrowup" || k === "arrowdown") { MENU.at = (MENU.at + (k === "arrowup" ? -1 : 1) + n) % n; MENU.said = ""; sfx("pick"); return drawMenu(); }
  if (k === "enter" || k === " ") return menuChange(MENU.at, 0);
  if (MENU.view !== "opts") return;
  if (k === "arrowleft" || k === "arrowright") return menuChange(MENU.at, k === "arrowleft" ? -1 : 1);
  if (k === "tab") return menuShow("opts", (MENU.page + (e.shiftKey ? -1 : 1) + MENU_PAGES.length) % MENU_PAGES.length);
  if (k === "r") menuReset();
}, true);
window.addEventListener("keyup", (e) => { if (MENU.open) e.stopImmediatePropagation(); }, true);
const menuBarAt = (e, bar) => { const b = bar.getBoundingClientRect(), r = menuRows()[MENU.drag]; return lo(r) + Math.max(0, Math.min(1, (e.clientX - b.left) / b.width)) * (r.max - lo(r)); };
// A finger in the list: it may be scrolling it. Nothing is done until it lifts where it came down (the click), or
// slides along a bar (the list could not be scrolled on a phone: its rows past the seventh were out of reach).
$("menu").addEventListener("pointerdown", (e) => {
  if (e.pointerType !== "touch" || !e.target.closest(".well")) return menuTap(e);
  const bar = e.target.closest(".bar"); MENU.tap = true; MENU.slid = false; MENU.x = e.clientX; MENU.drag = bar ? +bar.closest(".row").dataset.i : null;
});
$("menu").addEventListener("click", (e) => { if (!MENU.tap) return; MENU.tap = false; if (!MENU.slid && e.target.closest(".win")) menuTap(e); MENU.drag = null; });
function menuTap(e) {
  const row = e.target.closest(".row"), go = e.target.closest("[data-go]"), tab = e.target.closest(".tab");
  if (!e.target.closest(".win") || (go && go.dataset.go === "close")) return closeMenu();
  if (go) return go.dataset.go === "back" ? menuBack() : menuReset();
  if (tab) return menuShow("opts", +tab.dataset.page);
  if (!row) return;
  const i = +row.dataset.i, bar = e.target.closest(".bar"), side = e.target.closest("[data-d]");
  if (bar) { MENU.drag = i; menuChange(i, 0, menuBarAt(e, bar)); }
  else menuChange(i, side ? +side.dataset.d : 0);
}
addEventListener("pointermove", (e) => { if (!MENU.open || MENU.drag === null) return; if (MENU.tap && !MENU.slid && !(MENU.slid = Math.abs(e.clientX - MENU.x) > 6)) return; const bar = $("menu").querySelector(`.row[data-i="${MENU.drag}"] .bar`); if (bar) menuChange(MENU.drag, 0, menuBarAt(e, bar)); });
addEventListener("pointerup", () => { if (!MENU.tap) MENU.drag = null; }); addEventListener("pointercancel", () => { MENU.drag = null; MENU.tap = false; });
$("menubtn").onclick = () => openMenu();
addEventListener("keydown", (e) => {                         // Esc while you only watch (a player's Esc: keyboard.js)
  if (e.key === "Escape" && !me && !titleOpen() && !helpOpen() && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) openMenu();
});
