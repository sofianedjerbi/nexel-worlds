// What a shader adds to the world itself (the settings' Shaders page; the picture's glow and colours are shader.js):
// "we want real shaders, reflection, not just color hue tweaks, shadows, like minecraft".
//   Shadows: every tree, wall, thing, animal and person throws its own shape on the ground, away from the sun: long
//     to the west in the morning, short at noon, long to the east in the evening, faint at night.
//   Reflections: what stands by the water is seen in it upside down, under its feet, rippling.
// Both are made from the very sprites the frame is about to draw (render.js calls Sun.draw with its sorted list, the
// ground already painted, nothing standing on it yet): each is drawn once more through a transform onto a layer the
// size of the screen (a shadow: laid over on the ground from its foot, then filled flat; a reflection: turned over
// about its foot, kept only where there is water), and the layer is put on the picture. `ctx` is pointed at the
// layer meanwhile, so whatever draws a body or a wall draws its shadow too, with no code of its own.

const Sun = (() => {
  const SHADE = {alpha: .3, night: .1, color: "#1d2440", reach: 1.5, fall: .45, fire: 6, byFire: .36};      // fire: tiles a fire lights; byFire: how dark a shadow it throws   // reach: a shadow's length sideways at sunrise, in heights; fall: towards you, always
  const GLASS = {alpha: .5, ripple: 1, wave: .9, speed: 2.2};                     // ripple: art px a row slides; wave: how tight; speed
  let layer = null, lg = null, casting = false;
  // Where a sprite stands: its lowest row that is not empty (most have empty rows under them), in art px from its top
  const feet = new Map();
  function footOf(img, a, b, w, h) {
    const key = img.src + "|" + a + "|" + b + "|" + w + "|" + h;
    if (!feet.has(key)) {
      let row = h;
      try {
        const c = document.createElement("canvas"); c.width = w; c.height = h;
        const g = c.getContext("2d"); g.drawImage(img, a, b, w, h, 0, 0, w, h);
        const d = g.getImageData(0, 0, w, h).data;
        while (row > 1 && !Array.from({length: w}, (_, x) => d[((row - 1) * w + x) * 4 + 3]).some((v) => v > 40)) row--;
      } catch (e) { /* not readable: its whole height */ }
      feet.set(key, row);
    }
    return feet.get(key);
  }
  function ready() {
    if (!layer) { layer = document.createElement("canvas"); lg = layer.getContext("2d"); }
    if (layer.width !== cv.width || layer.height !== cv.height) { layer.width = cv.width; layer.height = cv.height; }
    lg.setTransform(DPR, 0, 0, DPR, 0, 0); lg.globalAlpha = 1; lg.globalCompositeOperation = "source-over"; lg.imageSmoothingEnabled = false;
    lg.clearRect(0, 0, W, H);
  }
  // Where a body's feet are on the screen. A person: the sheet's own measure (characters.js draws the frame 18 art px
  // over the body's place, its feet at row 32 of it), less a jump or a climb. An animal: each kind's sheet is its own,
  // so one of the kind is drawn once on the layer and its lowest painted row is found.
  const stands = new Map();
  let clean = false;                                // the layer is empty: a kind may be measured on it
  function standsAtY(p, sx, sy, S, t, now) {
    const y = bodyY(p, sy), kind = p.e.kind;
    if (kind === "agent") return y + 13 * zoom + overBody(p, S)[1];      // (a pixel in under the feet: the shadow starts under them, not after them)
    if (!stands.has(kind + zoom)) {
      let foot = 14 * zoom;
      if (!clean) return y + foot;
      try {
        lg.save(); lg.setTransform(DPR, 0, 0, DPR, 0, 0); lg.clearRect(0, 0, W, H);
        drawEntity({...p}, sx, sy, S, t, now);
        lg.restore();
        const x0 = Math.max(0, Math.round((sx(p.x) - S) * DPR)), y0 = Math.max(0, Math.round((y - 2 * S) * DPR)), w = Math.round(3 * S * DPR), h = Math.round(4 * S * DPR);
        const rg = Object.assign(document.createElement("canvas"), {width: w, height: h}).getContext("2d", {willReadFrequently: true}); rg.drawImage(layer, x0, y0, w, h, 0, 0, w, h); const d = rg.getImageData(0, 0, w, h).data;      // (a small copy made to be read: the layer is the GPU's)
        let row = h - 1;
        const painted = (r) => { for (let i = 0; i < w; i++) if (d[(r * w + i) * 4 + 3] > 60) return true; return false; };
        while (row > 0 && !painted(row)) row--;
        if (row > 0) foot = (y0 + row + 1) / DPR - y;
        lg.clearRect(0, 0, W, H);
      } catch (e) { /* not readable: a person's measure */ }
      if (jumping(p, now) || Climb.climbOf(p)) return y + foot;      // (in the air: not the one to measure a kind by)
      stands.set(kind + zoom, foot);
    }
    return y + stands.get(kind + zoom);
  }
  // Each thing of the list drawn through the transform `via(footX, footY)` gives, with ctx on the layer
  // (into: another canvas's context to draw them on, as it is set, instead of the layer)
  function cast(list, sx, sy, S, t, now, via, into = null, north = 0) {      // (north: px over the screen's top that count: the flat picture of a curved view)
    const main = ctx, lay = lg; let g = lg;
    // Drawing a body does more than paint it: it throws up dust and splashes, plays a step, notes where its swing is.
    // Drawn here a second and a third time, all of that came twice more ("particle shadow create weird patterns..
    // especially the one when sprinting in water"). So: a copy of the body is drawn (what it notes is thrown away),
    // what it throws up is taken back, it makes no sound (audio.js asks Sun.casting); and a body in the water has
    // no shadow and no reflection (its wake and its spray are drawn with it, and are not things that stand).
    const dust = parts.length, puff = puffs.length;
    let n = 0;
    ctx = lg; casting = true;
    try {
      clean = true;
      for (const o of list) if (o.p) standsAtY(o.p, sx, sy, S, t, now);      // (each kind of body here, measured before anything is on the layer)
      clean = false;
      if (into) { g = into; ctx = g; }
      for (const o of list) {
        const p = o.p, x = p ? p.x : o.x, y = p ? p.y : o.ty ?? o.y;
        if ((!o.spr && !p && !o.wall) || x === undefined || o.far !== undefined) continue;      // (past the horizon, curve.js: no shadow)
        if (p && DEPTH_OF[gndAt(Math.round(p.x), Math.round(p.y))]) continue;
        // (what the place you are seen in is seen through, xray.js: as faint as it is drawn, gone with it. "and their shadow should dispawn also")
        const over = p ? xrayOverBody(p) : o.spr ? xrayOver(o.x, o.ty) : 0;
        if (over > .98) continue;
        const fx = sx(x) + S / 2;
        const fy = p ? standsAtY(p, sx, sy, S, t, now) : o.spr && o.spr[0].src ? sy(y, x) + (o.spr[6] + footOf(...o.spr.slice(0, 5)) - 1) * zoom : sy(y, x) + S * .94;
        if (fx < -4 * S || fx > W + 4 * S || fy < -2 * S - north || fy > H + 6 * S) continue;
        const m = via(fx, fy, o);
        if (!m) continue;
        g.save();
        // (m: a transform; or, where it stands: {top: only what of it is under that row, erase: take it out of the layer}, cut where a hill hides it)
        if (m.length) { g.transform(...m); if (m.cut !== undefined || m.low !== undefined) { g.beginPath(); g.rect(-1e4, m.low ?? -1e4, 3e4, m.low === undefined ? m.cut + 1e4 : 2e4); g.clip(); } }      // (cut: only what of it is over that row throws a shadow)
        else if (m.erase) g.globalCompositeOperation = "destination-out"; else { g.beginPath(); g.rect(0, m.top - 2 * zoom, W, H); g.clip(); }
        const paint = (k) => {
          g.globalAlpha = (1 - over) * k;
          if (o.spr) { const [img, a, b, w, h, dx, dy] = o.spr; g.drawImage(img, a, b, w, h, Math.round(sx(x) + dx * zoom), Math.round(sy(y, x) + dy * zoom), w * zoom, h * zoom); }
          else if (p) drawEntity({...p}, sx, sy, S, t, now);
          else o.fx();
        };
        if (m.length || (!p && !tileBehind(x, y))) paint(1); else drawBehind(p || {x, y, e: {}}, sx, sy, S, paint);
        if (m.top !== undefined) {                            // (its last two rows: one px in two, on the land's grid: an edge, not a line)
          const pat = g.createPattern(checker("#000"), "repeat"); pat.setTransform(new DOMMatrix([zoom, 0, 0, zoom, sx(0), sy.base ?? sy(0)]));
          g.globalAlpha = 1; g.globalCompositeOperation = "destination-out"; g.fillStyle = pat; g.fillRect(fx - 3 * S, m.top - 2 * zoom, 6 * S, 2 * zoom);
        }
        g.restore(); n++;
      }
    } finally { clean = false; casting = false; parts.length = Math.min(parts.length, dust); puffs.length = Math.min(puffs.length, puff); ctx = main; lg = lay; lg.setTransform(DPR, 0, 0, DPR, 0, 0); lg.globalAlpha = 1; g.globalAlpha = 1; }
    return n;
  }
  function seenWater(vis, sx, sy, S) {
    if (!vis.some((b) => b.water && b.water.any)) return null;
    const [vx, vy, vw, vh] = viewRect(2), wet = new Path2D();
    let any = false, top = H, bottom = 0;
    // Water that is seen: higher ground to the south is drawn up the screen over what lies behind it ("player reflection
    // is visible even if player is standing on a mountain, because there's water under it"). A water tile shows down to
    // where the nearest land south of it begins on the screen: all of it by a shore, none of it behind a hill.
    for (let y = vy; y <= vy + vh; y++) for (let x = vx; x <= vx + vw; x++) if (DEPTH_OF[gndAt(x, y)]) {
      const up = liftAt(x, y), row = sy.row || ((r, l) => sy(r) - l), Y = row(y, up);         // (the tile itself, as tall as it is drawn: curve.js)
      let cut = row(y + 1, up);
      for (let k = 1; k <= 12 && cut > Y; k++) { const g = gndAt(x, y + k); if (g && !DEPTH_OF[g]) cut = Math.min(cut, row(y + k, liftAt(x, y + k))); }
      if (cut <= Y) continue;
      wet.rect(sx(x), Y, S, cut - Y); any = true; top = Math.min(top, Y); bottom = Math.max(bottom, cut);
    }
    return any ? {wet, top, bottom} : null;
  }
  // The seen water as a small picture, white where it is (a quarter of the screen's size): shader.js lays the sky, the
  // clouds and the sun's glitter on the water through it. What swims or floats in it is cut out: no glitter on a head.
  // Its own shape is cut, drawn small in black (it was a box round it: "patch is visible anywhere in the sea anytime",
  // a square of water with no sky on it round whoever swam).
  let maskCv = null, mask = null, cutCv = null;
  function waterMask(list, water, sx, sy, S, t, now) {
    mask = null;
    if (!water) return;
    if (!maskCv) { maskCv = document.createElement("canvas"); cutCv = document.createElement("canvas"); }
    const w = Math.ceil(W / 4), h = Math.ceil(H / 4), g = maskCv.getContext("2d"), c = cutCv.getContext("2d");
    for (const cvs of [maskCv, cutCv]) if (cvs.width !== w || cvs.height !== h) { cvs.width = w; cvs.height = h; }
    g.setTransform(1, 0, 0, 1, 0, 0); g.fillStyle = "#000"; g.fillRect(0, 0, w, h);
    g.setTransform(.25, 0, 0, .25, 0, 0); g.fillStyle = "#fff"; g.fill(water.wet);
    const swim = list.filter((o) => (o.p ? DEPTH_OF[gndAt(Math.round(o.p.x), Math.round(o.p.y))] : o.spr && DEPTH_OF[gndAt(o.x, o.ty)]));
    if (swim.length) {
      const main = ctx, dust = parts.length, puff = puffs.length;
      c.setTransform(1, 0, 0, 1, 0, 0); c.globalCompositeOperation = "source-over"; c.clearRect(0, 0, w, h); c.setTransform(.25, 0, 0, .25, 0, 0); c.imageSmoothingEnabled = false;
      ctx = c; casting = true;                               // (a copy of each, as a shadow is drawn: no dust, no sound of it)
      try {
        for (const o of swim) {
          if (o.spr) { const [img, a, b, sw, sh, dx, dy] = o.spr; c.drawImage(img, a, b, sw, sh, Math.round(sx(o.x) + dx * zoom), Math.round(sy(o.ty, o.x) + dy * zoom), sw * zoom, sh * zoom); }
          else drawEntity({...o.p}, sx, sy, S, t, now);
        }
      } finally { casting = false; parts.length = Math.min(parts.length, dust); puffs.length = Math.min(puffs.length, puff); ctx = main; }
      c.setTransform(1, 0, 0, 1, 0, 0); c.globalCompositeOperation = "source-in"; c.fillStyle = "#000"; c.fillRect(0, 0, w, h);
      g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(cutCv, 0, 0);
    }
    mask = maskCv;
  }
  function reflections(list, water, sx, sy, S, t, now) {
    const {wet, top, bottom} = water;
    ready();
    // turned over about where the water's level is under its foot: what stands on a cliff over the water is seen as far
    // under the shore as it is over it, under the cliff's own picture in the water (vox_light.js); on the shore: about its foot
    // (in a curved world a height is drawn squeezed with its row, curve.js: as far under as the land is drawn over the water there)
    // Only in the water it stands by: the first south of it in its column, to where that ends (far rows are close together: its picture went on into the next pond)
    cast(list, sx, sy, S, t, now, (fx, fy, o) => { const up = Math.max(0, levelOf(o)) * RELIEF_STEP * zoom, y = o.p ? o.p.y : o.ty ?? o.y, x = Math.round(o.p ? o.p.x : o.x); let a = Math.ceil(y), b; while (a < y + 5 && !DEPTH_OF[gndAt(x, a)]) a++; for (b = a; b < a + 12 && DEPTH_OF[gndAt(x, b)]; b++);
      if (b === a) return null; const line = fy + (sy.up && up ? sy.up(y, 0) - sy.up(y, up) : up), m = [1, 0, 0, -1, 0, 2 * line]; m.low = 2 * line - (sy.row ? sy.row(b, 0) : sy(b)); return m; });
    lg.globalCompositeOperation = "destination-in"; lg.fill(wet);                    // ...and only where there is water
    // onto the picture a row of art pixels at a time, each slid a little: the ripple (fixed to the land, not to the screen)
    const z = zoom, y0 = sy.base === undefined ? sy(0) : sy.base, first = Math.floor((Math.max(0, top) - y0) / z), last = Math.ceil((Math.min(H, bottom) - y0) / z);
    ctx.globalAlpha = Math.min(.95, GLASS.alpha * opt("reflect") / 100);
    for (let r = first; r < last; r++) {
      const Y = y0 + r * z, slide = Math.round(Math.sin(r * GLASS.wave + t * GLASS.speed) * GLASS.ripple) * z;
      ctx.drawImage(layer, 0, Math.round(Y * DPR), layer.width, Math.round(z * DPR), slide, Y, W, z);
    }
    ctx.globalAlpha = 1;
  }
  // The sun's shadows fall on the land as it stands (vox_light.js): the frame hands the engine, before the land is
  // drawn, where the sun is and a picture of the shadows of what stands: each lying flat on the level its foot is
  // on, that level written in its px. The land takes each where it truly falls: on its own level, down a cliff,
  // never up a wall. (They were laid flat over the finished picture: over walls, over cliffs, over higher land.)
  let fires = [], ground = null, sunNow = null;
  const levelOf = (o) => Math.round(liftOf(o.p || {x: o.x, y: o.ty ?? o.y}) / zoom / RELIEF_STEP - .01);
  function hour() {
    const phase = (((clock.phase || 0) % 1) + 1) % 1, day = phase < .75;
    const a = day ? phase / .75 : (phase - .75) / .25;                               // the sun's way across (at night: the moon's)
    const tint = lightAt(phase), dark = Math.min(1, (1 - (.3 * tint[0] + .59 * tint[1] + .11 * tint[2]) / 255) / .36);
    const much = opt("shadows") / 100, long = opt("shadowlen") / 100;                 // (the settings: how dark, how long)
    return {dark, much, long, alpha: Math.min(.9, (SHADE.alpha + (SHADE.night - SHADE.alpha) * dark) * much), kx: (2 * a - 1) * SHADE.reach * long, ky: SHADE.fall * long};
  }
  // render.js, before the land: -> what the engine is to know of the sun (voxels.js), null with no shader
  function cast_(list, vis, sx, sy0, S, t, now) {
    // (a curved world, curve.js: the shadows are laid on the FLAT picture, north over the screen's top as far as the bend shows; the land bends them with itself)
    const sy = sy0.bent ? Curve.sy(sy0.base, S, true) : sy0, north = sy0.bent ? Math.ceil(Curve.over() / zoom) * zoom : 0;
    fires = []; sunNow = null;
    if (!SHADERS[opt("shader")] || !opt("shaderk")) return null;
    try {
      const {dark, alpha, kx, ky} = hour();
      // At night what stands near a fire is lit by it: its shadow lies away from the fire, longer the further it stands.
      const lit = [];                                          // (the fires where they are seen, and, the fourth and fifth, on the flat picture)
      if (dark > .35 && opt("shadows")) {
        for (const f of fireAt) lit.push([f.x, f.y]);
        for (const b of vis) for (const [i, c] of b.objs) if (c === "^" || c === "x") lit.push([b.bx * B + i % B, b.by * B + (i / B | 0)]);
      }
      fires = lit.map(([x, y]) => [sx(x) + S / 2, sy0(y, x) + S * .8, 0, sx(x) + S / 2, sy(y, x) + S * .8]);
      let pic = null, at = null, lo = 0, hi = 0;
      if (opt("shadows")) {
        // (the picture is small: a px of it an art px of the land, on the land's own grid, as the night's lights are.
        // A shadow is whole px of the land, still on it as you walk, and little is handed to the GPU each frame)
        const z = zoom, x0 = ((sx(0) % z) + z) % z - z, y0 = ((sy(0) % z) + z) % z - z - north, gw = Math.ceil((W - x0) / z), gh = Math.ceil((H - y0) / z), by = new Map();
        if (!ground) ground = [0, 1].map(() => document.createElement("canvas").getContext("2d", {willReadFrequently: true}));      // (kept in memory: handed to the GPU each frame as it is, nothing waited for)
        for (const g of ground) { if (g.canvas.width !== gw || g.canvas.height !== gh) { g.canvas.width = gw; g.canvas.height = gh; } g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false; }
        const [one, all] = ground, land = !!opt("landshade"); let n = 0, kept = false;
        lo = 1e4; hi = -1e4;
        one.imageSmoothingEnabled = true;                      // (drawn small: a thin thing, a stalk, is a faint line, not dashes; the land takes what is a third there)
        for (const o of list) if (o.p || o.x !== undefined) { const lv = levelOf(o); if (!by.has(lv)) by.set(lv, []); by.get(lv).push(o); }
        ready();                                               // (a kind of body not yet measured is measured on the layer, where it is seen)
        clean = true; for (const o of list) if (o.p && !o.far) standsAtY(o.p, sx, sy0, S, t, now); clean = false;
        for (const [lv, some] of by) {
          if (n && !kept) { all.clearRect(0, 0, gw, gh); all.drawImage(one.canvas, 0, 0); kept = true; }      // (more than one level: each made on `one`, gathered on `all`)
          one.setTransform(1, 0, 0, 1, 0, 0); one.globalCompositeOperation = "source-over"; one.clearRect(0, 0, gw, gh); one.setTransform(1 / z, 0, 0, 1 / z, -x0 / z, -y0 / z);
          // laid over on the ground from its foot; what of it is in the land's shadow throws none
          if (!cast(some, sx, sy, S, t, now, (fx, fy, o) => { if (fires.length && fireBy(fx, fy, S, 3)) return null; const m = [1, 0, -kx, -ky, kx * fy, fy * (1 + ky)], up = land ? upOf(o, kx, ky) : 0; if (up >= 2) m.cut = fy - Math.round(up) * zoom; return m; }, one, north)) continue;
          one.setTransform(1, 0, 0, 1, 0, 0); one.globalCompositeOperation = "source-in"; one.fillStyle = `rgb(${((lv + 32768) & 15) * 16 + 8},${((lv + 32768) >> 4 & 15) * 16 + 8},255)`; one.fillRect(0, 0, gw, gh);
          if (kept) all.drawImage(one.canvas, 0, 0);
          n++; lo = Math.min(lo, lv); hi = Math.max(hi, lv);
        }
        if (n) { pic = (kept ? all : one).canvas; at = {x: x0, y: y0, scale: z}; }
      }
      const c = SHADE.color, glass = Math.min(.95, GLASS.alpha * opt("reflect") / 100);
      return sunNow = {dir: [kx, ky], alpha: opt("shadows") ? alpha : 0, shade: [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16) / 255), cast: pic, castAt: at, castLevels: [lo, hi], land: !!opt("landshade"),
        glass: glass > 0 ? {alpha: glass, wave: GLASS.wave, ripple: GLASS.ripple, phase: (t * GLASS.speed) % (Math.PI * 2)} : null};
    } catch (e) { if (!Sun.said) { Sun.said = true; console.warn("sun: " + e.message); } return null; }
  }
  const fireBy = (fx, fy, S, k = 0) => { let best = null, d = SHADE.fire * S; for (const f of fires) { const q = Math.hypot(fx - f[k], fy - f[k + 1]); if (q < d) { d = q; best = f; } } return best && [best, d / S]; };
  // What stands in the land's shadow is in it as high as the shadow stands there: a tree at a cliff's foot is dark
  // to where the sun's line clears the cliff, and lit over it. -> px of art over level L at (x, y) (tiles) in shadow
  function shadowUp(x, y, L, kx, ky) {
    const dx = -kx * RELIEF_STEP / P, dy = -ky * RELIEF_STEP / P, ix = 1 / Math.max(Math.abs(dx), 1e-6), iy = 1 / Math.max(Math.abs(dy), 1e-6);
    let tx = Math.floor(x), ty = Math.floor(y), up = 0, mx = (dx >= 0 ? tx + 1 - x : x - tx) * ix, my = (dy >= 0 ? ty + 1 - y : y - ty) * iy;
    for (let i = 0; i < 20; i++) {                                // (tile by tile toward the sun, as the land's own shadow is found: vox_light.js)
      let t; if (mx < my) { t = mx; mx += ix; tx += Math.sign(dx); } else { t = my; my += iy; ty += Math.sign(dy); }
      if (blockOf(tx, ty)) up = Math.max(up, topAt(tx, ty) - L - t);
    }
    return up * RELIEF_STEP;
  }
  const ups = new Map(); let upsOf = "";
  function upOf(o, kx, ky) {                                  // (kept for what stands on a tile, until the land or the sun moves on)
    const key = landVer + "|" + Math.round(kx * 50) + "|" + Math.round(ky * 50), k = o.p ? "" : o.x + "," + (o.ty ?? o.y);
    if (key !== upsOf || ups.size > 4000) { upsOf = key; ups.clear(); }
    if (o.p && coveredAt(Math.round(o.p.x), Math.round(o.p.y), Floors.standOf(o.p, Math.round(o.p.x), Math.round(o.p.y)))) return 0;      // (under a roof: no sun to be out of)
    let up = o.p ? undefined : ups.get(k);
    if (up === undefined) { up = shadowUp((o.p ? o.p.x : o.x) + .5, (o.p ? o.p.y : o.ty ?? o.y) + .9, levelOf(o), kx, ky); if (!o.p) ups.set(k, up); }
    return up;
  }
  // render.js, after what stands is drawn: the land's shadow on it
  function shade(list, sx, sy, S, t, now) {
    if (!sunNow || !sunNow.alpha || !sunNow.land) return;
    try {
      const [kx, ky] = sunNow.dir, dark = new Map(), near = [];
      for (const o of list) if (o.p || (o.spr && o.x !== undefined)) { const up = upOf(o, kx, ky); if (up >= 2) { dark.set(o, up); near.push(o.p ? o.p.x : o.x, o.p ? o.p.y : o.ty); } }
      if (!dark.size) return;
      const by = (x, y) => { for (let i = 0; i < near.length; i += 2) if (Math.abs(near[i] - x) < 4 && y - near[i + 1] > -1 && y - near[i + 1] < 6) return true; return false; };
      ready();
      cast(list, sx, sy, S, t, now, (fx, fy, o) => (dark.has(o) ? {top: fy - Math.round(dark.get(o)) * zoom} : by(o.p ? o.p.x : o.x, o.p ? o.p.y : o.ty ?? o.y) ? {erase: true} : null));
      lg.globalCompositeOperation = "source-in"; lg.fillStyle = SHADE.color; lg.fillRect(0, 0, W, H);
      ctx.globalAlpha = sunNow.alpha; ctx.drawImage(layer, 0, 0, W, H); ctx.globalAlpha = 1;
    } catch (e) { if (!Sun.said) { Sun.said = true; console.warn("sun: " + e.message); } }
  }
  // By a fire at night: flat on the picture, away from the fire
  function fireShadows(list, sx, sy, S, t, now) {
    if (!fires.length) return;
    const {dark, much, long} = hour();
    ready();
    cast(list, sx, sy, S, t, now, (fx, fy) => {
      const near = fireBy(fx, fy, S); if (!near || near[1] < .45) return null;       // (not the fire's own)
      const [f, d] = near, len = Math.min(2.4, .7 + d * .32) * long, qx = (fx - f[0]) / (d * S) * len, up = (fy - f[1]) / (d * S) * len * .7;
      const qy = Math.abs(up) < .28 ? (up < -.05 ? -.28 : .28) : up;                  // (level with the fire: still a shape on the ground, not a line)
      return [1, 0, -qx, -qy, qx * fy, fy * (1 + qy)];
    });
    lg.globalCompositeOperation = "source-in"; lg.fillStyle = SHADE.color; lg.fillRect(0, 0, W, H);
    ctx.globalAlpha = Math.min(.9, SHADE.byFire * dark * much); ctx.drawImage(layer, 0, 0, W, H); ctx.globalAlpha = 1;
  }
  // render.js, between the ground and what stands on it
  function draw(list, vis, sx, sy, S, t, now) {
    mask = null;
    if (!SHADERS[opt("shader")] || !opt("shaderk")) return;
    try {
      const water = opt("reflect") || opt("waterlight") ? seenWater(vis, sx, sy, S) : null;
      waterMask(opt("waterlight") ? list : [], opt("waterlight") ? water : null, sx, sy, S, t, now);
      if (opt("reflect") && water) reflections(list, water, sx, sy, S, t, now);
      if (opt("shadows")) fireShadows(list, sx, sy, S, t, now);
    } catch (e) { if (!Sun.said) { Sun.said = true; console.warn("sun: " + e.message); } }
  }
  const shades = () => !!SHADERS[opt("shader")] && opt("shaderk") > 0 && opt("shadows") > 0;      // are shadows being drawn?
  // (for the tests: the shadows handed to the land this frame, as a picture the screen's size; in a curved world it is the flat one)
  const layerData = () => { if (!sunNow || !sunNow.cast) return []; const c = sunNow.cast, a = sunNow.castAt; ready(); lg.setTransform(1, 0, 0, 1, 0, 0); lg.imageSmoothingEnabled = false; lg.drawImage(c, a.x * DPR, a.y * DPR, c.width * a.scale * DPR, c.height * a.scale * DPR); return lg.getImageData(0, 0, layer.width, layer.height).data; };
  return {draw, cast: cast_, shade, shades, layerData, get water() { return mask; }, SHADE, GLASS, get casting() { return casting; }};
})();
