// HUD: item icons, hotbar, bag, mail, toasts. (Crafting: craft.js)

function groundPreview(g, x, y) {
  if (g === "_") return [IMG.cobble, 16, 16, 16, 16, 0, 0];
  if (g === "n") return [IMG.bridge, 0, 32, 16, 16, 0, 0];
  if (g === ":") return [IMG.bridge, 0, 32, 16, 16, 0, 0];
  return [IMG.soil, 16, 16, 16, 16, 0, 0];
}
const ghosts = new Map();
const ghostIcon = (n) => ghosts.get(n) || (ghosts.set(n, iconCanvas(n)), ghosts.get(n));
function openCraft() { $("craft").style.display = "block"; }
// item icons from the sheets: [image name, sx, sy]
const ICONS = {   // [sheet, x, y, w, h]: the items sheet has seed packets in column 0, produce in column 1, materials in 2-3
  wood: ["items", 32, 48], plank: ["items", 32, 64], stone: ["items", 32, 80], ingot: ["items", 48, 64], fiber: ["gen", "fiber"],
  ore: ["gen", "ore"], path: ["cobble", 16, 16], dirt: ["soil", 0, 80], seed: ["items", 0, 128],
  axe: ["items", 32, 0], pickaxe: ["gen", "pickaxe"], hoe: ["items", 48, 0], watering_can: ["items", 32, 16], spear: ["gen", "spear"], sword: ["gen", "sword"],
  torch: ["gen", "torch"], rope: ["gen", "rope"],
  berries: ["items", 32, 160], fruit: ["items", 32, 96], mushroom: ["nature", 16, 0], egg: ["items", 48, 176], milk: ["items", 64, 0],
  meat: ["gen", "meat"], cooked_meat: ["gen", "cooked_meat"], bread: ["gen", "bread"],
  wheat: ["items", 16, 128], pumpkin: ["items", 16, 144], cauliflower: ["items", 16, 48], lettuce: ["items", 16, 112],
  eggplant: ["items", 16, 80], carrot: ["items", 16, 32],
  flower: ["nature", 16, 48], workbench: ["gen", "workbench"], campfire: ["gen", "campfire0"], chest: ["chest", 16, 16],
  boat: ["boats", 8, 36, 32, 24], mailbox: ["mailbox", 0, 16, 16, 32], fence: ["fences", 0, 48], gate: ["gates", 0, 0], wood_wall: ["house_walls", 16, 32], stone_wall: ["gen", "stone_wall"], door: ["house_walls", 48, 32],
  sign: ["signs", 0, 0], flag: ["gen", "flag"], bed: ["furniture", 0, 16, 16, 32], chair: ["furniture", 64, 32],
  table: ["furniture", 48, 48], plant: ["furniture", 48, 0, 16, 32], clock: ["furniture", 96, 48], rug: ["furniture", 0, 80], well: ["well", 0, 0, 32, 32], coop: ["coop", 160, 80, 32, 44], picnic_blanket: ["blanket", 2, 8, 44, 32], basket: ["basket", 0, 0], trough: ["barn", 0, 0], hay: ["barn", 0, 16],
};
function iconCanvas(name) {
  const c = document.createElement("canvas"); c.width = 16; c.height = 16; const g = c.getContext("2d");
  const ic = ICONS[name];
  if (!ic && WEAR[name]) return wearIcon(name);          // clothes and armor draw their own (wear_items.js)
  if (!ic) { g.fillStyle = "#8a6a55"; g.fillRect(4, 4, 8, 8); return c; }
  if (ic[0] === "gen") { g.drawImage(IMG.gen, GEN[ic[1]] * 16, 0, 16, 16, 0, 0, 16, 16); return c; }
  const [img, x, y, w = 16, h = 16] = ic;
  const k = 16 / Math.max(w, h), dw = Math.round(w * k), dh = Math.round(h * k);   // keep the shape
  g.drawImage(IMG[img], x, y, w, h, (16 - dw) >> 1, (16 - dh) >> 1, dw, dh);
  return c;
}
// The bar at the bottom is what you carry: ten slots, keys 1 to 9 and 0. (No button on it: I opens the inventory,
// C the crafting.) What is beyond ten kinds of thing is in the inventory.
const BAR = 10;
let slots = JSON.parse(localStorage.getItem("megastructure-slots") || "[]");
function slotOrder(inv) {               // items keep their slot; new items take the first free one
  slots = slots.map((n) => (n && inv[n] ? n : null));
  for (const n of Object.keys(inv)) if (!slots.includes(n)) { const i = slots.indexOf(null); if (i >= 0) slots[i] = n; else slots.push(n); }
  while (slots.length < BAR) slots.push(null);
  localStorage.setItem("megastructure-slots", JSON.stringify(slots));
  return slots;
}
function drawHotbar(inv) {
  const el = $("hotbar");
  if (selected && !inv[selected]) selected = null;
  const order = slotOrder(inv).slice(0, BAR);
  const extra = Object.keys(inv).filter((n) => !order.includes(n));
  const can = meObs ? meObs.self.can ?? CAN_SIZE : CAN_SIZE;
  const sig = JSON.stringify(inv) + order.join() + selected + can; if (el.dataset.sig === sig) return; el.dataset.sig = sig;
  el.innerHTML = "";
  order.forEach((name, i) => {
    const d = document.createElement("div"); d.className = "slot" + (name && name === selected ? " sel" : "");
    if (name) {
      d.appendChild(iconCanvas(name));
      const how = WEAR[name] ? " · E to wear" : FOODS.includes(name) ? " · E to eat, or feed animals" : name === "watering_can" ? ` · ${can}/${CAN_SIZE} water · click a crop; refill at a well or water`
        : (PLACEABLE_BLOCK[name] || FILLS[name] || name === "seed") ? " · select, click the ground to place" : "";
      d.insertAdjacentHTML("beforeend", `<span class="c">${inv[name]}</span><span class="tip">${esc(label(name) + how)}</span>`);
      if (name === "watering_can") d.insertAdjacentHTML("beforeend", `<span class="lvl"><i style="width:${Math.round(can / CAN_SIZE * 100)}%"></i></span>`);
      d.onclick = () => { selected = selected === name ? null : name; el.dataset.sig = ""; drawHotbar(meObs.self.inventory); };
      d.ondblclick = () => useSelected(name);
    }
    d.insertAdjacentHTML("beforeend", `<span class="k">${(i + 1) % 10}</span>`);
    el.appendChild(d);
  });
  drawBag(inv, order.filter(Boolean), extra);
}
// Hearts and food sit on the hotbar, 10 points an icon, halves allowed. Hearts are the UI pack's small hearts (full,
// half, empty); food is an apple drawn here in the hearts' own palette (plum outline, rose, glint, a leaf; empty is
// the bare outline colour, like an empty heart). Pixel-exact: every art pixel is a whole number of device pixels.
const HEART = [4, 84, 9, 8];                     // full; half and empty are the next 16 px cells along
const APPLE = ["....sg...", "...sgg...", ".aa.s.aa.", "abbabbbba", "abcbbbbba", "abbbbbbba", "abbbbbbda", ".abbbbda.", "..aaaaa.."];
const APPLE_COL = {a: "#664165", b: "#c87c86", c: "#e8b5ac", d: "#a8606e", s: "#7a5236", g: "#7fae5a"};
const HUD_K = 2.5;                               // CSS px an art pixel in the vitals and the xp bar
function pixelCanvas(cv, w, h, k = HUD_K) {      // sizes a canvas for art w x h at about k CSS px an art pixel
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
  const step = iw + 1, sig = [icon, value, gain, window.devicePixelRatio || 1].join();
  if (cv.dataset.sig === sig) return;
  cv.dataset.sig = sig;
  const [g, SC] = pixelCanvas(cv, step * (N - 1) + iw, 9);
  for (let i = 0; i < N; i++) {
    const x = i * step, full = value >= (i + 1) * 10, half = !full && value >= i * 10 + 5, top = 9 - ih;
    if (hearts) {
      g.drawImage(IMG.hearts, (full ? 0 : half ? 1 : 2) * 16 + HEART[0], HEART[1], iw, ih, x * SC, top * SC, iw * SC, ih * SC);
      continue;
    }
    const after = value + gain, fullA = after >= (i + 1) * 10, halfA = !fullA && after >= i * 10 + 5;
    APPLE.forEach((row, j) => [...row].forEach((c, k) => {
      if (c === ".") return;
      const lit = full || (half && k < 5), soon = !lit && (fullA || (halfA && k < 5));
      g.fillStyle = lit ? APPLE_COL[c] : APPLE_COL.a;
      g.fillRect((x + k) * SC, (top + j) * SC, SC, SC);
      if (soon) { g.globalAlpha = .55; g.fillStyle = APPLE_COL[c]; g.fillRect((x + k) * SC, (top + j) * SC, SC, SC); g.globalAlpha = 1; }
    }));
  }
  cv.classList.toggle("low", value <= 25);
}
// Holding food: the apples it would give back blink on the bar (every frame, from render; redrawn only on change).
function foodPreview() {
  if (!meObs) return;
  const h = meObs.self.hunger, gain = selected && foodValue[selected] && h < 100 ? foodValue[selected] : 0;
  drawIcons($("foods"), "food", h, gain && Math.floor(performance.now() / 450) % 2 === 0 ? gain : 0);
}
function drawVitals(s) {
  drawIcons($("hearts"), "heart", s.hp);
  foodPreview();
  const status = s.hunger < 25 ? "Starving: eat something (E)" : "";
  $("status").textContent = status; $("status").style.display = status ? "block" : "none";
}
let bagFocus = null;     // bag item highlighted for keyboard use
// The inventory (I): everything you carry, with its name: the ten of your bar, then what is beyond them. Picking one
// takes it in hand (one from beyond the bar comes onto it, in place of what you hold, or of the last slot).
function toggleBag() { const b = $("bag"), on = b.style.display !== "block"; sfx(on ? "open" : "close"); b.style.display = on ? "block" : "none"; }
function drawBag(inv, onBar, extra) {
  const el = $("bagitems"); if (!el) return;
  el.innerHTML = onBar.length || extra.length ? "" : `<span style="color:var(--ink2)">You carry nothing.</span>`;
  const card = (name, beyond) => {
    const d = document.createElement("div"); d.className = "slot" + (name === selected ? " sel" : "");
    d.appendChild(iconCanvas(name));
    d.insertAdjacentHTML("beforeend", `<span class="c">${inv[name]}</span><span class="tip">${esc(label(name))}</span>`);
    d.dataset.name = name; d.title = label(name); if (name === bagFocus) d.classList.add("kfocus");
    if (beyond) d.style.opacity = ".8";
    d.onclick = () => {
      if (beyond) {                              // onto the bar, swapping with the slot in hand (or the last)
        const i = selected && slots.indexOf(selected) >= 0 && slots.indexOf(selected) < BAR ? slots.indexOf(selected) : BAR - 1;
        const j = slots.indexOf(name); if (j >= 0) slots[j] = slots[i]; else slots.push(slots[i]);
        slots[i] = name; localStorage.setItem("megastructure-slots", JSON.stringify(slots));
      }
      selected = name; $("hotbar").dataset.sig = ""; drawHotbar(meObs.self.inventory);
    };
    el.appendChild(d);
  };
  onBar.forEach((n) => card(n, false));
  if (extra.length) el.insertAdjacentHTML("beforeend", `<span style="flex-basis:100%;color:var(--ink2);font-size:13px">not on your bar:</span>`);
  extra.forEach((n) => card(n, true));
}
// what animals eat: what grows (no eggs, meat or milk), and hay (tiles.FEED)
const FEEDS = ["pumpkin", "cauliflower", "lettuce", "eggplant", "carrot", "fruit", "berries", "mushroom", "wheat", "bread", "hay"];
const FOODS = ["pumpkin", "cauliflower", "lettuce", "eggplant", "carrot", "fruit", "berries", "mushroom", "egg", "milk", "meat", "cooked_meat", "wheat", "bread"];
function useSelected(name = selected) {
  if (!name) return toast("Nothing selected.", true);
  if (FOODS.includes(name)) return act("eat", {item: name});
  if (WEAR[name]) return act("wear", {item: name});
  toast(`Face a tile and press Space (or click it) to use the ${label(name)}.`);
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
function toast(msg, bad) {
  if (bad) sfx("buzz"); $("toastt").textContent = msg; const t = $("toast"); t.style.display = "block"; $("toastt").style.color = bad ? "var(--warn)" : "var(--ink)"; clearTimeout(toastTimer); toastTimer = setTimeout(() => t.style.display = "none", 3200); }


// ------------------------------------------------------------------ keyboard navigation inside panels
// Arrow keys (or WASD) move a highlight over the cards of an open panel; Enter/Space uses the highlighted card.
const isOpen = (id) => $(id).style.display === "block";
function nearestCard(cards, cur, dir) {
  if (cur < 0) return 0;
  const r = cards[cur].getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  let best = -1, bestD = Infinity;
  cards.forEach((c, i) => {
    if (i === cur) return;
    const q = c.getBoundingClientRect(), dx = q.left + q.width / 2 - cx, dy = q.top + q.height / 2 - cy;
    const along = {N: -dy, S: dy, W: -dx, E: dx}[dir], across = dir === "N" || dir === "S" ? Math.abs(dx) : Math.abs(dy);
    if (along <= 2) return;                                  // only cards that lie in that direction
    const d = along + across * 3;                            // prefer staying in the same row/column
    if (d < bestD) { bestD = d; best = i; }
  });
  return best < 0 ? cur : best;
}
function panelKey(id, cardSel, getFocus, setFocus, k, e) {
  const cards = [...$(id).querySelectorAll(cardSel)]; if (!cards.length) return false;
  let cur = cards.findIndex((c) => c.dataset.name === getFocus());
  const dir = KEYDIR[k];
  if (dir) cur = nearestCard(cards, cur, dir);
  else if (k === "enter" || k === " ") {
    const card = cards[Math.max(0, cur)];
    if (e.shiftKey && id === "craft" && !card.classList.contains("no")) act("craft", {recipe: card.dataset.name, n: 5});
    else if (card.onclick && !card.classList.contains("no")) card.onclick();
    else toast(card.title || "Can't use that now.", true);
    return true;
  } else return false;
  cards.forEach((c) => c.classList.remove("kfocus"));
  cards[cur].classList.add("kfocus"); cards[cur].scrollIntoView({block: "nearest"});
  setFocus(cards[cur].dataset.name);
  return true;
}
const bagKey = (k, e) => panelKey("bag", ".slot[data-name]", () => bagFocus, (n) => bagFocus = n, k, e);
