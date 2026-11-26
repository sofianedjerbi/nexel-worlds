// The island's people: their errands, what each thing they do does to the island (title_cast.js chooses which, and walks them there).
// Split out of TitleCast (#191): the same errands, given TitleCast's ways of going and doing (K: route, go, work, rest, visit,
// beside, crop, talk, mutter...) and the island being shown, K.I (title_scene.js gives it at each visit: read when an errand runs).
// An errand is a generator: each `yield` is a tenth of a second going by.
//   the errands come in three groups, each a function of its own: what is done in the field and woods, about the farm, and in company or on the water
//   TitleErrands(K) -> {water, harvest, chop, ...: (p) -> the errand of person p}
// field and woods: water, harvest, chop, mine, pick
const titleWork = (K) => {
  const {crop, dry, go, mutter, rest, ripe, visit, work} = K;
  function* gather(p, kind, full, picked, food) {
    const s = yield* visit(p, kind, (c) => c === CHAR[full]);
    if (!s) return;
    yield* work(p, {doing: "pick_up", dir: s[2]}, 5);
    K.I.put(s[3], s[4], {block: picked}, "pick", p.name);
    K.I.later(500 + K.I.pick(400), () => K.I.put(s[3], s[4], {block: full}, "grew"));
    yield* work(p, {doing: "eat", item: food, dir: "S"}, 24); mutter(p, "eat");
  }
  const WORK = {
    *water(p) {                                      // the field's dry soil, a few tiles of it
      for (let n = 2 + K.I.pick(3); n > 0; n--) {
        const s = crop(p, dry);
        if (!s || !(yield* go(p, s[0], s[1]))) return;
        yield* work(p, {doing: "water", with: "watering_can", dir: s[2], at: [s[3], s[4]]}, 16 + K.I.pick(8));
        K.I.put(s[3], s[4], {ground: "wet_tilled"});
      }
      mutter(p, "water");
    },
    *harvest(p) {                                    // ripe wheat comes up, and seed goes in where it grew
      for (let n = 2 + K.I.pick(3); n > 0; n--) {
        const s = crop(p, ripe);
        if (!s || !(yield* go(p, s[0], s[1]))) return;
        yield* work(p, {doing: "pick_up", dir: s[2]}, 5);
        K.I.put(s[3], s[4], {block: "none"}, "pick", p.name);
        yield* rest(p, 5, s[2]);
        yield* work(p, {doing: "place", dir: s[2]}, 5);
        K.I.put(s[3], s[4], {block: "sprout"}, "place", p.name);
        if (n === 1) emote(p.name, "star");
      }
      mutter(p, "harvest");
    },
    *chop(p) {                                       // a tree comes down; it grows again from its stump, in time
      const s = yield* visit(p, "trees", (c) => c === "T");
      if (!s) return;
      yield* work(p, {doing: "dig", with: "axe", dir: s[2], at: [s[3], s[4]]}, 34 + K.I.pick(16));
      K.I.put(s[3], s[4], {block: "stump"}, "dig", p.name); mutter(p, "chop");
      K.I.later(700 + K.I.pick(500), () => K.I.put(s[3], s[4], {block: "tree"}, "grew"));
      yield* rest(p, 12, s[2]);
    },
    *mine(p) {
      const s = yield* visit(p, "rocks");
      if (!s) return;
      yield* work(p, {doing: "dig", with: "pickaxe", dir: s[2], at: [s[3], s[4]]}, 28 + K.I.pick(16));
      if (!K.I.pick(3)) emote(p.name, "star");
      mutter(p, "mine"); yield* rest(p, 8, s[2]);
    },
    berries: (p) => gather(p, "bushes", "berry_bush", "bare_bush", "berries"),
    fruit: (p) => gather(p, "fruit", "fruit_tree", "bare_fruit_tree", "fruit"),
  };
  return WORK;
};

// about the farm and the house
const titleChores = (K) => {
  const {beside, go, mutter, one, rest, visit, work} = K;
  const CHORES = {
    *flower(p) {
      const s = yield* visit(p, "flowers", (c) => c === "f");
      if (!s) return;
      yield* work(p, {doing: "pick_up", dir: s[2]}, 5);
      K.I.put(s[3], s[4], {block: "none"}, "pick", p.name); emote(p.name, "love"); mutter(p, "flower");
      K.I.later(500 + K.I.pick(500), () => K.I.put(s[3], s[4], {block: "flower"}, "grew"));
      yield* rest(p, 10, "S");
    },
    *view(p) {                                       // somewhere to stand and look: the pier's end, the bridge, the top of the hill
      const s = yield* visit(p, "views", null, {run: p.name === "Nell" && !K.I.pick(2)});
      if (!s) return;
      mutter(p, "view"); yield* rest(p, 30 + K.I.pick(40), s[2]);
      if (!K.I.pick(3)) emote(p.name, "music");
    },
    *well(p) { const s = yield* visit(p, "well"); if (s) { yield* work(p, {doing: "take", dir: s[2]}, 6); yield* rest(p, 10, s[2]); } },
    *sign(p) { const s = yield* visit(p, "sign"); if (s) { yield* rest(p, 16, s[2]); mutter(p, "sign"); yield* rest(p, 10, s[2]); } },
    *feed(p) {                                       // the trough is filled: the hens are pleased
      const s = yield* visit(p, "trough");
      if (!s) return;
      yield* work(p, {doing: "place", dir: s[2]}, 6);
      K.I.trough = K.I.tick + 450; mutter(p, "feed");
      for (const a of K.I.herd) if (a.kind !== "cow") a.loved = K.I.tick + 30 + K.I.pick(30);
      yield* rest(p, 14, s[2]);
    },
    *eggs(p) { const s = yield* visit(p, "coop"); if (s) { yield* work(p, {doing: "take", dir: s[2]}, 6); emote(p.name, "happy"); mutter(p, "eggs"); yield* rest(p, 8, s[2]); } },
    *milk(p) {                                       // a cow, which waits for it
      const cow = one(K.I.herd.filter((a) => a.kind === "cow")), s = cow && beside(p, cow.x, cow.y);
      if (!s) return;
      cow.wait = 300;
      if (yield* go(p, s[0], s[1])) {
        yield* work(p, {doing: "milk", dir: s[2]}, 18);
        burst(K.I.ox + cow.x, K.I.oy + cow.y, "spark", 4, {dy: -.2, g: 5}); emote(p.name, "happy"); cow.loved = K.I.tick + 30; mutter(p, "milk");
      }
      cow.wait = 20;
    },
    *mail(p) { const s = yield* visit(p, "mail"); if (s) { yield* work(p, {doing: "take", dir: s[2]}, 6); K.I.mail = false; emote(p.name, "love"); mutter(p, "mail"); yield* rest(p, 12, "S"); } },
    *post(p) { const s = yield* visit(p, "mail"); if (s) { yield* work(p, {doing: "place", dir: s[2]}, 6); K.I.mail = true; mutter(p, "post"); yield* rest(p, 6, s[2]); } },
    *picnic(p) {
      const s = yield* visit(p, "picnic");
      if (!s) return;
      yield* work(p, {doing: "eat", item: one(["bread", "fruit", "carrot", "pumpkin", "berries"]), dir: "S"}, 26);
      burst(K.I.ox + p.x, K.I.oy + p.y, "food", 6, {dy: -.6, g: 3}); emote(p.name, "love"); yield* rest(p, 10, "S");
    },
  };
  return CHORES;
};

// company and the water: a stroll, a word, the fire, the pond, the boat
const titleOutings = (K) => {
  const {afloat, beside, far, go, mutter, one, rest, route, someone, talk, toward, visit, work} = K;
  const OUTINGS = {
    *stroll(p) {                                     // nowhere in particular
      for (let n = 12; n > 0; n--) {
        const x = p.x + K.I.pick(21) - 10, y = p.y + K.I.pick(15) - 7, t = K.I.at(x, y);
        if (!t || t[0] !== "." || someone(x, y, p)) continue;
        if (yield* go(p, x, y, {run: !K.I.pick(3)})) yield* rest(p, 8 + K.I.pick(20));
        return;
      }
    },
    *chat(p) {                                       // someone not far is called to, and waits
      const q = one(K.I.people.filter((o) => o !== p && !o.sail && !o.swim && !o.hold && far(p, [o.x, o.y]) < 26));
      const s = q && beside(p, q.x, q.y), way = s && route(p, s[0], s[1]);
      if (!way || way.length > 30) return;
      q.hold = way.length + 14; q.face = toward(q, p);
      if ((yield* go(p, s[0], s[1], {run: true})) && far(p, [q.x, q.y]) === 1) yield* talk(p, q, TITLE_TALK.meet);
    },
    *fire(p) {                                       // a while by the fire: something to eat, a song, a word with who is there
      const s = yield* visit(p, "fire");
      if (!s) return;
      for (let n = 2 + K.I.pick(3); n > 0 && K.I.evening(); n--) {
        yield* rest(p, 14 + K.I.pick(30), s[2]);
        const k = K.I.pick(5), round = K.I.people.filter((o) => o !== p && o.still && !o.hold && K.I.C.places.fire.includes(o.spot));
        if (k === 0) yield* work(p, {doing: "eat", item: one(["bread", "cooked_meat", "mushroom"]), dir: s[2] === "N" ? "S" : s[2]}, 24);
        else if (k === 1) emote(p.name, one(["music", "happy", "laugh"]));
        else if (k === 2) mutter(p, "fire");
        else yield* talk(p, one(round), TITLE_TALK.fire);
      }
    },
    *swim(p) {                                       // the duck, about its pond
      const [x, y] = one(K.I.C.pond);
      yield* go(p, x, y, {ok: afloat, pace: 4});
      yield* rest(p, 10 + K.I.pick(40));
      if (!K.I.pick(4)) emote(p.name, "music");
    },
    *sail(p) {                                       // round the island by boat: out from the pier's end, and back to it
      const ring = K.I.C.ring, moor = K.I.C.moor, [px, py] = K.I.C.pier, [mx, my] = moor[0];
      const splash = () => { burst(K.I.ox + mx, K.I.oy + my, "water", 8, {up: 1.5, spread: 2}); sfx("water", K.I.ox + mx, K.I.oy + my); };
      const to = function* ([x, y]) { p.x = x; p.y = y; p.doing = "walk"; yield; yield; };
      if (!p.sail) {                                 // aboard: the boat tied up there is theirs again
        if (!(yield* go(p, px, py))) return;
        yield* rest(p, 6, "E");
        K.I.put(mx, my, {block: "none"}, "board"); p.sail = true; splash();
        for (const t of [...moor, ring[0]]) yield* to(t);
        p.on = 0; p.turn = K.I.pick(2) ? 1 : -1;
      }
      let stops = 1 + K.I.pick(2);
      do {
        p.on = (p.on + p.turn + ring.length) % ring.length; yield* to(ring[p.on]);
        if (stops && !K.I.pick(90)) { stops--; mutter(p, "sea"); yield* rest(p, 30 + K.I.pick(40)); if (!K.I.pick(2)) emote(p.name, "music"); }
      } while (p.on);
      for (const t of [...moor].reverse()) yield* to(t);
      p.sail = false; p.x = px; p.y = py; p.ashore = 0;                        // ashore: the boat stays where they got off
      K.I.put(mx, my, {block: "boat"}, "moor"); splash();
      yield* rest(p, 8, "W");
    },
  };
  return OUTINGS;
};
const TitleErrands = (K) => ({...titleWork(K), ...titleChores(K), ...titleOutings(K)});
