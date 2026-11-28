// Your own walk. Your screen walks you itself: at the stride's exact speed, a tile at a time, looking at the land as
// the server does (intent.js: walkable), and never waits for an answer, which may come late (a phone, a slow line:
// waiting made you stop at every tile). The server is told the way and makes it after you: `walk` says the direction
// (it keeps going, as you do) and `from`, the tile you turned at; `stop` says `at`, the tile you stopped on. It makes
// those tiles first, in order, at the same stride (sim/movement.py: follow), so it ends where you are. Each has a
// number, and the server says the last it reached (`vn` on your entity): `trail` is the ones it still has to make.
// Getting far ahead of it (LEAD tiles along the way) you slow down, then wait: you're never more than a few tiles
// from where the world has you. Where it couldn't follow, you go back to where it has you.

let walking = null;          // {dir, run, lane, at}: lane: the row (column) you walk along; at: the tile you turn at, until you're on it
let walkN = 0;               // walks started: a late answer counts only for the last one (syncWalk)
const TAP_S = .1;            // the time a tap let go before any frame walks you: half a stride, into the next tile
let silkUntil = 0;           // pinned in a redknee's silk until then (performance.now; state.js): no step, as the server has it (sim/redknee.py)
const trail = [];            // {x, y, n}: tiles you turned or stopped at that the server hasn't made yet
let trailN = 0, srv = null;  // srv: the server's last step for you {x0, y0, x, y, t, ms} (from, to, when, how long its steps take)
const LEAD = [2, 4];         // tiles ahead of the server: from the first you slow down, at the second you wait for it

function mark(x, y) { const n = ++trailN; trail.push({x, y, n}); return [x, y, n]; }

// JUMP (options.js "jump"): AUTO-JUMP (options.js "autojump", on unless turned off: "Jump looks unnatural. Add
// automatic jump by default"): walking into a step with room over it (both cells over it empty, cells.js landAt) you
// jump up it as you come to it, at the walk's pace, no stop, no key; the server's walk is told (`jump`) and takes it
// after you. Off, walking into a step stops you ("player size should be 2 blocks ... also add a key to jump"); the key
// hops you up onto it. Walking, it is the step ahead of the tile you are on: your screen may walk onto it (`spring`,
// here) and the server's walk takes it after you (sim/movement.py _tool_jump `at`). Standing, the step you face (or
// the way out's next step: wayshow.js), now. On the level, a hop where you stand, nothing more (jump.js HOP).
const spring = new Map();    // "x,y" -> until: the steps your screen may hop onto (several: J pressed again, a step on, before the first is reached)
const autoJump = () => !!opt("autojump");
const springs = (x, y) => (!!walking && autoJump()) || performance.now() < (spring.get(x + "," + y) || 0);
// -> the step a jump would take you up now {x, y, d, way: it is the way out's}, or null (keyboard.js: the corner's "Jump")
function stepAhead() {
  const p = ents.get("agent" + myId); if (!p || !me || !meObs || Build.on) return null;
  const w = WayShow.offer(), wd = !walking && w && w.key === "jump" ? WayShow.cur.path[1].d : null;
  const d = walking ? walking.dir : wd || Object.keys(DIRV).find((k) => DIRV[k][0] === p.fx && DIRV[k][1] === p.fy);
  if (!d) return null;
  const x = p.tx + DIRV[d][0], y = p.ty + DIRV[d][1], h = myZ(p.tx, p.ty);
  return solidAt(x, y, h + 1) && landAt(h, x, y, p.tx, p.ty) === h + 1 ? {x, y, d, way: !!wd} : null;
}
function jumpKey() {
  const p = ents.get("agent" + myId); if (!p || !me || !meObs || Build.on) return;
  const s = stepAhead(), now = performance.now();
  if (jumpGoing || Leap.on()) return;            // (a jump on its way: J pressed again does not cut it short, as a new action would)
  if (Leap.gliding()) { BodyPlace.state(p).jumpNext = true; return; }   // (just down off a tile's middle, going to it: the jump once there, leap.js after)
  const low = s && !walking;                     // (standing, facing a step: up onto it with a hop: a tunnel or a shaft has no room for a jump through the air)
  if (Leap.can(p) && !low) { Leap.start(p, now, null); return; }   // a real jump (leap.js)
  if (!s) { const st = BodyPlace.state(p); if (now - st.hop < HOP.ms) return; st.hop = now; rpc("act", {tool: "jump", args: {}}); return; }      // (nothing to jump onto: a hop on the spot; in the air, Space again does not start it over)
  for (const [k, t] of spring) if (t < now) spring.delete(k);
  spring.set(s.x + "," + s.y, now + RULES.spring_s * 1000);
  if (s.way) turn(s.d);
  jumpGoing = !walking;
  rpc("act", {tool: "jump", args: walking ? {at: [s.x, s.y]} : {dir: s.d, at: [s.x, s.y], jump: autoJump()}}).then(() => { jumpGoing = false; if (walking === null && [...keys].some((k) => KEYDIR[k])) syncWalk(); });   // (a walk the server ended at the step: on again, up it)
}
let jumpGoing = false;

// Held keys (or the stick): one message when the direction or sprint changes, one when you let go.
function syncWalk() {
  if (Leap.on() || Leap.gliding()) return;       // (in the air: the keys steer, leap.js; the walk goes on when you land)
  const k = [...keys].reverse().find((k) => KEYDIR[k]);
  const want = k && me ? {dir: KEYDIR[k], run: sprinting()} : null;
  if (want && walking && want.dir === walking.dir && want.run === walking.run) return;
  if (!want && !walking) return;
  const prev = walking, p = ents.get("agent" + myId), now = performance.now();
  // (let go before a frame walked you: a tap on a page whose frames are slow, its down and its up both handled between two
  // frames, was a stop where you stood. The walk goes on for that one frame, as if held across it, and lets go after it)
  if (!want && !prev.walked && p && p.walking) { prev.letGo = true; return; }
  if (want) want.t0 = prev && p && p.walking ? prev.t0 : now;   // (when you set off: a turn walks on)
  walking = want;
  if (!want) {                                   // let go: you finish the tile you're entering, and the server comes to it
    const args = {};
    if (p && p.walking) {
      p.walking = false;
      pred = {x: p.tx, y: p.ty, until: now + 2000};
      args.at = mark(p.tx, p.ty); if (prev.run) args.run = true; if (autoJump()) args.jump = true;   // (the way there may go up a step: jumped)
    }
    rpc("act", {tool: "stop", args});
    return;
  }
  const [dx, dy] = DIRV[want.dir], args = want.run ? {dir: want.dir, run: true, push: true} : {dir: want.dir, push: true};   // (push: held against a step it waits for the jump key: sim/movement.py walk)
  if (autoJump()) args.jump = true;              // (jump: up every step it comes to, as your screen does)
  args.ledge = true;                             // (off a ledge as high as a fall your screen goes through the air itself, leap.js dropDue: the world's walk waits at its edge, sim/movement.py)
  if (p) {
    const [ox, oy] = prev && p.walking ? DIRV[prev.dir] : [0, 0];
    const line = (ox || oy) && !(ox * dy - oy * dx), back = line && (ox !== dx || oy !== dy);
    // the same line (faster, slower, back the way you came): from where you are. (Back up a drop you were falling
    // down: no, that step is made.)
    if (line && !(back && !prev.at && !walkable(p.tx - ox, p.ty - oy, p.tx, p.ty))) { want.lane = prev.lane; want.at = prev.at; }
    else {                                       // a turn: at the tile you're entering, which you finish first (as the server will)
      want.lane = dx ? p.ty : p.tx; want.at = {x: p.tx, y: p.ty};
      if (ox || oy) args.from = mark(p.tx, p.ty);
      // ...but let go and straight back the way you came: that tile isn't made after all, by you or the server
      // (`cut`), when it is on this same line (not still round a corner)
      const bx = Math.sign(p.x - p.tx), by = Math.sign(p.y - p.ty);
      if (pred && bx === dx && by === dy && trail.length === 1 && srv && (dx ? srv.y : srv.x) === want.lane) { want.at = null; args.cut = true; trail.length = 0; }
    }
    BodyPlace.face(p, dx, dy); p.walking = true; p.running = want.run; p.moved = now;
  }
  myAction = null; pred = null;
  const mine = want, n = ++walkN, from = p ? p.tx + "," + p.ty : "";
  rpc("act", {tool: "walk", args}).then((r) => {
    const wall = r.ok && r.result.stopped === "blocked";
    // replaced by a newer walk: that one says. By letting go (a stop): a tap at a wall that was let go before the server
    // answered (a slow link, a short tap) is still a turn to the wall (else the way out stays shown and nothing is aimed)
    if (walking !== mine && !(walking === null && wall && n === walkN)) return;
    if (walking === mine) { walking = null; if (p) p.walking = false; }    // it ended (a wall, a fall that hurt): the next tick says where you are
    if (wall) { const q = ents.get("agent" + myId); if (q) { BodyPlace.face(q, dx, dy); if (q.tx + "," + q.ty === from) WayShow.mine(); } }
    // (you turned to a wall where you stand: you are at work on it: the shown way out is put away, as at a key of your own: while it is shown nothing you face is offered (standing two seconds in a cave you can walk out of, then facing a wall: no bracket, no key, for good)
  });
}

// Where the server has you, between its ticks: it steps a tile at once, then waits a stride; you glide over that time.
function srvAt(now) {
  const k = Math.min(1, (now - srv.t) / srv.ms);
  return {x: srv.x0 + (srv.x - srv.x0) * k, y: srv.y0 + (srv.y - srv.y0) * k};
}
// How far ahead of it you are, along the way you came (it may still be round a corner). Under 0: it is ahead of you.
function leadOf(p, now) {
  if (!srv) return 0;
  const [wx, wy] = DIRV[walking.dir], at = walking.at;
  let q = srvAt(now), d = 0;
  for (const c of trail) {
    if (at && c.x === at.x && c.y === at.y) break;             // (the corner you're still on your way to)
    d += Math.abs(c.x - q.x) + Math.abs(c.y - q.y); q = c;
  }
  const ax = p.x - q.x, ay = p.y - q.y;
  if (at) return d + Math.abs(ax) + Math.abs(ay);
  const al = ax * wx + ay * wy, off = Math.abs(ax * wy) + Math.abs(ay * wx);
  return d || off > .01 ? d + Math.abs(al) + off : al;
}
// where nobody sprints: in a boat (and, on a server from before the sprint in the water, in the water)
// tiles a second a person goes from the tile (x, y): 5 walking, 10 at a sprint (`run`: yours, the walk's; another's, the world's word);
// in the water the server's SWIM_PACE times slower (half), and EAT_PACE times slower while you eat (half again: the two add up). The one
// pace of a person, walking under a key held (walkOn) or gliding to where the world has them (render.js): the glide went at the pace
// on land, a swimmer let go of the key twice as fast into place, others swam at a walk ("the swimming ... goes faster when player releases the key")
const speedAt = (x, y, p, run = !!(walking && walking.run)) => { const t = tile(x, y), mine = !!p.e && p.e.kind === "agent" && p.e.id === myId;
  return RULES.pace[run && !onWater(x, y, p) ? "sprint" : "walk"] / (t && wet(t[1]) && !(p.e && p.e.sail) ? SWIM_PACE : 1) / (mine && eating() ? EAT_PACE : 1); };
const onWater = (x, y, p) => { const t = tile(x, y); return (!SWIM_SPRINT && !!t && wet(t[1])) || !!(p.e && p.e.sail); };

// A frame of your walk (render.js). A turn first finishes the tile you were walking into, in a straight line, then
// turns: no diagonal slide. Each step as the server paces it, in its 0.1 s ticks: a stride of 1 tick (sprinting) or
// 2 (walking), twice that in the water. Up a layer the server takes a tick more (SLOPE_UP: hard going); you jump up
// it through the air without slowing (leap.js: "it stops the velocity and does an up-block animation"), down one you
// drop at the walk's pace (jump.js). It catches up when you stop, and on a long climb you slow down smoothly, by how far ahead of it you are (LEAD).
function walkOn(p, dt, now) {
  // (none of a frame's time from before you set off: a slow page's first frame walks the time the key is down for, not its whole
  // length, so the screen never walks longer than the key is held: a tap is a tile at any frame's length. A tap let go before
  // any frame walks one frame of TAP_S at the most: into the next tile, never past it)
  dt = Math.min(dt, walking.letGo ? TAP_S : Math.max(0, now - walking.t0) / 1000);
  if (dt <= 1e-5) return;                                    // (no time yet: no frame walks you, and a key let go now still gets its one)
  if (performance.now() < silkUntil) return;                 // pinned: the server holds you there (your `ready`), and so does your screen
  const [wx, wy] = DIRV[walking.dir], s = wx || wy, side = wx ? "y" : "x", along = wx ? "x" : "y", lead = leadOf(p, now);
  let t = dt * (lead < -1 ? 1.25 : lead <= LEAD[0] ? 1 : Math.max(0, (LEAD[1] - lead) / (LEAD[1] - LEAD[0])));   // the time you walk in
  for (let i = 0; i < 12 && t > 1e-5; i++) {   // (a tile a turn: a half-second frame's sprint is 5, and the lane first)
    const off = walking.lane - p[side];
    if (Math.abs(off) > 1e-3) {
      const v = speedAt(Math.round(p.x), Math.round(p.y), p), go = Math.min(Math.abs(off), v * t);
      p[side] += Math.sign(off) * go; t -= go / v; p.moved = now;
      continue;
    }
    p[side] = walking.lane; walking.at = null;
    const a0 = s > 0 ? Math.floor(p[along] + 1e-6) : Math.ceil(p[along] - 1e-6);      // the tile you're leaving, and the next
    const fx = wx ? a0 : walking.lane, fy = wx ? walking.lane : a0, nx = fx + wx, ny = fy + wy;
    if (autoJump() && Leap.due(p, walking)) { Leap.start(p, now, null, true); Leap.frame(p, t, now); return; }   // a step ahead: a jump through the air, at the walk's speed (leap.js), this frame's time in it
    if (Leap.dropDue(p, walking, t)) { Leap.start(p, now, null, false, 0); Leap.frame(p, t, now); return; }   // over a ledge: falling at the walk's speed (leap.js)
    if (!walkable(nx, ny, fx, fy)) { p[along] -= s * Math.min((p[along] - a0) * s, 10 * t); p.tx = fx; p.ty = fy; break; }   // a wall: you stay
    const v = Climb.pace(fx, fy, myZ(fx, fy), nx, ny) || speedAt(fx, fy, p);      // (up or down a ladder: rung by rung, climbing.js)
    const go = Math.min((a0 + s - p[along]) * s, v * t, autoJump() ? Math.max(0, Leap.room(p, walking)) + v / 60 + 1e-6 : Infinity);   // (no further past where the auto-jump is due than a 60th of a second's walk, as at 60 fps: leap.js room)
    p[along] += s * go; t -= go / v; p.tx = nx; p.ty = ny; p.moved = now;
  }
  walking.walked = true;
  if (walking.letGo) { walking.letGo = false; syncWalk(); }   // (let go before this frame: now, at the tile it is entering)
}

// A tick's word on where you are (state.js). -> true: you're on your own way, the server coming after you.
function myTick(p, e, now) {
  if (!srv || srv.x !== e.x || srv.y !== e.y) {
    const step = srv && Math.abs(e.x - srv.x) + Math.abs(e.y - srv.y) === 1;
    srv = {x0: step ? srv.x : e.x, y0: step ? srv.y : e.y, x: e.x, y: e.y, t: now, ms: step && now - srv.t < 350 ? Math.max(100, now - srv.t) : 150};
  }
  while (trail.length && trail[0].n <= (e.vn || 0)) trail.shift();
  if (pred && (!trail.length || now > pred.until)) { pred = null; trail.length = 0; }     // it's where you stopped (or never will be)
  if (!walking || !p.walking) return !!pred;
  const lane = DIRV[walking.dir][0] ? e.y : e.x;
  if (Math.abs(p.x - e.x) + Math.abs(p.y - e.y) > LEAD[1] + 2) {                           // moved away (woken elsewhere), or it lost you: be where it has you
    p.x = p.tx = e.x; p.y = p.ty = e.y; walking.lane = lane; walking.at = null; trail.length = 0;
  } else if (!trail.length && !walking.at && lane !== walking.lane) walking.lane = lane;   // it couldn't follow you round the corner: walk where it does
  return true;
}
