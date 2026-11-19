// The land is blocks: the game's side of VOX, the engine in js/vox_*.js that draws a world
// of cells as blocks. Only this file knows both. It tells the engine what the world is (a tile's column: cells.js;
// is it water; the paint of a top: the game's own drawTile, asked for a plain tile of that ground at that height,
// and its lip; the paint of its sides: voxpaint.js, off the hill sheets), when a tile changed, and each frame where the world is on the screen:
// where it is for all that stands on the land (render.js sx, sy: a level RELIEF_STEP art px up), so bodies, things,
// aiming and shadows are where they were. The engine's picture is laid on the game's canvas where the land was
// painted, and the game draws the rest over it as ever.
const Voxels = (() => {
  const one = new Map();
  let off = null;
  const host = {
    column: (x, y) => (blockOf(x, y) ? colAt(x, y) : null),
    water: (x, y) => { const g = gndAt(x, y) || "."; return wet(g) || g === ":"; },      // (under a bridge too: its deck is a model over it)
    models: Models.at, modelSheet: Models.sheet,                 // (models.js: what stands in the land as boxes)
    // (maskOf.plain: as if land as high lay all round it, so it has no rim and no cut corner; peek: the height
    // it is drawn at, cells.js. Then its lip, where the land beside it is lower: voxpaint.js. Water: what floats)
    paintTop(x, y, z, px, at, stride) {
      const was = peek; maskOf.plain = true; peek = one; one.set(x + "," + y, z);
      try { drawTile0(x, y, {px, o: at, w: stride}); } finally { maskOf.plain = false; peek = was; one.clear(); }
      if (!wet(gndAt(x, y) || ".")) VoxPaint.rim(x, y, z, px, at, stride);
    },
    paintFront: VoxPaint.front, shape: VoxPaint.shape, profile: VoxPaint.profile, lip: VoxPaint.lip, side: VoxPaint.side, band: VoxPaint.band,
  };
  // (the look of the sides, all the host's: under: a cave's mouth is dark; tuck, inset: the hill sheets' cells leave
  // up to 6 px empty at a corner, 2 along a side; bands: a wall that faces west or east leans out a level at a time
  // (voxpaint.js: 2 px), 5 levels at the most)
  const engine = Vox.create(host, {size: B, cell: P, up: RELIEF_STEP, levels: [-9, 12], variants: 4, under: [.16, .12, .15, .9], sea: [.42, .7, .84], tuck: 6, inset: 2, bands: 5});
  const made = (b) => engine.made(b.bx, b.by) && !!b.water;      // a block of tiles is ready to be shown: its faces, and its sea (water.js)
  // (the one place the land's px change: a tile drawn again is a tile the engine paints again)
  const drawTile0 = drawTile;
  drawTile = function (x, y, to = null) { drawTile0(x, y, to); if (!to) engine.touch(x, y); };
  const here = (list) => list.filter((b) => b.px).map((b) => ({cx: b.bx, cy: b.by}));
  // Blocks coming in or changed, within what is left of the frame's time for the land (render.js)
  // (and each one's sea, made again when its tiles changed: water.js says if there is anything to do)
  function work(coming, until) {
    if (dirtyTiles.length || !engine.ready()) return;
    engine.work(here(coming), until);
    for (const b of coming) if (b.px && engine.made(b.bx, b.by) && b.seaAt !== b.ver) { for (const _ of waterSteps(b)); b.seaAt = b.ver; if (performance.now() >= until) return; }
  }
  // The cut as the engine takes it: a picture a tile a px, made again when what is cut changes. What is cut: the
  // place you are hidden in (xray.js: pic.cut), and the build cursor's own tile where the ground hides it (in a
  // hole, the ground in front of it; in the ground, the earth over it): that tile down to the cursor's level, and
  // what is in front of it in its column. (keyhole.js painted that tile cut open, on the land painted flat.)
  let cutOf = null;
  function cursorCut() {
    const p = Build.on && Build.S.at; if (!p) return null;
    const L = Build.level(), out = new Map();
    if (levelAt(p.x, p.y) > L) out.set(p.x + "," + p.y, L);
    for (let ty = p.y + 1; ty <= p.y + XRAY.far; ty++) if ((levelAt(p.x, ty) - L) * RELIEF_STEP - (ty - p.y - 1) * 16 > 0) out.set(p.x + "," + ty, L);
    return out.size ? {key: [p.x, p.y, L, landVer].join(), cut: out} : null;
  }
  function cutMap() {
    const pic = xray.a > .01 && xray.pic && xray.pic.cut.size ? xray.pic : null, cur = cursorCut();
    if (!pic && !cur) return null;
    const ver = (pic ? pic.key : "") + "|" + (cur ? cur.key : "");
    if (!cutOf || cutOf.ver !== ver) {
      const all = new Map(pic ? pic.cut : []);
      if (cur) for (const [k, lv] of cur.cut) if (!all.has(k) || all.get(k) > lv) all.set(k, lv);
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const k of all.keys()) { const [x, y] = k.split(",").map(Number); x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
      const w = x1 - x0 + 1, h = y1 - y0 + 1, px = new Uint8Array(w * h * 4);
      for (const [k, lv] of all) { const [x, y] = k.split(",").map(Number), i = ((y - y0) * w + x - x0) * 4, v = lv + 32768; px[i] = v & 255; px[i + 1] = v >> 8; px[i + 2] = 255; px[i + 3] = 255; }
      cutOf = {x: x0, y: y0, w, h, px, ver, earth: [.3, .21, .17], line: [.2, .14, .13]};      // (a block's sliced top, and the line along its edge at a drop)
    }
    cutOf.fill = api.probe ? [1, 0, 1] : null;                // (probe: what the faces of the cut leave empty is counted, api.fillPx: none, tests)
    cutOf.a = cur ? 1 : xray.a;                              // (the cursor's is there at once; the place's comes with how hidden you are)
    return cutOf;
  }
  function frame(vis, ox, oy, S, t, high, sun = null) {
    if (!engine.ready()) return;
    engine.forget((cx, cy) => blocks.has(bkey(cx, cy)));
    // the sea: water.js makes its picture as ever (on a canvas of its own, waterCv); it is not laid on the game's
    // canvas but handed to the engine, which paints the water's faces from it
    const keep = ctx; off = off || document.createElement("canvas").getContext("2d");
    ctx = off; try { drawWater(vis.filter(made), ox, oy, t); } finally { ctx = keep; }
    const pic = engine.draw({w: W, h: H, pw: cv.width, ph: cv.height, ox, oy, tile: S, row: cam.y, chunks: here(vis), light: [1, 1, 1],
      clear: high ? [.659, .847, .918] : [.169, .141, .125],      // (the sky, or the dark of what has not come: as render.js fills)
      // (the curved world, curve.js: the ground bends to a horizon, the sky over it; far under the land, state.js away: earth, no sky)
      marks: Marks.list, curve: Curve.c, sky: Curve.on && (away.a < 1 || high || away.sky) ? Curve.sky(t) : null,
      water: waterView ? {canvas: waterCv, x: ox + waterView.x * zoom, y: oy + waterView.y * zoom, scale: zoom} : null,
      // hidden (behind a hill, down a hole, under a roof: xray.js says how much, and which tiles are cut how low):
      // the land is cut open over the place you are in
      cut: cutMap(), sun});                                      // (sun: with a shader on, the sun on the land, sun.js)
    if (api.probe) { const gl = VoxGL.gl, w = gl.drawingBufferWidth, h = gl.drawingBufferHeight, px = new Uint8Array(w * h * 4); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
      let n = 0; for (let i = 0; i < px.length; i += 4) if (px[i] === 255 && !px[i + 1] && px[i + 2] === 255) n++; api.fillPx = n; }
    ctx.imageSmoothingEnabled = false; ctx.drawImage(pic, 0, 0, W, H);
  }
  // Away from the land (state.js), going: what is behind the land, laid over it that much: the engine's own picture
  // with no land in it (its sky, or the dark of the earth): one sky, whatever the hour. -> was it done (the curved world on)
  function veil(ox, oy, S, t, a, sky) {
    if (!Curve.on || !engine.ready()) return false;
    const pic = engine.draw({w: W, h: H, pw: cv.width, ph: cv.height, ox, oy, tile: S, row: cam.y, chunks: [], light: [1, 1, 1], clear: [.169, .141, .125], water: null, cut: null, curve: Curve.c, sky: sky ? Curve.sky(t) : null});
    ctx.globalAlpha = a; ctx.drawImage(pic, 0, 0, W, H); ctx.globalAlpha = 1;
    return true;
  }
  const api = {made, work, frame, veil, engine, probe: false, fillPx: 0};
  return api;
})();
