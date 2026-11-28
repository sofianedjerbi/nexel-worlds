// Playing: joining, the agent socket, rpc and act.

let agentWs = null, aid = 0, pending = {}, busy = false;
function joinGame(name) {
  if (agentWs && agentWs.readyState <= 1) return;
  F3.woke();                                          // (Wake up: the phone's budget times the wait from here, f3.js)
  const key = "nexel-token-" + name;
  let token = localStorage.getItem(key); if (!token) { token = crypto.randomUUID(); localStorage.setItem(key, token); }
  agentWs = openSocket("/agent");
  agentWs.onopen = async () => {
    const ticket = ACCOUNT.url ? await accountTicket() : null;                         // a world that asks who you are (account.js)
    if (ACCOUNT.url && !ticket) { agentWs.close(); return; }
    const r = await rpc("hello", {name, token, persona: "human", race: myRace, ...(ticket ? {ticket} : {})});      // (races.js)
    if (r.error === "bad_ticket") accountDrop();
    if (!r.ok) { toast(r.error === "bad_token" ? `“${name}” is already someone else. Pick another name.` : errorText(r), true); agentWs.close(); return; }
    me = r.agent.name; myId = r.agent.id; follow = null; sendSpec({op: "me", id: myId}); localStorage.setItem("nexel-name", me);
    camT.x = cam.x = r.agent.x; camT.y = cam.y = r.agent.y;
    $("joinbox").style.display = "none"; $("hud").style.display = "flex"; document.body.classList.add("playing"); if (typeof zoomForTitle === "function") zoomForTitle(false);   // (your own zoom level back: zoom.js)
    $("help").style.display = localStorage.getItem("nexel-help") === "on" ? "block" : "none";
    $("mode").textContent = "playing as " + me;
    toast(TOUCH ? `**Welcome, ${me}.**\nYou wake up in a meadow.`
      : `**Welcome, ${me}.**\nYou wake up in a meadow.\n${["w", "a", "s", "d"].map((k) => `\`${keyCap(k)}\``).join(" ")} walk ·\`${capOf("jump")}\` jump\n\`${capOf("use")}\` use · \`${capOf("alt")}\` break · \`Enter\` talk\n\`G\` goals · \`H\` help`, false, 16000, true);      // (said once as you arrive: kept in the chat)
    refresh();
  };
  agentWs.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.type === "progress") {
      if (pendingAside && pendingAside.tool === d.tool) myAside = {...pendingAside, t0: performance.now()};
      else if (pendingAct && pendingAct.tool === d.tool) { myAction = {...pendingAct, t0: performance.now()}; const q = ents.get("agent" + myId); if (q) BodyPlace.faceAction(q, myAction.dir, myAction.tid); }
      if (d.ticks / d.tick_hz >= .35) progress = {t0: performance.now(), ms: d.ticks / d.tick_hz * 1000, tool: d.tool};
      return;
    }
    const f = pending[d.id]; if (f) { delete pending[d.id]; f(d); }
  };
  agentWs.onclose = (e) => { if (me) toast((e && e.reason) || "Disconnected", true); me = null; trail.length = 0; myId = null; meObs = null; $("mode").textContent = "watching"; ["hud", "craft", "help", "goals", "bag"].forEach((id) => $(id).style.display = "none"); $("joinbox").style.display = "block"; document.body.classList.remove("playing", "tab"); };
}
function rpc(op, extra) {
  return new Promise((res) => {
    if (!agentWs || agentWs.readyState !== 1) return res({ok: false, error: "offline"});
    const id = ++aid; pending[id] = res; agentWs.send(JSON.stringify({...extra, id, op}));     // (the message's own id last: an op's own `id` took its place, and its answer went to nobody)
  });
}
let refreshing = false, hurtAt = 0;
// What a fall cost you, on your hearts as you land (leap.js land): at once, not by the next look the poll gets back, up to a second after the "-1" over your head.
// A look asked for before that landing is older than it: it does not put the hearts back (refresh)
function hurtNow(n) {
  if (!meObs || !(n > 0)) return;
  meObs.self.hp = Math.max(0, meObs.self.hp - n); hurtAt = performance.now(); drawVitals(meObs.self);
}
async function refresh() {
  if (!me || refreshing) return;
  refreshing = true; const t0 = performance.now();
  const r = await rpc("observe", {});
  refreshing = false;
  if (!r.ok || t0 < hurtAt) return;
  meObs = r.obs; const s = meObs.self;
  // (your own place, as a tick that has you sets it (walk.js myTick: the world's word, your trail drained by vn, your stop dropped): a page
  // that misses those ticks still comes to where the world has you, an observe later. Standing, your tile is the world's; far
  // (another level, a teleport), you are put there at once. Not an answer older than the last tick here: the ticks come on
  // their own socket (/spectate), and one can pass it: it would put you back a tile, a tick long)
  const p = ents.get("agent" + myId), now = performance.now();
  if (p && !(clock && r.obs.tick < clock.tick) && !myTick(p, s, now) && (p.tx !== s.x || p.ty !== s.y)) {
    if (Math.abs(p.tx - s.x) + Math.abs(p.ty - s.y) > 4) { p.x = s.x; p.y = s.y; cam.x = camT.x = s.x; cam.y = camT.y = s.y; }
    p.tx = s.x; p.ty = s.y; p.moved = now;
  }
  $("mode").textContent = `${s.name} · ${s.x}, ${s.y}${s.sheltered ? " · sheltered" : ""}`;
  drawVitals(s);
  drawHotbar(s.inventory); drawGoals();
  if ($("craft").style.display === "block") drawRecipes();   // (shut, it is not kept up to date: every step you take changes what is near)
}
setInterval(refresh, 700);
let myAction = null, pendingAct = null;   // myAction is set only once the server confirms the action started
// What your hands do meanwhile (the server's ASIDE: eating): it runs beside walking, which goes on, and has its own
// two of these, so starting a walk or finishing a step doesn't end the meal on screen
let myAside = null, pendingAside = null;
// Eating, your hands are full: you can walk on and talk, nothing else until it is eaten (the server's rule: sim
// MEANWHILE). Nothing is asked for meanwhile, and no swing is shown (intent.js perform).
const eating = () => !!(pendingAside || myAside);
let actTarget = null;   // the exact tile perform() aims at: sent as x, y instead of a direction
function facingTo(p) {  // the direction to look when working on p (the bigger axis wins)
  const s = myPos(); if (!s) return null;
  const dx = p.x - s.x, dy = p.y - s.y;
  return Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? "E" : dx < 0 ? "W" : null) : dy > 0 ? "S" : "N";
}
// WHY AN ACTION WAS REFUSED, in words for people, from its code and data (#6; sim/entities.py ActionError). A code not here
// yet says the agents' sentence (`detail`). Looked up by its own keys only: a code from the wire is never a method of Object
const ERROR_TEXT = {
  need_tool: (d) => `Needs a ${label(d.tool).toLowerCase()} in hand` + (d.have === false ? ": you have none" : ""),
  missing_item: (d) => (d.food ? "Nothing it eats in your bag" : d.where === "chest" ? `No ${label(d.item).toLowerCase()} in the chest`
    : d.need > 1 ? `Takes ${d.need} ${label(d.item).toLowerCase()}: you have ${d.have}` : `No ${label(d.item).toLowerCase()} in your bag`),
  occupied: (d) => (Object.hasOwn(IN_THE_WAY, d.on) ? IN_THE_WAY[d.on] : `${label(d.on)} is there`),
  bad_target: (d) => (Object.hasOwn(TARGET_WHY, d.why) ? TARGET_WHY[d.why](d) : Object.hasOwn(Floors.WHY, d.why) ? Floors.WHY[d.why] : "Not there"),   // (a block's cell: build mode's own words, floors.js)
  changed: () => "Something changed there first",
  full: (d) => (d.what === "mailbox" ? "The mailbox is full" : "You're full"), empty: () => "Your watering can is empty: fill it at water",
  out_of_range: (d) => (Object.hasOwn(FAR_WHY, d.why) ? FAR_WHY[d.why] : "Out of reach"), no_path: (d) => (d.why === "far" ? "Too far to walk to" : "No way there"),
  need_station: (d) => `Needs a ${lcLabel(d.station)} nearby`, missing_items: (d) => `Short of ${Object.entries(d.missing).map(([k, n]) => `${n} ${lcLabel(k)}`).join(", ")}`,
  blocked: () => "Something is in the way", cliff_edge: () => "Not on the edge of a hill: build further in", not_food: () => "You can't eat that",
  no_bed: () => "That's not a bed", no_mailbox: () => "That's not a mailbox", no_chest: () => "That's not a chest", no_sign: () => "No sign to read there",
  not_placeable: () => "That can't be placed", unknown_recipe: () => "No such thing to make", no_target: () => "Nothing there", nothing_here: () => "Nothing to pick up here",
  already: () => "Already watered", missed: () => "It moved away", failed: () => "Something changed there first", bad_item: () => "A trough takes hay or food",
  need_fire: () => "Needs a torch in hand, or a campfire near", name_needed: () => "Pick a name", bad_name: () => "A name is 1 to 24 letters, digits, - or _",
  bad_token: () => "That name is someone else's", login_needed: () => "Log in with your email first", bad_ticket: () => "Log in again",
  accounts_down: () => "The accounts don't answer: try again soon",
  not_wearable: () => "That isn't worn", nothing_worn: () => "Nothing worn there", wont_burn: () => "That won't burn", not_ready: () => "Not ready yet: try again in a while",
  cannot_dig: (d) => (d.what ? `${label(d.what)} can't be dug` : (Object.hasOwn(NO_DIG, d.why) ? NO_DIG[d.why] : "That can't be dug")),
  // (the world's own refusals, not an action's: each had only the agents' sentence, and rate_limited's was its table, "limits: {'act': (900, 60.0), ...}")
  rate_limited: () => "Too fast: wait a moment", hello_first: () => "Not in the world yet: wait a moment", banned: () => "You are banned from this world",
  bad_args: () => "That can't be done that way", bad_json: () => "The world didn't understand that: reload the page", bug: () => "Something went wrong in the game",
  unknown_op: () => "The world doesn't know that", unknown_tool: () => "The world doesn't know that action", too_soon: () => "Not yet: wait a moment",
  hands_full: () => "You're eating: you can walk, nothing else until it's eaten", interrupted: () => "Stopped",
};
// (said over the bar: words, never a table, a list or a hole: "the messages over the health bar sometimes show JSON", #382)
const WORDS = (s) => typeof s === "string" && /\w/.test(s) && !/[{}[\]]|\b(undefined|null|NaN)\b|\[object/.test(s);
const NO_DIG = {deepest: "This is as deep as it goes", enclosed: "Inside the land: dig to it from beside it", not_clear: "Stand on clear ground to dig down"};
const IN_THE_WAY = {body: "Someone is standing there", you: "You stand where it goes: step aside", thing: "Something is there"};
const lcLabel = (n) => label(n).toLowerCase();
const FAR_WHY = {far: "Out of reach", behind: "Behind the land: out of reach", jump_far: "Too far to jump", inside: "Dig into the land from beside it"};
const TARGET_WHY = {
  not_a_crop: () => "Water a growing crop in tilled soil", not_open_ground: () => "On open ground only", seed_soil: () => "Seeds grow in tilled soil: dig the ground first",
  wrong_ground: (d) => `${label(d.item)} goes on ${d.goes_on.map(lcLabel).join(" or ")}`, cannot_place_on: (d) => `Not on ${lcLabel(d.ground)}`, boat_water: () => "A boat goes on the water beside you",
  needs_dry: (d) => `${label(d.item)} needs dry land`, needs_ground: (d) => `${label(d.item)} needs the ground under it`, no_floor: () => "No floor there to stand it on",
  no_lean: () => "A ladder goes against something taller", no_higher: () => "Stairs go up to something higher beside them", no_room: () => "No room there for the stairs",
  ladder_ground: () => "A ladder's foot goes on the ground", nothing_built: () => "Nothing built there", block_on_top: () => "Take the block on top first",
  no_support: () => "A block goes against something solid", too_high: () => "Nothing is built that high", nothing_overhead: () => "Nothing over your head to dig",
  self: () => "You can't hit yourself", untouchable: () => "Your hand goes through it", not_kind: (d) => `That is not a ${lcLabel(d.kind)}`, wont_eat: (d) => `A ${lcLabel(d.kind)} doesn't eat that`,
  not_agent: () => "Give to someone, not a creature",
};
// (its own words, from its data; a code whose words need data and came with none: the agents' sentence if it is words; else a plain no)
function ownWords(r) {
  const f = r && Object.hasOwn(ERROR_TEXT, r.error) ? ERROR_TEXT[r.error] : null;
  try { return f && (r.data || !f.length) ? f(r.data) : null; } catch (e) { return null; }   // (data short of what its words read)
}
const errorText = (r, s = ownWords(r)) => (WORDS(s) ? s : r && WORDS(r.detail) ? r.detail[0].toUpperCase() + r.detail.slice(1) : "That can't be done");
// A dig done with no strike heard: the strike sounds as the frame drawn at its fourth (characters.js), and a frame
// longer than the swing's first third (a slow device; the tests' fast clock on a runner: 0.47 s of the game a frame)
// went from before it to the action's end. The axe was silent ("chop" not heard, test_e2e_ui #47). Once, on the tile
// as it was when the key was pressed (a tree felled is a stump by now), and only if no strike sounded since the press:
// the frames draw your dig from the world's tick until the server's word that it started comes in (another socket, it
// may come later), with a time of its own, so a strike is told by when it sounded, not by which action drew it
function struckOnce(a, r) {
  if (!a || a.tool !== "dig" || !a.at || a.was == null || !r || !r.ok) return;
  const q = ents.get("agent" + myId);
  if (q && q.strikeAt >= a.pressed) return;
  sfx(strikeSound(a.was, a.with && SWING_ROW[toolArt(a.with)]), a.at[0], a.at[1]);
}
async function act(tool, args, quiet) {
  if (!me || (eating() && !RULES.meanwhile.includes(tool))) return null;
  while (pred && performance.now() < pred.until) await new Promise((ok) => setTimeout(ok, 16));   // the server is still coming to where you stopped: what you do, you do from there
  if (actTarget && "dir" in args) { args = {...args, x: actTarget.x, y: actTarget.y}; delete args.dir; }
  const look = actTarget ? facingTo(actTarget) : args.dir;
  const s0 = myPos(), dv = args.dir && DIRV[args.dir];
  const at = "x" in args && "y" in args && tool !== "move_to" ? [args.x, args.y] : dv && s0 ? [s0.x + dv[0], s0.y + dv[1]] : null;
  actTarget = null;
  const aside = RULES.aside.includes(tool);
  // the facing only shows once the server says the action takes time (instant things don't turn you or stop you)
  if (aside) pendingAside = {tool, item: args.item};
  else { busy = true; pendingAct = {tool, dir: look, at, tid: args.target, with: args.with, item: args.item, pressed: performance.now(), was: at ? combAt(...at) : null}; }
  const r = await rpc("act", {tool, args});
  if (aside) { pendingAside = myAside = null; if (progress && progress.tool === tool) progress = null; }
  else {
    struckOnce(myAction, r);
    pendingAct = null; myAction = null;
    busy = false; progress = null;
    if (walking === null && [...keys].some((k) => KEYDIR[k])) syncWalk();   // still holding a direction: walk on
  }
  if (!r.ok && !["interrupted", "offline", "too_soon"].includes(r.error) && !quiet) toast(`${label(tool)}: ${errorText(r)}`, true);
  if (r.ok) {
    if (r.result.lost) toast(r.result.lost[0].toUpperCase() + r.result.lost.slice(1), true);   // (ore broken with too low a pickaxe: it crumbled, sim/underground.py lost)
    const c = r.result.changed || {};
    const gained = Object.fromEntries(Object.entries(c.inventory || {}).filter(([, v]) => v > 0));
    const p = ents.get("agent" + myId);
    if (Object.keys(gained).length) sfx("collect");
    if (Object.keys(gained).length && p) floats.push({x: p.tx, y: p.ty, text: "+" + fmt(gained), color: "#fff1a8", t: performance.now() / 1000});
    if (tool === "place") markGoal({workbench: "placedBench", seed: "planted", campfire: "placedFire", mailbox: "placedMail"}[args.item] || "placed");
    if (tool === "water") markGoal("watered");
    if (tool === "dig_down") sfx("crumble");
    if (tool === "milk") markGoal("milked");
    if (r.result.text !== undefined) toast(`The sign reads\n**“${r.result.text}”**`);
    if (r.result.named) toast(`Its name is **${r.result.named}**.`);
    if (r.result.took) { if (!Object.keys(r.result.took).length) toast("It's empty."); }   // took it all (the +items float shows)
    else if (r.result.chest) toast(`Chest: ${fmt(r.result.chest) || "empty"}`);
    if (r.result.rows_near_to_far) toast(`You look into the distance: ${r.result.agents.length ? "someone is out there." : "nobody."}`);
  }
  if (tool !== "step" || (r.ok && r.result.changed && r.result.changed.inventory)) refresh();
  return r;
}
