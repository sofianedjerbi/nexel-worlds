// Build mode, a block of the land in hand (earth, stone): WHERE it will go is a picture. The audit's newcomer could
// not build a wall two high: E lifted the cursor a storey and the screen answered in red letters "Nothing holds it:
// put it against a block" ("show, don't tell": a 'why can't I?' is answered by the picture).
//   - the ghost: the block itself in the cell Space will fill, in its own paint (its top as the land paints a block
//     put down: bare soil, the stone sheet; its front by the land's wall painter, voxpaint.js `front`), whole art px,
//     at 60 %; red where it cannot go (nothing beside it, somebody in it, something there);
//   - every block planned: the same, fainter: two planned on a tile are two blocks, one on the other;
//   - what X will take: its cell in orange dashes (a block of the ground, a built block; what stands: its tile, two high).
// Stacking needs no height key: on a tile that has your block the cursor rides it (build.js `ride`), and on one you
// only planned the next goes on top of the plan (`cell`). E and Q move the ghost one level (build.js `stops`).
// Drawn with the cursor's keys (prompts.js `build`): in the HD look that is its marks pass, places by HdLook.screenOf;
// in the classic picture by build.js's own (`S.to`). An art px of the HD look: it hands it to wayshow.js's painter and to nobody else (`WayShow.u`: kept from there).
const BuildGhost = (() => {
  const paints = new Map(), RED = [232, 85, 74], INK = "#5b3f36", TAKE = "#ff9d3c", MOST = 9;
  // the next free cell from z up, over the blocks planned on that tile
  const cell = (p, z, planned) => { let n = z; while (n - z < MOST && planned(p.x, p.y, n)) n++; return n; };
  // a block's own paint, 16 x 24 art px: its top, then its front
  function paintOf(item) {
    if (paints.has(item)) return paints.get(item);
    let px = null;
    try {
      const stone = item === "stone_block", lv = stone ? 5 : 1, d = sheetData(stone ? hillSheet(lv) : dugSheet("soil", 0)), [bx, by] = blobCell(255), ox = stone ? bx * 16 : 0, oy = stone ? by * 16 : 80;
      px = new Uint32Array(16 * 24);
      for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) px[j * 16 + i] = d.px[(oy + j) * d.w + ox + i];
      VoxPaint.front(lv, 0, px, 256, 16);
    } catch (e) { px = null; }
    paints.set(item, px); return px;
  }
  const quads = (at, x, y, z0, z1) => { const T = [at(x, y, z1), at(x + 1, y, z1), at(x + 1, y + 1, z1), at(x, y + 1, z1)], B = [at(x, y + 1, z0), at(x + 1, y + 1, z0)]; return [...T, ...B].every((v) => v) ? {T, F: [T[3], T[2], B[1], B[0]]} : null; };
  // the block in the cell whose top is z, on g: at(x, y, z) -> its place there, u: an art px there
  function block(g, at, u, x, y, z, item, a, red) {
    const px = paintOf(item), q = px && quads(at, x, y, z - 1, z); if (!q) return false;
    const R = (v) => Math.round(v / u) * u;
    const face = (c, rows, row0) => { const y0 = R(c[0][1]), y1 = R(c[3][1]);
      for (let Y = y0; Y < y1; Y += u) { const k = (Y - y0) / (y1 - y0), l = R(c[0][0] + (c[3][0] - c[0][0]) * k), r = R(c[1][0] + (c[2][0] - c[1][0]) * k), j = row0 + Math.min(rows - 1, Math.floor(k * rows));
        for (let X = l; X < r; X += u) { const v = px[j * 16 + Math.min(15, Math.floor((X - l) / (r - l) * 16))], c3 = [v & 255, (v >> 8) & 255, (v >> 16) & 255].map((w, i) => (red ? (w + RED[i]) >> 1 : w));
          g.fillStyle = `rgb(${c3.join()})`; g.fillRect(X, Y, u, u); } } };
    g.globalAlpha = a; face(q.T, 16, 0); face(q.F, 8, 16); g.globalAlpha = 1;
    return true;
  }
  // what X will take: the edges of its cell, two px on, two off
  function outline(g, at, u, x, y, z0, z1, t) {
    const q = quads(at, x, y, z0, z1); if (!q) return;
    const R = (v) => Math.round(v / u) * u, ph = Math.floor(t * 6), T = q.T, F = q.F;
    for (const [a, b] of [[T[0], T[1]], [T[1], T[2]], [T[3], T[2]], [T[0], T[3]], [F[0], F[3]], [F[1], F[2]], [F[3], F[2]]]) {
      const n = Math.max(1, Math.round(Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) / u));
      for (let i = 0; i <= n; i++) { g.fillStyle = (i + ph) % 4 < 2 ? TAKE : INK; g.fillRect(R(a[0] + (b[0] - a[0]) * i / n), R(a[1] + (b[1] - a[1]) * i / n), u, u); }
    }
  }
  const api = {cell, paintOf, drew: null};
  // once a frame, with the cursor's keys. api.drew: what was drawn of the cursor (tests): {x, y, z, ok} the ghost, take: X's cell
  api.paint = () => {
    api.drew = null;
    const p = Build.on && meObs ? Build.S.at : null, at = p && (HdLook.on ? HdLook.screenOf : Build.S.to), a0 = at && at(p.x, p.y, Build.level()), a1 = a0 && at(p.x + 1, p.y, Build.level());
    if (!a1 || a1[0] === a0[0]) return;
    const u = HdLook.on ? WayShow.u || Math.max(1, Math.round(Math.abs(a1[0] - a0[0]) / 16)) : zoom, t = performance.now() / 1000, land = (j) => !j.take && j.up && LAND_BLOCKS.has(j.item);
    for (const j of [...Build.S.plans.values()].filter(land).sort((a, b) => a.y - b.y || a.z - b.z)) block(ctx, at, u, j.x, j.y, j.z, j.item, j.state === "doing" ? .75 : .5, j.state === "bad");
    const it = Build.hint(p), hit = Build.taking(p); api.drew = {};
    if (hit && !hit.plan && !hit.shut) { const tall = hit.dig || hit.up ? [hit.z - 1, hit.z] : [hit.z, hit.z + 2]; outline(ctx, at, u, p.x, p.y, tall[0], tall[1], t); api.drew.take = [p.x, p.y, tall[1]]; }
    if (LAND_BLOCKS.has(it.ghost) && it.z !== undefined && block(ctx, at, u, p.x, p.y, it.z, it.ghost, .6, it.ok === false)) Object.assign(api.drew, {x: p.x, y: p.y, z: it.z, ok: it.ok !== false, at: at(p.x + .5, p.y + .5, it.z), u});
  };
  return api;
})();
