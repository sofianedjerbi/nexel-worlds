// LEAP: the jump key is a real jump ("sprinting + jumping should preserve velocity of player - add a real height
// jumping. jump shouldn't be 'go on a bloc with nice animation' but 'gain z coordinates', so jumping + sprinting and
// jumping + directing yourself just like minecraft should be possible"). You leave the ground with the walk's speed
// (none standing, 5 tiles a second walking, 10 sprinting) and go up as a thrown thing does (jump.js JUMP: a block and
// a quarter at the top, 0.41 s in the air on the level), keep going the way you went, and may steer a little in the
// air (LEAP.steer: the keys held push you their way). The land stops you where it is higher than your feet; you come
// down on whatever is under you: a step up, the far side of a gap (two tiles across at a sprint), the foot of a
// ledge. Your screen works it out frame by frame; the world is told when you land: the tiles you went over and the
// height you landed at (sim/leaping.py checks them against the same arc, then makes them, a tile a stride).
// Standing in front of a step, the key takes you up onto it as before (walk.js jumpKey: in a tunnel or a shaft there
// is no room for a jump through the air).
// Auto-jump is the same jump: walking towards a step a layer up, you leave the ground just early enough to clear its edge
// (due), at the walk's speed ("it stops the velocity and does an up-block animation": the step's own hop at a third of a
// second a step; it is still how others are drawn going up a step, jump.js jumpOf).

const LEAP = {steer: 8, margin: .45};   // air control (tiles/s2 towards the way held); how near a tile's edge a wall stops you
const Leap = (() => {
  let L = null;                            // {t, x, y, z, vx, vy, vz, z0, path, run, tx, ty}: you in the air
  const ORDER = ["takeoff", "rise", "apex", "fall", "touch"];
  const G = () => JUMP.g / RELIEF_STEP, V0 = () => Math.sqrt(2 * G() * JUMP.top / RELIEF_STEP);   // levels/s2; levels/s up as you leave the ground
  const tileOf = (x, y) => [Math.round(x), Math.round(y)];
  // the body (feet at level z, two cells tall) fits on tile (x, y)
  const fits = (x, y, z) => { const c = Math.floor(z + 1e-6); return !solidAt(x, y, c + 1) && !solidAt(x, y, c + 2); };
  const held = () => { const k = [...keys].reverse().find((k) => KEYDIR[k]); return k ? DIRV[KEYDIR[k]] : null; };
  // May you jump from where you are? (in the water, in a boat, on a ladder, falling, building: the old ways)
  function can(p) {
    const [x, y] = tileOf(p.x, p.y), t = tile(x, y), h = myZ(x, y);
    // (room over your head for the jump's top: under a roof, in a tunnel or a cave's stair, the old way. A jump there
    // hit the roof, its tiles not the world's: you were drawn on the land over it and put back where the world had you)
    return !!p && !Build.on && !(p.e && p.e.sail) && !(t && wet(t[1])) && !Climb.climbOf(p) && !p.fall && !eating() && !solidAt(x, y, h + 3) && !solidAt(x, y, h + 4);
  }
  // Off the ground, with the walk's speed
  function start(p, now) {
    const [x, y] = tileOf(p.x, p.y), run = !!(walking && walking.run && sprinting()), w = walking && p.walking ? DIRV[walking.dir] : null;
    const sp = walking && p.walking ? RULES.pace[run ? "sprint" : "walk"] : 0;
    if (walking) {                                         // the walk ends where you leave the ground: the world comes to that tile first
      const args = {at: mark(x, y)}; if (walking.run) args.run = true; if (autoJump()) args.jump = true;   // (the way there may go up a step, sprung, as walk.js's stop says: without it the world did not take the step up off a stair's foot, refused every flight after it, and the screen was put back 5 tiles)
      walking = null; p.walking = false; pred = {x, y, until: now + 2000};
      rpc("act", {tool: "stop", args});
    }
    L = {t: 0, x: p.x, y: p.y, z: myZ(x, y), vx: w ? w[0] * sp : 0, vy: w ? w[1] * sp : 0, vz: V0(), path: [], run, tx: x, ty: y};
    L.z0 = L.z; if (C === null) { C = L.z; Ct = now; }
    if (w) BodyPlace.face(p, w[0], w[1]);
    jumpDust(p, 3, .8);
  }
  // walk.js walkOn, auto-jump: a step a layer up ahead, so near that a jump now, at the walk's speed, just clears its edge
  // (the time to rise a layer: T1; a little early rather than late: against the edge you would wait there)
  const T1 = () => { const v = V0(), g = G(); return (v - Math.sqrt(v * v - 2 * g)) / g; };
  // A step from (x0, y0) at height h up onto (x1, y1) is jumped through the air: not a flight of stairs (walked up), and
  // room for the jump's top over you and over it (two cells up: in a tunnel or a shaft the old hop up it, jump.js jumpOf)
  function leapable(x0, y0, h, x1, y1) {
    const c = FLOORS && Floors.get(x1, y1, h + 1);
    if ((c && c[0] === "stairs") || (FLOORS && (Floors.get(x0, y0, h) || [])[0] === "stairs")) return false;
    return !solidAt(x0, y0, h + 3) && !solidAt(x0, y0, h + 4) && !solidAt(x1, y1, h + 3) && !solidAt(x1, y1, h + 4);
  }
  function due(p, w) {
    if (!can(p)) return false;
    const [dx, dy] = DIRV[w.dir], s = dx || dy, x = Math.round(p.x), y = Math.round(p.y), h = myZ(x, y), at = dx ? p.x : p.y;
    const need = RULES.pace[w.run && sprinting() ? "sprint" : "walk"] * T1() + .08;
    for (let k = 1; k <= 2; k++) {
      const nx = x + dx * k, ny = y + dy * k, px = nx - dx, py = ny - dy, d = ((dx ? x : y) + (k - .5) * s - at) * s;   // (d: tiles to the edge before it)
      if (d < 0) continue;
      if (solidAt(nx, ny, h + 1)) return d <= need && landAt(h, nx, ny, px, py) === h + 1 && leapable(px, py, h, nx, ny);
      if (!solidAt(nx, ny, h) || d > need) return false;   // (a drop, or far: the walk's own)
    }
    return false;
  }
  // A frame in the air (render.js, in place of the walk)
  function frame(p, dt, now) {
    if (!L) return;
    L.t += dt;
    const h = held(), cap = RULES.pace[L.run ? "sprint" : "walk"];
    if (h) {                                               // steering: the way held pulls your speed towards it, a little
      const k = Math.min(1, LEAP.steer * dt / cap);
      L.vx += (h[0] * cap - L.vx) * k; L.vy += (h[1] * cap - L.vy) * k;
      BodyPlace.face(p, h[0], h[1]);
    }
    const g = G(), z1 = L.z + L.vz * dt - g * dt * dt / 2;
    L.vz -= g * dt;
    for (const [ax, v] of [["x", "vx"], ["y", "vy"]]) {    // along each axis: stopped by the land higher than your feet
      if (!L[v]) continue;
      const n = L[ax] + L[v] * dt, nt = Math.round(n), cur = ax === "x" ? L.tx : L.ty;
      if (nt !== cur) {
        const [x, y] = ax === "x" ? [nt, L.ty] : [L.tx, nt];
        if (!fits(x, y, Math.max(z1, L.z))) { L[ax] = cur + Math.sign(L[v]) * LEAP.margin; continue; }   // (against it, still pushing: higher up, on it)
        L[ax] = n; if (ax === "x") L.tx = nt; else L.ty = nt;
        L.path.push([L.tx, L.ty]);
        rpc("act", {tool: "leap", args: {path: [[L.tx, L.ty]], n: trailN, run: L.run}});   // (each tile as you come over it: the world goes with you, sim/leaping.py)
      } else L[ax] = n;
    }
    const ground = settleAt(L.tx, L.ty, L.z + 1e-6);      // (the ground under where you were: what you come down on)
    if (L.vz > 0 && solidAt(L.tx, L.ty, Math.floor(z1) + 3)) L.vz = 0;   // (the head against a ceiling)
    L.z = Math.max(z1, Math.min(L.z, ground));
    p.x = L.x; p.y = L.y; p.tx = L.tx; p.ty = L.ty; p.moved = now;
    if (!myAt || myAt.x !== L.tx || myAt.y !== L.ty) { myWas = myAt; myAt = {x: L.tx, y: L.ty, z: ground}; } else myAt.z = ground;
    if (L.vz <= 0 && L.z <= ground + 1e-6) land(p, now, ground);
  }
  // Down on the ground at `z`: the world is told the way you went; the walk goes on if a way is held
  function land(p, now, z) {
    const path = L.path.filter((t, i, a) => !i || t[0] !== a[i - 1][0] || t[1] !== a[i - 1][1]), run = L.run, z0 = L.z0;
    const h = held(), past = h && (p.x - p.tx) * h[0] + (p.y - p.ty) * h[1] >= 0 && Math.abs((p.x - p.tx) * h[1]) + Math.abs((p.y - p.ty) * h[0]) < .01 && fits(p.tx + h[0], p.ty + h[1], z);   // (and room on the way held: down by a wide hole's far wall, on into the wall was a step up four levels drawn as its arc, the body 20 px up and down)
    L = null; p.settle = now;
    // (the eye's way left to go, from this frame on: the body drawn on the ground is lifted by it (lift) from the frame
    //  you land. It was set at the eye's next look (cam): the landing frame drew you with none, 20 px up from the arc's
    //  last frame, a hole's floor four down under an eye two levels behind, then down again)
    if (C !== null && air) { off = z - C; air = false; }
    // (where you came down on the tile, off its middle: you go to it, at the walk's pace, before the walk goes on. On
    // the way you are on that tile and its height: between it and the one before, the step's own arc drew you a
    // second time, and half a level low. Past its middle the way you go, the walk goes on from there)
    p.leapAt = past ? null : {x: p.tx, y: p.ty, z};
    if (myAt) myAt.z = z;
    jumpDust(p, 4, z < z0 ? 1.3 : 1); sfx(z < z0 ? "thud" : "step", p.tx, p.ty);
    if (path.length) {
      const [x, y, n] = mark(p.tx, p.ty);
      if (!past) pred = {x, y, until: now + 3000};   // (walking on at once: no stop to wait for. A stop there read as turned back: `cut`, the flight dropped)
      rpc("act", {tool: "leap", args: {land: z, n, run}});
    } else rpc("act", {tool: "jump", args: {}});
    if (past) { p.tx += h[0]; p.ty += h[1]; syncWalk(); }   // (on into the next tile, as the walk is: the tile behind you read as a step down to it)
  }
  // You on the tile you came down on, on your way to its middle: its height (else null; and off it, put elsewhere by the
  // world, no longer: a teleport there left you gliding for good, the walk never started again). (jump.js jumpOf, relief.js liftOf, hd_level.js)
  function landedOn(p) {
    const a = p.leapAt;
    if (!a) return null;
    if (Math.round(p.x) !== a.x || Math.round(p.y) !== a.y || (walking && p.walking)) { p.leapAt = null; return null; }
    return a.z;
  }
  // render.js, a frame of yours on the ground: at the middle of the tile you came down on, the walk goes on if a way is held
  function after(p) {
    if (p.leapAt && Math.abs(p.x - p.leapAt.x) < 1e-3 && Math.abs(p.y - p.leapAt.y) < 1e-3) { p.leapAt = null; if (p.jumpNext) { p.jumpNext = false; jumpKey(); } else if (held()) syncWalk(); }
  }
  // What jump.js jumping() draws for you in the air: as a jump's, its height over the level you left
  function body(p, now) {
    if (!L || !p.e || p.e.kind !== "agent" || p.e.id !== myId) return null;
    const ground = settleAt(L.tx, L.ty, L.z + 1e-6), v0 = V0();
    const now1 = L.t < .03 ? "takeoff" : L.vz < 0 && L.z - ground < .12 ? "touch" : L.vz > .4 * v0 ? "rise" : L.vz < -.3 * v0 ? "fall" : "apex";
    const pose = ORDER[L.pi = Math.max(L.pi || 0, ORDER.indexOf(now1))];   // (one after the other, never back: a touch over the start of a step, then its edge, flashed)
    const k = Math.cos(HdLook.cam.pitch * Math.PI / 180);    // (a height as the eye sees it, as the land's levels are: a level up drawn 16 px up landed a few px off it)
    const c = C === null ? L.z0 : C;
    return {body: (L.z - c) * RELIEF_STEP * k, ground: (ground - c) * RELIEF_STEP * k, air: false, squash: false, tuck: true, pose, leap: true};
  }
  // The level you are drawn from (hd_level.js): from the jump on, it goes towards where you are a px a frame at the
  // most (CAM), in the air towards the ground under you, and after it to the level you would be drawn from; then it is
  // that again. (Up a step the land went down 16 px in a frame as you came down on it, the eye easing after it.) off:
  // how far that is from it, levels (jump.js jumping adds it to your body)
  let C = null, Ct = 0, off = 0, air = false;
  const CAM = 60 / RELIEF_STEP;
  function cam(natural, now) {
    if (C === null) { off = 0; return natural; }
    const dt = Math.min(.1, Math.max(0, (now - Ct) / 1000)), step = CAM * dt;
    Ct = now;
    if (L) { const goal = settleAt(L.tx, L.ty, L.z + 1e-6); C += Math.max(-step, Math.min(step, goal - C)); off = 0; air = true; return C; }
    // (on the ground: what is left between the two goes, a px a frame, while the eye goes with you as it does: it
    // chased you at a px a frame, and running down a flight of steps after a jump you ran away from it, 5 px a frame
    // down the screen)
    if (air) { off = natural - C; air = false; }          // (just down: from then on only the difference left goes)
    off -= Math.sign(off) * Math.min(Math.abs(off), step);
    if (Math.abs(off) < 1e-3) { C = null; off = 0; return natural; }
    C = natural - off;
    return C;
  }
  // jump.js jumping: you on the ground, drawn from that level: lifted by the difference (art px as the eye sees them)
  const lift = (p) => (off && p.e && p.e.kind === "agent" && p.e.id === myId ? off * RELIEF_STEP * Math.cos(HdLook.cam.pitch * Math.PI / 180) : 0);
  // hd_level.js: the level you stand at (the ground under you) and the one you are drawn from (the one you left)
  const level = () => (L ? [settleAt(L.tx, L.ty, L.z + 1e-6), L.z0] : null);
  return {leapable, can, due, start, frame, body, level, landedOn, after, cam, lift, on: () => !!L, gliding: () => { const p = ents.get("agent" + myId); return !!(p && p.leapAt && landedOn(p) !== null); }, get state() { return L; }};
})();
