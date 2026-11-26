// Nyxwing in the land (nyxwing.js, HdFx.add): its entrance, its shadow in the sky, its body breaking into stars.
//   NyxSky(K) -> {hd}
const NyxSky = (K) => {
  const {ARRIVE, BEAT, FALL_FROM, GOLD, LOCK, SKY, began, cell, dying, eclipse, marker, oval, speck, st} = K;
  // ---- in the land (HdFx.add): its entrance, its shadow in the sky, its body breaking into stars
  function hd(put, groundAt, now) {
    const at = (x, y, c, high, fade = 1) => put({canvas: c, fx: Math.floor(c.width / 2), fy: c.height + Math.round(high), x, y, z: groundAt(x, y), fade});
    for (const p of ents.values()) {
      if (!p.e || p.e.kind !== "nyxwing" || !IMG.nyxwing) continue;
      const e = p.e, s = st(e.id), cx = p.x + .5;
      if (e.act === "arrive") {
        const u = (now - (began(e) ?? now)) / BEAT, open = Math.min(1, Math.max(0, (u - 1) / 5)), q = Math.min(1, Math.max(0, (u - FALL_FROM) / (ARRIVE - FALL_FROM)));
        if (open > 0 && q < 1) at(cx + 4, p.y, eclipse(Math.max(3, Math.round(16 * open))), 7 * 16, 1 - q * q);
        if (u < FALL_FROM) continue;
        const k = 1 - q, ang = q * 2.6 * Math.PI, gx = cx + 4 * k * Math.cos(ang), gy = p.y + 2 * k * Math.sin(ang), high = 7 * 16 * k ** 1.25;
        const n = q < .3 ? 4 : q < .55 ? 3 : q < .8 ? 2 : 1, col = wildFrame(WILD.nyxwing.walk, now, true);
        at(gx, gy, oval(Math.max(4, Math.round(56 * q)), Math.max(2, Math.round(14 * q)), "#50408a"), 0, .45 * q);    // (see-through: a fade, HdFx's dither)
        at(gx, gy, speck(col, n), high);
        if (Math.random() < .2 + .6 * q) parts.push({x: gx + (Math.random() - .5) * 3 * q, y: gy - high / 16 - 2 * q, floor: gy, vx: (Math.random() - .5) * .6, vy: .4, g: 0, life: .7, age: 0, c: GOLD[Math.floor(Math.random() * 5)], s: 1});
      } else if (e.act === "sky") {
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
