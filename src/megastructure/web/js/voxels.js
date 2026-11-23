// The land is blocks: the game's side of the HD look's land (hd.js, vox_style.js). Its host says what the world is (a
// tile's column: cells.js; is it water; the paint of a top: the game's own drawTile, asked for a plain tile of that
// ground at that height, and its lip; the paint of its sides: voxpaint.js, off the hill sheets). Here too: when a block
// of the land is ready to be shown (made), its sea made a little a frame (work), and the water's picture (still).
const Voxels = (() => {
  const one = new Map();
  const host = {
    column: (x, y) => (blockOf(x, y) ? WaterBed.column(x, y) : null),      // (clear water, waterbed.js: a water tile's is its bed)
    waterTop: (x, y) => topAt(x, y),                            // (a hole that filled, a pool up on a hill: its face at its own height)
    water: (x, y) => { const g = gndAt(x, y) || "."; return wet(g) || g === ":"; },      // (under a bridge too: its deck is a model over it)
    flow: Flow.col,                                             // (water that runs, in the land's cells: flow.js)
    models: Models.at, modelSheet: Models.sheet,                 // (models.js: what stands in the land as boxes)
    // (maskOf.plain: as if land as high lay all round it, so it has no rim and no cut corner; peek: the height
    // it is drawn at, cells.js. Then its lip, where the land beside it is lower: voxpaint.js. Water: what floats)
    paintTop(x, y, z, px, at, stride) {
      const g0 = gndAt(x, y) || ".", sea = wet(g0) || g0 === ":"; if (sea && WaterBed.on && z < topAt(x, y)) return WaterBed.paintBed(x, y, z, px, at, stride);
      const was = peek; maskOf.plain = true; peek = one; one.set(x + "," + y, sea ? 0 : VoxPaint.level(x, y, z));      // (what floats on water: painted as at level 0, whatever its own)
      try { drawTile0(x, y, {px, o: at, w: stride}); } finally { maskOf.plain = false; peek = was; one.clear(); }
      if (!wet(gndAt(x, y) || ".")) VoxPaint.rim(x, y, z, px, at, stride);
    },
    built: (x, y) => matAt(x, y) === "s",                       // (a stone block put there: its sides laid courses; the land's own stone a cliff, voxpaint.js)
    rock: VoxPaint.rocky,                                      // (is a tile's block stone, where its top is high enough: a mass of it, voxpaint.js)
    paintFront: VoxPaint.front, shape: VoxPaint.shape, profile: VoxPaint.profile, crown: VoxPaint.crown, lip: VoxPaint.lip, side: VoxPaint.side,
  };
  // (engine: can the land be drawn at all: WebGL 2, hd.js; forget: clear water turned on or off, waterbed.js)
  const engine = {ready: () => !!VoxGL.start(), forget() {}, touch() {}};
  const made = (b) => !!b.px && !!b.water;      // a block of tiles is ready to be shown: come in (tiles.js arriveBlock), and its sea made (water.js)
  // (a tile drawn again: the clear water's beds round it are looked at again, waterbed.js)
  const drawTile0 = drawTile;
  drawTile = function (x, y, to = null) { drawTile0(x, y, to); if (!to) WaterBed.changed(x, y); };
  { const a0 = arriveBlock; arriveBlock = function (b) { a0(b); WaterBed.changed(b.bx * B, b.by * B); WaterBed.changed(b.bx * B + B - 1, b.by * B + B - 1); }; }   // (a block come in: its beds, one box)
  // Blocks coming in or changed, within what is left of the frame's time for the land (render.js): each one's sea, made
  // again when its tiles changed (water.js says if there is anything to do), and the clear water's beds round what changed
  function work(coming, until) {
    if (dirtyTiles.length || !engine.ready()) return;
    WaterBed.flush(engine.touch);
    for (const b of coming) if (b.px && b.seaAt !== b.ver) { for (const _ of waterSteps(b)); b.seaAt = b.ver; if (performance.now() >= until) return; }
  }
  // The water's picture (water.js, on its own canvas) the HD look lays on its water, made ten times a second -> api.wver goes up with each.
  // Over the land the HD look draws (hd.js box: tiles x0, y0, x1, y1), not the flat view's rectangle (vis: before the look's first frame)
  let wAt = 0;
  function still(vis, t) {
    if (!engine.ready()) return;
    const now = performance.now(); if (now - wAt < 100 && api.wver) return; wAt = now;
    const r = HdLook.box, [x0, y0, x1, y1] = r || [vis.map((b) => b.bx * B), vis.map((b) => b.by * B), vis.map((b) => b.bx * B + B - 1), vis.map((b) => b.by * B + B - 1)].map((l, i) => (i < 2 ? Math.min : Math.max)(...l));
    const near = [];
    if (r) { for (let by = Math.floor(y0 / B); by <= Math.floor(y1 / B); by++) for (let bx = Math.floor(x0 / B); bx <= Math.floor(x1 / B); bx++) { const b = blocks.get(bkey(bx, by)); if (b && made(b)) near.push(b); } }
    else near.push(...vis.filter(made));
    if (!near.length) { waterView = null; api.wver++; return; }
    drawWater(near, [x0 * 16, y0 * 16, (x1 - x0 + 1) * 16, (y1 - y0 + 1) * 16], t); api.wver++;
  }
  const api = {made, work, still, engine, host, wver: 0};      // (host: the HD look's, hd.js)
  return api;
})();
