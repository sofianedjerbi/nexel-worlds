// The HD look's things (hd.js): what is built or put down is a piece of the land, not a flat picture of itself stood
// up on tilted ground ("some tiles should be turned 3d: bed, etc"). Nothing is new art: every px is the thing's own.
//   Furniture (a bed, a chest, a table...): a CARD: its own sprite px for px, never squeezed (as big and as crisp as
//   its picture), drawn by the engine as a billboard at its foot. Its top rows lean, a whole px at a time, as a top
//   lying behind its front does off to a side of the screen, the side that shows is filled in the front's own edge
//   colour, and its shadow lies on the ground. A well, a coop, a sign...: their picture and a shadow, no lean.
//   Walls, doors, fences, built floors, steps and roofs, a rug: boxes in the land (the engine's models, vox_style.js
//   `model`), painted from the pack's sheets or by the game's own painters (structures.js, floors.js, climbing.js) at
//   zoom 1. A front is as many rows of paint as it is px high on the screen at your feet (KF: the eye's pitch).
//   HdThings.at(x, y) -> the boxes of the tile; is(c) -> a char that is boxes (no billboard); card(c, x, y, spr, X);
//   loose(x, y) -> [[char, z]...]: what stands on a built block and is not boxes; key() -> changes when the boxes must be made again
const HdThings = (() => {
  const S = HdSheet(), {sheet, room, pix, painted} = S, UP = RELIEF_STEP, LEAN = 0, PITCH = 4, plans = new Set(), FH = 16 + UP;   // (FH: a built block's picture: its 16 rows of top, a level of face under them) (KF: a front's px on the screen a px of its height, hd.js cam.pitch; LEAN: px a top's row leans, a px off the middle: none, it read as broken; PITCH: px a roof rises a tile; plans: walls only planned, "x,y,z")
  let ghosting = false;
  const KF = () => Math.cos((HdLook.cam.base || HdLook.cam.pitch) * Math.PI / 180);   // (a front's px on the screen a px of its height: the eye's pitch, 36 degrees, up to 52 on a screen held upright: at 36 always, a wall's 12 rows of planks would squeeze into 9 px on a phone)
  const cast = (out, x, y, zl, r, h0, h1, built) => { if (!ghosting && (built || zl === floorAt(x, y))) HdSun.box(out, x, y, built ? floorAt(x, y) : zl, r, h0, h1, built); };   // (what is built throws the shadow of the box it is, a px wider so that a run's are one)
  const {CARD, card, foot, shade, shadow, decal} = HdCards(S, LEAN), {hid, south} = HdRoom();
  const {wall, doorsAt, doorOpen} = HdWalls(S, {UP, KF, cast, plans, ghosting: () => ghosting}), {fence, sideGate} = HdFences(S, {UP, cast, doorOpen});
  const {pitch, block} = HdBlocks(S, {UP, PITCH, FH, cast, hid}), {thicket} = HdThickets(S, {UP, cast});
  const shaded = (c) => isObject(c) && !is(c) && !"f;\"wgVl".includes(c);      // (all that stands; not what is boxes, what is flat or thin, what floats)
  const is = (c, x, y) => "W%+#rmH".includes(c) || (c === "g" && x !== undefined && gateSide(x, y));
  function stand(out, c, x, y, zl) {     // what stands at level zl of the tile
    if (!c) return;
    if (Structures.WALLS.includes(c)) {
      const cells = Floors.cells(x, y); let over = 0, cutLow = false;
      if (cells) for (const zc of cells.keys()) if (zc > zl && zc <= zl + Floors.STOREY && (!over || zc < over)) { over = zc; cutLow = hid(x, y, zc); }   // (up to the lowest block over it: a storey, two blocks of wall)
      const p = myPos();      // (inside, the roof open: the walls south of you a low stub, you are seen over them; the others to their own height)
      const full = over ? (over - 1 - zl) * UP : UP; wall(out, c, x, y, zl, cutLow && (Build.on ? p && y > p.y : y > south()) ? 4 : full);   // (a stub: the room's south wall alone; else a block, or up to the block over it)
    } else if (c === "#") fence(out, x, y, zl * UP); else if (c === "H") thicket(out, x, y, zl * UP); else if (c === "g") sideGate(out, x, y, zl * UP);
    else decal(out, c, x, y, zl * UP);
  }
  // (the sheet emptied while a tile's pieces were asked for: those asked before name places of the old sheet. Asked once more, all in the new one: an oval of shade read a shadow's black blades, or nothing)
  const at = (x, y) => { const id = sheet.id, out = pieces(x, y); return sheet.id === id ? out : pieces(x, y); };
  function pieces(x, y) {
    const out = [], c = combAt(x, y), cells = Floors.cells(x, y);
    if (c && is(c, x, y)) stand(out, c, x, y, floorAt(x, y)); else if (c && shaded(c)) shade(out, c, x, y, floorAt(x, y) * UP, floorAt(x, y));      // (on the tile's lowest ground: in a cave, on its floor)
    if (cells) for (const [z, [kind, ch]] of cells) { if (hid(x, y, z)) continue; block(out, kind, x, y, z); if (ch && is(ch)) stand(out, ch, x, y, z); else if (ch && shaded(ch)) shade(out, ch, x, y, z * UP, z); }
    if (!ghosting) HdSun.land(out, x, y);      // (the land's own shadow on this tile: a cliff's, a terrace's)
    return out.length ? out : null;
  }
  // What is only planned, or would be put where you aim (build.js, intent.js): the same boxes, see-through (`ghost`: the engine draws one px in two of it).
  // item: what is put; z: the built block it is or stands on (none: on the ground); steps: a flight of stairs [[x, y, ground, top]...]. -> [[x, y, box]...], or null: no piece (a billboard, a ladder)
  const pieced = (item, steps, z) => !!steps || ((item === "roof" || item === "plank") && z !== undefined) || is(PLACEABLE_BLOCK[item] || "-");
  function ghost(item, x, y, z, steps) {
    if (!pieced(item, steps, z)) return null;
    const out = [], run = (tx, ty, fn) => { const l = []; ghosting = true; try { fn(l); } finally { ghosting = false; } for (const b of l) out.push([tx, ty, Object.assign(b, {ghost: true})]); };
    if (steps) for (const [tx, ty, g, t] of steps) for (let zz = g + 1; zz <= t; zz++) run(tx, ty, (l) => block(l, "stairs", tx, ty, zz));
    else if (item === "roof" || item === "plank") run(x, y, (l) => block(l, item, x, y, z));
    else run(x, y, (l) => stand(l, PLACEABLE_BLOCK[item], x, y, z === undefined ? floorAt(x, y) : z));
    return out;
  }
  function loose(x, y) { const cells = Floors.cells(x, y), out = []; if (cells) for (const [z, [, ch]] of cells) if (ch && !is(ch) && !hid(x, y, z)) out.push([ch, z]); return out; }
  // what the pieces hang on beside the land: what is built, where you are under it, the build cursor's level, who stands by a door
  function key(near = true) { const P = near && HdLevel.place, s = P && !P.free && {x: P.tx, y: P.ty, z: P.L}; let d = ""; if (doorsAt.size > 300) doorsAt.clear(); for (const [x, y] of doorsAt.values()) if ("+g".includes(combAt(x, y) || "-") && doorOpen(x, y)) d += x + "," + y + ";"; return [Floors.ver, s ? [s.x, s.y, s.z] : "", Build.on ? Build.level() : "", sheet.id, d, HdSun.key(), HdLook.cam.pitch].join("|"); }
  return {at, is, loose, key, painted, ghost, pieced, card, shadow, foot, plans, CARD, sheet, room, pix, pitch};
})();