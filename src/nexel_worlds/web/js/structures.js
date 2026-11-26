// What is built, drawn a piece at a time, not a house dropped onto the world in one go (a roof and a tall front
// laid over the lot once small blocks of wall close a room). Each wall is
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
    const lately = now - (doorShut.get(key) || -1e9) < 700;                          // (not again if it only just began to shut: someone hovering at the sill)
    if (!was && o && !lately) sfx("gate", x, y);                                      // it opens: the latch, the swing
    if (was >= 1 && o < 1 && !lately) { sfx("door_close", x, y); doorShut.set(key, now); }   // it begins to shut: the swing, then it meets its frame as it gets there
    doors.set(key, o);
    return 5 - Math.round(o * 5);
  }
  // A WALL'S LOOK IS DATA: its line and its cap's colour (a px, as the land's paints are: 0xAABBGGRR), and where its front is in the pack:
  // 16 x 12 px, the house's planks, the stone wall's stones. The land's own painter lays them (hd_things.js wall: boxes in the land, lit as
  // the land's faces). (No painter of its own here: its colours and its front's place in the pack
  // are said once, here, not drawn off screen on a 2D canvas and read back out of it.)
  const abgr = (h) => (0xff000000 | parseInt(h.slice(5, 7), 16) << 16 | parseInt(h.slice(3, 5), 16) << 8 | parseInt(h.slice(1, 3), 16)) >>> 0;
  const look = (c) => (c === "%" ? {ink: abgr(STONE[0]), cap: abgr(STONE[1]), front: [IMG.gen, genCell("stone_wall")[0], genCell("stone_wall")[1] + 2]} : {ink: abgr(INK), cap: abgr(CAP), front: [IMG.house_walls, 56, 4]});
  // One roof block's top, as px (16 wide, 30 high: 7 rows over its tile, its 16, 7 under): the middle of the pack's roof, its edges laid over
  // it where the roof ends. up, down: how many roof blocks go on north and south of it; w, e: one beside it. (Made as px here, not painted on
  // a 2D canvas at the zoom and read back.)
  function roofPx(up, down, w, e) {
    const d = sheetData(IMG.house_roof), px = new Uint32Array(16 * 30), row = up + down >= 2 && up === Math.floor((up + down) / 2) ? 2 : up % 2 ? 3 : 1;      // (the ridge half way down its run)
    const lay = (sx, sy, h, at, dx) => { for (let k = 0; k < h; k++) for (let i = 0; i < 16; i++) { const X = i + dx, v = d.px[(sy + k) * d.w + sx + i]; if (X >= 0 && X < 16 && v >>> 24 > 127) px[(at + k) * 16 + X] = v; } };
    const piece = (r, y0, h, at) => { lay(16, r * 16 + y0, h, at, 0); if (!w) lay(0, r * 16 + y0, h, at, -11); if (!e) lay(32, r * 16 + y0, h, at, 11); };
    piece(row, 0, 16, 7);
    if (!up) piece(0, 9, 7, 0);
    if (!down) piece(4, 0, 7, 23);
    return {px, w: 16, h: 30, key: "roof" + [up, down, w, e]};
  }
  return {WALLS, INK, look, roofPx, sideDoor, doorFrame};
})();
