// The vitals on the hotbar: the hearts, the food and the armor round the hearts (ui.js lays the HUD out: hudK).

// Hearts and food sit on the hotbar, ten of each, halves allowed: a heart is a tenth of full health, a piece a tenth
// of full food (state.js: HP_MAX, FOOD_MAX; a part of a half shows as the half). Hearts are the UI pack's small hearts (full,
// half, empty); food is an apple drawn here in the hearts' own palette (plum outline, rose, glint, a leaf; empty is
// the bare outline colour, like an empty heart). Pixel-exact: every art pixel is a whole number of device pixels.
const HEART = [4, 84, 9, 8];                     // full; half and empty are the next 16 px cells along
const APPLE = ["....sg...", "...sgg...", ".aa.s.aa.", "abbabbbba", "abcbbbbba", "abbbbbbba", "abbbbbbda", ".abbbbda.", "..aaaaa.."];
const APPLE_COL = {a: "#664165", b: "#c87c86", c: "#e8b5ac", d: "#a8606e", s: "#7a5236", g: "#7fae5a"};
function pixelCanvas(cv, w, h, k = hudK) {       // sizes a canvas for art w x h at about k CSS px an art pixel
  const SC = Math.max(1, Math.round(k * (window.devicePixelRatio || 1)));
  if (cv.width !== w * SC || cv.height !== h * SC) {
    cv.width = w * SC; cv.height = h * SC;
    cv.style.width = w * SC / (window.devicePixelRatio || 1) + "px"; cv.style.height = h * SC / (window.devicePixelRatio || 1) + "px";
  }
  const g = cv.getContext("2d"); g.imageSmoothingEnabled = false; g.clearRect(0, 0, cv.width, cv.height);
  return [g, SC];
}
function drawIcons(cv, icon, value, gain = 0) {   // gain: food points to preview (what eating would give back)
  const N = 10, hearts = icon === "heart", iw = hearts ? HEART[2] : APPLE[0].length, ih = hearts ? HEART[3] : APPLE.length;
  const one = (hearts ? HP_MAX : FOOD_MAX) / N;                // what an icon is worth
  value = Math.ceil(value / (one / 2) - 1e-9) * (one / 2);
  const step = iw + 1, sig = [icon, value, gain, window.devicePixelRatio || 1, hudK].join();
  if (cv.dataset.sig === sig) return;
  cv.dataset.sig = sig;
  const [g, SC] = pixelCanvas(cv, step * (N - 1) + iw, 9);
  for (let i = 0; i < N; i++) {
    const x = i * step, full = value >= (i + 1) * one, half = !full && value >= i * one + one / 2, top = 9 - ih;
    if (hearts) {
      g.drawImage(IMG.hearts, (full ? 0 : half ? 1 : 2) * 16 + HEART[0], HEART[1], iw, ih, x * SC, top * SC, iw * SC, ih * SC);
      continue;
    }
    const after = value + gain, fullA = after >= (i + 1) * one, halfA = !fullA && after >= i * one + one / 2;
    APPLE.forEach((row, j) => [...row].forEach((c, k) => {
      if (c === ".") return;
      const lit = full || (half && k < 5), soon = !lit && (fullA || (halfA && k < 5));
      g.fillStyle = lit ? APPLE_COL[c] : APPLE_COL.a;
      g.fillRect((x + k) * SC, (top + j) * SC, SC, SC);
      if (soon) { g.globalAlpha = .55; g.fillStyle = APPLE_COL[c]; g.fillRect((x + k) * SC, (top + j) * SC, SC, SC); g.globalAlpha = 1; }
    }));
  }
  cv.classList.toggle("low", value <= one * 2.5);
}
// Holding food: the apples it would give back blink on the bar (every frame, from render; redrawn only on change).
function foodPreview() {
  if (!meObs) return;
  const h = meObs.self.hunger, gain = selected && RULES.food[selected] && h < FOOD_MAX ? RULES.food[selected] : 0;
  drawIcons($("foods"), "food", h, gain && Math.floor(performance.now() / 450) % 2 === 0 ? gain : 0);
}
// Armor: a steel rim round a heart for each 5% of a blow what you wear turns (sim/wear.py armor: at most 45, nine rims),
// half a rim (its left side) for a half, as a heart is halved. A stat, like the hearts' count of what you have: it changes
// when a piece goes on or comes off, never when you are hit. Drawn on #armor, just behind #hearts (style.css): two art
// px round them at the sides and the foot, one over (where the jiggle of low health lifts them), so the hearts' own canvas
// keeps its size, and a heart is drawn over the rims, never a rim over a neighbour.
const ARMOR_STEP = 5, RIM = {top: "#e8eef6", mid: "#aab6c8", low: "#77839b", ink: "#3f4560"};
let rimRings = null;
function heartRims() {                     // the full heart's ring and the ring round that, [x, y, colour] from its top left
  const c = document.createElement("canvas"); c.width = 13; c.height = 12;
  const g = c.getContext("2d"); g.drawImage(IMG.hearts, HEART[0], HEART[1], HEART[2], HEART[3], 2, 2, HEART[2], HEART[3]);
  const d = g.getImageData(0, 0, 13, 12).data, on = (x, y) => x >= 0 && y >= 0 && x < 13 && y < 12 && d[(y * 13 + x) * 4 + 3] > 0;
  const near = (f, x, y, diag) => [[1, 0], [-1, 0], [0, 1], [0, -1], ...(diag ? [[1, 1], [-1, -1], [1, -1], [-1, 1]] : [])].some(([a, b]) => f(x + a, y + b));
  const ring = (x, y) => !on(x, y) && near(on, x, y, false), out = [];
  for (let y = 0; y < 12; y++) for (let x = 0; x < 13; x++) {
    if (ring(x, y)) out.push([x - 2, y - 2, y < 5 ? RIM.top : y < 8 ? RIM.mid : RIM.low]);
    else if (!on(x, y) && near(ring, x, y, true)) out.push([x - 2, y - 2, RIM.ink]);
  }
  return out;
}
function drawArmor(armor) {
  const cv = $("armor"), hearts = $("hearts"), rims = Math.round(armor / ARMOR_STEP * 2) / 2;
  const sig = [rims, window.devicePixelRatio || 1, hudK].join();
  if (cv.dataset.sig === sig) return;
  cv.dataset.sig = sig;
  const [g, SC] = pixelCanvas(cv, 99 + 4, 9 + 3), u = SC / (window.devicePixelRatio || 1);
  cv.style.left = -2 * u + "px"; cv.style.top = -u + "px";          // (art px 0 of #hearts at 2 across, 1 down)
  if (!rimRings) rimRings = heartRims();
  const top = 9 - HEART[3];
  for (let i = 0; i < Math.ceil(rims); i++) {
    for (const [x, y, col] of rimRings) {
      if (rims < i + 1 && x > (HEART[2] - 1) / 2) continue;        // a half: the left side
      g.fillStyle = col; g.fillRect((2 + i * (HEART[2] + 1) + x) * SC, (1 + top + y) * SC, SC, SC);
    }
  }
}
function drawVitals(s) {
  drawIcons($("hearts"), "heart", s.hp);
  drawArmor(s.armor || 0);
  $("armor").classList.toggle("low", $("hearts").classList.contains("low"));      // (lifted with the hearts at low health)
  foodPreview();
  const status = s.hunger <= 0 || (SPRINT_FOOD < 0 && s.hunger < 25) ? `Starving: eat something (${capOf("use")})` : s.hunger <= SPRINT_FOOD ? `Too hungry to sprint: eat something (${capOf("use")})` : "";
  if (walking && walking.run !== sprinting()) syncWalk();          // (fed again, or not enough any more: the sprint follows)
  $("status").textContent = status; $("status").style.display = status ? "block" : "none";
}
