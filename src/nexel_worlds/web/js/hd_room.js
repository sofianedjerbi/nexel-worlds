// Your room under a roof, for the HD look's things (hd_things.js): what is built over it is not drawn.
//   HdRoom() -> {hid(x, y, z): not drawn, south(): the room's southmost row}
const HdRoom = () => {
  // inside a house, the land's own rule (your space, vox_style_land.js): what is built over YOUR ROOM is not drawn (the roofed tiles walked to from yours on your level; a wall, a door stop it),
  // nor what is over the tiles right beside it and south of it (the eye's side); the north wall, its storeys and the roof over it stand whole: the room's back. (Round your body: hd_level.js place, one tile, not the walk's goal and key()'s tile apart) (Not all that is over your head: that leaves the house a low tray.) Build mode: the game's rule, over the cursor's level.
  let roomK = "", room0 = null, roomZ = 0, roomS = 0;
  function roomNow() { const P = HdLevel.place; if (!P || P.free) return null; const p = {x: P.tx, y: P.ty}, L = P.L, k = [p.x, p.y, L, Floors.ver, landVer].join(); if (k === roomK) return room0; roomK = k; room0 = null; roomZ = L; roomS = -1e9;
    const over = (x, y) => { const c = Floors.cells(x, y); if (c) for (const z of c.keys()) if (z > L) return true; return false; }; if (!over(p.x, p.y)) return null;
    const seen = new Set([p.x + "," + p.y]), q = [[p.x, p.y, 0]];
    for (let n = 0; n < q.length && q.length < 120; n++) { const [x, y, d] = q[n]; if (d < 10) for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const X = x + dx, Y = y + dy, k2 = X + "," + Y; if (seen.has(k2) || !over(X, Y) || [0, 1, 2, 3].some((dz) => Structures.WALLS.includes(Floors.thingAt(X, Y, L - dz) || "-"))) continue; seen.add(k2); q.push([X, Y, d + 1]); } }
    room0 = new Map(); for (const [x, y] of q) { roomS = Math.max(roomS, y); for (let dx = -1; dx <= 1; dx++) room0.set(x + dx, Math.min(room0.has(x + dx) ? room0.get(x + dx) : 1e9, y)); } return room0; }   // (a column -> the room's northmost row in it or beside it)
  const hid = (x, y, z) => { if (Build.on) return Floors.alpha(x, y, z) < 1; const r = roomNow(); if (!r || z <= roomZ) return false; const n = r.get(x); return n !== undefined && y >= n && y - n <= 14; };
  return {hid, south: () => roomS};
};
