// The HD look's cast shadows (hd.js, hd_things.js): what stands throws its own shape on the land, away from the game's
// sun (sunland.js `hour`: the classic picture's direction and length: long to the west in the morning, short at noon,
// long to the east in the evening, a little towards you always; none at night but away from a fire near by).
// A shadow is a small picture ON THE GROUND, in whole art px of the ground (16 a tile), made once for a shape and an
// hour's step: every px some px of the shape is thrown on, its outer px a softer rim. It is laid tile by tile, each
// piece on that tile's own top (down a step, up a step; not on water, not on a wall or a cliff's face, not under a
// roof, not on land the cut took away), by the engine's flat shade (vox_style.js `shade`: each px of the land is
// shaded once however many shadows lie on it).
//   HdSun.key() -> changes when the shadows must be made again; .sun: how dark the sun's are now (0..1)
//   HdSun.thing(out, x, y, L, P, dx, dy, r2): a standing sprite's (P: its px, hd_things.js pix; (dx, dy): where it is in its tile; r2: the row under its foot)
//   HdSun.box(out, x, y, L, [x0, y0, x1, y1], h0, h1): a box's (px of its tile; heights in px over the ground)
//   HdSun.body(out, s): a body's, each frame (s: hd.js's sprite of it) -> [[x, y, box]...] into out
const HdSun = (() => {
  const UP = RELIEF_STEP, bms = new Map(), sils = new Map(), SUN = [0xe0000000, 0xc0000000], LAMP = [0xff000000, 0xa0000000];   // (a full px, a rim px: vox_style_glsl.js kind 10)
  let H = {on: false, night: false, kx: 0, ky: 0, sun: 0}, sid = "";
  function hour() {
    const h = SunLand.hour(), want = !!opt("shadows") && !!opt("depth");
    H = {on: want && h.alpha > .02, night: want && h.dark > .35, kx: Math.round(h.kx * 8) / 8, ky: Math.round(h.ky / .6 * 8) / 8, sun: Math.min(1, h.alpha / Sun.SHADE.alpha)};   // (ky: the ground is seen from 36 degrees: as long on the screen as the classic picture's)
    return H;
  }
  const key = () => { hour(); return H.on ? H.kx + "," + H.ky : H.night ? "n" + fireAt.length : "-"; };
  // the fire that lights (x, y) at night -> where its shadows go there [vx, vy], or null
  function lamp(x, y) {
    let best = null, bd = Sun.SHADE.fire;
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
  // the top a shadow lies on at a tile, for what stands at level L: null: none (water, a wall, a cliff, under what is built, land the cut took away)
  const ground = (X, Y, L) => { const c = Voxels.host.column(X, Y); if (!c || !c.length || Voxels.host.water(X, Y) || Floors.any(X, Y)) return null; const t = c[c.length - 1]; return t - L > 1 || t - L < -4 || HdLook.cut(X, Y, t) ? null : t; };
  // lay a picture: (px, py): where its (0, 0) is, px from the tile (x, y)'s corner -> boxes for the engine, each a tile's (or a part of one), relative to (x, y)
  function lay(out, x, y, L, bm, px, py, wrap) {
    for (let ty = Math.floor(py / 16); ty * 16 < py + bm.h; ty++) for (let tx = Math.floor(px / 16); tx * 16 < px + bm.w; tx++) {
      const z = ground(x + tx, y + ty, L); if (z === null) continue;
      const x0 = Math.max(px, tx * 16), x1 = Math.min(px + bm.w, tx * 16 + 16), y0 = Math.max(py, ty * 16), y1 = Math.min(py + bm.h, ty * 16 + 16);
      for (let cj = (y0 - py) >> 4; cj * 16 < y1 - py; cj++) for (let ci = (x0 - px) >> 4; ci * 16 < x1 - px; ci++) {
        const ch = bm.chunk(ci, cj); if (!ch) continue;
        const a0 = Math.max(x0, px + ci * 16), a1 = Math.min(x1, px + ci * 16 + 16), b0 = Math.max(y0, py + cj * 16), b1 = Math.min(y1, py + cj * 16 + 16);
        const b = {x: a0, y: b0, z: z * UP + .5, w: a1 - a0, d: b1 - b0, h: 0, top: ch, win: [a0 - px - ci * 16, b0 - py - cj * 16], shade: true, sheet: HdThings.sheet};
        out.push(wrap ? [x, y, b] : b);
      }
    }
  }
  const open = (x, y, L) => { const c = Voxels.host.column(x, y); return !!c && c.length > 0 && c[c.length - 1] <= L && !Floors.any(x, y); };   // (under the sky: no land and nothing built over it)
  function thing(out, x, y, L, P, dx, dy, r2) {
    if (!open(x, y, L)) return; const v = way(x + .5, y + (dy + r2) / 16); if (!v) return;
    const bm = picture("t" + P.key + "," + r2, dx, dy + r2, v, (put) => { for (let j = 0; j < Math.min(P.h, r2); j++) for (let i = 0; i < P.w; i++) if ((P.px[j * P.w + i] >>> 24) >= 128) put(i, 0, r2 - 1 - j, r2 - j); });
    if (bm) lay(out, x, y, L, bm, bm.x + ((dx >> 4) << 4), bm.y + (((dy + r2) >> 4) << 4));
  }
  function box(out, x, y, L, r, h0, h1, built) {      // (built: a block of a floor or a roof: it is what is over its own tile)
    if (!built && !open(x, y, L)) return; const v = way(x + .5, y + .5); if (!v) return;
    const bm = picture("b" + [r[2] - r[0], r[3] - r[1], Math.round(h0), Math.round(h1)], r[0], r[1], v, (put) => { for (let j = 0; j < r[3] - r[1]; j++) for (let i = 0; i < r[2] - r[0]; i++) put(i, j, Math.round(h0), Math.round(h1)); });
    if (bm) lay(out, x, y, L, bm, bm.x + ((r[0] >> 4) << 4), bm.y + ((r[1] >> 4) << 4));
  }
  function body(out, s) {
    const kind = s.q.e ? s.q.e.kind || "agent" : "agent", X = Math.floor(s.x), Y = Math.floor(s.y + .42); if (!open(X, Y, s.z)) return; const v = way(s.x, s.y); if (!v) return;
    let S = sils.get(kind);
    if (!S) { const c = s.canvas, d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data, px = []; let low = 0;
      for (let j = 0; j < c.height; j++) for (let i = 0; i < c.width; i++) if (d[(j * c.width + i) * 4 + 3] >= 128) { px.push([i - s.fx, j]); low = Math.max(low, j); }
      if (!px.length) return; S = px.map(([i, j]) => [i, low - j]); sils.set(kind, S); }
    const bm = picture("e" + kind, 0, 0, v, (put) => { for (const [i, h] of S) put(i, 0, h, h + 1); });
    if (bm) lay(out, X, Y, s.z, bm, bm.x + Math.round((s.x - X) * 16), bm.y + Math.round((s.y + .42 - Y) * 16), true);
  }
  return {key, thing, box, body, way, get sun() { return H.on ? H.sun : 1; }, get hour() { return H; }};
})();
