// Experience orbs, items drawn in by the magnet, and the experience bar.
// Orbs burst out of what was felled, mined, crafted or hunted, hop on the ground a moment, then home in on whoever
// earned them with a rising blip each; the bar fills as they arrive. Loot next to you slides up into your hands.

const orbs = [], magnets = [];
let xpKnown = null, xpLevelShown = null;   // your experience as last heard; the bar leaves out orbs still flying

// the level curve of sim/progress.py: level 0 needs 7, then 3 more for each level
function levelOf(xp) {
  let level = 0, need = 7;
  while (xp >= need) { xp -= need; level++; need = 7 + 3 * level; }
  return [level, xp, need];
}

function spawnOrbs(e) {
  if (e.name === me && xpKnown !== null) xpKnown += e.n;
  const k = Math.min(e.n, 7);
  for (let i = 0; i < k; i++) {
    const a = Math.random() * Math.PI * 2, sp = 1.2 + Math.random() * 1.6;
    orbs.push({x: e.x + .5, y: e.y + .5, h: .2, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp * .6, vh: 3 + Math.random() * 2.5,
      who: e.name, value: e.n / k, age: -i * .04, homing: .35 + Math.random() * .25, big: e.n / k >= 2, seed: Math.random() * 9});
  }
}
function magnetItems(e) {
  Object.keys(e.items || {}).slice(0, 3).forEach((name, i) =>
    magnets.push({x: e.x + .5 + (i - 1) * .2, y: e.y + .5, name, who: e.name, age: -i * .05}));
}
const playerNamed = (name) => [...ents.values()].find((q) => q.e && q.e.kind === "agent" && q.e.name === name);

function drawOrbs(sx, sy, S, dt) {
  const z = zoom;
  for (let i = orbs.length - 1; i >= 0; i--) {
    const o = orbs[i]; o.age += dt;
    if (o.age < 0) continue;
    const p = playerNamed(o.who);
    if (!p || o.age > 4) { orbs.splice(i, 1); continue; }
    if (o.age < o.homing) {                                  // the burst: out and up, a hop on the grass
      o.x += o.vx * dt; o.y += o.vy * dt; o.vx *= .9; o.vy *= .9;
      o.vh -= 22 * dt; o.h = Math.max(0, o.h + o.vh * dt);
      if (o.h === 0) o.vh = Math.abs(o.vh) * .4;
    } else {                                                 // then home in, faster and faster
      const tx = p.x + .5, ty = p.y + .35, dx = tx - o.x, dy = ty - o.y, d = Math.hypot(dx, dy);
      const sp = Math.min(14, 3 + (o.age - o.homing) * 18);
      if (d < .25) { orbs.splice(i, 1); orbLanded(o); continue; }
      o.x += dx / d * Math.min(d, sp * dt); o.y += dy / d * Math.min(d, sp * dt); o.h *= .85;
    }
    const cx = Math.round(sx(o.x) / z) * z, cy = Math.round((sy(o.y) - o.h * S * .5) / z) * z;
    drawOrb(cx, cy, o.big ? ORB_BIG : ORB, Math.sin(o.age * 14 + o.seed) > 0);
  }
  for (let i = magnets.length - 1; i >= 0; i--) {           // loot sliding up into someone's hands
    const m = magnets[i]; m.age += dt;
    if (m.age < 0) continue;
    const p = playerNamed(m.who);
    const k = Math.min(1, m.age / .28);
    if (!p || k >= 1) { magnets.splice(i, 1); if (p) sfx("collect", p.tx, p.ty); continue; }
    const e = k * k, x = m.x + (p.x + .5 - m.x) * e, y = m.y + (p.y + .3 - m.y) * e - Math.sin(k * Math.PI) * .35;
    const sz = Math.round(10 * (1 - .4 * e)) * z;
    ctx.drawImage(ghostIcon(m.name), Math.round(sx(x) - sz / 2), Math.round(sy(y) - sz / 2), sz, sz);
  }
}

// round pixel orbs: o outline, y body (it flickers), w the glint
const ORB = [".ooo.", "owyyo", "oyyyo", "oyyyo", ".ooo."];
const ORB_BIG = ["..ooo..", ".owwyo.", "owyyyyo", "oyyyyyo", "oyyyyyo", ".oyyyo.", "..ooo.."];
function drawOrb(cx, cy, shape, flick) {
  const z = zoom, n = shape.length, x0 = cx - Math.floor(n / 2) * z, y0 = cy - Math.floor(n / 2) * z;
  ctx.fillStyle = "rgba(220,255,140,.25)"; ctx.beginPath(); ctx.arc(cx + z / 2, cy + z / 2, (n / 2 + 2) * z, 0, 7); ctx.fill();
  const col = {o: "#4f8a2a", y: flick ? "#b9e45a" : "#dcf27a", w: "#fffbd8"};
  shape.forEach((row, j) => [...row].forEach((c, i) => { if (c !== ".") { ctx.fillStyle = col[c]; ctx.fillRect(x0 + i * z, y0 + j * z, z, z); } }));
}
function orbLanded(o) {
  const p = playerNamed(o.who);
  if (p) { sfx("orb", p.tx, p.ty); burst(p.x, p.y, "spark", 2, {dy: -.4, g: 3}); }
}

// The bar under the hearts: the level in the middle, the fill trailing the orbs.
function drawXp() {
  if (!meObs) return;
  const flying = orbs.filter((o) => o.who === me).reduce((n, o) => n + o.value, 0);
  if (xpKnown === null || !flying) xpKnown = meObs.self.xp || 0;     // nothing in the air: the server's word
  const [level, into, need] = levelOf(Math.max(0, Math.floor(xpKnown - flying + 1e-6)));
  if (xpLevelShown !== null && level > xpLevelShown) {
    sfx("levelup");
    const p = ents.get("agent" + myId);
    if (p) { burst(p.x, p.y, "spark", 18, {dy: -.6, g: 2, spread: 1.4}); floats.push({x: p.tx, y: p.ty - .4, text: `Level ${level}!`, color: "#d8f070", t: performance.now() / 1000}); }
  }
  xpLevelShown = level;
  const w = (into / need * 100).toFixed(1) + "%", lv = level ? String(level) : "";
  if ($("xpfill").style.width !== w) $("xpfill").style.width = w;          // only touch the page when it changes
  if ($("xplevel").textContent !== lv) $("xplevel").textContent = lv;
}
