// The sun at this hour: which way the shadows of what stands lie and how dark they are (the HD look casts them: hd_sun.js).
// Long to the west in the morning, short at noon, long to the east in the evening; at night none but a fire's.
//   SunLand.hour() -> {dark: how dark the hour is, much, long: the settings' Shadows and Shadow length, alpha: how dark
//     a shadow is, kx, ky: where a shadow lies, in heights of what throws it (kx sideways, ky towards you)}
//   SunLand.SHADE: the numbers: alpha by day, night, reach (a shadow's length sideways at sunrise, in heights), fall
//     (towards you, always), fire (tiles a fire lights)
const SunLand = (() => {
  const SHADE = {alpha: .3, night: 0, reach: 1.5, fall: .45, fire: 6};
  function hour() {
    const phase = (((clock.phase || 0) % 1) + 1) % 1, day = phase < .75;
    const a = day ? phase / .75 : (phase - .75) / .25;                               // the sun's way across (at night: the moon's)
    const {dark} = Light.now();
    const much = opt("shadows") / 100, long = opt("shadowlen") / 100;                 // (the settings: how dark, how long)
    return {dark, much, long, alpha: Math.min(.9, (SHADE.alpha + (SHADE.night - SHADE.alpha) * dark) * much), kx: (2 * a - 1) * SHADE.reach * long, ky: SHADE.fall * long};
  }
  return {hour, SHADE};
})();
