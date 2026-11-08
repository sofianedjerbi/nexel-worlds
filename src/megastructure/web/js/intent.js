// What a click or key would do on a tile (intent) and doing it (perform).

const DIRV = {N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0]};
function myPos() { const p = ents.get("agent" + myId); return p ? {x: p.tx, y: p.ty} : meObs ? meObs.self : null; }
function dirTo(p) { const s = myPos(); if (!s) return null; for (const [d, [dx, dy]] of Object.entries(DIRV)) if (s.x + dx === p.x && s.y + dy === p.y) return d; return null; }
function walkable(x, y) {
  const t = tile(x, y); if (!t) return false;
  if (t[1] === "~" || t[1] === "=") return !!(meObs && meObs.self.sailing) || t[0] === "V";   // water: only by boat
  return WALKABLE_GROUND.has(t[1]) && !SOLID.has(t[0]);
}
// ---- what a click does, decided per tile (also shown as the cursor hint) ----------------
const FILLS = {dirt: {o: ",", u: ",", "~": ","}, path: {".": "_", ",": "_", "'": "_"}, plank: {"~": ":", ".": "n", ",": "n", "'": "n"}};
const FILL_TEXT = {",": "Fill with dirt", _: "Lay cobblestone path", ":": "Build bridge", n: "Lay wooden floor"};
const FILL_HELP = {dirt: "Dirt fills holes and shallow water", path: "Paths go on grass or dirt", plank: "Planks: bridge over water, floor on land"};
const PLACEABLE_BLOCK = {mailbox: "X", boat: "V", wood_wall: "W", flower: "f", bed: "B", chair: "h", table: "L", plant: "p", clock: "K", rug: "r", gate: "g", fence: "#", stone_wall: "%", door: "+", campfire: "^", workbench: "&", sign: "?", flag: "!", chest: "C", well: "Y", coop: "J", picnic_blanket: "m", basket: "q", trough: "e", hay: "y"};
const HARVEST = {t: "Dig up the stump", U: "Chop tree (the fruit grows back if you wait)", v: "Cut the bush (fiber)", e: "Take down the trough (and what's in it)", y: "Pick up the hay bale", Y: "Take down the well", J: "Take down the coop", m: "Roll up the blanket", q: "Take the basket", X: "Take down mailbox", V: "Pick up the boat", W: "Take down wall", f: "Pick flower", B: "Take down bed", h: "Take down chair", L: "Take down table", p: "Take the plant",
  K: "Take down clock", r: "Roll up rug", g: "Take down gate", F: "Pick fruit", ";": "Uproot sprout", T: "Chop tree", b: "Pick berries", M: "Mine rock", "*": "Mine ore", H: "Cut thicket", Q: "Pick mushroom",
  w: "Harvest wheat", "\"": "Uproot young wheat", "#": "Take down fence", "%": "Take down wall", "+": "Take down door",
  "^": "Take down campfire", "&": "Take down workbench", "?": "Take down sign", "!": "Take down flag", C: "Break chest open", x: "Fire!"};
// which tool speeds up digging each block (tiles.py Block.tool); ore can only be mined with a pickaxe in hand
const TOOL_FOR = {t: "axe", U: "axe", T: "axe", M: "pickaxe", "*": "pickaxe", H: "axe", "#": "axe", "%": "pickaxe", "+": "axe", "&": "axe", C: "axe", B: "axe", h: "axe",
  L: "axe", K: "axe", g: "axe", W: "axe", V: "axe", X: "axe", Y: "pickaxe", J: "axe", e: "axe"};
const WEAPON_DMG = {sword: 30, spear: 18, axe: 12, pickaxe: 10};
const inHand = () => (selected && meObs && meObs.self.inventory[selected] ? selected : null);   // what's in your hand
// The creature or person at a tile: where it stands, or where it is drawn right now (moving animals stay clickable).
function entityAt(p) {
  const others = [...ents.values()].filter((q) => q.e && !(q.e.kind === "agent" && q.e.id === myId));
  return others.find((q) => q.tx === p.x && q.ty === p.y) || others.find((q) => Math.round(q.x) === p.x && Math.round(q.y) === p.y);
}
const reachOf = (weapon) => (weapon === "spear" ? 3 : 2);   // tiles.py REACH
function intent(p, shift) {
  // the canopy of a tree covers the tile above its trunk: pointing at it means the tree
  if (combAt(p.x, p.y + 1) === "T" && GROUND.has(combAt(p.x, p.y)) && !entityAt(p) && !(selected && !shift)) p = {x: p.x, y: p.y + 1};
  let t = tile(p.x, p.y), s = myPos(), foot = null;
  if (!t || !s) return null;
  if (t[0] === "Z" || t[0] === "z") {          // part of a bigger structure: it means the whole thing
    const st = structAt(p.x, p.y);
    if (st && !(t[0] === "z" && selected && !shift && !FOODS.includes(selected))) {
      foot = footOf(st.c, st.x, st.y); t = [st.c, t[1]];
    }
  }
  const [c, g] = t, flower = c === "f", ent = entityAt(p);
  const res = intent0(p, shift, t, c, g, flower, ent, s);
  if (res && foot && !res.foot && !res.walk && !res.here) res.foot = foot;
  return res;
}
const CAN_SIZE = 12;
function intent0(p, shift, t, c, g, flower, ent, s) {
  const placing = selected && !shift && (PLACEABLE_BLOCK[selected] || FILLS[selected] || selected === "seed");
  const hasBlock = !GROUND.has(c) && !(flower && placing);   // building over a flower picks it
  const isMe = p.x === s.x && p.y === s.y;
  if (ent) {
    const who = ent.e.name || ent.e.kind, w = inHand(), weapon = w && WEAPON_DMG[w] ? w : null;
    if (ANIMALS[ent.e.kind] && selected && (FOODS.includes(selected) || selected === "hay") && !shift)
      return {text: `Feed ${label(selected)} to the ${ent.e.kind}`, near: 1, diag: true, run: () => act("feed", {target: ent.e.id, item: selected})};
    if (ent.e.kind === "agent" && selected && !weapon && !shift)
      return {text: `Give ${label(selected)} to ${ent.e.name}`, near: 2, run: (d) => act("give", {target: ent.e.id, item: selected, n: 1})};
    if (shift) {                                       // shift: the peaceful thing
      if (ent.e.kind === "cow") return {text: "Milk cow", near: 1, diag: true, run: () => act("milk", {target: ent.e.id})};
      if (ent.e.kind === "agent") return {text: `${ent.e.name} · select an item and click to give it`, info: true};
      return {text: {chicken: "Chicken: feed it (select food) for eggs", chick: "A chick: it grows into a chicken", calf: "A calf: it grows into a cow", gloom: "A gloom: it bites at night"}[ent.e.kind] || who, info: true};
    }
    const tail = ent.e.kind === "cow" ? " · shift: milk" : ent.e.kind === "agent" ? " · shift: talk" : "";
    return {text: weapon ? `Attack ${who} with ${label(weapon)}${tail}` : `Punch ${who}${tail}`, near: reachOf(weapon), diag: true, attack: true,
      run: () => act("attack", weapon ? {target: ent.e.id, with: weapon} : {target: ent.e.id})};
  }
  if (isMe && !(selected && !shift && (PLACEABLE_BLOCK[selected] || FILLS[selected] || selected === "seed")))
    return {text: "Pick up", run: () => act("pick_up", {}), here: true};
  // placing the selected item
  if (selected && !shift) {
    const it = selected, block = PLACEABLE_BLOCK[it];
    // containers first: clicking a chest, basket or trough with anything selected puts it in
    if (c === "e" && it !== "torch") return FOODS.includes(it) || it === "hay" ? {text: `Put ${label(it)} in the trough`, near: 1, run: (d) => act("store", {dir: d, item: it, n: meObs.self.inventory[it] || 1})}
                                                     : {text: "Troughs take hay or food", ok: false};
    if ((c === "C" || c === "q") && it !== "torch") return {text: `Store ${label(it)} in ${c === "q" ? "basket" : "chest"}`, near: 1, run: (d) => act("store", {dir: d, item: it, n: meObs.self.inventory[it] || 1})};
    const free = !hasBlock && WALKABLE_GROUND.has(g);
    if (FOOT[block]) {
      const f = footprint(block, p.x, p.y, s.x, s.y);
      const bad = f.tiles.filter((q) => { const tq = tile(q.x, q.y);
        return !tq || !(GROUND.has(tq[0]) || tq[0] === "f") || !WALKABLE_GROUND.has(tq[1]) || tq[1] === ":"
          || (q.x === s.x && q.y === s.y) || (SOLID.has(block) && entityAt(q)); });
      const near = [[0, 1], [0, -1], [1, 0], [-1, 0]].map(([dx, dy]) => ({x: p.x + dx, y: p.y + dy}))
        .filter((q) => !f.tiles.some((r) => r.x === q.x && r.y === q.y));
      return {text: bad.length ? (bad.some((q) => q.x === s.x && q.y === s.y) ? `Step out of the way to place the ${label(it)}` : bad.some((q) => entityAt(q)) ? "Wait, something is standing there" : `The ${label(it)} needs a clear ${FOOT[block].join("×")} spot of dry land`) : `Place ${label(it)}`,
        ghost: it, ok: !bad.length, bad, foot: f.tiles, anchor: {x: f.ax, y: f.ay}, from: near, near: 1, run: (d) => act("place", {dir: d, item: it})};
    }
    if (block === "V") return !hasBlock && g === "~" ? {text: "Launch boat", ghost: it, ok: true, near: 1, run: (d) => act("place", {dir: d, item: it})}
                                                     : {text: "Boats go on shallow water", ghost: it, ok: false};
    if (block) return free ? {text: `Place ${label(it === "hay" ? "hay_bale" : it)}`, ghost: it, ok: true, near: 1, run: (d) => act("place", {dir: d, item: it})}
                           : {text: `Can't place ${label(it)} here`, ghost: it, ok: false};
    if (it === "seed") {
      if (!hasBlock && (g === "o" || g === "u")) return {text: "Plant seed", ghost: it, ok: true, near: 1, run: (d) => act("place", {dir: d, item: it})};
      return {text: "Seeds grow in tilled soil: till it with a hoe first", ghost: it, ok: false};
    }
    if (FILLS[it]) {
      const res = !hasBlock && FILLS[it][g];
      return res ? {text: FILL_TEXT[res], ghost: it, ghostGround: res, ok: true, near: 1, run: (d) => act("place", {dir: d, item: it})}
                 : {text: FILL_HELP[it], ghost: it, ghostGround: Object.values(FILLS[it])[0], ok: false};
    }
    if (it === "torch") {
      const burnable = (!GROUND.has(c) && "TFbH#+&?!\";wCBhLrgWVXJmqeyUv".includes(c)) || (GROUND.has(c) && g === ".");
      return burnable ? {text: "Set on fire (uses the torch)", ok: true, near: 1, run: (d) => act("ignite", {dir: d, with: "torch"})}
                      : {text: "That won't burn", ok: false};
    }
    if (it === "hoe" && !hasBlock && (g === "." || g === ","))                  // the hoe in hand: Space/click tills
      return {text: "Till soil", near: 1, run: (d) => act("dig", {dir: d, with: "hoe"})};
    if (it === "watering_can" && (c === "Y" || ((g === "~" || g === "=") && GROUND.has(c))))
      return {text: `Fill the watering can (${meObs ? meObs.self.can ?? CAN_SIZE : "?"}/${CAN_SIZE})`, near: 1, run: (d) => act("water", {dir: d, with: "watering_can"})};
    if (it === "watering_can" && (c === ";" || c === '"') && meObs && meObs.self.can === 0) return {text: "The can is empty: fill it at a well or water", ok: false};
    if (it === "watering_can" && (c === ";" || c === '"')) return g === "u" ? {text: "Already watered", ok: false}
      : {text: "Water crop (grows 2x faster)", near: 1, run: (d) => act("water", {dir: d, with: "watering_can"})};
  }
  const sailing = !!(meObs && meObs.self.sailing);
  if (c === "V" && !shift && !sailing) return {text: "Board the boat", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
  if (sailing && !hasBlock && (g === "~" || g === "=")) return {text: "Sail here", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
  if (sailing && !hasBlock && WALKABLE_GROUND.has(g)) return {text: "Go ashore", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
  if (hasBlock) {
    if ((c === "C" || c === "q") && !shift) return {text: c === "q" ? "Open basket" : "Open chest", near: 1, run: (d) => act("take", {dir: d})};
    if (c === "e" && !shift) return {text: troughAt.has(p.x + "," + p.y) ? "Trough: animals within 5 tiles feed themselves · click to take out" : "Empty trough: select hay or food and click to fill it",
      near: 1, run: (d) => act("take", {dir: d})};
    if (c === "Y" && !shift) return {text: "Well (fills watering cans) · shift-click takes it down", info: true};
    if (c === "J" && !shift) return {text: "Chicken coop: hens nearby lay here, twice as often · shift: take down", info: true};
    if (c === "m" && !shift) return {text: "Picnic blanket: food eaten here fills you 50% more · shift: roll up", info: true};
    if ((c === "?" || c === "!") && !shift) return {text: "Read", near: 1, run: (d) => act("read_sign", {dir: d})};
    if (c === "X" && !shift) return {text: mailAt.has(p.x + "," + p.y) ? "Mailbox: there's mail!" : "Mailbox", near: 1, run: (d) => openMailPanel(d)};
    if (c === "B" && !shift) return {text: "Sleep (wake up here after dying)", near: 1, run: (d) => act("sleep", {dir: d})};
    if ((c === "&" || c === "^") && !shift) return {text: c === "&" ? "Workbench: craft tools here" : "Campfire: cook here", near: 2, run: () => openCraft()};
    const crop = cropSpecies(p.x, p.y);
    const text = c === "w" ? `Harvest ${crop}` : c === '"' ? `Young ${crop} (uproot)` : c === ";" ? `${crop} sprout (uproot)` : HARVEST[c] || label(CH[c]);
    const tool = TOOL_FOR[c], w = inHand();
    if (c === "*" && w !== "pickaxe")
      return {text: meObs && meObs.self.inventory.pickaxe ? "Ore: hold your pickaxe (select it) to mine it" : "Ore: you need a pickaxe to mine it", ok: false};
    const how = tool ? (w === tool ? ` with ${tool}` : " by hand (slow)") : "";
    return {text: text + how, near: 1, run: (d) => act("dig", w ? {dir: d, with: w} : {dir: d})};
  }
  if (g === "~" || g === "=") return {text: label(CH[g]), info: true};
  if (shift) {
    const takeUp = {_: "Take up the path", n: "Take up the floor", ":": "Take up the bridge"}[g];
    if (takeUp) return {text: takeUp, near: 1, run: (d) => act("dig", {dir: d})};
    if (g !== "." && g !== ",") return {text: label(CH[g]), info: true};
    return inHand() === "hoe" ? {text: "Till soil", near: 1, run: (d) => act("dig", {dir: d, with: "hoe"})}
                              : {text: "Tilling needs a hoe in hand", ok: false};
  }
  return {text: "Walk here", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
}
// walk next to the target (closest free side) if needed, then act facing it
async function perform(p, it) {
  if (!it || it.info || !it.run) return;
  if (it.ok === false) return toast(it.text, true);
  if (it.walk || it.here) return it.run();
  const s = myPos(); if (!s) return;
  if (it.foot && !it.from) {                       // a structure: any of its tiles will do
    const adj = it.foot.find((q) => Math.abs(q.x - s.x) + Math.abs(q.y - s.y) === 1);
    if (adj) return it.run(dirTo(adj));
    const onIt = it.foot.some((q) => q.x === s.x && q.y === s.y);
    if (!onIt) p = it.foot.slice().sort((a, b) => (Math.abs(a.x - s.x) + Math.abs(a.y - s.y)) - (Math.abs(b.x - s.x) + Math.abs(b.y - s.y)))[0];
  }
  const dist = Math.abs(p.x - s.x) + Math.abs(p.y - s.y), cheb = Math.max(Math.abs(p.x - s.x), Math.abs(p.y - s.y));
  const inside = it.foot && it.from && it.foot.some((q) => q.x === s.x && q.y === s.y);
  const close = dist > 0 && !inside && (it.diag ? cheb <= (it.near || 1) : dist <= (it.near || 1));
  if (!close) {
    const sides = (it.from || [[0, 1], [0, -1], [1, 0], [-1, 0]].map(([dx, dy]) => ({x: p.x + dx, y: p.y + dy})))
      .filter((q) => walkable(q.x, q.y) && !entityAt(q) && !(it.foot && it.foot.some((r) => r.x === q.x && r.y === q.y))).sort((a, b) => (Math.abs(a.x - s.x) + Math.abs(a.y - s.y)) - (Math.abs(b.x - s.x) + Math.abs(b.y - s.y)));
    if (!sides.length) return toast("Can't reach that.", true);
    const r = await act("move_to", {x: sides[0].x, y: sides[0].y}, true);
    if (!r || !r.ok) return toast("Can't get there.", true);
    const [ax, ay] = r.result.arrived;                     // trust the server's position, not the last tick
    const me_ = ents.get("agent" + myId); if (me_) { me_.tx = ax; me_.ty = ay; }
    const d = Object.entries(DIRV).find(([, [dx, dy]]) => ax + dx === p.x && ay + dy === p.y);
    return it.run(d ? d[0] : dirTo(p));
  }
  return it.run(dirTo(p));
}
function clickTile(p, shift) {
  if (combAt(p.x, p.y + 1) === "T" && GROUND.has(combAt(p.x, p.y)) && !entityAt(p) && !(selected && !shift)) p = {x: p.x, y: p.y + 1};
  perform(p, intent(p, shift));
}
