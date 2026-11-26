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
  const G = () => JUMP.g, V0 = () => Math.sqrt(2 * G() * JUMP.top);   // levels/s2; levels/s up as you leave the ground
  const tileOf = (x, y) => [Math.round(x), Math.round(y)];
  // the body (feet at level z, two cells tall) fits on tile (x, y)
  const fits = (x, y, z) => { const c = Math.floor(z + 1e-6); return !solidAt(x, y, c + 1) && !solidAt(x, y, c + 2); };
  const held = () => { const k = [...keys].reverse().find((k) => KEYDIR[k]); return k ? DIRV[KEYDIR[k]] : null; };
  // May you jump from where you are? (in the water, in a boat, on a ladder, falling, building: the old ways)
  function can(p, ledge) {   // (ledge: walking off one: the fall jump.js begins on the tile before the edge does not stop it, it is taken over)
    const [x, y] = tileOf(p.x, p.y), t = tile(x, y), h = myZ(x, y);
    // (room over your head for the jump's top: under a roof, in a tunnel or a cave's stair, the old way. A jump there
    // hit the roof, its tiles not the world's: you were drawn on the land over it and put back where the world had you)
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
    L = {t: 0, x: p.x, y: p.y, z: myZ(x, y), vx: w ? w[0] * sp : 0, vy: w ? w[1] * sp : 0, vz, path: [], run, tx: x, ty: y, cap};
    L.z0 = L.z; L.drop = vz === 0 && sp > 0; if (C === null) { C = L.z; Ct = now; }   // (drop: off a ledge, walking: on its level till you are over the edge, frame)
    if (w) BodyPlace.face(p, w[0], w[1]);
    if (vz > 0) jumpDust(p, 3, .8);
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
  // The first step a layer up on the way (dx, dy), within two tiles: {d: tiles to its edge, stairs: another a layer up just behind it}, or null (a drop, a wall, nothing near)
  function ahead(p, dx, dy) {
    const s = dx || dy, x = Math.round(p.x), y = Math.round(p.y), h = myZ(x, y), at = dx ? p.x : p.y;
    for (let k = 1; k <= 2; k++) {
      const nx = x + dx * k, ny = y + dy * k, px = nx - dx, py = ny - dy, d = ((dx ? x : y) + (k - .5) * s - at) * s;   // (d: tiles to the edge before it)
      if (d < 0) continue;
      if (solidAt(nx, ny, h + 1)) return landAt(h, nx, ny, px, py) === h + 1 && leapable(px, py, h, nx, ny)
        ? {d, stairs: solidAt(nx + dx, ny + dy, h + 2) && landAt(h + 1, nx + dx, ny + dy, nx, ny) === h + 2 && leapable(nx, ny, h + 1, nx + dx, ny + dy)} : null;
      if (!solidAt(nx, ny, h)) return null;
    }
    return null;
  }
  // UP A FLIGHT OF STEPS (a step a layer up and another just behind it): the whole jump (a block and a quarter, a tile and a half long at a walk) came down past the next
  // step's edge, and you hung against its face at every step ("when climbing (walking stairs up) ... i hit the block above when automatically jumping"). Here each jump
  // is planned: over the edge just above it, down on the step in time for the next: from d before the edge at v, over it at t = d / v, as low as clears it
  // (vz = 1 / t + g t / 2), and as fast as lands it dn before the next edge (2 v^2 / g: from there the next one goes at your pace): a flight is walked at a walk's
  // pace from its second step, run at 5.2 tiles a second (the most a jump clears steps a tile deep at). Never higher than the whole jump: from near the edge, slower.
  function stairArc(p, w, sp) {
    const a = ahead(p, w[0], w[1]); if (!a) return null;
    if (!a.stairs) return a.d < sp * T1() ? {v: Math.max(.5, a.d) / T1(), vz: V0()} : null;   // (one step, too near to clear its edge at your pace (off the step before it, the top of a flight): the whole jump, a little slower, over it)
    const g = G(), d = Math.max(.02, a.d), dn = Math.min(.9, 2 * sp * sp / g);   // (dn: where the next jump would go from at your pace: this one comes down there)
    let v = Math.min(sp, Math.sqrt(g * d * (1 + d - dn) / 2)), t = d / v, vz = 1 / t + g * t / 2 + .15;
    if (vz > V0()) { vz = V0(); v = Math.min(sp, d / T1()); }
    return {v, vz};
  }
  // WALKING OFF A LEDGE a fall's height or more (FALL.from; a step less is walked down, jump.js STEPDOWN): you go on over it at the walk's speed and come down as a thrown thing does, the same
  // fall as a jump's (frame, cam): it was a fall of its own (jump.js fallOf), the eye put on the ground under the edge in a frame, the body 55 px up the screen at once,
  // "weird issues when jumping from high heights". This frame's walk (t s) takes you over the edge: -> true
  function dropDue(p, w, t) {
    const [dx, dy] = DIRV[w.dir], s = dx || dy, x = Math.round(p.x), y = Math.round(p.y);
    const d = ((dx ? x : y) + .5 * s - (dx ? p.x : p.y)) * s, v = RULES.pace[w.run && sprinting() ? "sprint" : "walk"];
    return d >= 0 && d <= Math.max(.25, v * t + 1e-3) && ledge(p, dx, dy);
  }
  // Is the next tile the way (dx, dy) a ledge the jump's fall takes you off? A fall's height or more down, with room to go over it (no overhang in
  // front; a low roof over your head is none: you do not rise), into water too. The one answer: dropDue goes over it; jump.js jumpOf and fallOf leave it to it; the
  // world's walk waits at its edge for it, by the same cells (sim/movement.py at_ledge). Each asked its own: off a ledge into water or in a low tunnel,
  // nothing drew the fall (the body 23 px down the screen in a frame) and the world waited a second for a jump that never came.
  function ledge(p, dx, dy) {
    const x = Math.round(p.x), y = Math.round(p.y), h = myZ(x, y), nx = x + dx, ny = y + dy;
    if (!can(p, true) || solidAt(nx, ny, h + 1) || solidAt(nx, ny, h + 2)) return false;
    return settleAt(nx, ny, h + 1e-6) <= h - FALL.from;
  }
  // Would a jump from where p is, at v tiles/s the way w and vz levels/s up, meet the face of the land before it comes down? Played ahead as frame plays it (1/120 s a
  // step, the same stops). A run up a hill with the jump key: the whole jump at a run is four tiles long, and came down past the next rise, against its face (18 frames
  // up a hill seven high, "sprinting uphill still do the same issue"); slower, it comes down before the rise instead, and the next jump goes up it (land: on at once).
  function hits(p, w, v, vz) {
    let [tx, ty] = tileOf(p.x, p.y), a = w[0] ? p.x : p.y, z = myZ(tx, ty);
    const dt = 1 / 120, g = G(), s = w[0] || w[1];
    for (let i = 0; i < 240; i++) {
      const z1 = z + vz * dt - g * dt * dt / 2, n = a + s * v * dt, nt = Math.round(n), cur = w[0] ? tx : ty;
      vz -= g * dt;
      if (nt !== cur) { const [X, Y] = w[0] ? [nt, ty] : [tx, nt]; if (!fits(X, Y, Math.max(z1, z))) return true; if (w[0]) tx = nt; else ty = nt; }
      a = n;
      const ground = settleAt(tx, ty, z + 1e-6);
      if (vz > 0 && solidAt(tx, ty, Math.floor(z1) + 3)) vz = 0;
      z = Math.max(z1, Math.min(z, ground));
      if (vz <= 0 && z <= ground + 1e-6) return false;
    }
    return false;
  }
  // -> tiles to walk before the auto-jump is due (Infinity: none ahead). walk.js walks no further than a 60th of a second's walk past it in a frame,
  // however long the frame (0.1 s is a tile at a sprint): the jump leaves where stairArc planned it, far enough from the edge to keep its speed
  function room(p, w) {
    if (!can(p)) return Infinity;
    const [dx, dy] = DIRV[w.dir], v = RULES.pace[w.run && sprinting() ? "sprint" : "walk"], a = ahead(p, dx, dy), need = v * T1() + .08;
    return a ? a.d - (a.stairs ? Math.max(need, Math.min(1, 2 * v * v / G())) : need) : Infinity;   // (up a flight: from as far as its planned jump goes, stairArc)
  }
  const due = (p, w) => room(p, w) <= 1e-6;
  // A frame in the air (render.js, in place of the walk). A long one (render.js: up to 0.1 s) in pieces of a 60th of a second at
  // the most, the step the jump is planned in (hits, stairArc: 1/120 s a step): the body rises over the step it clears at the
  // place planned, a frame every 100 ms as at 60 a second
  function frame(p, dt, now) {
    const n = Math.max(1, Math.ceil(dt * 60 - .01));
    let i = 0;
    for (; i < n && L; i++) step(p, dt / n, now);
    if (!L && i < n && walking && p.walking) walkOn(p, (n - i) * dt / n, now);   // (down in the frame, the walk on: its time left is walked, so a sprint over steps keeps its speed)
  }
  function step(p, dt, now) {
    if (!L) return;
    L.t += dt;
    const h = held(), cap = L.cap || RULES.pace[L.run ? "sprint" : "walk"];   // (a planned jump up a flight: steered at its own speed, not the walk's)
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
        if (!fits(x, y, Math.max(z1, L.z))) { const m = cur + Math.sign(L[v]) * LEAP.margin; L[ax] = (L[ax] - m) * Math.sign(L[v]) > 0 ? cur + Math.sign(L[v]) * Math.min(.499, Math.abs(L[ax] - cur)) : m; continue; }   // (against it, still pushing: higher up, on it)
        L[ax] = n; if (ax === "x") L.tx = nt; else L.ty = nt;
        L.path.push([L.tx, L.ty]);
        rpc("act", {tool: "leap", args: {path: [[L.tx, L.ty]], n: trailN, run: L.run}});   // (each tile as you come over it: the world goes with you, sim/leaping.py)
      } else L[ax] = n;
    }
    const ground = settleAt(L.tx, L.ty, L.z + 1e-6);      // (the ground under where you were: what you come down on)
    if (L.drop && ground >= L.z0 - 1e-6) { L.vz = 0; L.z = L.z0; p.x = L.x; p.y = L.y; p.tx = L.tx; p.ty = L.ty; p.moved = now; return; }   // (still on the ledge: walked on at the walk's speed, nothing falls yet)
    L.drop = false;
    if (L.vz > 0 && solidAt(L.tx, L.ty, Math.floor(z1) + 3)) L.vz = 0;   // (the head against a ceiling)
    L.z = Math.max(z1, Math.min(L.z, ground));
    p.x = L.x; p.y = L.y; p.tx = L.tx; p.ty = L.ty; p.moved = now;
    if (!myAt || myAt.x !== L.tx || myAt.y !== L.ty) { myWas = myAt; myAt = {x: L.tx, y: L.ty, z: ground}; } else myAt.z = ground;
    if (L.vz < 0 && L.z0 - L.z > .5) fallWind(Math.min(1, -L.vz * 16 / 600));   // (falling: the wind in your ears, louder and higher with your speed, as a fall's was: audio.js)
    if (L.vz <= 0 && L.z <= ground + 1e-6) land(p, now, ground);
  }
  // Down on the ground at `z`: the world is told the way you went; the walk goes on if a way is held
  function land(p, now, z) {
    const path = L.path.filter((t, i, a) => !i || t[0] !== a[i - 1][0] || t[1] !== a[i - 1][1]), run = L.run, z0 = L.z0;
    const h = held(), past = h && (p.x - p.tx) * h[0] + (p.y - p.ty) * h[1] >= 0 && Math.abs((p.x - p.tx) * h[1]) + Math.abs((p.y - p.ty) * h[0]) < .01 && fits(p.tx + h[0], p.ty + h[1], z);   // (and room on the way held: down by a wide hole's far wall, on into the wall was a step up four levels drawn as its arc, the body 20 px up and down)
    const st = BodyPlace.state(p); L = null; st.settle = now; fallWind(-1);
    // (the eye's way left to go, from this frame on: the body drawn on the ground is lifted by it (lift) from the frame
    //  you land. It was set at the eye's next look (cam): the landing frame drew you with none, 20 px up from the arc's
    //  last frame, a hole's floor four down under an eye two levels behind, then down again)
    if (C !== null && air) { off = z - C; air = false; }
    // (where you came down on the tile, off its middle: you go to it, at the walk's pace, before the walk goes on. On
    // the way you are on that tile and its height: between it and the one before, the step's own arc drew you a
    // second time, and half a level low. Past its middle the way you go, the walk goes on from there)
    // (come down against a step a layer up, the way to it held, auto-jump on: up it at once at the speed you had, as
    //  walking into it does. You were put back to the tile's middle first and walked on from a standstill: "when
    //  sprinting + jumping the player is getting hit by the block AFTER jumping and it loses all his velocity")
    const nx = h && p.tx + h[0], ny = h && p.ty + h[1];
    const bump = !past && h && autoJump() && solidAt(nx, ny, z + 1) && landAt(z, nx, ny, p.tx, p.ty) === z + 1 && leapable(p.tx, p.ty, z, nx, ny);
    st.leapAt = past || bump ? null : {x: p.tx, y: p.ty, z};
    if (myAt) myAt.z = z;
    if (z0 - z >= FALL.from) {                // (what it costs shown as you land, by the world's own rule: sim/movement.py fell. Waiting for its `fall` event showed it most of a second after)
      const n = (z0 - z - RULES.fall_safe) * RULES.fall_hp; if (n > 0) { st.hurt = n; st.told = now; hurtNow(n); }   // (a server without fall_hp in its rules: NaN, its event says it)
      landed(p, z0 - z, now, true, st); st.bounce = null; }   // (down from high: a fall's landing, jump.js: its dust, its thud; what it cost when the world says, state.js. Not its bounce: the body 12 px up the screen in a frame and back)
    else { jumpDust(p, 4, z < z0 ? 1.3 : 1); sfx(z < z0 ? "thud" : "step", p.tx, p.ty); }
    if (path.length) {
      const [x, y, n] = mark(p.tx, p.ty);
      if (!past) pred = {x, y, until: now + 3000};   // (walking on at once: no stop to wait for. A stop there read as turned back: `cut`, the flight dropped)
      rpc("act", {tool: "leap", args: {land: z, n, run}}).then(() => refresh());   // (the world's own count as soon as it has the fall: hurtNow guessed it)
    } else rpc("act", {tool: "jump", args: {}}).then(() => refresh());
    if (past) { p.tx += h[0]; p.ty += h[1]; syncWalk(); }   // (on into the next tile, as the walk is: the tile behind you read as a step down to it)
    else if (bump) { if (can(p)) start(p, now, {w: h, run}, true); else st.leapAt = {x: p.tx, y: p.ty, z}; }
  }
  // You on the tile you came down on, on your way to its middle: its height (else null; and off it, put elsewhere by the
  // world, no longer: a teleport there left you gliding for good, the walk never started again). (jump.js jumpOf, relief.js liftOf, hd_level.js)
  function landedOn(p) {
    const st = BodyPlace.peek(p), a = st && st.leapAt;
    if (!a) return null;
    if (Math.round(p.x) !== a.x || Math.round(p.y) !== a.y || (walking && p.walking)) { st.leapAt = null; return null; }
    return a.z;
  }
  // render.js, a frame of yours on the ground: at the middle of the tile you came down on, the walk goes on if a way is held
  function after(p) {
    const st = BodyPlace.peek(p), a = st && st.leapAt;
    if (a && Math.abs(p.x - a.x) < 1e-3 && Math.abs(p.y - a.y) < 1e-3) { st.leapAt = null; if (st.jumpNext) { st.jumpNext = false; jumpKey(); } else if (held()) syncWalk(); }
  }
  // What jump.js jumping() draws for you in the air: as a jump's, its height over the level you left
  function body(p, now) {
    if (!L || !p.e || p.e.kind !== "agent" || p.e.id !== myId) return null;
    const ground = settleAt(L.tx, L.ty, L.z + 1e-6), v0 = V0();
    const now1 = L.t < .03 ? "takeoff" : L.vz < 0 && L.z - ground < .12 ? "touch" : L.vz > .4 * v0 ? "rise" : L.vz < -.3 * v0 ? "fall" : "apex";
    const pose = ORDER[L.pi = Math.max(L.pi || 0, ORDER.indexOf(now1))];   // (one after the other, never back: a touch over the start of a step, then its edge, flashed)
    const c = C === null ? L.z0 : C;
    return {body: L.z - c, ground: ground - c, air: false, squash: false, tuck: true, pose, leap: true};
  }
  // The level you are drawn from (hd_level.js): from the jump on, it goes towards where you are a px a frame at the
  // most (CAM), in the air towards the ground under you, and after it to the level you would be drawn from; then it is
  // that again. (Up a step the land went down 16 px in a frame as you came down on it, the eye easing after it.) off:
  // how far that is from it, levels (jump.js jumping adds it to your body)
  let C = null, Ct = 0, off = 0, air = false;
  const CAM = 60 / RELIEF_STEP;
  function cam(natural, now) {
    if (C === null) { off = 0; return natural; }
    const dt = Math.min(.1, Math.max(0, (now - Ct) / 1000)), rate = (d) => Math.min(2 * CAM, Math.max(CAM, (Math.abs(d) - 1) * 10)) * dt;   // (on the ground after a jump: a px a frame for a level or less; past that it closes a tenth of the way left every 1/100 s, twice that at the most (CAM: a px a frame at the pitch's flattest; 5 px a frame zoomed in, 9 at 4 x was seen as a jolt): down off a ledge it kept a px a frame, the land scrolling a second after you were down)
    Ct = now;
    if (L) { const g = settleAt(L.tx, L.ty, L.z + 1e-6), goal = g >= L.z0 ? g : Math.max(g, Math.min(L.z0, L.z)), step = g >= L.z0 ? CAM * dt : Math.max(CAM * dt, Math.abs(goal - C) * Math.min(1, 14 * dt));   // (in the air: up onto higher ground, a px a frame to its level; down, with your body once it is under the level you left, never under the ground (it went a px a frame to the ground under you: the land rushed under a jump's top, or lagged a second behind a fall))
      C += Math.max(-step, Math.min(step, goal - C)); off = 0; air = true; return C; }
    // (on the ground: what is left between the two goes, a px a frame, while the eye goes with you as it does: it
    // chased you at a px a frame, and running down a flight of steps after a jump you ran away from it, 5 px a frame
    // down the screen)
    if (air) { off = natural - C; air = false; }          // (just down: from then on only the difference left goes)
    off -= Math.sign(off) * Math.min(Math.abs(off), rate(off));
    if (Math.abs(off) < 1e-3) { C = null; off = 0; return natural; }
    C = natural - off;
    return C;
  }
  // jump.js jumping: you on the ground, drawn from that level: lifted by the difference (levels as the eye sees them)
  const lift = (p) => (off && p.e && p.e.kind === "agent" && p.e.id === myId ? off : 0);
  // how the eye sees a height of yours drawn from its own level (C), as the land's levels: its pitch's cosine (a level up drawn 16 px up landed a few px off it).
  // The picture's (BodyPlace's px), not the height's: in the height, your place's z said 1 level at a hop's top, the table's 1.25 (RULES.leap.top) seen from 36 degrees
  const seen = () => Math.cos(HdLook.cam.pitch * Math.PI / 180);
  // hd_level.js: the level you stand at (the ground under you) and the one you are drawn from (the one you left)
  const level = () => (L ? [settleAt(L.tx, L.ty, L.z + 1e-6), L.z0] : null);
  return {leapable, can, due, room, dropDue, ledge, start, ahead, frame, body, level, landedOn, after, cam, lift, seen, on: () => !!L, landing: (p) => !!(BodyPlace.peek(p) || {}).leapAt, gliding: () => { const p = ents.get("agent" + myId); return !!(p && landedOn(p) !== null); }, get state() { return L; }};
})();
