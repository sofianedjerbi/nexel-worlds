// Mouse: hover hints, click to act, drag, zoom.

// =====================================================================================
//  Input
// =====================================================================================
const mouse = {x: 0, y: 0, in: false};
let drag = null;
function tileAtScreen(mx, my) {
  const S = TS(), [ox, oy] = screenOrigin(S);
  return {x: Math.floor((mx - ox) / S), y: Math.floor((my - oy) / S)};
}
cv.addEventListener("mousemove", (e) => {
  if (Math.abs(e.clientX - mouse.x) + Math.abs(e.clientY - mouse.y) > 4) inputMode = "mouse";   // the mouse is back
  mouse.x = e.clientX; mouse.y = e.clientY; mouse.in = true;
  if (drag) {
    const dx = (e.clientX - drag.x) / TS(), dy = (e.clientY - drag.y) / TS();
    if (Math.abs(dx) + Math.abs(dy) > .3) drag.moved = true;
    if (drag.moved && !me) { follow = null; camT.x = cam.x = drag.cx - dx; camT.y = cam.y = drag.cy - dy; }
  }
  const p = tileAtScreen(e.clientX, e.clientY), t = tile(p.x, p.y), tip = $("hover");
  if (!t) { tip.style.display = "none"; return; }
  let text;
  if (me) { const it = intent(aimAt(p, e.shiftKey), e.shiftKey); text = it ? it.text : ""; tip.className = it && it.ok === false ? "bad" : ""; cv.classList.toggle("act", !!(it && !it.walk && !it.info && it.ok !== false)); }
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
cv.addEventListener("mouseup", (e) => { if (e.button === 0 && drag && !drag.moved && me) clickTile(tileAtScreen(e.clientX, e.clientY), e.shiftKey); drag = null; });
cv.addEventListener("contextmenu", (e) => { e.preventDefault(); if (me) clickTile(tileAtScreen(e.clientX, e.clientY), false); });
cv.addEventListener("wheel", (e) => { e.preventDefault(); zoom = Math.max(1, Math.min(6, zoom + (e.deltaY < 0 ? 1 : -1))); }, {passive: false});
