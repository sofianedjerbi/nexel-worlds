// Procedural sound effects (WebAudio), started on the first gesture.

let audio = null, muted = localStorage.getItem("megastructure-muted") === "1";
function ac() { if (!audio) { audio = new (window.AudioContext || window.webkitAudioContext)(); } return audio; }
// start audio on the first gesture, not inside the first frame that plays a sound (creating it stalls ~100 ms)
for (const ev of ["pointerdown", "keydown"]) addEventListener(ev, () => { if (!muted) ac(); }, {once: true, capture: true});
function tone(freq, dur, type = "sine", vol = .2, slide = 0, delay = 0) {
  const a = ac(), t0 = a.currentTime + delay, o = a.createOscillator(), g = a.createGain();
  o.type = type; o.frequency.setValueAtTime(freq, t0); if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq * slide), t0 + dur);
  g.gain.setValueAtTime(vol, t0); g.gain.exponentialRampToValueAtTime(.0001, t0 + dur);
  o.connect(g).connect(a.destination); o.start(t0); o.stop(t0 + dur + .02);
}
function noise(dur, vol = .2, hp = 800, lp = 6000, delay = 0) {
  const a = ac(), t0 = a.currentTime + delay, n = Math.floor(a.sampleRate * dur), buf = a.createBuffer(1, n, a.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
  const src = a.createBufferSource(), g = a.createGain(), h = a.createBiquadFilter(), l = a.createBiquadFilter();
  h.type = "highpass"; h.frequency.value = hp; l.type = "lowpass"; l.frequency.value = lp;
  g.gain.value = vol; src.buffer = buf; src.connect(h).connect(l).connect(g).connect(a.destination); src.start(t0);
}
// Every sound is made here from tones and filtered noise. v is the volume for the listener's distance (0..1).
const SFX = {
  // footsteps, by ground
  step: (v) => noise(.05, .05 * v, 300, 1800),
  tock: (v) => { tone(260, .05, "triangle", .08 * v, .8); noise(.03, .04 * v, 800, 3000); },        // wooden floor, bridge
  click: (v) => { tone(900, .03, "square", .025 * v, .7); noise(.03, .05 * v, 1500, 6000); },       // cobble
  // strikes while digging, by material
  chop: (v) => { tone(150, .12, "triangle", .32 * v, .6); noise(.07, .16 * v, 400, 2500); },
  mine: (v) => { tone(880, .09, "square", .07 * v, .7); tone(1320, .12, "triangle", .1 * v, .8, .01); noise(.05, .1 * v, 2000, 8000); },
  dig: (v) => noise(.12, .14 * v, 150, 1200),
  thud: (v) => { tone(90, .1, "sine", .25 * v, .6); noise(.05, .08 * v, 100, 900); },                // bare hands
  rustle: (v) => { noise(.16, .1 * v, 1800, 7000); noise(.1, .06 * v, 2500, 8000, .07); },
  // something breaks / falls
  snap: (v) => { noise(.06, .3 * v, 600, 4000); tone(180, .18, "triangle", .2 * v, .5, .02); },
  crumble: (v) => { for (let i = 0; i < 5; i++) noise(.05, .14 * v, 300, 2500, i * .045); tone(120, .2, "sine", .12 * v, .6); },
  creak: (v) => { tone(210, .45, "sawtooth", .035 * v, .55); tone(150, .4, "triangle", .05 * v, .7, .05); },
  fallthud: (v) => { tone(70, .3, "sine", .4 * v, .5); noise(.25, .14 * v, 80, 900); noise(.3, .07 * v, 1800, 7000, .05); },
  // getting, placing, making
  collect: (v) => { tone(784, .07, "sine", .16 * v); tone(1175, .12, "sine", .14 * v, 1, .06); },
  place: (v) => { tone(110, .1, "sine", .3 * v, .7); noise(.05, .08 * v, 200, 1500); },
  clack: (v) => { tone(520, .05, "square", .05 * v, .6); noise(.05, .12 * v, 900, 5000); },          // stone, chest lid
  plant: (v) => { noise(.07, .07 * v, 1200, 5000); tone(620, .06, "sine", .06 * v, 1.3, .03); },
  craft: (v) => [523, 659, 784, 1046].forEach((f, i) => tone(f, .12, "triangle", .08 * v, 1, i * .06)),
  // bodies
  hit: (v) => { noise(.09, .28 * v, 300, 3000); tone(220, .1, "sawtooth", .08 * v, .5); },
  hurt: (v) => { tone(330, .18, "square", .06 * v, .55); noise(.08, .12 * v, 400, 2500); },
  swing: (v) => noise(.1, .07 * v, 900, 4000),
  poof: (v) => { noise(.3, .12 * v, 500, 3000); tone(700, .25, "sine", .07 * v, .4, .02); },
  eat: (v) => { noise(.05, .12 * v, 600, 3000); noise(.05, .12 * v, 600, 3000, .12); },
  die: (v) => tone(440, .7, "triangle", .15 * v, .3),
  // animals
  cluck: (v) => { tone(700, .05, "square", .04 * v, .8); tone(820, .06, "square", .04 * v, .7, .08); },
  chirp: (v) => { tone(1800, .05, "sine", .06 * v, 1.3); tone(2000, .05, "sine", .05 * v, 1.2, .08); },
  moo: (v) => { tone(160, .55, "sawtooth", .05 * v, .75); tone(165, .5, "triangle", .07 * v, .8); },
  // world
  water: (v) => noise(.18, .08 * v, 1500, 7000),
  whoosh: (v) => noise(.35, .14 * v, 300, 2500),
  crackle: (v) => { for (let i = 0; i < 6; i++) noise(.02, .1 * v, 2000, 8000, Math.random() * .4); },
  gate: (v) => { tone(300, .2, "sawtooth", .025 * v, 1.3); tone(240, .15, "triangle", .04 * v, 1.2); },
  orb: (v) => tone(1250 + Math.random() * 700, .09, "sine", .07 * v, 1.25),               // pitch varies, like a sparkle
  levelup: (v) => [523, 659, 784, 1046, 1319].forEach((f, i) => tone(f, .3, "triangle", .07 * v, 1, i * .07)),
  chime: (v) => [880, 1109, 1319].forEach((f, i) => tone(f, .25, "sine", .07 * v, 1, i * .09)),
  // interface
  ui: (v) => tone(1200, .03, "sine", .06 * v),
  buzz: (v) => tone(140, .12, "square", .04 * v, .9),
};
// The material a tile char is made of: picks the strike, break and place sounds.
const WOOD_CHARS = "TUtH#+&CBhLKgWVXJeqy?!rmFpz", STONE_CHARS = "M*%Y^Z", PLANT_CHARS = "bvfQ;\"wo";
function material(c) {
  return WOOD_CHARS.includes(c) ? "wood" : STONE_CHARS.includes(c) ? "stone" : PLANT_CHARS.includes(c) ? "plant" : "soil";
}
const STRIKE = {wood: "chop", stone: "mine", plant: "rustle", soil: "dig"};
const BREAK = {wood: "snap", stone: "crumble", plant: "rustle", soil: "dig"};
const PLACE = {wood: "place", stone: "clack", plant: "plant", soil: "dig"};
function sfx(name, x, y) {
  if (muted || !SFX[name]) return;
  let v = 1;
  if (x !== undefined) { const s = myPos(); if (!s) return; const d = Math.hypot(x - s.x, y - s.y); if (d > 12) return; v = Math.max(.15, 1 - d / 12); }
  try { SFX[name](v); } catch (e) { /* audio not available yet (needs a user gesture) */ }
}

// ---- effects: particles, shakes, pops, falling trees ------------------------------------
