// The world's vocabulary: tile chars, what is solid, what an item in hand becomes, multi-tile footprints.
// None of it is typed here: every table is filled from the server's own (rules.py rules_table), which the page has
// from its first frame (rules.js, written from it) and which the server says again when it greets (state.js: hello).

"use strict";
const CH = {}, CHAR = {}, DEPTH_OF = {}, FOOT = {}, TOOL_FOR = {}, FILLS = {}, PLACEABLE_BLOCK = {}, recipes = {};
const GROUND = new Set(), SOLID = new Set(), WALKABLE_GROUND = new Set(), LAND_BLOCKS = new Set(), FOODS = [], FEEDS = [];
function refill(to, from) {               // the same table, with what the server says now
  if (to instanceof Set) { to.clear(); for (const v of from) to.add(v); }
  else if (Array.isArray(to)) to.splice(0, to.length, ...from);
  else { for (const k in to) delete to[k]; Object.assign(to, from); }
}
function setRules(r) {
  if (r !== RULES) refill(RULES, r);
  const T = r.tiles, of = (k) => Object.fromEntries(Object.keys(T).filter((c) => T[c][k]).map((c) => [c, T[c][k]]));
  for (const [to, from] of [[CH, of("name")], [DEPTH_OF, of("depth")], [FOOT, of("foot")], [TOOL_FOR, of("tool")], [FILLS, r.fills], [PLACEABLE_BLOCK, r.place], [recipes, r.recipes],
    [GROUND, Object.keys(of("ground"))], [SOLID, Object.keys(of("solid"))], [WALKABLE_GROUND, Object.keys(of("walk"))], [LAND_BLOCKS, r.land_blocks],
    [FOODS, Object.keys(r.food)], [FEEDS, Object.keys(r.feed)], [CHAR, Object.fromEntries(Object.entries(of("name")).map(([c, n]) => [n, c]))]]) refill(to, from);
}
setRules(RULES);
const tileOf = (c) => RULES.tiles[c] || {};                 // what the world says of a tile's char: solid, burns, tool, needs, quick, upstairs, holds
// A tool's kind and tier (ores.py TOOLS: a wood, a stone, an iron, a titanium axe or pickaxe): what the world asks of
// a tool is its kind, any tier; a dig is done with the best of a kind in your pack
const toolKind = (item) => (item && RULES.tools[item] ? RULES.tools[item][0] : item);
const toolArt = (item) => item && item.replace(/^(?:wood|iron|titanium)_(?=(?:axe|pickaxe|sword)$)/, "");   // (the picture it is held and swung as: its kind's, any tier: hold_art.js)
const bestTool = (kind) => { const inv = meObs ? meObs.self.inventory : {}; let best = null;
  for (const [t, [k, i]] of Object.entries(RULES.tools)) if (k === kind && inv[t] > 0 && (!best || i > RULES.tools[best][1])) best = t;
  return best; };
const placeable = (item) => !!(PLACEABLE_BLOCK[item] || FILLS[item] || RULES.sown[item]);     // in hand, it goes on the ground
// structures bigger than a tile (tiles.py FOOTPRINT): stored on the bottom-left tile, the rest is Z/z
function footprint(c, x, y, px, py) {     // placing at (x, y) from (px, py): the anchor and every covered tile
  const [w, h] = FOOT[c];                 // same rule as tiles.py footprint: extend away from the placer
  let x0 = x - ((w - 1) >> 1);
  if (px === x - 1 && py === y) x0 = x; else if (px === x + 1 && py === y) x0 = x - w + 1;
  const ay = px === x && py === y - 1 ? y + h - 1 : y;
  return {ax: x0, ay, tiles: footOf(c, x0, ay)};
}
function footOf(c, ax, ay) { const [w, h] = FOOT[c], tiles = []; for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) tiles.push({x: ax + i, y: ay - j}); return tiles; }
function structAt(x, y) {                 // the anchor of the structure a Z/z tile belongs to
  for (const [c, [w, h]] of Object.entries(FOOT)) for (let i = 0; i < w; i++) for (let j = 0; j < h; j++)
    if (combAt(x - i, y + j) === c) return {x: x - i, y: y + j, c};
  return null;
}
const wet = (g) => g in DEPTH_OF;                          // water: DEPTH_OF, how many layers down its bottom lies
const LABEL = {name_tag: "name tag", wood_wall: "wooden wall", wet_tilled: "watered soil", watering_can: "watering can", fruit_tree: "fruit tree", berry_bush: "berry bush", stone_wall: "stone wall", ripe_crop: "ripe wheat", crop: "young wheat",
  cooked_meat: "cooked meat", deep_water: "deep water", mid_water: "deeper water", abyss: "the deep", picnic_blanket: "picnic blanket", hay_bale: "hay bale", eclipse_core: "Eclipse Core"};
LABEL.stone_block = "stone block";
const label = (n) => LABEL[n] || String(n).replace("_", " ");
