// The HD look's built blocks (hd_things.js, floors.js): a floor's planks, a step, a roof's shingles, painted from the game's
// own picture of the block: its 16 rows the top, the rows under them its face.
//   HdBlocks(S, T) (S: HdSheet; T: {UP, PITCH, FH, cast, hid}) -> {pitch, block}
const HdBlocks = (S, T) => {
  const {sheet, SW, room, pix, shotOf, cut, side, push, flat} = S, {UP, PITCH, FH, cast, hid} = T;
  // ---- built blocks (floors.js): a floor's planks, a step, a roof's shingles. The game's own picture of the block: its 16 rows the top, the rows under them its face
  // a roof tile's place in its run north-south: up, down: tiles of roof north and south of it; yr: where the ridge is (tiles from the run's north edge); hat(v): px the roof stands over its eave there; split: the ridge crosses this tile
  function pitch(x, y, z) { const same = (dy) => { const c = Floors.get(x, y + dy, z); return !!c && c[0] === "roof" && !hid(x, y + dy, z); }; let up = 0, down = 0; while (up < 14 && same(-up - 1)) up++; while (down < 14 && same(down + 1)) down++;
    const n = up + down + 1, yr = Math.floor((n - 1) / 2) + .5, pk = PITCH * n / 2; return {up, down, yr, split: up === Math.floor(yr), hat: (v) => Math.round(v <= yr ? pk * v / yr : pk * (n - v) / (n - yr))}; }
  function block(out, kind, x, y, z) {
    const g = (dx, dy, dz = 0) => { const c = Floors.get(x + dx, y + dy, z + dz); return c && !hid(x + dx, y + dy, z + dz) ? c[0] : ""; }, same = (dx, dy) => g(dx, dy) === kind;
    if (kind === "roof") {                                  // shingles: a real roof, two pitched faces: up from its north edge to the ridge (the pack's ridge row: half way down its run), down from it to the eave; the eave its front, the gable its sides
      const {up, down, yr, hat} = pitch(x, y, z), w = same(-1, 0), e = same(1, 0);
      const rz = (z - 1) * UP + 7; cast(out, x, y, 0, [-1, -1, 17, 17], 0, rz - floorAt(x, y) * UP + hat(up + .5), true);   // (rz: the shingles' foot line: 7 px over its cell's floor, the walls' top: a roof lies on them, never hangs over a gap)
      const P = Structures.roofPx(up, down, w, e), E = pix(IMG.house_roof, 16, 64, 16, 7);
      const eave = room("eave", 16, 7, (put) => { for (let j = 0; j < 7; j++) for (let i = 0; i < 16; i++) put(i, j, E.px[j * 16 + i]); }), S = {px: sheet.px, w: SW, key: "eaveS"};
      for (const [y0, y1] of up === Math.floor(yr) ? [[0, 8], [8, 16]] : [[0, 16]]) { const d = y1 - y0, last = y1 === 16;
        push(out, {x: 0, y: y0, z: rz - 7, w: 16, d, h: 7, tilt: [hat(up + y0 / 16), hat(up + y1 / 16)], k: up + y0 / 16 < yr ? .7 : 1, top: cut(P, 0, 16, 7 + y0, 7 + y1), front: last && !down ? eave : null,
          west: w ? null : side(S, eave[0], eave[0] + 16, eave[1], eave[1] + 7, d, 0), east: e ? null : side(S, eave[0], eave[0] + 16, eave[1], eave[1] + 7, d, 1)}); }
      if (!up) push(out, {x: 0, y: -7, z: rz - 2, w: 16, d: 7, h: 2, top: cut(P, 0, 16, 0, 7)});      // (its scalloped far edge: over the wall's back)
      return;
    }
    const bits = [g(0, -1), g(-1, 0), g(1, 0), g(0, 1), g(0, 0, 1)].map((v) => (v ? 1 : 0)).join(""), stairs = kind === "stairs";
    if (stairs && !g(0, 0, 1)) {      // a step: two treads, the low half of its tile half its height, on the side it is climbed from
      const P = shotOf("st" + [x, y, z, Floors.ver, landVer], 16, FH, () => Floors.cell(kind, x, y, z, () => 0, () => shOf(z), 16, 1)), tone = P.px[(16 + UP / 2) * 16 + 7] || P.px[8 * 16 + 7] || 0xff5d6290;
      const [ux, uy] = [[0, -1], [1, 0], [-1, 0], [0, 1]].find(([dx, dy]) => solidAt(x + dx, y + dy, z + 1) && !solidAt(x + dx, y + dy, z + 2)) || [0, -1];
      for (const hi of [0, 1]) { const x0 = ux && (ux > 0) === !!hi ? 8 : 0, y0 = uy && (uy > 0) === !!hi ? 8 : 0, w = ux ? 8 : 16, d = uy ? 8 : 16, h = hi ? UP : UP / 2;
        push(out, {x: x0, y: y0, z: (z - 1) * UP, w, d, h, top: cut(P, x0, x0 + w, y0, y0 + d), front: cut(P, x0, x0 + w, FH - h, FH), west: flat(tone, d, h, tone), east: flat(tone, d, h, tone)}); }
      return;
    }
    cast(out, x, y, 0, [-1, -1, 17, 17], 0, (z - floorAt(x, y)) * UP, true);
    if (stairs) { const P = shotOf("st" + [x, y, z, Floors.ver, landVer], 16, FH, () => Floors.cell(kind, x, y, z, () => 0, () => shOf(z), 16, 1)), tone = P.px[(16 + UP / 2) * 16 + 7] || P.px[8 * 16 + 7] || 0xff5d6290;   // (a step under a block: its own picture)
      push(out, {x: 0, y: 0, z: (z - 1) * UP, w: 16, d: 16, h: UP, top: null, front: g(0, 1) ? null : cut(P, 0, 16, 16, FH), west: g(-1, 0) ? null : flat(tone, 16, UP, tone), east: g(1, 0) ? null : flat(tone, 16, UP, tone)}); return; }
    // planks: the pack's house floor on top, its line along the edges where no block goes on (north, west, east); its face a level of the pack's planks, 7 rows a course, a line over and under them
    const T = pix(IMG.house_walls, 16, 16, 16, 16), F = pix(IMG.house_walls, 56, 9, 16, 7), ink = Structures.look("W").ink, [n, w, e] = [g(0, -1), g(-1, 0), g(1, 0)], ends = (i) => (!w && i === 0) || (!e && i === 15);
    const top = room("plankT" + bits, 16, 16, (put) => { for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) put(i, j, (!n && j === 0) || ends(i) ? ink : T.px[j * 16 + i]); });
    const front = room("plankF" + bits, 16, UP, (put) => { for (let j = 0; j < UP; j++) for (let i = 0; i < 16; i++) put(i, j, j === 0 || j === UP - 1 || ends(i) ? ink : F.px[(j % 7) * 16 + i]); });
    const tone = F.px[((UP / 2) % 7) * 16 + 7];
    push(out, {x: 0, y: 0, z: (z - 1) * UP, w: 16, d: 16, h: UP, top: g(0, 0, 1) ? null : top, front: g(0, 1) ? null : front, west: w ? null : flat(tone, 16, UP, tone), east: e ? null : flat(tone, 16, UP, tone)});
  }
  return {pitch, block};
};
