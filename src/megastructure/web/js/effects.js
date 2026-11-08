// Particles, shakes, pops, falls, removals, emotes and floating text.

const parts = [], shakes = new Map(), pops = new Map(), falls = [], flashes = new Map(), gones = [];
const sprCols = new Map();
function spriteColors(spr) {                  // the main colours of a sprite, for debris that matches it
  const [img, sx0, sy0, w, h] = spr, key = (img.src || "c") + sx0 + "," + sy0;
  if (sprCols.has(key)) return sprCols.get(key);
  const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d");
  g.drawImage(img, sx0, sy0, w, h, 0, 0, w, h);
  const d = g.getImageData(0, 0, w, h).data, n = new Map();
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 200 || d[i] + d[i + 1] + d[i + 2] < 180) continue;   // skip outlines and shadow
    const k = "#" + [d[i], d[i + 1], d[i + 2]].map((v) => v.toString(16).padStart(2, "0")).join("");
    n.set(k, (n.get(k) || 0) + 1);
  }
  const cols = [...n.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k]) => k);
  sprCols.set(key, cols.length ? cols : PCOL.dust); return sprCols.get(key);
}
const PCOL = {T: ["#6b4b35", "#8f6a45", "#7fb069", "#5e8c4f"], H: ["#5e8c4f", "#7fb069"], b: ["#c0504a", "#7fb069", "#8a5aa0"],
  M: ["#8a8f8c", "#b6bab1", "#5d6260"], "*": ["#8a8f8c", "#f5d77a", "#b6bab1"], Q: ["#c0504a", "#f4f0e6"],
  w: ["#e0c35a", "#7fb069"], "\"": ["#7fb069"], "#": ["#a8775a", "#6b4a3a"], "%": ["#8a8f8c", "#b6bab1"], o: ["#b48b5c", "#8c6a44"],
  C: ["#a8775a", "#c8a45c"], "&": ["#a8775a", "#6b4a3a"], dust: ["#e9d9b4", "#d8c59c"], water: ["#bfe9f7", "#8fd3f4", "#ffffff"], spark: ["#fff1a8", "#ffd36a", "#ffffff"],
  hit: ["#ffffff", "#ffd0cc"], food: ["#c0504a", "#e0c35a", "#fff1a8"], blood: ["#d9473a", "#ffffff"]};
// Chips knocked off a block: its own colours, popping out low, landing around its foot and settling.
function debris(x, y, spr, n, opts = {}) {
  const cols = spr ? spriteColors(spr) : PCOL[opts.kind] || PCOL.dust;
  for (let i = 0; i < n; i++) parts.push({
    x: x + .5 + (Math.random() - .5) * .5, y: y + .45 + (opts.dy || 0) + (Math.random() - .5) * .2,
    vx: (Math.random() - .5) * 2.4, vy: -1.2 - Math.random() * 1.6, g: 11,
    floor: y + .62 + Math.random() * .3, life: .9 + Math.random() * .5, age: 0, c: cols[i % cols.length], s: 1});
  if (opts.dust) for (let i = 0; i < 3; i++) parts.push({   // a soft puff that drifts up
    x: x + .3 + Math.random() * .4, y: y + .6, vx: (Math.random() - .5) * .6, vy: -.5 - Math.random() * .4, g: -.2,
    life: .5 + Math.random() * .3, age: 0, c: "rgba(236,226,206,.7)", s: 2});
}
function burst(x, y, kind, n, opts = {}) {
  const cols = PCOL[kind] || PCOL.dust;
  for (let i = 0; i < n; i++) parts.push({
    x: x + .5 + (Math.random() - .5) * .5, y: y + .5 + (opts.dy || 0) + (Math.random() - .5) * .4,
    vx: (Math.random() - .5) * (opts.spread || 3), vy: -Math.random() * (opts.up || 3) - .5,
    g: opts.g ?? 9, life: opts.life || (.4 + Math.random() * .4), age: 0, c: cols[i % cols.length], s: opts.size || (Math.random() < .3 ? 2 : 1)});
}
const EMOTE = {happy: [0, 2], laugh: [1, 2], love: [0, 9], star: [0, 10], bang: [5, 8], what: [6, 8], music: [7, 8],
  sleep: [9, 8], skull: [7, 0], ok: [0, 8], no: [2, 8]};
const emotes = new Map();   // agent name -> {kind, t0}
function emote(name, kind) { if (name && EMOTE[kind]) emotes.set(name, {kind, t0: performance.now()}); }
function emoteFor(text) {
  const t = text.toLowerCase();
  if (/<3|love|thank|merci/.test(t)) return "love";
  if (/haha|lol|:\)|:d|\^\^/.test(t)) return "laugh";
  if (/\?$/.test(t)) return "what";
  if (/!$/.test(t)) return "bang";
  if (/♪|la la|sing/.test(t)) return "music";
  if (/\b(no|nope|non)\b/.test(t)) return "no";
  if (/\b(ok|yes|sure|oui|deal)\b/.test(t)) return "ok";
  return null;
}
function drawEmote(p, sx, sy, S) {
  const em = emotes.get(p.e.name); if (!em) return;
  const k = (performance.now() - em.t0) / 1000; if (k > 1.8) { emotes.delete(p.e.name); return; }
  const [c, rr] = EMOTE[em.kind], pop = k < .15 ? .6 + k / .15 * .5 : k < .25 ? 1.1 - (k - .15) : 1;
  const size = Math.round(16 * zoom * .75 * pop), x = Math.round(sx(p.x) + S / 2 - size / 2), y = Math.round(sy(p.y) - 9 * zoom - 18 - size);
  ctx.globalAlpha = k > 1.5 ? (1.8 - k) / .3 : 1;
  ctx.drawImage(IMG.emoji, c * 32, rr * 32, 32, 32, x, y, size, size);
  ctx.globalAlpha = 1;
}
function floatText(x, y, text, color) { floats.push({x, y, text, color, t: performance.now() / 1000}); }
// A felled tree falls over. Round trees use the pack's 13-frame felling sheet; young thin trees (the pack has no
// sheet for them) tip over from the base away from whoever chopped them, gather speed, then burst into leaves.
const THIN_FALL_MS = 650;
function felled(x, y, who, now) {
  const spr = objectSprite("T", x, y, now / 1000);
  if (spr && spr[0] !== IMG.trees) return falls.push({x, y, t0: now});           // round tree: the pack animation
  const c = who && [...ents.values()].find((q) => q.e && q.e.name === who);
  falls.push({x, y, t0: now, thin: spr, side: c && c.x > x ? -1 : 1});
}
function drawThinFall(f, sx, sy, now) {
  const k = (now - f.t0) / THIN_FALL_MS, z = zoom;
  if (k >= 1) {                                   // it hit the ground: leaves scatter where the crown landed
    if (!f.burst) { f.burst = true; debris(f.x + f.side * 1.1, f.y - .1, f.thin, 12, {dust: true}); }
    return k < 1.15;
  }
  const [img, a, b, w, h, dx, dy] = f.thin, ang = f.side * (Math.PI / 2) * k * k;   // eases in like a real fall
  const bx = sx(f.x) + (dx + w / 2) * z, by = sy(f.y) + (dy + h - 4) * z;            // pivot: the foot of the trunk
  ctx.save(); ctx.translate(Math.round(bx), Math.round(by)); ctx.rotate(ang);
  ctx.drawImage(img, a, b, w, h, -w / 2 * z, -(h - 4) * z, w * z, h * z);
  ctx.restore();
  return true;
}
// Picking fruit or berries: the plant shakes, the fruit pops out and arcs into the picker's hands.
const flyers = [];
const FLY_MS = 420;
function picked(x, y, old, by, now) {
  const key = x + "," + y, tree = old === "F";
  shakes.set(key, now);
  if (tree) dropping.set(key, now);                // the sheet's fruit-drop animation first (1 s)
  const [ix, iy] = tree ? FRUIT_ICON[fruitKind(x, y)] : BERRY_ICON[Math.floor(hash(x, y, 21) * 3)];
  const from = tree ? [[-.55, .55], [.75, .45], [1.15, .65]] : [[.2, .1], [.75, .2]];   // where fruit lands / berries hang
  from.forEach(([dx, dy], i) => flyers.push({x: x + dx, y: y + dy, ix, iy, by, t0: now + (tree ? 1000 : 80) + i * 90, hop: !tree}));
}
function drawFlyers(sx, sy, S, now) {
  const z = zoom;
  for (let i = flyers.length - 1; i >= 0; i--) {
    const f = flyers[i], k = (now - f.t0) / FLY_MS;
    if (k >= 1) { flyers.splice(i, 1); continue; }
    const who = f.by && [...ents.values()].find((q) => q.e && q.e.name === f.by);
    let x = f.x, y = f.y, sc = 1;
    if (k < 0) { if (f.hop) continue; }            // fruit waits on the ground until the drop animation ends
    else if (who) {                                 // arc into the picker's hands, shrinking as it is caught
      const tx = who.x + .5, ty = who.y + .1, e = k * k * (3 - 2 * k);
      x = f.x + (tx - f.x) * e; y = f.y + (ty - f.y) * e - Math.sin(k * Math.PI) * 1.1; sc = 1 - k * .45;
    } else { y -= k * .8; sc = 1 - k; }
    ctx.globalAlpha = k > .85 ? (1 - k) / .15 : 1;
    const w = 16 * z * sc;
    ctx.drawImage(IMG.trees, f.ix, f.iy, 16, 16, Math.round(sx(x) - w / 2), Math.round(sy(y) - w / 2), Math.round(w), Math.round(w));
  }
  ctx.globalAlpha = 1;
}
function drawEffects(sx, sy, S, dt) {
  const z = zoom;
  for (let i = parts.length - 1; i >= 0; i--) {
    const p = parts[i]; p.age += dt;
    if (p.age > p.life) { parts.splice(i, 1); continue; }
    p.vy += p.g * dt; p.x += p.vx * dt; p.y += p.vy * dt;
    if (p.floor !== undefined && p.y > p.floor) {   // debris lands: a small bounce, then it rests and fades
      p.y = p.floor; p.vx *= .5;
      p.vy = Math.abs(p.vy) > 1.2 ? -p.vy * .3 : 0;
      if (!p.vy) { p.g = 0; p.vx *= .6; }
    }
    ctx.globalAlpha = Math.min(1, 3.3 * (1 - p.age / p.life));
    ctx.fillStyle = p.c;
    ctx.fillRect(Math.round(sx(p.x)), Math.round(sy(p.y)), p.s * z, p.s * z);
  }
  ctx.globalAlpha = 1;
  const now = performance.now();
  for (const [key, t0] of dropping) {               // a picked fruit tree drops its fruit (12 frames)
    const fr = Math.floor((now - t0) / 1000 * 12), [x, y] = key.split(",").map(Number);
    if (fr >= 12) { dropping.delete(key); continue; }
    ctx.drawImage(fruitSheet(x, y), fr * 48, 144, 48, 48, sx(x) - 16 * z, sy(y) - 28 * z, 48 * z, 48 * z);
  }
  drawFlyers(sx, sy, S, now);
  for (let i = falls.length - 1; i >= 0; i--) {     // the pack's tree-felling animation, then fade
    if (falls[i].thin) { if (!drawThinFall(falls[i], sx, sy, now)) falls.splice(i, 1); continue; }
    const f = falls[i], k = (now - f.t0) / 1000, fr = Math.floor(k * 14);
    if (fr >= 12) { falls.splice(i, 1); continue; }
    ctx.globalAlpha = fr >= 9 ? 1 - (fr - 9) / 3 : 1;
    ctx.drawImage(IMG.tree_fall, fr * 64, 0, 64, 48, sx(f.x) - 32 * z, sy(f.y) - 28 * z, 64 * z, 48 * z);   // trunk at frame x 40
    ctx.globalAlpha = 1;
  }
}
