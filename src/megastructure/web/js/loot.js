// Loot: what a creature (or a person) drops pops out of the poof, arcs up and lands with a bounce or two, right where
// the pile then shows. The pile at that tile waits until everything has landed, so nothing appears twice.

const loot = [];
const LOOT_G = 26;   // gravity, in tiles/s² (a quick, light hop)

function dropLoot(x, y, items, now) {
  const names = Object.keys(items || {}).filter((n) => items[n] > 0);
  names.slice(0, 3).forEach((name, i, all) => {
    const slot = (i - (all.length - 1) / 2) * 4 / P;               // the same place the pile draws it
    const flight = .42 + Math.random() * .08;
    loot.push({x, y, name, slot, t0: now + 90 + i * 70, flight, vy: -LOOT_G * flight / 2});
  });
}
const lootAt = (x, y) => loot.some((l) => l.x === x && l.y === y);

function drawLoot(sx, sy, S, now, list) {   // queued into the depth-sorted list, like everything on the ground
  const z = zoom, sz = 10 * z;
  for (let i = loot.length - 1; i >= 0; i--) {
    const l = loot[i], s = (now - l.t0) / 1000;
    if (s < 0) continue;
    // a hop from the middle of the tile out to its slot, then two smaller bounces in place
    let h, dxk;
    if (s < l.flight) { h = -(l.vy * s + LOOT_G * s * s / 2); dxk = s / l.flight; }
    else {
      if (!l.landed) { l.landed = true; sfx("tock", l.x, l.y); }
      const b = s - l.flight, hops = [.16, .08];
      let t = b, n = 0;
      while (n < hops.length && t > hops[n]) t -= hops[n++];
      if (n >= hops.length) { loot.splice(i, 1); continue; }
      const up = LOOT_G * hops[n] / 2;
      h = up * t - LOOT_G * t * t / 2; dxk = 1;
    }
    const cx = sx(l.x) + S / 2 + l.slot * dxk * S, ground = sy(l.y, l.x) + S / 2;
    const squash = h < .02 && s > l.flight ? 1 : 0;                 // a pixel flatter as it touches down
    list.push({y: l.y - .01, x: l.x, fx: () => {
      ctx.fillStyle = "rgba(60,40,30,.25)";
      ctx.beginPath(); ctx.ellipse(cx, ground + 5 * z, Math.max(1, 4 - h * 4) * z, 1.5 * z, 0, 0, 7); ctx.fill();
      ctx.drawImage(ghostIcon(l.name), Math.round(cx - sz / 2), Math.round(ground - sz / 2 - h * S + squash * z), sz, sz - squash * z);
    }});
  }
}
