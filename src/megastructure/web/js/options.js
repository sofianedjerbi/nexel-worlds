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
  view: 13,               // how far you see, in tiles: where level ground meets the sky (hd.js viewOf), VIEW_MIN to VIEW_MAX in 4s (the bend's facets); a sixteenth of the picture stays sky: zoomed in, less far
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
  autojump: true,         // walking into a step with room over it jumps up it by itself (walk.js); off: it stops you, Space jumps
  keys: {},               // action -> key, where it is not the usual one (KEY_ACTIONS)
};
// the view distance's range, tiles (the bend's facets are 4 tiles: the horizon is at 1 + 4k): from the old Near to past the old Very far (37); the top
// as far as a desk and a phone keep a sprint within a frame, and the server gives far land (views.py FAR_VIEW); a short picture keeps a sixteenth of sky first (hd.js viewOf)
const VIEW_MIN = 9, VIEW_MAX = 65, VIEW_STEP = 4;
// what a setting was kept as before, and what it is now (the view distance was Near, Normal, Far, Very far)
const OPT_WAS = {view: {near: 9, normal: 13, far: 25, veryfar: 37}};
const OPT = {v: {...OPT_DEFAULT}};
try { Object.assign(OPT.v, JSON.parse(localStorage.getItem("megastructure-options") || "{}")); } catch (e) { /* unreadable: the defaults */ }
for (const [k, was] of Object.entries(OPT_WAS)) if (Object.prototype.hasOwnProperty.call(was, OPT.v[k])) OPT.v[k] = was[OPT.v[k]];
for (const k of Object.keys(OPT.v)) if (!(k in OPT_DEFAULT) || typeof OPT.v[k] !== typeof OPT_DEFAULT[k]) { if (k in OPT_DEFAULT) OPT.v[k] = OPT_DEFAULT[k]; else delete OPT.v[k]; }
const opt = (k) => OPT.v[k];
function setOpt(k, v) {
  OPT.v[k] = v;
  optSave();
  optApply(k);
}
function optSave() {
  const changed = Object.fromEntries(Object.entries(OPT.v).filter(([key, val]) => JSON.stringify(val) !== JSON.stringify(OPT_DEFAULT[key])));
  localStorage.setItem("megastructure-options", JSON.stringify(changed));
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
// Walking (WASD, the arrows), the bar's numbers, Shift, Enter and Esc stay what they are, and so do the keys of the
// windows (the book's, the inventory's, build mode's).
// (WASD walk, Space jumps, E uses what you face, the key over A breaks it: "you cannot push X while going right". E eats
// or wears what you hold too, there is no eat key: keyboard.js facingNow. Every key round WASD has its action)
// Break and build mode are by their place (keyq, keyz: the top-left and bottom-left letters, whatever they type: A and W
// on AZERTY); X still breaks and B still builds (keyboard.js SHORTCUTS); Tab the next thing in hand.
const KEY_ACTIONS = {use: ["e", "Use: open, place, eat"], alt: ["keyq", "Break: mine, chop, hit"], jump: [" ", "Jump"], pick: ["f", "Pick up"], next: ["tab", "Next thing in hand"],
  hands: ["`", "Empty your hands"], drop: ["keyy", "Drop one (Shift: all)"], craft: ["c", "Craft"], bag: ["i", "Inventory"], build: ["keyz", "Build mode"], up: ["r", "Dig up"], talk: ["t", "Talk"], mute: ["m", "Sound on or off"]};
// (Drop: the free key nearest the left hand, beside T and G, by its place: a German keyboard's Y and Z change places)
const KEY_FIXED = new Set(["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright", "shift", "enter", "escape", "control", "alt", "meta", "capslock",
  "h", "?", "g", "v", "f3", "/", "+", "=", "-", "_", ..."0123456789"]);
const bindable = (k) => typeof k === "string" && !KEY_FIXED.has(k) && (k.length === 1 || /^f\d+$/.test(k) || ["keyq", "keyz", "keyy", "tab"].includes(k));
const keyOf = (action) => opt("keys")[action] || KEY_ACTIONS[action][0];
// A key pressed -> its name for the game. Walking is by place (an AZERTY's Z Q S D are a QWERTY's W A S D: they walk,
// and are no letter's shortcut: the q there cycled the hand, the z opened build mode); so are keyq and keyz, the bar's
// numbers (an AZERTY types & é " ' without Shift) and ` (² there). The rest: the letter typed. (No code: a phone's pad.)
const KEY_CODE = {KeyW: "w", KeyA: "a", KeyS: "s", KeyD: "d", ArrowUp: "arrowup", ArrowDown: "arrowdown", ArrowLeft: "arrowleft", ArrowRight: "arrowright",
  KeyQ: "keyq", KeyZ: "keyz", KeyY: "keyy", Backquote: "`", ...Object.fromEntries([..."0123456789"].map((n) => ["Digit" + n, n]))};
// What the keys by place type on this keyboard, to write them on caps: the browser's map (Chrome), else learnt as they
// are pressed (walking west typed q: an AZERTY, so its KeyQ types a), else a QWERTY's
const LAYOUT = {KeyW: "w", KeyA: "a", KeyS: "s", KeyD: "d", KeyQ: "q", KeyZ: "z", KeyY: "y", Backquote: "`"}, LAYOUT_SEEN = new Set();
if (navigator.keyboard && navigator.keyboard.getLayoutMap) navigator.keyboard.getLayoutMap().then((m) => { for (const c of Object.keys(LAYOUT)) if (m.get(c)) { LAYOUT[c] = m.get(c); LAYOUT_SEEN.add(c); } }).catch(() => {});
function keyId(e) {
  const c = e.code || "";
  if (c in LAYOUT && e.key && e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
    LAYOUT[c] = e.key.toLowerCase(); LAYOUT_SEEN.add(c);
    const az = {KeyA: ["q", "KeyQ", "a"], KeyW: ["z", "KeyZ", "w"]}[c];            // (an AZERTY's A and Z change places with Q and W)
    if (az && LAYOUT[c] === az[0] && !LAYOUT_SEEN.has(az[1])) LAYOUT[az[1]] = az[2];
  }
  return KEY_CODE[c] || (e.key || "").toLowerCase();
}
// The key that was pressed -> the usual key of the action it now does ("": it does nothing any more)
function usualKey(k) {
  for (const a of Object.keys(KEY_ACTIONS)) if (keyOf(a) === k) return KEY_ACTIONS[a][0];
  return Object.values(KEY_ACTIONS).some(([d]) => d === k) ? "" : k;
}
// An action gets a key; the action that had it takes the one this had. -> could it?
function bindKey(action, k) {
  if (!bindable(k)) return false;
  const keys = {...opt("keys")}, other = Object.keys(KEY_ACTIONS).find((a) => a !== action && keyOf(a) === k);
  if (other) keys[other] = keyOf(action);
  keys[action] = k;
  for (const a of Object.keys(keys)) if (keys[a] === KEY_ACTIONS[a][0]) delete keys[a];
  setOpt("keys", keys);
  return true;
}
// A player's own keys, kept from before the usual ones changed (Space used, J jumped, E ate): each is given again as
// the menu gives it (bindKey: the action that had the key takes the one this had), over the usual keys of now, so no
// two actions share a key. The eat key is dropped (E uses, and eats). Given again to what it made: the same.
function keysAgain(own) {
  const now = Object.fromEntries(Object.entries(KEY_ACTIONS).map(([a, [k]]) => [a, k]));
  for (let [a, k] of Object.entries(own || {})) {
    if (k === "y") k = "keyy";                                  // (Y is by its place now: a Y given before is that key)
    if (!(a in now) || !bindable(k)) continue;
    const other = Object.keys(now).find((b) => b !== a && now[b] === k);
    if (other) now[other] = now[a];
    now[a] = k;
  }
  return Object.fromEntries(Object.entries(now).filter(([a, k]) => k !== KEY_ACTIONS[a][0]));
}
{ const k = keysAgain(OPT.v.keys); if (JSON.stringify(k) !== JSON.stringify(OPT.v.keys)) { OPT.v.keys = k; optSave(); } }
// How a key is written on a cap: keyCap("x") -> "X"; of an action: capOf("jump") -> "Space"; a key by place as this
// keyboard types it: keyCap("keyq") -> "A" on AZERTY, "Q" on QWERTY
const CAP_CODE = {w: "KeyW", a: "KeyA", s: "KeyS", d: "KeyD", keyq: "KeyQ", keyz: "KeyZ", keyy: "KeyY", "`": "Backquote"};
const keyCap = (k) => (CAP_CODE[k] ? LAYOUT[CAP_CODE[k]].toUpperCase() : k === " " ? "Space" : k.length === 1 ? k.toUpperCase() : k[0].toUpperCase() + k.slice(1));
const capOf = (action) => keyCap(keyOf(action));
