// The Voices box of robots.html: the game's own babble.js (a person) and robot_voice.js (a robot), played from the
// game's recorded "say" syllables (web/audio, built by tools/build_audio.py). The few things babble.js asks of
// audio.js are given here, plainly: no distance, no settings, full volume.
var muted = false, audio = null, soundOut = null, ears = null;
var SOUND = {mix: {}, hearing: 20};
var sounds = {manifest: null, buffers: new Map()};
const soundShare = () => 1, heard = () => ({vol: 1, pan: 0}), myPos = () => null;
const awake = () => !!audio, ac = () => audio, loadSounds = () => {}, loadSoundFile = () => {};

const VOICES = [
  ["person", "today's babble", "A person, as the game has it now: each vowel its own note, a question gliding up, a shout strained."],
  ["chip", "A. chip", "Held in steps and cut to few levels (5.8 kHz, 5 bits): an old game's robot. Notes in whole tones."],
  ["ring", "B. ring", "The recording times a slow wave (about 50 Hz, the speaker's own): the classic film robot's buzz."],
  ["comb", "C. comb", "One steady note, through a very short echo fed back on itself and tuned to the speaker: a metal hum."],
  ["tin", "D. tin", "Each syllable said as quick grains (one every 30 ms), as if read off a tape, out of a small tin box."],
];
const VOICE_LINES = [["Hello there, friend", "hello"], ["Where is the wood?", "question"], ["GET AWAY FROM MY HOUSE", "shout"]];
const VOICE_NAMES = ["Unit-7", "Bolt"];
const VOICE_RATE = 48000;

let recorded = null;                                         // the say syllables, decoded once
async function sayBuffers() {
  if (recorded) return recorded;
  const m = await (await fetch("web/audio/sfx.json", {cache: "no-cache"})).json(), s = m.sounds.say, dec = new OfflineAudioContext(1, 1, VOICE_RATE);
  sounds.manifest = m;
  recorded = await Promise.all(s.files.map(async (f) => {
    const b = await dec.decodeAudioData(await (await fetch(`web/audio/${f}?v=${m.version}`)).arrayBuffer());
    sounds.buffers.set(f, b); return b;
  }));
  return recorded;
}
// One line into context `a` from its time 0: the person through babble() itself, the game's robot voice (ROBOT_KIND)
// through babble() too, as an AI player's line in the game, the other robots through robotSay().
function speak(a, kind, name, text) {
  const shout = shouted(text), was = [audio, soundOut];
  audio = a; soundOut = a.destination;
  try {
    if (kind === "person" || kind === ROBOT_KIND) return babble(name, text, undefined, undefined, shout, kind === ROBOT_KIND);
    return robotSay(a, a.destination, recorded, name, text, shout, kind, a.currentTime + .02);
  } finally { [audio, soundOut] = was; }
}
// Rendered off the clock, for the numbers: Float32 samples of one line (and the seconds it lasts).
async function renderLine(kind, name, text) {
  await sayBuffers();
  const a = new OfflineAudioContext(2, VOICE_RATE * 4, VOICE_RATE);
  speak(a, kind, name, text);
  const b = await a.startRendering();
  return [b.getChannelData(0), b.getChannelData(1)];
}
let live = null;
async function playLine(kind, name, text, button) {
  await sayBuffers();
  if (!live) live = new AudioContext();
  if (live.state !== "running") await live.resume();
  speak(live, kind, name, text);
  document.querySelectorAll("button.play.on").forEach((b) => b.classList.remove("on"));
  button.classList.add("on"); setTimeout(() => button.classList.remove("on"), 1600);
}
function voiceRows() {
  const rows = document.getElementById("voicerows");
  for (const [kind, title, what] of VOICES) {
    const row = document.createElement("div"); row.className = "voice";
    row.innerHTML = `<div><b>${title}</b><small>${what}</small></div>`;
    const plays = document.createElement("div"); plays.className = "plays";
    for (const name of VOICE_NAMES) {
      const who = document.createElement("div"); who.className = "who"; who.textContent = name;
      plays.append(who);
      for (const [text, label] of VOICE_LINES) {
        const b = document.createElement("button"); b.className = "play"; b.title = `${name}: ${text}`;
        b.dataset.kind = kind; b.dataset.name = name; b.dataset.text = text;
        b.innerHTML = `<span class="tri"></span>${label}`;
        b.onclick = () => playLine(kind, name, text, b);
        plays.append(b);
      }
    }
    row.append(plays); rows.append(row);
  }
}
