// Crafting: on the left the kinds of thing, by name (first of all "Can make": what you can make here and now); on
// the right the recipes of the kind you are on, and only those, each a card that says it all: its picture, its name,
// what it needs (what you lack in red, have/need) and where. A card you can make is lit: a click, a tap or Enter
// makes it (Shift: five). There is nothing else on the panel. (It was a wall of sixty small pictures, most of them
// faded, under tabs with no names, beside a pane for the one you pointed at.)
// Arrows move over the cards, Tab or Q / E change kind, Home / End, Esc closes.

const RECIPE_GROUPS = [
  ["Start", "workbench", ["workbench", "campfire", "torch", "rope", "plank", "path"]],
  ["Tools", "pickaxe", ["axe", "pickaxe", "hoe", "watering_can", "spear", "sword"]],
  ["Travel", "boat", ["boat", "mailbox"]],
  ["Build", "wood_wall", ["wood_wall", "door", "fence", "gate", "stone_wall", "sign", "flag", "chest"]],
  ["Home", "bed", ["bed", "chair", "table", "plant", "clock", "rug"]],
  ["Farm", "well", ["well", "coop", "trough", "hay", "picnic_blanket", "basket"]],
  ["Cook", "bread", ["cooked_meat", "bread", "ingot"]],
];
const READY = "Can make";                  // the first kind: all that can be made here and now
let craftFocus = null, craftTab = null;    // the recipe highlighted; the kind shown (null: not chosen yet)

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

const craftOk = (name) => { const s = craftState(name); return s.have && s.near; };
const craftKinds = () => { const g = craftGroups(); return [[READY, null, g.flatMap(([, , n]) => n).filter(craftOk)], ...g]; };

// Opened: on what you can make (nothing yet: on where it starts), whatever was looked at last time
function craftOpened() { craftTab = craftFocus = null; $("recipes").dataset.sig = ""; drawRecipes(); }
function drawRecipes() {
  const el = $("recipes"); if (!el || !Object.keys(recipes).length) return;
  const kinds = craftKinds();
  if (!kinds.some(([t]) => t === craftTab)) craftTab = kinds[0][2].length ? READY : kinds[1][0];
  const sig = JSON.stringify(meObs ? meObs.self.inventory : {}) + (meObs ? meObs.grid.join("") : "") + craftTab;
  if (el.dataset.sig === sig) return; el.dataset.sig = sig;
  const cats = $("craftcats"); cats.innerHTML = "";         // the kinds, each with how many of it can be made now
  for (const [title, ic, names] of kinds) {
    const n = names.filter(craftOk).length, b = document.createElement("div");
    b.className = "ccat" + (title === craftTab ? " on" : "") + (title === READY ? " ready" : ""); b.dataset.kind = title;
    if (ic) b.appendChild(slotIcon(ic));
    b.insertAdjacentHTML("beforeend", `${ic ? "" : `<i${n ? "" : ' class="none"'}>${n}</i>`}<span>${esc(title)}</span>${ic && n ? `<i>${n}</i>` : ""}`);
    b.onclick = () => { craftTab = title; craftFocus = null; sfx("ui"); drawRecipes(); };
    cats.appendChild(b);
  }
  const names = kinds.find(([t]) => t === craftTab)[2];     // its recipes
  el.innerHTML = names.length ? "" : `<div class="cnone">Nothing yet. Gather wood, stone and fiber: what you can make will show here.</div>`;
  el.scrollTop = 0;
  if (!names.includes(craftFocus)) craftFocus = names.find(craftOk) || names[0] || null;
  for (const name of names) el.appendChild(recipeCard(name));
}
// A recipe: its picture, its name (and how many it makes, if more than one), and what it needs: each thing with how
// many (in red, have/need, what you lack), then where it is made
function recipeCard(name) {
  const rc = recipes[name], s = craftState(name), ok = s.have && s.near, out = Object.values(rc.output)[0];
  const d = document.createElement("div"); d.className = "rcard" + (ok ? "" : " no") + (name === craftFocus ? " kfocus" : "");
  d.dataset.name = name; d.title = craftWhy(name);
  const pic = document.createElement("div"); pic.className = "rpic"; pic.appendChild(iconCanvas(name));
  const txt = document.createElement("div"); txt.className = "rtxt"; txt.innerHTML = `<div class="rname">${esc(label(name))}${out > 1 ? ` <i>x${out}</i>` : ""}</div>`;
  const needs = document.createElement("div"); needs.className = "rneeds";
  const need = (item, text, miss, tip) => {
    const n = document.createElement("span"); n.className = "rneed" + (miss ? " miss" : ""); n.title = tip;
    n.appendChild(slotIcon(item)); n.insertAdjacentText("beforeend", text); needs.appendChild(n);
  };
  for (const [k, v] of Object.entries(rc.inputs)) { const have = s.inv[k] || 0; need(k, have >= v ? v : `${have}/${v}`, have < v, `${label(k)}: you have ${have} of ${v}`); }
  if (rc.station) { needs.insertAdjacentHTML("beforeend", `<span class="rat${s.near ? "" : " miss"}">at</span>`); need(rc.station, "", !s.near, s.near ? `at the ${label(rc.station)}` : `go within 2 tiles of a ${label(rc.station)}`); }
  txt.appendChild(needs); d.append(pic, txt);
  if (ok && s.n >= 5) {                                     // five at once (Shift+Enter, Shift and a click)
    const b5 = document.createElement("button"); b5.className = "rx5"; b5.textContent = "x5"; b5.title = "make five (Shift+Enter)";
    b5.onclick = (e) => { e.stopPropagation(); focusRecipe(name); act("craft", {recipe: name, n: 5}); }; d.appendChild(b5);
  }
  d.onclick = (e) => { focusRecipe(name); if (ok) act("craft", e && e.shiftKey && s.n >= 5 ? {recipe: name, n: 5} : {recipe: name}); else toast(craftWhy(name), true); };
  d.onmousemove = () => focusRecipe(name);                  // (only a mouse that moves: one resting there leaves the keys alone)
  return d;
}
function focusRecipe(name) {
  if (craftFocus === name) return;
  craftFocus = name;
  for (const c of $("recipes").querySelectorAll(".rcard")) c.classList.toggle("kfocus", c.dataset.name === name);
}
// Keys while it's open: arrows over the cards, Enter crafts, Tab the next kind
function craftKey(k, e) {
  if (k === "tab" || k === "q" || k === "e") {         // categories: Tab / Shift+Tab, or Q and E
    const tabs = craftKinds().map(([t]) => t), i = tabs.indexOf(craftTab), back = k === "q" || (k === "tab" && e.shiftKey);
    craftTab = tabs[(i + (back ? tabs.length - 1 : 1)) % tabs.length]; craftFocus = null; sfx("ui"); drawRecipes();
    return true;
  }
  if (k === "home" || k === "end") {                     // the first or the last recipe
    const cards = [...$("recipes").querySelectorAll(".rcard")];
    if (cards.length) { const c = cards[k === "home" ? 0 : cards.length - 1]; craftFocus = null; focusRecipe(c.dataset.name); }
    return true;
  }
  return panelKey("craft", ".rcard", () => craftFocus, (n) => { craftFocus = n; }, k, e);
}
