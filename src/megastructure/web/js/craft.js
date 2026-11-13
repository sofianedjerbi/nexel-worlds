// Crafting, a recipe book. Down its side, a bookmark for each of the five kinds of thing. On the left page a short
// list: five names at a time (the wheel or the arrows turn the pages; a switch keeps only what you can make). On the
// right page the one you are on, and nothing else: its picture and name, a line about it (blurbs.js), each thing it
// takes with what you have of it, where it is made, and one button.
// It is drawn in one pixel size, the land's (--q, ui.js): a sunk cell of 18 pixels holds a thing's whole 16 pixel
// icon, and the window, the cells and the buttons are bevelled, a light edge up and left, a dark one down and right.
// (It was sixty small pictures at once, then twelve cards of several sizes: too much on the screen.)
// Up and down move in the list and turn the page at its ends, left and right (or Tab, Q and E) change kind, Enter
// makes (Shift: five), Home and End go to the first and the last of the kind, Esc closes.

const RECIPE_GROUPS = [
  ["Basics", "workbench", ["workbench", "campfire", "torch", "rope", "plank", "path", "boat", "mailbox"]],
  ["Tools", "pickaxe", ["axe", "pickaxe", "hoe", "watering_can", "spear", "sword"]],
  ["Build", "wood_wall", ["wood_wall", "door", "fence", "gate", "stone_wall", "sign", "flag", "chest"]],
  ["Home", "bed", ["bed", "chair", "table", "plant", "clock", "rug", "well", "coop", "trough", "hay", "picnic_blanket", "basket", "cooked_meat", "bread", "ingot"]],
  ["Wear", "straw_hat", []],             // (clothes, armor and charms: wear_items.js)
];
const CRAFT_ROWS = 5;
let craftFocus = null, craftTab = "Basics", craftOnly = false, craftPage = 0;   // the recipe you are on; the kind, the switch, the page

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
  return !s.have ? "Missing materials" : s.near ? "Enter or the button to make it" : `Go within 2 tiles of a ${label(st)} to make it`;
}
const craftOk = (name) => { const s = craftState(name); return s.have && s.near; };
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);
// A sunk cell with a thing's whole icon in it (and a number on it, if given)
function craftCell(name, n, cls = "") {
  const d = document.createElement("div"); d.className = "cell " + cls; d.title = capital(label(name)); d.appendChild(iconCanvas(name));
  if (n != null) d.insertAdjacentHTML("beforeend", `<span>${n}</span>`);
  return d;
}
// What the list shows: the kind's recipes (with the switch on, the ones you can make), and the page of them you are on
function craftView() {
  const groups = craftGroups(), g = groups.find(([t]) => t === craftTab) || groups[0]; craftTab = g[0];
  const all = g[2].filter((n) => !craftOnly || craftOk(n)), pages = Math.max(1, Math.ceil(all.length / CRAFT_ROWS));
  craftPage = Math.max(0, Math.min(pages - 1, craftPage));
  const shown = all.slice(craftPage * CRAFT_ROWS, (craftPage + 1) * CRAFT_ROWS);
  if (!shown.includes(craftFocus)) craftFocus = shown[0] || null;
  return {groups, all, shown, pages};
}
function craftOpened() { $("recipes").dataset.sig = ""; drawRecipes(); }
function drawRecipes() {
  const el = $("recipes"); if (!el || !Object.keys(recipes).length) return;
  const v = craftView(), sig = JSON.stringify(meObs ? meObs.self.inventory : {}) + (meObs ? meObs.grid.join("") : "") + [craftTab, craftOnly, craftPage].join();
  if (el.dataset.sig === sig) return; el.dataset.sig = sig;
  const tabs = $("crafttabs"); tabs.innerHTML = "";         // the bookmarks
  for (const [title, ic] of v.groups) {
    const b = document.createElement("div"); b.className = "ctab" + (title === craftTab ? " on" : ""); b.dataset.kind = b.title = title;
    b.appendChild(iconCanvas(ic)); b.onclick = () => craftTurn({tab: title});
    tabs.appendChild(b);
  }
  $("craftonly").className = "b " + (craftOnly ? "on" : "paper");
  el.innerHTML = v.shown.length ? "" : `<div class="cnone">${craftOnly ? "Nothing in " + esc(craftTab) + " can be made yet." : "Nothing here."}</div>`;
  for (const name of v.shown) {                             // the list: a name, lit if it can be made
    const d = document.createElement("div"); d.className = "line rcard" + (craftOk(name) ? "" : " no") + (name === craftFocus ? " cur" : "");
    d.dataset.name = name; d.title = craftWhy(name);
    d.appendChild(craftCell(name)); d.insertAdjacentHTML("beforeend", `<span>${esc(capital(label(name)))}</span>`);
    d.onmousemove = () => focusRecipe(name);                // (only a mouse that moves: one resting there leaves the keys alone)
    d.onclick = () => focusRecipe(name); d.ondblclick = () => craftMake(name);
    el.appendChild(d);
  }
  $("craftmore").textContent = `${craftTab} · ${craftPage + 1} of ${v.pages}`;
  drawCraftDetail();
}
function focusRecipe(name) {
  if (craftFocus === name) return;
  craftFocus = name;
  for (const c of $("recipes").querySelectorAll(".rcard")) c.classList.toggle("cur", c.dataset.name === name);
  drawCraftDetail();
}
// Another kind, another page, the switch: then the list again, from its first line (or its last, coming back up)
function craftTurn({tab, page, only, last}) {
  if (tab !== undefined) { craftTab = tab; craftPage = 0; }
  if (only !== undefined) { craftOnly = only; craftPage = 0; }
  if (page !== undefined) craftPage = page;
  craftFocus = null; sfx("ui"); drawRecipes();
  if (last) { const c = [...$("recipes").querySelectorAll(".rcard")].pop(); if (c) focusRecipe(c.dataset.name); }
}
function craftMake(name, five) {
  if (!name) return;
  const s = craftState(name);
  if (s.have && s.near) act("craft", five && s.n >= 5 ? {recipe: name, n: 5} : {recipe: name}); else toast(craftWhy(name), true);
}
// The right page: the recipe you are on
function drawCraftDetail() {
  const el = $("craftdetail"), name = craftFocus; if (!el) return;
  el.innerHTML = ""; if (!name || !recipes[name]) return;
  const rc = recipes[name], s = craftState(name), ok = s.have && s.near, out = Object.values(rc.output)[0];
  const head = document.createElement("div"); head.className = "chead"; head.appendChild(craftCell(name, null, "res"));
  head.insertAdjacentHTML("beforeend", `<div class="cname">${esc(capital(label(name)))}${out > 1 ? ` <i>x${out}</i>` : ""}</div>`);   // (x2: how many it makes)
  const needs = document.createElement("div"); needs.className = "well cneeds";
  const need = (item, text, miss) => {
    const row = document.createElement("div"); row.className = "cneed" + (miss ? " miss" : ""); row.appendChild(craftCell(item));
    row.insertAdjacentHTML("beforeend", `<span>${esc(capital(label(item)))}</span><b>${text}</b>`); needs.appendChild(row);
  };
  for (const [k, v] of Object.entries(rc.inputs)) need(k, `${s.inv[k] || 0}/${v}`, (s.inv[k] || 0) < v);     // what you have of what it takes
  if (rc.station) need(rc.station, s.near ? "here" : "far", !s.near);
  const btns = document.createElement("div"); btns.className = "cbtns";
  const b = document.createElement("div"); b.className = "b cbtn" + (ok ? "" : " off");
  b.textContent = ok ? "Craft" : !s.have ? "Missing materials" : `Go to a ${label(rc.station)}`;
  if (ok) b.onclick = () => craftMake(name);
  btns.appendChild(b);
  if (ok && s.n >= 5) { const b5 = document.createElement("div"); b5.className = "b paper x5"; b5.textContent = "x5"; b5.title = "five at once (Shift+Enter)"; b5.onclick = () => craftMake(name, true); btns.appendChild(b5); }
  el.append(head); el.insertAdjacentHTML("beforeend", `<div class="cblurb">${esc(BLURB[name] || "")}</div>`); el.append(needs, btns);
}
// Keys while it is open
function craftKey(k, e) {
  const v = craftView(), kinds = v.groups.map(([t]) => t), ki = kinds.indexOf(craftTab), i = v.shown.indexOf(craftFocus);
  const dir = KEYDIR[k];
  if (k === "tab" || k === "q" || k === "e" || dir === "W" || dir === "E") {       // the kinds
    const back = k === "q" || dir === "W" || (k === "tab" && e.shiftKey);
    craftTurn({tab: kinds[(ki + (back ? kinds.length - 1 : 1)) % kinds.length]});
  } else if (dir === "S") { if (i < v.shown.length - 1) focusRecipe(v.shown[i + 1]); else if (craftPage < v.pages - 1) craftTurn({page: craftPage + 1}); }
  else if (dir === "N") { if (i > 0) focusRecipe(v.shown[i - 1]); else if (craftPage > 0) craftTurn({page: craftPage - 1, last: true}); }
  else if (k === "pagedown" || k === "pageup") craftTurn({page: craftPage + (k === "pagedown" ? 1 : -1)});
  else if (k === "home") craftTurn({page: 0});
  else if (k === "end") craftTurn({page: v.pages - 1, last: true});
  else if (k === "enter" || k === " ") craftMake(craftFocus, e.shiftKey);
  else return false;
  return true;
}
$("craftonly").onclick = () => craftTurn({only: !craftOnly});
$("craftprev").onclick = () => craftTurn({page: craftPage - 1});
$("craftnext").onclick = () => craftTurn({page: craftPage + 1});
$("craft").addEventListener("wheel", (e) => { e.preventDefault(); const p = craftPage; craftPage += Math.sign(e.deltaY); craftView(); if (craftPage !== p) craftTurn({page: craftPage}); }, {passive: false});
