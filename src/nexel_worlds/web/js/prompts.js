// The keys that do something where you look, beside it, in the corner's keycaps. By the build cursor (build.js):
// what Space and X do there at its right; at its left E over Q where it can go up or down (the way they move it),
// how deep it is between them. By what you face, playing by keys: E and X. Not a list in the bottom
// corner, nor each mode saying its keys in the chat: "the keys appear in the chat, as a guide in each mode. can't you
// make it more intuitive ??" The corner keeps the rest (keyboard.js: the mode's name, Esc, eat, pick up). Put where
// the thing is on the screen each frame; its words written again only when they change.
const Prompts = (() => {
  const el = document.getElementById("prompts"), part = {};
  let html = "";
  const row = ([k, t, cls]) => `<div class="${cls || ""}"><span class="key">${esc(k)}</span>${esc(t)}</div>`;
  // rect: where the thing is on the screen (css px), or nothing: none shown. side: rows at its right; up, down: a row
  // each at its left, high and low (over it they hid your feet: you stand next to it)
  // (rect.under: the rows under it, not at its right; rect.right: up and down at its right, not at its left: you stand there, and what marks the block's height on you is not written over)
  // Nothing is written on you or on your name (`keep`: your body and your name on the screen, characters.js; facing west the rows lay across your face, and at both ends of the zoom),
  // nor on another part (Q's row lay on Space's, under the build cursor): each part's size is measured when its words change, and the rows take the first of their places that is free:
  // at its right, under it, at its left, over it (and the last two again, ending at its right edge).
  let keep = null, size = {};
  const hit = (a, b) => Array.isArray(b) ? b.some((c) => hit(a, c)) : !!a && !!b && a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  function show(rect, side = [], up = null, down = null) {
    const h = rect && (side.length || up || down) ? `<div class="side">${side.map(row).join("")}</div><div class="up">${up ? row(up) : ""}</div><div class="down">${down ? row(down) : ""}</div>` : "";
    if (h !== html) { html = h; el.innerHTML = h; for (const k of ["side", "up", "down"]) { part[k] = el.querySelector("." + k); size[k] = part[k] ? [part[k].offsetWidth, part[k].offsetHeight] : [0, 0]; } }
    if (!h) return;
    const R = Math.round, mid = R(rect.y + rect.h / 2), [sw, sh] = size.side, box = (k, x, y) => size[k][0] ? {x, y, w: size[k][0], h: size[k][1]} : null;
    const lx = (k, right) => right ? R(rect.x + rect.w + 10) : R(rect.x - 10) - size[k][0];     // (up and down at its left, over and under its middle: the depth goes between, keyhole.js)
    const ud = (r) => [box("up", lx("up", r), mid - 14 - size.up[1]), box("down", lx("down", r), mid + 14)], bad = (q) => hit(q[0], keep) || hit(q[1], keep);
    let onRight = !!rect.right, [U, D] = ud(onRight);
    if (bad([U, D])) { const o = ud(!onRight); if (!bad(o)) [U, D] = o; else for (const b of [U, D]) for (const k of keep || []) if (hit(b, k)) b.x = onRight ? R(k.x + k.w + 6) : R(k.x - 6) - b.w; }   // (on you both ways, the cursor on your own tile: out past your name)
    const ux = R(rect.x - 4), lx2 = R(rect.x + rect.w + 4) - sw, clear = (x, y) => { let v = R(y); const b = {x, y: v, w: sw, h: sh}; if (hit(b, D)) v = D.y + D.h + 4; return v; };   // (under it: under Q's row too)
    const high = (x) => { let v = R(rect.y - 12) - sh; if (hit({x, y: v, w: sw, h: sh}, U)) v = U.y - 4 - sh; return v; };
    const at = {right: [R(rect.x + rect.w + 10), mid - R(sh / 2)], under: [ux, clear(ux, rect.y + rect.h + 12)], left: [R(rect.x - 10) - sw, mid - R(sh / 2)], over: [ux, high(ux)], underL: [lx2, clear(lx2, rect.y + rect.h + 12)], overL: [lx2, high(lx2)]};
    let S = null;
    for (const k of rect.under ? ["under", "right", "left", "over", "underL", "overL"] : ["right", "under", "left", "over", "underL", "overL"]) { const b = {x: at[k][0], y: at[k][1], w: sw, h: sh}; if (!S) S = b; if (!hit(b, keep) && !hit(b, U) && !hit(b, D)) { S = b; break; } }
    part.side.style.transform = `translate(${S.x}px, ${S.y}px)`;
    if (U) part.up.style.transform = `translate(${U.x}px, ${U.y}px)`;
    if (D) part.down.style.transform = `translate(${D.x}px, ${D.y}px)`;
  }
  // build mode: the cursor's keys (its rows but the mode's name, Esc, and Q E: those go at its left)
  function build() {
    const r = Build.S.rect, ways = Build.ways();
    BuildGhost.paint();      // (a block of the land in hand: its ghost where it will go, what X will take: buildghost.js)
    show(r, Build.rows().filter(([k]) => ![capOf("build"), "B", "Esc", Build.LAYER_CAP()].includes(k)), ways.up ? ["E", "Up"] : null, ways.down ? [keyCap("keyq"), "Down"] : null);
  }
  return {show, build, set keep(v) { keep = v; }, get keep() { return keep; }};
})();
