// VOX: the 2.5D look's shaders (vox_style.js draws with them): the land's (VS, FS: every face from the atlas of paints,
// AW px a side; a face's kind says how it is lit: 0 a wall, 1 a top, 2 a terrace of the open pit, 3 water,
// 7 far land, 8 a model's face, 9 a ghost, 10 a shadow) and the sprites' (SV, SF: px for px). No game global.
const VoxStyleGLSL = (() => {
  const AW = 1024;
  const VS = `#version 300 es
  in vec3 p; in vec2 uv; in vec4 a; in float e; uniform mat4 m; uniform vec3 ctr, go; uniform float bend; uniform sampler2D gw; out vec2 vu; out vec4 va, vs; out float ve; out vec3 wp;
  void main() { vec3 q = p; float dn = max(0., ctr.z - 1. - q.z); q.y -= bend * dn * dn; gl_Position = m * vec4(q, 1.); vu = uv; va = a; ve = e; wp = p; vs = vec4(0.);
    if (a.z > .5 && a.z < 1.5 && a.y < .5) { vec2 tl = floor(p.xz - step(8., mod(uv, 16.)) + .5) - go.xy; if (tl.x >= 0. && tl.y >= 0. && tl.x < go.z && tl.y < go.z) vs = texelFetch(gw, ivec2(tl), 0); } }`;   // (vs: the light of your space on this tile (vox_style.js `light`), for a floor under the land: its tile is its corner less where in its paint that corner is)
  const FS = `#version 300 es
  precision mediump float; in vec2 vu; in vec4 va, vs; in float ve; in vec3 wp; uniform sampler2D t, wt; uniform vec3 lamp, eye, fogc, mc;
  uniform vec4 cl, wv, wtn[5]; uniform float wa, dep, lr, day, amb, fn, ff, rim, rd, sun, shp; uniform vec2 rv; out vec4 o;
  float bit(float v, float k) { return mod(floor(v / k), 2.); }
  vec3 cold(vec3 c) { return mix(vec3(dot(c, vec3(.3, .59, .11))), c, .3) * vec3(.74, .82, .96); }   // (not reachable from here: grey-blue)
  void main() {
    float kind = va.z, ck = mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.); vec2 lu = mod(vu, 16.);
    if (!(kind > 6.5 && kind < 7.5) && !(kind > 2.5 && kind < 3.5 && ve > 8.5) && !(kind > 8.5 && kind < 9.5) && (wp.x < cl.x + .001 || wp.x > cl.y - .001 || wp.z < cl.z + .001 || wp.z > cl.w + .001)) discard;   // (cl: the columns and rows of the land asked for: the lists are whole chunks of 8 x 8 tiles (vox_style_land.js), what is outside is left out here; not the far patches, not a ghost)
    if (rv.y != 0. && !(kind > 8.5 && kind < 9.5) && rv.y * (distance(gl_FragCoord.xy, mc.xy) - rv.x + (ck - .5) * 6.) > 0.) discard;   // (rv: a land that takes another's place when the pit changed: for 300 ms both are drawn, the new one inside a ring round you that grows (rv.y 1), the old one outside it (-1), its rim a 2x2 checker; vox_style.js rev)
    bool cov = kind > 7.5 && kind < 8.5 && wp.z >= lamp.z + .3 && wp.y >= lamp.y - .55 && distance(gl_FragCoord.xy, mc.xy + vec2(0., 8.)) < mc.z + 2.;   // (a model's face south of you and over your feet, in the disc round your body)
    if (rd > .5 ? !cov || ck < 1. : cov) discard;   // (what covers you has a hole round you: you and what is behind it are drawn whole there, then (rd) one px in two of it again, 2x2: a checker disc on a roof, a wall, as on a tree (SF). It was the checker laid over you alone: you read as standing on the roof)
    if (kind < 2.5 && bit(ve, 32.) > .5 && ck < 1. && distance(gl_FragCoord.xy, mc.xy) < mc.z * 4.) discard;   // (the wall left south of a pit past its cap: one px in two of it round you)
    vec4 c = texture(t, vu / ${AW}.); if (kind > 7.5 && (c.a < .5 || (kind > 8.5 && kind < 9.5 && ck < 1.))) discard; if (kind > 9.5) { float sa = c.a * 255., rm = sa < 200. && sa > 150. ? 1. : 0., fx = sa > 240. || sa < 176. ? 1. : sun; if (rm != shp || fx < .03) discard; o = vec4(.2, .15, .3, .3 * fx * (1. - .45 * rm)); return; } if (c.a < .5) c = vec4(.42, .32, .25, 1.);   // (8: a model's face, host.models: a bridge's planks; its see-through px are holes; 9: a ghost of one, view.ghosts: one px in two; 10: a shadow on the ground, box.shade: a flat shade laid over the land; its paint's alpha says which: 255 a shade that is always there, 224 the sun's (as dark as sun), 192 the sun's soft rim, 160 a rim that is always there; shp: which are drawn now, 0 the full ones, 1 the rims)
    float d = distance(wp, lamp) / lr, lan = clamp(1.15 - d * d, 0., 1.), ls = floor(lan * 3. + .5) / 3.;
    float kx = floor(va.x * 20. + .05) / 20.;   // (a face's light and the shade of its corners: in whole steps; it ran smooth from corner to corner: a blurred halo on the ground round every block)
    float l = max(va.y * day, amb + (1. - amb) * lan) * kx;
    vec3 col = c.rgb * l * mix(vec3(1.), vec3(1.1, .97, .8), lan * (1. - va.y));
    // under the land's top (a face the sky does not reach: a cave's wall, a face or a terrace of the pit): the day's light at the land's top, level by level down to your lantern's at your floor; never dark
    float up = clamp((va.w - (lamp.y - .6) / .5) / 14., 0., 1.); vec3 pit = mix(vec3(1.14, 1., .82), vec3(max(day * .95, amb)), max(up, 1. - clamp(dep, 0., 1.)));   // (dep: levels of land over you. Under the open sky, a gorge's floor, no lantern: the cut is the block's own material in the day's light. It was warm there too: grey stone cut brown, an earth wall in a stone mountain)
    if (kind > 1.5 && kind < 2.5) { col = c.rgb * pit * (.74 - .04 * mod(floor(va.w / 2.), 2.)) + vec3(.03, .02, .01); if (va.x < .95 && lu.y < 9.) col *= .9; }   // a terrace of the pit, a sliced top: CUT rock, as strata: the material's own paint (earth near the top, stone under it), tops and faces one tone, a band every two levels a little darker, a soft line where a level ends on a face. No rim a tile (it was: a slope read as courses of bricks), no hatch
    else if (kind < .5 && va.y < .5) col = bit(ve, 16.) > .5 ? mix(c.rgb, vec3(.8, .62, .43), .6) * (.95 + .15 * ls) : c.rgb * pit * kx + vec3(.03, .02, .01);   // a wall; the riser of a step you can take: the tread's tone, a wall is rock
    else if (kind < 1.5 && kind > .5 && va.y < .5) {   // a floor under the land, open now. Of YOUR space (vs: how much, 0..1, eased by the painter: a floor that joins your space warms over 300 ms, one that leaves it cools): lit warm, one rule for a room's and a stair's, a lit lip at a step down, shade at a wall's foot.
      // One you cannot walk to from here (a stair's treads over a dead end, a passage past a wall): as it is, at its own height, but cold: grey-blue, no warm light; its lips pale: never the warm lit floor of your space
      float w = abs(mod(va.w + 1024., 256.) - vs.g * 255.) < .5 ? vs.r : 0., dl = clamp(va.w - (lamp.y - .6) / .5 + .5, -4., 6.);
      float ue = min(min(mix(9., lu.y, bit(ve, 512.)), mix(9., 15. - lu.x, bit(ve, 1024.))), min(mix(9., 15. - lu.y, bit(ve, 2048.)), mix(9., lu.x, bit(ve, 4096.))));
      bool lip = (bit(ve, 1.) > .5 && lu.y < 1.) || (bit(ve, 2.) > .5 && lu.x > 15.) || (bit(ve, 4.) > .5 && lu.y > 15.) || (bit(ve, 8.) > .5 && lu.x < 1.);
      float de = min(mix(9., lu.y, bit(ve, 64.)), min(mix(9., 15. - lu.x, bit(ve, 128.)), mix(9., lu.x, bit(ve, 256.))));   // (its edge over a drop of two or more)
      vec3 cc = cold(c.rgb) * 1.15; if (ue < 3.) cc *= ue < 2. ? .45 : .7; if (lip) cc = mix(cc, vec3(.8, .88, 1.), .45);
      vec3 wc = (c.rgb * (1.02 + .2 * ls) * vec3(1.08, 1., .85) + vec3(.04, .025, .01) * ls) * (1. + .05 * dl) * (1. - .22 * vs.b);   // (the floor's own paint under the warm light; a floor is a little lighter each level over yours, darker each level under: a floor two levels up is not the next step; vs.b: one you can only drop to: dimmer)
      if (ue < 7.) wc *= ue < 3. ? .3 : .5 + .1 * floor(ue - 3.); if (lip) wc = mix(wc, vec3(1., .93, .75), .5);   // (the foot of a wall you cannot climb: a dark rim 3 px wide, then its shade 4 px out on your floor: it is seen whichever way the wall faces; a step you can take has the light lip)
      col = mix(cc, wc, w); if (de < 2.) col *= .42;
    } else if (kind < 1.5 && kind > .5 && rim > 0.) {            // a top at a drop: its lip catches the light
      if (bit(ve, 4.) > .5 && lu.y > 15.) col = mix(col, vec3(1., .94, .78), rim * .7);
      if (bit(ve, 1.) > .5 && lu.y < 1.) col *= 1. - rim * .5;
      float dr = min(min(mix(9., lu.y, bit(ve, 64.)), mix(9., 15. - lu.x, bit(ve, 128.))), min(mix(9., lu.x, bit(ve, 256.)), mix(9., 15. - lu.y, bit(ve, 2048.))));
      if (dr < 2.) col = c.rgb * l * (dr < 1. ? .5 : .68);   // (the edge over a drop that hurts, three levels or more: a dark rim two px wide all along it, no light lip: a step down has the lip, a cliff has the rim. A fall of 12 looked like the next terrace)
    } else if (kind < .5 && va.y > .5) col *= 1. - .1 * (bit(ve, 64.) + 2. * bit(ve, 128.));   // (and the cliff's face darker every two levels down)
    if (kind > 2.5 && kind < 3.5) {                              // water: the game's own picture of it over a tint (the picture is the clear water, its bed showing: only a little of it over the sea tint)
      vec2 w = (vec2(wp.x, wp.z) * 16. - wv.xy) / wv.zw; vec4 wc = wv.z > 0. ? texture(wt, w) : vec4(0.);
      vec3 sea = vec3(.36, .64, .8) * max(l, .6);
      col = mix(sea, wc.rgb, wc.a * .3);
      if (wtn[4].a > .5) { vec4 tn = wtn[int(clamp(ve, 0., 4.))]; col = mix(tn.rgb * max(l, .6), wc.rgb, wc.a * .45); o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)) * .4), max(tn.a, wc.a * .45)); return; }   // (light.wtint: clear water: a tint and how much of it for water 0..4 levels deep (ve), the bed showing through; the game's picture of the water, its waves and glints, over it)
      o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye)) * .4), wa); return;   // (the far sea stays blue to the horizon)
    }
    if (kind > 3.5 && kind < 4.5) { if (ck < 1.) discard; col = va.x > .95 ? cold(c.rgb) * 1.12 : mix(cold(c.rgb), vec3(.3, .34, .44), .6); if ((bit(ve, 1.) > .5 && lu.y < 1.) || (bit(ve, 2.) > .5 && lu.x > 15.) || (bit(ve, 4.) > .5 && lu.y > 15.) || (bit(ve, 8.) > .5 && lu.x < 1.)) col = vec3(.84, .9, 1.); }   // the floor over your head (vox_style_land.js slab): cold, one px in two, its tiles edged pale: you are under it
    if (kind > 6.5 && kind < 7.5) col = (texture(t, (vu + vec2(-4., -4.)) / ${AW}.).rgb + texture(t, (vu + vec2(4., -4.)) / ${AW}.).rgb + texture(t, (vu + vec2(-4., 4.)) / ${AW}.).rgb + texture(t, (vu + vec2(4., 4.)) / ${AW}.).rgb) * .25 * kx * max(day, .35);   // (the land past the box: its own tint, flat, in the haze)
    o = vec4(mix(col, fogc, smoothstep(fn, ff, distance(wp, eye))), 1.);
  }`;
  const SV = `#version 300 es
  in vec3 p; in vec2 uv; in float s; out vec2 vu; out float sil; void main() { gl_Position = vec4(p, 1.); vu = uv; sil = s; }`;
  const SF = `#version 300 es
  precision mediump float; in vec2 vu; in float sil; uniform sampler2D t; uniform vec3 mc; out vec4 o; void main() { vec4 c = texture(t, vu); if (c.a < .5) discard; float dm = distance(gl_FragCoord.xy, mc.xy + vec2(0., 8.)); if (sil > 1.5 && dm < mc.z + 2. && mod(floor(gl_FragCoord.x / 2.) + floor(gl_FragCoord.y / 2.), 2.) < 1.) discard; o = sil > .5 && sil < 1.5 ? vec4(.95, .8, .55, .4) : sil > 2.5 ? vec4(mix(c.rgb, vec3(1., .97, .8), .45), 1.) : c; }`;   // (sil 3: a ghost: what would be put, pale)   // (sil 2: what stands in front of you: one px in two of it, 2x2, in a disc round you (mc): you are seen through it and it keeps its shape. It was a whole hole: a tree's crown was gone, a stub at your feet)
  return {AW, VS, FS, SV, SF};
})();
