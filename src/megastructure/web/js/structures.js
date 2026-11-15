// What is built, drawn a piece at a time. A house was walls drawn as small blocks until they closed a room; then
// a roof and a tall front were drawn over the lot in one go: a house dropped onto the world. Now each wall is
// itself from the first one laid, and a roof is tiles laid one by one (the server keeps where: sim/roofing.py).
//   A wall is thin, as the pack's own house walls are and as a fence is: it stands in the middle of its tile and
//   everything of it is drawn on that tile (4 px over it), so it hides nothing behind it. Where nothing is built
//   south of it, it shows its front: a cap over planks, from the wall beside it (or its own middle) to the wall on
//   its other side. Where a wall goes on south of it, it shows its top: a band 6 px wide down the middle of the
//   tile, and the front of a wall joining it from a side runs up to that band. So a corner, a T and a crossing are
//   one wall, a gap in a wall is a gap, and a wall that ends has an end.
//   (Twice before: fronts one way and wide flat bands the other, which met badly; then blocks a tile high, whose
//   tops hid the row behind them, were seen through to make up for it, and turned a gap into a patch of planks.)
//   A door in a run east-west is the pack's door, as it is drawn. In a run north-south it is seen from above: the
//   band's two ends as its posts, the leaf between them (back against a post while someone goes through), and
//   under it the doorway's shadow, the dark of the game's holes.
//   Nothing is put on a wall that you did not put there (windows came by themselves, one wall in three).
//   A roof tile is drawn over its tile, a tile and a bit up (on the walls): its top edge scalloped where no roof
//   is north of it, its eave where none is south, its sides where none is beside it, the ridge half way down its run.
// Where you stand under a roof, that whole roof is seen through; in build mode every roof is, so that what is
// under it can be planned. Walls are never seen through: they are in nothing's way.
// (A server from before roofs were laid by hand says so by not saying `roofs`: houses.js then draws as it did.)
let ROOFS = false, roofVer = 0;
const Structures = (() => {
  const WALLS = "W%+", LIFT = 22, INK = "#754c60", CAP = "#c49a6c", STONE = ["#6f7471", "#b6bab1"];
  const wall = (x, y) => WALLS.includes(combAt(x, y) || "-");
  const sideDoor = (x, y) => combAt(x, y) === "+" && !wall(x - 1, y) && !wall(x + 1, y) && (wall(x, y - 1) || wall(x, y + 1));      // a door in a run north-south
  const roofAt = (x, y) => { const t = tileIdx(x, y); return !!t && !!t[0].roofs && t[0].roofs.has(t[1]); };
  function setRoof(x, y, on) { const t = tileIdx(x, y); if (!t) return; (t[0].roofs || (t[0].roofs = new Set()))[on ? "add" : "delete"](t[1]); roofVer++; }
  // The roof you are under, as the set of its tiles ("x,y"): worked out again when you move or a roof changes
  let under = {at: "", ver: -1, tiles: new Set()};
  function mine() {
    const s = myPos(), at = s ? s.x + "," + s.y : "";
    if (at === under.at && roofVer === under.ver) return under.tiles;
    const tiles = new Set(), line = s && roofAt(s.x, s.y) ? [[s.x, s.y]] : [];
    if (line.length) tiles.add(at);
    for (let i = 0; i < line.length && i < 600; i++) for (const [dx, dy] of Object.values(DIRV)) {
      const x = line[i][0] + dx, y = line[i][1] + dy, k = x + "," + y;
      if (!tiles.has(k) && roofAt(x, y)) { tiles.add(k); line.push([x, y]); }
    }
    return (under = {at, ver: roofVer, tiles}).tiles;
  }
  const seeThrough = (x, y) => (mine().has(x + "," + y) ? .12 : Build.on ? .4 : 1);          // how much of the roof tile at (x, y) is drawn
  // A door: open while someone is by it (as houses.js has it), and the sheet's frame for how far (5: shut)
  function doorFrame(x, y) {
    const key = x + "," + y, near = [[0, 0], [0, -1], [0, 1], [1, 0], [-1, 0]].some(([dx, dy]) => occupied.has((x + dx) + "," + (y + dy)));
    const o = Math.max(0, Math.min(1, (doors.get(key) || 0) + (near ? .15 : -.1)));
    if (!(doors.get(key) || 0) && o) sfx("gate", x, y);
    doors.set(key, o);
    return 5 - Math.round(o * 5);
  }
  // One wall, on its own tile (UP px over it). a: how much of it is drawn (a plan's ghost is half there)
  const UP = 4, L = 5, R = 11;                          // how far over its tile it stands; the band's two edges
  function drawWall(c, x, y, sx, sy, S, now, a = 1) {
    const z = zoom, px = sx(x), py = sy(y, x) - UP * z, n = wall(x, y - 1), s = wall(x, y + 1), w = wall(x - 1, y), e = wall(x + 1, y), stone = c === "%";
    const ink = stone ? STONE[0] : INK, top = stone ? STONE[1] : CAP, x0 = w ? 0 : L, x1 = e ? 16 : R;
    const r = (col, X, Y, W_, H_) => { ctx.fillStyle = col; ctx.fillRect(px + X * z, py + Y * z, W_ * z, H_ * z); };
    const planks = (X, W_) => {                         // a wall's front: under its cap, the pack's planks (stone: its stones)
      if (W_ <= 0) return;
      if (stone) { const [gx, gy] = genCell("stone_wall"); ctx.drawImage(IMG.gen, gx + X, gy + 2, W_, 12, px + X * z, py + 4 * z, W_ * z, 12 * z); }
      else ctx.drawImage(IMG.house_walls, 56 + X, 4, W_, 12, px + X * z, py + 4 * z, W_ * z, 12 * z);
    };
    const cap = (X0, X1) => { r(top, X0, 1, X1 - X0, 3); r(ink, X0, 0, X1 - X0, 1); };
    ctx.globalAlpha = a;
    if (sideDoor(x, y)) {                               // seen from above: its posts, its leaf, the doorway's shadow under it
      [.3, .2, .1].forEach((al, k) => r(`rgba(${SHADE},${al})`, 3 - k, 4, 10 + 2 * k, 8));
      for (const Y of [0, 12]) { r(ink, L, Y, 6, 4); r(top, L + 1, Y + (Y ? 0 : 1), 4, 3); }
      if ((a === 1 ? doorFrame(x, y) : 5) >= 3) { r(INK, 6, 4, 4, 8); r("#90625d", 7, 4, 2, 8); r("#e8cfa6", 7, 9, 1, 1); }       // shut: across the way
      else { r(INK, R, 3, 5, 4); r("#90625d", R, 4, 4, 2); }                                                                   // open: swung back from its post
    } else if (c === "+") {                             // the pack's door between its posts, a dark doorway behind it
      r("#4a3530", 3, 1, 10, 14);
      ctx.drawImage(IMG.door, (a === 1 ? doorFrame(x, y) : 5) * 16, 0, 16, 16, px, py, S, S);
    } else if (!s) {                                    // nothing south of it: its front, from one side of it to the other
      planks(x0, x1 - x0); cap(x0, x1);
      if (!w) r(ink, x0, 0, 1, 16);
      if (!e) r(ink, x1 - 1, 0, 1, 16);
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
  // One roof tile: the middle of the sheet's roof, its edges laid over it where the roof ends
  function drawRoof(x, y, sx, sy, S, alpha = seeThrough(x, y)) {
    const z = zoom, px = sx(x), top = sy(y, x) - LIFT * z, n = roofAt(x, y - 1), s = roofAt(x, y + 1), w = roofAt(x - 1, y), e = roofAt(x + 1, y);
    let up = 0, down = 0;
    while (up < 14 && roofAt(x, y - up - 1)) up++;
    while (down < 14 && roofAt(x, y + down + 1)) down++;
    const row = up + down >= 2 && up === Math.floor((up + down) / 2) ? 2 : up % 2 ? 3 : 1;                 // (the ridge half way down its run)
    const piece = (r, y0, h, at) => {
      ctx.drawImage(IMG.house_roof, 16, r * 16 + y0, 16, h, px, at, S, h * z);
      if (!w) ctx.drawImage(IMG.house_roof, 0, r * 16 + y0, 16, h, px - 11 * z, at, S, h * z);
      if (!e) ctx.drawImage(IMG.house_roof, 32, r * 16 + y0, 16, h, px + 11 * z, at, S, h * z);
    };
    ctx.globalAlpha = alpha;
    piece(row, 0, 16, top);
    if (!n) piece(0, 9, 7, top - 7 * z);
    if (!s) piece(4, 0, 7, top + 16 * z);
    ctx.globalAlpha = 1;
  }
  // The frame's roof tiles, each in its place among the rest (after what stands on its tile, before the row south)
  function roofs(vis, list, sx, sy, S) {
    for (const b of vis) for (const i of b.roofs || []) {
      const x = b.bx * B + i % B, y = b.by * B + (i / B | 0);
      list.push({y: y + .6, x, fx: () => drawRoof(x, y, sx, sy, S)});
    }
  }
  return {WALLS, roofAt, setRoof, drawWall, drawRoof, roofs, seeThrough, sideDoor};
})();
