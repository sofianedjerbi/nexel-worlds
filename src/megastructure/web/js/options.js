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
  night: 0,               // how much the night is lit up, 0 (as it is) to 100
  particles: "all",       // all, fewer, none
  shake: true,            // the ground shakes when a fall hurts
  glide: true,            // a zoom level glides into the next
  shimmer: true,          // the water's moving light and small waves
  floats: true,           // hearts lost, things gained, written over heads
  // interface
  bubbles: true, names: true, chat: 10, hints: true, tips: true,
  // keys
  sprint: "hold",         // hold: while Shift is down; toggle: Shift once to run, once more to walk
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

// The sound families of audio.js (SOUND.mix) under the settings' sliders.
const SOUND_OPT = {Footsteps: "steps", Work: "work", Breaking: "work", Building: "work", Fights: "fights", Boss: "fights", Animals: "animals",
                   World: "world", Items: "world", Progress: "world", People: "voices", Interface: "ui"};
const soundShare = (family) => (SOUND_OPT[family] ? opt(SOUND_OPT[family]) / 100 : 1);
const particles = (n) => (opt("particles") === "none" ? 0 : opt("particles") === "fewer" ? Math.ceil(n / 3) : n);

// The keys that can be changed: action -> [its usual key (as keyboard.js SHORTCUTS names it), what it is called].
// Walking (WASD, the arrows), the bar's numbers, Shift, Tab, Enter and Esc stay what they are, and so do the keys of
// the windows (the book's, the inventory's, build mode's).
const KEY_ACTIONS = {use: [" ", "Use what you face"], alt: ["x", "Other use"], pick: ["f", "Pick up"], eat: ["e", "Eat or wear"], next: ["q", "Next thing in hand"],
  hands: ["`", "Empty your hands"], craft: ["c", "Craft"], bag: ["i", "Inventory"], build: ["b", "Build mode"], talk: ["t", "Talk"], mute: ["m", "Sound on or off"]};
const KEY_FIXED = new Set(["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright", "shift", "tab", "enter", "escape", "control", "alt", "meta", "capslock",
  "h", "?", "g", "f3", "/", "+", "=", "-", "_", ..."0123456789"]);
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
