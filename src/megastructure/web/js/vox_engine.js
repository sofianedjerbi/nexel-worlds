// VOX: the engine. `Vox.create(host, cfg)` gives a world of blocks to draw.
//
//   host, what the user of the engine knows and the engine asks for:
//     column(x, y)  -> a tile's column of cells, or null where the world is not known. A column is the heights
//                      where it changes, from the bottom: solid up to c[0], empty up to c[1], solid up to c[2]...
//     water(x, y)   -> is this tile water (one face at height 0)
//     paintTop(x, y, z, px, at, stride)  paint the top of the tile's cell z: cfg.cell x cfg.cell px into px
//                      (a Uint32 a px), its first px at `at`, a row `stride` px on. The lip of a block is the
//                      host's to paint here. A px left see-through shows what is behind: the land round a
//                      rounded corner, the water on a shore. Asked for a water tile too (z 0): what floats on it
//     paintFront(z, v, px, at, stride)   paint a front (a south face) of a cell at level z, its variant v of
//                      cfg.variants: cfg.cell px across, cfg.up px tall, into px as paintTop does
//     shape(x, y, z) -> the shape of the tile's cell z, a number under 256 (0: the whole square), and
//     profile(id)   -> that shape: for each px across, how many px the block leaves empty at its south end
//                      (cfg.cell: that px across has none of it). paintTop leaves the same px see-through
//     lip(id)       -> (if it has it) that shape's lip: for each px across, how many px at its south end are not the
//                      top's ground but the wall under it (paintTop paints the wall's first px there): the sun takes
//                      them for the wall
//     band(z)       -> px the level z of a wall that faces west or east stands out under the level over it (its
//                      bank; 0: none)
//     side(z)       -> the colours of a wall's level z that faces west or east: {band: [r, g, b] its bank's top,
//                      body: [r, g, b] its bank's front, foot: [r, g, b] the line at a wall's foot,
//                      shadow: [r, g, b, a] the shadow at its foot on the land under it}
//   cfg: {size: tiles a chunk's side, cell: px of paint a tile's side, up: px a level is drawn up, levels: [lo, hi]
//         (the levels that have sides of their own; beyond them, the last), variants: pictures of a front a level
//         (a power of 2), under: [r, g, b, a], the dark of what is under a roof (mixed that much toward it),
//         sea: [r, g, b] water when no picture of it is given, and the look of a drop that has no face in view:
//         tuck: px a top goes on under a higher block beside it (as many as a shape leaves empty at the most),
//         inset: px of those a straight side leaves empty (the wall's foot is that far in), bands: the levels of
//         a wall that stand out a bank each at the most (under them it goes straight down), dug: the level under
//         which a narrow hole is darker the deeper it goes (vox_mesh.js; left out: no hole is)}
//
//   what it gives:
//     ready()            can it draw at all (WebGL 2, its program)
//     touch(x, y)        a tile changed: its paint and its chunk's faces are made again
//     work(list, until)  make what is missing of the chunks [{cx, cy}...], until that time (performance.now)
//     made(cx, cy)       is that chunk ready to be drawn
//     forget(keep)       let go of every chunk for which keep(cx, cy) is false
//     draw(view)         draw one frame on the engine's canvas and return it. view:
//                          w, h: the picture's size (px of the screen); pw, ph: the canvas's (px of the device)
//                          ox, oy: where tile (0, 0)'s corner is in the picture; tile: a tile's side there
//                          row: the eye's row (tiles), for what is in front; clear: [r, g, b] behind everything
//                          chunks: [{cx, cy}...] to draw; light: [r, g, b] on everything
//                          water: null, or {canvas, x, y, scale}: the water's picture, its corner in the picture
//                                 (px of the screen) and how many px of the screen a px of it is
//                          window: null, or {x, y, r, row, z, earth}: see through to someone. In the round window
//                                 (its middle and radius, px of the screen) no block is drawn that is higher than
//                                 level z and not north of row `row` (tiles): what stands between that someone and
//                                 the eye. Where nothing is behind what was left out (the inside of the ground),
//                                 the colour `earth` [r, g, b]: a cut through it.
//                          cut: null, or {x, y, w, h, px, ver, a, earth}: the land cut open, tile by tile. A picture
//                                 of w x h tiles whose corner is tile (x, y): px is 4 bytes a tile: the third 255
//                                 where the tile is cut, the first two the level it is cut down to (+ 32768, low
//                                 byte first): nothing of that tile higher than that is drawn. ver: changes when
//                                 px does. a: how far it has come, 0 to 1 (it comes a px in four at a time).
//                                 earth: as the window's: here the colour of a block's sliced top. What a knife
//                                 would leave is drawn: the faces of the cut (vox_section.js). line: [r, g, b] the
//                                 line along a sliced top's edge at a drop. fill: (if given) the colour of a px
//                                 where land was left out and nothing at all is behind (there should be none)
//                          curve: null (flat), or {y0, yh, ref, lean, line}: the land rolls away to a horizon
//                                 (vox_curve.js says what each is, and where a point is then drawn).
//                                 line: where level land meets the sky (px from the top): what is well past its
//                                 horizon (a tile and a half) has come down behind the roll, and is drawn only
//                                 over that line (a far height that still stands over it)
//                          sky: null, or what vox_sky.js draws behind the land in place of `clear`
//                          marks: none, or [{x, y, z0, z1, colour, a, grow, fill}...]: cells shown as boxes with
//                                 the land's depth (what is aimed at): vox_mark.js
//                          sun: null (the land as it is painted), or the sun on it (vox_light.js): {dir: [x, y] px of
//                                 ground a shadow goes on for each px of height (east, south), alpha, shade: [r, g, b]
//                                 its colour, cast: null or a picture of the view's size with the shadows of what
//                                 stands, land: false for no shadows of the land itself, glass: null or {alpha, wave, ripple, phase}:
//                                 the land seen in the water, fire: how dark a shadow marked a fire's is, cloud: null or
//                                 {k, drift: [x, y]}: the clouds' shadows}
//     models             how many faces of models are made (the land's: faces)
//
//   models, what stands in the land and is not a block of it (a bridge's deck, a post): if the host has
//     models(x, y)  -> null, or the boxes of that tile, each with the paint of its top and its front, and
//     modelSheet()  -> the sheet that paint is in
//   they are made with their chunk's faces (touch) and drawn with the land in one depth. See vox_models.js.
//
// Where a point is: x right, y south, z up. On the screen a height is drawn `up` px of paint a level up the
// picture, a px of paint being tile / cell px of the screen: (ox + x * tile, oy + y * tile - z * up * tile / cell).
// With a curve: (ox + x * tile, VoxCurve.y(curve, oy + y * tile, z * up * tile / cell)).
//
// What a block shows of itself. Its top: the host's paint, its shape (the px the host leaves see-through). South:
// its front, cell by cell down, cut to that shape, its foot the host's line. West, east: an upright face has no
// width from here, so the wall leans (vox_mesh.js): a bank beside it, a strip a level, wider the higher the wall
// is, with its own front where the wall ends; the host's shadow on the land at its foot. North: the lower land is
// behind the block: its shape against what is further north. All in whole px of paint, in the host's colours.
const Vox = (() => {
  const VS = `#version 300 es
in vec3 aPos; in vec2 aLoc; in vec4 aMeta, aMore;
uniform vec2 uRes, uO, uChunk, uTorO; uniform float uK, uRow, uCell, uUp;
out vec3 vGround; out vec2 vLoc, vScr, vAt, vWorld, vFlat; out float vPast; flat out vec2 vTile; flat out vec4 vMeta, vMore;
` + VoxCurve.GLSL + `
void main() {
  vec2 f = uO + aPos.xy * uK; float past;                       // (where its spot of the ground is, flat; then bent: vox_curve.js)
  vec2 p = vec2(f.x, curveY(f.y, aPos.z * uK, past));           // (a height: that far up the picture)
  vFlat = vec2(f.x, f.y - aPos.z * uK); vPast = past;           // (where it would be flat: the water's picture is laid flat)
  // in front: what is further south, and what is higher; what is past the horizon is behind all that is before it
  float near = (aPos.y + aPos.z) / uCell + uRow - (2. * past + past * past / (uCurve.x - uCurve.y + 1.)) / (uK * uCell);
  gl_Position = vec4(p.x / uRes.x * 2. - 1., 1. - p.y / uRes.y * 2., clamp(-near / 700., -1., 1.), 1.);
  vLoc = aLoc; vTile = aPos.xy - aLoc; vMeta = aMeta; vMore = aMore; vScr = p;
  vAt = vec2(aPos.y / uCell + uRow, aPos.z / uUp);              // its row (from the eye's) and its level
  vWorld = aPos.xy + uChunk;                                    // where it is on the ground, px from the cut's corner
  vGround = vec3(aPos.xy + uTorO, aPos.z);                      // ...and in the ring of heights, with its height (vox_light.js)
}`;
  // vMeta: what is round the face (bits: vox_mesh.js), its kind (0 top, 1 front, 2 water, 3 and 4 a bank's top and
  // front), its strip of the sheets; vMore: where the feet of the walls west and east of a top are; a front's shape, the shape it
  // is a sliver past, its variant. vLoc is VoxMesh.BIAS px more than where the px is in its tile.
  const FS = `#version 300 es
precision highp float;
uniform sampler2D uPage, uFronts, uSides, uWater, uFoot; uniform vec2 uWaterO, uWaterSize; uniform float uWaterK, uStrips, uSea, uCell, uUp, uSide, uVars, uK, uCut, uInset; uniform vec3 uLight, uWin, uSeaCol, uCutBox, uEarth, uEdge; uniform float uSec, uSlab; uniform sampler2D uCutMap; uniform vec2 uWinAt; uniform vec4 uUnder;
in vec2 vLoc, vScr, vAt, vWorld, vFlat; in float vPast; uniform float uLine; flat in vec2 vTile; flat in vec4 vMeta, vMore; out vec4 o;
// the host's shadow (of the level in the face's strip) over a colour
vec3 shadow(vec3 c) { vec4 s = texelFetch(uSides, ivec2(2, int(vMeta.z)), 0); return mix(c, s.rgb, s.a); }
uniform sampler2D uModel; uniform vec2 uModelSize;              // (models, vox_models.js: their sheet)
uniform vec2 uRes;${VoxLight.FS}
float cutLv(vec2 t) { if (t.x < 0. || t.y < 0. || t.x >= uCutBox.x || t.y >= uCutBox.y) return 1e5; vec4 m = texelFetch(uCutMap, ivec2(t), 0); return m.b > .5 ? m.r * 255. + m.g * 65280. - 32768. : 1e5; }      // the level a tile (counted from the cut's corner) is cut down to; 1e5: it is not cut
void main() {
  // well past the horizon (vox_curve.js): behind it, seen only over the line where the land meets the sky (it comes
  // down for good, and showed through whatever opens the land in front of it)
  if (vPast > 24. * uK && vScr.y > uLine) discard;
  // the window (uWin: its middle and radius; uWinAt: the row and level of who is seen through it), a px of paint at a time
  bool cut = uWin.z > 0. && vAt.y > uWinAt.y + .02 && vAt.x > uWinAt.x - 1. && distance((floor(vScr / uK) + .5) * uK, uWin.xy) < uWin.z;
  // the land cut open (uCutBox: its picture's size in tiles, and how far it has come): a front belongs to the tile north of its edge
  // (a bank, kinds 3 and 4, lies over the ground beside its wall: it belongs to its wall's tile, half a tile on. A
  // top's px under a neighbour (vLoc: 8 more than where it is in its tile) are inside that neighbour: of its tile.)
  // What is higher than its tile's cut is left out; the faces of the cut itself (uSec: vox_section.js) are all there.
  bool open = false, front = abs(vMeta.y - 1.) < .5, bank = vMeta.y > 2.5 && vMeta.y < 4.5, on = false, day = false, into = false, other = false;
  if (uCutBox.z > 0.) {
    vec2 tl = floor((vWorld - vec2(bank ? ((int(vMeta.x + .5) & (vMeta.y > 3.5 ? 32 : 1)) != 0 ? uCell * .5 : -uCell * .5) : 0., front || vMeta.y > 3.5 ? .5 : 0.)) / uCell), q = mod(floor(vFlat / uK + .001), 2.);
    on = uCutBox.z > ((q.x == q.y ? q.x : 3. - q.x) + .5) / 4.;      // (it comes a px of paint in four at a time, on the land's own grid of px: a checker at half, never a stripe)
    if (uSec > .5) { open = true; cut = !on; }
    else {
      float lv = cutLv(tl);
      // (a front that looks into a tile that is cut open is seen with it: the wall at the back of a cave)
      into = front && cutLv(tl + vec2(0., 1.)) < 1e4; open = lv < 1e4 || into;
      vec2 s = tl + vec2(0., 1.); if (front && on && s.x >= 0. && s.y >= 0. && s.x < uCutBox.x && s.y < uCutBox.y) { float a = floor(texelFetch(uCutMap, ivec2(s), 0).a * 255. + .5), head = mod(a, 128.); day = a >= 128.; other = head > 0. && vAt.y > cutLv(s) + head + .02; }      // (a front of the land's in a hole of the cut that has a wall out of doors: the day's light, as all its walls)
      if (on && vAt.y > lv + .02) cut = true;
    }
  }
  if (cut != (uCut > .5)) discard;                              // (uCut: the other way round, only what is left out: to mark where the window opened something)
  if (vMeta.y > 6.5) {                                          // a model's face (kind 7): its px of the sheet, as it is (vLoc: half px)
    vec4 m = texture(uModel, vLoc / 2. / uModelSize);
    if (m.a < .02) discard;                                     // (a half see-through px: over the water's picture, a shadow on the water)
    if (m.a < .98) m.rgb = mix(uSea > .5 ? texture(uWater, (vFlat - uWaterO) / uWaterK / uWaterSize).rgb : vec3(.42, .7, .84), m.rgb, m.a);
    o = vec4(sunlit(m.rgb, m.rgb, 7, 0, -1.) * uLight, 1.); return;
  }
  int bits = int(vMeta.x + .5), kind = int(vMeta.y + .5);
  vec3 c, plain = vec3(-1.); float far = uCell - .01; vec2 loc = vLoc - 8., tile = vTile + 8.;
  if (kind == 5) {                                              // a block's sliced top: the earth of its level, as its fronts have it; a line along a drop
    float x = floor(loc.x), y = floor(loc.y);
    if (y >= uCell - texelFetch(uFoot, ivec2(int(clamp(x, 0., far)), int(vMore.x)), 0).r * 255.) discard;      // (none of its block here)
    // (a front's px, a px a px: its body over the top's far part, the whole of it, with its seam, along the near edge. uSlab: the cut's one colour instead)
    float fy = y < uCell - uUp ? min(mod(y, uUp), uUp - 2.) : y - (uCell - uUp);
    vec3 e = uSlab > .5 ? uEarth : texture(uFronts, vec2((vMore.z * uCell + clamp(loc.x, .01, far)) / (uVars * uCell), (vMeta.z * uUp + fy + .5) / (uStrips * uUp))).rgb;
    o = vec4((((bits & 2) != 0 && x < 1.) || ((bits & 4) != 0 && x > uCell - 2.) || ((bits & 1) != 0 && y < 1.) || ((bits & 16) != 0 && y > uCell - 2.) ? (uSlab > .5 ? uEdge : texelFetch(uSides, ivec2(1, int(vMeta.z)), 0).rgb) : e) * uLight, 1.); return;
  }
  if (kind == 0) {
    vec4 t = texture(uPage, (tile + clamp(loc, .01, far)) / uSide);
    if (t.a < .5) discard;
    c = t.rgb; plain = c;
    float x = floor(loc.x), y = floor(loc.y);
    if ((bits & 128) == 0) {                                    // (128: what floats on water, as painted)
      // the shadow at the foot of a wall: west and east of it past the wall's bank, north at a front's foot
      // (not of a wall that is cut away down to here)
      vec2 own = floor((vWorld - loc) / uCell + .5); bool gw = on && cutLv(own - vec2(1., 0.)) < vAt.y + .5, ge = on && cutLv(own + vec2(1., 0.)) < vAt.y + .5, gn = on && cutLv(own - vec2(0., 1.)) < vAt.y + .5;
      if (uSec > .5) { gw = false; ge = false; gn = false; }
      // (...and along a side where the land beside it is cut lower than it: the line of a cut edge, the wall's foot colour. A roof lifted off shows where it was)
      if (on && uSec < .5 && ((x < 1. && loc.x >= 0. && cutLv(own - vec2(1., 0.)) < vAt.y - .5) || (x > uCell - 2. && loc.x < uCell && cutLv(own + vec2(1., 0.)) < vAt.y - .5) || (y < 1. && loc.y >= 0. && cutLv(own - vec2(0., 1.)) < vAt.y - .5) || (y > uCell - 2. && cutLv(own + vec2(0., 1.)) < vAt.y - .5))) c = texelFetch(uSides, ivec2(1, int(vMeta.z)), 0).rgb;
      if (((bits & 2) != 0 && !gw && x == vMore.x - 8.) || ((bits & 4) != 0 && !ge && uCell - 1. - x == vMore.y - 8.) || ((bits & 1) != 0 && !gn && y == -texelFetch(uFoot, ivec2(int(clamp(x, 0., far)), int(vMore.z)), 0).r * 255.)) c = shadow(c);
    }
  } else if (kind == 1) {
    int i = int(clamp(loc.x, 0., far)); float r = floor(clamp(loc.y, 0., uUp - .01)), f = texelFetch(uFoot, ivec2(i, int(vMore.x)), 0).r * 255.;
    if (f >= uCell || (vMore.y > 0. && texelFetch(uFoot, ivec2(i, int(vMore.y)), 0).r * 255. < uCell)) discard;      // none of its block over this px; a sliver: only past the block south
    c = texture(uFronts, vec2((vMore.z * uCell + clamp(loc.x, .01, far)) / (uVars * uCell), (vMeta.z * uUp + clamp(loc.y, .01, uUp - .01)) / (uStrips * uUp))).rgb;
    if (((bits & 32) != 0 && i < 8) || ((bits & 64) != 0 && i > 7)) f = min(f, uInset);
    if (into && on) f = 0.;                                     // (a wall of the cut: its foot is square, on the floor: the ground that went on under its set-in foot is not there at the horizon, a line of nothing)
    if ((bits & 16) != 0) { if (r >= uUp - f) discard; if (r == uUp - f - 1.) c = texelFetch(uSides, ivec2(1, int(vMeta.z)), 0).rgb; }      // its foot: where its block's shape ends, a line
  } else if (kind > 2) {                                        // a bank: its top; its front, and that one's foot
    c = texelFetch(uSides, ivec2(kind == 3 ? ((bits & 4) != 0 ? 1 : 0) : 3, int(vMeta.z)), 0).rgb;      // (4: the last px of a bank that did not fit: the wall's foot colour)
    if (kind == 4 && (bits & 16) != 0) { float r = floor(clamp(loc.y, 0., uUp - .01)); if (r >= uUp - uInset) discard; if (r == uUp - uInset - 1.) c = texelFetch(uSides, ivec2(1, int(vMeta.z)), 0).rgb; }
  } else {
    c = uSea > .5 ? texture(uWater, (vFlat - uWaterO) / uWaterK / uWaterSize).rgb : uSeaCol;
  }
  // under a roof: a cave's own dark. Seen from outside, at its mouth, nearly all of it; seen through the window on
  // who is in it, a third: the place is to be seen
  if (uSec > .5) { o = vec4(((bits & 8) != 0 ? mix(c, uUnder.rgb, uUnder.a * .38) : c) * uLight, 1.); return; }      // (the faces of the cut: bit 8, in the dark of the place; else the day's light, as painted)
  // (vMeta.w, vox_mesh.js: under a roof, how far in from the open it is: the dark comes on inward, the ground is seen going in under an overhang;
  // out of doors, how deep down a narrow hole: darker a step at a time. A hollow over the room that is cut open: darker than that room's walls)
  if ((bits & 8) != 0 && kind < 2 && !day) c = mix(c, uUnder.rgb, uUnder.a * (other ? .8 : open || (uWin.z > 0. && distance((floor(vScr / uK) + .5) * uK, uWin.xy) < uWin.z) ? .38 : vMeta.w > 0. ? min(1., .25 + .2 * vMeta.w) : 1.));
  else if ((kind < 2 || kind == 3) && vMeta.w > 0.) c = mix(c, uUnder.rgb, uUnder.a * .15 * min(vMeta.w, 5.));
  o = vec4(sunlit(c, plain.r < 0. ? c : plain, kind, bits, kind == 0 && (bits & 128) == 0 ? floor(loc.y) + texelFetch(uFoot, ivec2(int(clamp(loc.x, 0., far)), int(vMore.w)), 0).g * 255. - uCell : -1.) * uLight, 1.);                 // (the sun, if the view has one: vox_light.js)
}`;
  function create(host, cfg) {
    const chunks = new Map(), key = (cx, cy) => cx + "," + cy, N = cfg.size, [lo, hi] = cfg.levels;
    let cutTex = null, cutVer = null, sec = {}, prog = null, fill = null, fronts = null, sea = null, failed = false;
    const keep = {};                                            // (the models' sheet, vox_models.js)
    const light = VoxLight.create(cfg);                         // (the sun: vox_light.js)
    const pending = new Set([0]);                               // shapes met by the faces made, not yet in the shapes' sheet
    const FILL = [`#version 300 es\nin vec2 p; void main() { gl_Position = vec4(p, .9995, 1.); }`, `#version 300 es\nprecision highp float; uniform vec3 uCol; out vec4 o; void main() { o = vec4(uCol, 1.); }`];
    const strip = (z) => Math.max(lo, Math.min(hi, z)) - lo;
    function ready() {
      if (failed || !VoxGL.start()) return false;
      if (!prog) { try { prog = VoxGL.program(VS, FS); fill = VoxGL.program(FILL[0], FILL[1]); } catch (e) { failed = true; console.error(e); return false; } }
      return true;
    }
    function touch(x, y) {
      const cx = Math.floor(x / N), cy = Math.floor(y / N), ch = chunks.get(key(cx, cy));
      if (ch) { ch.todo.push((y - cy * N) * N + (x - cx * N)); ch.stale = true; }
    }
    function work(list, until) {
      for (const {cx, cy} of list) {
        let ch = chunks.get(key(cx, cy));
        if (!ch) chunks.set(key(cx, cy), ch = {cx, cy, pages: [], todo: Array.from({length: N * N}, (_, i) => i), stale: true, ready: false, vao: null, buf: null, ranges: [], faces: 0});
        for (let n = 0; ch.todo.length && (n++ < 24 || performance.now() < until);) { const i = ch.todo.pop(); VoxPages.tile(ch, host, cfg, i % N, i / N | 0); }
        if (ch.todo.length) return;                             // (out of time: the rest next frame)
        VoxPages.upload(ch, cfg);
        if (ch.stale) { const mesh = VoxMesh.build(ch, host, cfg, strip); for (const id of mesh.shapes) pending.add(id); VoxMesh.upload(ch, mesh, prog); VoxModels.make(ch, host, cfg, prog); light.tops(ch, host); ch.stale = false; ch.ready = true; }
        if (performance.now() >= until) return;
      }
    }
    const made = (cx, cy) => { const ch = chunks.get(key(cx, cy)); return !!ch && ch.ready; };
    function forget(keep) { for (const [k, ch] of chunks) if (!keep(ch.cx, ch.cy)) { VoxPages.drop(ch); VoxMesh.drop(ch); VoxModels.drop(ch); light.drop(ch); chunks.delete(k); } }
    function draw(v) {
      const gl = VoxGL.gl, u = prog.u, k = v.tile / cfg.cell;
      VoxGL.fit(v.pw, v.ph);
      gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
      gl.clearColor(v.clear[0], v.clear[1], v.clear[2], 1); gl.clearDepth(1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.disable(gl.BLEND);
      if (v.sky) VoxSky.draw(v.sky, v.w, v.h, v.pw, k);
      fronts = fronts || VoxPages.fronts(host, cfg, lo, hi);
      // the cut, and its faces (vox_section.js), made again when it changed
      const open = v.cut && v.cut.a > 0 ? v.cut : null, fresh = open && (!cutTex || cutVer !== open.ver);
      if (fresh) { const t0 = performance.now(), m = VoxSection.build(host, cfg, strip, open); for (const id of m.shapes) pending.add(id); VoxMesh.upload(sec, m, prog); sec.lit = m.lit; sec.room = m.room; sec.ms = performance.now() - t0; }
      gl.useProgram(prog.pr);
      gl.uniform2f(u.uRes, v.w, v.h); gl.uniform1f(u.uK, k); gl.uniform1f(u.uCell, cfg.cell); gl.uniform1f(u.uUp, cfg.up); gl.uniform1f(u.uSide, N * cfg.cell);
      const cu = v.curve; gl.uniform4f(u.uCurve, cu ? cu.y0 : 0, cu ? cu.yh : 0, cu ? cu.ref : 0, cu ? cu.lean : 0); gl.uniform1f(u.uLine, cu ? cu.line : 0);
      gl.uniform1f(u.uStrips, fronts.n); gl.uniform3f(u.uLight, v.light[0], v.light[1], v.light[2]);
      gl.uniform1i(u.uPage, 0); gl.uniform1i(u.uFronts, 1); gl.uniform1i(u.uWater, 2); gl.uniform1i(u.uSides, 3); gl.uniform1i(u.uFoot, 4);
      gl.uniform4f(u.uUnder, ...cfg.under); gl.uniform1f(u.uVars, cfg.variants); gl.uniform1f(u.uInset, cfg.inset); gl.uniform3f(u.uSeaCol, ...cfg.sea);
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, fronts.tex); gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, fronts.sides);
      gl.activeTexture(gl.TEXTURE4); VoxPages.shapes(fronts.prof, host, cfg, pending); pending.clear(); gl.bindTexture(gl.TEXTURE_2D, fronts.prof.tex);
      gl.uniform1f(u.uSea, v.water ? 1 : 0);
      if (v.water) {
        gl.activeTexture(gl.TEXTURE2); sea = VoxGL.texture(v.water.canvas, sea);
        gl.uniform2f(u.uWaterO, v.water.x, v.water.y); gl.uniform1f(u.uWaterK, v.water.scale); gl.uniform2f(u.uWaterSize, v.water.canvas.width, v.water.canvas.height);
      }
      VoxModels.bind(host, keep, u);
      light.frame(gl, u, v, chunks);
      gl.activeTexture(gl.TEXTURE0);
      const win = v.window && v.window.r > 0 ? v.window : null;
      gl.uniform3f(u.uWin, win ? win.x : 0, win ? win.y : 0, win ? win.r : 0); gl.uniform2f(u.uWinAt, win ? win.row - v.row : 0, win ? win.z : 0);
      const all = () => { for (const {cx, cy} of v.chunks) {
        const ch = chunks.get(key(cx, cy)); if (!ch || !ch.ready) continue;
        gl.uniform2f(u.uO, v.ox + cx * N * v.tile, v.oy + cy * N * v.tile); gl.uniform1f(u.uRow, cy * N - v.row); gl.uniform2f(u.uChunk, (cx * N - (v.cut ? v.cut.x : 0)) * cfg.cell, (cy * N - (v.cut ? v.cut.y : 0)) * cfg.cell);
        light.at(gl, u, v, cx, cy);
        gl.bindVertexArray(ch.vao);
        for (const [p, first, count] of ch.ranges) { const pg = ch.pages[p]; if (!pg || !pg.tex) continue; gl.bindTexture(gl.TEXTURE_2D, pg.tex); gl.drawArrays(gl.TRIANGLES, first, count); }
        VoxModels.draw(ch);
      } };
      if (fresh) { cutTex = VoxSection.hand(gl, open, sec, cutTex); cutVer = open.ver; }      // (the cut's picture, handed over when it changed)
      if (open) { gl.activeTexture(gl.TEXTURE5); gl.bindTexture(gl.TEXTURE_2D, cutTex); }
      gl.uniform1i(u.uCutMap, 5); gl.uniform3f(u.uCutBox, open ? open.w : 0, open ? open.h : 0, open ? open.a : 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.uniform1f(u.uCut, 0); gl.uniform1f(u.uSec, 0); all();
      if (open) VoxSection.draw(gl, u, v, open, sec, () => light.at(gl, u, v, open.x / N, open.y / N));      // (the faces of the cut)
      // Where the window left blocks out and nothing is behind them: the cut's colour. What was left out is drawn once
      // more, only to mark those px; then the colour is laid on the marked px that are still empty (vox_section.js).
      if (win || open) VoxSection.fill(gl, u, v, win ? win.earth : open.fill || open.earth, all, fill);
      VoxMark.draw(v, k, cfg);                                  // (marks: boxes over the land, vox_mark.js)
      gl.bindVertexArray(null);
      return VoxGL.el;
    }
    return {ready, touch, work, made, forget, draw, get section() { return {faces: sec.faces || 0, ms: sec.ms || 0}; }, get chunks() { return chunks.size; }, get faces() { let n = 0; for (const ch of chunks.values()) n += ch.faces; return n; },
            get sides() { let n = 0; for (const ch of chunks.values()) n += ch.sides || 0; return n; },
      get models() { let n = 0; for (const ch of chunks.values()) n += VoxModels.count(ch); return n; }};
  }
  return {create};
})();
