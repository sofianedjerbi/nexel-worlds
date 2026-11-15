// The first screen's background: a small island made by hand, with a life of its own, instead of the world you
// are about to wake in. It is part of the page (title_map.js: six blocks of land baked by tools/build_title_scene.py,
// and one of open sea used for everything round them), so it is there as soon as the pictures are: no server to
// answer, no world to load (the demo's takes many seconds to start).
// It is drawn by the game itself, as any land is: the blocks are handed over as the server would hand them, far
// from where anyone lives, and ten times a second the game is told who is where and what has changed, as a
// server's tick and its events would tell it. This file is the island's clock: its hours (a day in a little over
// three minutes, so the light, the dusk and the fire at night all pass), its field (watered wheat grows a stage and
// its soil dries), what was felled or picked growing back, its hens and cows, and the view, which goes slowly after
// one of its people, then another.
// Its people are their own (title_cast.js): they choose what to do, and no two visits are the same.
// It stops when you wake up or choose to watch: the land is forgotten and the world's own is asked for.

const TitleScene = (() => {
  const OX = -8000, OY = -8000, M = typeof TITLE_MAP === "undefined" ? null : TITLE_MAP, DAY = 2000, DIRS = [[0, -1], [1, 0], [0, 1], [-1, 0]];
  // The island, as its people know it too: where it is, its places, its hour, its dice, who is there, what is due
  const S = {on: false, tick: 0, phase: .3, timer: 0, seed: 1, people: [], herd: [], due: [], mail: false, trough: 0, eye: null, till: 0, ox: OX, oy: OY, C: M && M.cast, w: M && M.w, h: M && M.h};
  S.rnd = () => (S.seed = (Math.imul(S.seed, 1103515245) + 12345) >>> 0) / 4294967296;
  S.pick = (n) => Math.floor(S.rnd() * n);
  S.at = (x, y) => tile(OX + x, OY + y);
  S.evening = () => S.phase >= .7 && S.phase < .98;
  S.later = (ticks, fn) => S.due.push([S.tick + ticks, fn]);
  // A tile of the island changes, said as a server says it: the game shows it as it shows any (a tree falls, wheat
  // comes up and goes to the one who pulled it, a thing pops into its place)
  S.put = (x, y, now, cause, by) => {
    const t = S.at(x, y);
    if (t) onEvent({type: "tile", x: OX + x, y: OY + y, ground: now.ground || CH[t[1]], block: now.block || (GROUND.has(t[0]) ? "none" : CH[t[0]]), cause, by});
  };
  S.say = (p, text, shout = false) => {                      // (over their head, and not in the world's chat)
    bubbles.push({name: p.name, text, t: performance.now() / 1000, shout});
    const em = emoteFor(text); if (em) setTimeout(() => S.on && emote(p.name, em), 2500);
  };
  const free = (x, y, but) => { const t = S.at(x, y); return !!t && t[0] === "." && ![...S.herd, ...S.people].some((o) => o !== but && o.x === x && o.y === y); };

  function herd(kind, n, id0, box, every) {                  // animals of a kind, each on bare grass of its field
    const out = [];
    for (let i = 0; i < n; i++) {
      const a = {id: id0 + i, kind, box, every, wait: S.pick(every), loved: 0, x: box[0], y: box[1]};
      for (let k = 0; k < 40; k++) { a.x = box[0] + S.pick(box[2] - box[0] + 1); a.y = box[1] + S.pick(box[3] - box[1] + 1); if (free(a.x, a.y, a) && !out.some((o) => o.x === a.x && o.y === a.y)) break; }
      out.push(a);
    }
    return out;
  }
  function graze(a) {                                        // a step now and then, inside its field, where the grass is bare; at night it sleeps
    if (--a.wait > 0 || S.phase >= .75) return;
    a.wait = a.every + S.pick(a.every);
    const [dx, dy] = DIRS[S.pick(4)], x = a.x + dx, y = a.y + dy;
    if (x >= a.box[0] && x <= a.box[2] && y >= a.box[1] && y <= a.box[3] && free(x, y, a)) { a.x = x; a.y = y; }
  }
  function grow() {                                          // a tile of the field: watered, its wheat grows a stage and its soil dries; dry, it grows now and then
    const [x0, y0, x1, y1] = S.C.field, x = x0 + S.pick(x1 - x0 + 1), y = y0 + S.pick(y1 - y0 + 1), t = S.at(x, y), next = {";": "crop", "\"": "ripe_crop"}[t[0]];
    if (t[1] === "u") S.put(x, y, {ground: "tilled", ...(next ? {block: next} : {})}, "grew");
    else if (next && !S.pick(6)) S.put(x, y, {block: next}, "grew");
  }
  const z = (a) => levelAt(OX + a.x, OY + a.y) || 0;
  const said = (a) => a.kind === "agent"                     // (someone held in a talk stands and faces who spoke)
    ? {kind: "agent", name: a.name, id: a.id, x: OX + a.x, y: OY + a.y, hp: HP_MAX, doing: a.hold ? "look" : a.doing, weapon: null, dir: a.hold ? a.face : a.doing && a.doing !== "walk" ? a.dir : null, tid: null,
       at: a.aim ? [OX + a.aim[0], OY + a.aim[1]] : null, with: a.with || null, item: a.item || null, run: !!a.run, sail: !!a.sail, z: z(a), race: a.race, ...(a.worn ? {worn: a.worn} : {}), ...(a.swim ? {swim: true} : {})}
    : {kind: a.kind, id: a.id, x: OX + a.x, y: OY + a.y, z: z(a), hp: 10, love: a.loved > S.tick, scared: false};
  function sea() {                                           // open sea wherever the screen looks past the island's blocks
    const [x, y, w, h] = viewRect(8);
    for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++) for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++)
      if (!blocks.has(bkey(bx, by))) onRegion({x: bx * B, y: by * B, w: B, h: B, ...M.sea});
  }
  function step() {
    S.tick++; S.phase = (.3 + S.tick / DAY) % 1;
    const now = S.due.filter(([at]) => at <= S.tick); S.due = S.due.filter(([at]) => at > S.tick);
    for (const [, fn] of now) fn();                          // what was felled or picked is grown again
    if (S.tick % 8 === 0) grow();
    for (const p of S.people) TitleCast.live(p);
    TitleCast.hail();
    for (const a of S.herd) graze(a);
    const hm = Math.floor(S.phase * 1440), two = (n) => String(n).padStart(2, "0"), night = S.phase >= .75, where = (s) => [[OX + s[3], OY + s[4]]];
    onTick({type: "tick", tick: S.tick, time: `day 1, ${two(Math.floor(hm / 60))}:${two(hm % 60)}${night ? " (night)" : ""}`, night, phase: S.phase, entities: [...S.people, ...S.herd].map(said), items: [],
      mail: S.mail ? where(S.C.places.mail[0]) : [], troughs: S.trough > S.tick ? where(S.C.places.trough[0]) : [], fires: []});
    look(); sea();
  }
  // The view: it goes slowly after one of them for a while, then after another (someone on land; in the evening,
  // someone at the fire), never as far as the open sea
  function look() {
    if (!S.eye || S.eye.sail || S.tick >= S.till) {
      const who = S.people.filter((p) => !p.sail && !p.swim && p !== S.eye), fire = who.filter((p) => p.last === "fire");
      S.eye = (fire.length ? fire : who)[S.pick((fire.length ? fire : who).length)] || S.eye; S.till = S.tick + 140 + S.pick(120);
    }
    const [x0, y0, x1, y1] = S.C.view, x = Math.max(x0, Math.min(x1, S.eye.x)), y = Math.max(y0, Math.min(y1, S.eye.y));
    camT.x += (OX + x - camT.x) * .035; camT.y += (OY + y - camT.y) * .035;
  }
  function start(seed) {                                     // (a seed: the same play again, for a test; none: the hour's own)
    if (S.on || !M || me) return;
    Object.assign(S, {on: true, tick: 0, phase: .3, seed: (seed || Date.now()) >>> 0 || 1, due: [], mail: false, trough: 0, people: [], herd: [], eye: null, till: 0});
    for (const b of M.blocks) onRegion({...b, x: b.x + OX, y: b.y + OY});
    cam.x = camT.x = OX + S.C.centre[0]; cam.y = camT.y = OY + S.C.centre[1] + 4 * Math.sin(1);
    S.herd = [...herd("chicken", 3, 9101, S.C.pen, 14), ...herd("chick", 1, 9111, S.C.pen, 9), ...herd("cow", 2, 9121, S.C.meadow, 26)];
    S.people = TitleCast.wake(S);
    sea(); step();
    S.timer = setInterval(step, 100);
  }
  function stop() {                                          // you wake up, or watch: the island is forgotten, the world's land is asked for
    if (!S.on) return;
    S.on = false; clearInterval(S.timer);
    ents.clear(); blocks.clear(); dirtyTiles.length = 0; requested.clear(); lastWatch = ""; arrivingNow = true; fireAt = [];
    bubbles.length = 0; emotes.clear(); mailAt = new Set(); troughAt = new Set();
    if (!me) { cam.x = camT.x = 0; cam.y = camT.y = 0; }
  }
  return {start, stop, step, get on() { return S.on; }, S};
})();
// It plays from the moment the pictures are loaded, while the first screen shows (not when you came to follow someone)
ready.then(() => { if ($("joinbox").style.display !== "none" && !new URLSearchParams(location.search).get("follow")) TitleScene.start(); });
new MutationObserver(() => { if ($("joinbox").style.display === "none") TitleScene.stop(); }).observe($("joinbox"), {attributes: true, attributeFilter: ["style"]});
