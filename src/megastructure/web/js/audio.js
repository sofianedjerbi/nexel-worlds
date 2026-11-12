// Sound effects: samples rendered by music/sfx.py, built into audio/ by tools/build_audio.py, played through WebAudio.
//
// How to change things:
//   a sound itself            edit its generator in music/sfx.py, then `uv run python tools/build_audio.py`
//   what an object sounds like when placed    edit music/sfx_map.json, then rebuild
//   how loud a family is, how far sounds carry, how often one may repeat    edit SOUND below
//   the music                 music/compose.py renders it; rebuild; its volume is SOUND.music
//   when a sound plays        the call sites: sfx(name, x, y) for something in the world, sfx(name) for the player or the interface
// A name that the build does not know is reported once in the console and stays silent (tests/test_audio.py catches it earlier).

const SOUND = {
  master: .8,
  music: .45,         // the background loop's volume (0 to turn it off); it fades in over musicFade seconds
  musicFade: 4,
  bossMusic: 1.2,     // the boss fight's loop, as a multiple of `music`
  mix: {Footsteps: .9, Work: 1, Breaking: 1, Building: 1, Items: .9, Progress: 1, Fights: 1, Animals: .9, World: .9, People: .8, Interface: .8, Boss: 1},
  hearing: 12,        // tiles: a sound in the world further than this is not heard
  quietest: .15,      // volume at the edge of hearing (it fades linearly from 1)
  panWidth: 9,        // tiles to the side at which a sound is fully left or right
  panAmount: .8,
  pitch: .04,         // random pitch spread on physical sounds, so repeats never sound stamped (tuned sounds keep their pitch)
  minGap: {default: 45, step: 110, tock: 110, click: 110, wade: 130, orb: 30, crackle: 400, grow: 800, say: 150, rustle: 90},   // ms between plays of one sound
  maxVoices: 20,      // sounds playing at once; beyond this new ones are dropped
  loaders: 4,         // parallel downloads while warming the cache after the first gesture
};

let audio = null, soundOut = null, muted = localStorage.getItem("megastructure-muted") === "1";
const sounds = {manifest: null, loading: null, buffers: new Map(), lastVariant: {}, lastAt: {}, voices: 0, warned: new Set()};

function ac() {
  if (!audio) {
    audio = new (window.AudioContext || window.webkitAudioContext)();
    soundOut = audio.createGain();
    soundOut.gain.value = SOUND.master;
    const limiter = audio.createDynamicsCompressor();      // a safety net when many sounds land together
    limiter.threshold.value = -6; limiter.ratio.value = 12; limiter.attack.value = .002; limiter.release.value = .15;
    soundOut.connect(limiter).connect(audio.destination);
  }
  return audio;
}
// start audio on the first gesture, not inside the first frame that plays a sound (creating it stalls ~100 ms)
for (const ev of ["pointerdown", "keydown"]) addEventListener(ev, () => { if (!muted) { ac(); loadSounds(); } }, {once: true, capture: true});

// The manifest (what exists, which file, which family), then every file in the background.
function loadSounds() {
  if (!sounds.loading) sounds.loading = fetch("audio/sfx.json", {cache: "no-cache"})
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((m) => { sounds.manifest = m; return warmSounds(); })
    .then(startMusic)
    .catch(() => { console.info("no sound effects: run `uv run python tools/build_audio.py`"); setTimeout(() => sounds.loading = null, 15000); });
  return sounds.loading;
}
function loadSoundFile(file) {
  let entry = sounds.buffers.get(file);
  if (!entry) {
    entry = fetch(`audio/${file}?v=${sounds.manifest.version}`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); })
      .then((raw) => ac().decodeAudioData(raw))
      .then((buf) => { sounds.buffers.set(file, buf); return buf; })
      .catch(() => { sounds.buffers.delete(file); return null; });      // try again the next time it is wanted
    sounds.buffers.set(file, entry);
  }
  return entry;
}
async function warmSounds() {
  const files = Object.values(sounds.manifest.sounds).flatMap((s) => s.files);
  const worker = async () => { while (files.length) await loadSoundFile(files.shift()); };
  await Promise.all(Array.from({length: SOUND.loaders}, worker));
}

// The background loop: one buffer, looping sample-exact, on its own gain (the effects' limiter never pumps it).
const music = {node: null, gain: null};
async function startMusic() {
  const m = sounds.manifest && sounds.manifest.music;
  if (!m || music.node || muted || !SOUND.music) return;
  const buf = await loadSoundFile(m.file);
  if (!buf || music.node || muted) return;
  const a = ac();
  music.gain = a.createGain();
  music.gain.gain.value = 0;
  music.gain.gain.setTargetAtTime(SOUND.music, a.currentTime, SOUND.musicFade / 3);
  music.node = a.createBufferSource();
  music.node.buffer = buf;
  music.node.loop = true;
  music.node.connect(music.gain).connect(a.destination);
  music.node.start();
}
// The boss's own loop (music/boss.py) takes over from the background one while a fight is on, and hands back after.
const bossTrack = {node: null, gain: null, on: false};
async function bossMusic(on) {
  const m = sounds.manifest && sounds.manifest.boss;
  if (on === bossTrack.on || !audio || !m || !SOUND.music) return;
  bossTrack.on = on;
  if (on && !bossTrack.node) {
    const buf = await loadSoundFile(m.file);
    if (!buf || bossTrack.node || !bossTrack.on) return;
    bossTrack.gain = audio.createGain();
    bossTrack.gain.gain.value = 0;
    bossTrack.node = audio.createBufferSource();
    bossTrack.node.buffer = buf; bossTrack.node.loop = true;
    bossTrack.node.connect(bossTrack.gain).connect(audio.destination);
    bossTrack.node.start();
  }
  const t = audio.currentTime;
  if (bossTrack.gain) bossTrack.gain.gain.setTargetAtTime(on && !muted ? SOUND.music * SOUND.bossMusic : 0, t, on ? .3 : 1.2);
  if (music.gain) music.gain.gain.setTargetAtTime(on || muted ? 0 : SOUND.music, t, on ? .3 : 1.5);
  if (!on && bossTrack.node) { bossTrack.node.stop(t + 6); bossTrack.node = null; }      // the next fight starts from its first bar
}
// M: everything off or on. The music fades instead of stopping, so it comes back where it was.
function setMuted(on) {
  muted = on;
  localStorage.setItem("megastructure-muted", on ? "1" : "0");
  if (bossTrack.gain) bossTrack.gain.gain.setTargetAtTime(on || !bossTrack.on ? 0 : SOUND.music * SOUND.bossMusic, audio.currentTime, .3);
  if (music.gain) music.gain.gain.setTargetAtTime(on || bossTrack.on ? 0 : SOUND.music, audio.currentTime, .3);
  if (!on) { ac(); (sounds.loading || loadSounds()).then(startMusic); }
}

// Play a sound. With x, y it is in the world: quieter with distance, panned to its side, silent beyond SOUND.hearing
// (or beyond `reach` tiles when given). Without, it is the player's own or the interface's.
function sfx(name, x, y, reach) {
  if (muted) return;
  const m = sounds.manifest;
  if (!m) { loadSounds(); return; }
  const s = m.sounds[name];
  if (!s) { if (!sounds.warned.has(name)) { sounds.warned.add(name); console.warn(`sfx: unknown sound "${name}"`); } return; }
  let vol = 1, pan = 0;
  if (x !== undefined) {
    const me = myPos();
    if (!me) return;
    const dx = x - me.x, d = Math.hypot(dx, y - me.y), far = reach || SOUND.hearing;
    if (d > far) return;
    vol = Math.max(SOUND.quietest, 1 - d / far);
    pan = Math.max(-1, Math.min(1, dx / SOUND.panWidth)) * SOUND.panAmount;
  }
  const now = performance.now(), gap = SOUND.minGap[name] ?? SOUND.minGap.default;
  if (now - (sounds.lastAt[name] || -1e9) < gap || sounds.voices >= SOUND.maxVoices) return;
  let k = Math.floor(Math.random() * s.files.length);
  if (s.files.length > 1 && k === sounds.lastVariant[name]) k = (k + 1) % s.files.length;       // never the same variant twice running
  const buf = sounds.buffers.get(s.files[k]);
  if (!(buf instanceof AudioBuffer)) { loadSoundFile(s.files[k]); return; }                    // still downloading: skip this once
  sounds.lastVariant[name] = k;
  sounds.lastAt[name] = now;
  try {
    const a = ac(), src = a.createBufferSource(), g = a.createGain(), p = a.createStereoPanner();
    src.buffer = buf;
    if (s.pitch) src.playbackRate.value = 1 + (Math.random() * 2 - 1) * SOUND.pitch;
    g.gain.value = vol * (SOUND.mix[s.category] ?? 1);
    p.pan.value = pan;
    src.connect(g).connect(p).connect(soundOut);
    sounds.voices++;
    src.onended = () => { sounds.voices--; };
    src.start();
  } catch (e) { /* audio not available yet (needs a user gesture) */ }
}

// Something was put down: each kind of block or ground has its own sound (music/sfx_map.json).
function sfxPlaced(block, ground, x, y) {
  const m = sounds.manifest;
  if (!m) { loadSounds(); return; }
  sfx(m.place[block] || m.ground[ground] || "place", x, y);
}

// The material a tile char is made of: picks the strike and break sounds.
const WOOD_CHARS = "TUtH#+&CBhLKgWVXJeqy?!rmFpz", STONE_CHARS = "M*%Y^Z", PLANT_CHARS = "bvfQ;\"wo";
function material(c) {
  return WOOD_CHARS.includes(c) ? "wood" : STONE_CHARS.includes(c) ? "stone" : PLANT_CHARS.includes(c) ? "plant" : "soil";
}
const STRIKE = {wood: "chop", stone: "mine", plant: "rustle", soil: "dig"};      // a tool hits it
const BREAK = {wood: "snap", stone: "crumble", plant: "rustle", soil: "dig"};    // it gives way
const STEP = {n: "tock", ":": "tock", _: "click", "~": "wade"};                  // ground char under the feet -> footstep (default: step)
const VOICE = {cow: "moo", calf: "moo", chicken: "cluck", chick: "chirp"};       // an animal's ordinary voice
const animalVoice = (kind) => VOICE[kind] || "cluck";
