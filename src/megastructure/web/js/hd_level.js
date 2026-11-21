// The HD look (hd.js): WHERE YOU ARE, as its picture has it. Three answers, each from the land's own shape and the height the game keeps for you (caves.js `myAt`, as the server does):
//   of(p, now)  -> [L, Lf]: the level you stand at (your tile's), and the same between two tiles: on the straight line between their heights (the game's own line, relief.js liftOf: a hop is an arc over it).
//     (L was the land's TOP unless the classic x-ray had opened (xray.a): that one never opens during a hop, and a stair is hop after hop: all the way down a covered stair you were drawn on the grass over it, the window shut,
//      "the game thinks the player is still out". And your body went a whole level at each tile's middle: 16 px down the screen and back, every step of a stair.)
//   steep(tx, ty, L, was, k0) -> is the eye to look from above (hd.js api.steep). In: a roof of two levels over you, six levels of land over the eye's line south of you, or a shaft or a trench (walls of three or more on three sides, or on two that face each other).
//     Out: none of them left: no roof, under five levels over the line, and no wall of two or more on two sides (a dug stair's last step but one): the land's shape, not a clock. (A shaft six deep was seen from the side and its
//     way out, one step on, from above: two views a step apart.)
//   own(tx, ty, L, cov) -> the boxes of the x-ray window that are yours whatever the search for your space has found yet: your tile, floor to ceiling, and the covered tiles you just came from (vox_style.js adds the ones its window lacks)
const HdLevel = (() => {
  const col = (x, y) => Voxels.host.column(x, y), topAt = (x, y) => { const c = col(x, y); return c && c.length ? c[c.length - 1] : 0; };
  const solid = (c, z) => { if (!c) return false; for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  let trail = [];
  function of(p, now) {
    const H0 = Voxels.host, rx = Math.round(p.x), ry = Math.round(p.y), near = typeof myAt !== "undefined" && myAt && Math.abs(myAt.x - rx) + Math.abs(myAt.y - ry) <= 2;
    const at = (x, y) => { const t = topAt(x, y), s = near ? Floors.standOf(p, x, y) : xray.a > .5 ? xray.L : t; return s >= t && H0.water && H0.water(x, y) && H0.waterTop ? Math.max(s, H0.waterTop(x, y)) : s; };   // (in water: at its face)
    const cl = Climb.climbOf(p); if (cl) return [Math.floor(cl.h), cl.h];   // (on a ladder's rungs: as high as you have climbed)
    const L = at(rx, ry), ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y); if ((ax === bx && ay === by) || falling(p, now)) return [L, L];
    const la = at(ax, ay), lb = at(bx, by), f = ax === bx ? p.y - ay : p.x - ax; return [L, Math.abs(la - lb) >= FALL.from ? L : la + (lb - la) * f];   // (a fall: the eye and the body have their own way down, hd.js)
  }
  function steep(tx, ty, L, was, k0) {
    const over = Math.max(0, topAt(tx, ty) - L); let enc = 0, w2 = 0, w3 = 0; for (let d = 1; d <= 20; d++) enc = Math.max(enc, topAt(tx, ty + d) - L - 1 - (d - .5) * k0);
    const up = [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => topAt(tx + dx, ty + dy) - L); for (const t of up) { if (t >= 2) w2++; if (t >= 3) w3++; }
    return was ? over >= 1 || enc >= 5 || w2 >= 2 : over >= 2 || enc >= 6 || w3 >= 3 || (up[0] >= 3 && up[1] >= 3) || (up[2] >= 3 && up[3] >= 3);
  }
  function own(tx, ty, L, cov) {
    if (!cov) { trail = []; return trail; }
    const c = col(tx, ty), roof = topAt(tx, ty) > L; let hi = L + 1; if (roof) while (hi < L + 6 && !solid(c, hi + 1)) hi++;
    const b = roof ? [tx, ty, L, hi] : [tx, ty, L, L + 2, 1], l = trail[trail.length - 1]; if (l && l[0] === tx && l[1] === ty && l[2] === L) return trail;
    trail = trail.filter((t) => t.length < 5 && (t[0] !== tx || t[1] !== ty) && Math.abs(t[0] - tx) + Math.abs(t[1] - ty) <= 3).slice(-3).concat([b]); return trail;   // (behind you: only what was under a roof; under the open sky the land there is as it is)
  }
  const rim = (tx, ty, L) => Math.max(L, topAt(tx, ty), topAt(tx + 1, ty), topAt(tx - 1, ty), topAt(tx, ty - 1), topAt(tx, ty + 1));   // (the level of the land round your hole: its rim)
  return {of, steep, own, rim};
})();
