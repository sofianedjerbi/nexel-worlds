// Clear water (the settings' Picture page, on by default): the water is seen through, to its bed. The engine draws it
// (vox_water.js); this file says what is under the water, since the world does not: a water tile is a ground kind at
// its tile's level, and its kind says how deep it is (vocab.js DEPTH_OF: 1 to 4 layers), no more.
// The bed is calm: one body getting deeper toward its middle. A level down a tile from its banks (a rim), then the
// basin, 2 deep; its kind takes it deeper (3, the dark) only FAR tiles or more from a bank: a pond, a river have one
// step, a lake two, the sea its own. What only stands in the water (a pillar, an islet, a pile: SMALL tiles of land
// or fewer, joined by their sides) is not a bank: it rises out of a bed that is as deep as it would be without it
// (a step down round every pillar, each with its lip: a quilt). And a tile that differs from 6 of the 8 round it
// (a notch, a tongue one tile wide) takes their depth; the deep is nowhere less than two tiles wide.
// It is for the eye only: what you aim at, swim on and build on is the water's face, as ever (cells.js knows no bed).
// Its paint is water.js's own bottom (sand, ridges, pebbles, weed), its sides the earth of the land's walls, the
// tint over it water.js's own, by depth; water.js then draws only what is on the face (waves, glints).
// A bed depends on the land round it: when a tile changes, the beds within reach of it are looked at again, and
// what changed is made again with what is drawn from it (`changed`, `flush`: voxels.js). What is worked out is kept a
// chunk at a time, made once (`grids`), forgotten only round a tile that changed.
// Off: none of this; the water is water.js's picture on one face, as it was.
const WaterBed = (() => {
  const REACH = 2, FAR = 4, SMALL = 12, LOOK = 6, cfg = {clear: false, dark: 4};      // (cfg: the engine's cfg.water; LOOK: how far a tile's change is looked for in the beds)
  // The tint over a bed, by its depth (0: none; 1 to 3 levels): water.js's own hues, thicker: a pond one level deep is
  // water at every hour, never a pit of pale sand. BAND: the first row of a wall under water, that much of its colour: a shelf's line, not a box's edge
  const TINT = [[176, 236, 226, .08], [104, 204, 208, .52], [70, 174, 204, .66], [44, 132, 188, .8]], BAND = .93;
  let tint = null, pad = null, legs = null, floats = null;      // (floats: the shapes of what floats, water_objects 8, 9, 10, 11, 6, 7, 0: 16 x 16 bytes each, 1 where it is)
  // What is worked out, kept a chunk (B x B tiles) at a time in typed arrays, made as it is first asked for and kept
  // until a tile near it changes (not when other land comes: a sprint into new land threw it all away every block):
  // d the bed's depth, r its depth before smoothing, s is that land a piece that only stands in the water (1) or a bank
  // (0), sh the depth it was painted with (-1: none of it, unknown, not painted), w is it water (1, 0; -1 unknown), col its column (an array: the engine's)
  const grids = new Map(), gk = (bx, by) => bx * 4194304 + by, N4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  let hx = NaN, hy = NaN, hg = null, gi = 0;
  function G(x, y) {                                            // -> the grid of tile (x, y), its index in gi
    const bx = Math.floor(x / B), by = Math.floor(y / B);
    if (bx !== hx || by !== hy) { hx = bx; hy = by; hg = grids.get(gk(bx, by)); if (!hg) grids.set(gk(bx, by), hg = {d: new Int8Array(B * B).fill(-1), r: new Int8Array(B * B).fill(-1), s: new Int8Array(B * B).fill(-1), sh: new Int8Array(B * B).fill(-1), w: new Int8Array(B * B).fill(-1), col: new Array(B * B)}); }
    gi = (y - by * B) * B + (x - bx * B); return hg;
  }
  const pending = [];                                            // tiles drawn again since the last look: x, y, x, y...
  const isWater = (x, y) => { const g = gndAt(x, y); return !!g && (wet(g) || g === ":"); };
  // Land that only stands in the water: its piece of land is SMALL tiles or fewer (worked out once a piece: each tile of it is told)
  function stands(x, y) {
    if (!gndAt(x, y) || isWater(x, y)) return false;
    let g = G(x, y), s = g.s[gi];
    if (s < 0) {
      const q = [x, y], seen = new Set([(x + 32768) * 65536 + y + 32768]);
      for (let i = 0; i < q.length && q.length <= SMALL * 2; i += 2) for (const [dx, dy] of N4) { const a = q[i] + dx, b = q[i + 1] + dy, k = (a + 32768) * 65536 + b + 32768; if (!seen.has(k) && !isWater(a, b)) { seen.add(k); q.push(a, b); } }
      s = q.length <= SMALL * 2 ? 1 : 0; for (let i = 0; i < q.length; i += 2) { g = G(q[i], q[i + 1]); g.s[gi] = s; }
    }
    return s === 1;
  }
  // Tiles to the nearest bank (land that does not just stand in the water), R at the most
  function bank(x, y, R) {
    const land = (a, b) => !isWater(a, b) && !stands(a, b);
    for (let r = 1; r < R; r++) for (let k = -r; k < r; k++) if (land(x + k, y - r) || land(x + r, y + k) || land(x - k, y + r) || land(x - r, y - k)) return r;
    return R;
  }
  // A water tile's depth by its banks and its kind
  function raw(x, y) {
    let g = G(x, y), d = g.r[gi];
    if (d < 0) {
      const i = gi;
      // (under a bridge: as deep as the water it crosses, beside it: its own kind says nothing, and its bed was a paler square under the deck)
      let own = DEPTH_OF[gndAt(x, y)] || Math.max(1, ...N4.map(([dx, dy]) => DEPTH_OF[gndAt(x + dx, y + dy)] || 0));
      if (own > 2 && bank(x, y, FAR) < FAR) own = 2;
      d = Math.max(bank(x, y, REACH), own); g.r[i] = d;
    }
    return d;
  }
  // ...smoothed: its bed's depth
  function work(x, y) {
    let d = raw(x, y);
    if (bank(x, y, REACH) > 1) {                                // (not the rim: it is the bank's)
      const n = [0, 0, 0, 0, 0]; let other = 0;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if ((dx || dy) && isWater(x + dx, y + dy)) { const r = raw(x + dx, y + dy); n[r]++; if (r !== d) other++; }
      if (other >= 6) d = n.indexOf(Math.max(...n));
      // (the deep: only where four tiles of it meet, a square of two by two. What is left of it between a shelf and a point of land, a tile here and one there, is the basin)
      const block = (v) => [[0, 0], [-1, 0], [0, -1], [-1, -1]].some(([ox, oy]) => [[0, 0], [1, 0], [0, 1], [1, 1]].every(([dx, dy]) => isWater(x + ox + dx, y + oy + dy) && raw(x + ox + dx, y + oy + dy) >= v));
      while (d > 2 && !block(d)) d--;
    }
    return d;
  }
  // A water tile's column under its face: its bed (kept until the land near it changes)
  function bed(x, y) {
    let g = G(x, y), i = gi, c = g.col[i];
    if (!c || g.d[i] < 0) { const d = work(x, y); g = G(x, y); g.d[i] = d; g.col[i] = c = [topAt(x, y) - d]; }
    return c;
  }
  const depth = (x, y) => (cfg.clear && isWater(x, y) ? topAt(x, y) - bed(x, y)[0] : 0);
  function column(x, y) {                                       // (asked for every tile and its neighbours as a chunk's faces are made: is it water, kept)
    if (!cfg.clear) return colAt(x, y);
    const g = G(x, y); let w = g.w[gi]; if (w < 0) w = g.w[gi] = isWater(x, y) ? 1 : 0;
    return w ? bed(x, y) : colAt(x, y);
  }
  // The bed's paint: water.js's bottom of that depth
  function paintBed(x, y, z, px, at, stride) {
    if (!pad) { const c = document.createElement("canvas"); c.width = c.height = 16; pad = c.getContext("2d", {willReadFrequently: true}); }
    const d = topAt(x, y) - z; G(x, y).sh[gi] = d;
    bedTile(pad, x, y, Math.max(1, Math.min(4, d)), 0, 0, () => 0, () => false);
    const img = pad.getImageData(0, 0, 16, 16).data, data = new Uint32Array(img.buffer), hd = hash(x, y, 41);
    // what floats on it (tiles.js: shore water's pads, reeds and rocks) shades the bed: its own shape, a px east, baked
    // (the bed is drawn a level's px down the picture for each level it lies deep: so is the shade)
    if (gndAt(x, y) === "~" && hd < .09 && (hd < .015 || [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => isLand(gndAt(x + dx, y + dy))))) {
      const on = floats ? floats[Math.floor(hash(x, y, 42) * 7)] : null;      // (read once, view: a block of land is made drawing on no canvas)
      if (on) for (let j = 0; j < 16; j++) for (let i = 0; i < 15; i++) if (on[j * 16 + i]) { const q = (j * 16 + i + 1) * 4; img[q] *= .74; img[q + 1] *= .8; img[q + 2] *= .86; }
    }
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) px[at + j * stride + i] = data[j * 16 + i] | 0xff000000;
  }
  // A tile was drawn again: the beds within reach of it may have changed
  const changed = (x, y) => { if (cfg.clear) pending.push(x, y); };
  // ...looked at, before the land is made. What changed, a box a chunk (a block of land coming is B x B tiles drawn: one
  // box), and round it: the pieces of land within SMALL (s), the depths within LOOK (r, d) are forgotten; a bed in that
  // ring that was painted is worked out again, and if it is not as it was painted it is made again, with the tiles whose
  // faces are made from it (the bank north of it down to it; the faces south, west and east of it, which know its depth).
  // Those it has no time for this frame (MS) wait for the next.
  const MS = 2, AGAIN = [[0, 0], [0, -1], [0, 1], [0, 2], [-1, 0], [1, 0], [-1, 1], [1, 1], [-1, -1], [1, -1]], check = [];
  function forget(x0, y0, x1, y1, R, what) {
    for (let y = y0 - R; y <= y1 + R; y++) for (let x = x0 - R; x <= x1 + R;) {
      const bx = Math.floor(x / B), g = grids.get(gk(bx, Math.floor(y / B))), end = Math.min(x1 + R, bx * B + B - 1);
      if (g) { const row = (y - Math.floor(y / B) * B) * B - bx * B;
        for (let i = x; i <= end; i++) { const k = row + i; if (what === "s") g.s[k] = -1; else { g.r[k] = -1; g.w[k] = -1; if (g.d[k] >= 0) { g.d[k] = -1; if (g.sh[k] >= 0) check.push(i, y); } } } }
      x = end + 1;
    }
  }
  function flush(touch) {
    if (pending.length) {
      const box = new Map();                                    // (the changed tiles, a box a chunk)
      for (let i = 0; i < pending.length; i += 2) { const x = pending[i], y = pending[i + 1], k = gk(Math.floor(x / B), Math.floor(y / B)), b = box.get(k);
        if (!b) box.set(k, [x, y, x, y]); else { if (x < b[0]) b[0] = x; if (y < b[1]) b[1] = y; if (x > b[2]) b[2] = x; if (y > b[3]) b[3] = y; } }
      pending.length = 0;
      for (const [x0, y0, x1, y1] of box.values()) { forget(x0, y0, x1, y1, SMALL, "s"); forget(x0, y0, x1, y1, LOOK, "d"); }
      if (grids.size > 400) for (const k of [...grids.keys()]) { const bx = Math.round(k / 4194304), by = k - bx * 4194304; if (!blocks.has(bkey(bx, by))) grids.delete(k); }      // (chunks gone from the world kept: let go)
      hx = NaN;
    }
    const t0 = performance.now(), again = new Set();
    while (check.length && performance.now() - t0 < MS) {
      const y = check.pop(), x = check.pop(), g = G(x, y), i = gi, was = g.sh[i];
      if (was < 0) continue;
      if (isWater(x, y) && depth(x, y) === was) continue;
      if (!isWater(x, y)) G(x, y).sh[i] = -1;
      for (const [ax, ay] of AGAIN) again.add((x + ax + 32768) * 65536 + y + ay + 32768);
    }
    for (const k of again) touch(Math.floor(k / 65536) - 32768, (k % 65536) - 32768);
  }
  // The setting, each frame: turned on or off, all of the land's faces and paint are made again. -> the engine's view.wlook
  function view(engine, t) {
    const on = !!opt("clearwater");
    if (on !== cfg.clear) { cfg.clear = on; grids.clear(); hx = NaN; pending.length = 0; check.length = 0; engine.forget(() => false); }
    if (!on) return null;
    if (!floats && IMG.water_objects && IMG.water_objects.complete && IMG.water_objects.naturalWidth) {
      const c = document.createElement("canvas"); c.width = 16 * 12; c.height = 16; const g = c.getContext("2d", {willReadFrequently: true}); g.drawImage(IMG.water_objects, 0, 0, 16 * 12, 16, 0, 0, 16 * 12, 16);
      const d = g.getImageData(0, 0, 16 * 12, 16).data; floats = [8, 9, 10, 11, 6, 7, 0].map((n) => Uint8Array.from({length: 256}, (_, k) => (d[((k >> 4) * 16 * 12 + n * 16 + (k & 15)) * 4 + 3] > 127 ? 1 : 0)));
    }
    if (!tint) { const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)), deepest = WATER.tint[4], sand = hex(WATER.sand[4]);
      tint = new Float32Array([...TINT.map(([r, g, b, a]) => [r / 255, g / 255, b / 255, a]),
        [...deepest.slice(0, 3).map((v, i) => (v * deepest[3] + sand[i] * (1 - deepest[3])) / 255), 1], [...hex(WATER.sand[0]).map((v) => v / 255), BAND],
        ...WATER.sand.map((h) => [...hex(h).map((v) => v / 255), 1])].flat()); }
    const l = lightAt((((clock.phase || 0) % 1) + 1) % 1), night = Math.max(0, Math.min(1, (1 - (.3 * l[0] + .59 * l[1] + .11 * l[2]) / 255) / .36));
    return {t, tint, bend: opt("shimmer") ? 1.4 : 0, light: opt("shimmer") ? 1 : 0, far: [5, 16, .8], night, dark: [.38, .58, .54], foam: .55, foamAt: 1, shade: [.7, .8, .92], shadow: .16};
  }
  // A swimmer's body under the surface (swim.js): its px of the sheet, tinted as the water over it is and fainter the deeper the water
  function under(sheet, a, b, w, h, x, y, z, tx, ty) {
    const d = Math.max(1, Math.min(4, depth(tx, ty))), [r, g, bl, al] = tint ? tint.subarray(d * 4, d * 4 + 4) : [.5, .8, .8, .3];
    if (!legs) { const c = document.createElement("canvas"); c.width = 48; c.height = 16; legs = c.getContext("2d"); }
    legs.globalCompositeOperation = "source-over"; legs.clearRect(0, 0, 48, 16); legs.drawImage(sheet, a, b, w, h, 0, 0, w, h);
    legs.globalCompositeOperation = "source-atop"; legs.fillStyle = `rgba(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(bl * 255)},${Math.min(.85, al + .25)})`; legs.fillRect(0, 0, w, h);
    ctx.globalAlpha = Math.max(.25, .8 - .18 * d); ctx.drawImage(legs.canvas, 0, 0, w, h, x, y, w * z, h * z); ctx.globalAlpha = 1;
  }
  return {cfg, column, paintBed, changed, flush, view, under, depth, get on() { return cfg.clear; }};
})();
