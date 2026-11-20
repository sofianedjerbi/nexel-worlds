// VOX: the 2.5D look's shaders (vox_style.js draws with them): the land's (VS, FS: every face from the atlas of paints,
// AW px a side; a face's kind says how it is lit: 0 a wall, 1 a top, 2 a terrace of the open pit, 3 water,
// 7 far land, 8 a model's face, 9 a ghost, 10 a shadow) and the sprites' (SV, SF: px for px). No game global.
const VoxStyleGLSL = (() => {
  const AW = 1024;
  const VS = `#version 300 es
  in vec3 p; in vec2 uv; in vec4 a; in float e; uniform mat4 m; uniform vec3 ctr; uniform float bend; out vec2 vu; out vec4 va; out float ve; out vec3 wp;
  void main() { vec3 q = p; float dn = max(0., ctr.z - 1. - q.z); q.y -= bend * dn * dn; gl_Position = m * vec4(q, 1.); vu = uv; va = a; ve = e; wp = p; }`;
  const FS = `#version 300 es
  precision mediump float; in vec2 vu; in vec4 va; in float ve; in vec3 wp; uniform sampler2D t, wt; uniform vec3 lamp, eye, fogc, mc;
  uniform vec4 cl, wv, wtn[5]; uniform float wa, dep, lr, day, amb, fn, ff, rim, rd, sun, shp; out vec4 o;
  float bit(float v, float k) { return mod(floor(v / k), 2.); }
  void main() {
    float kind = va.z, ck = mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.); vec2 lu = mod(vu, 16.);
    if (!(kind > 6.5 && kind < 7.5) && !(kind > 2.5 && kind < 3.5 && ve > 8.5) && !(kind > 8.5 && kind < 9.5) && (wp.x < cl.x + .001 || wp.x > cl.y - .001 || wp.z < cl.z + .001 || wp.z > cl.w + .001)) discard;   // (cl: the columns and rows of the land asked for: the lists are whole chunks of 8 x 8 tiles (vox_style_land.js), what is outside is left out here; not the far patches, not a ghost)
    if (rd > .5 && (wp.z < lamp.z + .3 || wp.y < lamp.y - .55 || distance(gl_FragCoord.xy, mc.xy) > mc.z || ck < 1.)) discard;   // (rd: a model south of you and over your feet, drawn again over you: one px in two of it, in a disc round you)
    if (kind < 2.5 && bit(ve, 32.) > .5 && ck < 1. && distance(gl_FragCoord.xy, mc.xy) < mc.z * 4.) discard;   // (the wall left south of a pit past its cap: one px in two of it round you)
    vec4 c = texture(t, vu / ${AW}.); if (kind > 7.5 && (c.a < .5 || (kind > 8.5 && kind < 9.5 && ck < 1.))) discard; if (kind > 9.5) { float sa = c.a * 255., rm = sa < 200. && sa > 150. ? 1. : 0., fx = sa > 240. || sa < 176. ? 1. : sun; if (rm != shp || fx < .03) discard; o = vec4(.2, .15, .3, .3 * fx * (1. - .45 * rm)); return; } if (c.a < .5) c = vec4(.42, .32, .25, 1.);   // (8: a model's face, host.models: a bridge's planks; its see-through px are holes; 9: a ghost of one, view.ghosts: one px in two; 10: a shadow on the ground, box.shade: a flat shade laid over the land; its paint's alpha says which: 255 a shade that is always there, 224 the sun's (as dark as sun), 192 the sun's soft rim, 160 a rim that is always there; shp: which are drawn now, 0 the full ones, 1 the rims)
    float d = distance(wp, lamp) / lr, lan = clamp(1.15 - d * d, 0., 1.), ls = floor(lan * 3. + .5) / 3.;
    float kx = floor(va.x * 20. + .05) / 20.;   // (a face's light and the shade of its corners: in whole steps; it ran smooth from corner to corner: a blurred halo on the ground round every block)
    float l = max(va.y * day, amb + (1. - amb) * lan) * kx;
    vec3 col = c.rgb * l * mix(vec3(1.), vec3(1.1, .97, .8), lan * (1. - va.y));
    // under the land's top (a face the sky does not reach: a cave's wall, a face or a terrace of the pit): the day's light at the land's top, level by level down to your lantern's at your floor; never dark
    float up = clamp((va.w - (lamp.y - .6) / .5) / max(dep, 1.), 0., 1.); vec3 pit = mix(vec3(1.14, 1., .82), vec3(max(day * .95, amb)), up);
    if (kind > 1.5 && kind < 2.5) col = c.rgb * pit * .85 + vec3(.03, .02, .01);                    // a terrace of the pit: cut earth, cut stone: a little darker than the faces, no lip
    else if (kind < .5 && va.y < .5) col = bit(ve, 16.) > .5 ? mix(c.rgb, vec3(.8, .62, .43), .6) * (.95 + .15 * ls) : c.rgb * pit * kx + vec3(.03, .02, .01);   // a wall; the riser of a step you can take: the tread's tone, a wall is rock
    else if (kind < 1.5 && kind > .5 && va.y < .5) {                          // a floor under a roof, open now: lit warm (a room's bright, the tone that was approved; a stair's tread or landing its own tone), a lit lip at a step down, shade at the foot of a step up
      float trd = bit(ve, 16.); col = mix(c.rgb * (1.05 + .3 * ls) * vec3(1.1, 1., .82) + vec3(.1, .065, .025) * ls, c.rgb * (1.05 + .2 * ls) * vec3(1.08, 1., .86), trd);
      float ue = min(min(mix(9., lu.y, bit(ve, 512.)), mix(9., 15. - lu.x, bit(ve, 1024.))), min(mix(9., 15. - lu.y, bit(ve, 2048.)), mix(9., lu.x, bit(ve, 4096.))));
      if (ue < 3.) col *= .45 + .15 * floor(ue);
      if ((bit(ve, 1.) > .5 && lu.y < 1.) || (bit(ve, 2.) > .5 && lu.x > 15.) || (bit(ve, 4.) > .5 && lu.y > 15.) || (bit(ve, 8.) > .5 && lu.x < 1.)) col = mix(col, vec3(1., .93, .75), .5);
    } else if (kind < 1.5 && kind > .5 && rim > 0.) {            // a top at a drop: its lip catches the light
      if (bit(ve, 4.) > .5 && lu.y > 15.) col = mix(col, vec3(1., .94, .78), rim * .7);
      if (bit(ve, 1.) > .5 && lu.y < 1.) col *= 1. - rim * .5;
    }
    if (kind > 2.5 && kind < 3.5) {                              // water: the game's own picture of it over a tint (the picture is the clear water, its bed showing: only a little of it over the sea tint)
      vec2 w = (vec2(wp.x, wp.z) * 16. - wv.xy) / wv.zw; vec4 wc = wv.z > 0. ? texture(wt, w) : vec4(0.);
      vec3 sea = vec3(.36, .64, .8) * max(l, .6);
      col = mix(sea, wc.rgb, wc.a * .3);
      if (wtn[4].a > .5) { vec4 tn = wtn[int(clamp(ve, 0., 4.))]; col = mix(tn.rgb * max(l, .6), wc.rgb, wc.a * .45); o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)) * .4), max(tn.a, wc.a * .45)); return; }   // (light.wtint: clear water: a tint and how much of it for water 0..4 levels deep (ve), the bed showing through; the game's picture of the water, its waves and glints, over it)
      o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)) * .4), wa); return;   // (the far sea stays blue to the horizon)
    }
    if (kind > 6.5 && kind < 7.5) col = (texture(t, (vu + vec2(-4., -4.)) / ${AW}.).rgb + texture(t, (vu + vec2(4., -4.)) / ${AW}.).rgb + texture(t, (vu + vec2(-4., 4.)) / ${AW}.).rgb + texture(t, (vu + vec2(4., 4.)) / ${AW}.).rgb) * .25 * kx * max(day, .35);   // (the land past the box: its own tint, flat, in the haze)
    o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye))), 1.);
  }`;
  const SV = `#version 300 es
  in vec3 p; in vec2 uv; in float s; out vec2 vu; out float sil; void main() { gl_Position = vec4(p, 1.); vu = uv; sil = s; }`;
  const SF = `#version 300 es
  precision mediump float; in vec2 vu; in float sil; uniform sampler2D t; uniform vec3 mc; out vec4 o; void main() { vec4 c = texture(t, vu); if (c.a < .5) discard; if (sil > 1.5 && distance(gl_FragCoord.xy, mc.xy) < mc.z && mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.) < 1.) discard; o = sil > .5 && sil < 1.5 ? vec4(.95, .8, .55, .4) : c; }`;   // (sil 2: what stands in front of you: one px in two of it, a 2x2 checker, in a disc round you (mc), so you are seen through it; the rest of it whole)
  return {AW, VS, FS, SV, SF};
})();
