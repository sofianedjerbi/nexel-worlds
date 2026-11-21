// The frame loop: who walks, the camera, the land coming in, what moves on by itself. The world is drawn by the HD
// look (hd.js) after it.

// =====================================================================================
//  Frame
// =====================================================================================
let lastT = performance.now(), arrivingNow = true;
const LAND_MS = 3 * (window.__pace || 1), HOLD_MS = 2500;      // (__pace: only in the browser tests, whose pages' clocks run faster, tests/e2e/clock.py: the land's share of a frame is the machine's time, not the game's)
let goodAt = 0;                // when the land where you are was last all there (a frame drawn whole)
const WATCH = {x: 0, y: 0, z: 0, free: true};      // (the eye of who watches: render.js, hd.js)
function frame(now) {
  requestAnimationFrame(frame);
  const began = performance.now();
  const dt = Math.max(0, Math.min(.1, (now - lastT) / 1000)); lastT = now;   // (never back in time: a frame stamped before the last one moved every body standing still by 0/0, for good)
  const t = now / 1000;
  for (const p of ents.values()) {
    if (p.e && p.e.kind === "agent" && p.e.id === myId && walking && p.walking) { walkOn(p, dt, now); continue; }   // your own walk (walk.js)
    const dx = p.tx - p.x, dy = p.ty - p.y, d = Math.hypot(dx, dy);
    // people walk 5 tiles/s (10 sprinting); animals amble, so each of their steps takes most of the pause between them
    // (a scared animal: exactly the server's pace, a tile every FLEE_STRIDE: slower and it fell behind, then snapped)
    // (an animal that the world moves faster than it ambles, a tusker trotting into line or ending its charge, goes at
    // the world's pace, p.pace, state.js; and one that paws the ground or stands dazed is where it is: it was drawn
    // most of a tile behind, sliding into place while it pawed. "it glitches a few pixels... when doing key moves")
    const amble = p.e && AMBLE[p.e.kind] ? Math.max(p.e.scared ? 1 / FLEE_STRIDE : AMBLE[p.e.kind], p.pace || 0, p.e.kind === "tusker" && p.e.act ? 8 : 0) : 0;
    const pace = Climb.paceOf(p) || (p.running || (p.e && p.e.run) ? 10 : amble || 5);      // (up or down a ladder: rung by rung, climbing.js)
    const step = (d > 1.5 ? d * 8 : pace * 1.05) * dt;
    if (d <= step) { p.x = p.tx; p.y = p.ty; }
    else if (d > 1.5) { p.x += dx / d * step; p.y += dy / d * step; }    // far behind (lag, teleport): straight there
    else if (Math.abs(dx) > 1e-3 && Math.abs(dy) > 1e-3) {              // on the grid, one axis at a time: line up first
      if (Math.abs(dx) < Math.abs(dy)) p.x += Math.sign(dx) * Math.min(step, Math.abs(dx)); else p.y += Math.sign(dy) * Math.min(step, Math.abs(dy));
    } else { p.x += dx / d * step; p.y += dy / d * step; }
  }
  cam.lift = 0;                                      // (art px the camera is lifted with you: the eye's height, curve.js)
  if (me && myId !== null) {
    if (HdLook.eye && HdLook.eye.watch) HdLook.eye = null;      // (in the world now: the eye is on you)
    const p = ents.get("agent" + myId);
    if (p) {                                         // (you are drawn lifted on high ground: centre that; falling: you, not the ground you left; jump.js)
      const fall = falling(p, now);
      const pan = Build.pan(dt);                      // (build mode: half way to the cursor)
      const cl = Climb.climbOf(p);                    // (on a ladder: where the body is drawn, climbing.js)
      cam.x = camT.x = p.x + pan.x + (cl ? cl.dx : 0); cam.lift = liftOf(p) / zoom + (cl ? cl.lift : 0) + (fall ? fall.body : 0) + fallShake(now); cam.y = camT.y = p.y + pan.y + (cl ? cl.dy : 0) - cam.lift / P;
      // (the land drawn where you are drawn, found: a tile within APART layers' rows of you, in your column or two each
      // side, whose top is there, or the wall between two; none: you are away from it, state.js. Under it if the land
      // round your tile is over you, else over it; high: far over the land beside you, a tower's top, a pillar's)
      const z = liftOf(p) / zoom / RELIEF_STEP, tx = Math.round(p.x), ty = Math.round(p.y), r = ty - z / 2;
      let found = null, high = topAt(tx, ty), low = 1e9;
      for (const dx of [0, -1, 1, -2, 2]) for (let y2 = ty - APART / 2, last = null; y2 <= ty + APART / 2 && found === null; y2++) { const top = topAt(tx + dx, y2), r2 = y2 - top / 2; if (Math.abs(r2 - r) <= 1 || (last !== null && last < r && r < r2)) found = top; last = r2; }
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const top = topAt(tx + dx, ty + dy); high = Math.max(high, top); low = Math.min(low, top); }
      away.on = found === null; away.y = p.y + pan.y; away.shift = found !== null && Math.abs(found) > APART / 2 ? found / 2 : 0; away.sky = high - z <= APART; away.high = z - low > APART; away.z = z; away.t = now;
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
  for (const b of coming) if (!b.drawn) arriveBlock(b);      // (a block come in: nothing to paint, the HD look makes its own land: tiles.js)
  for (let n = 0; dirtyTiles.length && (n++ & 15 || performance.now() < landUntil);) { const yy = dirtyTiles.pop(), xx = dirtyTiles.pop(); drawTile(xx, yy); }
  Voxels.work(coming, landUntil);                    // (its beds and its sea: voxels.js)
  const landMs = performance.now() - landFrom;

  // The world is drawn by the HD look (hd.js, after this frame, on a canvas of its own): here nothing of it is painted.
  // While it is live `ctx` is a canvas of one px (hd_view.js sink): what is still drawn below goes nowhere.
  const S = TS();
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.imageSmoothingEnabled = false;
  const [ox, oy] = screenOrigin(S);
  Curve.frame(ox, oy, S, now);                       // (the curved world's line: the HD look's sky, curve.js)
  const sx = (x) => ox + x * S, sy = Curve.sy(oy, S);
  const hereBlock = blocks.get(bkey(Math.floor(cam.x / B), Math.floor((away.a >= 1 ? away.y : cam.y + away.shift) / B)));
  const allShown = vis.every((b) => !onScreen(b) || Voxels.made(b));
  arrivingNow = (arrivingNow || !hereBlock || !Voxels.made(hereBlock)) && !allShown;   // (from arriving until all of it is ready)
  const worldReady = !arrivingNow;
  // A long way at once (a teleport, waking again after a death): until the land there has come, the screen keeps the
  // picture it had. Held for HOLD_MS at the most once some of the land there is ready; after that, what has come.
  const lacking = !!me && (!hereBlock || !worldReady), late = lacking && goodAt > 0 && now - goodAt >= HOLD_MS && (now - goodAt >= 4 * HOLD_MS || vis.some((b) => onScreen(b) && Voxels.made(b)));      // (...and while none of it has come at all, four times as long: a busy machine)
  if (!lacking) goodAt = now; else if (!late && goodAt > 0) { slowFrame(dt, false); return; }
  if (!HdLook.live && me) { ctx.fillStyle = "#2b2420"; ctx.fillRect(0, 0, W, H); }   // (no picture of the world: WebGL 2 missing, or not ready yet)
  slowFrame(dt, worldReady);
  // (where people are: a gate or a door opens for someone beside it. Not for a hen: animals work neither, sim/animals.py)
  occupied = new Set([...ents.values()].filter((p) => p.e && p.e.kind === "agent" && !Floors.rise(p)).map((p) => Math.round(p.x) + "," + Math.round(p.y)));   // (on the land: someone upstairs over a door does not open it)
  Voxels.still(vis, ox, oy, t);                      // (the water's picture the HD look lays on its water, voxels.js)
  // what moves on by itself and is not drawn by the HD look (yet): drops hopping out (their sound as they land), orbs flying to you, poofs, dust, plucked
  // flowers: their state goes on here (drawn to the canvas of one px)
  const none = [];
  drawLoot(sx, sy, S, now, none); drawOrbs(sx, sy, S, dt, none);
  drawDying(sx, sy, S, t, now); drawEffects(sx, sy, S, dt); drawPuffs(sx, sy, dt); drawPlucks(sx, sy, S, now);
  drawXp();
  foodPreview();
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
