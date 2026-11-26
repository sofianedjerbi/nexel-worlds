// VOX: A CELL'S FACES, for one land asked of vox_style_land.js (steps), by THE FACE RULE (the top of vox_style_land.js): which faces a cell
// has, painted with which paint, lit with which flags; and THE MOUTHS on them, a way into the land seen from any side. Split out of
// VoxStyleLand's create (#154): the same code, given what it reads of that land and of create's paints.
//   VoxLandMouth.shade(px, at, st, m): a top's mouth shade; VoxLandMouth.of({topOf, mouth, inTo, walled}) -> {mark(x, y, z): a top's mouth
//     bits, shadow(x, y, z, sky, mo): its shadow's flags inside or before a mouth}
//   VoxLandFaces({...}) -> faces(x, y, z, dst): a cell's faces onto dst
const VoxLandMouth = (() => {
  // A WAY INTO THE LAND, SEEN FROM ANY SIDE: the eye looks north, so a cave's or a tunnel's mouth that opens north, east or west has its face hidden. Its shade is laid in the
  // paint of the tops round it (m, a top's mouth bits: 1 << d the ground in front of a mouth on its side d, 16 << d the land's top over a mouth that opens on side d; d 0 N, 1 E, 2 S, 3 W):
  // a cool shade toward the mouth, 12 art px deep, in whole art px, four steps of a 2x2 dither, its corners lighter (a south mouth's ground too, as its face shows). Made with the paint, never by the frame.
  // (Of three tried, mockups "Cave mouths you can see from every side": the ground alone was hidden by the hill itself; a 6-px band on the top was too faint from the meadow)
  // (four steps of 3 px from .58, a cool blue-grey shade, not a stain: near black reads as "those black spots ... the execution is ugly"; of eight tried (~/nexel/local/mockups/mouth),
  //  the one "a little bit more beautiful and more obvious" than a fainter dither of three steps from .72.
  //  A mouth that opens north, its face hidden by its own hill, has instead a little arch on that edge: the shape of an opening, mockup G)
  const MD = [[0, -1], [1, 0], [0, 1], [-1, 0]], MK = [.58, .7, .82, .93];
  function mouthShade(px, at, st, m) {
    const north = (m & 16) || (m & 4);          // (a mouth that opens north: the top over it, the ground before it)
    for (let j = 0; j < C; j++) for (let i = 0; i < C; i++) { let k = 1, ka = 1;
      for (let d = 0; d < 4; d++) { if (!(m >> d & 17)) continue;
        const e = [j, 15 - i, 15 - j, i][d], a = d & 1 ? j : i;
        if (d === 0 && m & 1 && !(m & 16)) continue;   // (before a mouth that opens south, its face seen: the shader's shadow, out of it, MOUTHS (vox_style_glsl.js); no paint)
        const lo = m & 256 << 2 * d, hi = m & 512 << 2 * d;   // (the same mouth on the tile before / after along this edge: one mark over all of them, rounded only at its ends)
        if ((d === 0 && m & 16) || (d === 2 && m & 4)) { const dx = Math.max(0, lo ? 0 : 7.5 - a, hi ? 0 : a - 7.5), r = (dx / 4.5) ** 2 + (e / 4) ** 2; ka = Math.min(ka, r < .55 ? .38 : r < 1 ? .62 : 1); continue; }
        const t = e + Math.max(0, lo ? 0 : 3 - a, hi ? 0 : a - 12), s = Math.floor(t / 3 + ((i >> 1) + (j >> 1) & 1) * .5);
        if (s < 4) k = Math.min(k, MK[s]); }
      if (k < 1) { const o = at + j * st + i, q = px[o], b = 1 - (1 - k) * .45, g = k + (1 - k) * .2;   // (a cool shade: blue kept most, green a little: blue-grey)
        px[o] = (q & 0xff000000) | Math.round((q >>> 16 & 255) * b) << 16 | Math.round((q >>> 8 & 255) * g) << 8 | Math.round((q & 255) * k); }
      if (north && ka < 1) { const o = at + j * st + i, q = px[o], b = 1 - (1 - ka) * .75;   // (the arch: an opening's dark half-oval on that edge, its rim lighter)
        px[o] = (q & 0xff000000) | Math.round((q >>> 16 & 255) * b) << 16 | Math.round((q >>> 8 & 255) * ka) << 8 | Math.round((q & 255) * ka); } }
  }
  // which tops a mouth marks, over one land (topOf, mouth, inTo: vox_land_space.js's walk; walled: steps')
  function of({topOf, mouth, inTo, walled}) {
    const mouths = (x, y, z) => { let m = 0; for (let d = 0; d < 4; d++) { const X = x + MD[d][0], Y = y + MD[d][1], t = topOf(X, Y); if (t > z + 1 && mouth(x, y, z, X, Y)) m |= 1 << d; else if (d === 0 && t < z - 1 && !walled(X, Y, t) && mouth(X, Y, t, x, y)) m |= 16 << d; } return m; };   // (this top under the sky: in front of a mouth on side d, or over one that opens north (its arch): an east or west one's mark is on the ground before it alone, "except for north facing entries, don't show the shadow above")
    // a wide mouth: for each side d it is on, whether the tile before (256 << 2d: west, or north on an east or west side) and the one after (512 << 2d) along that edge have the same
    // mouth, at the same height: its mark is one over all of them, not one a tile ("dont do one per tile, fuse them beautifully")
    const runs = (x, y, z, m) => { if (!m) return 0; for (let d = 0; d < 4; d++) { const b = m & (17 << d); if (!b) continue;
      const same = (X, Y) => topOf(X, Y) === z && !walled(X, Y, z) && (mouths(X, Y, z) & b) === b;
      if (d & 1 ? same(x, y - 1) : same(x - 1, y)) m |= 256 << 2 * d; if (d & 1 ? same(x, y + 1) : same(x + 1, y)) m |= 512 << 2 * d; } return m; };
    const mark = (x, y, z) => runs(x, y, z, mouths(x, y, z));
    const shadow = (x, y, z, sky, mo) => {
      if (sky && mo & 1) return 262144 + (mo & 256 ? 2097152 : 0) + (mo & 512 ? 4194304 : 0);   // (the ground before a mouth that opens south: the cave's shadow spills onto it, the shader's; and the same on the tile west, east of it: one spill along a wide mouth)
      if (!sky && topOf(x, y + 1) === z && mouth(x, y + 1, z, x, y)) return 131072;   // (the floor just inside a mouth that opens south: its shadow, deeper in)
      if (!sky && topOf(x, y + 2) === z && mouth(x, y + 2, z, x, y + 1)) return 524288;   // (and the one behind it: darker still)
      if (!sky && topOf(x, y + 3) === z && mouth(x, y + 3, z, x, y + 2) && inTo(x, y + 1, x, y, z) !== null) return 1048576;   // (and the one behind that: its darkest, as all the way in: no light band at the end of the shadow)
      return 0;
    };
    return {mark, shadow};
  }
  return {shade: mouthShade, of};
})();
const VoxLandFaces = ({host, cfg, C, FACES, solidC, real, col, topOf, solidIn, walled, hop, mark, shadow, topSlot, topPaint, front, quad}) => {
  const faces = (x, y, z, dst) => {
    const c = real(x, y) || col(x, y), open = c[c.length - 1], top = VoxMesh.topOf(c, z);   // (|| col: the land's block gone since its column was read for this chunk, before a yield)   // (what a face is lit as and painted by: the land as it is; which faces there are: as drawn, solidIn)
    for (let f = 0; f < 6; f++) {
      const F = FACES[f], nx = x + F.n[0], ny = y + F.n[1], nz = z + F.n[2];
      if (f === 1 || solidIn(nx, ny, nz)) continue;
      const nc = real(nx, ny); let sky = (f === 0 ? z >= open : !nc || z > nc[nc.length - 1]) ? 1 : 0, s, kind = f === 0 ? 1 : 0, e = 0;
      const ore = host.ore && !solidC(nc, nz) && host.ore(x, y, z);   // (a cell of ore that shows: nuggets on its faces that open onto the land's real air, ore_paint.js; a face only the x-ray cut opens (rock beside it in the real column, nc) is the rock's own, face rule 4)
      if (f === 0) {
        const mo = sky && !walled(x, y, z) ? mark(x, y, z) : 0; s = topSlot(x, y, z, (px, at, st) => { topPaint(x, y, z, px, at, st); if (mo) VoxLandMouth.shade(px, at, st, mo); if (ore) OrePaint.nuggets(px, at, st, C, C, ore, x * 31 + y * 17 + z); }, ore ? (mo || "") + "o" + ore : mo);   // (a mouth's shade is for the open ground before it: a shaft's floor at a passage's end took it, a dark blue band across a level way in the window)
        if (sky && walled(x, y, z)) e |= 32768;   // (a floor under the sky in a shaft, a trench, a pit: lit as the floors of your space are when you are under the land (the shader's sk); open ground, even at a cliff's foot, keeps the sun: "still weird color mismatch when entering a cave")
        e |= shadow(x, y, z, sky, mo);   // (the shadow before and inside a mouth: VoxLandMouth)
        { [[0, -1, 1], [1, 0, 2], [0, 1, 4], [-1, 0, 8]].forEach(([dx, dy, b]) => { if (!solidIn(x + dx, y + dy, z) && (sky || solidIn(x + dx, y + dy, z - 1))) e |= b; });   // (a lip: under a roof only at a step of one level, one you can take; a drop of two or more has none)
          // (a top under the sky over a drop of three levels or more, one that hurts, had a dark rim 2 px wide all along its edge, the shader's: "ugly dark borders on cliffs and above holes". It has the light lip of any step now; the faces below show the depth)
          if (!sky) [[0, -1, 64], [1, 0, 128], [-1, 0, 256]].forEach(([dx, dy, b]) => { if (!solidIn(x + dx, y + dy, z) && !solidIn(x + dx, y + dy, z - 1)) e |= b; });   // (a floor under a roof: its edge over a drop of two levels or more, north, east, west (its south one shows the wall's face): a thick dark rim: from above a wall that faces east or west is not seen at all)
          if (!sky) [[0, -1, 512], [1, 0, 1024], [0, 1, 2048], [-1, 0, 4096]].forEach(([dx, dy, b]) => { if (solidIn(x + dx, y + dy, z + 1) && !hop(x, y, x + dx, y + dy, z)) e |= b; });   // (a floor under a roof: a WALL at that edge (too high to jump, or no room to): its foot in shade; a step you can take has none)
          if (!sky) [[0, -1, 8192], [1, 0, 16384], [-1, 0, 65536]].forEach(([dx, dy, b]) => { if (hop(x, y, x + dx, y + dy, z)) e |= b; });   // (the foot of a step UP you can take under a roof, north, east, west: a dark line there (the riser's foot): with the lit lip of the tread over it a step is a step)
        }   // (ONE floor rule under the land: every floor of your space the same warm light, a room's or a stair's (not two, by how many tiles lie on one level: a floor would change its light as you walk); 64: a floor under the land that is NOT of your space, you cannot walk to it: bare rock, no light, no lip; 128: one you can only drop to: dimmer)
      } else { s = front(x, y, z, top, false, ore); if (!sky && !solidC(c, z + 1) && hop(nx, ny, x, y, z - 1)) e |= 16; else if (sky && nc && top - nc[nc.length - 1] >= 3) e |= 64 * Math.min(3, (top - z) >> 1); }   // (64, 128: the face of a drop of three or more: darker every two levels down, three steps)   // (the riser of a step you can take: light, the tread's own tone; any other face is a wall)
      if (cfg.rock && VoxMesh.rock(cfg, top, top, !host.rock || host.rock(x, y, top)) >= cfg.rock.from) e += 8388608;   // (its ground is stone, as its walls are painted: the x-ray's cut shows it so, vox_style_glsl.js cut)
      quad(dst, x, y, z - 1, F, F.k, sky, kind, z, e, s, solidIn, f === 0);
    }
  };
  return faces;
};
