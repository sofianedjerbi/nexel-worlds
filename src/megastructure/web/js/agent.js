// Playing: joining, the agent socket, rpc and act.

let agentWs = null, aid = 0, pending = {}, busy = false;
function joinGame(name) {
  if (agentWs && agentWs.readyState <= 1) return;
  const key = "megastructure-token-" + name;
  let token = localStorage.getItem(key); if (!token) { token = crypto.randomUUID(); localStorage.setItem(key, token); }
  agentWs = openSocket("/agent");
  agentWs.onopen = async () => {
    const r = await rpc("hello", {name, token, persona: "human"});
    if (!r.ok) { toast(r.error === "bad_token" ? `“${name}” is already someone else. Pick another name.` : (r.detail || r.error), true); agentWs.close(); return; }
    me = r.agent.name; myId = r.agent.id; follow = null; localStorage.setItem("megastructure-name", me);
    camT.x = cam.x = r.agent.x; camT.y = cam.y = r.agent.y;
    $("joinbox").style.display = "none"; $("hud").style.display = "flex"; document.body.classList.add("playing");
    $("help").style.display = localStorage.getItem("megastructure-help") === "on" ? "block" : "none";
    $("mode").textContent = "playing as " + me;
    toast("You wake up in a meadow. WASD to walk, click things to use them, Enter to talk.");
    refresh();
  };
  agentWs.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.type === "progress") {
      if (pendingAct && pendingAct.tool === d.tool) myAction = {...pendingAct, t0: performance.now()};
      if (d.ticks / d.tick_hz >= .35) progress = {t0: performance.now(), ms: d.ticks / d.tick_hz * 1000, tool: d.tool};
      return;
    }
    const f = pending[d.id]; if (f) { delete pending[d.id]; f(d); }
  };
  agentWs.onclose = () => { if (me) toast("Disconnected", true); me = null; myId = null; meObs = null; $("mode").textContent = "watching"; ["hud", "craft", "help", "goals", "bag"].forEach((id) => $(id).style.display = "none"); $("joinbox").style.display = "block"; document.body.classList.remove("playing"); };
}
function rpc(op, extra) {
  return new Promise((res) => {
    if (!agentWs || agentWs.readyState !== 1) return res({ok: false, error: "offline"});
    const id = ++aid; pending[id] = res; agentWs.send(JSON.stringify({id, op, ...extra}));
  });
}
let refreshing = false;
async function refresh() {
  if (!me || refreshing) return;
  refreshing = true;
  const r = await rpc("observe", {});
  refreshing = false;
  if (!r.ok) return;
  meObs = r.obs; const s = meObs.self;
  const p = ents.get("agent" + myId);                          // far from where the server has you (another level,
  if (p && !pred && !levelShift(p, s.x, s.y, true) && Math.abs(p.tx - s.x) + Math.abs(p.ty - s.y) > 4) {   // a teleport): be there
    p.x = p.tx = s.x; p.y = p.ty = s.y; cam.x = camT.x = s.x; cam.y = camT.y = s.y;
  }
  $("mode").textContent = `${s.name} · ${s.x}, ${s.y}${s.sheltered ? " · sheltered" : ""}`;
  drawVitals(s);
  drawHotbar(s.inventory); drawRecipes(); drawGoals();
}
setInterval(refresh, 700);
let myAction = null, pendingAct = null;   // myAction is set only once the server confirms the action started
let actTarget = null;   // the exact tile perform() aims at: sent as x, y instead of a direction
function facingTo(p) {  // the direction to look when working on p (the bigger axis wins)
  const s = myPos(); if (!s) return null;
  const dx = p.x - s.x, dy = p.y - s.y;
  return Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? "E" : dx < 0 ? "W" : null) : dy > 0 ? "S" : "N";
}
async function act(tool, args, quiet) {
  if (!me) return null;
  if (actTarget && "dir" in args) { args = {...args, x: actTarget.x, y: actTarget.y}; delete args.dir; }
  const look = actTarget ? facingTo(actTarget) : args.dir;
  const s0 = myPos(), dv = args.dir && DIRV[args.dir];
  const at = "x" in args && "y" in args && tool !== "move_to" ? [args.x, args.y] : dv && s0 ? [s0.x + dv[0], s0.y + dv[1]] : null;
  actTarget = null;
  busy = true;
  // the facing only shows once the server says the action takes time (instant things don't turn you or stop you)
  pendingAct = {tool, dir: look, at, tid: args.target, with: args.with, item: args.item};
  const r = await rpc("act", {tool, args});
  pendingAct = null; myAction = null;
  busy = false; progress = null;
  if (walking === null && [...keys].some((k) => KEYDIR[k])) syncWalk();   // still holding a direction: walk on
  if (!r.ok && !["interrupted", "offline", "too_soon"].includes(r.error) && !quiet) toast(`${label(tool)}: ${r.detail || r.error}`, true);
  if (r.ok) {
    const c = r.result.changed || {};
    const gained = Object.fromEntries(Object.entries(c.inventory || {}).filter(([, v]) => v > 0));
    const p = ents.get("agent" + myId);
    if (Object.keys(gained).length) sfx("collect");
    if (Object.keys(gained).length && p) floats.push({x: p.tx, y: p.ty, text: "+" + fmt(gained), color: "#fff1a8", t: performance.now() / 1000});
    if (tool === "place") markGoal({workbench: "placedBench", seed: "planted", campfire: "placedFire", mailbox: "placedMail"}[args.item] || "placed");
    if (tool === "water") markGoal("watered");
    if (tool === "dig_down") { toast("A cave mouth: walk down it (south)"); sfx("crumble"); }
    if (tool === "milk") markGoal("milked");
    if (r.result.text !== undefined) toast(`The sign reads: “${r.result.text}”`);
    if (r.result.took) { if (!Object.keys(r.result.took).length) toast("It's empty."); }   // took it all (the +items float shows)
    else if (r.result.chest) toast(`Chest: ${fmt(r.result.chest) || "empty"}`);
    if (r.result.rows_near_to_far) toast(`You look into the distance: ${r.result.agents.length ? "someone is out there." : "nobody."}`);
  }
  if (tool !== "step" || (r.ok && r.result.changed && r.result.changed.inventory)) refresh();
  return r;
}
