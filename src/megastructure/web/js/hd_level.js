// The HD look (hd.js): WHERE YOU ARE, as its picture has it. Three answers, each from the land's own shape and the height the game keeps for you (caves.js `myAt`, as the server does):
//   of(p, now)  -> [L, Lf]: the level you stand at (your tile's), and the same between two tiles: on the straight line between their heights (the game's own line, relief.js liftOf: a hop is an arc over it).
//     (L was the land's TOP unless the classic x-ray had opened (xray.a): that one never opens during a hop, and a stair is hop after hop: all the way down a covered stair you were drawn on the grass over it, the window shut,
//      "the game thinks the player is still out". And your body went a whole level at each tile's middle: 16 px down the screen and back, every step of a stair.)
//   over(x, y, L, k) -> LEVELS OF LAND OVER THE EYE'S LINE to the feet of somebody on (x, y) at L (k: levels the line climbs a tile south, 2 tan(pitch)): 0: seen through the open air (or a cave's mouth);
//     1: half a body hidden; 2 or more: all of it (99: the line runs into a ceiling, or into anything when a roof is over the feet: nothing of a body shows). A block somebody put (a wall you built) is not land. EVERY question of "does land hide this" is asked here (they were three: hd.js `hidden`, the land search's own, the tilt's walls).
//   sunk(x, y, L, k, n) -> a tile under the open sky that is IN the land, not behind it: land over the line to it (more than half a body) AND land north of it too (two levels over it within six tiles): a pit, a trench,
//     a dug stair's tread, a gorge's floor. Behind a hill, a ridge, a cliff, a wall: not. under(x, y, L, k): a roof over it, or sunk: there the x-ray window is; behind land you show through it (vox_style.js), nothing is opened.
//   steep(tx, ty, L, was, k0, ver) -> is the eye to look from above (hd.js api.steep). ONE rule: the floor you stand on (the tiles at your level you can walk to within three steps) and the eye's line at the surface's pitch:
//     when no tile of it shows from the side (two levels of land or more over the line to each: a whole body), the eye looks from above; back when one of them shows again (under one level). The land's shape, not a clock.
//     (It was by the walls beside you: a stair one tile wide tipped at its second step, one three wide never, a pit at its first dig, a cave three tiles deep at its mouth.) ver: changes when the land does
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
  function over(x, y, L, k, n = 20) { let m = 0; for (let d = 1; d <= n; d++) { const c = col(x, y + d), e = L + (d - .5) * k; if (!c || !c.length || matAt(x, y + d)) continue; for (let i = 0; i < c.length; i += 2) if (c[i] > e && (i ? c[i - 1] : -1e9) < e + k) m = Math.max(m, i && c[i - 1] > e ? 99 : c[i] - e); } return m > 0 && topAt(x, y) > L ? 99 : m; }
  const sunk = (x, y, L, k, n) => { if (over(x, y, L, k, n) <= 1) return false; for (let d = 1; d <= 6; d++) if (topAt(x, y - d) >= L + 2) return true; return false; };
  const under = (x, y, L, k) => topAt(x, y) > L || sunk(x, y, L, k);
  let sk = "", sv = 0;
  function steep(tx, ty, L, was, k0, ver) {
    const key = [tx, ty, L, ver].join(); if (key !== sk) { sk = key; sv = 1e9; const seen = new Set([tx + "," + ty]); let fr = [[tx, ty]];
      for (let n = 0; n <= 3 && sv > 0; n++) { const nx = []; for (const [x, y] of fr) { sv = Math.min(sv, over(x, y, L, k0)); for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const X = x + dx, Y = y + dy, c = col(X, Y), q = X + "," + Y; if (!seen.has(q) && solid(c, L) && !solid(c, L + 1) && !solid(c, L + 2)) { seen.add(q); nx.push([X, Y]); } } } fr = nx; } }
    return was ? sv >= 1 : sv >= 2;
  }
  function own(tx, ty, L, cov) {
    if (!cov) { trail = []; return trail; }
    const c = col(tx, ty), roof = topAt(tx, ty) > L; let hi = L + 1; if (roof) while (hi < L + 6 && !solid(c, hi + 1)) hi++;
    const b = roof ? [tx, ty, L, hi] : [tx, ty, L, L + 2, 1], l = trail[trail.length - 1]; if (l && l[0] === tx && l[1] === ty && l[2] === L) return trail;
    trail = trail.filter((t) => t.length < 5 && (t[0] !== tx || t[1] !== ty) && Math.abs(t[0] - tx) + Math.abs(t[1] - ty) <= 3).slice(-3).concat([b]); return trail;   // (behind you: only what was under a roof; under the open sky the land there is as it is)
  }
  const rim = (tx, ty, L) => Math.max(L, topAt(tx, ty), topAt(tx + 1, ty), topAt(tx - 1, ty), topAt(tx, ty - 1), topAt(tx, ty + 1));   // (the level of the land round your hole: its rim)
  return {of, steep, own, rim, over, sunk, under, get shows() { return sv; }};
})();
