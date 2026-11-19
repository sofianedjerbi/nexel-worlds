// VOX: the engine. `Vox.create(host, cfg)` gives a world of blocks to draw.
//
//   host, what the user of the engine knows and the engine asks for:
//     column(x, y)  -> a tile's column of cells, or null where the world is not known. A column is the heights
//                      where it changes, from the bottom: solid up to c[0], empty up to c[1], solid up to c[2]...
//     water(x, y)   -> is this tile water: one face in place of its top, at the level waterTop(x, y) says (0 if the host has none)
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
//     crown(id)     -> (if it has it) [west, east]: the px that shape leaves empty at its north end along that side
//                      (a rounded corner: the wall's side beside it starts that far down)
//     side(z)       -> the colours of a wall's level z that faces west or east: {band: [r, g, b] its side's light,
//                      body: [r, g, b] its side's body, foot: [r, g, b] its dark line, and the line at a wall's foot,
//                      shadow: [r, g, b, a] the shadow at its foot on the land under it}
//   cfg: {size: tiles a chunk's side, cell: px of paint a tile's side, up: px a level is drawn up, levels: [lo, hi]
//         (the levels that have sides of their own; beyond them, the last), variants: pictures of a front a level
//         (a power of 2), under: [r, g, b, a], the dark of what is under a roof (mixed that much toward it),
//         sea: [r, g, b] water when no picture of it is given, and the look of a drop that has no face in view:
//         tuck: px a top goes on under a higher block beside it (as many as a shape leaves empty at the most),
//         inset: px of those a straight side leaves empty (the wall's foot is that far in), side: the px a
//         wall that faces west or east shows of its side (its outer px a dark line; vox_mesh.js), dug: the level under
//         which a narrow hole is darker the deeper it goes (vox_mesh.js; left out: no hole is)}
//
//   what it gives:
//     ready()            can it draw at all (WebGL 2, its program)
//     touch(x, y)        a tile changed: its paint, the paint of the tiles round it (a top's lip and shape are by its
//                        eight neighbours) and the faces of every chunk it can be seen in are made again
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
//                                 {k, drift: [x, y]}: the clouds' shadows, rays: null or {k, dir: [x, y], t}: the low sun's shafts on the tops, depth: true for the land's depth}
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
// width from here, so the wall shows a thin side (vox_mesh.js): cfg.side px in the px its cap leaves empty, straight
// down, with its own front where the wall ends; the host's shadow on the land at its foot. North: the lower land is
// behind the block: its shape against what is further north. All in whole px of paint, in the host's colours.
const Vox = (() => {
  const VS = `#version 300 es
in vec3 aPos; in vec2 aLoc; in vec4 aMeta, aMore;
uniform vec2 uRes, uO, uChunk, uTorO; uniform float uK, uRow, uCell, uUp;
out vec3 vGround0; out vec2 vLoc0, vScr, vAt, vWorld, vFlat0; out float vPast; flat out vec2 vTile, vRows; flat out vec4 vMeta, vMore;
` + VoxCurve.VS + `
void main() {
  vec2 f = uO + aPos.xy * uK; float past;                       // (where its spot of the ground is, flat; then bent: vox_curve.js)
  vec2 p = vec2(f.x, rollY(f.y, aPos.z * uK, past));            // (a height: that far up the picture; bent: on a whole px of the paint)
  vFlat0 = vec2(f.x, f.y - aPos.z * uK); vPast = past;           // (where it would be flat: the water's picture is laid flat)
  float t0 = f.y - (aLoc.y - 8.) * uK, pp; vRows.x = rollY(t0, aPos.z * uK, pp); vRows.y = (rollY(t0 + uCell * uK, aPos.z * uK, pp) - vRows.x) / uK;      // (its tile's row as it is drawn: where it starts, how many px of paint tall)
  // in front: what is further south, and what is higher; what is past the horizon is behind all that is before it
  float near = (aPos.y + aPos.z) / uCell + uRow - (2. * past + past * past / (uCurve.x - uCurve.y + 1.)) / (uK * uCell);
  gl_Position = vec4(p.x / uRes.x * 2. - 1., 1. - p.y / uRes.y * 2., clamp(-near / 700., -1., 1.), 1.);
  vLoc0 = aLoc; vTile = aPos.xy - aLoc; vMeta = aMeta; vMore = aMore; vScr = p;
  vAt = vec2(aPos.y / uCell + uRow, aPos.z / uUp);              // its row (from the eye's) and its level
  vWorld = aPos.xy + uChunk;                                    // where it is on the ground, px from the cut's corner
  vGround0 = vec3(aPos.xy + uTorO, aPos.z);                      // ...and in the ring of heights, with its height (vox_light.js)
}`;
  // vMeta: what is round the face (bits: vox_mesh.js), its kind (0 top, 1 front, 2 water, 3 and 4 a bank's top and
  // front), its strip of the sheets; vMore: where the feet of the walls west and east of a top are; a front's shape, the shape it
  // is a sliver past, its variant. vLoc is VoxMesh.BIAS px more than where the px is in its tile.
  const FS = `#version 300 es
precision highp float;
uniform sampler2D uPage, uFronts, uSides, uWater, uFoot; uniform vec2 uWaterO, uWaterSize; uniform float uWaterK, uStrips, uSea, uCell, uUp, uSide, uVars, uK, uCut, uInset; uniform vec3 uLight, uWin, uSeaCol, uCutBox; uniform float uSec, uOpen; uniform sampler2D uCutMap; uniform vec2 uWinAt; uniform vec4 uUnder;
in vec3 vGround0; in vec2 vLoc0, vScr, vAt, vWorld, vFlat0; vec3 vGround; vec2 vLoc, vFlat; in float vPast; uniform float uLine; uniform vec4 uCurve; uniform vec2 uO; flat in vec2 vTile, vRows; flat in vec4 vMeta, vMore; out vec4 o;
// the host's shadow (of the level in the face's strip) over a colour
vec3 shadow(vec3 c) { vec4 s = texelFetch(uSides, ivec2(2, int(vMeta.z)), 0); return mix(c, s.rgb, s.a); }
uniform sampler2D uModel; uniform vec2 uModelSize;              // (models, vox_models.js: their sheet)
uniform vec2 uRes;${VoxLight.FS}${VoxCurve.FS}${VoxWater.FS}
bool cutIn = false;                                             // (cutLv: ...and is that tile a floor of the hole you are in)
float cutLv(vec2 t) { cutIn = false; if (t.x < 0. || t.y < 0. || t.x >= uCutBox.x || t.y >= uCutBox.y) return 1e5; vec4 m = texelFetch(uCutMap, ivec2(t), 0); cutIn = m.b > .9; return m.b > .5 ? m.r * 255. + m.g * 65280. - 32768. : 1e5; }      // the level a tile (counted from the cut's corner) is cut down to; 1e5: it is not cut
void main() {
  // (where the px is, as its face's corners say: vLoc in its tile, vFlat on the flat picture, vGround on the ground. In the roll, vox_curve.js, read at the
  // middle of the px of paint this px of the screen is in: the paint, the sun's shadows and the land's depth are whole px of paint there, squeezed with their rows)
  vLoc = vLoc0; vFlat = vFlat0; vGround = vGround0; bool roll = uCurve.x > uCurve.y;
  if (roll) { vLoc.y = rollRow(vLoc0.y, vScr.y, uO.y, uK); vFlat.y = rollRow(vFlat0.y, vScr.y, uO.y, uK); vGround.yz = vec2(rollRow(vGround0.y, vScr.y, uO.y, uK), rollRow(vGround0.z, vScr.y, uO.y, uK)); }
  // well past the horizon (vox_curve.js): behind it, seen only over the line where the land meets the sky (it comes
  // down for good, and showed through whatever opens the land in front of it)
  if (vPast > 24. * uK && vScr.y > uLine) discard;
  // the window (uWin: its middle and radius; uWinAt: the row and level of who is seen through it), a px of paint at a time
  bool cut = uWin.z > 0. && vAt.y > uWinAt.y + .02 && vAt.x > uWinAt.x - 1. && distance((floor(vScr / uK) + .5) * uK, uWin.xy) < uWin.z;
  // the land cut open (uCutBox: its picture's size in tiles, and how far it has come): a front belongs to the tile north of its edge
  // (a bank, kinds 3 and 4, lies over the ground beside its wall: it belongs to its wall's tile, half a tile on. A
  // top's px under a neighbour (vLoc: 8 more than where it is in its tile) are inside that neighbour: of its tile.)
  // What is higher than its tile's cut is left out; the faces of the cut itself (uSec: vox_section.js) are all there.
  bool open = false, front = abs(vMeta.y - 1.) < .5, bank = vMeta.y > 2.5 && vMeta.y < 4.5, on = false, day = false, into = false, other = false, mouth = false;
  if (uCutBox.z > 0.) {
    vec2 tl = floor((vWorld - vec2(bank ? ((int(vMeta.x + .5) & (vMeta.y > 3.5 ? 32 : 1)) != 0 ? uCell * .5 : -uCell * .5) : 0., front || vMeta.y > 3.5 ? .5 : 0.)) / uCell), q = mod(floor(vec2(vFlat.x, vScr.y - uO.y) / uK + .001), 2.); noSun = cutLv(tl) < 1e4 && (cutIn || uOpen > .5);      // (vox_light.js: no sun's shadow in what is cut open: the floors under a roof of a hole you are in, and of the other cut tiles the px seen through the opening, uOpen: vox_section.js mark. Not the ground beside it, still in the shadow of the land that stands: a light square in a slab's shadow)
    on = uCutBox.z > (q.x == q.y ? .2 : .6);      // (it comes in two steps, a checker of px of paint as they are drawn, then whole. One px in four first, on the flat picture's rows: a lattice of dots, and stripes where the roll squeezes the rows)
    if (uSec > .5) { open = true; cut = !on; }
    else {
      float lv = cutLv(tl);
      // (a front that looks into a tile that is cut open is seen with it: the wall at the back of a cave)
      into = front && cutLv(tl + vec2(0., 1.)) < 1e4; open = lv < 1e4 || into; mouth = on && bank && cutLv(tl + vec2(0., 1.)) < 1e4;      // (mouth: the front of a wall's side that looks into a cut tile: its foot square too. Set in, it left two px of the dark behind it: a black tick at each end of a room's floor line)
      vec2 s = tl + vec2(0., 1.); if (front && on && s.x >= 0. && s.y >= 0. && s.x < uCutBox.x && s.y < uCutBox.y) { float a = floor(texelFetch(uCutMap, ivec2(s), 0).a * 255. + .5), head = mod(a, 128.); day = a >= 128.; other = head > 0. && vAt.y > cutLv(s) + head + .02; }      // (a front of the land's in a hole of the cut that has a wall out of doors: the day's light, as all its walls)
      if (on && vAt.y > lv + .02) cut = true;
      if (on && bank && abs(cutLv(floor((vWorld - vec2(0., vMeta.y > 3.5 ? .5 : 0.)) / uCell)) - 3e4) < .5) cut = true;      // (a bank lying on the open floor of a hole you are in: its wall is seen straight, the floor whole to the cut's edge. Leaning, each level's strip ended at its own row: lines down the floor's sides, "a messy tray")
    }
  }
  if (cut != (uCut > .5)) discard;                              // (uCut: the other way round, only what is left out: to mark where the window opened something)
  if (vMeta.y > 6.5) {                                          // a model's face (kind 7): its px of the sheet, as it is (vLoc: half px)
    vec4 m = texture(uModel, vLoc / 2. / uModelSize);
    if (m.a < .02) discard;                                     // (a half see-through px: over the water's picture, a shadow on the water)
    if (wmodel(m)) discard; if (uWPass > .5) { o = vec4(m.rgb * m.a, m.a); return; }      // (water seen through, vox_water.js: a shade on it is mixed in with it)
    if (m.a < .98) m.rgb = mix(uSea > .5 ? texture(uWater, (vFlat - uWaterO) / uWaterK / uWaterSize).rgb : vec3(.42, .7, .84), m.rgb, m.a);
    o = vec4(sunlit(m.rgb, m.rgb, 7, 0, -1.) * uLight, 1.); return;
  }
  int bits = int(vMeta.x + .5), kind = int(vMeta.y + .5);
  // (of a top in the roll: the row of its paint that its tile's height says, the same whatever the frame; its shadows and its depth are that row's)
  if (roll && kind == 0) { float i = floor((vScr.y - vRows.x) / uK); if (vRows.y > 0. && vRows.y < uCell && i >= 0. && i < vRows.y) { float dy = rollPick(i, vRows.y, uCell) + 8.5 - vLoc.y; vLoc.y += dy; vGround.y += dy; vFlat.y += dy * uK; } }
  vec3 c, plain = vec3(-1.); float far = uCell - .01, wa = 1.; vec2 loc = vLoc - 8., tile = vTile + 8.;
  if (kind == 5) {                                              // a block's sliced top: the rock seen inside, a cross-section: its front's own body and flecks (the rows of a front between its top and its seam, a variant every five rows: no seam, so no wall's strata), the whole square (a cut is straight: no cap, no lip, no rounded corner), a touch darker than the wall beside it (CUT, one tone everywhere), its level's dark line along a drop. (It was one flat colour: in stone a blank grey slab)
    float x = floor(clamp(loc.x, 0., far)), y = floor(clamp(loc.y, 0., far));
    vec3 e = texture(uFronts, vec2((mod(vMore.z + floor(y / 5.) + floor(y / 5.) * floor(x / 8.), uVars) * uCell + mod(x + 5. * floor(y / 5.), uCell) + .5) / (uVars * uCell), (vMeta.z * uUp + 1.5 + mod(y, 5.)) / (uStrips * uUp))).rgb;
    if (((bits & 2) != 0 && x < 1.) || ((bits & 4) != 0 && x > uCell - 2.) || ((bits & 1) != 0 && y < 1.) || ((bits & 16) != 0 && y > uCell - 2.)) e = texelFetch(uSides, ivec2(1, int(vMeta.z)), 0).rgb * .8;
    o = vec4(e * vec3(.8, .8, .83) * uLight, 1.); return;
  }
  if (kind == 0) {
    vec4 t = texture(uPage, (tile + clamp(loc + wbend(bits), .01, far)) / uSide);
    if (t.a < .5) discard;
    c = wbed(t.rgb, bits); plain = c;
    float x = floor(loc.x), y = floor(loc.y);
    if ((bits & 128) == 0) {                                    // (128: what floats on water, as painted)
      // the shadow at the foot of a wall: west and east of it past the wall's bank, north at a front's foot
      // (not of a wall that is cut away down to here)
      vec2 own = floor((vWorld - loc) / uCell + .5); bool gw = on && cutLv(own - vec2(1., 0.)) < vAt.y + .5, ge = on && cutLv(own + vec2(1., 0.)) < vAt.y + .5, gn = on && cutLv(own - vec2(0., 1.)) < vAt.y + .5;
      if (uSec > .5) { gw = false; ge = false; gn = false; }
      // (...and along a side where the land beside it is cut lower than it: the edge of a cut, two px of the wall's foot colour: the ground's inside. A roof lifted off shows where it was)
      if (on && uSec < .5 && ((x < 2. && loc.x >= 0. && cutLv(own - vec2(1., 0.)) < vAt.y - .5) || (x > uCell - 3. && loc.x < uCell && cutLv(own + vec2(1., 0.)) < vAt.y - .5) || (y < 2. && loc.y >= 0. && cutLv(own - vec2(0., 1.)) < vAt.y - .5) || (y > uCell - 3. && cutLv(own + vec2(0., 1.)) < vAt.y - .5))) c = texelFetch(uSides, ivec2(1, int(vMeta.z) - (uRock.x > 0. && abs(vAt.y - uRock.x + 1.) < .5 ? 1 : 0)), 0).rgb;      // (a top's strip is the level's over it, for the shadow at a wall's foot: the last level under stone (uRock, vox_light.js) had stone's, a grey frame on brown earth)
      if ((bits & 64) == 0 && (((bits & 2) != 0 && !gw && x == vMore.x - 8.) || ((bits & 4) != 0 && !ge && uCell - 1. - x == vMore.y - 8.) || ((bits & 1) != 0 && !gn && y == -texelFetch(uFoot, ivec2(int(clamp(x, 0., far)), int(vMore.z)), 0).r * 255.))) c = shadow(c);      // (not a bed's, bit 64: vox_water.js)
    }
  } else if (kind == 1) {
    int i = int(clamp(loc.x, 0., far)); float r = floor(clamp(loc.y, 0., uUp - .01)), f = texelFetch(uFoot, ivec2(i, int(vMore.x)), 0).r * 255.;
    if (f >= uCell || (vMore.y > 0. && texelFetch(uFoot, ivec2(i, int(vMore.y)), 0).r * 255. < uCell)) discard;      // none of its block over this px; a sliver: only past the block south
    c = texture(uFronts, vec2((vMore.z * uCell + clamp(loc.x, .01, far)) / (uVars * uCell), (vMeta.z * uUp + clamp(loc.y, .01, uUp - .01)) / (uStrips * uUp))).rgb;
    if (((bits & 32) != 0 && i < 8) || ((bits & 64) != 0 && i > 7)) f = min(f, uInset);
    if (into && on) f = 0.;                                     // (a wall of the cut: its foot is square, on the floor: the ground that went on under its set-in foot is not there at the horizon, a line of nothing)
    if ((bits & 16) != 0) { if (r >= uUp - f) discard; if (r == uUp - f - 1.) c = texelFetch(uSides, ivec2(1, int(vMeta.z)), 0).rgb; }      // its foot: where its block's shape ends, a line
  } else if (kind > 2) {                                        // a wall's side: its strip beside the top; its front, and that one's foot
    // (4: its outer px, the wall's dark line; on the side the sun is on, the wall's body: a lit edge, not a line lost in the shade at its foot. The rest, beside the
    // top: the wall's light and its body in turn along it, as the pack's own caps have their sides; down the front: its body, its level's seam along its foot as the front beside it has)
    // (...by how far to that side the sun is, as the side's own light is, vox_light.js: none at noon, and never a jump at an hour: it flipped as the sun passed a mark, at the hour a day starts with)
    float r = floor(clamp(loc.y, 0., uUp - .01)), sunny = uDepth > .5 ? clamp(((bits & (kind == 3 ? 1 : 32)) != 0 ? -uSun.x : uSun.x) * 2.5, 0., 1.) : 0.;
    c = texelFetch(uSides, ivec2((bits & 4) != 0 ? 1 : kind == 4 ? (r == uUp - 1. ? 1 : 3) : mod(floor(loc.y), 8.) < 3. ? 0 : 3, int(vMeta.z)), 0).rgb;
    if ((bits & 4) != 0) c = mix(c, texelFetch(uSides, ivec2(3, int(vMeta.z)), 0).rgb, sunny);
    if (kind == 4 && (bits & 16) != 0 && !mouth) { if (r >= uUp - uInset) discard; if (r == uUp - uInset - 1.) c = texelFetch(uSides, ivec2(1, int(vMeta.z)), 0).rgb; }
  } else { vec4 w = wface(loc, bits); c = w.rgb; wa = w.a; }    // (water: the view's picture at its level; or seen through: vox_water.js)
  // under a roof: a cave's own dark. Seen from outside, at its mouth, nearly all of it; seen through the window on
  // who is in it, a third: the place is to be seen
  if (uSec > .5) { o = vec4(((bits & 8) != 0 ? mix(roofed(deep(c, kind, bits, -1., true), kind), uUnder.rgb, uUnder.a * .38) : kind == 1 && (bits & 128) != 0 ? c * vec3(.8, .8, .83) : deep(c, kind, bits & ~8, -1., true)) * uLight, 1.); return; }      // (a front of the cut that rises from a sliced top, bit 128, is the same slice through the same rock: its one tone. The faces of the cut: bit 8, in the dark of the place; else the day's light, with the land's depth as the wall out of doors beside them has it)
  // (vMeta.w, vox_mesh.js: under a roof, how far in from the open it is: the dark comes on inward, the ground is seen going in under an overhang;
  // out of doors, how deep down a narrow hole: darker a step at a time. A hollow over the room that is cut open: darker than that room's walls)
  if ((bits & 8) != 0 && kind < 2 && !day) c = mix(roofed(c, kind), uUnder.rgb, uUnder.a * (other ? .8 : open || (uWin.z > 0. && distance((floor(vScr / uK) + .5) * uK, uWin.xy) < uWin.z) ? .38 : vMeta.w > 0. ? min(1., .25 + .2 * vMeta.w) : 1.));
  else if ((kind < 2 || kind == 3) && vMeta.w > 0.) c = mix(c, uUnder.rgb, uUnder.a * .15 * min(vMeta.w, 5.));
  if (day) { o = vec4(deep(c, kind, bits & ~8, -1., true) * uLight, 1.); return; }      // (a wall of the land's in a hole lit as the day: the land's depth, and no shadow of the sun)
  o = wout(vec4(wshade(sunlit(c, plain.r < 0. ? c : plain, kind, bits, kind == 0 && (bits & 128) == 0 ? floor(loc.y) + texelFetch(uFoot, ivec2(int(clamp(loc.x, 0., far)), int(vMore.w)), 0).g * 255. - uCell : -1.), c, kind, bits) * uLight, 1.) * wa);      // (the sun, if the view has one: vox_light.js)
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
    // (what a tile's change reaches: the paint of the eight tiles round it, whichever chunk they are in (a tile noted once: ch.noted); and the
    // faces of the chunks within FAR tiles: vox_mesh.js looks that far for the walls of a narrow hole and the way out from under a roof)
    const FAR = 4, at = (x, y) => chunks.get(key(Math.floor(x / N), Math.floor(y / N)));
    function touch(x, y) {
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const ch = at(x + dx, y + dy), far = at(x + dx * FAR, y + dy * FAR); if (far) far.stale = true;
        if (ch) { const i = (y + dy - ch.cy * N) * N + (x + dx - ch.cx * N); if (!ch.noted[i]) { ch.noted[i] = 1; ch.todo.push(i); } ch.stale = true; }
      }
    }
    function work(list, until) {
      for (const {cx, cy} of list) {
        let ch = chunks.get(key(cx, cy));
        if (!ch) chunks.set(key(cx, cy), ch = {cx, cy, pages: [], todo: Array.from({length: N * N}, (_, i) => i), noted: new Uint8Array(N * N).fill(1), stale: true, ready: false, vao: null, buf: null, ranges: [], faces: 0});
        for (let n = 0; ch.todo.length && (n++ < 24 || performance.now() < until);) { const i = ch.todo.pop(); ch.noted[i] = 0; VoxPages.tile(ch, host, cfg, i % N, i / N | 0); }
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
      const cu = v.curve; gl.uniform4f(u.uCurve, cu ? cu.y0 : 0, cu ? cu.yh : 0, cu ? cu.ref : 0, cu ? cu.lean : 0); gl.uniform1f(u.uLine, cu ? cu.line : 0); gl.uniform1f(u.uFloor, cu ? cu.floor || 0 : 0);
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
      light.frame(gl, u, v, chunks); VoxWater.frame(gl, u, v);
      gl.activeTexture(gl.TEXTURE0);
      const win = v.window && v.window.r > 0 ? v.window : null;
      gl.uniform3f(u.uWin, win ? win.x : 0, win ? win.y : 0, win ? win.r : 0); gl.uniform2f(u.uWinAt, win ? win.row - v.row : 0, win ? win.z : 0);
      const all = (sea = false) => { for (const {cx, cy} of v.chunks) {      // (sea: only the faces of water seen through, vox_water.js: a list of their own, drawn in no other go)
        const ch = chunks.get(key(cx, cy)); if (!ch || !ch.ready) continue;
        gl.uniform2f(u.uO, v.ox + cx * N * v.tile, v.oy + cy * N * v.tile); gl.uniform1f(u.uRow, cy * N - v.row); gl.uniform2f(u.uChunk, (cx * N - (v.cut ? v.cut.x : 0)) * cfg.cell, (cy * N - (v.cut ? v.cut.y : 0)) * cfg.cell);
        light.at(gl, u, v, cx, cy);
        gl.bindVertexArray(ch.vao);
        for (const [p, first, count] of ch.ranges) { const pg = ch.pages[p]; if (p === VoxWater.PAGE ? !sea : sea || !pg || !pg.tex) continue; if (!sea) gl.bindTexture(gl.TEXTURE_2D, pg.tex); gl.drawArrays(gl.TRIANGLES, first, count); }
        VoxModels.draw(ch);
      } };
      if (fresh) { cutTex = VoxSection.hand(gl, open, sec, cutTex); cutVer = open.ver; }      // (the cut's picture, handed over when it changed)
      if (open) { gl.activeTexture(gl.TEXTURE5); gl.bindTexture(gl.TEXTURE_2D, cutTex); }
      gl.uniform1i(u.uCutMap, 5); gl.uniform3f(u.uCutBox, open ? open.w : 0, open ? open.h : 0, open ? open.a : 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.uniform1f(u.uCut, 0); gl.uniform1f(u.uSec, 0); all();
      if (win || open) VoxSection.mark(gl, u, all, !!open);     // (the px seen through what was left out, marked; in a cut, the land there once more with no shadow of the sun on it)
      if (open) VoxSection.draw(gl, u, v, open, sec, () => light.at(gl, u, v, open.x / N, open.y / N));      // (the faces of the cut)
      // Where the window left blocks out and nothing is behind them: the cut's colour. What was left out is drawn once
      // more, only to mark those px; then the colour is laid on the marked px that are still empty (vox_section.js).
      if (win || open) VoxSection.fill(gl, u, v, win ? win.earth : open.fill || open.earth, fill);
      if (VoxWater.pass(gl, u, v, prog.pr, true)) { all(true); VoxWater.pass(gl, u, v, prog.pr, false); }      // (water seen through: over all of the land)
      VoxMark.draw(v, k, cfg);                                  // (marks: boxes over the land, vox_mark.js)
      gl.bindVertexArray(null);
      return VoxGL.el;
    }
    return {ready, touch, work, made, forget, draw, get section() { return {faces: sec.faces || 0, ms: sec.ms || 0}; }, get chunks() { return chunks.size; }, get faces() { let n = 0; for (const ch of chunks.values()) n += ch.faces; return n; }, get sides() { let n = 0; for (const ch of chunks.values()) n += ch.sides || 0; return n; }, get models() { let n = 0; for (const ch of chunks.values()) n += VoxModels.count(ch); return n; }};
  }
  return {create};
})();
