// The frame loop: terrain blocks, y-sorted sprites, characters, night lighting.

// =====================================================================================
//  Frame
// =====================================================================================
let lastT = performance.now(), arrivingNow = true;
const pileSince = new Map();   // when each pile on the ground was first shown (its hover starts from rest)
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(.1, (now - lastT) / 1000); lastT = now;
  const t = now / 1000;
  for (const p of ents.values()) {
    if (p.e && p.e.kind === "agent" && p.e.id === myId && walking && p.walking) { walkOn(p, dt, now); continue; }   // your own walk (walk.js)
    const dx = p.tx - p.x, dy = p.ty - p.y, d = Math.hypot(dx, dy);
    // people walk 5 tiles/s (10 sprinting); animals amble, so each of their steps takes most of the pause between them
    // (a scared animal: exactly the server's pace, a tile every FLEE_STRIDE: slower and it fell behind, then snapped)
    const pace = p.running || (p.e && p.e.run) ? 10 : p.e && p.e.scared && AMBLE[p.e.kind] ? 1 / FLEE_STRIDE : p.e && AMBLE[p.e.kind] ? AMBLE[p.e.kind] : 5;
    const step = (d > 1.5 ? d * 8 : pace * 1.05) * dt;
    if (d <= step) { p.x = p.tx; p.y = p.ty; }
    else if (d > 1.5) { p.x += dx / d * step; p.y += dy / d * step; }    // far behind (lag, teleport): straight there
    else if (Math.abs(dx) > 1e-3 && Math.abs(dy) > 1e-3) {              // on the grid, one axis at a time: line up first
      if (Math.abs(dx) < Math.abs(dy)) p.x += Math.sign(dx) * Math.min(step, Math.abs(dx)); else p.y += Math.sign(dy) * Math.min(step, Math.abs(dy));
    } else { p.x += dx / d * step; p.y += dy / d * step; }
  }
  if (me && myId !== null) {
    const p = ents.get("agent" + myId);
    if (p) { cam.x = camT.x = p.x; cam.y = camT.y = p.y - liftOf(p) / TS(); }   // (you are drawn lifted on high ground: centre that)
    else if (meObs) { cam.x = camT.x = meObs.self.x; cam.y = camT.y = meObs.self.y; }
  } else {
    if (follow) {
      const a = [...ents.values()].find((p) => p.e && p.e.kind === "agent" && p.e.name === follow);
      const b = a || agents.find((q) => q.name === follow);
      if (b) { camT.x = b.x; camT.y = b.y; if (!a) { cam.x = b.x; cam.y = b.y; } }
    }
    const k = 1 - Math.pow(.002, dt); cam.x += (camT.x - cam.x) * k; cam.y += (camT.y - cam.y) * k;
  }
  // bounded work per frame: at most one fresh block, plus incremental tile redraws within ~4 ms
  const [vx, vy, vw, vh0] = viewRect(2), vh = vh0 + 6;   // (+6 rows south: high ground there is drawn up into view)
  const vis = [];
  for (let by = Math.floor(vy / B); by <= Math.floor((vy + vh) / B); by++)
    for (let bx = Math.floor(vx / B); bx <= Math.floor((vx + vw) / B); bx++) { const b = blocks.get(bkey(bx, by)); if (b) vis.push(b); }
  setCaveOpen();
  // a block coming into view: its canvas now, its tiles a few at a time within the frame's budget (below)
  const [qx, qy, qw, qh] = viewRect(0), onScreen = (b) => b.bx * B < qx + qw && (b.bx + 1) * B > qx && b.by * B < qy + qh + 6 && (b.by + 1) * B > qy;
  const fresh = vis.find((b) => !b.drawn && onScreen(b)) || vis.find((b) => !b.drawn);
  if (fresh) { if (onScreen(fresh)) renderBlock(fresh); else startBlock(fresh); }   // (on screen: whole, at once)
  freshThisFrame = !!fresh;                        // (then no relief work this frame: relief.js)
  const t0 = performance.now();
  while (dirtyTiles.length && performance.now() - t0 < 4) { const yy = dirtyTiles.pop(), xx = dirtyTiles.pop(); drawTile(xx, yy); }

  const S = TS();
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.imageSmoothingEnabled = false;
  const [ox, oy] = screenOrigin(S);
  // world to screen. sy(y, x): give the x too and the point is lifted with the ground there (relief.js): everything
  // standing in the world goes through this, so on high ground it is drawn, picked up, killed... where you see it
  const sx = (x) => ox + x * S, sy = (y, x) => oy + y * S - (x === undefined ? 0 : liftOf({x, y}));
  // underneath: plain dark (what hasn't come yet is not the sea). The sea is painted on it where there is sea
  // (water.js: its bottom is under every water tile and every shore), the land over that
  ctx.fillStyle = "#2b2420"; ctx.fillRect(0, 0, W, H);
  drawWater(vis.filter((b) => b.relief), ox, oy, t);    // the sea: its bottom, its depth, its light (water.js); the land goes over it
  for (const b of vis) if (b.canvas) drawBlockRelief(b, sx, sy, S);   // (each level lifted a little: relief.js)
  drawCaves(vis, sx, sy);                            // (their mouths; the one you're in, seen through its roof)
  xrayLook(dt); drawXray(vis, sx, sy);                    // (behind a mountain: a circle round you seen through it, xray.js)
  // arriving (connecting, waking, a long way): the screen shows once all of it is ready, at once, never piece by piece
  const hereBlock = blocks.get(bkey(Math.floor(cam.x / B), Math.floor(cam.y / B)));
  const allShown = vis.every((b) => !onScreen(b) || b.relief);
  arrivingNow = (arrivingNow || !hereBlock || !hereBlock.relief) && !allShown;   // (from arriving until all of it is ready)
  const worldReady = !arrivingNow;
  slowFrame(dt, worldReady && !fresh);
  if (!worldReady) { ctx.fillStyle = "#2b2420"; ctx.fillRect(0, 0, W, H); }
  // y-sorted sprites: objects and creatures
  const list = [];
  for (const b of vis) if (b.relief && worldReady) for (const [i, c] of b.objs) {   // (things show with their ground, not before)
    const x = b.bx * B + i % B, y = b.by * B + (i / B | 0);
    if (hiddenAt(x, y)) continue;                     // (in a cave, seen from outside: under its roof)
    if (x < vx - 2 || x > vx + vw + 2 || y < vy - 2 || y > vy + vh + 3) continue;
    const spr = objectSprite(c, x, y, t); if (spr) list.push({y: c === "m" ? y - 2 : y, ty: y, x, spr});
  }
  occupied = new Set([...ents.values()].filter((p) => p.e).map((p) => Math.round(p.x) + "," + Math.round(p.y)));
  const shownAt = (x, y) => { const b = blocks.get(bkey(Math.floor(Math.round(x) / B), Math.floor(Math.round(y) / B))); return !!(b && b.relief); };
  // (someone shows once the ground under them is here: before that their height is unknown, and they'd pop up)
  for (const p of ents.values()) if (p.e && worldReady && shownAt(p.x, p.y) && !unseen(p)) list.push({y: p.y + .01, p});
  for (const [ix, iy, pile] of groundItems) if (!hiddenAt(ix, iy)) list.push({y: iy - .01, x: ix, ty: iy, pile});   // (ty: its tile; y sorts)
  if (pileSince.size) { const here = new Set(groundItems.map(([ix, iy]) => ix + "," + iy)); for (const k of pileSince.keys()) if (!here.has(k) || lootAt(...k.split(",").map(Number))) pileSince.delete(k); }
  drawLoot(sx, sy, S, now, list);                   // (drops, orbs and magnet loot: in the same depth order)
  drawOrbs(sx, sy, S, dt, list);
  list.sort((a, b) => a.y - b.y || a.x - b.x);
  for (const o of list) {
    selMeasure(o);
    if (o.spr) {
      const [img, a, b2, w, h, dx, dy] = o.spr, key = o.x + "," + o.ty;
      let px = sx(o.x) + dx * zoom, py = sy(o.ty, o.x) + dy * zoom, ww = w * zoom, hh = h * zoom;
      const pop = pops.get(key);
      if (pop !== undefined) {                       // newly placed: bounce in
        const k = (now - pop) / 260;
        if (k >= 1) pops.delete(key);
        else { const sc = 1 + Math.sin(k * Math.PI) * .25 - (1 - k) * .3; const cx = px + ww / 2, by = py + hh; ww *= sc; hh *= sc; px = cx - ww / 2; py = by - hh; }
      }
      const sh = shakes.get(key);
      if (sh !== undefined && o.spr[0] !== IMG.tree_anim) { const k = (now - sh) / 1000; if (k < .25) px += Math.round(Math.sin(k * 60) * (1 - k * 4) * 1.5) * zoom; }
      const over = xrayOver(o.x, o.ty); if (over) ctx.globalAlpha = 1 - over;   // (standing in the way of what the circle shows: it fades)
      ctx.drawImage(img, a, b2, w, h, Math.round(px), Math.round(py), Math.round(ww), Math.round(hh));
      ctx.globalAlpha = 1;
    }
    else if (o.pile) {
      if (lootAt(o.x, o.ty)) continue;                // its loot is still hopping in: the pile shows once it lands
      // a gentle hover, smooth to the screen pixel (whole art pixels made it tick between three heights)
      // (just landed: it starts from rest, where the drop came down, and eases into its hover: no jump)
      const key = o.x + "," + o.ty; if (!pileSince.has(key)) pileSince.set(key, now);
      const settle = smooth((now - pileSince.get(key)) / 700);
      const names = Object.keys(o.pile), lift = settle * (Math.sin((now - pileSince.get(key)) / 1000 * 2.4 - Math.PI / 2) + 1) / 2, sz = 10 * zoom;
      const cx = sx(o.x) + S / 2, cy = sy(o.ty, o.x) + S / 2, bob = lift * 2 * zoom;
      ctx.fillStyle = `rgba(60,40,30,${.25 - lift * .1})`; ctx.beginPath(); ctx.ellipse(cx, cy + 5 * zoom, (4 - lift * .8) * zoom, 1.5 * zoom, 0, 0, 7); ctx.fill();
      names.slice(0, 3).forEach((n, i) => ctx.drawImage(ghostIcon(n), Math.round(cx - sz / 2 + (i - (Math.min(3, names.length) - 1) / 2) * 4 * zoom), Math.round((cy - sz / 2 - bob) * DPR) / DPR, sz, sz));
    }
    else if (o.fx) o.fx();
    else {
      const see = xraySees(o.p); if (see < 0) continue;
      const cut = !see && clipBehind(o.p, sx, sy, S); drawEntity(o.p, sx, sy, S, t, now); if (cut) ctx.restore();
    }
  }
  for (const f of fireAt) {                          // flames over whatever is burning (taller over trees)
    const px = sx(f.x), py = sy(f.y, f.x), tall = "TF".includes(combAt(f.x, f.y) || "");
    if (px < -S * 2 || py < -S * 3 || px > W + S || py > H + S) continue;
    drawFire(px, py, S, t, f.x, f.y);
    if (tall) { drawFire(px - S * .3, py - S * .9, S, t + 1, f.x + 7, f.y); drawFire(px + S * .3, py - S * 1.4, S, t + 2, f.x, f.y + 5); }
    if (Math.random() < dt * 6) parts.push({x: f.x + .2 + Math.random() * .6, y: f.y - (tall ? 1.6 : .3), vx: (Math.random() - .5) * .4, vy: -1.2, g: -.5, life: 1.2, age: 0, c: Math.random() < .5 ? "#6b6f73" : "#ffb454", s: 1});
  }
  selMeasure(null);
  drawDying(sx, sy, S, t, now);
  drawEffects(sx, sy, S, dt);
  drawPuffs(sx, sy, dt);
  drawXp();
  foodPreview();
  drawPlucks(sx, sy, S, now);
  if (roomsDirty || now - roomsAt > 600) { roomsAt = now; roomsDirty = false; findRooms(vx - 4, vy - 4, vw + 8, vh + 8); }
  drawHouses(sx, sy, S, dt, now);
  drawCaveDark(vis, sx, sy, S, t);                   // (the cave you're in: dark past where daylight reaches)
  drawNight(vis, sx, sy, S, t);
  drawGrid(sx, sy, S);                             // (/grid: debug.js)
  updateActions();
  const aim = aimedTile();          // the tile the mouse points at, or the one you face when playing by keyboard
  drawSelector(aim ? drawIntent(aim.p, aim.it, sx, sy, S, t, ox, oy) : null, sx, sy, now);
  for (const o of list) if (o.p && o.p.e.kind === "agent") { drawNameplate(o.p, sx, sy, S); if (!bubbles.some((b) => b.name === o.p.e.name)) drawEmote(o.p, sx, sy, S); }
  for (const o of list) if (o.p && ANIMALS[o.p.e.kind]) drawEmote(o.p, sx, sy, S);
  drawProgress(sx, sy, S);
  floats = floats.filter((f) => t - f.t < 1.4);
  ctx.textAlign = "center"; ctx.font = "18px SproutPixel";
  for (const f of floats) { ctx.globalAlpha = 1 - (t - f.t) / 1.4; outlined(f.text, Math.round(sx(f.x) + S / 2), Math.round(sy(f.y, f.x) - (t - f.t) * S * .7), f.color); }
  ctx.globalAlpha = 1;
  bubbles = bubbles.filter((b) => t - b.t < 7);
  ctx.font = "18px SproutPixel";
  for (const b of bubbles) {
    const p = [...ents.values()].find((q) => q.e && q.e.kind === "agent" && q.e.name === b.name); if (!p) continue;
    const text = b.text.length > 60 ? b.text.slice(0, 58) + "…" : b.text, w = ctx.measureText(text).width;
    const bx = Math.round(sx(p.x) + S / 2), by = Math.round(bodyY(p, sy) - 26 * zoom / 3 - 22 - b.slot * 26);
    ctx.globalAlpha = Math.min(1, (7 - (t - b.t)) * 2);
    ctx.fillStyle = b.shout ? "#ffe3a3" : "#fff6e2"; ctx.strokeStyle = "#5b3f36"; ctx.lineWidth = 2;
    roundRect(bx - w / 2 - 9, by - 16, w + 18, 23, 4); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx - 5, by + 7); ctx.lineTo(bx + 5, by + 7); ctx.lineTo(bx, by + 13); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillRect(bx - 4, by + 5, 8, 3);
    ctx.fillStyle = "#5b3f36"; ctx.fillText(text, bx, by + 1);
    ctx.globalAlpha = 1;
  }
  ctx.textAlign = "start";
}
// Highlight what an action would hit: a ghost of what gets placed, tinted footprint, and an outline.
function drawIntent(p, it, sx, sy, S, t, ox, oy) {
  if (it && it.ghost) {
    ctx.globalAlpha = .7;
    const spr = it.ghostGround ? groundPreview(it.ghostGround, p.x, p.y)
      : it.ghost === "seed" ? [IMG.crops, 0, CROP_ROW[cropSpecies(p.x, p.y)] * 16, 16, 16, 0, -2]
      : objectSprite(PLACEABLE_BLOCK[it.ghost], it.anchor ? it.anchor.x : p.x, it.anchor ? it.anchor.y : p.y, t);
    const gx = it.anchor ? it.anchor.x : p.x, gy = it.anchor ? it.anchor.y : p.y;
    if (spr) { const [img, a2, b2, w2, h2, dx2, dy2] = spr; ctx.drawImage(img, a2, b2, w2, h2, sx(gx) + dx2 * zoom, sy(gy, gx) + dy2 * zoom, w2 * zoom, h2 * zoom); }
    ctx.globalAlpha = 1;
    for (const q of it.foot || [p]) {
      ctx.fillStyle = it.ok && !(it.bad || []).some((b) => b.x === q.x && b.y === q.y) ? "rgba(120,220,120,.25)" : "rgba(230,80,70,.3)";
      ctx.fillRect(sx(q.x), sy(q.y, q.x), S, S);
    }
  }
  // what the selector goes around, in tiles: the aimed creature, person or thing as it was just drawn (selector.js),
  // or a structure's whole footprint
  if (!it || it.info || it.walk) return null;
  const bad = it.ok === false;
  const drawn = selTarget(p, it, ox, oy, S);
  if (drawn) return {...drawn, bad};
  if (it.ent) return {x0: it.ent.x, y0: it.ent.y, x1: it.ent.x + 1, y1: it.ent.y + 1, bad};   // until it's been drawn once
  const xs = (it.foot || [p]).map((q) => q.x), ys = (it.foot || [p]).map((q) => q.y), up = liftAt(p.x, p.y) / S;   // (as drawn)
  return {x0: Math.min(...xs), y0: Math.min(...ys) - up, x1: Math.max(...xs) + 1, y1: Math.max(...ys) + 1 - up, bad};
}

function outlined(text, x, y, color) {
  ctx.fillStyle = "#5b3f36";
  for (const [a, b] of [[-1, 0], [1, 0], [0, -1], [0, 1], [1, 1]]) ctx.fillText(text, x + a, y + b);
  ctx.fillStyle = color; ctx.fillText(text, x, y);
}
function roundRect(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
function drawNight(vis, sx, sy, S, t) {
  const phase = clock.phase || 0;
  const dusk = Math.max(0, Math.min(1, (phase - .70) / .05)), dawn = phase < .03 ? 1 - phase / .03 : 0;
  const dark = .58 * Math.max(dusk, dawn);
  if (dark <= 0.01) return;
  ctx.save();
  ctx.globalCompositeOperation = "multiply";
  ctx.fillStyle = `rgba(${Math.round(255 - 170 * dark)},${Math.round(255 - 150 * dark)},${Math.round(255 - 70 * dark)},1)`;
  ctx.fillRect(0, 0, W, H);
  ctx.globalCompositeOperation = "lighter";
  const glow = (x, y, r, c, a) => { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, `rgba(${c},${a})`); g.addColorStop(1, `rgba(${c},0)`); ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2); };
  for (const p of ents.values()) if (p.e && p.e.kind === "agent") glow(sx(p.x) + S / 2, bodyY(p, sy) + S / 2, S * 3, "255,214,150", .22 * dark);
  const lights = [...fireAt];
  for (const b of vis) for (const [i, c] of b.objs) if (c === "^" || c === "x") lights.push({x: b.bx * B + i % B, y: b.by * B + (i / B | 0)});
  for (const {x, y} of lights) { const f = .9 + .1 * Math.sin(t * 13 + x); glow(sx(x) + S / 2, sy(y, x) + S / 2, S * 4.5 * f, "255,160,70", .45 * dark); }
  ctx.restore();
}
