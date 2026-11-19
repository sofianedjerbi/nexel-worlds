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
uniform sampler2D uTops, uCast; uniform vec4 uSun, uGlass; uniform vec3 uCastAt; uniform vec2 uCastLv; uniform vec3 uShade; uniform float uTor, uTopMax, uCastOn, uRip, uLo, uLand;
in vec3 vGround;
float topAt(vec2 tile, out float wet) { vec4 h = texelFetch(uTops, ivec2(mod(tile, uTor)), 0); wet = h.b; return floor(h.r * 255. + .5) + floor(h.g * 255. + .5) * 256. - 32768.; }
// from p (tiles) at level z0 toward the sun (d: tiles a level up): does the land stand in the way?
bool shaded(vec2 p, float z0, vec2 d) {
  if (z0 >= uTopMax) return false;
  vec2 tile = floor(p), st = sign(d), inv = 1. / max(abs(d), 1e-6), tm = mix(p - tile, tile + 1. - p, step(0., d)) * inv;
  for (int i = 0; i < 20; i++) {
    float t, w;
    if (tm.x < tm.y) { t = tm.x; tm.x += inv.x; tile.x += st.x; } else { t = tm.y; tm.y += inv.y; tile.y += st.y; }
    if (z0 + t >= uTopMax) return false;
    if (topAt(tile, w) > z0 + t + .02) return true;
  }
  return false;
}
// (lip: a top's px that is its wall, the top of its front: 0 or more, the px it is under the top's last)
// (plain: its colour before the host's own shadow at a wall's foot was laid on it: the sun's shadow is laid on that, once)
vec3 sunlit(vec3 c, vec3 plain, int kind, int bits, float lip) {
  if (uSun.w < .5 || ((bits & 8) != 0 && kind < 2)) return c;
  vec2 g = (floor(vGround.xy) + .5) / uCell, d = -uSun.xy * uUp / uCell; float z0 = vGround.z / uUp, far = uCell - .01;
  // (a top, the water: a px that goes on under the block beside it is asked for at its own tile's edge: at that wall's foot)
  if (kind == 0 || kind == 2) g = (vGround.xy - vLoc + 8. + clamp(floor(vLoc - 8.) + .5, vec2(.5), vec2(uCell - .5))) / uCell;
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
  if (uSun.z <= 0.) return c;
  if (kind == 2) plain = c;
  float much = uSun.z;
  bool dark = false, front = kind == 1 || kind == 4, lies = kind == 0 || kind == 2; vec2 gt = g; float zt = z0;      // (gt, zt: as a top, for the shadows of what stands: a top's lip takes them as its top does, to the tile's end)
  if (lip >= 0.) { front = true; kind = 1; g.y = ceil(g.y) + .5 / uCell; z0 -= (lip + .5) / uUp; d.y = 0.; }
  else if (front) { g.y = (floor(vGround.y + .5) + .5) / uCell; z0 = (floor(vGround.z) + .5) / uUp; d.y = 0.; }
  if (kind == 3 && uLand > .5) {
    bool east = (bits & 1) != 0;
    if (abs(uSun.x) > .2 && (uSun.x > 0.) == east && (bits & 2) != 0) dark = true;      // (a wall of one level shows too little of its side: it stays as painted)
    else g.x = east ? floor(g.x) + 1. + .5 / uCell : floor(g.x) - .5 / uCell;
  }
  if (!dark && uLand > .5) { dark = shaded(g, z0, d); if (dark && kind == 2) much *= .5; }      // (the land's shadow on water: half, the water shows the land in it there)
  if (!dark && uCastOn > .5 && (lies || kind == 7)) {
    vec2 size = vec2(textureSize(uCast, 0)) * uCastAt.z;
    if (kind == 7) dark = texture(uCast, (vFlat - uCastAt.xy) / size).a > .25;
    else for (int i = -3; i < 7; i++) {
      float L = ceil(zt - .01) + float(i), t = L - zt, w;
      if (L < uCastLv.x) continue;
      if (L > uCastLv.y) break;
      // (a level under this one: only the shadow that goes on under this land, the upper part of what stands at a wall's foot)
      if (i < 0 && topAt(floor(gt + uSun.xy * uUp / uCell * float(-i)), w) <= L) continue;
      vec2 q = vFlat - vec2(uSun.x * t * uUp, uSun.y * t * uUp + t * uUp) * uK;      // (on the flat picture: where the point that far along the line is)
      vec2 at = (q - uCastAt.xy) / size; if (at.y < 0. || at.x < 0. || at.x > 1. || at.y > 1.) continue;      // (north of the picture: none there, not its edge's)
      vec4 s = texture(uCast, at);
      if (s.a > .25 && floor(s.rg * 255. / 16.) == vec2(mod(L + 32768., 16.), mod(floor((L + 32768.) / 16.), 16.))) { dark = true; break; }
    }
  }
  return dark ? mix(plain, uShade, much) : c;
}`;
  function create(cfg) {
    const N = cfg.size, side = TOR * N, slots = new Map(), blank = new Uint8Array(N * N * 4);
    let tex = null, cast = null;
    const slot = (cx, cy) => (((cy % TOR) + TOR) % TOR) * TOR + ((cx % TOR) + TOR) % TOR;
    // A chunk's heights, made with its faces: a tile's highest top (+ 32768, low byte first), blue: water
    function tops(ch, host) {
      const px = ch.tops || (ch.tops = new Uint8Array(N * N * 4)); let most = -1e9;
      for (let ly = 0, i = 0; ly < N; ly++) for (let lx = 0; lx < N; lx++, i += 4) {
        const x = ch.cx * N + lx, y = ch.cy * N + ly, c = host.column(x, y), wet = !!c && host.water(x, y), v = c ? (wet ? 0 : c[c.length - 1]) + 32768 : 0;
        px[i] = v & 255; px[i + 1] = v >> 8; px[i + 2] = wet ? 255 : 0; px[i + 3] = 255;
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
      gl.uniform1i(u.uTops, 7); gl.uniform1i(u.uCast, 8);
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
      gl.uniform1f(u.uCastOn, sun.cast ? 1 : 0); gl.uniform1f(u.uLand, sun.land === false ? 0 : 1);
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
      gl.uniform2f(u.uTorO, (((cx % TOR) + TOR) % TOR) * T, (((cy % TOR) + TOR) % TOR) * T);
      if (g) gl.uniform1f(u.uRip, (g.phase + Math.floor(cy / TOR) * TOR * T * g.wave) % (Math.PI * 2));
    }
    return {tops, drop, frame, at};
  }
  return {create, FS, TOR};
})();
