// VOX: YOUR SPACE and THE CUT for one land asked of vox_style_land.js (steps): where you can walk, drop to and came down from (the flood),
// the x-ray window's boxes over it and the hollows beside it, and how far the land over it is cut. Split out of VoxStyleLand's create (#154):
// the same code, given what it reads of that land (K: host, real: a column as it is, topOf, inBox and at: the land's box and a tile's place
// in it, cx, cy, r: its middle and reach, L: your level, pt: the window's settings (null: none), D, NO, BIG, DIR: the box's side and its marks, solidC: is a column's cell solid).
//   VoxLandSpace(K) -> {hollow, hop, floorOf, inTo, mouth, upsOf: the game's own walk over that land; flood(): your space into the
//     reach arrays; boxes() -> win: the window's boxes; cut(cutH): the cut's height a column; reachA, clsA, reached, win, sky0}
const VoxLandSpace = ({host, real, topOf, inBox, at, cx, cy, r, L, pt, D, NO, BIG, DIR, solidC}) => {
  const reachA = new Int16Array(D * D).fill(NO), farA = new Uint8Array(D * D), nearA = new Uint8Array(D * D), clsA = new Uint8Array(D * D), lowA = new Int16Array(D * D).fill(BIG), reached = [], win = [];
  // HOLLOW: a top under the open sky at f with land over it (f + 1) within 12 tiles NORTH of it (land south hides it: host.sunk), or both east and west: a trench, a pit, a gorge's floor, a strip under a cliff.
  // (north alone, not north and south both: a strip's ends past the plateau south of it, its corners leaning over them, open too)
  // Only such a tile, land hiding it, carries your space on and is a box of the window (the near ones aside). (Not any tile land hides: at a mountain's north foot every meadow tile behind the
  // mountain would be "your space", 24 tiles each way: the mountain cut away over half the screen, "the whole world disappears, the camera behind the mountain x-raying everything")
  const hollow = (x, y, f) => { const s = [[0, -1], [0, 1], [-1, 0], [1, 0]].map(([dx, dy]) => { for (let j = 1; j <= 12; j++) if (topOf(x + dx * j, y + dy * j) > f) return 1; return 0; }); return s[0] || (s[2] && s[3]); };
  const hop = (x0, y0, x1, y1, h) => { const a = real(x0, y0), b = real(x1, y1); return !!a && !!b && solidC(a, h) && !solidC(a, h + 1) && !solidC(a, h + 2) && solidC(b, h + 1) && !solidC(b, h + 2); };   // (the game's own rule: from a floor at h a jump up one level, room over it and over your head)
  // where a step from (x0, y0) at f0 onto (x, y) lands, by the game's own walk: level, up one (hop), or down any drop with nothing in the way -> the floor's level (as a drop of two or more: + .5: no way back up), or null: a wall
  // (not any floor within two levels: a stair's treads two levels over a dead end would be "your space", lit and lipped as the next step)
  const floorOf = (x0, y0, x, y, f0) => { const c = real(x, y); if (!c || !c.length) return null; if (host.water && host.water(x, y) && host.waterTop) { const w = host.waterTop(x, y); if (w >= c[c.length - 1]) return Math.abs(w - f0) <= 1 ? w : null; }
    if (solidC(c, f0 + 1)) return hop(x0, y0, x, y, f0) || (host.water && host.water(x0, y0) && !solidC(c, f0 + 2)) ? f0 + 1 : null; for (let dz = 0; dz <= 8; dz++) if (solidC(c, f0 - dz)) return f0 - dz + (dz > 1 ? .5 : 0); return null; };
  // A MOUTH: from the open floor f on (ox, oy) a step by the game's own walk into (mx, my) lands under land (a roof over your head), and on from there, straight in, under land again:
  // a way in. A wall (no step in), a ledge of one tile over the ground (no way on from under it), water: none
  const inTo = (x0, y0, x, y, f) => { if (host.water && host.water(x, y)) return null; const g = floorOf(x0, y0, x, y, f); return g !== null && g % 1 === 0 && topOf(x, y) > g + 1 ? g : null; };
  const mouth = (ox, oy, f, mx, my) => { if (host.water && host.water(ox, oy)) return false; const g = inTo(ox, oy, mx, my, f); return g !== null && inTo(mx, my, 2 * mx - ox, 2 * my - oy, g) !== null; };
  // from a floor at f0 on (x0, y0): the floors of (x, y) over it (up to 8 levels) from which a step lands on f0: the way you came down by
  const upsOf = (x0, y0, x, y, f0) => { const c = real(x, y), l = []; if (c) for (let j = 0; j < c.length; j += 2) { const f = c[j]; if (f > f0 && f <= f0 + 8) { const g = floorOf(x, y, x0, y0, f); if (g !== null && Math.floor(g) === f0) l.push(f); } } return l; };
  let sky0 = false;
  function flood() {
    // YOUR SPACE, three passes: 1 where you can WALK, there and back; 2 from there where you can only drop to and on from there; 3 the floors you could have dropped FROM, and on from those (the stair over the room you
    // dropped into). The window is on all three, so a walk along one cave, down its drops, does not change it (with 1 and 2 alone the step off a stair into a room is another space, another hole, in one frame:
    // a quarter of the px). Only the LIGHT tells them apart (cls -> the painter's light of the space, vox_style.js: 1 warm, 2 dimmer, 3 cold), and that eases. A tile has ONE level: a floor under the land
    // before one under the sky (the meadow over a room is of your space too, by the stair's mouth: found first it kept the room shut till you were near), else the first found; the flood goes on through its other floors (treads over a passage)
    if (pt) { let L0 = L; const c0 = real(cx, cy); if (c0 && !(host.water && host.water(cx, cy))) for (let n = 0; n < 8 && !solidC(c0, L0); n++) L0--;   // (in the air, a jump, a fall: your space is the floor's under you. From a level in mid air the flood found another space for the frames of a fall: the picture flashed)
      sky0 = topOf(cx, cy) <= L0; const i0 = at(cx, cy), lim = pt.reach ?? Infinity, nodes = [[cx, cy, L0, 0]], seenN = new Set([i0 * 2048 + L0 + 1024]); reachA[i0] = L0; clsA[i0] = 1; nearA[i0] = 1; reached.push(i0);
      for (const pass of pt.walk ? [1, 2] : [1, 2, 3]) { let fr = nodes.slice();
        for (let d = 1; d <= lim && fr.length; d++) { const nx = []; for (const [x, y, f0, o] of fr) { if (o > 4) continue; for (const [dx, dy] of DIR) { const X = x + dx, Y = y + dy, i = at(X, Y); if (i < 0) continue; const f1 = floorOf(x, y, X, Y, f0), l = pass > 2 ? upsOf(x, y, X, Y, f0) : [];   // (o: steps under the open sky since the last floor under the land: the flood stops five out on a meadow: it ran over the whole surface, 8 ms of one frame, for nothing: only what is under land is looked into)
          if (f1 !== null && (pass > 1 || f1 % 1 === 0)) l.push(Math.floor(f1));
          for (const f of l) { const k = i * 2048 + f + 1024; if (seenN.has(k) || (sky0 && topOf(X, Y) > f && Math.abs(X - cx) + Math.abs(Y - cy) > 2)) continue; seenN.add(k); nx.push([X, Y, f, topOf(X, Y) <= f && !(host.sunk && hollow(X, Y, f) && host.sunk(X, Y, f)) ? o + 1 : 0]);
            if (reachA[i] === NO) { reachA[i] = f; clsA[i] = pass; reached.push(i); if (d > 2 || pass > 1) farA[i] = 1; if ((d <= 4 && pass === 1) || (pt.walk && Math.abs(X - cx) + Math.abs(Y - cy) <= 4)) nearA[i] = 1; } else if (farA[i] && topOf(X, Y) <= reachA[i] && topOf(X, Y) > f) { reachA[i] = f; clsA[i] = pass; } } } } for (const q of nx) nodes.push(q); fr = nx; } }
      for (const [x, y, f] of nodes) { const i = at(x, y); if (f < lowA[i] && reachA[i] - f <= 4) lowA[i] = f; } }   // (lowA: where a tile has two floors of your space near each other, treads over a passage: the lower: the window goes down to it whichever you stand on)
  }
  function boxes() {
    // THE WINDOW'S BOXES: a floor of your space under the land: from it (the lower of two near each other) up to its ceiling, six levels at most; under the open sky (a shaft, a trench, a gorge's floor) only
    // the sunk tiles within four steps of you, each up to the rim of the land beside it: what stands between the eye and you is looked through, the rest of the gorge is as it is;
    // the ones land hides (host.sunk) as far as your space goes (not a square five tiles round you: the gorge's river is shut past it; nor four steps, a diamond: its stairs leave notches of the cliff's top standing in the river)
    for (const i of reached) { const x = cx - r + i % D, y = cy - r + (i / D | 0), f = reachA[i], tp = topOf(x, y), c = real(x, y);
      if (pt.walk && (Math.abs(x - cx) + Math.abs(y - cy) > 2 || f < L - 3)) continue;   // (from the surface only what you are about to step into: two tiles off, three levels down at most: a tunnel was opened through its hill's front from four tiles away, a room from the hill over it)
      if (tp > f) { let z = f; while (z < f + 6 && !solidC(c, z + 1)) z++; win.push([x, y, Math.min(f, lowA[i]), Math.max(z, f + 1)]); }
      else if (nearA[i] || (clsA[i] === 1 && !!host.sunk && hollow(x, y, f) && host.sunk(x, y, f))) { let h = f + 1, n = 0; for (const [dx, dy] of DIR) { const t = topOf(x + dx, y + dy); if (t >= f + 2) n++; h = Math.max(h, Math.min(f + 40, t)); } const hid = !!host.sunk && host.sunk(x, y, f); if (hid) win.push([x, y, f, n > 2 ? h : f + 2, 1]); } }   // (host.sunk(x, y, f): the HOST's one answer to "is this tile under the open sky IN the land": land hides it from the eye and stands north of it too: a pit, a trench, a gorge's floor; the ground behind a hill or a wall is not, and is never a box: standing on a small hill its top was opened onto the meadow behind it. Only those: a meadow tile near you no land hides was put in the window too, a tall pale notch north of doben1 on his strip. Walls on three sides or four, a shaft: up to its rim, the window joins its mouth; else two levels: in a gorge the boxes stood as high as its banks, their long edges drawn down the far bank)
    // OTHER SPACES: a hollow beside the window (three tiles out at most, its floor near your floors' heights): the passage past a wall, the treads you cannot reach: the window is on it too. Its floor is not of your space:
    // the painter draws it cold, at its own height: it is seen where the way on is
    if (pt && !pt.walk && !sky0) { const own = new Set(win.map((t) => t[0] + "," + t[1])); let fr = win.slice();
      for (let d = 0; d < 3 && fr.length; d++) { const nx = []; for (const [x, y, lo, hi] of fr) for (const [dx, dy] of DIR) { const X = x + dx, Y = y + dy, k = X + "," + Y, c = own.has(k) || !inBox(X, Y) ? null : real(X, Y); if (!c) continue;
        for (let j = 0; j + 2 < c.length; j += 2) if (c[j] >= lo - 4 && c[j] <= hi + 6) { own.add(k); const t = [X, Y, c[j], Math.min(c[j] + 6, c[j + 1])]; win.push(t); nx.push(t); break; } } fr = nx; } }
    return win;
  }
  function cut(cutH) {
    // THE CUT (the owner's pick, the mockup page: "under the land, the real blocks round you"; "the whole cave should show up to the player, not a small
    // radius"): covered by the land, it is not drawn over YOUR SPACE (the window's boxes: every floor you can walk or drop to, the whole cave, as far
    // as the land made round you: the view's) and the tile of land round each, at that floor's head: every wall of your cave a block of its own earth or stone, two levels high
    // NOTHING HIDDEN IS SHOWN (the owner: "x-ray should not allow to see ores in wall"): the cut shows the land's cells as land, earth or stone, never
    // what is in them; what stands on the land cut is not drawn (hd.js cutOff): an ore over your tunnel is not seen from under it. Ore in a wall, when the
    // land has it, is seen where a face of it opens onto your space, not on the cut
    // ...and south of your space the eye's line to its floor's near edge (58 degrees down, a level half a tile: k tiles out, 3.2 (k - 1) levels over it):
    // nothing between the eye and you, nor your floors (a wall two levels high a tile south of you hid you)
    const cutAt = (x, y, h) => { if (topOf(x, y) <= h) return; const k = x * 1048576 + y, was = cutH.get(k); if (was === undefined || h < was) cutH.set(k, h); };
    // (only UNDER the land: land over your own head. Behind a mountain on the surface its caves stay shut, the owner: "being behind a mountain shouldn't show the caves")
    if (pt && !pt.walk && topOf(cx, cy) > L + 2) for (const [x, y, lo] of win) {
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) cutAt(x + dx, y + dy, lo + 2);
      for (let k = 1; k <= 4; k++) cutAt(x, y + k, lo + Math.floor(3.2 * (k - 1)));
    }
    if (cutH.size) for (const [x, y, lo] of win) { const kk = x * 1048576 + y, h = cutH.get(kk); if (h < lo) cutH.set(kk, lo); }
    // (nothing hidden is shown: outside your space the cut never opens air. A column with air under the cut (a cave no way joins, a room not yours) keeps a
    // cell of its roof over it: it stays under the land)
    if (cutH.size) { const own = new Set(win.map((t) => t[0] * 1048576 + t[1])); for (const [kk, h] of cutH) { if (own.has(kk)) continue;
      const c = real(Math.round(kk / 1048576), kk - Math.round(kk / 1048576) * 1048576); let keep = h; for (let j = 1; j < c.length; j += 2) if (c[j] < c[c.length - 1] && c[j - 1] < keep) keep = Math.max(keep, c[j] + 1); if (keep > h) cutH.set(kk, keep); } }   // (a floor of your space is never cut: a step up south of a lower one stays)
  }
  return {hollow, hop, floorOf, inTo, mouth, upsOf, flood, boxes, cut, reachA, clsA, reached, win, get sky0() { return sky0; }};
};
