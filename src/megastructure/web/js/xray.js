// Behind a wall or a mountain you'd be hidden (behind.js: clipBehind). Instead, a circle round you is seen through
// it. The rule is one: inside the circle the land is drawn without the rock in front of you, and nothing else
// changes. The rock in front: what stands two layers or more over you, south of your row. The land without it is
// painted by the land's own painter (relief.js: reliefSteps), the few tiles round you, every shape and colour as it
// is with the rock there: the ground you stand on with its water, the cliff behind you down to its foot, a step, a
// ledge. Of that picture only what the rock is drawn over is put on the screen: ground that shows anyway is never
// touched, and where there is only the rock's own inside to see (where it stands, where it joins a hill beside you),
// the rock stays as it is drawn. What stands on that rock in the way (a tree, a creature, things lying there) fades
// with it; who is on the ground behind it shows through it. It fades out toward its edge, comes and goes softly, and
// is only for you. Painted again when you step onto another tile or the land changes, not each frame.

// r, core: its radius (tiles) and the part of it that's clear. It comes when you're really hidden, not for an edge
// that hides your legs or a post you walk past: body: your height, feet to ears (art px; your feet are 2 + STAND over
// the foot of your tile: relief.js); from, full: the share of you that's hidden where it starts and where it is whole
// (a ledge a layer high in front of you hides your legs: nothing; two layers leave the top of your head: the circle);
// wait: seconds hidden before it comes; far: tiles south to look for ground drawn up over you; box: tiles across
// that are painted (the circle, wherever you are on your tile); ms: a frame's share of painting it; turn: seconds a new picture takes to come over the one before; whole (tests): no rock is left out and all of the
// picture is shown: it must then be the land's own, to the pixel
const XRAY = {r: 3.1, core: .42, body: 18, from: .5, full: .6, wait: .15, far: 12, box: 9, ms: 2.5, turn: .12, whole: false};
// how strong, the height you stand at, your row, its centre (tiles), its canvas, how long you've been hidden, the land
// without the rock (pic), the next one being painted (job), the one before (old) and how far pic has come over it (mix)
const xray = {a: 0, L: 0, row: 0, x: 0, y: 0, c: null, c2: null, t: 0, pic: null, job: null, old: null, mix: 1};

// The rock that is seen through
const xrayRock = (tx, ty) => ty > xray.row && levelAt(tx, ty) >= xray.L + 2 && !XRAY.whole;
// How clear the circle is at a spot as drawn (tiles, lifted with its ground): 0 the land as it is, 1 seen through
function xrayAt(x, y) {
  if (xray.a <= .01) return 0;
  const d = Math.hypot(x - xray.x, y - xray.y) / XRAY.r;
  return xray.a * smooth(Math.max(0, Math.min(1, (1 - d) / (1 - XRAY.core))));
}
const xrayOn = (tx, ty) => xrayAt(tx, ty - shOf(levelAt(tx, ty)) / 16);      // ...at what stands on a tile
// What stands on the rock seen through is in the way where something shows behind it (its tile as drawn, and the one
// over that: a tree is tall). -> how much it fades (0: it stays: nothing is seen behind it)
function xrayOver(tx, ty) {
  const P = xray.pic;
  if (xray.a <= .01 || !P || !xrayRock(tx, ty)) return 0;
  const X = tx * 16 - P.x, Y = ty * 16 - shOf(levelAt(tx, ty)) - P.y;
  for (let y = Math.max(0, Y - 16); y < Math.min(P.h, Y + 16); y += 2) for (let x = Math.max(0, X); x < Math.min(P.w, X + 16); x += 2) if (P.seen[y * P.w + x]) return xrayOn(tx, ty);
  return 0;
}
// Someone on the ground behind that rock: how clearly they show through it (0: hidden as ever, 1: whole)
const xrayShows = (p) => (xrayRock(Math.round(p.x), Math.round(p.y)) ? 0 : xrayOn(Math.round(p.x), Math.round(p.y)));

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
      hidden += part * Math.max(0, Math.min(1, (cover - 2 - STAND) / XRAY.body));
    }
    want = Math.max(0, Math.min(1, (hidden - XRAY.from) / (XRAY.full - XRAY.from)));
    xray.t = want > 0 ? xray.t + dt : 0;
    if (xray.t < XRAY.wait && xray.a <= .01) want = 0;      // (a moment behind something: not yet)
    if (xray.t > 0 || xray.a > .01) {
      xray.L = L; xray.row = row; xray.x = p.x; xray.y = p.y - shOf(L) / 16 - .5 - UP;   // (its centre: your body, where it is drawn)
      if (!xrayPaint(Math.round(p.x)) && xray.a <= .01) want = 0;              // (it comes once its picture is ready)
    }
  }
  xray.a += (want - xray.a) * (1 - Math.exp(-dt / .09));
  xray.mix = XRAY.turn ? Math.min(1, xray.mix + dt / XRAY.turn) : 1;
  if (xray.mix >= 1 || xray.a <= .01) xray.old = null;
  if (xray.a < .01 && !want) xray.a = 0;
}

// The land without the rock in front, round the tile you're on: painted when that tile, your height or the land
// changes, a few ms a frame (XRAY.ms): until it is ready the one before stays, which is right a tile further along
// a wall, and a row late for a moment when you step toward it or away. -> is the picture the one for where you are?
function xrayPaint(tx) {
  const near = [];                                          // the blocks it can take tiles from, and what they have of the land
  for (let by = Math.floor((xray.row - 14) / B); by <= Math.floor((xray.row + 14) / B); by++) for (let bx = Math.floor((tx - 5) / B); bx <= Math.floor((tx + 5) / B); bx++) {
    const b = blocks.get(bkey(bx, by)); if (b && b.px) near.push(b);
  }
  const key = [tx, xray.row, xray.L, XRAY.whole, ...near.map((b) => b.bx + ":" + b.by + ":" + (b.ver || 0))].join();
  if (xray.pic && xray.pic.key === key) { xray.job = null; return true; }
  if (!xray.job || xray.job.key !== key) xray.job = {key, steps: xrayPicture(tx, key, near)};
  const t0 = performance.now();
  let r = xray.job.steps.next(); while (!r.done && performance.now() - t0 < XRAY.ms) r = xray.job.steps.next();
  if (r.done) {                                             // (a step toward the rock or away changes what is seen through by a row of it: the new picture comes over the old, not at once)
    if (xray.a > .01 && xray.pic) { xray.old = xray.pic; xray.mix = 0; }
    xray.pic = r.value; xray.job = null;
  }
  return r.done;
}
function* xrayPicture(tx, key, near) {
  const D = Math.ceil(XRAY.r * 32) + 2, w = XRAY.box, W = w * 16, h = D + 22, y = xray.row * 16 - shOf(xray.L) - (D >> 1) - 6;   // (its rows on the screen, in art px: the circle's, wherever you are on your tile)
  let lo = 99, hi = -99;
  for (let ty = xray.row - 14; ty <= xray.row + 14; ty++) for (let x = tx - 5; x <= tx + 5; x++) { const l = levelAt(x, ty); lo = Math.min(lo, l); hi = Math.max(hi, l); }
  const y0 = Math.max(xray.row - 14, (y + shOf(lo) >> 4) - 1), y1 = Math.min(xray.row + 14, y + h + shOf(hi) >> 4);   // every row of tiles that can be drawn in it
  const R = {x: tx - (w >> 1), y: y0, w, h: y1 - y0 + 1}, gh = R.h * 16, ground = new Uint32Array(W * gh);   // (its ground: the blocks' own px, tiles.js)
  const row = xray.row, L = xray.L, rock = (x, ty) => ty > row && levelAt(x, ty) >= L + 2 && !XRAY.whole;   // (the rock seen through, from where you were when this was started)
  for (const b of near) {
    const bx = (b.bx * B - R.x) * 16, by = (b.by * B - R.y) * 16, x0 = Math.max(0, bx), x1 = Math.min(W, bx + BW);
    if (x1 > x0) for (let yy = Math.max(0, by); yy < Math.min(gh, by + BW); yy++) ground.set(b.px.subarray((yy - by) * BW + x0 - bx, (yy - by) * BW + x1 - bx), yy * W + x0);
  }
  const see = {keep: new Uint8Array((w + 4) * (R.h + 4)), c0: y - R.y * 16, c1: y - R.y * 16 + h, state: new Uint8Array(W * h), cover: new Uint8Array(W * h), wet: new Uint8Array(W * h)};
  for (let j = -2; j < R.h + 2; j++) for (let i = -2; i < w + 2; i++) see.keep[(j + 2) * (w + 4) + i + 2] = rock(R.x + i, R.y + j) ? 0 : 1;
  see.base = (R, put, lift, minLv) => {                    // the ground itself, each tile kept at the lowest level (water shows through it at the sea's)
    for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) {
      const keep = see.keep[(j + 2) * (w + 4) + i + 2], Y = j * 16 + lift;
      if (keep) put(i, j, Y);
      for (let yy = Math.max(0, Y); yy < Math.min(h, Y + 16); yy++) for (let f = yy * W + i * 16, e = f + 16; f < e; f++) {
        if (keep) { see.state[f] = 1; see.cover[f] = 0; see.wet[f] = minLv === 0 ? 1 : 0; } else see.cover[f] = 1;
      }
    }
  };
  const {flat: over} = yield* reliefSteps(R, ground, see);
  const mouths = caveMouths(near, R.x * 16, y, W, h, rock);   // (the mouths of caves in what is kept: caves.js)
  if (mouths) over.getContext("2d").drawImage(mouths, -OV_M, -OV_M);
  // of it, what the rock is drawn over: the kept ground that is on top there (seen), and its water
  // (two masks, a canvas each, made once: one written again after it was drawn from is what a phone's GPU got wrong)
  const seen = new Uint8Array(W * h), m = new Uint32Array(W * h), wm = new Uint32Array(W * h);
  let any = 0;
  for (let f = 0; f < seen.length; f++) if ((see.cover[f] || XRAY.whole) && see.state[f] === 1) { seen[f] = 1; any++; m[f] = 0xff000000; if (see.wet[f]) wm[f] = 0xff000000; }
  const og = over.getContext("2d"); og.globalCompositeOperation = "destination-in"; og.drawImage(pxCanvas(m, W, h), 0, 0);
  return {key, x: R.x * 16, y, w: W, h, over, wet: pxCanvas(wm, W, h), seen, any};
}

// The circle itself, over the land and under everything standing on it
function drawXray(sx, sy) {
  const P = xray.pic;
  if (xray.a <= .01 || !P || !(P.any || xray.old)) return;
  const D = Math.ceil(XRAY.r * 32) + 2, cx = xray.x * 16 + 8, cy = xray.y * 16 + 8, ax = Math.round(cx - D / 2), ay = Math.round(cy - D / 2);
  for (const k of ["c", "c2"]) if (!xray[k]) { xray[k] = document.createElement("canvas"); xray[k].width = xray[k].height = D; }
  const part = (c, Q, share) => {                          // a picture's part under the circle: its water as it is on the screen this frame (water.js), the land over it
    const g = c.getContext("2d");
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = "source-over"; g.globalAlpha = 1; g.clearRect(0, 0, D, D); g.imageSmoothingEnabled = false;
    if (waterView) {
      g.drawImage(waterCv, ax - waterView.x, ay - waterView.y, D, D, 0, 0, D, D);
      g.globalCompositeOperation = "destination-in"; g.drawImage(Q.wet, ax - Q.x, ay - Q.y, D, D, 0, 0, D, D);
      g.globalCompositeOperation = "source-over";
    }
    g.drawImage(Q.over, ax - Q.x, ay - Q.y, D, D, 0, 0, D, D);
    if (share < 1) { g.globalCompositeOperation = "destination-in"; g.fillStyle = `rgba(0,0,0,${share})`; g.fillRect(0, 0, D, D); }
    return g;
  };
  const g = part(xray.c, P, xray.old ? xray.mix : 1);
  if (xray.old) { part(xray.c2, xray.old, 1 - xray.mix); g.globalCompositeOperation = "lighter"; g.drawImage(xray.c2, 0, 0); }   // (the two, each for its share)
  const R = XRAY.r * 16, fade = g.createRadialGradient(cx - ax, cy - ay, R * XRAY.core, cx - ax, cy - ay, R);
  [1, .8, .6, .4, .2, 0].forEach((v, i, all) => {                             // (in steps, as pixel art fades: rings, not a blur)
    fade.addColorStop(i / all.length, `rgba(0,0,0,${v})`); fade.addColorStop(Math.min(1, (i + 1) / all.length), `rgba(0,0,0,${v})`);
  });
  g.globalCompositeOperation = "destination-in"; g.fillStyle = fade; g.fillRect(0, 0, D, D);
  ctx.globalAlpha = xray.a;
  ctx.drawImage(xray.c, sx(0) + ax * zoom, sy(0) + ay * zoom, D * zoom, D * zoom);   // (on the land's own grid: not rounded apart from it)
  ctx.globalAlpha = 1;
}
