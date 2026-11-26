// VOX: the curved world. The land rolls away from the eye as on a log ("a voxel world viewed top-down in Animal
// Crossing style": there the world stays flat and every point is pushed down the picture by the square of its
// distance, whatever its height). One place for where a point of the land is drawn: `y` for whoever draws on the
// engine's picture (what stands on the land, aiming), and `GLSL`, the same in the engine's vertex shader, so the two
// cannot disagree (tests/test_vox_layer.py holds them together).
//
// A point at row f (where the row would be drawn flat at height 0: oy + row * tile), h px high, is drawn at
//     f - h + d * d / (4 * D)        D = y0 - yh
// x is never bent, a height is never scaled: it is taken off as on the flat picture. d is how far the point is past
// the line where the roll starts, px: of its row at the eye's height, and `lean` of what it stands over the eye
// (what is higher is drawn further up the picture, and counts as further: without that a slope that rises north
// climbs the picture as fast as the roll takes it down, and there is no horizon on a mountain's side); what is under the
// eye's height counts where the flat picture has it (from a cliff you look down on the plain, to the same horizon).
// d 0 and less: the flat picture, to the px. Level ground at the eye's height goes up the picture to the horizon,
// yh, where d = 2 * D, and past it comes down again, faster and faster: behind the roll. Since the push down is a
// square and a slope is a line, every slope has its horizon.
//
// A curve c: null (flat: today's picture), or {y0, yh, ref, lean, floor}, px of the picture from its top:
//   y0    where the roll starts. Under that line nothing changes.
//   yh    the top of the parabola (over y0): D = y0 - yh. With no floor, the horizon of level ground at the eye's height
//   ref   the eye's height, px over height 0
//   lean  the share of a height over the eye that counts as distance (0 to 1; 1: no land is ever over the line)
//   floor how squeezed a row is when it reaches the horizon (0, or not given: to nothing, the whole parabola; .25: a
//         tile's 16 px are 4 there, and what is further is behind the horizon: land is never drawn as mush). The
//         horizon is then where the parabola's slope is `floor`: at d = 2 * D * (1 - floor), drawn D * floor * floor
//         under yh (`line(c)`); past it a point comes down as the mirror of how it goes up.
// Whole px of paint ("never scale pixel art"): `snap` and the GLSL's rollY put a bent point on a whole px of the
// paint (k px of the picture each, counted from o: the flat picture's own px), so a tile's row is drawn a whole
// number of them tall; which of its 16 rows of paint are then left out is `rows`' (the same for a given height,
// whatever the frame: nothing shimmers as you walk), FS for the engine's fragment shader.
const VoxCurve = (() => {
  const span = (c) => { const q = c.floor || 0, D = c.y0 - c.yh; return [D, 2 * D * (1 - q), q]; };      // D, how far the horizon is past y0, the floor
  // a place s of the flat picture (a row at the eye's height, or lower land where it lies), `up` px over the eye
  function core(c, s, up) {
    const d = c.y0 - s + c.lean * up;
    if (d <= 0) return s - up;
    const [D, d1, q] = span(c), e = d - d1;
    return s - up + (e > 0 ? D * (1 - q) * (1 - q) + (1 + q) * e + e * e / (4 * D) : d * d / (4 * D));
  }
  // where a point of the land is drawn: its row (f) and its height
  const y = (c, f, h = 0) => { if (!c) return f - h; const up = Math.max(0, h - c.ref); return core(c, f - h + up, up); };
  // ...on a whole px of the paint (k px of the picture, counted from o), as the engine draws it. Flat: as it is
  const snap = (c, f, h, o, k) => { const v = y(c, f, h); return v === f - h ? v : Math.floor((v - o) / k + .5) * k + o; };
  // the row of a tile's paint (of `cell`) that its i-th px down shows when the tile is drawn n px tall (n <= cell)
  const rows = (i, n, cell) => Math.floor((i + .5) * cell / n + .01);
  function inv(c, s) {                                 // the place of the flat picture that is drawn at s (before the horizon); over the line: the horizon's
    if (!c || s >= c.y0) return s;
    const [D, d1] = span(c);
    return c.y0 - Math.min(d1, 2 * D * (1 - Math.sqrt(Math.max(0, 1 - (c.y0 - s) / D))));
  }
  const edge = (c) => c.y0 - span(c)[1];                                 // the place of the flat picture that is on the horizon
  // px past its horizon (0: before it): of a point, as it is looked for in the roll
  const past = (c, f, h = 0) => { if (!c) return 0; const up = Math.max(0, h - c.ref); return Math.max(0, c.y0 - (f - h + up) + c.lean * up - span(c)[1]); };
  const line = (c, h = 0) => c.yh + (c.y0 - c.yh) * (c.floor || 0) ** 2 - Math.max(0, h - c.ref) * (1 - c.lean);      // the horizon of level ground h px high: where it meets the sky
  // how squeezed level ground at the eye's height is at place s of the flat picture: 1 as it is, `floor` at the horizon
  const squeeze = (c, s) => { if (!c) return 1; const [D, , q] = span(c); return Math.max(q, Math.min(1, 1 - (c.y0 - s) / (2 * D))); };
  // uCurve: y0, yh, ref, lean (y0 <= yh: flat); uFloor. past: px past the horizon.
  const GLSL = `uniform vec4 uCurve; uniform float uFloor;
float curveY(float f, float h, out float past) {
  float D = uCurve.x - uCurve.y, up = max(0., h - uCurve.z), d = uCurve.x - (f - h + up) + uCurve.w * up; past = 0.;
  if (D <= 0. || d <= 0.) return f - h;
  past = max(0., d - 2. * D * (1. - uFloor));
  return f - h + (past > 0. ? D * (1. - uFloor) * (1. - uFloor) + (1. + uFloor) * past + past * past / (4. * D) : d * d / (4. * D));
}`;
  // for a vertex shader that has uO (where its tiles' corner is, flat) and uK (px of the picture a px of paint): `snap`
  const VS = GLSL + `
float rollY(float f, float h, out float past) { float y = curveY(f, h, past); return y == f - h ? y : floor((y - uO.y) / uK + .5) * uK + uO.y; }`;
  // for a fragment shader: a face's own row of paint (v, as it comes between the face's corners) at the middle of the
  // px of paint this px of the screen is in (y: where it is in the picture, o: a row of the paint's px): a px of
  // paint on the screen is one row of the paint, whole. And `rows`.
  const FS = `float rollRow(float v, float y, float o, float k) { float c = (floor((y - o) / k) + .5) * k + o, dy = dFdy(y); return abs(dy) > 0. ? v + (c - y) * dFdy(v) / dy + .003 : v; }
float rollPick(float i, float n, float cell) { return floor((i + .5) * cell / n + .01); }`;
  return {y, snap, rows, inv, past, edge, line, squeeze, GLSL, VS, FS, warp: (c, s) => (c ? core(c, s, 0) : s)};
})();
