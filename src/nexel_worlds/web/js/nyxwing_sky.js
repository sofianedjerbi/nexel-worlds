// Nyxwing in the land (nyxwing.js, HdFx.add): its entrance, its shadow in the sky, its body breaking into stars.
//   NyxRift(K) -> {rift, quake}; NyxSky(K) -> {hd}
// Its entrance (#270), in beats of its song from when it came (Nyx.began: a late player's from where it is): the land
// shakes, a gold tear splits the air beside you, taller than it, cracks of light run out over the ground and up the air,
// it tears open wider than its wings, stars pour out, two eyes open in it, a roar (beat 24), it comes up out of the
// dark, and on the drop (beat 32) it steps out in a flash and a shockwave, the rift slammed shut behind it.
const NyxRift = (K) => {
  const {ARRIVE, BEAT, GOLD, began, speck, st} = K;
  const RX = 72, RY = 82, UP = 86, CW = 2 * RX + 100, CH = UP + RY + 62, GY = CH - 6, CX = CW / 2, CY = GY - UP;   // art px: the rift, its canvas
  const GW = 300, GH = 96;                                                       // the ground's cracks (seen flat: a third as deep)
  const rgb = (r, g, b) => (255 << 24 | b << 16 | g << 8 | r) >>> 0;               // (a px of an ImageData, read as one number)
  const [GLD, PALE, WHITE, VIO, LILAC] = [[255, 207, 90], [255, 243, 192], [255, 255, 255], [169, 130, 255], [216, 200, 255]].map((c) => rgb(...c));
  const WIDE = 16;                                                               // (the beat it is torn open wide by)
  let seed = 11; const r1 = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const crack = (x, y, a, len, flat, depth = 0) => {                            // a jagged line of light, a branch or two off it
    const pts = []; let ang = a;
    for (let d = 0; d < len; d++) { if (d % 3 === 0) ang += (r1() - .5) * .9; x += Math.cos(ang); y += Math.sin(ang) * (flat ? .32 : 1); pts.push([Math.round(x), Math.round(y), d / len]); }
    const out = [{pts, from: 0}];
    if (!depth) for (let b = 0; b < 2; b++) { const q = pts[Math.floor(pts.length * (.35 + r1() * .4))];
      for (const c of crack(q[0], q[1], ang + (r1() < .5 ? -1 : 1) * (.6 + r1() * .5), len * .45, flat, 1)) out.push({pts: c.pts, from: q[2]}); }
    return out;
  };
  const ground = [], air = [];
  for (let i = 0; i < 9; i++) { const a = i / 9 * Math.PI * 2 + r1() * .4; ground.push(...crack(GW / 2 + Math.cos(a) * 10, GH / 2 + Math.sin(a) * 3, a, 60 + r1() * 70, true)); }
  for (let i = 0; i < 11; i++) { const a = -Math.PI * (.1 + .08 * i) + (r1() - .5) * .2; air.push(...crack(CX + Math.cos(a) * RX, CY + Math.sin(a) * RY, a, 26 + r1() * 34, false)); }
  const JAG = Array.from({length: 44}, (_, i) => .86 + r1() * .22 + (i % 3 ? 0 : .08)), N = 22;
  const stars = Array.from({length: 110}, () => [r1() * Math.PI * 2, Math.sqrt(r1()), r1()]);
  const clamp = (v) => Math.max(0, Math.min(1, v)), seg = (u, a, b) => clamp((u - a) / (b - a)), ease = (t) => t * t * (3 - 2 * t);
  // how hard the land shakes (art px), from its first rumble to the drop
  const shakeOf = (u) => u < 4 ? .3 + u * .35 : u < 9 ? 1.4 : u < 24 ? .8 : u < 26.5 ? 3.2 * (1 - seg(u, 24, 26.5)) + .8 : u < 32 ? 1 + 1.5 * seg(u, 28, 32) : 6 * (1 - seg(u, 32, 34));
  const picture = (s, k, w, h) => { if (!s[k]) { const c = document.createElement("canvas"); c.width = w; c.height = h; s[k] = c; } return s[k]; };
  const made = new Map(), pixels = (col, n) => { const k = col + "," + n; if (!made.has(k)) { const c = speck(col, n); made.set(k, [c.width, c.height, new Uint32Array(c.getContext("2d").getImageData(0, 0, c.width, c.height).data.buffer)]); } return made.get(k); };
  const lines = (b, w, h, list, grow, hot) => {                                // cracks grown so far, gold with a violet glow (white sparks running on them)
    for (const c of list) { const k = (grow - c.from) / (1 - c.from); if (k <= 0) continue;
      for (const [x, y, f] of c.pts) { if (f > k) break; if (x < 1 || y < 1 || x >= w - 1 || y >= h - 1) continue;
        if ((x + y) % 2 === 0) { b[y * w + x - 1] ||= VIO; b[y * w + x + 1] ||= VIO; }
        b[y * w + x] = (x + y + hot) % 7 ? GLD : WHITE; } }
  };
  // the tear's half widths on a row (its left, its right): an almond, pointed top and bottom, jagged
  const half = (t, rx) => { const h = Math.pow(Math.max(0, 1 - Math.abs(t) ** 1.9), .72) * rx, i = Math.round((t + 1) / 2 * N); return [h * JAG[(i + N) % 44], h * JAG[i % 44]]; };
  function tear(b, u, rx, ry, k) {                                              // open: night turning in it, a gold rim, a violet glow round it
    for (let y = Math.max(0, Math.floor(CY - ry)); y <= Math.min(CH - 1, CY + ry); y++) {
      const t = (y + .5 - CY) / ry, [hl, hr] = half(t, rx);
      for (let x = Math.max(0, Math.floor(CX - hl - 4)); x <= Math.min(CW - 1, CX + hr + 4); x++) {
        const dx = x + .5 - CX, o = y * CW + x;
        if (dx < -hl || dx > hr) { if ((x + y) % 2 === 0 && dx > -hl - 4 && dx < hr + 4) b[o] = VIO; continue; }
        if (dx < -hl + 2 || dx > hr - 2 || Math.abs(t) > .97) { b[o] = (x * 2 + y + Math.floor(u * 9)) % 6 ? PALE : WHITE; continue; }
        if (k > 0 && (x + y) % 2 && r1() < k) { b[o] = WHITE; continue; }    // (the flash as it shuts)
        const e = Math.min(1, Math.hypot(dx / rx * .9, t)), th = Math.atan2(t, dx / rx), arm = Math.sin(4 * th + 8 * e - u * 1.1);
        const q = clamp(e * e * .8 + (arm > .55 ? .25 : arm > .15 ? .1 : 0) * (.3 + e) + ((x + y) % 2 ? .03 : 0));
        b[o] = rgb(Math.round(5 + 75 * q), Math.round(2 + 34 * q * q), Math.round(18 + 130 * q));
      }
    }
    for (const [a0, r, z] of stars) { const a = a0 + u * .25 * (z > .5 ? 1 : -1), t = Math.sin(a) * r * .92, [hl, hr] = half(t, rx * .85), x = Math.round(CX + Math.cos(a) * r * (Math.cos(a) < 0 ? hl : hr)), y = Math.round(CY + t * ry);
      if (Math.sin(u * 4 + z * 30) > -.2 && x > 0 && y > 0 && x < CW && y < CH) b[y * CW + x] = z > .8 ? PALE : LILAC; }
  }
  function body(b, u, act) {                                                    // it, coming up out of the dark (21-32): in the rift, its wings past its edge from 30
    if (u < 21 || act !== "arrive") return;
    const k = ease(seg(u, 21, 32)), n = k < .3 ? 4 : k < .55 ? 3 : k < .8 ? 2 : 1, [w, h, d] = pixels(WILD.nyxwing.walk[0] + Math.floor(u * 2) % 8, n);
    const X = Math.round(CX - w / 2), Y = Math.round((1 - k) * (CY - h / 2) + k * (GY + 8 - h));
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const v = d[j * w + i]; if (v >>> 24 < 128) continue; const x = X + i, y = Y + j;
      if (x < 0 || y < 0 || x >= CW || y >= CH) continue; const o = y * CW + x; if (u > 30 || (b[o] >>> 24 && b[o] !== VIO)) b[o] = v; }
  }
  function rings(b, u) {                                                        // the roar (24-26.5): rings of violet going out from it, and the drop's (32-34)
    for (const [a, r0, r1_, c] of [[24, 20, 110, VIO], [24.5, 20, 110, VIO], [25, 20, 110, VIO]]) { const k = seg(u, a, a + 1.5); if (k <= 0 || k >= 1) continue; const R = r0 + k * (r1_ - r0);
      for (let t = 0; t < Math.PI * 2; t += 1 / R) { const x = Math.round(CX + Math.cos(t) * R), y = Math.round(CY + Math.sin(t) * R * .75); if ((x + y) % 2 === 0 && x >= 0 && y >= 0 && x < CW && y < CH) b[y * CW + x] = c; } }
  }
  function paint(s, u, act) {
    const rc = picture(s, "riftC", CW, CH), g = rc.getContext("2d"), im = g.createImageData(CW, CH), b = new Uint32Array(im.data.buffer);
    const line = ease(seg(u, 4, 8)), open = ease(seg(u, 9, WIDE)) * (1 - ease(seg(u, 32, 33))), breathe = 1 + .03 * Math.sin(u * 2.2);
    const rx = Math.max(1, 3 + (RX - 3) * open * breathe), ry = RY * line * (u >= 32 ? 1 - .7 * seg(u, 32, 33) : 1), hot = Math.floor(u * 9);
    s.rift = {u, line, open, at: performance.now()};                          // (what was drawn last: tests, Nyx.rift)
    if (u < 33) lines(b, CW, CH, air, seg(u, 8, 15) * (open > .05 ? 1 : 0), hot);
    if (line > 0 && open < .02 && u < 32) for (let y = Math.round(CY - ry); y <= CY + ry; y++) {          // the tear, a jagged gold line taller than it
      const x = Math.round(CX + Math.sin(y * .5) * 2 + Math.sin(y * .13) * 4); for (let i = -2; i <= 2; i++) b[y * CW + x + i] = i ? ((y + i) % 2 ? VIO : b[y * CW + x + i]) : (y + hot) % 4 ? PALE : WHITE; }
    else if (open > 0) tear(b, u, rx, ry, u >= 32 ? 1 - seg(u, 32, 32.8) : 0);
    if (open > .5 && u > 14 && u < 23 && !(u > 18 && u < 18.35)) for (const d of [-7, 7]) for (let j = 0; j < (u > WIDE ? 3 : 1); j++) for (let i = -2; i < 2; i++) b[(CY - 11 + j) * CW + CX + d + i] = PALE;   // its eyes
    body(b, u, act); rings(b, u);
    g.putImageData(im, 0, 0); rc._v = (rc._v || 0) + 1;                      // (a new picture each frame: the sprite sheet takes it again, vox_style_sprites.js)
    const gc = picture(s, "riftG", GW, GH), h = gc.getContext("2d"), gm = h.createImageData(GW, GH), gb = new Uint32Array(gm.data.buffer);
    if (u < 37) lines(gb, GW, GH, ground, seg(u, 6, 14), hot);
    const k = seg(u, 32, 34); if (k > 0 && k < 1) { const R = 10 + k * 140; for (let t = 0; t < Math.PI * 2; t += 1 / R) { const x = Math.round(GW / 2 + Math.cos(t) * R), y = Math.round(GH / 2 + Math.sin(t) * R * .3); if (x >= 0 && y >= 0 && x < GW && y < GH) gb[y * GW + x] = PALE; } }   // the shockwave
    h.putImageData(gm, 0, 0); gc._v = (gc._v || 0) + 1;
    return [rc, gc];
  }
  function pour(cx, y, u, rx, ry) {                                             // stars and sparks pouring out of it, more and more as the drop comes; a burst as it shuts
    const n = u > 32 && u < 32.3 ? 25 : u > 9 && u < 32 ? .5 + 2.5 * seg(u, WIDE, 32) : 0;
    for (let i = 0; i < n; i++) { if (Math.random() > n - i) break; const a = Math.random() * Math.PI * 2, t = Math.sin(a) * .9, [hl, hr] = half(t, rx), side = Math.cos(a) < 0 ? -hl : hr, burst = u > 32;
      parts.push({x: cx + (burst ? 0 : side / P), y: y - (UP - t * ry) / P, floor: y, vx: Math.cos(a) * (burst ? 3 : .8), vy: burst ? Math.sin(a) * 3 : .3 + Math.random(), g: burst ? 1 : 3,
        life: .9 + Math.random() * .6, age: 0, c: Math.random() < .3 ? "#ffffff" : Math.random() < .6 ? GOLD[Math.floor(Math.random() * 3)] : "#d8c8ff", s: 1}); }
  }
  const entering = (e, now) => { const u = (now - began(e, now)) / BEAT; return e.act === "arrive" || (u >= ARRIVE && u < ARRIVE + 5) ? u : null; };
  function rift(put, groundAt, now) {
    for (const p of ents.values()) {
      if (!p.e || p.e.kind !== "nyxwing" || !IMG.nyxwing) continue;
      const e = p.e, u = entering(e, now); if (u === null) continue;
      const s = st(e.id), [rc, gc] = paint(s, u, e.act), cx = p.x + .5, z = groundAt(cx, p.y);
      put({canvas: gc, fx: GW / 2, fy: GH / 2, x: cx, y: p.y, z});
      put({canvas: rc, fx: CW / 2, fy: GY, x: cx, y: p.y, z});
      const open = ease(seg(u, 9, WIDE)) * (1 - ease(seg(u, 32, 33)));
      pour(cx, p.y, u, Math.max(1, 3 + (RX - 3) * open), RY * ease(seg(u, 4, 8)));
    }
  }
  // the land shaking under its entrance (art px, for the camera: jump.js fallShake)
  const quake = (now) => { let a = 0; for (const p of ents.values()) if (p.e && p.e.kind === "nyxwing") { const u = entering(p.e, now); if (u !== null && u < ARRIVE + 2) a = Math.max(a, shakeOf(u)); }
    return Math.round(Math.sin(now / 1000 * 61) * a); };
  return {rift, quake};
};

const NyxSky = (K) => {
  const {BEAT, GOLD, LOCK, SKY, cell, dying, eclipse, marker, oval, rift, st} = K;
  // ---- in the land (HdFx.add): its shadow in the sky, its body breaking into stars
  function hd(put, groundAt, now) {
    rift(put, groundAt, now);                                                 // its entrance (NyxRift)
    const at = (x, y, c, high, fade = 1) => put({canvas: c, fx: Math.floor(c.width / 2), fy: c.height + Math.round(high), x, y, z: groundAt(x, y), fade});
    for (const p of ents.values()) {
      if (!p.e || p.e.kind !== "nyxwing" || !IMG.nyxwing) continue;
      const e = p.e, s = st(e.id), cx = p.x + .5;
      if (e.act === "sky") {
        const t = now - (s.upAt ?? now), left = SKY - t, locked = left < LOCK;
        at(cx, p.y, oval(56, 14, "#50408a"), 0, .5);
        at(cx, p.y, marker(Math.round(locked ? 24 : 32 + 6 * Math.sin(t / 120)), locked), 0);
        if (t < 400) at(cx, p.y, cell(WILD.nyxwing.dive[0] + 3, 0), t * 1.6);                    // up and away
        if (left < 160) at(cx, p.y, cell(WILD.nyxwing.dive[0] + 4, 0), left * 4);               // and down on you
        if (Math.random() < .6) parts.push({x: cx + (Math.random() - .5) * 2, y: p.y - 6, floor: p.y, vx: 0, vy: 14, g: 0, life: .4, age: 0, c: GOLD[Math.floor(Math.random() * 5)], s: 1});
      }
    }
    for (const [id, d] of dying) {                                           // its body, its pixels leaving it, and the sky taking them
      const u = (now - d.at) / BEAT;
      if (u > 7.5) { dying.delete(id); continue; }
      if (u < 6.5) at(d.x + .5, d.y, eclipse(16), 7 * 16, Math.min(1, u / 1.5) * Math.min(1, (6.5 - u) / .8));
      if (u < 2) at(d.x + .5 + (Math.random() - .5) * .2 * u, d.y, Math.floor(u * 6) % 2 ? d.white : d.body, 0);
      else if (d.left.length) {
        while (d.left.length && d.left[d.left.length - 1].rel <= u) {        // edges first, its heart last
          const q = d.left.pop();
          d.g.clearRect(q.i, q.j, 2, 2);
          const high = (WILD.nyxwing.ch - q.j - 8) / 16, t = 1.35;
          parts.push({x: d.x + .5 + (q.i - WILD.nyxwing.cw / 2) / 16, y: d.y - high, floor: d.y, vx: (-(q.i - WILD.nyxwing.cw / 2) / 16) / t, vy: -.5, g: -2 * (7 - high) / (t * t), life: t, age: 0, c: Math.random() < .35 ? "#ffffff" : q.c, s: 2});
        }
        at(d.x + .5, d.y, d.canvas, 0);
      }
    }
  }
  return {hd};
};
