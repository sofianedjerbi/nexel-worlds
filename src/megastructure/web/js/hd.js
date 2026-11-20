// The HD look (the default land view; Settings, Picture, Look: HD or Classic): ONE look on the surface and under ground. The land round you is drawn by VoxStyle
// (vox_style.js) at the art's own size, a tilted perspective, every face from the tileset, and laid on the game's
// canvas zoom times bigger. Over it the game's own sky (its curved horizon's, copied from the frame the game drew).
// Going down nothing switches: how shut in you are (levels of land over your tile and round it) is one number u,
// 0 in the open, 1 under ground; the earth's slice (style 6) opens in a ring round you that grows with u, the light
// goes from the day's to your lantern's, the sky fades into the dark of the earth. Trees, bushes, crops: upright
// billboards of their own sprites (objectSprite), px for px; furniture, walls, fences, built floors and roofs: small 3D
// pieces in the land (hd_things.js), a built house open over your head; you and the others: drawEntity at zoom 1.
const HdLook = (() => {
  const urlLook = new URLSearchParams(location.search).get("look"), EASE = .2, GROW = .4, R = 24;
  const cfg = {levels: [-9, 12], variants: 4, up: RELIEF_STEP, rock: {from: 5, lo: -512, n: 4}};
  const cam = {kind: "persp", pitch: 36, fov: 26};
  const api = {get active() { return (urlLook || opt("look")) === "hd"; }, get on() { return this.active && !!me && myId !== null; }, u: 0, ms: 0, build: 0, get busy() { return !!gen; }, box: null, force: null, cam, bend: .03, blur: 1, faces: 0, builds: 0};
  let ul = 0, wd = 0, south = 8, gen = null, seen = null, eng = null, key = "", ver = -1, last = performance.now(), u = 0, back = null, art = null, fx = null, lit = null, hl = 0, hy = 0, lad = {}, lv = 0, at = [0, 0], genBox = "", wantBox = "", since = 0, hurry = false, cand = null, candKey = "";
  const sprs = new Map(), things = new Map(), piles = new Map();
  const Z = () => zoom * DPR;   // (canvas px an art px: `zoom` CSS px, as the classic picture's. It was `zoom` canvas px: on a dense screen, a phone's, the land half the size and twice as far as it would show)
  const mix = (a, b, k) => Array.isArray(a) ? a.map((v, i) => v + (b[i] - v) * k) : a + (b - a) * k;
  function ent(p, now) {      // (a person or a creature, drawn by the game at zoom 1: one art px a px)
    const T = P, w = T * 4, h = T * 5, base = h - T * 1.5;
    let pc = sprs.get(p) || document.createElement("canvas"); sprs.set(p, pc); if (pc.width !== w || pc.height !== h) { pc.width = w; pc.height = h; }
    const g = pc.getContext("2d", {willReadFrequently: true}); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, w, h); g.imageSmoothingEnabled = false;   // (its px are read each frame: its shadow is its shape now, hd_sun.js)
    const keep = ctx, kz = zoom, sx = (x) => w / 2 - T / 2 + (x - p.x) * T, sy = Object.assign((y) => base + (y - p.y) * T, {up: (y) => base + (y - p.y) * T});
    ctx = g; zoom = 1; try { drawEntity(p, sx, sy, T, now / 1000, now); } catch (e) { /* (nothing to draw) */ } finally { ctx = keep; zoom = kz; }
    return {canvas: pc, fx: w / 2, fy: Math.round(base + T * .5)};
  }
  function thing(spr) {       // (a thing's sprite on a canvas of its own, once: its foot the middle of its tile's bottom)
    const [img, sx, sy, sw, sh, dx, dy] = spr, k = (img.src || img.id || "") + "|" + sx + "," + sy + "," + sw + "," + sh;
    let c = things.get(k);
    if (!c) { c = document.createElement("canvas"); c.width = sw; c.height = sh; const g = c.getContext("2d"); g.imageSmoothingEnabled = false; g.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh); things.set(k, c); }
    return {canvas: c, fx: 8 - dx, fy: 16 - dy, still: true, d: true};
  }
  const topAt = (x, y) => { const c = Voxels.host.column(x, y); return c && c.length ? c[c.length - 1] : 0; };
  const solidAt = (c, z) => { for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
  // a bank's top: the pack's shore tile has a white line of foam along the water's edge, where the classic picture's water laps. Here the water lies a level under the bank:
  // the line stood up on the rim, a bright white line along a pond. Its white px take the earth px next inward.
  function shore(x, y, z, px, at, st) {
    const H0 = Voxels.host; H0.paintTop(x, y, z, px, at, st); if (H0.water(x, y)) return;
    const white = (v) => (v >>> 24) > 127 && (v & 255) > 214 && (v >> 8 & 255) > 214 && (v >> 16 & 255) > 205;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) if (H0.water(x + dx, y + dy)) for (let n = 0; n < 16; n++) for (let k = 0; k < 4; k++) {
      const q = (m) => at + (dx ? n : dy > 0 ? 15 - m : m) * st + (dy ? n : dx > 0 ? 15 - m : m); if (!white(px[q(k)])) continue;
      let m = k + 1; while (m < 8 && white(px[q(m)])) m++; px[q(k)] = px[q(m)]; }
    for (const [dx, dy] of [[1, 1], [-1, 1], [1, -1], [-1, -1]]) if (H0.water(x + dx, y + dy)) for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) {   // (a corner's)
      const q = (a, b) => at + (dy > 0 ? 15 - b : b) * st + (dx > 0 ? 15 - a : a); if (white(px[q(i, j)])) px[q(i, j)] = px[q(5, 5)]; }
  }
  function roofed(x, y, L) {   // land over the level you stand at, with air under it (a roof, not a wall beside you)
    const c = Voxels.host.column(x, y); if (!c || solidAt(c, L + 1)) return 0;
    for (let z = L + 2; z <= L + 9; z++) if (solidAt(c, z)) return 1; return 0;
  }
  function walled(tx, ty, L) {   // a canyon, a pit, a pond under a cliff: land south of you over the eye's line to you hides you (and the water at your feet) -> how many tiles south it is, 0: none
    const k = Math.tan(cam.pitch * Math.PI / 180) * 2;   // (levels the eye's line climbs a tile south: a level is half a tile high)
    let far = 0; for (let dy = 1; dy <= 12; dy++) for (let dx = -1; dx <= 1; dx++) if (topAt(tx + dx, ty + dy) - L > 1 + (dy - .5) * k) far = dy;
    return far;
  }
  function shut(tx, ty, L) {  // how shut in: 0 open sky (a canyon, a trench, a pond by a cliff) .. 1 a roof over you and round you
    let s = 0, n = 0;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const c = Voxels.host.column(tx + dx, ty + dy); if (!c || (dx || dy) && solidAt(c, L + 1)) continue; s += roofed(tx + dx, ty + dy, L); n++; }
    return n ? Math.min(1, roofed(tx, ty, L) * .5 + s / n * .6) : 0;
  }
  // the lens: far rows (the 48 art px under the horizon, hy) a little soft, the rest crisp; a faint bloom of the light parts; no vignette
  // (it was the top three tenths of the screen, wherever the horizon: looked at from close, or on a screen held upright, the land near you was a blur)
  function post(pic, w, h) {
    art = art || document.createElement("canvas"); fx = fx || document.createElement("canvas");
    for (const c of [art, fx]) if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    const g = art.getContext("2d"), f = fx.getContext("2d"); g.globalCompositeOperation = "source-over"; g.clearRect(0, 0, w, h); g.drawImage(pic, 0, 0);
    if (api.blur > 0 && hy + 48 > 0) {
      f.globalCompositeOperation = "source-over"; f.clearRect(0, 0, w, h); f.filter = `blur(${api.blur}px)`; f.drawImage(pic, 0, 0); f.filter = "none";
      f.globalCompositeOperation = "destination-in"; const gr = f.createLinearGradient(0, hy, 0, hy + 48);
      gr.addColorStop(0, "rgba(0,0,0,.85)"); gr.addColorStop(1, "rgba(0,0,0,0)"); f.fillStyle = gr; f.fillRect(0, 0, w, h);
      g.globalCompositeOperation = "source-atop"; g.drawImage(fx, 0, 0);
    }
    f.globalCompositeOperation = "source-over"; f.clearRect(0, 0, w, h); f.filter = "brightness(.55) contrast(8) blur(4px)"; f.drawImage(pic, 0, 0); f.filter = "none";
    g.globalCompositeOperation = "lighter"; g.globalAlpha = .07; g.drawImage(fx, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = "source-over";
    return art;
  }
  // the backdrop: the game's own sky, the rows over its horizon, copied from the frame it drew; under it the air's colour
  function backdrop(w, h, sky, k, tx, ty) {
    back = back || document.createElement("canvas"); if (back.width !== w || back.height !== h) { back.width = w; back.height = h; }
    const g = back.getContext("2d"); g.imageSmoothingEnabled = false; const low = sky ? sky.low : [.62, .78, .86], line = sky ? Math.round(sky.line / zoom) : 0;
    // under the horizon, past the bend: the air's haze; the sea's tint only over the columns where the sea is really there, past the last land you see (it was the sea's all across: a sea behind every hill inland)
    const tint = (c, a) => `rgb(${low.map((v, i) => Math.round((v * (1 - a) + c[i] * a) * 255)).join()})`, H0 = Voxels.host; g.fillStyle = tint([.8, .84, .8], .45); g.fillRect(0, 0, w, h);
    if (eng && seen) { g.fillStyle = tint([.36, .64, .8], .65); let run = null;
      for (let x = tx - R; x <= tx + R + 2; x += 2) { let n = 0; for (let y = ty - 20; y <= ty - 12; y += 2) if (!H0.column(x, y) || H0.water(x, y)) n++;
        const sea = x <= tx + R && n >= 3, a = eng.at(x, ty - 14, 0), px = x <= tx - R ? 0 : x > tx + R ? w : Math.round(a[0]);
        if (sea && run === null) run = px; if (!sea && run !== null) { g.fillRect(run, 0, px - run, h); for (const ex of [run - 8, px]) for (let j = 0; j < h; j += 2) for (let i = (j >> 1 & 1) * 2; i < 8; i += 4) g.fillRect(ex + i, j, 2, 2); run = null; } } }   // (its two ends: a 2x2 checker, 8 px)
    if (line > 0) {   // (from the land's own picture, which in this look is the sky alone, with the hour's light the game lays over its frame: it was copied from the finished frame, and a tree, a wall, a boulder the classic picture drew up there stood in the sky)
      const ph = clock.phase || 0, ws = washAt(ph), lf = opt("night") / 100 * .6; g.drawImage(Voxels.pic || cv, 0, 0, w * Z(), line * Z(), 0, 0, w, line);
      if (Voxels.pic) { g.globalAlpha = ws[3]; g.fillStyle = `rgb(${ws.slice(0, 3).join()})`; g.fillRect(0, 0, w, line); g.globalAlpha = 1; g.globalCompositeOperation = "multiply"; g.fillStyle = `rgb(${lightAt(ph).map((v) => Math.round(v + (255 - v) * lf)).join()})`; g.fillRect(0, 0, w, line); g.globalCompositeOperation = "source-over"; }
    }
    if (k > 0) { g.fillStyle = `rgba(30,23,21,${k.toFixed(3)})`; g.fillRect(0, 0, w, h); }
    return {canvas: back, low};
  }
  // the hour's light on the land: the game's own (daylight.js: its tint, its wash, a lamp on each of you and each fire, in whole steps), put where this camera
  // puts them; under a roof (el) none of it. (It was the shader's `day` alone: the night's land as bright as noon under a night sky.) -> {wash, lit: the light's picture}
  // for the land's own painter to lay over what it draws (vox_style.js `hour`), or nothing at plain day
  function hour(w, h, list, el) {
    const ph = clock.phase || 0, tint = lightAt(ph).map((v) => v + (255 - v) * el), wash = washAt(ph), dark = Math.min(1, (1 - (.3 * tint[0] + .59 * tint[1] + .11 * tint[2]) / 255) / .36);
    if (wash[3] * (1 - el) <= .004 && dark <= .01) return null;
    const lift = opt("night") / 100 * .6; if (dark <= .2) return {wash: [wash[0], wash[1], wash[2], wash[3] * (1 - el)], tint: tint.map((v) => Math.round(v + (255 - v) * lift))};   // (no lamp shows: one colour, a px of it: it was a picture the screen's size sent to the GPU every frame of a morning)
    lit = lit || document.createElement("canvas"); if (lit.width !== w || lit.height !== h) { lit.width = w; lit.height = h; }
    const q = lit.getContext("2d"); q.globalAlpha = 1; q.globalCompositeOperation = "source-over"; q.fillStyle = `rgb(${tint.map((v) => Math.round(v + (255 - v) * lift)).join()})`; q.fillRect(0, 0, w, h);
    if (dark > .2) { q.globalCompositeOperation = "lighter"; const k = (dark - .2) / .8;
      for (const s of list) if (s.lamp) { const a = eng.at(s.x, s.y, s.z); if (a) lamp(q, a[0], a[1] - 8, s.lamp > 1 ? 64 : 42, s.lamp > 1 ? "rgb(255,176,96)" : "rgb(255,222,170)", (s.lamp > 1 ? 1.15 : .45) * k, [0, 0]); } }
    q.globalAlpha = 1; return {wash: [wash[0], wash[1], wash[2], wash[3] * (1 - el)], lit};
  }
  // what is written and pointed at, over the picture, by the game's own painters (names, a health bar, an emote, what is said, a progress bar): they were
  // drawn at the classic picture's places, under this one. Their sx, sy: someone's own place as this camera has it (found by its x, its y), else measured from you.
  function written(p, now) {
    const S = TS(), F = api.screenOf(seen.me.x, seen.me.y, seen.me.z), who = (v, ax) => { for (const s of seen.list) if (s.q && s.q[ax] === v) return api.screenOf(s.x, s.y, s.z); return null; };
    const sx = (x) => { const a = who(x, "x"); return a ? a[0] - S / 2 : F[0] - S / 2 + (x - p.x) * S; }, fy = (y) => { const a = who(y, "y"); return a ? a[1] - S / 2 : F[1] - S / 2 + (y - p.y) * S; }, sy = Object.assign(fy, {up: fy, out: fy});
    const px = zoom / seen.k, t = now / 1000, snap = (v) => Math.round(v / px) * px, quad = (x, y, z) => [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => api.screenOf(x + a, y + b, z));
    // (all of it in whole art px) corners: a quad's four corners, a third of each side; fill: a tile's face, row by row; ghost: a thing's own sprite where it would stand; rectOf: the px its picture takes
    const corners = (c, col) => { for (const [cl, o] of [["#5b3f36", px], [col, 0]]) { ctx.fillStyle = cl; c.forEach((a, i) => { for (const b of [c[(i + 1) % 4], c[(i + 3) % 4]]) { const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) * .3 / px)); for (let j = 0; j <= n; j++) ctx.fillRect(snap(a[0] + (b[0] - a[0]) * j / n * .3), snap(a[1] + (b[1] - a[1]) * j / n * .3) + o, px, px); } }); } };
    const fill = (c, col) => { ctx.fillStyle = col; const at = (a, b, y) => a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) || 1); for (let y = snap(c[0][1]); y < c[3][1]; y += px) { const l = snap(at(c[0], c[3], y)), r = snap(at(c[1], c[2], y)); ctx.fillRect(l, y, r - l, px); } };
    const rectOf = (spr, x, y) => { const f = api.screenOf(x + .5, y + 1, shown(x, y)), k = px; return [snap(f[0] - (8 - spr[5]) * k), snap(f[1] - (16 - spr[6]) * k), spr[3] * k, spr[4] * k]; };
    const edge = (a, b, col, dot) => { if (!a || !b) return; const n = Math.max(1, Math.ceil(Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) / px)); for (const [cl, o] of [["#5b3f36", px], [col, 0]]) { ctx.fillStyle = cl; for (let i = 0; i <= n; i++) if (!dot || (i >> 1) % 2 === 0) ctx.fillRect(snap(a[0] + (b[0] - a[0]) * i / n), snap(a[1] + (b[1] - a[1]) * i / n) + o, px, px); } };   // (a line in whole art px; dot: two on, two off)
    const ladder = (x, y, z, a) => { const k = [x, y, z, landVer, Floors.ver].join(); if (lad.k !== k) lad = {k, c: HdThings.painted(48, 96, () => Climb.drawLadder(x, y, z, (X) => 16 + (X - x) * 16, (Y) => 64 + (Y - y) * 16 + shOf(z), 16, 1))}; const f = api.screenOf(x + .5, y + 1, z); if (!f) return;   // (a ladder stands: the game's own picture of it, upright)
      ctx.globalAlpha = a; ctx.imageSmoothingEnabled = false; ctx.drawImage(lad.c, snap(f[0] - 24 * px), snap(f[1] - 80 * px), 48 * px, 96 * px); ctx.globalAlpha = 1; };
    const ghost = (ch, x, y, a) => { const spr = ch && objectSprite(ch, x, y, t); if (!spr || !spr[0] || !spr[0].width) return; const r = rectOf(spr, x, y); ctx.globalAlpha = a; ctx.imageSmoothingEnabled = false; ctx.drawImage(spr[0], spr[1], spr[2], spr[3], spr[4], ...r); ctx.globalAlpha = 1; };
    const box = (r) => [[r[0], r[1]], [r[0] + r[2] - px, r[1]], [r[0] + r[2] - px, r[1] + r[3] - px], [r[0], r[1] + r[3] - px]], bound = (c) => { const xs = c.map((v) => v[0]), ys = c.map((v) => v[1]); return {x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)}; };
    if (Build.on) {   // build mode: what is planned, each on its own tile at its own height as this camera has it, and the cursor (the game drew them at the classic picture's places)
      for (const j of Build.S.plans.values()) { const c = quad(j.x, j.y, j.z); if (c.some((v) => !v)) continue;
        if (j.item === "ladder") ladder(j.x, j.y, j.z, .6); else if (!j.take && !j.dig && !HdThings.pieced(j.item, j.steps, j.up ? j.z : undefined)) ghost(PLACEABLE_BLOCK[j.item], j.x, j.y, j.state === "doing" ? .75 : .5);   // (pieces: in the land, see-through: pieces())
        fill(c, j.state === "bad" ? "rgba(230,80,70,.4)" : j.take ? "rgba(255,150,60,.3)" : j.state === "doing" ? "rgba(255,241,168,.35)" : "rgba(140,190,255,.28)"); if (j.dig) fill(c.map((v, i) => [v[0] + (c[(i + 2) % 4][0] - v[0]) * .2, v[1] + (c[(i + 2) % 4][1] - v[1]) * .2]), "rgba(60,36,30,.5)"); }
      const at = Build.S.at; if (at) { const c = quad(at.x, at.y, Build.level()), it = Build.aim().it, mx = (myPos() || at).x; if (it && it.ghost === "ladder" && it.z !== undefined) ladder(at.x, at.y, it.z, .6); else if (it && it.ghost && it.ok !== false && !HdThings.pieced(it.ghost, it.steps, it.draw ? undefined : it.z)) ghost(PLACEABLE_BLOCK[it.ghost], at.x, at.y, .7);
        // the depth mark (mark.js's cells, as this camera has them): the cursor's cell as a box, its front edges; in the air a dotted line down to the ground under it and a small square there; each step of a flight; how far over or under you it is, beside it and on you (keyhole.js)
        for (const m of Marks.list) { const col = `rgb(${m.colour.map((v) => Math.round(v * 255)).join()})`, S0 = api.screenOf;
          if (m.z1 > m.z0 && !m.flat) { for (const dx of [0, 1]) edge(S0(m.x + dx, m.y + 1, m.z1), S0(m.x + dx, m.y + 1, m.z0), col); edge(S0(m.x, m.y + 1, m.z0), S0(m.x + 1, m.y + 1, m.z0), col); }
          if (m.fill === 0 && m.to && m.to.fill === 0) { const q = quad(Math.round(m.x), Math.round(m.y), m.z1); if (q.every((v) => v)) corners(q, col); }
          if (m.drop !== undefined && m.drop < m.z0) { edge(S0(m.x + .5, m.y + .5, m.z0), S0(m.x + .5, m.y + .5, m.drop), col, true); const q = [[.3, .3], [.7, .3], [.7, .7], [.3, .7]].map(([a, b]) => S0(m.x + a, m.y + b, m.drop)); if (q.every((v) => v)) fill(q, "rgba(91,63,54,.55)"); } }
        corners(c, it && it.ok === false ? "#e8554a" : Math.floor(t * 3) % 2 ? "#fff1a8" : "#ffffff"); Build.S.rect = Object.assign(bound(c), {under: mx !== at.x, right: mx < at.x}); Prompts.build();
        const s = myPos(), L1 = Build.level(), r = Build.S.rect; if (s) Keyhole.mark(r.x, r.y, r.h, L1 - myZ(s.x, s.y), landSolid(at.x, at.y, L1) && landSolid(at.x, at.y, L1 + 1), sx, sy, r.right); }
    } else {          // the aim: what stands there, round its picture; a ghost of what would be put; else the corners of the tile as the land shows it; its keys beside it (prompts.js)
      const aim = aimedTile(), it = aim && aim.it, a = aim && aim.p, on = a && tile(a.x, a.y) && it && !it.info && !it.walk; let r = null;
      if (on && it.ghost === "ladder" && it.z !== undefined) ladder(a.x, a.y, it.z, .6); else if (on && it.ghost && !HdThings.pieced(it.ghost, it.steps, it.draw ? undefined : it.z)) ghost(PLACEABLE_BLOCK[it.ghost], a.x, a.y, .7);
      if (on) { const e = it.ent && seen.list.find((s) => s.q && s.q.e === it.ent || s.q === it.ent), c0 = combAt(a.x, a.y), spr = !e && c0 && isObject(c0) && objectSprite(c0, a.x, a.y, t), f = e && api.screenOf(e.x, e.y, e.z);
        const cs = !e && seen.list.find((s) => s.card && s.tx === a.x && s.ty === a.y), cf = cs && api.screenOf(cs.x, cs.y, cs.z), pb = !e && !cs && c0 && HdThings.is(c0, a.x, a.y) ? boxed(a.x, a.y) : null;   // (round the piece as it is drawn: a card's own px, the boxes' corners)
        const c = e ? box([snap(f[0] - 8 * px), snap(f[1] - 12 * px), 16 * px, 16 * px]) : cs && cf ? box([snap(cf[0] - (cs.fx - cs.card.b[0]) * px), snap(cf[1] - (cs.fy - cs.card.b[1]) * px), (cs.card.b[2] - cs.card.b[0]) * px, (cs.card.b[3] - cs.card.b[1]) * px])
          : pb ? box([snap(pb.x), snap(pb.y), snap(pb.w) + px, snap(pb.h) + px]) : spr && spr[0] ? box(rectOf(spr, a.x, a.y)) : quad(a.x, a.y, shown(a.x, a.y)); corners(c, it.ok === false ? "#e8554a" : "#fff8e8"); r = bound(c); }
      Prompts.show(r, faceRows); api.aim = r;
    }
    const ny = (y) => fy(y) - Math.max(0, 12 - 3 * zoom), nsy = Object.assign(ny, {up: ny, out: ny});   // (a name: higher where an art px is small, a phone's 2 px: the letters are 18 px whatever the zoom, and seen from behind a body's ears were in its name)
    for (const s of seen.list) if (s.q && s.q.e && (s.q.e.kind === "agent" || s.q.e.name)) drawNameplate(s.q, sx, nsy, S);
    for (const s of seen.list) if (s.q && s.q.e && (ANIMALS[s.q.e.kind] || !bubbles.some((b) => b.name === s.q.e.name))) drawEmote(s.q, sx, sy, S);
    drawProgress(sx, sy, S); drawBubbles(sx, sy, S, t); ctx.textAlign = "start";
  }
  // what is planned (build mode) and what the aim would put: see-through pieces in the land, each where and as it will stand (hd_things.js): a wall, a floor's planks, a roof, a flight of stairs, a bed
  function pieces(list) {
    const out = [], big = (k) => (k === "mossback" ? [30, 8] : ANIMALS[k] && ANIMALS[k].fw === 32 ? [16, 5] : [9, 4]), add = (item, x, y, z, steps) => { const l = HdThings.ghost(item, x, y, z, steps); if (l) out.push(...l); };
    for (const s of list) if (s.q || s.pile) { const [w, d] = s.pile ? [8, 3] : big(s.q.e && s.q.e.kind); for (const b of HdThings.shadow(w, d, s.z * RELIEF_STEP + .5)) out.push([s.x, s.y + (s.pile ? .08 : .42), b]); if (s.q) HdSun.body(out, s); }   // (the shadow under each body and each pile: on the ground where its feet are drawn)
    HdThings.plans.clear(); if (Build.on) for (const j of Build.S.plans.values()) if (!j.take && !j.dig && j.state !== "bad" && "W%+".includes(PLACEABLE_BLOCK[j.item] || "-")) HdThings.plans.add(j.x + "," + j.y + "," + (j.up ? j.z : floorAt(j.x, j.y)));   // (planned walls join each other)
    if (Build.on) for (const j of Build.S.plans.values()) if (!j.take && !j.dig && j.state !== "bad") add(j.item, j.x, j.y, j.up ? j.z : undefined, j.steps);
    const a = Build.on ? Build.aim() : aimedTile(), it = a && a.it; if (a && a.p && it && it.ghost && it.ok !== false && !it.info && !it.walk) add(it.ghost, a.p.x, a.p.y, it.z !== undefined && !it.draw ? it.z : undefined, it.steps);
    return out;
  }
  // the game's sky with its horizon where this land's is: the top of the bent ground at your level (it was the classic picture's horizon, higher: a wide empty band
  // between the sky and the land, a third of a phone held upright); it follows your height softly
  api.sky = (t) => { const s = Curve.sky(t); return api.on && hl ? Object.assign({}, s, {line: Math.round(hl) * zoom}) : s; };
  function horizon(tx, ty, L, dt) { let y = 1e9; for (let dn = 6; dn <= 22; dn++) { const a = eng.at(tx + .5, ty - dn, L); if (a) y = Math.min(y, a[1]); } hy = y < 1e8 ? y : -1e9; if (y < 1e8) hl = hl ? hl + (Math.max(8, y + 2) - hl) * Math.min(1, dt * 5) : Math.max(8, y + 2); }
  function after() {
    if (!api.on || !Voxels.engine.ready()) return;
    const now = performance.now(), dt = Math.min(.1, (now - last) / 1000); last = now;
    const p = ents.get("agent" + myId); if (!p) return;
    const H0 = Voxels.host, wet = (x, y) => H0.water && H0.water(x, y) && H0.waterTop ? H0.waterTop(x, y) : -1e9;   // (in water: you stand at its face)
    const t0 = performance.now(), L = FLOORS && Floors.any(Math.round(p.x), Math.round(p.y)) ? Floors.standOf(p, Math.round(p.x), Math.round(p.y)) : xray.a > .5 ? xray.L : Math.max(topAt(Math.round(p.x), Math.round(p.y)), wet(Math.round(p.x), Math.round(p.y))), tx = Math.round(p.x), ty = Math.round(p.y);
    const w = Math.ceil(cv.width / Z()), h = Math.ceil(cv.height / Z());
    // a screen held upright: the eye looks from higher (36 to 52 degrees), or half of it was sky and the land ran out under you; and what stands south of you is drawn as far as the screen shows (it was 6 rows: trees came in half way up a tall screen)
    cam.pitch = 36 + 16 * Math.max(0, Math.min(1, h / w - 1)); south = Math.min(R, Math.ceil(h / 32 / Math.sin(cam.pitch * Math.PI / 180)) + 3);
    const roof = shut(tx, ty, L), want = api.force !== null ? api.force : Math.max(roof, (wd = walled(tx, ty, L)) ? 1 : 0);
    ul = roof > ul ? Math.min(roof, ul + dt / EASE) : Math.max(roof, ul - dt / EASE);   // (the light goes under ground only under a roof)
    u = want > u ? Math.min(want, u + dt / EASE) : Math.max(want, u - dt / EASE); api.u = u;
    // (the cut is made for where you ARE, the frame you are covered: its size by how shut in you are now, not eased. It grew with an ease of 1.2 s, a land made again at each size: "a lot of time to trigger". Only the light eases, a fifth of a second)
    const e = want, gr = Math.min(1, roof / GROW), gs = gr * gr * (3 - 2 * gr), b0 = [1, 3, Math.max(2, Math.round(e * (wd + 1)))], b1 = [1 + e * (R - 10), 1 + e * R, 1 + e * R].map((v, i) => Math.round(mix(b0[i], v, gs))),
      box = e < .08 ? null : {n: b1[0], w: b1[1], s: b1[2]},   // (walls alone: a small box round you; a roof: the whole cut-away, grown from the small one tile by tile as the roof closes over you (it came all at once))
        // (the cut-away: south and across all, north 14 tiles, so the land beyond it, the surface, sinks to the horizon under the sky at any depth; beyond it the land whole, its terraces, the sky)
      inBox = (x, y) => !!box && y - ty >= -box.n && y - ty <= box.s && Math.abs(x - tx) <= box.w, dep = Math.max(0, topAt(tx, ty) - L);
    eng = eng || VoxStyle.create(Object.assign({}, Voxels.host, {paintTop: shore, models: (x, y) => { const a = Models.at(x, y), b = api.box && floorAt(x, y) > lv + 2 && y - at[1] >= -api.box.n && y - at[1] <= api.box.s && Math.abs(x - at[0]) <= api.box.w ? null : HdThings.at(x, y); return a && b ? a.concat(b) : a || b; }}), cfg);   // (what is built and put down: small 3D pieces, hd_things.js)
    if (ver !== landVer || eng.lost) { eng.forget(); ver = landVer; key = ""; }
    const k = [tx, ty, L, JSON.stringify(box), HdThings.key()].join();
    const bk = JSON.stringify(box); if (bk !== wantBox) { wantBox = bk; since = now; }   // (since: when the cut wanted last changed; api.lag: ms from then to the land with that cut drawn)
    if (k !== key && !gen) { gen = eng.steps(tx, ty, L, L + 2, {r: R, rx: Math.min(R, Math.ceil(w / 32 * 1.4) + 3), rs: south + 1, deep: 20, over: 0, under: true, sea: 1, cut: box || {n: -9, s: -9, w: -9}}); key = k; genBox = bk; hurry = bk !== JSON.stringify(api.box); api.box = box; lv = L; at = [tx, ty]; api.build = 0; api.builds++; }   // (one land at a time: the next is made when this one is done)
    if (gen) { const b0 = performance.now(); while (performance.now() - b0 < (hurry ? 14 : 4)) if (gen.next().done) { gen = null; break; } api.build = Math.max(api.build, performance.now() - b0); api.water = eng.water;   // (the land made again a few rows a frame, ~4 ms; what was drawn stays till it is done; a cut that opens or shuts: at once, up to 14 ms a frame)
      if (!gen) { if (genBox === wantBox && since) { api.lag = performance.now() - since; since = 0; } } }
    const list = [];
    const stood = (c, x, y, z) => {      // a thing that stands: furniture as its card (hd_things.js: px for px, its top leaning with where it is on the screen), the rest a billboard
      const s = objectSprite(c, x, y, now / 1000); if (!s || !s[0] || !s[0].width) return; const cd = HdThings.card(c, x, y, s);
      const r2 = cd || c === "g" ? 0 : HdThings.foot(c, s), plain = cd || c === "g" ? null : {fy: r2, card: {b: spriteBounds(s[0], s[1], s[2], s[3], s[4]) || [0, 0, s[3], s[4]]}};   // (each stands where its foot is in its tile, as the game has it: they stood at the tile's south edge, their feet half a tile north of their shadow)
      list.push(Object.assign(cd ? {} : thing(s), cd, {x: x + .5, y: y + (cd ? cd.y : plain ? (s[6] + r2) / 16 : 1), z, lamp: c === "^" || c === "x" ? 2 : 0, flat: c === "g", tx: x, ty: y, card: cd}, plain));   // (flat: a gate: a standing face of the land a tile wide, vox_style.js)
    };
    const dk = ul * ul * (3 - 2 * ul) * Math.max(0, Math.min(1, (dep - 6) / 4)), gone = (x, y) => (inBox(x, y) && floorAt(x, y) > L + 2) || (dk > .3 && floorAt(x, y) > L + 6);   // (deep under a roof the sky is the dark of the earth: what stands on the surface past the cut is not drawn: bushes peeked over the far earth's edge, lit, in the dark)
    const ck = [tx, ty, L, landVer, Floors.ver, bk, dk > .3, Math.floor(now / 250)].join();   // (what stands: looked for four times a second and when you or the land move, not on 2400 tiles every frame)
    if (ck !== candKey) { candKey = ck; cand = []; for (let y = ty - R; y <= ty + south; y++) for (let x = tx - R; x <= tx + R; x++) {
      if (gone(x, y)) continue;   // (on land the slice took away; in a cave: on its floor, the tile's lowest ground)
      const c = combAt(x, y), up = Floors.any(x, y) ? HdThings.loose(x, y) : null; if (up) for (const [ch, z] of up) cand.push([ch, x, y, z]);   // (what stands on a built block)
      if (c && isObject(c) && !HdThings.is(c, x, y)) cand.push([c, x, y, floorAt(x, y)]);      // (not the boxes of the land: hd_things.js)
    } }
    for (const [c, x, y, z] of cand) stood(c, x, y, z);
    for (const [ix, iy, pile] of groundItems) if (Math.abs(ix - tx) <= R && iy >= ty - R && iy <= ty + south && !gone(ix, iy)) {   // what lies on the ground: its small icons as the game lays them (loot.js), a px a px (they were not drawn in this look)
      const names = Object.keys(pile).slice(0, 3), k = names.join(); let c = piles.get(k);
      if (!c) { c = document.createElement("canvas"); c.width = 24; c.height = 16; const g = c.getContext("2d"); names.forEach((n, i) => { const [dx, dy] = pileAt(i, names.length); g.drawImage(ghostIcon(n), 7 + dx, 3 + dy); }); piles.set(k, c); }
      list.push({canvas: c, fx: 12, fy: 14 + Math.round(Math.sin(now / 1000 * 2.4 + ix * 1.3 + iy) + 1), still: true, d: true, pile: true, x: ix + .5, y: iy + .7, z: floorAt(ix, iy)});   // (it hovers, as in the classic picture: 0 to 2 px, a whole px at a time)
    }
    for (const q of ents.values()) if (q.x !== undefined && Math.abs(q.x - p.x) < 16 && Math.abs(q.y - p.y) < 12) {
      const s = ent(q, now), z = q === p ? L : FLOORS && Floors.any(Math.round(q.x), Math.round(q.y)) ? Floors.standOf(q, Math.round(q.x), Math.round(q.y)) : topAt(Math.round(q.x), Math.round(q.y));   // (on a built floor: at its height)
      list.push({canvas: s.canvas, fx: s.fx, fy: s.fy, x: q.x + .5, y: q.y + .5, z, d: q !== p, top: q === p, q, lamp: q.e && q.e.kind === "agent" ? 1 : 0});   // (you: never hidden by land)
    }
    list.sort((a, b) => a.y - b.y);
    const snap = (v) => Math.round(v * 16) / 16;
    const sky = typeof Curve !== "undefined" && Curve.on ? api.sky(now / 1000) : null, bd = backdrop(w, h, sky, dk, tx, ty);   // (the sky stays over the far land down to 6 levels; from 10 down none of it, no sun: the dark of the earth)
    const wl = WaterBed.view(Voxels.engine, now / 1000), day = 1, ed = h / (32 * Math.tan(cam.fov * Math.PI / 360));   // (the eye's distance: fog counts from there)
    const el = ul * ul * (3 - 2 * ul), light = {amb: mix(.8, .62, el), lr: mix(8, 6.5, el), day, sk: .85, fog: [mix(ed + 4, ed + 8, el), mix(ed + 22, ed + 34, el)], fogc: mix(bd.low, [.5, .45, .4], el * .6), clear: [0, 0, 0], ca: 0, dark: el, sun: HdSun.sun,
      roof: .6, rim: mix(.25, .6, el), under: true, wa: .92, wtint: wl && wl.tint ? wl.tint.subarray(0, 20) : null, ub: box ? [box.n, box.w, box.s, 1] : [-9, -9, -9, 1]};
    let pic = eng.draw({w, h, cam, at: [snap(p.x + .5), snap(p.y + .5), L + .5], bend: api.bend, t: now / 1000, light,
      water: typeof waterCv !== "undefined" && waterView ? {canvas: waterCv, x: waterView.x, y: waterView.y} : null, dep, sprites: list, ghosts: pieces(list), hour: hour(w, h, list, el)});
    if (!pic) return;
    seen = {tx, ty, L, box, k: 1, me: list.find((q) => q.top), list}; horizon(tx, ty, L, dt);
    api.faces = eng.faces; api.models = eng.models; if (!document.body.classList.contains("touch")) pic = post(pic, w, h);   // (a phone: no lens: two blurs of the whole picture a frame, and canvases laid on each other, which a phone has drawn wrong)
    // the land's picture over the backdrop at the art's own size, then ONE picture laid on the screen (they were two, each the whole screen: 2.6 million px a frame on a phone)
    const bg = bd.canvas.getContext("2d"); bg.save();
    if (el > .05) {   // under a roof: the sky stays as a band over the earth's far edge, a ridge in whole steps of 2 art px (the earth's silhouette), lower as you go deeper
      const top = Math.round(Math.min(h * .16, 4 + dep * 1.5) * el), sx = Math.round(p.x * 2); bg.beginPath(); bg.moveTo(0, h);
      for (let x = 0; x <= w; x += 2) { const n = Math.sin((x + sx) * .071) * 2.5 + Math.sin((x + sx) * .023 + 1.3) * 3.5, y = Math.max(0, top + Math.round(n / 2) * 2); bg.lineTo(x, y); bg.lineTo(x + 2, y); }
      bg.lineTo(w, h); bg.closePath(); bg.clip();
    }
    bg.drawImage(pic, 0, 0); bg.restore();
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.imageSmoothingEnabled = false; const z = Z(); ctx.drawImage(bd.canvas, 0, 0, w * z, h * z); ctx.restore();
    written(p, now);
    api.ms = performance.now() - t0;
  }
  // the px a tile's boxes take on the screen (hd_things.js: a wall, a fence, a door): {x, y, w, h}, or null
  function boxed(x, y) {
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const b of HdThings.at(x, y) || []) if (!b.shade) for (let n = 0; n < 8; n++) { const p = api.screenOf(x + (b.x + (n & 1) * b.w) / 16, y + (b.y + (n >> 1 & 1) * b.d) / 16, (b.z + (n >> 2) * b.h) / 8); if (p) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); } }
    return x1 > x0 ? {x: x0, y: y0, w: x1 - x0, h: y1 - y0} : null;
  }
  // what is under the pointer (client px): the nearest top drawn there, as the land shows it (a top the cut took away: at the cut)
  api.cut = (x, y, t) => !!api.box && t > lv + 2 && y - at[1] >= -api.box.n && y - at[1] <= api.box.s && Math.abs(x - at[0]) <= api.box.w;   // (land the cut took away)
  const shown = (x, y) => { const t = topAt(x, y); return seen && seen.box && t > seen.L + 2 && y - seen.ty >= -seen.box.n && y - seen.ty <= seen.box.s && Math.abs(x - seen.tx) <= seen.box.w ? seen.L + 2 : t; };
  api.screenOf = (x, y, z) => { if (!eng || !seen) return null; const a = eng.at(x, y, z); return a && [a[0] * zoom / seen.k, a[1] * zoom / seen.k]; };
  // -> the tile under the pointer: from the south (the nearest) north, the first whose south front or whose top is under it (a front: face, down: levels under its top, as mouse.js). zf: its height, if not the land's as shown (build mode)
  api.pick = (mx, my, zf) => {
    if (!eng || !seen) return null;
    const inq = (P, q) => { let s = 0; for (let i = 0; i < 4; i++) { const a = q[i], b = q[(i + 1) % 4], c = (b[0] - a[0]) * (P[1] - a[1]) - (b[1] - a[1]) * (P[0] - a[0]); if (c && s && Math.sign(c) !== s) return false; if (c) s = Math.sign(c); } return true; };
    const zo = (x, y) => (zf ? zf(x, y) : shown(x, y)), part = (q) => Math.max(0, Math.min(.999, (my - Math.min(q[0][1], q[1][1])) / Math.max(1, Math.max(q[2][1], q[3][1]) - Math.min(q[0][1], q[1][1]))));
    for (let y = seen.ty + south; y >= seen.ty - R; y--) for (let x = seen.tx - R; x <= seen.tx + R; x++) {
      if (!zf) { const c0 = combAt(x, y), pb = c0 && "W%+#g".includes(c0) && HdThings.is(c0, x, y) ? boxed(x, y) : null; if (pb && mx >= pb.x && mx <= pb.x + pb.w && my >= pb.y && my <= pb.y + pb.h) return {x, y, fy: .5}; }   // (a wall, a fence: what stands as boxes is pointed at where it is drawn: the pointer on a wall's front named the ground behind it)
      const z = zo(x, y), zs = zf ? z : zo(x, y + 1);
      if (zs < z) { const q = [[x, y + 1, z], [x + 1, y + 1, z], [x + 1, y + 1, zs], [x, y + 1, zs]].map((v) => api.screenOf(...v)); if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: .999, face: true, down: Math.floor(part(q) * (z - zs))}; }
      const q = [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]].map(([a, b]) => api.screenOf(a, b, z));
      if (q.every((v) => v) && inq([mx, my], q)) return {x, y, fy: part(q)};
    }
    return null;
  };
  // how much of you is seen (tests): the share of your own drawn px that are on the screen as they are drawn
  api.catSeen = () => {
    const s = seen && seen.me; if (!s || !eng) return 0; const a = eng.at(s.x, s.y, s.z); if (!a) return 0;
    const sg = s.canvas.getContext("2d").getImageData(0, 0, s.canvas.width, s.canvas.height).data, g = ctx.getImageData(0, 0, cv.width, cv.height).data;
    let n = 0, ok = 0;
    for (let j = 0; j < s.canvas.height; j++) for (let i = 0; i < s.canvas.width; i++) { const o = (j * s.canvas.width + i) * 4; if (sg[o + 3] < 128) continue; n++;
      const X = Math.floor((Math.round(a[0]) - s.fx + i + .5) * Z()), Y = Math.floor((Math.round(a[1]) - s.fy + j + .5) * Z()), p = (Y * cv.width + X) * 4;
      if (X >= 0 && Y >= 0 && X < cv.width && Y < cv.height && Math.abs(g[p] - sg[o]) + Math.abs(g[p + 1] - sg[o + 1]) + Math.abs(g[p + 2] - sg[o + 2]) < 60) ok++; }
    return n ? ok / n : 0;
  };
  { const f0 = frame; frame = function (now) { f0(now); after(); }; }
  return api;
})();
