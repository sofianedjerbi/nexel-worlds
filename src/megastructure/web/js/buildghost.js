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
// behind a wall keeps one px in two there, fainter (it was drawn through the wall, as if in front of it).
const BuildGhost = (() => {
  const paints = new Map(), RED = [232, 85, 74], MOST = 9;
  // the next free cell from z up, over the blocks planned on that tile
  const cell = (p, z, planned) => { let n = z; while (n - z < MOST && planned(p.x, p.y, n)) n++; return n; };
  // a block's own paint, 16 x (16 + a level) art px: its top, then its front
  function paintOf(item) {
    if (paints.has(item)) return paints.get(item);
    let px = null;
    try {
      const stone = item === "stone_block", lv = stone ? 5 : 1, d = sheetData(stone ? hillSheet(lv) : dugSheet("soil", 0)), [bx, by] = blobCell(255), ox = stone ? bx * 16 : 0, oy = stone ? by * 16 : 80;
      px = new Uint32Array(16 * (16 + RELIEF_STEP));
      for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) px[j * 16 + i] = d.px[(oy + j) * d.w + ox + i];
      VoxPaint.front(lv, 0, px, 256, 16, 1);
    } catch (e) { px = null; }
    paints.set(item, px); return px;
  }
  const quads = (at, x, y, z0, z1) => { const T = [at(x, y, z1), at(x + 1, y, z1), at(x + 1, y + 1, z1), at(x, y + 1, z1)], B = [at(x, y + 1, z0), at(x + 1, y + 1, z0)]; return [...T, ...B].every((v) => v) ? {T, F: [T[3], T[2], B[1], B[0]]} : null; };
  // the block in the cell whose top is z, on g: at(x, y, z) -> its place there, u: an art px there
  function block(g, at, u, x, y, z, item, a, red, behind) {
    const px = paintOf(item), q = px && quads(at, x, y, z - 1, z); if (!q) return false;
    // a face, px by px: an art px is the face's when its middle is in it (the land's own rule, and the box's: target.js pxOf); a px of it lay outside the block
    const face = (c, rows, row0) => { const ys = c.map((p) => p[1]), top = (c[0][1] + c[1][1]) / 2, bot = (c[2][1] + c[3][1]) / 2;
      for (let J = Math.ceil(Math.min(...ys) / u - .5); (J + .5) * u < Math.max(...ys); J++) { const Y = J * u, yc = Y + u / 2; let l = 1e9, r = -1e9;
        for (let n = 0; n < 4; n++) { const A = c[n], B = c[(n + 1) % 4]; if ((A[1] <= yc) === (B[1] <= yc)) continue; const xi = A[0] + (B[0] - A[0]) * (yc - A[1]) / (B[1] - A[1]); l = Math.min(l, xi); r = Math.max(r, xi); }
        if (!(r > l)) continue;
        const k = Math.max(0, Math.min(.999, (yc - top) / (bot - top))), hid = !!behind && (row0 ? behind(x + .5, y + .999, z - k) : behind(x + .5, y + k, z)), j = row0 + Math.floor(k * rows);
        g.globalAlpha = hid ? a * .6 : a;
        for (let I = Math.ceil(l / u - .5); (I + .5) * u < r; I++) { const X = I * u; if (hid && ((I >> 1) + (J >> 1)) % 2) continue; const v = px[j * 16 + Math.max(0, Math.min(15, Math.floor((X + u / 2 - l) / (r - l) * 16)))], c3 = [v & 255, (v >> 8) & 255, (v >> 16) & 255].map((w, i) => (red ? (w + RED[i]) >> 1 : w));
          g.fillStyle = `rgb(${c3.join()})`; g.fillRect(X, Y, u, u); } } };
    face(q.T, 16, 0); face(q.F, RELIEF_STEP, 16); g.globalAlpha = 1;
    return true;
  }
  const api = {cell, paintOf, block, drew: null};
  // once a frame, with the cursor's keys. api.drew: what was drawn of the cursor (tests): {x, y, z, ok} the ghost, take: X's cell
  api.paint = () => {
    api.drew = null;
    const p = Build.on && meObs ? Build.S.at : null, art = HdLook.on ? HdLook.art() : null, at = p && art && art.at, a0 = at && at(p.x, p.y, Build.level()), a1 = a0 && at(p.x + 1, p.y, Build.level());
    if (!a1 || a1[0] === a0[0]) return;
    const u = art ? art.u : zoom, bh = art && art.behind, t = performance.now() / 1000, land = (j) => !j.take && j.up && LAND_BLOCKS.has(j.item);
    for (const j of [...Build.S.plans.values()].filter(land).sort((a, b) => a.y - b.y || a.z - b.z)) block(ctx, at, u, j.x, j.y, j.z, j.item, j.state === "doing" ? .75 : .5, j.state === "bad", bh);
    const it = Build.hint(p), hit = Build.taking(p); api.drew = {};
    if (hit && !hit.plan && !hit.shut) api.drew.take = [p.x, p.y, hit.dig || hit.up ? hit.z : hit.z + 1];   // (its box: target.js)
    if (LAND_BLOCKS.has(it.ghost) && it.z !== undefined && block(ctx, at, u, p.x, p.y, it.z, it.ghost, .6, it.ok === false, bh)) Object.assign(api.drew, {x: p.x, y: p.y, z: it.z, ok: it.ok !== false, at: at(p.x + .5, p.y + .5, it.z), u, hid: !!bh && bh(p.x + .5, p.y + .5, it.z)});
  };
  return api;
})();
