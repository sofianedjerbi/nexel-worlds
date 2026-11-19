// VOX: water seen through. Water is one face a tile (vox_mesh.js), painted from the picture the view hands over
// (view.water). If the user of the engine asks (cfg.water.clear when the faces are made; view.wlook, each frame),
// that face is see-through and what is under it is drawn: a water tile's column that ends under its face is its bed,
// a block as the land's are (its top: bit 64, painted by the host, a page on from what floats; its fronts; the banks
// and cliffs beside it go on down to it). The faces seen through are kept apart (a list of their own, PAGE: no paint
// of theirs) and laid over the finished land in a second go, mixed in:
//   the tint   wlook.tint: a colour and how much of it [r, g, b, a] for water 0, 1, 2, 3, 4 levels deep (the last is
//              the deep the eye does not see through), then the sand under a shore's edge. How deep: of what is
//              seen under the px, a bed's top or the wall between two (a face knows its tile's depth, those of the
//              two tiles north of it and of the tiles west and east: `deep`). A bed is one step, whole
//              to its edge: no dither, no fade. The wall between two beds (a bank's foot under water too) is not seen
//              as it is painted: it is the colour of the bed at its foot (wlook.tint 6 to 10: the sand that deep, under
//              its tint), solid, its first two rows a step darker (the 6th tint's alpha: how much)
//   over it    the view's picture, as it is where it has paint (the waves, the glints), see-through where it has
//              none (the host leaves its bed out of it); and the foam: a broken line (5 px, 3 none) along the foot of a wall
//              that stands north of the water, where the eye sees water meet rock; none up a wall's west and east
//              sides: a stepped bank was a staircase of outlined squares (a face knows which of the eight tiles round it
//              are walls: its bits; wlook.foam: how much of it, wlook.foamAt: px from the wall's tile)
//   night      wlook.night (0 to 1): that much nearer to its night colour, wlook.dark [r, g, b], and hardly seen through
//   far        wlook.far [from, to, how much]: rows north of the eye over which the face is less and less seen through
// and the bed under it:
//   bend       wlook.bend: px the bed's paint slides sideways, in strips of four rows, slowly: it lies under moving water
//   light      wlook.light: lines of light drifting on the bed, fainter the deeper it lies
//   shade      what is in a shadow under water (the bed, the face) is never darker than wlook.shade of itself
//              [r, g, b]: a shadow in water stays water's colour; and a bed takes half of the land's light (its
//              shadows, its depth: the face over it has the other half), and no shade at the foot of its walls
// The water under a shore's top (a px under its level; the shore's paint leaves px see-through over it) is drawn
// twice: as the sand under the edge with the land, then with the faces seen through as water one level deep.
const VoxWater = (() => {
  const PAGE = 30;
  const FS = `
uniform vec4 uWL, uWM, uWT[11]; uniform vec3 uWFar, uWShade, uWNight; uniform float uWPass;
float wlift() { return floor(vGround.z / uUp + .5) * uUp; }      // a water face's level, px (the one under a shore's top is a px lower)
// a model's px (m: its paint): one that is half see-through, a shade on the water, is mixed in with the faces seen through
bool wmodel(vec4 m) { return uWL.x > .5 && (m.a < .98) != (uWPass > .5); }
// the bed's paint: slid sideways (bits 64: a top under water)
vec2 wbend(int bits) {
  if (uWL.y <= 0. || (bits & 64) == 0) return vec2(0.);
  return vec2(floor(sin(uWM.x * 1.5 + floor(vGround.y / 4.) * .36) * (uWL.y + .3) + .5), 0.);
}
// ...and the light on it: a net of lines where three waves cancel, drifting a px at a time
vec3 wbed(vec3 c, int bits) {
  if (uWL.z <= 0. || (bits & 64) == 0) return c;
  vec2 p = floor(vGround.xy) + vec2(floor(uWM.x * 5.), floor(uWM.x * 3.)); float k = 6.2832 / 64., d = -vGround.z / uUp;
  float v = sin(k * (2. * p.x + 3. * sin(k * 2. * p.y))) + sin(k * (3. * p.y + 2. * sin(k * 3. * p.x))) + sin(k * (p.x + p.y) * 2.);
  return abs(v) < .2 ? mix(c, vec3(1.), uWL.z * max(.08, .5 - .12 * d)) : c;
}
// a colour with the sun on it (lit), of what is in water (the bed, the face): its shadow kept water's colour
vec3 wshade(vec3 lit, vec3 c, int kind, int bits) { return uWL.x < .5 ? lit : kind == 2 ? max(lit, c * uWShade) : kind == 0 && (bits & 64) != 0 ? max(mix(c, lit, .5), c * uWShade) : lit; }
// ...and a face's px, lit, as it is laid (o: times how much of it there is): over a wall under water it is whole, the
// wall's colour (wWall, from wface) under it, in the shade if the face is (as a bed is: half)
vec4 wWall = vec4(0.);
vec4 wout(vec4 o) { if (wWall.a < .5) return o; vec3 b = inShade ? max(mix(wWall.rgb, mix(wWall.rgb, uShade, uSun.z), .5), wWall.rgb * uWShade) : wWall.rgb; return vec4(o.rgb + b * uLight * (1. - o.a), 1.); }
// how deep what is seen under row sy of a face lies (D: its tile's depth, the tile's north of it, the next one's): a
// bed's top (drawn a level's px down the picture for each level it lies deep), the nearest; or the wall between two:
// 100 more than the depth of the bed at its foot, and .5 more in its first two rows. The dark (4 deep, the last tint) is
// not seen through: all of its own tile, and a wall that goes down into it is the bed over it, no more
float wseen(float sy, vec3 D) {
  float d = 99.; bool hole = false; if (D.x > 3.5) return 4.;      // (hole: where the dark's own bed would be seen: there is none, the wall's colour)
  for (int j = 0; j < 3; j++) { float lo = -uCell * float(j) + uUp * D[j]; if (D[j] > 0. && sy >= lo && sy < lo + uCell) { if (D[j] > 3.5) hole = true; else d = min(d, D[j]); } }
  if (d > 98.) for (int j = 1; j < 3; j++) { float head = uCell - uCell * float(j) + uUp * D[j]; if (D[j - 1] > D[j] && sy >= head && sy < head + uUp * (D[j - 1] - D[j])) return D[j - 1] > 3.5 ? D[j] + 100. : D[j - 1] + (sy < head + 2. ? 100.5 : 100.); }
  return d < 98. ? d : hole ? 103. : D.x;
}
// the water's face: its colour and how much of it is laid over what is under (1: all of it). near: the land round its tile
// (1 north, then round by the east: 2, 4... 128)
vec4 wface(vec2 loc, int near) {
  vec4 s = uSea > .5 ? texture(uWater, (vFlat + vec2(0., wlift() * uK) - uWaterO) / uWaterK / uWaterSize) : vec4(uSeaCol, 1.);
  if (uWL.x < .5) return vec4(s.rgb, 1.);
  if (uWPass < .5) return vec4(uWT[5].rgb, 1.);                 // (under a shore's top, with the land: the sand under its edge)
  if (uSea < .5) s = vec4(0.);
  vec2 g = floor(vGround.xy), l = floor(loc); float d = 1., wall = 0.;
  if (vGround.z - wlift() > -.5) {
    d = wseen(clamp(l.y, 0., uCell - 1.), vMore.xyz); if (d > 50.) { wall = fract(d) > .25 ? 2. : 1.; d = floor(d - 100.); }
    // the foam: at the foot of a wall north of the face, in dashes
    if ((near & 1) != 0 && l.y + 1. == uWM.w && l.x >= 0. && l.x < uCell && mod(g.x + 3. * floor(g.y / uCell), 8.) < 5.) s = vec4(mix(s.rgb, vec3(1.), 1. - s.a), max(s.a, uWM.y));
  } else d = max(1., vMore.x);                                   // (under a shore's top: as deep as the water beside it)
  int di = int(clamp(floor(d + .5), 0., 4.)); vec4 t = uWT[di];
  // (a wall under water: the bed at its foot, as the land's depth has it, vox_light.js)
  if (wall > 0.) wWall = vec4(uWT[6 + di].rgb * (uDepth > .5 ? vec3(1.) - vec3(.025, .025, .021) * float(di) : vec3(1.)) * (wall > 1. ? uWT[5].a : 1.), 1.);
  float a = max(t.a, uWL.w * .86); t.rgb = mix(t.rgb, uWNight, uWL.w);      // (night)
  a = mix(a, max(a, uWFar.z), clamp((-vAt.x - uWFar.x) / max(1., uWFar.y - uWFar.x), 0., 1.) * step(.001, uWFar.z));
  float all = 1. - (1. - a) * (1. - s.a);
  return vec4((s.rgb * s.a + t.rgb * a * (1. - s.a)) / max(all, .001), all);
}`;
  // Before a frame's faces: what the view asks for
  function frame(gl, u, v) {
    const w = v.wlook || null, far = w && w.far ? w.far : [0, 1, 0], sh = w && w.shade ? w.shade : [0, 0, 0];
    gl.uniform4f(u.uWL, w ? 1 : 0, w ? w.bend || 0 : 0, w ? w.light || 0 : 0, w ? w.night || 0 : 0); gl.uniform4f(u.uWM, w ? w.t % 4096 : 0, w ? w.foam || 0 : 0, 0, w && w.foamAt !== undefined ? w.foamAt : 2);
    gl.uniform3f(u.uWFar, far[0], far[1], far[2]); gl.uniform3f(u.uWShade, sh[0], sh[1], sh[2]); gl.uniform3f(u.uWNight, ...(w && w.dark ? w.dark : [0, 0, 0])); gl.uniform1f(u.uWPass, 0);
    if (w) gl.uniform4fv(u["uWT[0]"], w.tint);
  }
  // The second go, the faces seen through: mixed over what is drawn, writing no depth (pr: the land's program, again).
  // -> is there one (on: start it; off: end it)
  function pass(gl, u, v, pr, on) {
    if (!v.wlook) return false;
    if (on) { gl.useProgram(pr); gl.uniform1f(u.uCut, 0); gl.uniform1f(u.uSec, 0); gl.enable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA); } else gl.disable(gl.BLEND);
    gl.uniform1f(u.uWPass, on ? 1 : 0); gl.depthMask(!on);
    return true;
  }
  // For the face of water tile (x, y), vox_mesh.js. deep: how deep the water is (levels) on it, on the tile north of
  // it and on the next (land: 0), and west and east of it (16 times the east's, and the west's). near: which of the
  // eight tiles round it are walls (land higher than its face: a shore has its own painted edge). Not seen through: all 0, as ever.
  const on = (cfg) => !!(cfg.water && cfg.water.clear);
  const bed = (cfg, deep) => on(cfg) && deep > 0 && deep < (cfg.water.dark || 1e9);      // is a bed that many levels under its face drawn: not one in the dark (cfg.water.dark: the depth the last tint is for)
  function deep(host, cfg, x, y) {
    if (!on(cfg)) return [0, 0, 0, 0];
    const d = (a, b) => { const c = host.column(a, b); return c && host.water(a, b) ? Math.max(0, Math.min(15, (host.waterTop ? host.waterTop(a, b) : 0) - c[c.length - 1])) : 0; };
    return [d(x, y), d(x, y - 1), d(x, y - 2), d(x - 1, y) + 16 * d(x + 1, y)];
  }
  // ...and for the water under a shore's top at (x, y): the shallowest of the water round it (an islet in the deep is not in a square of shallows)
  const shore = (host, cfg, x, y) => (on(cfg) ? RING.reduce((m, [dx, dy]) => { const d = deep(host, cfg, x + dx, y + dy)[0]; return d ? Math.min(m, d) : m; }, 16) % 16 : 0);
  const RING = [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]];
  function near(host, cfg, x, y) {
    let m = 0; const top = host.waterTop ? host.waterTop(x, y) : 0; if (on(cfg)) RING.forEach(([dx, dy], k) => { const c = host.column(x + dx, y + dy); if (c && !host.water(x + dx, y + dy) && c[c.length - 1] > top) m |= 1 << k; });
    return m;
  }
  return {FS, PAGE, frame, pass, deep, near, shore, on, bed};
})();
