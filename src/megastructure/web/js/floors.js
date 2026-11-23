// What is built over the land, a block at a time (the server keeps it: sim/storeys.py, floors.py). A built block is
// a cell of its tile's column, like the land's own (cells.js): stood on, jumped onto and fallen from by the one rule.
// But it is no land: no hill is painted for it. It is drawn as what it is, in its place among the frame's things:
// its top a layer's step higher a cell (relief.js), its south face under that, and what stands on it, on it.
//   planks: a floor (the pack's house floor), its face the pack's wall planks. roof: the pack's shingles
//   (structures.js), the same block.
// So a tile can be stood on at more than one height (the room, the floor over it): a body is drawn at its own.
// What is over your head is seen through, with all that holds to it at that height and all that is higher there: you
// see the room you are in. In build mode: all that is over the cursor's level. How, the settings say (options.js,
// VIEWS): not drawn (cut away), or faint (faded).
// A server from before blocks says `roofs`, not `floors`: each of its roof tiles is shown as a roof block a storey
// over its ground; nobody stands on those (FLOORS false).
let FLOORS = false;
const Floors = (() => {
  const STOREY = 3, K = .03, THIN = .12, FAINT = .3;
  let ver = 0, over = {key: "-", z: 99, tiles: new Set()};
  const colOf = (x, y) => { const b = blockOf(x, y); return b && b.built ? b.built.get((y - b.by * B) * B + (x - b.bx * B)) : undefined; };   // z -> [kind, the char of what stands on it]
  const get = (x, y, z) => { const c = colOf(x, y); return c ? c.get(z) : undefined; };
  function put(b, i, z, kind, ch) { let c = b.built.get(i); if (!c) b.built.set(i, c = new Map()); c.set(z, [kind, ch === " " ? "" : ch || ""]); }
  function set(x, y, z, kind, ch) {
    const t = tileIdx(x, y); if (!t) return;
    if (!t[0].built) t[0].built = new Map();
    const c = t[0].built.get(t[1]);
    if (kind) put(t[0], t[1], z, kind, ch); else if (c) { c.delete(z); if (!c.size) t[0].built.delete(t[1]); }
    ver++;
  }
  function load(b, d) {                               // a region's blocks (an old server's roof tiles: a storey over their ground)
    const had = !!(b.built && b.built.size); b.built = new Map();
    for (const [i, z, kind, ch] of d.floors || []) put(b, i, z, kind, ch);
    for (const i of d.roofs || []) put(b, i, b.lv[i].charCodeAt(0) - SEA + STOREY, "roof", "");
    if (had || b.built.size) ver++;   // (a block with nothing built, come in: nothing built changed. It was a new version of all that is built: the HD look's whole land made again at each block come in)
  }
  // The built cells of the tile's column (cells.js: what you walk on is the land and these): all of them, by height; is there one at z?
  const cells = (x, y) => (FLOORS && colOf(x, y)) || null, built = (x, y, z) => { const c = FLOORS && colOf(x, y); return !!c && c.has(z); };
  // What stands at height z of the tile: on a built block, what was put on it; on the land, the tile's own
  const thingAt = (x, y, z) => { const c = get(x, y, z); return c ? c[1] : z === groundAt(x, y) ? combAt(x, y) || "" : ""; };
  // As the server's block_fits: why no block can go in the cell (x, y, z), in a few words; nothing when one can
  // (planned: blocks that are only planned yet, which hold the ones planned beside them: build.js)
  function fits(x, y, z, planned = () => false) {
    if (solidAt(x, y, z)) return "A block is there";
    const under = settleAt(x, y, z - 1), on = thingAt(x, y, under), t = tile(x, y);
    if (under === z - 1) return on && !GROUND.has(on) ? "Something is in the way" : !get(x, y, under) && t && wet(t[1]) ? "Not on water: a bridge first" : null;
    if (z - under < STOREY) return "Too low over the floor";
    if (z - under === STOREY && Structures.WALLS.includes(on || "-")) return null;
    return Object.values(DIRV).some(([dx, dy]) => solidAt(x + dx, y + dy, z) || planned(x + dx, y + dy, z)) ? null : "Needs a wall under it";
  }

  // The height a body is drawn at on a tile: the land's, or, where something is built, its own (yours: caves.js keeps
  // it as the server does; the others': the server says), where it was a step ago, or where a step would land it
  function standOf(p, x, y) {
    if (!p.e || !(FLOORS && colOf(x, y) || hollow(x, y))) return standAt(x, y);   // (over a hollow too, a cave or a tunnel: on its roof or in it)
    const mine = p.e.kind === "agent" && p.e.id === myId, at = mine ? myAt : p.zAt, was = mine ? myWas : p.zWas;
    if (at && at.x === x && at.y === y) return at.z;
    if (was && was.x === x && was.y === y) return was.z;
    const z = at && Math.abs(at.x - x) + Math.abs(at.y - y) === 1 ? landAt(at.z, x, y, at.x, at.y) : null;
    return z !== null ? z : at ? settleNear(x, y, at.z) : standAt(x, y);
  }
  // a body between two tiles: [ax, ay, bx, by, and their grounds for it] (jump.js, climbing.js, relief.js: once, here)
  const between = (p) => { const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y); return [ax, ay, bx, by, standOf(p, ax, ay), standOf(p, bx, by)]; };
  const rise = (p) => { const x = Math.round(p.x), y = Math.round(p.y); return FLOORS && colOf(x, y) ? standOf(p, x, y) - standAt(x, y) : 0; };   // how far over the land it stands

  // What is over your head: with a block over you, the lowest one over your height on your tile or the next (on the
  // steps, the floor you are climbing to), and every tile that goes on from yours with a block that high or higher
  function mine() {
    const P = HdLevel.place, s = P && !P.free ? {x: P.tx, y: P.ty, z: P.L} : null, key = s ? [s.x, s.y, s.z, ver].join() : "";   // (where your body is: hd_level.js place)
    if (key === over.key) return over;
    const zs = (x, y) => { const c = colOf(x, y); return c ? [...c.keys()] : []; }, tiles = new Set();
    let z = 99;
    if (s && zs(s.x, s.y).some((v) => v > s.z)) for (const [dx, dy] of [[0, 0], ...Object.values(DIRV)]) for (const v of zs(s.x + dx, s.y + dy)) if (v > s.z && v < z) z = v;
    const line = z < 99 ? [[s.x, s.y]] : [];
    if (line.length) tiles.add(s.x + "," + s.y);
    for (let i = 0; i < line.length && i < 900; i++) for (const [dx, dy] of Object.values(DIRV)) {
      const x = line[i][0] + dx, y = line[i][1] + dy, k = x + "," + y;
      if (!tiles.has(k) && zs(x, y).some((v) => v >= z)) { tiles.add(k); line.push([x, y]); }
    }
    return (over = {key, z, tiles});
  }
  // How much of what is at height z of the tile is drawn: over you, or over the cursor's floor, as the view has it
  // (cut away: none of it)
  const hides = (x, y, z) => (mine().tiles.has(x + "," + y) && z >= over.z ? THIN : Build.on && z > Build.level() ? FAINT : 0);
  const alpha = (x, y, z) => { const h = hides(x, y, z); return !h ? 1 : opt("above") === "faded" || opt("above") === "circle" ? h : 0; };
  // One block: its top (unless a block is on it), its south face (unless one goes on south of it)
  function cell(kind, x, y, z, sx, sy, S, a) {
    const q = zoom, px = sx(x), top = syUp(sy, y, shOf(z) * q), same = (dx, dy) => { const c = get(x + dx, y + dy, z); return !!c && c[0] === kind; };
    const r = (col, X, Y, W_, H_) => { ctx.fillStyle = col; ctx.fillRect(px + X * q, top + Y * q, W_ * q, H_ * q); };
    ctx.globalAlpha = a;
    if (kind === "stairs") { ctx.globalAlpha = 1; return Climb.drawStep(x, y, z, px, top, a); }   // (a step of a flight: climbing.js)
    if (kind === "roof") {
      let up = 0, down = 0;
      while (up < 14 && same(0, -up - 1)) up++;
      while (down < 14 && same(0, down + 1)) down++;
      Structures.drawRoof(px, top, S, up, down, same(-1, 0), same(1, 0));
    } else {
      const ink = Structures.INK;
      if (!get(x, y, z + 1)) {
        ctx.drawImage(IMG.house_walls, 16, 16, 16, 16, px, top, S, S);
        if (!get(x, y - 1, z)) r(ink, 0, 0, 16, 1);
        if (!get(x - 1, y, z)) r(ink, 0, 0, 1, 16);
        if (!get(x + 1, y, z)) r(ink, 15, 0, 1, 16);
      }
      if (!get(x, y + 1, z)) {                        // its face: a layer high, planks, the pack's ink under them
        const n = RELIEF_STEP; for (let j = 0; j < n - 1; j += 7) { const h = Math.min(7, n - 1 - j); ctx.drawImage(IMG.house_walls, 56, 9, 16, h, px, top + (16 + j) * q, S, h * q); }   // (a level's rows of planks: a cube's face, two courses)
        r(ink, 0, 15 + n, 16, 1); r(ink, 0, 16, 16, 1);
        if (!get(x - 1, y, z)) r(ink, 0, 16, 1, n);
        if (!get(x + 1, y, z)) r(ink, 15, 16, 1, n);
      }
    }
    ctx.globalAlpha = 1;
  }
  // What a click or a key means with a block in hand, or on a tile whose ground at your height is a built block
  // (intent.js asks first): said in a few words, with what does it. Nothing: the ground's own (intent.js goes on)
  const UP = new Set("W%+#ghLBpKrl");                // what stands on a built block (sim/storeys.py UPSTAIRS)
  function intent(p, shift) {
    const s = myPos(), it = selected && !shift ? selected : null, isMe = s.x === p.x && s.y === p.y;
    const z = settleNear(p.x, p.y, myZ(s.x, s.y)), c = FLOORS ? get(p.x, p.y, z) : null, on = c ? c[1] : "", zArg = (zz) => (FLOORS ? {z: zz} : {});
    const place = (zz, text) => ({text, ghost: it, ok: true, near: 1, z: zz, run: (d) => act("place", {dir: d, item: it, ...zArg(zz)})});
    const t = tile(p.x, p.y);                         // earth on open ground: the ground comes up a layer (as digging takes it down one)
    if (LAND_BLOCKS.has(it) && FLOORS && t && ".,'".includes(t[1]) && (GROUND.has(t[0]) || t[0] === "f") && !isMe && !c && z === topAt(p.x, p.y) && colAt(p.x, p.y) === colSolid(z) && !colOf(p.x, p.y))
      return entityAt(p) ? {text: "Someone is standing there", ghost: it, ok: false} : {text: "Raise the ground", ghost: it, ok: true, near: 1, run: (d) => act("place", {dir: d, item: it})};
    const h = myZ(s.x, s.y);                          // standing on a block, the air before you at your own height: the floor goes on
    if (it === "plank" && FLOORS && get(s.x, s.y, h) && !isMe && !solidAt(p.x, p.y, h) && !fits(p.x, p.y, h)) return place(h, "Lay planks");
    if (it === "roof" || (it === "plank" && c && !isMe)) {       // a block: a roof a storey over the tile; planks on the block you face
      const zz = z + (it === "roof" ? STOREY : 1), why = fits(p.x, p.y, zz);
      return why ? {text: why, ghost: it, ok: false, z: zz} : place(zz, it === "roof" ? "Lay roof" : "Put planks on top");
    }
    if (!c || isMe) return null;
    if (it && PLACEABLE_BLOCK[it] && c[0] === "stairs") return {text: "Not on a step", ghost: it, ok: false, z};
    if (it && PLACEABLE_BLOCK[it]) return on ? {text: "Something is there", ghost: it, ok: false, z} : UP.has(PLACEABLE_BLOCK[it]) ? place(z, `Place ${label(it)}`) : {text: "It needs the ground", ghost: it, ok: false, z};
    if (on === "B" && !shift) return {text: "Sleep", near: 1, z, run: (d) => act("sleep", {dir: d})};
    if (on && !shift) return {text: label(CH[on]), info: true, quiet: true, z};      // (shift: X's verb, intent.js: E takes nothing down)
    if (on) { const tool = TOOL_FOR[on], w = inHand(); return {text: (HARVEST[on] || "Take down " + label(CH[on])) + (tool && w !== tool ? " (slow)" : ""), near: 1, z, run: (d) => act("dig", {dir: d, z, ...(w ? {with: w} : {})})}; }
    if (shift) return {text: c[0] === "roof" ? "Take the roof block" : c[0] === "stairs" ? "Take up the step" : "Take up the planks", near: 1, z, ground: true, run: (d) => act("dig", {dir: d, z})};
    return {text: "Walk here", walk: true, run: () => act("move_to", {x: p.x, y: p.y, z})};
  }
  return {STOREY, K, UP, any: (x, y) => !!colOf(x, y), get, set, load, cells, built, thingAt, fits, standOf, between, rise, alpha, cell, intent, get ver() { return ver; }};
})();
