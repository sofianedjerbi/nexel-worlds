// The island's people (title_scene.js gives them their island, its hours and its dice). Nobody follows a script:
// each has things they like doing, and when one is done chooses the next among them by chance, never the one just
// done, and only what can be done now (no harvest without ripe wheat, no letter to fetch from an empty box).
// What they do is done to the island: watered soil is wet and its wheat grows, ripe wheat is pulled and sown again,
// a tree comes down and grows back from its stump, berries and fruit are picked and eaten, flowers go and come
// again, the trough is filled, a letter is posted and found, a cow is milked, the boat is tied up at the pier and
// taken out again. They call to each other and stop for a word (title_talk.js), and now and then one shouts
// across the island and is shouted back at; in the evening the day's work is left and they come round the fire,
// going off between two whiles by it for a walk, a letter, the well.
// The dice are thrown anew at each visit: no two are the same.
// An errand is written as a generator: each `yield` is a tenth of a second going by.
const TitleCast = (() => {
  let I = null, spoke = 0, loud = 0, last = null;    // the island; when someone last spoke to themselves; when the next shout is due, and the last one
  const WAYS = {N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0]}, taken = new Map();      // (a place -> who has it)
  const lv = (x, y) => levelAt(I.ox + x, I.oy + y) || 0, one = (list) => list[I.pick(list.length)];
  const bare = (x, y) => standOn(I.at(x, y), false);
  const afloat = (x, y) => { const t = I.at(x, y); return !!t && wet(t[1]) && GROUND.has(t[0]); };
  const far = (a, b) => Math.abs(a.x - b[0]) + Math.abs(a.y - b[1]);
  const someone = (x, y, but) => I.people.some((o) => o !== but && o.x === x && o.y === y);
  const toward = (a, b) => Math.abs(b.x - a.x) >= Math.abs(b.y - a.y) ? (b.x > a.x ? "E" : "W") : (b.y > a.y ? "S" : "N");
  const mutter = (p, kind) => { if (I.tick - spoke > 60 && !I.pick(3)) { spoke = I.tick; I.say(p, one(TITLE_TALK.solo[kind])); } };

  // The way from where p stands to (tx, ty), a tile after the other (null: there is none): round what is solid, a
  // level up or down at a step at most, round anyone standing at their work; and the easiest way rather than the
  // shortest: a path or a bridge is two to walk where grass is three, and the field's soil six (its wheat is walked
  // through only for want of another way)
  const HARD = {".": 3, o: 6, u: 6};
  function route(p, tx, ty, ok = bare) {
    const w = I.w, k0 = p.y * w + p.x, from = new Map([[k0, -1]]), cost = new Map([[k0, 0]]), due = [[k0]];
    for (let c = 0; c < due.length; c++) for (const k of due[c] || []) {
      if (cost.get(k) !== c) continue;               // (reached more easily since)
      const x = k % w, y = (k - x) / w;
      if (x === tx && y === ty) { const way = []; for (let q = k; q !== k0; q = from.get(q)) way.unshift([q % w, Math.floor(q / w)]); return way; }
      for (const [dx, dy] of Object.values(WAYS)) {
        const nx = x + dx, ny = y + dy, n = ny * w + nx;
        if (nx < 0 || ny < 0 || nx >= w || ny >= I.h || !ok(nx, ny) || Math.abs(lv(nx, ny) - lv(x, y)) > 1) continue;
        if ((nx !== tx || ny !== ty) && I.people.some((o) => o !== p && o.still && o.x === nx && o.y === ny)) continue;
        const to = c + (HARD[I.at(nx, ny)[1]] || 2);
        if (cost.has(n) && cost.get(n) <= to) continue;
        cost.set(n, to); from.set(n, k); (due[to] || (due[to] = [])).push(n);
      }
    }
    return null;
  }
  // There on foot (how.run: at a run; how.ok, how.pace: a swimmer's water, and its time a tile) -> were they able to
  function* go(p, x, y, how = {}) {
    const way = route(p, x, y, how.ok);
    if (!way) return false;
    p.run = !!how.run;
    for (const [nx, ny] of way) {
      const pace = (how.pace || (how.run ? 1 : 2)) + (lv(nx, ny) > lv(p.x, p.y) ? 1 : 0);
      p.x = nx; p.y = ny; p.doing = "walk";
      for (let i = pace; i > 0; i--) yield;
    }
    p.doing = null; p.run = false; yield;
    return true;
  }
  // Something done on the spot for a while: {doing, with, item, dir, at}; nothing but a way to face is standing and looking
  function* work(p, what, ticks) {
    Object.assign(p, {doing: what.doing || (what.dir ? "look" : null), with: what.with || null, item: what.item || null, dir: what.dir || null, aim: what.at || null, still: true});
    while (ticks-- > 0) yield;
    Object.assign(p, {doing: null, with: null, item: null, aim: null, still: false});
  }
  const rest = (p, ticks, dir) => work(p, {dir}, ticks);
  // A free place of a kind (title_map.js: where to stand, the way to face, the tile it is about), one of the four
  // nearest, not the one they last stood at; it is theirs till the errand is over. `ok`: what must be on its tile
  function place(p, kind, ok) {
    const s = one(I.C.places[kind].filter((q) => !taken.has(q) && q !== p.was && (!ok || ok(I.at(q[3], q[4])[0]))).sort((a, b) => far(p, a) - far(p, b)).slice(0, 4));
    if (s) { taken.set(s, p); p.spot = s; }
    return s;
  }
  function* visit(p, kind, ok, how) { const s = place(p, kind, ok); return s && (yield* go(p, s[0], s[1], how)) ? s : null; }
  // Where to stand to be at (tx, ty): bare ground beside it with nobody on it, the nearest (from below only if it is
  // a good deal nearer: a head hides the tile over it) -> [x, y, the way to face, tx, ty]
  function beside(p, tx, ty) {
    const cost = (s) => far(p, s) + (s[2] === "N" ? 4 : 0);
    const out = (x, y) => { const t = I.at(x, y); return t[0] !== "+" && t[1] !== "n"; };                    // (not in a doorway, nor indoors: under the roof they are not seen)
    return Object.entries(WAYS).map(([d, [dx, dy]]) => [tx - dx, ty - dy, d, tx, ty]).filter(([x, y]) => bare(x, y) && out(x, y) && !someone(x, y, p)).sort((a, b) => cost(a) - cost(b))[0] || null;
  }
  // The field's tiles that are as wanted (their thing, their ground); and for p one of the two nearest, with where to stand
  const field = (want) => { const [x0, y0, x1, y1] = I.C.field, out = []; for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const t = I.at(x, y); if (t && want(t[0], t[1])) out.push([x, y]); } return out; };
  const crop = (p, want) => one(field(want).map(([x, y]) => beside(p, x, y)).filter(Boolean).sort((a, b) => far(p, a) - far(p, b)).slice(0, 2));
  const ripe = (c) => c === "w", dry = (c, g) => g === "o";
  // Two of them, a line and its answer: the one spoken to stops what they are doing and turns
  function* talk(p, q, lines) {
    if (!q) return;
    const [a, b] = one(lines);
    q.hold = 72; q.face = toward(q, p); p.talks = I.tick + 72;
    I.say(p, a); yield* rest(p, 32, toward(p, q));
    I.say(q, b); yield* rest(p, 34, toward(p, q));
  }
  // Berries off a bush, fruit off a tree: picked, eaten there; they grow back
  // What each of them does, and what it does to the island: title_errands.js (the island read when an errand runs: K.I)
  const DO = TitleErrands({get I() { return I; }, afloat, beside, crop, dry, far, go, mutter, one, rest, ripe, route, someone, talk, toward, visit, work});
  // What each likes doing, and how much; and what cannot be done just now
  const LIKES = {
    Mira: {harvest: 6, water: 4, feed: 2, eggs: 1.5, milk: 2, well: 1, mail: 3, picnic: 1, chat: 2.5, flower: 1, view: .5},
    Tobi: {chop: 4, mine: 3, berries: 1.5, fruit: 1, picnic: 1, view: 1, sign: .5, well: .5, chat: 2.5, stroll: .5},
    Nell: {view: 3, flower: 2.5, stroll: 2, berries: 1.5, fruit: 1.5, chat: 3, picnic: 1, milk: 1, sign: .5},
    Pip: {sail: 5, post: 2.5, view: 2, chat: 3, picnic: 1.5, fruit: 1, stroll: 1},
    Lou: {swim: 1},
  };
  const DAY = ["harvest", "water", "chop", "mine", "sail", "milk", "feed"], CAN = {harvest: () => field(ripe).length > 0, water: () => field(dry).length > 0, mail: () => I.mail, post: () => !I.mail, feed: () => I.trough < I.tick, sail: (p) => p.ashore >= 2};
  function choose(p) {
    if (p.sail) return DO.sail(p);                   // (at sea when the island wakes: the lap is finished first)
    // (the evening: the fire, and between two whiles by it something that is done in the dark too)
    if (I.evening() && !p.swim && p.last !== "fire" && I.C.places.fire.some((s) => !taken.has(s))) { p.last = "fire"; return DO.fire(p); }
    let likes = Object.entries(LIKES[p.name]).filter(([k]) => k !== p.last && (!CAN[k] || CAN[k](p)) && !(I.evening() && DAY.includes(k)));
    if (!likes.length) likes = Object.entries(LIKES[p.name]);
    let r = I.rnd() * likes.reduce((sum, [, w]) => sum + w, 0);
    const [kind] = likes.find(([, w]) => (r -= w) < 0) || likes[0];
    p.last = kind; p.ashore = (p.ashore || 0) + 1;
    return DO[kind](p);
  }
  // One of them, a tenth of a second on: held in a talk, or on with their errand, or choosing the next
  function live(p) {
    if (p.hold > 0) { p.hold--; return; }
    if (p.job && !p.job.next().done) return;
    if (p.spot) { taken.delete(p.spot); p.was = p.spot; p.spot = null; }
    Object.assign(p, {doing: null, with: null, item: null, aim: null, still: false, run: false});
    p.job = choose(p);
  }
  // Now and then someone in sight shouts across the island, and is shouted back at; whoever else is by laughs.
  // (The first, a few seconds after the island wakes: it is the first thing a visitor hears of them.)
  function hail() {
    if (I.tick < loud || !I.eye) return;
    const who = (n) => I.people.find((p) => p.name === n), seen = (p) => !!p && Math.abs(p.x - I.eye.x) <= 11 && Math.abs(p.y - I.eye.y) <= 6;
    const free = (p) => seen(p) && !p.hold && !(p.talks > I.tick);                                         // (in sight, and not in the middle of a word with someone)
    const s = one(TITLE_TALK.shout.filter((q) => q !== last && free(who(q[0]))));
    if (!s) { loud = I.tick + 20; return; }          // (nobody in sight has anything to shout: soon again)
    last = s; loud = I.tick + 220 + I.pick(200);
    I.say(who(s[0]), s[1], true);
    I.later(32, () => {
      I.say(who(s[2]), s[3], true);
      const by = one(I.people.filter((p) => seen(p) && p.name !== s[0] && p.name !== s[2]));
      if (by) I.later(14, () => emote(by.name, "laugh"));
    });
  }
  // The island wakes: who lives there, and where each is found (somewhere else each time)
  function wake(island) {
    I = island; taken.clear(); spoke = 0; last = null; loud = 40 + I.pick(30);
    const C = I.C, on = 1 + I.pick(C.ring.length - 1), at = ([x, y]) => ({x, y});
    const P = (id, name, race, worn, more) => ({id, kind: "agent", name, race, worn, doing: null, dir: null, hold: 0, ...more});
    return [P(9001, "Mira", "bunny", {head: "straw_hat"}, at(C.door)), P(9002, "Tobi", "bear", null, at(one(C.places.trees))),
      P(9003, "Pip", "frog", {head: "bandana"}, {...at(C.ring[on]), sail: true, on, turn: I.pick(2) ? 1 : -1}),
      P(9004, "Lou", "duck", null, {...at(one(C.pond)), swim: true}), P(9005, "Nell", "cat", null, at(one(C.places.views)))];
  }
  return {wake, live, hail};
})();
