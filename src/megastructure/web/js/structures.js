// What is built, drawn a piece at a time. A house was walls drawn as small blocks until they closed a room; then
// a roof and a tall front were drawn over the lot in one go: a house dropped onto the world. Now each wall is
// itself from the first one laid, and a roof is tiles laid one by one (the server keeps where: sim/roofing.py).
//   A wall is a block, a tile high: its top, drawn a tile up (over the tile north of it: it hides what is behind
//   it), the same for every wall, edged where no wall is beside it; and, where nothing is built south of it, its
//   front under that: the pack's planks (stone: its stones). So a wall running east is a band of top over a band of
//   front, one running north a band of top with a front at its south end, and they meet as one thing at a corner.
//   (They were two things: fronts with a trim over them one way, wide flat bands the other.)
//   A door in a run east-west is the pack's door in that front, as it is drawn (it was stretched). In a run
//   north-south it is seen from above, as the game's holes are: the wall's band is open over the door's own tile
//   (the top of the wall south of it is left out there, or it would hide the way through), dark in under the
//   lintel and lighter towards you, the band's edges going on as its posts, and the door's leaf across it, shut,
//   or back against a post while someone goes through.
//   Nothing is put on a wall that you did not put there (windows came by themselves, one wall in three).
//   A roof tile is drawn over its tile, a tile and a bit up (on the walls): its top edge scalloped where no roof
//   is north of it, its eave where none is south, its sides where none is beside it, the ridge half way down its run.
// Where you stand under a roof, that whole roof is seen through; so are the wall tops south of you and near (a
// wall a tile high hides the row behind it: you, and what you are at); in build mode every roof is, so that what
// is under it can be planned.
// (A server from before roofs were laid by hand says so by not saying `roofs`: houses.js then draws as it did.)
let ROOFS = false, roofVer = 0;
const Structures = (() => {
  const WALLS = "W%+", LIFT = 22, INK = "#754c60", CAP = "#c49a6c", BEVEL = "#b68962", STONE = ["#8a8f8c", "#b6bab1", "#9da89a"];
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
  // A wall's top: a plain cap a tile up, edged where no wall is beside it, a darker line along its south where its
  // front begins
  function cap(px, py, z, x, y, stone) {
    const top = py - 16 * z, open = (dx, dy) => !wall(x + dx, y + dy);
    ctx.fillStyle = stone ? STONE[1] : CAP; ctx.fillRect(px, top, 16 * z, 16 * z);
    ctx.fillStyle = stone ? STONE[2] : BEVEL;
    if (open(0, -1)) ctx.fillRect(px, top + z, 16 * z, z);
    if (open(0, 1)) ctx.fillRect(px, top + 14 * z, 16 * z, z);
    if (open(-1, 0)) ctx.fillRect(px + z, top, z, 16 * z);
    if (open(1, 0)) ctx.fillRect(px + 14 * z, top, z, 16 * z);
    ctx.fillStyle = stone ? STONE[0] : INK;
    if (open(-1, 0)) ctx.fillRect(px, top, z, 16 * z);
    if (open(1, 0)) ctx.fillRect(px + 15 * z, top, z, 16 * z);
    if (open(0, -1)) ctx.fillRect(px, top, 16 * z, z);
    if (open(0, 1)) ctx.fillRect(px, top + 15 * z, 16 * z, z);
  }
  // A door: open while someone is by it (as houses.js has it), and the sheet's frame for how far (5: shut)
  function doorFrame(x, y) {
    const key = x + "," + y, near = [[0, 0], [0, -1], [0, 1]].some(([dx, dy]) => occupied.has((x + dx) + "," + (y + dy)));
    const o = Math.max(0, Math.min(1, (doors.get(key) || 0) + (near ? .15 : -.1)));
    if (!(doors.get(key) || 0) && o) sfx("gate", x, y);
    doors.set(key, o);
    return 5 - Math.round(o * 5);
  }
  // The way through a door in a run north-south, on the door's own tile: shaded as a hole is (caves.js: its dark,
  // deepest in under the lintel), a post each side, and the leaf
  function passage(px, py, z, x, y, a) {
    const r = (c, X, Y, W_, H_) => { ctx.fillStyle = c; ctx.fillRect(px + X * z, py + Y * z, W_ * z, H_ * z); };
    ctx.globalAlpha = a;
    r(`rgba(${SHADE},.42)`, 2, 0, 12, 16);
    [.4, .28, .18, .09].forEach((al, k) => r(`rgba(${SHADE},${al})`, 2, k * 3, 12, 3));
    r(INK, 0, 0, 1, 16); r(BEVEL, 1, 0, 1, 16); r(BEVEL, 14, 0, 1, 16); r(INK, 15, 0, 1, 16);
    if ((a === 1 ? doorFrame(x, y) : 5) >= 3) { r(INK, 2, 6, 12, 4); r("#90625d", 2, 7, 12, 2); r("#e8cfa6", 11, 7, 1, 1); }      // shut: across the way
    else { r(INK, 2, 0, 3, 11); r("#90625d", 2, 1, 2, 9); }                                                                    // open: back against its post
    ctx.globalAlpha = 1;
  }
  // (a: how much of it is drawn: a plan's ghost is half there)
  function drawWall(c, x, y, sx, sy, S, now, a = 1) {
    const z = zoom, px = sx(x), py = sy(y, x), south = wall(x, y + 1), w = wall(x - 1, y), e = wall(x + 1, y), stone = c === "%";
    // (its top is seen through when it would hide where you are: you are north of it, near, or under the roof behind it)
    const s = myPos(), hides = a === 1 && s && ((s.y < y && y - s.y <= 4 && Math.abs(x - s.x) <= 5) || mine().has(x + "," + (y - 1)));
    const side = sideDoor(x, y);
    if (side) passage(px, py, z, x, y, a);
    else if (!south) {                                 // its front
      ctx.globalAlpha = a;
      if (c === "+") {                                 // the pack's door between its posts, a dark doorway behind it
        ctx.fillStyle = "#4a3530"; ctx.fillRect(px + 3 * z, py, 10 * z, 15 * z);
        ctx.drawImage(IMG.door, (a === 1 ? doorFrame(x, y) : 5) * 16, 0, 16, 16, px, py, S, S);
      } else if (stone) { const [gx, gy] = genCell("stone_wall"); ctx.drawImage(IMG.gen, gx, gy, 16, 16, px, py, S, S); }
      else { const [fx, fy] = FRONT[!w ? 0 : !e ? 2 : 1]; ctx.drawImage(IMG.house_walls, fx, fy + 8, 16, 8, px, py, S, 8 * z); ctx.drawImage(IMG.house_walls, fx, fy + 8, 16, 8, px, py + 8 * z, S, 8 * z); }
    }
    if (sideDoor(x, y - 1)) return;                    // (the wall south of such a door: its top would lie over the way through)
    ctx.globalAlpha = a * (hides ? .3 : 1);
    cap(px, py, z, x, y, stone);
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
