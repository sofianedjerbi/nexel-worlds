// The settings (Esc, then Settings; js/menu.js draws them): what each is by default, kept in this browser, and read
// by the code it changes with opt("name"). Loaded first: everything else may ask.
// "implement a full settings menu into the game (echap) like minecraft with lot of options".
//
// To add one: its default here, a row in menu.js (MENU_PAGES), and opt("name") where it acts. A setting that must do
// something the moment it changes (a volume, a class on the page) does it in optApply.

const OPT_DEFAULT = {
  // sound: each a share (0 to 100) of what audio.js SOUND sets
  master: 100, music: 100, steps: 100, work: 100, fights: 100, animals: 100, world: 100, voices: 100, ui: 100,
  often: "normal",        // how long the silences between two pieces of music are: often, normal, rarely
  // picture
  sharp: "auto",          // device px a CSS px: auto (2, and 1 on a machine that cannot keep up), full (2), light (1)
  above: "cut",           // what is built over you: cut (away), faded (VIEWS; an old browser's outline is cut, its circle faded: floors.js)
  night: 0,               // how much the night is lit up, 0 (as it is) to 100
  particles: "all",       // all, fewer, none
  shake: true,            // the ground shakes when a fall hurts
  glide: true,            // a zoom level glides into the next
  shimmer: true,          // the water's moving light and small waves
  curve: "far",           // the ground bends away to a horizon, with a sky over it (curve.js): off (the flat picture), near, far
  floats: true,           // hearts lost, things gained, written over heads
  clearwater: true,       // the water is seen through, to its bed (waterbed.js, vox_water.js); off: the water as one painted face
  depth: true,            // the land's depth: the sun's shadows, shade at a wall's foot, higher land lighter (sunland.js, vox_light.js); off: the land as it is painted
  // the sun's shadows (sunland.js, hd_sun.js): how dark, how long, 0 to 200
  shadows: 100, shadowlen: 100,
  // interface
  bubbles: true, names: true, chat: 10, hints: true, tips: true,
  // keys
  sprint: "hold",         // hold: while Shift is down; toggle: Shift once to run, once more to walk
  autojump: true,         // walking into a step with room over it jumps up it by itself (walk.js); off: it stops you, J jumps
  keys: {},               // action -> key, where it is not the usual one (KEY_ACTIONS)
};
const OPT = {v: {...OPT_DEFAULT}};
try { Object.assign(OPT.v, JSON.parse(localStorage.getItem("megastructure-options") || "{}")); } catch (e) { /* unreadable: the defaults */ }
for (const k of Object.keys(OPT.v)) if (!(k in OPT_DEFAULT) || typeof OPT.v[k] !== typeof OPT_DEFAULT[k]) { if (k in OPT_DEFAULT) OPT.v[k] = OPT_DEFAULT[k]; else delete OPT.v[k]; }
const opt = (k) => OPT.v[k];
function setOpt(k, v) {
  OPT.v[k] = v;
  const changed = Object.fromEntries(Object.entries(OPT.v).filter(([key, val]) => JSON.stringify(val) !== JSON.stringify(OPT_DEFAULT[key])));
  localStorage.setItem("megastructure-options", JSON.stringify(changed));
  optApply(k);
}
// What a setting changes at once (the rest is read where it is used).
function optApply(k) {
  if (typeof soundLevels === "function") soundLevels();                      // (audio.js: the volumes)
  if (k === "sharp" && typeof resize === "function") resize();
  document.body.classList.toggle("nohints", !opt("hints"));
  document.body.classList.toggle("notips", !opt("tips"));
}
addEventListener("DOMContentLoaded", () => optApply());

// What is built over you, two ways to show it: the floors and the roof of the house you are in (in build mode, all over
// the cursor's floor: floors.js) cut away, or drawn faint (hd_things.js). (Land over you: the HD look's x-ray window,
// whatever this says.) V goes from one to the next (keyboard.js); the Picture page has them too.
const VIEWS = [{key: "cut", name: "Cut away"}, {key: "faded", name: "Faded"}];
function nextView() {
  const i = VIEWS.findIndex((v) => v.key === opt("above")), v = VIEWS[(i + 1) % VIEWS.length];
  setOpt("above", v.key);
  toast(`What is built over you: **${v.name}** \`V\``);
}

// The sound families of audio.js (SOUND.mix) under the settings' sliders.
const SOUND_OPT = {Footsteps: "steps", Work: "work", Breaking: "work", Building: "work", Fights: "fights", Boss: "fights", Animals: "animals",
                   World: "world", Items: "world", Progress: "world", People: "voices", Interface: "ui"};
const soundShare = (family) => (SOUND_OPT[family] ? opt(SOUND_OPT[family]) / 100 : 1);
const particles = (n) => (opt("particles") === "none" ? 0 : opt("particles") === "fewer" ? Math.ceil(n / 3) : n);

// The keys that can be changed: action -> [its usual key (as keyboard.js SHORTCUTS names it), what it is called].
// Walking (WASD, the arrows), the bar's numbers, Shift, Tab, Enter and Esc stay what they are, and so do the keys of
// the windows (the book's, the inventory's, build mode's).
// (Jump: J. Every key round WASD has its action, and Shift sprints)
const KEY_ACTIONS = {use: [" ", "Use what you face"], alt: ["x", "Other use"], jump: ["j", "Jump"], pick: ["f", "Pick up"], eat: ["e", "Eat or wear"], next: ["q", "Next thing in hand"],
  hands: ["`", "Empty your hands"], craft: ["c", "Craft"], bag: ["i", "Inventory"], build: ["z", "Build mode"], up: ["r", "Dig up"], talk: ["t", "Talk"], mute: ["m", "Sound on or off"]};
const KEY_FIXED = new Set(["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright", "shift", "tab", "enter", "escape", "control", "alt", "meta", "capslock",
  "h", "?", "g", "v", "f3", "/", "+", "=", "-", "_", ..."0123456789"]);
const keyOf = (action) => opt("keys")[action] || KEY_ACTIONS[action][0];
// The key that was pressed -> the usual key of the action it now does ("": it does nothing any more)
function usualKey(k) {
  for (const a of Object.keys(KEY_ACTIONS)) if (keyOf(a) === k) return KEY_ACTIONS[a][0];
  return Object.values(KEY_ACTIONS).some(([d]) => d === k) ? "" : k;
}
// An action gets a key; the action that had it takes the one this had. -> could it?
function bindKey(action, k) {
  if (KEY_FIXED.has(k) || k.length > 1 && !/^f\d+$/.test(k)) return false;
  const keys = {...opt("keys")}, other = Object.keys(KEY_ACTIONS).find((a) => a !== action && keyOf(a) === k);
  if (other) keys[other] = keyOf(action);
  keys[action] = k;
  for (const a of Object.keys(keys)) if (keys[a] === KEY_ACTIONS[a][0]) delete keys[a];
  setOpt("keys", keys);
  return true;
}
// How a key is written on a cap: keyCap("x") -> "X"; of an action: capOf("use") -> "Space"
const keyCap = (k) => (k === " " ? "Space" : k.length === 1 ? k.toUpperCase() : k[0].toUpperCase() + k.slice(1));
const capOf = (action) => keyCap(keyOf(action));
