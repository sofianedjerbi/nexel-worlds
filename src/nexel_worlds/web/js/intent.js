// What a click or key would do on a tile (intent) and doing it (perform).

const DIRV = {N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0]};
function myPos() { const p = ents.get("agent" + myId); return p ? {x: p.tx, y: p.ty} : meObs ? meObs.self : null; }
function dirTo(p) { const s = myPos(); if (!s) return null; for (const [d, [dx, dy]] of Object.entries(DIRV)) if (s.x + dx === p.x && s.y + dy === p.y) return d; return null; }
function walkable(x, y, fx, fy) {               // your step from (fx, fy) onto (x, y): it lands somewhere (cells.js landAt), and you can stand there
  const z = landAt(myZ(fx, fy), x, y, fx, fy, springs(x, y));
  return z !== null && stand(x, y, z);
}
// ---- what a click does, decided per tile (also shown as the cursor hint) ----------------
// The words: "interaction sentences are wayyyy too long" (it said "Chop tree (the fruit grows back if you wait) by hand
// (slow)" beside the key). What you can do is a verb and a thing, three words or so; no reason, no advice, no tool
// named (it is in your hand). Without the tool a thing wants: "(slow)". Why something cannot be done: one short line.
const FILL_TEXT = {",": "Fill with dirt", "~": "Raise the bottom", "(": "Raise the bottom", "=": "Raise the bottom", _: "Lay path", ":": "Build bridge", n: "Lay floor"};
const FILL_HELP = {dirt: "Dirt fills holes and shallow water", stone_block: "Stone fills holes and shallow water", path: "Paths go on grass or dirt", plank: "Planks: bridge over water, floor on land"};
const HARVEST = {t: "Dig up stump", U: "Chop tree", v: "Cut bush", e: "Take down trough", y: "Take hay bale", Y: "Take down well", J: "Take down coop", m: "Roll up blanket", q: "Take basket", X: "Take down mailbox", V: "Take boat", W: "Take down wall", l: "Take ladder", f: "Pick flower", B: "Take down bed", h: "Take down chair", L: "Take down table", p: "Take plant",
  K: "Take down clock", r: "Roll up rug", g: "Take down gate", F: "Pick fruit", ";": "Uproot sprout", T: "Chop tree", b: "Pick berries", M: "Mine rock", R: "Mine rock wall", "*": "Mine ore", H: "Cut thicket", Q: "Pick mushroom",
  w: "Harvest wheat", "\"": "Uproot young wheat", "#": "Take down fence", "%": "Take down wall", "+": "Take down door",
  "^": "Take down campfire", "&": "Take down workbench", "?": "Take down sign", "!": "Take down flag", C: "Break chest open", x: "Fire!"};
const inHand = () => (selected && meObs && meObs.self.inventory[selected] ? selected : null);   // what's in your hand
// The creature or person at a tile: where it stands, or where it is drawn right now (moving animals stay clickable).
function entityAt(p) {                        // (who stands there, near your own height: a tusker on the mountain over your tunnel, twenty layers up, was on your tile: "Punch tusker", "i shouldn't be able to select the tusker here !". As far as a hand or a bite goes: sim/wild.py BITE_HIGH)
  const s = myPos(), h = s ? myZ(s.x, s.y) : null, others = [...ents.values()].filter((q) => q.e && !(q.e.kind === "agent" && q.e.id === myId) && (h === null || Math.abs(standsAt(q) - h) <= RULES.bite_high));
  return others.find((q) => q.tx === p.x && q.ty === p.y) || others.find((q) => Math.round(q.x) === p.x && Math.round(q.y) === p.y);
}
// What the pointer means at a tile. A tree's crown hangs over the tiles above its trunk (a round tree's almost two
// tiles, a thin one's one): pointing there means the tree, unless you hold something meant for that ground tile.
const TALL = "TFU";
function aimAt(p, brk) {
  if (!GROUND.has(combAt(p.x, p.y)) || entityAt(p)) return p;
  // someone's head and shoulders are drawn over the lower half of the tile above theirs: pointing there means them
  if (p.fy > 1 - (4 + STAND) / 16 && entityAt({x: p.x, y: p.y + 1})) return {x: p.x, y: p.y + 1};
  const forGround = selected && !brk && (placeable(selected) || ["hoe", "watering_can"].includes(selected));
  if (forGround) return p;
  for (const dy of [1, 2]) {
    const c = combAt(p.x, p.y + dy);
    if (!c || !TALL.includes(c)) continue;
    const spr = objectSprite(c, p.x, p.y + dy, 0), above = spr ? -spr[6] : 0;   // how far the sprite reaches up (px)
    if (above > (dy - 1) * 16 + 3) return {x: p.x, y: p.y + dy};
  }
  return p;
}
function intent(p, brk) {
  let t = tile(p.x, p.y), s = myPos(), foot = null;
  if (!t || !s) return null;
  if (t[0] === "Z" || t[0] === "z") {          // part of a bigger structure: it means the whole thing
    const st = structAt(p.x, p.y);
    if (st && !(t[0] === "z" && selected && !brk && !FOODS.includes(selected))) {
      foot = footOf(st.c, st.x, st.y); t = [st.c, t[1]];
    }
  }
  const [c, g] = t, flower = c === "f", ent = entityAt(p);
  const res = intent0(p, brk, t, c, g, flower, ent, s);
  if (res && foot && !res.foot && !res.walk && !res.here) res.foot = foot;
  if (res && !res.ent && res.z === undefined && !res.walk && !res.here) res.at = floorAt(p.x, p.y);   // (what is on a tile lies on its lowest ground: its height, for your reach. Not the tile's ground nearest you: "Pick flower" from a stair 24 layers over the flower)
  return res;
}
// Two verbs, as in Minecraft ("Why do I break rocks with E?"): brk (X, a left click) takes apart what it is on: mines,
// chops, cuts, digs, takes down, uproots, hits. Not brk (E, a right click) uses it: opens, reads, sleeps, crafts,
// talks, feeds, milks, places, plants, tills, waters, boards. Gathering (a ripe crop, a flower, berries, fruit, a
// mushroom) is a use: E.
const GATHER = "bFQfw";
function intent0(p, brk, t, c, g, flower, ent, s) {
  const placing = selected && !brk && placeable(selected);
  const hasBlock = !GROUND.has(c) && !(flower && placing);   // building over a flower picks it
  const isMe = p.x === s.x && p.y === s.y;
  if (ent) {
    const who = ent.e.name || ent.e.kind, w = inHand(), weapon = w && RULES.weapons[w] ? w : null;
    if (ent.e.kind !== "agent" && selected === "name_tag" && !brk)       // a name tag in hand: its name (ask.js)
      return {ent, text: ent.e.name ? `Rename ${ent.e.name}` : `Name the ${label(ent.e.kind)}`, reach: "animal", diag: true, run: () => nameAnimal(ent.e)};
    if (ANIMALS[ent.e.kind] && selected && FEEDS.includes(selected) && !brk)
      return {ent, text: `Feed ${label(ent.e.kind)}`, reach: "animal", diag: true, uses: true, run: () => act("feed", {target: ent.e.id, item: selected})};
    if (ent.e.kind === "agent" && selected && !weapon && !brk)
      return {ent, text: `Give to ${ent.e.name}`, reach: "give", uses: "faced", run: (d) => act("give", {target: ent.e.id, item: selected, n: 1})};
    if (!brk) {                                        // E: the peaceful thing
      if (ent.e.kind === "cow") return {ent, text: "Milk cow", reach: "animal", diag: true, run: () => act("milk", {target: ent.e.id})};
      if (ent.e.kind === "agent") return {ent, text: `${ent.e.name}: hold a thing to give it`, info: true};
      return {ent, text: {chicken: "Chicken: feed it for eggs", chick: "A chick", calf: "A calf",
        tusker: "A tusker: it charges, step aside", pincer: "A pincer: it snaps up close",
        strawman: "A strawman: it fears firelight", wisp: "A wisp",
        wyrm: "A wyrm: stay out of its line", gustling: "A gustling: it snatches what you hold",
        grumblestump: "A grumblestump: back off when its arms go up", snapbloom: "A snapbloom: step aside when it rears",
        hob: "A hob: it keeps wild things off",
        mossback: "Old Mossback: hit the neck", sporeling: "A sporeling: one hit", nyxwing: "Nyxwing: hit it between its moves"}[ent.e.kind] || who, info: true};
    }
    return {ent, text: weapon ? `Attack ${who}` : `Punch ${who}`, reach: "melee", diag: true, attack: true,      // X hits (a left click)
      run: () => act("attack", weapon ? {target: ent.e.id, with: weapon} : {target: ent.e.id})};
  }
  const up = Climb.intent(p, brk) || Floors.intent(p, brk);     // (stairs, a ladder; a block in hand, or a built block under what you aim at: climbing.js, floors.js)
  if (up) return up;
  // your own tile: something growing under your feet (a flower, a mushroom, a crop) is picked; otherwise pick up items
  const underfoot = isMe && hasBlock && !SOLID.has(c);
  if (isMe && !underfoot && !placing)
    return {text: "Pick up", run: () => act("pick_up", {}), here: true};
  // placing the selected item
  if (selected && !brk) {
    const it = selected, block = PLACEABLE_BLOCK[it];
    if (placeable(it) && rimAt(p.x, p.y)) return {text: "Nothing stays on the edge of a hill", ghost: it, ok: false};
    // containers first: clicking a chest, basket or trough with anything selected puts it in (`uses`: what you hold
    // goes there, so E does not eat it: keyboard.js facingNow; `uses` "faced": only the one you face)
    if (c === "e" && it !== "torch") return FEEDS.includes(it) ? {text: "Fill trough", uses: true, run: (d) => act("store", {dir: d, item: it, n: meObs.self.inventory[it] || 1})}
                                                     : {text: "Troughs take hay, grain or greens", ok: false};
    if ((c === "C" || c === "q") && it !== "torch") return {text: `Store in ${c === "q" ? "basket" : "chest"}`, uses: "faced", run: (d) => act("store", {dir: d, item: it, n: meObs.self.inventory[it] || 1})};
    const free = !hasBlock && WALKABLE_GROUND.has(g);
    if (FOOT[block]) {
      const f = footprint(block, p.x, p.y, s.x, s.y);
      const bad = f.tiles.filter((q) => { const tq = tile(q.x, q.y);
        return !tq || !(GROUND.has(tq[0]) || tq[0] === "f") || !WALKABLE_GROUND.has(tq[1]) || tq[1] === ":"
          || (q.x === s.x && q.y === s.y) || (SOLID.has(block) && entityAt(q)) || rimAt(q.x, q.y) || floorAt(q.x, q.y) !== floorAt(p.x, p.y); });
      const near = [[0, 1], [0, -1], [1, 0], [-1, 0]].map(([dx, dy]) => ({x: p.x + dx, y: p.y + dy}))
        .filter((q) => !f.tiles.some((r) => r.x === q.x && r.y === q.y));
      return {text: bad.length ? (bad.some((q) => q.x === s.x && q.y === s.y) ? "Step aside first" : bad.some((q) => entityAt(q)) ? "Something is in the way" : `Needs a clear ${FOOT[block].join("×")} spot`) : `Place ${label(it)}`,
        ghost: it, ok: !bad.length, bad, foot: f.tiles, anchor: {x: f.ax, y: f.ay}, from: near, run: (d) => act("place", {dir: d, item: it})};
    }
    if (it === "hob") return free ? {text: "Light the hob", ok: true, run: (d) => act("place", {dir: d, item: it})}   // (a creature, not a tile: sim/hob.py)
                                  : {text: "A hob needs open ground", ok: false};
    if (block === "V") return !hasBlock && wet(g) ? {text: "Launch boat", ghost: it, ok: true, run: (d) => act("place", {dir: d, item: it})}
                                                     : {text: "Boats go on shallow water", ghost: it, ok: false};
    if (block) return free ? {text: `Place ${label(it === "hay" ? "hay_bale" : it)}`, ghost: it, ok: true,
                              run: (d) => (it === "sign" || it === "flag" ? placeWritten(d, it) : act("place", {dir: d, item: it}))}      // (a sign is written as it goes up: ask.js)
                           : {text: `Can't place ${label(it)} here`, ghost: it, ok: false};
    if (RULES.sown[it]) {
      if (!hasBlock && RULES.sown[it].includes(g)) return {text: "Plant seed", ghost: it, ok: true, run: (d) => act("place", {dir: d, item: it})};
      return {text: "Seeds need tilled soil", ghost: it, ok: false};
    }
    if (FILLS[it]) {
      const res = !hasBlock && FILLS[it][g];
      return res ? {text: FILL_TEXT[res], ghost: it, ghostGround: res, ok: true, run: (d) => act("place", {dir: d, item: it})}
                 : {text: FILL_HELP[it], ghost: it, ghostGround: Object.values(FILLS[it])[0], ok: false};
    }
    if (it === "torch") {
      return tileOf(GROUND.has(c) ? g : c).burns ? {text: "Set on fire", ok: true, run: (d) => act("ignite", {dir: d, with: "torch"})}
                      : {text: "That won't burn", ok: false};
    }
    if (it === "hoe" && !hasBlock && (g === "." || g === ","))                  // the hoe in hand: Space/click tills
      return {text: "Till soil", run: (d) => act("dig", {dir: d, with: "hoe"})};
    if (it === "watering_can" && (c === "Y" || (wet(g) && GROUND.has(c)) || Flow.col(p.x, p.y)))
      return {text: `Fill can (${meObs ? meObs.self.can ?? RULES.can_size : "?"}/${RULES.can_size})`, run: (d) => act("water", {dir: d, with: "watering_can"})};
    if (it === "watering_can" && (c === ";" || c === '"') && meObs && meObs.self.can === 0) return {text: "The can is empty", ok: false};
    if (it === "watering_can" && (c === ";" || c === '"')) return g === "u" ? {text: "Already watered", ok: false}
      : {text: "Water crop", run: (d) => act("water", {dir: d, with: "watering_can"})};
    if (it === "watering_can" && !hasBlock && WALKABLE_GROUND.has(g) && !isMe)       // a full can poured out on open ground: water that runs (sim/waters.py)
      return meObs && (meObs.self.can ?? RULES.can_size) >= RULES.can_size ? {text: "Pour water", run: (d) => act("water", {dir: d, with: "watering_can", pour: true})} : {text: "Pouring takes a full can", ok: false};
  }
  const sailing = !!(meObs && meObs.self.sailing);
  if (c === "V" && !brk && !sailing) return {text: "Board the boat", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
  if (sailing && !hasBlock && wet(g)) return {text: "Sail here", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
  if (!hasBlock && wet(g) && toolKind(inHand()) === "pickaxe" && brk && g !== ")") return {text: "Dig deeper", run: (d) => act("dig", {dir: d, with: inHand()})};
  if (!sailing && !hasBlock && wet(g) && !placingItem()) return {text: "Swim here", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
  if (sailing && !hasBlock && WALKABLE_GROUND.has(g)) return {text: "Go ashore", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
  if (hasBlock) {
    if ((c === "C" || c === "q") && !brk) return {text: c === "q" ? "Open basket" : "Open chest", run: (d) => act("take", {dir: d})};
    if (c === "e" && !brk) return {text: troughAt.has(p.x + "," + p.y) ? "Trough: feeds animals nearby" : "Empty trough: fill it with hay",
      run: (d) => act("take", {dir: d})};
    if (c === "Y" && !brk) return {text: "Well: fills watering cans", info: true};
    if (c === "J" && !brk) return {text: "Coop: hens lay here", info: true};
    if (c === "m" && !brk) return {text: "Picnic blanket: food fills you more", info: true};
    if ((c === "?" || c === "!") && !brk) return {text: "Read", run: (d) => act("read_sign", {dir: d})};
    if (c === "X" && !brk) return {text: mailAt.has(p.x + "," + p.y) ? "Read mail" : "Mailbox", run: () => openMailPanel(actTarget)};
    if (c === "B" && !brk) return {text: "Sleep", run: (d) => act("sleep", {dir: d})};
    if ((c === "&" || c === "^") && !brk) return {text: c === "&" ? "Craft" : "Cook", run: () => openCraft()};
    const crop = cropSpecies(p.x, p.y);
    const text = c === "w" ? `Harvest ${crop}` : c === '"' ? `Uproot ${crop}` : c === ";" ? `Uproot ${crop} sprout` : HARVEST[c] || label(CH[c]);
    if (brk === GATHER.includes(c)) return {text: label(CH[c]), info: true, quiet: true};      // (E takes nothing apart; what is picked is E's, not X's)
    const tool = TOOL_FOR[c], w = inHand(), k = toolKind(w);      // (k: what the tool in hand is, any tier of it: vocab.js)
    const needs = tileOf(c).needs, Name = label(CH[c]).replace(/^./, (l) => l.toUpperCase());      // (what cannot be dug by hand at all: ore)
    if (needs && k !== needs) return {text: bestTool(needs) ? `${Name}: hold your ${needs}` : `${Name}: needs a ${needs}`, ok: false};
    const how = tool && k !== tool ? " (slow)" : "";
    return {text: text + how, gather: !brk, run: (d) => act("dig", w ? {dir: d, with: w} : {dir: d})};
  }
  if (wet(g)) return {text: label(CH[g]), info: true};
  if (brk) {
    const takeUp = {_: "Take up the path", n: "Take up the floor", ":": "Take up the bridge"}[g];
    if (takeUp) return {text: takeUp, ground: true, run: (d) => act("dig", {dir: d})};      // (ground: a click there walks, clickTile; X takes it up)
  }
  return {text: "Walk here", walk: true, run: () => act("move_to", {x: p.x, y: p.y})};
}
// walk next to the target (closest free side) if needed, then act facing it
// Do it, right here: no walking to the target (getting close is up to you). How far each kind of thing is reached: reach(),
// below. The exact tile goes to the server, so it also works while you are walking or running.
const reach = (kind, weapon, who) => RULES.reach[kind] + (RULES.long[weapon] || 0) + (RULES.wide[who] || 0);   // the world's table (tiles.py REACH; it accepts a tile more: your lead)
const SWING_MS = 420;
let lastSwing = 0;
// What you can reach: a circle round you, as the crow flies (r tiles, and the half tile to the far tile's edge), and
// height is distance too, a layer half a tile: up a cliff or down one is out of reach, however near on the map (the
// server's rule: sim/movement.py near). z: the height of what is there (someone's own; a tile's: its ground nearest
// your own height); flat: height left out.
function reaches(x, y, r, z, flat) {
  const s = myPos(); if (!s) return false;
  const h = myZ(s.x, s.y), dz = flat ? 0 : ((z === undefined ? settleNear(x, y, h) : z) - h) * RULES.layer;
  return (x - s.x) ** 2 + (y - s.y) ** 2 + dz * dz <= (r + .5) ** 2;
}
// What stands at height z on p is behind the land for you at s: higher, your own tile is shut over your head on the way
// up to it; lower, its tile is shut over it (sim/bodies.py land_between: nothing is reached through the land)
function landBetween(s, p, z) {
  const h = myZ(s.x, s.y);
  if (z > h) { for (let c = h + 2; c <= z + 1; c++) if (solidAt(s.x, s.y, c)) return true; return false; }
  if (p.x === s.x && p.y === s.y) return false;
  for (let c = z + 1; c <= h + 1; c++) if (solidAt(p.x, p.y, c)) return true;
  return false;
}
const standsAt = (o) => (o.e && o.e.z !== undefined ? o.e.z : floorAt(o.tx, o.ty));   // someone's height: a person's own; a creature's, the lowest ground under it
function inReach(p, it, flat = it.flat) {                       // (it.flat: a wall you dig into is at your own height, whatever is on top of it)
  const s = myPos(); if (!s) return false;
  const tiles = it.foot && !it.from ? it.foot : [p];            // a structure: any of its tiles will do
  const r = reach(it.reach || "use", it.attack && inHand(), it.ent && it.ent.e.kind), z = it.ent ? standsAt(it.ent) : it.z !== undefined ? it.z : it.at;
  if (!flat && !it.ent && it.z === undefined && it.at !== undefined && !it.ghost && landBetween(s, p, it.at)) return false;   // (a tree from a tunnel four layers under it)
  return tiles.some((q) => reaches(q.x, q.y, r, z, flat))
    && !(it.foot && it.from && it.foot.some((q) => q.x === s.x && q.y === s.y));   // not standing in a new structure's spot
}
const TOO_HIGH = "Out of reach: too high up, or too far down.";
async function perform(p, it) {
  if (!it || it.info || !it.run || (eating() && !it.walk)) return;   // (eating: no punch, no digging: agent.js)
  if (it.ok === false) return toast(it.text, true);
  if (it.walk || it.here) return it.run();
  if (!inReach(p, it)) return toast(inReach(p, it, true) ? TOO_HIGH : "Too far: get closer.", true);
  if (it.attack) {                                  // one swing per cooldown (sim ATTACK_COOLDOWN): no queued swings
    const now = performance.now(), me_ = ents.get("agent" + myId);
    if (now - lastSwing < SWING_MS) return;
    lastSwing = now; if (me_) me_.swing = {t0: now, with: inHand()};   // swing at once, the hit follows
  }
  if (it.foot && !it.from) {                       // a structure: aim at its nearest tile
    const s = myPos();
    p = it.foot.slice().sort((a, b) => Math.max(Math.abs(a.x - s.x), Math.abs(a.y - s.y)) - Math.max(Math.abs(b.x - s.x), Math.abs(b.y - s.y)))[0];
  }
  actTarget = p;
  return it.run(dirTo(p));
}
// A click, by how: "break" (the left button: X's verb), "use" (the right one: E's), "tap" (a phone's finger: E's, else
// X's). The left button walks you over open ground (a path too: it is not taken up), and picks what grows (a flower,
// berries: nothing to break there). -> {p, it}
function clickIntent(p0, how) {
  const brk = how === "break", p = aimAt(p0, brk), it = intent(p, brk);
  let a = {p, it};
  if (how === "tap" ? !useful(it) : brk && !useful(it)) {
    const q = aimAt(p0, !brk), o = intent(q, !brk);
    if (useful(o) && (!brk || o.gather)) a = {p: q, it: o};
  }
  if (a.it && a.it.ground) a = {p: a.p, it: {text: "Walk here", walk: true, run: () => act("move_to", {x: a.p.x, y: a.p.y})}};
  return {p: (a.it && a.it.own) || a.p, it: a.it};      // (a ladder against the wall you point at: on your own tile, climbing.js)
}
function clickTile(p, how) { const a = clickIntent(p, how); perform(a.p, a.it); }
