// Which sound a thing makes: a block put down (music/sfx_map.json), a tile struck or broken by its material, the ground
// under the feet, an animal's voice. Played through audio.js (sfx).

// Something was put down: each kind of block or ground has its own sound (music/sfx_map.json).
function sfxPlaced(block, ground, x, y) {
  const m = sounds.manifest;
  if (!m) { if (audio) loadSounds(); return; }      // (not before the first key or tap: the island's own sounds asked for 4.9 MB of them on a line nobody had touched)
  sfx(m.place[block] || m.ground[ground] || "place", x, y);
}

// The material a tile char is made of: picks the strike and break sounds.
const WOOD_CHARS = "TUtH#+&CBhLKgWVXJeqy?!rmFpz", STONE_CHARS = "M*%Y^Z", PLANT_CHARS = "bvfQ;\"wo";
function material(c) {
  return WOOD_CHARS.includes(c) ? "wood" : STONE_CHARS.includes(c) ? "stone" : PLANT_CHARS.includes(c) ? "plant" : "soil";
}
const STRIKE = {wood: "chop", stone: "mine", plant: "rustle", soil: "dig"};      // a tool hits it
const BREAK = {wood: "snap", stone: "crumble", plant: "rustle", soil: "dig"};    // it gives way
const STEP = {n: "tock", ":": "tock", _: "click", "~": "wade", "(": "wade", "=": "wade", ")": "wade"};                  // ground char under the feet -> footstep (default: step)
const VOICE = {cow: "moo", calf: "moo", chicken: "cluck", chick: "chirp"};       // an animal's ordinary voice
const animalVoice = (kind) => VOICE[kind] || "cluck";
