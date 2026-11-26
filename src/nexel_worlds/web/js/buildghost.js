// Build mode, a block of the land in hand (earth, stone): WHERE it will go is a picture. The audit's newcomer could
// not build a wall two high: E lifted the cursor a storey and the screen answered in red letters "Nothing holds it:
// put it against a block" ("show, don't tell": a 'why can't I?' is answered by the picture).
//   - the ghost: the block itself in the cell Space will fill, in its own paint (its top as the land paints a block
//     put down: bare soil, the stone sheet; its front by the land's wall painter, voxpaint.js `front`), whole art px,
//     at 60 %; red where it cannot go (nothing beside it, somebody in it, something there);
//   - every block planned: the same, fainter: two planned on a tile are two blocks, one on the other;
//   - what X will take, and the cursor's own cell: boxes in the land (target.js).
// Stacking needs no height key: on a tile that has your block the cursor rides it (build.js `ride`), and on one you
// only planned the next goes on top of the plan (`cell`). E and Q move the ghost one level (build.js `stops`).
// Drawn with the cursor's keys (prompts.js `build`): the HD look's marks pass, places by HdLook.screenOf. The HD look hands what a painter of marks needs (`HdLook.art()`: an art px, a place's px, is a place behind land): a ghost
// behind a wall keeps one px in two there, fainter (not drawn through the wall, as if in front of it).
const BuildGhost = (() => {
  const paints = new Map(), RED = [232, 85, 74], MOST = 9;
  // the next free cell from z up, over the blocks planned on that tile
  const cell = (p, z, planned) => { let n = z; while (n - z < MOST && planned(p.x, p.y, n)) n++; return n; };
  // a block's own paint, 16 x (16 + a level) art px: its top, then its front
  function paintOf(item) {
    if (paints.has(item)) return paints.get(item);
    let px = null;
    try {
      const stone = item === "stone_block", lv = stone ? 5 : 1, d = sheetData(stone ? hillSheet(lv) : IMG.soil), [bx, by] = blobCell(255), ox = stone ? bx * 16 : 0, oy = stone ? by * 16 : 80;
      px = new Uint32Array(16 * (16 + RELIEF_STEP));
      for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) px[j * 16 + i] = d.px[(oy + j) * d.w + ox + i];
      VoxPaint.front(lv, 0, px, 256, 16, 1);
    } catch (e) { px = null; }
    paints.set(item, px); return px;
  }
  // the faces of the cell: its corners a, b, c, d (a: its paint's top left, a to b its paint's columns, a to d its rows), the cell beyond it. The top, then the sides as the land's walls (its front's paint)
  const FACES = [["T", [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], [0, 0, 1]], ["S", [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]], [0, 1, 0]], ["N", [[1, 0, 1], [0, 0, 1], [0, 0, 0], [1, 0, 0]], [0, -1, 0]],
    ["W", [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0]], [-1, 0, 0]], ["E", [[1, 1, 1], [1, 0, 1], [1, 0, 0], [1, 1, 0]], [1, 0, 0]]];
  const cl = (v) => Math.max(0, Math.min(.999, v));
  // where a place of the screen is on a face (a, b, c, d its corners there) -> [s, t], 0 to 1 across it (the bilinear map turned round)
  function onFace(p, a, b, c, d) {
    const e = [b[0] - a[0], b[1] - a[1]], f = [d[0] - a[0], d[1] - a[1]], g = [a[0] - b[0] + c[0] - d[0], a[1] - b[1] + c[1] - d[1]], h = [p[0] - a[0], p[1] - a[1]], X = (m, n) => m[0] * n[1] - m[1] * n[0];
    const k2 = X(g, f), k1 = X(e, f) + X(h, g), k0 = X(h, e), s = (v) => { const dx = e[0] + g[0] * v, dy = e[1] + g[1] * v; return Math.abs(dx) > Math.abs(dy) ? (h[0] - f[0] * v) / dx : (h[1] - f[1] * v) / (dy || 1e-9); };
    if (Math.abs(k2) < 1e-9) { const v = -k0 / (k1 || 1e-9); return [cl(s(v)), cl(v)]; }
    const w = Math.sqrt(Math.max(0, k1 * k1 - 4 * k0 * k2)), v1 = (-k1 - w) / (2 * k2), u1 = s(v1), v2 = (-k1 + w) / (2 * k2);
    return u1 >= -.01 && u1 <= 1.01 && v1 >= -.01 && v1 <= 1.01 ? [cl(u1), cl(v1)] : [cl(s(v2)), cl(v2)];
  }
  // the block in the cell whose top is z, on g: at(x, y, z) -> its place there, u: an art px there. Every face of it the eye sees (turned to it on the screen, no block beside it): its top, its front,
  // a side (not its top and front alone: a block put by a block's side, off to a side of the screen, would have no side)
  function block(g, at, u, x, y, z, item, a, red, behind) {
    const px = paintOf(item); if (!px) return false;
    // a face, px by px: an art px is the face's when its middle is in it (the land's own rule, and the box's: target.js pxOf); its paint where that px is on it
    const face = (q, W, rows, row0) => { const ys = q.map((p) => p[1]);
      for (let J = Math.ceil(Math.min(...ys) / u - .5); (J + .5) * u < Math.max(...ys); J++) { const Y = J * u, yc = Y + u / 2; let l = 1e9, r = -1e9;
        for (let n = 0; n < 4; n++) { const A = q[n], B = q[(n + 1) % 4]; if ((A[1] <= yc) === (B[1] <= yc)) continue; const xi = A[0] + (B[0] - A[0]) * (yc - A[1]) / (B[1] - A[1]); l = Math.min(l, xi); r = Math.max(r, xi); }
        if (!(r > l)) continue;
        const [s0, t0] = onFace([(l + r) / 2, yc], ...q), hid = !!behind && behind(...[0, 1, 2].map((i) => W[0][i] + (W[1][i] - W[0][i]) * s0 + (W[3][i] - W[0][i]) * t0));
        g.globalAlpha = hid ? a * .6 : a;
        for (let I = Math.ceil(l / u - .5); (I + .5) * u < r; I++) { const X = I * u; if (hid && ((I >> 1) + (J >> 1)) % 2) continue; const [S, T] = onFace([X + u / 2, yc], ...q), v = px[(row0 + Math.floor(T * rows)) * 16 + Math.floor(S * 16)], c3 = [v & 255, (v >> 8) & 255, (v >> 16) & 255].map((w, i) => (red ? (w + RED[i]) >> 1 : w));
          g.fillStyle = `rgb(${c3.join()})`; g.fillRect(X, Y, u, u); } } };
    for (const [f, C, [nx, ny, nz]] of FACES) {
      const W = C.map(([i, j, k]) => [x + i, y + j, z - 1 + k]), q = W.map((w) => at(...w));
      if (q.some((v) => !v)) { if (f === "T") return false; continue; }
      let A = 0; for (let n = 0; n < 4; n++) A += q[n][0] * q[(n + 1) % 4][1] - q[(n + 1) % 4][0] * q[n][1];
      if (A > u * u * .1 && !solidAt(x + nx, y + ny, z + nz)) face(q, W, f === "T" ? 16 : RELIEF_STEP, f === "T" ? 0 : 16);
    }
    g.globalAlpha = 1;
    return true;
  }
  const api = {cell, paintOf, block, drew: null};
  // once a frame, with the cursor's keys. api.drew: what is drawn of the cursor (tests): {x, y, z, ok} the ghost, take: X's cell
  api.paint = () => {
    api.drew = null;
    const p = Build.on && meObs ? Build.S.at : null, art = HdLook.on ? HdLook.art() : null, at = p && art && art.at, a0 = at && at(p.x, p.y, Build.level()), a1 = a0 && at(p.x + 1, p.y, Build.level());
    if (!a1 || a1[0] === a0[0]) return;
    const u = art ? art.u : zoom, bh = art && art.behind, t = performance.now() / 1000, land = (j) => !j.take && j.up && LAND_BLOCKS.has(j.item);
    for (const j of [...Build.S.plans.values()].filter(land).sort((a, b) => a.y - b.y || a.z - b.z)) block(ctx, at, u, j.x, j.y, j.z, j.item, j.state === "doing" ? .75 : .5, j.state === "bad", bh);
    const it = Build.hint(p), hit = Build.taking(p), q = it.at || p; api.drew = {};      // (q: the cell beside the face the mouse is on, build.js)
    if (hit && !hit.plan && !hit.shut) api.drew.take = [p.x, p.y, hit.dig || hit.up ? hit.z : hit.z + 1];   // (its box: target.js)
    if (LAND_BLOCKS.has(it.ghost) && it.z !== undefined && !it.far && block(ctx, at, u, q.x, q.y, it.z, it.ghost, .6, it.ok === false, bh)) Object.assign(api.drew, {x: q.x, y: q.y, z: it.z, ok: it.ok !== false, at: at(q.x + .5, q.y + .5, it.z), u, hid: !!bh && bh(q.x + .5, q.y + .5, it.z)});   // (far: nothing holds it yet: its dotted box alone, target.js)
  };
  return api;
})();
