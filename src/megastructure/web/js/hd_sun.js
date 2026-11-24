// The HD look's cast shadows (hd.js, hd_things.js): what stands throws its own shape on the land, away from the game's
// sun (sunland.js `hour`: the classic picture's direction and length: long to the west in the morning, short at noon,
// long to the east in the evening, a little towards you always; none at night but away from a fire near by).
// A shadow is a small picture ON THE GROUND, in whole art px of the ground (16 a tile), made once for a shape and an
// hour's step: every px some px of the shape is thrown on, its outer px a softer rim. It is laid tile by tile, each
// piece on that tile's own top (down a step, up a step; not on water, not on a wall or a cliff's face, not under a
// roof, not on land the x-ray window leaves out), by the engine's flat shade (vox_style.js `shade`: each px of the land is
// shaded once however many shadows lie on it).
//   HdSun.key() -> changes when the shadows must be made again; .sun: how dark the sun's are now (0..1)
//   HdSun.thing(out, x, y, L, P, dx, dy, r2): a standing sprite's (P: its px, hd_things.js pix; (dx, dy): where it is in its tile; r2: the row under its foot)
//   HdSun.box(out, x, y, L, [x0, y0, x1, y1], h0, h1): a box's (px of its tile; heights in px over the ground)
//   HdSun.body(out, s): a body's, each frame (s: hd.js's sprite of it) -> [[x, y, box]...] into out
//   HdSun.land(out, x, y): the land's own on a tile (a cliff's, a terrace's, a hill's); landAt(x, y): is there one (tests)
const HdSun = (() => {
  const UP = RELIEF_STEP, bms = new Map(), sils = new Map(), poses = new Map(), SUN = [0xe0000000, 0xc0000000], LAMP = [0xff000000, 0xa0000000];   // (a full px, a rim px: vox_style_glsl.js kind 10)
  let H = {on: false, night: false, kx: 0, ky: 0, sun: 0}, sid = "";
  function hour() {
    const h = SunLand.hour(), want = !!opt("shadows") && !!opt("depth");
    H = {on: want && h.alpha > .02, night: want && Light.now().night, kx: Math.round(h.kx * 8) / 8, ky: Math.round(h.ky * 8) / 8, sun: Math.min(1, h.alpha / SunLand.SHADE.alpha)};   // (kx, ky: the sun's way in the world, ground px a px of height; the eye's projection alone foreshortens it. It was ky / .6, made for the 36-degree eye: from 78.6 degrees a cliff's shadow lay 1.6x as long on the screen)
    return H;
  }
  const key = () => { hour(); return H.on ? H.kx + "," + H.ky : H.night ? "n" + fireAt.length : "-"; };
  // the fire that lights (x, y) at night -> where its shadows go there [vx, vy], or null
  function lamp(x, y) {
    let best = null, bd = SunLand.SHADE.fire;
    const see = (fx, fy) => { const d = Math.hypot(x - fx, y - fy); if (d < bd && d > .2) { bd = d; best = [fx, fy]; } };
    for (const f of fireAt) see(f.x + .5, f.y + .5);
    for (let j = -6; j <= 6; j++) for (let i = -6; i <= 6; i++) { const c = combAt(Math.floor(x) + i, Math.floor(y) + j); if (c === "^" || c === "x") see(Math.floor(x) + i + .5, Math.floor(y) + j + .5); }
    if (!best) return null; const k = Math.min(1.5, .5 + bd * .2) / bd;
    return [Math.round((x - best[0]) * k * 4) / 4, Math.round((y - best[1]) * k * 4) / 4];
  }
  const way = (x, y) => (H.on ? [H.kx, H.ky, SUN] : H.night ? ((v) => v && [v[0], v[1], LAMP])(lamp(x, y)) : null);
  // a shadow's picture: each(put): the shape, put(gx, gy, h0, h1): a px of it over the ground px (gx, gy), from h0 to h1 px high. (ox, oy): where the shape's (0, 0) is in its tile.
  // -> {x, y, w, h, chunk(i, j) -> its paint (16 x 16, hd_things.js's sheet) or null}: (x, y) px of the tile, a multiple of 16: its chunks are the tiles'
  function picture(k, ox, oy, v, each) {
    if (sid !== HdThings.sheet.id) { bms.clear(); sid = HdThings.sheet.id; }
    const kk = [k, ox & 15, oy & 15, v[0], v[1], v[2][0]].join(); let bm = bms.get(kk); if (bm) return bm;
    const on = new Set(), P = (x, y) => (x + 2048) * 4096 + y + 2048; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    each((gx, gy, h0, h1) => { for (let t = h0; t <= h1; t += .5) { const x = Math.round((ox & 15) + gx + v[0] * t), y = Math.round((oy & 15) + gy + v[1] * t); on.add(P(x, y)); if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } });
    if (x1 < x0) { bm = null; bms.set(kk, bm); return bm; }
    const X = Math.floor(x0 / 16) * 16, Y = Math.floor(y0 / 16) * 16, w = Math.ceil((x1 + 1 - X) / 16) * 16, h = Math.ceil((y1 + 1 - Y) / 16) * 16, has = (x, y) => on.has(P(x, y)), rooms = new Map();
    const px = (x, y) => (!has(x, y) ? 0 : has(x - 1, y) && has(x + 1, y) && has(x, y - 1) && has(x, y + 1) ? v[2][0] : v[2][1]);   // (its outer px: the rim)
    bm = {x: X, y: Y, w, h, chunk(i, j) { const c = i + "," + j; if (!rooms.has(c)) { let any = false; for (let b = 0; b < 16 && !any; b++) for (let a = 0; a < 16; a++) if (has(X + i * 16 + a, Y + j * 16 + b)) { any = true; break; }
      rooms.set(c, any ? HdThings.room("sun" + kk + "#" + c, 16, 16, (put) => { for (let b = 0; b < 16; b++) for (let a = 0; a < 16; a++) put(a, b, px(X + i * 16 + a, Y + j * 16 + b)); }) : null); } return rooms.get(c); }};
    bms.set(kk, bm); return bm;
  }
  // what a shadow lies on at a tile, for what stands at level L (none given: whatever is topmost): the land's top, or the top of what is built there (a floor's planks; a roof: its
  // pitch, hd_things.js) -> {z, roof}, or null: none (water, a step, land the x-ray window leaves out, a house open over your head, a top too far over or under L; a wall or a cliff's face never)
  function surface(X, Y, L) {
    const c = Voxels.host.column(X, Y); if (!c || !c.length || Voxels.host.water(X, Y)) return null;
    let t = c[c.length - 1], roof = null; const cells = Floors.any(X, Y) && Floors.cells(X, Y);
    if (cells && cells.size) { let top = -1e9, kind = ""; for (const [z, [k]] of cells) if (z > top) { top = z; kind = k; }
      if (kind === "stairs" || Floors.alpha(X, Y, top) < 1) return null; if (L === undefined || top - L <= 1) { t = top; if (kind === "roof") roof = HdThings.pitch(X, Y, top); } }   // (what is built high over L: the ground under it, seen under an eave: a lit strip lay along a house's foot)
    
    return L !== undefined && (t - L > 1 || t - L < -4) ? null : {z: t, roof};
  }
  // a piece of a shadow on a tile's surface: px a0..a1, b0..b1 of that tile, (ox, oy): the tile's corner in the caller's px; on a roof it leans with the pitch, in two at the ridge
  function piece(out, s, ox, oy, a0, a1, b0, b1, ch, wx, wy, at) {
    const R = s.roof, cutY = R && R.split && b0 < 8 && b1 > 8 ? [[b0, 8], [8, b1]] : [[b0, b1]];
    for (const [c0, c1] of cutY) { const b = {x: ox + a0, y: oy + c0, z: s.z * UP + .5, w: a1 - a0, d: c1 - c0, h: 0, top: ch, win: [wx, wy + c0 - b0], shade: true, sheet: HdThings.sheet};
      if (R) b.tilt = [R.hat(R.up + c0 / 16), R.hat(R.up + c1 / 16)]; out.push(at ? [at[0], at[1], b] : b); }
  }
  // lay a picture: (px, py): where its (0, 0) is, px from the tile (x, y)'s corner -> boxes for the engine, each a tile's (or a part of one), relative to (x, y)
  function lay(out, x, y, L, bm, px, py, wrap) {
    for (let ty = Math.floor(py / 16); ty * 16 < py + bm.h; ty++) for (let tx = Math.floor(px / 16); tx * 16 < px + bm.w; tx++) {
      const s = surface(x + tx, y + ty, L); if (!s) continue;
      const x0 = Math.max(px, tx * 16), x1 = Math.min(px + bm.w, tx * 16 + 16), y0 = Math.max(py, ty * 16), y1 = Math.min(py + bm.h, ty * 16 + 16);
      for (let cj = (y0 - py) >> 4; cj * 16 < y1 - py; cj++) for (let ci = (x0 - px) >> 4; ci * 16 < x1 - px; ci++) {
        const ch = bm.chunk(ci, cj); if (!ch) continue;
        const a0 = Math.max(x0, px + ci * 16), a1 = Math.min(x1, px + ci * 16 + 16), b0 = Math.max(y0, py + cj * 16), b1 = Math.min(y1, py + cj * 16 + 16);
        piece(out, s, tx * 16, ty * 16, a0 - tx * 16, a1 - tx * 16, b0 - ty * 16, b1 - ty * 16, ch, a0 - px - ci * 16, b0 - py - cj * 16, wrap && [x, y]);
      }
    }
  }
  // The land's own shadow: a cliff, a terrace, a hill throws the hour's shadow on the land under it (the classic picture had it). For a tile's surface, px by px: is some
  // column towards the sun, two levels or more over it, between the px and the sun? (a px h px under a top is in its shadow when the px, moved h back along the sun's
  // way, is on that top's tile.) The same tone and the same soft rim as the things' shadows, on tops only (never a wedge on a wall's face); kept until the land or the sun moves on.
  const lands = new Map(), tops = new Map(), TALL = 192; let lkey = null;   // (TALL: the height in px a column's shadow is counted to: 12 levels, the gorge's cliff whole. It was 6: a taller cliff's shadow stopped short, cut straight)
  const topOf = (x, y) => { const k = (x + 32768) * 65536 + y + 32768; let t = tops.get(k); if (t === undefined) { const c = Voxels.host.column(x, y); t = c && c.length ? c[c.length - 1] : null; tops.set(k, t); } return t; };
  function land(out, x, y) {
    if (!H.on) return; const lk = lkey; if (!lk || lk[0] !== landVer || lk[1] !== Floors.ver || lk[2] !== H.kx || lk[3] !== H.ky || lk[4] !== HdThings.sheet.id || lands.size > 8000) { lands.clear(); tops.clear(); lkey = [landVer, Floors.ver, H.kx, H.ky, HdThings.sheet.id]; }   // (what it hangs on, looked at: a string was made of it for every tile asked)
    const s = surface(x, y); if (!s) return; const k = x + "," + y + "," + s.z; let ch = lands.get(k);
    // (the columns asked: a column further each way than the shadows reach: the px just outside the tile are asked too, for the rim: without them each tile's shadow had a rim of its own, light lines between tiles)
    if (ch === undefined) { ch = null; const src = [], sg = H.kx < 0 ? 1 : -1, nx = Math.ceil(TALL * Math.abs(H.kx) / 16), ny = Math.ceil(TALL * H.ky / 16);
      for (let j = -1; j <= ny + 1; j++) for (let i = -1; i <= nx + 1; i++) { if (!i && !j) continue; const T = topOf(x + sg * i, y - j); if (T === null || (T - s.z) * UP < 16) continue; const h = Math.min(TALL, (T - s.z) * UP);
        if ((i - 1) * 16 <= h * Math.abs(H.kx) + 1 && (j - 1) * 16 <= h * H.ky + 1) src.push([sg * i * 16, -j * 16, h]); }   // (a column whose shadow does not reach this tile is not asked of every px: as many as 12 levels counted made the land's shadows 2.4x as slow)
      if (src.length) { const kx = H.kx, ky = H.ky, ns = src.length, sx = new Float32Array(ns), sy = new Float32Array(ns), sh = new Float32Array(ns); src.forEach((q, i) => { sx[i] = q[0]; sy[i] = q[1]; sh[i] = q[2]; });
        // (is a ground px in the shadow of one of the columns: the stretch of the sun's ray over that column's tile, across and along, within its height. In plain numbers: it made two lists and sorted them for every px of every column: most of the script's time when land came in)
        const dark = (gx, gy) => { gx += .5; gy += .5; for (let i = 0; i < ns; i++) { let p0, p1, q0, q1;
          if (kx) { const a = (gx - sx[i] - 16) / kx, b = (gx - sx[i]) / kx; p0 = a < b ? a : b; p1 = a < b ? b : a; } else if (gx >= sx[i] && gx < sx[i] + 16) { p0 = 0; p1 = 1e9; } else continue;
          if (ky) { const a = (gy - sy[i] - 16) / ky, b = (gy - sy[i]) / ky; q0 = a < b ? a : b; q1 = a < b ? b : a; } else if (gy >= sy[i] && gy < sy[i] + 16) { q0 = 0; q1 = 1e9; } else continue;
          if (Math.max(p0, q0, 0) < Math.min(p1, q1, sh[i])) return true; } return false; };
        const m = new Uint8Array(18 * 18); let any = false, str = ""; for (let b = -1; b <= 16; b++) for (let a = -1; a <= 16; a++) if (dark(a, b)) m[(b + 1) * 18 + a + 1] = 1;
        const v = (a, b) => (!m[(b + 1) * 18 + a + 1] ? 0 : m[(b + 1) * 18 + a] && m[(b + 1) * 18 + a + 2] && m[b * 18 + a + 1] && m[(b + 2) * 18 + a + 1] ? 1 : 2);
        for (let b = 0; b < 16; b++) for (let a = 0; a < 16; a++) { const q = v(a, b); str += q; if (q) any = true; }
        if (any) ch = HdThings.room("ls" + str, 16, 16, (put) => { for (let b = 0; b < 16; b++) for (let a = 0; a < 16; a++) { const q = v(a, b); put(a, b, q ? SUN[q - 1] : 0); } }); }
      lands.set(k, ch); }
    if (ch) piece(out, s, 0, 0, 0, 16, 0, 16, ch, 0, 0);
  }
  // is a tile's top in the land's shadow at its middle (tests)
  const landAt = (x, y) => { hour(); const o = []; land(o, x, y); return o.length > 0; };
  const open = (x, y, L, roofed) => { const c = Voxels.host.column(x, y); if (!c || !c.length || c[c.length - 1] > L) return false; const cells = !roofed && Floors.any(x, y) && Floors.cells(x, y); if (cells) for (const z of cells.keys()) if (z > L) return false; return true; };   // (under the sky: no land and nothing built over it)
  function thing(out, x, y, L, P, dx, dy, r2) {
    if (!open(x, y, L)) return; const v = way(x + .5, y + (dy + r2) / 16); if (!v) return;
    const bm = picture("t" + P.key + "," + r2, dx, dy + r2, v, (put) => { for (let j = 0; j < Math.min(P.h, r2); j++) for (let i = 0; i < P.w; i++) if ((P.px[j * P.w + i] >>> 24) >= 128) put(i, 0, r2 - 1 - j, r2 - j); });
    if (bm) lay(out, x, y, L, bm, bm.x + ((dx >> 4) << 4), bm.y + (((dy + r2) >> 4) << 4));
  }
  function box(out, x, y, L, r, h0, h1, built) {      // (built: a block of a floor or a roof: it is what is over its own tile)
    if (!built && !open(x, y, L, true)) return; const v = way(x + .5, y + .5); if (!v) return;   // (a wall under its own roof throws its shadow too: there was a lit strip between a house's foot and its roof's shadow; indoors nothing takes it)
    const bm = picture("b" + [r[2] - r[0], r[3] - r[1], Math.round(h0), Math.round(h1)], r[0], r[1], v, (put) => { for (let j = 0; j < r[3] - r[1]; j++) for (let i = 0; i < r[2] - r[0]; i++) put(i, j, Math.round(h0), Math.round(h1)); });
    if (bm) lay(out, x, y, L, bm, bm.x + ((r[0] >> 4) << 4), bm.y + ((r[1] >> 4) << 4));
  }
  // a body's: the shape it has NOW (its pose, the way it faces: its own picture this frame; it was the shape it had when first seen), thrown from its feet
  function body(out, s) {
    const kind = s.q.e ? s.q.e.kind || "agent" : "agent", X = Math.floor(s.x), Y = Math.floor(s.y + .42), Z = s.zh ?? s.z; if (!open(X, Y, Z)) return; const v = way(s.x, s.y); if (!v) return;   // (Z: where the body stands as the land's depth has it (hd.js zh): a swimmer lifted to a river's rim cast its shadow on the bank)
    const c = s.canvas, pk = c._h === undefined ? undefined : kind + c._h; let sk = pk === undefined ? undefined : poses.get(pk), S = sk ? sils.get(sk) : null;   // (a picture made by the same calls as one looked at before (canvas._h, hd.js): its shape is known: its px were read and counted every frame)
    if (sk === undefined || (sk && !S)) { const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let hsh = 0, n = 0;
    for (let i = 3, k = 0; i < d.length; i += 4, k++) if (d[i] >= 128) { hsh = (Math.imul(hsh, 31) + k) | 0; n++; }
    sk = n ? kind + hsh + "," + n : null; if (pk !== undefined) { if (poses.size > 600) poses.clear(); poses.set(pk, sk); } S = sk ? sils.get(sk) : null;
    if (sk && !S) { const px = []; let low = 0; for (let j = 0; j < c.height; j++) for (let i = 0; i < c.width; i++) if (d[(j * c.width + i) * 4 + 3] >= 128) { px.push([i - s.fx, j]); low = Math.max(low, j); }
      if (sils.size > 300) sils.clear(); S = px.map(([i, j]) => [i, low - j]); sils.set(sk, S); } }
    if (!sk) return;
    if (bms.size > 1500) bms.clear();
    const bm = picture("e" + sk, 0, 0, v, (put) => { for (const [i, h] of S) put(i, 0, h, h + 1); });
    if (bm) lay(out, X, Y, Z, bm, bm.x + Math.round((s.x - X) * 16), bm.y + Math.round((s.y + .42 - Y) * 16), true);
  }
  return {key, thing, box, body, way, land, landAt, surface, get sun() { return H.on ? H.sun : 1; }, get hour() { return H; }};
})();
