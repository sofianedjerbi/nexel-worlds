// The land is cells, solid or empty (gen.py): a tile's column is its 32 cells from the bottom (LOW) up, a bit each,
// set where the cell is solid; cell z is the block whose top is at height z, so land h high is solid up to cell h
// (0: sea level). Nothing else is kept about relief. A cave is empty cells with solid ones over them; a pit, a column
// dug low. A block of tiles (tiles.js) keeps a char a tile for its lowest ground (SEA + height) and, for the tiles
// where that isn't the whole story (a hollow under a hill), their column.

const SEA = 64, LOW = -16;
function tileIdx(x, y) { const b = blockOf(x, y); return b ? [b, (y - b.by * B) * B + (x - b.bx * B)] : null; }
const colSolid = (lv) => (lv - LOW >= 31 ? 0xFFFFFFFF : ((1 << (lv - LOW + 1)) - 1) >>> 0);   // a plain column: solid up to lv
const colTop = (c) => 31 - Math.clz32(c) + LOW;                                 // its highest solid cell
const colFloor = (c) => 30 - Math.clz32(~c & (c + 1)) + LOW;                    // the top of the solid cells standing on the bottom
// (floorAt, colAt and roofAt are asked for a tile many hundred times a frame: straight from its block, no pair made)
const floorAt = (x, y) => { const b = blockOf(x, y); return b ? b.lv[(y - b.by * B) * B + (x - b.bx * B)].charCodeAt(0) - SEA : 0; };   // the lowest ground
function colAt(x, y) {
  const b = blockOf(x, y); if (!b) return colSolid(0);
  const i = (y - b.by * B) * B + (x - b.bx * B), c = b.col ? b.col[i] : undefined;
  return c === undefined ? colSolid(b.lv[i].charCodeAt(0) - SEA) : c;
}
const topAt = (x, y) => colTop(colAt(x, y));                                    // the land as seen from above
const roofAt = (x, y) => { const b = blockOf(x, y), i = b ? (y - b.by * B) * B + (x - b.bx * B) : 0; return b && b.col && b.col[i] !== undefined ? colTop(b.col[i]) - (b.lv[i].charCodeAt(0) - SEA) : 0; };   // over the lowest ground: how far up the land goes (0: open sky)
// What you walk on is the land and what is built over it (floors.js): a column with both. (colAt is the land alone:
// what is painted as land, and what a cave is under.)
const fullAt = (x, y) => (colAt(x, y) | Floors.mask(x, y)) >>> 0;
const solidAt = (x, y, z) => z < LOW || (z - LOW < 32 && (fullAt(x, y) >>> (z - LOW) & 1) === 1);
const landSolid = (x, y, z) => z < LOW || (z - LOW < 32 && (colAt(x, y) >>> (z - LOW) & 1) === 1);    // ...the land alone
const coveredAt = (x, y, z) => z - LOW < 31 && colAt(x, y) >>> (z - LOW + 1) !== 0;   // standing at z: land over you (a cave)
function ceilAt(x, y, z) { let c = z; while (c - LOW < 31 && !landSolid(x, y, c + 1)) c++; return c; }   // ...and how high the room you stand in goes: the top of its last empty cell
function surfacesAt(x, y) {                 // every height you can stand at, lowest first
  const c = fullAt(x, y), tops = (c & ~(c >>> 1)) >>> 0, out = [];
  for (let i = 0; i < 32; i++) if (tops >>> i & 1) out.push(i + LOW);
  return out;
}
// as Movement.height: the ground at or under z here (the lowest ground, if none is)
function settleAt(x, y, z) { const s = surfacesAt(x, y), under = s.filter((v) => v <= z); return under.length ? under[under.length - 1] : s[0]; }
// as Movement.landing: the height a step from height h onto (x, y) lands at, or null (a wall). Where the cell at
// your body's height is solid you jump up onto it if it's ground (and nothing is over your head); where it's empty you step in and come down on the
// ground under you there (a fall, however far)
function landAt(h, x, y, fx, fy) {       // (fx, fy: the tile you step from: a jump needs room over your head there)
  let z = h;
  if (solidAt(x, y, h + 1)) z = solidAt(x, y, h + 2) || (fx !== undefined && solidAt(fx, fy, h + 2)) ? null : h + 1;
  else while (!solidAt(x, y, z)) z--;
  if (fx !== undefined && FLOORS && Floors.thingAt(fx, fy, h) === "l" && (z === null || !Climb.openAt(x, y, z))) {   // (on a ladder, into a wall: up it, climbing.js)
    const up = Climb.climb(h, fx, fy, x, y);
    if (up !== null) return up;
  }
  return z;
}

// Floors the land is drawn with while this is set ("x,y" -> a height), in place of its top there: the place you are
// in under a roof, in the picture of it seen through what hides you (xray.js)
let peek = null;
// A hollow: empty cells under solid ones, a cave under a hill, a tunnel or a room dug under the ground alike. From
// above it is the land over it, always. In it you are hidden, as behind a hill or down a hole, and seen the same one
// way: through what hides you (xray.js), you, the place you are in and what is there. (There were three ways: a cave
// under a hill was opened for good, flat, its floors where they are drawn and nothing round them: a stair dug down
// under a hill was squares of earth lying on the hill, tiles south of it.)
const hollow = (x, y) => roofAt(x, y) > 0;
const seenUnder = (x, y) => (xray.a > .01 && xray.pic ? xray.pic.floor.get(x + "," + y) : undefined);   // its floor there, where the place you are in is shown through its roof
const levelAt = (x, y) => { const v = peek ? peek.get(x + "," + y) : undefined; return v === undefined ? topAt(x, y) : v; };   // the height the land is drawn at
function standAt(x, y) { const f = roofAt(x, y) > 0 ? seenUnder(x, y) : undefined; return f === undefined ? topAt(x, y) : f; }   // ...and what's on the tile
// ...as the world has it, however it is drawn (what you can build on, take, climb): its lowest ground, where what is
// on a tile lies (under a roof: in the hollow, seen through or not)
const groundAt = floorAt;
const hiddenAt = (x, y) => roofAt(x, y) > 0 && seenUnder(x, y) === undefined;   // what lies on the lowest ground, under ground you're not in

let myAt = null, myWas = null;             // your tile and the height you stand at (caves.js keeps it, as the server does); and the tile before
const myZ = (x, y) => (myAt && myAt.x === x && myAt.y === y ? myAt.z : myAt && Math.abs(myAt.x - x) + Math.abs(myAt.y - y) <= 2 ? settleNear(x, y, myAt.z) : topAt(x, y));
function settleNear(x, y, z) { return surfacesAt(x, y).reduce((a, v) => (Math.abs(v - z) < Math.abs(a - z) ? v : a)); }   // the ground nearest z
function rimAt(x, y) {                      // as World.rim: lower ground around it (nothing built)
  const lv = floorAt(x, y);
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if ((dx || dy) && floorAt(x + dx, y + dy) < lv) return true;
  return false;
}
// for your own steps: from the height you're at on (x0, y0), is the tile beside it not a wall?
const canStep = (x0, y0, x1, y1) => landAt(myZ(x0, y0), x1, y1, x0, y0) !== null;
