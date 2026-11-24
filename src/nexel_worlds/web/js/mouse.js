// Mouse: hover hints, click to act, drag. (The wheel: zoom.js.)

// =====================================================================================
//  Input
// =====================================================================================
const mouse = {x: 0, y: 0, in: false};
let drag = null;
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
  // (a cell whose top is `top`, of the land or built, or what stands in it as boxes (a wall, a door, a fence: hd_things.js `is`): 2; over the x-ray window's ceiling the land is not drawn: not pointed at)
  const solid = (x, y, top) => ((w) => w && top > w[1])(win(x, y)) ? 0 : solidAt(x, y, top) ? 1 : HdThings.is(Floors.thingAt(x, y, top - 1) || "-", x, y) && solidAt(x, y, top - 1) ? 2 : 0;
  const FACE = [["W", "E"], ["N", "S"], ["T", "T"]];
  // THE RAY'S POINTS, a level's half apart, from its highest down: followed from your own level up and down, each from the one
  // before. (It was followed from its top down, begun where you stand: on a curved world (HdLook.bend) a level meets the screen's
  // point a second time far past the bend, where the land drops away, and begun 20 levels up, over a tall hill near you, it found
  // that far one and went down it: the cursor was 30 tiles north of the tile pointed at, on the land there)
  const zl = Math.max(rayHi.lo - 2, z0 - 64), zm = Math.round(z0 * 2) / 2, pts = [], walk = (z, step, end, g) => { for (; step > 0 ? z <= end : z >= end; z += step) { const r = on(z, g); if (!r || Math.hypot(r[0] - g[0], r[1] - g[1]) > 3) return; (step > 0 ? pts.unshift(r) : pts.push(r)); g = [r[0], r[1]]; } };
  const m = on(zm, [s.x + .5, s.y + .5]); if (m) { pts.push(m); walk(zm + .5, .5, rayHi.hi + 1, [m[0], m[1]]); walk(zm - .5, -.5, zl, [m[0], m[1]]); }
  else { let g = [s.x + .5, s.y + .5]; for (let z = rayHi.hi + 1; z >= zl; z -= .5) { const r = on(z, g); pts.push(r); if (r) g = [r[0], r[1]]; } }
  let A = null;
  for (const B of pts) {
    if (!B) { A = null; continue; }
    if (A) {   // the cells this piece of the ray goes through, in order
      const d = [0, 1, 2].map((i) => B[i] - A[i]), c = A.map(Math.floor), st = d.map(Math.sign), tD = d.map((v) => (v ? 1 / Math.abs(v) : Infinity)), tM = [0, 1, 2].map((i) => (d[i] ? (st[i] > 0 ? c[i] + 1 - A[i] : A[i] - c[i]) * tD[i] : Infinity));
      for (let n = 0; n < 64; n++) { const i = tM[0] <= tM[1] && tM[0] <= tM[2] ? 0 : tM[1] <= tM[2] ? 1 : 2; if (tM[i] > 1) break; c[i] += st[i]; tM[i] += tD[i];
        const k = solid(c[0], c[1], c[2] + 1); if (k) return {x: c[0], y: c[1], z: c[2] + 2 - k, cz: c[2] + 1, face: FACE[i][st[i] > 0 ? 0 : 1], thing: k === 2}; }   // (a thing: z the level it stands on, as the keys' cursor has it; cz: the cell's top)
    } else if (solid(Math.floor(B[0]), Math.floor(B[1]), Math.floor(B[2]) + 1)) return null;   // (the ray begins inside land: no answer here)
    A = B;
  }
  return null;
}
// THE TILE UNDER THE POINTER -> {x, y, fy: how far down the tile, 0 to 1}, or null: none (the sky): the HD camera's own answer for every px of the land, its tops, its fronts and its sides, the one way back
// from the screen to the world. (Where it had none the classic flat picture's maths answered: a click on the sky was a walk to some tile far north.)
function tileAtScreen(mx, my) {
  if (HdLook.on && Build.on && Build.S.plane === null && Build.S.deep === null) { const h = rayHit(mx, my); if (h) return {x: h.x, y: h.y, fy: .5, z: h.z, cz: h.cz, face: h.face !== "T", side: h.face}; }   // (build mode: the block under the pointer, its top or a side)
  if (HdLook.on) { const q = HdLook.pick(mx, my, Build.on ? (x, y) => Build.level({x, y}) : null); if (q) return q; }   // (the HD camera: the top or the front under the pointer, hd.js; build mode lifted or sunk by E, Q: at the cursor's height)
  return null;
}
cv.addEventListener("mousemove", (e) => {
  if (Math.abs(e.clientX - mouse.x) + Math.abs(e.clientY - mouse.y) > 4) inputMode = "mouse";   // the mouse is back
  mouse.x = e.clientX; mouse.y = e.clientY; mouse.in = true;
  if (drag) {
    const dx = (e.clientX - drag.x) / TS(), dy = (e.clientY - drag.y) / TS();
    if (Math.abs(dx) + Math.abs(dy) > .3) drag.moved = true;
    if (drag.moved && me && Build.on) { const q = tileAtScreen(e.clientX, e.clientY); if (q && (!drag.at || drag.at.x !== q.x || drag.at.y !== q.y)) { drag.at = q; Build.click(q, e.shiftKey); } }   // (a row of plans)
    if (drag.moved && !me) { follow = null; camT.x = cam.x = drag.cx - dx; camT.y = cam.y = drag.cy - dy; }
  }
  const p = tileAtScreen(e.clientX, e.clientY), t = p && tile(p.x, p.y), tip = $("hover");
  if (!t) { tip.style.display = "none"; return; }
  let text;
  if (me && Build.on) Build.point(p);
  if (me && Build.on) { const it = Build.hint(p); text = it ? it.text : ""; tip.className = it && it.ok === false ? "bad" : ""; cv.classList.toggle("act", !!(it && !it.walk && !it.info && it.ok !== false)); }
  else if (me) {      // a left click breaks (X's verb), a right click uses (E's): each line its button's (intent.js clickIntent)
    const L = clickIntent(p, "break").it, R = clickIntent(p, "use").it, does = (it) => !!it && !it.walk && !it.info, said = (it) => does(it) || (!!it && it.ok === false);
    const r = said(R) && (!L || R.text !== L.text) ? R : null;
    text = [said(L) ? L.text : "", r ? `Right click: ${r.text}` : ""].filter(Boolean).join("\n");
    const top = said(L) ? L : r; tip.className = top && top.ok === false ? "bad" : ""; cv.classList.toggle("act", does(L) || does(R));
  }
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
cv.addEventListener("mouseup", (e) => { if (e.button === 0 && drag && !drag.moved && me) { const q = tileAtScreen(e.clientX, e.clientY); if (!q) { /* (the sky: nothing) */ } else if (Build.on) Build.click(q, e.shiftKey); else clickTile(q, "break"); } drag = null; });      // (the left button: X's verb; open ground: walk there)
cv.addEventListener("contextmenu", (e) => { e.preventDefault(); if (!me) return; const q = tileAtScreen(e.clientX, e.clientY); if (!q) return; if (Build.on) Build.click(q, true); else clickTile(q, "use"); });      // (the right one: E's)
