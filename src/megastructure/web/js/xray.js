// Behind a wall or a mountain you'd be hidden (relief.js: clipBehind). Instead, a circle round you is seen through it:
// where rock is drawn over ground you could be on (your height, a step up, or lower), that ground shows instead, with
// its water, you, and who and what is there. Rock is what stands two layers or more over you. Nothing else changes:
// a pixel that shows such ground already, rock that hides none, everything outside the circle stay exactly as they
// are drawn. It fades out toward its edge, comes and goes softly, and is only for you. Painted small (art px, a few
// tiles) every frame.

// r, core: its radius (tiles) and the part of it that's clear. It comes when you're really hidden, not for an edge
// that hides your legs or a post you walk past: body: your height over the foot of your tile (art px); from, full: the
// share of you that's hidden where it starts and where it is whole (a ledge a layer high in front of you hides you
// to the waist: nothing; two layers leave your ears: the circle); wait: seconds hidden before it comes
const XRAY = {r: 3.1, core: .42, body: 20, from: .7, full: .8, wait: .15, far: 12};   // (far: tiles south to look for ground drawn up over you)
const xray = {a: 0, L: 0, row: 0, x: 0, y: 0, c: null, m: null, t: 0};   // how strong, the height you stand at, your row, its centre (tiles), its two pictures, how long you've been hidden

// Ground you could be on, from where you stand: your height, a step up (a jump), anything lower. The rest is rock.
const xrayOpen = (tx, ty) => levelAt(tx, ty) <= xray.L + 1;
// How clear the circle is at a spot as drawn (tiles, lifted with its ground): 0 the land as it is, 1 seen through
function xrayAt(x, y) {
  if (xray.a <= .01) return 0;
  const d = Math.hypot(x - xray.x, y - xray.y) / XRAY.r;
  return xray.a * smooth(Math.max(0, Math.min(1, (1 - d) / (1 - XRAY.core))));
}
const xrayOn = (tx, ty) => xrayAt(tx, ty - shOf(levelAt(tx, ty)) / 16);      // ...at what stands on a tile
// What stands on a tile is in the way: on rock in front of you (south), drawn up over ground the circle shows.
// -> how much it fades (0: it stays: nothing is hidden behind it)
function xrayOver(tx, ty) {
  if (xray.a <= .01 || ty <= xray.row || xrayOpen(tx, ty)) return 0;
  const r = Math.round(ty - (levelAt(tx, ty) - xray.L) / 2);                 // the row, at your height, that it is drawn over
  return xrayOpen(tx, r) || xrayOpen(tx, r - 1) ? xrayOn(tx, ty) : 0;
}
// Someone in the circle: 1 on the hidden ground with you (drawn whole, not cut at the hill's edge), -1 standing in
// the way (not drawn), 0 neither
function xraySees(p) {
  const tx = Math.round(p.x), ty = Math.round(p.y);
  if (xray.a <= .01) return 0;
  return xrayOver(tx, ty) >= .3 ? -1 : xrayOpen(tx, ty) && xrayOn(tx, ty) >= .3 ? 1 : 0;
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
  if (xray.a < .01 && !want && xray.a) { xray.a = 0; for (const b of blocks.values()) b.rock = b.rockGen = null; }   // (gone: the rock pictures with it)
}

// The circle itself, over the land and under everything standing on it. Two small pictures, the size of the circle:
// the rock in it exactly as it is drawn (relief.js: rockOf, the land's own shapes: rounded edges, ledges, walls), and
// the ground you could be on, painted plainly. The ground is kept only where the rock is: a pixel that already shows
// that ground is never touched.
function drawXray(vis, sx, sy) {
  if (xray.a <= .01) return;
  const D = Math.ceil(XRAY.r * 32) + 2, L = xray.L, lift = shOf(L), n = B * 16;
  if (!xray.c) for (const k of ["c", "m"]) { xray[k] = document.createElement("canvas"); xray[k].width = xray[k].height = D; }
  const g = xray.c.getContext("2d"), m = xray.m.getContext("2d");
  const cx = xray.x * 16 + 8, cy = xray.y * 16 + 8, ax = Math.round(cx - D / 2), ay = Math.round(cy - D / 2);
  m.clearRect(0, 0, D, D);
  let any = false;
  for (const b of vis) {                                                      // the rock, from two layers over where you stand
    const rel = b.relief; if (!rel || rel.maxLv < L + 2) continue;
    const X = b.bx * n - ax, Y = b.by * n - rel.up - ay;
    if (X >= D || Y >= D || X + n <= 0 || Y + n + rel.up - shOf(rel.minLv) <= 0) continue;
    const rock = rockOf(b, L + 2);
    if (!rock) { xray.a = Math.min(xray.a, .011); return; }                   // (being worked out: the circle waits for it)
    m.drawImage(rock, X, Y); any = true;
  }
  if (!any) return;
  const x0 = Math.floor(ax / 16) - 1, x1 = Math.floor((ax + D) / 16) + 1, y0 = Math.floor((ay + lift) / 16) - 6, y1 = Math.floor((ay + D + lift) / 16) + 1;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = "source-over"; g.globalAlpha = 1; g.clearRect(0, 0, D, D);
  g.imageSmoothingEnabled = false;
  for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {     // the ground, from the back: each tile at its height
    const t = tileIdx(tx, ty); if (!t || !t[0].canvas || !xrayOpen(tx, ty)) continue;
    const lv = levelAt(tx, ty), X = tx * 16 - ax, Y = ty * 16 - shOf(lv) - ay, i = t[1];
    if (waterView && lv === 0) {                                              // water there, and under a shore's edge (water.js: as it is on screen)
      const wx = tx * 16 - waterView.x, wy = ty * 16 - waterView.y;
      if (wx >= 0 && wy >= 0 && wx + 16 <= waterCv.width && wy + 16 <= waterCv.height) g.drawImage(waterCv, wx, wy, 16, 16, X, Y, 16, 16);
    }
    g.drawImage(t[0].canvas, (i % B) * 16, (i / B | 0) * 16, 16, 16, X, Y, 16, 16);
    for (let k = lv, below = xrayOpen(tx, ty + 1) ? levelAt(tx, ty + 1) : lv; k > below; k--) {   // its wall down to lower ground in front (a band a layer, as relief.js paints them)
      const c = colsOf(hillSheet(k)).bands, yk = Y + 16 + (lv - k) * RELIEF_STEP;
      g.fillStyle = `rgb(${c[1].map(Math.round)})`; g.fillRect(X, yk, 16, RELIEF_STEP);
      g.fillStyle = `rgb(${c[0].slice(0, 3).map(Math.round)})`; g.fillRect(X, yk, 16, 1);
      g.fillStyle = `rgb(${c[2].slice(0, 3).map(Math.round)})`; g.fillRect(X, yk + RELIEF_STEP - 1, 16, 1);
    }
  }
  g.globalCompositeOperation = "destination-in"; g.drawImage(xray.m, 0, 0);  // ...only where the rock is drawn over it
  const R = XRAY.r * 16, fade = g.createRadialGradient(cx - ax, cy - ay, R * XRAY.core, cx - ax, cy - ay, R);
  [1, .8, .6, .4, .2, 0].forEach((v, i, all) => {                             // (in steps, as pixel art fades: rings, not a blur)
    fade.addColorStop(i / all.length, `rgba(0,0,0,${v})`); fade.addColorStop(Math.min(1, (i + 1) / all.length), `rgba(0,0,0,${v})`);
  });
  g.fillStyle = fade; g.fillRect(0, 0, D, D);
  ctx.globalAlpha = xray.a;
  ctx.drawImage(xray.c, Math.round(sx(0) + ax * zoom), Math.round(sy(0) + ay * zoom), D * zoom, D * zoom);
  ctx.globalAlpha = 1;
}
