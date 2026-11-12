// Swimming: in shallow water without a boat (sim/movement.py). Every race and every outfit swims the same way, because
// the swimmer is the person's own sheet: head and shoulders above the water, the rest dimly seen under it.
// Around them: a ring of foam that breathes, a splash on alternate sides with each stroke, and a wake that spreads
// and fades along the way they came.

const SWIM = {sink: 5, line: 27, stroke: 260, tread: 700, wakeEvery: 110, wakeLife: 1400};   // art px; sheet row of the waterline; ms
function swimsAt(p, e) {
  if (e.sail) return false;
  const t = tile(Math.round(p.x), Math.round(p.y));
  return t ? wet(t[1]) && t[0] !== "V" : !!e.swim;
}
function drawSwimmer(p, e, sheet, x, y, z, now, sx, sy) {
  const moving = now - p.moved < 300 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
  const stroke = Math.floor((now + e.id * 97) / (moving ? SWIM.stroke : SWIM.tread));
  const bob = (moving ? stroke % 2 : Math.round(Math.sin(now / 450 + e.id) * .5 + .5)) * z;      // one pixel, with each stroke
  p.running = false;                                         // nobody sprints in water (the server will not either)
  if (!p.swam) {                                             // going in: a splash
    p.swam = true; p.wake = [];
    burst(p.x, p.y + .3, "water", 10, {up: 2.6, spread: 3, g: 7, life: .5});
    sfx("water", Math.round(p.x), Math.round(p.y));          // one splash going in; after that only the strokes are heard
  }
  // the wake: a mark dropped every few steps of the way, each one two flecks of foam drifting apart and fading
  if (moving && (!p.wake.length || now - p.wake[p.wake.length - 1].t > SWIM.wakeEvery)) p.wake.push({x: p.x, y: p.y, t: now, across: !!p.fy});
  while (p.wake.length && now - p.wake[0].t > SWIM.wakeLife) p.wake.shift();
  for (const w of p.wake) {
    const a = (now - w.t) / SWIM.wakeLife, wx = Math.round(sx(w.x)) + 8 * z, wy = Math.round(sy(w.y, w.x)) + 13 * z, d = Math.round(2 + a * 7) * z;
    ctx.globalAlpha = (1 - a) * .85;
    ctx.fillStyle = a < .35 ? "#ffffff" : "#d8f4ff";
    if (w.across) { ctx.fillRect(wx - d - z, wy, 2 * z, z); ctx.fillRect(wx + d, wy, 2 * z, z); }      // swimming up or down: foam to the left and right
    else { ctx.fillRect(wx - z, wy - d, 2 * z, z); ctx.fillRect(wx - z, wy + d, 2 * z, z); }           // sideways: above and below
    if (a < .3) ctx.fillRect(wx, wy, z, z);                                                            // bubbles where they just were
  }
  ctx.globalAlpha = 1;
  const deep = DEPTH_OF[gndAt(Math.round(p.x), Math.round(p.y))] || 1, shY = y + (15 + deep * 2) * z;   // their shadow on the bottom, further down the deeper it lies
  ctx.fillStyle = "rgba(24,40,72,.2)";
  ctx.fillRect(x + 3 * z, shY, 10 * z, 2 * z); ctx.fillRect(x + 5 * z, shY - z, 6 * z, 4 * z);
  if (moving && stroke !== p.lastStroke) {                   // a stroke: a splash beside them, a side each time
    const side = stroke % 2 ? .35 : -.35;
    burst(p.x + (p.fy ? side : -p.fx * .2), p.y + .35 + (p.fx ? side * .4 : 0), "water", 3, {up: 1.4, spread: 1.6, g: 6, life: .35});
    if (stroke % 2) sfx("swim", Math.round(p.x), Math.round(p.y));      // a soft pull, every second stroke; treading water is silent
  }
  p.lastStroke = stroke;
  const row = DIR_ROW(p), col = Math.floor(now / 140) % 8, cellX = x - 16 * z, cellY = y - 18 * z + SWIM.sink * z + bob, wl = y + 14 * z;
  const back = [-p.fx, -p.fy], fi = row * 8 + col;
  wearFx("back", e, sheet, fi, cellX, cellY, z, now, moving, back);
  ctx.globalAlpha = .28;                                     // legs and feet, seen through the water
  ctx.drawImage(sheet, col * 48, row * 48 + SWIM.line, 48, 7, cellX, cellY + SWIM.line * z, 48 * z, 7 * z);
  ctx.globalAlpha = 1;
  ctx.drawImage(sheet, col * 48, row * 48, 48, SWIM.line, cellX, cellY, 48 * z, SWIM.line * z);          // head and shoulders
  wearFx("front", e, sheet, fi, cellX, cellY, z, now, moving, back);
  const wide = (7 + stroke % 2) * z, cx = x + 8 * z;         // the ring of foam at the waterline, breathing with the stroke
  ctx.fillStyle = "rgba(255,255,255,.85)";
  ctx.fillRect(cx - wide, wl - z, 3 * z, z); ctx.fillRect(cx + wide - 3 * z, wl - z, 3 * z, z);
  ctx.fillStyle = "rgba(216,244,255,.7)";
  ctx.fillRect(cx - wide + 2 * z, wl, 2 * wide - 4 * z, z);
  ctx.fillRect(cx - wide - z, wl - 2 * z, z, z); ctx.fillRect(cx + wide, wl - 2 * z, z, z);
}
