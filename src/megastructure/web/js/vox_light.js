// VOX: the sun on the land (view.sun, vox_engine.js). Off (no view.sun), every px is as it is without this file.
//   Shadows of the land on the land. The engine keeps the height of every tile it has (a column's highest top) in
//     one picture, a px a tile, laid out as a ring (TOR chunks a side: a chunk's place in it is its own, mod TOR; a
//     chunk let go of is wiped from it). A px of a face asks: from here toward the sun, a level up for every
//     sun.dir px of ground, tile by tile (each tile the line crosses, exactly: no steps to miss a block), is a tile
//     higher than the line where it comes into it? Then it is in shadow: sun.shade over it, sun.alpha of it, once
//     (two shadows that cross are not darker). In whole px of paint, so a shadow's edge is the land's own grid.
//     A top, the water and a model's faces ask from where they are. A wall's side that faces away from the sun is
//     in its own shadow (a wall of two levels or more); one that faces it asks from the foot of the wall. A front (it faces south, and the sun
//     is never south) only asks sideways: what stands west or east of it in its row.
//     What is under a roof (a cave's floor) has no sun and no shadow.
//   Clouds' shadows (sun.cloud): see `cloud` below.
//     sun.land false: none of this (the shadows of what stands still fall as below).
//   Shadows of what stands (sun.cast): the user of the engine hands a picture of the flat view (sun.castAt: {x, y, scale}:
//     its corner in the view and how many px of the screen a px of it is; left out: it is the view's size), in which the
//     shadow of each thing lies flat on the level its foot is on, and that level is written in the px (the level +
//     32768: its low four bits in red's high four, the next four in green's: a px half there still says its level;
//     alpha: a quarter or more: there is one). A top takes the shadow that lies on its own level
//     where it is; and, going up its line to the sun, the shadow lying on a higher level where the line crosses
//     that level (the shadow of a tree on a cliff's edge falls down the cliff to here); and the shadow lying on a
//     lower level where it goes on under this land (what stands at the foot of a step is taller than the step: the
//     shadow of its upper part is on the step's top). So a shadow never lies on a wall as on flat ground, drops off
//     an edge and climbs a step. sun.castLevels [lowest, highest]: the levels written in the picture (none other
//     is looked for).
//   Land in the water (sun.glass): a water px shows the front of the land north of it turned over about its
//     foot, each row slid as the ripple says, sun.glass.alpha of it over the water.
// The picture of sun.cast is of the FLAT view (no curve: vFlat, where a px would be with none), so the bend of a
// curved view (vox_curve.js) needs nothing here: a shadow is squeezed with the row it lies on, as its paint is.
const VoxLight = (() => {
  const TOR = 16;
  // (vGround: where the px is, px of paint in the ring, and its height in px; vFlat: on the screen, were it flat)
  const FS = `
uniform sampler2D uTops, uCast; uniform vec4 uSun, uGlass, uCloud; uniform vec3 uCastAt, uShade; uniform vec2 uCastLv, uCloudO; uniform float uTor, uTopMax, uCastOn, uRip, uLo, uLand, uFire, uDepth;
// (vGround: the engine's, vox_engine.js: in the roll, read at the middle of a px of paint)
bool inShade;                                                  // (lit: this px is in a shadow: no cloud's shadow on it too)
vec4 tileAt(vec2 tile) { return texelFetch(uTops, ivec2(mod(tile, uTor)), 0); }
float high(vec4 h) { return floor(h.r * 255. + .5) + floor(h.g * 255. + .5) * 256. - 32768.; }
float topAt(vec2 tile, out float wet) { vec4 h = tileAt(tile); wet = h.b; return high(h); }
// is the spot p (tiles) of a tile under its top's cap? (its shape: the px it leaves empty at its south end and its sides)
bool capped(vec2 p, vec2 tile, float id) { vec2 l = clamp((p - tile) * uCell, 0., uCell - .01); return l.y < uCell - texelFetch(uFoot, ivec2(int(l.x), int(id)), 0).r * 255.; }
// from p (tiles) at level z0 toward the sun (d: tiles a level up): does the land stand in the way?
// A block's top level is its cap's shape (rounded corners, sides set in), under it the whole square. All land that
// stands over the line throws a shadow, a step of one level as a wall does (as long as its height says: a terrace
// reads as a step). One walk for all of it: a shadow is one shape along a riser and round its corners.
// (-> the top of the land in the way, levels; none: far under)
float block(vec2 p, float z0, vec2 d) {
  if (z0 >= uTopMax) return -1e5;
  vec2 tile = floor(p), st = sign(d), inv = 1. / max(abs(d), 1e-6), tm = mix(p - tile, tile + 1. - p, step(0., d)) * inv;
  for (int i = 0; i < 20; i++) {
    float t;
    if (tm.x < tm.y) { t = tm.x; tm.x += inv.x; tile.x += st.x; } else { t = tm.y; tm.y += inv.y; tile.y += st.y; }
    if (z0 + t >= uTopMax) return -1e5;
    vec4 at = tileAt(tile); float h = high(at), id = floor(at.a * 255. + .5), t1 = min(h - z0, min(tm.x, tm.y));
    if (h <= z0 + t + .02) continue;
    if (id > 0. && z0 + t > h - 1. && !capped(p + d * (t + .001), tile, id) && !capped(p + d * (t + t1) * .5, tile, id) && !capped(p + d * (t1 - .001), tile, id)) continue;
    return h;
  }
  return -1e5;
}
bool shaded(vec2 p, float z0, vec2 d) { return block(p, z0, d) > -1e4; }
// the shadow of what stands, lying on level L, where the px's line to the sun is t levels on: 0 none, 1 the sun's, 2 a fire's
float lies(float L, float t) {
  vec2 q = vFlat - vec2(uSun.x * t * uUp, uSun.y * t * uUp + t * uUp) * uK, at = (q - uCastAt.xy) / (vec2(textureSize(uCast, 0)) * uCastAt.z);      // (on the flat picture)
  if (at.y < 0. || at.x < 0. || at.x > 1. || at.y > 1.) return 0.;      // (north of the picture: none there, not its edge's)
  vec4 s = texture(uCast, at);
  return s.a > .25 && floor(s.rg * 255. / 16.) == vec2(mod(L + 32768., 16.), mod(floor((L + 32768.) / 16.), 16.)) ? (s.b < .7 ? 2. : 1.) : 0.;
}
// (lip: a top's px that is its wall, the top of its front: 0 or more, the px it is under the top's last)
// (plain: its colour before the host's own shadow at a wall's foot was laid on it: the sun's shadow is laid on that, once)
vec3 lit(vec3 c, vec3 plain, int kind, int bits, float lip) {
  if (uSun.w < .5 || ((bits & 8) != 0 && kind < 2)) return c;
  vec2 g = (floor(vGround.xy) + .5) / uCell, d = -uSun.xy * uUp / uCell; float z0 = vGround.z / uUp, far = uCell - .01;
  // (a top, the water: a px that goes on under the block beside it, at that wall's foot, is asked for at the nearest edge
  // of that block's tile with land no higher past it: whichever tile draws the px, the same answer. Each asked at its own
  // tile's edge: two tops drawn at one depth round a corner did not agree, a shadow's end in lines a third of a px thin)
  if (kind == 0 || kind == 2) { vec2 rt = floor(g), l = floor((g - rt) * uCell), e = vec2(.5 / uCell, 0.); float L0 = ceil(z0 - .01), best = 99.;
    if (high(tileAt(rt)) > L0) { vec2 q = g;
      if (high(tileAt(rt + vec2(0., 1.))) <= L0) { best = uCell - l.y; q = vec2(g.x, rt.y + 1. + e.x); }
      if (l.x + 1. < best && high(tileAt(rt - vec2(1., 0.))) <= L0) { best = l.x + 1.; q = vec2(rt.x - e.x, g.y); }
      if (uCell - l.x < best && high(tileAt(rt + vec2(1., 0.))) <= L0) { best = uCell - l.x; q = vec2(rt.x + 1. + e.x, g.y); }
      if (l.y + 1. < best && high(tileAt(rt - vec2(0., 1.))) <= L0) q = vec2(g.x, rt.y - e.x);
      g = q; } }
  if (kind == 2 && uGlass.x > 0.) {                             // the land north of the water, in it
    vec2 at = vec2(floor(vGround.x) + .5 - floor(sin(floor(vGround.y) * uGlass.y + uRip) * uGlass.w + .5), floor(vGround.y) + .5), tile = floor(at / uCell);
    for (int k = 1; k <= 5; k++) {
      float wet, h = topAt(tile - vec2(0., float(k)), wet), dd = at.y - (tile.y - float(k) + 1.) * uCell;
      if (wet > .5 || h <= 0. || dd >= h * uUp) continue;
      float strip = clamp(floor(dd / uUp) + 1., uLo, uLo + uStrips - 1.) - uLo, r = uUp - 1. - floor(mod(dd, uUp));
      // (fainter than what stands is seen in it, and fainter still on the rows the ripple slides: bands, not a slab)
      c = mix(c, texture(uFronts, vec2(clamp(mod(at.x, uCell), .01, far) / (uVars * uCell), (strip * uUp + r + .5) / (uStrips * uUp))).rgb, uGlass.x * (at.x == floor(vGround.x) + .5 ? .5 : .25));
      break;
    }
  }
  if (uSun.z <= 0. && uFire <= 0.) return c;
  if (kind == 2) plain = c;
  float much = uSun.z, w;
  bool dark = false, front = kind == 1 || kind == 4, flat_ = kind == 0 || kind == 2; vec2 gt = g; float zt = z0;      // (gt, zt: as a top, for the shadows of what stands: a top's lip takes them as its top does, to the tile's end)
  if (lip >= 0.) { front = true; kind = 1; g.y = ceil(g.y) + .5 / uCell; z0 -= (lip + .5) / uUp; d.y = 0.; }
  else if (front) { g.y = (floor(vGround.y + .5) + .5) / uCell; z0 = (floor(vGround.z) + .5) / uUp; d.y = 0.;
    if (kind == 1) g.y = ceil(g.y - (uInset + 1.) / uCell) + .5 / uCell; }      // (a front stands uInset px in from its tile's edge: asked for in the row at its foot, as a lip is: the wall's own tiles beside it are not in its way)
  // (a front's px in a column where higher land stands at its foot, a wall's inner corner: asked for from beside that land,
  // on its open side: in its shadow with the sun behind it. It was a lit strip two px wide down the corner, inside the shadow)
  if (front && kind != 4) { vec2 rt = floor(g); float top = z0 + .02;
    if (high(tileAt(rt)) > top) { bool we = high(tileAt(rt - vec2(1., 0.))) <= top, ea = high(tileAt(rt + vec2(1., 0.))) <= top;
      if (we && (!ea || g.x - rt.x < .5)) g.x = rt.x - .5 / uCell; else if (ea) g.x = rt.x + 1. + .5 / uCell; } }
  if ((kind == 3 || kind == 4) && uLand > .5) {                 // (a wall's side, and the fronts of its banks: one face)
    bool east = (bits & (kind == 3 ? 1 : 32)) != 0;
    if (abs(uSun.x) > .2 && (uSun.x > 0.) == east) dark = true;      // (it faces away: in its own shadow, a step's side as a wall's)
    // (from the foot of its wall: past its own tile's edge only if the px is in the wall's tile. A bank's px out over the open
    // tile beside it was asked for a tile further, inside the next wall of a narrow way: dark dashes down the lit side)
    else if (high(tileAt(floor(g))) > z0 + .02) g.x = east ? floor(g.x) + 1. + .5 / uCell : floor(g.x) - .5 / uCell;
  }
  // (a front: by the ground at its foot: in the shadow that lies there, as high as what throws it stands. A band straight up
  // the wall: asked for at each px's own height it was a wedge widening down every cliff beside a corner)
  if (!dark && uLand > .5 && uSun.z > 0.) { dark = front && kind == 1 ? block(g, min(z0, high(tileAt(floor(g)))), d) > z0 : shaded(g, z0, d); if (dark && kind == 2) much *= .5; }      // (the land's shadow on water: half, the water shows the land in it there)
  if (!dark && uCastOn > .5) {
    float by = 0.;
    if (kind == 7) by = texture(uCast, (vFlat - uCastAt.xy) / (vec2(textureSize(uCast, 0)) * uCastAt.z)).a > .25 ? 1. : 0.;
    else if ((kind == 3 || (kind == 4 && (uSun.x > 0.) != ((bits & 32) != 0))) && uLand > .5) {      // a wall's side that faces the sun (its banks' tops and fronts): the shadow lying at its foot goes on up it
      float L = topAt(floor(g), w);
      if (L < z0 + .01 && L >= uCastLv.x && L <= uCastLv.y) by = lies(L, L - z0) == 1. ? 1. : 0.;
    } else if (flat_) for (int i = -3; i < 7 && by == 0.; i++) {
      float L = ceil(zt - .01) + float(i);
      if (L < uCastLv.x) continue;
      if (L > uCastLv.y) break;
      // (a level under this one: only the shadow that goes on under this land, the upper part of what stands at a wall's foot)
      if (i < 0 && topAt(floor(gt + uSun.xy * uUp / uCell * float(-i)), w) <= L) continue;
      by = lies(L, L - zt);
      if (by == 2. && i != 0) by = 0.;                           // (a fire's: on its own level only)
    }
    // (none found on a top: the sun's shadow lying a level under or over, where it is: across a step of one level a shadow
    // goes on as on flat ground. A body's on a stair was there and not there as it climbed)
    if (by == 0. && flat_) { float L = ceil(zt - .01); for (float k = -1.; k < 2. && by == 0.; k += 2.) if (L + k >= uCastLv.x && L + k <= uCastLv.y && lies(L + k, 0.) == 1.) by = 1.; }
    if (by > 0.) { dark = true; if (by == 2.) much = uFire; }
  }
  inShade = dark && much > 0.;
  return inShade ? mix(plain, uShade, much) : c;
}
// The clouds' shadows (uCloud: how dark, and how far they have drifted). They lie on the land at its height, where
// the sun's line through the px meets the ground's level 0: a cloud's edge breaks at a cliff as a shadow does. None
// under a roof, none on what is in a shadow already (a shadow is dark once). The field is made of whole numbers'
// hashes, so VoxLight.cloud (for what stands on the land: it is as dark as the ground at its foot) is the same one.
float chash(ivec2 q) { uint n = uint(q.x) * 374761393u + uint(q.y) * 668265263u; n = (n ^ (n >> 13u)) * 1274126177u; return float((n ^ (n >> 16u)) & 65535u) / 65535.; }
float cnoise(vec2 q) { ivec2 i = ivec2(floor(q)); vec2 f = fract(q); f = f * f * (3. - 2. * f);
  return mix(mix(chash(i), chash(i + ivec2(1, 0)), f.x), mix(chash(i + ivec2(0, 1)), chash(i + ivec2(1, 1)), f.x), f.y); }
// (px: the px of paint on the ground. Two shades, none and the cloud's, and one px in two between them: a cloud's
// shadow has an edge of whole px, as every shadow has. Few and small, as the sky's clouds are: it was half the land in nested rings)
// (par: which px of two is the darker at an edge: counted on the face itself. Counted on the ground under the sun's line
// it was slanted stripes down a front, whose rows are not the ground's)
float cloud(vec2 px, float par) { vec2 w = px / uCell * .055 + uCloud.yz; float s = smoothstep(.57, .63, cnoise(w) * .55 + cnoise(w * 2.1 + 7.3) * .3 + cnoise(w * 4.3 + 1.7) * .15);
  return floor(s + (mod(par, 2.) < .5 ? .67 : .33)) * uCloud.x; }
// The land's depth (uDepth: on), with or without the sun: each a multiply of the land's own paint, never another paint.
//   Height as light: a level of the world a little brighter and warmer than the one under it, from level 0 (as it is
//     painted) up to level 4 (no more: high stone went to white), and under level 0 darker and cooler down to four levels (a deep pit's floor is darker than a shallow one's); a wall's front by the height of each of its px, so it darkens down to its foot a level at
//     a time, as its sheet's bands go. By the world's height, not the eye's: nothing changes as you climb.
//   A face's side: a front (it faces south) a little darker than a top; a wall's side that faces west or east lighter
//     toward the sun and darker away from it, by how far to that side the sun is (none at noon): all of a side one face.
//   Contact shade: the ground at the foot of higher land north, west or east of it darker for two px (the higher the
//     wall the darker; west and east: from the foot of the wall's bank), an inner corner darker still.
// Under a roof only the height; not the water (it is the sky's), not what floats. contact: with the shade (a px in a shadow has
// none: a shadow is dark once).
const float NB = 3.;                                            // (the band behind a step: px north of the higher top's edge it starts)
const vec3 FRONT = vec3(.88, .89, .93);                           // a front: the side of the land turned to the eye, a little darker than a top
// (a front under a roof: the cave's dark is laid on that, so that a wall in the dark is darker than the same wall in the day's light: the engine's own lines)
vec3 roofed(vec3 c, int kind) { return uDepth > .5 && kind == 1 ? c * FRONT : c; }
// (a foot's shade: two px of one tone: it was three px of three tones, soft stripes)
float chk;
float sh(float d) { return d < 2. ? .3 : 0.; }
vec3 deep(vec3 c, int kind, int bits, float lip, bool contact) {
  if (uDepth < .5 || kind == 2 || kind > 4) return c;
  float z = vGround.z / uUp, w, lv = kind == 0 ? ceil(z - .01) : floor(z + .01), up = clamp(lv, 0., 4.), down = clamp(-lv, 0., 4.);
  if ((bits & 8) != 0) down = 0.;                               // (under a roof the place has its own dark: darker again by its depth, a floor was the colour of the earth cut round it)
  c *= (vec3(1.) + vec3(.013, .012, .009) * up) * (vec3(1.) - vec3(.05, .05, .042) * down);
  if (!contact || (bits & 128) != 0 || ((bits & 8) != 0 && kind < 2)) return c;      // (under a roof: its height only, no side to the sun, no shade at a foot: the place has its own dark)
  if (kind == 1 || (kind == 0 && lip >= 0.)) return c * FRONT;      // (a front, and a top's own lip of wall)
  if (kind > 2) { float s = clamp(((bits & (kind == 3 ? 1 : 32)) != 0 ? -uSun.x : uSun.x) * 2.5, -1., 1.); return c * (s > 0. ? vec3(1. + .05 * s) : vec3(1.) + vec3(.22, .21, .15) * s); }
  vec2 tile = floor((vGround.xy - vLoc + 8.) / uCell + .5), l = floor(vLoc - 8.);
  chk = mod(l.x + l.y, 2.) < .5 ? 1. : 0.;
  float L = ceil(z - .01), a = 0., n = topAt(tile + vec2(0., -1.), w) - L, we = topAt(tile + vec2(-1., 0.), w) - L, ea = topAt(tile + vec2(1., 0.), w) - L;
  // (px from the wall's foot: a front's foot is uInset px in from its tile's edge, and so are its two ends where the wall ends)
  float dn = l.y + uInset, dw = (bits & 2) != 0 ? l.x - (vMore.x - 8.) : l.x + uInset, de = (bits & 4) != 0 ? uCell - 1. - l.x - (vMore.y - 8.) : uCell - 1. - l.x + uInset;
  // (a px that goes on under a wall, round the corner of its foot, is drawn by the tile on the corner's other side too,
  // at the same depth: there neither takes any, so the two are one colour as they are painted)
  float nw = topAt(tile + vec2(-1., -1.), w) - L, ne = topAt(tile + vec2(1., -1.), w) - L, T = uCell - 6.;
  bool ends = (l.x < uInset && we <= 0. && nw <= 0.) || (l.x >= uCell - uInset && ea <= 0. && ne <= 0.);
  if ((l.y < 0. && ((l.x < 6. && nw <= 0.) || (l.x >= T && ne <= 0.))) || (l.x < 0. && ((l.y < 6. && nw <= 0.) || (l.y >= T && topAt(tile + vec2(-1., 1.), w) <= L)))
    || (l.x >= uCell && ((l.y < 6. && ne <= 0.) || (l.y >= T && topAt(tile + vec2(1., 1.), w) <= L)))) return c;
  if (n > 0. && dn < 3. && !ends) a = (.75 + .25 * min(n, 3.)) * sh(dn);
  bool low = l.y >= uCell - uInset;                             // (a wall's side ends uInset px short of its tile's south edge, where no wall goes on south of it)
  if (we > 0. && dw < 3. && !(low && topAt(tile + vec2(-1., 1.), w) <= L)) a = max(a, (.75 + .25 * min(we, 3.)) * sh(dw)) + min(a, .08);
  if (ea > 0. && de < 3. && !(low && topAt(tile + vec2(1., 1.), w) <= L)) a = max(a, (.75 + .25 * min(ea, 3.)) * sh(de)) + min(a, .08);
  // (seen from behind, a terrace: the ground a step under a higher top, just north of where that top hides it: two px of
  // the same shade, short of the step's ends. Only a step of one level: beyond a pillar or a cliff it was a bar in the air)
  float r = l.y - (uCell - uUp - 3.) - NB;
  if (r >= 0. && r < 2. && l.x >= 0. && l.x < uCell && abs(topAt(tile + vec2(0., 1.), w) - L - 1.) < .5) {
    float in_ = min(topAt(tile + vec2(-1., 1.), w) - L < .5 ? l.x : 99., topAt(tile + vec2(1., 1.), w) - L < .5 ? uCell - 1. - l.x : 99.);
    if (in_ >= 6. || (in_ >= 4. && chk > .5)) a = max(a, .22);
  }
  return c * mix(vec3(1.), vec3(.55, .55, .62), min(a, .6));      // (two walls' shade is the darker of the two and a little more in their corner, not their sum: a narrow trench's floor is not a slab of grey)
}
vec3 sunlit(vec3 c, vec3 plain, int kind, int bits, float lip) {
  c = deep(c, kind, bits, lip, true); plain = deep(plain, kind, bits, lip, false);
  vec3 lone = c; inShade = false; c = lit(c, plain, kind, bits, lip);
  if (uCloud.x <= 0. || ((bits & 8) != 0 && kind < 2)) return c;
  // (in a shadow under a cloud: the darker of the two, not both. With no cloud on it a cliff's shadow was a lighter wedge on the cloud's)
  lone *= mix(vec3(1.), vec3(.74, .78, .9), cloud(floor(vGround.xy - uSun.xy * max(vGround.z, 0.)) + uCloudO * uCell, kind == 1 || kind == 4 ? floor(vGround.x) + floor(vGround.z) : kind == 3 ? floor(vGround.y) + floor(vGround.z) : floor(vGround.x) + floor(vGround.y)));
  return inShade ? min(c, lone) : lone;
}`;
  function create(cfg) {
    const N = cfg.size, side = TOR * N, slots = new Map(), blank = new Uint8Array(N * N * 4);
    let tex = null, cast = null;
    const slot = (cx, cy) => (((cy % TOR) + TOR) % TOR) * TOR + ((cx % TOR) + TOR) % TOR;
    // A chunk's heights, made with its faces: a tile's highest top (+ 32768, low byte first), blue: water, alpha: that top's shape
    function tops(ch, host) {
      const px = ch.tops || (ch.tops = new Uint8Array(N * N * 4)); let most = -1e9;
      for (let ly = 0, i = 0; ly < N; ly++) for (let lx = 0; lx < N; lx++, i += 4) {
        const x = ch.cx * N + lx, y = ch.cy * N + ly, c = host.column(x, y), wet = !!c && host.water(x, y), v = c ? (wet ? 0 : c[c.length - 1]) + 32768 : 0;
        px[i] = v & 255; px[i + 1] = v >> 8; px[i + 2] = wet ? 255 : 0; px[i + 3] = c && !wet ? host.shape(x, y, c[c.length - 1]) : 0;
        if (c) most = Math.max(most, v - 32768);
      }
      ch.most = most; ch.lit = false;
    }
    function put(gl, s, px) { gl.texSubImage2D(gl.TEXTURE_2D, 0, (s % TOR) * N, (s / TOR | 0) * N, N, N, gl.RGBA, gl.UNSIGNED_BYTE, px); }
    function drop(ch) { const s = slot(ch.cx, ch.cy); if (slots.get(s) === ch) slots.set(s, null); }
    // Before a frame's chunks. chunks: all the engine has; v: the view
    function frame(gl, u, v, chunks) {
      const sun = v.sun || null;
      gl.uniform4f(u.uSun, sun ? sun.dir[0] : 0, sun ? sun.dir[1] : 0, sun ? sun.alpha : 0, sun ? 1 : 0);
      gl.uniform1i(u.uTops, 7); gl.uniform1i(u.uCast, 8); gl.uniform1f(u.uDepth, sun && sun.depth ? 1 : 0);
      if (!sun) return;
      gl.activeTexture(gl.TEXTURE7);
      if (!tex) {
        tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, side, side, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(side * side * 4));
        for (const [k, val] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, val);
      }
      gl.bindTexture(gl.TEXTURE_2D, tex);
      let most = -1e9;
      for (const [s, ch] of slots) if (ch === null) { put(gl, s, blank); slots.delete(s); }      // (let go of: wiped)
      for (const ch of chunks.values()) if (ch.tops) {
        const s = slot(ch.cx, ch.cy);
        if (slots.get(s) !== ch || !ch.lit) { put(gl, s, ch.tops); slots.set(s, ch); ch.lit = true; }
        most = Math.max(most, ch.most);
      }
      gl.uniform3f(u.uShade, sun.shade[0], sun.shade[1], sun.shade[2]); gl.uniform1f(u.uTor, side); gl.uniform1f(u.uTopMax, most); gl.uniform1f(u.uLo, cfg.levels[0]);
      const glass = sun.glass && sun.glass.alpha > 0 ? sun.glass : null;
      gl.uniform4f(u.uGlass, glass ? glass.alpha : 0, glass ? glass.wave : 0, 0, glass ? glass.ripple : 0);
      gl.uniform1f(u.uCastOn, sun.cast ? 1 : 0); gl.uniform1f(u.uLand, sun.land === false ? 0 : 1); gl.uniform1f(u.uFire, sun.fire || 0);
      const cl = sun.cloud || null; gl.uniform4f(u.uCloud, cl ? cl.k : 0, cl ? cl.drift[0] : 0, cl ? cl.drift[1] : 0, 0);
      if (sun.cast) {
        const a = sun.castAt || {x: 0, y: 0, scale: v.w / sun.cast.width}; gl.uniform3f(u.uCastAt, a.x, a.y, a.scale);
        const lv = sun.castLevels || [-1e4, 1e4]; gl.uniform2f(u.uCastLv, lv[0], lv[1]);
        gl.activeTexture(gl.TEXTURE8); cast = cast || gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, cast);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, sun.cast);
        for (const [k, val] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, val);
      }
    }
    // Before a chunk's faces: where it is in the ring (px of paint), and the ripple's place at its rows
    function at(gl, u, v, cx, cy) {
      const T = N * cfg.cell, g = v.sun && v.sun.glass;
      gl.uniform2f(u.uTorO, (((cx % TOR) + TOR) % TOR) * T, (((cy % TOR) + TOR) % TOR) * T); gl.uniform2f(u.uCloudO, Math.floor(cx / TOR) * TOR * N, Math.floor(cy / TOR) * TOR * N);
      if (g) gl.uniform1f(u.uRip, (g.phase + Math.floor(cy / TOR) * TOR * T * g.wave) % (Math.PI * 2));
    }
    return {tops, drop, frame, at};
  }
  // The clouds' field as the land has it (the GLSL above, number for number): how dark a cloud's shadow is on the
  // ground at (x, y), tiles; c: the view's sun.cloud
  const hash = (x, y) => { let n = (Math.imul(x, 374761393) + Math.imul(y, 668265263)) >>> 0; n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0; return ((n ^ (n >>> 16)) & 65535) / 65535; };
  function noise(x, y) {
    const ix = Math.floor(x), iy = Math.floor(y), s = (v) => v * v * (3 - 2 * v), fx = s(x - ix), fy = s(y - iy), a = hash(ix, iy), b = hash(ix, iy + 1);
    return a + (hash(ix + 1, iy) - a) * fx + (b + (hash(ix + 1, iy + 1) - b) * fx - a - (hash(ix + 1, iy) - a) * fx) * fy;
  }
  function cloud(c, x, y, cell) {
    const px = Math.floor(x * cell), py = Math.floor(y * cell), wx = px / cell * .055 + c.drift[0], wy = py / cell * .055 + c.drift[1];
    const n = noise(wx, wy) * .55 + noise(wx * 2.1 + 7.3, wy * 2.1 + 7.3) * .3 + noise(wx * 4.3 + 1.7, wy * 4.3 + 1.7) * .15, q = Math.max(0, Math.min(1, (n - .57) / .06));
    return Math.floor(q * q * (3 - 2 * q) + ((((px + py) % 2) + 2) % 2 < .5 ? .67 : .33)) * c.k;
  }
  return {create, FS, TOR, cloud};
})();
