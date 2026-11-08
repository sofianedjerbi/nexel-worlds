// Canvas, camera and shared client state; the spectator socket; tick and event handling.

// =====================================================================================
//  Networking
// =====================================================================================
const cv = document.getElementById("c"), ctx = cv.getContext("2d");
let DPR = 1, W = 0, H = 0;
function resize() {
  DPR = window.devicePixelRatio || 1; W = innerWidth; H = innerHeight;
  cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR); cv.style.width = W + "px"; cv.style.height = H + "px";
}
addEventListener("resize", resize); resize();
let zoom = 3;
const TS = () => P * zoom;
// Screen position of world tile (0, 0). The screen centre and the camera are rounded separately, so whatever sits at
// the camera (you) lands on the same pixel every frame; rounding them together made you wobble 1 px against the
// scrolling ground at odd window sizes, which read as stutter when sprinting.
function screenOrigin(S = TS()) {
  return [Math.round(W / 2 - S / 2) - Math.round(cam.x * S), Math.round(H / 2 - S / 2) - Math.round(cam.y * S)];
}
let cam = {x: 0, y: 0}, camT = {x: 0, y: 0};
let follow = null, me = null, myId = null, meObs = null, agents = [], metrics = {}, recipes = {}, clock = {night: false, phase: .3};
let selected = null, progress = null;
const ents = new Map();
let bubbles = [], floats = [];
const requested = new Map();
const wsBase = (location.protocol === "https:" ? "wss://" : "ws://") + location.host;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;"}[c]));
const fmt = (o) => Object.entries(o || {}).map(([k, v]) => `${v} ${label(k)}`).join(", ");

let spec, sid = 0, lastWatch = "";
function connectSpec() {
  spec = new WebSocket(wsBase + "/spectate");
  spec.onopen = () => { lastWatch = ""; requested.clear(); sendSpec({op: "recipes"}); sendSpec({op: "agents"}); };
  spec.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.type === "tick") onTick(d);
    else if (d.type === "event") onEvent(d.ev);
    else if (d.type === "reply") {
      if (d.rows) onRegion(d);
      else if (d.agents) { agents = d.agents; drawAgents(); }
      else if (d.recipes) { recipes = d.recipes; drawRecipes(); }
      else if (d.tick_ms_p50 !== undefined) { metrics = d; drawStats(); }
    }
  };
  spec.onclose = () => setTimeout(connectSpec, 1000);
}
const sendSpec = (o) => spec && spec.readyState === 1 && spec.send(JSON.stringify({...o, id: ++sid}));
function viewRect(margin) {
  const w = Math.ceil(W / TS()) + margin * 2, h = Math.ceil(H / TS()) + margin * 2;
  return [Math.floor(cam.x - w / 2), Math.floor(cam.y - h / 2), w, h];
}
setInterval(() => {
  if (!spec || spec.readyState !== 1) return;
  const [x, y, w, h] = viewRect(6);
  const key = [Math.round(x / 4), Math.round(y / 4), w, h].join();
  if (key !== lastWatch) { lastWatch = key; sendSpec({op: "watch", x, y, w, h}); }
  const now = performance.now();
  for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++)
    for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++) {
      const k = bkey(bx, by), b = blocks.get(k);
      const stale = b && now - b.at > 30000;
      if ((!b || stale) && !(requested.get(k) > now - 3000)) { requested.set(k, now); if (b) b.at = now; sendSpec({op: "region", x: bx * B, y: by * B, w: B, h: B}); }
    }
}, 100);
setInterval(() => { sendSpec({op: "agents"}); sendSpec({op: "metrics"}); }, 1500);

let pred = null;
let groundItems = [], mailAt = new Set(), fireAt = [], troughAt = new Set();
function onTick(d) {
  clock = d;
  groundItems = d.items || [];
  mailAt = new Set((d.mail || []).map(([x, y]) => x + "," + y));
  troughAt = new Set((d.troughs || []).map(([x, y]) => x + "," + y));
  fireAt = (d.fires || []).map(([x, y]) => ({x, y}));
  $("clock").textContent = d.time.replace("(night)", "· night");
  const seen = new Set(), now = performance.now();
  for (const e of d.entities) {
    const key = e.kind + e.id; seen.add(key);
    let p = ents.get(key);
    if (!p) { p = {x: e.x, y: e.y, tx: e.x, ty: e.y, fx: 0, fy: 1, moved: 0}; ents.set(key, p); }
    p.e = e;
    if (e.kind === "agent" && e.id === myId && pred) {
      if ((e.x === pred.x && e.y === pred.y) || now > pred.until) pred = null; else { p.e = e; continue; }
    }
    if (p.tx !== e.x || p.ty !== e.y) {
      const dx = Math.sign(e.x - p.tx), dy = Math.sign(e.y - p.ty);
      if (dx || dy) { p.fx = dx; p.fy = dy; }
      p.moved = now; p.tx = e.x; p.ty = e.y;
      if (Math.abs(p.x - e.x) + Math.abs(p.y - e.y) > 4) { p.x = e.x; p.y = e.y; }
    }
  }
  for (const k of ents.keys()) if (!seen.has(k)) ents.delete(k);
}
function onEvent(e) {
  const t = performance.now() / 1000;
  if (e.type === "tile") {
    const g = CHAR[e.ground], blk = e.block === "none" ? g : CHAR[e.block];
    if (g && blk) setTile(e.x, e.y, blk, g);
    if (e.cause === "fire") sfx("hit", e.x, e.y);
    return;
  }
  if (e.type === "say" || e.type === "shout") { const em = emoteFor(e.text); if (em) setTimeout(() => emote(e.from, em), 2500); }
  if (e.type === "give") { emote(e.to, "love"); emote(e.from, "happy"); }
  if (e.type === "craft") emote(e.name, "star");
  if (e.type === "attack") emote(e.target, "bang");
  if (e.type === "death") emote(e.name, "skull");
  if (e.type === "say" || e.type === "shout") {
    const slot = bubbles.filter((b) => b.name === e.from && t - b.t < 7).length;
    bubbles.push({name: e.from, text: e.text, t, shout: e.type === "shout", slot: Math.min(slot, 2)});
  }
  if (e.type === "attack") {
    const tgt = [...ents.values()].find((q) => q.e && (q.e.name === e.target || `${q.e.kind}#${q.e.id}` === e.target));
    const tx = tgt ? tgt.x : e.x, ty = tgt ? tgt.y : e.y;
    if (tgt) flashes.set(tgt.e.kind === "agent" ? "agent" + tgt.e.id : tgt.e.kind + tgt.e.id, performance.now());
    burst(tx, ty, "hit", 6, {dy: -.4}); sfx("hit", tx, ty); floats.push({x: tx, y: ty, text: "-" + e.damage, color: "#ff8a7a", t});
  }
  if (e.type === "death" && e.name === me) {
    sfx("die");
    const lost = fmt(e.dropped);
    banner("You died", `${e.cause}.${lost ? " Everything you carried (" + lost + ") lies where you fell, at " + e.x + ", " + e.y + "." : ""} ${meObs && meObs.self.spawn ? "You wake up by your bed." : "You wake up somewhere else. Sleep in a bed to choose where."}`);
  }
  if (e.type === "fade") burst(e.x, e.y, "dust", 10, {up: 2, spread: 2, g: -1, life: .8});
  if (e.type === "death" || e.type === "creature_died") burst(e.x, e.y, "dust", 16, {dy: -.3, up: 2.5, spread: 4, g: 3, life: .7, size: 2});
  if (e.type === "pick_up") { burst(e.x, e.y, "spark", 6, {dy: -.5, g: 3}); sfx("pick", e.x, e.y); }
  if (e.type === "chest") chestOpen.set(e.x + "," + e.y, performance.now());
  if (e.type === "milk") { burst(e.x, e.y, "spark", 4, {dy: -.2, g: 5}); emote(e.name, "happy"); }
  if (e.type === "love") emote(e.by, "love");
  if (e.type === "lay") burst(e.x, e.y, "dust", 5, {up: 1, spread: 1.5, g: 3});
  if (e.type === "fill") { burst(e.x, e.y, "water", 8, {up: 1.5, spread: 1.5}); sfx("water", e.x, e.y); }
  if (e.type === "trough") burst(e.x, e.y, "food", 3, {dy: -.4, g: 3});
  if (e.type === "picnic") { emote(e.name, "love"); burst(e.x, e.y, "food", 6, {dy: -.6, g: 3}); }
  if (e.type === "mail" && e.to === me && e.from !== me) toast(`${e.from} left you a letter (mailbox at ${e.x}, ${e.y}).`);
  if (e.type === "mail_opened" && e.owner === me && e.by !== me) toast(`${e.by} opened your mailbox and took ${e.n} letter${e.n > 1 ? "s" : ""}!`, true);
  if (e.type === "board" || e.type === "moor") { burst(e.x, e.y, "water", 8, {up: 1.5, spread: 2}); sfx("water", e.x, e.y); }
  if (e.type === "hatch") { burst(e.x, e.y, "spark", 8, {dy: -.3, g: 4}); sfx("pick", e.x, e.y); }
  if (e.type === "born") burst(e.x, e.y, "food", 8, {dy: -.5, g: 3});
  if (e.type === "craft") { burst(e.x, e.y, "spark", 10, {dy: -.6, g: 4}); sfx("craft", e.x, e.y); }
  if (["pick_up", "drop", "chest", "milk", "love", "lay", "fill", "picnic", "trough"].includes(e.type)) return;
  if (e.type === "attack" && e.attacker !== me && e.target !== me) return;   // other people's fights: deaths still show
  let text;
  switch (e.type) {
    case "say": text = `${e.from}: “${e.text}”`; break;
    case "shout": text = `${e.from} shouts: “${e.text}”`; break;
    case "death": text = `${e.name} died (${e.cause})`; break;
    case "attack": text = `${e.attacker} hits ${e.target} (−${e.damage})`; break;
    case "give": text = `${e.from} gave ${e.to} ${fmt(e.items)}`; break;
    case "craft": text = `${e.name} made ${fmt(e.made)}`; break;
    case "join": text = `${e.name} ${e.new ? "washed ashore" : "woke up"}`; break;
    case "leave": text = `${e.name} fell asleep`; break;
    case "sign": text = `${e.by} wrote “${e.text}”`; break;
    case "creature_died": text = `a ${e.kind} died${e.by ? " (" + e.by + ")" : ""}`; break;
    default: return;
  }
  const feed = $("feed"), top = feed.firstChild;
  if (top && top.dataset.text === text) {          // the same thing again: count it instead of repeating it
    top.dataset.n = +(top.dataset.n || 1) + 1; top.querySelector(".n").textContent = ` ×${top.dataset.n}`; return;
  }
  const d = document.createElement("div"); d.dataset.text = text;
  d.innerHTML = `<span class="k">${e.tick}</span><span class="${e.type}">${esc(text)}</span><span class="n k"></span>`;
  d.onclick = () => { if (!me) { follow = null; camT.x = e.x; camT.y = e.y; } };
  feed.prepend(d); while (feed.childElementCount > 150) feed.lastChild.remove();
}
