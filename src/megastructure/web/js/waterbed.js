// Clear water (the settings' Picture page, on by default): the water is seen through, to its bed. The engine draws it
// (vox_water.js); this file says what is under the water, since the world does not: a water tile is a ground kind at
// its tile's level, and its kind says how deep it is (vocab.js DEPTH_OF: 1 to 4 layers), no more.
// The bed: that many levels under the face, and never less than the tiles to the nearest land, 2 at the most (a
// pond, a river go down a step from their banks; only the sea's own kinds go deeper). It is for the eye only: what
// you aim at, swim on and build on is the water's face, as ever (cells.js knows no bed).
// Its paint is water.js's own bottom (sand, ridges, pebbles, weed), its sides the earth of the land's walls, the
// tint over it water.js's own, by depth; water.js then draws only what is on the face (waves, glints).
// A bed depends on the land round it: when a tile changes, the beds within reach of it are looked at again, and
// what changed is made again with what is drawn from it (`changed`, `flush`: voxels.js).
// Off: none of this; the water is water.js's picture on one face, as it was.
const WaterBed = (() => {
  const REACH = 2, cfg = {clear: false, dark: 4};                         // (cfg: the engine's cfg.water)
  let tint = null, beds = new Map(), bedsAt = -1, pad = null, legs = null;
  const shown = new Map(), pending = new Set();                  // the depth each bed was painted with; tiles that changed since the last look
  const isWater = (x, y) => { const g = gndAt(x, y); return !!g && (wet(g) || g === ":"); };
  const key = (x, y) => x + "," + y;
  // A water tile's column under its face: its bed (kept until the land changes)
  function bed(x, y) {
    if (bedsAt !== landVer) { beds.clear(); bedsAt = landVer; }
    let c = beds.get(key(x, y));
    if (!c) {
      let d = REACH;
      for (let r = REACH - 1; r > 0; r--) for (let k = -r; k < r; k++) if (!isWater(x + k, y - r) || !isWater(x + r, y + k) || !isWater(x - k, y + r) || !isWater(x - r, y - k)) d = r;
      beds.set(key(x, y), c = [topAt(x, y) - Math.max(d, DEPTH_OF[gndAt(x, y)] || 1)]);
    }
    return c;
  }
  const depth = (x, y) => (cfg.clear && isWater(x, y) ? topAt(x, y) - bed(x, y)[0] : 0);
  const column = (x, y) => (cfg.clear && isWater(x, y) ? bed(x, y) : colAt(x, y));
  // The bed's paint: water.js's bottom of that depth
  function paintBed(x, y, z, px, at, stride) {
    if (!pad) { const c = document.createElement("canvas"); c.width = c.height = 16; pad = c.getContext("2d", {willReadFrequently: true}); }
    const d = topAt(x, y) - z; shown.set(key(x, y), d);
    bedTile(pad, x, y, Math.max(1, Math.min(4, d)), 0, 0, () => 0, () => false);
    const data = new Uint32Array(pad.getImageData(0, 0, 16, 16).data.buffer);
    for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) px[at + j * stride + i] = data[j * 16 + i] | 0xff000000;
  }
  // A tile was drawn again: the beds within reach of it may have changed
  const changed = (x, y) => { if (cfg.clear) pending.add(key(x, y)); };
  // ...looked at, before the land is made: a bed that is not as it was painted is made again, and with it the tiles
  // whose faces are made from it (the bank north of it down to it; the faces south, west and east of it, which know its depth)
  function flush(touch) {
    if (!pending.size) return;
    const again = new Set();
    for (const k of pending) {
      const [x, y] = k.split(",").map(Number);
      for (let dy = -REACH; dy <= REACH; dy++) for (let dx = -REACH; dx <= REACH; dx++) {
        const nx = x + dx, ny = y + dy, nk = key(nx, ny), was = shown.get(nk);
        if (was === undefined || (isWater(nx, ny) && depth(nx, ny) === was)) continue;
        if (!isWater(nx, ny)) shown.delete(nk);
        for (const [ax, ay] of [[0, 0], [0, -1], [0, 1], [0, 2], [-1, 0], [1, 0], [-1, 1], [1, 1], [-1, -1], [1, -1]]) again.add(key(nx + ax, ny + ay));
      }
    }
    pending.clear();
    for (const k of again) touch(...k.split(",").map(Number));
  }
  // The setting, each frame: turned on or off, all of the land's faces and paint are made again. -> the engine's view.wlook
  function view(engine, t) {
    const on = !!opt("clearwater");
    if (on !== cfg.clear) { cfg.clear = on; shown.clear(); pending.clear(); engine.forget(() => false); }
    if (!on) return null;
    if (!tint) { const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)), deepest = WATER.tint[4], sand = hex(WATER.sand[4]);
      tint = new Float32Array([...WATER.tint.slice(0, 4).map(([r, g, b, a], i) => [r / 255, g / 255, b / 255, a + i * .04]),
        [...deepest.slice(0, 3).map((v, i) => (v * deepest[3] + sand[i] * (1 - deepest[3])) / 255), 1], [...hex(WATER.sand[0]).map((v) => v / 255), 1]].flat()); }
    const l = lightAt((((clock.phase || 0) % 1) + 1) % 1), night = Math.max(0, Math.min(1, (1 - (.3 * l[0] + .59 * l[1] + .11 * l[2]) / 255) / .36));
    return {t, tint, bend: opt("shimmer") ? 1.4 : 0, light: opt("shimmer") ? 1 : 0, far: [5, 16, .8], night, dark: [.46, .58, .62], foam: .55, foamAt: 1, shade: [.7, .8, .92]};
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
