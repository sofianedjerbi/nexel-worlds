// The keys that do something where you look, beside it, in the corner's keycaps. By the build cursor (build.js):
// what Space and X do there at its right; at its left E over Q where it can go up or down (the way they move it),
// how deep it is between them. By what you face, playing by keys: Space and X. They were a list in the bottom
// corner, and each mode said its keys in the chat: "the keys appear in the chat, as a guide in each mode. can't you
// make it more intuitive ??" The corner keeps the rest (keyboard.js: the mode's name, Esc, eat, pick up). Put where
// the thing is on the screen each frame; its words written again only when they change.
const Prompts = (() => {
  const el = document.getElementById("prompts"), part = {};
  let html = "";
  const row = ([k, t, cls]) => `<div class="${cls || ""}"><span class="key">${esc(k)}</span>${esc(t)}</div>`;
  // rect: where the thing is on the screen (css px), or nothing: none shown. side: rows at its right; up, down: a row
  // each at its left, high and low (over it they hid your feet: you stand next to it)
  function show(rect, side = [], up = null, down = null) {
    const h = rect && (side.length || up || down) ? `<div class="side">${side.map(row).join("")}</div><div class="up">${up ? row(up) : ""}</div><div class="down">${down ? row(down) : ""}</div>` : "";
    if (h !== html) { html = h; el.innerHTML = h; for (const k of ["side", "up", "down"]) part[k] = el.querySelector("." + k); }
    if (!h) return;
    const left = Math.round(rect.x - 10), mid = Math.round(rect.y + rect.h / 2);     // (up and down at its left, over and under its middle: the depth goes between, keyhole.js)
    part.side.style.transform = `translate(${Math.round(rect.x + rect.w + 10)}px, ${mid}px) translateY(-50%)`;
    part.up.style.transform = `translate(${left}px, ${mid - 14}px) translate(-100%, -100%)`;
    part.down.style.transform = `translate(${left}px, ${mid + 14}px) translateX(-100%)`;
  }
  // build mode: the cursor's keys (its rows but the mode's name, Esc, and Q E: those go at its left)
  function build() {
    const r = Build.S.rect, ways = Build.ways();
    show(r, Build.rows().filter(([k]) => !["B", "Esc", "Q E"].includes(k)), ways.up ? ["E", "Up"] : null, ways.down ? ["Q", "Down"] : null);
  }
  return {show, build};
})();
