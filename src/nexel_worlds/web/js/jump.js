// Up or down a layer (or several, down): a hop, for a person or a creature alike (sim/bodies.py: one way to stand on
// the land). Between two tiles a body is placed on the straight line between their heights (relief.js liftOf: the
// camera and the name over a head follow that line, smoothly). The hop is one arc over that line, from the middle
// of a tile to the middle of the next, as a thrown thing goes: high enough to clear the edge it goes over. Its
// shadow stays on the ground under it (the ground it leaves, until it is over the edge), it holds the pose it took
// off in (no walking on air), and there is dust where it leaves the ground and where it lands.
// A hop takes the time a jump takes (below), not a step's. Seen frame by frame, what must not show
// is a hang: a step and a half long, the body near the top of its arc for most of it.
// And then ("Jump looks unnatural"): it left the ground the moment the step began and landed the moment it ended,
// stiff, in the pose it stood in. Then ("improve the jumping animation") each part has a pose drawn for it (jump_art.js):
// a crouch on the ground it leaves (JUMP.crouch), the push off a px taller, the legs tucked going up, the
// ears a px up as it turns over the top, the legs reaching down as it comes down, a squash with the feet apart where
// it lands and a settle on the way back up (SETTLE, by the clock: the walk goes on meanwhile).
// The pose in the air is told by how fast it goes up or down, not by the time: a thrown thing's arc, a parabola.
// Dust is thrown out low to both sides where it leaves the ground and where it lands, a little more there.

// And then, seen at 60 frames a second ("make the jumping animation smoother and better"; "the Space jump should be as
// high as 1 block and more ... right now it looks like a weird 1/10th block animation"): the hop on the level went 6 px
// up, a tenth of the body's height; up a step the arc was squeezed into the step's 200 ms, 4 px up the screen in a
// frame, then 3 px a frame down in the "apex" pose (the pose turned to "fall" for a frame at the most) and its head 4
// rows lower at once as it landed; down a step it dipped 2 px under the ground and back up. Now a jump is thrown and
// falls by its weight (JUMP.g, as a fall's): a hop goes a block and more up (JUMP.top), a step's jump the same, its top
// JUMP.over over the step's (or the ledge it leaves, going down), and it takes the time that takes (jumpMs: about a
// third of a second up or down a step: the walk waits for it, walk.js; the world takes 0.3 s for a step up at a walk,
// sim/movement.py SLOPE_UP). The ground before it is a short crouch, the landing goes on after it by the clock
// (SETTLE: the squash, then back up), the legs straighten as the feet touch (touch: the standing frame, between the
// reach and the squash), and on a staircase each step lands (dust, a step's sound).

const JUMP = {g: RULES.leap.g, top: RULES.leap.top, over: .25, crouch: 40, off: 30, touch: 25};   // its weight (levels/s2); a hop's top (levels); a step's, over the higher floor; ms crouched before it; ms of the push off; ms of the feet down before landing
const SETTLE = {land: 45, ms: 100};                                       // ms from touching the ground: in the squash, then back up to standing (by the clock: the walk goes on meanwhile)
const STEPDOWN = {from: .35, q: 1.6};                                                // down a step: on the ground until this share of the way, then falling faster and faster to the lower one at its middle
// (and at its end no faster than one level's at a walk: sprinting down a step, or walking down two, the curve went
// 4.7 px down the screen in a 60th of a second as it ended, a jump on the screen. Past that pace, the drop is that much
// the straight line between the two tiles: the px of a frame are its time's, at any frame length)
STEPDOWN.v = STEPDOWN.q / (1 - STEPDOWN.from) * RULES.pace.walk;                    // levels a second at the most
const JPOSE = {crouch: 0, takeoff: 1, rise: 2, apex: 3, fall: 4, land: 5, settle: 6, touch: 7};   // the column of each pose in the jump's rows (ANIM.jump; 7: the standing frame)

// A jump from 0 to d levels up (its top: levels over where it leaves): -> {v: levels/s up as it leaves, air: s in the air, ms: all of it, crouch first}
function jumpPath(d, top) {
  const v = Math.sqrt(2 * JUMP.g * top), air = v / JUMP.g + Math.sqrt(2 * Math.max(0, top - d) / JUMP.g);
  return {v, air, ms: JUMP.crouch + air * 1000, d};
}
const STEPJ = new Map();                 // (d -> its path: worked out once)
const stepPath = (d) => STEPJ.get(d) || STEPJ.set(d, jumpPath(d, Math.max(0, d) + JUMP.over)).get(d);
const HOPJ = jumpPath(0, JUMP.top), HOP = {ms: HOPJ.ms};
// ms a jump up (or down) d levels takes (walk.js: you go no faster over it)
const jumpMs = (d) => stepPath(d).ms;
// At ms from its start (crouching, then in the air): -> [height over where it left (levels), its pose, in the air]. The
// pose by how fast it goes up the screen: over the line the eye follows (lineV levels/s) when it is a step's
function jumpAt(J, ms, lineV) {
  if (ms < JUMP.crouch) return [0, "crouch", false];
  const t = Math.min(J.air, (ms - JUMP.crouch) / 1000), h = t >= J.air ? J.d : J.v * t - JUMP.g * t * t / 2;
  if (t * 1000 < JUMP.off) return [h, "takeoff", true];
  if ((J.air - t) * 1000 < JUMP.touch) return [h, "touch", true];
  const v = J.v - JUMP.g * t - lineV, v0 = J.v - lineV;
  return [h, v > .4 * v0 ? "rise" : v < -.3 * v0 ? "fall" : "apex", true];
}

const mineWalking = (p) => !!(p.e && p.e.kind === "agent" && p.e.id === myId && walking && p.walking);
// -> null on the level, or {body, ground: levels over the straight line (its feet, its shadow), squash, tuck: in the air, pose, d: levels up, key: the step} (all the jump's solvers say levels; BodyPlace makes the px)
function jumpOf(p) {
  if (Leap.landedOn(p) !== null) return null;                                        // (come down from a jump through the air, off a tile's middle: on that tile, leap.js)
  const [ax, ay, bx, by, la, lb] = Floors.between(p);
  if ((ax === bx && ay === by) || la === lb || Climb.onLadder(ax, ay, la, bx, by, lb)) return null;          // (up or down a ladder: a straight climb)
  const f = ax === bx ? p.y - ay : p.x - ax, d = lb - la;                         // how far across; levels from the first to the second
  const fwd = (ax === bx ? p.ty - p.y || p.fy : p.tx - p.x || p.fx) >= 0;        // from the first to the second?
  const g = fwd ? f : 1 - f, D = fwd ? d : -d, line = D * g, key = ax + "," + ay + "," + bx + "," + by;   // the way it goes: how far along, levels up by, the straight line
  if (D > 0 && mineWalking(p) && (fwd ? Leap.leapable(ax, ay, la, bx, by) : Leap.leapable(bx, by, lb, ax, ay))) return null;   // (yours walking up to a step you jump: on your own level until you do, leap.js due)
  if (D <= -FALL.from && mineWalking(p) && Leap.ledge(p, ...DIRV[walking.dir])) return null;   // (yours walking to a ledge: on your own level to its edge, then the jump's fall, leap.js dropDue: not drawn as a step down: that jumps 13 px up the screen a frame, then back)
  if (D < 0) {                                                                    // down: no jump, a drop off the edge at the walk's pace
    const k = Math.max(0, (g - STEPDOWN.from) / (1 - STEPDOWN.from)), end = STEPDOWN.q / (1 - STEPDOWN.from);
    const v = -D * RULES.pace[p.running ? "sprint" : "walk"];   // (w: the straight line's share; the curve is steepest at its end)
    const w = Math.min(1, Math.max(0, (end * v - STEPDOWN.v) / ((end - 1) * v))), h = D * ((1 - w) * k ** STEPDOWN.q + w * g);
    return {body: h - line, ground: (g < .5 ? 0 : D) - line, squash: false, tuck: false, pose: null, d: D, key};
  }
  const J = stepPath(D), [h, pose, air] = jumpAt(J, g * J.ms, D * 1000 / J.ms);
  return {body: h - line, ground: (g < .5 ? 0 : D) - line, squash: !air, tuck: air, pose, d: D, key};
}

// A drop of FALL.from layers or more is a fall, not a hop. You walk to the edge on the ground you leave; from the edge
// you come down by your own weight (FALL.g), however long that takes: the step is usually over before you land. Your
// shadow waits on the ground below and grows as you near it, your legs go (two frames of the run, turn about), the
// camera comes down with you (render.js) and the wind rises in your ears (audio.js: fallWind). Where you land: dust
// thrown out to both sides and a thump, heavier the further you fell. A fall that hurt (the server says so: its
// `fall` event, more than 3 layers) lands with the tree's thud, the ground shakes, you flash, bounce, and lose
// what it cost you there, not when you stepped off. (A fall was a hop: one arc at the pace of a step, twelve layers
// in a fifth of a second, the screen jumping with it, and nothing to say it had hurt.)
const FALL = {from: RULES.fall_safe, g: 1000, flail: 70, heavy: 4, shake: [3.5, .32], bounce: [3 / 16, .17]};   // layers; art px/s2; ms a frame; layers from which it lands heavily; px and s of the shake; levels and s of the bounce
let fallQuake = null;                 // {t0, amp}: the ground shaking under you (render.js: fallShake)

// The fall of p now -> null, or {z: its feet, ground: where it lands (levels), air}. BodyPlace asks, once a frame, with
// the body's state (st.fall: {top, land: levels, t0, done}); anyone else reads the place (falling, jumping: below).
const falling = (p) => BodyPlace.of(p).fall, jumping = (p) => BodyPlace.of(p).jump;
function fallOf(p, now, st = BodyPlace.state(p)) {
  // (you in a jump's arc (leap.js): the arc is your height, the ground under it whatever it is. A fall begun under the
  //  arc, over a hole three deep, drew you at the fall's height, the name at it too, while the arc went on: you went
  //  down into the hole, then up the fall's own curve again as the jump ended: "only the nametag jumps")
  //  (and down from it, on your way to the middle of the tile you came down on (leap.js leapAt): come down by a hole's far
  //  wall, 0.45 of a tile off the middle, going back to it read as stepping off the wall's top into the hole: a fall from
  //  the rim, the body up 60 px in a frame and down again)
  if (p.e && p.e.kind === "agent" && p.e.id === myId && (Leap.on() || Leap.gliding())) { st.fall = null; return null; }
  const [ax, ay, bx, by, la, lb] = Floors.between(p), between = (ax !== bx || ay !== by) && la !== lb;
  const fwd = (ax === bx ? p.ty - p.y || p.fy : p.tx - p.x || p.fx) >= 0, down = between && fwd === la > lb;   // going to the lower one?
  const f = ax === bx ? p.y - ay : p.x - ax, u = la > lb ? f : 1 - f;         // how far from the higher tile's middle to the lower one's
  let F = st.fall;
  if (!F) {
    if (!down || Math.abs(la - lb) < FALL.from || Climb.onLadder(ax, ay, la, bx, by, lb)) return null;
    if (mineWalking(p) && Leap.ledge(p, ...DIRV[walking.dir])) return null;   // (yours, walking: on the ground to the edge, and over it the jump's fall, leap.js dropDue. This one began on the tile before the edge, the eye on the ground under it at once: the body 13 px up the screen a frame)
    // (a fall is from the higher tile: already down at the lower one's level (yours, myAt; another's, the world's), going
    //  back to its middle from beside a wall is no fall. Come down by a wide hole's far wall, the body went up to the
    //  rim in a frame and fell again: "jumping above a biiiig hole ... only the nametag jumps")
    const zNow = p.e && p.e.kind === "agent" && p.e.id === myId ? myAt && myAt.z : p.e && p.e.z;
    if (typeof zNow === "number" && zNow <= Math.min(la, lb)) return null;
    F = st.fall = {top: Math.max(la, lb), land: Math.min(la, lb), t0: 0};
  }
  if (F.done) {                                           // down before the step was over: on the ground, to the end of it
    if (!between) { st.fall = null; return null; }
    return {z: F.land, ground: F.land, air: false};
  }
  if (!F.t0) {                                            // to the edge, on the ground it leaves
    if (!down) { st.fall = null; return null; }            // (turned back)
    if (u < .5) return {z: F.top, ground: F.top, air: false};
    F.t0 = now;
  }
  const t = (now - F.t0) / 1000, h = F.top - .5 * FALL.g / RELIEF_STEP * t * t, mine = p.e && p.e.kind === "agent" && p.e.id === myId;
  if (h <= F.land || t > 3) {
    landed(p, F.top - F.land, now, mine, st);
    st.fall = between ? {...F, done: true} : null;
    return st.fall ? {z: F.land, ground: F.land, air: false} : null;
  }
  if (mine) fallWind(Math.min(1, FALL.g * t / 600));       // (louder and higher with its speed)
  return {z: h, ground: F.land, air: true};
}
// The jump key on the level: a hop on the spot (walk.js jumpKey; others: their `jump` event, state.js) -> null, or as jumpOf
function hopOf(p, now, st) {
  if (!(now - st.hop < HOP.ms) || jumpOf(p) || (p.e && swimsAt(p, p.e))) return null;   // (swimming: nothing to push off: no hop, no dust)
  const [h, pose, air] = jumpAt(HOPJ, now - st.hop, 0);
  return {body: h, ground: 0, air: false, squash: !air, tuck: air, pose};
}
// It lands, `layers` further down
function landed(p, layers, now, mine, st) {
  const tx = Math.round(p.x), ty = Math.round(p.y), heavy = layers >= FALL.heavy, hurt = st.hurt;
  if (mine) fallWind(-1);
  for (const side of [-1, 1]) for (let i = 0; i < 3 + Math.min(6, layers); i++)       // dust, thrown out low to both sides
    parts.push({x: p.x + .5 + side * .2, y: p.y + .85 - UP, vx: side * (1.5 + Math.random() * (2 + layers * .25)), vy: -.4 - Math.random() * 1.2,
      g: 5, life: .35 + Math.random() * .3, age: 0, c: PCOL.dust[i % PCOL.dust.length], s: Math.random() < .4 ? 2 : 1});
  smoke(p.x, p.y + .35 - UP, heavy ? 7 : 4, heavy ? .6 : .4);
  sfx(heavy ? "fallthud" : "thud", tx, ty);
  if (heavy || hurt) st.bounce = now;
  if (hurt) fallHurts(p, now, mine);
}
// What a fall cost, shown where it lands (state.js keeps it from the server's `fall` event until then)
function fallHurts(p, now, mine) {
  const st = BodyPlace.state(p), n = st.hurt; if (!n) return;
  st.hurt = 0;
  flashes.set(p.e.kind + p.e.id, now);
  floats.push({x: Math.round(p.x), y: Math.round(p.y), text: "-" + hearts(n), heart: true, color: "#ff8a7a", t: now / 1000});
  if (mine) { sfx("hurt"); fallQuake = {t0: now, amp: FALL.shake[0] + Math.min(3, hearts(n))}; }
}
// The ground shaking under you after a fall that hurt, and under a nyxwing's entrance (Nyx.quake): art px to move the camera by
function fallShake(now) {
  if (!opt("shake")) { fallQuake = null; return 0; }
  const k = fallQuake ? (now - fallQuake.t0) / 1000 / FALL.shake[1] : 1;
  if (k >= 1) fallQuake = null;
  return (fallQuake ? Math.round(Math.sin(k * 34) * fallQuake.amp * (1 - k) * (1 - k)) : 0) + Nyx.quake(now);
}

// Called as a body is drawn: dust as it leaves the ground, dust and a sound as it lands. -> its hop (or its fall), or null
function jumpNow(p, now, st, fall) {
  const lp = Leap.body(p, now); if (lp) return lp;                              // (you in the air: leap.js)
  const lift = Leap.lift(p), j = jumping0(p, now, st, fall) || (lift ? {body: 0, ground: 0, air: false, squash: false, tuck: false, pose: null} : null);
  return lift ? {...j, body: j.body + lift, ground: j.ground + lift} : j;   // (just down from a jump: drawn from the level the eye is coming to)
}
function jumping0(p, now, st, fall) {
  // (a hop asked for in a fall, or at the edge as it began, is no hop: it waited under the fall and played what was left
  //  of its arc once you were down, the body 18 px up in a frame and down again: "when i jump above a hole it glitches")
  if (fall) { if (fall.air && now - st.hop < HOP.ms) st.hop = -1e9; return fall; }
  if (now - st.bounce < FALL.bounce[1] * 1000 && !jumpOf(p)) {                 // a heavy landing: up a little off the ground, and down (not on a step: its arc)
    const k = (now - st.bounce) / 1000 / FALL.bounce[1];
    return {body: Math.sin(k * Math.PI) * FALL.bounce[0], ground: 0, air: false};
  }
  const hop = hopOf(p, now, st);
  if (hop) { if (hop.tuck && st.hopUp !== st.hop) { st.hopUp = st.hop; jumpDust(p, 3, .8); } return hop; }
  if (st.hop && st.hopDown !== st.hop && now - st.hop >= HOP.ms) { st.hopDown = st.hop; if (now - st.hop < HOP.ms + 200) { st.settle = st.hop + HOP.ms; jumpDust(p, 3, 1); } }   // (down: the squash, by the clock)
  const j = jumpOf(p), tx = Math.round(p.x), ty = Math.round(p.y);
  if (st.jair !== null && !(j && j.tuck && j.key === st.jair)) {           // down: its feet touch (the step's last frames, or the next step's crouch up a staircase, or off it)
    const down = st.jd < 0;
    jumpDust(p, 4, down ? 1.3 : 1); sfx(down ? "thud" : "step", tx, ty);
    st.jair = null; st.settle = now;
  }
  if (j && j.tuck && st.jair === null) { st.jair = j.key; st.jd = j.d; jumpDust(p, 3, .8); }   // (off the ground: dust where it leaves it, not while it crouches)
  if (!j && now - st.settle < SETTLE.ms) return {body: 0, ground: 0, air: false, squash: true, tuck: false, pose: now - st.settle < SETTLE.land ? "land" : "settle"};   // (on the ground again: the squash, back up to standing)
  if (j && !j.pose && now - st.settle < SETTLE.ms) return {...j, pose: now - st.settle < SETTLE.land ? "land" : "settle"};   // (down off a step as you land: the landing's poses go on over the drop, not walk, land, walk)
  return j;
}
// Dust where the feet leave the ground or come down on it: a few px of the dust's colours thrown out low to both sides
// along the ground, gone in a sixth of a second (k: how hard). (floor: the ground under the feet, which the HD look
// draws it over: without one a speck came out half a body up, beside the hips)
function jumpDust(p, n, k) {
  const x = p.x + .5, fl = p.y + .55, r = Math.random, m = particles(n);
  for (const side of [-1, 1]) for (let i = 0; i < m; i++) {      // (from beside the feet, not on them: white socks)
    const floor = fl + .02 + r() * .05;
    parts.push({x: x + side * (.3 + r() * .1), y: floor - .03, floor, vx: side * (1.4 + r() * 1.2) * k, vy: -.25 * k - r() * .25, g: 1.4,
      life: .12 + r() * .1, age: 0, c: i % 2 ? "rgba(233,217,180,.9)" : "rgba(246,238,216,.9)", s: i ? 1 : 2});
  }
}
// Its shadow, on the ground under it (x, y: where the body is drawn standing; z: the zoom). (The HD look draws no px
// of a sprite under half opaque (vox_style_glsl.js): there this is not seen; its shadow in the air is the sun's,
// a shade under its feet that shrinks as it goes up: hd_sun.js body)
function jumpShadow(j, x, y, S, z, wide = 5) {
  ctx.fillStyle = "rgba(40,30,50,.2)";
  pixelOval(x + S / 2, y - Math.round(j.ground * z) + S - 2 * z, Math.max(wide * .6, wide - (j.body - j.ground) / 6), 2, 0, .5);
}
// How fast you may walk from (fx, fy) to (nx, ny) on foot, in tiles a second: up a step (not a ladder) no faster
// than the jump takes (walk.js walkOn: the walk waits for it), else Infinity
function jumpPace(p, fx, fy, nx, ny) {
  const la = Floors.standOf(p, fx, fy), lb = Floors.standOf(p, nx, ny);
  if (lb <= la || Climb.onLadder(fx, fy, la, nx, ny, lb)) return Infinity;      // (down: a drop, at the walk's pace. Slowed to a jump's 337 ms a step, a sprint down the cave stairs fell 6 tiles behind the world and was put back on it at once)
  return 1000 / jumpMs(lb - la);
}
