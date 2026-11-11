// Crops, animals, fruit trees, fire and fences.

const CROPS = ["wheat", "pumpkin", "cauliflower", "lettuce", "eggplant", "carrot"];
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
const WILD = {
  tusker: {cw: 32, ch: 32, idle: [0, 8, 260], walk: [8, 8, 90], warn: [16, 4, 170], run: [20, 8, 55]},
  pincer: {cw: 24, ch: 16, idle: [0, 8, [800, 300, 300, 600, 140, 500, 140, 600]], walk: [8, 8, 80], act: [16, 5, [140, 420, 80, 220, 220]]},
  strawman: {cw: 32, ch: 32, idle: [0, 4, [900, 900, 500, 180]], walk: [4, 8, 110], act: [12, 4, [520, 90, 260, 300]]},
  wisp: {cw: 32, ch: 32, idle: [0, 8, 140], walk: [8, 8, 90], act: [16, 6, [220, 300, 90, 160, 160, 160]]},
  wyrm: {cw: 48, ch: 32, idle: [0, 8, 150], walk: [8, 8, 95], act: [16, 4, [480, 90, 240, 280]]},
};
function wildFrame([col, n, ms], t, loop) {
  if (!Array.isArray(ms)) return col + (loop ? Math.floor(t / ms) % n : Math.min(n - 1, Math.floor(t / ms)));
  const all = ms.reduce((a, b) => a + b, 0);
  t = loop ? t % all : Math.min(t, all - 1);
  let i = 0;
  while (t >= ms[i]) t -= ms[i++];
  return col + i;
}
function drawWild(p, x, y, now) {
  const e = p.e, A = WILD[e.kind], z = zoom;
  const moving = now - p.moved < 350 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
  if (e.act === "windup" && p.act !== "windup") p.windAt = now;      // the warning starts: play it from its first frame
  p.act = e.act;
  const [fx, fy] = e.act && e.dir ? e.dir : [p.fx, p.fy], row = fy > 0 ? 0 : fy < 0 ? 1 : fx < 0 ? 2 : 3;
  const since = now - (p.windAt || -1e9), calm = () => wildFrame(moving ? A.walk : A.idle, now + e.id * 137, true);
  let col, shake = 0;
  if (A.warn) {
    col = e.act === "windup" ? wildFrame(A.warn, since, true) : e.act === "charge" ? wildFrame(A.run, now, true) : calm();
    if (e.act === "stun") shake = Math.round(Math.sin(now / 45)) * z;       // dazed: it rammed something
  } else col = since < A.act[2].reduce((a, b) => a + b, 0) ? wildFrame(A.act, since, false) : calm();
  const blit = () => ctx.drawImage(IMG[e.kind], col * A.cw, row * A.ch, A.cw, A.ch, x - (A.cw - 16) / 2 * z + shake, y - (A.ch - 16) * z, A.cw * z, A.ch * z);
  blit();
  const fl = flashes.get(e.kind + e.id);
  if (fl && now - fl < 120) { ctx.globalCompositeOperation = "lighter"; blit(); ctx.globalCompositeOperation = "source-over"; }
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
const chestOpen = new Map(), doors = new Map();
let occupied = new Set();

function drawFire(px, py, S, t, x, y) {            // the generated two-frame flame sprite, flickering per tile
  const f = Math.floor(t * 8 + x * 3 + y) % 2 ? "fire1" : "fire0";
  ctx.drawImage(IMG.gen, GEN[f] * 16, 0, 16, 16, Math.round(px), Math.round(py - 3 * zoom), S, S);
}

function fenceSprite(x, y) {
  const f = (dx, dy) => { const c = combAt(x + dx, y + dy); return c === "#" || c === "+"; };
  const n = f(0, -1), s = f(0, 1), e = f(1, 0), w = f(-1, 0);
  const col = e && w ? 2 : e ? 1 : w ? 3 : 0, row = n && s ? 1 : s ? 0 : n ? 2 : 3;
  return [IMG.fences, col * 16, row * 16, 16, 16, 0, -4];
}
