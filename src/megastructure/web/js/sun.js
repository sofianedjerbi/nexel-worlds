// What a shader adds to the world itself (the settings' Shaders page; the picture's glow and colours are shader.js):
// "we want real shaders, reflection, not just color hue tweaks, shadows, like minecraft".
//   Shadows: every tree, wall, thing, animal and person throws its own shape on the ground, away from the sun: long
//     to the west in the morning, short at noon, long to the east in the evening; at night none but a fire's.
//   Reflections: what stands by the water is seen in it upside down, under its feet, rippling.
// Both are made from the very sprites the frame is about to draw (render.js calls Sun.draw with its sorted list, the
// ground already painted, nothing standing on it yet): each is drawn once more through a transform onto a layer the
// size of the screen (a shadow: laid over on the ground from its foot, then filled flat; a reflection: turned over
// about its foot, kept only where there is water), and the layer is put on the picture. `ctx` is pointed at the
// layer meanwhile, so whatever draws a body or a wall draws its shadow too, with no code of its own.

const Sun = (() => {
  const SHADE = {alpha: .3, night: 0, color: "#1d2440", reach: 1.5, fall: .45, fire: 6, byFire: .36};      // fire: tiles a fire lights; byFire: how dark a shadow it throws   // reach: a shadow's length sideways at sunrise, in heights; fall: towards you, always
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
        const p = o.p, x = p ? p.x : o.x, y = rowOf(o);
        if ((!o.spr && !p && !o.wall && o.row === undefined) || x === undefined || o.far !== undefined) continue;      // (row: what is built over the land, floors.js)      // (past the horizon, curve.js: no shadow)
        if (p && DEPTH_OF[gndAt(Math.round(p.x), Math.round(p.y))]) continue;
        // (what the place you are seen in is seen through, xray.js: as faint as it is drawn, gone with it. "and their shadow should dispawn also")
        const over = p ? xrayOverBody(p) : o.spr ? xrayOver(o.x, o.ty) : 0;
        if (over > .98) continue;
        const fx = sx(x) + S / 2;
        const fy = p ? standsAtY(p, sx, sy, S, t, now) : o.spr && o.spr[0].src ? sy(y, x) + (o.spr[6] + footOf(...o.spr.slice(0, 5)) - 1) * zoom : sy(y, x) + S * .94;
        if (fx < -4 * S || fx > W + 4 * S || fy < -2 * S - north || fy > H + 6 * S) continue;
        const m = via(fx, fy, o);
        if (!m) continue;
        if (m.poly) { g.globalAlpha = 1 - over; g.fillStyle = "#000"; g.beginPath(); m.poly.forEach((q, i) => (i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]))); g.fill(); n++; continue; }      // (what is built: its shadow's outline, sunland.js)
        g.save();
        // (m: a transform (cut: only what of it is over that row throws a shadow); or, where it stands: {erase}: it is taken
        // out of the layer; else it alone where it is (what was under it on the layer is taken out first): {top}: what of
        // it is under that row; {tops, x0}: the same an art px across at a time (what is built); {plain}: it, as it is drawn)
        if (!m.length && o.clip !== undefined) { g.beginPath(); g.rect(0, 0, W, Math.max(0, o.clip)); g.clip(); }      // (going down behind the roll, curve.js: cut as it is drawn)
        const paint = (k) => {
          g.globalAlpha = (1 - over) * k;
          if (o.spr) { const [img, a, b, w, h, dx, dy] = o.spr; g.drawImage(img, a, b, w, h, Math.round(sx(x) + dx * zoom), Math.round(sy(y, x) + dy * zoom), w * zoom, h * zoom); }
          else if (p) drawEntity({...p}, sx, sy, S, t, now);
          else o.fx();
        };
        const all = () => { if (m.length || (!p && !tileBehind(x, y))) paint(1); else drawBehind(p || {x, y, e: {}}, sx, sy, S, paint); };
        if (m.length) { g.transform(...m); if (m.cut !== undefined || m.low !== undefined) { g.beginPath(); g.rect(-1e4, m.low ?? -1e4, 3e4, m.low === undefined ? m.cut + 1e4 : 2e4); g.clip(); } all(); }
        else if (m.plain) all();
        else {
          g.globalCompositeOperation = "destination-out"; all(); g.globalCompositeOperation = "source-over";
          if (!m.erase) {
            g.beginPath();
            if (m.tops) for (let i = 0; i < 16; i++) g.rect(m.x0 + (i ? i * zoom : -S), m.tops[i], i % 15 ? zoom : S + zoom, H + 2e5);
            else g.rect(0, m.top - 2 * zoom, W, H);
            g.clip(); all();
          }
        }
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
    // (in a curved world, curve.js: as far under as the curve draws the land over the water there: a height is as tall far off as near, what is over the eye a little more)
    // Only in the water it stands by: the first south of it in its column, to where that ends (far rows are close together: its picture went on into the next pond)
    cast(list, sx, sy, S, t, now, (fx, fy, o) => { const up = Math.max(0, levelOf(o)) * RELIEF_STEP * zoom, y = rowOf(o), x = Math.round(o.p ? o.p.x : o.x); let a = Math.ceil(y), b; while (a < y + 5 && !DEPTH_OF[gndAt(x, a)]) a++; for (b = a; b < a + 12 && DEPTH_OF[gndAt(x, b)]; b++);
      if (b === a) return null; const line = fy + (sy.up && up ? sy.up(y, 0) - sy.up(y, up) : up), m = [1, 0, 0, -1, 0, 2 * line]; m.low = 2 * line - (sy.row ? sy.row(b, 0) : sy(b)); return m; });
    lg.globalCompositeOperation = "destination-in"; lg.fill(wet);                    // ...and only where there is water
    // (in the water's own colour, faint: over water seen through, a boat's was a grey copy of the boat under it)
    lg.globalCompositeOperation = "source-atop"; lg.fillStyle = "rgba(96,186,200,.6)"; lg.fillRect(0, 0, W, H); lg.globalCompositeOperation = "source-over";
    // onto the picture a row of art pixels at a time, each slid a little: the ripple (fixed to the land, not to the screen)
    const z = zoom, y0 = sy.base === undefined ? sy(0) : sy.base, first = Math.floor((Math.max(0, top) - y0) / z), last = Math.ceil((Math.min(H, bottom) - y0) / z);
    ctx.globalAlpha = Math.min(.95, GLASS.alpha * .7 * opt("reflect") / 100);
    for (let r = first; r < last; r++) {
      const Y = y0 + r * z, slide = Math.round(Math.sin(r * GLASS.wave + t * GLASS.speed) * GLASS.ripple) * z;
      ctx.drawImage(layer, 0, Math.round(Y * DPR), layer.width, Math.round(z * DPR), slide, Y, W, z);
    }
    ctx.globalAlpha = 1;
  }
  // (the level a thing's foot is on, and its tile's row; what is built over the land says its row itself: floors.js)
  const rowOf = (o) => (o.p ? o.p.y : o.ty ?? o.row ?? o.y);
  const levelOf = (o) => Math.round(liftOf(o.p || {x: o.x, y: rowOf(o)}) / zoom / RELIEF_STEP - .01);
  // render.js, between the ground and what stands on it
  function draw(list, vis, sx, sy, S, t, now) {
    mask = null;
    if (!SHADERS[opt("shader")] || !opt("shaderk")) return;
    try {
      const water = opt("reflect") || opt("waterlight") ? seenWater(vis, sx, sy, S) : null;
      waterMask(opt("waterlight") ? list : [], opt("waterlight") ? water : null, sx, sy, S, t, now);
      if (opt("reflect") && water) reflections(list, water, sx, sy, S, t, now);
    } catch (e) { if (!Sun.said) { Sun.said = true; console.warn("sun: " + e.message); } }
  }
  const shades = () => ((!!SHADERS[opt("shader")] && opt("shaderk") > 0) || !!opt("depth")) && opt("shadows") > 0;      // are shadows being drawn? (by a shader, or as the land's depth: sunland.js)
  // (kit: for sunland.js, the other half of this: the shadows the land takes. It adds Sun.cast, Sun.shade, Sun.layerData)
  const kit = {ready, cast, levelOf, rowOf, measure(list, sx, sy, S, t, now) { ready(); clean = true; for (const o of list) if (o.p && !o.far) standsAtY(o.p, sx, sy, S, t, now); clean = false; }, get lg() { return lg; }, get layer() { return layer; }};
  return {draw, shades, kit, get water() { return mask; }, SHADE, GLASS, get casting() { return casting; }};
})();
