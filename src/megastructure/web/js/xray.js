// Behind a wall or a mountain you'd be hidden (behind.js: clipBehind). Instead, a circle round you is seen through
// it. The rule is one: inside the circle the land is drawn without the rock in the way, and nothing else changes.
// The rock in the way: of the mass that hides you (the ground two layers or more over you, all that joins up with
// what is drawn over you), the tiles on the line of sight to the place you are in, which is the ground you could
// walk or drop to from where you stand without leaving the circle. So the river ahead of you along a bank that turns
// shows, not only what is north of your feet; a cliff with nothing of that place behind it stays whole, and so does
// a rock that stands apart, whatever it hides. The land without it is
// painted by the land's own painter (relief.js: reliefSteps), the few tiles round you, every shape and colour as it
// is with the rock there: the ground you stand on with its water, the cliff behind you down to its foot, a step, a
// ledge. Of that picture only what the rock is drawn over is put on the screen: ground that shows anyway is never
// touched, and where there is only the rock's own inside to see (where it stands; where it joins a hill beside you,
// under that hill's tiles and along its side alike: no wall is drawn at the cut), the rock stays as it is drawn. What stands on that rock in the way (a tree, a creature, things lying there) fades
// with it; who is on the ground behind it shows through it. It fades out toward its edge, comes and goes softly, and
// is only for you. Painted again when you step onto another tile or the land changes, not each frame.

// r, core: its radius (tiles) and the part of it that's clear. It comes when you're really hidden, not for an edge
// that hides your legs or a post you walk past: body: your height, feet to ears (art px; your feet are 2 + STAND over
// the foot of your tile: relief.js); from, full: the share of you that's hidden where it starts and where it is whole
// (a ledge a layer high in front of you hides your legs: nothing; two layers leave the top of your head: the circle);
// wait: seconds hidden before it comes; far: tiles south to look for ground drawn up over you; box: tiles across
// that are painted (the circle, wherever you are on your tile); ms: a frame's share of painting it; turn: seconds a
// new picture takes to come over the one before; near: how far from your tile (tiles) the place you are in goes;
// whole (tests): no rock is left out and all of the picture is shown: it must then be the land's own, to the pixel
// wide: how far from your tile ground that was dug is seen (not in the circle: it has its own reach, r)
const XRAY = {r: 3.1, core: .42, body: 18, from: .5, full: .6, wait: .15, far: 12, box: 9, ms: 2.5, turn: .12, near: 4.1, wide: 12, whole: false};
// how strong, the height you stand at, your row, its centre (tiles), its canvas, how long you've been hidden, the land
// without the rock (pic), the next one being painted (job), the one before (old) and how far pic has come over it (mix)
const xray = {a: 0, L: 0, row: 0, x: 0, y: 0, c: null, c2: null, t: 0, pic: null, job: null, old: null, mix: 1};

// The rock that is seen through (the picture's: xrayPicture)
function xrayRock(tx, ty) {
  const P = xray.pic, i = P ? tx - P.rx : -1, j = P ? ty - P.ry : -1;
  return i >= 0 && i < P.rw && j >= 0 && j < P.rh && P.rock[j * P.rw + i] === 1;
}
// The place you are in: the ground you could walk or drop to from your tile (your height, a step up, or lower; no
// rock on the way), no further than XRAY.near; and, in ground that was dug, all you could walk to under sea level: up
// its steps too, and under its roof (a tunnel, a room: cells.js), so that the way you came stays seen as you go down
// it (a step down, the one two behind you was out of the place: it closed). -> {cols: column of tiles -> its rows of
// that ground, z: "x,y" -> its height there}. Ground that was dug is of it as far as XRAY.wide: all of the tunnel
// or the room on the screen ("underground vision should display as much as player can see"; it stopped four tiles
// from you, a fire a little further on not seen); how much of it light shows: cavelight.js
function xrayPlace(tx, row, L) {
  const far = opt("above") === "circle" ? 0 : XRAY.wide, h0 = settleNear(tx, row, L), cols = new Map(), z = new Map([[tx + "," + row, h0]]), todo = [[tx, row, h0]];   // (h0: your tile's own height: stepping off it down a stair, L is already the next one's)
  while (todo.length) {
    const [x, y, h] = todo.pop();
    if (!cols.has(x)) cols.set(x, []);
    cols.get(x).push(y);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy, key = nx + "," + ny;
      if (z.has(key) || tile(nx, ny) === null) continue;
      const lv = levelAt(nx, ny), w = lv <= L + 1 ? null : landAt(h, nx, ny, x, y), h2 = lv <= L + 1 ? lv : w !== null && w < 0 && (w === lv || dugHollow(nx, ny)) ? w : null;
      if (h2 === null || ((nx - tx) ** 2 + (ny - row) ** 2 > XRAY.near ** 2 && !(h2 < 0 && Math.max(Math.abs(nx - tx), Math.abs(ny - row)) <= far))) continue;
      z.set(key, h2); todo.push([nx, ny, h2]);
    }
  }
  return {cols, z};
}
// How clear the circle is at a spot as drawn (tiles, lifted with its ground): 0 the land as it is, 1 seen through.
// Not a circle (the views of options.js: VIEWS): the rock in the way is gone (cut away, outline) or faint (faded)
// all over the picture, and so is what stands on it
const XRAY_FADED = .65;                                    // (faded: how much of the rock goes)
function xrayAt(x, y) {
  if (xray.a <= .01) return 0;
  const v = opt("above"), P = xray.pic;
  if (v !== "circle") return P && x >= P.rx && x < P.rx + P.rw && y >= P.ry - 1 && y < P.ry + P.rh ? xray.a * (v === "faded" ? XRAY_FADED : 1) : 0;
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
// ...and the ground over the place you are in, under it: left out as that rock is (behind.js: neither hides anybody)
const xrayGone = (tx, ty) => xrayRock(tx, ty) || seenUnder(tx, ty) !== undefined;
// Someone on that rock fades with it, and so does who walks over the roof of the place you are in (not who is in it)
function xrayOverBody(p) {
  const x = Math.round(p.x), y = Math.round(p.y), f = seenUnder(x, y);
  return f === undefined ? xrayOver(x, y) : Floors.standOf(p, x, y) > f + 1 ? xrayOn(x, y) : 0;
}
// Someone on the ground behind that rock: how clearly they show through it (0: hidden as ever, 1: whole). (Under a
// roof of the place you are in: on its floor, not who walks over it)
function xrayShows(p) {
  const x = Math.round(p.x), y = Math.round(p.y), f = seenUnder(x, y);
  if (f !== undefined) return Floors.standOf(p, x, y) <= f + 1 ? xrayAt(x, y - shOf(f) / 16) : 0;
  return xrayRock(x, y) ? 0 : xrayOn(x, y);
}

// How far (art px) the ground south of a tile rises over the foot of its row (py: the row as drawn) at height L
function xrayCover(tx, row, py, L) {
  let cover = 0;
  for (let ty = row + 1; ty <= row + XRAY.far; ty++) cover = Math.max(cover, (levelAt(tx, ty) - L) * RELIEF_STEP - (ty - py - 1) * 16);
  return cover;
}
// Once a frame, before anything of it is drawn: are you behind something, and how much of you. (The build cursor
// down a hole went round with it too; it has its own keyhole now: keyhole.js)
function xrayLook(dt) {
  const p = me && ents.get("agent" + myId);
  let want = 0, f = null;                                  // (what the circle is round: px, py as drawn, L, row; mid: its centre over its tile)
  if (p && p.e && !caveOpen) {
    // (where you are as drawn, at the height you are at: on a step, a floor, a ladder's rungs; it was the land's under
    // you, and a climb up a cliff's side or a flight of stairs beside one brought the circle up half way)
    const cl = Climb.climbOf(p), px = p.x + (cl ? cl.dx : 0), py = p.y + (cl ? cl.dy : 0);
    const L = cl ? Math.floor(cl.h) : Math.min(Floors.standOf(p, Math.floor(p.x), Math.floor(p.y)), Floors.standOf(p, Math.ceil(p.x), Math.ceil(p.y))), row = Math.floor(py + .001);
    let hidden = 0;                                        // the share of you under the top edge of the ground in front: the two
    const fr = px - Math.floor(px);                        //  columns you stand across, each for the part of you in it
    let roof = false;                                      // (under ground that was dug, its roof over you: all of you, at once)
    for (const [tx, part] of [[Math.floor(px), 1 - fr], [Math.floor(px) + 1, fr]]) if (part > .001) {
      const under = dugHollow(tx, row) && coveredAt(tx, row, L);
      roof = roof || under; hidden += part * (under ? 1 : Math.max(0, Math.min(1, (xrayCover(tx, row, py, L) - 2 - STAND) / XRAY.body)));
    }
    want = Math.max(0, Math.min(1, (hidden - XRAY.from) / (XRAY.full - XRAY.from)));
    f = {px, py, L, row, mid: .5 + UP, roof};
  }
  if (f) {
    xray.t = want > 0 ? xray.t + dt : 0;
    if (xray.t < XRAY.wait && xray.a <= .01 && !f.roof) want = 0;      // (a moment behind something: not yet)
    if (xray.t > 0 || xray.a > .01) {
      xray.L = f.L; xray.row = f.row; xray.x = f.px; xray.y = f.py - shOf(f.L) / 16 - f.mid;   // (its centre: your body, where it is drawn)
      if (!xrayPaint(Math.round(f.px)) && xray.a <= .01) want = 0;               // (it comes once its picture is ready)
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
  const near = [], wide = opt("above") === "circle" ? 5 : XRAY.wide + 2;   // the blocks it can take tiles from, and what they have of the land
  for (let by = Math.floor((xray.row - 14) / B); by <= Math.floor((xray.row + 14) / B); by++) for (let bx = Math.floor((tx - wide) / B); bx <= Math.floor((tx + wide) / B); bx++) {
    const b = blocks.get(bkey(bx, by)); if (b && b.px) near.push(b);
  }
  const key = [tx, xray.row, xray.L, XRAY.whole, wide, ...near.map((b) => b.bx + ":" + b.by + ":" + (b.ver || 0))].join();
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
  // the rock seen through, from where you were when this was started: on the line of sight to a tile of your place
  // (south of it in its column, and high enough to be drawn over it: two layers a row), and of the mass that hides
  // you (gone through from what is over your tile and the two beside it, tile to tile)
  const L = xray.L, row = xray.row, {cols: place, z: floors} = xrayPlace(tx, row, L), mass = new Set(), todo = [];
  const sight = (x, ty) => {
    const lv = XRAY.whole ? -99 : levelAt(x, ty), rows = lv >= L + 2 && place.get(x);
    return !!rows && rows.some((gy) => gy < ty && lv - floors.get(x + "," + gy) > 2 * (ty - gy) - 2);
  };
  const at = (x, ty) => (x - tx + 16) * 64 + ty - row + 24, join = (x, ty) => { if (!mass.has(at(x, ty))) { mass.add(at(x, ty)); todo.push([x, ty]); } };
  for (let x = tx - 1; x <= tx + 1; x++) if ((place.get(x) || []).includes(row)) for (let ty = row + 1; ty <= row + XRAY.far; ty++) if (sight(x, ty)) join(x, ty);
  while (todo.length) {
    const [x, ty] = todo.pop();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) if (Math.abs(x + dx - tx) <= XRAY.wide + 2 && Math.abs(ty + dy - row) <= 20 && levelAt(x + dx, ty + dy) >= L + 2) join(x + dx, ty + dy);
  }
  // the place under a roof (a tunnel, a room dug under the ground): its floor is kept, the ground over it left out
  const floor = new Map(); for (const [key, h] of floors) { const [x, ty] = key.split(",").map(Number); if (h < levelAt(x, ty)) floor.set(key, h); }
  const rock = (x, ty) => mass.has(at(x, ty)) && sight(x, ty) && !floor.has(x + "," + ty);
  // its tiles across and its rows on the screen (art px): the circle's, wherever you are on your tile; and all of the
  // dug ground of your place, each floor where it is drawn with the wall behind it
  const D = Math.ceil(XRAY.r * 32) + 2, dug = [...floors].filter(([, f]) => f < 0).map(([k, f]) => [...k.split(",").map(Number), f]);
  const xa = Math.min(tx - (XRAY.box >> 1), ...dug.map((d) => d[0] - 1)), w = Math.max(tx + (XRAY.box >> 1), ...dug.map((d) => d[0] + 1)) - xa + 1, W = w * 16;
  const ya = xray.row * 16 - shOf(xray.L) - (D >> 1) - 6, y = Math.min(ya, ...dug.map((d) => d[1] * 16 - 24)), h = Math.max(ya + D + 22, ...dug.map((d) => d[1] * 16 - shOf(d[2]) + 26)) - y;
  let lo = Math.min(99, ...floor.values()), hi = -99, edged = [];
  for (let ty = xray.row - 14; ty <= xray.row + 14; ty++) for (let x = xa - 1; x <= xa + w; x++) { const l = levelAt(x, ty); lo = Math.min(lo, l); hi = Math.max(hi, l); }
  const y0 = Math.max(xray.row - 14, (y + shOf(lo) >> 4) - 1), y1 = Math.min(xray.row + 14, y + h + shOf(hi) >> 4);   // every row of tiles that can be drawn in it
  const R = {x: xa, y: y0, w, h: y1 - y0 + 1}, gh = R.h * 16, ground = new Uint32Array(W * gh);   // (its ground: the blocks' own px, tiles.js)
  for (const b of near) {
    const bx = (b.bx * B - R.x) * 16, by = (b.by * B - R.y) * 16, x0 = Math.max(0, bx), x1 = Math.min(W, bx + BW);
    if (x1 > x0) for (let yy = Math.max(0, by); yy < Math.min(gh, by + BW); yy++) ground.set(b.px.subarray((yy - by) * BW + x0 - bx, (yy - by) * BW + x1 - bx), yy * W + x0);
  }
  if (floor.size) {                                         // (those floors as the land's painter draws them, and the tiles round them, with their edge to them: tiles.js; the picture's levels with them)
    const again = new Set();
    for (const key of floor.keys()) { const [x, ty] = key.split(",").map(Number); for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (x + dx >= R.x && x + dx < R.x + w && ty + dy >= R.y && ty + dy < R.y + R.h) again.add((ty + dy - R.y) * w + x + dx - R.x); }
    peek = floor;
    for (const q of again) drawTile(R.x + q % w, R.y + (q / w | 0), {px: ground, o: (q / w | 0) * 16 * W + (q % w) * 16, w: W});
    rectLevels(R, "lk"); peek = null;
    edged = [...again].filter((q) => !floor.has((R.x + q % w) + "," + (R.y + (q / w | 0))));
  }
  const see = {keep: new Uint8Array((w + 4) * (R.h + 4)), c0: y - R.y * 16, c1: y - R.y * 16 + h, state: new Uint8Array(W * h), lev: new Int8Array(W * h), cover: new Uint8Array(W * h), wet: new Uint8Array(W * h)};
  const rocks = new Uint8Array(w * R.h);
  for (let j = -2; j < R.h + 2; j++) for (let i = -2; i < w + 2; i++) {
    const is = rock(R.x + i, R.y + j);
    see.keep[(j + 2) * (w + 4) + i + 2] = is ? 0 : 1;
    if (is && i >= 0 && i < w && j >= 0 && j < R.h) rocks[j * w + i] = 1;
  }
  see.base = (R, put, lift, minLv) => {                    // the ground itself, each tile kept at the lowest level (water shows through it at the sea's)
    for (let j = 0; j < R.h; j++) for (let i = 0; i < w; i++) {
      const keep = see.keep[(j + 2) * (w + 4) + i + 2], Y = j * 16 + lift;
      if (keep) put(i, j, Y);
      for (let yy = Math.max(0, Y); yy < Math.min(h, Y + 16); yy++) for (let f = yy * W + i * 16, e = f + 16; f < e; f++) {
        if (keep) { see.state[f] = 1; see.lev[f] = minLv; see.cover[f] = 0; see.wet[f] = minLv === 0 ? 1 : 0; } else see.cover[f] = 1;
      }
    }
  };
  const {flat: over} = yield* reliefSteps(R, ground, see);
  for (const q of edged) {                                  // (the ground beside a roof left out: with its edge to it, where it is on top)
    const lv = R.lv[((q / w | 0) + 2) * (w + 4) + q % w + 2], X = (q % w) * 16, Y = (R.y + (q / w | 0)) * 16 - shOf(lv) - y;
    for (let r = Math.max(0, -Y); r < 16 && Y + r < h; r++) for (let f = (Y + r) * W + X, e = f + 16; f < e; f++) if (see.state[f] === 1 && see.lev[f] === lv) see.cover[f] = 1;
  }
  const mouths = caveMouths(near, R.x * 16, y, W, h, (x, ty) => rock(x, ty) || floor.has(x + "," + ty));   // (the mouths of caves in what is kept: caves.js)
  if (mouths) over.getContext("2d").drawImage(mouths, -OV_M, -OV_M);
  // of it, what the rock is drawn over: the kept ground that is on top there (seen), and its water
  // (two masks, a canvas each, made once: one written again after it was drawn from is what a phone's GPU got wrong)
  const seen = new Uint8Array(W * h), m = new Uint32Array(W * h), wm = new Uint32Array(W * h);
  let any = 0;
  for (let f = 0; f < seen.length; f++) if ((see.cover[f] || XRAY.whole) && see.state[f] === 1) { seen[f] = 1; any++; m[f] = 0xff000000; if (see.wet[f]) wm[f] = 0xff000000; }
  const og = over.getContext("2d"); og.globalCompositeOperation = "destination-in"; og.drawImage(pxCanvas(m, W, h), 0, 0);
  // In ground that was dug, what is seen through ends in a line, the hole's own outline, where the ground left beside
  // it or in front of it stands higher (a pit's floor lay on the meadow in front like a sheet of paper, cut square)
  const rim = colsOf(hillSheet(0)).side.reduce((d, c) => (c[0] + c[1] + c[2] < d[0] + d[1] + d[2] ? c : d)), ink = (255 << 24 | rim[2] << 16 | rim[1] << 8 | rim[0]) >>> 0, edge = new Uint32Array(W * h);
  let lines = 0;
  for (let f = 0; f < seen.length; f++) if (seen[f] && see.lev[f] < 0) for (const n of [f % W ? f - 1 : -1, (f + 1) % W ? f + 1 : -1, f + W]) {
    if (n >= 0 && n < seen.length && !seen[n] && !(see.state[n] === 1 && see.lev[n] <= see.lev[f])) { edge[f] = ink; lines++; break; }
  }
  if (lines) { og.globalCompositeOperation = "source-over"; og.drawImage(pxCanvas(edge, W, h), 0, 0); }
  return {key, x: R.x * 16, y, w: W, h, over, wet: pxCanvas(wm, W, h), seen, any, rock: rocks, floor, place: floors, lev: see.lev, depth: underDepths(floor, floors), rx: R.x, ry: R.y, rw: w, rh: R.h};
}

// The circle itself, over the land and under everything standing on it (in the other views: drawXrayWhole)
function drawXray(sx, sy) {
  const P = xray.pic;
  if (xray.a <= .01 || !P || !(P.any || xray.old)) return;
  if (opt("above") !== "circle") return drawXrayWhole(sx, sy);
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
