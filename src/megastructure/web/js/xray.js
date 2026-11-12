// Behind a wall or a mountain you'd be hidden (relief.js: clipBehind). Instead, a circle round you is seen through it:
// the higher ground in front of you (south) is cut down to the height you stand at, its footprint dimmed and outlined
// (it is still a wall), and what is behind shows: you, the ground you walk on, who and what is there. It fades out
// toward its edge, and comes and goes softly. Only where the hill really is in the way (the rest of the screen is
// the land as drawn), and only for you. Painted small (art px, a few tiles), every frame: nothing is rebuilt or kept.

// r, core: its radius (tiles) and the part of it that's clear. It comes when you're really hidden, not for an edge
// that hides your feet or a post you walk past: body: your height (art px); from, full: the share of you that's
// hidden where it starts and where it is whole (a wall two layers high in front of you leaves your head: nothing; three
// hides you: the circle); wait: seconds hidden before it comes
const XRAY = {r: 3.1, core: .42, body: 22, from: .75, full: .95, wait: .15, far: 12};   // (far: tiles south to look for ground drawn up over you)
const xray = {a: 0, L: 0, row: 0, x: 0, y: 0, c: null, t: 0};   // how strong, the height and row it cuts from, its centre (tiles), how long you've been hidden

// The ground in front of you that is in the way: south of your row, higher than you stand
const xrayCut = (tx, ty) => xray.a > .01 && ty > xray.row && levelAt(tx, ty) > xray.L;
// How clear the circle is at a spot as drawn (tiles, lifted with its ground): 0 the land as it is, 1 seen through
function xrayAt(x, y) {
  if (xray.a <= .01) return 0;
  const d = Math.hypot(x - xray.x, y - xray.y) / XRAY.r;
  return xray.a * smooth(Math.max(0, Math.min(1, (1 - d) / (1 - XRAY.core))));
}
const xrayOn = (tx, ty) => xrayAt(tx, ty - shOf(levelAt(tx, ty)) / 16);      // ...at what stands on a tile
// Someone in the circle: 1 behind the hill with you (drawn whole, not cut at its edge), -1 standing on the ground
// that's seen through (not drawn), 0 neither
function xraySees(p) {
  const tx = Math.round(p.x), ty = Math.round(p.y);
  return xrayOn(tx, ty) < .3 ? 0 : xrayCut(tx, ty) ? -1 : 1;
}

// Once a frame, before anything of it is drawn: are you behind something, and how much of you
function xrayLook(dt) {
  const p = me && ents.get("agent" + myId);
  let want = 0;
  if (p && p.e && !caveOpen) {
    const L = Math.min(standAt(Math.floor(p.x), Math.floor(p.y)), standAt(Math.ceil(p.x), Math.ceil(p.y))), row = Math.floor(p.y + .001);
    let hidden = 0;                                        // the share of you under the top edge of the ground in front: the two
    const f = p.x - Math.floor(p.x);                       //  columns you stand across, each for the part of you in it
    for (const [tx, part] of [[Math.floor(p.x), 1 - f], [Math.floor(p.x) + 1, f]]) {
      let cover = 0;
      if (part > .001) for (let ty = row + 1; ty <= row + XRAY.far; ty++) cover = Math.max(cover, (levelAt(tx, ty) - L) * RELIEF_STEP - (ty - p.y - 1) * 16);
      hidden += part * Math.min(1, cover / XRAY.body);
    }
    want = Math.max(0, Math.min(1, (hidden - XRAY.from) / (XRAY.full - XRAY.from)));
    xray.t = want > 0 ? xray.t + dt : 0;
    if (xray.t < XRAY.wait && xray.a <= .01) want = 0;      // (a moment behind something: not yet)
    if (want > 0 || xray.a > .01) { xray.L = L; xray.row = row; xray.x = p.x; xray.y = p.y - shOf(L) / 16 - .5; }   // (its centre: your body, where it is drawn)
  }
  xray.a += (want - xray.a) * (1 - Math.exp(-dt / .09));
  if (xray.a < .01 && !want) xray.a = 0;
}

// The circle itself, over the land and under everything standing on it
function drawXray(sx, sy) {
  if (xray.a <= .01) return;
  const D = Math.ceil(XRAY.r * 32) + 2, L = xray.L, lift = shOf(L);
  if (!xray.c) { xray.c = document.createElement("canvas"); xray.c.width = xray.c.height = D; }
  const g = xray.c.getContext("2d"), cx = xray.x * 16 + 8, cy = xray.y * 16 + 8, ax = Math.round(cx - D / 2), ay = Math.round(cy - D / 2);
  const x0 = Math.floor(ax / 16) - 1, x1 = Math.floor((ax + D) / 16) + 1, y0 = xray.row - 6, y1 = Math.floor((ay + D + lift) / 16) + 1;
  const lvOf = (tx, ty) => (xrayCut(tx, ty) ? L : levelAt(tx, ty));          // the land with what's in the way cut down
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = "source-over"; g.globalAlpha = 1; g.clearRect(0, 0, D, D);
  g.save(); g.beginPath();                                                    // only where the hill is drawn over what's behind it
  let any = false;
  // (as far south as high ground is drawn up into the circle: a plateau 12 layers high is, from 6 tiles further on)
  for (let ty = xray.row + 1; ty <= y1 + XRAY.far; ty++) for (let tx = x0; tx <= x1; tx++) if (xrayCut(tx, ty)) {
    const top = ty * 16 - shOf(levelAt(tx, ty)) - ay;
    if (top >= D) continue;
    g.rect(tx * 16 - ax - 8, top, 32, ty * 16 + 16 - lift - ay - top); any = true;
  }
  if (!any) { g.restore(); return; }
  g.clip(); g.imageSmoothingEnabled = false;
  for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {     // from the back: each tile at its height, its wall under it
    const t = tileIdx(tx, ty); if (!t || !t[0].canvas) continue;
    const lv = lvOf(tx, ty), X = tx * 16 - ax, Y = ty * 16 - shOf(lv) - ay, i = t[1];
    if (waterView && lv === 0) {                                              // water there, and under a shore's edge (water.js: as it is on screen)
      const wx = tx * 16 - waterView.x, wy = ty * 16 - waterView.y;
      if (wx >= 0 && wy >= 0 && wx + 16 <= waterCv.width && wy + 16 <= waterCv.height) g.drawImage(waterCv, wx, wy, 16, 16, X, Y, 16, 16);
    }
    g.drawImage(t[0].canvas, (i % B) * 16, (i / B | 0) * 16, 16, 16, X, Y, 16, 16);
    for (let k = lv, below = lvOf(tx, ty + 1); k > below; k--) {              // (a band a layer, as relief.js paints them)
      const c = colsOf(hillSheet(k)).bands, yk = Y + 16 + (lv - k) * RELIEF_STEP;
      g.fillStyle = `rgb(${c[1].map(Math.round)})`; g.fillRect(X, yk, 16, RELIEF_STEP);
      g.fillStyle = `rgb(${c[0].slice(0, 3).map(Math.round)})`; g.fillRect(X, yk, 16, 1);
      g.fillStyle = `rgb(${c[2].slice(0, 3).map(Math.round)})`; g.fillRect(X, yk + RELIEF_STEP - 1, 16, 1);
    }
    if (!xrayCut(tx, ty)) continue;
    // the hill, cut: its earth (the colour of its own walls); a layer up (a step you can jump) is only shaded
    const high = levelAt(tx, ty) > L + 1, e = colsOf(hillSheet(L + 2)).bands[1];
    g.fillStyle = high ? `rgba(${e.map(Math.round)},.9)` : "rgba(60,40,30,.28)"; g.fillRect(X, Y, 16, 16);
    g.fillStyle = high ? "rgba(46,28,24,.9)" : "rgba(46,28,24,.5)";           // its outline, where the ground beside it is open
    if (!xrayCut(tx, ty - 1)) g.fillRect(X, Y, 16, 1);
    if (!xrayCut(tx - 1, ty)) g.fillRect(X, Y, 1, 16);
    if (!xrayCut(tx + 1, ty)) g.fillRect(X + 15, Y, 1, 16);
    if (!xrayCut(tx, ty + 1)) g.fillRect(X, Y + 15, 16, 1);
  }
  g.restore();
  const R = XRAY.r * 16, fade = g.createRadialGradient(cx - ax, cy - ay, R * XRAY.core, cx - ax, cy - ay, R);
  [1, .8, .6, .4, .2, 0].forEach((v, i, all) => {                             // (in steps, as pixel art fades: rings, not a blur)
    fade.addColorStop(i / all.length, `rgba(0,0,0,${v})`); fade.addColorStop(Math.min(1, (i + 1) / all.length), `rgba(0,0,0,${v})`);
  });
  g.globalCompositeOperation = "destination-in"; g.fillStyle = fade; g.fillRect(0, 0, D, D);
  ctx.globalAlpha = xray.a;
  ctx.drawImage(xray.c, Math.round(sx(0) + ax * zoom), Math.round(sy(0) + ay * zoom), D * zoom, D * zoom);
  ctx.globalAlpha = 1;
}
