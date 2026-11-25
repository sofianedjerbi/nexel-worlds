// The frame loop: who walks, the camera, the land coming in, what moves on by itself. The world is drawn by the HD
// look (hd.js) after it.

// =====================================================================================
//  Frame
// =====================================================================================
let lastT = performance.now(), arrivingNow = true;
const LAND_MS = 3 * (window.__pace || 1), HOLD_MS = 2500;      // (__pace: only in the browser tests, whose pages' clocks run faster, tests/e2e/clock.py: the land's share of a frame is the machine's time, not the game's)
let goodAt = 0;                // when the land where you are was last all there (a frame drawn whole)
const WATCH = {x: 0, y: 0, z: 0, free: true};      // (the eye of who watches: render.js, hd.js)
// A FRAME, its parts in their order, here and nowhere else: the way out's marks (wayshow.js), is there a picture of the world (hd.js begin), the game's own step (update), the HD look's
// picture of it (hd.js end). (hd.js and wayshow.js each put a function of theirs round `frame` as they loaded, voxels.js and hd.js round drawTile and arriveBlock: what ran, and in what order,
// hung on the order of the script tags.)
function frame(now) {
  requestAnimationFrame(frame);
  const t0 = performance.now();
  WayShow.frame(); HdLook.begin(); update(now); HdLook.end(now, t0);
}
function update(now) {
  const began = performance.now();
  const dt = Math.max(0, Math.min(.1, (now - lastT) / 1000)); lastT = now;   // (never back in time: a frame stamped before the last one moved every body standing still by 0/0, for good)
  const t = now / 1000;
  for (const p of ents.values()) {
    if (p.e && p.e.kind === "agent" && p.e.id === myId && Leap.on()) { Leap.frame(p, dt, now); continue; }   // you in the air (leap.js)
    if (p.e && p.e.kind === "agent" && p.e.id === myId && walking && p.walking) { walkOn(p, dt, now); continue; }   // your own walk (walk.js)
    const dx = p.tx - p.x, dy = p.ty - p.y, d = Math.hypot(dx, dy);
    // people walk 5 tiles/s (10 sprinting); animals amble, so each of their steps takes most of the pause between them
    // (a scared animal: exactly the server's pace, a tile every FLEE_STRIDE: slower and it fell behind, then snapped)
    // (an animal that the world moves faster than it ambles, a tusker trotting into line or ending its charge, goes at
    // the world's pace, p.pace, state.js; and one that paws the ground or stands dazed is where it is: it was drawn
    // most of a tile behind, sliding into place while it pawed. "it glitches a few pixels... when doing key moves")
    const amble = p.e && AMBLE[p.e.kind] ? Math.max(p.e.scared ? 1 / RULES.flee_stride : AMBLE[p.e.kind], p.pace || 0, p.e.kind === "tusker" && p.e.act ? 8 : 0) : 0;
    const run = !!(p.running || (p.e && p.e.run)), person = !!p.e && p.e.kind === "agent";
    const pace = Climb.paceOf(p) || (person ? speedAt(Math.round(p.x), Math.round(p.y), p, run) : run ? RULES.pace.sprint : amble || RULES.pace.walk);      // (up or down a ladder: rung by rung, climbing.js; a person's, in the water too: walk.js speedAt)
    const jp = d > 0 && d <= 1.5 && !Leap.landing(p) ? jumpPace(p, p.tx - (Math.abs(dx) > 1e-3 ? Math.sign(dx) : 0), p.ty - (Math.abs(dy) > 1e-3 ? Math.sign(dy) : 0), p.tx, p.ty) : Infinity;   // (up or down a step: as long as its jump takes, jump.js; it was squeezed into a step's time)
    // (any other body a tile behind or more goes a little quicker, and is put straight there only past 2.5 tiles: the world's
    //  ticks come unevenly (a scared cow's tiles 261 to 333 ms apart for its 300), it fell half a tile behind, and the next tile
    //  made it 1.53 off: past 1.5 it went at 8 tiles a second, .8 of a tile in a frame, a snap every few tiles: "it teleported")
    const mine = p.e && p.e.kind === "agent" && p.e.id === myId, far = d > (mine ? LEAD[1] + 2 : 2.5);   // (you, a few tiles behind where the world has you as your walk ends: walked there, a little quicker. It was 8 tiles a second: at the foot of the cave stairs, a teleport)
    const step = (far ? d * 8 : Math.min(pace, jp) * (d > (mine ? 1.5 : 1) ? 1.3 : 1.05)) * dt;
    if (d <= step) { p.x = p.tx; p.y = p.ty; Leap.after(p); }
    else if (far) { p.x += dx / d * step; p.y += dy / d * step; }    // far behind (lag, teleport): straight there
    else if (Math.abs(dx) > 1e-3 && Math.abs(dy) > 1e-3) {              // on the grid, one axis at a time: line up first
      if (Math.abs(dx) < Math.abs(dy)) p.x += Math.sign(dx) * Math.min(step, Math.abs(dx)); else p.y += Math.sign(dy) * Math.min(step, Math.abs(dy));
    } else { p.x += dx / d * step; p.y += dy / d * step; }
  }
  cam.lift = 0;                                      // (art px the camera is lifted with you: the eye's height, curve.js)
  if (me && myId !== null) {
    if (HdLook.eye && HdLook.eye.watch) HdLook.eye = null;      // (in the world now: the eye is on you)
    const p = ents.get("agent" + myId);
    if (p) {                                         // (you are drawn lifted on high ground: centre that; falling: you, not the ground you left; jump.js)
      const pan = Build.pan(dt);                      // (build mode: half way to the cursor)
      const pl = BodyPlace.of(p);                     // (on a ladder, in a fall: where the body is drawn, body_place.js)
      cam.x = camT.x = p.x + pan.x + pl.dx; cam.lift = liftOf(p) / zoom + pl.eye + fallShake(now); cam.y = camT.y = p.y + pan.y + pl.dy - cam.lift / P;
      // (the land drawn where you are drawn, found: a tile within APART layers' rows of you, in your column or two each
      // side, whose top is there, or the wall between two; none: you are away from it, state.js. Under it if the land
      // round your tile is over you, else over it; high: far over the land beside you, a tower's top, a pillar's)
      const z = liftOf(p) / zoom / RELIEF_STEP, tx = Math.round(p.x), ty = Math.round(p.y), lt = RELIEF_STEP / 16, r = ty - z * lt;   // (lt: tiles a level is drawn up)
      let found = null, high = topAt(tx, ty), low = 1e9;
      for (const dx of [0, -1, 1, -2, 2]) for (let y2 = ty - APART * lt, last = null; y2 <= ty + APART * lt && found === null; y2++) { const top = topAt(tx + dx, y2), r2 = y2 - top * lt; if (Math.abs(r2 - r) <= 1 || (last !== null && last < r && r < r2)) found = top; last = r2; }
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const top = topAt(tx + dx, ty + dy); high = Math.max(high, top); low = Math.min(low, top); }
      away.on = found === null; away.y = p.y + pan.y; away.shift = found !== null && Math.abs(found) > APART / 2 ? found * lt : 0; away.sky = high - z <= APART; away.high = z - low > APART; away.z = z; away.t = now;
    }
    else if (meObs) { cam.x = camT.x = meObs.self.x; cam.y = camT.y = meObs.self.y; away.on = away.high = false; away.y = cam.y; away.shift = 0; }
    away.a = Math.abs(cam.y - away.y) > 40 || Math.abs(+away.on - away.a) < .02 ? +away.on : away.a + (+away.on - away.a) * (1 - Math.exp(-dt / .12));   // (a jump a long way: at once)
  } else {
    away.on = away.high = false; away.a = 0; away.shift = 0; away.y = cam.y;
    if (follow) {
      const a = [...ents.values()].find((p) => p.e && p.e.kind === "agent" && p.e.name === follow);
      const b = a || agents.find((q) => q.name === follow);
      if (b) { camT.x = b.x; camT.y = b.y; if (!a) { cam.x = b.x; cam.y = b.y; } }
    }
    const k = 1 - Math.pow(.002, dt); cam.x += (camT.x - cam.x) * k; cam.y += (camT.y - cam.y) * k;
    // watching, not in the world (?follow=, the first screen gone): the HD look's eye is the camera, at the land's top there (hd.js eye)
    if (!HdLook.eye && $("joinbox").style.display === "none") HdLook.eye = Object.assign(() => Object.assign(WATCH, {x: cam.x, y: cam.y, z: topAt(Math.round(cam.x), Math.round(cam.y))}), {watch: true});
  }
  const [vx, vy, vw, vh0] = viewRect(2), vh = vh0 + 6;   // (+6 rows south: high ground there is drawn up into view)
  const inRect = (x, y, w, h) => { const out = []; for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++) for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++) { const b = blocks.get(bkey(bx, by)); if (b) out.push(b); } return out; };
  const vis = inRect(vx, vy, vw, vh);
  trackMe();
  // Land coming in (a new block's ground, tiles to draw again, raised ground and water: relief.js) is built a little
  // a frame, all of it within LAND_MS: what is on the screen first, then what is about to be, then the rest of what
  // was asked for (state.js: six tiles out). More of the frame while something on the screen is still missing, most
  // of it while you arrive (nothing is shown yet).
  const [qx, qy, qw, qh] = viewRect(0), onScreen = (b) => b.bx * B < qx + qw && (b.bx + 1) * B > qx && b.by * B < qy + qh + 6 && (b.by + 1) * B > qy;
  const [ax, ay, aw, ah] = viewRect(6), rank = (b) => (onScreen(b) ? 0 : vis.includes(b) ? 1 : 2);
  const coming = inRect(ax, ay, aw, ah + 6).sort((a, b) => rank(a) - rank(b));
  const landFrom = performance.now(), landUntil = landFrom + (arrivingNow ? LAND_MS * 4 : coming.some((b) => !Voxels.made(b) && onScreen(b)) ? LAND_MS * 2.5 : LAND_MS);
  // (a block come in: nothing to paint, the HD look makes its own land (tiles.js): its beds looked at again, one box (waterbed.js), every tile of it as drawn again (hd.js);
  //  a tile drawn again: the clear water's beds round it, its chunk of the HD look's land)
  for (const b of coming) if (!b.drawn) { const x0 = b.bx * B, y0 = b.by * B; arriveBlock(b); WaterBed.changed(x0, y0); WaterBed.changed(x0 + B - 1, y0 + B - 1); HdLook.touchBox(x0, y0, x0 + B - 1, y0 + B - 1); }
  for (let n = 0; dirtyTiles.length && (n++ & 15 || performance.now() < landUntil);) { const yy = dirtyTiles.pop(), xx = dirtyTiles.pop(); drawTile(xx, yy); WaterBed.changed(xx, yy); HdLook.touch(xx, yy); }
  Voxels.work(coming, landUntil);                    // (its beds and its sea: voxels.js)
  const landMs = performance.now() - landFrom;

  // The world is drawn by the HD look (hd.js, after this frame, on a canvas of its own): here nothing of it is painted.
  const S = TS(), [ox, oy] = screenOrigin(S);
  Curve.frame(ox, oy, S, now);                       // (the curved world's line: the HD look's sky, curve.js)
  const hereBlock = blocks.get(bkey(Math.floor(cam.x / B), Math.floor((away.a >= 1 ? away.y : cam.y + away.shift) / B)));
  const allShown = vis.every((b) => !onScreen(b) || Voxels.made(b));
  arrivingNow = (arrivingNow || !hereBlock || !Voxels.made(hereBlock)) && !allShown;   // (from arriving until all of it is ready)
  const worldReady = !arrivingNow;
  // A long way at once (a teleport, waking again after a death): until the land there has come, the screen keeps the
  // picture it had. Held for HOLD_MS at the most once some of the land there is ready; after that, what has come.
  const lacking = !!me && (!hereBlock || !worldReady), late = lacking && goodAt > 0 && now - goodAt >= HOLD_MS && (now - goodAt >= 4 * HOLD_MS || vis.some((b) => onScreen(b) && Voxels.made(b)));      // (...and while none of it has come at all, four times as long: a busy machine)
  if (!lacking) goodAt = now; else if (!late && goodAt > 0) { slowFrame(dt, false); return; }
  slowFrame(dt, worldReady);
  // (where people are: a gate or a door opens for someone beside it. Not for a hen: animals work neither, sim/animals.py)
  occupied = new Set([...ents.values()].filter((p) => p.e && p.e.kind === "agent" && !Floors.rise(p)).map((p) => Math.round(p.x) + "," + Math.round(p.y)));   // (on the land: someone upstairs over a door does not open it)
  Voxels.still(vis, t);                     // (the water's picture the HD look lays on its water, voxels.js)
  // what moves on by itself: drops hopping out (their sound as they land), orbs flying to you, poofs, dust, plucked flowers: their state goes on
  // here, a step each (loot.js, xp.js, effects.js); the HD look draws them (hd_fx.js)
  stepLoot(now); stepOrbs(dt); stepEffects(dt, performance.now());
  drawXp();
  foodPreview();
  swingDoors(t);
  updateActions();
  Build.tick();                                      // (plans that could not be done go; out of the mode when you are gone: build.js)
  floats = opt("floats") ? floats.filter((f) => t - f.t < 1.4) : [];
  perfFrame(now, performance.now() - began, landMs);   // (/perf: debug.js)
}
function outlined(text, x, y, color) {
  ctx.fillStyle = "#5b3f36";
  for (const [a, b] of [[-1, 0], [1, 0], [0, -1], [0, 1], [1, 1]]) ctx.fillText(text, x + a, y + b);
  ctx.fillStyle = color; ctx.fillText(text, x, y);
}
// Doors and gates near you swing open for whoever is by them, with their sound (structures.js doorFrame, sprites.js
// gate): the HD look draws them open or shut by itself (hd_things.js); here their state and the latch's sound go on.
// The doors round you are looked for twice a second, ticked every frame.
let doorList = [], doorScan = -1e9;
function swingDoors(t) {
  const s = me && myPos(), now = performance.now(); if (!s) return;
  if (now - doorScan > 500) { doorScan = now; doorList = []; for (let y = s.y - 12; y <= s.y + 12; y++) for (let x = s.x - 16; x <= s.x + 16; x++) { const c = combAt(x, y); if (c === "+" || c === "g") doorList.push([x, y, c]); } }
  for (const [x, y, c] of doorList) if (combAt(x, y) === c) { if (c === "+") Structures.doorFrame(x, y); else objectSprite("g", x, y, t); }
}
