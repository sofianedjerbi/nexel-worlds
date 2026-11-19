// VOX: the curved world. The ground bends away to a horizon in the upper part of the picture, as on a log seen
// from above ("a voxel world viewed top-down in Animal Crossing style"). One place for where a row of the ground
// is drawn: `y` for whoever draws on the engine's picture (what stands on the land, aiming), and `GLSL`, the same
// in the engine's vertex shader, so the two cannot disagree (tests/test_vox_layer.py holds them together).
//
// x is never bent. What is lower than the eye is bent where the flat picture has it (from a height you look down
// on it: the plain under a mountain goes up to the same horizon as the mountain's own top, and a drop is squeezed
// with distance as the rows are). What is higher than the eye leans back as it goes away: a share of its height
// (lean) is bent with the rows, the rest stands up from them unscaled: a far hill stands over the line, against
// the sky, half as tall as beside you, and a far terrace is not a wall. The two meet at the eye's height; near you
// neither changes anything; and neither ever puts a further row lower down the picture than a nearer one.
//
// A curve c: null (flat: today's picture), or {y0, yh, ref, sink, soft, g, lean}, px of the picture from its top:
//   y0    where the bend starts. Under that line nothing changes: the picture is exactly the flat one.
//   yh    the horizon line (over y0). A place s px down the flat picture, w = (y0 - s) / d past the start (d = y0 -
//         yh), is drawn at y0 - d * t, where asin(t) * (1 + g * t * t) = w: g 0, a point as far round a log (t =
//         sin(w)); it reaches the line at t = 1.
//   g     the stretch: how much more ground the far part of the bend holds (the roll-off: far rows are closer
//         together, and (1 + g) times the ground is seen before the horizon)
//   ref   the eye's height, px over height 0
//   lean  the share of a height over the eye that is bent as rows are (0: it stands up whole; 1: no land is
//         ever over the horizon)
//   sink  past the horizon the ground comes down again behind it, `sink` px for each px further...
//   soft  ...once it is well past: gently at first, sink * p * p / (p + soft) for p px past (it leaves the line as
//         level as it came to it: a hole dug on the horizon has its far side just under the line, not a tile down)
// f, everywhere: where the row would be drawn flat at height 0 (oy + row * tile); h: a height, px.
const VoxCurve = (() => {
  const Q = Math.PI / 2;
  // t for w: by halving, the same steps as the shader's (g 0: the sine itself)
  function roll(w, g) {
    if (!g) return Math.sin(w);
    let lo = 0, hi = 1;
    for (let i = 0; i < 24; i++) { const m = (lo + hi) * .5; if (Math.asin(m) * (1 + g * m * m) < w) lo = m; else hi = m; }
    return (lo + hi) * .5;
  }
  // a place s of the flat picture (a row at the eye's height, or lower land where it lies), `up` px over the eye
  function core(c, s, up) {
    const a = s - c.lean * up;                         // (where it is looked for in the bend)
    if (a >= c.y0) return s - up;
    const d = c.y0 - c.yh, most = Q * (1 + c.g), w = (c.y0 - a) / d, p = Math.max(0, (c.y0 - s) / d - most) * d;
    return c.y0 - d * (w >= most ? 1 : roll(w, c.g)) - (1 - c.lean) * up + (p > 0 ? c.sink * p * p / (p + c.soft) : 0);
  }
  // where a point of the land is drawn: its row (f) and its height
  const y = (c, f, h = 0) => { if (!c) return f - h; const up = Math.max(0, h - c.ref); return core(c, f - h + up, up); };
  function inv(c, s) {                                 // the place of the flat picture that is drawn at s; over the line: the horizon's
    if (!c || s >= c.y0) return s;
    const d = c.y0 - c.yh, t = Math.min(1, (c.y0 - s) / d);
    return c.y0 - d * Math.asin(t) * (1 + c.g * t * t);
  }
  const edge = (c) => c.y0 - (c.y0 - c.yh) * Q * (1 + c.g);              // the place of the flat picture that is on the horizon
  const past = (c, f, h = 0) => (c ? Math.max(0, edge(c) - (f - Math.min(h, c.ref))) : 0);      // px past the horizon (0: before it)
  const line = (c, h = 0) => c.yh - Math.max(0, h - c.ref) * (1 - c.lean);      // the horizon of ground h px high: where it meets the sky
  // uCurve: y0, yh, ref, sink (y0 <= yh: flat); uRoll: soft, g, lean. past: px past the horizon.
  const GLSL = `uniform vec4 uCurve; uniform vec3 uRoll;
float curveY(float f, float h, out float past) {
  float d = uCurve.x - uCurve.y, up = max(0., h - uCurve.z), s = f - h + up, a = s - uRoll.z * up; past = 0.;
  if (d <= 0. || a >= uCurve.x) return f - h;
  float most = 1.5707963 * (1. + uRoll.y), w = (uCurve.x - a) / d, t = 1.;
  past = max(0., (uCurve.x - s) / d - most) * d;
  if (w < most) {
    if (uRoll.y <= 0.) t = sin(w);
    else { float lo = 0., hi = 1.; for (int i = 0; i < 24; i++) { float m = (lo + hi) * .5; if (asin(m) * (1. + uRoll.y * m * m) < w) lo = m; else hi = m; } t = (lo + hi) * .5; }
  }
  return uCurve.x - d * t - (1. - uRoll.z) * up + (past > 0. ? uCurve.w * past * past / (past + uRoll.x) : 0.);
}`;
  return {y, inv, past, edge, line, GLSL, warp: (c, s) => (c ? core(c, s, 0) : s)};
})();
