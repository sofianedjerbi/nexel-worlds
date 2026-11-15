// What is built, drawn a piece at a time. A house was walls drawn as small blocks until they closed a room; then
// a roof and a tall front were drawn over the lot in one go: a house dropped onto the world. Now each wall is
// itself from the first one laid, and a roof is tiles laid one by one (the server keeps where: sim/roofing.py).
//   A wall is thin, as the pack's own house walls are and as a fence is: it stands in the middle of its tile and
//   everything of it is drawn on that tile (4 px over it), so it hides nothing behind it. Where nothing is built
//   south of it, it shows its front: a cap over planks, from the wall beside it (or its own middle) to the wall on
//   its other side. Where a wall goes on south of it, it shows its top: a band 6 px wide down the middle of the
//   tile, and the front of a wall joining it from a side runs up to that band; a band that comes down onto a
//   front runs into its cap. So a corner (upper or lower), a T and a crossing are one wall, a gap in a wall is a
//   gap, and a wall that ends has an end.
//   (Twice before: fronts one way and wide flat bands the other, which met badly; then blocks a tile high, whose
//   tops hid the row behind them, were seen through to make up for it, and turned a gap into a patch of planks.)
//   A door in a run east-west is the pack's door, as it is drawn. In a run north-south it is seen from above: the
//   band's two ends as its posts, the leaf between them (back against a post while someone goes through), and
//   under it the doorway's shadow, the dark of the game's holes.
//   Nothing is put on a wall that you did not put there (windows came by themselves, one wall in three).
//   A wall stands on the ground or on a built block (floors.js: upstairs): the walls it joins are those at its own
//   height.
//   A roof is a block like any other (floors.js), in shingles: its top edge scalloped where no roof is north of
//   it, its eave where none is south, its sides where none is beside it, the ridge half way down its run.
// Walls are never seen through: they are in nothing's way (those over your head go with the floor they stand on).
const Structures = (() => {
  const WALLS = "W%+", LIFT = 22, INK = "#754c60", CAP = "#c49a6c", STONE = ["#6f7471", "#b6bab1"];
  // (z: the height it stands at, upstairs; none: on the ground)
  const wall = (x, y, z) => WALLS.includes((z === undefined ? combAt(x, y) : Floors.thingAt(x, y, z)) || "-");
  const sideDoor = (x, y, z) => (z === undefined ? combAt(x, y) : Floors.thingAt(x, y, z)) === "+" && !wall(x - 1, y, z) && !wall(x + 1, y, z) && (wall(x, y - 1, z) || wall(x, y + 1, z));      // a door in a run north-south
  // A door: open while someone is by it (upstairs: someone at its height), and the sheet's frame for how far (5: shut)
  function doorFrame(x, y, z) {
    const by = (p) => Math.abs(Math.round(p.x) - x) + Math.abs(Math.round(p.y) - y) <= 1 && Floors.standOf(p, Math.round(p.x), Math.round(p.y)) === z;
    const key = x + "," + y + (z === undefined ? "" : "," + z);
    const near = z === undefined ? [[0, 0], [0, -1], [0, 1], [1, 0], [-1, 0]].some(([dx, dy]) => occupied.has((x + dx) + "," + (y + dy))) : [...ents.values()].some((p) => p.e && p.e.kind === "agent" && by(p));
    const was = doors.get(key) || 0, o = Math.max(0, Math.min(1, was + (near ? .15 : -.1))), now = performance.now();
    if (!was && o && now - (doorShut.get(key) || -1e9) > 700) sfx("gate", x, y);      // (heard when it opens, not again if it only just shut: someone hovering at the sill)
    if (was && !o) doorShut.set(key, now);
    doors.set(key, o);
    return 5 - Math.round(o * 5);
  }
  // One wall, on its own tile (UP px over it). a: how much of it is drawn (a plan's ghost is half there)
  const UP = 4, L = 5, R = 11;                          // how far over its tile it stands; the band's two edges
  function drawWall(c, x, y, sx, sy, S, now, a = 1, at) {
    const z = zoom, px = sx(x), py = sy(y, x) - UP * z, n = wall(x, y - 1, at), s = wall(x, y + 1, at), w = wall(x - 1, y, at), e = wall(x + 1, y, at), stone = c === "%";
    const ink = stone ? STONE[0] : INK, top = stone ? STONE[1] : CAP, x0 = w ? 0 : L, x1 = e ? 16 : R;
    const r = (col, X, Y, W_, H_) => { ctx.fillStyle = col; ctx.fillRect(px + X * z, py + Y * z, W_ * z, H_ * z); };
    const planks = (X, W_) => {                         // a wall's front: under its cap, the pack's planks (stone: its stones)
      if (W_ <= 0) return;
      if (stone) { const [gx, gy] = genCell("stone_wall"); ctx.drawImage(IMG.gen, gx + X, gy + 2, W_, 12, px + X * z, py + 4 * z, W_ * z, 12 * z); }
      else ctx.drawImage(IMG.house_walls, 56 + X, 4, W_, 12, px + X * z, py + 4 * z, W_ * z, 12 * z);
    };
    const cap = (X0, X1) => { r(top, X0, 1, X1 - X0, 3); r(ink, X0, 0, X1 - X0, 1); };
    ctx.globalAlpha = a;
    if (sideDoor(x, y, at)) {                               // seen from above: its posts, its leaf, the doorway's shadow under it
      [.3, .2, .1].forEach((al, k) => r(`rgba(${SHADE},${al})`, 3 - k, 4, 10 + 2 * k, 8));
      for (const Y of [0, 12]) { r(ink, L, Y, 6, 4); r(top, L + 1, Y + (Y ? 0 : 1), 4, 3); }
      if ((a >= 1 ? doorFrame(x, y, at) : 5) >= 3) { r(INK, 6, 4, 4, 8); r("#90625d", 7, 4, 2, 8); r("#e8cfa6", 7, 9, 1, 1); }       // shut: across the way
      else { r(INK, R, 3, 5, 4); r("#90625d", R, 4, 4, 2); }                                                                   // open: swung back from its post
    } else if (c === "+") {                             // the pack's door between its posts, a dark doorway behind it
      r("#4a3530", 3, 1, 10, 14);
      ctx.drawImage(IMG.door, (a >= 1 ? doorFrame(x, y, at) : 5) * 16, 0, 16, 16, px, py, S, S);
    } else if (!s) {                                    // nothing south of it: its front, from one side of it to the other
      planks(x0, x1 - x0); cap(x0, x1);
      if (!w) r(ink, x0, 0, 1, 16);
      if (!e) r(ink, x1 - 1, 0, 1, 16);
      if (n) r(top, L + 1, 0, R - L - 2, 1);           // (a wall comes down onto it: its band runs into this cap, no line across it)
    } else {                                            // a wall goes on south of it: its top, a band; a wall from a side joins it
      if (w) planks(0, L);
      if (e) planks(R, 16 - R);
      r(ink, L, 0, 1, 16); r(ink, R - 1, 0, 1, 16); r(top, L + 1, 0, R - L - 2, 16);
      if (w) { cap(0, L + 1); r(top, L, 1, 1, 3); }
      if (e) { cap(R - 1, 16); r(top, R - 1, 1, 1, 3); }
      if (!n) r(ink, L, 0, R - L, 1);
    }
    ctx.globalAlpha = 1;
  }
  // One roof block's top, at (px, top) on the screen: the middle of the sheet's roof, its edges laid over it where
  // the roof ends. up, down: how many roof blocks go on north and south of it; w, e: one beside it
  function drawRoof(px, top, S, up, down, w, e) {
    const z = zoom, row = up + down >= 2 && up === Math.floor((up + down) / 2) ? 2 : up % 2 ? 3 : 1;      // (the ridge half way down its run)
    const piece = (r, y0, h, at) => {
      ctx.drawImage(IMG.house_roof, 16, r * 16 + y0, 16, h, px, at, S, h * z);
      if (!w) ctx.drawImage(IMG.house_roof, 0, r * 16 + y0, 16, h, px - 11 * z, at, S, h * z);
      if (!e) ctx.drawImage(IMG.house_roof, 32, r * 16 + y0, 16, h, px + 11 * z, at, S, h * z);
    };
    piece(row, 0, 16, top);
    if (!up) piece(0, 9, 7, top - 7 * z);
    if (!down) piece(4, 0, 7, top + 16 * z);
  }
  return {WALLS, INK, drawWall, drawRoof, sideDoor};
})();
