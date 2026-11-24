// What moves on by itself, drawn in the HD look: chips and sparks (effects.js parts), smoke (puffs), a felled tree falling (falls),
// fruit and plucked plants flying to the picker (flyers, plucks), drops hopping out (loot.js), orbs and loot flying to you (xp.js),
// flames over what burns (fireAt); and what is said over heads (floats: a blow's hearts, "+1 wood"). Their state moves in render.js, as
// it did for the old flat picture (where they alone were drawn: none of it showed here). Each is a sprite of the land's list (hd.js):
// a picture px for px at its place, its foot on the ground where it is, hidden by land in front of it as a body is; a height over
// the ground is px over its foot. The flat picture's y had the height in it (north was up): ground y + height there = its y.
const HdFx = (() => {
  const cvs = new Map(), last = {parts: 0, puffs: 0, loot: 0, orbs: 0, fire: 0, falls: 0, floats: []};
  const made = (k, w, h, paint) => { let c = cvs.get(k); if (!c) { c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d"); g.imageSmoothingEnabled = false; paint(g); cvs.set(k, c); } return c; };
  const opaque = (c) => { const m = /^rgba\((\d+),(\d+),(\d+),([\d.]+)\)$/.exec(String(c).replace(/\s/g, "")); return m ? [`rgb(${m[1]},${m[2]},${m[3]})`, +m[4]] : [c, 1]; };   // (a sprite's px is there or not: its see-through is its fade, a 2x2 dither)
  const top = (x, y) => { const c = Voxels.host.column(Math.floor(x), Math.floor(y)); return c && c.length ? c[c.length - 1] : 0; };
  const ground = (x, y) => floorAt(Math.floor(x), Math.floor(y));
  const dot = (c, s) => { const [cl] = opaque(c); return made("d" + cl + s, s, s, (g) => { g.fillStyle = cl; g.fillRect(0, 0, s, s); }); };
  // a round puff in whole art px, its edge a px darker (effects.js drawPuffs, pixelOval)
  const puff = (r) => made("p" + r, 2 * r + 1, 2 * r + 1, (g) => { for (let j = 0; j <= 2 * r; j++) for (let i = 0; i <= 2 * r; i++) { const d = Math.hypot(i - r, j - r); if (d > r + .3) continue; g.fillStyle = r >= 2 && d > r - .7 ? "rgb(150,128,116)" : "rgb(246,240,228)"; g.fillRect(i, j, 1, 1); } });
  const orb = (big, flick) => made("o" + big + flick, big ? 7 : 5, big ? 7 : 5, (g) => { const col = {o: "#4f8a2a", y: flick ? "#b9e45a" : "#dcf27a", w: "#fffbd8"}; (big ? ORB_BIG : ORB).forEach((row, j) => [...row].forEach((c, i) => { if (c !== ".") { g.fillStyle = col[c]; g.fillRect(i, j, 1, 1); } })); });
  const cell = (img, sx, sy, w, h, flip = false) => made([img.src || img.id || "", sx, sy, w, h, flip].join(), w, h, (g) => { if (flip) { g.translate(w, 0); g.scale(-1, 1); } g.drawImage(img, sx, sy, w, h, 0, 0, w, h); });
  const ok = (img) => img && img.complete !== false && (img.naturalWidth || img.width);
  // -> into `list`, this frame's sprites (hd.js after): p, who looks (only what is near)
  function add(list, p, now, dt) {
    const t = now / 1000, near = (x, y) => Math.abs(x - p.x) < 26 && y > p.y - 26 && y < p.y + 26, put = (s) => { if (near(s.x, s.y)) list.push(Object.assign({d: true, still: true}, s)); };
    let n = 0;
    for (const q of parts) { if (q.age < 0 || q.age > q.life) continue; const base = q.floor !== undefined ? q.floor : (q.by === undefined ? (q.by = q.y + HdLevel.DRAW_AT.chip[1]) : q.by), [, a] = opaque(q.c);   // (a chip: its floor; a spark or a puff of dust: where it came out, a little over the ground)
      put({canvas: dot(q.c, q.s), fx: 0, fy: q.s + Math.round(Math.max(0, base - q.y) * 16), x: q.x, y: base, z: ground(q.x, base), fade: Math.min(1, 3.3 * (1 - q.age / q.life)) * a}); n++; }
    last.parts = n; n = 0;
    for (const q of puffs) { if (q.age < 0 || q.age > q.life) continue; const k = q.age / q.life, r = Math.max(1, Math.round(q.r + q.grow * k)), base = q.by === undefined ? (q.by = q.y + HdLevel.DRAW_AT.puff[1]) : q.by;
      put({canvas: puff(r), fx: r, fy: r + Math.round(Math.max(0, base - q.y) * 16), x: q.x, y: base, z: ground(q.x, base), fade: (1 - k) * .85}); n++; }
    last.puffs = n; n = 0;
    for (const f of falls) { const k = (now - f.t0) / 1000, fr = Math.floor(k * 14), img = f.thin ? IMG.thin_fall : IMG.tree_fall; if (fr < 0 || fr >= 12 || !ok(img)) continue; const [bx, by] = brink(f.x, f.y);   // (the pack's felling sheet: its trunk at x 32 to 48 of a frame, mirrored about it to fall the other way)
      put({canvas: cell(img, fr * 64, 0, 64, 48, f.side > 0), fx: f.side > 0 ? 24 - bx : 40 - bx, fy: 44 - by, x: f.x + .5, y: HdLevel.foot("stood", f.x, f.y)[1], z: Math.max(top(f.x, f.y), ground(f.x, f.y)), fade: fr >= 9 ? 1 - (fr - 9) / 3 : 1}); n++; }
    last.falls = n; n = 0;
    for (const f of flyers) { const k = (now - f.t0) / FLY_MS; if (k >= 1 || (k < 0 && !f.drop) || !ok(IMG.trees)) continue; let y = f.y, x = f.x, a = 1;   // (fruit off a tree, berries off a bush: effects.js drawFlyers)
      if (k < 0) { const tf = (now - f.drop.t0) / 1000; if (tf < 0) continue; if (tf * 1000 < f.drop.fall) y = f.drop.top + .5 * FRUIT_G * tf * tf; }
      else { const who = f.by && [...ents.values()].find((q) => q.e && q.e.name === f.by), e = k * k * (3 - 2 * k); if (who) { x = f.x + (who.x + .5 - f.x) * e; y = f.y + (who.y + .1 - UP - f.y) * e - Math.sin(k * Math.PI) * 1.1; } else { y -= k * .8; a = 1 - k; } if (k > .7) a = Math.min(a, (1 - k) / .3); }
      put({canvas: cell(IMG.trees, f.ix, f.iy, 16, 16), fx: 8, fy: 8 + Math.round(Math.max(0, f.y - y) * 16), x, y: f.y, z: ground(x, f.y), fade: a}); }
    for (const f of plucks) { const ms = now - f.t0, [img, a0, b0, w, h, dx, dy] = f.spr; if (ms > TUG_MS + PLUCK_MS || !ok(img)) continue; let ox = 0, oy = 0, a = 1;   // (a plant pulled up: effects.js drawPlucks; never smaller: it fades as it is caught)
      if (ms < TUG_MS) oy = -Math.sin(ms / TUG_MS * Math.PI / 2) * .25; else { const k = (ms - TUG_MS) / PLUCK_MS, e = k * k * (3 - 2 * k), who = f.by && [...ents.values()].find((q) => q.e && q.e.name === f.by); if (who) { ox = (who.x - f.x) * e; oy = -.25 + (who.y - .3 - f.y + .25) * e - Math.sin(k * Math.PI) * .8; } else { oy = -.25 - k * .6; a = 1 - k; } if (k > .8) a = Math.min(a, (1 - k) / .2); }
      put({canvas: cell(img, a0, b0, w, h), fx: 8 - dx, fy: 16 - dy + Math.round(Math.max(0, -oy) * 16), x: f.x + ox + .5, y: HdLevel.foot("stood", f.x, f.y)[1], z: ground(f.x + ox, f.y), fade: a}); }
    for (const l of loot) { const s = (now - l.t0) / 1000; if (s < 0) continue; let h = 0, dk = 1, since = 1;   // a drop hopping out to its place in the pile (loot.js drawLoot), then two bounces; the pile shows once all of its tile's have landed (hd.js)
      if (s < l.flight) { h = -(l.vy * s + LOOT_G * s * s / 2); dk = s / l.flight; } else { let u = s - l.flight, m = 0; while (m < LOOT_HOPS.length && u > LOOT_HOPS[m]) u -= LOOT_HOPS[m++]; if (m < LOOT_HOPS.length) { h = LOOT_G * LOOT_HOPS[m] / 2 * u - LOOT_G * u * u / 2; since = u; } }
      const dip = s > l.flight && since < .05 ? 1 : 0;   // (a px into the ground as it touches down)
      const [ox, oy] = lootFrom(l, dk);   // (let go of in front of you: from you to its place, loot.js)
      put({canvas: ghostIcon(l.name), fx: 5, fy: 11 - Math.round(l.dy * dk) + Math.max(0, Math.round(h * 16)) - dip, x: l.x + ox + .5 + Math.round(l.dx * dk) / 16, y: HdLevel.foot("pile", l.x, l.y + oy)[1], z: ground(l.x, l.y), pile: true}); n++; }   // (pile: its shadow on the ground under it, hd.js pieces)
    last.loot = n; n = 0;
    for (const o of orbs) { if (o.age < 0) continue; const w = Math.max(0, Math.min(1, (o.age - o.homing) / .2)), by = o.y + (UP + .15) * w;   // (homing: to your middle, the flat picture's y up by UP: here over your feet)
      put({canvas: orb(o.big, Math.sin(o.age * 14 + o.seed) > 0), fx: o.big ? 3 : 2, fy: (o.big ? 4 : 3) + Math.round(o.h * 8 + Math.max(0, by - o.y) * 16), x: o.x, y: by, z: ground(o.x, by)}); n++; }
    for (const m of magnets) { const pl = playerNamed(m.who); if (m.age < 0 || !pl) continue; const k = Math.min(1, m.age / .28), e = k * k, x = m.x + (pl.x + .5 - m.x) * e, gy = m.y + (pl.y + .5 - m.y) * e, lift = (gy - (m.y + (pl.y + .3 - UP - m.y) * e)) + Math.sin(k * Math.PI) * .35;
      put({canvas: ghostIcon(m.name), fx: 5, fy: 6 + Math.round(lift * 16), x, y: gy, z: ground(x, gy), fade: k > .7 ? (1 - k) / .3 : 1}); n++; }
    last.orbs = n; n = 0;
    for (const f of fireAt) { if (!near(f.x, f.y) || !ok(IMG.gen)) continue; const tall = "TF".includes(combAt(f.x, f.y) || ""), z = Math.max(top(f.x, f.y), ground(f.x, f.y));   // flames over whatever burns, taller over a tree (the generated two-frame flame, world_decor's drawFire)
      const fl = (tt, dx, up, ax, ay) => put({canvas: cell(IMG.gen, ...genCell(Math.floor(tt * 8 + ax * 3 + ay) % 2 ? "fire1" : "fire0"), 16, 16), fx: 8, fy: 19 + up, x: f.x + .5 + dx, y: f.y + 1, z, lamp: up ? 0 : Light.lamp("fire"), d: false});   // (d: false: as near as a body's head, never under the posts of the fence it burns)
      fl(t, 0, 0, f.x, f.y); if (tall) { fl(t + 1, -.3, 14, f.x + 7, f.y); fl(t + 2, .3, 22, f.x, f.y + 5); }
      if (Math.random() < dt * 6) parts.push({x: f.x + .2 + Math.random() * .6, y: f.y - (tall ? 1.6 : .3), vx: (Math.random() - .5) * .4, vy: -1.2, g: -.5, life: 1.2, age: 0, c: Math.random() < .5 ? "#6b6f73" : "#ffb454", s: 1, by: f.y + .9}); n++; }   // (smoke and sparks going up)
    last.fire = n;
  }
  // the small heart beside a blow's number (2 px a pixel), as the flat picture had it
  const HEART = [".oo.oo.", "owrorro", "orrrrro", ".orrro.", "..oro..", "...o..."];
  // what is said over heads, in the words pass (hd.js written: on the game's canvas with the names): over whom it is about, rising and fading
  function words(seen, at) {
    const c = ctx;
    last.floats = []; if (!seen || !floats.length) return; const t = performance.now() / 1000, S = TS();
    c.textAlign = "center"; c.font = "18px SproutPixel";
    for (const f of floats) { const k = t - f.t; if (k < 0 || k >= 1.4) continue;
      const s = seen.list.find((v) => v.q && v.q.tx === f.x && v.q.ty === f.y), a = s ? at(s.x, s.y, s.z) : at(f.x + .5, f.y + .5, ground(f.x, f.y)); if (!a) continue;
      const x = onArt(a[0]) - (f.heart ? onArt(9) : 0), y = onArt(a[1] - 22 * artPx() - (s && s.q.e && s.q.e.kind === "agent" ? 22 : 0) - k * S * .7);   // (over the head, a whole art px; over a person's name)
      c.globalAlpha = 1 - k / 1.4; outlined(f.text, x, y, f.color); last.floats.push([f.text, x, y]);
      if (f.heart) { const hx = x + Math.ceil(c.measureText(f.text).width / 2) + 4, hy = y - 13; HEART.forEach((row, j) => [...row].forEach((ch, i) => { if (ch !== ".") { c.fillStyle = ch === "o" ? "#5b3f36" : ch === "w" ? "#ffd9d0" : "#e8554a"; c.fillRect(hx + i * 2, hy + j * 2, 2, 2); } })); } }
    c.globalAlpha = 1; c.textAlign = "start";
  }
  return {add, words, last};
})();
