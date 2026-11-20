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
    column: (x, y) => (blockOf(x, y) ? WaterBed.column(x, y) : null),      // (clear water, waterbed.js: a water tile's is its bed)
    waterTop: (x, y) => topAt(x, y),                            // (a hole that filled, a pool up on a hill: its face at its own height)
    water: (x, y) => { const g = gndAt(x, y) || "."; return wet(g) || g === ":"; },      // (under a bridge too: its deck is a model over it)
    models: Models.at, modelSheet: Models.sheet,                 // (models.js: what stands in the land as boxes)
    // (maskOf.plain: as if land as high lay all round it, so it has no rim and no cut corner; peek: the height
    // it is drawn at, cells.js. Then its lip, where the land beside it is lower: voxpaint.js. Water: what floats)
    paintTop(x, y, z, px, at, stride) {
      const g0 = gndAt(x, y) || ".", sea = wet(g0) || g0 === ":"; if (sea && WaterBed.on && z < topAt(x, y)) return WaterBed.paintBed(x, y, z, px, at, stride);
      const was = peek; maskOf.plain = true; peek = one; one.set(x + "," + y, sea ? 0 : VoxPaint.level(x, y, z));      // (what floats on water: painted as at level 0, whatever its own)
      try { drawTile0(x, y, {px, o: at, w: stride}); } finally { maskOf.plain = false; peek = was; one.clear(); }
      if (!wet(gndAt(x, y) || ".")) VoxPaint.rim(x, y, z, px, at, stride);
    },
    rock: VoxPaint.rocky,                                       // (is a tile's block stone, where its top is high enough: a mass of it, voxpaint.js)
    paintFront: VoxPaint.front, shape: VoxPaint.shape, profile: VoxPaint.profile, crown: VoxPaint.crown, lip: VoxPaint.lip, side: VoxPaint.side,
  };
  // (the look of the sides, all the host's: under: a cave's mouth is dark; tuck, inset: the hill sheets' cells leave
  // up to 6 px empty at a corner, 2 along a side; side: a wall that faces west or east shows 2 px of its side,
  // in those px: a dark line and a px of wall)
  const engine = Vox.create(host, {size: B, cell: P, up: RELIEF_STEP, levels: [-9, 12], variants: 4, under: [.16, .12, .15, .9], sea: [.42, .7, .84], tuck: 6, inset: 2, side: 2, dug: 0, gorge: 4, rock: {from: 5, lo: -512, n: 4}, water: WaterBed.cfg});      // (rock: a block whose top is stone, level 5 or over, is stone all the way down, under the ground too: voxpaint.js)
  const made = (b) => (HdLook.live ? !!b.px : engine.made(b.bx, b.by)) && !!b.water;      // a block of tiles is ready to be shown: its faces, and its sea (water.js) (the HD look, hd.js, makes its own land: this engine makes none meanwhile: no faces, no pages sent)
  // (the one place the land's px change: a tile drawn again is a tile the engine paints again)
  const drawTile0 = drawTile, FAR = [[-3, -3], [0, -3], [3, -3], [-3, 0], [3, 0], [-3, 3], [0, 3], [3, 3]];
  drawTile = function (x, y, to = null) { drawTile0(x, y, to); if (!to) { engine.touch(x, y); if (topAt(x, y) > 3) for (const [dx, dy] of FAR) engine.touch(x + dx, y + dy); WaterBed.changed(x, y); } };      // (high land: is a block stone is told by the land up to five tiles off, voxpaint.js rocky: their paint too)
  const here = (list) => list.filter((b) => b.px).map((b) => ({cx: b.bx, cy: b.by}));
  // Blocks coming in or changed, within what is left of the frame's time for the land (render.js)
  // (and each one's sea, made again when its tiles changed: water.js says if there is anything to do)
  function work(coming, until) {
    if (dirtyTiles.length || !engine.ready()) return;
    WaterBed.flush(engine.touch);                               // (clear water: the beds round what changed)
    if (!HdLook.live) engine.work(here(coming), until);
    for (const b of coming) if (b.px && (HdLook.live || engine.made(b.bx, b.by)) && b.seaAt !== b.ver) { for (const _ of waterSteps(b)); b.seaAt = b.ver; if (performance.now() >= until) return; }
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
  // Each tile of the cut comes and goes on its own (fade: "x,y" -> {lv, a: how far it has come, to}): FADE seconds, the engine's checker of px of paint.
  // You walk, the keyhole follows: the tiles that join it come in, those that leave it close, none jumps. The third byte of a tile's px: how far it has
  // come (1 to 127; with all of the cut's own coming, xray.a), + 128: a floor of the hole you are in, lit evenly (no shadow of the sun, vox_engine.js noSun)
  // (...when it is you who moved. The land or what it is cut for changed where you stand, or the cut is only now coming, all of it, with xray.a: at once, as the land itself changes)
  const FADE = .12, fade = new Map(); let fadeAt = 0, cutN = 0, cutKey = "", cutFor = "";
  function cutMap() {
    const pic = xray.a > .01 && xray.pic && xray.pic.cut.size ? xray.pic : null, cur = cursorCut(), all = new Map(pic ? pic.cut : []);
    if (cur) for (const [k, lv] of cur.cut) if (!all.has(k) || all.get(k) > lv) all.set(k, lv);
    const now = performance.now(), dt = fade.size ? Math.max(0, Math.min(.1, (now - fadeAt) / 1000)) : 0; fadeAt = now;
    const key = (pic ? pic.key : "") + "|" + (cur ? cur.key : ""), p = pic ? pic.key.split(",") : [], what = pic ? p.slice(3, 5) + "|" + p.slice(7) : cutFor, once = what !== cutFor || !fade.size;
    let shape = !cutOf || key !== cutKey; cutKey = key; cutFor = what;
    if (once) for (const [k, f] of fade) if (!all.has(k)) f.a = 0;
    for (const [k, lv] of all) { let f = fade.get(k); if (!f) { fade.set(k, f = {lv, a: once ? 1 : 0}); shape = true; } else if (f.lv !== lv) { f.lv = lv; shape = true; } f.to = 1; if (cur && cur.cut.has(k)) f.a = 1; }      // (the cursor's is there at once)
    for (const [k, f] of fade) { if (!all.has(k)) f.to = 0; f.a = f.to ? Math.min(1, f.a + dt / FADE) : f.a - dt / FADE; if (!f.to && f.a <= 0) { fade.delete(k); shape = true; } }
    if (!fade.size) { cutOf = null; return null; }
    if (shape) {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const k of fade.keys()) { const [x, y] = k.split(",").map(Number); x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
      const w = x1 - x0 + 1, h = y1 - y0 + 1, px = new Uint8Array(w * h * 4);
      for (const [k, f] of fade) { const [x, y] = k.split(",").map(Number), i = ((y - y0) * w + x - x0) * 4, v = f.lv + 32768; px[i] = v & 255; px[i + 1] = v >> 8; px[i + 3] = 255; }
      cutOf = {x: x0, y: y0, w, h, px, ver: ++cutN, fades: 0, a: 1, earth: [.3, .21, .17]};      // (the colour where nothing at all is behind: there should be none)
    }
    for (const [k, f] of fade) { const [x, y] = k.split(",").map(Number), i = ((y - cutOf.y) * cutOf.w + x - cutOf.x) * 4, v = (pic && xrayLit(x, y) ? 128 : 0) + Math.max(1, Math.round(127 * Math.min(f.a, cur && cur.cut.has(k) ? 1 : xray.a))); if (cutOf.px[i + 2] !== v) { cutOf.px[i + 2] = v; cutOf.fades++; } }
    cutOf.fill = api.probe ? [1, 0, 1] : null;                // (probe: what the faces of the cut leave empty is counted, api.fillPx: none, tests)
    return cutOf;
  }
  function frame(vis, ox, oy, S, t, high, sun = null) {
    if (!engine.ready()) return;
    engine.forget((cx, cy) => blocks.has(bkey(cx, cy)));
    // the sea: water.js makes its picture as ever (on a canvas of its own, waterCv); it is not laid on the game's
    // canvas but handed to the engine, which paints the water's faces from it
    const keep = ctx; off = off || document.createElement("canvas").getContext("2d");
    const wlook = WaterBed.view(engine, t);                     // (clear water, waterbed.js)
    ctx = off; try { drawWater(vis.filter(made), ox, oy, t); } finally { ctx = keep; }
    const pic = engine.draw({w: W, h: H, pw: cv.width, ph: cv.height, ox, oy, tile: S, row: cam.y, chunks: HdLook.on ? [] : here(vis), light: [1, 1, 1],   // (the HD look draws the land itself where you play, hd.js: here only the sky; the first screen, a spectator: the land as ever)
     
      clear: high ? [.659, .847, .918] : [.169, .141, .125],      // (the sky, or the dark of what has not come: as render.js fills)
      // (the curved world, curve.js: the ground bends to a horizon, the sky over it; far under the land, state.js away: earth, no sky)
      marks: Marks.list, curve: Curve.c, sky: Curve.on && (away.a < 1 || high || away.sky) ? HdLook.sky(t) : null,   // (HdLook.sky: the game's sky, its horizon where the HD land's is)
      wlook, wmask: Sun.masks(), water: waterView ? {canvas: waterCv, x: ox + waterView.x * zoom, y: oy + waterView.y * zoom, scale: zoom} : null,
      // hidden (behind a hill, down a hole, under a roof: xray.js says how much, and which tiles are cut how low):
      // the land is cut open over the place you are in
      cut: HdLook.on ? null : cutMap(), sun});                                      // (sun: with a shader on, the sun on the land, sun.js)
    if (api.probe) { const gl = VoxGL.gl, w = gl.drawingBufferWidth, h = gl.drawingBufferHeight, px = new Uint8Array(w * h * 4); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
      let n = 0; for (let i = 0; i < px.length; i += 4) if (px[i] === 255 && !px[i + 1] && px[i + 2] === 255) n++; api.fillPx = n; }
    ctx.imageSmoothingEnabled = false; ctx.drawImage(pic, 0, 0, W, H); api.pic = pic;   // (pic: the HD look takes its sky from it, hd.js: nothing stands in it yet)
  }
  // The HD look (hd.js) draws the land itself: here nothing is drawn. What it still takes from here: the chunks no longer in view let go, and the water's picture
  // (water.js, on its own canvas), made ten times a second (it was every frame) -> api.wver goes up with each
  let wAt = 0;
  function still(vis, ox, oy, t) {
    if (!engine.ready()) return; engine.forget((cx, cy) => blocks.has(bkey(cx, cy)));
    const now = performance.now(); if (now - wAt < 100 && api.wver) return; wAt = now;
    const keep = ctx; off = off || document.createElement("canvas").getContext("2d");
    ctx = off; try { drawWater(vis.filter(made), ox, oy, t); } finally { ctx = keep; } api.wver++;
  }
  // Away from the land (state.js), going: what is behind the land, laid over it that much: the engine's own picture
  // with no land in it (its sky, or the dark of the earth): one sky, whatever the hour. -> was it done (the curved world on)
  function veil(ox, oy, S, t, a, sky) {
    if (!Curve.on || !engine.ready()) return false;
    const pic = engine.draw({w: W, h: H, pw: cv.width, ph: cv.height, ox, oy, tile: S, row: cam.y, chunks: [], light: [1, 1, 1], clear: [.169, .141, .125], water: null, cut: null, curve: Curve.c, sky: sky ? Curve.sky(t) : null});
    ctx.globalAlpha = a; ctx.drawImage(pic, 0, 0, W, H); ctx.globalAlpha = 1;
    return true;
  }
  const api = {made, work, frame, still, veil, engine, host, probe: false, fillPx: 0, wver: 0};      // (host: the underground view, underground.js)
  return api;
})();
