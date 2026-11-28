// Crops, animals, fruit trees, fire and fences.

const CROPS = RULES.crops;
const CROP_ROW = {wheat: 8, pumpkin: 9, cauliflower: 3, lettuce: 7, eggplant: 5, carrot: 2};
const cropSpecies = (x, y) => CROPS[((Math.imul(x, 73856093) ^ Math.imul(y, 19349663)) >>> 0) % CROPS.length];
const FLOWERS = [[0, 3], [1, 3], [2, 3], [4, 3], [5, 3], [6, 3], [8, 3], [9, 3], [10, 3], [11, 3],
  [0, 4], [1, 4], [4, 4], [5, 4], [6, 4], [8, 4], [9, 4], [10, 4], [11, 4]];
// animal sheets: [row, frames, ms per frame] per behaviour, measured from the pack
const ANIMALS = {
  // bird sheets: row 1 is a hop (squash and stretch), row 2 the 8-frame walk; idle stays on row 0
  chicken: {fw: 16, idle: [0, 4, 220], walk: [2, 8, 90], alt: [0, 4, 260], sleep: [8, 4, 400], love: [26, 7, 140], hearts: [25, 7]},
  chick: {fw: 16, idle: [0, 4, 220], walk: [2, 8, 80], alt: [0, 4, 260], sleep: [8, 4, 400], love: [14, 7, 140], hearts: [13, 7]},
  cow: {fw: 32, idle: [0, 3, 260], walk: [1, 8, 90], alt: [6, 4, 220], sleep: [4, 4, 400], love: [7, 6, 160]},
  calf: {fw: 32, idle: [0, 2, 300], walk: [6, 8, 90], alt: [7, 4, 220], sleep: [4, 4, 400], love: [8, 6, 160]},
};
// Wild enemies (sim/wild.py): one sheet each, drawn in design/enemies; rows are down, up, left, right. Each animation is
// [first column, frames, ms a frame (or one per frame)]. The tusker warns (paws the ground) and runs for as long as the
// server says; the others play their whole action once from the moment the warning starts, so the blow lands on its strike frame.
// Old Mossback and its sporelings have several actions (`once`), named as the server names them; `hp`: a boss's whole life, for its bar across the top (bossbar.js).
const WILD = {
  tusker: {cw: 32, ch: 32, idle: [0, 8, 260], walk: [8, 8, 90], warn: [16, 4, 170], run: [20, 8, 55]},
  pincer: {cw: 24, ch: 16, idle: [0, 8, [800, 300, 300, 600, 140, 500, 140, 600]], walk: [8, 8, 80], act: [16, 5, [140, 420, 80, 220, 220]]},
  strawman: {cw: 32, ch: 32, idle: [0, 4, [900, 900, 500, 180]], walk: [4, 8, 110], act: [12, 4, [520, 90, 260, 300]]},
  wisp: {cw: 32, ch: 32, idle: [0, 8, 140], walk: [8, 8, 90], act: [16, 6, [220, 300, 90, 160, 160, 160]]},
  wyrm: {cw: 48, ch: 32, idle: [0, 8, 150], walk: [8, 8, 95], act: [16, 4, [480, 90, 240, 280]]},
  grumblestump: {cw: 40, ch: 44, idle: [0, 8, [400, 300, 260, 300, 400, 300, 260, 300]], walk: [8, 8, 130], act: [16, 8, [180, 260, 200, 200, 80, 160, 200, 260]], sleep: [24, 8, 600]},
  snapbloom: {cw: 36, ch: 40, idle: [0, 8, 220], walk: [8, 8, 110], act: [16, 11, [160, 180, 220, 150, 150, 70, 110, 140, 140, 140, 200]]},
  hob: {cw: 32, ch: 42, idle: [0, 8, [260, 220, 220, 260, 300, 260, 140, 260]], walk: [8, 8, 110], act: [16, 7, [260, 320, 80, 140, 180, 220, 260]]},     // (an ally: sim/hob.py)
  gustling: {cw: 32, ch: 40, idle: [0, 8, 110], walk: [8, 8, 70], act: [16, 11, [170, 130, 100, 100, 100, 80, 160, 160, 130, 130, 160]]},
  mossback: {cw: 80, ch: 64, hp: 60, sleep: [0, 8, 320], idle: [8, 8, 240], walk: [16, 8, 120], stomp: [24, 7, [160, 300, 220, 80, 180, 220, 200]], snap: [31, 7, [180, 200, 200, 70, 260, 140, 180]], shake: [38, 11, [180, 150, 150, 90, 90, 90, 90, 100, 110, 180, 200]], once: ["stomp", "snap", "shake"]},
  nyxwing: {cw: 128, ch: 114, hp: 120, idle: [0, 8, 96], walk: [8, 8, 48], breath: [16, 8, [192, 192, 193, 96, 96, 96, 96, 96]],    // (drawn by nyxwing.js: its moves are timed to its song)
    storm: [24, 21, [192, 192, 193, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 96, 96]], dive: [45, 9, [192, 192, 193, 96, 96, 96, 96, 96, 96]],
    sweep: [54, 8, [192, 192, 193, 64, 64, 64, 96, 96]], rush: [62, 6, [96, 96, 193, 192, 192, 192]]},
  skeleton: {cw: 24, ch: 26, idle: [0, 8, [300, 260, 300, 200, 260, 300, 90, 90]], walk: [8, 8, 85], act: [16, 10, [160, 200, 120, 120, 80, 90, 140, 160, 160, 160]]},   // (rattles 0.6 s, then the swipe: sim/skeleton.py)
  redknee: {cw: 62, ch: 44, idle: [0, 8, [300, 260, 300, 160, 200, 160, 220, 260]], walk: [8, 8, 95], act: [16, 12, [160, 200, 240, 200, 140, 90, 110, 80, 70, 140, 180, 220]]},   // (rears up 0.8 s, then the pounce: sim/redknee.py)
  sporeling: {cw: 24, ch: 24, idle: [0, 8, 240], walk: [8, 8, 75], land: [16, 6, [80, 80, 160, 120, 90, 140]], puff: [22, 6, [150, 150, 90, 130, 150, 140]], once: ["land", "puff"]},
};
// Each creature's own sounds (music/sfx.py, "Creatures", picked by ear): its warning, its blow when it lands, its cry
// when it is hit. `slams`: its blow is the slam itself (one sound for the ring, however many it hits: wildEvent).
const CRY = {
  tusker: {warn: "tusker_warn", blow: "tusker_ram", hurt: "tusker_hurt"},
  pincer: {warn: "pincer_warn", blow: "pincer_snap", hurt: "pincer_hurt"},
  strawman: {warn: "strawman_warn", blow: "strawman_swipe", hurt: "strawman_hurt"},
  wyrm: {warn: "wyrm_warn", blow: "wyrm_lunge", hurt: "wyrm_hurt"},
  gustling: {warn: "gustling_spin"},
  grumblestump: {warn: "grumblestump_warn", slams: true, hurt: "grumblestump_hurt"},
  snapbloom: {warn: "snapbloom_warn", blow: "snapbloom_bite", hurt: "snapbloom_hurt"},
  hob: {warn: "hob_warn"}, wisp: {warn: "gloom"}, mossback: {warn: "boss_groan"},
  skeleton: {warn: "skeleton_rattle", blow: "skeleton_swipe", hurt: "skeleton_hurt"},
  redknee: {warn: "redknee_warn", blow: "redknee_pounce", hurt: "redknee_hurt"},
  nyxwing: {slams: true, hurt: "drake_hurt"},          // (its warnings and blows sound in nyxwing.js: a scream when its jaws open)
};
// A blow lands (an "attack" event, its `who` {kind: "tusker", ...} when it is a wild one): the creature's own sound in place of a
// punch and a thump; a creature that is hit cries its own cry in place of the thump.
function wildBlow(e, tgt, tx, ty) {
  const kind = e.who ? e.who.kind : "", foe = CRY[kind] || {}, cry = tgt && CRY[tgt.e.kind] ? CRY[tgt.e.kind].hurt : null;
  if (foe.blow) sfx(foe.blow, e.x, e.y);
  else if (!foe.slams) { if (WILD[kind]) sfx("punch", e.x, e.y); sfx(cry || "hit", tx, ty); }
}
// The moves of the wild ones and the hob, as the server tells them (sim/wild.py, gust.py, stump.py, hob.py): dust,
// sparks, a sound, and a flash on whom they touched.
function wildEvent(e) {
  if (e.type === "windup" && e.kind === "nyxwing") Nyx.windup(e);          // (nyxwing.js)
  if (e.type === "slam") { burst(e.x, e.y, "dust", 22, {up: 1.2, spread: 5, g: 3}); sfx("grumblestump_slam", e.x, e.y); }        // a grumblestump's arms come down: a ring of dust
  if (e.type === "flare") {                                                            // a hob's firebox bursts: a blaze of sparks, it and what it burnt lit up
    burst(e.x, e.y, "spark", 34, {up: 4, spread: 6, g: 4, life: .7}); burst(e.x, e.y, "rage", 10, {up: 2.5, spread: 3, g: 6});
    sfx("hob_burst", e.x, e.y);
    const now = performance.now(); flashes.set("hob" + e.id, now); for (const [k, id] of e.burnt || []) flashes.set(k + id, now);
    for (const k of new Set((e.burnt || []).map(([k]) => k))) if (CRY[k] && CRY[k].hurt) sfx(CRY[k].hurt, e.x, e.y);   // what it burnt cries out
  }
  if (e.type === "hob_lit") { burst(e.x, e.y, "spark", 14, {up: 2, spread: 2, g: 5}); sfx("hob_lit", e.x, e.y); }   // set down: it catches
  if (e.type === "snatch") { burst(e.x, e.y, "dust", 10, {up: 2.5, spread: 3, g: 2}); sfx("gustling_snatch", e.x, e.y); }        // a gustling took what was in a hand
  if (e.type === "scatter") { burst(e.x, e.y, "dust", 14, {up: 1.5, spread: 4, g: 1}); sfx("gustling_scatter", e.x, e.y); }        // hit while it spun up: it blows apart
}
function wildFrame([col, n, ms], t, loop) {
  if (!Array.isArray(ms)) return col + (loop ? Math.floor(t / ms) % n : Math.min(n - 1, Math.floor(t / ms)));
  const all = ms.reduce((a, b) => a + b, 0);
  t = loop ? t % all : Math.min(t, all - 1);
  let i = 0;
  while (t >= ms[i]) t -= ms[i++];
  return col + i;
}
// A tusker's dust and temper. Pawing the ground: a puff thrown back from its hoof at each scrape. Charging: earth
// torn up behind it all the way, big puffs and bits of the ground itself (effects.js KICK), so its line is seen.
// Angry: steam blown from its snout to both sides every half second, and a red spark off its back now and then.
const TUSK_FX = {paw: 170, tear: 40, snort: 520};          // ms between two of each
function tuskerFx(p, e, now) {
  const [fx, fy] = e.dir || [p.fx || 0, p.fy || 1], r = Math.random, bits = KICK[gndAt(Math.round(p.x), Math.round(p.y))] || PCOL.dust;
  const due = (k) => now - (p[k] || 0) > TUSK_FX[k] && (p[k] = now);
  if (e.act === "windup" && due("paw")) {
    const x = p.x + .5 + fx * .3, y = p.y + .9 - UP + fy * .2;
    for (let i = 0; i < 3; i++) parts.push({x: x + (r() - .5) * .3, y, vx: -fx * (1.5 + r() * 1.5) + (r() - .5) * .8, vy: -fy * (1 + r()) - .5 - r() * .8, g: -.4,
      life: .3 + r() * .25, age: 0, c: "rgba(236,222,190,.85)", s: i ? 2 : 3});
    parts.push({x, y, vx: -fx * (2 + r() * 2) + (r() - .5), vy: -2 - r() * 1.5 - fy, g: 12, floor: y + .05 + r() * .1 - fy * .4, life: .5, age: 0, c: bits[0], s: 1});
  }
  if (e.act === "charge" && due("tear")) {
    const x = p.x + .5 - fx * .6, y = p.y + .9 - UP - fy * .45;
    for (let i = 0; i < 3; i++) parts.push({x: x + (r() - .5) * .5, y: y + (r() - .5) * .2, vx: -fx * (.6 + r() * 1.6) + (r() - .5) * 1.4, vy: -fy * (.5 + r()) - .3 - r() * .9, g: -.8,
      life: .4 + r() * .45, age: 0, c: i % 2 ? "rgba(233,217,180,.85)" : "rgba(246,238,216,.85)", s: i === 0 ? 4 : i === 1 ? 3 : 2});
    for (let i = 0; i < 2; i++) parts.push({x: x + (r() - .5) * .5, y, vx: -fx * (1 + r() * 2) + (r() - .5) * 2.2, vy: -2 - r() * 2.2 - fy * .5, g: 13,
      floor: y + .05 + r() * .15 - fy * .4, life: .55 + r() * .3, age: 0, c: bits[i % bits.length], s: r() < .3 ? 2 : 1});
  }
  if (e.angry && due("snort")) {
    const x = p.x + .5 + fx * .7, y = p.y + .45 - UP + fy * .35, side = fx ? [0, 1] : [1, 0];
    for (const s of [-1, 1]) for (let i = 0; i < 3; i++) parts.push({x, y, vx: fx * (.8 + r() * .8) + side[0] * s * (.9 + i * .5), vy: fy * .6 + side[1] * s * (.5 + i * .3) - .7 - r() * .4, g: -1.6,
      life: .35 + i * .12, age: 0, c: i ? "rgba(255,255,255,.8)" : "rgba(255,238,230,.9)", s: i === 2 ? 1 : 2});
    if (r() < .6) parts.push({x: p.x + .5 + (r() - .5) * .6, y: p.y + .1 - UP, vx: (r() - .5) * 2, vy: -2.5 - r() * 1.5, g: 6, life: .45, age: 0, c: r() < .5 ? "#f0503f" : "#ffb347", s: 1});
  }
}
const ANGER = [".r...r.", "rr...rr", ".......", "rr...rr", ".r...r."];      // the mark over one that is angry (a tusker that was hit: sim/wild.py)
function drawWild(p, x, y, now) {
  if (p.e.kind === "nyxwing") return Nyx.draw(p, x, y, now);              // (nyxwing.js)
  const e = p.e, A = WILD[e.kind], z = zoom;
  const moving = now - p.moved < 350 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
  if (A.once ? e.act !== p.act && A.once.includes(e.act) : e.act === "windup" && p.act !== "windup") {      // the warning starts:
    p.windAt = now; p.anim = e.act; p.animDir = e.dir;                                                    // play it from its first frame
  }
  p.act = e.act;
  if (e.kind === "tusker") tuskerFx(p, e, now);
  const since = now - (p.windAt || -1e9), once = A.once ? A[p.anim] : A.act, acting = once && since < once[2].reduce((a, b) => a + b, 0);
  const [fx, fy] = acting && p.animDir ? p.animDir : e.act && e.dir ? e.dir : [p.fx, p.fy], row = fy > 0 ? 0 : fy < 0 ? 1 : fx < 0 ? 2 : 3;
  const calm = () => wildFrame(e.act === "sleep" ? A.sleep : moving ? A.walk : A.idle, now + e.id * 137, true);
  let col, shake = 0;
  if (A.warn) {
    col = e.act === "windup" ? wildFrame(A.warn, since, true) : e.act === "charge" ? wildFrame(A.run, now, true) : calm();
    if (e.act === "stun") shake = Math.round(Math.sin(now / 45)) * z;       // dazed: it rammed something
  } else col = acting ? wildFrame(once, since, false) : calm();
  const blit = () => ctx.drawImage(IMG[e.kind], col * A.cw, row * A.ch, A.cw, A.ch, x - (A.cw - 16) / 2 * z + shake, y - (A.ch - 16) * z, A.cw * z, A.ch * z);
  blit();
  const fl = flashes.get(e.kind + e.id);
  if (fl && now - fl < 120) { ctx.globalCompositeOperation = "lighter"; blit(); ctx.globalCompositeOperation = "source-over"; }
  if (e.angry) {                                             // angry: the red mark by its head, beating
    const mx = x + 13 * z, my = y - (A.ch - 16) * z + 3 * z - (Math.floor(now / 170) % 2) * z;
    ANGER.forEach((row, j) => [...row].forEach((ch, i) => { if (ch === "r") { ctx.fillStyle = "#6e1d1d"; ctx.fillRect(mx + i * z, my + (j + 1) * z, z, z); } }));
    ANGER.forEach((row, j) => [...row].forEach((ch, i) => { if (ch === "r") { ctx.fillStyle = "#f0503f"; ctx.fillRect(mx + i * z, my + j * z, z, z); } }));
  }
}
const VARIANTS = {chicken: ["chicken", "chicken", "chicken_brown", "chicken_red", "chicken_blue", "chicken_green"],
  cow: ["cow", "cow", "cow_light", "cow_pink", "cow_purple", "cow_green"],
  chick: ["chick", "chick", "chick_brown", "chick_red", "chick_blue", "chick_green"],
  calf: ["calf", "calf", "calf_light", "calf_pink", "calf_purple", "calf_green"]};
const animalSheet = (kind, id) => IMG[VARIANTS[kind][Math.floor(hash(id, 3, 91) * VARIANTS[kind].length)]];
const FRUITS = ["tree_apple", "tree_pear", "tree_peach", "tree_orange"];
const fruitKind = (x, y) => Math.floor(hash(x, y, 33) * 4);   // index into FRUITS (and fruit_bare.png)
const fruitSheet = (x, y) => IMG[FRUITS[fruitKind(x, y)]];
const FRUIT_ICON = [[16, 32], [80, 32], [112, 32], [48, 32]];   // trees.png: apple, pear, peach, orange
const BERRY_BUSH = [32, 48, 64];                                // trees.png x of the red, purple, blue bushes (row 48)
const BERRY_ICON = [[16, 64], [48, 64], [64, 64]];              // matching single berries (row 64)
const chestOpen = new Map(), doors = new Map(), doorShut = new Map();      // (doorShut: when each door last closed, structures.js)
let occupied = new Set();

// A chair is turned to what it is set at: a table or a fire a tile or two from it (every chair faced east, the
// sheet's first of four: of two chairs by a fire, one had its back to it). With neither near: east.
const CHAIR = {E: 64, W: 80, S: 96, N: 112};          // (the sheet's four chairs: where each is, by the way it faces)
function chairFaces(x, y) {
  for (const far of [1, 2]) for (const [way, dx, dy] of [["E", 1, 0], ["W", -1, 0], ["S", 0, 1], ["N", 0, -1]])
    if ("L^".includes(combAt(x + dx * far, y + dy * far) || "-")) return way;
  return "E";
}
// A gate in a fence (or a wall) that runs north and south: seen from the side (sprites.js)
function gateSide(x, y) {
  const f = (dx, dy) => "#gW%".includes(combAt(x + dx, y + dy) || "-");
  return (f(0, -1) || f(0, 1)) && !f(-1, 0) && !f(1, 0);
}
// (a fence's rails go on to a gate beside it that is seen from the front: to its hinge post, and for its door to
// shut on. Not to one over or under it: that gate's leaves hang from this fence's own posts)
function fenceSprite(x, y) {
  const f = (dx, dy) => { const c = combAt(x + dx, y + dy); return c === "#" || c === "+" || (c === "g" && !dy && !gateSide(x + dx, y)); };
  const n = f(0, -1), s = f(0, 1), e = f(1, 0), w = f(-1, 0);
  const col = e && w ? 2 : e ? 1 : w ? 3 : 0, row = n && s ? 1 : s ? 0 : n ? 2 : 3;
  return [IMG.fences, col * 16, row * 16, 16, 16, 0, -4];
}
