// HUD: item icons, hotbar, bag, goals, crafting, mail, toasts.

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
  if (!ic) { g.fillStyle = "#8a6a55"; g.fillRect(4, 4, 8, 8); return c; }
  if (ic[0] === "gen") { g.drawImage(IMG.gen, GEN[ic[1]] * 16, 0, 16, 16, 0, 0, 16, 16); return c; }
  const [img, x, y, w = 16, h = 16] = ic;
  const k = 16 / Math.max(w, h), dw = Math.round(w * k), dh = Math.round(h * k);   // keep the shape
  g.drawImage(IMG[img], x, y, w, h, (16 - dw) >> 1, (16 - dh) >> 1, dw, dh);
  return c;
}
let slots = JSON.parse(localStorage.getItem("megastructure-slots") || "[]");
function slotOrder(inv) {               // items keep their slot; new items take the first free one
  slots = slots.map((n) => (n && inv[n] ? n : null));
  for (const n of Object.keys(inv)) if (!slots.includes(n)) { const i = slots.indexOf(null); if (i >= 0) slots[i] = n; else slots.push(n); }
  while (slots.length < 9) slots.push(null);
  localStorage.setItem("megastructure-slots", JSON.stringify(slots));
  return slots;
}
function drawHotbar(inv) {
  const el = $("hotbar");
  if (selected && !inv[selected]) selected = null;
  const order = slotOrder(inv).slice(0, 9);
  const extra = Object.keys(inv).filter((n) => !order.includes(n));
  const can = meObs ? meObs.self.can ?? CAN_SIZE : CAN_SIZE;
  const sig = JSON.stringify(inv) + order.join() + selected + can; if (el.dataset.sig === sig) return; el.dataset.sig = sig;
  el.innerHTML = "";
  order.forEach((name, i) => {
    const d = document.createElement("div"); d.className = "slot" + (name && name === selected ? " sel" : "");
    if (name) {
      d.appendChild(iconCanvas(name));
      const how = FOODS.includes(name) ? " · E to eat, or feed animals" : name === "watering_can" ? ` · ${can}/${CAN_SIZE} water · click a crop; refill at a well or water`
        : (PLACEABLE_BLOCK[name] || FILLS[name] || name === "seed") ? " · select, click the ground to place" : "";
      d.insertAdjacentHTML("beforeend", `<span class="c">${inv[name]}</span><span class="tip">${esc(label(name) + how)}</span>`);
      if (name === "watering_can") d.insertAdjacentHTML("beforeend", `<span class="lvl"><i style="width:${Math.round(can / CAN_SIZE * 100)}%"></i></span>`);
      d.onclick = () => { selected = selected === name ? null : name; el.dataset.sig = ""; drawHotbar(meObs.self.inventory); };
      d.ondblclick = () => useSelected(name);
    }
    if (i < 9) d.insertAdjacentHTML("beforeend", `<span class="k">${i + 1}</span>`);
    el.appendChild(d);
  });
  const bag = document.createElement("div"); bag.className = "slot bagslot";   // everything beyond 9 lives in the bag
  bag.innerHTML = `<span class="bagtxt">${extra.length ? "+" + extra.length : "bag"}</span><span class="k">B</span><span class="tip">bag (B)</span>`;
  bag.onclick = () => toggleBag();
  el.appendChild(bag);
  drawBag(inv, extra);
}
// Hearts and food sit on the hotbar, 10 points an icon, halves allowed, at the art's own pixel size: hearts are the
// UI pack's wooden heart badges (full, half, empty); food is a drumstick, dark when that part of you is empty.
const BADGE = [5, 6, 21, 19];                    // where a heart badge sits in its 32 px cell
function drawIcons(cv, icon, value) {
  const N = 10, SC = 2, hearts = icon === "heart";
  // food: the icon's drawn part (its sheet cell is mostly empty), at twice its pixels: as tall as a heart
  const fb = hearts ? null : spriteBounds(IMG.gen, GEN[icon] * 16, 0, 16, 16) || [0, 0, 16, 16];
  const cw = hearts ? BADGE[2] : (fb[2] - fb[0]) * 2, step = hearts ? 19 : cw + 1, h = BADGE[3];
  const w = step * (N - 1) + cw, sig = icon + value;
  if (cv.dataset.sig === sig) return;
  cv.dataset.sig = sig;
  if (cv.width !== w * SC) { cv.width = w * SC; cv.height = h * SC; cv.style.width = w + "px"; cv.style.height = h + "px"; }
  const g = cv.getContext("2d"); g.imageSmoothingEnabled = false; g.clearRect(0, 0, cv.width, cv.height);
  for (let i = 0; i < N; i++) {
    const x = i * step * SC, full = value >= (i + 1) * 10, half = !full && value >= i * 10 + 5;
    if (hearts) {
      g.drawImage(IMG.hearts_wood, (full ? 0 : half ? 1 : 2) * 32 + BADGE[0], BADGE[1], BADGE[2], BADGE[3], x, 0, BADGE[2] * SC, BADGE[3] * SC);
      continue;
    }
    const fw = fb[2] - fb[0], fh = fb[3] - fb[1], top = Math.round((h - fh * 2) / 2) * SC;
    const food = (part) => g.drawImage(IMG.gen, GEN[icon] * 16 + fb[0], fb[1], Math.ceil(fw * part), fh, x, top, Math.ceil(fw * part) * 2 * SC, fh * 2 * SC);
    g.filter = "brightness(.3) opacity(.45)"; food(1); g.filter = "none";   // the empty socket
    if (full) food(1); else if (half) food(.5);
  }
  cv.classList.toggle("low", value <= 25);
}
function drawVitals(s) {
  drawIcons($("hearts"), "heart", s.hp);
  drawIcons($("foods"), "meat", s.hunger);
  const status = s.hunger < 25 ? "Starving: eat something (E)" : "";
  $("status").textContent = status; $("status").style.display = status ? "block" : "none";
}
let bagFocus = null;     // bag item highlighted for keyboard use
function toggleBag() { const b = $("bag"); b.style.display = b.style.display === "block" ? "none" : "block"; }
function drawBag(inv, extra) {
  const el = $("bagitems"); if (!el) return;
  el.innerHTML = extra.length ? "" : `<span style="color:var(--ink2)">Everything fits in your hotbar.</span>`;
  for (const name of extra) {
    const d = document.createElement("div"); d.className = "slot";
    d.appendChild(iconCanvas(name));
    d.insertAdjacentHTML("beforeend", `<span class="c">${inv[name]}</span><span class="tip">${esc(label(name))}</span>`);
    d.dataset.name = name; if (name === bagFocus) d.classList.add("kfocus");
    d.onclick = () => {                          // bring it into the hotbar (swapping with the selected slot or slot 9)
      const i = selected && slots.indexOf(selected) >= 0 && slots.indexOf(selected) < 9 ? slots.indexOf(selected) : 8;
      const j = slots.indexOf(name); if (j >= 0) slots[j] = slots[i]; else slots.push(slots[i]);
      slots[i] = name; selected = name; localStorage.setItem("megastructure-slots", JSON.stringify(slots));
      $("hotbar").dataset.sig = ""; drawHotbar(meObs.self.inventory);
    };
    el.appendChild(d);
  }
}
const FOODS = ["pumpkin", "cauliflower", "lettuce", "eggplant", "carrot", "fruit", "berries", "mushroom", "egg", "milk", "meat", "cooked_meat", "wheat", "bread"];
function useSelected(name = selected) {
  if (!name) return toast("Nothing selected.", true);
  if (FOODS.includes(name)) return act("eat", {item: name});
  toast(`Face a tile and press Space (or click it) to use the ${label(name)}.`);
}
const GOALS = [
  ["Chop trees for 4 wood", (inv, d) => (inv.wood || 0) >= 4 || d.workbench],
  ["Craft a workbench and place it", (inv, d) => d.placedBench],
  ["Pick berries (eat with E when hungry)", (inv) => (inv.berries || 0) > 0],
  ["Make a hoe, till soil, plant a seed", (inv, d) => d.planted],
  ["Mine 3 stone from a boulder", (inv) => (inv.stone || 0) >= 3],
  ["Craft an axe at the workbench", (inv) => inv.axe],
  ["Build a campfire before night", (inv, d) => d.placedFire],
  ["Craft a watering can, water a crop", (inv, d) => d.watered],
  ["Collect an egg or milk a cow", (inv, d) => inv.egg || inv.milk || d.milked],
  ["Build a house: walls and a door", (inv, d) => d.sheltered],
  ["Build a boat and go sailing", (inv, d) => d.sailed],
  ["Put up a mailbox", (inv, d) => d.placedMail],
];
function markGoal(key) { if (!me) return; const d = goalState(); d[key] = true; localStorage.setItem("megastructure-goals-" + me, JSON.stringify(d)); }
function goalState() { return JSON.parse(localStorage.getItem("megastructure-goals-" + me) || "{}"); }
function drawGoals() {
  if (!meObs) return;
  const inv = meObs.self.inventory, d = goalState();
  if (inv.workbench) d.workbench = true;
  if (meObs.self.sheltered) d.sheltered = true;
  if (meObs.self.sailing) d.sailed = true;
  const grid = meObs.grid.join("");
  GOALS.forEach(([, f], i) => { if (f(inv, d)) d["g" + i] = true; });
  localStorage.setItem("megastructure-goals-" + me, JSON.stringify(d));
  const open = GOALS.map(([t], i) => [t, !!d["g" + i]]);
  const shown = open.filter(([, done]) => !done).slice(0, 3);
  const el = $("goals");
  if (!shown.length) { el.style.display = "none"; return; }
  el.style.display = $("craft").style.display === "block" ? "none" : "block";
  $("goallist").innerHTML = shown.map(([t]) => `<div class="goal"><span class="box"></span><span>${esc(t)}</span></div>`).join("");
}
const RECIPE_GROUPS = [
  ["Getting started", ["workbench", "campfire", "torch", "rope", "plank", "path"]],
  ["Tools & weapons", ["axe", "pickaxe", "hoe", "watering_can", "spear", "sword"]],
  ["Travel & mail", ["boat", "mailbox"]],
  ["Building", ["wood_wall", "door", "fence", "gate", "stone_wall", "sign", "flag", "chest"]],
  ["Home", ["bed", "chair", "table", "plant", "clock", "rug"]],
  ["Farm & picnic", ["well", "coop", "trough", "hay", "picnic_blanket", "basket"]],
  ["Cooking & smelting", ["cooked_meat", "bread", "ingot"]],
];
let craftFocus = null;   // recipe name highlighted for keyboard use
function drawRecipes() {
  const el = $("recipes"); if (!el || !Object.keys(recipes).length) return;
  const inv = meObs ? meObs.self.inventory : {};
  const near = (st) => !st || (meObs && meObs.grid.some((row, j) => [...row].some((ch, i) => Math.abs(i - 10) <= 2 && Math.abs(j - 10) <= 2 && CH[ch] === st)));
  const sig = JSON.stringify(inv) + (meObs ? meObs.grid.join("") : ""); if (el.dataset.sig === sig) return; el.dataset.sig = sig;
  el.innerHTML = "";
  const listed = new Set(RECIPE_GROUPS.flatMap(([, n]) => n));
  const groups = [...RECIPE_GROUPS, ["Other", Object.keys(recipes).filter((n) => !listed.has(n))]];
  for (const [title, names] of groups) {
    const items = names.filter((n) => recipes[n]); if (!items.length) continue;
    el.insertAdjacentHTML("beforeend", `<div class="rgroup">${esc(title)}</div>`);
    const grid = document.createElement("div"); grid.className = "rgrid"; el.appendChild(grid);
    for (const name of items) {
      const rc = recipes[name], haveAll = Object.entries(rc.inputs).every(([k, v]) => (inv[k] || 0) >= v), atStation = near(rc.station);
      const card = document.createElement("div"); card.className = "rcard" + (haveAll && atStation ? "" : " no");
      card.dataset.name = name; if (name === craftFocus) card.classList.add("kfocus");
      const big = iconCanvas(name); big.className = "big"; card.appendChild(big);
      const out = Object.values(rc.output)[0];
      const body = document.createElement("div");
      body.innerHTML = `<div class="nm">${esc(label(name))}${out > 1 ? " ×" + out : ""}</div><div class="cost"></div>`;
      for (const [k, v] of Object.entries(rc.inputs)) {
        const chip = document.createElement("span"); if ((inv[k] || 0) < v) chip.className = "miss";
        chip.appendChild(iconCanvas(k)); chip.insertAdjacentText("beforeend", `${v}`);
        chip.title = `${label(k)}: need ${v}, you have ${inv[k] || 0}`;
        body.querySelector(".cost").appendChild(chip);
      }
      card.appendChild(body);
      if (rc.station) {
        const st = document.createElement("div"); st.className = "stn" + (atStation ? "" : " miss");
        st.appendChild(iconCanvas(rc.station)); st.insertAdjacentText("beforeend", `at ${label(rc.station)}`);
        body.appendChild(st);
      }
      card.title = !haveAll ? "Missing materials" : atStation ? "Click to craft"
        : `Go within 2 tiles of a ${label(rc.station)} to make it`;   // getting there is up to you
      if (haveAll && atStation) card.onclick = () => act("craft", {recipe: name});
      grid.appendChild(card);
    }
  }
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
    else if (card.onclick) card.onclick();
    else toast(card.title || "Can't use that now.", true);
    return true;
  } else return false;
  cards.forEach((c) => c.classList.remove("kfocus"));
  cards[cur].classList.add("kfocus"); cards[cur].scrollIntoView({block: "nearest"});
  setFocus(cards[cur].dataset.name);
  return true;
}
const craftKey = (k, e) => panelKey("craft", ".rcard", () => craftFocus, (n) => craftFocus = n, k, e);
const bagKey = (k, e) => panelKey("bag", ".slot[data-name]", () => bagFocus, (n) => bagFocus = n, k, e);
