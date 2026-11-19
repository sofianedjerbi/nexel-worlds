// The curved world, the game's side ("a voxel world viewed top-down in Animal Crossing style"): the ground bends
// away to a horizon in the upper part of the screen, with a sky over it. Where you stand nothing changes: under the
// line where the bend starts the screen is exactly the flat one, and aiming is as it was. The maths is the engine's
// (vox_curve.js: one function for the GPU and for this file); here are the numbers, where the eye is, the `sy`
// everything that stands is placed with (render.js), and the sky's colours by the hour (vox_sky.js draws it).
// The settings' "Curved world" (options.js: curve): Off, the flat picture, as ever; Near, a bend that shows the
// ground the flat screen showed; Far, a roll-off that shows more land, further away. (?curve=0, near or far in the
// page's address, or Curve.force "off", "near", "far": that for this page whatever the setting, which is left as
// it is: the browser tests are written on the flat picture.)
//
// x is as it was, and a height is as tall far off as near. Every point is pushed down the screen by the square
// of how far it is past the line where the roll starts (vox_curve.js), so level ground goes up to a horizon and
// comes down again behind it, and whatever rises to the north has its horizon too. What stands is never drawn
// smaller (a pixel of a sprite is a pixel of the land): far rows are closer together, what stands on them stands
// closer, and where its row is squeezed to under half a tile it starts down into the ground it stands on, cut at
// its own ground line: it leaves the picture as a thing behind a hill does, before it lies over what is in front.

// from, horizon: where the roll starts and where level ground's horizon is, as shares of the screen's height from
// its bottom. Twice their distance of flat ground lies before the horizon: Near, a little less than the flat screen
// showed north of you; Far, a little more. lean: the share of a height over you that counts as distance (vox_curve.js:
// what keeps a horizon on a mountain's side). foot: how far down its tile what stands has its feet (13 art px of
// 16): that spot of the tile is where it is put. fade, depth: a row squeezed under `fade` of a tile takes what
// stands on it down, `depth` tiles by the time the row is on the horizon.
const CURVE = {near: {from: .55, horizon: .74}, far: {from: .55, horizon: .8}, lean: .6, foot: 13 / 16, fade: .5, depth: 1.5};
const CURVE_SKY = {      // each: by day, at dusk and dawn, at night
  top: [[.33, .6, .93], [.27, .3, .58], [.05, .07, .19]], low: [[.78, .9, .98], [.99, .68, .42], [.17, .21, .44]],
  cloud: [[1, 1, 1], [1, .82, .72], [.3, .34, .56]], far: [[.5, .62, .78], [.52, .36, .5], [.1, .13, .3]], near: [[.4, .6, .5], [.5, .36, .34], [.08, .13, .22]],
  sun: [1, .95, .7], moon: [.92, .94, 1],
};
const Curve = (() => {
  let force = {0: "off", near: "near", far: "far"}[new URLSearchParams(location.search).get("curve")] ?? null;
  let c = null, audit = false, zs = 1;
  // Once a frame, before anything is placed (render.js): the curve as it is now. (zs: a zoom's glide has just ended:
  // the roll as the magnified picture had it, let back to its own place: zoom.js)
  function frame(ox, oy, S, now) {
    const m = CURVE[force === null ? opt("curve") : force];
    if (!m || (typeof TitleScene !== "undefined" && TitleScene.on)) { c = null; return; }      // (the first screen's island is drawn on the very px of its still picture: flat)
    const z = zoom, snap = (v) => Math.round(v / z) * z, mid = H / 2;
    if (!ZOOM.busy) zs = Math.abs(zs - 1) < .004 ? 1 : zs + (1 - zs) * .14;
    const yh = snap(mid + (H * (1 - m.horizon) - mid) * zs);
    c = {y0: snap(mid + (H * (1 - m.from) - mid) * zs), yh, ref: (cam.lift || 0) * z, lean: CURVE.lean, line: yh};      // (line: where level land meets the sky)
  }
  // render.js's sy: where what is on row y of the world is drawn (the top of the tile-high square it is drawn in,
  // as ever: flat, the row's own top), and with x, lifted by the ground there. In the bend that square is put by
  // its foot (CURVE.foot), on a whole px (what stands is drawn on whole px). Also:
  //   up(y, lift): the same for what is drawn `lift` px up (a floor, a step, a body's own height): where a draw
  //     site wrote sy(y) - lift (a height is part of where a thing is, in the bend: curve.js's first lines)
  //   row(y, lift): where the row itself is (the ground's line: a tile's top edge, the foot of the one north of it)
  //   tall(y, lift): how tall the tile's row is drawn; far(y, lift): is what stands there past its horizon;
  //   clip(y, lift), gone(y, lift): below;
  //   cut(lift): the horizon of ground drawn `lift` px up; base: the flat picture's origin (what is locked to the
  //   land's own pixels counts from it); inv(py) and out(u): a place on the screen as a row and back (the selector
  //   keeps its box in rows: over the horizon line, where no row is drawn, they go on a tile's side a row, so a
  //   tree that stands up into the sky has its whole box)
  // (flat: as with no curve, whatever the curve is: sun.js lays shadows on the flat picture, and the land bends them)
  function sy(oy, S, flat = false) {
    const k = flat ? null : c, A = CURVE.foot, row = (y, lift = 0) => { const flat = oy + y * S - lift, v = VoxCurve.y(k, oy + y * S, lift); return Math.abs(v - flat) < 1e-9 ? flat : Math.round(v); };
    // (lost: px what stands on row y is taken down: its row squeezed under CURVE.fade of a tile, the more the nearer its horizon)
    const lost = (y) => { if (!k) return 0; const d = k.y0 - (oy + (y + A) * S - k.ref), q = 1 - d / (2 * (k.y0 - k.yh)); return q >= CURVE.fade ? 0 : Math.min(1, 1 - q / CURVE.fade) ** 2 * CURVE.depth * S; };
    const at = (y, lift) => { const flat = oy + y * S - lift; if (!k) return flat; const v = VoxCurve.y(k, oy + (y + A) * S, lift) - A * S; return Math.abs(v - flat) < 1e-9 ? flat : Math.round(v + lost(y)); };
    const f = (y, x) => at(y, x === undefined ? 0 : liftOf({x, y}));
    f.base = oy; f.bent = !!k; f.row = row; f.up = at;
    const top = k ? k.yh : 0, edge = k ? VoxCurve.edge(k) : 0;
    f.inv = (py) => ((k && py < top ? edge - (top - py) : VoxCurve.inv(k, py)) - oy) / S;
    f.out = (u) => { const F = oy + u * S; return k && F < edge ? top - (edge - F) : VoxCurve.warp(k, F); };
    f.tall = (y, lift = 0) => (k ? row(y + 1, lift) - row(y, lift) : S);
    f.far = (y, lift = 0) => VoxCurve.past(k, oy + (y + A) * S, lift) > 0;
    f.cut = (lift) => (k ? VoxCurve.line(k, lift) : -1e4);
    // where what stands on row y (its ground `lift` px up) is cut: its own ground line once it is going down, the horizon of its ground past it; nothing: whole
    f.clip = (y, lift = 0) => { if (!k) return undefined; const p = f.far(y, lift), l = lost(y); return p || l > 0 ? Math.min(p ? f.cut(lift) : 1e9, Math.round(VoxCurve.y(k, oy + (y + A) * S, lift)) + 3 * zoom) : undefined; };
    f.gone = (y, lift = 0) => !!k && (f.far(y, lift) || lost(y) > S * .75);      // ...and so far down that it has no shadow, no name
    return f;
  }
  // The sky at this hour (clock.phase: 0 sunrise, the night its last quarter), for the engine. The night's light is
  // laid over the whole picture afterwards (daylight.js drawNight multiplies it): the colours are given that much
  // brighter, so that the sky is what is written in CURVE_SKY once the night is on it.
  function sky(t) {
    const p = (((clock.phase || 0) % 1) + 1) % 1, day = p < .75, way = day ? p / .75 : (p - .75) / .25;
    const night = p < .5 ? 1 - smooth((p + .035) / .07) : Math.min(smooth((p - .72) / .08), 1 - smooth((p - .965) / .07));
    const dusk = p < .3 ? 1 - smooth((p - .035) / .125) : smooth((p - .56) / .14);
    const lift = opt("night") / 100 * .6, tint = lightAt(p).map((v) => (v + (255 - v) * lift) / 255);
    const col = (q) => q.map((v, i) => Math.min(1, v / tint[i])), pick = (q) => col(q[0].map((v, i) => { const d = v + (q[1][i] - v) * dusk; return d + (q[2][i] - d) * night; }));
    const line = c.yh, band = Math.max(8, line / zoom);
    return {line, t, shift: cam.x * P * .12, top: pick(CURVE_SKY.top), low: pick(CURVE_SKY.low), cloud: pick(CURVE_SKY.cloud), far: pick(CURVE_SKY.far), near: pick(CURVE_SKY.near),
      orb: col(day ? CURVE_SKY.sun : CURVE_SKY.moon), at: [.88 - .76 * way, -.14 + .92 * Math.sin(way * Math.PI), Math.min(day ? 5.5 : 4.5, band * .2)], stars: night, audit};
  }
  return {frame, sy, sky, get on() { return !!c; }, get c() { return c; }, get line() { return c ? c.yh : 0; },
    y: (f, h = 0) => VoxCurve.y(c, f, h), inv: (s) => VoxCurve.inv(c, s),      // (a row and a height on the screen; the place of the flat picture drawn at s)
    // how much further north than the flat screen the rolled one shows before its horizon: px (Far: a little; in a
    // pit the land over you is nearer its horizon still: nothing more)
    over: () => (c ? Math.max(0, Math.ceil(-VoxCurve.edge(c))) + 2 : 0),
    rezoom: (k) => { zs *= k; },                             // (the picture was magnified k times and is now drawn at that size: zoom.js)
    set audit(v) { audit = v; }, set force(v) { force = v; }};
})();
