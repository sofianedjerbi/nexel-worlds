// Leap's parts (leap.js), each a factory of its own: the auto-jump up steps (LeapSteps), off a ledge and when a jump is
// due (LeapLedge), the landing (LeapLand), a frame in the air (LeapAir), the level you are drawn from (LeapEye).

// The auto-jump up steps (leap.js): when a jump just clears a step's edge, which steps are jumped through the air,
// the first step up ahead, and the whole jump up a flight of steps.
//   LeapSteps(S, K) -> {T1, leapable, ahead, stairArc}
const LeapSteps = (S, K) => {
  const {G, V0} = K;
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
  return {T1, leapable, ahead, stairArc};
};

// Off a ledge, and when a jump is due (leap.js): a walk over an edge a fall's height or more, whether a jump meets the
// land's face, how far to walk before the auto-jump.
//   LeapLedge(S, K) -> {dropDue, ledge, hits, room, due}
const LeapLedge = (S, K) => {
  const {G, T1, ahead, can, fits, tileOf} = K;
  // WALKING OFF A LEDGE a fall's height or more (FALL.from; a step less is walked down, jump.js STEPDOWN): you go on over it at the walk's speed and come down as a thrown thing does, the same
  // fall as a jump's (frame, cam), not jump.js fallOf's (the eye on the ground under the edge in a frame, the body 55 px up the screen at once,
  // "weird issues when jumping from high heights"). This frame's walk (t s) takes you over the edge: -> true
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
    const z = settleAt(nx, ny, h + 1e-6);
    return z <= h - FALL.from && !Climb.onLadder(x, y, h, nx, ny, z);   // (down a ladder: climbed rung by rung, walk.js Climb.pace, not fallen past its foot)
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
  return {dropDue, ledge, hits, room, due};
};

// The landing (leap.js): down on the ground, the world told the way you went, on to the tile's middle, the walk on.
//   LeapLand(S, K) -> {land, landedOn, after}
const LeapLand = (S, K) => {
  const {can, fits, held, leapable, start} = K;
  // Down on the ground at `z`: the world is told the way you went; the walk goes on if a way is held
  function land(p, now, z) {
    const path = S.L.path.filter((t, i, a) => !i || t[0] !== a[i - 1][0] || t[1] !== a[i - 1][1]), run = S.L.run, z0 = S.L.z0;
    const h = held(), past = h && (p.x - p.tx) * h[0] + (p.y - p.ty) * h[1] >= 0 && Math.abs((p.x - p.tx) * h[1]) + Math.abs((p.y - p.ty) * h[0]) < .01 && fits(p.tx + h[0], p.ty + h[1], z);   // (and room on the way held: down by a wide hole's far wall, on into the wall was a step up four levels drawn as its arc, the body 20 px up and down)
    const st = BodyPlace.state(p); S.L = null; st.settle = now; fallWind(-1);
    // (the eye's way left to go, from this frame on: the body drawn on the ground is lifted by it (lift) from the frame
    //  you land, not at the eye's next look (cam): else the landing frame draws you with none, 20 px up from the arc's
    //  last frame, a hole's floor four down under an eye two levels behind, then down again)
    if (S.C !== null && S.air) { S.off = z - S.C; S.air = false; }
    // (where you came down on the tile, off its middle: you go to it, at the walk's pace, before the walk goes on. On
    // the way you are on that tile and its height: between it and the one before, the step's own arc drew you a
    // second time, and half a level low. Past its middle the way you go, the walk goes on from there)
    // (come down against a step a layer up, the way to it held, auto-jump on: up it at once at the speed you had, as
    //  walking into it does. You were put back to the tile's middle first and walked on from a standstill: "when
    //  sprinting + jumping the player is getting hit by the block AFTER jumping and it loses all his velocity")
    const nx = h && p.tx + h[0], ny = h && p.ty + h[1];
    const bump = !past && h && autoJump() && solidAt(nx, ny, z + 1) && landAt(z, nx, ny, p.tx, p.ty) === z + 1 && leapable(p.tx, p.ty, z, nx, ny);
    S.landed0 = {x: p.x, y: p.y, tx: p.tx, ty: p.ty, z, h, past, bump, can: can(p), up: !!h && solidAt(nx, ny, z + 1), to: h && landAt(z, nx, ny, p.tx, p.ty), room: !!h && leapable(p.tx, p.ty, z, nx, ny)};   // (Leap.landed: shown by a test that fails)
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
  // world, null too: else a teleport there leaves you gliding for good, the walk never on again). (jump.js jumpOf, relief.js liftOf, hd_level.js)
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
  return {land, landedOn, after};
};

// A frame in the air (leap.js, render.js): the jump's arc, in steps of the planned size, its tiles told to the world.
//   LeapAir(S, K) -> {frame, step}
const LeapAir = (S, K) => {
  const {G, V0, fits, held, hits, land, stairArc, tileOf} = K;
  // A frame in the air (render.js, in place of the walk). A long one (render.js: up to 0.1 s) in pieces of a 60th of a second at
  // the most, the step the jump is planned in (hits, stairArc: 1/120 s a step): the body rises over the step it clears at the
  // place planned, a frame every 100 ms as at 60 a second
  function frame(p, dt, now) {
    const n = Math.max(1, Math.ceil(dt * 60 - .01));
    let i = 0;
    for (; i < n && S.L; i++) step(p, dt / n, now);
    if (!S.L && i < n && walking && p.walking) walkOn(p, (n - i) * dt / n, now);   // (down in the frame, the walk on: its time left is walked, so a sprint over steps keeps its speed)
  }
  function step(p, dt, now) {
    if (!S.L) return;
    S.L.t += dt;
    const h = held(), cap = S.L.cap || RULES.pace[S.L.run ? "sprint" : "walk"];   // (a planned jump up a flight: steered at its own speed, not the walk's)
    if (h) {                                               // steering: the way held pulls your speed towards it, a little
      const k = Math.min(1, LEAP.steer * dt / cap);
      S.L.vx += (h[0] * cap - S.L.vx) * k; S.L.vy += (h[1] * cap - S.L.vy) * k;
      BodyPlace.face(p, h[0], h[1]);
    }
    const g = G(), z1 = S.L.z + S.L.vz * dt - g * dt * dt / 2;
    S.L.vz -= g * dt;
    for (const [ax, v] of [["x", "vx"], ["y", "vy"]]) {    // along each axis: stopped by the land higher than your feet
      if (!S.L[v]) continue;
      const n = S.L[ax] + S.L[v] * dt, nt = Math.round(n), cur = ax === "x" ? S.L.tx : S.L.ty;
      if (nt !== cur) {
        const [x, y] = ax === "x" ? [nt, S.L.ty] : [S.L.tx, nt];
        if (!fits(x, y, Math.max(z1, S.L.z))) { const m = cur + Math.sign(S.L[v]) * LEAP.margin; S.L[ax] = (S.L[ax] - m) * Math.sign(S.L[v]) > 0 ? cur + Math.sign(S.L[v]) * Math.min(.499, Math.abs(S.L[ax] - cur)) : m; continue; }   // (against it, still pushing: higher up, on it)
        S.L[ax] = n; if (ax === "x") S.L.tx = nt; else S.L.ty = nt;
        S.L.path.push([S.L.tx, S.L.ty]);
        rpc("act", {tool: "leap", args: {path: [[S.L.tx, S.L.ty]], n: trailN, run: S.L.run}});   // (each tile as you come over it: the world goes with you, sim/leaping.py)
      } else S.L[ax] = n;
    }
    const ground = settleAt(S.L.tx, S.L.ty, S.L.z + 1e-6);      // (the ground under where you were: what you come down on)
    if (S.L.drop && ground >= S.L.z0 - 1e-6) { S.L.vz = 0; S.L.z = S.L.z0; p.x = S.L.x; p.y = S.L.y; p.tx = S.L.tx; p.ty = S.L.ty; p.moved = now; return; }   // (still on the ledge: walked on at the walk's speed, nothing falls yet)
    S.L.drop = false;
    if (S.L.vz > 0 && solidAt(S.L.tx, S.L.ty, Math.floor(z1) + 3)) S.L.vz = 0;   // (the head against a ceiling)
    S.L.z = Math.max(z1, Math.min(S.L.z, ground));
    p.x = S.L.x; p.y = S.L.y; p.tx = S.L.tx; p.ty = S.L.ty; p.moved = now;
    if (!myAt || myAt.x !== S.L.tx || myAt.y !== S.L.ty) { myWas = myAt; myAt = {x: S.L.tx, y: S.L.ty, z: ground}; } else myAt.z = ground;
    if (S.L.vz < 0 && S.L.z0 - S.L.z > .5) fallWind(Math.min(1, -S.L.vz * 16 / 600));   // (falling: the wind in your ears, louder and higher with your speed, as a fall's was: audio.js)
    if (S.L.vz <= 0 && S.L.z <= ground + 1e-6) land(p, now, ground);
  }
  return {frame, step};
};

// The level you are drawn from in a jump (leap.js, jump.js, hd_level.js): your body in the air, the eye easing to the
// ground after it, and how it sees a height.
//   LeapEye(S, K) -> {body, cam, lift, seen, level}
const LeapEye = (S, K) => {
  const {ORDER, V0, step} = K;
  // What jump.js jumping() draws for you in the air: as a jump's, its height over the level you left
  function body(p, now) {
    if (!S.L || !p.e || p.e.kind !== "agent" || p.e.id !== myId) return null;
    const ground = settleAt(S.L.tx, S.L.ty, S.L.z + 1e-6), v0 = V0();
    const now1 = S.L.t < .03 ? "takeoff" : S.L.vz < 0 && S.L.z - ground < .12 ? "touch" : S.L.vz > .4 * v0 ? "rise" : S.L.vz < -.3 * v0 ? "fall" : "apex";
    const pose = ORDER[S.L.pi = Math.max(S.L.pi || 0, ORDER.indexOf(now1))];   // (one after the other, never back: a touch over the start of a step, then its edge, flashed)
    const c = S.C === null ? S.L.z0 : S.C;
    return {body: S.L.z - c, ground: ground - c, air: false, squash: false, tuck: true, pose, leap: true};
  }
  // The level you are drawn from (hd_level.js): from the jump on, it goes towards where you are a px a frame at the
  // most (CAM), in the air towards the ground under you, and after it to the level you would be drawn from; then it is
  // that again. (Up a step the land went down 16 px in a frame as you came down on it, the eye easing after it.) off:
  // how far that is from it, levels (jump.js jumping adds it to your body)
  const CAM = 60 / RELIEF_STEP;
  function cam(natural, now) {
    if (S.C === null) { S.off = 0; return natural; }
    const dt = Math.min(.1, Math.max(0, (now - S.Ct) / 1000)), rate = (d) => Math.min(2 * CAM, Math.max(CAM, (Math.abs(d) - 1) * 10)) * dt;   // (on the ground after a jump: a px a frame for a level or less; past that it closes a tenth of the way left every 1/100 s, twice that at the most (CAM: a px a frame at the pitch's flattest; 5 px a frame zoomed in, 9 at 4 x was seen as a jolt): down off a ledge it kept a px a frame, the land scrolling a second after you were down)
    S.Ct = now;
    if (S.L) { const g = settleAt(S.L.tx, S.L.ty, S.L.z + 1e-6), goal = g >= S.L.z0 ? g : Math.max(g, Math.min(S.L.z0, S.L.z)), step = g >= S.L.z0 ? CAM * dt : Math.max(CAM * dt, Math.abs(goal - S.C) * Math.min(1, 14 * dt));   // (in the air: up onto higher ground, a px a frame to its level; down, with your body once it is under the level you left, never under the ground (not a px a frame to the ground under you: the land would rush under a jump's top, or lag a second behind a fall))
      S.C += Math.max(-step, Math.min(step, goal - S.C)); S.off = 0; S.air = true; return S.C; }
    // (on the ground: what is left between the two goes, a px a frame, while the eye goes with you as it does: it
    // chased you at a px a frame, and running down a flight of steps after a jump you ran away from it, 5 px a frame
    // down the screen)
    if (S.air) { S.off = natural - S.C; S.air = false; }          // (just down: from then on only the difference left goes)
    S.off -= Math.sign(S.off) * Math.min(Math.abs(S.off), rate(S.off));
    if (Math.abs(S.off) < 1e-3) { S.C = null; S.off = 0; return natural; }
    S.C = natural - S.off;
    return S.C;
  }
  // jump.js jumping: you on the ground, drawn from that level: lifted by the difference (levels as the eye sees them)
  const lift = (p) => (S.off && p.e && p.e.kind === "agent" && p.e.id === myId ? S.off : 0);
  // how the eye sees a height of yours drawn from its own level (C), as the land's levels: its pitch's cosine (a level up drawn 16 px up landed a few px off it).
  // The picture's (BodyPlace's px), not the height's: in the height, your place's z said 1 level at a hop's top, the table's 1.25 (RULES.leap.top) seen from 36 degrees
  const seen = () => Math.cos(HdLook.cam.pitch * Math.PI / 180);
  // hd_level.js: the level you stand at (the ground under you) and the one you are drawn from (the one you left)
  const level = () => (S.L ? [settleAt(S.L.tx, S.L.ty, S.L.z + 1e-6), S.L.z0] : null);
  return {body, cam, lift, seen, level};
};

