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
  const SHADE = {alpha: .3, night: .1, color: "#1d2440", reach: 1.5, fall: .45};   // reach: a shadow's length sideways at sunrise, in heights; fall: towards you, always
  const GLASS = {alpha: .5, ripple: 1, wave: .9, speed: 2.2};                     // ripple: art px a row slides; wave: how tight; speed
  let layer = null, lg = null;
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
  // Each thing of the list drawn through the transform `via(footX, footY)` gives, with ctx on the layer
  function cast(list, sx, sy, S, t, now, via) {
    const main = ctx;
    ctx = lg;
    try {
      for (const o of list) {
        const p = o.p, x = p ? p.x : o.x, y = p ? p.y : o.ty ?? o.y;
        if ((!o.spr && !p && !o.wall) || x === undefined) continue;
        const fx = sx(x) + S / 2;
        const fy = p ? bodyY(p, sy) + S * .74 : o.spr && o.spr[0].src ? sy(y, x) + (o.spr[6] + footOf(...o.spr.slice(0, 5)) - 1) * zoom : sy(y, x) + S * .94;
        if (fx < -4 * S || fx > W + 4 * S || fy < -2 * S || fy > H + 6 * S) continue;
        lg.save();
        lg.transform(...via(fx, fy));
        if (o.spr) { const [img, a, b, w, h, dx, dy] = o.spr; lg.drawImage(img, a, b, w, h, Math.round(sx(x) + dx * zoom), Math.round(sy(y, x) + dy * zoom), w * zoom, h * zoom); }
        else if (p) drawEntity(p, sx, sy, S, t, now);
        else o.fx();
        lg.restore();
      }
    } finally { ctx = main; lg.setTransform(DPR, 0, 0, DPR, 0, 0); lg.globalAlpha = 1; }
  }
  function reflections(list, vis, sx, sy, S, t, now) {
    if (!vis.some((b) => b.water && b.water.any)) return;
    const [vx, vy, vw, vh] = viewRect(2), wet = new Path2D();
    let any = false, top = H, bottom = 0;
    for (let y = vy; y <= vy + vh; y++) for (let x = vx; x <= vx + vw; x++) if (DEPTH_OF[gndAt(x, y)]) {
      const Y = sy(y, x); wet.rect(sx(x), Y, S, S); any = true; top = Math.min(top, Y); bottom = Math.max(bottom, Y + S);
    }
    if (!any) return;
    ready();
    cast(list, sx, sy, S, t, now, (fx, fy) => [1, 0, 0, -1, 0, 2 * fy]);            // turned over about its foot
    lg.globalCompositeOperation = "destination-in"; lg.fill(wet);                    // ...and only where there is water
    // onto the picture a row of art pixels at a time, each slid a little: the ripple (fixed to the land, not to the screen)
    const z = zoom, y0 = sy(0), first = Math.floor((Math.max(0, top) - y0) / z), last = Math.ceil((Math.min(H, bottom) - y0) / z);
    ctx.globalAlpha = GLASS.alpha;
    for (let r = first; r < last; r++) {
      const Y = y0 + r * z, slide = Math.round(Math.sin(r * GLASS.wave + t * GLASS.speed) * GLASS.ripple) * z;
      ctx.drawImage(layer, 0, Math.round(Y * DPR), layer.width, Math.round(z * DPR), slide, Y, W, z);
    }
    ctx.globalAlpha = 1;
  }
  function shadows(list, sx, sy, S, t, now) {
    const phase = (((clock.phase || 0) % 1) + 1) % 1, day = phase < .75;
    const a = day ? phase / .75 : (phase - .75) / .25;                               // the sun's way across (at night: the moon's)
    const tint = lightAt(phase), dark = Math.min(1, (1 - (.3 * tint[0] + .59 * tint[1] + .11 * tint[2]) / 255) / .36);
    const alpha = SHADE.alpha + (SHADE.night - SHADE.alpha) * dark;
    const kx = (2 * a - 1) * SHADE.reach, ky = SHADE.fall;
    ready();
    cast(list, sx, sy, S, t, now, (fx, fy) => [1, 0, -kx, -ky, kx * fy, fy * (1 + ky)]);   // laid over on the ground from its foot
    lg.globalCompositeOperation = "source-in"; lg.fillStyle = SHADE.color; lg.fillRect(0, 0, W, H);   // one flat shade: two shadows that cross are not darker
    ctx.globalAlpha = alpha; ctx.drawImage(layer, 0, 0, W, H); ctx.globalAlpha = 1;
  }
  // render.js, between the ground and what stands on it
  function draw(list, vis, sx, sy, S, t, now) {
    if (!SHADERS[opt("shader")] || !opt("shaderk")) return;
    try {
      if (opt("reflect")) reflections(list, vis, sx, sy, S, t, now);
      if (opt("shadows")) shadows(list, sx, sy, S, t, now);
    } catch (e) { if (!Sun.said) { Sun.said = true; console.warn("sun: " + e.message); } }
  }
  return {draw, SHADE, GLASS};
})();
