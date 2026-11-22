// Object and character sprites (per-tile chars to sprite rects).

// =====================================================================================
//  Sprites drawn every frame (y-sorted with characters)
// =====================================================================================
const AGENT_TINTS = ["#f4b6b6", "#a9cdf2", "#b8e0a0", "#f2d58f", "#d3b6ef", "#9fdcd0", "#f3b7d6", "#e8c9a4", "#c9d0f5", "#f6c79a"];
const agentTint = (name) => AGENT_TINTS[[...name].reduce((h, c) => h * 31 + c.charCodeAt(0) >>> 0, 7) % AGENT_TINTS.length];
const tinted = new Map();
function characterSheet(tint, src = IMG.character) {   // recolour the cream body to a per-person colour
  const key = tint + (src === IMG.character ? "" : ":" + src.src);
  if (tinted.has(key)) return tinted.get(key);
  const c = document.createElement("canvas"); c.width = src.width; c.height = src.height;
  const g = c.getContext("2d", {willReadFrequently: true}); g.drawImage(src, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height), px = d.data;
  const tr = parseInt(tint.slice(1, 3), 16), tg = parseInt(tint.slice(3, 5), 16), tb = parseInt(tint.slice(5, 7), 16);
  for (let i = 0; i < px.length; i += 4) {
    const r = px[i], gg = px[i + 1], bb = px[i + 2];
    if (px[i + 3] && r > 200 && gg > 190 && bb > 150 && r - bb < 90) {   // cream / white body pixels
      const k = (r + gg + bb) / (243 + 242 + 192);   // 1.0 for the main body colour, keeps shading
      px[i] = Math.min(255, tr * k); px[i + 1] = Math.min(255, tg * k); px[i + 2] = Math.min(255, tb * k);
    }
  }
  g.putImageData(d, 0, 0); tinted.set(key, c); return c;
}
// premium character sheet: 8-frame rows, 4 directions each: down, up, right, left
// (checked from the eye and collar-bell position; the pink spot is the inner ear, at the back)
const ANIM = {idle: 0, walk: 4, run: 8, hoe: 12, axe: 16, water: 20, pickaxe: 24, sword: 28, spear: 32, jump: 36};   // water = watering can; pickaxe, sword, spear are drawn by tool_art.js, the jump's poses by jump_art.js
const DIR_ROW = (p) => (p.fy < 0 ? 1 : p.fx > 0 ? 2 : p.fx < 0 ? 3 : 0);
let troughFullC = null;
function troughFull() {                     // the feeding box with hay heaped in it (18 px tall: hay pokes out)
  if (troughFullC) return troughFullC;
  const c = troughFullC = document.createElement("canvas"); c.width = 16; c.height = 18; const g = c.getContext("2d");
  g.drawImage(IMG.barn, 0, 0, 16, 16, 0, 2, 16, 16); g.drawImage(IMG.barn, 2, 51, 11, 10, 2, 1, 11, 10);
  return c;
}
function genCell(name) { return [GEN[name] * 16, 0]; }
// What stands at the brink of raised ground, or of the water, is drawn back from it. An edge tile is not flat all
// over: a hill's south edge is the cliff's face from the 8th px down, a ledge 7 px wide its west and east edges;
// a shore's is cut the same (the bank, the foam, the water); and a thing's foot is at the bottom of its tile, in
// the middle. A tree on such a tile stood on the face of the cliff, or in the water. So what grows or lies there
// (trees, stumps, bushes, rocks, mushrooms, flowers) is drawn 8 px back from a drop to the south, 4 from one to a
// side, less from one only at a corner. Its tile, and what it stops, are what they were.
const BRINK = new Set("TFUtbvM*Qf");
const BK = [0, 0], lowBy = (x, y, l, dx, dy) => !!blockOf(x + dx, y + dy) && (standAt(x + dx, y + dy) < l || !(isLand(gndAt(x + dx, y + dy)) || Bridge.rests(x, y, x + dx, y + dy)));   // (lower ground beside it, its ground read as it is: no pair made)
function brinkAt(x, y) {                             // -> BK: [dx, dy], art px (kept: no pair made)
  // (a drop: lower ground; or what the land is painted as a shore towards, tiles.js: water, a bridge's side)
  const l = standAt(x, y), s = lowBy(x, y, l, 0, 1), w = lowBy(x, y, l, -1, 0), e = lowBy(x, y, l, 1, 0), sw = !s && !w && lowBy(x, y, l, -1, 1), se = !s && !e && lowBy(x, y, l, 1, 1);
  BK[0] = (w ? 4 : sw ? 3 : 0) - (e ? 4 : se ? 3 : 0); BK[1] = s ? -8 : sw || se ? -4 : 0; return BK;
}
function brink(x, y) { brinkAt(x, y); return [BK[0], BK[1]]; }
// object sprite for a tile char: [img, sx, sy, sw, sh, dx (from tile left), dy (from tile top)]
// out: an array of the caller's to write it into (the HD look's things, each frame: hd.js stood), returned; it was seven numbers made a thing a frame
let spOut = null;
const S7 = (a, b, c, d, e, f, g) => { const o = spOut; spOut = null; if (!o) return [a, b, c, d, e, f, g]; o[0] = a; o[1] = b; o[2] = c; o[3] = d; o[4] = e; o[5] = f; o[6] = g; return o; };
function objectSprite(c, x, y, t, out) {
  spOut = out || null; const s = spriteOf(c, x, y, t); spOut = null;
  if (!s || !BRINK.has(c)) return s;
  brinkAt(x, y); const dx = BK[0], dy = BK[1]; if (!(dx || dy)) return s;
  const s5 = s[5] + dx, s6 = s[6] + dy; if (!out) return [s[0], s[1], s[2], s[3], s[4], s5, s6];
  if (s !== out) for (let i = 0; i < 5; i++) out[i] = s[i]; out[5] = s5; out[6] = s6; return out;
}
function spriteOf(c, x, y, t) {
  const h = hash(x, y, 21);
  switch (c) {
    case "T": {
      if (h < .7) {                                                                       // animated round tree
        const hit = shakes.size ? shakes.get(x + "," + y) : undefined, k = hit ? (performance.now() - hit) / 1000 : 9;
        if (k < .32) return S7(IMG.tree_anim, 48 * Math.min(3, Math.floor(k * 12.5)), 48, 48, 48, -16, -28);
        const f = Math.floor(t * 6 + h * 60) % 12;
        return S7(IMG.tree_anim, 48 * f, 144, 48, 48, -16, -28);
      }
      return S7(IMG.trees, 0, 0, 16, 32, 0, -13);                                         // young tree (base at y 28)
    }
    case "F": {                                                                           // fruit tree, 4 species
      const img = fruitSheet(x, y), hit = shakes.size ? shakes.get(x + "," + y) : undefined, k = hit ? (performance.now() - hit) / 1000 : 9;
      if (k < .32) return S7(img, 48 * Math.min(3, Math.floor(k * 12.5)), 48, 48, 48, -16, -28);
      return S7(img, 48 * (Math.floor(t * 5 + h * 30) % 6), 96, 48, 48, -16, -28);
    }
    case "b": return S7(IMG.trees, BERRY_BUSH[Math.floor(h * 3)], 48, 16, 16, 0, -3);
    case "v": return S7(IMG.trees, 16, 48, 16, 16, 0, -3);                                 // picked bush: leaves only
    case "U": {                                                                           // picked fruit tree: the same tree, bare
      return S7(IMG.fruit_bare, fruitKind(x, y) * 48, 0, 48, 48, -16, -28);
    }
    case "*": return S7(IMG.gen, GEN["ore"] * 16, 0, 16, 16, 0, -3);
    case "M": return S7(IMG.gen, GEN["boulder"] * 16, 0, 16, 16, 0, -3);
    case "%": return S7(IMG.gen, GEN["stone_wall"] * 16, 0, 16, 16, 0, -4);
    case "Q": return S7(IMG.nature, [0, 16, 48][Math.floor(h * 3)], 0, 16, 16, 0, 0);
    case "#": return fenceSprite(x, y);
    case "X": return mailAt.has(x + "," + y)                                            // a letter pops up when mail waits
      ? S7(IMG.mailbox, 64, 60 + (Math.floor(t * 2) % 2 ? 0 : -1), 16, 36, 0, -20) : S7(IMG.mailbox, 0, 16, 16, 32, 0, -16);      // (from the sheet's row 60: the letter's bubble begins at 62, and its top was cut off)
    case "V": return S7(IMG.boats, (Math.floor(t * 1.5 + h * 9) % 2) * 48, 32, 48, 32, -16, -10);   // moored, rocking
    case "W": return S7(IMG.house_walls, 48, 16, 16, 16, 0, 0);                         // (a wall as a thing: a small plank block; standing, structures.js draws it)
    case "l": return S7(IMG.gen, GEN["ladder"] * 16, 0, 16, 16, 0, -2);                    // (as a thing in hand; standing, climbing.js draws it up to its top)
    case "+": return S7(IMG.door, 80, 0, 16, 16, 0, 0);                                 // a door, shut (it was a wall with a small hole in it: a window, to look at)
    case "^": return S7(IMG.gen, GEN[Math.floor(t * 6 + x) % 2 ? "campfire1" : "campfire0"] * 16, 0, 16, 16, 0, -2);
    case "x": return S7(IMG.gen, GEN[Math.floor(t * 8 + x + y) % 2 ? "fire1" : "fire0"] * 16, 0, 16, 16, 0, -3);
    case "&": return S7(IMG.gen, GEN["workbench"] * 16, 0, 16, 16, 0, -3);
    case "?": return S7(IMG.signs, 0, 0, 16, 16, 0, -2);
    case "!": return S7(IMG.gen, GEN["flag"] * 16, 0, 16, 16, 0, -6);
    case ";": return S7(IMG.crops, 0, CROP_ROW[cropSpecies(x, y)] * 16, 16, 16, 0, -2);
    case "\"": return S7(IMG.crops, 32, CROP_ROW[cropSpecies(x, y)] * 16, 16, 16, 0, -3);
    case "w": return S7(IMG.crops, 48, CROP_ROW[cropSpecies(x, y)] * 16, 16, 16, 0, -4);
    case "f": {
      if (h < .06) return S7(IMG.nature, 48, 48, 16, 32, 0, -16);                         // tall sunflower (both halves)
      const [fx, fy] = FLOWERS[Math.floor(hash(x, y, 44) * FLOWERS.length)];
      return S7(IMG.nature, fx * 16, fy * 16, 16, 16, 0, -1);
    }
    case "B": return S7(IMG.furniture, Math.floor(h * 3) * 16, 16, 16, 32, 0, -16);         // bed: foot on this tile
    case "h": return S7(IMG.furniture, CHAIR[chairFaces(x, y)], 32, 16, 16, 0, -3);       // (turned to what it is set at: world_decor.js)
    case "L": return S7(IMG.furniture, 48, 48, 16, 16, 0, -3);
    case "p": return S7(IMG.furniture, 48 + Math.floor(h * 3) * 16, 0, 16, 32, 0, -16);
    case "K": return S7(IMG.furniture, 96, 48, 16, 16, 0, -3);
    case "r": return S7(IMG.furniture, Math.floor(h * 3) * 16, 80, 16, 16, 0, 0);
    case "g": {                                                                           // opens next to people
      const key = x + "," + y, near = [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => occupied.has((x + dx) + "," + (y + dy)));
      const was = doors.get(key) || 0, o = Math.max(0, Math.min(1, was + (near ? .12 : -.08)));
      if (!was && o) sfx("gate", x, y);                                                     // it starts to swing open
      if (was >= 1 && o < 1) sfx("door_close", x, y);                                       // ...and to swing shut
      doors.set(key, o);
      // (five frames a way: seen from the front, every other cell of the sheet's first row, the ones hinged on the
      // left; in a fence that runs north and south, the sheet's side-on gate, two leaves between the posts over
      // and under it. It showed the first four cells one after the other: its hinge changed sides as it opened.)
      const f = Math.round(o * 4) * 32;
      return gateSide(x, y) ? S7(IMG.gates, f, 16, 32, 32, 0, -13) : S7(IMG.gates, f, 0, 16, 16, 0, -3);
    }
    case "t": {                                       // a stump, cut flat: the felling sheet's own, or the thin tree's
      // hidden while the fall animation still draws the tree there: the round sheet draws its stump until its fade
      // (frame 9); the thin one stands whole for frames 0-2, then it is cut and the stump tile shows
      const now = performance.now();
      if (falls.some((f) => f.x === x && f.y === y && now - f.t0 < (f.thin ? 3 : 9) / 14 * 1000)) return null;
      return h < .7 ? S7(IMG.tree_fall, 12 * 64 + 32, 28, 16, 16, 0, 0) : S7(IMG.stump_thin, 0, 0, 16, 16, 0, 0);
    }
    case "Y": return S7(IMG.well, 0, 0, 32, 32, 0, -16);                                   // 2x2, drawn from the bottom-left tile
    case "J": { const k = Math.floor(h * 6); return S7(IMG.coop, 160 + (k % 3) * 32, 80 + Math.floor(k / 3) * 48, 32, 44, 0, -28); }
    case "m": return S7(IMG.blanket, 0, 8, 48, 32, 0, -16);
    case "q": return S7(IMG.basket, 0, 0, 16, 16, 0, -3);
    case "e": return troughAt.has(x + "," + y) ? S7(troughFull(), 0, 0, 16, 18, 0, -5) : S7(IMG.barn, 0, 0, 16, 16, 0, -3);
    case "y": return S7(IMG.barn, 0, 16, 16, 16, 0, -2);
    case "Z": case "z": return null;                                                       // drawn by the structure itself
    case "C": {                                                                           // lid opens when used
      const o = chestOpen.get(x + "," + y), k = o ? (performance.now() - o) / 1000 : 9;
      const f = k < .2 ? Math.floor(k / .2 * 4) : k < 1.2 ? 4 : k < 1.4 ? 4 - Math.floor((k - 1.2) / .2 * 4) : 0;
      return S7(IMG.chest, f * 48 + 16, 16, 16, 16, 0, -2);
    }
  }
  return null;
}
// ---- sound: short procedural effects through WebAudio; M mutes ---------------------------
// The opaque part of a sprite frame (in its own pixels): the white aiming box hugs the thing, not its tile.
let boundsIds = 0;
const boundsCache = new Map(), boundsCv = document.createElement("canvas");
function spriteBounds(img, a, b, w, h) {
  if (!img.bid) img.bid = ++boundsIds;          // canvases have no src: give every image its own id
  const key = `${img.bid}|${a},${b},${w},${h}`;
  if (boundsCache.has(key)) return boundsCache.get(key);
  boundsCv.width = w; boundsCv.height = h;
  const g = boundsCv.getContext("2d", {willReadFrequently: true});
  g.clearRect(0, 0, w, h); g.drawImage(img, a, b, w, h, 0, 0, w, h);
  const d = g.getImageData(0, 0, w, h).data;
  // count solid pixels per row and column, then trim edges with fewer than 2: stray specks (a leaf, a chip) don't count
  const cols = new Array(w).fill(0), rows = new Array(h).fill(0);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (d[(y * w + x) * 4 + 3] >= 120) { cols[x]++; rows[y]++; }
  let x0 = 0, y0 = 0, x1 = w - 1, y1 = h - 1;
  while (x0 <= x1 && cols[x0] < 2) x0++;
  while (x1 >= x0 && cols[x1] < 2) x1--;
  while (y0 <= y1 && rows[y0] < 2) y0++;
  while (y1 >= y0 && rows[y1] < 2) y1--;
  const r = x1 < x0 || y1 < y0 ? null : [x0, y0, x1 + 1, y1 + 1];
  if (!(img instanceof HTMLImageElement) || (img.complete && img.naturalWidth)) boundsCache.set(key, r);
  return r;
}
