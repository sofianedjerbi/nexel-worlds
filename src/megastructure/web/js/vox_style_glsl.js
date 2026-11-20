// VOX: the 2.5D look's shaders (vox_style.js draws with them): the land's (VS, FS: every face from the atlas of paints,
// AW px a side; a face's kind says how it is lit and cut: 0 a wall, 1 a top, 2 a sliced top, 3 water, 6 the box's
// side, 7 far land, 8 a model's face, 9 a ghost, 10 a shadow) and the sprites' (SV, SF: px for px). No game global.
const VoxStyleGLSL = (() => {
  const AW = 1024;
  const VS = `#version 300 es
  in vec3 p; in vec2 uv; in vec4 a; in float e; uniform mat4 m; uniform vec3 ctr; uniform float bend; out vec2 vu; out vec4 va; out float ve; out vec3 wp;
  void main() { vec3 q = p; float dn = max(0., ctr.z - 1. - q.z); q.y -= bend * dn * dn; gl_Position = m * vec4(q, 1.); vu = uv; va = a; ve = e; wp = p; }`;
  const FS = `#version 300 es
  precision mediump float; in vec2 vu; in vec4 va; in float ve; in vec3 wp; uniform sampler2D t, wt; uniform vec3 lamp, eye, fogc;
  uniform vec4 ub; uniform float wa, und, dep, sk, ovd, lr, day, amb, fn, ff, roof, rim, strata, dith, veil, chk, tm, dk, rd, sun, shp; uniform vec4 wv; uniform vec4 wtn[5]; uniform vec3 mc; out vec4 o;
  uniform vec2 vp; float hsh(vec2 v) { return fract(sin(dot(v, vec2(12.99, 78.23))) * 43758.5); }
  float bit(float v, float k) { return mod(floor(v / k), 2.); }
  vec3 rk(vec2 g, float d0, float kd) {   // natural strata: bands of uneven thickness and tone, earth near the meadow, stone deeper (g.y down = deeper)
    float b = g.y + floor(3. * sin(g.x * .09 + floor(g.y / 23.)) + 2. * sin(g.x * .031 + 1.7)), bd = floor(b / 11.), lb = b - bd * 11.;
    if (lb < (hsh(vec2(bd, 1.)) - .5) * 8.) { bd -= 1.; lb += 11.; } else if (lb >= 11. + (hsh(vec2(bd + 1., 1.)) - .5) * 8.) { bd += 1.; lb -= 11.; }
    float bdep = d0 + bd * 11. * kd, bn = hsh(vec2(bd, 3.));
    float st = step(bn, clamp((bdep - 1.) / 8., 0., .85)), sh = hsh(vec2(bd, 5.)), hu = hsh(vec2(bd, 6.));
    sh = floor(sh * 5.) / 4. + (hsh(g) > .92 ? .2 : 0.) - (hsh(g + 3.) > .95 ? .15 : 0.);
    vec3 ea = mix(vec3(.62, .41, .24), vec3(.36, .23, .14), sh), sa = mix(vec3(.56, .51, .45), vec3(.28, .27, .29), sh) * (hu < .33 ? vec3(1.08, .96, .84) : hu < .66 ? vec3(.92, .97, 1.06) : vec3(1.));
    vec3 col = mix(ea, sa, st); float lo = lb - (hsh(vec2(bd, 1.)) - .5) * 8.;
    if (lo < 1. && hsh(vec2(bd, 9.)) > .4 && hsh(vec2(floor((g.x + bd * 7.) / 6.), bd)) > .35) col *= .62;   // a seam: on some boundaries only, broken
    vec2 pc = floor(g / 7.); float ph = hsh(pc); vec2 pp = mod(g, 7.) - floor(vec2(hsh(pc + 7.), hsh(pc + 9.)) * 4. + 1.);
    if (ph > .68 && pp.x >= 0. && pp.x < 2. && pp.y >= 0. && pp.y < 2. - step(.84, ph)) col = (st > .5 ? vec3(.58, .55, .5) : vec3(.66, .52, .37)) * (pp.y < 1. ? 1.1 : .78);   // a pebble
    if (ub.w > .5) { vec3 base = mix(vec3(.5, .38, .28), vec3(.47, .45, .43), smoothstep(2., 12., bdep)); col = base * (.92 + .16 * clamp(dot(col, vec3(.33)) / .45 - .5, 0., 1.)); }   // (?hd: calm: one earth tone fading to one stone tone, the bands a faint 15% texture)
    return col;
  }
  vec3 fl() { float b = clamp(floor((dep + (lamp.y - .6) / .5 - va.w) / 4.) / 3., 0., 1.); return mix(vec3(.46, .36, .27), vec3(.4, .38, .38), b); }   // flat rock: one tone per depth band
  void main() {
    float kind = va.z; vec2 lu = mod(vu, 16.);
    if (rd > .5 && (wp.z < lamp.z + .3 || wp.y < lamp.y - .55 || distance(gl_FragCoord.xy, mc.xy) > mc.z || mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.) < 1.)) discard;   // (rd: a model south of you and over your feet, drawn again over you: one px in two of it, in a disc round you)
    float hd = distance(wp.xz, lamp.xz), va2 = veil > 0. ? mix(veil, 1., smoothstep(2.5, 6.5, hd)) : 1.;
    if (chk > .5 && hd < 4.5 && mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.) < 1.) discard;
    vec4 c = texture(t, vu / ${AW}.); if (kind > 7.5 && (c.a < .5 || (kind > 8.5 && kind < 9.5 && mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.) < 1.))) discard; if (kind > 9.5) { float sa = c.a * 255., rm = sa < 200. && sa > 150. ? 1. : 0., fx = sa > 240. || sa < 176. ? 1. : sun; if (rm != shp || fx < .03) discard; o = vec4(.2, .15, .3, .3 * fx * (1. - .45 * rm)); return; } if (c.a < .5) c = vec4(.42, .32, .25, 1.);   // (8: a model's face, host.models: a bridge's planks; its see-through px are holes; 9: a ghost of one, view.ghosts: one px in two; 10: a shadow on the ground, box.shade: a flat shade laid over the land; its paint's alpha says which: 255 a shade that is always there, 224 the sun's (as dark as sun), 192 the sun's soft rim, 160 a rim that is always there; shp: which are drawn now, 0 the full ones, 1 the rims)
    float d = distance(wp, lamp) / lr, lan = clamp(1.15 - d * d, 0., 1.);
    float kx = floor(va.x * 20. + .05) / 20.;   // (a face's light and the shade of its corners: in whole steps; it ran smooth from corner to corner: a blurred halo on the ground round every block)
    float l = max(va.y * day, amb + (1. - amb) * lan) * kx;
    if (dith > .5) { float b = mod(floor(gl_FragCoord.x / 2.), 2.) * 2. + mod(floor(gl_FragCoord.y / 2.), 2.); l = floor(l * 4. + (b + .5) / 4.) / 4. + .12; }
    vec3 warm = mix(vec3(1.), vec3(1.1, .97, .8), lan * (1. - va.y));
    vec3 col = c.rgb * l * warm;
    vec2 bq = wp.xz - lamp.xz; float bj = .5 * mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.) - (kind < .5 ? 1. : 0.);   // (?hd: the slice only in its box round you, ub: tiles north, across, south, on; edge a 2x2 checker; the box's cut sides strata too)
    if (und > .5 && kind < 2.5 && !(ub.w > .5 && kind > .5 && kind < 1.5 && va.y > .5) && (ub.w < .5 || kind > 1.5 || (bq.y >= -ub.x - .5 + bj && abs(bq.x) <= ub.y + .5 - bj && bq.y <= ub.z + .5 - bj))) {                                // under ground: a slice through the earth, your space hollowed in it
      vec2 b0 = vu - lu; vec3 rf = (texture(t, (b0 + vec2(3.5, 9.5)) / ${AW}.).rgb + texture(t, (b0 + vec2(11.5, 11.5)) / ${AW}.).rgb + texture(t, (b0 + vec2(5.5, 13.5)) / ${AW}.).rgb + texture(t, (b0 + vec2(13.5, 15.5)) / ${AW}.).rgb) * .25, base = mix(vec3(.5, .38, .28), vec3(.47, .45, .43), smoothstep(2., 12., dep + (5. - lamp.z * 16.) / 16. * 1.6));   // (?hd: a front's own flat tone, and the rock's calm tone by depth)
      if (kind > 1.5) {                                          // the cut: dark earth near the surface, stone deeper, in strata
        vec2 g = floor(wp.xz * 16.); col = bit(ve, 8192.) > .5 ? fl() : rk(g, dep + (5. - lamp.z * 16.) / 16. * 1.6, 1.6 / 16.);   // (far from your space: plain flat rock)
        vec2 sc = gl_FragCoord.xy / vp - .5; col *= .7 * (1. - .9 * dot(sc, sc));                // darker and flat, darker to the screen's edges
        if (ub.w > .5) {   // (?hd: the cut is rock: the tileset's own front, its 8 rows twice a tile, each tile's a little off its neighbour's (no planks). Under a roof (dk): one calm tone by depth, the front's lines faint on it, your lantern's light on it in three flat steps, five tiles round you (it was rings to the screen's edge, a checker at each: a target), beyond it flat rock; no roof: the rock as it is, in the day's light)
          float oy = mod(lu.y + floor(hsh(floor(wp.xz)) * 8.), 8.), q = distance(wp.xz, lamp.xz) / 5.5, g4 = floor(clamp(1. - q * q, 0., 1.) * 3. + .5) / 3.; vec3 rc = texture(t, (b0 + vec2(lu.x, 8. + oy)) / ${AW}.).rgb;
          col = mix(rf * .82, base * (.3 + .26 * g4) * mix(vec3(1.), vec3(1.06, .98, .88), g4), dk) * clamp(dot(rc, vec3(.33)) / max(.05, dot(rf, vec3(.33))), .92 - .06 * dk, 1.06 + .04 * dk); }
        if (bit(ve, 16.) > .5) col = c.rgb * .13 * (mod(g.x + g.y, 2.) < 1. ? 1. : .8) + vec3(.02);   // a cave on another level: dark, its floor faint
        if ((bit(ve, 32.) > .5 && lu.y < 2.) || (bit(ve, 64.) > .5 && lu.x > 14.) || (bit(ve, 128.) > .5 && lu.y > 14.) || (bit(ve, 256.) > .5 && lu.x < 2.)) col = vec3(.85, .68, .48);
        float r = 0.; if (bit(ve, 1.) > .5 && lu.y < 1.) r = 1.; if (bit(ve, 2.) > .5 && lu.x > 15.) r = 1.; if (bit(ve, 4.) > .5 && lu.y > 15.) r = 1.; if (bit(ve, 8.) > .5 && lu.x < 1.) r = 1.;
        col = mix(col, vec3(.95, .75, .5) * (.5 + lan), r * .8);
      } else if (kind < .5) { col = bit(ve, 16384.) > .5 ? c.rgb * .3 : bit(ve, 8192.) > .5 ? fl() * .75 : ub.w > .5 ? mix(c.rgb * max(day * .85, amb), base * vec3(1.42, 1.2, .98) * clamp(dot(c.rgb, vec3(.33)) / max(.05, dot(rf, vec3(.33))), .84, 1.1) * (amb + (1. - amb) * lan) * warm, dk) * kx * .92 : rk(floor(vec2((wp.x + wp.z) * 16., -wp.y * 16.)), dep + (lamp.y - .6) / .5, 1. / 8.) * l * warm * .6; }   // a wall: the strata in world height (one band pattern, not per level)
      else {                                                      // a floor: a step down has a lit lip, a step up shades its foot
        float ls = floor(lan * 3. + .5) / 3., trd = bit(ve, 16384.); col = ub.w > .5 ? mix(c.rgb * (1.05 + .5 * ls) * vec3(1.12, 1., .8) + vec3(.2, .13, .05) * ls, c.rgb * (1.05 + .2 * ls) * vec3(1.08, 1., .86), trd) : c.rgb * (.75 + .6 * lan) * vec3(1.12, 1., .8) + vec3(.2, .13, .05) * lan;   // your space: lighter and warmer, a lantern's glow (?hd: in three flat steps as the rock round it. A room's floor is bright and warm, the look that was approved (189 took the glow off every floor for the stair's sake: the room went dull); trd: a stair's tread or small landing, a floor that is not 4 tiles on one level: the floor's own tone and no glow (with it each tread was a bright yellow block), its lip lit, its riser dark)
        float ue = min(min(mix(9., lu.y, bit(ve, 512.)), mix(9., 15. - lu.x, bit(ve, 1024.))), min(mix(9., 15. - lu.y, bit(ve, 2048.)), mix(9., lu.x, bit(ve, 4096.))));
        if (ue < 3.) col *= .45 + .15 * floor(ue);
        if (va.w > (lamp.y - .6) / .5 - 3. && ((bit(ve, 1.) > .5 && lu.y < 1.) || (bit(ve, 2.) > .5 && lu.x > 15.) || (bit(ve, 4.) > .5 && lu.y > 15.) || (bit(ve, 8.) > .5 && lu.x < 1.))) col = mix(col, vec3(1., .93, .75), .5);   // (only near your level: no lines far below; a lip, not a block: at .85 with the glow each tread of a stair was a bright yellow block)
      }
      if (va.y > .5 && kind < 1.5) col = mix(col, c.rgb * vec3(.9, 1., 1.15) * .85, .6);   // the daylight of the way up
    } else if (kind > 1.5 && kind < 2.5) {                              // a sliced top: the land over you
      col = c.rgb * mix(roof, 1., va.y * sk) * mix(vec3(.9, .85, 1.), vec3(1.), va.y * sk);
      float r = 0.; if (bit(ve, 1.) > .5 && lu.y < 1.) r = 1.; if (bit(ve, 2.) > .5 && lu.x > 15.) r = 1.;
      if (bit(ve, 4.) > .5 && lu.y > 15.) r = 1.; if (bit(ve, 8.) > .5 && lu.x < 1.) r = 1.;
      if (r > 0. && rim > 0.) col = mix(col, vec3(1., .9, .68), rim);
    } else if (kind < 1.5 && kind > .5 && rim > 0.) {            // a top at a drop: its lip catches the light
      if (bit(ve, 4.) > .5 && lu.y > 15.) col = mix(col, vec3(1., .94, .78), rim * .7);
      if (bit(ve, 1.) > .5 && lu.y < 1.) col *= 1. - rim * .5;
    }
    if (kind > 5.5 && strata > 0.) { float s = mod(va.w, 2.); col *= s < 1. ? 1. : 1. - strata; if (lu.y > 15.) col *= .7; col = mix(col, col * vec3(.85, .9, 1.1), clamp(-va.w / 10., 0., .6)); }
    if (kind > 2.5 && kind < 3.5) {                              // water: the game's own picture of it over a tint (?hd: the picture is the clear water, its bed showing: only a little of it over the sea tint)
      vec2 w = (vec2(wp.x, wp.z) * 16. - wv.xy) / wv.zw; vec4 wc = wv.z > 0. ? texture(wt, w) : vec4(0.);
      vec3 sea = vec3(.36, .64, .8) * max(l, .6);
      col = mix(sea, wc.rgb, wc.a * (ub.w > .5 ? .3 : .8));
      if (wtn[4].a > .5) { vec4 tn = wtn[int(clamp(ve, 0., 4.))]; col = mix(tn.rgb * max(l, .6), wc.rgb, wc.a * .45); o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)) * .4), max(tn.a, wc.a * .45)); return; }   // (light.wtint: clear water: a tint and how much of it for water 0..4 levels deep (ve), the bed showing through; the game's picture of the water, its waves and glints, over it)
      o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)) * (ub.w > .5 ? .4 : 1.)), wa); return;   // (?hd: the far sea stays blue to the horizon)
    }
    if (kind > 6.5 && kind < 7.5) col = (texture(t, (vu + vec2(-4., -4.)) / ${AW}.).rgb + texture(t, (vu + vec2(4., -4.)) / ${AW}.).rgb + texture(t, (vu + vec2(-4., 4.)) / ${AW}.).rgb + texture(t, (vu + vec2(4., 4.)) / ${AW}.).rgb) * .25 * kx * max(day, .35);   // (?hd: the land past the box: its own tint, flat, in the haze)
    col = mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)));
    if (veil > 0.) col *= mix(ovd, 1., smoothstep(2.5, 6.5, hd)); o = vec4(col, va2);
  }`;
  const SV = `#version 300 es
  in vec3 p; in vec2 uv; out vec2 vu; void main() { gl_Position = vec4(p, 1.); vu = uv; }`;
  const SF = `#version 300 es
  precision mediump float; in vec2 vu; uniform sampler2D t; uniform float sil; uniform vec3 mc; out vec4 o; void main() { vec4 c = texture(t, vu); if (c.a < .5) discard; if (sil > 1.5 && distance(gl_FragCoord.xy, mc.xy) < mc.z && mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.) < 1.) discard; o = sil > .5 && sil < 1.5 ? vec4(.95, .8, .55, .4) : c; }`;   // (sil 2: what stands in front of you: one px in two of it, a 2x2 checker, in a disc round you (mc), so you are seen through it; the rest of it whole)
  return {AW, VS, FS, SV, SF};
})();
