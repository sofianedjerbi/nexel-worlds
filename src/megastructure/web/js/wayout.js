// The way out of the ground, found ("i dont know how to get out of that cave", "It looks like we can get out but no
// evident way or block to break !!"): from where you stand to the nearest place under the open sky that is OUT (land
// round it no higher than a hop or two: not a shaft's bottom). It knows no game name: the world is handed in, so it
// runs alone under node (tests/test_wayout.py), and its answer is played on the real simulation there.
//   W: {solid(x, y, z): land or something built; land(x, y, z): a cell of land a dig takes; top(x, y): the land's top;
//       step(h, x, y, fx, fy) -> the level a step lands at | null (if not given: the game's rule, below);
//       enter(x, y, z): you may stand there; can(x, y, h, dx, dy): a step is cut here (digup.js offers it);
//       on(x, y, z): the wall in front is dug on; down(x, y, z): the floor under you is dug}
// The moves are the game's (sim/bodies.py lands, sim/underground.py): a step level, up one (a jump: its key is shown on it, wayshow.js) with room over both
// heads, down however far (a fall over 3 hurts: very dear), a ladder (the game's step). And with a pickaxe:
//   cut a step ("up": R): the cell over your head, the cell in front at your head's height, then the hop;
//   dig on ("use"): the cell in front at your body's height, then the step in;
//   dig down ("alt"): the cell you stand on. (The names of the moves: both are X's, the break key's: wayshow.js `press`.)
// A step costs 1, a block 30: so first WITHOUT digging (a real way out, however long, within reach: you are not
// trapped), and only if there is none the way with the fewest blocks to break, then the shortest. Trapped is geometry:
// no way out on foot AND the places you reach on foot are all inside your reach: a gorge's river that goes on past it
// is no trap ("the escape detection triggers when swimming between canyons": you swim along it).
// The land is read as it is now: a block broken on the way is not gone for the steps after it (but nobody stands on
// one). The way is found again each time the land changes, and its first move is always true.
const WayOut = (() => {
  const WAYS = [[1, 0, "E"], [-1, 0, "W"], [0, -1, "N"], [0, 1, "S"]], TURN = .01,      // (of two ways as good: the one that goes straight on; east or west first: a stair seen from its side; south last: its blocks stand between the eye and you)
     DIG = 30, FALL = 3, HURT = 100, R = 28;      // (HURT: a level of a fall that costs hearts: more than three blocks: the way shown is not one that hurts while a stair can be cut. It was 6: out of a shaft in the stone mountain the way dropped six into the river)
  const key = (x, y, z) => ((x + 32768) * 65536 + (y + 32768)) * 2048 + (z + 1024);
  // out: under the open sky and not walled in (of the 49 tiles round it, 12 at most stand higher than a hop), nor at
  // the bottom of a gorge or a wide pit (of 49 tiles looked at 9 around, half at most stand over three higher: the
  // river between two cliffs of twelve was "out", and nothing was ever shown to who fell in)
  function out(W, x, y, z) {
    if (W.top(x, y) > z) return false;
    let n = 0; for (let j = -3; j <= 3; j++) for (let i = -3; i <= 3; i++) if (W.top(x + i, y + j) > z + 1 && ++n > 12) return false;
    n = 0; for (let j = -9; j <= 9; j += 3) for (let i = -9; i <= 9; i += 3) if (W.top(x + i, y + j) > z + 3 && ++n > 24) return false;
    return true;
  }
  const stepOf = (W) => W.step || ((h, x, y, fx, fy) => { if (W.solid(x, y, h + 1)) return W.solid(x, y, h + 2) || W.solid(fx, fy, h + 2) ? null : h + 1; let z = h; while (!W.solid(x, y, z)) z--; return z; });
  function heap() {      // (the cheapest first)
    const a = [];
    return {get size() { return a.length; },
      push(c, v) { let i = a.length; a.push([c, v]); while (i) { const p = (i - 1) >> 1; if (a[p][0] <= c) break; [a[p], a[i]] = [a[i], a[p]]; i = p; } },
      pop() { const t = a[0], l = a.pop(); if (a.length) { a[0] = l; let i = 0; for (;;) { let m = i; const q = 2 * i + 1; if (q < a.length && a[q][0] < a[m][0]) m = q; if (q + 1 < a.length && a[q + 1][0] < a[m][0]) m = q + 1; if (m === i) break; [a[m], a[i]] = [a[i], a[m]]; i = m; } } return t; }};
  }
  // One search from s = {x, y, z}. dig: blocks may be broken. pull: 0, or how much a level still to climb (to zt) weighs
  // (a hurried search for when the plain one ran out: straight up through solid rock). -> {goal, sky, capped, edge: a place
  // past your reach is a step away (what you reach goes on), n}
  function* run(W, s, dig, cap, pull, zt, d0) {
    const step = stepOf(W), enter = W.enter || (() => true), best = new Map(), q = heap(), h = (z) => (pull ? pull * Math.max(0, zt - z) : 0);
    const s0 = {x: s.x, y: s.y, z: s.z, c: 0, from: null, digs: null, d: d0 || null, nd: 0}; best.set(key(s.x, s.y, s.z), s0); q.push(h(s.z), s0);
    let n = 0, sky = 0, edge = false;
    const relax = (x, y, z, c, from, d, digs) => { const k = key(x, y, z), b = best.get(k); if (b && b.c <= c) return;
      if (from.nd) for (let a = from; a; a = a.from) if (a.digs && a.digs.some((e) => e.x === x && e.y === y && e.z === z)) return;      // (the block you would stand on was broken on the way here: a stair that turns back over itself)
      const v = {x, y, z, c, from, d, digs, nd: from.nd + (digs ? 1 : 0)}; best.set(k, v); q.push(c + h(z), v); };
    const fall = (a, b) => (a - b > FALL ? HURT * (a - b - FALL) : 0), drop = (x, y, z) => { while (!W.solid(x, y, z)) z--; return z; };
    while (q.size) {
      const v = q.pop()[1], {x, y, z} = v; if (best.get(key(x, y, z)) !== v) continue;
      if (out(W, x, y, z)) return {goal: v, sky, n, edge, capped: false};
      if (++n > cap) return {goal: null, sky, n, edge, capped: true};
      if (n % 24 === 0) yield;
      if (W.top(x, y) <= z) sky++;
      for (const [dx, dy, d] of WAYS) {
        const qx = x + dx, qy = y + dy; if (Math.abs(qx - s.x) > R || Math.abs(qy - s.y) > R) { if (!dig && !edge) { const e = step(z, qx, qy, x, y); edge = e !== null && enter(qx, qy, e); } continue; }
        const z2 = step(z, qx, qy, x, y), c = v.c + (v.d && v.d !== d ? TURN : 0);
        if (z2 !== null) { if (enter(qx, qy, z2)) relax(qx, qy, z2, c + 1 + (z2 < z - 1 && W.ladder && W.ladder(x, y, z, qx, qy, z2) ? 0 : fall(z, z2)), v, d, null); }
        else if (dig && W.solid(qx, qy, z + 1) && (!W.can || W.can(x, y, z, dx, dy)) && enter(qx, qy, z + 1)) {      // a step cut: head room over you, then over it
          const cells = []; let ok = true;
          for (const [cx, cy] of [[x, y], [qx, qy]]) if (W.solid(cx, cy, z + 2)) { ok = ok && W.land(cx, cy, z + 2); cells.push({x: cx, y: cy, z: z + 2, key: "up", d}); }
          if (ok && cells.length) relax(qx, qy, z + 1, c + 1 + DIG * cells.length, v, d, cells);
        }
        if (dig && W.land(qx, qy, z + 1) && (!W.on || W.on(x, y, z, qx, qy))) { const z3 = drop(qx, qy, z); if (enter(qx, qy, z3)) relax(qx, qy, z3, c + 1 + DIG + fall(z, z3), v, d, [{x: qx, y: qy, z: z + 1, key: "use", d}]); }
      }
      if (dig && W.land(x, y, z) && W.down && W.down(x, y, z)) { const z3 = drop(x, y, z - 1); if (z3 > s.z - 6) relax(x, y, z3, v.c + DIG + fall(z, z3), v, v.d, [{x, y, z, key: "alt", d: null}]); }
    }
    return {goal: null, sky, n, edge, capped: false};
  }
  function pathOf(v) { const p = []; for (; v; v = v.from) p.unshift({x: v.x, y: v.y, z: v.z, d: v.from ? v.d : null, digs: v.digs || [], down: !!(v.from && v.from.x === v.x && v.from.y === v.y)}); return p; }
  // The whole of it, a piece at a time (a generator: `next()` does a few dozen places; the caller stops when its time
  // is up). -> {out: you are out; trapped: no way without digging; path: [{x, y, z, d: the way stepped, digs: the
  // cells broken before that step [{x, y, z, key, d}]}] from where you stand, or null; blocks; sky: the first place
  // of the path under the open sky; n: places looked at}
  function* find(W, s, o = {}) {
    if (out(W, s.x, s.y, s.z)) return {out: true, trapped: false, path: null, blocks: 0, n: 0};
    const a = yield* run(W, s, false, o.walk || 3000, 0, 0, o.d);
    let g = a.goal, n = a.n; const trapped = !g && !a.capped && !a.edge;      // (it was "fewer than 150 places under the sky": a closed canyon was no trap, a long river's was one when narrow)
    if (!g && (trapped || !o.sky)) { const b = yield* run(W, s, true, o.dig || 6000, 0, 0, o.d); g = b.goal; n += b.n;      // (o.sky: under the open sky only a trap's way is shown: no dig search for the rest)
      if (!g && b.capped) { const tops = []; for (let j = -9; j <= 9; j += 3) for (let i = -9; i <= 9; i += 3) tops.push(W.top(s.x + i, s.y + j));      // (the level to climb to: where half the land round you is no more than three higher: `out`. It was the lowest top within reach: in a gorge, its own floor: no pull, no way)
        const zt = tops.sort((p, q) => q - p)[24] - 3;
        const c = yield* run(W, s, true, o.far || 12000, 2 * DIG, zt, o.d); g = c.goal; n += c.n; } }
    const path = g ? pathOf(g) : null;
    return {out: false, trapped, path, n, blocks: path ? path.reduce((t, p) => t + p.digs.length, 0) : 0, sky: path ? path.findIndex((p) => W.top(p.x, p.y) <= p.z) : -1};
  }
  // Is this way (one found before, or the rest of it) still a way, the land as it is now? wayshow.js keeps the way it
  // showed while it is one: found anew at every step, two ways as good took turns (up a step of a stair being cut
  // out of the gorge, back down it, sixty times), and a search was run a tile.
  function holds(W, path) {
    const step = stepOf(W), enter = W.enter || (() => true), drop = (x, y, z) => { while (!W.solid(x, y, z)) z--; return z; }, end = path[path.length - 1];
    for (let i = 1; i < path.length; i++) { const a = path[i - 1], b = path[i], left = b.digs.filter((c) => W.solid(c.x, c.y, c.z));
      if (left.some((c) => !W.land(c.x, c.y, c.z)) || !enter(b.x, b.y, b.z)) return false;
      if (!left.length) { if (b.down || step(a.z, b.x, b.y, a.x, a.y) !== b.z) return false; }
      else if (b.down ? b.z !== drop(b.x, b.y, a.z - 1) : left[0].key === "up" ? b.z !== a.z + 1 || !W.solid(b.x, b.y, b.z) : b.z !== drop(b.x, b.y, a.z)) return false; }
    return path.length > 1 && out(W, end.x, end.y, end.z);
  }
  // ...and all at once (tests)
  function now(W, s, o) { const g = find(W, s, o); for (;;) { const r = g.next(); if (r.done) return r.value; } }
  // what a hand does, in order: [{t: "dig", x, y, z, key, d} | {t: "step", d, x, y, z}]
  const moves = (path) => (path || []).flatMap((p) => [...p.digs.map((c) => ({t: "dig", ...c, d: c.d})), ...(p.d && !p.down ? [{t: "step", d: p.d, x: p.x, y: p.y, z: p.z}] : [])]);
  return {find, now, moves, out, holds, DIG};
})();
if (typeof module !== "undefined") module.exports = WayOut;
