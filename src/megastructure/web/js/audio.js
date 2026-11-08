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
const SFX = {
  step: (v) => noise(.05, .05 * v, 300, 1800),
  chop: (v) => { tone(150, .12, "triangle", .32 * v, .6); noise(.07, .16 * v, 400, 2500); },
  mine: (v) => { tone(880, .09, "square", .07 * v, .7); tone(1320, .12, "triangle", .1 * v, .8, .01); noise(.05, .1 * v, 2000, 8000); },
  dig: (v) => noise(.12, .14 * v, 150, 1200),
  pick: (v) => { tone(660, .07, "sine", .14 * v); tone(990, .1, "sine", .12 * v, 1, .06); },
  place: (v) => { tone(110, .1, "sine", .3 * v, .7); noise(.05, .08 * v, 200, 1500); },
  craft: (v) => [523, 659, 784, 1046].forEach((f, i) => tone(f, .12, "triangle", .08 * v, 1, i * .06)),
  hit: (v) => { noise(.09, .28 * v, 300, 3000); tone(220, .1, "sawtooth", .08 * v, .5); },
  eat: (v) => { noise(.05, .12 * v, 600, 3000); noise(.05, .12 * v, 600, 3000, .12); },
  water: (v) => noise(.18, .08 * v, 1500, 7000),
  die: (v) => tone(440, .7, "triangle", .15 * v, .3),
  ui: (v) => tone(1200, .03, "sine", .06 * v),
};
function sfx(name, x, y) {
  if (muted || !SFX[name]) return;
  let v = 1;
  if (x !== undefined) { const s = myPos(); if (!s) return; const d = Math.hypot(x - s.x, y - s.y); if (d > 12) return; v = Math.max(.15, 1 - d / 12); }
  try { SFX[name](v); } catch (e) { /* audio not available yet (needs a user gesture) */ }
}

// ---- effects: particles, shakes, pops, falling trees ------------------------------------
