// The sun on the land (the second half of sun.js; the engine's side is vox_light.js). With the land's depth on (the settings' Picture page, on by default) or a shader, the frame hands
// the engine, before the land is drawn, where the sun is and a picture of the shadows of what stands: each lying flat
// on the level its foot is on, that level written in its px. The land takes each where it truly falls: on its own
// level, down a cliff, up a step, never over a wall. (They were laid flat over the finished picture.)
//   Sun.cast   render.js, before the land: what the engine is to know of the sun (voxels.js), null with neither
//   Sun.shade  render.js, after what stands is drawn: the land's shadow on what stands in it
// By a fire at night what stands near it is lit by the fire: its shadow lies away from the fire, longer the further
// it stands, in the same picture (its px say so: the land takes it on its own level, as dark as a fire's is).
// In a curved world (curve.js) the picture is of the FLAT view, north over the screen's top as far as the roll shows:
// the land rolls the shadows away with itself. What is going down behind the roll throws the shadow of what is still
// seen of it, from its ground line; what is gone throws none.
// What is built (a floor's or a roof's block, a wall) throws the shadow of the box it is: `box`.
// The clouds' shadows are the land's own (vox_light.js: at its height, in the world, so a rolled view needs nothing);
// what stands is as dark as the land at its foot: `shade`.
const SunLand = (() => {
  const K = Sun.kit, SHADE = Sun.SHADE, GLASS = Sun.GLASS;
  let fires = [], ground = null, sunNow = null, cloudLayer = null;
  const said = (e) => { if (!Sun.said) { Sun.said = true; console.warn("sun: " + e.message); } };
  function hour() {
    const phase = (((clock.phase || 0) % 1) + 1) % 1, day = phase < .75;
    const a = day ? phase / .75 : (phase - .75) / .25;                               // the sun's way across (at night: the moon's)
    const tint = lightAt(phase), dark = Math.min(1, (1 - (.3 * tint[0] + .59 * tint[1] + .11 * tint[2]) / 255) / .36);
    const much = opt("shadows") / 100, long = opt("shadowlen") / 100;                 // (the settings: how dark, how long)
    return {dark, much, long, alpha: Math.min(.9, (SHADE.alpha + (SHADE.night - SHADE.alpha) * dark) * much), kx: (2 * a - 1) * SHADE.reach * long, ky: SHADE.fall * long};
  }
  const fireBy = (fx, fy, S) => { let best = null, d = SHADE.fire * S; for (const f of fires) { const q = Math.hypot(fx - f[0], fy - f[1]); if (q < d) { d = q; best = f; } } return best && [best, d / S]; };
  function cast(list, vis, sx, sy0, S, t, now) {
    const sy = sy0.bent ? Curve.sy(sy0.base, S, true) : sy0, north = sy0.bent ? Math.ceil(Curve.over() / zoom) * zoom : 0;
    fires = []; sunNow = null;
    // (the land's depth, the settings' Picture page: the sun's shadows and the land's own shade, with no shader too.
    // A shader adds the clouds, what is seen in the water, its glow and colours: shader.js, Sun.draw)
    const on = !!SHADERS[opt("shader")] && opt("shaderk") > 0, depth = !!opt("depth");
    if (!on && !depth) return null;
    try {
      const {dark, much, long, alpha, kx, ky} = hour(), land = !!opt("landshade");
      if (dark > .35 && opt("shadows")) {                       // (the fires, on the flat picture)
        for (const f of fireAt) fires.push([sx(f.x) + S / 2, sy(f.y, f.x) + S * .8]);
        for (const b of vis) for (const [i, c] of b.objs) if (c === "^" || c === "x") { const x = b.bx * B + i % B, y = b.by * B + (i / B | 0); fires.push([sx(x) + S / 2, sy(y, x) + S * .8]); }
      }
      let pic = null, at = null, lo = 1e4, hi = -1e4;
      if (opt("shadows")) {
        // (the picture is small: a px of it an art px of the land, on the land's own grid, as the night's lights are.
        // A shadow is whole px of the land, still on it as you walk, and little is handed to the GPU each frame)
        const z = zoom, x0 = ((sx(0) % z) + z) % z - z, y0 = ((sy(0) % z) + z) % z - z - north, gw = Math.ceil((W - x0) / z), gh = Math.ceil((H - y0) / z), by = new Map();
        if (!ground) ground = [0, 1].map(() => document.createElement("canvas").getContext("2d", {willReadFrequently: true}));      // (kept in memory: handed to the GPU each frame as it is, nothing waited for)
        for (const g of ground) { if (g.canvas.width !== gw || g.canvas.height !== gh) { g.canvas.width = gw; g.canvas.height = gh; } g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false; }
        const [one, all] = ground; let n = 0, kept = false;
        one.imageSmoothingEnabled = true;                      // (drawn small: a thin thing, a stalk, is a faint line, not dashes; the land takes what is a quarter there)
        for (const o of list) if (o.p || o.x !== undefined) { const lv = K.levelOf(o); if (!by.has(lv)) by.set(lv, []); by.get(lv).push(o); }
        K.measure(list, sx, sy0, S, t, now);                   // (a kind of body not yet measured is measured on the layer, where it is seen)
        // the sun's: laid over on the ground from its foot; what of it is in the land's shadow throws none; none by a fire
        // (going down behind the roll, curve.js: only what of it is still over its ground throws a shadow, from its ground line)
        const sunk = sy0.bent ? (o) => sy0.lost(K.rowOf(o)) : () => 0;
        const lay = (qx, qy, fy, l, up) => { const m = [1, 0, -qx, -qy, qx * (fy - l), fy + qy * (fy - l)]; if (l > 0 || up >= 2) m.cut = fy - l - (up >= 2 ? Math.round(up) * zoom : 0); return m; };
        const sun = (fx, fy, o) => (fires.length && fireBy(fx, fy, S) ? null : o.slab || o.wall ? box(o, sx, sy, kx, ky, land) : lay(kx, ky, fy, sunk(o), land ? upOf(o, kx, ky) : 0));
        const fire = (fx, fy, o) => {
          const near = fireBy(fx, fy, S); if (!near || near[1] < .45) return null;     // (not the fire's own)
          const [f, d] = near, len = Math.min(2.4, .7 + d * .32) * long, qx = (fx - f[0]) / (d * S) * len, up = (fy - f[1]) / (d * S) * len * .7;
          const qy = Math.abs(up) < .28 ? (up < -.05 ? -.28 : .28) : up;                // (level with the fire: still a shape on the ground, not a line)
          return o.slab || o.wall ? box(o, sx, sy, qx, qy, false) : lay(qx, qy, fy, sunk(o), 0);
        };
        for (const [lv, some] of by) for (const [via, blue] of [[sun, 255], [fire, 96]].filter((v, i) => (i ? fires.length : alpha > 0))) {      // (at night: the fires' only, the moon throws none)
          if (n && !kept) { all.clearRect(0, 0, gw, gh); all.drawImage(one.canvas, 0, 0); kept = true; }      // (more than one: each made on `one`, gathered on `all`)
          one.setTransform(1, 0, 0, 1, 0, 0); one.globalCompositeOperation = "source-over"; one.clearRect(0, 0, gw, gh); one.setTransform(1 / z, 0, 0, 1 / z, -x0 / z, -y0 / z);
          if (!K.cast(some, sx, sy, S, t, now, via, one, north)) continue;
          // (its level: + 32768, four bits in red's high four, the next four in green's; blue: the sun's, or a fire's)
          one.setTransform(1, 0, 0, 1, 0, 0); one.globalCompositeOperation = "source-in"; one.fillStyle = `rgb(${((lv + 32768) & 15) * 16 + 8},${((lv + 32768) >> 4 & 15) * 16 + 8},${blue})`; one.fillRect(0, 0, gw, gh);
          if (kept) all.drawImage(one.canvas, 0, 0);
          n++; lo = Math.min(lo, lv); hi = Math.max(hi, lv);
        }
        if (n) { pic = (kept ? all : one).canvas; at = {x: x0, y: y0, scale: z}; }
      }
      const c = SHADE.color, glass = on ? Math.min(.95, GLASS.alpha * opt("reflect") / 100) : 0, clouds = Shader.clouds();
      return sunNow = {dir: [kx, ky], alpha: opt("shadows") ? alpha : 0, shade: [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16) / 255), cast: pic, castAt: at, castLevels: [lo, hi], land, depth,
        fire: Math.min(.9, SHADE.byFire * dark * much),            // (how dark a fire's shadow is)
        cloud: clouds > 0 ? {k: clouds, drift: [-t * .011, t * .004]} : null,      // (the clouds' shadows: on the land at its height; on what stands: `shade`)
        glass: glass > 0 ? {alpha: glass, wave: GLASS.wave, ripple: GLASS.ripple, phase: (t * GLASS.speed) % (Math.PI * 2)} : null};
    } catch (e) { said(e); return null; }
  }
  // What stands in the land's shadow is in it as high as the shadow stands there: a tree at a cliff's foot is dark
  // to where the sun's line clears the cliff, and lit over it. -> px of art over level L at (x, y) (tiles) in shadow.
  // (As the land's own shadow is found, vox_light.js: tile by tile toward the sun; only a wall throws one, steps of one level do not.)
  function shadowUp(x, y, L, kx, ky) {
    const dx = -kx * RELIEF_STEP / P, dy = -ky * RELIEF_STEP / P, ix = 1 / Math.max(Math.abs(dx), 1e-6), iy = 1 / Math.max(Math.abs(dy), 1e-6);
    let tx = Math.floor(x), ty = Math.floor(y), up = 0, mx = (dx >= 0 ? tx + 1 - x : x - tx) * ix, my = (dy >= 0 ? ty + 1 - y : y - ty) * iy;
    for (let i = 0, was = L; i < 20; i++) {
      let t; if (mx < my) { t = mx; mx += ix; tx += Math.sign(dx); } else { t = my; my += iy; ty += Math.sign(dy); }
      if (!blockOf(tx, ty)) continue;
      const h = topAt(tx, ty); if (h - was > 1.5) up = Math.max(up, h - L - t);      // (a wall: two levels or more over the tile before it)
      was = h;
    }
    return up * RELIEF_STEP;
  }
  // What is built throws the shadow of what it is, not of its picture stood up: a block of a floor or a roof is a
  // slab at its height, a wall a thin box on its tile. Each one's outline on the ground: side by side they are one
  // shadow with one edge (each was its picture laid over from its own foot: a comb along a roof's side).
  function box(o, sx, sy, kx, ky, land) {
    const z = zoom, x = o.x, y = K.rowOf(o), wl = (dx, dy) => Structures.WALLS.includes(combAt(x + dx, y + dy) || "-");
    let a = [0, 0, 16, 16], h1 = 12 * z, h0 = 0;
    if (o.slab) { h1 = shOf(o.z) * z - liftAt(x, y); h0 = Math.max(0, h1 - RELIEF_STEP * z); if (o.slab === "roof") a = [-2, -2, 18, 18]; }
    else a = [wl(-1, 0) ? 0 : 5, wl(0, -1) ? 0 : 7, wl(1, 0) ? 16 : 11, wl(0, 1) ? 16 : 12];
    if (land && upOf(o, kx, ky) * z >= h1) return null;         // (all of it in the land's shadow: it throws none)
    const X0 = sx(x) + a[0] * z + kx * h0, Y0 = sy(y, x) + a[1] * z + ky * h0, X1 = X0 + (a[2] - a[0]) * z, Y1 = Y0 + (a[3] - a[1]) * z, vx = kx * (h1 - h0), vy = ky * (h1 - h0);
    return {poly: vx >= 0 ? [[X0, Y0], [X1, Y0], [X1 + vx, Y0 + vy], [X1 + vx, Y1 + vy], [X0 + vx, Y1 + vy], [X0, Y1]] : [[X0, Y0], [X1, Y0], [X1, Y1], [X1 + vx, Y1 + vy], [X0 + vx, Y1 + vy], [X0 + vx, Y0 + vy]]};
  }
  // (what is built is in the land's shadow as high as the shadow stands at each art px across it: a house half in a
  // cliff's shadow is cut by the shadow's own line, not a piece at a time)
  function colsOf(o, kx, ky) {
    upOf(o, kx, ky);                                           // (the kept ones are for this land and this sun)
    const k = o.x + "," + K.rowOf(o) + "c"; let c = ups.get(k);
    if (!c) { const L = K.levelOf(o); c = Array.from({length: 16}, (_, i) => shadowUp(o.x + (i + .5) / 16, K.rowOf(o) + .9, L, kx, ky)); ups.set(k, c); }
    return c;
  }
  // (a slab's top is a floor at one height: all in the shadow where the shadow stands that high, else lit; its front, and a wall, by height)
  const slabTops = (o, c, fy) => { const h = o.slab ? shOf(o.z) * zoom - liftAt(o.x, K.rowOf(o)) : 1e9; return c.map((u) => (u < 2 ? 1e5 : u * zoom >= h ? -1e5 : fy - Math.round(u) * zoom)); };
  const ups = new Map(); let upsOf = "";
  function upOf(o, kx, ky) {                                  // (kept for what stands on a tile, until the land or the sun moves on)
    const key = landVer + "|" + Math.round(kx * 50) + "|" + Math.round(ky * 50), k = o.p ? "" : o.x + "," + K.rowOf(o);
    if (key !== upsOf || ups.size > 4000) { upsOf = key; ups.clear(); }
    if (o.p && coveredAt(Math.round(o.p.x), Math.round(o.p.y), Floors.standOf(o.p, Math.round(o.p.x), Math.round(o.p.y)))) return 0;      // (under a roof: no sun to be out of)
    let up = o.p ? undefined : ups.get(k);
    if (up === undefined) { up = shadowUp((o.p ? o.p.x : o.x) + .5, K.rowOf(o) + .9, K.levelOf(o), kx, ky); if (!o.p) ups.set(k, up); }
    return up;
  }
  // Is a body's foot (bx, by, on the flat picture) in the shadow of what stands on its level near it? What is built: in
  // its shadow's outline (`box`); a thing: in its picture laid over, taken as a stem under a crown. By where they are:
  // nothing is read back from a picture (reading the shadows' own picture each frame cost three ms of the frame).
  function under(o, bx, by, list, sx, sy, S, kx, ky) {
    const lv = K.levelOf(o);
    for (const q of list) if (q !== o && !q.p && q.far === undefined && q.x !== undefined && Math.abs(q.x - o.p.x) < 5 && Math.abs(K.rowOf(q) - o.p.y) < 4 && (q.spr || q.wall || q.slab) && K.levelOf(q) === lv) {
      if (q.slab || q.wall) {
        const b = box(q, sx, sy, kx, ky, false), P_ = b ? b.poly : []; let in_ = false;
        for (let a = 0, c = P_.length - 1; a < P_.length; c = a++) if ((P_[a][1] > by) !== (P_[c][1] > by) && bx < (P_[c][0] - P_[a][0]) * (by - P_[a][1]) / (P_[c][1] - P_[a][1]) + P_[a][0]) in_ = !in_;
        if (in_) return true;
      } else if (q.spr[0].src) {
        const sp = q.spr, H = sp[4] * zoom, u = (by - (sy(K.rowOf(q), q.x) + S * .94)) / ky;      // (how high on it the px is that shades the foot)
        if (u >= 0 && u <= H && Math.abs(bx - (sx(q.x) + (sp[5] + sp[3] / 2) * zoom + kx * u)) <= (u < H * .35 ? 3 * zoom : sp[3] * zoom * .4)) return true;
      }
    }
    return false;
  }
  // (bodies, things, and what is built: walls, floors, roofs, what stands on them)
  function shade(list, sx, sy, S, t, now) {
    if (!sunNow) return;
    try {
      const [kx, ky] = sunNow.dir, dark = new Map(), near = [], lg = K.lg, stands = (o) => o.far === undefined && (o.p || ((o.spr || o.wall || o.row !== undefined) && o.x !== undefined));
      const cols = new Map(), flat = sy.bent ? Curve.sy(sy.base, S, true) : sy;
      if (sunNow.alpha) for (const o of list) if (stands(o)) {
        let up = sunNow.land ? upOf(o, kx, ky) : 0;
        if (o.p && up < 40 && under(o, sx(o.p.x) + S / 2, bodyY(o.p, flat) + 13 * zoom, list, sx, flat, S, kx, ky)) up = 40;      // (in the shadow of what stands: all of it, once)
        if (o.wall || o.row !== undefined) { const c = colsOf(o, kx, ky); up = Math.max(...c); if (up >= 2) cols.set(o, c); }
        if (up >= 2) { dark.set(o, up); near.push(o.p ? o.p.x : o.x, K.rowOf(o)); }
      }
      if (dark.size) {
        const by = (x, y) => { for (let i = 0; i < near.length; i += 2) if (Math.abs(near[i] - x) < 4 && y - near[i + 1] > -1 && y - near[i + 1] < 6) return true; return false; };
        K.ready();
        K.cast(list, sx, sy, S, t, now, (fx, fy, o) => (cols.has(o) ? {tops: slabTops(o, cols.get(o), fy), x0: sx(o.x)} : dark.has(o) ? {top: fy - Math.round(dark.get(o)) * zoom} : by(o.p ? o.p.x : o.x, K.rowOf(o)) ? {erase: true} : null));
        lg.globalCompositeOperation = "source-in"; lg.fillStyle = SHADE.color; lg.fillRect(0, 0, W, H);
        ctx.globalAlpha = sunNow.alpha; ctx.drawImage(K.layer, 0, 0, W, H); ctx.globalAlpha = 1;
      }
      // The clouds' shadows on what stands: each as dark as the land at its foot is (the land's own field, at its
      // height: vox_light.js), all of it alike; not what of it is in the land's shadow already; none under a roof.
      // All of them are drawn once on the layer, as they are; then each one's place is filled with its own shade, back
      // to front, only where something is drawn (a box round it: the field is smooth, what it takes of a neighbour is the neighbour's shade nearly)
      const tone = new Map();
      if (sunNow.cloud) for (const o of list) if (stands(o)) { const k = cloudOn(o, kx, ky); if (k > .004) tone.set(o, k); }
      if (!tone.size) return;
      // (on a picture of its own, a px of it a px of the page: what stands is drawn on whole px of the page, and a phone has nine px of its screen to each)
      const at = [], g = cloudLayer || (cloudLayer = document.createElement("canvas").getContext("2d")), w = Math.ceil(W), h = Math.ceil(H);
      if (g.canvas.width !== w || g.canvas.height !== h) { g.canvas.width = w; g.canvas.height = h; }
      g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false; g.clearRect(0, 0, w, h);
      K.cast(list, sx, sy, S, t, now, (fx, fy, o) => { at.push(o, fx, fy); return {plain: true}; }, g);
      g.globalCompositeOperation = "source-in"; g.fillStyle = "#fff"; g.fillRect(0, 0, w, h);
      g.globalCompositeOperation = "source-atop";
      for (let i = 0; i < at.length; i += 3) {
        const o = at[i], fx = at[i + 1], fy = at[i + 2], k = tone.get(o) || 0, sp = o.spr && o.spr[0].src ? o.spr : null;
        const up = o.z === undefined ? 0 : shOf(o.z) * zoom - liftAt(o.x, K.rowOf(o));
        const r = sp ? [sx(o.x) + sp[5] * zoom, sy(K.rowOf(o), o.x) + sp[6] * zoom, sp[3] * zoom, sp[4] * zoom] : o.wall ? [fx - S / 2, fy - 1.5 * S, S, 2 * S] : [fx - 1.5 * S, fy - 3 * S - up, 3 * S, 3.6 * S];
        const low = cols.has(o) ? Math.min(...slabTops(o, cols.get(o), fy)) : dark.has(o) ? fy - Math.round(dark.get(o)) * zoom : 1e9;
        g.fillStyle = `rgb(${255 - 66 * k},${255 - 56 * k},${255 - 26 * k})`; g.fillRect(r[0] - 1, r[1] - 1, r[2] + 2, Math.min(r[3] + 2, low - r[1] + 1));
      }
      ctx.globalCompositeOperation = "multiply"; ctx.drawImage(g.canvas, 0, 0, w, h); ctx.globalCompositeOperation = "source-over";
    } catch (e) { said(e); }
  }
  function cloudOn(o, kx, ky) {
    const x = o.p ? o.p.x : o.x, y = K.rowOf(o), z = Math.max(0, K.levelOf(o)) * RELIEF_STEP / P;
    if (o.p ? coveredAt(Math.round(x), Math.round(y), Floors.standOf(o.p, Math.round(x), Math.round(y))) : o.row === undefined && roofAt(Math.round(x), Math.round(y)) > 1) return 0;
    return VoxLight.cloud(sunNow.cloud, x + .5 - kx * z, y + .9 - ky * z, P);
  }
  // (for the tests: the shadows handed to the land this frame, as a picture the screen's size; in a curved world it is the flat one)
  const layerData = () => { if (!sunNow || !sunNow.cast) return []; const c = sunNow.cast, a = sunNow.castAt, lg = K.lg; K.ready(); lg.setTransform(1, 0, 0, 1, 0, 0); lg.imageSmoothingEnabled = false; lg.drawImage(c, a.x * DPR, a.y * DPR, c.width * a.scale * DPR, c.height * a.scale * DPR); return lg.getImageData(0, 0, K.layer.width, K.layer.height).data; };
  Object.assign(Sun, {cast, shade, layerData, given: () => sunNow});      // (given: what the engine was handed this frame, for the tests)
  return {hour};
})();
