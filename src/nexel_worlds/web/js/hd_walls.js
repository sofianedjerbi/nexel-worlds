// The HD look's walls and doors (hd_things.js): thin boxes in the middle of their tile, a top to each, the planks of their
// fronts as many rows as they are px on the screen; a door shut or open, by who stands by it.
//   HdWalls(S, T) (S: HdSheet; T: {UP, KF, cast, plans, ghosting()}) -> {wall, planksTone, doorsAt, doorOpen}
const HdWalls = (S, T) => {
  const {sheet, SW, room, pix, solid, cut, push, flat} = S, {UP, KF, cast, plans} = T;
  // ---- walls, doors: thin, in the middle of their tile (structures.js: the band's 6 px), a top to each. h: its height in px of the land: a BLOCK (UP), as many rows of planks as it is px on the screen; under a built block up to it (a storey). One block of wall is one level: a wall reads as the cube it is
  const L0 = 5, R0 = 11, tint = (c) => Structures.look(c);   // (a wall's line and its cap's colour: structures.js)
  function planks(c, X, w, h) {   // a wall's front, as structures.js takes it: the pack's planks (stone: its stones), 12 rows; taller: its last rows again over them
    const stone = c === "%", P = pix(...Structures.look(c).front, 16, 12);
    return room("p" + [stone, X, w, h], w, h, (put) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const v = P.px[((j + 12 - (h % 12)) % 12) * 16 + X + i]; put(i, j, solid(v) ? v : P.px[5 * 16 + 1]); } });   // (the sprite's see-through corners: its line's colour)
  }
  const isWall = (x, y, z) => Structures.WALLS.includes(Floors.thingAt(x, y, z) || "-") || (T.ghosting() && plans.has(x + "," + y + "," + z));
  const doorsAt = new Map(), doorOpen = (x, y) => doorsAt.set(x + "," + y, [x, y]) && [[0, 0], [0, -1], [0, 1], [1, 0], [-1, 0]].some(([dx, dy]) => occupied.has((x + dx) + "," + (y + dy)));
  function wall(out, c, x, y, zl, h) {
    const n = isWall(x, y - 1, zl), s = isWall(x, y + 1, zl), w = isWall(x - 1, y, zl), e = isWall(x + 1, y, zl), T = tint(c), z = zl * UP;
    const rows = (hh) => Math.max(1, Math.round(hh * KF()));
    const part = (x0, x1, y0, y1, hh, ed, front, pc = c) => { cast(out, x, y, zl, [x0 - 1, y0 - 1, x1 + 1, y1 + 1], 0, hh); push(out, {x: x0, y: y0, z, w: x1 - x0, d: y1 - y0, h: hh, fh: rows(hh), top: flat(T.cap, x1 - x0, y1 - y0, T.ink, ed), front: front ? planks(pc, x0, x1 - x0, rows(hh)) : null,
      west: x0 === 0 ? null : flat(planksTone(pc), Math.min(16, y1 - y0), rows(hh), T.ink, "n"), east: x1 === 16 ? null : flat(planksTone(pc), Math.min(16, y1 - y0), rows(hh), T.ink, "n")}); };
    if (c === "+" && Structures.sideDoor(x, y, zl)) {      // a door in a run north-south: two posts, its leaf between them (open: swung away)
      part(L0, R0, 0, 4, h, "we", true); part(L0, R0, 12, 16, h, "wes", true);
      if (!doorOpen(x, y)) { const D = pix(IMG.door, 80, 0, 16, 16), lv = D.px[8 * 16 + 6]; push(out, {x: 6, y: 4, z, w: 4, d: 8, h: h * .9, fh: rows(h * .9), top: flat(lv, 4, 8, T.ink, "we"), west: flat(lv, 8, rows(h * .9), T.ink, "n"), east: flat(lv, 8, rows(h * .9), T.ink, "n")}); }
      return;
    }
    if (c === "+") {                                        // a door in a run east-west: the pack's door as it is drawn, the wall's planks over it up to what it holds
      const D = pix(IMG.door, (doorOpen(x, y) ? 0 : 5) * 16, 0, 16, 16), hh = Math.min(h, UP), fh = Math.min(16, rows(hh)), up = h - hh > .5 ? h - hh : 0, fu = rows(up);      // (a block high: the rows of it that fit, from its foot up; a taller storey: the wall's planks over it)
      cast(out, x, y, zl, [-1, L0 - 1, 17, R0 + 1], 0, h); push(out, {x: 0, y: L0, z, w: 16, d: 6, h: hh, fh, top: up ? null : flat(T.cap, 16, 6, T.ink, "ns"), front: cut(D, 0, 16, 16 - fh, 16), west: flat(T.ink, 6, fh, T.ink), east: flat(T.ink, 6, fh, T.ink)});
      if (up) push(out, {x: 0, y: L0, z: z + hh, w: 16, d: 6, h: up, fh: fu, top: flat(T.cap, 16, 6, T.ink, "ns"), front: planks(c, 0, 16, fu), west: flat(T.ink, 6, fu, T.ink), east: flat(T.ink, 6, fu, T.ink)});
      return;
    }
    const x0 = w ? 0 : L0, x1 = e ? 16 : R0;
    part(x0, x1, L0, R0, h, (n ? "" : "n") + (s ? "" : "s") + (w ? "" : "w") + (e ? "" : "e"), true);
    if (n) part(L0, R0, 0, L0, h, "we", false);
    if (s) part(L0, R0, R0, 16, h, "we", true);      // (a front to each: the wall south of it may be lower, cut open)
  }
  const tones = new Map(), planksTone = (c) => { let v = tones.get(c); if (v === undefined) { const u = planks(c, 0, 16, 12); v = sheet.px[(u[1] + 5) * SW + u[0] + 7]; tones.set(c, v); } return v; };
  return {wall, planksTone, doorsAt, doorOpen};
};
