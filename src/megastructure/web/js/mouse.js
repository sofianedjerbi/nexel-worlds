// Mouse: hover hints, click to act, drag. (The wheel: zoom.js.)

// =====================================================================================
//  Input
// =====================================================================================
const mouse = {x: 0, y: 0, in: false};
let drag = null;
// How far up a tile is drawn, where you point at it: in build mode with the cursor lifted or sunk, at its height;
// where something is built (floors.js), the floor nearest your own height; otherwise the land
function aimLift(x, y) {
  if (Build.on && (Build.S.plane !== null || Build.S.deep !== null)) return shOf(Build.S.plane !== null ? Build.S.plane : Build.S.deep) * zoom;
  return FLOORS && myAt && Floors.any(x, y) ? shOf(settleNear(x, y, myAt.z)) * zoom : liftAt(x, y);
}
function tileAtScreen(mx, my) {                        // -> {x, y, fy: how far down the tile, 0 to 1}
  const S = TS(), [ox, oy] = screenOrigin(S), x = Math.floor((mx - ox) / S), at = (y, up) => Curve.y(oy + y * S, up), row = (f) => Math.floor((f - oy) / S);
  // The column's tiles from the nearest that could be drawn there to the furthest (a level is drawn higher or lower:
  // relief.js; a row far north nearer the horizon: curve.js): the first whose top is under the pointer, or whose
  // front is, down to the land south of it. (It looked six tiles south and at tops alone: a pit was not undone.)
  const reach = (APART / 2 + 1) * S, eye = Curve.c ? Math.abs(Curve.c.ref) : 0;
  // Who stands in the roll is drawn as big as ever on rows a few px tall: under the pointer, it is who is meant, not
  // the tile behind its head (the nearest, if two). Near you, where a body is on its own tile, the tile says it.
  if (Curve.on && !Build.on) {
    const sy = Curve.sy(oy, S); let who = null;
    for (const p of ents.values()) if (p.e && !(p.e.kind === "agent" && p.e.id === myId)) {
      const bx = ox + p.x * S, lift = liftOf(p), by = bodyY(p, sy);
      if (mx >= bx && mx < bx + S && my >= by && my < by + S && Math.abs(by - (oy + p.y * S - lift - STAND * zoom)) > 1 && !sy.gone(p.y, lift) && (!who || p.y > who.y)) who = p;
    }
    if (who) return {x: Math.round(who.x), y: Math.round(who.y), fy: .5};
  }
  for (let y = row(Curve.inv(my + reach) + reach + eye), end = row(Curve.inv(my) - reach - eye) - 1; y >= end; y--) {
    const up = aimLift(x, y), top = at(y, up), foot = at(y + 1, up);
    if (my >= top && my < foot) return {x, y, fy: (my - top) / (foot - top)};
    if (my >= foot && my < at(y + 1, aimLift(x, y + 1))) return {x, y, fy: .999};
  }
  const y = row(Curve.inv(my)), top = at(y, 0);
  return {x, y, fy: Math.max(0, Math.min(.999, (my - top) / Math.max(1, at(y + 1, 0) - top)))};
}
cv.addEventListener("mousemove", (e) => {
  if (Math.abs(e.clientX - mouse.x) + Math.abs(e.clientY - mouse.y) > 4) inputMode = "mouse";   // the mouse is back
  mouse.x = e.clientX; mouse.y = e.clientY; mouse.in = true;
  if (drag) {
    const dx = (e.clientX - drag.x) / TS(), dy = (e.clientY - drag.y) / TS();
    if (Math.abs(dx) + Math.abs(dy) > .3) drag.moved = true;
    if (drag.moved && me && Build.on) { const q = tileAtScreen(e.clientX, e.clientY); if (!drag.at || drag.at.x !== q.x || drag.at.y !== q.y) { drag.at = q; Build.click(q, e.shiftKey); } }   // (a row of plans)
    if (drag.moved && !me) { follow = null; camT.x = cam.x = drag.cx - dx; camT.y = cam.y = drag.cy - dy; }
  }
  const p = tileAtScreen(e.clientX, e.clientY), t = tile(p.x, p.y), tip = $("hover");
  if (!t) { tip.style.display = "none"; return; }
  let text;
  if (me && Build.on) Build.point(p);
  if (me) { const it = Build.on ? Build.hint(p) : intent(aimAt(p, e.shiftKey), e.shiftKey); text = it ? it.text : ""; tip.className = it && it.ok === false ? "bad" : ""; cv.classList.toggle("act", !!(it && !it.walk && !it.info && it.ok !== false)); }
  else {
    const here = entityAt(p);
    text = here ? (here.e.name || here.e.kind) : GROUND.has(t[0]) ? label(CH[t[1]]) : label(CH[t[0]]);
  }
  if (!text || (me && text === "Walk here")) { tip.style.display = "none"; return; }
  tip.textContent = text;
  tip.style.display = "block"; tip.style.left = e.clientX + 16 + "px"; tip.style.top = e.clientY + 14 + "px";
});
cv.addEventListener("mouseleave", () => { mouse.in = false; $("hover").style.display = "none"; });
cv.addEventListener("mousedown", (e) => { if (e.button === 0) drag = {x: e.clientX, y: e.clientY, cx: cam.x, cy: cam.y, moved: false}; });
cv.addEventListener("mouseup", (e) => { if (e.button === 0 && drag && !drag.moved && me) { const q = tileAtScreen(e.clientX, e.clientY); if (Build.on) Build.click(q, e.shiftKey); else clickTile(q, e.shiftKey); } drag = null; });
cv.addEventListener("contextmenu", (e) => { e.preventDefault(); if (!me) return; const q = tileAtScreen(e.clientX, e.clientY); if (Build.on) Build.click(q, true); else clickTile(q, false); });
