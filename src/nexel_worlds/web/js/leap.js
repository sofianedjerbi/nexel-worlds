// LEAP: the jump key is a real jump ("sprinting + jumping should preserve velocity of player - add a real height
// jumping. jump shouldn't be 'go on a bloc with nice animation' but 'gain z coordinates', so jumping + sprinting and
// jumping + directing yourself just like minecraft should be possible"). You leave the ground with the walk's speed
// (none standing, 5 tiles a second walking, 10 sprinting) and go up as a thrown thing does (jump.js JUMP: a block and
// a quarter at the top, 0.41 s in the air on the level), keep going the way you went, and may steer a little in the
// air (LEAP.steer: the keys held push you their way). The land stops you where it is higher than your feet; you come
// down on whatever is under you: a step up, the far side of a gap (two tiles across at a sprint), the foot of a
// ledge. Your screen works it out frame by frame; the world is told when you land: the tiles you went over and the
// height you landed at (sim/leaping.py checks them against the same arc, then makes them, a tile a stride).
// Standing in front of a step, the key takes you up onto it with a hop (walk.js jumpKey: in a tunnel or a shaft there
// is no room for a jump through the air).
// Auto-jump is the same jump: walking towards a step a layer up, you leave the ground just early enough to clear its edge
// (due), at the walk's speed ("it stops the velocity and does an up-block animation": the step's own hop at a third of a
// second a step; it is still how others are drawn going up a step, jump.js jumpOf).

const LEAP = {steer: 8, margin: .45};   // air control (tiles/s2 towards the way held); how near a tile's edge a wall stops you
const Leap = (() => {
  const S = {L: null, landed0: null, C: null, Ct: 0, off: 0, air: false};   // (L: {t, x, y, z, vx, vy, vz, z0, path, run, tx, ty}: you in the air)
  const ORDER = ["takeoff", "rise", "apex", "fall", "touch"];
  const G = () => JUMP.g, V0 = () => Math.sqrt(2 * G() * JUMP.top);   // levels/s2; levels/s up as you leave the ground
  const tileOf = (x, y) => [Math.round(x), Math.round(y)];
  // the body (feet at level z, two cells tall) fits on tile (x, y)
  const fits = (x, y, z) => { const c = Math.floor(z + 1e-6); return !solidAt(x, y, c + 1) && !solidAt(x, y, c + 2); };
  const held = () => { const k = [...keys].reverse().find((k) => KEYDIR[k]); return k ? DIRV[KEYDIR[k]] : null; };
  // May you jump from where you are? (in the water, in a boat, on a ladder, falling, building: the old ways)
  function can(p, ledge) {   // (ledge: walking off one: the fall jump.js begins on the tile before the edge does not stop it, it is taken over)
    const [x, y] = tileOf(p.x, p.y), t = tile(x, y), h = myZ(x, y);
    // (room over your head for the jump's top: under a roof, in a tunnel or a cave's stair, a hop instead: a jump there
    // meets the roof, the screen's tiles not the world's, and the world puts you back where it has you)
    return !!p && !Build.on && !(p.e && p.e.sail) && !(t && wet(t[1])) && !Climb.climbOf(p) && (ledge || !BodyPlace.state(p).fall) && !eating() && (ledge || (!solidAt(x, y, h + 3) && !solidAt(x, y, h + 4)));   // (off a ledge you do not rise: no room over your head wanted)
  }
  // Off the ground, with the walk's speed
  // (carry: {w, run}, on again at once from where you landed, against a step: no walk to take the speed from, land)
  // (auto: the auto-jump's, not the key's: up a flight of steps it is planned, stairArc)
  // (vz0: up as you leave the ground, levels/s: a step off a ledge leaves with none, dropDue)
  function start(p, now, carry, auto, vz0) {
    const [x, y] = tileOf(p.x, p.y), run = carry ? carry.run : !!(walking && walking.run && sprinting()), w = carry ? carry.w : walking && p.walking ? DIRV[walking.dir] : held();   // (no walk, a way held (just down, going to the tile's middle): that way, as walking: the air's steering took it there anyway, unplanned, into a step's face)
    let sp = w ? RULES.pace[run ? "sprint" : "walk"] : 0, vz = vz0 === undefined ? V0() : vz0, cap = null;
    if (w && sp > 0 && vz > 0) {                         // (a jump on the move, the key's or the auto-jump's: never into a step's face)
      const a = stairArc(p, w, sp); if (a) { sp = cap = a.v; vz = a.vz; }
      while (sp > .5 && hits(p, w, sp, vz)) sp = cap = Math.max(.5, sp - .25);
    }
    if (walking) {                                         // the walk ends where you leave the ground: the world comes to that tile first
      const args = {at: mark(x, y)}; if (walking.run) args.run = true; if (autoJump()) args.jump = true;   // (the way there may go up a step, sprung, as walk.js's stop says: without it the world did not take the step up off a stair's foot, refused every flight after it, and the screen was put back 5 tiles)
      walking = null; p.walking = false; pred = {x, y, until: now + 2000};
      rpc("act", {tool: "stop", args});
    }
    S.L = {t: 0, x: p.x, y: p.y, z: myZ(x, y), vx: w ? w[0] * sp : 0, vy: w ? w[1] * sp : 0, vz, path: [], run, tx: x, ty: y, cap};
    S.L.z0 = S.L.z; S.L.drop = vz === 0 && sp > 0; if (S.C === null) { S.C = S.L.z; S.Ct = now; }   // (drop: off a ledge, walking: on its level till you are over the edge, frame)
    if (w) BodyPlace.face(p, w[0], w[1]);
    if (vz > 0) jumpDust(p, 3, .8);
  }
  // (its parts, each its own file, made in order: each takes what it uses from K)
  const K = {ORDER, G, V0, tileOf, fits, held, can, start};
  for (const part of [LeapSteps, LeapLedge, LeapLand, LeapAir, LeapEye]) Object.assign(K, part(S, K));
  const {leapable, due, room, dropDue, ledge, ahead, frame, body, level, landedOn, after, cam, lift, seen, stairArc, hits} = K;
  return {leapable, can, due, room, dropDue, ledge, start, ahead, frame, body, level, landedOn, after, cam, lift, seen, on: () => !!S.L, landing: (p) => !!(BodyPlace.peek(p) || {}).leapAt, get landed() { return S.landed0; }, gliding: () => { const p = ents.get("agent" + myId); return !!(p && landedOn(p) !== null); }, get state() { return S.L; }};
})();
