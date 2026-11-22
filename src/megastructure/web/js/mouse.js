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
// THE BLOCK UNDER THE POINTER (build mode, the cursor riding the land): the pointer's ray through the cubes as the HD camera draws them, the first solid cell it meets -> {x, y, z: its top, face: "T" its top, "S", "W", "E", "N"}, or null.
// The ray: the place on the screen's px at each height (HdLook.screenOf solved for x, y at that height), from over the highest land in view down, a straight piece every half level, cell by cell along it
// (Amanatides-Woo). (It was each tile's top at the cursor's riding height, nearest row first, no side faces: on terraces the pointer on a block's side picked a block two tiles off, or nothing)
let rayHi = null;
function rayHit(mx, my) {
  const s = myPos(); if (!s || !HdLook.on || !HdLook.screenOf(s.x, s.y, 0)) return null;
  const S = HdLook.screenOf, z0 = myZ(s.x, s.y), win = (x, y) => (HdLook.win && HdLook.win.n && HdLook.win.a > 0 ? HdLook.winAt(x, y) : null);
  if (!rayHi || rayHi.x !== s.x || rayHi.y !== s.y || performance.now() - rayHi.t > 500) { let hi = z0, lo = z0; for (let y = s.y - 40; y <= s.y + 24; y++) for (let x = s.x - 24; x <= s.x + 24; x++) { const t = topAt(x, y); hi = Math.max(hi, t); lo = Math.min(lo, t); } rayHi = {x: s.x, y: s.y, t: performance.now(), hi, lo}; }
  const on = (z, g) => { let [x, y] = g; for (let i = 0; i < 12; i++) { const a = S(x, y, z), b = S(x + .01, y, z), c = S(x, y + .01, z); if (!a || !b || !c) return null; const ex = a[0] - mx, ey = a[1] - my; if (Math.abs(ex) + Math.abs(ey) < .02) return [x, y, z];
    const j11 = (b[0] - a[0]) / .01, j21 = (b[1] - a[1]) / .01, j12 = (c[0] - a[0]) / .01, j22 = (c[1] - a[1]) / .01, d = j11 * j22 - j12 * j21; if (!d) return null; x -= (j22 * ex - j12 * ey) / d; y -= (j11 * ey - j21 * ex) / d; } return null; };
  const solid = (x, y, top) => solidAt(x, y, top) && !((w) => w && top > w[1])(win(x, y));   // (a cell whose top is `top`; over the x-ray window's ceiling the land is not drawn: not pointed at)
  const FACE = [["W", "E"], ["N", "S"], ["T", "T"]];
  let g = [s.x + .5, s.y + .5], A = null;
  for (let z = rayHi.hi + 1; z >= Math.max(rayHi.lo - 2, z0 - 64); z -= .5) {
    const B = on(z, g); if (!B) { A = null; continue; } g = [B[0], B[1]];
    if (A) {   // the cells this piece of the ray goes through, in order
      const d = [0, 1, 2].map((i) => B[i] - A[i]), c = A.map(Math.floor), st = d.map(Math.sign), tD = d.map((v) => (v ? 1 / Math.abs(v) : Infinity)), tM = [0, 1, 2].map((i) => (d[i] ? (st[i] > 0 ? c[i] + 1 - A[i] : A[i] - c[i]) * tD[i] : Infinity));
      for (let n = 0; n < 64; n++) { const i = tM[0] <= tM[1] && tM[0] <= tM[2] ? 0 : tM[1] <= tM[2] ? 1 : 2; if (tM[i] > 1) break; c[i] += st[i]; tM[i] += tD[i];
        if (solid(c[0], c[1], c[2] + 1)) return {x: c[0], y: c[1], z: c[2] + 1, face: FACE[i][st[i] > 0 ? 0 : 1]}; }
    } else if (solid(Math.floor(B[0]), Math.floor(B[1]), Math.floor(B[2]) + 1)) return null;   // (the ray begins inside land: no answer here)
    A = B;
  }
  return null;
}
function tileAtScreen(mx, my) {                        // -> {x, y, fy: how far down the tile, 0 to 1}
  if (HdLook.on && Build.on && Build.S.plane === null && Build.S.deep === null) { const h = rayHit(mx, my); if (h) return {x: h.x, y: h.y, fy: .5, z: h.z, face: h.face !== "T", side: h.face}; }   // (build mode: the block under the pointer, its top or a side)
  if (HdLook.on) { const q = HdLook.pick(mx, my, Build.on ? (x, y) => Build.level({x, y}) : null); if (q) return q; }   // (the HD camera: the top or the front under the pointer, hd.js; build mode lifted or sunk by E, Q: at the cursor's height)
  const S = TS(), [ox, oy] = screenOrigin(S), x = Math.floor((mx - ox) / S), at = (y, up) => Curve.y(oy + y * S, up), row = (f) => Math.floor((f - oy) / S);
  // The column's tiles from the nearest that could be drawn there to the furthest (a level is drawn higher or lower:
  // relief.js; a row far north nearer the horizon: curve.js): the first whose top is under the pointer, or whose
  // front is, down to the land south of it. (It looked six tiles south and at tops alone: a pit was not undone.)
  const reach = (APART * RELIEF_STEP / 16 + 1) * S, eye = Curve.c ? Math.abs(Curve.c.ref) : 0;
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
    if (my >= foot && my < at(y + 1, aimLift(x, y + 1))) return {x, y, fy: .999, face: true, down: Math.max(0, Math.floor((my - foot) / (RELIEF_STEP * zoom)))};      // (down: which cell of the face, levels under its top)      // (face: its wall's face is what is pointed at: the mark is that block down to its foot, mark.js: its top alone was a box on the far rim of a pit, a tile and a half over the pointer)
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
