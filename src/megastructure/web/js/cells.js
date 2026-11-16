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
const floorAt = (x, y) => { const t = tileIdx(x, y); return t ? t[0].lv[t[1]].charCodeAt(0) - SEA : 0; };   // the lowest ground
function colAt(x, y) {
  const t = tileIdx(x, y); if (!t) return colSolid(0);
  const c = t[0].col ? t[0].col[t[1]] : undefined;
  return c === undefined ? colSolid(t[0].lv[t[1]].charCodeAt(0) - SEA) : c;
}
const topAt = (x, y) => colTop(colAt(x, y));                                    // the land as seen from above
const roofAt = (x, y) => { const t = tileIdx(x, y); return t && t[0].col && t[0].col[t[1]] !== undefined ? colTop(t[0].col[t[1]]) - floorAt(x, y) : 0; };   // over the lowest ground: how far up the land goes (0: open sky)
// What you walk on is the land and what is built over it (floors.js): a column with both. (colAt is the land alone:
// what is painted as land, and what a cave is under.)
const fullAt = (x, y) => (colAt(x, y) | Floors.mask(x, y)) >>> 0;
const solidAt = (x, y, z) => z < LOW || (z - LOW < 32 && (fullAt(x, y) >>> (z - LOW) & 1) === 1);
const landSolid = (x, y, z) => z < LOW || (z - LOW < 32 && (colAt(x, y) >>> (z - LOW) & 1) === 1);    // ...the land alone
const coveredAt = (x, y, z) => z - LOW < 31 && colAt(x, y) >>> (z - LOW + 1) !== 0;   // standing at z: land over you (a cave)
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

// The cave you're in is seen through the hill over it (caves.js): its tiles ("x,y") and the height of its floor there
let caveOpen = false, openCave = new Map();
const inOpenCave = (x, y) => caveOpen && openCave.has(x + "," + y);
// Floors the land is drawn with while this is set ("x,y" -> a height), in place of its top there: the open cave's
// while its overlay is drawn (caves.js); under ground that was dug, the place you are in, in the picture of it seen
// through what hides you (xray.js)
let peek = null;
// A hollow dug under level ground (its floor under sea level: only digging gets there; the land over it no higher
// than the meadow): a tunnel, a room. From above it is the ground over it. In it you are seen as in a hole with
// ground in front: through it (xray.js), you, the way you came and what is there, not as in a cave under a hill
// (caves.js: a pocket eight down showed four tiles from its stair, on the grass; and drawn open for good, you stood
// at its bottom while walking over it)
const dugHollow = (x, y) => roofAt(x, y) > 0 && floorAt(x, y) < 0 && topAt(x, y) <= 0;
const seenUnder = (x, y) => (xray.a > .01 && xray.pic ? xray.pic.floor.get(x + "," + y) : undefined);   // its floor there, where the place you are in is shown through its roof
const levelAt = (x, y) => { const v = peek ? peek.get(x + "," + y) : undefined; return v === undefined ? topAt(x, y) : v; };   // the height the land is drawn at
function standAt(x, y) {                    // ...and what's on the tile
  if (inOpenCave(x, y)) return openCave.get(x + "," + y);
  const f = roofAt(x, y) > 0 ? seenUnder(x, y) : undefined;
  return f === undefined ? topAt(x, y) : f;
}
// ...as the world has it, however it is drawn (what you can build on, take, climb): on its lowest ground, in the
// tunnel under a roof that was dug (seen through or not: build mode took a step for the ground over it, now and then)
const groundAt = (x, y) => (inOpenCave(x, y) ? openCave.get(x + "," + y) : dugHollow(x, y) ? floorAt(x, y) : topAt(x, y));
const hiddenAt = (x, y) => roofAt(x, y) > 0 && !inOpenCave(x, y) && seenUnder(x, y) === undefined;   // what lies on the lowest ground, under ground you're not in

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
