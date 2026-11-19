// VOX: water seen through. Water is one face a tile (vox_mesh.js), painted from the picture the view hands over
// (view.water). If the user of the engine asks (cfg.water.clear when the faces are made; view.wlook, each frame),
// that face is see-through and what is under it is drawn: a water tile's column that ends under its face is its bed,
// a block as the land's are (its top: bit 64, painted by the host, a page on from what floats; its fronts; the banks
// and cliffs beside it go on down to it). The faces seen through are kept apart (a list of their own, PAGE: no paint
// of theirs) and laid over the finished land in a second go, mixed in:
//   the tint   wlook.tint: a colour and how much of it [r, g, b, a] for water 0, 1, 2, 3, 4 levels deep (the last is
//              the deep the eye does not see through), then the sand under a shore's edge. How deep: of what is
//              seen under the px, a bed's top or the wall between two (a face knows its tile's depth, those of the
//              two tiles north of it and of the tiles west and east: `deep`). A bed is one step; down a wall, and
//              for a px each side where two steps meet on the flat, the steps follow each other in 2 x 2 dither. No smooth fade.
//   over it    the view's picture, as it is where it has paint (the waves, the glints), see-through where it has
//              none (the host leaves its bed out of it); and the foam: one line along the foot of every wall that
//              stands in the water, all the way round its corners (a face knows which of the eight tiles round it
//              are walls: its bits; wlook.foam: how much of it, wlook.foamAt: px from the wall's tile)
//   night      wlook.night (0 to 1): that much nearer to its night colour, wlook.dark [r, g, b], and hardly seen through
//   far        wlook.far [from, to, how much]: rows north of the eye over which the face is less and less seen through
// and the bed under it:
//   bend       wlook.bend: px the bed's paint slides sideways, in strips of four rows, slowly: it lies under moving water
//   light      wlook.light: lines of light drifting on the bed, fainter the deeper it lies
//   shade      what is in a shadow under water (the bed, the face) is never darker than wlook.shade of itself
//              [r, g, b]: a shadow in water stays water's colour
// The water under a shore's top (a px under its level; the shore's paint leaves px see-through over it) is drawn
// twice: as the sand under the edge with the land, then with the faces seen through as water one level deep.
const VoxWater = (() => {
  const PAGE = 30;
  const FS = `
uniform vec4 uWL, uWM, uWT[6]; uniform vec3 uWFar, uWShade, uWNight; uniform float uWPass;
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
vec3 wshade(vec3 lit, vec3 c, int kind, int bits) { return uWL.x > .5 && (kind == 2 || (kind == 0 && (bits & 64) != 0)) ? max(lit, c * uWShade) : lit; }
// how deep what is seen under row sy of a face lies (D: its tile's depth, the tile's north of it, the next one's): a
// bed's top (drawn a level's px down the picture for each level it lies deep), the nearest; or the wall between two
float wseen(float sy, vec3 D) {
  float d = 99.;
  for (int j = 0; j < 3; j++) { float lo = -uCell * float(j) + uUp * D[j]; if (D[j] > 0. && sy >= lo && sy < lo + uCell) d = min(d, D[j]); }
  if (d > 98.) for (int j = 1; j < 3; j++) { float head = uCell - uCell * float(j); if (D[j - 1] > D[j] && sy >= head + uUp * D[j] && sy < head + uUp * D[j - 1]) d = min(d, (sy - head + .5) / uUp); }
  return d > 98. ? D.x : d;
}
// the water's face: its colour and how much of it is laid over what is under (1: all of it). near: the land round its tile
// (1 north, then round by the east: 2, 4... 128)
vec4 wface(vec2 loc, int near) {
  vec4 s = uSea > .5 ? texture(uWater, (vFlat + vec2(0., wlift() * uK) - uWaterO) / uWaterK / uWaterSize) : vec4(uSeaCol, 1.);
  if (uWL.x < .5) return vec4(s.rgb, 1.);
  if (uWPass < .5) return vec4(uWT[5].rgb, 1.);                 // (under a shore's top, with the land: the sand under its edge)
  if (uSea < .5) s = vec4(0.);
  vec2 g = floor(vGround.xy), l = floor(loc); float d = 1., b = (mod(g.x, 2.) + 2. * mod(g.x + g.y, 2.)) / 4. + .125;
  if (vGround.z - wlift() > -.5) {
    vec3 D = vMore.xyz; float we = floor(vMore.w + .5), W = mod(we, 16.), E = floor(we / 16.), sy = clamp(l.y, 0., uCell - 1.);
    d = (wseen(sy - 1., D) + wseen(sy + 1., D)) * .5;
    if (abs(d - D.x) < .01) { if (l.x < 1. && W > 0.) d = (d + W) * .5; if (l.x > uCell - 2. && E > 0.) d = (d + E) * .5; }
    // the foam: the px at one distance from the walls, whichever way they lie
    float n = l.y + 1., e = uCell - l.x, so = uCell - l.y, w = l.x + 1., f = 99.;
    if ((near & 1) != 0) f = min(f, n); if ((near & 4) != 0) f = min(f, e); if ((near & 16) != 0) f = min(f, so); if ((near & 64) != 0) f = min(f, w);
    if ((near & 2) != 0) f = min(f, max(e, n)); if ((near & 8) != 0) f = min(f, max(e, so)); if ((near & 32) != 0) f = min(f, max(w, so)); if ((near & 128) != 0) f = min(f, max(w, n));
    if (f == uWM.w) s = vec4(mix(s.rgb, vec3(1.), 1. - s.a), max(s.a, uWM.y));
  }
  vec4 t = uWT[int(clamp(floor(d + b), 0., 4.))];              // (from one step to the next: 2 x 2 dither)
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
  const RING = [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]];
  function near(host, cfg, x, y) {
    let m = 0; const top = host.waterTop ? host.waterTop(x, y) : 0; if (on(cfg)) RING.forEach(([dx, dy], k) => { const c = host.column(x + dx, y + dy); if (c && !host.water(x + dx, y + dy) && c[c.length - 1] > top) m |= 1 << k; });
    return m;
  }
  return {FS, PAGE, frame, pass, deep, near, on, bed};
})();
