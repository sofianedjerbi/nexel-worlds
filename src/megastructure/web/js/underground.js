// Under ground: when the cut is on (xray.js: land is over you) and the land is over your own tile, the place round you
// is drawn by VoxUnder (vox_under.js) in the HD-2D look: a slice through the earth in natural strata, your space
// lit warm by your lantern, a cool beam where it opens to the sky, one sign by you (levels of land over your feet,
// your own column), the outline of a cave over your space dashed. Drawn at the art's own size and laid on the game's
// canvas zoom times bigger: every art px a whole square of px, you drawn px for px by the game's own drawEntity.
// It comes on whole (never half of two pictures): it grows in from the screen's edges, a hard stepped edge.
// On the surface the game's own view (behind a hill too: its keyhole); IN the ground (a cave, a hole, a canyon: xray.pic.hole, .pit) this one, sky-lit where open.
const Underground = (() => {
  const EASE = .3, CEIL = 2, CAM = {pitch: 38, fov: 26}, O = {r: 16, deep: 10};
  const LIGHT = {amb: .3, lr: 6.5, fog: [16, 32], fogc: [.06, .045, .04], clear: [.05, .04, .035]};
  const cfg = {levels: [-9, 12], variants: 4, up: RELIEF_STEP, rock: {from: 5, lo: -512, n: 4}};
  let pcs = new Map(), eng = null, a = 0, key = "", ver = -1, last = performance.now(), art = null, fx = null;
  const api = {a: 0, ms: 0, build: 0, on: false, force: null};
  function sprite(p, now) {      // (someone, drawn by the game at zoom 1: one art px a px)
    const T = P, w = T * 4, h = T * 5, base = h - T * 1.5;
    const pc = pcs.get(p) || document.createElement("canvas"); pcs.set(p, pc); if (pc.width !== w || pc.height !== h) { pc.width = w; pc.height = h; }
    const g = pc.getContext("2d"); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, w, h); g.imageSmoothingEnabled = false;
    const keep = ctx, kz = zoom, sx = (x) => w / 2 - T / 2 + (x - p.x) * T, sy = Object.assign((y) => base + (y - p.y) * T, {up: (y) => base + (y - p.y) * T});
    ctx = g; zoom = 1; try { drawEntity(p, sx, sy, T, now / 1000, now); } catch (e) { /* (nothing to draw) */ } finally { ctx = keep; zoom = kz; }
    return {canvas: pc, fx: w / 2, fy: Math.round(base + T * .5)};
  }
  // HD-2D's lens: far rows (the top of the picture) soft, near rows a little, the daylight blooming
  function post(pic, w, h) {
    art = art || document.createElement("canvas"); fx = fx || document.createElement("canvas");
    for (const c of [art, fx]) if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    const g = art.getContext("2d"), f = fx.getContext("2d"); g.globalCompositeOperation = "source-over"; g.filter = "none"; g.drawImage(pic, 0, 0);
    f.globalCompositeOperation = "source-over"; f.clearRect(0, 0, w, h); f.filter = "blur(1.6px)"; f.drawImage(pic, 0, 0); f.filter = "none";
    f.globalCompositeOperation = "destination-in"; const gr = f.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, "rgba(0,0,0,1)"); gr.addColorStop(.38, "rgba(0,0,0,0)"); gr.addColorStop(.85, "rgba(0,0,0,0)"); gr.addColorStop(1, "rgba(0,0,0,.6)"); f.fillStyle = gr; f.fillRect(0, 0, w, h);
    g.drawImage(fx, 0, 0);
    f.globalCompositeOperation = "source-over"; f.clearRect(0, 0, w, h); f.filter = "brightness(.5) contrast(9) blur(5px)"; f.drawImage(pic, 0, 0); f.filter = "none";
    g.globalCompositeOperation = "lighter"; g.globalAlpha = .15; g.drawImage(fx, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = "source-over";
    const vg = g.createRadialGradient(w / 2, h * .6, h * .4, w / 2, h * .6, w * .7); vg.addColorStop(0, "rgba(40,24,10,0)"); vg.addColorStop(1, "rgba(40,24,10,.3)"); g.fillStyle = vg; g.fillRect(0, 0, w, h);
    return art;
  }
  const FONT = {"-": [0, 0, 7, 0, 0], 0: [7, 5, 5, 5, 7], 1: [2, 6, 2, 2, 7], 2: [7, 1, 7, 4, 7], 3: [7, 1, 3, 1, 7], 4: [5, 5, 7, 1, 1], 5: [7, 4, 7, 1, 7], 6: [7, 4, 7, 5, 7], 7: [7, 1, 1, 2, 2], 8: [7, 5, 7, 5, 7], 9: [7, 5, 7, 1, 7]};
  function sign(g, t, x, y) {
    const W = t.length * 4 + 3, X = Math.round(x), Y = Math.round(y);
    g.fillStyle = "#2a1d17"; g.fillRect(X, Y, W, 9); g.fillStyle = "#6b4d36"; g.fillRect(X + 1, Y + 1, W - 2, 7);
    g.fillStyle = "#f2dfb4"; [...t].forEach((ch, i) => FONT[ch].forEach((r, j) => { for (let k = 0; k < 3; k++) if (r & (4 >> k)) g.fillRect(X + 2 + i * 4 + k, Y + 2 + j, 1, 1); }));
  }
  // the way up (a cool beam with motes down to each tile open to the sky), how deep you are, a cave over your space
  function marks(g, now, fx, fy, dep, L) {
    g.save(); g.globalCompositeOperation = "lighter";
    for (const [x, y, z] of eng.skies) { if (z > L) continue;   // (the beam: only down a cut near your level, not on the land outside)
      const a = eng.at(x, y, z), b = eng.at(x + 1, y, z), c = eng.at(x, y + 1, z); if (!a) continue;
      const tp = eng.at(x, y + 1, z + 7), x0 = Math.round(Math.min(a[0], c[0])), x1 = Math.round(Math.max(b[0], c[0] + b[0] - a[0])), yb = Math.round(c[1]), y0 = Math.max(0, Math.round(tp[1]));
      if (x1 < 0 || x0 > g.canvas.width || yb < 0 || yb - y0 < 2) continue;
      for (let px = x0 - 1; px <= x1 + 1; px++) {                 // shafts: 2 px of light, 1 dark, brighter in whole steps going down
        if ((px + x * 3) % 3 === 2) continue; const k = ((px * 7 + y * 5) % 5 + 5) % 5;
        for (let s = 0; s < 3; s++) { const ya = y0 + Math.round((yb - y0) * s / 3), yz = y0 + Math.round((yb - y0) * (s + 1) / 3); g.fillStyle = `rgba(190,215,240,${(.04 + s * .05 + (k === 0 ? .05 : 0)).toFixed(2)})`; g.fillRect(px, ya, 1, yz - ya); }
      }
      g.fillStyle = "rgba(255,245,210,.22)"; for (let py = Math.round(a[1]); py < yb; py++) for (let px = x0 + (py & 1); px < x1; px += 2) g.fillRect(px, py, 1, 1);   // the sunlit floor, a checker
      g.fillStyle = "rgba(255,250,225,.5)";
      for (let i = 0; i < 4; i++) { const s = (x * 7 + y * 13 + i * 31) % 97, my = y0 + (s * 5 + now / 40 * (1 + i % 2)) % (yb - y0); g.fillRect(x0 + (s * 3 + Math.round(Math.sin(now / 900 + s) * 2)) % Math.max(1, Math.abs(x1 - x0)), Math.round(my), 1, 1); }
    }
    g.globalCompositeOperation = "source-over";
    if (dep >= 1) sign(g, "-" + dep, fx + 10, fy - 26);
    const seen = new Set(), hk = new Map(eng.holes.map((h) => [h[0] + "," + h[1], h]));
    for (const h of eng.holes) { if (seen.has(h[0] + "," + h[1])) continue; const grp = [], st = [h];
      while (st.length) { const q = st.pop(), k = q[0] + "," + q[1]; if (seen.has(k)) continue; seen.add(k); grp.push(q);
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const n = hk.get((q[0] + dx) + "," + (q[1] + dy)); if (n && !n[3] === !q[3]) st.push(n); } }
      if (!grp[0][3]) continue;   // (a cave on another level reads by its dark footprint alone; one over your space: its outline dashed)
      g.fillStyle = "rgba(242,223,180,.55)";
      for (const q of grp) for (const [dx, dy, a0, b0, a1, b1] of [[0, -1, 0, 0, 1, 0], [1, 0, 1, 0, 1, 1], [0, 1, 0, 1, 1, 1], [-1, 0, 0, 0, 0, 1]]) {
        if (grp.some((r) => r[0] === q[0] + dx && r[1] === q[1] + dy)) continue; const u = eng.at(q[0] + a0, q[1] + b0, q[2] - 1), v = eng.at(q[0] + a1, q[1] + b1, q[2] - 1);
        const n = Math.max(Math.abs(v[0] - u[0]), Math.abs(v[1] - u[1])) | 0; for (let i = 0; i <= n; i += 1) if (i % 4 < 2) g.fillRect(Math.round(u[0] + (v[0] - u[0]) * i / n), Math.round(u[1] + (v[1] - u[1]) * i / n), 1, 1); }
    }
    g.restore();
  }
  function after() {
    if (HdLook.active || !me || myId === null || !Voxels.engine.ready()) return;
    const now = performance.now(), dt = Math.min(.1, (now - last) / 1000); last = now;
    const p = ents.get("agent" + myId); if (!p) return;
    const L = xray.L, tx = Math.round(p.x), ty = Math.round(p.y);
    const oc = Voxels.host.column(tx, ty) || [], dep = Math.max(0, (oc[oc.length - 1] | 0) - L);   // (how deep: levels from your feet up to the meadow over you, your own tile)
    let want = api.force !== null ? api.force : xray.a > .5 && xray.pic && (xray.pic.hole || xray.pic.pit) ? 1 : 0;   // (whole wherever you are IN the ground: a cave, a tunnel, a pit, a trench, a canyon; merely behind a hill, on the surface: the game's own keyhole)
    eng = eng || VoxUnder.create(Voxels.host, cfg);
    if (want || a) {
      if (ver !== landVer) { eng.forget(); ver = landVer; key = ""; }
      const k = [tx, ty, L].join(); if (k !== key) { eng.build(tx, ty, L, L + CEIL, O); key = k; api.build = eng.cost; }
    }
    a = want > a ? Math.min(want, a + dt / EASE) : Math.max(want, a - dt / EASE); api.a = a; api.on = a > 0; if (!a) return;
    const t0 = performance.now(), sf = sprite(p, now), sprs = [{canvas: sf.canvas, fx: sf.fx, fy: sf.fy, x: p.x + .5, y: p.y + .5, z: L}];
    for (const e of ents.values()) if (e !== p && e.x !== undefined && Math.abs(e.x - p.x) < 12 && Math.abs(e.y - p.y) < 9) { const q = sprite(e, now); sprs.push({canvas: q.canvas, fx: q.fx, fy: q.fy, x: e.x + .5, y: e.y + .5, z: e.z !== undefined ? Math.min(e.z, L + 8) : L}); }
    const w = Math.ceil(cv.width / zoom), h = Math.ceil(cv.height / zoom), snap = (v) => Math.round(v * 16) / 16;
    let pic = eng.draw({w, h, cam: CAM, at: [snap(p.x + .5), snap(p.y + .5), L + .5], t: now / 1000, light: Object.assign({day: clock.night ? .35 : 1, sk: .85}, LIGHT),
      water: typeof waterCv !== "undefined" && waterView ? {canvas: waterCv, x: waterView.x, y: waterView.y} : null, dep, sprites: sprs});
    if (!pic) return;
    pic = post(pic, w, h);
    { const f = eng.at(p.x + .5, p.y + .5, L); marks(pic.getContext("2d"), now, f[0], f[1], dep, L); }
    const e = a * a * (3 - 2 * a);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.imageSmoothingEnabled = false;
    if (e < .999) {   // (coming in: the slice grows in from the screen's edges, a hard stepped edge, never two pictures through each other)
      const rx = (1 - e) * (w / 2 + 24), ry = (1 - e) * (h / 2 + 24), cx = w / 2, cy = h / 2, R = [], Lf = [];
      ctx.beginPath(); ctx.rect(0, 0, w * zoom, h * zoom);
      for (let y = Math.floor((cy - ry) / 4) * 4; y < cy + ry; y += 4) { const d = (y + 2 - cy) / ry, hw = Math.round(rx * Math.sqrt(Math.max(0, 1 - d * d)) / 4) * 4; if (!hw) continue;
        R.push([cx + hw, y], [cx + hw, y + 4]); Lf.unshift([cx - hw, y + 4], [cx - hw, y]); }
      if (R.length) { const Q = R.concat(Lf); ctx.moveTo(Q[0][0] * zoom, Q[0][1] * zoom); for (const [x, y] of Q) ctx.lineTo(Math.round(x) * zoom, y * zoom); ctx.closePath(); }
      ctx.clip("evenodd");
    }
    ctx.drawImage(pic, 0, 0, w * zoom, h * zoom); ctx.restore();
    api.ms = performance.now() - t0;
  }
  { const f0 = frame; frame = function (now) { f0(now); after(); }; }
  return api;
})();
