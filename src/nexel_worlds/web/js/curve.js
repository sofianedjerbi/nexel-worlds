// The curved world, the game's side ("a voxel world viewed top-down in Animal Crossing style"): the ground bends
// away to a horizon in the upper part of the screen, with a sky over it. Where you stand nothing changes: under the
// line where the bend starts the screen is exactly the flat one, and aiming is unchanged. The maths is the engine's
// (vox_curve.js: one function for the GPU and for this file); here are the numbers, where the eye is, the `sy`
// everything that stands is placed with (render.js), and the sky's colours by the hour (vox_sky.js draws it).
// The settings' "Curved world" (options.js: curve), ONE parameter of the HD look's view (hd.js viewOf): on, the land
// bends away to the horizon the view distance puts, a sky over it; off, it is flat, the land to the picture's top,
// no sky. (?curve=0 or 1 in the page's address, or Curve.force "off" / "on": that for this page whatever the setting.)
//
// x is unchanged, and a height is as tall far off as near. Every point is pushed down the screen by the square
// of how far it is past the line where the roll starts (vox_curve.js), so level ground goes up to a horizon and
// comes down again behind it, and whatever rises to the north has its horizon too. What stands is never drawn
// smaller (a pixel of a sprite is a pixel of the land): far rows are closer together, what stands on them stands
// closer, and where its row is squeezed to under half a tile it starts down into the ground it stands on, cut at
// its own ground line: it leaves the picture as a thing behind a hill does, before it lies over what is in front.

// from, horizon: where the roll starts and where level ground's horizon is, as shares of the screen's height from
// its bottom (the sky's line before the HD look has its own, hd_eye.js). lean: the share of a height over you that counts as distance (vox_curve.js:
// what keeps a horizon on a mountain's side). foot: how far down its tile what stands has its feet (13 art px of
// 16): that spot of the tile is where it is put. fade, depth: a row squeezed under `fade` of a tile takes what
// stands on it down, `depth` tiles by the time the row is on the horizon. floor: how squeezed a row may get: a tile's
// row is never drawn under that share of its 16 px, and what is further is behind the horizon ("never scale pixel
// art": the land near the horizon is whole px of its paint, and readable: vox_curve.js). tuft, short: what goes down
// behind the roll is cut along the grass of the ground before it, tufts up to `tuft` art px tall, and is not drawn
// at all once under `short` art px of it are left.
const CURVE = {from: .55, horizon: .86, floor: .5, lean: .3, foot: 13 / 16, fade: .5, depth: 1.5, tuft: 2, short: 6};
const CURVE_SKY = {      // each: by day, at dusk and dawn, at night (vox_sky.js: sun, moon and stars)
  top: [[.28, .52, .9], [.2, .22, .52], [.03, .04, .14]], mid: [[.48, .7, .95], [.56, .42, .68], [.06, .08, .24]], low: [[.8, .9, .98], [.96, .66, .52], [.14, .17, .38]],
  glow: [[.8, .9, .98], [.96, .66, .52], [.26, .28, .52]], cloud: [[1, 1, 1], [.98, .82, .76], [.18, .2, .38]], rim: [[1, 1, 1], [1, .9, .7], [.5, .54, .78]],
  shade: [[.82, .88, .96], [.7, .52, .64], [.12, .14, .3]], far: [[.5, .62, .78], [.52, .36, .5], [.1, .13, .3]], near: [[.4, .6, .5], [.5, .36, .34], [.08, .13, .22]],
  sun: [1, .95, .7], moon: [.92, .94, 1],
};
const Curve = (() => {
  const forced = (v) => (v === null || v === undefined ? null : !(v === "off" || v === "0" || v === false || v === 0));
  let force = forced(new URLSearchParams(location.search).get("curve"));
  const bent = () => (force === null ? !!opt("curve") : force);   // (the setting, or the page's own)
  let c = null, audit = false, zs = 1;
  // Once a frame, before anything is placed (render.js): the curve as it is now. (zs: a zoom's glide has just ended:
  // the roll as the magnified picture had it, let back to its own place: zoom.js)
  function frame(ox, oy, S, now) {
    const m = bent() ? CURVE : null;
    if (!m || (typeof TitleScene !== "undefined" && TitleScene.on && !HdLook.live)) { c = null; return; }      // (the first screen's island in the classic look is drawn on the very px of its still picture: flat; in the HD look it has its sky)
    const z = zoom, snap = (v) => Math.round(v / z) * z, mid = H / 2;
    if (!ZOOM.busy) zs = Math.abs(zs - 1) < .004 ? 1 : zs + (1 - zs) * .14;
    const line = snap(mid + (H * (1 - m.horizon) - mid) * zs), y0 = snap(mid + (H * (1 - m.from) - mid) * zs), q = m.floor || 0;
    c = {y0, yh: y0 - (y0 - line) / (1 - q * q), ref: (cam.lift || 0) * z, lean: CURVE.lean, floor: q, line};      // (line: where level land meets the sky; yh: the top of its parabola, vox_curve.js)
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
    const k = flat ? null : c, A = CURVE.foot, a = S / P, row = (y, lift = 0) => VoxCurve.snap(k, oy + y * S, lift, oy, a);      // (bent: on a whole px of the paint, as the land is drawn)
    // (lost: px what stands on row y is taken down: its row squeezed under CURVE.fade of a tile, the more the nearer its horizon)
    const lost = (y) => { if (!k) return 0; const q = 1 - (k.y0 - (oy + (y + A) * S - k.ref)) / (2 * (k.y0 - k.yh)); return q >= CURVE.fade ? 0 : Math.min(1, 1 - Math.max(k.floor, q) / CURVE.fade) ** 2 * CURVE.depth * S; };
    const at = (y, lift) => { const flat = oy + y * S - lift; if (!k) return flat; const v = VoxCurve.y(k, oy + (y + A) * S, lift) - A * S; return Math.abs(v - flat) < 1e-9 ? flat : oy + Math.round((v + lost(y) - oy) / a) * a; };
    const f = (y, x) => at(y, x === undefined ? 0 : liftOf({x, y}));
    f.base = oy; f.bent = !!k; f.row = row; f.up = at; f.lost = lost;      // (lost: sunland.js cuts a shadow as its thing is cut)
    const top = k ? k.line : 0, edge = k ? VoxCurve.edge(k) : 0;
    f.inv = (py) => ((k && py < top ? edge - (top - py) : VoxCurve.inv(k, py)) - oy) / S;
    f.out = (u) => { const F = oy + u * S; return k && F < edge ? top - (edge - F) : VoxCurve.warp(k, F); };
    f.tall = (y, lift = 0) => (k ? row(y + 1, lift) - row(y, lift) : S);
    f.far = (y, lift = 0) => VoxCurve.past(k, oy + (y + A) * S, lift) > 0;
    f.cut = (lift) => (k ? VoxCurve.line(k, lift) : -1e4);
    // where what stands on row y (its ground `lift` px up) is cut: its own ground line once it is going down, the horizon of its ground past it (and a tuft: `mask` cuts along grass, so the land's edge is its own px there too); nothing: whole
    f.clip = (y, lift = 0) => { if (!k) return undefined; const p = f.far(y, lift), l = lost(y); return p || l > 0 ? Math.min(p ? f.cut(lift) + CURVE.tuft * a : 1e9, Math.round(VoxCurve.y(k, oy + (y + A) * S, lift)) + 3 * zoom) : undefined; };
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
    const tint = Light.now().lit.map((v) => v / 255);
    const col = (q) => q.map((v, i) => Math.min(1, v / tint[i])), pick = (q) => col(q[0].map((v, i) => { const d = v + (q[1][i] - v) * dusk; return d + (q[2][i] - d) * night; }));
    const line = c.line, band = Math.max(8, line / zoom);
    return {line, t, shift: ((myId !== null && ents.get("agent" + myId)) || cam).x * P * .12,   // (where you are, not the camera: on a ladder and with the build cursor the clouds slid sideways with it)
      ...Object.fromEntries(["top", "mid", "low", "glow", "cloud", "rim", "shade", "far", "near"].map((k) => [k, pick(CURVE_SKY[k])])),
      dusk: dusk * (1 - night), day, moon: ((Math.floor((clock.tick || 0) / RULES.day_ticks) % 8) + .5) / 8,   // (the moon's phase from the day's count, 8 days a round)
      orb: col(day ? CURVE_SKY.sun : CURVE_SKY.moon), at: [.88 - .76 * way, -.14 + .92 * Math.sin(way * Math.PI), Math.min(day ? 5.5 : 4.5, band * .2)], stars: night, audit};
  }
  return {frame, sy, sky, get on() { return !!c; }, get bent() { return bent(); }, get c() { return c; }, get line() { return c ? c.line : 0; },
    y: (f, h = 0) => VoxCurve.y(c, f, h), inv: (s) => VoxCurve.inv(c, s),      // (a row and a height on the screen; the place of the flat picture drawn at s)
    // how much further north than the flat screen the rolled one shows before its horizon: px (Far: a little; in a
    // pit the land over you is nearer its horizon still: nothing more)
    over: () => (c ? Math.max(0, Math.ceil(-VoxCurve.edge(c))) + 2 : 0),
    rezoom: (k) => { zs *= k; },                             // (the picture was magnified k times and is now drawn at that size: zoom.js)
    set audit(v) { audit = v; }, set force(v) { force = forced(v); }};
})();
