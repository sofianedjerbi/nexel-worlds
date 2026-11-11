// Particles, shakes, pops, falls, removals, emotes and floating text.

const parts = [], shakes = new Map(), pops = new Map(), falls = [], flashes = new Map();
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
  const key = p.e.name || p.e.kind + p.e.id, em = emotes.get(key); if (!em) return;   // people by name, animals by id
  const k = (performance.now() - em.t0) / 1000; if (k > 1.8) { emotes.delete(key); return; }
  const [c, rr] = EMOTE[em.kind], pop = k < .15 ? .6 + k / .15 * .5 : k < .25 ? 1.1 - (k - .15) : 1;
  const size = Math.round(16 * zoom * .75 * pop), x = Math.round(sx(p.x) + S / 2 - size / 2);
  const head = p.e.kind === "agent" ? 9 * zoom + 18 : ANIMALS[p.e.kind] && ANIMALS[p.e.kind].fw === 32 ? 12 * zoom : 2 * zoom;   // above the head
  const y = Math.round(sy(p.y, p.x) - head - size);
  ctx.globalAlpha = k > 1.5 ? (1.8 - k) / .3 : 1;
  ctx.drawImage(IMG.emoji, c * 32, rr * 32, 32, 32, x, y, size, size);
  ctx.globalAlpha = 1;
}
function floatText(x, y, text, color) { floats.push({x, y, text, color, t: performance.now() / 1000}); }
// A felled tree falls over and leaves its stump. Round trees use the pack's 13-frame felling sheet; young thin trees
// use thin_fall.png, derived from it frame by frame at build time (same wobble, swoosh, landing and leaf burst).
// Both fall away from whoever chopped them (the sheets fall left; mirrored about the trunk to fall right).
function felled(x, y, who, now) {
  const spr = objectSprite("T", x, y, now / 1000), thin = !!spr && spr[0] === IMG.trees;
  const c = who && [...ents.values()].find((q) => q.e && q.e.name === who), side = c && c.x > x ? -1 : 1;
  sfx("creak", x, y);
  setTimeout(() => { sfx("fallthud", x, y); sfx("rustle", x, y); }, 5 / 14 * 1000);   // frame 5: it lands
  falls.push({x, y, t0: now, side, thin});
}
// Picking fruit or berries: the plant shakes, the fruit pops out and arcs into the picker's hands.
const flyers = [];
const FRUIT_G = 30, BOUNCE_MS = 150, REST_MS = 160;   // fruit falling from a tree: gravity (tiles/s²), bounce, rest
const FLY_MS = 420;
function picked(x, y, old, by, now) {
  const key = x + "," + y, tree = old === "F";
  shakes.set(key, now);
  const [ix, iy] = tree ? FRUIT_ICON[fruitKind(x, y)] : BERRY_ICON[Math.floor(hash(x, y, 21) * 3)];
  if (!tree) {                                     // berries pop straight off the bush into your hands
    [[.2, .1], [.75, .2]].forEach(([dx, dy], i) => flyers.push({x: x + dx, y: y + dy, ix, iy, by, t0: now + 80 + i * 90}));
    return;
  }
  // fruit falls from the edge of the crown (smooth gravity, so it never skips), bounces once, rests, then hops to you
  [[-.1, -1.3, .55], [1.05, -1.1, .6]].forEach(([dx, top, ground], i) => {
    const start = now + 60 + i * 110, fall = Math.sqrt(2 * (ground - top) / FRUIT_G) * 1000;
    flyers.push({x: x + dx, y: y + ground, ix, iy, by, drop: {top: y + top, t0: start, fall}, t0: start + fall + BOUNCE_MS + REST_MS});
  });
}
function drawFlyers(sx, sy, S, now) {
  const z = zoom;
  for (let i = flyers.length - 1; i >= 0; i--) {
    const f = flyers[i], k = (now - f.t0) / FLY_MS;
    if (k >= 1) { flyers.splice(i, 1); continue; }
    const who = f.by && [...ents.values()].find((q) => q.e && q.e.name === f.by);
    let x = f.x, y = f.y, sc = 1;
    if (k < 0 && !f.drop) continue;
    if (k < 0) {                                    // falling from the tree, then one small bounce, then resting
      const tf = (now - f.drop.t0) / 1000;
      if (tf < 0) continue;
      if (tf * 1000 < f.drop.fall) y = f.drop.top + .5 * FRUIT_G * tf * tf;
      else { const b = (tf * 1000 - f.drop.fall) / BOUNCE_MS; if (b < 1) y = f.y - Math.sin(b * Math.PI) * .14; }
      if (tf * 1000 - f.drop.fall > 0 && !f.landed) { f.landed = true; sfx("plant", f.x, f.y); }
    } else if (who) {                                 // arc into the picker's hands, shrinking as it is caught
      const tx = who.x + .5, ty = who.y + .1, e = k * k * (3 - 2 * k);
      x = f.x + (tx - f.x) * e; y = f.y + (ty - f.y) * e - Math.sin(k * Math.PI) * 1.1; sc = 1 - k * .45;
    } else { y -= k * .8; sc = 1 - k; }
    ctx.globalAlpha = k > .85 ? (1 - k) / .15 : 1;
    const w = 16 * z * sc;
    ctx.drawImage(IMG.trees, f.ix, f.iy, 16, 16, Math.round(sx(x) - w / 2), Math.round(sy(y, x) - w / 2), Math.round(w), Math.round(w));
  }
  ctx.globalAlpha = 1;
}
// Breaking anything (a bush, a rock, a fence, a table...): its sprite falls apart into 2x2 clumps of its own pixels
// that drift out a little, land, bounce and fade.
const clumpCache = new Map();
function clumpsOf(spr) {
  const [img, a, b, w, h] = spr, key = (img.src || "c") + a + "," + b;
  if (clumpCache.has(key)) return clumpCache.get(key);
  const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d");
  g.drawImage(img, a, b, w, h, 0, 0, w, h);
  const d = g.getImageData(0, 0, w, h).data, out = [];
  for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {
    const i = (y * w + x) * 4;
    if (d[i + 3] > 200) out.push({x, y, c: `rgb(${d[i]},${d[i + 1]},${d[i + 2]})`});
  }
  clumpCache.set(key, out); return out;
}
function shatter(x, y, spr) {
  const [, , , w, h, dx, dy] = spr, cx = (dx + w / 2) / 16, cy = (dy + h / 2) / 16;
  for (const q of clumpsOf(spr)) {
    const px = (dx + q.x + 1) / 16, py = (dy + q.y + 1) / 16, ox = px - cx, oy = py - cy;
    parts.push({x: x + px, y: y + py, vx: ox * 2.2 + (Math.random() - .5) * .5, vy: -.4 - Math.random() * .7, g: 9,
      floor: y + .62 + Math.random() * .3, life: .45 + Math.random() * .35, age: 0, c: q.c, s: 2});   // collapses, drifts a little
  }
}
// Plucking a small plant (mushroom, flower, crop, sprout): a tug up out of the soil, then it arcs into the picker's
// hands, shrinking as it is caught (or just lifts and fades if we can't see who picked it).
const PLUCKED = "Qf;\"w";
const plucks = [];
const TUG_MS = 140, PLUCK_MS = 420;
function plucked(x, y, spr, who, now) {
  plucks.push({x, y, spr, by: who, t0: now});
  debris(x, y, null, 4, {kind: "o"});            // a little soil comes up with it (the rustle is the tile's sound)
}
function drawPlucks(sx, sy, S, now) {
  const z = zoom;
  for (let i = plucks.length - 1; i >= 0; i--) {
    const f = plucks[i], ms = now - f.t0;
    if (ms > TUG_MS + PLUCK_MS) { plucks.splice(i, 1); continue; }
    const [img, a, b, w, h, dx, dy] = f.spr;
    let ox = 0, oy = 0, sc = 1, stretch = 1, alpha = 1;
    if (ms < TUG_MS) { const k = ms / TUG_MS; oy = -Math.sin(k * Math.PI / 2) * .25; stretch = 1 + Math.sin(k * Math.PI) * .18; }
    else {
      const k = (ms - TUG_MS) / PLUCK_MS, e = k * k * (3 - 2 * k);
      const who = f.by && [...ents.values()].find((q) => q.e && q.e.name === f.by);
      if (who) { ox = (who.x - f.x) * e; oy = -.25 + (who.y - .3 - f.y + .25) * e - Math.sin(k * Math.PI) * .8; sc = 1 - k * .55; }
      else { oy = -.25 - k * .6; alpha = 1 - k; }
      if (k > .8) alpha = Math.min(alpha, (1 - k) / .2);
    }
    const ww = w * z * sc, hh = h * z * sc * stretch;
    const cx = sx(f.x + ox) + (dx + w / 2) * z, by = sy(f.y + oy, f.x + ox) + (dy + h) * z;   // anchored at its base
    ctx.globalAlpha = alpha;
    ctx.drawImage(img, a, b, w, h, Math.round(cx - ww / 2), Math.round(by - hh), Math.round(ww), Math.round(hh));
  }
  ctx.globalAlpha = 1;
}
// Dying: the creature's own sprite flashes white, lifts a little and fades inside a puff of smoke.
const dying = [], puffs = [];
const DIE_MS = 480;
function dyingPoof(p, now) {
  dying.push({p: {...p, e: {...p.e, love: false, doing: null}, moved: 0}, y0: p.y, t0: now});
  smoke(p.x, p.y, 8);
}
function smoke(x, y, n, size = 1) {   // size 1: a creature's poof; smaller for a little dust
  for (let i = 0; i < n; i++) puffs.push({x: x + .5 + (Math.random() - .5) * .7, y: y + .35 + (Math.random() - .5) * .35,
    vx: (Math.random() - .5) * .7, vy: -.35 - Math.random() * .45, r: (1.5 + Math.random() * 1.5) * size, grow: (4 + Math.random() * 4) * size,
    life: .65 + Math.random() * .45, age: -i * .025});
}
function drawDying(sx, sy, S, t, now) {
  for (let i = dying.length - 1; i >= 0; i--) {
    const d = dying[i], k = (now - d.t0) / DIE_MS;
    if (k >= 1) { dying.splice(i, 1); continue; }
    d.p.y = d.y0 - k * .35;
    ctx.save(); ctx.globalAlpha = 1 - k * k; ctx.filter = k < .3 ? "brightness(2.4) saturate(.4)" : "brightness(1.4)";
    drawEntity(d.p, sx, sy, S, t, now);
    ctx.restore();
  }
}
function drawPuffs(sx, sy, dt) {
  const z = zoom;
  for (let i = puffs.length - 1; i >= 0; i--) {
    const p = puffs[i]; p.age += dt;
    if (p.age > p.life) { puffs.splice(i, 1); continue; }
    if (p.age < 0) continue;
    const k = p.age / p.life, r = Math.round((p.r + p.grow * k) * z / 2) * 2;
    p.x += p.vx * dt; p.y += p.vy * dt; p.vx *= .97;
    const cx = Math.round(sx(p.x)), cy = Math.round(sy(p.y, p.x)), a = (1 - k) * .85;
    ctx.fillStyle = `rgba(246,240,228,${a})`; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
    ctx.strokeStyle = `rgba(150,128,116,${a * .6})`; ctx.lineWidth = z; ctx.stroke();
  }
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
    ctx.fillRect(Math.round(sx(p.x)), Math.round(sy(p.y, p.x)), p.s * z, p.s * z);
  }
  ctx.globalAlpha = 1;
  const now = performance.now();
  drawFlyers(sx, sy, S, now);
  for (let i = falls.length - 1; i >= 0; i--) {     // the pack's tree-felling animation, then fade
    const f = falls[i], k = (now - f.t0) / 1000, fr = Math.floor(k * 14);
    if (fr >= 12) { falls.splice(i, 1); continue; }
    ctx.globalAlpha = fr >= 9 ? 1 - (fr - 9) / 3 : 1;
    // the sheet falls to the left with the trunk at frame x 32-48; mirrored about the trunk when it should fall right
    if (f.side > 0) { ctx.save(); ctx.translate(sx(f.x) + 8 * z, 0); ctx.scale(-1, 1); ctx.translate(-(sx(f.x) + 8 * z), 0); }
    ctx.drawImage(f.thin ? IMG.thin_fall : IMG.tree_fall, fr * 64, 0, 64, 48, sx(f.x) - 32 * z, sy(f.y, f.x) - 28 * z, 64 * z, 48 * z);
    if (f.side > 0) ctx.restore();
    ctx.globalAlpha = 1;
  }
}
