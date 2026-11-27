// The boss bar (#384): while a boss is about (Old Mossback awake, Nyxwing), its name in big letters and its life in a
// thick bar across the top of the screen, nothing boxed behind them. The letters slam down one by one, the bar shoots
// out from the middle and fills; a blow flashes the bit lost, a pale trail drains after it and bits fly off; at half its
// life (Nyxwing's rush, sim/nyxwing.py) everything flashes white and it turns ember, sparks rising off it; when it dies
// the bar shatters and the letters fall away, FELLED comes down in their place. The buttons at the top (the goals, a
// phone's Items, Craft, Talk and Menu) step down under it while it is there (--bossband, style.css).
// Drawn on #bossbar in whole art pixels, as the hearts are (vitals.js pixelCanvas, ui.js hudK); its state is on the
// canvas's dataset (boss, hp, max, phase, state, fill), for the browser tests.

const BOSS_NAME = {mossback: "OLD MOSSBACK", nyxwing: "NYXWING"};
const BB_ROSE = ["#c87c86", "#e8b5ac", "#a8606e"], BB_RAGE = ["#c4473a", "#f08a5c", "#7c2a26"];
const BB_INK = "#3b2a33", BB_WHITE = "#fff8ee", BB_LAG = "#f3d6c4", BB_TROUGH = "#2a1c2a", BB_GOLD = "#e8c35a";
const BB_FELLED = 2100, BB_END = 2400;                    // ms after its death: FELLED goes; the bar is done
const BB = {key: null};
const bbClamp = (v) => Math.max(0, Math.min(1, v));
const bbHash = (n) => { n = Math.sin(n * 127.1 + 311.7) * 43758.5453; return n - Math.floor(n); };

function bossInView() {                                   // the boss to show: awake, the nearest
  const me = myPos(); let best = null, far = Infinity;
  for (const [key, q] of ents) {
    const e = q.e;
    if (!e || !BOSS_NAME[e.kind] || e.act === "sleep" || !WILD[e.kind]) continue;
    const d = me ? Math.hypot(e.x - me.x, e.y - me.y) : 0;
    if (d < far) { far = d; best = [key, e]; }
  }
  return best;
}
function bossDied(e) {                                    // its creature_died (state.js), before it leaves ents
  if (BB.key === e.kind + e.id) BB.dying = true;          // (timed from the next frame, on the frames' own clock)
}
function bbReset() {
  for (const k of Object.keys(BB)) delete BB[k];
  BB.key = null;
  const cv = $("bossbar"); cv.style.display = "none"; cv.dataset.state = "none"; delete cv.dataset.boss;
  document.documentElement.style.setProperty("--bossband", "0px");
}
function bossBar(now) {
  if (BB.dying && !BB.deadAt) { BB.deadAt = now; BB.hits.push({at: now, from: BB.hp, to: 0}); BB.hp = 0; }
  if (!BB.deadAt) {
    const b = bossInView();
    if (!b) { if (BB.key) bbReset(); return; }
    const [key, e] = b;
    if (key !== BB.key) {
      bbReset();
      const max = WILD[e.kind].hp;
      Object.assign(BB, {key, kind: e.kind, max, t0: now, hp: e.hp, hits: [], phaseAt: e.hp * 2 <= max ? now - 1e5 : null});   // (come on it below half: no flash)
    }
    if (e.hp < BB.hp) BB.hits.push({at: now, from: BB.hp, to: e.hp});
    BB.hp = e.hp;
    if (BB.phaseAt === null && BB.hp * 2 <= BB.max) BB.phaseAt = now;
  }
  if (BB.deadAt && now - BB.deadAt > BB_END) return bbReset();
  BB.hits = BB.hits.filter((h) => now - h.at < 1000);
  drawBossBar(now);
}

function drawBossBar(now) {
  const cv = $("bossbar"), dpr = window.devicePixelRatio || 1;
  cv.style.display = "block";
  const SC = Math.max(1, Math.round(hudK * dpr)), NP = Math.max(1, Math.round(SC * 5 / 3));     // device px: an art px; a pixel of the name's letters
  const artW = Math.floor(innerWidth * dpr / SC), W = artW < 400 ? artW - 10 : Math.round(artW * .66);
  const nameH = Math.ceil(9 * NP / SC), by = 2 + nameH + 4, bh = 9, band = by + bh + 3, CW = W + 8, CH = band + 44;
  const [g] = pixelCanvas(cv, CW, CH, SC / dpr);
  document.documentElement.style.setProperty("--bossband", (BB.deadAt && now - BB.deadAt > BB_FELLED ? 0 : band * SC / dpr) + "px");
  const r = (x, y, w, h, c) => { if (w <= 0 || h <= 0) return; g.fillStyle = c; g.fillRect(Math.round(x) * SC, Math.round(y) * SC, Math.round(w) * SC, Math.round(h) * SC); };
  const e = now - BB.t0, x0 = 4, cx = x0 + Math.round(W / 2), max = BB.max, hp = BB.hp, dead = BB.deadAt ? now - BB.deadAt : null;
  const ph = BB.phaseAt !== null && now >= BB.phaseAt, last = BB.hits[BB.hits.length - 1], since = last ? now - last.at : Infinity;
  const flash = (ph && now - BB.phaseAt < 130) || (dead !== null && dead < 260 && (dead / 65 | 0) % 2 === 0);
  const shake = since < 160 && dead === null ? ((since / 40 | 0) % 2 ? 1 : -1) : 0;
  const text = (s, x, y, col) => {                         // in the name's own pixels, outlined an art px
    g.font = `${9 * NP}px SproutPixel`; g.textBaseline = "top";
    g.fillStyle = BB_INK; for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) g.fillText(s, x + dx * SC, y + dy * SC);
    g.fillStyle = col; g.fillText(s, x, y);
  };
  const tw = (s) => { g.font = `${9 * NP}px SproutPixel`; return Math.round(g.measureText(s).width); };
  // the name: each letter slammed down in turn; at its death they fall
  const name = BOSS_NAME[BB.kind], nw = tw(name);
  let ax = cx * SC - Math.round(nw / 2);
  for (let i = 0; i < name.length; i++) {
    const ch = name[i], at = 150 + i * 70, cw = tw(ch);
    if (e >= at && !(dead !== null && dead > BB_FELLED - 900)) {
      const land = e - at < 70;
      let dy = land ? -4 : 0;
      if (dead !== null) { const d = Math.max(0, dead - 300 - i * 45) / 1000; dy += Math.round(30 * d + 260 * d * d); }
      if (dy < CH) text(ch, ax + (ph && dead === null ? 0 : shake * SC), (2 + dy) * SC, flash || land ? BB_WHITE : ph ? "#ffc9a8" : "#fff4dc");
    }
    ax += cw;
  }
  if (ph && dead === null) {                               // two ember pips each side of the name
    const L = Math.round((cx * SC - nw / 2) / SC), R = Math.round((cx * SC + nw / 2) / SC), my = 2 + Math.round(nameH / 2);
    for (const px of [L - 10, L - 16, R + 7, R + 13]) { r(px, my - 1, 3, 3, BB_INK); r(px + 1, my - 2, 1, 5, BB_INK); r(px - 1, my, 5, 1, BB_INK); r(px + 1, my, 1, 1, BB_RAGE[1]); }
  }
  // the bar: out from the middle, then filled; gone in bits when it dies
  const iw = W - 2, fillK = e < 1100 ? 0 : e < 1900 ? bbClamp((e - 1100) / 800) : 1;
  const fill = Math.round(iw * Math.min(fillK, hp / max));
  if (dead === null || dead < 260) {
    const half = Math.round(W / 2 * bbClamp((e - 750) / 350));
    if (half > 0) {
      r(cx - half, by, half * 2, bh, flash ? BB_WHITE : BB_INK); r(cx - half + 1, by + 1, half * 2 - 2, bh - 2, flash ? BB_WHITE : BB_TROUGH);
      if (e < 1120) { r(cx - half, by - 1, 2, bh + 2, BB_WHITE); r(cx + half - 2, by - 1, 2, bh + 2, BB_WHITE); }
    }
    if (!flash && fillK > 0) {
      const cols = ph ? BB_RAGE : BB_ROSE, y = by + 1 + Math.abs(shake), h = bh - 2;
      const lag = BB.hits.reduce((m, h0) => Math.max(m, h0.from - (h0.from - h0.to) * bbClamp((now - h0.at - 350) / 400)), hp);
      if (fillK >= 1) r(x0 + 1 + fill, y, Math.round(iw * lag / max) - fill, h, BB_LAG);
      r(x0 + 1, y, fill, h, cols[0]); r(x0 + 1, y, fill, 1, cols[1]); r(x0 + 1, y + h - 1, fill, 1, cols[2]);
      if (fillK < 1) r(x0 + fill - 1, y, 2, h, BB_WHITE);
      else if (since < 110) r(x0 + 1 + fill, y, Math.round(iw * last.from / max) - fill, h, BB_WHITE);
      if (ph) for (let i = 0; i < 9; i++) {                 // sparks rising off it
        const k = ((now + bbHash(i) * 900) % 900) / 900;
        r(x0 + 1 + Math.round(bbHash(i * 3) * fill), by - Math.round(k * 9), 1, 1, [BB_RAGE[1], BB_GOLD, "#ffd27a"][i % 3]);
      }
    }
  }
  const bits = (at, n, x, y, cols, seed, spread) => {      // pixel bits flying off and falling
    const dt = (now - at) / 1000; if (dt < 0 || dt > 1.2) return;
    for (let i = 0; i < n; i++) {
      const vx = (bbHash(seed + i) - .5) * 70 * spread, vy = -40 - bbHash(seed + i + 50) * 60;
      r(x + vx * dt, y + vy * dt + 130 * dt * dt, 1 + (bbHash(seed + i + 3) > .6), 1 + (bbHash(seed + i + 4) > .7), cols[i % cols.length]);
    }
  };
  for (const h of BB.hits) if (h.to > 0) bits(h.at, 6, x0 + 1 + Math.round(iw * h.to / max), by + 3, ph ? BB_RAGE : BB_ROSE, h.at % 97, .9);
  if (dead !== null) for (let i = 0; i < 8; i++) bits(BB.deadAt + 260, 7, x0 + Math.round(W * (i + .5) / 8), by + 3, [BB_INK, BB_TROUGH, BB_GOLD, BB_WHITE], 300 + i * 11, 1.1);
  if (dead !== null && dead >= 1200 && dead < BB_FELLED) text("FELLED", cx * SC - Math.round(tw("FELLED") / 2), 2 * SC, (dead / 120 | 0) % 2 && dead < 1500 ? BB_WHITE : "#ffd8c0");
  Object.assign(cv.dataset, {boss: BB.kind, hp, max, phase: ph ? 2 : 1, fill, iw, state: dead !== null ? "dead" : e < 1900 ? "enter" : "fight"});
}
