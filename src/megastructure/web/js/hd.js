// The HD look (the game's only land view): ONE look on the surface and under ground. The land round you is drawn by VoxStyle
// (vox_style.js) at the art's own size, a tilted perspective, every face from the tileset, on a canvas of its own the page shows
// zoom times bigger (hd_view.js). Behind it the game's own sky (its curved horizon's). The game's frame (render.js) moves who walks, loads the land and paints nothing of it.
// Going down nothing switches: the land is always drawn whole, as it is (meadow, trees, sky, the day's light). When land hides you (a roof over you, or land
// in the eye's line to your feet) you are seen through an X-RAY WINDOW: a hole of your own space's shape (its floors' boxes seen from the eye, vox_style_win.js; a rim of the land a step darker,
// the ground's section, its own earth or stone, along its top edge), through which the land between the eye and your space is not drawn. Nothing is cut out of the land; it fades in over a tenth of a second, and is there before you step under the land (your space is looked for from the surface too). Trees, bushes, crops: upright
// billboards of their own sprites (objectSprite), px for px; furniture, walls, fences, built floors and roofs: small 3D
// pieces in the land (hd_things.js), a built house open over your head; you and the others: drawEntity at zoom 1.
const HdLook = (() => {
  const GROW = .25, EASE = .4, HOLD = 300, CAP = 20, R = 24;
  const cfg = {levels: [-9, 12], variants: 4, up: RELIEF_STEP, rock: {from: 5, lo: -512, n: 4}};
  const cam = {kind: "persp", pitch: 36, fov: 26};
  const api = {eye: null, get on() { return !!this.eye || (!!me && myId !== null); }, u: 0, ms: 0, build: 0, slice: 0, live: false, drew: false, get busy() { return !!gen; }, get win() { return eng ? eng.win : {n: 0, a: 0, tiles: []}; }, steep: 78.6, nowin: false, force: null, cam, bend: .03, faces: 0, builds: 0, n: 0};
  let camL = null, pitN = null, stage = 0, tilt = 0, flip = 0, covAt = -1e9, grow = 0, wantG = 0, genG = 0, shownG = 0, south = 8, gen = null, seen = null, eng = null, key = "", ver = -1, last = performance.now(), lit = null, hl = 0, hy = 0, since = 0, hurry = false, cand = null, candKey = "", noGL = false, wrote = false, keyNear = "", keyFar = "", slice1 = 0, camV = 0, genAt = null, landAt = null, held = false, heldAt = 0;
  const sprs = new Map(), lads = new Map(), things = new Map(), piles = new Map(), built = new Map(), stoodOf = new Map();
  const Z = () => zoom * DPR;   // (canvas px an art px: `zoom` CSS px, as the classic picture's. It was `zoom` canvas px: on a dense screen, a phone's, the land half the size and twice as far as it would show)
  const mix = (a, b, k) => Array.isArray(a) ? a.map((v, i) => v + (b[i] - v) * k) : a + (b - a) * k;
  function ent(p, now, z) {   // (a person or a creature, drawn by the game at zoom 1: one art px a px; z: the level it is put at)
    // (a FALL: the game says the body's height over the straight line between the two tiles' grounds (the classic picture's lift). Here a body stands at one tile's level, z: its height over THAT.
    // It was the game's number as it is: walking to a rim 12 high you rose 48 px into the air, then dropped 96 px in one frame as the fall began)
    const T = P, j = jumping(p, now), fl = j && falling(p, now), off = fl ? liftOf(p) / zoom - z * RELIEF_STEP : 0, up = j ? Math.max(0, Math.ceil((j.body + off) * (fl ? Math.cos(cam.pitch * Math.PI / 180) : 1))) : 0, fo = fl ? Math.round(j.body) - up : 0, w = T * 4, h = Math.ceil((T * 5 + up) / 32) * 32, base = h - T * 1.5 + fo;   // (a height as this eye sees it: its cosine; taller for a fall: the body and its name stay together)   // (its canvas in steps of 32 rows, the body at its foot: down a stair every hop made it again, and its place in the sprites' sheet)
    let pc = sprs.get(p) || document.createElement("canvas"); sprs.set(p, pc); if (pc.width !== w || pc.height !== h) { pc.width = w; pc.height = h; }
    const g = pc.getContext("2d", {willReadFrequently: true}); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, w, h); g.imageSmoothingEnabled = false;   // (its px are read each frame: its shadow is its shape now, hd_sun.js)
    const keep = ctx, kz = zoom, sx = (x) => w / 2 - T / 2 + (x - p.x) * T, sy = Object.assign((y) => base + (y - p.y) * T, {up: (y) => base + (y - p.y) * T, apart: true});   // (apart: a swimmer's wake is not in it: swim.js wakePicture)
    const rc = pc._r || (pc._r = HdView.recorder(g, false)); rc.reset();   // (what was asked of its canvas, as one number: the same as last frame: the same picture: not sent to the GPU again, its shadow not looked for again)
    ctx = rc.proxy; zoom = 1; p._hd = api.n; try { drawEntity(p, sx, sy, T, now / 1000, now); } catch (e) { /* (nothing to draw) */ } finally { ctx = keep; zoom = kz; }
    if (rc.hash !== pc._h) { pc._h = rc.hash; pc._v = (pc._v || 0) + 1; }
    return {canvas: pc, fx: w / 2, fy: Math.round(h - T), fo};
  }
  function thing(spr) {       // (a thing's sprite on a canvas of its own, once: its foot the middle of its tile's bottom)
    const [img, sx, sy, sw, sh, dx, dy] = spr, k = (img.src || img.id || "") + "|" + sx + "," + sy + "," + sw + "," + sh;
    let c = things.get(k);
    if (!c) { c = document.createElement("canvas"); c.width = sw; c.height = sh; const g = c.getContext("2d"); g.imageSmoothingEnabled = false; g.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh); things.set(k, c); }
    return {canvas: c, fx: 8 - dx, fy: 16 - dy, still: true, d: true};
  }
  const topAt = (x, y) => { const c = Voxels.host.column(x, y); return c && c.length ? c[c.length - 1] : 0; };
  const come = (x, y) => { for (let j = y - 12; j <= y + 6; j += 9) for (let i = x - 10; i <= x + 10; i += 10) if (!blockOf(i, j)) return false; return true; };   // (the blocks of the world round (x, y) are here: a land made before they came has nothing there)
  // where a tile's thing stands: the game has it on the tile's lowest ground. What grows under the sky (a tree, a bush, a flower, a crop) over a room dug under it: on the land's top, where it grew; while the x-ray window is on that tile it is not drawn (after)
  // (flowers stood on a cave's floor, a tree in a tunnel)
  const standAt = (c, x, y) => ("TFUtbvHf;\"w".includes(c) ? Math.max(topAt(x, y), floorAt(x, y)) : floorAt(x, y));
  const solidAt = (c, z) => { for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  // a bank's top: the pack's shore tile has a white line of foam along the water's edge, where the classic picture's water laps. Here the water lies a level under the bank:
  // the line stood up on the rim, a bright white line along a pond. Its white px take the earth px next inward.
  // a floor under the land (a cave's, a dug room's, a stair's tread): the rock's own paint from the tileset, and its texture: earth (the soil sheet, as dug ground has it), stone where the block is stone, most tiles one of the sheet's
  // speckled ones (its fine specks mostly, its pale blobs seldom). It was the tile's paint as on the surface: a cave under a meadow had a floor of grass, lit warm: flat yellow; dug ground the sheet's plain tile on every tile: one flat colour
  function under(x, y, z, px, at, st) {
    const g0 = gndAt(x, y), put = topAt(x, y) === z && matAt(x, y) === "d"; if (!put && (topAt(x, y) <= z || (g0 !== "." && g0 !== ","))) return false;   // (put: a block of earth put down: bare earth, no grass on it)
    const lv = VoxPaint.level(x, y, z), d = sheetData(lv >= 5 ? hillSheet(lv) : dugSheet("soil", Math.max(0, Math.min(3, -lv)))), [bx, by] = blobCell(255), pl = hash(x, y, 3) >= .8;   // (no darker than three layers down: under a roof the lantern is the light)
    const sx = pl ? bx * 16 : Math.floor(hash(x, y, 4) ** 2 * 5) * 16, sy = pl ? by * 16 : (5 + (hash(x, y, 5) < .5 ? 0 : 1)) * 16;
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) px[at + j * st + i] = d.px[(sy + j) * d.w + sx + i];
    if (!put) VoxPaint.rim(x, y, z, px, at, st); return true;   // (a put block of earth: the soil to its edges: the cap's own art has grass in its middle)
  }
  function shore(x, y, z, px, at, st) {
    const H0 = Voxels.host; if (under(x, y, z, px, at, st)) return; H0.paintTop(x, y, z, px, at, st); if (H0.water(x, y)) return;
    const white = (v) => (v >>> 24) > 127 && (v & 255) > 214 && (v >> 8 & 255) > 214 && (v >> 16 & 255) > 205;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) if (H0.water(x + dx, y + dy)) for (let n = 0; n < 16; n++) for (let k = 0; k < 4; k++) {
      const q = (m) => at + (dx ? n : dy > 0 ? 15 - m : m) * st + (dy ? n : dx > 0 ? 15 - m : m); if (!white(px[q(k)])) continue;
      let m = k + 1; while (m < 8 && white(px[q(m)])) m++; px[q(k)] = px[q(m)]; }
    for (const [dx, dy] of [[1, 1], [-1, 1], [1, -1], [-1, -1]]) if (H0.water(x + dx, y + dy)) for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) {   // (a corner's)
      const q = (a, b) => at + (dy > 0 ? 15 - b : b) * st + (dx > 0 ? 15 - a : a); if (white(px[q(i, j)])) px[q(i, j)] = px[q(5, 5)]; }
  }
  // the sea behind the land (hd_view.js show): the columns of the picture where the sea is really there, past the last land you see -> [[x0, x1]...] (it was the sea's tint all across: a sea behind every hill inland)
  let runsKey = "", runsOf = [];
  function seaRuns(w, tx, ty, cam2) {
    const k = [w, tx, ty, eng.stamp, cam2].join(); if (k === runsKey) return runsOf; runsKey = k; runsOf = []; const H0 = Voxels.host; let run = null;
    for (let x = tx - R; x <= tx + R + 2; x += 2) { let n = 0; for (let y = ty - 20; y <= ty - 12; y += 2) if (!H0.column(x, y) || H0.water(x, y)) n++;
      const sea = x <= tx + R && n >= 3, a = eng.at(x, ty - 14, 0), px = x <= tx - R ? 0 : x > tx + R ? w : Math.round(a[0]);
      if (sea && run === null) run = px; if (!sea && run !== null) { runsOf.push([run, px]); run = null; } }
    return runsOf;
  }
  // the hour's light on the land: the game's own (daylight.js: its tint, its wash, a lamp on each of you and each fire, in whole steps), put where this camera
  // puts them; under a roof (el) none of it. (It was the shader's `day` alone: the night's land as bright as noon under a night sky.) -> {wash, lit: the light's picture}
  // for the land's own painter to lay over what it draws (vox_style.js `hour`), or nothing at plain day
  function hour(w, h, list, el) {
    const ph = clock.phase || 0, tint = lightAt(ph).map((v) => v + (255 - v) * el), wash = washAt(ph), dark = Math.min(1, (1 - (.3 * tint[0] + .59 * tint[1] + .11 * tint[2]) / 255) / .36);
    if (wash[3] * (1 - el) <= .004 && dark <= .01) return null;
    const lift = opt("night") / 100 * .6; if (dark <= .2) return {wash: [wash[0], wash[1], wash[2], wash[3] * (1 - el)], tint: tint.map((v) => Math.round(v + (255 - v) * lift))};   // (no lamp shows: one colour, a px of it: it was a picture the screen's size sent to the GPU every frame of a morning)
    lit = lit || document.createElement("canvas"); if (lit.width !== w || lit.height !== h) { lit.width = w; lit.height = h; lit._k = ""; }
    const base = tint.map((v) => Math.round(v + (255 - v) * lift)), lamps = []; for (const s of list) if (s.lamp) { const a = eng.at(s.x, s.y, s.z); if (a) lamps.push(Math.round(a[0] * 4), Math.round(a[1] * 4), s.lamp); }
    const lk = [base, dark.toFixed(3), lamps, api.builds].join(), out = {wash: [wash[0], wash[1], wash[2], wash[3] * (1 - el)], lit}; if (lk === lit._k) return out; lit._k = lk; lit._v = (lit._v || 0) + 1;   // (the same lamps at the same places: the picture there is this frame's: not painted, not sent again)
    const q = lit.getContext("2d"); q.globalAlpha = 1; q.globalCompositeOperation = "source-over"; q.fillStyle = `rgb(${tint.map((v) => Math.round(v + (255 - v) * lift)).join()})`; q.fillRect(0, 0, w, h);
    if (dark > .2) { q.globalCompositeOperation = "lighter"; const k = (dark - .2) / .8;
      for (const s of list) if (s.lamp) { const a = eng.at(s.x, s.y, s.z), cl = topAt(Math.floor(s.x), Math.floor(s.y)) > s.z; if (!a) continue; if (cl) { q.save(); winPath(q, Math.floor(s.x), Math.floor(s.y)); q.clip(); }   // (a light under the land, your lantern, a fire in your room, lights what the window shows, not the grass over it: a campfire 14 levels down lit a ring on the meadow)
        lamp(q, a[0], a[1] - 8, s.lamp > 1 ? 64 : 42, s.lamp > 1 ? "rgb(255,176,96)" : "rgb(255,222,170)", (s.lamp > 1 ? 1.15 : .45) * k, [0, 0]); if (cl) q.restore(); } }
    q.globalAlpha = 1; return out;
  }
  // the px of the picture the window shows round (tx, ty): each of its tiles' floor, and the walls north and beside it up to its ceiling: a path on q
  function winPath(q, tx, ty) {
    q.beginPath(); const quad = (l) => { const a = l.map((v) => eng.at(...v)); let ar = 0; for (let i = 0; i < 4; i++) ar += a[i][0] * a[(i + 1) % 4][1] - a[(i + 1) % 4][0] * a[i][1]; if (ar < 0) a.reverse(); q.moveTo(...a[0]); for (let i = 1; i < 4; i++) q.lineTo(...a[i]); q.closePath(); };
    for (const [x, y, lo, hi] of eng.win.tiles) if (Math.abs(x - tx) <= 9 && Math.abs(y - ty) <= 9) { quad([[x, y, lo], [x + 1, y, lo], [x + 1, y + 1, lo], [x, y + 1, lo]]);
      for (const e of [[[x, y], [x + 1, y]], [[x, y], [x, y + 1]], [[x + 1, y], [x + 1, y + 1]]]) quad([[...e[0], lo], [...e[1], lo], [...e[1], hi], [...e[0], hi]]); }
  }
  // what is written and pointed at, over the picture, by the game's own painters (names, a health bar, an emote, what is said, a progress bar): they were
  // drawn at the classic picture's places, under this one. Their sx, sy: someone's own place as this camera has it (found by its x, its y), else measured from you.
  // (two parts. marks: what is pointed at and planned (corners, ghosts, the build cursor), all in whole art px: on the world's own canvas with the land (hd_view.js marks): they move with every step you take,
  // and the game's canvas, the screen's size, was wiped and painted again for them each frame. words: the letters, on the game's canvas: yours stand still while you walk)
  function written(p, now, words) {
    if (p.free && !words) return;
    const S = TS(), art = (a) => a && [Math.round(a[0] / zoom) * zoom, Math.round(a[1] / zoom) * zoom], F = art(api.screenOf(seen.at[0], seen.at[1], seen.at[2] + seen.lift)), who = (v, ax) => { for (const s of seen.list) if (s.q && s.q[ax] === v) { const a = s === seen.me ? F : art(api.screenOf(s.x, s.y, s.z)); return a && s.fo && ax === "y" ? [a[0], a[1] + s.fo * zoom] : a; } return null; };   // (fo: falling: its name with its body, ent)   // (art: a body's place as its picture has it, a whole art px: its name stands still over it (it slid a px or two against it at every step, and the canvas was wiped and painted again for that))
    const sx = (x) => { const a = who(x, "x"); return a ? a[0] - S / 2 : F[0] - S / 2 + (x - p.x) * S; }, fy = (y) => { const a = who(y, "y"); return a ? a[1] - S / 2 : F[1] - S / 2 + (y - p.y) * S; }, sy = Object.assign(fy, {up: fy, out: fy});
    const px = zoom / seen.k, t = now / 1000, snap = (v) => Math.round(v / px) * px, quad = (x, y, z) => [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => api.markOf(x + a, y + b, z));
    // (all of it in whole art px) corners: a quad's four corners, a third of each side; fill: a tile's face, row by row; ghost: a thing's own sprite where it would stand; rectOf: the px its picture takes
    const corners = (c, col) => { for (const [cl, o] of [["#5b3f36", px], [col, 0]]) { ctx.fillStyle = cl; c.forEach((a, i) => { for (const b of [c[(i + 1) % 4], c[(i + 3) % 4]]) { const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) * .3 / px)); for (let j = 0; j <= n; j++) ctx.fillRect(snap(a[0] + (b[0] - a[0]) * j / n * .3), snap(a[1] + (b[1] - a[1]) * j / n * .3) + o, px, px); } }); } };
    const fill = (c, col) => { ctx.fillStyle = col; const at = (a, b, y) => a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) || 1); for (let y = snap(c[0][1]); y < c[3][1]; y += px) { const l = snap(at(c[0], c[3], y)), r = snap(at(c[1], c[2], y)); ctx.fillRect(l, y, r - l, px); } };
    const rectOf = (spr, x, y, z = shown(x, y)) => { const f = api.screenOf(x + .5, y + 1, z), k = px; return [snap(f[0] - (8 - spr[5]) * k), snap(f[1] - (16 - spr[6]) * k), spr[3] * k, spr[4] * k]; };
    const edge = (a, b, col, dot) => { if (!a || !b) return; const n = Math.max(1, Math.ceil(Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) / px)); for (const [cl, o] of [["#5b3f36", px], [col, 0]]) { ctx.fillStyle = cl; for (let i = 0; i <= n; i++) if (!dot || (i >> 1) % 2 === 0) ctx.fillRect(snap(a[0] + (b[0] - a[0]) * i / n), snap(a[1] + (b[1] - a[1]) * i / n) + o, px, px); } };   // (a line in whole art px; dot: two on, two off)
    const ghost = (ch, x, y, a) => { const spr = ch && objectSprite(ch, x, y, t); if (!spr || !spr[0] || !spr[0].width) return; const r = rectOf(spr, x, y); ctx.globalAlpha = a; ctx.imageSmoothingEnabled = false; ctx.drawImage(spr[0], spr[1], spr[2], spr[3], spr[4], ...r); ctx.globalAlpha = 1; };
    // a cell of the land that would be dug into (keyboard.js `cell`: the wall beside you, at your level): its top, one level over your floor. (The corners sat on the wall's top: up at its ceiling, or on the meadow over it)
    const box = (r) => [[r[0], r[1]], [r[0] + r[2] - px, r[1]], [r[0] + r[2] - px, r[1] + r[3] - px], [r[0], r[1] + r[3] - px]], bound = (c) => { const xs = c.map((v) => v[0]), ys = c.map((v) => v[1]); return {x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)}; };
    if (!words) { ctx.save(); const m = seen.me; if (m) HdLevel.cut(ctx, m, api.screenOf(m.x, m.y, m.z), zoom / seen.k); }   // (no mark lies on your body: hd_level.js cut)
    if (words) { const at = Build.on && Build.S.at, s = at && myPos(), r = at && Build.S.rect; if (s && r) { const L1 = Build.level(); Keyhole.mark(r.x, r.y, r.h, L1 - myZ(s.x, s.y), landSolid(at.x, at.y, L1) && landSolid(at.x, at.y, L1 + 1), sx, sy, r.right); } }
    else if (Build.on) {   // build mode: what is planned, each on its own tile at its own height as this camera has it, and the cursor (the game drew them at the classic picture's places)
      for (const j of Build.S.plans.values()) { const c = quad(j.x, j.y, j.z); if (c.some((v) => !v)) continue;
        if (j.item !== "ladder" && !j.take && !j.dig && !HdThings.pieced(j.item, j.steps, j.up ? j.z : undefined)) ghost(PLACEABLE_BLOCK[j.item], j.x, j.y, j.state === "doing" ? .75 : .5);   // (pieces: in the land, see-through: pieces())
        fill(c, j.state === "bad" ? "rgba(230,80,70,.4)" : j.take ? "rgba(255,150,60,.3)" : j.state === "doing" ? "rgba(255,241,168,.35)" : "rgba(140,190,255,.28)"); if (j.dig) fill(c.map((v, i) => [v[0] + (c[(i + 2) % 4][0] - v[0]) * .2, v[1] + (c[(i + 2) % 4][1] - v[1]) * .2]), "rgba(60,36,30,.5)"); }
      const at = Build.S.at; if (at) { const c = quad(at.x, at.y, Build.level()), it = Build.aim().it, mx = (myPos() || at).x; if (it && it.ghost && it.ghost !== "ladder" && it.ok !== false && !HdThings.pieced(it.ghost, it.steps, it.draw ? undefined : it.z)) ghost(PLACEABLE_BLOCK[it.ghost], at.x, at.y, .7);
        Build.S.rect = Object.assign(bound(c), {under: mx !== at.x, right: mx < at.x}); Prompts.build(); Target.paint(ctx, api.art());   // (the cursor's cell, the block X takes: boxes in the land, target.js)
        }
    } else {          // the aim: what stands there, round its picture; a ghost of what would be put; else the corners of the tile as the land shows it; its keys beside it (prompts.js)
      const aim = aimedTile(), it = aim && aim.it, a = aim && aim.p, on = a && tile(a.x, a.y) && it && !it.info && !it.walk; let r = null, thing = false;
      if (on && it.ghost && it.ghost !== "ladder" && !HdThings.pieced(it.ghost, it.steps, it.draw ? undefined : it.z)) ghost(PLACEABLE_BLOCK[it.ghost], a.x, a.y, .7);
      if (on) { const e = it.ent && seen.list.find((s) => s.q && s.q.e === it.ent || s.q === it.ent), c0 = combAt(a.x, a.y), spr = !e && c0 && isObject(c0) && objectSprite(c0, a.x, a.y, t), f = e && api.screenOf(e.x, e.y, e.z);
        const cs = !e && seen.list.find((s) => s.card && s.tx === a.x && s.ty === a.y), cf = cs && api.screenOf(cs.x, cs.y, cs.z), pb = !e && !cs && c0 && HdThings.is(c0, a.x, a.y) ? boxed(a.x, a.y, seen.L * RELIEF_STEP) || boxed(a.x, a.y) : null;   // (round the piece as it is drawn: a card's own px, the boxes' corners)
        const c = e ? box([snap(f[0] - 8 * px), snap(f[1] - 12 * px), 16 * px, 16 * px]) : cs && cf ? box([snap(cf[0] - (cs.fx - cs.card.b[0]) * px), snap(cf[1] - (cs.fy - cs.card.b[1]) * px), (cs.card.b[2] - cs.card.b[0]) * px, (cs.card.b[3] - cs.card.b[1]) * px])
          : pb ? box([snap(pb.x), snap(pb.y), snap(pb.w) + px, snap(pb.h) + px]) : spr && spr[0] ? box(rectOf(spr, a.x, a.y, standAt(c0, a.x, a.y) > floorAt(a.x, a.y) ? standAt(c0, a.x, a.y) : undefined)) : null; thing = !!c;
        if (c) corners(c, it.ok === false ? "#e8554a" : "#fff8e8"); r = bound(c || quad(a.x, a.y, it.cell !== undefined ? it.cell : shown(a.x, a.y))); }
      Target.paint(ctx, api.art(), {thing, shown});   // (a cell of the land, what Space, X and R act on: boxes in the land, target.js; what stands keeps its brackets)
      WayShow.paint(ctx, api.markOf, px, now, 1, api.art().wall); Prompts.show(r, WayShow.rows(faceRows)); api.aim = r;   // (the way out of the ground, shown: wayshow.js)
    }
    if (!words) { ctx.restore(); return; }
    const ny = (y) => fy(y) - Math.max(0, 12 - 3 * zoom), nsy = Object.assign(ny, {up: ny, out: ny});   // (a name: higher where an art px is small, a phone's 2 px: the letters are 18 px whatever the zoom, and seen from behind a body's ears were in its name)
    for (const s of seen.list) if (s.q && s.q.e && (s.q.e.kind === "agent" || s.q.e.name)) drawNameplate(s.q, sx, nsy, S);
    for (const s of seen.list) if (s.q && s.q.e && (ANIMALS[s.q.e.kind] || !bubbles.some((b) => b.name === s.q.e.name))) drawEmote(s.q, sx, sy, S);
    drawProgress(sx, sy, S); HdFx.words(seen, api.screenOf); drawBubbles(sx, sy, S, t); ctx.textAlign = "start";   // (hearts lost, things gained: over heads, hd_fx.js)
  }
  // what is planned (build mode) and what the aim would put: see-through pieces in the land, each where and as it will stand (hd_things.js): a wall, a floor's planks, a roof, a flight of stairs, a bed
  function pieces(list) {
    const out = [], big = (k) => (k === "mossback" ? [30, 8] : ANIMALS[k] && ANIMALS[k].fw === 32 ? [16, 5] : [9, 4]), add = (item, x, y, z, steps) => { const l = HdThings.ghost(item, x, y, z, steps); if (l) out.push(...l); };
    for (const s of list) if (s.q || s.pile) { const [w, d] = s.pile ? [8, 3] : big(s.q.e && s.q.e.kind); for (const b of HdThings.shadow(w, d, (s.zs === undefined ? s.z : s.zs) * RELIEF_STEP + .5)) out.push([s.x, s.y + (s.pile ? .08 : .42), b]); if (s.q) HdSun.body(out, s); }   // (the shadow under each body and each pile: on the ground where its feet are drawn)
    HdThings.plans.clear(); if (Build.on) for (const j of Build.S.plans.values()) if (!j.take && !j.dig && j.state !== "bad" && "W%+".includes(PLACEABLE_BLOCK[j.item] || "-")) HdThings.plans.add(j.x + "," + j.y + "," + (j.up ? j.z : floorAt(j.x, j.y)));   // (planned walls join each other)
    if (Build.on) for (const j of Build.S.plans.values()) if (!j.take && !j.dig && j.state !== "bad") add(j.item, j.x, j.y, j.up ? j.z : undefined, j.steps);
    const a = Build.on ? Build.aim() : aimedTile(), it = a && a.it; if (a && a.p && it && it.ghost && it.ok !== false && !it.info && !it.walk) add(it.ghost, a.p.x, a.p.y, it.z !== undefined && !it.draw ? it.z : undefined, it.steps);
    return out;
  }
  // the game's sky with its horizon where ground at the eye's own level meets it, at the top of its bend (it was the classic picture's horizon, higher: a wide empty band
  // between the sky and the land, a third of a phone held upright). Fixed to the eye: its pitch and the screen, nothing of the land (eyeLine)
  api.sky = (t) => { const s = Curve.sky(t); return api.on && hl ? Object.assign({}, s, {line: Math.round(hl) * zoom}) : s; };
  let hKey = "", hRaw = 1e9;   // (the skyline is looked for when you change tile, level or tilt: it was 45 points of the land put through the camera every frame, .3 ms of a sprint's frame on a phone)
  function horizon(tx, ty, L) { const hk = [tx, ty, L, cam.pitch.toFixed(1), Math.round(camL * 8), eng.stamp, api.builds, !!gen].join(); let y = hRaw; if (hk !== hKey) { hKey = hk; y = -1e9; for (let dx = -18; dx <= 18; dx += 9) { let m = 1e9; for (let dn = 6; dn <= 22; dn += 2) { const c = Voxels.host.column(tx + dx, ty - dn), a = eng.at(tx + dx + .5, ty - dn, c && c.length ? c[c.length - 1] : L); if (a) m = Math.min(m, a[1]); } if (m < 1e8) y = Math.max(y, m); } if (y < -1e8) y = 1e9; hRaw = y; } hy = y < 1e8 ? y : -1e9; }   // (hy: the land's own skyline north of you, five columns across: where the far rows are a little soft, and what bare() counts under)
  // the sky's line: where level ground at the eye's level (at: the eye's point, as drawn) is highest on the screen, past the bend. It moves only with the pitch (and the screen's size): a real sky
  // does not move with the land in front of it. It came down to the lowest of the land's skylines north of you, eased: past a mountain the whole sky (sun, clouds, far hills) slid up
  // its side and down again, 58 art px walking 12 tiles to it. Where the land ends lower (a hill top), the band between is the far land's (hd_view.js skyOf), not a sky moved down to it
  let eKey = "", eY = 0;
  function eyeLine(at, w, h) { const k = [cam.pitch.toFixed(2), cam.fov, api.bend, w, h].join(); if (k !== eKey) { let m = 1e9; for (let dn = 1; dn <= 120; dn++) { const a = eng.at(at[0], at[1] - dn, at[2] - .5); if (a && isFinite(a[1])) m = Math.min(m, a[1]); } eKey = k; eY = m < 1e8 ? m : 0; } return eY; }
  function after() {
    const now = performance.now(), dt = Math.min(.1, (now - last) / 1000); last = now; api.n++;   // (n: this look's frames: who it drew in the last one, ent)
    const p = api.eye ? api.eye() : ents.get("agent" + myId); if (!p) return;   // (api.eye: the first screen, title_scene.js: nobody is you: the eye looks at a place {x, y, z, free}: its level, the surface's pitch, no window, nothing aimed at)
    const H0 = Voxels.host, wet = (x, y) => H0.water && H0.water(x, y) && H0.waterTop ? H0.waterTop(x, y) : -1e9;   // (in water: you stand at its face)
    const t0 = performance.now(), [L, Lf] = p.free ? [p.z, p.z] : HdLevel.of(p, now), tx = Math.round(p.x), ty = Math.round(p.y);   // (your level, and the same between two tiles: hd_level.js. It was the land's top until the classic x-ray had opened: down a covered stair you were drawn on the grass over it)
    const w = Math.ceil(cv.width / Z()), h = Math.ceil(cv.height / Z());
    // a screen held upright: the eye looks from higher (36 to 52 degrees), or half of it was sky and the land ran out under you; and what stands south of you is drawn as far as the screen shows (it was 6 rows: trees came in half way up a tall screen)
    const base = 36 + 16 * Math.max(0, Math.min(1, h / w - 1)); south = Math.min(R, Math.ceil(h / 32 / Math.sin(base * Math.PI / 180)) + 3 + Math.ceil(Math.max(0, topAt(tx, ty) - L) * .9));   // (deep under the land its top south of you is nearer the eye: more rows of it show)
    // the more the land shuts you in, the steeper the eye looks down (api.steep): 78.6 degrees when your feet are a level (your height) under the land round you (hd_level.js steep: one rule). (It was 68 when a level was 8 px: tan 78.6 = 2 tan 68, a cube's 16 px seen from it are the 3 px a level was on the screen: a hole, a gorge, a shaft hide no more of you, and show as much of their floor, as they did) The window is then a
    // hole seen from above, your room's walls all round it, and what is between the eye and you is a few tiles of land, not a hillside. It eases over 400 ms.
    const sw = p.free ? 0 : +HdLevel.steep(tx, ty, L, landVer);   // (two pitches, not one a level: the eye would tilt at every step of a stair. A shallow place keeps the surface's pitch. In and out by the land's shape, hd_level.js)
    if (sw === stage) flip = now; else if (sw || now - flip > HOLD) { stage = sw; flip = now; }   // (back to the surface's pitch only after 300 ms of open sky: along a roof's edge the eye went up and down at every tile)
    // (the eye tilts over 400 ms, slow at both ends, the window opening with it: it was most of the way in 8 frames, one sudden change)
    const want = base + (api.steep - base) * stage; tilt = pitN === null ? stage : Math.max(0, Math.min(1, tilt + (stage ? 1 : -1) * Math.min(dt, .034) / EASE)); pitN = base + (api.steep - base) * tilt * tilt * (3 - 2 * tilt); cam.pitch = pitN; cam.base = base; cam.want = want;
    const kS = eyeRise(want), cov0 = p.free ? false : api.force !== null ? api.force > 0 : HdLevel.under(tx, ty, L), cov = cov0 || (api.force === null && now - covAt < HOLD), dep = p.free ? 0 : Math.max(0, topAt(tx, ty) - L);
    // IN A HOLE SEEN FROM ABOVE you are drawn no deeper than the eye sees into it past its south rim: lifted by the land over the eye's line on the tile south of you, your feet on that rim's line, whole, cut by it (hd_level.js `lift`)
    const lift = p.free || cov0 ? 0 : HdLevel.lift(tx, ty, L, cam.pitch, p.e && swimsAt(p, p.e) ? SWIM.sink : 0) * tilt, liftD = p.free || cov0 ? 0 : HdLevel.lift(tx, ty, L, cam.pitch) * tilt;
    // (liftD: the height your sprite's depth is taken at: a walker's lift. A swimmer is drawn higher, its waterline on the rim, but stands as deep: the bank in front still hides its legs under the water and its shadow on the bottom)   // (no pitch below 90 shows a deep 1x1 floor inside its rim: your body was drawn one px in two on the meadow south of the hole, "a ghost on the grass")
    const own = HdLevel.own(tx, ty, L, cov0);   // (the window's boxes that are yours before your space is found: your tile and the covered ones you came from)
    if (cov0) covAt = now;   // (the window shuts 300 ms after the land last hid you, with the eye's tilt)
    grow = cov ? Math.min(CAP, grow + dt / GROW * CAP) : Math.max(0, grow - dt / GROW * CAP); api.u = grow / CAP; const st = cov ? CAP : 0;   // (u: how open the window is as this file counts it; the painter eases its own, vox_style.js)
    eng = eng || VoxStyle.create(Object.assign({}, Voxels.host, {paintTop: shore, models: (x, y, cz) => { const a = Models.at(x, y), b = floorAt(x, y) > cz ? null : HdThings.at(x, y); return a && b ? a.concat(b) : a || b; },
      chunkKey: (x0, y0, n) => { let c = built.get(x0 + "," + y0); if (!c || c[0] !== Floors.ver) { let f = ""; for (let y = y0; y < y0 + n && !f; y++) for (let x = x0; x < x0 + n; x++) if (Floors.any(x, y)) { f = "f"; break; } if (built.size > 2000) built.clear(); built.set(x0 + "," + y0, c = [Floors.ver, f]); } const fl = c[1];   // (what stands in a chunk hangs on the hour, what is built, open doors; where you are only if something is built in it: a roof over your head is open. And on the blocks of the world that have come, its own and the ones beside it)
        return (fl ? keyNear : keyFar) + fl + [[0, 0], [-1, 0], [n, 0], [0, -1], [0, n]].map(([i, j]) => (blockOf(x0 + i, y0 + j) ? 1 : 0)).join(""); }}), cfg);   // (what is built and put down: small 3D pieces, hd_things.js)
    if (eng.lost) { eng.forget(); key = ""; }   // (a tile that changed: drawTile, below: its chunk alone is made again. It was the whole land, and all its paints, at every change)
    keyNear = HdThings.key(); keyFar = HdThings.key(false); const rx = Math.min(R, Math.ceil(w / 32 * 1.4) + 3), k = [tx, ty, L, st, keyNear, eng.stamp, rx, south].join();
    const wg = cov ? CAP : 0; if (wg !== wantG) { wantG = wg; since = now; }   // (since: when land came over you or left; api.lag: ms from then to the land made with your space's window, or with none)
    if (k !== key && !gen) { gen = eng.steps(tx, ty, L, {r: R, rx, rs: south + 1, deep: 20, sea: 1, win: st ? {reach: 24} : {reach: 7, walk: true}}); key = k; genG = st; hurry = st !== shownG; api.build = 0; api.builds++; genAt = come(tx, ty) ? [tx, ty] : null; }   // (one land at a time: the next is made when this one is done)
    if (gen) { const b0 = performance.now(); while (performance.now() - b0 < (p.rush || held ? 12 : hurry || st ? 5 : 2.5)) if (gen.next().done) { gen = null; break; } api.build = Math.max(api.build, performance.now() - b0); slice1 = performance.now() - b0; api.slice = Math.max(api.slice, slice1); api.water = eng.water;   // (the chunks that are new or changed, a tile a step, 2.5 ms a frame (5 under the land); what was drawn stays till it is done)
      if (!gen) { shownG = genG; landAt = genAt; if (genG === wantG && since) { api.lag = performance.now() - since; since = 0; } } }
    // NEVER THE LAND UNPAINTED: after a teleport, waking again, arriving, the picture on the screen stays as it was (no new frame: the land, you, the words) until a land made HERE is done, with the blocks
    // round you come (2.5 s at the most). For 0.3 to 1 s the trees and you stood on the backdrop's flat grey and the sea's blue band, the land not made yet
    held = !p.free && (!landAt || Math.abs(landAt[0] - tx) > 8 || Math.abs(landAt[1] - ty) > 8); if (!held) heldAt = 0; else if (!heldAt) heldAt = now; if (held && now - heldAt > 2500) held = false;
    // the eye's level follows yours: a step over some 150 ms; a FALL: the eye stays while your body is in the air (the land steady, the body coming down it; at most 9 levels over where you will land), then comes
    // down to you slow at both ends (a spring, critically damped, its exact answer for any frame's length: .4 s for 12 levels. Stepped a frame at a time it ran away when a frame took over 83 ms: a slow phone). (Over 8 levels it went there in one frame: off the gorge's rim more than half the picture changed at once, your body in the top quarter of it)
    { const fl = falling(p, now), air = fl && fl.air, far = camL !== null && Math.abs(Lf - camL); if (air) camV = 0;
      if (camL === null || far > 40) { camL = Lf; camV = 0; } else if (air) camL = Math.max(Math.min(camL, L + 9), camL - 40 * dt); else if (far > 3 || camV) { const e = camL - Lf, a = camV + 12 * e, q = Math.exp(-12 * dt); camL = Lf + (e + a * dt) * q; camV = (camV - 12 * a * dt) * q; if (Math.abs(Lf - camL) < .07 && Math.abs(camV) < 1) { camL = Lf; camV = 0; } }
      else camL = far < .07 ? Lf : camL + (Lf - camL) * (1 - Math.exp(-dt / .1)); }   // (Lf: your level between two tiles, on the line between their heights: down a stair the eye goes down a slope, not a step a tile)
    const list = [];
    const stood = (c, x, y, z, gh, m) => {      // a thing that stands: furniture as its card (hd_things.js: px for px, its top leaning with where it is on the screen), the rest a billboard
      if (c === "l") { const k = [x, y, z, landVer, Floors.ver].join(), ln = Climb.lean(x, y, z); let lc = lads.get(k); if (!lc) { if (lads.size > 60) lads.clear(); const LH = Math.ceil((shOf(ln ? ln.top - z : 2) + 48) / 16) * 16, R0 = LH - 32, a = HdThings.painted(48, LH, () => Climb.drawLadder(x, y, z, (X) => 16 + (X - x) * 16, (Y) => R0 + (Y - y) * 16 + shOf(z), 16, 1)); lc = document.createElement("canvas"); lc.width = 48; lc.height = LH;
        const q = lc.getContext("2d"); q.drawImage(a, 0, 0, 48, R0 - 10, 0, 12, 48, R0 - 10); q.drawImage(a, 0, R0 + 2, 48, LH - R0 - 2, 0, R0 + 2, 48, LH - R0 - 2); lads.set(k, lc); }   // (the game's picture of it runs 12 px on, a tile's depth in the classic picture: here it stood over the rim. Three rungs taken out of its middle; its canvas as tall as the wall it leans on: a deep shaft's ladder was cut at 128 px)   // (a ladder: a standing face of the land, a px of it a px of the land's own fronts: as tall as the wall it leans on at any pitch. Upright px for px it stood three tiles over the rim of a shaft)
        list.push({canvas: lc, fx: 24, fy: lc.height - 16, x: x + .5, y: y + (ln && ln.dy < 0 ? .12 : ln && ln.dy > 0 ? .9 : .5), z, flat: true, still: true, d: true, tx: x, ty: y, ghost: gh}); return; }
      const s = objectSprite(c, x, y, now / 1000); if (!s || !s[0] || !s[0].width) return;
      const o = m || {}; if (o.it && o.img === s[0] && o.sx === s[1] && o.sy === s[2] && o.sw === s[3] && o.sh === s[4] && o.dx === s[5] && o.dy === s[6]) { o.it.fade = undefined; list.push(o.it); return; }   // (m: what this thing was last drawn as (cand): the same picture, the same entry. Its card, foot, bounds and canvas were looked for again for every thing, every frame: a fifth of a still frame's script)
      const cd = HdThings.card(c, x, y, s);
      const r2 = cd || c === "g" ? 0 : HdThings.foot(c, s), plain = cd || c === "g" ? null : {fy: r2, card: {b: spriteBounds(s[0], s[1], s[2], s[3], s[4]) || [0, 0, s[3], s[4]]}};   // (each stands where its foot is in its tile, as the game has it: they stood at the tile's south edge, their feet half a tile north of their shadow)
      const it = Object.assign(cd ? {} : thing(s), cd, {x: x + .5, y: y + (cd ? cd.y : plain ? (s[6] + r2) / 16 : 1), z, lamp: c === "^" || c === "x" ? 2 : 0, flat: c === "g", tx: x, ty: y, card: cd}, plain);   // (flat: a gate: a standing face of the land a tile wide, vox_style.js)
      Object.assign(o, {img: s[0], sx: s[1], sy: s[2], sw: s[3], sh: s[4], dx: s[5], dy: s[6], it}); list.push(it);
    };
    const memo = (c, x, y, z) => { const k = c + "," + x + "," + y + "," + z; let o = stoodOf.get(k); if (!o) { if (stoodOf.size > 6000) stoodOf.clear(); stoodOf.set(k, o = {}); } return o; };   // (a thing's last entry, found when what stands is looked for, not each frame)
    const ck = [tx, ty, L, landVer, Floors.ver, api.builds, !!gen, Math.floor(now / 250)].join();   // (what stands: looked for four times a second and when you or the land move, not on 2400 tiles every frame)
    if (ck !== candKey) { candKey = ck; cand = []; for (let y = ty - R; y <= ty + south; y++) for (let x = tx - R; x <= tx + R; x++) {
      const c = combAt(x, y), up = Floors.any(x, y) ? HdThings.loose(x, y) : null; if (up) for (const [ch, z] of up) cand.push([ch, x, y, z, memo(ch, x, y, z)]);   // (what stands on a built block)
      if (c && isObject(c) && !HdThings.is(c, x, y)) { const z = standAt(c, x, y); cand.push([c, x, y, z, memo(c, x, y, z)]); }      // (not the boxes of the land: hd_things.js)
    } }
    { const wmp = winMap(); HdEase.frame(now); for (const [c, x, y, z, m] of cand) { const n0 = list.length, a = z > floorAt(x, y) ? HdEase.of(x + "," + y, !wmp.has(x + "," + y)) : 1; if (a > 0) stood(c, x, y, z, false, m); if (a < 1) for (let i = n0; i < list.length; i++) list[i].fade = a; } }   // (what grows on ground the window leaves out is left out with it: one px in two of a flower hung over your room's floor; it goes and comes over 120 ms, hd_ease.js: a tree over your room was gone in one frame)
    // a ladder that would be put (the aim's, on your own tile in a shaft; build mode's plans): the ladder's own standing face where it will stand, as tall as its wall, pale (it was an upright picture laid over the frame: at 68 degrees two tiles over the shaft's rim, and not where the ladder comes)
    { const a = Build.on ? Build.aim() : aimedTile(), it = a && a.it, q = it && (it.own || a.p); if (q && it.ghost === "ladder" && it.z !== undefined && it.ok !== false && !it.info) stood("l", q.x, q.y, it.z, true);
      if (Build.on) for (const j of Build.S.plans.values()) if (j.item === "ladder" && !j.take && j.state !== "bad") stood("l", j.x, j.y, j.z, true); }
    for (const [ix, iy, pile] of groundItems) if (Math.abs(ix - tx) <= R && iy >= ty - R && iy <= ty + south && !lootAt(ix, iy)) {   // (its drops still hopping in: the pile once they have landed, hd_fx.js)   // what lies on the ground: its small icons as the game lays them (loot.js), a px a px (they were not drawn in this look)
      const names = Object.keys(pile).slice(0, 3), k = names.join(); let c = piles.get(k);
      if (!c) { c = document.createElement("canvas"); c.width = 24; c.height = 16; const g = c.getContext("2d"); names.forEach((n, i) => { const [dx, dy] = pileAt(i, names.length); g.drawImage(ghostIcon(n), 7 + dx, 3 + dy); }); piles.set(k, c); }
      list.push({canvas: c, fx: 12, fy: 14 + Math.round(Math.sin(now / 1000 * 2.4 + ix * 1.3 + iy) + 1), still: true, d: true, pile: true, x: ix + .5, y: iy + .7, z: floorAt(ix, iy)});   // (it hovers, as in the classic picture: 0 to 2 px, a whole px at a time)
    }
    const wmB = winMap(), wr = wmB.size ? winRect() : null;   // UNDER A ROOF nobody up on the land over you is seen: over the window, or over the land round it (in the window's box on the screen); only who is in your space (like Minecraft: no mob through the ceiling)
    for (const q of ents.values()) if (q.x !== undefined && Math.abs(q.x - p.x) < 16 && Math.abs(q.y - p.y) < 12) {
      const qx = Math.round(q.x), qy = Math.round(q.y), z = q === p ? Lf + lift : FLOORS && Floors.any(qx, qy) ? Floors.standOf(q, qx, qy) : q.e && typeof q.e.z === "number" && !H0.water(qx, qy) ? q.e.z : Math.max(topAt(qx, qy), wet(qx, qy));   // (on a built floor: at its height; in a cave: at the level the server has them. They were put on the land's top: a friend in your room stood on the grass over it)
      if (q !== p && z < topAt(qx, qy)) { const c = H0.column(qx, qy), b = winMap().get(qx + "," + qy); let over = false; for (let zz = z + 1; zz <= topAt(qx, qy) && !over; zz++) over = solidAt(c, zz); if (over && !(b && z >= b[0] - 1 && z <= b[1])) continue; }
      if (q !== p && wmB.size) { const b = wmB.get(qx + "," + qy), a = !b && eng.at(q.x + .5, q.y + .5, z); if (!(b ? z >= b[0] - 1 && z <= b[1] : Math.abs(z - L) <= 1) && (b || (a && wr && a[0] + 6 > wr[0] && a[0] - 6 < wr[2] && a[1] > wr[1] && a[1] - 14 < wr[3]))) continue; }   // (not in your space: on the window's tile at another level, or its body in the window's box: hidden, its name with it. It was drawn, the ground under its feet kept one px in two: a hen over your head read as in the cave with you)   // (under land the window is not on: not seen, nor their name)
      const s = ent(q, now, z);
      list.push({canvas: s.canvas, fx: s.fx, fy: s.fy, fo: s.fo, x: q.x + .5, y: q.y + .5, z, zh: q === p ? Lf + liftD : undefined, zs: q === p ? L : z, d: q !== p, top: q === p, on: true, q, lamp: q.e && q.e.kind === "agent" ? (q === p && dep > 0 ? 2 : 1) : 0});   // (under the land your lantern is the light)   // (you: never hidden by land)
      const wk = q.wake && q.wake.length && wakePicture(q, now);   // (a swimmer's wake: a picture of its own lying on the water, no shadow)
      if (wk) list.push({canvas: wk.canvas, fx: wk.fx, fy: wk.fy, x: q.x + .5, y: q.y + .5, z, lie: true});
    }
    HdFx.add(list, p, now, dt);   // (what moves by itself: chips, smoke, drops, orbs, flames, a tree falling: hd_fx.js)
    list.sort((a, b) => a.y - b.y);
    const snap = (v) => Math.round(v * 16) / 16;
    const sky = typeof Curve !== "undefined" && Curve.on ? api.sky(now / 1000) : null, low = sky ? sky.low : [.62, .78, .86];   // (the sky stays over the far land down to 6 levels; from 10 down none of it, no sun: the dark of the earth)
    const wl = WaterBed.view(Voxels.engine, now / 1000), day = 1, ed = h / (32 * Math.tan(cam.fov * Math.PI / 360));   // (the eye's distance: fog counts from there)
    const light = {amb: .8, lr: 8, day, fog: [ed + 4, ed + 22], fogc: low, clear: [0, 0, 0], ca: 0, sun: HdSun.sun, rim: .25, wa: .92, wtint: wl && wl.tint ? wl.tint.subarray(0, 20) : null};
    let pic = eng.draw({w, h, cam, at: [snap(p.x + .5), snap(p.y + .5), Math.round(camL * 8) / 8 + .5], bend: api.bend, t: now / 1000, light,
      water: typeof waterCv !== "undefined" && waterView ? {canvas: waterCv, x: waterView.x, y: waterView.y, ver: Voxels.wver} : null, dep, own, rim: HdLevel.rim(tx, ty, L), hole: tilt * HdEase.of("shut", !p.free && HdLevel.shut(tx, ty, L, kS)), hid: lift > 0 ? 0 : 1, behind: p.free || cov0 || lift > 0 ? 0 : HdEase.of("behind", HdLevel.over(tx, ty, L, kS) >= 1), win: api.nowin ? 0 : 1, sprites: list, way: WayShow.land(), ghosts: pieces(list), hour: hour(w, h, list, 0)});
    if (!pic) { noGL = true; return; }
    seen = {tx, ty, L, lift, rim: HdLevel.rim(tx, ty, L), top: tilt > .5 && !cov0, ks: eyeRise(cam.pitch), k: 1, me: list.find((q) => q.top), list, at: [snap(p.x + .5), snap(p.y + .5), Lf]}; horizon(tx, ty, L + dep); hl = Math.max(8, eyeLine([snap(p.x + .5), snap(p.y + .5), Math.round(camL * 8) / 8 + .5], w, h) + 2);   // (the horizon is the surface's, however deep you are)   // (at: where the eye looks: you, to a px of the land: your own name is written from there)
    api.faces = eng.faces; api.models = eng.models;
    // the land's picture over the backdrop on the world's own canvas, at the art's own size (hd_view.js): put together only when one of them is new; under a roof the sky stays as a band over the earth's far edge
    api.held = held; if (held) { api.ms = performance.now() - t0; return; }   // (the last picture stays: see `held`)
    api.drew = HdView.show({w, h, pic, marks: HdView.marks(() => written(p, now, false)), fresh: eng.fresh, sky, runs: seaRuns(w, tx, ty, [snap(p.x), snap(p.y), L, h, cam.pitch].join())});
    wrote = HdView.words(() => written(p, now, true), now);
    api.ms = performance.now() - t0;
  }
  // the px a tile's boxes take on the screen (hd_things.js: a wall, a fence, a door): {x, y, w, h}, or null
  function boxed(x, y, lo) {   // (lo: only the boxes of the storey that starts at that height, px: the aim's corners went round a wall, the wall over it and the roof: two pairs of brackets a storey apart)
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const b of HdThings.at(x, y) || []) if (!b.shade && (lo === undefined || (b.z < lo + 20 && b.z + b.h > lo - 2))) for (let n = 0; n < 8; n++) { const p = api.screenOf(x + (b.x + (n & 1) * b.w) / 16, y + (b.y + (n >> 1 & 1) * b.d) / 16, (b.z + (n >> 2) * b.h) / RELIEF_STEP); if (p) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); } }
    return x1 > x0 ? {x: x0, y: y0, w: x1 - x0, h: y1 - y0} : null;
  }
  // what is under the pointer (client px): the nearest top drawn there, as the land shows it (in the x-ray window: your space's floors, the land over them is not drawn)
  Object.defineProperty(api, "level", {get: () => [seen ? seen.L : null, camL, seen ? seen.at[2] : null, seen ? seen.lift : 0, seen ? seen.rim : null]});   // (tests: your level as the picture has it, the eye's, yours between two tiles, how much you are lifted in a hole and its rim)
  api.forget = () => { if (eng) { eng.forget(); key = ""; } };   // (tests: the land and its paints wiped, as when the paints ran out (eng.lost), at once: while a land is being made too)
  api.spaceAt = (x, y) => (eng ? eng.spaceAt(x, y) : null); api.winAt = (x, y) => winMap().get(x + "," + y) || null;   // (tests: a tile of your space, vox_style.js; a tile of the window: [floor, ceiling])
  let wmV = -1, wm = new Map(); const winMap = () => { const w = eng ? eng.win : null; if (!w || !w.n || w.a <= 0) { if (wm.size) wm = new Map(); wmV = -1; return wm; } if (w.tiles !== wmV) { wmV = w.tiles; wm = new Map(); for (const [x, y, lo, hi] of w.tiles) { const k = x + "," + y, o = wm.get(k); wm.set(k, o ? [Math.min(o[0], lo), Math.max(o[1], hi)] : [lo, hi]); } } return wm; };   // (the window's tiles now: "x,y" -> [floor, ceiling])
  const winRect = () => { let r = null; for (const [x, y, lo, hi] of eng.win.tiles) for (const z of [lo, hi + 1]) for (const [a, b] of [[x, y], [x + 1, y], [x, y + 1], [x + 1, y + 1]]) { const s = eng.at(a, b, z); if (s) r = r ? [Math.min(r[0], s[0]), Math.min(r[1], s[1]), Math.max(r[2], s[0]), Math.max(r[3], s[1])] : [s[0], s[1], s[0], s[1]]; } return r; };   // (the window's box on the screen, art px: its boxes' corners, floor and ceiling)
  // a tile's height as the picture shows it: the land's top; in the window your space's floor, and the top of the wall beside it (its ceiling's height): the aim's corners go there, not up on the meadow over it
  const shown = (x, y) => { const t = topAt(x, y), m = winMap(), b = m.get(x + "," + y); if (b) return Math.min(t, b[0]); for (const [dx, dy] of [[0, 1], [1, 0], [-1, 0], [0, -1]]) { const n = m.get((x + dx) + "," + (y + dy)); if (n && n[1] < t) return n[1]; } return t; };
  // for what is drawn in the marks pass by others (buildghost.js): an art px there (u), a place's px (at), and is a place behind land as the eye sees it (land south of it over the eye's line to it: eyeRise levels a tile)
  api.markOf = (x, y, z) => api.screenOf(x, y, HdLevel.raise(z, seen));   // (where a mark of yours is: lifted with you in a hole, hd_level.js raise)
  api.art = () => (seen ? {u: zoom / seen.k, at: api.markOf, behind: (x, y, Z0) => { const z = HdLevel.raise(Z0, seen), k = eyeRise(cam.pitch), y0 = Math.floor(y); for (let d = 1; d <= 8; d++) if (topAt(Math.floor(x), y0 + d) > z + (y0 + d - y) * k) return true; return false; }, wall: (x, y, z) => { const f = HdLevel.wall(x, y, z, seen); return f ? (X, Y, Z) => api.screenOf(...HdLevel.wallAt(X, Y, Z, seen, f)) : null; },
    body: seen.me ? HdLevel.body(seen.me, api.screenOf(seen.me.x, seen.me.y, seen.me.z), zoom / seen.k) : null} : null);   // (wall: a cell in the wall between the eye and you -> where its places are drawn, hd_level.js wallAt; body: your sprite's box)
  api.screenOf = (x, y, z) => { if (!eng || !seen) return null; const a = eng.at(x, y, z); return a && [a[0] * zoom / seen.k, a[1] * zoom / seen.k]; };
  // -> the tile under the pointer: what the window shows first (your space's floors, the fronts of the walls north of them: the land over them is not drawn, so it is not pointed at); then from the south (the nearest) north, the first whose south front or whose top is under it (a front: face, down: levels under its top, as mouse.js). zf: its height, if not the land's as shown (build mode)
  api.pick = (mx, my, zf) => {
    if (!eng || !seen) return null;
    const inq = (P, q) => { let s = 0; for (let i = 0; i < 4; i++) { const a = q[i], b = q[(i + 1) % 4], c = (b[0] - a[0]) * (P[1] - a[1]) - (b[1] - a[1]) * (P[0] - a[0]); if (c && s && Math.sign(c) !== s) return false; if (c) s = Math.sign(c); } return true; };
    const wmp = winMap(), flr = (x, y) => { const b = wmp.get(x + "," + y), t = topAt(x, y); return b ? Math.min(t, b[0]) : t; }, zo = (x, y) => (zf ? zf(x, y) : Models.up(x, y) ? liftAt(x, y) / zoom / RELIEF_STEP : flr(x, y)), part = (q) => Math.max(0, Math.min(.999, (my - Math.min(q[0][1], q[1][1])) / Math.max(1, Math.max(q[2][1], q[3][1]) - Math.min(q[0][1], q[1][1]))));
    if (!zf && wmp.size) for (const [x, y, lo, hi] of eng.win.tiles.slice().sort((a, b) => b[1] - a[1])) { const q = [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]].map(([a, b]) => api.screenOf(a, b, lo)); if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: part(q)};
      if (!wmp.has(x + "," + (y - 1)) && topAt(x, y - 1) > lo) { const f = [[x, y, Math.min(hi, topAt(x, y - 1))], [x + 1, y, Math.min(hi, topAt(x, y - 1))], [x + 1, y, lo], [x, y, lo]].map((v) => api.screenOf(...v)); if (f.every((v) => v) && inq([mx, my], f)) return {x, y: y - 1, fy: .999, face: true, down: Math.floor(part(f) * (Math.min(hi, topAt(x, y - 1)) - lo))}; } }
    for (let y = seen.ty + south; y >= seen.ty - R; y--) for (let x = seen.tx - R; x <= seen.tx + R; x++) {
      if (!zf) { const c0 = combAt(x, y), pb = c0 && "W%+#g".includes(c0) && HdThings.is(c0, x, y) ? boxed(x, y) : null; if (pb && mx >= pb.x && mx <= pb.x + pb.w && my >= pb.y && my <= pb.y + pb.h) return {x, y, fy: .5}; }   // (a wall, a fence: what stands as boxes is pointed at where it is drawn: the pointer on a wall's front named the ground behind it)
      const z = zo(x, y), zs = zf ? z : zo(x, y + 1);
      if (zs < z) { const q = [[x, y + 1, z], [x + 1, y + 1, z], [x + 1, y + 1, zs], [x, y + 1, zs]].map((v) => api.screenOf(...v)); if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: .999, face: true, down: Math.floor(part(q) * (z - zs))}; }
      const q = [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]].map(([a, b]) => api.screenOf(a, b, z));
      if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: part(q)};
    }
    return null;
  };
  // how much of you is seen (tests): the share of your own drawn px that are on the screen as they are drawn; box [x0, y0, x1, y1] (CSS px): -> [that share, how many of them are seen outside the box]
  api.catSeen = (box) => {
    const s = seen && seen.me; if (!s || !eng) return 0; const a = eng.at(s.x, s.y, s.z); if (!a) return 0;
    const sg = s.canvas.getContext("2d").getImageData(0, 0, s.canvas.width, s.canvas.height).data, g = HdView.read(0, 0, cv.width, cv.height).data;
    let n = 0, ok = 0, out = 0; const B = box && box.map((v) => v * cv.width / innerWidth);
    for (let j = 0; j < s.canvas.height; j++) for (let i = 0; i < s.canvas.width; i++) { const o = (j * s.canvas.width + i) * 4; if (sg[o + 3] < 128) continue; n++;
      const X = Math.floor((Math.round(a[0]) - s.fx + i + .5) * Z()), Y = Math.floor((Math.round(a[1]) - s.fy + j + .5) * Z()), p = (Y * cv.width + X) * 4;
      if (X >= 0 && Y >= 0 && X < cv.width && Y < cv.height && Math.abs(g[p] - sg[o]) + Math.abs(g[p + 1] - sg[o + 1]) + Math.abs(g[p + 2] - sg[o + 2]) < 60) { ok++; if (B && (X < B[0] || X > B[2] || Y < B[1] || Y > B[3])) out++; } }
    return box ? [n ? ok / n : 0, out] : n ? ok / n : 0;
  };
  api.stands = () => (seen ? seen.list.filter((s) => s.tx !== undefined && !s.q).map((s) => [s.tx, s.ty, s.z]) : []);   // (tests: what stands, drawn this frame: [its tile, the level it stands at])
  api.read = (...a) => HdView.read(...a); api.bodies = () => (seen ? seen.list.filter((s) => s.q && !s.top).map((s) => [s.q.e.kind, s.z]) : []); api.bare = () => (eng && seen ? eng.bare(Math.max(0, Math.ceil(hy) + 2)) : 0); api.raw = () => (eng ? eng.raw() : 0); api.fades = () => (seen ? seen.list.filter((s) => s.fade !== undefined).map((s) => [s.tx, s.ty, s.fade]) : []); api.blank = () => eng && eng.blank(); Object.defineProperty(api, "units", {get: () => eng && eng.units}); Object.defineProperty(api, "why", {get: () => eng && eng.why}); Object.defineProperty(api, "wrote", {get: () => wrote}); Object.defineProperty(api, "made", {get: () => (eng ? eng.made : 0)}); Object.defineProperty(api, "work", {get: () => (eng ? eng.work : null)});   // (units: the longest step of each kind of the land's making; why: why the last frame was drawn again; made: chunks made by the last land)   // (px under the horizon where no land is drawn)
  // a frame: with this look live (WebGL 2, and you or an eye in the world), the game's frame (render.js) draws to a canvas of one px (who walks, the land coming in), then this look's picture
  { const f0 = frame; frame = function (now) {
    const t0 = performance.now(), keep = ctx; api.live = api.on && !noGL && Voxels.engine.ready() && !!(api.eye || ents.get("agent" + myId)); api.drew = wrote = false; slice1 = 0;
    if (api.live) ctx = HdView.sink(); try { f0(now); } finally { ctx = keep; }
    if (api.live) after(); else HdView.hide();
    HdView.perf(now, performance.now() - t0, api.drew, eng ? eng.calls : 0, slice1, wrote);
  };
    const d0 = drawTile; drawTile = function (x, y, to = null) { d0(x, y, to); if (!to && eng) eng.touch(x, y); };
    const a0 = arriveBlock; arriveBlock = function (b) { a0(b); if (eng) eng.touchBox(b.bx * B, b.by * B, b.bx * B + B - 1, b.by * B + B - 1); }; }   // (a block come in at once: every tile of it as drawn again, tiles.js)   // (a tile of the land drawn again: its chunk of this land is made again, its paints painted again)
  return api;
})();
