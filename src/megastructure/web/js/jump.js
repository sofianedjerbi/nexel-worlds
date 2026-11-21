// Up or down a layer (or several, down): a hop, for a person or a creature alike (sim/bodies.py: one way to stand on
// the land). Between two tiles a body is placed on the straight line between their heights (relief.js liftOf: the
// camera and the name over a head follow that line, smoothly). The hop is one arc over that line, from the middle
// of a tile to the middle of the next, as a thrown thing goes: high enough to clear the edge it goes over. Its
// shadow stays on the ground under it (the ground it leaves, until it is over the edge), it holds the pose it took
// off in (no walking on air), and there is dust where it leaves the ground and where it lands.
// It is quick: a hop takes the time of a step (walk.js: your screen doesn't slow down for it). Seen frame by frame,
// what looked wrong before was the hang: a step and a half long, the body near the top of its arc for most of it.
// And then ("Jump looks unnatural"): it left the ground the moment the step began and landed the moment it ended,
// stiff, in the pose it stood in. Then ("improve the jumping animation") each part has a pose drawn for it (jump_art.js):
// a crouch on the ground it leaves (JUMP.crouch of the step), the push off a px taller, the legs tucked going up, the
// ears a px up as it turns over the top, the legs reaching down as it comes down, a squash with the feet apart where
// it lands (JUMP.land) and a settle on the way back up (SETTLE ms more, after the step: the walk goes on meanwhile).
// The pose in the air is told by how fast it goes up or down, not by the time: a thrown thing's arc, a parabola.
// Dust is thrown out low to both sides where it leaves the ground and where it lands, a little more there.

const JUMP = {over: 2, off: 1, crouch: .12, land: .16};   // art px the arc clears the edge by (going up, coming down); the share of the step on the ground before it, after it
const HOP = {ms: 280, px: 6, crouch: .16, land: .22};     // a hop on the level: how long, how high (art px), its crouch and landing (~3 frames at 60 fps, ~4)
const SETTLE = 50;                                        // ms of the settle after a step's landing (on the ground again: the walk's own pace)
const JPOSE = {crouch: 0, takeoff: 1, rise: 2, apex: 3, fall: 4, land: 5, settle: 6};   // the column of each pose in the jump's rows (ANIM.jump)

// A thrown body's height at u (0 to 1) going from 0 to d art px: over the straight line, its peak `top` over the higher end, about
const jumpArc = (u, d, top) => d * u + 4 * (Math.abs(d) / 2 + top) * u * (1 - u);
// Its pose in the air at u: the push off, then going up fast, turning over the top, coming down (by its speed up: from the arc)
function airPose(u, d, top) {
  if (u < .16) return "takeoff";
  const a = 4 * (Math.abs(d) / 2 + top), v = d + a * (1 - 2 * u), v0 = Math.max(1e-6, d + a);
  return v > .4 * v0 ? "rise" : v < -.4 * v0 ? "fall" : "apex";
}
// The parts of a jump at f (0 to 1 of its time): -> [u: how far through the air (0 to 1), squashed: on the ground, its pose there]
const jumpPhase = (f, crouch, land) => (f < crouch ? [0, true, "crouch"] : f > 1 - land ? [1, true, f > 1 - land * .4 ? "settle" : "land"]
  : [(f - crouch) / (1 - crouch - land), false, null]);

// -> null on the level, or {body, ground: art px over the straight line (its feet, its shadow), squash, tuck: in the air, pose}
function jumpOf(p) {
  const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
  if (ax === bx && ay === by) return null;
  const la = Floors.standOf(p, ax, ay), lb = Floors.standOf(p, bx, by);
  if (la === lb || Climb.onLadder(ax, ay, la, bx, by, lb)) return null;          // (up or down a ladder: a straight climb)
  const f = ax === bx ? p.y - ay : p.x - ax, d = (lb - la) * RELIEF_STEP;        // how far across; px from the first to the second
  const fwd = (ax === bx ? p.ty - p.y || p.fy : p.tx - p.x || p.fx) >= 0;        // from the first to the second?
  const g = fwd ? f : 1 - f, D = fwd ? d : -d, line = D * g, top = D > 0 ? JUMP.over : JUMP.off;   // the way it goes: how far along, px up by, the straight line
  const [u, squash, on] = jumpPhase(g, JUMP.crouch, JUMP.land);
  return {body: jumpArc(u, D, top) - line, ground: (g < .5 ? 0 : D) - line, squash, tuck: !squash, pose: on === "settle" ? "land" : on || airPose(u, D, top)};   // (its settle: after the step, SETTLE)
}

// A drop of FALL.from layers or more is a fall, not a hop. You walk to the edge on the ground you leave; from the edge
// you come down by your own weight (FALL.g), however long that takes: the step is usually over before you land. Your
// shadow waits on the ground below and grows as you near it, your legs go (two frames of the run, turn about), the
// camera comes down with you (render.js) and the wind rises in your ears (audio.js: fallWind). Where you land: dust
// thrown out to both sides and a thump, heavier the further you fell. A fall that hurt (the server says so: its
// `fall` event, more than 3 layers) lands with the tree's thud, the ground shakes, you flash, bounce, and lose
// what it cost you there, not when you stepped off. (A fall was a hop: one arc at the pace of a step, twelve layers
// in a fifth of a second, the screen jumping with it, and nothing to say it had hurt.)
const FALL = {from: 3, g: 1000, flail: 70, heavy: 4, shake: [3.5, .32], bounce: [3, .17]};   // layers; art px/s2; ms a frame; layers from which it lands heavily; px and s of the shake, of the bounce
let fallQuake = null;                 // {t0, amp}: the ground shaking under you (render.js: fallShake)

// -> null, or the fall of p now: {body, ground: art px over the straight line (relief.js liftOf), air}. (Asked once
// a frame by the camera and once by the drawing: worked out once.)
function falling(p, now) {
  if (p.fallAt !== now) { p.fallAt = now; p.fallNow = fallOf(p, now); }
  return p.fallNow;
}
function fallOf(p, now) {
  const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y), ramp = liftOf(p) / zoom;
  const la = Floors.standOf(p, ax, ay), lb = Floors.standOf(p, bx, by), between = (ax !== bx || ay !== by) && la !== lb;
  const fwd = (ax === bx ? p.ty - p.y || p.fy : p.tx - p.x || p.fx) >= 0, down = between && fwd === la > lb;   // going to the lower one?
  const f = ax === bx ? p.y - ay : p.x - ax, u = la > lb ? f : 1 - f;         // how far from the higher tile's middle to the lower one's
  let F = p.fall;
  if (!F) {
    if (!down || Math.abs(la - lb) < FALL.from || Climb.onLadder(ax, ay, la, bx, by, lb)) return null;
    F = p.fall = {top: Math.max(la, lb) * RELIEF_STEP, land: Math.min(la, lb) * RELIEF_STEP, t0: 0};
  }
  if (F.done) {                                           // down before the step was over: on the ground, to the end of it
    if (!between) { p.fall = null; return null; }
    return {body: F.land - ramp, ground: F.land - ramp, air: false};
  }
  if (!F.t0) {                                            // to the edge, on the ground it leaves
    if (!down) { p.fall = null; return null; }            // (turned back)
    if (u < .5) return {body: F.top - ramp, ground: F.top - ramp, air: false};
    F.t0 = now;
  }
  const t = (now - F.t0) / 1000, h = F.top - .5 * FALL.g * t * t, mine = p.e && p.e.kind === "agent" && p.e.id === myId;
  if (h <= F.land || t > 3) {
    landed(p, (F.top - F.land) / RELIEF_STEP, now, mine);
    p.fall = between ? {...F, done: true} : null;
    return p.fall ? {body: F.land - ramp, ground: F.land - ramp, air: false} : null;
  }
  if (mine) fallWind(Math.min(1, FALL.g * t / 600));       // (louder and higher with its speed)
  return {body: h - ramp, ground: F.land - ramp, air: true};
}
// What is drawn over a body (its name, its health, what it says, its marks) goes where the body is drawn: up a ladder
// (climbing.js), in a hop, in a fall. -> screen px to move it by from sx(p.x), bodyY. (It followed falls only: on a
// ladder the name stayed on the straight line, a tile and more from the climber; in a hop it stood still.)
function overBody(p, S) {
  const cl = Climb.climbOf(p), j = p.fall && p.fallNow ? p.fallNow : jumpOf(p);
  return [cl ? cl.dx * S : 0, (cl ? cl.dy * S - cl.lift * zoom : 0) - (j ? j.body * zoom : 0)];
}
// It lands, `layers` further down
function landed(p, layers, now, mine) {
  const tx = Math.round(p.x), ty = Math.round(p.y), heavy = layers >= FALL.heavy, hurt = p.fallHurt;
  if (mine) fallWind(-1);
  for (const side of [-1, 1]) for (let i = 0; i < 3 + Math.min(6, layers); i++)       // dust, thrown out low to both sides
    parts.push({x: p.x + .5 + side * .2, y: p.y + .85 - UP, vx: side * (1.5 + Math.random() * (2 + layers * .25)), vy: -.4 - Math.random() * 1.2,
      g: 5, life: .35 + Math.random() * .3, age: 0, c: PCOL.dust[i % PCOL.dust.length], s: Math.random() < .4 ? 2 : 1});
  smoke(p.x, p.y + .35 - UP, heavy ? 7 : 4, heavy ? .6 : .4);
  sfx(heavy ? "fallthud" : "thud", tx, ty);
  if (heavy || hurt) p.bounce = now;
  if (hurt) fallHurts(p, now, mine);
}
// What a fall cost, shown where it lands (state.js keeps it from the server's `fall` event until then)
function fallHurts(p, now, mine) {
  const n = p.fallHurt; if (!n) return;
  p.fallHurt = 0;
  flashes.set(p.e.kind + p.e.id, now);
  floats.push({x: Math.round(p.x), y: Math.round(p.y), text: "-" + hearts(n), heart: true, color: "#ff8a7a", t: now / 1000});
  if (mine) { sfx("hurt"); fallQuake = {t0: now, amp: FALL.shake[0] + Math.min(3, hearts(n))}; }
}
// The ground shaking under you after a fall that hurt: art px to move the camera by, dying away
function fallShake(now) {
  if (!opt("shake")) fallQuake = null;
  if (!fallQuake) return 0;
  const k = (now - fallQuake.t0) / 1000 / FALL.shake[1];
  if (k >= 1) { fallQuake = null; return 0; }
  return Math.round(Math.sin(k * 34) * fallQuake.amp * (1 - k) * (1 - k));
}

// Called as a body is drawn: dust as it leaves the ground, dust and a sound as it lands. -> its hop (or its fall), or null
function jumping(p, now = performance.now()) {
  const fall = falling(p, now);
  if (fall) return fall;
  if (now - p.bounce < FALL.bounce[1] * 1000 && !jumpOf(p)) {                 // a heavy landing: up a little off the ground, and down
    const k = (now - p.bounce) / 1000 / FALL.bounce[1];
    return {body: Math.sin(k * Math.PI) * FALL.bounce[0], ground: 0, air: false};
  }
  if (now - p.hop < HOP.ms && !jumpOf(p)) {                                   // the jump key on the level: a hop on the spot (walk.js jumpKey; others: their `jump` event, state.js)
    const [u, squash, on] = jumpPhase((now - p.hop) / HOP.ms, HOP.crouch, HOP.land);
    if (!squash && p.hopUp !== p.hop) { p.hopUp = p.hop; jumpDust(p, 3, .8); }
    if (u === 1 && p.hopDown !== p.hop) { p.hopDown = p.hop; jumpDust(p, 3, 1); }
    return {body: Math.round(jumpArc(u, 0, HOP.px)), ground: 0, air: false, squash, tuck: !squash, pose: on || airPose(u, 0, HOP.px)};
  }
  const j = jumpOf(p), tx = Math.round(p.x), ty = Math.round(p.y);
  if (j && j.tuck && p.jfrom === undefined) { p.jfrom = Floors.standOf(p, tx, ty); jumpDust(p, 3, .8); }   // (off the ground: dust where it leaves it, not while it crouches)
  if (!j && p.jfrom !== undefined) {
    const down = Floors.standOf(p, tx, ty) < p.jfrom;
    jumpDust(p, 4, down ? 1.3 : 1); sfx(down ? "thud" : "step", tx, ty);
    p.jfrom = undefined; p.settle = now;
  }
  if (!j && now - p.settle < SETTLE) return {body: 0, ground: 0, air: false, squash: true, tuck: false, pose: "settle"};   // (on the ground again: back up to standing)
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
