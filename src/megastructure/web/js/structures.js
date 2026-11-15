// What is built, drawn a piece at a time. A house was walls drawn as small blocks until they closed a room; then
// a roof and a tall front were drawn over the lot in one go: a house dropped onto the world. Now each wall is
// itself from the first one laid, and a roof is tiles laid one by one (the server keeps where: sim/roofing.py).
//   A wall with nothing built south of it shows its front: the pack's plank wall, a tile high, its trim over it.
//   A wall with a wall south of it shows its top only (a run going north and south: one band).
//   A door in a run east-west is the pack's door in that front; in a run north-south, an opening under a lintel.
//   A roof tile is drawn over its tile, a tile and a bit up (on the walls): its top edge scalloped where no roof
//   is north of it, its eave where none is south, its sides where none is beside it, the ridge half way down its run.
// Where you stand under a roof, that whole roof is seen through, and so are the wall tops just south of you (they
// would hide you); in build mode every roof is, so that what is under it can be planned.
// (A server from before roofs were laid by hand says so by not saying `roofs`: houses.js then draws as it did.)
let ROOFS = false, roofVer = 0;
const Structures = (() => {
  const WALLS = "W%+", LIFT = 22, INK = "#754c60", CAP = "#c49a6c", BEVEL = "#b68962", STONE = ["#8a8f8c", "#b6bab1", "#9da89a"];
  const wall = (x, y) => WALLS.includes(combAt(x, y) || "-");
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
  // A wall's top, h px of it from y0 (art px over the tile's top): a plain cap, edged where nothing is built beside it
  function cap(px, py, z, y0, h, x, y, stone) {
    ctx.fillStyle = stone ? STONE[1] : CAP; ctx.fillRect(px, py + y0 * z, 16 * z, h * z);
    ctx.fillStyle = stone ? STONE[0] : INK;
    if (!wall(x - 1, y)) ctx.fillRect(px, py + y0 * z, z, h * z);
    if (!wall(x + 1, y)) ctx.fillRect(px + 15 * z, py + y0 * z, z, h * z);
    if (!wall(x, y - 1)) { ctx.fillRect(px, py + y0 * z, 16 * z, z); ctx.fillStyle = stone ? STONE[2] : BEVEL; ctx.fillRect(px + z, py + (y0 + 1) * z, 14 * z, z); }
  }
  function drawWall(c, x, y, sx, sy, S, now) {
    const z = zoom, px = sx(x), py = sy(y, x), south = wall(x, y + 1), w = wall(x - 1, y), e = wall(x + 1, y), stone = c === "%";
    const s = myPos(), hides = s && ((s.x === x && s.y === y - 1) || mine().has(x + "," + (y - 1)));        // (you are just behind it, or under the roof behind it)
    const side = c === "+" && !w && !e && (wall(x, y - 1) || south);                                        // a door in a run north-south
    if (south || side) {                               // its top only, a band going on south
      ctx.globalAlpha = hides ? .3 : side ? .55 : 1; cap(px, py, z, -8, 16, x, y, stone); ctx.globalAlpha = 1;
      return;
    }
    const [fx, fy] = FRONT[!w ? 0 : !e ? 2 : 1];
    if (stone) { const [gx, gy] = genCell("stone_wall"); ctx.drawImage(IMG.gen, gx, gy, 16, 16, px, py, S, S); }
    else { ctx.drawImage(IMG.house_walls, fx, fy + 8, 16, 8, px, py, S, 8 * z); ctx.drawImage(IMG.house_walls, fx, fy + 8, 16, 8, px, py + 8 * z, S, 8 * z); }
    if (c === "+") drawDoor(x, y, sx, sy, S, z, now);                                                       // (houses.js: the pack's door, which opens for you)
    else if (!stone && w && e) { let k = 0; while (k < 14 && wall(x - k - 1, y)) k++; if (k % 3 === 1 && combAt(x - 1, y) !== "+" && combAt(x + 1, y) !== "+") ctx.drawImage(IMG.gen, GEN.window * 16, 0, 16, 16, px, py - 5 * z, S, S); }
    ctx.globalAlpha = hides ? .3 : 1;                  // over it, its trim (seen through when it would hide you)
    if (stone) cap(px, py, z, -8, 8, x, y, true); else ctx.drawImage(IMG.house_walls, fx, fy, 16, 8, px, py - 8 * z, S, 8 * z);
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
  return {WALLS, roofAt, setRoof, drawWall, drawRoof, roofs, seeThrough};
})();
