// The frame loop: terrain blocks, y-sorted sprites, characters, night lighting.

// =====================================================================================
//  Frame
// =====================================================================================
let lastT = performance.now(), waterPatterns = null;
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(.1, (now - lastT) / 1000); lastT = now;
  const t = now / 1000;
  for (const p of ents.values()) {
    if (p.e && p.e.kind === "agent" && p.e.id === myId && walking && p.walking) {
      // your own walk: glide at exactly the stride speed, never more than a tile ahead of the server
      const [wx, wy] = DIRV[walking.dir], spd = walking.run ? 10 : 5;
      const nx = p.x + wx * spd * dt, ny = p.y + wy * spd * dt;
      const ahead = (nx - p.tx) * wx + (ny - p.ty) * wy;
      const edge = {x: Math.round(p.tx) + wx, y: Math.round(p.ty) + wy};
      const limit = walkable(edge.x, edge.y) ? 1 : 0;
      if (ahead <= limit) { p.x = nx; p.y = ny; }
      const off = wx ? p.y - p.ty : p.x - p.tx;               // drift sideways back onto the server's row/column
      if (wx) p.y -= off * Math.min(1, dt * 12); else p.x -= off * Math.min(1, dt * 12);
      continue;
    }
    const dx = p.tx - p.x, dy = p.ty - p.y, d = Math.hypot(dx, dy);
    const pace = p.running || (p.e && p.e.run) ? 10 : 5;
    const step = (d > 1.5 ? d * 8 : pace * 1.05) * dt;
    if (d <= step) { p.x = p.tx; p.y = p.ty; } else { p.x += dx / d * step; p.y += dy / d * step; }
  }
  if (me && myId !== null) {
    const p = ents.get("agent" + myId);
    if (p) { cam.x = camT.x = p.x; cam.y = camT.y = p.y; }
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
  const [vx, vy, vw, vh] = viewRect(2);
  const vis = [];
  for (let by = Math.floor(vy / B); by <= Math.floor((vy + vh) / B); by++)
    for (let bx = Math.floor(vx / B); bx <= Math.floor((vx + vw) / B); bx++) { const b = blocks.get(bkey(bx, by)); if (b) vis.push(b); }
  const fresh = vis.find((b) => !b.drawn); if (fresh) renderBlock(fresh);
  const t0 = performance.now();
  while (dirtyTiles.length && performance.now() - t0 < 4) { const yy = dirtyTiles.pop(), xx = dirtyTiles.pop(); drawTile(xx, yy); }

  const S = TS();
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.imageSmoothingEnabled = false;
  const [ox, oy] = screenOrigin(S);
  const sx = (x) => ox + x * S, sy = (y) => oy + y * S;
  // animated water underneath everything
  if (!waterPatterns) waterPatterns = [0, 1, 2, 3].map((f) => { const c = document.createElement("canvas"); c.width = c.height = 16; c.getContext("2d").drawImage(IMG.water, f * 16, 0, 16, 16, 0, 0, 16, 16); return ctx.createPattern(c, "repeat"); });
  ctx.save(); ctx.translate(ox, oy); ctx.scale(zoom, zoom);
  ctx.fillStyle = waterPatterns[Math.floor(t * 3) % 4];
  ctx.fillRect(-ox / zoom - 16, -oy / zoom - 16, W / zoom + 32, H / zoom + 32);
  ctx.restore();
  for (const b of vis) if (b.canvas) ctx.drawImage(b.canvas, sx(b.bx * B), sy(b.by * B), B * S, B * S);
  // y-sorted sprites: objects and creatures
  const list = [];
  for (const b of vis) for (const [i, c] of b.objs) {
    const x = b.bx * B + i % B, y = b.by * B + (i / B | 0);
    if (x < vx - 2 || x > vx + vw + 2 || y < vy - 2 || y > vy + vh + 3) continue;
    const spr = objectSprite(c, x, y, t); if (spr) list.push({y: c === "m" ? y - 2 : y, ty: y, x, spr});
  }
  for (let i = gones.length - 1; i >= 0; i--) {
    const k = (now - gones[i].t0) / 240;
    if (k >= 1) gones.splice(i, 1); else list.push({y: gones[i].y, ty: gones[i].y, x: gones[i].x, spr: gones[i].spr, gone: k});
  }
  occupied = new Set([...ents.values()].filter((p) => p.e).map((p) => Math.round(p.x) + "," + Math.round(p.y)));
  for (const p of ents.values()) if (p.e) list.push({y: p.y + .01, p});
  for (const [ix, iy, pile] of groundItems) list.push({y: iy - .01, x: ix, pile});
  list.sort((a, b) => a.y - b.y || a.x - b.x);
  for (const o of list) {
    if (o.spr) {
      const [img, a, b2, w, h, dx, dy] = o.spr, key = o.x + "," + o.ty;
      let px = sx(o.x) + dx * zoom, py = sy(o.ty) + dy * zoom, ww = w * zoom, hh = h * zoom;
      const pop = o.gone === undefined ? pops.get(key) : undefined;
      if (o.gone !== undefined) {                      // squash toward the ground and fade
        const k = o.gone, cx = px + ww / 2, by = py + hh; ww *= 1 + k * .25; hh *= 1 - k * .85; px = cx - ww / 2; py = by - hh;
        ctx.globalAlpha = 1 - k * k;
      }
      if (pop !== undefined) {                       // newly placed: bounce in
        const k = (now - pop) / 260;
        if (k >= 1) pops.delete(key);
        else { const sc = 1 + Math.sin(k * Math.PI) * .25 - (1 - k) * .3; const cx = px + ww / 2, by = py + hh; ww *= sc; hh *= sc; px = cx - ww / 2; py = by - hh; }
      }
      const sh = shakes.get(key);
      if (sh !== undefined && o.spr[0] !== IMG.tree_anim) { const k = (now - sh) / 1000; if (k < .25) px += Math.round(Math.sin(k * 60) * (1 - k * 4) * 1.5) * zoom; }
      ctx.drawImage(img, a, b2, w, h, Math.round(px), Math.round(py), Math.round(ww), Math.round(hh));
      ctx.globalAlpha = 1;
    }
    else if (o.pile) {
      const names = Object.keys(o.pile), bob = Math.round(Math.sin(t * 3 + o.x + o.y) * 1.5) * zoom, sz = 10 * zoom;
      const cx = sx(o.x) + S / 2, cy = sy(o.y) + S / 2;
      ctx.fillStyle = "rgba(60,40,30,.25)"; ctx.beginPath(); ctx.ellipse(cx, cy + 5 * zoom, 4 * zoom, 1.5 * zoom, 0, 0, 7); ctx.fill();
      names.slice(0, 3).forEach((n, i) => ctx.drawImage(ghostIcon(n), cx - sz / 2 + (i - (Math.min(3, names.length) - 1) / 2) * 4 * zoom, cy - sz / 2 - bob, sz, sz));
    }
    else drawEntity(o.p, sx, sy, S, t, now);
  }
  for (const f of fireAt) {                          // flames over whatever is burning (taller over trees)
    const px = sx(f.x), py = sy(f.y), tall = "TF".includes(combAt(f.x, f.y) || "");
    if (px < -S * 2 || py < -S * 3 || px > W + S || py > H + S) continue;
    drawFire(px, py, S, t, f.x, f.y);
    if (tall) { drawFire(px - S * .3, py - S * .9, S, t + 1, f.x + 7, f.y); drawFire(px + S * .3, py - S * 1.4, S, t + 2, f.x, f.y + 5); }
    if (Math.random() < dt * 6) parts.push({x: f.x + .2 + Math.random() * .6, y: f.y - (tall ? 1.6 : .3), vx: (Math.random() - .5) * .4, vy: -1.2, g: -.5, life: 1.2, age: 0, c: Math.random() < .5 ? "#6b6f73" : "#ffb454", s: 1});
  }
  drawDying(sx, sy, S, t, now);
  drawEffects(sx, sy, S, dt);
  drawPuffs(sx, sy, dt);
  if (roomsDirty || now - roomsAt > 600) { roomsAt = now; roomsDirty = false; findRooms(vx - 4, vy - 4, vw + 8, vh + 8); }
  drawRoofs(sx, sy, S, dt);
  drawNight(vis, sx, sy, S, t);
  updateActions();
  const aim = aimedTile();          // the tile the mouse points at, or the one you face when playing by keyboard
  if (aim) drawIntent(aim.p, aim.it, sx, sy, S, t);
  for (const o of list) if (o.p && o.p.e.kind === "agent") { drawNameplate(o.p, sx, sy, S); if (!bubbles.some((b) => b.name === o.p.e.name)) drawEmote(o.p, sx, sy, S); }
  drawProgress(sx, sy, S);
  floats = floats.filter((f) => t - f.t < 1.4);
  ctx.textAlign = "center"; ctx.font = "18px SproutPixel";
  for (const f of floats) { ctx.globalAlpha = 1 - (t - f.t) / 1.4; outlined(f.text, Math.round(sx(f.x) + S / 2), Math.round(sy(f.y) - (t - f.t) * S * .7), f.color); }
  ctx.globalAlpha = 1;
  bubbles = bubbles.filter((b) => t - b.t < 7);
  ctx.font = "18px SproutPixel";
  for (const b of bubbles) {
    const p = [...ents.values()].find((q) => q.e && q.e.kind === "agent" && q.e.name === b.name); if (!p) continue;
    const text = b.text.length > 60 ? b.text.slice(0, 58) + "…" : b.text, w = ctx.measureText(text).width;
    const bx = Math.round(sx(p.x) + S / 2), by = Math.round(sy(p.y) - 26 * zoom / 3 - 22 - b.slot * 26);
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
// which swing of the character sheet each tool in hand uses (the sheet has an axe and a hoe swing)
const SWING_ROW = {axe: "axe", sword: "axe", spear: "axe", pickaxe: "axe", hoe: "hoe", watering_can: "water"};
function drawIntent(p, it, sx, sy, S, t) {
  if (it && it.ghost) {
    ctx.globalAlpha = .7;
    const spr = it.ghostGround ? groundPreview(it.ghostGround, p.x, p.y)
      : it.ghost === "seed" ? [IMG.crops, 0, CROP_ROW[cropSpecies(p.x, p.y)] * 16, 16, 16, 0, -2]
      : objectSprite(PLACEABLE_BLOCK[it.ghost], it.anchor ? it.anchor.x : p.x, it.anchor ? it.anchor.y : p.y, t);
    const gx = it.anchor ? it.anchor.x : p.x, gy = it.anchor ? it.anchor.y : p.y;
    if (spr) { const [img, a2, b2, w2, h2, dx2, dy2] = spr; ctx.drawImage(img, a2, b2, w2, h2, sx(gx) + dx2 * zoom, sy(gy) + dy2 * zoom, w2 * zoom, h2 * zoom); }
    ctx.globalAlpha = 1;
    for (const q of it.foot || [p]) {
      ctx.fillStyle = it.ok && !(it.bad || []).some((b) => b.x === q.x && b.y === q.y) ? "rgba(120,220,120,.25)" : "rgba(230,80,70,.3)";
      ctx.fillRect(sx(q.x), sy(q.y), S, S);
    }
  }
  if (it && !it.info && !it.walk) {
    ctx.strokeStyle = it.ok === false ? "rgba(230,80,70,.9)" : "rgba(255,248,232,.95)"; ctx.lineWidth = zoom;
    const xs = (it.foot || [p]).map((q) => q.x), ys = (it.foot || [p]).map((q) => q.y);
    const x0 = Math.min(...xs), y0 = Math.min(...ys), x1 = Math.max(...xs) + 1, y1 = Math.max(...ys) + 1;
    ctx.strokeRect(sx(x0) + zoom / 2, sy(y0) + zoom / 2, (x1 - x0) * S - zoom, (y1 - y0) * S - zoom);
  }
}

function outlined(text, x, y, color) {
  ctx.fillStyle = "#5b3f36";
  for (const [a, b] of [[-1, 0], [1, 0], [0, -1], [0, 1], [1, 1]]) ctx.fillText(text, x + a, y + b);
  ctx.fillStyle = color; ctx.fillText(text, x, y);
}
function roundRect(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
function drawEntity(p, sx, sy, S, t, now) {
  const e = p.e, x = Math.round(sx(p.x)), y = Math.round(sy(p.y)), z = zoom;
  if (x < -S * 2 || x > W + S * 2 || y < -S * 2 || y > H + S * 2) return;
  const moving = now - p.moved < 300;
  if (e.kind === "agent") {
    const mine = me && e.id === myId;
    const action = mine && myAction ? myAction : (e.doing ? {tool: e.doing, dir: e.dir, tid: e.tid, with: e.with, t0: p.doingSince || now} : null);
    if (e.doing && !p.doingSince) p.doingSince = now;
    if (!e.doing) p.doingSince = 0;
    if (!mine) p.running = !!e.run;
    // face the action's target
    if (action && action.dir && DIRV[action.dir]) { [p.fx, p.fy] = DIRV[action.dir]; }
    if (action && action.tid != null) { const q = [...ents.values()].find((q) => q.e && q.e.id == action.tid); if (q) { p.fx = Math.sign(q.x - p.x); p.fy = p.fx ? 0 : Math.sign(q.y - p.y); } }
    const sheetImg = characterSheet(agentTint(e.name));
    let bob = 0, anim = "idle", frame, lunge = 0;
    const tool = action && action.tool, k = action ? (now - action.t0) / 1000 : 0;
    if (mine || e.name === follow) {
      ctx.fillStyle = mine ? "rgba(255,248,232,.55)" : "rgba(255,200,120,.55)";
      ctx.beginPath(); ctx.ellipse(x + S / 2, y + S - 2 * z, 6 * z, 2.5 * z, 0, 0, 7); ctx.fill();
    }
    if (tool === "dig" || tool === "attack" || tool === "craft") {
      // full 8-frame tool swings: wind-up, strike (frame 4, with the arc), follow-through
      const tx = Math.round(p.tx) + p.fx, ty = Math.round(p.ty) + p.fy, target = combAt(tx, ty);
      // the sheet's swings show a tool: only use them when one is in hand; bare hands reach out and back
      const held = action.with && SWING_ROW[action.with];
      anim = held || "idle";
      const fps = tool === "attack" ? 20 : 13, n = Math.floor(k * fps);
      frame = n % 8;
      if (!held) lunge = Math.round(Math.sin(Math.min(1, frame / 6) * Math.PI) * 3) * z;
      const swing = Math.floor(n / 8);
      if (frame >= 4 && p.lastSwing !== swing) {     // the strike lands: debris and a shake on the target
        p.lastSwing = swing;
        if (tool === "dig" && target) {
          const spr = GROUND.has(target) ? null : objectSprite(target, tx, ty, now / 1000);
          debris(tx, ty, spr, GROUND.has(target) ? 5 : 4, {kind: "o", dy: "TFU".includes(target) ? -.5 : 0, dust: "M*%Y".includes(target) || GROUND.has(target)});
          shakes.set(tx + "," + ty, now);
          const mat = GROUND.has(target) ? "soil" : material(target);
          sfx(!held && (mat === "wood" || mat === "stone") ? "thud" : STRIKE[mat], tx, ty);
        } else if (tool === "craft") burst(Math.round(p.tx), Math.round(p.ty), "spark", 5, {dy: -.6, g: 4});
      }
    } else if (tool === "water") {
      anim = "water"; const n = Math.floor(k * 10); frame = n % 8;
      if (frame >= 3 && frame <= 6 && p.lastDrop !== n) { p.lastDrop = n; const tx = Math.round(p.tx) + p.fx, ty = Math.round(p.ty) + p.fy;
        parts.push({x: tx + .3 + Math.random() * .4, y: ty - .1, vx: (Math.random() - .5) * .6, vy: 1.5, g: 9, life: .35, age: 0, c: "#8fd3f4", s: 1});
        if (n % 3 === 0) sfx("water", tx, ty); }
    } else if (tool === "milk" || tool === "feed" || tool === "sleep") {
      bob = tool === "sleep" ? 0 : Math.round(Math.abs(Math.sin(k * 8)) * 2) * z;
      if (tool === "sleep" && !emotes.has(e.name)) emote(e.name, "sleep");
    } else if (tool === "eat") {
      bob = Math.round(Math.abs(Math.sin(k * 14)) * 2) * z;
      if (Math.floor(k * 7) !== p.lastCrumb) { p.lastCrumb = Math.floor(k * 7); if (p.lastCrumb % 2 === 0) sfx("eat", p.x, p.y); burst(Math.round(p.tx), Math.round(p.ty), "food", 2, {dy: -.3, up: 1.5, spread: 1.5}); }
    } else if (tool === "place" || tool === "pick_up" || tool === "give" || tool === "store" || tool === "take" || tool === "drop") {
      bob = Math.round(Math.sin(Math.min(1, k * 5) * Math.PI) * 3) * z;
    } else if (tool === "rest") {
      if (!emotes.has(e.name)) emote(e.name, "sleep");
      if (Math.floor(k * 1.5) !== p.lastZ) { p.lastZ = Math.floor(k * 1.5); floatText(p.x + .3, p.y - .3, "z", "#e8f0ff"); }
    }
    if (frame === undefined) {
      const moving = p.walking || (e.doing === "walk" && !mine) || now - p.moved < 220 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
      const running = moving && (p.running || (mine && runKey));
      if (moving) {
        anim = running ? "run" : "walk";
        const ms = running ? 60 : 85;                 // 8-frame cycles
        frame = Math.floor(now / ms) % 8;
        if (frame % 4 === 0 && p.lastStep !== Math.floor(now / ms)) {
          p.lastStep = Math.floor(now / ms);
          burst(p.x, p.y + .35, "dust", running ? 3 : 2, {up: .6, spread: running ? 2 : 1.2, g: 2, life: .35});
          if (mine) { const gr = gndAt(Math.round(p.x), Math.round(p.y)); sfx(gr === "n" || gr === ":" ? "tock" : gr === "_" ? "click" : "step"); }
        }
      } else frame = Math.floor(now / 140 + e.id * 3) % 8;   // idle: the sheet's 8-frame breathing
    }
    if (tool === "sleep" && action.dir && DIRV[action.dir]) {
      // tucked into the bed: head on the pillow, the bed's blanket drawn over the body
      const bx = Math.round(p.tx) + DIRV[action.dir][0], by = Math.round(p.ty) + DIRV[action.dir][1];
      if (combAt(bx, by) === "B") {
        const bed = objectSprite("B", bx, by, t), px0 = sx(bx), py0 = sy(by);
        ctx.drawImage(sheetImg, (Math.floor(now / 400) % 2) * 48, 0, 48, 48, px0 - 16 * z, py0 - 26 * z, 48 * z, 48 * z);
        ctx.drawImage(bed[0], bed[1], bed[2] + 14, 16, 18, px0, py0 + (bed[6] + 14) * z, 16 * z, 18 * z);
        return;
      }
    }
    if (e.sail) {                                     // in a boat: the hull, a wake when moving, and the sailor sitting in it
      const movingB = now - p.moved < 300 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
      const bf = movingB ? Math.floor(now / 140) % 3 : Math.floor(now / 600) % 2, brow = movingB ? 64 : 32;
      ctx.save();
      if (p.fx < 0) { ctx.translate(x + S / 2, 0); ctx.scale(-1, 1); ctx.translate(-(x + S / 2), 0); }
      ctx.drawImage(IMG.boats, bf * 48, brow, 48, 32, x - 16 * z, y - 10 * z, 48 * z, 32 * z);
      ctx.restore();
      ctx.drawImage(sheetImg, (Math.floor(now / 500) % 2) * 48, DIR_ROW(p) * 48, 48, 28, x - 16 * z, y - 22 * z, 48 * z, 28 * z);
      return;
    }
    const sxx = frame * 48, syy = (ANIM[anim] + DIR_ROW(p)) * 48;
    const fl = flashes.get("agent" + e.id), hitK = fl ? (now - fl) / 1000 : 9;
    const kb = hitK < .15 ? Math.round((1 - hitK / .15) * 2) * z : 0;
    ctx.drawImage(sheetImg, sxx, syy, 48, 48, x - 16 * z - p.fx * (kb - lunge), y - 18 * z - bob - p.fy * (kb - lunge), 48 * z, 48 * z);   // feet at frame y 32
    if (hitK < .12) { ctx.globalCompositeOperation = "lighter"; ctx.globalAlpha = .7; ctx.drawImage(sheetImg, sxx, syy, 48, 48, x - 16 * z, y - 18 * z, 48 * z, 48 * z); ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over"; }
  } else if (ANIMALS[e.kind]) {
    const A = ANIMALS[e.kind], img = animalSheet(e.kind, e.id), fw = A.fw, big = fw === 32;
    const moving = now - p.moved < 350 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
    let st;
    if (moving) st = A.walk;
    else if (e.love) st = A.love;
    else if (clock.night) st = A.sleep;
    else st = hash(e.id, Math.floor((now / 1000 + e.id) / 4), 7) < .45 ? A.idle : A.alt;   // a new whim every 4 s
    const [row, n, ms] = st, f = Math.floor(now / ms + e.id) % n;
    const fl = flashes.get(e.kind + e.id), white = fl && now - fl < 120;
    const w = fw * z, dx = big ? x - S / 2 : x, dy = big ? y - S : y;
    ctx.save();
    const blit = (ox) => { ctx.drawImage(img, f * fw, row * fw, fw, fw, ox, dy, w, w); if (white) { ctx.globalCompositeOperation = "lighter"; ctx.drawImage(img, f * fw, row * fw, fw, fw, ox, dy, w, w); } };
    if (p.fx < 0) { ctx.translate(dx + w, 0); ctx.scale(-1, 1); blit(0); } else blit(dx);
    ctx.restore();
    if (e.love && A.hearts) ctx.drawImage(img, (Math.floor(now / 140) % A.hearts[1]) * 16, A.hearts[0] * 16, 16, 16, x, y - S + 2 * z, S, S);
  } else if (e.kind === "gloom") {
    const [gx] = genCell(Math.floor(t * 3 + e.id) % 2 ? "gloom1" : "gloom0");
    const hop = Math.round(Math.abs(Math.sin(t * 5 + e.id)) * 2) * z;
    ctx.drawImage(IMG.gen, gx, 0, 16, 16, x, y - 2 * z - hop, S, S);
    const fl = flashes.get("gloom" + e.id);
    if (fl && now - fl < 120) { ctx.globalCompositeOperation = "lighter"; ctx.drawImage(IMG.gen, gx, 0, 16, 16, x, y - 2 * z - hop, S, S); ctx.globalCompositeOperation = "source-over"; }
  }
}
function drawNameplate(p, sx, sy, S) {
  const e = p.e, x = Math.round(sx(p.x) + S / 2), y = Math.round(sy(p.y) - 9 * zoom);
  if (x < -S || x > W + S || y < -S || y > H + S) return;
  ctx.font = "18px SproutPixel"; ctx.textAlign = "center";
  outlined(e.name, x, y, me && e.name === me ? "#fff1a8" : "#fff8e8");
  if (e.hp < 100) { ctx.fillStyle = "#5b3f36"; ctx.fillRect(x - 16, y + 4, 32, 5); ctx.fillStyle = e.hp > 40 ? "#6aa66f" : "#d9473a"; ctx.fillRect(x - 15, y + 5, 30 * e.hp / 100, 3); }
  ctx.textAlign = "start";
}
function drawProgress(sx, sy, S) {
  if (!progress || !me) return;
  const p = ents.get("agent" + myId); if (!p) return;
  const k = Math.min(1, (performance.now() - progress.t0) / progress.ms);
  if (k >= 1) { progress = null; return; }
  const x = Math.round(sx(p.x) + S / 2 - 18), y = Math.round(sy(p.y) + S + 2);
  ctx.fillStyle = "#5b3f36"; ctx.fillRect(x - 2, y - 2, 40, 9);
  ctx.fillStyle = "#e9cfa2"; ctx.fillRect(x, y, 36, 5);
  ctx.fillStyle = "#6aa66f"; ctx.fillRect(x, y, Math.round(36 * k), 5);
}
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
  for (const p of ents.values()) if (p.e && p.e.kind === "agent") glow(sx(p.x) + S / 2, sy(p.y) + S / 2, S * 3, "255,214,150", .22 * dark);
  const lights = [...fireAt];
  for (const b of vis) for (const [i, c] of b.objs) if (c === "^" || c === "x") lights.push({x: b.bx * B + i % B, y: b.by * B + (i / B | 0)});
  for (const {x, y} of lights) { const f = .9 + .1 * Math.sin(t * 13 + x); glow(sx(x) + S / 2, sy(y) + S / 2, S * 4.5 * f, "255,160,70", .45 * dark); }
  ctx.restore();
}
