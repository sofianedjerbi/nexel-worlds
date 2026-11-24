// Canvas, camera and shared client state; the spectator socket; tick and event handling.

// =====================================================================================
//  Networking
// =====================================================================================
const cv = document.getElementById("c");
let ctx = cv.getContext("2d");      // (let: drawOn points it elsewhere, and nothing else does)
// drawOn(g, z, fn): the game's painters called in fn paint on g, an art px z of its px (they read `ctx` and `zoom`). THE ONE PLACE the two are pointed elsewhere, and put back
// whatever fn does. (Five painters each kept, set and restored them by hand: a body's picture, a wake's, a built piece's, the words', the marks'.)
function drawOn(g, z, fn) { const keep = ctx, kz = zoom; ctx = g; zoom = z; try { return fn(); } finally { ctx = keep; zoom = kz; } }
// The canvas is drawn with at most DPR_MAX device px a CSS px: pixel art gains nothing past 2, and a 3x phone
// screen is nine times the paint of a plain one. A machine that still can't keep up (slowFrame, below) draws at 1.
let DPR = 1, W = 0, H = 0, DPR_MAX = 2, frameMs = 16, paceFrom = 0;
function resize() {
  DPR = Math.min(window.devicePixelRatio || 1, DPR_MAX); W = innerWidth; H = innerHeight;
  cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR); cv.style.width = W + "px"; cv.style.height = H + "px";
}
addEventListener("resize", resize); resize();
// Called each frame with its length: when frames have been long for a good while on a dense screen, draw at 1 px a
// CSS px from then on (a quarter of the paint; the art is as sharp, only the lettering loses a little)
function slowFrame(dt, settled) {
  const now = performance.now();
  if (!settled || document.hidden || DPR <= 1) { paceFrom = now; return; }   // (loading, in the background: says nothing)
  frameMs += (Math.min(dt, .1) * 1000 - frameMs) * .02;
  if (frameMs < 30) paceFrom = now;
  else if (now - paceFrom > 4000) { DPR_MAX = 1; frameMs = 16; resize(); }
}
let zoom = 3;
const TS = () => P * zoom;
// THE LAND'S PIXEL ON THE SCREEN: an art px is a whole number of the screen's own px (devicePixelRatio's): zoom x density, rounded where that is not whole. At a density of 1.25 or
// 1.75 (a laptop's, a page zoomed in the browser) a zoom of 3 was 3.75 px: art px 3 and 4 px wide in turn, the land shimmering as it went by, and what is written over it
// (names, bubbles, hearts) put at fractions of a px: soft, and another px each step. artPx: CSS px an art px (the land's canvas is shown at that, hd_view.js); onArt: a place
// put on that pixel. What is written over a body is put there by its place on the land's pixel plus fixed offsets: it goes with the body px for px.
const artPx = () => { const d = window.devicePixelRatio || 1; return Math.max(1, Math.round(zoom * d)) / d; };
const onArt = (v) => { const u = artPx(); return Math.round(v / u) * u; };
// Screen position of world tile (0, 0). The screen centre and the camera are rounded separately, so whatever sits at
// the camera (you) lands on the same pixel every frame; rounding them together made you wobble 1 px against the
// scrolling ground at odd window sizes, which read as stutter when sprinting.
function screenOrigin(S = TS()) {
  return [Math.round(W / 2 - S / 2) - Math.round(cam.x * S), Math.round(H / 2 - S / 2) - Math.round(cam.y * S)];
}
let cam = {x: 0, y: 0}, camT = {x: 0, y: 0};
let follow = null, me = null, myId = null, meObs = null, agents = [], metrics = {}, clock = {night: false, phase: .3};
let selected = null, progress = null;
let handSlot = Math.min(9, Math.max(0, Math.floor(+localStorage.getItem("nexel-hand")) || 0));   // the bar's slot in hand, always one (an empty one too): `selected` is what is in it (ui.js handSync)
// Health and food: how much is full, and the food it takes to sprint. The server says so when it greets (20, 20 and 6:
// half hearts and half pieces, as the sandbox classic has them); one from before that says nothing: 0 to 100.
let {hp_max: HP_MAX, food_max: FOOD_MAX, sprint_food: SPRINT_FOOD, swim_pace: SWIM_PACE, eat_pace: EAT_PACE} = RULES, SWIM_SPRINT = false;      // (SWIM_SPRINT: this server sprints in the water too; SWIM_PACE, EAT_PACE: how many times longer a tile takes there, and while eating)
const hearts = (hp) => Math.round(hp / (HP_MAX / 10) * 10) / 10;      // a blow, on a person or a creature, is said in hearts: "-0.5", "-1.5"
const ents = new Map();
let bubbles = [], floats = [];
const requested = new Map();   // a block asked for -> when (ms); asked as FAR land, minus when: a far ask does not keep the land you come to from being asked for (state.js below)
const wsBase = (location.protocol === "https:" ? "wss://" : "ws://") + location.host;
// the demo build has no server: the game runs in the page (local.js) behind the same socket interface
const openSocket = (path) => typeof LocalSocket !== "undefined" ? new LocalSocket(path) : new WebSocket(wsBase + path);
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;"}[c]));
const fmt = (o) => Object.entries(o || {}).map(([k, v]) => `${v} ${label(k)}`).join(", ");

let spec, sid = 0, lastWatch = "", webStamp = 0;
function connectSpec() {
  spec = openSocket("/spectate");
  spec.onopen = () => { lastWatch = ""; requested.clear(); sendSpec({op: "agents"}); if (myId !== null) sendSpec({op: "me", id: myId}); };   // (me: who plays on this screen, for what it is sent: it hears what you hear)
  spec.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.type === "hello") {                     // back after the server restarted with newer code: this page is stale (it would draw the new world wrong)
      if (webStamp && d.web && d.web !== webStamp) location.reload();
      webStamp = d.web || webStamp;
      if (d.rules) { setRules(d.rules); ({hp_max: HP_MAX, food_max: FOOD_MAX, sprint_food: SPRINT_FOOD, swim_pace: SWIM_PACE, eat_pace: EAT_PACE} = RULES); }   // (the world's rules, said again: vocab.js)
      FLOORS = !!d.floors;                           // (blocks built over the land, stood on: floors.js)
      SWIM_SPRINT = !!d.swim_sprint;
    } else if (d.type === "tick") { if (typeof TitleScene === "undefined" || !TitleScene.on) onTick(d); }   // (the first screen's island has its own hour: a world watched before the island began lit it with its own, a frame in two)
    else if (d.type === "event") onEvent(d.ev);
    else if (d.type === "resync") { for (const b of blocks.values()) b.at = -1e9; }   // we missed events (too many at once): ask for our land again
    else if (d.type === "reply") {
      if (d.rows) onRegion(d);
      else if (d.agents) { agents = d.agents; drawAgents(); if (document.body.classList.contains("tab")) drawWho(); }
      else if (d.tick_ms_p50 !== undefined) { metrics = d; }      // (the debug screen reads them: panels.js)
      else if (d.who) accountNamed(d.name);                  // (account.js)
    }
  };
  spec.onclose = () => setTimeout(connectSpec, 1000);
}
const sendSpec = (o) => spec && spec.readyState === 1 && spec.send(JSON.stringify({...o, id: ++sid}));
// The tiles of the screen: what is loaded, watched and drawn. Round where you are drawn (near) and round where you
// are (far): the two are a few rows apart, as you stand high or low (a hill's top, a pit). Far from the land that is
// drawn where you are (away: more than APART layers under it or over it, a tunnel forty down, a tower), that land is
// rows away from you and nothing of yours: a corridor forty layers down showed in the middle of a forest twenty tiles
// south of it, and at a hundred the page had let go of the tiles you stood on. There it is round where you are, and
// no more: your own land at its own height from yours (off the screen, its top), the rest of the screen earth, or sky.
// away: on: so now; a: how far gone the other land is (0 to 1, a moment: render.js); y: your own row; shift: rows from
// where you are drawn to the land drawn there, when it is high or low itself (a plateau); sky: over the land, not under;
// t: when it was worked out (not this moment's: nobody plays, the first screen: the camera alone says where)
const away = {on: false, a: 0, y: 0, shift: 0, sky: false, high: false, t: -1e9};
function viewRect(margin) {
  // (THE HD LOOK'S LAND IS THE VIEW: the land it makes tile by tile (HdLook.box, hd.js viewOf: the screen and the view distance), not the flat picture's rows. They were two extents: the box reaches
  //  farther north, and its north rows were asked for only as far land, 3 to 6 s late on new land)
  const hb = typeof HdLook !== "undefined" && HdLook.live && HdLook.box; if (hb) return [hb[0] - margin, hb[1] - margin, hb[2] - hb[0] + 1 + 2 * margin, hb[3] - hb[1] + 1 + 2 * margin];
  const more = typeof Curve === "undefined" ? 0 : Math.min(40, Math.ceil(Curve.over() / TS()));      // (the curved world shows further north: curve.js)
  const w = Math.ceil(W / TS()) + margin * 2, h = Math.ceil(H / TS()) + margin * 2 + more, x = Math.floor(cam.x - w / 2), y = Math.floor(cam.y - (h - more) / 2) - more;
  if (!me || performance.now() - away.t > 250) return [x, y, w, h];
  const near = Math.floor(cam.y + away.shift - (h - more) / 2) - more, far = Math.floor(away.y - (h - more) / 2) - more, top = Math.min(near, far);
  return away.a >= 1 ? [x, far, w, h] : [x, top, w, Math.max(near, far) + h - top];
}
setInterval(() => {
  if (!spec || spec.readyState !== 1 || (typeof TitleScene !== "undefined" && TitleScene.on)) return;     // (the first screen's island is the page's own: title_scene.js)
  const [x, y, w, h0] = viewRect(6), h = h0 + 6;   // (+6 rows south: high ground there is drawn up into view, with what's on it)
  { // who is there is told of as far as the HD look shows land (HdLook.reach: a hill 26 rows north, past the top-down screen's rows), 4 tiles more: in before it is in view
    const r0 = typeof HdLook !== "undefined" && HdLook.live && HdLook.reach, r = r0 && r0[0] < x + w && r0[2] > x && r0[1] < y + h && r0[3] > y ? r0 : null, ex =   // (a reach of another place, before a teleport, is not joined to this one: the server cut the two to 200 tiles, this place outside: no far land for it, views.py far_near)
      r ? Math.min(x, r[0] - 4) : x, ey = r ? Math.min(y, r[1] - 4) : y;
    const ew = (r ? Math.max(x + w, r[2] + 5) : x + w) - ex, eh = (r ? Math.max(y + h, r[3] + 5) : y + h) - ey, key = [Math.round(ex / 4), Math.round(ey / 4), ew, eh].join();
    if (key !== lastWatch) { lastWatch = key; sendSpec({op: "watch", x: ex, y: ey, w: ew, h: eh}); } }
  const now = performance.now();
  for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++)
    for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++) {
      const k = bkey(bx, by), b = blocks.get(k);
      const stale = b && now - b.at > 30000;
      if ((!b || stale) && !(requested.get(k) > now - 3000)) { requested.set(k, now); if (b) b.at = now; sendSpec({op: "region", x: bx * B, y: by * B, w: B, h: B}); }
    }
  // THE FAR LAND the HD look draws to its horizon (HdLook.far: its patches, 40 tiles past its box): asked for too, nearest first, four blocks a tenth of a second. (It was the top-down
  // screen's blocks only: past them the far land was not known, drawn as a flat sea, and the sky's line over a gap of the backdrop's flat colours: "a flat blue mass", seen from a mountain)
  const f = typeof HdLook !== "undefined" && HdLook.live && HdLook.far, fb = f && [f[0], f[1], f[2], f[3]].map((v) => Math.floor(v / B));
  if (fb) { const cx = Math.floor(cam.x / B), cy = Math.floor(cam.y / B), far = [];
    for (let by = fb[1]; by <= fb[3]; by++) for (let bx = fb[0]; bx <= fb[2]; bx++) { const k = bkey(bx, by), b = blocks.get(k); if ((!b || now - b.at > 30000) && !(Math.abs(requested.get(k)) > now - 3000)) far.push([Math.abs(bx - cx) + Math.abs(by - cy), bx, by]); }
    for (const [, bx, by] of far.sort((a, b) => a[0] - b[0]).slice(0, 4)) { const k = bkey(bx, by), b = blocks.get(k); requested.set(k, -now); if (b) b.at = now; sendSpec({op: "region", x: bx * B, y: by * B, w: B, h: B, far: true}); } }   // (far: land not made yet is made off the server's tick, and asked for again 3 s on: views.py far_ready)
  // (A FAR ASK IS NOT A NEAR ONE: its time is kept as minus itself, and the land on the screen above asks for its block again at once. Land not made yet is answered "later" to a far ask
  //  (nothing comes), and the block then waited the 3 s for the land on the screen too: sprinting toward new land, or zooming out, a block-wide strip of the screen's side was the backdrop's
  //  flat colours for up to 3 s, growing as you ran in: "part of the world disappears", 5400 px of a 600 x 400 picture, test_e2e_holes.py)
  // land left well behind is forgotten, with its pictures (it comes again if you go back): a long walk kept it all
  const bx0 = Math.min(Math.floor(x / B) - 1, fb ? fb[0] : 1e9), bx1 = Math.max(Math.floor((x + w) / B) + 1, fb ? fb[2] : -1e9), by0 = Math.min(Math.floor(y / B) - 1, fb ? fb[1] : 1e9), by1 = Math.max(Math.floor((y + h) / B) + 1, fb ? fb[3] : -1e9);
  for (const [k, b] of blocks) if (b.bx < bx0 || b.bx > bx1 || b.by < by0 || b.by > by1) blocks.delete(k);
}, 100);
setInterval(() => { sendSpec({op: "agents"}); sendSpec({op: "metrics"}); }, 1500);

let pred = null;             // {x, y, until}: the tile you stopped on, until the server is there too (walk.js)
const recentlyGone = new Map();   // entities that just left the view (a death event may arrive after the tick)
let groundItems = [], mailAt = new Set(), fireAt = [], troughAt = new Set();
function onTick(d) {
  clock = d;
  groundItems = d.items || [];
  mailAt = new Set((d.mail || []).map(([x, y]) => x + "," + y));
  troughAt = new Set((d.troughs || []).map(([x, y]) => x + "," + y));
  fireAt = (d.fires || []).map(([x, y]) => ({x, y}));
  $("clock").textContent = d.time.replace("(night)", "· night");
  if (document.body.classList.contains("tab")) whoTick();      // (who.js: the hour, on what Tab shows)
  const seen = new Set(), now = performance.now();
  for (const e of d.entities) {
    const key = e.kind + e.id; seen.add(key);
    let p = ents.get(key);
    if (!p) { p = {x: e.x, y: e.y, tx: e.x, ty: e.y, fx: 0, fy: 1, moved: 0}; ents.set(key, p); }
    if (!p.zAt || p.zAt.x !== e.x || p.zAt.y !== e.y || p.zAt.z !== e.z) { p.zWas = p.zAt; p.zAt = {x: e.x, y: e.y, z: e.z}; }     // (its height, and the tile before: floors.js)
    p.e = e;
    if (e.kind === "agent" && e.id === myId && myTick(p, e, now)) continue;   // (your own walk is yours: walk.js)
    if (p.tx !== e.x || p.ty !== e.y) {
      const dx = Math.sign(e.x - p.tx), dy = Math.sign(e.y - p.ty);
      // animal sheets only walk sideways: going up or down they keep facing the way they last went
      // a body faces one of the four ways, never a diagonal: a move along both axes (a corner turned between two ticks) faces the longer one; far (a teleport) it keeps its facing.
      // (It faced (1, -1) after a teleport north-east: the tile it faced, keyboard.js facingTile, was a corner off, X's orange box on a floor it does not face)
      const ax = Math.abs(e.x - p.tx), ay = Math.abs(e.y - p.ty);
      if (ANIMALS[e.kind]) { if (dx) BodyPlace.face(p, dx, p.fy); } else if (dx && dy) { if (ax + ay <= 3) BodyPlace.face(p, ax >= ay ? dx : 0, ax >= ay ? 0 : dy); } else if (dx || dy) BodyPlace.face(p, dx, dy);
      const gap = (now - p.moved) / 1000;               // how fast the world is moving it: tiles a second, over its last two places (render.js)
      p.pace = e.run ? RULES.pace.sprint : gap < 1 ? Math.min(RULES.pace.sprint, Math.hypot(e.x - p.tx, e.y - p.ty) / Math.max(gap, .05)) : 0;
      p.moved = now; p.tx = e.x; p.ty = e.y;
      if (Math.abs(p.x - e.x) + Math.abs(p.y - e.y) > 4) { p.x = e.x; p.y = e.y; }
    }
    if (e.kind === "agent" && e.doing) BodyPlace.faceAction(p, e.dir, e.tid);   // (what it is doing: turned to it, body_place.js)
  }
  for (const [k, p] of ents) if (!seen.has(k)) {
    if (k === "agent" + myId) { refresh(); continue; }       // you're never out of your own view: you just moved far (a level)
    recentlyGone.set(k, {p, t: now}); ents.delete(k);
  }
  for (const [k, g] of recentlyGone) if (now - g.t > 2000) recentlyGone.delete(k);
}
// The sound of a tile changing: what broke, what was placed, what was picked.
function tileSound(old, now, e) {
  if (old === now) return;
  const {x, y, cause} = e, oldBlock = !GROUND.has(old);
  if (cause === "pick") return sfx("rustle", x, y);
  if (cause === "dig") {
    if (old === "T" || old === "U") return;                                   // felling has its own creak and thud
    return sfx(oldBlock ? BREAK[material(old)] : "dig", x, y);
  }
  if (cause === "place") return sfxPlaced(e.block, e.ground, x, y);        // each kind of thing has its own sound
  if (cause === "burnt") return sfx("crackle", x, y);
  if (cause === "flood") return sfx("flood", x, y);
  if (cause === "grew") return sfx("grow", x, y, 5);                        // only what grows right beside you
}
function onEvent(e) {
  const t = performance.now() / 1000;
  if (e.type === "tile") {
    const g = CHAR[e.ground], blk = e.block === "none" ? g : CHAR[e.block], old = combAt(e.x, e.y);
    if (g && blk) setTile(e.x, e.y, blk, g, e.by, e.col === undefined ? null : colIn(e.col), e.mat === undefined ? null : e.mat);
    if (old && blk) tileSound(old, blk, e);
    return;
  }
  if (e.type === "floor") {                         // (a block built or taken, or what stands on it: floors.js)
    Floors.set(e.x, e.y, e.z, e.kind, e.thing);
    if (e.cause === "dig") sfx("snap", e.x, e.y); else sfxPlaced(CH[e.thing] || "", "floor", e.x, e.y);
    return;
  }
  if (e.type === "water") { Flow.set(e.cells); return; }        // (water that runs, a step of it: flow.js)
  if (e.type === "roof") { Floors.set(e.x, e.y, floorAt(e.x, e.y) + Floors.STOREY, e.on ? "roof" : null); sfx(e.on ? "plant" : "rustle", e.x, e.y); return; }     // (a server from before blocks)
  if (e.type === "say" || e.type === "shout") { const em = emoteFor(e.text); if (em) setTimeout(() => emote(e.from, em), 2500); }
  if (e.type === "give") { emote(e.to, "love"); emote(e.from, "happy"); }
  if (e.type === "craft") emote(e.name, "star");
  if (e.type === "attack") emote(e.target, "bang");
  if (e.type === "death") emote(e.name, "skull");
  if (e.type === "say" || e.type === "shout") {
    bubbles.push({name: e.from, text: e.text, t, shout: e.type === "shout"});      // (drawn, piled and let go by bubbles.js)
  }
  if (e.type === "attack") {
    noteFight(e);
    const who = [...ents.values()].find((q) => q.e && q.e.kind === "agent" && q.e.name === e.attacker);
    if (who && e.attacker !== me) who.swing = {t0: performance.now(), with: e.weapon !== "fists" ? e.weapon : null};
    const tgt = [...ents.values()].find((q) => q.e && (q.e.name === e.target || `${q.e.kind}#${q.e.id}` === e.target));
    const tx = tgt ? tgt.x : e.x, ty = tgt ? tgt.y : e.y;
    if (tgt) flashes.set(tgt.e.kind === "agent" ? "agent" + tgt.e.id : tgt.e.kind + tgt.e.id, performance.now());
    if (tgt && ANIMALS[tgt.e.kind]) {             // a hit animal: a startled "!" and a few feathers or tufts of its own colour
      emote(tgt.e.kind + tgt.e.id, "bang");
      const fw = ANIMALS[tgt.e.kind].fw;
      debris(tgt.x, tgt.y - .2, [animalSheet(tgt.e.kind, tgt.e.id), 0, 0, fw, fw], 6, {});
      sfx(tgt.e.kind === "chicken" || tgt.e.kind === "chick" ? "squawk" : animalVoice(tgt.e.kind), tx, ty);
    }
    if (WILD[String(e.attacker).slice(2)]) sfx("punch", e.x, e.y);
    burst(tx, ty, "hit", 6, {dy: -.4}); sfx("hit", tx, ty); if (e.target === me) sfx("hurt"); floats.push({x: tx, y: ty, text: "-" + hearts(e.damage), heart: true, color: "#ff8a7a", t});      // (in hearts, whoever is hit)
  }
  if (e.type === "jump" && e.name !== me && !e.step) {   // somebody hops (on the level: jump.js HOP; up a step, its own arc shows as it goes: a hop where it stood first, then the step's, was one jump drawn as two)
    const q = [...ents.values()].find((q) => q.e && q.e.kind === "agent" && q.e.name === e.name);
    if (q) BodyPlace.state(q).hop = performance.now();
  }
  if (e.type === "fall") {                          // a fall that hurt: shown as they land (jump.js), or now if they are not seen falling
    const q = [...ents.values()].find((q) => q.e && q.e.kind === "agent" && q.e.name === e.name);
    if (q) { BodyPlace.state(q).hurt = e.damage; setTimeout(() => fallHurts(q, performance.now(), e.name === me), 700); }   // (if nothing landed by then)
  }
  if (e.type === "death" && e.name === me) {
    sfx("die");
    showDeath(e);                                     // (death.js)
  }
  if (e.type === "creature_died" || e.type === "fade") {   // it flashes, lifts and fades away in a puff of smoke
    const key = e.kind + e.id, p = ents.get(key) || (recentlyGone.get(key) || {}).p;
    if (p && p.e) dyingPoof(p, performance.now()); else smoke(e.x, e.y, 8);
    if (e.drops) dropLoot(e.x, e.y, e.drops, performance.now());
    ents.delete(key);
    sfx("poof", e.x, e.y);
  }
  if (e.type === "death") { smoke(e.x, e.y, 10); sfx("poof", e.x, e.y); dropLoot(e.x, e.y, e.dropped, performance.now()); }
  const warn = e.type === "windup" && {tusker: "rustle", pincer: "click", strawman: "creak", wisp: "gloom", wyrm: "water", gustling: "whoosh", grumblestump: "creak", snapbloom: "rustle", hob: "crackle", mossback: "boss_groan"}[e.kind];
  if (warn) sfx(warn, e.x, e.y);                       // a wild creature warns (the wisp's call is a sigh)
  if (e.type === "boss") bossEvent(e);                 // (boss.js)
  if (e.type === "wear") sfx("rustle", e.x, e.y);      // someone puts something on, or takes it off
  if (e.type === "enrage") { burst(e.x, e.y, "dust", 8, {up: 1.3, spread: 2.6, g: 3}); burst(e.x, e.y, "rage", 12, {up: 4.5, spread: 4.5, g: 9, life: .6, dy: -.3}); sfx("thud", e.x, e.y); flashes.set(e.kind + e.id, performance.now()); }   // a tusker that was hit stamps: it is angry now
  wildEvent(e);                                                                           // what the wild ones do: world_decor.js
  if (e.type === "bonk") { burst(e.x, e.y, "dust", 8, {up: 1, spread: 2, g: 3}); sfx("thud", e.x, e.y); }          // a tusker rams something
  if (e.type === "xp") spawnOrbs(e);
  if (e.type === "pick_up" && e.magnet) magnetItems(e);
  else if (e.type === "pick_up") { burst(e.x, e.y, "spark", 6, {dy: -.5, g: 3}); sfx("collect", e.x, e.y); }
  if (e.type === "chest") { chestOpen.set(e.x + "," + e.y, performance.now()); sfx("chest", e.x, e.y); }
  if (e.type === "milk") { burst(e.x, e.y, "spark", 4, {dy: -.2, g: 5}); emote(e.name, "happy"); sfx("milk", e.x, e.y); }
  if (e.type === "love") { emote(e.by, "love"); sfx(animalVoice(e.kind), e.x, e.y); sfx("love", e.x, e.y); }
  if (e.type === "lay") { burst(e.x, e.y, "dust", 5, {up: 1, spread: 1.5, g: 3}); sfx("lay", e.x, e.y); }
  if (e.type === "ignite") { sfx("whoosh", e.x, e.y); sfx("crackle", e.x, e.y); }
  if (e.type === "fill") { burst(e.x, e.y, "water", 8, {up: 1.5, spread: 1.5}); sfx("fill", e.x, e.y); }
  if (e.type === "trough") { burst(e.x, e.y, "food", 3, {dy: -.4, g: 3}); sfx(animalVoice(e.kind), e.x, e.y); }
  if (e.type === "picnic") { emote(e.name, "love"); burst(e.x, e.y, "food", 6, {dy: -.6, g: 3}); }
  if (e.type === "mail" && e.to === me && e.from !== me) sfx("mail");
  if (e.type === "shout" && e.from !== me) sfx("shout", e.x, e.y, 30);
  if (e.type === "say" || e.type === "shout") babble(e.from, e.text, e.x, e.y, e.type === "shout", e.bot);      // (babble.js: a run of syllables, yours too; an AI player's in its robot voice)
  if (e.type === "give" && e.to === me) sfx("give");
  if ((e.type === "join" || e.type === "leave") && e.name !== me) sfx(e.type);
  if (e.type === "sign") sfx("write", e.x, e.y);
  if (e.type === "mail" && e.to === me && e.from !== me) toast(`**${e.from}** left you a letter\nin the mailbox at ${e.x}, ${e.y}`);
  if (e.type === "mail_opened" && e.owner === me && e.by !== me) toast(`**${e.by}** opened your mailbox\nand took ${e.n} letter${e.n > 1 ? "s" : ""}`, true);
  if (e.type === "board" || e.type === "moor") { burst(e.x, e.y, "water", 8, {up: 1.5, spread: 2}); sfx("water", e.x, e.y); }
  if (e.type === "hatch") { burst(e.x, e.y, "spark", 8, {dy: -.3, g: 4}); sfx("hatch", e.x, e.y); }
  if (e.type === "born") { burst(e.x, e.y, "food", 8, {dy: -.5, g: 3}); sfx("love", e.x, e.y); }
  if (e.type === "craft") { burst(e.x, e.y, "spark", 10, {dy: -.6, g: 4}); sfx("craft", e.x, e.y); }
  if (e.type === "drop") dropLoot(e.x, e.y, e.items, performance.now(), e.ox, e.oy);      // (let go of: it hops from the hands down to where it lies, loot.js)
  if (["xp", "pick_up", "drop", "chest", "milk", "love", "lay", "fill", "picnic", "trough"].includes(e.type)) return;
  if (e.type === "attack") return;                     // hits show on screen; the chat only tells of deaths
  let text;
  switch (e.type) {
    case "say": text = e.text; break;
    case "shout": text = e.text; break;
    case "death": text = `**${e.name}** died (${e.cause})`; break;
    case "give": if (e.from !== me && e.to !== me) return; text = `**${e.from}** gave **${e.to}** ${fmt(e.items)}`; break;
    case "join": text = `**${e.name}** ${e.new ? "washed ashore" : "woke up"}`; break;
    case "leave": text = `**${e.name}** fell asleep`; break;
    case "named": text = `**${e.by}** named a ${e.kind} **${e.name}**`; break;

    default: return;
  }
  chatLine(text, e.type === "say" ? "" : e.type === "shout" ? "shout" : e.type === "death" ? "bad" : "sys",
    e.type === "say" || e.type === "shout" ? e.from : null);
}
