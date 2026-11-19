// A bridge is a model (models.js): a deck of planks over the water, each plank a box, on posts.
// ("blocks such as bridges should be low-poly modelized". It was planks painted flat on its tile: bridge.js lay.)
// Its looks are the pack's bridge sheet's: a plank's top is cut out of it (four px a plank, its seam and its two
// nails), its front is the sheet's lit edge over its dark one, a post is the sheet's post (its light top, its
// front under it), and where a post stands in water, the sheet's foam at its foot.
// The deck is UP art px over the water, its planks two px thick: under it, the water in its shade. Where it runs
// onto land of its own height its last four planks step down to it, a px a plank; two posts stand on the bank at
// its mouth. Where it meets land of another height (a wall) its deck goes on to the wall's set-in side. Where it ends in the water (a pier) two posts stand in the water past its end. A long one has a
// pair of thin posts where two of its tiles meet. What stands on a bridge stands on its deck (up: relief.js lifts it).
const BridgeModel = (() => {
  const UP = 4, THICK = 2, RISE = 2;                  // the deck over the water; a plank's thickness; a post over the deck
  let P = null;                                      // its pieces in the sheet
  function start() {
    const c = document.createElement("canvas"); c.width = IMG.bridge.width; c.height = IMG.bridge.height;
    const q = c.getContext("2d", {willReadFrequently: true}); q.drawImage(IMG.bridge, 0, 0);
    const col = (x, y) => { const d = q.getImageData(x, y, 1, 1).data; return `rgb(${d[0]},${d[1]},${d[2]})`; };
    // the sheet's own colours: its line, a plank's lit edge, a plank, a seam, foam
    const pal = {A: col(1, 34), B: col(1, 45), D: col(1, 35), E: col(0, 36), K: col(48, 26)};
    const cut = (sx, sy, w, h) => Models.room(w, h, (g, u, v) => g.drawImage(IMG.bridge, sx, sy, w, h, u, v, w, h));
    P = {
      ewTop: cut(0, 34, 4, 11), ewFront: Models.rows(["ABBB", "AAAA"], pal),                      // a plank that lies north-south (the bridge runs east-west)
      nsTop: cut(33, 32, 14, 4), nsFront: Models.rows(["ABBBBBBBBBBBBA", "AAAAAAAAAAAAAA"], pal),   // ...and one that lies east-west
      postTop: Models.rows([".AA.", "ABBA", "ABBA"], pal),
      post: Models.rows(["ADDA", "ADDA", "ADDA", "ADDA", "ADDA", "ADDA", "ADDA", "EDDE"], pal),     // (a post's front: as many rows as it is high, from the foot up)
      pile: Models.rows(["ADDA", "ADDA", "ADDA", "ADDA", "ADDA", "ADDA", "ADDA", "KDDK"], pal), foam: Models.rows([".KK."], pal),
      slimTop: Models.rows([".A.", "ABA", "ABA"], pal), slim: Models.rows(["ADA", "ADA", "ADA", "ADA", "ADA", "ADA", "ADA", "KDK"], pal), slimFoam: Models.rows([".K."], pal),
      ewFill: Models.rows(["EDDD", "EDDD", "EDDD", "EDDD", "EDDD"], pal), nsFill: Models.rows(["ADDDDDDDDDDDDA", "ADDDDDDDDDDDDA", "ADDDDDDDDDDDDA"], pal),   // (planks on, between two decks)
      // (beside a deck that runs north-south: half of a thin post, the deck's own line its other side)
      sideTop: [Models.rows(["AA", "AB", "AB"], pal), Models.rows(["AA", "BA", "BA"], pal)], side: [Models.rows(["AD", "AD", "AD", "AD", "AD", "AD", "AD", "KD"], pal), Models.rows(["DA", "DA", "DA", "DA", "DA", "DA", "DA", "DK"], pal)],
      plank: Models.rows(["D"], pal),                                                              // (a px of plank: what goes on to a wall)
      shade: Models.room(1, 1, (g, u, v) => { g.fillStyle = "rgba(80,64,134,.25)"; g.fillRect(u, v, 1, 1); }),
    };
  }
  const is = (x, y) => gndAt(x, y) === ":";
  // what is past the tile (x, y) of a bridge, k tiles along the way it runs: "bridge", "cross" (a bridge that runs
  // the other way), "bank" (land of its own height: it runs onto it), "wall" (other land) or "water"
  function past(x, y, ew, k) {
    const tx = ew ? x + k : x, ty = ew ? y : y + k, q = gndAt(tx, ty);
    return q === ":" ? (Bridge.ew(tx, ty) === ew ? "bridge" : "cross") : !isLand(q) ? "water" : topAt(tx, ty) === topAt(x, y) ? "bank" : "wall";
  }
  // its four planks' heights over the water, from the north or the west
  function planks(x, y, ew) {
    const a = past(x, y, ew, -1) === "bank", b = past(x, y, ew, 1) === "bank";
    return [0, 1, 2, 3].map((i) => Math.min(UP, a ? 1 + i : UP, b ? 4 - i : UP));
  }
  const up = (x, y) => { if (!is(x, y)) return 0; const h = planks(x, y, Bridge.ew(x, y)); return Math.max(h[1], h[2]); };
  // a post h px high whose foot is at height z; wet: it stands in water (foam round its foot); slim: a thin one
  function post(out, x, y, z, h, wet, slim) {
    const f = slim ? P.slim : wet ? P.pile : P.post, w = slim ? 3 : 4;
    out.push({x, y, z, w, d: 3, h, top: slim ? P.slimTop : P.postTop, front: [f[0], f[1] + 8 - h]});
    if (wet) out.push({x, y: y + 3, z, w, d: 1, h: 0, top: slim ? P.slimFoam : P.foam});
  }
  function at(x, y) {
    if (!is(x, y)) return null;
    const ew = Bridge.ew(x, y), hs = planks(x, y, ew), out = [], base = topAt(x, y) * RELIEF_STEP;
    // (a bridge two tiles wide is rows of bridges that run east-west: one deck, the planks go on to the next row's)
    const beside = (k) => ew && is(x, y + k) && Bridge.ew(x, y + k), wide = beside(1);
    hs.forEach((z, i) => {
      const h = Math.min(THICK, z), gap = z - h;
      if (ew) out.push({x: i * 4, y: 3, z: base + gap, w: 4, d: 11, h, top: P.ewTop, front: P.ewFront});
      else out.push({x: 1, y: i * 4, z: base + gap, w: 14, d: 4, h, top: P.nsTop, front: P.nsFront});
      // the water in its shade: under its south edge, and as far again south of it
      if (wide) out.push({x: i * 4, y: 14, z: base + z, w: 4, d: 5, h: 0, top: P.ewFill});
      else if (gap && ew) out.push({x: i * 4, y: 14 - gap, z: base, w: 4, d: 2 * gap, h: 0, top: [...P.shade, 1]});
      if (gap && !ew && i === 3 && past(x, y, ew, 1) === "water") out.push({x: 1, y: 16 - gap, z: base, w: 14, d: 2 * gap, h: 0, top: [...P.shade, 1]});
    });
    // its posts: at an end, a pair past it (on the bank, or in the water); along it, a pair where two tiles meet
    if (!ew) for (const k of [-1, 1]) if (past(x, y, ew, k) === "cross") out.push({x: 1, y: k < 0 ? -2 : 16, z: base + UP, w: 14, d: k < 0 ? 2 : 3, h: 0, top: P.nsFill});   // (on to the deck it meets)
    const pair = (k, z, h, wet) => { for (const s of [0, 1]) if (!beside(s ? 1 : -1)) ew ? post(out, k, s ? 14 : 0, z, h, wet) : post(out, s ? 12 : 0, k, z, h, wet); };
    for (const k of [-1, 1]) {
      const e = past(x, y, ew, k);
      if (e === "bank") pair(k < 0 ? (ew ? -4 : -3) : 16, base, 4, false);
      if (e === "water") pair(k < 0 ? (ew ? -4 : -3) : 16, base, UP + RISE, true);
      // (land of another height: its side is set in two px from its tile's, and the deck stopped at the tile's: water between
      // them. The deck goes on those two px, to the wall, under the land's own edge)
      if (e === "wall") { const z = hs[k < 0 ? 0 : 3], h = Math.min(THICK, z), at = k < 0 ? -2 : 16;
        out.push(ew ? {x: at, y: 3, z: base + z - h, w: 2, d: 11, h, top: [...P.plank, 1], front: [P.ewFront[0] + 1, P.ewFront[1]]} : {x: 1, y: at, z: base + z - h, w: 14, d: 2, h, top: [...P.plank, 1], front: P.nsFront}); }
    }
    if (past(x, y, ew, -1) === "bridge") { for (const s of [0, 1]) if (!beside(s ? 1 : -1)) ew ? post(out, -2, s ? 14 : 0, base, UP + 1, true, true) : out.push({x: s ? 15 : -1, y: -2, z: base, w: 2, d: 3, h: UP + 1, top: P.sideTop[s], front: [P.side[s][0], P.side[s][1] + 7 - UP]}); }
    return out;
  }
  Models.add({start, at, up});
  return {UP, up, planks};
})();
