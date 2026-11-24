// The land is cells, solid or empty (cells.py): a tile's column is its cells from the bottom (LOW) to the top (HIGH);
// cell z is the block whose top is at height z, so land h high is solid up to cell h (0: sea level). Nothing else is
// kept about relief. A cave is empty cells with solid ones over them; a pit, a column dug low. A column is kept as
// the heights where it changes, from the bottom up: solid up to the first, empty up to the second, solid up to the
// third... An odd count: a plain column is one height; a cave under a hill three (its floor, its ceiling, the hill's
// top). (It was 32 cells, -16 to 15, a bit each in a number: "make the underground reach -512 and the sky max block
// should be 512 too".) A block of tiles (tiles.js) keeps a char a tile for its lowest ground (SEA + height) and, for
// the tiles where that isn't the whole story (a hollow under a hill), their column.

const {sea: SEA, low: LOW, high: HIGH} = RULES, PLAIN = new Map();   // (SEA: a height's char here; who sends land says what it counted from, tiles.js: 64 before)
const APART = 24;                             // layers: further than that from you, up or down, is not of where you are (state.js: away; all the land was within it, before)
function tileIdx(x, y) { const b = blockOf(x, y); return b ? [b, (y - b.by * B) * B + (x - b.bx * B)] : null; }
const colSolid = (lv) => PLAIN.get(lv) || PLAIN.set(lv, [lv]).get(lv);            // a plain column: solid up to lv (one list a height, for every tile that is that)
const colTop = (c) => c[c.length - 1];                                          // its highest solid cell
const colFloor = (c) => c[0];                                                   // the top of the solid cells standing on the bottom
const colSame = (a, b) => a === b || (a.length === b.length && a.every((v, i) => v === b[i]));
function colHas(c, z) { for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; }   // is its cell z solid?
// A column as it comes from the server -> as it is kept. (From a server from before: 32 cells from -16 up, a bit each.)
function colIn(v) {
  if (typeof v !== "number") return v.length === 1 ? colSolid(v[0]) : v;
  const out = [];
  for (let i = 0; i < 32; i++) if ((v >>> i & 1) !== (i < 31 ? v >>> (i + 1) & 1 : 0)) out.push(i - 16);
  return out.length === 1 ? colSolid(out[0]) : out;
}
// (floorAt, colAt and roofAt are asked for a tile many hundred times a frame: straight from its block, no pair made)
const floorAt = (x, y) => { const b = blockOf(x, y); return b ? b.lv[(y - b.by * B) * B + (x - b.bx * B)].charCodeAt(0) - SEA : 0; };   // the lowest ground
function colAt(x, y) {
  const b = blockOf(x, y); if (!b) return colSolid(0);
  const i = (y - b.by * B) * B + (x - b.bx * B), c = b.col ? b.col[i] : undefined;
  return c === undefined ? colSolid(b.lv[i].charCodeAt(0) - SEA) : c;
}
const topAt = (x, y) => colTop(colAt(x, y));                                    // the land as seen from above
const roofAt = (x, y) => { const b = blockOf(x, y), i = b ? (y - b.by * B) * B + (x - b.bx * B) : 0; return b && b.col && b.col[i] !== undefined ? colTop(b.col[i]) - (b.lv[i].charCodeAt(0) - SEA) : 0; };   // over the lowest ground: how far up the land goes (0: open sky)
// What you walk on is the land and what is built over it (floors.js: a block built is one more solid cell of its
// tile). (colAt is the land alone: what is painted as land, and what a cave is under.)
const landSolid = (x, y, z) => z < LOW || colHas(colAt(x, y), z);               // ...the land alone
const solidAt = (x, y, z) => landSolid(x, y, z) || Floors.built(x, y, z);
function surfacesAt(x, y) {                 // every height you can stand at, lowest first
  const c = colAt(x, y), over = Floors.cells(x, y), out = [];
  for (let i = 0; i < c.length; i += 2) if (!over || !over.has(c[i] + 1)) out.push(c[i]);
  if (over) { for (const z of over.keys()) if (!over.has(z + 1) && !colHas(c, z + 1)) out.push(z); out.sort((p, q) => p - q); }
  return out;
}
// as Movement.height: the ground at or under z here (the lowest ground, if none is)
function settleAt(x, y, z) { const s = surfacesAt(x, y), under = s.filter((v) => v <= z); return under.length ? under[under.length - 1] : s[0]; }
// as Movement.landing: the height a step from height h onto (x, y) lands at, or null (a wall). A body is one cell
// (h + 1). Where that cell is solid there it is a step: you jump up onto it if you jump (`jump`: false, a walk that
// did not: walk.js springs) and nothing is over it nor over your head; where it's empty you step in and come down
// on the ground under you there (a fall, however far)
function landAt(h, x, y, fx, fy, jump = true) {       // (fx, fy: the tile you step from: a jump needs room over your head there)
  let z = h;
  const stair = (sx, sy, sz) => { const c = FLOORS && sx !== undefined ? Floors.get(sx, sy, sz) : null; return !!c && c[0] === "stairs"; };
  jump = jump || stair(x, y, h + 1) || stair(fx, fy, h);      // (stairs are walked up: onto a step of them, or off the top one)
  if (solidAt(x, y, h + 1)) z = !jump || solidAt(x, y, h + 2) || (fx !== undefined && solidAt(fx, fy, h + 2)) ? null : h + 1;
  else z = settleAt(x, y, h);                           // (in at your height, down on the ground under you: the one rule, settleAt)
  if (fx !== undefined && FLOORS && Floors.thingAt(fx, fy, h) === "l" && (z === null || !Climb.openAt(x, y, z))) {   // (on a ladder, into a wall: up it, climbing.js)
    const up = Climb.climb(h, fx, fy, x, y);
    if (up !== null) return up;
  }
  return z;
}

// Floors the land is painted with while this is set ("x,y" -> a height), in place of its top there (voxels.js paintTop)
let peek = null;
// A hollow: empty cells under solid ones, a cave under a hill, a tunnel or a room dug under the ground alike. From
// above it is the land over it, always. In it you are seen through the HD look's x-ray window (hd.js).
const hollow = (x, y) => roofAt(x, y) > 0;
const levelAt = (x, y) => { const v = peek ? peek.get(x + "," + y) : undefined; return v === undefined ? topAt(x, y) : v; };   // the height the land is drawn at
const standAt = (x, y) => topAt(x, y);   // ...and what's on the tile (the HD look puts what grows under a roof on its own floor: hd.js standAt)
// ...as the world has it, however it is drawn (what you can build on, take, climb): its lowest ground, where what is
// on a tile lies (under a roof: in the hollow, seen through or not)
const groundAt = floorAt;
// the block somebody put on the tile's top (landblocks.py): "s" stone, "d" earth; "": none, the land is what its height says
const rockAt = (x, y) => { const b = blockOf(x, y); return !!(b && b.rock && b.rock[(y - b.by * B) * B + (x - b.bx * B)]); };   // is the tile's column stone (the world's own word: tiles.js putMat)
const matAt = (x, y) => { const b = blockOf(x, y); return (b && b.mat && b.mat[(y - b.by * B) * B + (x - b.bx * B)]) || ""; };

let myAt = null, myWas = null;             // your tile and the height you stand at (caves.js keeps it, as the server does); and the tile before
const myZ = (x, y) => (myAt && myAt.x === x && myAt.y === y ? myAt.z : myAt && Math.abs(myAt.x - x) + Math.abs(myAt.y - y) <= 2 ? settleNear(x, y, myAt.z) : topAt(x, y));
function settleNear(x, y, z) { return surfacesAt(x, y).reduce((a, v) => (Math.abs(v - z) < Math.abs(a - z) ? v : a)); }   // the ground nearest z
function rimAt(x, y) {                      // as World.rim: lower ground around it (nothing built)
  const lv = floorAt(x, y);
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if ((dx || dy) && floorAt(x + dx, y + dy) < lv) return true;
  return false;
}
// Can a body be there? The one answer (the server's: sim/bodies.py stand, from the same table). A tile `t` ([what is
// on it, its ground]): ground to walk on with nothing solid on it; water, for who swims (on top of it, whatever its
// depth, or into a moored boat). At height z on (x, y): on a built block, what stands on that block is what counts
// (floors.js); on the land over the tile's lowest ground, nothing is (what is on a tile lies on its lowest ground).
const standOn = (t, swims = true) => !!t && (wet(t[1]) ? swims && (t[0] === "V" || !SOLID.has(t[0])) : WALKABLE_GROUND.has(t[1]) && !SOLID.has(t[0]));
function stand(x, y, z, swims) {
  const c = z === undefined || !FLOORS ? null : Floors.get(x, y, z);
  return c ? !SOLID.has(c[1]) : (z !== undefined && z !== floorAt(x, y)) || standOn(tile(x, y), swims);
}
