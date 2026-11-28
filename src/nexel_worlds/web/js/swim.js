// Swimming: in shallow water without a boat (sim/movement.py). Every race and every outfit swims the same way, because
// the swimmer is the person's own sheet: head and shoulders above the water, the rest dimly seen under it.
// Around them: a ring of foam that breathes, a splash on alternate sides with each stroke, and a wake that spreads
// and fades along the way they came.
// A sprint in the water (Shift, as on land: twice as fast): the strokes come twice as often, each throws water up on
// both sides and behind, a wave of foam is pushed ahead, and the wake is another thing: marks twice as close, three
// flecks a side that spread nearly twice as wide and last longer, with a churned line of white down the middle.

const SWIM = {sink: 5, sinkMs: 150, line: 27, stroke: 260, tread: 700, wakeEvery: 110, wakeLife: 1400, dashStroke: 130, dashEvery: 45, dashLife: 2100};   // art px; sheet row of the waterline; ms
function swimsAt(p, e) {
  if (e.sail) return false;
  // (you in the air, a jump's arc (leap.js) over the water: not in it. The tile under you is water, and you were drawn
  // swimming there, sunk to the face, while your name flew the arc over it: "teleported into the water")
  if (e.kind === "agent" && e.id === myId && Leap.on()) return false;
  const t = tile(Math.round(p.x), Math.round(p.y));
  return t ? (wet(t[1]) && t[0] !== "V") || !!(e.swim && Flow.col(Math.round(p.x), Math.round(p.y))) : !!e.swim;   // (or in water that runs, deep enough: the server says, flow.js)
}
// The wake someone left: each mark two flecks of foam drifting apart and fading, in its own time. Drawn for a swimmer
// and for someone who has just come out (characters.js): the marks behind them were all gone at once at the shore.
// A mark fades out over the last part of its life in whole art px, never by a smooth alpha (the HD look draws a
// body's picture with no blending: a px under half there was gone, one over it whole, so the wake ended in a pop):
// it thins (one px in two, then one in four, by a 2x2 pattern of its own px) and its flecks shorten. Its last px
// goes when its life ends.
const WAKE_FADE = {from: .45, line: .3, bubble: .2};       // (part of a mark's life where it starts to thin: flecks, the churned line, bubbles)
const wakeLeft = (a, from) => Math.max(0, Math.min(1, (1 - a) / (1 - from)));      // 1 until `from`, then down to 0 at its end
const WAKE_2X2 = [.125, .625, .875, .375];                 // (a 2x2 pattern: a px is kept while what is left of it is over its number)
function wakePx(x, y, w, h, left, z, seed) {               // a fleck of w x h art px, each kept while `left` is over its place in the pattern
  if (left >= 1) { ctx.fillRect(x, y, w * z, h * z); return; }
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (left > WAKE_2X2[((i + seed) & 1) + ((j + (seed >> 1)) & 1) * 2]) ctx.fillRect(x + i * z, y + j * z, z, z);
}
function drawWake(p, now, sx, sy, z) {
  if (!p.wake || !p.wake.length || sy.apart) return;       // (apart: the HD look draws it on its own, wakePicture)
  while (p.wake.length && now - p.wake[0].t > (p.wake[0].dash ? SWIM.dashLife : SWIM.wakeLife)) p.wake.shift();
  for (const w of p.wake) {
    const a = Math.min(1, (now - w.t) / (w.dash ? SWIM.dashLife : SWIM.wakeLife)), left = wakeLeft(a, WAKE_FADE.from); if (left <= 0) continue;
    const wx = Math.round(sx(w.x)) + 8 * z, wy = Math.round(sy(w.y, w.x)) + (13 - STAND) * z;
    const d = Math.round(w.dash ? 3 + a * 13 : 2 + a * 7), seed = (w.t / 45) | 0;
    ctx.fillStyle = a < .35 ? "#ffffff" : "#d8f4ff";
    for (let k = 0; k < (w.dash ? 2 : 1); k++) {             // (a sprint's: a second, shorter fleck inside the first and a little behind it: two broken lines a side)
      const dk = d - k * 4, len = Math.max(1, Math.round((w.dash ? 4 - 2 * k : 2) * Math.min(1, left * 1.5))), lag = k * 3;
      if (dk < 2) break;
      if (w.across) { wakePx(wx - (dk + 1) * z, wy - w.fy * lag * z, 1, len, left, z, seed); wakePx(wx + dk * z, wy - w.fy * lag * z, 1, len, left, z, seed + 1); }       // swimming up or down: foam to the left and right
      else { wakePx(wx - (1 + w.fx * lag) * z, wy - dk * z, len, 1, left, z, seed); wakePx(wx - (1 + w.fx * lag) * z, wy + dk * z, len, 1, left, z, seed + 1); }             // sideways: above and below
    }
    const bub = wakeLeft(a / .3, WAKE_FADE.bubble); if (bub > 0) wakePx(wx, wy, 1, 1, bub, z, seed);                       // bubbles where they just were
    const line = wakeLeft(a / .55, WAKE_FADE.line);
    if (w.dash && line > 0) { ctx.fillStyle = "#ffffff"; const j = ((w.t / 45 | 0) % 3 - 1) * z; if (w.across) wakePx(wx + j - z, wy, 2, 2, line, z, seed); else wakePx(wx - z, wy + j - z, 2, 2, line, z, seed); }   // the churned line down the middle
  }
}
// The HD look: a swimmer's wake as a picture of its own, as big as the wake is, laid flat on the water (hd.js,
// vox_style.js `lie`: a px of it an art px of the water), with no shadow. It was drawn in the body's upright picture,
// four tiles wide: cut in a straight line a tile and a half behind them. -> {canvas, fx, fy} (the swimmer's foot at
// px fx, fy: the middle of their tile), or null
const wakePics = new WeakMap();
function wakePicture(p, now) {
  if (!p.wake || !p.wake.length) return null;
  let l = 0, r = 0, t = 0, b = 0;
  for (const w of p.wake) { l = Math.min(l, w.x - p.x); r = Math.max(r, w.x - p.x); t = Math.min(t, w.y - p.y); b = Math.max(b, w.y - p.y); }
  const q = (v) => Math.ceil((v * 16 + 28) / 16) * 16, L = q(-l), R = q(r), T = q(-t), B = q(b);   // (room for the flecks spreading, 16 px, and their length; whole tiles: not a new size each frame)
  let c = wakePics.get(p); if (!c) { c = document.createElement("canvas"); wakePics.set(p, c); }
  if (c.width !== L + R || c.height !== T + B) { c.width = L + R; c.height = T + B; }
  const g = c.getContext("2d"); g.clearRect(0, 0, c.width, c.height);
  const sx = (x) => L - 8 + (x - p.x) * 16, sy = (y) => T - 8 + (y - p.y) * 16;      // (as the body's picture has them: the foot 8 px under its tile's top)
  drawOn(g, 1, () => drawWake(p, now, sx, sy, 1));
  c._v = (c._v || 0) + 1;
  return {canvas: c, fx: L, fy: T};
}
// how far under the water's face a swimmer is drawn: SWIM.sink, eased in over SWIM.sinkMs from going in (all at once, the body
// dropped 5 art px in a frame on top of the leap's own fall: hd_splash's jolt, 11 px in 27 ms), in whole art px
const sinkOf = (st, now) => Math.round(SWIM.sink * Math.min(1, (now - (st.swamAt ?? -1e9)) / SWIM.sinkMs));
function drawSwimmer(p, e, sheet, x, y, z, now, sx, sy) {
  y -= BodyPlace.of(p).up * z;                              // (just down from a leap: its lift, body_place.js)
  const moving = now - p.moved < 300 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
  const dash = SWIM_SPRINT && moving && (e.id === myId && e.kind === "agent" ? sprinting() : !!e.run);     // a sprint in the water
  const stroke = Math.floor((now + e.id * 97) / (dash ? SWIM.dashStroke : moving ? SWIM.stroke : SWIM.tread));
  const bob = (moving ? stroke % 2 : Math.round(Math.sin(now / 450 + e.id) * .5 + .5)) * z;      // one pixel, with each stroke
  p.running = dash; p.stroking = moving;                     // (what this frame drew: strokes, or treading water)
  const st = BodyPlace.state(p);
  if (!st.swam) {                                             // going in: a splash
    st.swam = true; st.swamAt = now; p.wake = p.wake || [];                   // (the marks of the last swim, if any are left, stay)
    burst(p.x, p.y + .3 - UP, "water", 10, {up: 2.6, spread: 3, g: 7, life: .5});
    sfx("water", Math.round(p.x), Math.round(p.y));          // one splash going in; after that only the strokes are heard
  }
  // the wake: a mark dropped every few steps of the way, each one two flecks of foam drifting apart and fading
  if (moving && (!p.wake.length || now - p.wake[p.wake.length - 1].t > (dash ? SWIM.dashEvery : SWIM.wakeEvery))) p.wake.push({x: p.x, y: p.y, t: now, across: !!p.fy, dash, fx: p.fx || 0, fy: p.fy || 0});
  drawWake(p, now, sx, sy, z);
  const deep = DEPTH_OF[gndAt(Math.round(p.x), Math.round(p.y))] || 1, shY = y + (15 + deep * 2) * z;   // their shadow on the bottom, further down the deeper it lies
  ctx.fillStyle = "rgba(24,40,72,.2)";
  ctx.fillRect(x + 3 * z, shY, 10 * z, 2 * z); ctx.fillRect(x + 5 * z, shY - z, 6 * z, 4 * z);
  if (moving && stroke !== p.lastStroke) {                   // a stroke: a splash beside them, a side each time
    const side = stroke % 2 ? .35 : -.35;
    burst(p.x + (p.fy ? side : -p.fx * .2), p.y + .35 - UP + (p.fx ? side * .4 : 0), "water", dash ? 5 : 3, {up: dash ? 2.2 : 1.4, spread: dash ? 2.4 : 1.6, g: 6, life: dash ? .45 : .35});
    if (dash) {                                              // a sprint: the other side too, and a tail of water thrown up behind
      burst(p.x + (p.fy ? -side : -p.fx * .2), p.y + .35 - UP + (p.fx ? -side * .4 : 0), "water", 3, {up: 1.8, spread: 2, g: 6, life: .4});
      burst(p.x - p.fx * .6, p.y - p.fy * .6 + .3 - UP, "water", 4, {up: 2.6, spread: 1.6, g: 7, life: .5});
    }
    if (stroke % 2) sfx("swim", Math.round(p.x), Math.round(p.y));      // a soft pull, every second stroke; treading water is silent
  }
  p.lastStroke = stroke;
  const row = DIR_ROW(p), col = Math.floor(now / (dash ? 70 : 140)) % 8, cellX = x - 16 * z, cellY = y - 18 * z + sinkOf(st, now) * z + bob, wl = y + 14 * z;
  const back = [-p.fx, -p.fy], fi = row * 8 + col;
  wearFx("back", e, sheet, fi, cellX, cellY, z, now, moving, back);
  if (WaterBed.on) WaterBed.under(sheet, col * 48, row * 48 + SWIM.line, 48, 12, cellX, cellY + SWIM.line * z, z, Math.round(p.x), Math.round(p.y));      // (clear water: the body under the face, tinted by its depth)
  else { ctx.globalAlpha = .28; ctx.drawImage(sheet, col * 48, row * 48 + SWIM.line, 48, 7, cellX, cellY + SWIM.line * z, 48 * z, 7 * z); ctx.globalAlpha = 1; }      // legs and feet, seen through the water
  ctx.drawImage(sheet, col * 48, row * 48, 48, SWIM.line, cellX, cellY, 48 * z, SWIM.line * z);          // head and shoulders
  wearFx("front", e, sheet, fi, cellX, cellY, z, now, moving, back);
  const wide = (7 + stroke % 2 + (dash ? 1 : 0)) * z, cx = x + 8 * z;         // the ring of foam at the waterline, breathing with the stroke
  if (dash) {                                                // the wave pushed ahead: a chevron of foam, its point the way they go
    const fx = p.fx || 0, fy = p.fx ? 0 : (p.fy || 1), bx = cx + fx * 10 * z, by = wl - z + fy * 5 * z;
    ctx.fillStyle = "rgba(255,255,255,.9)";
    for (let k = 0; k < 3; k++) for (const s of [-1, 1]) {
      const qx = bx - fx * k * z + (fx ? 0 : s * (k + 1) * 2 * z), qy = by - fy * k * z + (fx ? s * (k + 1) * z : 0);
      ctx.fillRect(Math.round(qx) - z, Math.round(qy), (fx ? 1 : 2) * z, z);
    }
  }
  ctx.fillStyle = "rgba(255,255,255,.85)";
  ctx.fillRect(cx - wide, wl - z, 3 * z, z); ctx.fillRect(cx + wide - 3 * z, wl - z, 3 * z, z);
  ctx.fillStyle = "rgba(216,244,255,.7)";
  ctx.fillRect(cx - wide + 2 * z, wl, 2 * wide - 4 * z, z);
  ctx.fillRect(cx - wide - z, wl - 2 * z, z, z); ctx.fillRect(cx + wide, wl - 2 * z, z, z);
}
