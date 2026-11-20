// The HD look's things (hd.js): what is built or put down is a piece of the land, not a flat picture of itself stood
// up on tilted ground ("some tiles should be turned 3d: bed, etc"). Nothing is new art: every px is the thing's own.
//   Furniture (a bed, a chest, a table...): a CARD: its own sprite px for px, never squeezed (as big and as crisp as
//   its picture), drawn by the engine as a billboard at its foot. Its top rows lean, a whole px at a time, as a top
//   lying behind its front does off to a side of the screen, the side that shows is filled in the front's own edge
//   colour, and its shadow lies on the ground. A well, a coop, a sign...: their picture and a shadow, no lean.
//   Walls, doors, fences, built floors, steps and roofs, a rug: boxes in the land (the engine's models, vox_style.js
//   `model`), painted from the pack's sheets or by the game's own painters (structures.js, floors.js, climbing.js) at
//   zoom 1. A front is as many rows of paint as it is px high on the screen at your feet (KF: the eye's pitch).
//   HdThings.at(x, y) -> the boxes of the tile; is(c) -> a char that is boxes (no billboard); card(c, x, y, spr, X);
//   loose(x, y) -> [[char, z]...]: what stands on a built block and is not boxes; key() -> changes when the boxes must be made again
const HdThings = (() => {
  const SW = 1024, SH = 1024, sheet = {px: new Uint32Array(SW * SH), w: SW, id: "hd"}, rooms = new Map(), pixs = new Map(), UP = RELIEF_STEP, LEAN = 0, PITCH = 4, plans = new Set();   // (KF: a front's px on the screen a px of its height, hd.js cam.pitch; LEAN: px a top's row leans, a px off the middle: none, it read as broken; PITCH: px a roof rises a tile; plans: walls only planned, "x,y,z")
  let nx = 0, ny = 0, tall = 0, ids = 0, scratch = null;
  const KF = () => Math.cos(HdLook.cam.pitch * Math.PI / 180);   // (a front's px on the screen a px of its height: the eye's pitch, 36 degrees, up to 52 on a screen held upright: it was 36 always, and a wall's 12 rows of planks were squeezed into 9 px on a phone)
  // room for w x h px of paint in the sheet, filled once by fill(put(i, j, px)) -> [u, v]
  function room(key, w, h, fill) {
    let p = rooms.get(key); if (p) return p;
    if (nx + w > SW) { nx = 0; ny += tall; tall = 0; }
    if (ny + h > SH) { rooms.clear(); sheet.px.fill(0); nx = ny = tall = 0; sheet.id = "hd" + (++ids); }   // (full: from none, under a new name so the engine paints its slots again)
    p = [nx, ny]; const ox = nx, oy = ny; fill((i, j, v) => { if (i >= 0 && j >= 0 && i < w && j < h) sheet.px[(oy + j) * SW + ox + i] = v; });
    nx += w; tall = Math.max(tall, h); rooms.set(key, p); return p;
  }
  // the px of a piece of a picture (an image or a canvas): {px, w, h, key}
  function pix(img, sx, sy, w, h) {
    if (!img._hd) img._hd = ++ids; const key = img._hd + "|" + sx + "," + sy + "," + w + "," + h; let p = pixs.get(key); if (p) return p;
    scratch = scratch || document.createElement("canvas"); scratch.width = w; scratch.height = h; const g = scratch.getContext("2d", {willReadFrequently: true});
    g.clearRect(0, 0, w, h); g.drawImage(img, sx, sy, w, h, 0, 0, w, h); p = {px: new Uint32Array(g.getImageData(0, 0, w, h).data.buffer.slice(0)), w, h, key}; pixs.set(key, p); return p;
  }
  // one of the game's own painters on a canvas of its own at zoom 1 (as hd.js draws a body)
  function painted(w, h, fn) {
    const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    const keep = ctx, kz = zoom; ctx = g; zoom = 1; try { fn(g); } catch (e) { /* (nothing to draw) */ } finally { ctx = keep; zoom = kz; }
    return c;
  }
  const shotOf = (key, w, h, fn) => { let p = pixs.get(key); if (!p) { p = pix(painted(w, h, fn), 0, 0, w, h); p.key = key; pixs.set(key, p); } return p; };   // (...and its px, kept under a name)
  const solid = (v) => (v >>> 24) >= 128;
  // paints cut out of P: rows r0..r1 of its columns c0..c1 (rep: row r0 that many times); a side: each row's px a px in from that edge (w px wide)
  const cut = (P, c0, c1, r0, r1, rep) => room(P.key + "c" + [c0, c1, r0, r1, rep], c1 - c0, rep || r1 - r0, (put) => { for (let j = 0; j < (rep || r1 - r0); j++) for (let i = c0; i < c1; i++) put(i - c0, j, P.px[(rep ? r0 : r0 + j) * P.w + i]); });
  const side = (P, c0, c1, r0, r1, w, east) => room(P.key + "s" + [c0, c1, r0, r1, w, east], w, r1 - r0, (put) => { for (let j = r0; j < r1; j++) { let v = 0, n = 0;
    for (let i = east ? c1 - 1 : c0; i >= c0 && i < c1 && n < 2; i += east ? -1 : 1) if (solid(P.px[j * P.w + i])) { v = P.px[j * P.w + i]; n++; }      // (the second solid px in: past the outline)
    for (let i = 0; i < w; i++) put(i, j - r0, v); } });
  // a box into the list, in pieces a slot of the engine can hold (16 px a side)
  function push(out, b) {
    for (let i = 0; i < b.w; i += 16) for (let j = 0; j < b.d; j += 16) for (let k = 0; k < (b.fh ? 1 : Math.max(1, b.h)); k += 16) {      // (fh: its front is that many rows of paint, whatever its height: one piece)
      const w = Math.min(16, b.w - i), d = Math.min(16, b.d - j), h = b.fh ? b.h : Math.min(16, b.h - k), o = (p, a, c) => (p ? [p[0] + a, p[1] + c] : null);
      out.push({x: b.x + i, y: b.y + j, z: b.z + b.h - k - h, w, d, h, fh: b.fh, shade: b.shade, tilt: b.tilt, k: b.k, sheet, top: k === 0 ? o(b.top, i, j) : null, front: j + 16 >= b.d ? o(b.front, i, k) : null, west: i === 0 ? o(b.west, j, k) : null, east: i + 16 >= b.w ? o(b.east, j, k) : null});
    }
  }
  // ---- furniture: a card (see the top). CARD: char -> [r0, rS, r2]: its top's first row, its front's first row, the row under its foot. PLAIN: char -> the row under its foot where that is not its last row (a coop's ramp runs on past its legs)
  const CARD = {B: [10, 28, 32], C: [3, 8, 14], L: [1, 12, 15], "&": [2, 7, 13], e: [1, 8, 15], y: [1, 7, 15], q: [1, 7, 14]}, PLAIN = {J: 42}, cards = new Map();
  const span = (P, r0, r1) => { let c0 = P.w, c1 = 0; for (let j = Math.max(0, r0); j < Math.min(P.h, r1); j++) for (let i = 0; i < P.w; i++) if (solid(P.px[j * P.w + i])) { c0 = Math.min(c0, i); c1 = Math.max(c1, i + 1); } return c1 > c0 ? [c0, c1] : [0, P.w]; };
  // -> {canvas, fx, fy, y, lean, b}: its picture where it is on the screen (X: art px right of the middle), the px of it that is its foot's middle, how far south in its tile its foot is (tiles), its bounds in it
  function card(c, x, y, spr, X = 0) {
    const S = CARD[c]; if (!S || !spr || !spr[0] || !spr[0].width) return null;
    const [img, sx, sy, sw, sh, dx, dy] = spr, P = pix(img, sx, sy, sw, sh), [r0, rS, r2] = S, n = rS - r0, k = Math.max(-8, Math.min(8, Math.round(X * LEAN * n))), key = P.key + "|" + k;
    let cd = cards.get(key); if (cd) return cd;
    const a = Math.abs(k), off = k > 0 ? a : 0, W2 = sw + a, cv2 = document.createElement("canvas"); cv2.width = W2; cv2.height = sh;
    const g = cv2.getContext("2d"), im = g.createImageData(W2, sh), o = new Uint32Array(im.data.buffer), [c0, c1] = span(P, rS, r2), lean = (j) => (j >= rS ? 0 : -Math.sign(k) * Math.round(a * (rS - j) / n));      // (right of the middle: its far rows towards the left, and its west side shows)
    for (let t = 1; t <= a; t++) { const jt = rS - Math.round(t / a * n), X0 = (k > 0 ? c0 - t : c1 - 1 + t) + off;      // (the side: a column a px, each as high as the front, in the front's edge colour row by row)
      for (let i = 0; i < r2 - rS; i++) { let v = 0, m = 0; for (let q = k > 0 ? c0 : c1 - 1; q >= c0 && q < c1 && m < 2; q += k > 0 ? 1 : -1) if (solid(P.px[(rS + i) * sw + q])) { v = P.px[(rS + i) * sw + q]; m++; } if (v && jt + i >= 0) o[(jt + i) * W2 + X0] = v; } }
    for (let j = 0; j < sh; j++) for (let i = 0; i < sw; i++) { const v = P.px[j * sw + i]; if (solid(v)) o[j * W2 + i + off + lean(j)] = v; }
    const b = [W2, sh, 0, 0]; for (let j = 0; j < sh; j++) for (let i = 0; i < W2; i++) if (o[j * W2 + i]) { b[0] = Math.min(b[0], i); b[1] = Math.min(b[1], j); b[2] = Math.max(b[2], i + 1); b[3] = Math.max(b[3], j + 1); }
    g.putImageData(im, 0, 0); cd = {canvas: cv2, fx: 8 - dx + off, fy: r2, y: (dy + r2) / 16, lean: k, b, still: true, d: true}; cards.set(key, cd); return cd;
  }
  // the shadow under a thing that stands: an oval of shade on the ground round its foot (the engine lays it over the land: `shade`)
  const oval = (w, d) => room("o" + [w, d], w, d, (put) => { for (let j = 0; j < d; j++) for (let i = 0; i < w; i++) { const u = (i + .5) / w * 2 - 1, v = (j + .5) / d * 2 - 1; if (u * u + v * v <= 1) put(i, j, 0xff000000); } });
  const shaded = (c) => isObject(c) && !is(c) && !"f;\"wgVl".includes(c);      // (all that stands; not what is boxes, what is flat or thin, what floats)
  // the row of a thing's sprite that is under its foot (its last row with a px): where it stands on the ground, and where its shadow lies
  function foot(c, spr) { if (CARD[c]) return CARD[c][2]; if (PLAIN[c] !== undefined) return PLAIN[c]; const P = pix(spr[0], spr[1], spr[2], spr[3], spr[4]), has = (j) => { for (let i = 0; i < P.w; i++) if (solid(P.px[j * P.w + i])) return true; return false; }; let r = P.h; while (r > 1 && !has(r - 1)) r--; return r; }
  function shade(out, c, x, y, base, L) {      // (L: it stands on the ground at that level: the hour's shadow too, hd_sun.js)
    const spr = objectSprite(c, x, y, 0); if (!spr || !spr[0] || !spr[0].width) return;
    const P = pix(spr[0], spr[1], spr[2], spr[3], spr[4]), r2 = foot(c, spr);
    const [c0, c1] = span(P, r2 - 4, r2), tall = P.h >= 40 && !CARD[c] && PLAIN[c] === undefined, w = tall ? 22 : c1 - c0 + 4, d = CARD[c] ? 11 : tall ? 9 : 8, mid = (c0 + c1) / 2;      // (a tree: its crown's, wider than its trunk)
    push(out, {x: Math.round(spr[5] + mid - w / 2), y: spr[6] + r2 - d + 4, z: base + .5, w, d, h: 0, top: oval(w, d), shade: true});
    if (L !== undefined && c !== "^" && c !== "x") HdSun.thing(out, x, y, L, P, spr[5], spr[6], r2);
  }
  const cast = (out, x, y, zl, r, h0, h1, built) => { if (!ghosting && (built || zl === floorAt(x, y))) HdSun.box(out, x, y, built ? floorAt(x, y) : zl, r, h0, h1, built); };   // (what is built throws the shadow of the box it is, a px wider so that a run's are one)
  // the shadow of what moves (a body, what lies on the ground): boxes for the engine's view.ghosts, w x d px round a point, z px up
  function shadow(w, d, z) { const l = []; push(l, {x: -Math.round(w / 2), y: -Math.round(d / 2), z, w, d, h: 0, top: oval(w, d), shade: true}); return l; }
  // a rug, a blanket: flat on the ground, its picture the top of a box with no height
  function decal(out, c, x, y, base) { const spr = objectSprite(c, x, y, 0); if (!spr || !spr[0] || !spr[0].width) return; push(out, {x: spr[5] - 1, y: spr[6] - 1, z: base + .5, w: spr[3] + 2, d: spr[4] + 2, h: 0, top: flat(0xff000000, spr[3] + 2, spr[4] + 2, 0xff000000), shade: true}); push(out, {x: spr[5], y: spr[6], z: base + 1, w: spr[3], d: spr[4], h: 0, top: cut(pix(spr[0], spr[1], spr[2], spr[3], spr[4]), 0, spr[3], 0, spr[4])}); }
  // ---- walls, doors: thin, in the middle of their tile (structures.js: the band's 6 px), a top to each. h: its height in px of the land: 12 rows of planks as its picture (12 / KF() px); under a built block 16 px, up to it (13 rows)
  const tints = new Map(), L0 = 5, R0 = 11;
  function tint(c, x, y, at) {   // a wall's ink and its cap's colour: off the game's own picture of it
    let t = tints.get(c); if (t) return t;
    const P = pix(painted(16, 16, () => Structures.drawWall(c === "+" ? "W" : c, x, y, () => 0, () => 4, 16, 0, 1, at)), 0, 0, 16, 16), cap = P.px[2 * 16 + 8], ink = [P.px[8], P.px[2 * 16 + 5], P.px[2 * 16]].find((v) => solid(v) && v !== cap);
    if (!solid(cap) || !ink) return {ink: 0xff604c75, cap: 0xff6c9ac4}; t = {ink, cap}; tints.set(c, t); return t;
  }
  const flat = (v, w, h, inkv, edges = "") => room("f" + [v, w, h, inkv, edges], w, h, (put) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) put(i, j, (edges.includes("n") && !j) || (edges.includes("s") && j === h - 1) || (edges.includes("w") && !i) || (edges.includes("e") && i === w - 1) ? inkv : v); });
  function planks(c, X, w, h) {   // a wall's front, as structures.js takes it: the pack's planks (stone: its stones), 12 rows; taller: its last rows again over them
    const stone = c === "%", g = stone ? genCell("stone_wall") : null, P = stone ? pix(IMG.gen, g[0], g[1] + 2, 16, 12) : pix(IMG.house_walls, 56, 4, 16, 12);
    return room("p" + [stone, X, w, h], w, h, (put) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const v = P.px[((j + 12 - (h % 12)) % 12) * 16 + X + i]; put(i, j, solid(v) ? v : P.px[5 * 16 + 1]); } });   // (the sprite's see-through corners: its line's colour)
  }
  let ghosting = false; const isWall = (x, y, z) => Structures.WALLS.includes(Floors.thingAt(x, y, z) || "-") || (ghosting && plans.has(x + "," + y + "," + z));
  const doorsAt = new Map(), doorOpen = (x, y) => doorsAt.set(x + "," + y, [x, y]) && [[0, 0], [0, -1], [0, 1], [1, 0], [-1, 0]].some(([dx, dy]) => occupied.has((x + dx) + "," + (y + dy)));
  function wall(out, c, x, y, zl, h) {
    const n = isWall(x, y - 1, zl), s = isWall(x, y + 1, zl), w = isWall(x - 1, y, zl), e = isWall(x + 1, y, zl), T = tint(c, x, y, zl), z = zl * UP;
    const rows = (hh) => Math.max(1, Math.round(hh * KF()));
    const part = (x0, x1, y0, y1, hh, ed, front, pc = c) => { cast(out, x, y, zl, [x0 - 1, y0 - 1, x1 + 1, y1 + 1], 0, hh); push(out, {x: x0, y: y0, z, w: x1 - x0, d: y1 - y0, h: hh, fh: rows(hh), top: flat(T.cap, x1 - x0, y1 - y0, T.ink, ed), front: front ? planks(pc, x0, x1 - x0, rows(hh)) : null,
      west: x0 === 0 ? null : flat(planksTone(pc), Math.min(16, y1 - y0), rows(hh), T.ink, "n"), east: x1 === 16 ? null : flat(planksTone(pc), Math.min(16, y1 - y0), rows(hh), T.ink, "n")}); };
    if (c === "+" && Structures.sideDoor(x, y, zl)) {      // a door in a run north-south: two posts, its leaf between them (open: swung away)
      part(L0, R0, 0, 4, h, "we", true); part(L0, R0, 12, 16, h, "wes", true);
      if (!doorOpen(x, y)) { const D = pix(IMG.door, 80, 0, 16, 16), lv = D.px[8 * 16 + 6]; push(out, {x: 6, y: 4, z, w: 4, d: 8, h: h * .9, fh: rows(h * .9), top: flat(lv, 4, 8, T.ink, "we"), west: flat(lv, 8, rows(h * .9), T.ink, "n"), east: flat(lv, 8, rows(h * .9), T.ink, "n")}); }
      return;
    }
    if (c === "+") {                                        // a door in a run east-west: the pack's door as it is drawn, the wall's planks over it up to what it holds
      const D = pix(IMG.door, (doorOpen(x, y) ? 0 : 5) * 16, 0, 16, 16), hh = h < 12 || Math.abs(h - 16) < .5 ? h : 16 / KF(), fh = rows(hh);      // (free: its own 16 rows; under a block: the 13 that fit, from its foot up)
      cast(out, x, y, zl, [-1, L0 - 1, 17, R0 + 1], 0, hh); push(out, {x: 0, y: L0, z, w: 16, d: 6, h: hh, fh, top: flat(T.cap, 16, 6, T.ink, "ns"), front: cut(D, 0, 16, 16 - fh, 16), west: flat(T.ink, 6, fh, T.ink), east: flat(T.ink, 6, fh, T.ink)});
      return;
    }
    const x0 = w ? 0 : L0, x1 = e ? 16 : R0;
    part(x0, x1, L0, R0, h, (n ? "" : "n") + (s ? "" : "s") + (w ? "" : "w") + (e ? "" : "e"), true);
    if (n) part(L0, R0, 0, L0, h, "we", false);
    if (s) part(L0, R0, R0, 16, h, "we", true);      // (a front to each: the wall south of it may be lower, cut open)
  }
  const tones = new Map(), planksTone = (c) => { let v = tones.get(c); if (v === undefined) { const u = planks(c, 0, 16, 12); v = sheet.px[(u[1] + 5) * SW + u[0] + 7]; tones.set(c, v); } return v; };
  // ---- fences: a post, its rails east and west as the sprite has them (upright), its rails north and south as thin boxes of the rail's own colour
  function fence(out, x, y, base) {
    const spr = fenceSprite(x, y), P = pix(spr[0], spr[1], spr[2], 16, 16), dy = spr[6], f = (dx, ddy) => "#+g".includes(combAt(x + dx, y + ddy) || "-");
    const rail = P.px[8 * 16 + 7] || P.px[6 * 16 + 7], dark = P.px[12 * 16 + 5] || rail, Y1 = 12;
    // (a run north-south: a post on every other tile, the rails through between them: a post is 12 px high and a tile 9 px deep on the screen, a post a tile was one mush of posts)
    const run = f(0, -1) && f(0, 1) && !f(-1, 0) && !f(1, 0) && combAt(x, y) === "#", post = !run || !(y & 1), L = base / UP, sun = (r, h0, h1) => cast(out, x, y, L, r, h0, h1);
    if (post) { sun([4, Y1 - 5, 12, Y1 + 1], 0, 12 / KF()); push(out, {x: 5, y: Y1 - 4, z: base, w: 6, d: 4, h: 12 / KF(), fh: 12, top: cut(P, 5, 11, 2, 6), front: cut(P, 5, 11, 2, 14), west: side(P, 5, 11, 2, 14, 4, 0), east: side(P, 5, 11, 2, 14, 4, 1)}); }
    for (const [on, c0, c1] of [[f(-1, 0), 0, 5], [f(1, 0), 11, 16]]) if (on) { for (const rz of [3, 8]) sun([c0, Y1 - 3, c1, Y1 - 1], rz / KF(), (rz + 2) / KF()); push(out, {x: c0, y: Y1 - 3, z: base, w: c1 - c0, d: 2, h: 12 / KF(), fh: 12, top: null, front: cut(P, c0, c1, 2, 14)}); }
    for (const [on, y0, y1] of post ? [[f(0, -1), 0, Y1 - 4], [f(0, 1), Y1, 16]] : [[true, 0, 16]]) if (on) for (const rz of [3, 8]) { sun([6, y0, 10, y1], rz / KF(), (rz + 2) / KF());
      push(out, {x: 6, y: y0, z: base + rz / KF(), w: 3, d: y1 - y0, h: 2 / KF(), fh: 2, top: flat(rail, 3, y1 - y0, dark, "we"), west: flat(dark, Math.min(16, y1 - y0), 2, dark), east: flat(dark, Math.min(16, y1 - y0), 2, dark)}); }   // (a rail from above: its two edges dark, so it reads between the posts)
  }
  // a gate in a run north-south: its leaf along the run, a thin box as high as the posts beside it (open: none); the posts are the fences' own
  function sideGate(out, x, y, base) {
    if (doorOpen(x, y)) return; const P = pix(IMG.gates, 0, 0, 16, 16), lum = (v) => (v & 255) + (v >> 8 & 255) + (v >> 16 & 255); let wood = 0, dark = 0;
    for (let i = 0; i < 256; i++) { const v = P.px[i]; if (!solid(v)) continue; if (!wood || lum(v) > lum(wood)) wood = v; if (!dark || lum(v) < lum(dark)) dark = v; }      // (the gate's own lightest wood and its line)
    push(out, {x: 6, y: -4, z: base + 2 / KF(), w: 4, d: 24, h: 9 / KF(), fh: 9, top: flat(wood, 4, 24, dark, "wens"), front: flat(wood, 4, 9, dark, "wens"), west: flat(wood, 24, 9, dark, "ns"), east: flat(wood, 24, 9, dark, "ns")});
  }
  // ---- built blocks (floors.js): a floor's planks, a step, a roof's shingles. The game's own picture of the block: its 16 rows the top, the rows under them its face
  const hid = (x, y, z) => Floors.alpha(x, y, z) < 1;        // (over your head, or over the build cursor's level: not drawn, as the game's own rule has it)
  function block(out, kind, x, y, z) {
    const g = (dx, dy, dz = 0) => { const c = Floors.get(x + dx, y + dy, z + dz); return c && !hid(x + dx, y + dy, z + dz) ? c[0] : ""; }, same = (dx, dy) => g(dx, dy) === kind;
    if (kind === "roof") {                                  // shingles: a real roof, two pitched faces: up from its north edge to the ridge (the pack's ridge row: half way down its run), down from it to the eave; the eave its front, the gable its sides
      let up = 0, down = 0; while (up < 14 && same(0, -up - 1)) up++; while (down < 14 && same(0, down + 1)) down++;
      const w = same(-1, 0), e = same(1, 0), n = up + down + 1, yr = Math.floor((n - 1) / 2) + .5, pk = PITCH * n / 2, hat = (v) => Math.round(v <= yr ? pk * v / yr : pk * (n - v) / (n - yr));
      cast(out, x, y, 0, [-1, -1, 17, 17], 0, (z - floorAt(x, y)) * UP + hat(up + .5), true);
      const P = shotOf("roof" + [up, down, w, e], 16, 30, () => Structures.drawRoof(0, 7, 16, up, down, w, e)), E = pix(IMG.house_roof, 16, 64, 16, 7);
      const eave = room("eave", 16, 7, (put) => { for (let j = 0; j < 7; j++) for (let i = 0; i < 16; i++) put(i, j, E.px[j * 16 + i]); }), S = {px: sheet.px, w: SW, key: "eaveS"};
      for (const [y0, y1] of up === Math.floor(yr) ? [[0, 8], [8, 16]] : [[0, 16]]) { const d = y1 - y0, last = y1 === 16;
        push(out, {x: 0, y: y0, z: z * UP - 7, w: 16, d, h: 7, tilt: [hat(up + y0 / 16), hat(up + y1 / 16)], k: up + y0 / 16 < yr ? .7 : 1, top: cut(P, 0, 16, 7 + y0, 7 + y1), front: last && !down ? eave : null,
          west: w ? null : side(S, eave[0], eave[0] + 16, eave[1], eave[1] + 7, d, 0), east: e ? null : side(S, eave[0], eave[0] + 16, eave[1], eave[1] + 7, d, 1)}); }
      if (!up) push(out, {x: 0, y: -7, z: z * UP - 2, w: 16, d: 7, h: 2, top: cut(P, 0, 16, 0, 7)});      // (its scalloped far edge: over the wall's back)
      return;
    }
    const bits = [g(0, -1), g(-1, 0), g(1, 0), g(0, 1), g(0, 0, 1)].map((v) => (v ? 1 : 0)).join(""), stairs = kind === "stairs";
    if (stairs && !g(0, 0, 1)) {      // a step: two treads, the low half of its tile half its height, on the side it is climbed from
      const P = shotOf("st" + [x, y, z, Floors.ver, landVer], 16, 24, () => Floors.cell(kind, x, y, z, () => 0, () => shOf(z), 16, 1)), tone = P.px[20 * 16 + 7] || P.px[8 * 16 + 7] || 0xff5d6290;
      const [ux, uy] = [[0, -1], [1, 0], [-1, 0], [0, 1]].find(([dx, dy]) => solidAt(x + dx, y + dy, z + 1) && !solidAt(x + dx, y + dy, z + 2)) || [0, -1];
      for (const hi of [0, 1]) { const x0 = ux && (ux > 0) === !!hi ? 8 : 0, y0 = uy && (uy > 0) === !!hi ? 8 : 0, w = ux ? 8 : 16, d = uy ? 8 : 16, h = hi ? UP : UP / 2;
        push(out, {x: x0, y: y0, z: (z - 1) * UP, w, d, h, top: cut(P, x0, x0 + w, y0, y0 + d), front: cut(P, x0, x0 + w, 24 - h, 24), west: flat(tone, d, h, tone), east: flat(tone, d, h, tone)}); }
      return;
    }
    cast(out, x, y, 0, [-1, -1, 17, 17], 0, (z - floorAt(x, y)) * UP, true);
    const P = shotOf(stairs ? "st" + [x, y, z, Floors.ver, landVer] : "cell" + kind + bits, 16, 24, () => Floors.cell(kind, x, y, z, () => 0, () => shOf(z), 16, 1));
    const tone = P.px[20 * 16 + 7] || P.px[8 * 16 + 7] || 0xff5d6290;
    push(out, {x: 0, y: 0, z: (z - 1) * UP, w: 16, d: 16, h: UP, top: g(0, 0, 1) ? null : cut(P, 0, 16, 0, 16), front: g(0, 1) ? null : cut(P, 0, 16, 16, 24), west: g(-1, 0) ? null : flat(tone, 16, UP, tone), east: g(1, 0) ? null : flat(tone, 16, UP, tone)});
  }
  const is = (c, x, y) => "W%+#rm".includes(c) || (c === "g" && x !== undefined && gateSide(x, y));
  function stand(out, c, x, y, zl) {     // what stands at level zl of the tile
    if (!c) return;
    if (Structures.WALLS.includes(c)) {
      const cells = Floors.cells(x, y); let over = 0, cutLow = false;
      if (cells) for (const zc of cells.keys()) if (zc > zl && zc <= zl + Floors.STOREY) { over = zc; cutLow = hid(x, y, zc); }
      const p = myPos();      // (inside, the roof open: the walls south of you a low stub, as the cut leaves the rock south of your space; the others to their own height)
      wall(out, c, x, y, zl, cutLow ? (p && y > p.y ? 4 : 16) : over ? (over - 1 - zl) * UP : 12 / KF());
    } else if (c === "#") fence(out, x, y, zl * UP); else if (c === "g") sideGate(out, x, y, zl * UP);
    else decal(out, c, x, y, zl * UP);
  }
  function at(x, y) {
    const out = [], c = combAt(x, y), cells = Floors.cells(x, y);
    if (c && is(c, x, y)) stand(out, c, x, y, floorAt(x, y)); else if (c && shaded(c)) shade(out, c, x, y, floorAt(x, y) * UP, floorAt(x, y));      // (on the tile's lowest ground: in a cave, on its floor)
    if (cells) for (const [z, [kind, ch]] of cells) { if (hid(x, y, z)) continue; block(out, kind, x, y, z); if (ch && is(ch)) stand(out, ch, x, y, z); else if (ch && shaded(ch)) shade(out, ch, x, y, z * UP); }
    return out.length ? out : null;
  }
  // What is only planned, or would be put where you aim (build.js, intent.js): the same boxes, see-through (`ghost`: the engine draws one px in two of it).
  // item: what is put; z: the built block it is or stands on (none: on the ground); steps: a flight of stairs [[x, y, ground, top]...]. -> [[x, y, box]...], or null: no piece (a billboard, a ladder)
  const pieced = (item, steps, z) => !!steps || ((item === "roof" || item === "plank") && z !== undefined) || is(PLACEABLE_BLOCK[item] || "-");
  function ghost(item, x, y, z, steps) {
    if (!pieced(item, steps, z)) return null;
    const out = [], run = (tx, ty, fn) => { const l = []; ghosting = true; try { fn(l); } finally { ghosting = false; } for (const b of l) out.push([tx, ty, Object.assign(b, {ghost: true})]); };
    if (steps) for (const [tx, ty, g, t] of steps) for (let zz = g + 1; zz <= t; zz++) run(tx, ty, (l) => block(l, "stairs", tx, ty, zz));
    else if (item === "roof" || item === "plank") run(x, y, (l) => block(l, item, x, y, z));
    else run(x, y, (l) => stand(l, PLACEABLE_BLOCK[item], x, y, z === undefined ? floorAt(x, y) : z));
    return out;
  }
  function loose(x, y) { const cells = Floors.cells(x, y), out = []; if (cells) for (const [z, [, ch]] of cells) if (ch && !is(ch) && !hid(x, y, z)) out.push([ch, z]); return out; }
  // what the pieces hang on beside the land: what is built, where you are under it, the build cursor's level, who stands by a door
  function key() { const s = myAt; let d = ""; if (doorsAt.size > 300) doorsAt.clear(); for (const [x, y] of doorsAt.values()) if ("+g".includes(combAt(x, y) || "-") && doorOpen(x, y)) d += x + "," + y + ";"; return [Floors.ver, s ? [s.x, s.y, s.z] : "", Build.on ? Build.level() : "", sheet.id, d, HdSun.key(), HdLook.cam.pitch].join("|"); }
  return {at, is, loose, key, painted, ghost, pieced, card, shadow, foot, plans, CARD, sheet, room, pix};
})();
