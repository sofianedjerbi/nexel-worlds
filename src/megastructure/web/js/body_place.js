// BODY PLACE: where a body is this frame, worked out once, read by all that draws it or stands over it: the camera
// (render.js), its picture (characters.js drawBody), its name, bubble, emote, health and progress bars, its shadow, the
// HD look's level and list (hd_level.js, hd.js), the light and the x-ray (Cover).
// It was nobody's: each reader asked jumping(), falling(), climbOf(), swimsAt() itself, in its own order (the body:
// fall, bounce, hop, step; its name: fall, leap, step, hop, no bounce, no landing's lift; the swimmer: after the hop's
// bob). So the name hopped over a boat that did not, over a swimmer who did not, and sat off the head while the eye
// caught up after a jump down a few levels.
//
// BodyPlace.of(p) -> {tx, ty: the tile it is drawn on (on a ladder's rungs the ladder's, not the cliff's it nears); z: its feet's height, levels, as drawn; ground: the ground under it, levels (its
//   shadow, its dust); mode: one of "boat", "swim", "climb", "fall", "jump", "walk"; air: feet off the ground; pose: the
//   jump's pose or null; fx, fy: the way it faces; dx, dy: tiles aside (a ladder's lean);
//   line: the level of the straight line between its two tiles' grounds, where it is on the way (a fall's drop or a ladder between them: the nearer tile's);
//   up: art px its picture and all over it are drawn over the straight line between its two tiles (relief.js liftOf);
//   eye: art px the camera follows over that line (a climb, a fall: not a hop's arc);
//   jump, climb: the mode's own numbers, for its picture (jump.js, climbing.js); fall: {z, ground: levels, air}}
// One record a body a frame (the frame's time: render.js lastT): asked again in the frame, the same record.
const BodyPlace = (() => {
  // A body's own state of its moves, one record a body, BodyPlace's (not fields on the body): fall: a fall begun
  // {top, land: levels, t0, done}; hurt: what a fall cost, shown where it lands; bounce: when a heavy landing was
  const states = new WeakMap();
  const state = (p) => { let s = states.get(p); if (!s) states.set(p, s = {fall: null, hurt: 0, bounce: -1e9}); return s; };
  function make(p, now) {
    const e = p.e || {}, boat = !!e.sail;
    // (the mode, in ONE order. In a boat nothing else: no hop, no fall. Swimming, unless still in the air over the water.
    // On a ladder's rungs. Then the air: a fall, a jump (through the air, on the spot, up a step). Else on the ground)
    const st = state(p), line = liftOf(p) / zoom, fall = boat ? null : fallOf(p, now, st);   // (a fall: levels; for its picture, art px over the line)
    const j0 = boat ? null : jumpNow(p, now, st, fall && {body: fall.z * RELIEF_STEP - line, ground: fall.ground * RELIEF_STEP - line, air: fall.air});
    const swim = !boat && !!p.e && swimsAt(p, e) && !(j0 && j0.air), climb = boat || swim ? null : Climb.climbOf(p), jump = swim ? null : j0;
    const air = !!jump && !!(jump.air || jump.tuck);
    if (climb && climb.on) face(p, climb.fx, climb.fy);       // (on the rungs: to the ladder)
    const mode = boat ? "boat" : swim ? "swim" : climb ? "climb" : fall && fall.air ? "fall" : jump && (jump.leap || jump.tuck || jump.pose) ? "jump" : "walk";
    const up = (climb ? climb.lift : 0) + (jump ? Math.round(jump.body) : 0);
    const dx = climb ? climb.dx : 0, dy = climb ? climb.dy : 0, [ax, ay, bx, by, la, lb] = Floors.between(p), f = ax === bx ? p.y - ay : p.x - ax;
    return {at: now, tx: Math.round(p.x + dx), ty: Math.round(p.y + dy), mode, air, pose: jump && jump.pose || null, fx: p.fx || 0, fy: p.fy || 0, dx, dy,
      line: Math.abs(la - lb) >= FALL.from || Climb.onLadder(ax, ay, la, bx, by, lb) ? (f < .5 ? la : lb) : la + (lb - la) * f, up, eye: (climb ? climb.lift : 0) + (fall ? fall.z * RELIEF_STEP - line : 0), z: climb ? climb.h : (line + up) / RELIEF_STEP, ground: (line + (jump ? jump.ground : 0)) / RELIEF_STEP, jump, fall, climb};
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
  // screen px to move what is over a body by, from sx(p.x), bodyY(p): by whole art px, as the body is drawn
  const over = (p, S) => { const b = of(p); return [b.dx * S, b.dy * S - b.up * zoom]; };
  return {of, over, face, faceAction, state};
})();
