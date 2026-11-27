// Zoom: how many screen pixels an art pixel takes: a whole number of the screen's own px, so the art stays sharp. The
// levels (ZOOM_LEVELS) are 1 to 6, and 2.5 between 2 and 3 where it is whole in the screen's own px (a density of 2: 5 px
// an art px; not at 1, where art px would be 2 and 3 px wide in turn): #401.
// "fix the zooming process. in the game, zooming is hard, uninturitive and ugly". What went wrong: every wheel event was a
// whole level, so one swipe on a trackpad (dozens of events) flew from one end to the other; the picture jumped with
// nothing between two sizes; nothing said where you were or where it stops; and the smallest level made you a few
// pixels tall. Now:
//   - the wheel is counted in distance, not in events: a notch of a mouse wheel is a level, a swipe or a pinch on a
//     trackpad is a level per stretch of it, and never faster than the eye follows;
//   - a level glides into the next (the picture itself grows or shrinks for a moment, then is drawn at its new size);
//   - a small sign shows the levels and where you are; its − and + can be clicked;
//   - a player's view stops at 2 (at 1 you were 16 px tall); a spectator's still goes to 1, to see wide;
//   - the level you chose is kept for the next visit.
const ZOOM = {min: 2, max: 6, ms: 140, to: zoom, busy: false, acc: 0, at: 0, stepped: 0, hide: 0, el: null};
const zoomLeast = () => (me ? ZOOM.min : 1);
const ZOOM_LEVELS = [1, 2, 2.5, 3, 4, 5, 6];
const zoomSharp = (z) => Number.isInteger(z) || Number.isInteger(z * (window.devicePixelRatio || 1));
const zoomLevels = () => ZOOM_LEVELS.filter((z) => z >= zoomLeast() && z <= ZOOM.max && zoomSharp(z));
function zoomStep(from, d) {             // the next level up (d > 0) or down from `from`; none that way: where it is
  const L = zoomLevels();
  return (d > 0 ? L.find((z) => z > from + 1e-9) : L.reverse().find((z) => z < from - 1e-9)) ?? from;
}
{ const z = +localStorage.getItem("nexel-zoom"); if (ZOOM_LEVELS.includes(z)) ZOOM.saved = z; }
// The home screen has its own view, the island at the first level, never zoomed ("do not allow zooming out/in in the
// homescreen, it breaks the view"); the level you chose comes back as you wake up (title.js titleDraw calls this).
function zoomForTitle(open) {
  const q = +new URLSearchParams(location.search).get("zoom"), base = q >= 1 ? q : Math.min(innerWidth, innerHeight) < 520 ? 2 : 3;   // (a phone's first level is 2: touch.js)
  const saved = ZOOM.saved && (zoomSharp(ZOOM.saved) ? ZOOM.saved : Math.round(ZOOM.saved));   // (2.5 kept on another screen: 3 here)
  const want = open ? base : (saved || base);
  if (zoom !== want && !ZOOM.busy) { zoom = ZOOM.to = want; }
}

function zoomBy(d) {
  if (typeof titleOpen === "function" && titleOpen()) return;      // (the home screen is not zoomed)
  if (!ZOOM.busy) ZOOM.to = zoom;
  let to = ZOOM.to;
  for (let i = 0; i < Math.abs(d); i++) to = zoomStep(to, d);         // a level at a time (a view already under the least is left where it is)
  zoomSign(to, to === ZOOM.to);
  if (to === ZOOM.to) return;
  ZOOM.to = to;
  localStorage.setItem("nexel-zoom", to); ZOOM.saved = to;
  if (!ZOOM.busy) zoomLeg();
}
function zoomTo(v) {                     // the menu's slider: the level at v, or the next one in the direction it moves
  const from = ZOOM.busy ? ZOOM.to : zoom, L = zoomLevels(), up = v > from;
  const to = up ? (L.find((z) => z >= v - 1e-9) ?? L[L.length - 1]) : ([...L].reverse().find((z) => z <= v + 1e-9) ?? L[0]);
  const n = L.filter((z) => (up ? z > from + 1e-9 && z <= to : z < from - 1e-9 && z >= to)).length;
  if (n) zoomBy(up ? n : -n);
}
// One level at a time. The canvas is never shown smaller than the window (its edges would show): going in, the picture
// is magnified up to the next size and then drawn at it; going out, it is drawn at the new size first, magnified to
// look as it did, and let down.
function zoomLeg() {
  if (ZOOM.to === zoom) { ZOOM.busy = false; return; }
  ZOOM.busy = true;
  const up = ZOOM.to > zoom, step = zoomStep(zoom, up ? 1 : -1), next = up ? Math.min(step, ZOOM.to) : Math.max(step, ZOOM.to);
  if (!cv.animate || !opt("glide") || LESS_MOTION.matches) { zoom = next; return zoomLeg(); }
  const glide = (a, b, done) => {
    const an = cv.animate([{transform: `scale(${a})`}, {transform: `scale(${b})`}], {duration: ZOOM.ms, easing: "cubic-bezier(.3, .6, .4, 1)", fill: "forwards"});
    // (the HD look's world lies under this one: it glides with it)
    const fx = (HdLook.live && HdView.el ? [HdView.el] : []).map((c) => c.animate([{transform: `scale(${a})`}, {transform: `scale(${b})`}], {duration: ZOOM.ms, easing: "cubic-bezier(.3, .6, .4, 1)", fill: "forwards"}));
    an.onfinish = () => { done(); an.cancel(); fx.forEach((f) => f.cancel()); };      // (finish comes before the frame is drawn: the new size and the plain canvas show together)
  };
  // (the curved world's roll is not magnified with the picture: it is put where the magnified picture has it, and let back: curve.js)
  if (next > zoom) glide(1, next / zoom, () => { Curve.rezoom(next / zoom); zoom = next; zoomLeg(); });
  else { const from = zoom / next; zoom = next; Curve.rezoom(1 / from); glide(from, 1, zoomLeg); }
}
// The wheel. A mouse wheel sends one event of about 100 px a notch; a trackpad sends dozens of small ones for one
// swipe, and goes on sending while the swipe dies away; a pinch on a trackpad is a wheel with Ctrl held, in small steps.
cv.addEventListener("wheel", (e) => {
  e.preventDefault();
  const now = performance.now(), px = e.deltaY * (e.deltaMode === 1 ? 33 : e.deltaMode === 2 ? 300 : 1) * (e.ctrlKey ? 6 : 1);
  if (now - ZOOM.at > 220 || Math.sign(px) !== Math.sign(ZOOM.acc)) ZOOM.acc = 0;           // a new gesture, or it turned round
  ZOOM.at = now; ZOOM.acc += px;
  const notch = Math.abs(px) >= 50;                                                        // a mouse wheel: each notch counts
  if (Math.abs(ZOOM.acc) < (notch ? 50 : 90) || now - ZOOM.stepped < (notch ? 60 : 200)) return;
  zoomBy(ZOOM.acc < 0 ? 1 : -1);
  ZOOM.acc = 0; ZOOM.stepped = now;
}, {passive: false});

// The keys. "qwerty -+ does not work. you use the numpad ones ? ppl dont always have numpads": the key that types - or
// the one that types = or + (with or without Shift), whatever the layout; failing that, the two keys right of 0 where
// a QWERTY keyboard has them, and the numpad's. Also when you only watch (the game's other keys wait for a player).
addEventListener("keydown", (e) => {
  const el = document.activeElement;
  if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || (el && /^(INPUT|TEXTAREA)$/.test(el.tagName))) return;   // (Ctrl or Cmd with + is the browser's own zoom)
  if (/^Digit/.test(e.code)) return;      // (the bar's numbers, by place: an AZERTY's 6 types -, its 8 _; there the two keys right of 0 zoom)
  const d = e.key === "+" || e.key === "=" ? 1 : e.key === "-" || e.key === "_" ? -1 : {Equal: 1, NumpadAdd: 1, Minus: -1, NumpadSubtract: -1}[e.code] || 0;
  if (d) { e.preventDefault(); zoomBy(d); }
});

// The sign: − ▪▪▪▫▫ +, shown in the middle just over the hearts while you zoom and a moment after; it nods at an end.
function zoomSign(level, stuck) {
  if (!ZOOM.el) {
    ZOOM.el = document.createElement("div"); ZOOM.el.id = "zoomer";
    ZOOM.el.innerHTML = "<b data-d='-1'>−</b><span></span><b data-d='1'>+</b>";
    document.body.appendChild(ZOOM.el);
    ZOOM.el.addEventListener("pointerdown", (e) => { e.preventDefault(); e.stopPropagation(); if (e.target.dataset.d) zoomBy(+e.target.dataset.d); });
  }
  const lo = Math.min(zoomLeast(), level), el = ZOOM.el;
  el.querySelector("span").innerHTML = [...new Set([lo, ...zoomLevels()])].filter((z) => z >= lo).map((z) => `<i class="${z <= level ? "on" : ""}"></i>`).join("");
  el.querySelector("[data-d='-1']").classList.toggle("end", level <= lo);
  el.querySelector("[data-d='1']").classList.toggle("end", level >= ZOOM.max);
  const hud = $("vitals").getBoundingClientRect();           // "the zoom indicator show up at a weird spot" (not half way up the right edge): over your bar, under you
  el.style.bottom = (hud.height ? innerHeight - hud.top + 10 : 16) + "px";
  el.classList.add("show");
  if (stuck) { el.classList.remove("nod"); void el.offsetWidth; el.classList.add("nod"); }
  clearTimeout(ZOOM.hide);
  ZOOM.hide = setTimeout(() => el.classList.remove("show"), 1800);
}
