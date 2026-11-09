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
