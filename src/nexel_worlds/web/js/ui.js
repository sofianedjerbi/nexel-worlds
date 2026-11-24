// HUD: item icons, hotbar, bag, mail, toasts. (Crafting: craft.js)

const fulls = new Map();                         // an item's icon, kept (what lies on the ground is a smaller one: ghostIcon, loot.js)
const fullIcon = (n) => fulls.get(n) || (fulls.set(n, iconCanvas(n)), fulls.get(n));
const slotIcon = (n) => smallCanvas(n);          // what a slot shows: the small picture, as on the ground, at the land's pixel (--i)
function openCraft() { $("craft").style.display = "block"; craftOpened(); }
// item icons from the sheets: [image name, sx, sy]
const ICONS = {   // [sheet, x, y, w, h]: the items sheet has seed packets in column 0, produce in column 1, materials in 2-3
  wood: ["items", 32, 48], plank: ["items", 32, 64], stone: ["items", 32, 80], ingot: ["items", 48, 64], fiber: ["gen", "fiber"],
  ore: ["gen", "ore"], path: ["cobble", 16, 16], dirt: ["hill1", 16, 32, 14, 14], stone_block: ["hill3", 16, 32, 14, 14], seed: ["items", 0, 128],
  axe: ["items", 32, 0], pickaxe: ["gen", "pickaxe"], hoe: ["items", 48, 0], watering_can: ["items", 32, 16], spear: ["gen", "spear"], sword: ["gen", "sword"],
  torch: ["gen", "torch"], rope: ["gen", "rope"], name_tag: ["gen", "name_tag"], ladder: ["gen", "ladder"], stairs: ["gen", "stairs"],
  berries: ["items", 32, 160], fruit: ["items", 32, 96], mushroom: ["nature", 16, 0], egg: ["items", 48, 176], milk: ["items", 64, 0],
  meat: ["gen", "meat"], cooked_meat: ["gen", "cooked_meat"], bread: ["gen", "bread"],
  wheat: ["items", 16, 128], pumpkin: ["items", 16, 144], cauliflower: ["items", 16, 48], lettuce: ["items", 16, 112],
  eggplant: ["items", 16, 80], carrot: ["items", 16, 32],
  flower: ["nature", 16, 48], workbench: ["gen", "workbench"], campfire: ["gen", "campfire0"], chest: ["chest", 16, 16],
  boat: ["boats", 8, 36, 32, 24], mailbox: ["mailbox", 0, 16, 16, 32], fence: ["fences", 0, 48], gate: ["gates", 0, 0], wood_wall: ["house_walls", 16, 32], roof: ["house_roof", 16, 16], stone_wall: ["gen", "stone_wall"], door: ["door", 80, 0],
  sign: ["signs", 0, 0], flag: ["gen", "flag"], bed: ["furniture", 0, 16, 16, 32], chair: ["furniture", 64, 32],
  table: ["furniture", 48, 48], plant: ["furniture", 48, 0, 16, 32], clock: ["furniture", 96, 48], rug: ["furniture", 0, 80], well: ["well", 0, 0, 32, 32], coop: ["coop", 160, 80, 32, 44], picnic_blanket: ["blanket", 2, 8, 44, 32], basket: ["basket", 0, 0], trough: ["barn", 0, 0], hay: ["barn", 0, 16],
};
// A block of the land in your pack is drawn as a block, as the game shows one: 14 x 14 px cut from its sheet's own
// plateau where its south edge runs straight: the top, its lip, the wall under it. No px changed. (A pebble and a
// speck of soil are materials' pictures: "breaked blocks should stay blocks in inventory: not items".)
// An item's picture is 16 x 16 art pixels, and wherever it shows, an art pixel is a whole number of screen pixels:
// the land's own on the ground (zoom; loot.js), the frames' own in the HUD (--u: hudFit below). A thing bigger than a tile (a
// boat, a bed, a well) is made smaller by whole pixels, never squeezed: each n x n block becomes one pixel, of the
// colour most of it has (the darker of two as many: an outline holds). The px are worked out here and put once.
const smalls = new Map();
function smallArt(img, x, y, w, h, size = 16) {     // (size: how many px it may be across; 11 on the ground, loot.js)
  const src = document.createElement("canvas"); src.width = w; src.height = h;
  const sg = src.getContext("2d", {willReadFrequently: true}); sg.drawImage(img, x, y, w, h, 0, 0, w, h);
  const d = sg.getImageData(0, 0, w, h).data, at = (i, j) => (j * w + i) * 4;
  let x0 = w, y0 = h, x1 = -1, y1 = -1;                    // what is drawn of it (a mailbox is 8 px of its cell: as it is)
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (d[at(i, j) + 3] >= 128) { x0 = Math.min(x0, i); x1 = Math.max(x1, i); y0 = Math.min(y0, j); y1 = Math.max(y1, j); }
  const bw = x1 - x0 + 1, bh = y1 - y0 + 1, n = Math.ceil(Math.max(bw, bh) / size), ow = Math.ceil(bw / n), oh = Math.ceil(bh / n), out = new ImageData(ow, oh);
  const dark = (c) => (c >> 16) * 3 + (c >> 8 & 255) * 6 + (c & 255);
  for (let j = 0; j < oh; j++) for (let i = 0; i < ow; i++) {
    const seen = new Map(); let solid = 0, cells = 0;
    for (let b = 0; b < n && j * n + b < bh; b++) for (let a = 0; a < n && i * n + a < bw; a++) {
      const o = at(x0 + i * n + a, y0 + j * n + b); cells++;
      if (d[o + 3] < 128) continue;
      const c = d[o] << 16 | d[o + 1] << 8 | d[o + 2]; solid++; seen.set(c, (seen.get(c) || 0) + 1);
    }
    if (solid * 2 < cells) continue;
    let best = 0, votes = 0;
    for (const [c, v] of seen) if (v > votes || (v === votes && dark(c) < dark(best))) { best = c; votes = v; }
    out.data.set([best >> 16, best >> 8 & 255, best & 255, 255], (j * ow + i) * 4);
  }
  return out;
}
// The tools without the white edge the pack's icons have round them (a sticker's: a ring of white px, and the hole in
// the can's handle filled with it). A tool has no white of its own, so every near white px of it goes. In the bar,
// the book, the inventory and the hand they are then as the sword and the spear always were: no ring.
const BARE = new Set(["axe", "pickaxe", "hoe", "watering_can"]);
function bare(c) {
  const g = c.getContext("2d"), im = g.getImageData(0, 0, 16, 16), d = im.data;
  for (let o = 0; o < d.length; o += 4) if (Math.min(d[o], d[o + 1], d[o + 2]) > 225) d[o + 3] = 0;
  g.putImageData(im, 0, 0);
  return c;
}
function iconCanvas(name) {
  const c = document.createElement("canvas"); c.width = 16; c.height = 16; const g = c.getContext("2d", {willReadFrequently: BARE.has(name)});
  const ic = ICONS[name];
  if (CubeIcon.is(name)) { const im = CubeIcon.px(name, CubeIcon.CELL); if (im) { const [x, y] = CubeIcon.mid(im, 16); g.putImageData(im, x, y); return c; } }      // a block: a cube made at the size the other things sit at in a cell, in its middle (cube_icons.js)
  if (!ic && RULES.wear[name]) return wearIcon(name);          // clothes and armor draw their own (wear_items.js)
  if (!ic) { g.fillStyle = "#8a6a55"; g.fillRect(4, 4, 8, 8); return c; }
  if (ic[0] === "gen") { g.drawImage(IMG.gen, GEN[ic[1]] * 16, 0, 16, 16, 0, 0, 16, 16); return BARE.has(name) ? bare(c) : c; }
  const [img, x, y, w = 16, h = 16] = ic;
  if (w <= 16 && h <= 16) { g.drawImage(IMG[img], x, y, w, h, (16 - w) >> 1, (16 - h) >> 1, w, h); return BARE.has(name) ? bare(c) : c; }
  if (!smalls.has(name)) smalls.set(name, smallArt(IMG[img], x, y, w, h));
  const small = smalls.get(name);
  g.putImageData(small, (16 - small.width) >> 1, (16 - small.height) >> 1);
  return c;
}
// The bar at the bottom is what you carry: ten slots, keys 1 to 9 and 0. (No button on it: I opens the inventory,
// C the crafting.) What is beyond ten kinds of thing is in the inventory.
const BAR = 10;
// The HUD's art pixels, each a whole number of screen pixels, so that all is cut on the screen's own grid: --u for
// a slot's frame (about 2 CSS px), --i for the item in it (the land's own pixel at the zoom the game starts with: 3,
// or 2 on a small phone, so an item looks in the bar as it does on the ground), --u3 for the crafting's big picture.
// The bar's (--u) is a screen pixel less, and again, while its ten slots would not fit across, or the HUD would take
// more than hudTall of the height (a phone: touch.js); the item's is no more than fits the frame. Nothing is scaled.
// --q is the recipe book's own (craft.js): everything in it is a number of them.
let hudU = 2, hudTall = 1, hudK = 2.5, hudSig = "", hudSide = false, hudEdge = null;   // (hudK: CSS px an art pixel of the hearts and the food: 2.5, less where the two rows would not fit across)
// A phone on its side: the hearts, the food and the experience stand at the bar's left, in its height (hudSide): one band,
// 14% of the height at most, a slot 40 CSS px at least. (Stacked over the bar they took a fifth of a screen 390 px high.) Where the
// screen is not wide enough for that beside the thumbs' buttons (and its notch: hudEdge measures the safe area), they stay over it.
function hudFit() {
  const d = window.devicePixelRatio || 1, st = document.documentElement.style, was = hudU, touch = document.body.classList.contains("touch");
  let n = Math.max(1, Math.round(2 * d));
  const low = touch && innerHeight < 520 && innerWidth > innerHeight, tall = low ? Math.min(hudTall, .2) : hudTall;   // (a phone on its side: a fifth of its height: the HUD took the bottom third of the land)
  let side = false;
  if (low) {
    if (!hudEdge) { hudEdge = document.createElement("div"); hudEdge.style.cssText = "position:fixed;visibility:hidden;pointer-events:none;left:0;top:0;width:calc(env(safe-area-inset-left) + env(safe-area-inset-right));height:env(safe-area-inset-bottom)"; document.body.appendChild(hudEdge); }
    const u3 = Math.max(1, Math.round(3 * d)) / d, room = innerWidth - hudEdge.offsetWidth - 56 * u3 - 12, vit = 99 * Math.max(1, Math.round(4 / 3 * d)) / d + 8;
    const fits = (m) => 30 * m / d + 4 <= innerHeight * .14 && vit + (BAR * 32 - 2) * m / d <= room;      // (its own height: the home bar's inset under it is not the HUD's)
    let m = n; while (m > 1 && !fits(m)) m--;
    if (30 * m / d >= 40 && fits(m)) { side = true; n = m; }
  }
  if (side !== hudSide) { hudSide = side; document.body.classList.toggle("hudside", side); }
  const h = $("hud").offsetHeight;
  while (!side && n > 1 && ((BAR * 32 - 2) * n / d > innerWidth - 16 || (h && h + 30 * (n / d - was) > innerHeight * tall))) n--;
  hudU = n / d; hudK = side ? Math.max(1, Math.round(4 / 3 * d)) / d : Math.min(low ? 5 / 3 : 2.5, Math.max(1, Math.floor((innerWidth - 34) * d / 198)) / d);   // (two rows of ten icons: 99 art px each)
  const small = document.body.classList.contains("touch") && Math.min(innerWidth, innerHeight) < 520, land = small ? 2 : 3;
  const item = Math.max(1, Math.min(Math.round(land * d), Math.floor(1.6 * n)));    // (11 px of it in a hole of 16: its edge px are empty)
  const book = bookPx();   // the recipe book's pixel (--q): the land's (a screen pixel more under a thumb), less while its 272 x 160 would not fit (index.html: worked out there first, before the first picture)
  const up = small && innerHeight > innerWidth, [bw, bh] = up ? [116, 299] : small ? [270, 150] : [224, 162];   // (--b: the inventory's, bag.js. A phone held upright: five cells across, a finger each; on its side its buttons beside it: phone.css)
  let bag = up ? Math.round(3.4 * d) : book; while (bag > 1 && (bw * bag / d > innerWidth - 12 || bh * bag / d > innerHeight - 12)) bag--;
  if (hudSig === (hudSig = [n, d, item, book, bag, up, side].join())) return false;
  let cq = Math.round(2.4 * d); while (cq > 1 && (162 * cq / d > innerWidth - 12 || 326 * cq / d > innerHeight - 12)) cq--;      // (--cq: the recipe book's, upright: the list over the page)
  st.setProperty("--cq", cq / d + "px"); document.body.classList.toggle("upright", up); st.setProperty("--p2", Math.max(1, Math.round(2 * d)) / d + "px");
  st.setProperty("--u", hudU + "px"); st.setProperty("--i", item / d + "px"); st.setProperty("--i2", (11 * (item + 1) <= 24 * n ? item + 1 : item) / d + "px"); st.setProperty("--u3", Math.max(1, Math.round(3 * d)) / d + "px"); st.setProperty("--q", book / d + "px"); st.setProperty("--w", Math.max(1, Math.round(book * .7)) / d + "px");
  st.setProperty("--b", bag / d + "px");   // (--w: what Tab shows, who.js: a size under the book's)
  return hudU !== was;
}
hudFit(); addEventListener("resize", hudFit);
new ResizeObserver(() => document.documentElement.style.setProperty("--hudh", $("hud").offsetHeight + "px")).observe($("hud"));   // (the bag sits on it)
// The corner's keys (keyboard.js updateActions) stand over the bar where it leaves them no room beside it: in a window 800
// px wide "Dig down Q" was under its last slots. (Across, the corner and the bar are where they are whatever its height.)
{ const clear = () => { const a = $("actions"), r = a.getBoundingClientRect(), b = $("hud").getBoundingClientRect(); a.classList.toggle("lift", r.width > 0 && b.width > 0 && r.left < b.right + 8 && r.right > b.left); };
  const ro = new ResizeObserver(clear); ro.observe($("actions")); ro.observe($("hud")); addEventListener("resize", clear); }
let slots = JSON.parse(localStorage.getItem("nexel-slots") || "[]");
function slotOrder(inv) {               // items keep their slot; new items take the first free one, the empty hand's last
  slots = slots.map((n) => (n && inv[n] ? n : null));         // (a flower picked with empty hands stays out of them: E picks the next one, not plants it)
  while (slots.length < BAR) slots.push(null);
  const free = () => { const i = slots.findIndex((n, j) => !n && j !== handSlot); return i >= 0 ? i : slots.indexOf(null); };
  for (const n of Object.keys(inv)) if (!slots.includes(n)) { const i = free(); if (i >= 0) slots[i] = n; else slots.push(n); }
  localStorage.setItem("nexel-slots", JSON.stringify(slots));
  return slots;
}
// The hand is a slot of the bar, like Minecraft ("always keep an item selected in the inventory, even empty hands"): what
// is in it is in your paw; it runs out, the slot stays and the hands are empty; a new thing landing in it is held.
let handWant = null;                    // a name asked for before it is in the bag (selectItem): taken in hand when it comes
function handSync(inv = meObs ? meObs.self.inventory : {}) {
  if (handWant && inv[handWant]) { slotOrder(inv); const i = slots.indexOf(handWant); handWant = null; handTo(i); }
  const n = slots[handSlot]; selected = n && inv[n] ? n : null; return selected;
}
function handTo(i) {                    // the slot holding a thing: in hand (from the pack: swapped into the slot in hand)
  if (i >= BAR) { [slots[i], slots[handSlot]] = [slots[handSlot], slots[i]]; localStorage.setItem("nexel-slots", JSON.stringify(slots)); }
  else if (i >= 0) handSlot = i;
  localStorage.setItem("nexel-hand", handSlot);
}
function drawHotbar(inv) {
  const el = $("hotbar");
  const order = slotOrder(inv).slice(0, BAR);
  handSync(inv);
  const extra = Object.keys(inv).filter((n) => !order.includes(n));
  const can = meObs ? meObs.self.can ?? RULES.can_size : RULES.can_size;
  if (meObs) Held.sync(meObs.self);                  // (in your paw for the others too: held.js)
  if (selected !== hotWas) { if (hotWas !== undefined && selected) heldName(selected); hotWas = selected; }
  const sig = JSON.stringify(inv) + order.join() + handSlot + can; if (el.dataset.sig === sig) return; el.dataset.sig = sig;
  el.innerHTML = "";
  order.forEach((name, i) => {
    const d = document.createElement("div"); d.className = "slot" + (i === handSlot ? " sel" : "");
    d.onclick = () => selectSlot(i);                 // (any slot, an empty one too; the one in hand again: it stays in hand)
    if (name) {
      d.appendChild(slotIcon(name));
      const how = RULES.wear[name] ? ` · ${capOf("use")} to wear` : FOODS.includes(name) ? ` · ${capOf("use")} to eat, or feed animals` : name === "watering_can" ? ` · ${can}/${RULES.can_size} water · click a crop; refill at a well or water`
        : placeable(name) ? " · select, click the ground to place" : name === "name_tag" ? " · select, use it on an animal to name it" : "";
      d.insertAdjacentHTML("beforeend", `<span class="c">${inv[name]}</span><span class="tip">${esc(label(name) + how)}</span>`);
      if (name === "watering_can") d.insertAdjacentHTML("beforeend", `<span class="lvl"><i style="width:${Math.round(can / RULES.can_size * 100)}%"></i></span>`);
      d.ondblclick = () => useSelected(name);
    }
    d.insertAdjacentHTML("beforeend", `<span class="k">${(i + 1) % 10}</span>`);
    el.appendChild(d);
  });
  drawBag();                                         // (bag.js: the inventory, if it is open)
}
// The slot in hand: two art px bigger each side, lifted, its frame lit (the pack's frame with its middle drawn longer, its
// wood lighter: whole px, nothing scaled; --slotsel), its icon a screen px bigger an art px if that fits (--i2, hudFit).
// Its name shows over the bar a moment when it changes ("the selected item in inventory isn't clear").
// The game's short notes show in the same spot ("'you're full' messages etc they could show up above the chat beautifully
// like item"): one spot, one timer, the newest shown (a name, a note) replaces what was there and is never cut short by
// the older one's timer. A note stays longer than a name; a no is warm red (the buzz too, toast).
let hotWas, nameTimer;
const NAME_MS = 1400, BAR_NOTE_MS = 2500;
function overBar(html, cls, ms) {
  const e = $("heldname"); e.innerHTML = html; e.className = "on" + (cls ? " " + cls : ""); e.dataset.t = Date.now();
  clearTimeout(nameTimer); nameTimer = setTimeout(() => e.classList.remove("on"), ms);
}
function heldName(n) { overBar(esc(label(n)), "", NAME_MS); }
ready.then(() => { const im = IMG.slot; if (!im) return; (() => {   // (the frame from the pack: the demo asks for no picture on its own, web_bundle.py)
  const c = document.createElement("canvas"); c.width = c.height = 34; const g = c.getContext("2d"), cut = [[0, 15, 0, 15], [15, 1, 15, 4], [16, 14, 19, 15]];
  for (const [sx, sw, dx, dw] of cut) for (const [sy, sh, dy, dh] of cut) g.drawImage(im, sx, sy, sw, sh, dx, dy, dw, dh);
  const d = g.getImageData(0, 0, 34, 34), L = [255, 248, 232];
  for (let y = 0; y < 34; y++) for (let x = 0; x < 34; x++) if (x < 5 || y < 5 || x > 28 || y > 28) { const o = (y * 34 + x) * 4; for (let k = 0; k < 3; k++) d.data[o + k] = Math.round(d.data[o + k] * .62 + L[k] * .38); }
  g.putImageData(d, 0, 0); document.documentElement.style.setProperty("--slotsel", `url(${c.toDataURL()})`);
  // every other slot's frame dark wood, the one in hand alone light ("use dark border everywhere and light for selected")
  const e = document.createElement("canvas"); e.width = e.height = 30; const h = e.getContext("2d"); h.drawImage(im, 0, 0);
  const q = h.getImageData(0, 0, 30, 30), D = [91, 63, 54];
  for (let y = 0; y < 30; y++) for (let x = 0; x < 30; x++) if (x < 5 || y < 5 || x > 24 || y > 24) { const o = (y * 30 + x) * 4; for (let k = 0; k < 3; k++) q.data[o + k] = Math.round(q.data[o + k] * .45 + D[k] * .55); }
  h.putImageData(q, 0, 0); document.documentElement.style.setProperty("--slotdark", `url(${e.toDataURL()})`); })(); });
// Hearts and food sit on the hotbar, ten of each, halves allowed: a heart is a tenth of full health, a piece a tenth
// of full food (state.js: HP_MAX, FOOD_MAX; a part of a half shows as the half). Hearts are the UI pack's small hearts (full,
// half, empty); food is an apple drawn here in the hearts' own palette (plum outline, rose, glint, a leaf; empty is
// the bare outline colour, like an empty heart). Pixel-exact: every art pixel is a whole number of device pixels.
const HEART = [4, 84, 9, 8];                     // full; half and empty are the next 16 px cells along
const APPLE = ["....sg...", "...sgg...", ".aa.s.aa.", "abbabbbba", "abcbbbbba", "abbbbbbba", "abbbbbbda", ".abbbbda.", "..aaaaa.."];
const APPLE_COL = {a: "#664165", b: "#c87c86", c: "#e8b5ac", d: "#a8606e", s: "#7a5236", g: "#7fae5a"};
function pixelCanvas(cv, w, h, k = hudK) {       // sizes a canvas for art w x h at about k CSS px an art pixel
  const SC = Math.max(1, Math.round(k * (window.devicePixelRatio || 1)));
  if (cv.width !== w * SC || cv.height !== h * SC) {
    cv.width = w * SC; cv.height = h * SC;
    cv.style.width = w * SC / (window.devicePixelRatio || 1) + "px"; cv.style.height = h * SC / (window.devicePixelRatio || 1) + "px";
  }
  const g = cv.getContext("2d"); g.imageSmoothingEnabled = false; g.clearRect(0, 0, cv.width, cv.height);
  return [g, SC];
}
function drawIcons(cv, icon, value, gain = 0) {   // gain: food points to preview (what eating would give back)
  const N = 10, hearts = icon === "heart", iw = hearts ? HEART[2] : APPLE[0].length, ih = hearts ? HEART[3] : APPLE.length;
  const one = (hearts ? HP_MAX : FOOD_MAX) / N;                // what an icon is worth
  value = Math.ceil(value / (one / 2) - 1e-9) * (one / 2);
  const step = iw + 1, sig = [icon, value, gain, window.devicePixelRatio || 1, hudK].join();
  if (cv.dataset.sig === sig) return;
  cv.dataset.sig = sig;
  const [g, SC] = pixelCanvas(cv, step * (N - 1) + iw, 9);
  for (let i = 0; i < N; i++) {
    const x = i * step, full = value >= (i + 1) * one, half = !full && value >= i * one + one / 2, top = 9 - ih;
    if (hearts) {
      g.drawImage(IMG.hearts, (full ? 0 : half ? 1 : 2) * 16 + HEART[0], HEART[1], iw, ih, x * SC, top * SC, iw * SC, ih * SC);
      continue;
    }
    const after = value + gain, fullA = after >= (i + 1) * one, halfA = !fullA && after >= i * one + one / 2;
    APPLE.forEach((row, j) => [...row].forEach((c, k) => {
      if (c === ".") return;
      const lit = full || (half && k < 5), soon = !lit && (fullA || (halfA && k < 5));
      g.fillStyle = lit ? APPLE_COL[c] : APPLE_COL.a;
      g.fillRect((x + k) * SC, (top + j) * SC, SC, SC);
      if (soon) { g.globalAlpha = .55; g.fillStyle = APPLE_COL[c]; g.fillRect((x + k) * SC, (top + j) * SC, SC, SC); g.globalAlpha = 1; }
    }));
  }
  cv.classList.toggle("low", value <= one * 2.5);
}
// Holding food: the apples it would give back blink on the bar (every frame, from render; redrawn only on change).
function foodPreview() {
  if (!meObs) return;
  const h = meObs.self.hunger, gain = selected && RULES.food[selected] && h < FOOD_MAX ? RULES.food[selected] : 0;
  drawIcons($("foods"), "food", h, gain && Math.floor(performance.now() / 450) % 2 === 0 ? gain : 0);
}
function drawVitals(s) {
  drawIcons($("hearts"), "heart", s.hp);
  foodPreview();
  const status = s.hunger <= 0 || (SPRINT_FOOD < 0 && s.hunger < 25) ? `Starving: eat something (${capOf("use")})` : s.hunger <= SPRINT_FOOD ? `Too hungry to sprint: eat something (${capOf("use")})` : "";
  if (walking && walking.run !== sprinting()) syncWalk();          // (fed again, or not enough any more: the sprint follows)
  $("status").textContent = status; $("status").style.display = status ? "block" : "none";
}
function useSelected(name = selected) {
  if (!name) return toast("Nothing selected.", true);
  if (FOODS.includes(name)) return act("eat", {item: name});
  if (RULES.wear[name]) return act("wear", {item: name});
  toast(TOUCH ? `Face a tile and tap the big button to use the ${label(name)}.` : `Face a tile and press ${capOf("use")} (or click it) to use the ${label(name)}.`);
}
let mailAtTile = null;   // the mailbox the panel is open on (posting and taking aim at it exactly)
function openMailPanel(p) {
  mailAtTile = p ? {x: p.x, y: p.y} : null; $("mail").style.display = "block"; $("letters").innerHTML = `<span style="color:var(--ink2)">Write a letter, or take the letters out.</span>`;
  $("mailtitle").textContent = "Mailbox"; setTimeout(() => $("letter").focus(), 50);
}
async function postLetter() {
  const text = $("letter").value.trim(); if (!text || !mailAtTile) return;
  const r = await act("post", {...mailAtTile, text});
  if (r && r.ok) { $("letter").value = ""; toast(r.result.owner ? `Letter posted for ${r.result.owner}.` : "Letter posted."); }
}
async function takeLetters() {
  if (!mailAtTile) return;
  const r = await act("open_mail", {...mailAtTile}); if (!r || !r.ok) return;
  const {owner, letters} = r.result;
  $("mailtitle").textContent = owner ? `Mailbox of ${owner}` : "Mailbox";
  $("letters").innerHTML = letters.length ? letters.map((l) => `<div class="letter"><div class="from">from ${esc(l.from)}</div>${esc(l.text)}</div>`).join("")
    : `<span style="color:var(--ink2)">It's empty.</span>`;
}
let bannerTimer;
function banner(title, text) {
  $("bannert").textContent = title; $("bannerd").textContent = text; $("banner").style.display = "block";
  clearTimeout(bannerTimer); bannerTimer = setTimeout(() => $("banner").style.display = "none", 7000);
}
let toastTimer;
// What the game has to tell you: something could not be done, a hint, a word about what just happened.
// "all errors messages and shit show up on top of screen..": while you play the sign at the top is not shown (it is
// only for the first screen). A short note (no key in it: "You're full", "Too far: get closer.") shows over the bar
// where an item's name shows, a moment (overBar; not kept in the chat any more). The dressed welcome (a key in it, said
// to the chat on purpose: chat=true) is still a line of the chat (a small mark before it), which fades like the others.
// (The sign's text is still set, unseen: the tests and the first screen read it.)
const NOTE_MS = 6000;                                  // a note in the chat shows a little less long than what someone said
// (a guide, a message with a key in it, shows and goes: it is not kept in the chat. The keys are beside what they do)
function toast(msg, bad, stay = NOTE_MS, chat = !msg.includes("`")) {             // (msg may be dressed: **bold**, a new line, `K` a key; main.js rich. stay: ms it shows)
  if (me && chat && !msg.includes("`") && typeof rich === "function") overBar(rich(msg), bad ? "note bad" : "note", BAR_NOTE_MS);
  else if (me && chat && typeof chatLine === "function") { chatLine(msg, bad ? "note bad" : "note sys"); $("chatlog").lastElementChild.dataset.t = Date.now() - (chatKeep() * 1000 - Math.min(stay, chatSmall() ? chatKeep() * 1000 : stay)); }
  if (bad) sfx("buzz"); $("toastt").textContent = typeof plain === "function" ? plain(msg) : msg; const t = $("toast"); t.style.display = "block"; $("toastt").style.color = bad ? "var(--warn)" : "var(--ink)"; clearTimeout(toastTimer); toastTimer = setTimeout(() => t.style.display = "none", 3200); }


const isOpen = (id) => $(id).style.display === "block";
