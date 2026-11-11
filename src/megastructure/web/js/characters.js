// Characters and animals: drawing them with their animations (walking, tools, eating, fleeing), nameplates and the
// progress bar.

const BITES = 3, EAT_S = .9;   // sim constants EAT_SECONDS
// Eating, per bite: the food comes up from the hand (40%), is bitten (30%), goes back down (30%).
function eatPose(k) {
  const t = k * BITES / EAT_S, n = Math.min(BITES - 1, Math.floor(t)), ph = Math.min(1, t - n);
  const lift = ph < .4 ? ph / .4 : ph < .7 ? 1 : 1 - (ph - .7) / .3;
  return {n, lift: lift * lift * (3 - 2 * lift), biting: ph >= .4 && ph < .7, bites: n + (ph >= .55 ? 1 : 0)};
}
// A crisp 8x8 version of an item icon (each 2x2 block becomes one pixel), with round bites taken out of it.
const biteIcons = new Map();
const BITE_AT = [[6, 1, 2.6], [3, 0, 3.2], [4, 4, 9]];   // each bite: centre x, y and radius in the 8x8 icon
function biteIcon(name, bites) {
  const key = name + bites;
  if (biteIcons.has(key)) return biteIcons.get(key);
  const big = ghostIcon(name).getContext("2d").getImageData(0, 0, 16, 16).data;
  const c = document.createElement("canvas"); c.width = c.height = 8; const g = c.getContext("2d"), img = g.createImageData(8, 8);
  let left = 0;
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) {
    let best = -1;
    for (const [dx, dy] of [[1, 1], [0, 0], [1, 0], [0, 1]]) { const i = ((y * 2 + dy) * 16 + x * 2 + dx) * 4; if (big[i + 3] > 128) { best = i; break; } }
    if (best < 0 || BITE_AT.slice(0, bites).some(([bx, by, r]) => (x - bx) ** 2 + (y - by) ** 2 < r * r)) continue;
    img.data.set(big.slice(best, best + 4), (y * 8 + x) * 4); left++;
  }
  g.putImageData(img, 0, 0);
  biteIcons.set(key, left ? c : null); return left ? c : null;
}
// which swing of the character sheet each tool in hand uses (the sheet has an axe and a hoe swing)
const SWING_ROW = {axe: "axe", sword: "axe", spear: "axe", pickaxe: "axe", hoe: "hoe", watering_can: "water"};
// Between a tile and one a layer up or down: a jump (or a hop down). Lift (art px) along a quick arc.
function hopLift(p) {
  const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
  if (ax === bx && ay === by) return 0;
  const la = standAt(ax, ay), lb = standAt(bx, by);
  if (la === lb) return 0;
  const f = ax === bx ? p.y - ay : p.x - ax, k = la > lb ? f : 1 - f;          // 0 at the top, 1 landed
  return Math.sin(k * Math.PI) * 7 + (1 - k) * 2;
}
function drawEntity(p, sx, sy, S, t, now) {
  const e = p.e, x = Math.round(sx(p.x)), y = Math.round(sy(p.y, p.x)), z = zoom;
  if (x < -S * 2 || x > W + S * 2 || y < -S * 2 || y > H + S * 2) return;
  const moving = now - p.moved < 300;
  if (e.kind === "agent") {
    const lv = standAt(Math.round(p.x), Math.round(p.y));    // stepping up a slope: a little puff of effort
    if (p.lastLv !== undefined && lv > p.lastLv) { smoke(p.x, p.y + .3, 3, .35); sfx("step", Math.round(p.x), Math.round(p.y)); }
    const hop = hopLift(p);                                     // hopping down off an edge: an arc, then a soft landing
    if (p.lastHop > 0 && hop === 0) { smoke(p.x, p.y + .35, 4, .4); sfx("thud", Math.round(p.x), Math.round(p.y)); }
    p.lastHop = hop;
    p.lastLv = lv;
    const mine = me && e.id === myId;
    let action = mine && myAction ? myAction : (e.doing ? {tool: e.doing, dir: e.dir, at: e.at, tid: e.tid, with: e.with, item: e.item, t0: p.doingSince || now} : null);
    if ((!action || action.tool === "walk" || action.tool === "move_to") && p.swing && now - p.swing.t0 < 320)
      action = {tool: "attack", t0: p.swing.t0, with: p.swing.with};   // a swing, even on the move
    if (e.doing && !p.doingSince) p.doingSince = now;
    if (!e.doing) p.doingSince = 0;
    if (!mine) p.running = !!e.run;
    // face the action's target
    if (action && action.dir && DIRV[action.dir]) { [p.fx, p.fy] = DIRV[action.dir]; }
    if (action && action.tid != null) { const q = [...ents.values()].find((q) => q.e && q.e.id == action.tid); if (q) { p.fx = Math.sign(q.x - p.x); p.fy = p.fx ? 0 : Math.sign(q.y - p.y); } }
    const sheetImg = characterSheet(agentTint(e.name));
    let bob = Math.round(hop * z), anim = "idle", frame, lunge = 0;
    const tool = action && action.tool, k = action ? (now - action.t0) / 1000 : 0;
    if (mine || e.name === follow) {
      ctx.fillStyle = mine ? "rgba(255,248,232,.55)" : "rgba(255,200,120,.55)";
      ctx.beginPath(); ctx.ellipse(x + S / 2, y + S - 2 * z, 6 * z, 2.5 * z, 0, 0, 7); ctx.fill();
    }
    if (tool === "dig" || tool === "attack" || tool === "craft") {
      // full 8-frame tool swings: wind-up, strike (frame 4, with the arc), follow-through
      const [tx, ty] = action.at || [Math.round(p.tx) + p.fx, Math.round(p.ty) + p.fy], target = combAt(tx, ty);   // the tile worked on
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
          sfx(!held && (mat === "wood" || mat === "stone") ? "punch" : STRIKE[mat], tx, ty);
        } else if (tool === "craft") burst(Math.round(p.tx), Math.round(p.ty), "spark", 5, {dy: -.6, g: 4});
      }
    } else if (tool === "water") {
      anim = "water"; const n = Math.floor(k * 10); frame = n % 8;
      if (frame >= 3 && frame <= 6 && p.lastDrop !== n) { p.lastDrop = n; const [tx, ty] = action.at || [Math.round(p.tx) + p.fx, Math.round(p.ty) + p.fy];
        parts.push({x: tx + .3 + Math.random() * .4, y: ty - .1, vx: (Math.random() - .5) * .6, vy: 1.5, g: 9, life: .35, age: 0, c: "#8fd3f4", s: 1});
        if (n % 3 === 0) sfx("pour", tx, ty); }
    } else if (tool === "milk" || tool === "feed" || tool === "sleep") {
      bob = tool === "sleep" ? 0 : Math.round(Math.abs(Math.sin(k * 8)) * 2) * z;
      if (tool === "sleep" && !emotes.has(e.name)) emote(e.name, "sleep");
    } else if (tool === "eat") {                      // three bites (see eatPose): a small nod on each, crumbs fall
      const pose = eatPose(k);
      if (k < .05) p.lastBite = -1;                  // a new meal
      bob = pose.biting ? z : 0;
      if (pose.biting && p.lastBite !== pose.n) {
        p.lastBite = pose.n; sfx("eat", p.x, p.y);
        const mx = p.x + .5 + (p.fx || 0) * .28, cols = spriteColors([ghostIcon(action.item), 0, 0, 16, 16]);
        for (let i = 0; i < 4; i++) parts.push({x: mx + (Math.random() - .5) * .25, y: p.y + .35, vx: (Math.random() - .5) * .8,
          vy: -.3 - Math.random() * .6, g: 9, floor: p.y + .85 + Math.random() * .1, life: .5 + Math.random() * .3, age: 0, c: cols[i % cols.length], s: 1});
      }
    } else if (tool === "place" || tool === "pick_up" || tool === "give" || tool === "store" || tool === "take" || tool === "drop") {
      bob = Math.round(Math.sin(Math.min(1, k * 5) * Math.PI) * 3) * z;
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
          if (mine) sfx(STEP[gndAt(Math.round(p.x), Math.round(p.y))] || "step");
        }
      } else frame = Math.floor(now / 140 + e.id * 3) % 8;   // idle: the sheet's 8-frame breathing
    }
    if (tool === "sleep" && action.dir && DIRV[action.dir]) {
      // tucked into the bed: head on the pillow, the bed's blanket drawn over the body
      const bx = Math.round(p.tx) + DIRV[action.dir][0], by = Math.round(p.ty) + DIRV[action.dir][1];
      if (combAt(bx, by) === "B") {
        const bed = objectSprite("B", bx, by, t), px0 = sx(bx), py0 = sy(by, bx);
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
    if (tool === "eat" && action.item && p.fy >= 0) {   // the food, half size and crisp, held up to the mouth
      const pose = eatPose(k), food = biteIcon(action.item, pose.bites);
      if (food) {
        // the mouth is at frame row 22 (screen y + 4z); side-on it is at the edge of the face
        const mx = Math.round(x + S / 2 + (p.fx || 0) * 4 * z), my = Math.round(y + 5 * z);
        const fx = mx - 4 * z + (p.fx || 0) * z * Math.round(2 * (1 - pose.lift)), fy = my - 3 * z + z * Math.round(5 * (1 - pose.lift));
        ctx.drawImage(food, fx, fy - bob, 8 * z, 8 * z);
      }
    }
    if (hitK < .12) { ctx.globalCompositeOperation = "lighter"; ctx.globalAlpha = .7; ctx.drawImage(sheetImg, sxx, syy, 48, 48, x - 16 * z, y - 18 * z, 48 * z, 48 * z); ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over"; }
  } else if (ANIMALS[e.kind]) {
    const A = ANIMALS[e.kind], img = animalSheet(e.kind, e.id), fw = A.fw, big = fw === 32;
    const moving = now - p.moved < 350 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
    let st;
    if (moving) st = A.walk;
    else if (e.love) st = A.love;
    else if (clock.night) st = A.sleep;
    else st = hash(e.id, Math.floor((now / 1000 + e.id) / 4), 7) < .45 ? A.idle : A.alt;   // a new whim every 4 s
    const [row, n, ms] = st, f = Math.floor(now / (e.scared ? ms / 2 : ms) + e.id) % n;   // running scared: quick steps
    const fl = flashes.get(e.kind + e.id), white = fl && now - fl < 120;
    const w = fw * z, dx = big ? x - S / 2 : x, dy = big ? y - S : y;
    ctx.save();
    const blit = (ox) => { ctx.drawImage(img, f * fw, row * fw, fw, fw, ox, dy, w, w); if (white) { ctx.globalCompositeOperation = "lighter"; ctx.drawImage(img, f * fw, row * fw, fw, fw, ox, dy, w, w); } };
    if (p.fx < 0) { ctx.translate(dx + w, 0); ctx.scale(-1, 1); blit(0); } else blit(dx);
    ctx.restore();
    if (e.love && A.hearts) ctx.drawImage(img, (Math.floor(now / 140) % A.hearts[1]) * 16, A.hearts[0] * 16, 16, 16, x, y - S + 2 * z, S, S);
  } else if (WILD[e.kind]) {
    drawWild(p, x, y, now);                           // (world_decor.js)
  }
}
function drawNameplate(p, sx, sy, S) {
  const e = p.e, x = Math.round(sx(p.x) + S / 2), y = Math.round(sy(p.y, p.x) - 9 * zoom);
  if (x < -S || x > W + S || y < -S || y > H + S) return;
  ctx.font = "18px SproutPixel"; ctx.textAlign = "center";
  outlined(e.name, x, y, me && e.name === me ? "#fff1a8" : "#fff8e8");
  if (e.hp < 100) { ctx.fillStyle = "#5b3f36"; ctx.fillRect(x - 16, y + 4, 32, 5); ctx.fillStyle = e.hp > 40 ? "#6aa66f" : "#d9473a"; ctx.fillRect(x - 15, y + 5, 30 * e.hp / 100, 3); }
  ctx.textAlign = "start";
}
const AMBLE = {chicken: 1.6, chick: 1.4, cow: 1.2, calf: 1.3, tusker: 1.2, pincer: 4, strawman: 1.2, wisp: 3.3, wyrm: 2.5};   // tiles per second
const FLEE_STRIDE = .3;   // a scared animal runs a tile every this many seconds (sim/constants.py FLEE_STRIDE)
function drawProgress(sx, sy, S) {
  if (!progress || !me) return;
  const p = ents.get("agent" + myId); if (!p) return;
  const k = Math.min(1, (performance.now() - progress.t0) / progress.ms);
  if (k >= 1) { progress = null; return; }
  const x = Math.round(sx(p.x) + S / 2 - 18), y = Math.round(sy(p.y, p.x) + S + 2);
  ctx.fillStyle = "#5b3f36"; ctx.fillRect(x - 2, y - 2, 40, 9);
  ctx.fillStyle = "#e9cfa2"; ctx.fillRect(x, y, 36, 5);
  ctx.fillStyle = "#6aa66f"; ctx.fillRect(x, y, Math.round(36 * k), 5);
}
