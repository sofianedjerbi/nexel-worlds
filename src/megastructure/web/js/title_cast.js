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
  const bare = (x, y) => { const t = I.at(x, y); return !!t && WALKABLE_GROUND.has(t[1]) && !SOLID.has(t[0]); };
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
  // nearest, not the one they were last at; it is theirs till the errand is over. `ok`: what must be on its tile
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
  // Two of them, a line and its answer: the one spoken to stops what they were at and turns
  function* talk(p, q, lines) {
    if (!q) return;
    const [a, b] = one(lines);
    q.hold = 72; q.face = toward(q, p); p.talks = I.tick + 72;
    I.say(p, a); yield* rest(p, 32, toward(p, q));
    I.say(q, b); yield* rest(p, 34, toward(p, q));
  }
  // Berries off a bush, fruit off a tree: picked, eaten there; they grow back
  function* gather(p, kind, full, picked, food) {
    const s = yield* visit(p, kind, (c) => c === CHAR[full]);
    if (!s) return;
    yield* work(p, {doing: "pick_up", dir: s[2]}, 5);
    I.put(s[3], s[4], {block: picked}, "pick", p.name);
    I.later(500 + I.pick(400), () => I.put(s[3], s[4], {block: full}, "grew"));
    yield* work(p, {doing: "eat", item: food, dir: "S"}, 24); mutter(p, "eat");
  }

  const DO = {
    *water(p) {                                      // the field's dry soil, a few tiles of it
      for (let n = 2 + I.pick(3); n > 0; n--) {
        const s = crop(p, dry);
        if (!s || !(yield* go(p, s[0], s[1]))) return;
        yield* work(p, {doing: "water", with: "watering_can", dir: s[2], at: [s[3], s[4]]}, 16 + I.pick(8));
        I.put(s[3], s[4], {ground: "wet_tilled"});
      }
      mutter(p, "water");
    },
    *harvest(p) {                                    // ripe wheat comes up, and seed goes in where it was
      for (let n = 2 + I.pick(3); n > 0; n--) {
        const s = crop(p, ripe);
        if (!s || !(yield* go(p, s[0], s[1]))) return;
        yield* work(p, {doing: "pick_up", dir: s[2]}, 5);
        I.put(s[3], s[4], {block: "none"}, "pick", p.name);
        yield* rest(p, 5, s[2]);
        yield* work(p, {doing: "place", dir: s[2]}, 5);
        I.put(s[3], s[4], {block: "sprout"}, "place", p.name);
        if (n === 1) emote(p.name, "star");
      }
      mutter(p, "harvest");
    },
    *chop(p) {                                       // a tree comes down; it grows again from its stump, in time
      const s = yield* visit(p, "trees", (c) => c === "T");
      if (!s) return;
      yield* work(p, {doing: "dig", with: "axe", dir: s[2], at: [s[3], s[4]]}, 34 + I.pick(16));
      I.put(s[3], s[4], {block: "stump"}, "dig", p.name); mutter(p, "chop");
      I.later(700 + I.pick(500), () => I.put(s[3], s[4], {block: "tree"}, "grew"));
      yield* rest(p, 12, s[2]);
    },
    *mine(p) {
      const s = yield* visit(p, "rocks");
      if (!s) return;
      yield* work(p, {doing: "dig", with: "pickaxe", dir: s[2], at: [s[3], s[4]]}, 28 + I.pick(16));
      if (!I.pick(3)) emote(p.name, "star");
      mutter(p, "mine"); yield* rest(p, 8, s[2]);
    },
    berries: (p) => gather(p, "bushes", "berry_bush", "bare_bush", "berries"),
    fruit: (p) => gather(p, "fruit", "fruit_tree", "bare_fruit_tree", "fruit"),
    *flower(p) {
      const s = yield* visit(p, "flowers", (c) => c === "f");
      if (!s) return;
      yield* work(p, {doing: "pick_up", dir: s[2]}, 5);
      I.put(s[3], s[4], {block: "none"}, "pick", p.name); emote(p.name, "love"); mutter(p, "flower");
      I.later(500 + I.pick(500), () => I.put(s[3], s[4], {block: "flower"}, "grew"));
      yield* rest(p, 10, "S");
    },
    *view(p) {                                       // somewhere to stand and look: the pier's end, the bridge, the top of the hill
      const s = yield* visit(p, "views", null, {run: p.name === "Nell" && !I.pick(2)});
      if (!s) return;
      mutter(p, "view"); yield* rest(p, 30 + I.pick(40), s[2]);
      if (!I.pick(3)) emote(p.name, "music");
    },
    *well(p) { const s = yield* visit(p, "well"); if (s) { yield* work(p, {doing: "take", dir: s[2]}, 6); yield* rest(p, 10, s[2]); } },
    *sign(p) { const s = yield* visit(p, "sign"); if (s) { yield* rest(p, 16, s[2]); mutter(p, "sign"); yield* rest(p, 10, s[2]); } },
    *feed(p) {                                       // the trough is filled: the hens are pleased
      const s = yield* visit(p, "trough");
      if (!s) return;
      yield* work(p, {doing: "place", dir: s[2]}, 6);
      I.trough = I.tick + 450; mutter(p, "feed");
      for (const a of I.herd) if (a.kind !== "cow") a.loved = I.tick + 30 + I.pick(30);
      yield* rest(p, 14, s[2]);
    },
    *eggs(p) { const s = yield* visit(p, "coop"); if (s) { yield* work(p, {doing: "take", dir: s[2]}, 6); emote(p.name, "happy"); mutter(p, "eggs"); yield* rest(p, 8, s[2]); } },
    *milk(p) {                                       // a cow, which waits for it
      const cow = one(I.herd.filter((a) => a.kind === "cow")), s = cow && beside(p, cow.x, cow.y);
      if (!s) return;
      cow.wait = 300;
      if (yield* go(p, s[0], s[1])) {
        yield* work(p, {doing: "milk", dir: s[2]}, 18);
        burst(I.ox + cow.x, I.oy + cow.y, "spark", 4, {dy: -.2, g: 5}); emote(p.name, "happy"); cow.loved = I.tick + 30; mutter(p, "milk");
      }
      cow.wait = 20;
    },
    *mail(p) { const s = yield* visit(p, "mail"); if (s) { yield* work(p, {doing: "take", dir: s[2]}, 6); I.mail = false; emote(p.name, "love"); mutter(p, "mail"); yield* rest(p, 12, "S"); } },
    *post(p) { const s = yield* visit(p, "mail"); if (s) { yield* work(p, {doing: "place", dir: s[2]}, 6); I.mail = true; mutter(p, "post"); yield* rest(p, 6, s[2]); } },
    *picnic(p) {
      const s = yield* visit(p, "picnic");
      if (!s) return;
      yield* work(p, {doing: "eat", item: one(["bread", "fruit", "carrot", "pumpkin", "berries"]), dir: "S"}, 26);
      burst(I.ox + p.x, I.oy + p.y, "food", 6, {dy: -.6, g: 3}); emote(p.name, "love"); yield* rest(p, 10, "S");
    },
    *stroll(p) {                                     // nowhere in particular
      for (let n = 12; n > 0; n--) {
        const x = p.x + I.pick(21) - 10, y = p.y + I.pick(15) - 7, t = I.at(x, y);
        if (!t || t[0] !== "." || someone(x, y, p)) continue;
        if (yield* go(p, x, y, {run: !I.pick(3)})) yield* rest(p, 8 + I.pick(20));
        return;
      }
    },
    *chat(p) {                                       // someone not far is called to, and waits
      const q = one(I.people.filter((o) => o !== p && !o.sail && !o.swim && !o.hold && far(p, [o.x, o.y]) < 26));
      const s = q && beside(p, q.x, q.y), way = s && route(p, s[0], s[1]);
      if (!way || way.length > 30) return;
      q.hold = way.length + 14; q.face = toward(q, p);
      if ((yield* go(p, s[0], s[1], {run: true})) && far(p, [q.x, q.y]) === 1) yield* talk(p, q, TITLE_TALK.meet);
    },
    *fire(p) {                                       // a while by the fire: something to eat, a song, a word with who is there
      const s = yield* visit(p, "fire");
      if (!s) return;
      for (let n = 2 + I.pick(3); n > 0 && I.evening(); n--) {
        yield* rest(p, 14 + I.pick(30), s[2]);
        const k = I.pick(5), round = I.people.filter((o) => o !== p && o.still && !o.hold && I.C.places.fire.includes(o.spot));
        if (k === 0) yield* work(p, {doing: "eat", item: one(["bread", "cooked_meat", "mushroom"]), dir: s[2] === "N" ? "S" : s[2]}, 24);
        else if (k === 1) emote(p.name, one(["music", "happy", "laugh"]));
        else if (k === 2) mutter(p, "fire");
        else yield* talk(p, one(round), TITLE_TALK.fire);
      }
    },
    *swim(p) {                                       // the duck, about its pond
      const [x, y] = one(I.C.pond);
      yield* go(p, x, y, {ok: afloat, pace: 4});
      yield* rest(p, 10 + I.pick(40));
      if (!I.pick(4)) emote(p.name, "music");
    },
    *sail(p) {                                       // round the island by boat: out from the pier's end, and back to it
      const ring = I.C.ring, moor = I.C.moor, [px, py] = I.C.pier, [mx, my] = moor[0];
      const splash = () => burst(I.ox + mx, I.oy + my, "water", 8, {up: 1.5, spread: 2});
      const to = function* ([x, y]) { p.x = x; p.y = y; p.doing = "walk"; yield; yield; };
      if (!p.sail) {                                 // aboard: the boat tied up there is theirs again
        if (!(yield* go(p, px, py))) return;
        yield* rest(p, 6, "E");
        I.put(mx, my, {block: "none"}, "board"); p.sail = true; splash();
        for (const t of [...moor, ring[0]]) yield* to(t);
        p.on = 0; p.turn = I.pick(2) ? 1 : -1;
      }
      let stops = 1 + I.pick(2);
      do {
        p.on = (p.on + p.turn + ring.length) % ring.length; yield* to(ring[p.on]);
        if (stops && !I.pick(90)) { stops--; mutter(p, "sea"); yield* rest(p, 30 + I.pick(40)); if (!I.pick(2)) emote(p.name, "music"); }
      } while (p.on);
      for (const t of [...moor].reverse()) yield* to(t);
      p.sail = false; p.x = px; p.y = py; p.ashore = 0;                        // ashore: the boat stays where they got off
      I.put(mx, my, {block: "boat"}, "moor"); splash();
      yield* rest(p, 8, "W");
    },
  };
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
