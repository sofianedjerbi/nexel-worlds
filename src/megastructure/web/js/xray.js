// The one way you are seen when you are hidden: behind a wall or a mountain, down a hole, under a roof (a cave under
// a hill, a tunnel dug under the meadow). The land is blocks (voxels.js) and is always drawn as it is; where you are
// hidden the land is cut open over the whole place you are in: its roof is left out, the land in front of it down
// to its floor, and the rock round it down to its ceiling, so the place is seen with its walls standing (the engine
// does that, a tile at a time: vox_engine.js `cut`). This file says when you are hidden and how much (xrayLook),
// which tiles are cut and how low (xrayFind), and what else goes with it: the place you are in (the ground you could walk or drop to from where you
// stand), whose floors under a roof are where things on them stand (cells.js seenUnder); the rock in the way (of
// the mass that hides you, the tiles on the line of sight to that place), on which what stands fades; and who shows
// through. Nothing is painted here. (The land was painted flat, and this file painted a second picture of it
// without the rock, a few tiles round you, with xraycut.js and xrayviews.js: git tag flat-land.)

// r, core: the window's radius (tiles) and the part of it that is clear for what fades. It comes when you're really
// hidden, not for an edge that hides your legs or a post you walk past: body: your height, feet to ears (art px);
// from, full: the share of you that's hidden where it starts and where it is whole; wait: seconds hidden before it
// comes; far: tiles south to look for ground drawn up over you; near: how far from your tile (tiles) the place you
// are in goes
// wide: how far from your tile ground that was dug, or is under a roof, is of that place (all of a cave, a tunnel)
const XRAY = {even: true, r: 3.1, core: .42, body: 18, from: .5, full: .6, wait: .15, far: 12, near: 4.1, wide: 14};
// how strong, the height you stand at, your row, the window's centre (tiles, as drawn), how long you've been hidden,
// and what was found for where you are (pic: {key, floor: "x,y" -> the place's floor under a roof, rock: the tiles
// of the rock in the way, place: the tiles of the place, cut: "x,y" -> the level that tile is cut down to})
const xray = {a: 0, L: 0, row: 0, x: 0, y: 0, t: 0, pic: null};
const xrayRock = (tx, ty) => !!xray.pic && xray.pic.rock.has(tx + "," + ty);
// The place you are in: the ground you could walk or drop to from your tile (your height, a step up, or lower; no
// rock on the way), no further than XRAY.near; and, in ground that was dug, all you could walk to under sea level: up
// its steps too; and under a roof of any kind (a cave, a tunnel, a room: cells.js), so that the way you came stays
// seen as you go down it (a step down, the one two behind you was out of the place: it closed); and, there, what is open onto the room you are in though no step leads to it: a floor higher up beside you, under your room's top (dug down two layers at a tunnel's end, the tunnel was a wall to climb: gone from the picture, you in a hole in the rock: "how did he get there ? where's the exit ? why the tunnel is invisible ??"). -> {cols: column of
// tiles -> its rows of that ground, z: "x,y" -> its height there}. Ground that was dug or is under a roof is of it
// as far as XRAY.wide: all of the tunnel, the room or the cave on the screen ("underground vision should display as
// much as player can see"; it stopped four tiles from you, a fire a little further on not seen); how much of it
// light shows: cavelight.js
function xrayPlace(tx, row, L) {
  const far = XRAY.wide, h0 = settleNear(tx, row, L), cols = new Map(), z = new Map([[tx + "," + row, h0]]), todo = [[tx, row, h0]], by = new Map();   // (h0: your tile's own height: stepping off it down a stair, L is already the next one's)
  while (todo.length) {
    const [x, y, h, past] = todo.pop();
    if (!past) { if (!cols.has(x)) cols.set(x, []); cols.get(x).push(y); }
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy, key = nx + "," + ny;
      if (tile(nx, ny) === null) continue;
      // (every height of that tile you get to from here: the one you walk or drop to, and what is open onto this room. A tile that is of the place at another height is gone by at this one, not drawn twice: a tunnel dug under a tunnel, the upper one went on to its way out and none of it was seen past where it is over you, "the cave extend and has an exit, but im unable to see it")
      const lv = levelAt(nx, ny), top = ceilAt(x, y, h), ws = lv <= L + 1 ? [lv] : [landAt(h, nx, ny, x, y), ...surfacesAt(nx, ny).filter((s) => s > h && s < top)].filter((w) => w !== null && (w === lv ? w < 0 : coveredAt(nx, ny, w)));
      for (const h2 of new Set(ws)) if ((nx - tx) ** 2 + (ny - row) ** 2 <= XRAY.near ** 2 || ((h2 < 0 || h2 < lv) && Math.max(Math.abs(nx - tx), Math.abs(ny - row)) <= far)) { if (!z.has(key)) { z.set(key, h2); todo.push([nx, ny, h2]); } else if (z.get(key) !== h2 && !(by.get(key) || []).includes(h2)) { by.set(key, [...(by.get(key) || []), h2]); todo.push([nx, ny, h2, true]); } }
    }
  }
  return {cols, z, by};
}
// How clear the window is at a spot as drawn (tiles, lifted with its ground): 0 the land as it is, 1 seen through
function xrayAt(x, y) {
  if (xray.a <= .01) return 0;
  const d = Math.hypot(x - xray.x, y - xray.y) / XRAY.r;
  return xray.a * smooth(Math.max(0, Math.min(1, (1 - d) / (1 - XRAY.core))));
}
const xrayOn = (tx, ty) => xrayAt(tx, ty - shOf(levelAt(tx, ty)) / 16);      // ...at what stands on a tile
// What stands on land that is cut away under it goes with it: how much it fades (0: it stays)
const xrayCutAt = (tx, ty) => (xray.a > .01 && xray.pic ? xray.pic.cut.get(tx + "," + ty) : undefined);
const xrayOver = (tx, ty) => { const c = xrayCutAt(tx, ty); return c !== undefined && levelAt(tx, ty) > c ? xray.a : 0; };
// ...and the ground over the place you are in, under it: left out as that rock is (behind.js: neither hides anybody)
const xrayGone = (tx, ty) => xrayRock(tx, ty) || seenUnder(tx, ty) !== undefined;
// A tile of the place may have two of its rooms, one over the other (pic.all: every floor of the place there; pic.floor:
// the one that is seen, the cut goes down to it). Who stands on any of them is of the place: shown, never faded.
const xrayTop = (x, y) => { const a = xray.a > .01 && xray.pic ? xray.pic.all.get(x + "," + y) : undefined; return a ? a[a.length - 1] : undefined; };
// Who stands on land that is cut away under their feet goes with it (they would stand in the air), and only they:
// on the rock in the way, on the roof of the place. A step from whole land onto cut land: little by little.
function xrayOverBody(p) {
  const at = (x, y) => { const c = xrayCutAt(x, y), top = xrayTop(x, y), h = Floors.standOf(p, x, y); return c !== undefined && h > c && !(top !== undefined && h <= top + 1) ? xray.a : 0; };
  const x0 = Math.floor(p.x), y0 = Math.floor(p.y), fx = p.x - x0, fy = p.y - y0;
  return fx > .001 ? at(x0, Math.round(p.y)) * (1 - fx) + at(x0 + 1, Math.round(p.y)) * fx : fy > .001 ? at(x0, y0) * (1 - fy) + at(x0, y0 + 1) * fy : at(x0, y0);
}
// Someone on the ground behind that rock: how clearly they show through it (0: hidden as ever, 1: whole). (Under a
// roof of the place you are in: on one of its floors, not who walks over it)
function xrayShows(p) {
  const x = Math.round(p.x), y = Math.round(p.y), top = xrayTop(x, y);
  if (seenUnder(x, y) !== undefined) return Floors.standOf(p, x, y) <= top + 1 ? xray.a : 0;
  return !xrayRock(x, y) && xray.pic && xray.pic.place.has(x + "," + y) ? xray.a : 0;
}

// How far (art px) the ground south of a tile rises over the foot of its row (py: the row as drawn) at height L
function xrayCover(tx, row, py, L) {
  let cover = 0;
  for (let ty = row + 1; ty <= row + XRAY.far; ty++) cover = Math.max(cover, (levelAt(tx, ty) - L) * RELIEF_STEP - (ty - py - 1) * 16);
  return cover;
}
// Once a frame, before anything of it is drawn: are you behind something, and how much of you. (The build cursor
// down a hole went round with it too; it has its own keyhole now: keyhole.js)
function xrayLook(dt) {
  const p = me && ents.get("agent" + myId);
  let want = 0, f = null;                                  // (what the circle is round: px, py as drawn, L, row; mid: its centre over its tile)
  if (p && p.e) {
    // (where you are as drawn, at the height you are at: on a step, a floor, a ladder's rungs; it was the land's under
    // you, and a climb up a cliff's side or a flight of stairs beside one brought the circle up half way)
    const cl = Climb.climbOf(p), px = p.x + (cl ? cl.dx : 0), py = p.y + (cl ? cl.dy : 0);
    const L = cl ? Math.floor(cl.h) : Math.min(Floors.standOf(p, Math.floor(p.x), Math.floor(p.y)), Floors.standOf(p, Math.ceil(p.x), Math.ceil(p.y))), row = Math.floor(py + .001);
    let hidden = 0;                                        // the share of you under the top edge of the ground in front: the two
    const fr = px - Math.floor(px);                        //  columns you stand across, each for the part of you in it
    let roof = false;                                      // (under ground that was dug, its roof over you: all of you, at once)
    for (const [tx, part] of [[Math.floor(px), 1 - fr], [Math.floor(px) + 1, fr]]) if (part > .001) {
      const under = roofAt(tx, row) > 0 && coveredAt(tx, row, L);
      // (down a hole that was dug, behind its rim: at once too, however little of you the rim hides: you are IN the pit, seen on its floor, not a head at its edge)
      const cover = xrayCover(tx, row, py, L) - 2 - STAND;
      roof = roof || under; hidden += part * (under || (L < 0 && cover > 0) ? 1 : Math.max(0, Math.min(1, cover / XRAY.body)));
    }
    want = Math.max(0, Math.min(1, (hidden - XRAY.from) / (XRAY.full - XRAY.from)));
    f = {px, py, L, row, mid: .5 + UP, roof};
  }
  if (f) {
    xray.t = want > 0 ? xray.t + dt : 0;
    if (xray.t < XRAY.wait && xray.a <= .01 && !f.roof) want = 0;      // (a moment behind something: not yet)
    if (xray.t > 0 || xray.a > .01) {
      xray.L = f.L; xray.row = f.row; xray.x = f.px; xray.y = f.py - shOf(f.L) / 16 - f.mid;   // (its centre: your body, where it is drawn)
      xrayFind(Math.round(f.px));
    }
  }
  xray.a += (want - xray.a) * (1 - Math.exp(-dt / .09));
  if (xray.a < .01 && !want) xray.a = 0;
}


// What goes with the window where you are: the place's floors under a roof and the rock in the way. Worked out when
// your tile, your height or the land changes, not each frame.
function xrayFind(tx) {
  const key = [tx, xray.row, xray.L, Floors.ver, landVer].join();
  if (xray.pic && xray.pic.key === key) return;
  // the rock seen through: on the line of sight to a tile of your place (south of it in its column, and high enough
  // to be drawn over it: two layers a row), and of the mass that hides you (gone through from what is over your tile
  // and the two beside it, tile to tile)
  const L = xray.L, row = xray.row, {cols: place, z: floors, by} = xrayPlace(tx, row, L), mass = new Map(), todo = [];
  // (a tile with two rooms of the place, one over the other: every floor it has there, lowest first; the one that
  // is seen is the highest you are not under: from the lower room, that room; from the upper one, its own floor, whole)
  const all = new Map();
  for (const [k, h] of floors) { const a = [...new Set([h, ...(by.get(k) || [])])].sort((p, q) => p - q), at = a.filter((f) => f <= L + 1); all.set(k, a); floors.set(k, at.length ? at[at.length - 1] : a[0]); }
  // the place under a roof (a cave under a hill, a tunnel, a room dug under the ground): its floor is kept
  const floor = new Map(); for (const [k, h] of floors) { const [x, ty] = k.split(",").map(Number); if (h < levelAt(x, ty)) floor.set(k, h); }
  // What the land is cut open FOR. Your own body, always, and where your next step goes: your tile and the eight round it. All of the place
  // you are in only if you are in a hole: under a roof, or in ground that was dug, and of it the floors under a roof
  // or dug. On open ground a hill is cut where it covers you, no further ("standing north of a hill wrecks it": every
  // tile of it that hid any of the meadow round you was cut, the whole hill pressed flat). And a roof that is open
  // on most of its sides (an overhang: more of its edge open than walled) is no room: it is lifted over you alone,
  // the rest of it stands, cut round you.
  let walled = 0, free = 0;
  for (const [k, h] of floor) { const [x, ty] = k.split(",").map(Number); for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) if (!floor.has((x + dx) + "," + (ty + dy))) { if (levelAt(x + dx, ty + dy) > h + 1) walled++; else free++; } }
  const hole = (L < 0 || floor.has(tx + "," + row)) && free <= walled;
  const seen = (x, gy) => (Math.abs(x - tx) <= 1 && Math.abs(gy - row) <= 1) || (hole && (floor.has(x + "," + gy) || floors.get(x + "," + gy) < 0));
  for (const k of [...floor.keys()]) { const [x, ty] = k.split(",").map(Number); if (!seen(x, ty)) floor.delete(k); }      // (a roof that is not lifted: what is under it stays under it)
  // (-> how low it must be cut for the eye to see the floors of the place it hides (the eye looks down two levels
  // a row: a tile further south needs less taken off), or null: it hides none)
  const hides = (x, ty) => {
    const lv = levelAt(x, ty), rows = lv >= L + 2 && place.get(x); let low = null;
    // (the cut is a section through solid blocks, vox_section.js: a floor with land between it and this tile that is
    // not cut, and stands a tile's height or more over the eye's line there, stays hidden whatever is cut here: `shut`)
    const shut = (gy, f) => { for (let t = gy + 1; t < ty; t++) { const h = levelAt(x, t); if (h < L + 2 && h >= f + 2 * (t - gy) && !floors.has(x + "," + t)) return true; } return false; };
    if (rows) for (const gy of rows) { const f = floors.get(x + "," + gy), up = lv - f; if (gy < ty && up > 1 && up > 2 * (ty - gy) - 2 && seen(x, gy) && !shut(gy, f)) { const need = f + 2 * (ty - gy) - 2; low = low === null ? need : Math.min(low, need); } }
    return low;
  };
  const sight = (x, ty) => hides(x, ty) !== null;
  const join = (x, ty) => { const k = x + "," + ty; if (!mass.has(k)) { mass.set(k, [x, ty]); todo.push([x, ty]); } };
  for (let x = tx - 1; x <= tx + 1; x++) if ((place.get(x) || []).includes(row)) for (let ty = row + 1; ty <= row + XRAY.far; ty++) if (sight(x, ty)) join(x, ty);
  while (todo.length) {
    const [x, ty] = todo.pop();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) if (Math.abs(x + dx - tx) <= 14 && Math.abs(ty + dy - row) <= 20 && levelAt(x + dx, ty + dy) >= L + 2) join(x + dx, ty + dy);
  }
  const rock = new Set(), cut = new Map(), lower = (k, v) => { if (!cut.has(k) || cut.get(k) > v) cut.set(k, v); };
  for (const [k, [x, ty]] of mass) if (sight(x, ty) && !floor.has(k)) { rock.add(k); lower(k, hides(x, ty)); }
  // The cut. Over a floor under a roof: all that is over it (its roof is lifted off). The tiles south of it, in
  // front: down to that floor (you look in over them). The rock north of it and beside it is left whole: the wall
  // behind the place stands, up to the top of the land. (Cut down to the room's ceiling too, the rock round a cave
  // was a dark frame a tile wide all round it.)
  for (const [k, h] of floor) {
    const [x, ty] = k.split(",").map(Number);
    lower(k, h);
    const nk = x + "," + (ty + 1); if (!floor.has(nk)) lower(nk, h);      // (the one straight south: only what is in its own column is in front of it)
  }
  // (the open floors of a hole you are in, a pit's: nothing is over them to cut; they are of the cut all the same, cut
  // "down" to far over them, so that the cut's walls know the hole has walls out of doors: vox_section.js, one light)
  if (hole) for (const [k, h] of floors) if (h < 0 && !floor.has(k) && !cut.has(k)) cut.set(k, 30000);
  // (and your own tile first: a higher floor of the place south of you, drawn up over where you stand, is cut down
  // to your floor as any ground in front of you is: you stood in a dark column with no floor under you)
  for (let ty = row + 1; ty <= row + XRAY.far; ty++) { const k = tx + "," + ty, f = floor.get(k); if (f !== undefined && (f - L) * RELIEF_STEP - (ty - row - 1) * 16 > RELIEF_STEP) lower(k, L); }
  // The front of the hole is one straight edge. Each column's own cut ended at its own row (a stair: a sliced square
  // south of every step, a sill under the lowest floor alone). Row by row going south, the tiles in front of the
  // place that are side by side (cut for the eye's line, or south of one that is, or of a floor under a roof) are
  // all cut to the lowest of them: a higher floor stands on its block, whose front is seen down to that edge.
  if (XRAY.even && cut.size) {
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9; for (const k of cut.keys()) { const [x, ty] = k.split(",").map(Number); x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, ty); y1 = Math.max(y1, ty); }
    for (let ty = y0; ty <= y1 + XRAY.far; ty++) for (let x = x0, run = []; x <= x1 + 1; x++) {
      const k = x + "," + ty, n = x + "," + (ty - 1);
      if (x <= x1 && !floors.has(k) && (cut.has(k) || floor.has(n) || (cut.has(n) && !floors.has(n)))) { run.push(x); continue; }
      const low = Math.min(...run.filter((v) => cut.has(v + "," + ty)).map((v) => cut.get(v + "," + ty)));      // (none of them cut: Infinity, nothing is)
      for (const v of run) if (levelAt(v, ty) > low) { lower(v + "," + ty, low); rock.add(v + "," + ty); }
      run = [];
    }
  }
  xray.pic = {key, floor, rock, cut, all, place: new Set(floors.keys())};
}
