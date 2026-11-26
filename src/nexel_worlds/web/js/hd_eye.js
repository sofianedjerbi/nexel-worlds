// THE EYE of the HD look (hd.js), one source: its PITCH (from the cover alone, one easing), its LEVEL (it follows yours) and its LINES (the sky's, the land's edge, the skyline).
//   HdEye(H) (H: the look's {cam, api, R, SEA_L, eng, making}) -> {pitch(cov, b0, dt) -> levels the eye's line climbs a tile at the pitch it goes to; level(p, L, Lf, dt) -> the eye's level;
//     lines(tx, ty, L, at, w, h, dt): the sky's line and the land's edge for this frame (api.sky, api.line, api.low); camL, tilt (0..1: how far from above), above (it is to look from above), hy (the land's skyline, px)}
const HdEye = (H) => {
  const {cam, api} = H, EASE = .4;
  let camL = null, camV = 0, lastLf = null, pitN = null, stage = 0, tilt = 0, hl = 0, he = 0, hy = 0;
  // THE EYE, from the cover alone, one easing: the surface's pitch (b0) out in the open whatever the land's shape round you; from above (STEEP) while land covers or hides you (cov: back 300 ms
  // after it last did). It tilts over 400 ms, slow at both ends, the window opening with it. (Not four probes: land south over your head row by row (clear), 16 rays "shut in" (steep), the roof, hides:
  // crossing a dip one level deep they tilt the eye to 58 and back within a second, the mountain south of you sliding up the screen and down: doben00, "like the mountain is moving")
  function pitch(cov, b0, dt) {
    stage = cov ? 1 : 0; const base = b0, want = base + (api.steep - base) * stage; tilt = pitN === null ? stage : Math.max(0, Math.min(1, tilt + (stage ? 1 : -1) * Math.min(dt, .034) / EASE)); pitN = base + (api.steep - base) * tilt * tilt * (3 - 2 * tilt); cam.pitch = pitN; cam.base = base; cam.want = want;
    return eyeRise(want);
  }
  // the eye's level follows yours: a step over some 150 ms; a FALL: the eye stays while your body is in the air (the land steady, the body coming down it; at most 9 levels over where you will land), then comes
  // down to you slow at both ends (a spring, critically damped, its exact answer for any frame's length: .4 s for 12 levels. Stepped a frame at a time it runs away when a frame takes over 83 ms: a slow phone). (Over 8 levels too: one frame there, off the gorge's rim, would change more than half the picture at once, your body in the top quarter of it)
  function level(p, L, Lf, dt) {
    { const fl = BodyPlace.of(p).fall, air = fl && fl.air, far = camL !== null && Math.abs(Lf - camL); if (air) camV = 0;
      if (camL === null || far > 40) { camL = Lf; camV = 0; } else if (air) camL = Math.max(Math.min(camL, L + 9), camL - 40 * dt); else if (far > 3 || camV) { const e = camL - Lf, a = camV + 12 * e, q = Math.exp(-12 * dt); camL = Lf + (e + a * dt) * q; camV = (camV - 12 * a * dt) * q; if (Math.abs(Lf - camL) < .07 && Math.abs(camV) < 1) { camL = Lf; camV = 0; } }
      else { const d = lastLf === null || fl ? 0 : Lf - lastLf; if (Math.abs(d) < .5) camL += d; const e = Lf - camL; camL = Math.abs(e) < .01 ? Lf : camL + e * (1 - Math.exp(-dt / .1)); }
      lastLf = Lf; }   // (a step, a hop up or down one: the eye goes with Lf as it goes, frame for frame (the arc moves only the body); only a sudden change of it (a block put under you) is eased. It eased all of it over 100 ms: the eye a third of a level behind you as you landed, the land still sliding 200 ms after, your body bobbing on the screen at every step)   // (Lf: your level between two tiles, on the line between their heights: down a stair the eye goes down a slope, not a step a tile)
    return camL;
  }
  // the game's sky with its horizon where ground at the eye's own level meets it, at the top of its bend (not the classic picture's horizon, higher: a wide empty band
  // between the sky and the land, a third of a phone held upright). Fixed to the eye: its pitch and the screen, nothing of the land (eyeLine). edge: where the land ahead really
  // ends, at or under the line (he, below): the far hills stand on it and the sky goes on down to them (vox_sky.js)
  api.sky = (t) => { const s = Curve.sky(t); return api.on && hl ? Object.assign({}, s, {line: Math.round(hl) * zoom, edge: Math.round(Math.max(hl, he)) * zoom}) : s; };
  let hKey = "", hRaw = 1e9;   // (the skyline is looked for when you change tile, level or tilt, not every frame: 45 points of the land put through the camera, .3 ms of a sprint's frame on a phone)
  function horizon(tx, ty, L) { const hk = [tx, ty, L, cam.pitch.toFixed(1), Math.round(camL * 8), H.eng.stamp, api.builds, H.making, api.bend].join(); let y = hRaw; if (hk !== hKey) { hKey = hk; y = -1e9; for (let dx = -18; dx <= 18; dx += 9) { let m = 1e9; for (let dn = 6; dn <= 22; dn += 2) { const c = Voxels.host.column(tx + dx, ty - dn), a = H.eng.at(tx + dx + .5, ty - dn, c && c.length ? c[c.length - 1] : L); if (a) m = Math.min(m, a[1]); } if (m < 1e8) y = Math.max(y, m); } if (y < -1e8) y = 1e9; hRaw = y; } hy = y < 1e8 ? y : -1e9; }   // (hy: the land's own skyline north of you, five columns across: where the far rows are a little soft, and what bare() counts under)
  // the sky's line: where level ground at the eye's level (at: the eye's point, as drawn) is highest on the screen, past the bend. It moves only with the pitch (and the screen's size): a real sky
  // does not move with the land in front of it. It came down to the lowest of the land's skylines north of you, eased: past a mountain the whole sky (sun, clouds, far hills) slid up
  // its side and down again, 58 art px walking 12 tiles to it.
  // ...with ground as low as the LOWEST LAND AHEAD, if it is lower than the eye's own (low: the level of the far land and sea north of you, as far as the far patches go, the sea's where the land is not known; past it the
  // patches stop: the line is at the farthest of them at the most). From a mountain the far land drops away past the bend, lower on the screen than ground at the eye's level would: the line was over a
  // gap the land could never fill, the backdrop's flat colours in it (the far land's green, the sea's blue in columns, a checker at their ends): "a flat blue mass" between the land and the far hills
  // ...and that is the EDGE (he, api.sky's edge), not the sky's line: the sky's line stays the eye's, the pitch's alone (hl). On the sky's line, climbing a hill of steps 6 levels the
  // whole sky, sun and clouds would come down 55 art px with the land ahead's own horizon, 9 a level, and up again down the other side. The far hills stand on the edge, the sky goes on down to them
  let lowKey = "", lowL = 1; const eyeC = {k: "", y: 0}, edgeC = {k: "", y: 0};
  function eyeLine(at, w, h, low, C) { const lv = Math.min(at[2] - .5, low), k = [cam.pitch.toFixed(2), cam.fov, api.bend, w, h, Math.round(lv * 16), Math.round(at[2] * 16)].join(); if (k !== C.k) { let m = 1e9; for (let dn = 1; dn <= H.R + 40; dn++) { const a = H.eng.at(at[0], at[1] - dn, lv); if (a && isFinite(a[1])) m = Math.min(m, a[1]); } C.k = k; C.y = m < 1e8 ? m : 0; } return C.y; }
  function lowAhead(tx, ty) { const H0 = Voxels.host, k = [tx >> 2, ty >> 2, H.eng.stamp].join(); if (k === lowKey) return lowL; lowKey = k; let m = 1e9;   // (every 4 tiles, as you go 4: some 200 columns)
    for (let dy = 6; dy <= H.R + 40; dy += 4) for (let dx = -H.R; dx <= H.R; dx += 4) { const x = tx + dx, y = ty - dy, c = H0.column(x, y); m = Math.min(m, !c ? H.SEA_L : H0.water(x, y) ? H0.waterTop(x, y) : c.length ? c[c.length - 1] : H.SEA_L); }
    return api.low = lowL = m; }   // (a dug pit there: the line a little lower, more sky behind the land, never a gap)
  // ONE EASING while the eye tilts: its pitch's (above). The sky's line is then where that pitch puts it, this frame: it goes with the land. (It had a quarter second of its own over the pitch's 400 ms:
  // through a tilt the sky came after the land, and a test that waited for the pitch to rest found the sky still moving.) At rest the line's small steps (the eye's level, a px or three over a hill)
  // and the land's edge (the far land's level comes in steps) are eased
  function lines(tx, ty, L, at, w, h, dt) {   // (the horizon is the surface's, however deep you are)
    horizon(tx, ty, L); const ease = (v, t) => !v || Math.abs(t - v) < .5 ? t : v + (t - v) * (1 - Math.exp(-dt / .25)), lw = lowAhead(tx, ty), te = Math.max(8, eyeLine(at, w, h, lw, edgeC) + 2);
    { const t = Math.max(8, eyeLine(at, w, h, 1e9, eyeC) + 2); hl = tilt > 0 && tilt < 1 ? t : ease(hl, t); } he = ease(he, te); api.line = [Math.min(at[2] - .5, lw), te - 2];
  }
  return {pitch, level, lines, snap() { hl = 0; }, get camL() { return camL; }, get tilt() { return tilt; }, get above() { return !!stage; }, get hy() { return hy; }};
};
