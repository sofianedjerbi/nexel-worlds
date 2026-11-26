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
  agentWs.onclose = (e) => { if (me) toast((e && e.reason) || "Disconnected", true); me = null; myId = null; meObs = null; $("mode").textContent = "watching"; ["hud", "craft", "help", "goals", "bag"].forEach((id) => $(id).style.display = "none"); $("joinbox").style.display = "block"; document.body.classList.remove("playing", "tab"); };
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
  const p = ents.get("agent" + myId);                          // far from where the server has you (another level,
  // (the tile you stopped on, its time gone: not a guess any more. It is dropped as a tick has you (walk.js myTick), but moved
  // far as you let go, no tick may have you again (they tell of what is round the screen): it would stay, and you with it, for good)
  if (pred && performance.now() > pred.until) { pred = null; trail.length = 0; }
  if (p && !pred && !(walking && p.walking) && Math.abs(p.tx - s.x) + Math.abs(p.ty - s.y) > 4) {   // a teleport): be there
    p.x = p.tx = s.x; p.y = p.ty = s.y; cam.x = camT.x = s.x; cam.y = camT.y = s.y;
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
  cannot_dig: (d) => (d.what ? `${label(d.what)} can't be dug` : (Object.hasOwn(NO_DIG, d.why) ? NO_DIG[d.why] : "That can't be dug")),
};
const NO_DIG = {deepest: "This is as deep as it goes", enclosed: "Inside the land: dig to it from beside it", not_clear: "Stand on clear ground to dig down"};
const IN_THE_WAY = {body: "Someone is standing there", you: "You stand where it goes: step aside", thing: "Something is there"};
const errorText = (r) => (r.data && Object.hasOwn(ERROR_TEXT, r.error) ? ERROR_TEXT[r.error](r.data) : r.detail || r.error);
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
  else { busy = true; pendingAct = {tool, dir: look, at, tid: args.target, with: args.with, item: args.item}; }
  const r = await rpc("act", {tool, args});
  if (aside) { pendingAside = myAside = null; if (progress && progress.tool === tool) progress = null; }
  else {
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
