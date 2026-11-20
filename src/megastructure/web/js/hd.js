// The HD look (the default land view; Settings, Picture, Look: HD or Classic): ONE look on the surface and under ground. The land round you is drawn by VoxStyle
// (vox_style.js) at the art's own size, a tilted perspective, every face from the tileset, and laid on the game's
// canvas zoom times bigger. Over it the game's own sky (its curved horizon's, copied from the frame the game drew).
// Going down nothing switches: how shut in you are (levels of land over your tile and round it) is one number u,
// 0 in the open, 1 under ground; the earth's slice (style 6) opens in a ring round you that grows with u, the light
// goes from the day's to your lantern's, the sky fades into the dark of the earth. Trees, houses, things: upright
// billboards of their own sprites (objectSprite), px for px; you and the others: drawEntity at zoom 1.
const HdLook = (() => {
  const urlLook = new URLSearchParams(location.search).get("look"), EASE = 1.2, GROW = .4, R = 24;
  const cfg = {levels: [-9, 12], variants: 4, up: RELIEF_STEP, rock: {from: 5, lo: -512, n: 4}};
  const cam = {kind: "persp", pitch: 36, fov: 26};
  const api = {get active() { return (urlLook || opt("look")) === "hd"; }, get on() { return this.active && !!me && myId !== null; }, u: 0, ms: 0, build: 0, box: null, force: null, bend: .03, blur: 1, faces: 0, builds: 0};
  let ul = 0, wd = 0, gen = null, seen = null, eng = null, key = "", ver = -1, last = performance.now(), u = 0, back = null, art = null, fx = null, lit = null, hl = 0;
  const sprs = new Map(), things = new Map();
  const mix = (a, b, k) => Array.isArray(a) ? a.map((v, i) => v + (b[i] - v) * k) : a + (b - a) * k;
  function ent(p, now) {      // (a person or a creature, drawn by the game at zoom 1: one art px a px)
    const T = P, w = T * 4, h = T * 5, base = h - T * 1.5;
    let pc = sprs.get(p) || document.createElement("canvas"); sprs.set(p, pc); if (pc.width !== w || pc.height !== h) { pc.width = w; pc.height = h; }
    const g = pc.getContext("2d"); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, w, h); g.imageSmoothingEnabled = false;
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
  // the lens: far rows (the top) a little soft, the rest crisp; a faint bloom of the light parts; no vignette
  function post(pic, w, h) {
    art = art || document.createElement("canvas"); fx = fx || document.createElement("canvas");
    for (const c of [art, fx]) if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    const g = art.getContext("2d"), f = fx.getContext("2d"); g.globalCompositeOperation = "source-over"; g.clearRect(0, 0, w, h); g.drawImage(pic, 0, 0);
    if (api.blur > 0) {
      f.globalCompositeOperation = "source-over"; f.clearRect(0, 0, w, h); f.filter = `blur(${api.blur}px)`; f.drawImage(pic, 0, 0); f.filter = "none";
      f.globalCompositeOperation = "destination-in"; const gr = f.createLinearGradient(0, 0, 0, h);
      gr.addColorStop(0, "rgba(0,0,0,.85)"); gr.addColorStop(.3, "rgba(0,0,0,0)"); f.fillStyle = gr; f.fillRect(0, 0, w, h);
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
      const ph = clock.phase || 0, ws = washAt(ph), lf = opt("night") / 100 * .6; g.drawImage(Voxels.pic || cv, 0, 0, w * zoom, line * zoom, 0, 0, w, line);
      if (Voxels.pic) { g.globalAlpha = ws[3]; g.fillStyle = `rgb(${ws.slice(0, 3).join()})`; g.fillRect(0, 0, w, line); g.globalAlpha = 1; g.globalCompositeOperation = "multiply"; g.fillStyle = `rgb(${lightAt(ph).map((v) => Math.round(v + (255 - v) * lf)).join()})`; g.fillRect(0, 0, w, line); g.globalCompositeOperation = "source-over"; }
    }
    if (k > 0) { g.fillStyle = `rgba(13,10,9,${k.toFixed(3)})`; g.fillRect(0, 0, w, h); }
    return {canvas: back, low};
  }
  // the hour's light on the land: the game's own (daylight.js: its tint, its wash, a lamp on each of you and each fire, in whole steps), put where this camera
  // puts them; under a roof (el) none of it. (It was the shader's `day` alone: the night's land as bright as noon under a night sky.)
  function hour(raw, g, w, h, list, el) {
    const ph = clock.phase || 0, tint = lightAt(ph).map((v) => v + (255 - v) * el), wash = washAt(ph), dark = Math.min(1, (1 - (.3 * tint[0] + .59 * tint[1] + .11 * tint[2]) / 255) / .36);
    if (wash[3] * (1 - el) <= .004 && dark <= .01) return;
    lit = lit || document.createElement("canvas"); if (lit.width !== w || lit.height !== h) { lit.width = w; lit.height = h; }
    const q = lit.getContext("2d"), lift = opt("night") / 100 * .6; q.globalAlpha = 1; q.globalCompositeOperation = "source-over"; q.fillStyle = `rgb(${tint.map((v) => Math.round(v + (255 - v) * lift)).join()})`; q.fillRect(0, 0, w, h);
    if (dark > .2) { q.globalCompositeOperation = "lighter"; const k = (dark - .2) / .8;
      for (const s of list) if (s.lamp) { const a = eng.at(s.x, s.y, s.z); lamp(q, a[0], a[1] - 8, s.lamp > 1 ? 64 : 42, s.lamp > 1 ? "rgb(255,176,96)" : "rgb(255,222,170)", (s.lamp > 1 ? 1.15 : .45) * k, [0, 0]); } }
    q.globalAlpha = 1; g.globalCompositeOperation = "source-over"; g.globalAlpha = wash[3] * (1 - el); g.fillStyle = `rgb(${wash.slice(0, 3).join()})`; g.fillRect(0, 0, w, h); g.globalAlpha = 1;
    g.globalCompositeOperation = "multiply"; g.drawImage(lit, 0, 0); g.globalCompositeOperation = "destination-in"; g.drawImage(raw, 0, 0); g.globalCompositeOperation = "source-over";
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
    const ghost = (ch, x, y, a) => { const spr = ch && objectSprite(ch, x, y, t); if (!spr || !spr[0] || !spr[0].width) return; const r = rectOf(spr, x, y); ctx.globalAlpha = a; ctx.imageSmoothingEnabled = false; ctx.drawImage(spr[0], spr[1], spr[2], spr[3], spr[4], ...r); ctx.globalAlpha = 1; };
    const box = (r) => [[r[0], r[1]], [r[0] + r[2] - px, r[1]], [r[0] + r[2] - px, r[1] + r[3] - px], [r[0], r[1] + r[3] - px]], bound = (c) => { const xs = c.map((v) => v[0]), ys = c.map((v) => v[1]); return {x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)}; };
    if (Build.on) {   // build mode: what is planned, each on its own tile at its own height as this camera has it, and the cursor (the game drew them at the classic picture's places)
      for (const j of Build.S.plans.values()) { const c = quad(j.x, j.y, j.z); if (c.some((v) => !v)) continue;
        if (!j.take && !j.dig && !j.steps) ghost(PLACEABLE_BLOCK[j.item], j.x, j.y, j.state === "doing" ? .75 : .5);
        fill(c, j.state === "bad" ? "rgba(230,80,70,.4)" : j.take ? "rgba(255,150,60,.3)" : j.state === "doing" ? "rgba(255,241,168,.35)" : "rgba(140,190,255,.28)"); if (j.dig) fill(c.map((v, i) => [v[0] + (c[(i + 2) % 4][0] - v[0]) * .2, v[1] + (c[(i + 2) % 4][1] - v[1]) * .2]), "rgba(60,36,30,.5)"); }
      const at = Build.S.at; if (at) { const c = quad(at.x, at.y, Build.level()), it = Build.aim().it, mx = (myPos() || at).x; if (it && it.ghost && it.ok !== false) ghost(PLACEABLE_BLOCK[it.ghost], at.x, at.y, .7);
        corners(c, it && it.ok === false ? "#e8554a" : Math.floor(t * 3) % 2 ? "#fff1a8" : "#ffffff"); Build.S.rect = Object.assign(bound(c), {under: mx !== at.x, right: mx < at.x}); Prompts.build(); }
    } else {          // the aim: what stands there, round its picture; a ghost of what would be put; else the corners of the tile as the land shows it; its keys beside it (prompts.js)
      const aim = aimedTile(), it = aim && aim.it, a = aim && aim.p, on = a && tile(a.x, a.y) && it && !it.info && !it.walk; let r = null;
      if (on && it.ghost) ghost(PLACEABLE_BLOCK[it.ghost], a.x, a.y, .7);
      if (on) { const e = it.ent && seen.list.find((s) => s.q && s.q.e === it.ent || s.q === it.ent), c0 = combAt(a.x, a.y), spr = !e && c0 && isObject(c0) && objectSprite(c0, a.x, a.y, t), f = e && api.screenOf(e.x, e.y, e.z);
        const c = e ? box([snap(f[0] - 8 * px), snap(f[1] - 12 * px), 16 * px, 16 * px]) : spr && spr[0] ? box(rectOf(spr, a.x, a.y)) : quad(a.x, a.y, shown(a.x, a.y)); corners(c, it.ok === false ? "#e8554a" : "#fff8e8"); r = bound(c); }
      Prompts.show(r, faceRows);
    }
    for (const s of seen.list) if (s.q && s.q.e && (s.q.e.kind === "agent" || s.q.e.name)) drawNameplate(s.q, sx, sy, S);
    for (const s of seen.list) if (s.q && s.q.e && (ANIMALS[s.q.e.kind] || !bubbles.some((b) => b.name === s.q.e.name))) drawEmote(s.q, sx, sy, S);
    drawProgress(sx, sy, S); drawBubbles(sx, sy, S, t); ctx.textAlign = "start";
  }
  // the game's sky with its horizon where this land's is: the top of the bent ground at your level (it was the classic picture's horizon, higher: a wide empty band
  // between the sky and the land, a third of a phone held upright); it follows your height softly
  api.sky = (t) => { const s = Curve.sky(t); return api.on && hl ? Object.assign({}, s, {line: Math.round(hl) * zoom}) : s; };
  function horizon(tx, ty, L, dt) { let y = 1e9; for (let dn = 6; dn <= 22; dn++) { const a = eng.at(tx + .5, ty - dn, L); if (a) y = Math.min(y, a[1]); } if (y < 1e8) hl = hl ? hl + (Math.max(8, y + 2) - hl) * Math.min(1, dt * 5) : Math.max(8, y + 2); }
  function after() {
    if (!api.on || !Voxels.engine.ready()) return;
    const now = performance.now(), dt = Math.min(.1, (now - last) / 1000); last = now;
    const p = ents.get("agent" + myId); if (!p) return;
    const H0 = Voxels.host, wet = (x, y) => H0.water && H0.water(x, y) && H0.waterTop ? H0.waterTop(x, y) : -1e9;   // (in water: you stand at its face)
    const t0 = performance.now(), L = xray.a > .5 ? xray.L : Math.max(topAt(Math.round(p.x), Math.round(p.y)), wet(Math.round(p.x), Math.round(p.y))), tx = Math.round(p.x), ty = Math.round(p.y);
    const roof = shut(tx, ty, L), want = api.force !== null ? api.force : Math.max(roof, (wd = walled(tx, ty, L)) ? 1 : 0);
    ul = roof > ul ? Math.min(roof, ul + dt / EASE) : Math.max(roof, ul - dt / EASE);   // (the light goes under ground only under a roof)
    u = want > u ? Math.min(want, u + dt / EASE) : Math.max(want, u - dt / EASE); api.u = u;
    const e = u * u * (3 - 2 * u), gr = Math.min(1, ul / GROW), gs = gr * gr * (3 - 2 * gr), b0 = [1, 3, Math.max(2, Math.round(e * (wd + 1)))], b1 = [1 + e * (R - 10), 1 + e * R, 1 + e * R].map((v, i) => Math.round(mix(b0[i], v, gs))),
      box = e < .08 ? null : {n: b1[0], w: b1[1], s: b1[2]},   // (walls alone: a small box round you; a roof: the whole cut-away, grown from the small one tile by tile as the roof closes over you (it came all at once))
        // (the cut-away: south and across all, north 14 tiles, so the land beyond it, the surface, sinks to the horizon under the sky at any depth; beyond it the land whole, its terraces, the sky)
      inBox = (x, y) => !!box && y - ty >= -box.n && y - ty <= box.s && Math.abs(x - tx) <= box.w, dep = Math.max(0, topAt(tx, ty) - L);
    eng = eng || VoxStyle.create(Voxels.host, cfg);
    if (ver !== landVer) { eng.forget(); ver = landVer; key = ""; }
    const k = [tx, ty, L, JSON.stringify(box)].join();
    if (k !== key && !gen) { gen = eng.steps(tx, ty, L, L + 2, {r: R, deep: 20, over: 0, under: true, sea: 1, cut: box || {n: -9, s: -9, w: -9}}); key = k; api.box = box; api.build = 0; api.builds++; }   // (one land at a time: the next is made when this one is done, so a box that grows is shown at each size it was made at)
    if (gen) { const b0 = performance.now(); while (performance.now() - b0 < 6) if (gen.next().done) { gen = null; break; } api.build = Math.max(api.build, performance.now() - b0); api.water = eng.water; }   // (the land made again a few rows a frame, ~6 ms; what was drawn stays till it is done)
    const list = [];
    for (let y = ty - R; y <= ty + 6; y++) for (let x = tx - R; x <= tx + R; x++) {
      if (inBox(x, y) && topAt(x, y) > L + 2) continue;   // (on land the slice took away)
      const c = combAt(x, y); if (!c || !isObject(c)) continue;
      const s = objectSprite(c, x, y, now / 1000); if (!s || !s[0] || !s[0].width) continue;
      list.push(Object.assign(thing(s), {x: x + .5, y: y + 1, z: topAt(x, y), lamp: c === "^" || c === "x" ? 2 : 0, flat: "%W+#g".includes(c), tx: x, ty: y}));   // (flat: a built wall, a door, a fence: a standing face of the land a tile wide, so neighbours touch, vox_style.js)
    }
    for (const q of ents.values()) if (q.x !== undefined && Math.abs(q.x - p.x) < 16 && Math.abs(q.y - p.y) < 12) {
      const s = ent(q, now), z = q === p ? L : topAt(Math.round(q.x), Math.round(q.y));
      list.push({canvas: s.canvas, fx: s.fx, fy: s.fy, x: q.x + .5, y: q.y + .5, z, d: q !== p, top: q === p, q, lamp: q.e && q.e.kind === "agent" ? 1 : 0});   // (you: never hidden by land)
    }
    list.sort((a, b) => a.y - b.y);
    const w = Math.ceil(cv.width / zoom), h = Math.ceil(cv.height / zoom), snap = (v) => Math.round(v * 16) / 16;
    const sky = typeof Curve !== "undefined" && Curve.on ? api.sky(now / 1000) : null, bd = backdrop(w, h, sky, 0, tx, ty);   // (the sky stays at any depth: over the far land)
    const day = 1, ed = h / (32 * Math.tan(cam.fov * Math.PI / 360));   // (the eye's distance: fog counts from there)
    const el = ul * ul * (3 - 2 * ul), light = {amb: mix(.8, .62, el), lr: mix(8, 6.5, el), day, sk: .85, fog: [mix(ed + 4, ed + 8, el), mix(ed + 22, ed + 34, el)], fogc: mix(bd.low, [.5, .45, .4], el * .6), clear: [0, 0, 0], ca: 0, dark: el,
      roof: .6, rim: mix(.25, .6, el), under: true, wa: .92, ub: box ? [box.n, box.w, box.s, 1] : [-9, -9, -9, 1]};
    let pic = eng.draw({w, h, cam, at: [snap(p.x + .5), snap(p.y + .5), L + .5], bend: api.bend, t: now / 1000, light,
      water: typeof waterCv !== "undefined" && waterView ? {canvas: waterCv, x: waterView.x, y: waterView.y} : null, dep, sprites: list});
    if (!pic) return;
    seen = {tx, ty, L, box, k: cv.width / W, me: list.find((q) => q.top), list}; horizon(tx, ty, L, dt);
    api.faces = eng.faces; const raw = pic; pic = post(pic, w, h); hour(raw, pic.getContext("2d"), w, h, list, el);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.imageSmoothingEnabled = false;
    ctx.drawImage(bd.canvas, 0, 0, w * zoom, h * zoom);
    if (el > .05) {   // under a roof: the sky stays as a band over the earth's far edge, a ridge in whole steps of 2 art px (the earth's silhouette), lower as you go deeper
      const top = Math.round(Math.min(h * .16, 4 + dep * 1.5) * el), sx = Math.round(p.x * 2); ctx.beginPath(); ctx.moveTo(0, h * zoom);
      for (let x = 0; x <= w; x += 2) { const n = Math.sin((x + sx) * .071) * 2.5 + Math.sin((x + sx) * .023 + 1.3) * 3.5, y = Math.max(0, top + Math.round(n / 2) * 2); ctx.lineTo(x * zoom, y * zoom); ctx.lineTo((x + 2) * zoom, y * zoom); }
      ctx.lineTo(w * zoom, h * zoom); ctx.closePath(); ctx.clip();
    }
    ctx.drawImage(pic, 0, 0, w * zoom, h * zoom); ctx.restore();
    written(p, now);
    api.ms = performance.now() - t0;
  }
  // what is under the pointer (client px): the nearest top drawn there, as the land shows it (a top the cut took away: at the cut)
  const shown = (x, y) => { const t = topAt(x, y); return seen && seen.box && t > seen.L + 2 && y - seen.ty >= -seen.box.n && y - seen.ty <= seen.box.s && Math.abs(x - seen.tx) <= seen.box.w ? seen.L + 2 : t; };
  api.screenOf = (x, y, z) => { if (!eng || !seen) return null; const a = eng.at(x, y, z); return a && [a[0] * zoom / seen.k, a[1] * zoom / seen.k]; };
  // -> the tile under the pointer: from the south (the nearest) north, the first whose south front or whose top is under it (a front: face, down: levels under its top, as mouse.js). zf: its height, if not the land's as shown (build mode)
  api.pick = (mx, my, zf) => {
    if (!eng || !seen) return null;
    const inq = (P, q) => { let s = 0; for (let i = 0; i < 4; i++) { const a = q[i], b = q[(i + 1) % 4], c = (b[0] - a[0]) * (P[1] - a[1]) - (b[1] - a[1]) * (P[0] - a[0]); if (c && s && Math.sign(c) !== s) return false; if (c) s = Math.sign(c); } return true; };
    const zo = (x, y) => (zf ? zf(x, y) : shown(x, y)), part = (q) => Math.max(0, Math.min(.999, (my - Math.min(q[0][1], q[1][1])) / Math.max(1, Math.max(q[2][1], q[3][1]) - Math.min(q[0][1], q[1][1]))));
    for (let y = seen.ty + 8; y >= seen.ty - R; y--) for (let x = seen.tx - R; x <= seen.tx + R; x++) {
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
      const X = Math.floor((Math.round(a[0]) - s.fx + i + .5) * zoom), Y = Math.floor((Math.round(a[1]) - s.fy + j + .5) * zoom), p = (Y * cv.width + X) * 4;
      if (X >= 0 && Y >= 0 && X < cv.width && Y < cv.height && Math.abs(g[p] - sg[o]) + Math.abs(g[p + 1] - sg[o + 1]) + Math.abs(g[p + 2] - sg[o + 2]) < 60) ok++; }
    return n ? ok / n : 0;
  };
  { const f0 = frame; frame = function (now) { f0(now); after(); }; }
  return api;
})();
