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
// A curve c: null (flat: today's picture), or {y0, yh, ref, lean}, px of the picture from its top:
//   y0    where the roll starts. Under that line nothing changes.
//   yh    the horizon of level ground at the eye's height (over y0)
//   ref   the eye's height, px over height 0
//   lean  the share of a height over the eye that counts as distance (0 to 1; 1: no land is ever over the line)
const VoxCurve = (() => {
  // a place s of the flat picture (a row at the eye's height, or lower land where it lies), `up` px over the eye
  function core(c, s, up) {
    const d = c.y0 - s + c.lean * up;
    return d <= 0 ? s - up : s - up + d * d / (4 * (c.y0 - c.yh));
  }
  // where a point of the land is drawn: its row (f) and its height
  const y = (c, f, h = 0) => { if (!c) return f - h; const up = Math.max(0, h - c.ref); return core(c, f - h + up, up); };
  function inv(c, s) {                                 // the place of the flat picture that is drawn at s (before the horizon); over the line: the horizon's
    if (!c || s >= c.y0) return s;
    const D = c.y0 - c.yh;
    return c.y0 - 2 * D * (1 - Math.sqrt(Math.max(0, 1 - (c.y0 - s) / D)));
  }
  const edge = (c) => c.y0 - 2 * (c.y0 - c.yh);                          // the place of the flat picture that is on the horizon
  // px past its horizon (0: before it): of a point, as it is looked for in the roll
  const past = (c, f, h = 0) => { if (!c) return 0; const up = Math.max(0, h - c.ref); return Math.max(0, c.y0 - (f - h + up) + c.lean * up - 2 * (c.y0 - c.yh)); };
  const line = (c, h = 0) => c.yh - Math.max(0, h - c.ref) * (1 - c.lean);      // the horizon of level ground h px high: where it meets the sky
  // uCurve: y0, yh, ref, lean (y0 <= yh: flat). past: px past the horizon.
  const GLSL = `uniform vec4 uCurve;
float curveY(float f, float h, out float past) {
  float D = uCurve.x - uCurve.y, up = max(0., h - uCurve.z), d = uCurve.x - (f - h + up) + uCurve.w * up; past = 0.;
  if (D <= 0. || d <= 0.) return f - h;
  past = max(0., d - 2. * D);
  return f - h + d * d / (4. * D);
}`;
  return {y, inv, past, edge, line, GLSL, warp: (c, s) => (c ? core(c, s, 0) : s)};
})();
