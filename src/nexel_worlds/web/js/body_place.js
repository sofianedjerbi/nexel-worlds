// BODY PLACE: where a body is this frame, worked out once, read by all that draws it or stands over it: the camera
// (render.js), its picture (characters.js drawBody), its name, bubble, emote, health and progress bars, its shadow, the
// HD look's level and list (hd_level.js, hd.js), the light and the x-ray (Cover).
// It was nobody's: each reader asked jumping(), falling(), climbOf(), swimsAt() itself, in its own order (the body:
// fall, bounce, hop, step; its name: fall, leap, step, hop, no bounce, no landing's lift; the swimmer: after the hop's
// bob). So the name hopped over a boat that did not, over a swimmer who did not, and sat off the head while the eye
// caught up after a jump down a few levels.
//
// BodyPlace.of(p) -> {tx, ty: the tile it is drawn on (on a ladder's rungs the ladder's, not the cliff's it nears); z: its feet's height, levels (the solvers', not the picture's px); ground: the ground under it, levels (its
//   shadow, its dust); mode: one of "boat", "swim", "climb", "fall", "jump", "walk"; air: feet off the ground; pose: the
//   jump's pose or null; fx, fy: the way it faces; dx, dy: tiles aside (a ladder's lean);
//   line: the level of the straight line between its two tiles' grounds, where it is on the way (a fall's drop or a ladder between them: the nearer tile's);
//   up: art px its picture and all over it are drawn over the straight line between its two tiles (relief.js liftOf);
//   eye: art px the camera follows over that line (a climb, a fall: not a hop's arc);
//   jump: {body, ground: art px over the line (its solver's levels, made px here), pose, key: the step it is on}, climb: the mode's own numbers, for its picture (jump.js, climbing.js); fall: {z, ground: levels, air}}
// One record a body a frame (the frame's time: render.js lastT): asked again in the frame, the same record.
const BodyPlace = (() => {
  // A body's own state of its moves, one record a body, BodyPlace's (not fields on the body): fall: a fall begun {top, land: levels, t0, done}; hurt: what a fall cost, shown where it lands;
  // bounce: when a heavy landing was; hop: when a hop on the spot began (0: none), hopUp, hopDown: the hop whose dust was thrown, leaving and landing; swam: in the water at the last frame drawn (swim.js);
  // jair, jd: the step whose arc it is in the air of (its key), its levels up; settle: when it last touched down; leapAt: {x, y, z}: the tile a jump through the air came down on, off its middle, on its way there; jumpNext: the jump key pressed on that way (leap.js)
  const states = new WeakMap();
  const state = (p) => { let s = states.get(p); if (!s) states.set(p, s = {fall: null, hurt: 0, bounce: -1e9, hop: 0, hopUp: 0, hopDown: 0, swam: false, jair: null, jd: 0, settle: -1e9, leapAt: null, jumpNext: false}); return s; };
  const peek = (p) => states.get(p) || null;   // (made by no reading: relief.js liftOf asks of any place, a puff's)
  function make(p, now) {
    const e = p.e || {}, boat = !!e.sail;
    // (the mode, in ONE order. In a boat nothing else: no hop, no fall. Swimming, unless still in the air over the water.
    // On a ladder's rungs. Then the air: a fall, a jump (through the air, on the spot, up a step). Else on the ground)
    const st = state(p), line = liftOf(p) / zoom, lv = line / RELIEF_STEP, fall = boat ? null : fallOf(p, now, st);   // (a fall, a jump: levels; over the line)
    const j0 = boat ? null : jumpNow(p, now, st, fall && {body: fall.z - lv, ground: fall.ground - lv, air: fall.air});
    const swim = !boat && !!p.e && swimsAt(p, e) && !(j0 && j0.air), climb = boat || swim ? null : Climb.climbOf(p);
    const k = Leap.seen() * RELIEF_STEP, jump = swim || !j0 ? null : {...j0, body: Math.round(line + j0.body * k) - line, ground: j0.ground * k};   // (its picture's px: every body's hop seen from the eye's pitch, leap.js seen, yours and others' alike: its feet on a whole art px, as drawn. It was the arc's own px over the line rounded, the line between two tiles' grounds not whole: at a ledge's edge the feet went 5.021, 4.979, 5 levels up, frame to frame)
    const air = !!jump && !!(jump.air || jump.tuck);
    if (climb && climb.on) face(p, climb.fx, climb.fy);       // (on the rungs: to the ladder)
    const mode = boat ? "boat" : swim ? "swim" : climb ? "climb" : fall && fall.air ? "fall" : jump && (jump.leap || jump.tuck || jump.pose) ? "jump" : "walk";
    const dx = climb ? climb.dx : 0, dy = climb ? climb.dy : 0, [ax, ay, bx, by, la, lb] = Floors.between(p), f = ax === bx ? p.y - ay : p.x - ax;
    if (climb) climb.lift = (climb.h - (la + (lb - la) * f)) * RELIEF_STEP;   // (on a ladder: art px over the straight line, for its picture)
    // (a body with no jump of its own, a swimmer just down from a leap: drawn from the level the eye is coming to, by the landing's
    //  lift, as a jump's landing is in it (jump.js jumpNow), #24)
    const lift = Math.round(Leap.lift(p) * k);
    const up = (climb ? climb.lift : 0) + (jump ? jump.body : lift);
    return {at: now, tx: Math.round(p.x + dx), ty: Math.round(p.y + dy), mode, air, pose: jump && jump.pose || null, fx: p.fx || 0, fy: p.fy || 0, dx, dy,
      line: Math.abs(la - lb) >= FALL.from || Climb.onLadder(ax, ay, la, bx, by, lb) ? (f < .5 ? la : lb) : la + (lb - la) * f, up, eye: (climb ? climb.lift : 0) + (fall ? fall.z * RELIEF_STEP - line : 0), z: climb ? climb.h : lv + (jump ? j0.body : 0), ground: lv + (jump ? j0.ground : 0), jump, fall, climb};   // (z, ground: the solver's levels, not the picture's px)
  }
  // THE WAY A BODY FACES: one writer, called by what turns it: a key (keyboard.js turn), the walk and its wall (walk.js),
  // a jump and its steering (leap.js), the world's tick (state.js: its step, what it sets about doing), your own action
  // as it starts (agent.js), a ladder's rungs (make, above). The picture reads it. (Nine places wrote p.fx, p.fy, three
  // of them while drawing: a body off the screen was not turned, and drawing an action turned you back to it at every
  // frame: walking off from a dig you faced the wall, and the keys aimed at it)
  const face = (p, fx, fy) => { p.fx = fx; p.fy = fy; };
  // ...to what it sets about doing: the action's way, or the one it is done to
  function faceAction(p, dir, tid) {
    if (dir && DIRV[dir]) face(p, ...DIRV[dir]);
    if (tid != null) { const q = [...ents.values()].find((q) => q.e && q.e.id == tid); if (q) { const fx = Math.sign(q.x - p.x); face(p, fx, fx ? 0 : Math.sign(q.y - p.y)); } }
  }
  const of = (p) => (p.place && p.place.at === lastT ? p.place : (p.place = make(p, lastT)));
  // screen px to move what is over a body by, from sx(p.x), bodyY(p): by whole art px, as the body is drawn (its lift in the land's own pixel, state.js artPx: not zoom)
  const over = (p, S) => { const b = of(p); return [b.dx * S, b.dy * S - b.up * artPx()]; };
  return {of, over, face, faceAction, state, peek};
})();
