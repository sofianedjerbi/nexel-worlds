// Crafting: category tabs, a grid of what can be made (in the hotbar's own slots; what you can't make yet dimmed),
// and beside it the one you're on: what it needs (have / need), where it's made, and a Craft button.
// Arrows move over the grid, Enter crafts (Shift+Enter five), Tab or Q / E change category, Home / End, Esc closes.
// What can be made right now wears a green tick; the rest is faded.

const RECIPE_GROUPS = [
  ["Start", "workbench", ["workbench", "campfire", "torch", "rope", "plank", "path"]],
  ["Tools", "pickaxe", ["axe", "pickaxe", "hoe", "watering_can", "spear", "sword"]],
  ["Travel", "boat", ["boat", "mailbox"]],
  ["Build", "wood_wall", ["wood_wall", "door", "fence", "gate", "stone_wall", "sign", "flag", "chest"]],
  ["Home", "bed", ["bed", "chair", "table", "plant", "clock", "rug"]],
  ["Farm", "well", ["well", "coop", "trough", "hay", "picnic_blanket", "basket"]],
  ["Cook", "bread", ["cooked_meat", "bread", "ingot"]],
];
let craftFocus = null, craftTab = "All";   // the recipe highlighted; the category shown

function craftGroups() {
  const listed = new Set(RECIPE_GROUPS.flatMap(([, , n]) => n));
  const other = Object.keys(recipes).filter((n) => !listed.has(n));
  return [...RECIPE_GROUPS, ...(other.length ? [["Other", "chest", other]] : [])].map(([t, ic, n]) => [t, ic, n.filter((r) => recipes[r])]);
}
// Can it be made here and now: {have: all materials, near: at its station, n: how many times}
function craftState(name) {
  const rc = recipes[name], inv = meObs ? meObs.self.inventory : {};
  const st = rc.station, near = !st || (meObs && meObs.grid.some((row, j) => [...row].some((ch, i) => Math.abs(i - 10) <= 2 && Math.abs(j - 10) <= 2 && CH[ch] === st)));
  const n = Math.min(...Object.entries(rc.inputs).map(([k, v]) => Math.floor((inv[k] || 0) / v)));
  return {have: n >= 1, near, n, inv};
}
function craftWhy(name) {
  const s = craftState(name), st = recipes[name].station;
  return !s.have ? "Missing materials" : s.near ? "Click to craft" : `Go within 2 tiles of a ${label(st)} to make it`;
}

function drawRecipes() {
  const el = $("recipes"); if (!el || !Object.keys(recipes).length) return;
  const sig = JSON.stringify(meObs ? meObs.self.inventory : {}) + (meObs ? meObs.grid.join("") : "") + craftTab;
  if (el.dataset.sig === sig) return; el.dataset.sig = sig;
  const groups = craftGroups();
  // the tabs
  const tabs = $("crafttabs"); tabs.innerHTML = "";
  for (const [title, ic] of [["All", null], ...groups.map(([t, i]) => [t, i])]) {
    const b = document.createElement("div"); b.className = "ctab" + (title === craftTab ? " on" : ""); b.title = title;
    if (ic) b.appendChild(slotIcon(ic)); else b.textContent = "All";
    b.onclick = () => { craftTab = title; sfx("ui"); drawRecipes(); };
    tabs.appendChild(b);
  }
  const shown = groups.filter(([t]) => craftTab === "All" || t === craftTab).flatMap(([, , n]) => n);
  const ready = shown.filter((n) => { const q = craftState(n); return q.have && q.near; }).length;
  tabs.insertAdjacentHTML("beforeend", `<div class="ctitle">${esc(craftTab === "All" ? "Everything" : craftTab)}${ready ? ` · <i>${ready} ready</i>` : ""}</div>`);
  // the grid
  el.innerHTML = "";
  const names = groups.filter(([t]) => craftTab === "All" || t === craftTab).flatMap(([, , n]) => n);
  if (!names.includes(craftFocus)) craftFocus = names.find((n) => craftState(n).have && craftState(n).near) || names[0];
  for (const name of names) {
    const s = craftState(name), out = Object.values(recipes[name].output)[0];
    const d = document.createElement("div"); d.className = "slot rcard" + (s.have && s.near ? "" : " no") + (name === craftFocus ? " kfocus" : "");
    d.dataset.name = name; d.title = craftWhy(name);
    d.appendChild(slotIcon(name));
    if (out > 1) d.insertAdjacentHTML("beforeend", `<span class="c">${out}</span>`);
    if (s.have && s.near) d.insertAdjacentHTML("beforeend", `<span class="ok">✓</span>`);   // (can be made right now)
    if (s.have && s.near) d.onclick = () => { focusRecipe(name); act("craft", {recipe: name}); };
    else d.onclick = () => focusRecipe(name);
    d.onmousemove = () => focusRecipe(name);              // (only a mouse that moves: one resting there leaves the keys alone)
    el.appendChild(d);
  }
  drawCraftDetail();
}
function focusRecipe(name) {
  if (craftFocus === name) return;
  craftFocus = name;
  for (const c of $("recipes").querySelectorAll(".rcard")) {
    c.classList.toggle("kfocus", c.dataset.name === name);
    if (c.dataset.name === name) c.scrollIntoView({block: "nearest"});
  }
  drawCraftDetail();
}
// The recipe you're on: its picture and name, what it needs, where, and the button
function drawCraftDetail() {
  const el = $("craftdetail"), name = craftFocus; if (!el) return;
  el.innerHTML = ""; if (!name || !recipes[name]) return;
  const rc = recipes[name], s = craftState(name), out = Object.values(rc.output)[0];
  const head = document.createElement("div"); head.className = "chead";
  const pic = document.createElement("div"); pic.className = "slot big"; pic.appendChild(iconCanvas(name)); head.appendChild(pic);
  head.insertAdjacentHTML("beforeend", `<div><div class="cname">${esc(label(name))}</div>${out > 1 ? `<div class="cmakes">makes ${out}</div>` : ""}</div>`);
  el.appendChild(head);
  const list = document.createElement("div"); list.className = "cneeds";
  for (const [k, v] of Object.entries(rc.inputs)) {
    const have = s.inv[k] || 0, row = document.createElement("div"); row.className = "cneed" + (have >= v ? "" : " miss");
    row.appendChild(slotIcon(k));
    row.insertAdjacentHTML("beforeend", `<span class="cn">${esc(label(k))}</span><span class="cq">${have >= v ? v : have + "/" + v}</span>`);
    list.appendChild(row);
  }
  if (rc.station) {
    const row = document.createElement("div"); row.className = "cneed st" + (s.near ? "" : " miss");
    row.appendChild(slotIcon(rc.station));
    row.insertAdjacentHTML("beforeend", `<span class="cn">${s.near ? "at the" : "go to a"} ${esc(label(rc.station))}</span><span class="cq">${s.near ? "✓" : ""}</span>`);
    list.appendChild(row);
  }
  el.appendChild(list);
  const btns = document.createElement("div"); btns.className = "cbtns";
  const ok = s.have && s.near, b = document.createElement("button"); b.className = "cbtn" + (ok ? "" : " off");
  b.textContent = ok ? "Craft" : !s.have ? "Missing materials" : `Go to a ${label(rc.station)}`;
  if (ok) b.onclick = () => act("craft", {recipe: name});
  btns.appendChild(b);
  if (ok && s.n >= 5) {
    const b5 = document.createElement("button"); b5.className = "cbtn x5"; b5.textContent = "×5"; b5.title = "Shift+Enter";
    b5.onclick = () => act("craft", {recipe: name, n: 5}); btns.appendChild(b5);
  }
  el.appendChild(btns);
}
// Keys while it's open: arrows over the grid, Enter crafts, Tab the next category
function craftKey(k, e) {
  if (k === "tab" || k === "q" || k === "e") {         // categories: Tab / Shift+Tab, or Q and E
    const tabs = ["All", ...craftGroups().map(([t]) => t)], i = tabs.indexOf(craftTab), back = k === "q" || (k === "tab" && e.shiftKey);
    craftTab = tabs[(i + (back ? tabs.length - 1 : 1)) % tabs.length]; craftFocus = null; sfx("ui"); drawRecipes();
    return true;
  }
  if (k === "home" || k === "end") {                     // the first or the last recipe
    const cards = [...$("recipes").querySelectorAll(".rcard")];
    if (cards.length) { const c = cards[k === "home" ? 0 : cards.length - 1]; craftFocus = null; focusRecipe(c.dataset.name); }
    return true;
  }
  const r = panelKey("craft", ".rcard", () => craftFocus, (n) => { craftFocus = n; drawCraftDetail(); }, k, e);
  return r;
}
