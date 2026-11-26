// Nyxwing, the boss of "Sugar rush" (sim/nyxwing.py; its sheet: design/enemies/roster/nyxwing.py): how it is drawn
// (drawWild hands it here), and, in the land (HdFx hands it a `put`), what is not on its body: the eclipse it comes out
// of, the speck it is far off and the dragon it grows into, its shadow while it is up in the sky, its body breaking into
// stars when it dies. Every time here is a count of beats of its song (156 BPM), as the server's are.
// Its sounds are music/sfx.py's drake_* set, all of one palette.
const Nyx = (() => {
  const BEAT = 60000 / 156, WARN = 1.5 * BEAT, SKY = 4.5 * BEAT, LOCK = BEAT;
  const FALL_FROM = 12, ARRIVE = 32;                        // beats into its entrance: it comes out of the eclipse; it lands (the drop)
  // From a sound's start to its loudest moment, in ms, measured on the renders of music/sfx.py: started that much before
  // the beat it is to land on (the descent's swell on the landing, the fall's on the crash, the dissolve's on the last star).
  const HIT = {drake_descend: 5422, drake_fall: 501, drake_dissolve: 1370};
  const GOLD = ["#ffcf5a", "#fff3c0", "#ffe08a", "#c77dff", "#7fb8ff"], FIRE = ["#fff3c0", "#ffcf5a", "#c77dff", "#7a4dd0", "#2a1c4a"];
  const ATTACKS = new Set(["breath", "storm", "sweep", "dive", "rush"]);
  const seen = new Map();                                    // id -> what this client knows of it (times, its last picture)
  const st = (id) => { if (!seen.has(id)) seen.set(id, {}); return seen.get(id); };
  const later = (ms, f) => setTimeout(f, Math.max(0, ms));
  const say = (name, e) => sfx(name, e.x, e.y, 30);         // (a dragon carries further than a tortoise: boss.js's 20)
  const owns = (e) => e.kind === "nyxwing" || ents.has("nyxwing" + e.id);
  // when its entrance began, on this page's clock (its song's start): the server's event, or, for a player who comes
  // when it is already here, how long ago the server says it came (views.py `came`); what is still to be heard of it is
  // played when it falls due
  function came(e, at) {
    const s = st(e.id);
    if (s.arriveAt !== undefined) return s.arriveAt;
    s.arriveAt = at;
    const due = (after, name) => { const ms = at + after - performance.now(); if (ms >= 0) later(ms, () => say(name, e)); };
    due(8 * BEAT, "drake_omen");                                            // a roar from far off; its swell lands on the landing
    due(ARRIVE * BEAT - HIT.drake_descend, "drake_descend");
    return at;
  }
  const began = (e) => e.came === undefined ? st(e.id).arriveAt : came(e, performance.now() - e.came * 1000);
  // (its parts, each its own file, made in order: each takes what it uses from K)
  const K = {BEAT, WARN, SKY, LOCK, FALL_FROM, ARRIVE, HIT, GOLD, FIRE, ATTACKS, seen, st, later, say, came, began};
  for (const part of [NyxArt, NyxBody, NyxDeath, NyxSky, NyxDeeds]) Object.assign(K, part(K));
  const {draw, hd, windup, event, died} = K;
  // every beat, its wings (between its moves)
  setInterval(() => { for (const p of ents.values()) if (p.e && p.e.kind === "nyxwing" && !p.e.act) sfx("drake_flap", p.x, p.y, 20); }, BEAT);
  return {draw, hd, windup, event, died, owns, began};
})();
