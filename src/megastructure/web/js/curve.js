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
// x is as it was. Land higher than you stands up from its bent row and leans back with distance (a far hill
// stands over the line, half as tall as beside you); land lower than you is bent where the flat picture has it (from a
// mountain you look down on the plain, up to the same horizon). What stands is never drawn smaller (a pixel of a
// sprite is a pixel of the land): far rows are closer together, and what stands on them stands closer. Past the
// horizon the ground goes down behind it, and what stands there goes down with it, cut at the horizon line of the
// ground it stands on.

// from, horizon: where the bend starts and where the horizon is, as shares of the screen's height from its bottom;
// g: the stretch (vox_curve.js): the bent part holds (horizon - from) * pi / 2 * (1 + g) of the screen's height of
// flat ground. Near: the ground the flat screen showed and a twenty-seventh more. Far: about four fifths of a
// screen more to the north. sink: px the ground comes down for each px past the horizon (gently for the first
// tile: vox_curve.js soft); foot: how far down its tile what stands has its feet (13 art px of 16: a body's, a
// trunk's): that spot of the tile is where it is put, so far off, where a tile is a few px tall, its feet are
// still on its own tile and the rest of it stands up from there. lean: the share of a height over you that is
// squeezed with the rows (vox_curve.js): a far hill is half as tall over the horizon as beside you.
const CURVE = {near: {from: .55, horizon: .86, g: 0}, far: {from: .55, horizon: .86, g: 1.2}, sink: 2, lean: .5, foot: 13 / 16};
const CURVE_SKY = {      // each: by day, at dusk and dawn, at night
  top: [[.33, .6, .93], [.27, .3, .58], [.05, .07, .19]], low: [[.78, .9, .98], [.99, .68, .42], [.17, .21, .44]],
  cloud: [[1, 1, 1], [1, .82, .72], [.3, .34, .56]], far: [[.5, .62, .78], [.52, .36, .5], [.1, .13, .3]], near: [[.4, .6, .5], [.5, .36, .34], [.08, .13, .22]],
  sun: [1, .95, .7], moon: [.92, .94, 1],
};
const Curve = (() => {
  let force = {0: "off", near: "near", far: "far"}[new URLSearchParams(location.search).get("curve")] ?? null;
  let c = null, line = 0, lineAt = -1e9, audit = false;
  // Once a frame, before anything is placed (render.js): the curve as it is now, and the sky's horizon. The sky
  // meets the land where the lowest land on the horizon is drawn (from a mountain, the plain's far edge is well
  // under the bend's own line; in a valley it is over it), gliding there: no band of nothing between the two.
  function frame(ox, oy, S, now) {
    const m = CURVE[force === null ? opt("curve") : force];
    if (!m || (typeof TitleScene !== "undefined" && TitleScene.on)) { c = null; return; }      // (the first screen's island is drawn on the very px of its still picture: flat)
    const z = zoom, snap = (v) => Math.round(v / z) * z;
    c = {y0: snap(H * (1 - m.from)), yh: snap(H * (1 - m.horizon)), ref: (cam.lift || 0) * z, sink: CURVE.sink, soft: S, g: m.g, lean: CURVE.lean, line: 0};      // (line: where the land meets the sky, below)
    const row = Math.floor((VoxCurve.edge(c) + c.ref - oy) / S);      // (the row the horizon runs through, at your height: the last of the land that is seen)
    const lvs = [];
    if (away.a < 1) for (let x = Math.floor(-ox / S); x <= Math.floor((W - ox) / S); x++) { const g = gndAt(x, row); if (g) lvs.push(wet(g) ? 0 : topAt(x, row)); }
    // (the lowest that is seven tiles wide: a pit or a gully on the horizon is not where the land ends. Land lower
    // than you ends on the horizon line itself; higher, that much over it)
    let low = null;
    for (let i = 0; i < lvs.length; i++) { let top = -1e9; for (let j = Math.max(0, i - 3); j <= Math.min(lvs.length - 1, i + 3); j++) top = Math.max(top, lvs[j]); if (low === null || top < low) low = top; }
    c.line = low === null ? c.yh : VoxCurve.line(c, shOf(low) * z);
    const want = c.line, dt = Math.min(.1, (now - lineAt) / 1000);
    line = now - lineAt > 500 || Math.abs(want - line) > H ? want : line + (want - line) * (1 - Math.exp(-dt / .3));
    lineAt = now;
  }
  // render.js's sy: where what is on row y of the world is drawn (the top of the tile-high square it is drawn in,
  // as ever: flat, the row's own top), and with x, lifted by the ground there. In the bend that square is put by
  // its foot (CURVE.foot), on a whole px (what stands is drawn on whole px). Also:
  //   up(y, lift): the same for what is drawn `lift` px up (a floor, a step, a body's own height): where a draw
  //     site wrote sy(y) - lift (a height is part of where a thing is, in the bend: curve.js's first lines)
  //   row(y, lift): where the row itself is (the ground's line: a tile's top edge, the foot of the one north of it)
  //   tall(y, lift): how tall the tile's row is drawn; far(y, lift): is what stands there past the horizon;
  //   cut(lift): the horizon of ground drawn `lift` px up; base: the flat picture's origin (what is locked to the
  //   land's own pixels counts from it); inv(py) and out(u): a place on the screen as a row and back (the selector
  //   keeps its box in rows: over the horizon line, where no row is drawn, they go on a tile's side a row, so a
  //   tree that stands up into the sky has its whole box)
  // (flat: as with no curve, whatever the curve is: sun.js lays shadows on the flat picture, and the land bends them)
  function sy(oy, S, flat = false) {
    const k = flat ? null : c, A = CURVE.foot, row = (y, lift = 0) => { const flat = oy + y * S - lift, v = VoxCurve.y(k, oy + y * S, lift); return Math.abs(v - flat) < 1e-9 ? flat : Math.round(v); };
    const at = (y, lift) => { const flat = oy + y * S - lift; if (!k) return flat; const v = VoxCurve.y(k, oy + (y + A) * S, lift) - A * S; return Math.abs(v - flat) < 1e-9 ? flat : Math.round(v); };
    const f = (y, x) => at(y, x === undefined ? 0 : liftOf({x, y}));
    f.base = oy; f.bent = !!k; f.row = row; f.up = at;
    const top = k ? k.yh : 0, edge = k ? VoxCurve.edge(k) : 0;
    f.inv = (py) => ((k && py < top ? edge - (top - py) : VoxCurve.inv(k, py)) - oy) / S;
    f.out = (u) => { const F = oy + u * S; return k && F < edge ? top - (edge - F) : VoxCurve.warp(k, F); };
    f.tall = (y, lift = 0) => (k ? row(y + 1, lift) - row(y, lift) : S);
    f.far = (y, lift = 0) => VoxCurve.past(k, oy + (y + A) * S, lift) > 0;
    f.cut = (lift) => (k ? VoxCurve.line(k, lift) : -1e4);
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
    const band = Math.max(8, line / zoom);
    return {line, t, shift: cam.x * P * .12, top: pick(CURVE_SKY.top), low: pick(CURVE_SKY.low), cloud: pick(CURVE_SKY.cloud), far: pick(CURVE_SKY.far), near: pick(CURVE_SKY.near),
      orb: col(day ? CURVE_SKY.sun : CURVE_SKY.moon), at: [.88 - .76 * way, -.14 + .92 * Math.sin(way * Math.PI), Math.min(day ? 5.5 : 4.5, band * .2)], stars: night, audit};
  }
  return {frame, sy, sky, get on() { return !!c; }, get c() { return c; }, get line() { return line; },
    y: (f, h = 0) => VoxCurve.y(c, f, h), inv: (s) => VoxCurve.inv(c, s),      // (a row and a height on the screen; the place of the flat picture drawn at s)
    // how much further north than the flat screen the bent one shows: px (Near: a twenty-seventh of the screen; Far:
    // four fifths of it; and in a pit as far again as you are deep: the ground up there is judged from your own height)
    over: () => (c ? Math.ceil(-VoxCurve.edge(c) + Math.max(0, -c.ref)) + 2 : 0),
    set audit(v) { audit = v; }, set force(v) { force = v; }};
})();
