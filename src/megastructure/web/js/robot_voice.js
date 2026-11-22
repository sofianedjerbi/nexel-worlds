// A robot's voice, for the AI players: the same recorded "say" syllables as a person's babble (babble.js), on the same
// grid of time (a syllable for every two letters, a breath at a space, at most BABBLE.most s), the same voice of their
// own from their name (voiceOf), a question still rising and a shout still a yell. Only the sound is made a machine's,
// out of the recordings themselves: nothing here is a made-up tone that is heard on its own.
//   chip  the recording held in steps and cut to few levels (a lower sample rate, fewer bits): an old game's robot
//   ring  the recording times a slow wave (ring modulation): the classic film robot's buzz
//   comb  the recording through a very short echo fed back on itself, tuned to the speaker: a steady metal hum
//   tin   each syllable said as quick grains, as if read off a tape, out of a small tin box
// Not used by the game yet (design/enemies/site/robots.html plays them); babble.js would call robotSay for an AI player.

const ROBOT = {
  chip: {steps: 2, hold: 5800, bits: 5, shoutBits: 4, level: 1, shout: 1},     // whole tones; Hz it is held at; bits
  ring: {steps: 1, carrier: 52, shoutCarrier: 78, dry: .2, level: 1.5, shout: .85},   // Hz of the wave by voice 0; the dry part
  comb: {steps: 0, hum: 150, feed: .8, shoutFeed: .84, level: .9, shout: .8},   // Hz of the hum by voice 0; feedback
  tin: {steps: 2, grain: .022, gap: .03, box: [[1700, 6, 9], [3100, 8, 6]], level: 1.3, shout: .74},   // s; s; Hz, Q, dB
};
const ROBOT_ASK = [2, 4, 7];                                // a question: its last three syllables a step up each
let robotCurve = null;
const robotHeld = new Map();                                // (the chip voice's recordings, made once a recording and depth)
const robotOf = (name, lo, hi) => lo * 2 ** ((voiceOf(name) + 4) / 8 * Math.log2(hi / lo));   // a speaker's own number from lo to hi

// A recording held in steps of `hold` Hz and cut to 2^bits levels, kept for the next time.
function robotChip(a, buf, hold, bits) {
  const key = buf, depth = hold + ":" + bits;
  let byDepth = robotHeld.get(key);
  if (!byDepth) { byDepth = new Map(); robotHeld.set(key, byDepth); }
  let made = byDepth.get(depth);
  if (made) return made;
  made = a.createBuffer(buf.numberOfChannels, buf.length, buf.sampleRate);
  const every = Math.max(1, Math.round(buf.sampleRate / hold)), levels = 2 ** (bits - 1);
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const src = buf.getChannelData(c), dst = made.getChannelData(c);
    let peak = 1e-6;
    for (let i = 0; i < src.length; i++) peak = Math.max(peak, Math.abs(src[i]));
    for (let i = 0; i < src.length; i += every) {
      const v = Math.round(src[i] / peak * levels) / levels * peak;
      for (let j = i; j < Math.min(i + every, src.length); j++) dst[j] = v;
    }
  }
  byDepth.set(depth, made);
  return made;
}

// The way a voice goes out: from the node the syllables go into to `dest`. Returns {into, stop(at)}.
function robotChain(a, kind, name, shout, dest, t0, t1) {
  const v = ROBOT[kind], into = a.createGain(), level = a.createGain();
  level.gain.value = v.level * (shout ? v.shout : 1);   // (each kind as loud as a person, talking and shouting)
  if (kind === "ring") {
    const wave = a.createOscillator(), times = a.createGain(), dry = a.createGain();
    wave.frequency.value = robotOf(name, v.carrier * .75, v.carrier * 1.35) * (shout ? v.shoutCarrier / v.carrier : 1);
    times.gain.value = 0; wave.connect(times.gain);         // (the recording times the wave: the gain is the wave)
    dry.gain.value = v.dry;
    into.connect(times).connect(level); into.connect(dry).connect(level);
    wave.start(t0); wave.stop(t1 + .05);
  } else if (kind === "comb") {
    const late = a.createDelay(.05), back = a.createGain(), dull = a.createBiquadFilter();
    late.delayTime.value = 1 / robotOf(name, v.hum * .75, v.hum * 1.35);
    back.gain.value = shout ? v.shoutFeed : v.feed;
    dull.type = "lowpass"; dull.frequency.value = 3500; dull.Q.value = -3;   // (no peak at the cut: it would ring on)
    into.connect(level); into.connect(late).connect(dull).connect(back).connect(late); back.connect(level);
  } else if (kind === "tin") {
    let at = into;
    const low = a.createBiquadFilter(); low.type = "highpass"; low.frequency.value = 380; at = at.connect(low);
    for (const [f, q, db] of v.box) { const p = a.createBiquadFilter(); p.type = "peaking"; p.frequency.value = f; p.Q.value = q; p.gain.value = db; at = at.connect(p); }
    const top = a.createBiquadFilter(); top.type = "lowpass"; top.frequency.value = 5200; at = at.connect(top);
    const late = a.createDelay(.05), back = a.createGain();
    late.delayTime.value = .011; back.gain.value = .3;
    at.connect(level); at.connect(late).connect(back).connect(late); back.connect(level);
  } else into.connect(level);
  if (shout) {                                               // a yell as a person's (babble.js): the breaking curve, the bite, an echo
    if (!robotCurve) { robotCurve = new Float32Array(1024); for (let i = 0; i < 1024; i++) robotCurve[i] = Math.tanh((i / 511.5 - 1) * SHOUT.push) / Math.tanh(SHOUT.push); }
    const hard = a.createWaveShaper(), bite = a.createBiquadFilter(), late = a.createDelay(1), back = a.createGain();
    hard.curve = robotCurve; bite.type = "peaking"; bite.frequency.value = SHOUT.bite[0]; bite.gain.value = SHOUT.bite[1]; bite.Q.value = .9;
    late.delayTime.value = SHOUT.echo[0]; back.gain.value = SHOUT.echo[1];
    level.connect(hard).connect(bite).connect(dest); bite.connect(late).connect(back).connect(dest); back.connect(late);
  } else level.connect(dest);
  return into;
}

// Say `text` as a robot of kind `kind` into `dest` from audio time t0, at `vol`. Returns the syllables put on the clock.
function robotSay(a, dest, bufs, name, text, shout, kind, t0, vol = 1) {
  const v = ROBOT[kind];
  if (!v || !bufs.length) return 0;
  const letters = [...String(text).toLowerCase()], asks = /\?\s*$/.test(text), base = voiceOf(name) + (shout ? SHOUT.up : 0);
  const marks = [];                                          // (first where each syllable falls, so a question knows its last three)
  let run = 0;
  letters.forEach((ch, i) => {
    const at = i * BABBLE.letter;
    if (at > BABBLE.most) return;
    if (!/[a-z0-9ß-ɏ]/.test(ch)) { run = 0; return; }
    if (run++ % BABBLE.every) return;
    marks.push([ch, at]);
  });
  if (!marks.length) return 0;
  const piece = shout ? SHOUT.piece : BABBLE.piece, t1 = t0 + marks[marks.length - 1][1] + piece + .1;
  const out = a.createGain();
  out.gain.value = vol * (shout ? SHOUT.level : .85);
  out.connect(dest);
  const into = robotChain(a, kind, name, shout, out, t0, t1);
  marks.forEach(([ch, at], n) => {
    const code = ch.charCodeAt(0), raw = bufs[code % bufs.length], from = marks.length - 1 - n;
    const step = v.steps ? Math.round((BABBLE.vowel[ch] ?? code % 5 - 2) / 3) * v.steps : 0;      // (a few fixed notes, not a tune)
    const semis = base + step + (asks && from < 3 ? ROBOT_ASK[2 - from] : 0);
    const rate = 2 ** (semis / 12), buf = kind === "chip" ? robotChip(a, raw, v.hold, shout ? v.shoutBits : v.bits) : raw;
    const len = Math.min(piece, buf.duration / rate - .02);
    const grains = [0];                                      // (tin: a grain every v.gap s as long as the syllable lasts)
    if (kind === "tin") while (grains[grains.length - 1] + v.gap < len - .012) grains.push(grains[grains.length - 1] + v.gap);
    grains.forEach((g) => {
      const l = kind === "tin" ? Math.min(v.grain, len - g) : len, s = t0 + at + g;
      if (l <= .01) return;
      const src = a.createBufferSource(), env = a.createGain();
      src.buffer = buf; src.playbackRate.value = rate;
      env.gain.setValueAtTime(0, s); env.gain.linearRampToValueAtTime(1, s + .004);
      env.gain.setValueAtTime(1, s + l - .008); env.gain.linearRampToValueAtTime(0, s + l);
      src.connect(env).connect(into);
      src.start(s, 0, l * rate + .01);
    });
  });
  return marks.length;
}
