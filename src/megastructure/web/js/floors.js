// What is built over the land, a block at a time (the server keeps it: sim/storeys.py, floors.py). A built block is
// a cell of its tile's column, like the land's own (cells.js): stood on, jumped onto and fallen from by the one rule.
// But it is no land: no hill is painted for it. It is drawn as what it is, in its place among the frame's things:
// its top a layer's step higher a cell (relief.js), its south face under that, and what stands on it, on it.
//   planks: a floor (the pack's house floor), its face the pack's wall planks. roof: the pack's shingles
//   (structures.js), the same block.
// So a tile can be stood on at more than one height (the room, the floor over it): a body is drawn at its own.
// What is over your head is seen through, with all that holds to it at that height and all that is higher there: you
// see the room you are in. In build mode: all that is over the cursor's level. How, the settings say (options.js,
// VIEWS): not drawn (cut away), its edges only (outline), faint (faded, circle).
// A server from before blocks says `roofs`, not `floors`: each of its roof tiles is shown as a roof block a storey
// over its ground; nobody stands on those (FLOORS false).
let FLOORS = false;
const Floors = (() => {
  const STOREY = 3, K = .03, THIN = .12, FAINT = .3, VEIL = .25, FADED = .65;     // (FADED: how much of it goes, faded, in front of you)
  let ver = 0, over = {key: "-", z: 99, tiles: new Set()}, veils = 0;      // (veils: how many blocks were a veil over you in the last frame)
  const FADE = .15;                                  // the circle round you comes and goes over this many seconds
  let drawnAt = 0;
  const colOf = (x, y) => { const t = tileIdx(x, y); return t && t[0].built ? t[0].built.get(t[1]) : undefined; };   // z -> [kind, the char of what stands on it]
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
    b.built = new Map();
    for (const [i, z, kind, ch] of d.floors || []) put(b, i, z, kind, ch);
    for (const i of d.roofs || []) put(b, i, b.lv[i].charCodeAt(0) - SEA + STOREY, "roof", "");
    ver++;
  }
  // The built cells of the tile's column, a bit each (cells.js: what you walk on is the land and these)
  function mask(x, y) { const c = FLOORS && colOf(x, y); let m = 0; if (c) for (const z of c.keys()) m |= 1 << (z - LOW); return m >>> 0; }
  // What stands at height z of the tile: on a built block, what was put on it; on the land, the tile's own
  const thingAt = (x, y, z) => { const c = get(x, y, z); return c ? c[1] : z === groundAt(x, y) ? combAt(x, y) || "" : ""; };
  // As the server's block_fits: why no block can go in the cell (x, y, z), in a few words; nothing when one can
  // (planned: blocks that are only planned yet, which hold the ones planned beside them: build.js)
  function fits(x, y, z, planned = () => false) {
    if (solidAt(x, y, z)) return "A block is there";
    const under = Math.max(...surfacesAt(x, y).filter((s) => s < z)), on = thingAt(x, y, under), t = tile(x, y);
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
  const rise = (p) => { const x = Math.round(p.x), y = Math.round(p.y); return FLOORS && colOf(x, y) ? standOf(p, x, y) - standAt(x, y) : 0; };   // how far over the land it stands

  // What is over your head: with a block over you, the lowest one over your height on your tile or the next (on the
  // steps, the floor you are climbing to), and every tile that goes on from yours with a block that high or higher
  function mine() {
    const s = myAt, key = s ? [s.x, s.y, s.z, ver].join() : "";
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
  // (cut away and outline: none of it; outline() draws the edges)
  const hides = (x, y, z) => (mine().tiles.has(x + "," + y) && z >= over.z ? THIN : Build.on && z > Build.level() ? FAINT : 0);
  const alpha = (x, y, z) => { const h = hides(x, y, z); return !h ? 1 : opt("above") === "cut" || opt("above") === "outline" ? 0 : h; };
  // A block's top as its edges, in the pack's ink: the sides no block of its kind goes on from (the outline view)
  function outline(kind, x, y, z, sx, sy, a) {
    const q = zoom, px = sx(x), top = sy(y) - shOf(z) * q, same = (dx, dy) => !!get(x + dx, y + dy, z);
    ctx.globalAlpha = a; ctx.fillStyle = Structures.INK;
    if (!same(0, -1)) ctx.fillRect(px, top, 16 * q, q);
    if (!same(0, 1)) ctx.fillRect(px, top + 15 * q, 16 * q, q);
    if (!same(-1, 0)) ctx.fillRect(px, top, q, 16 * q);
    if (!same(1, 0)) ctx.fillRect(px + 15 * q, top, q, 16 * q);
    ctx.globalAlpha = 1;
  }

  // One block: its top (unless a block is on it), its south face (unless one goes on south of it)
  function cell(kind, x, y, z, sx, sy, S, a) {
    const q = zoom, px = sx(x), top = sy(y) - shOf(z) * q, same = (dx, dy) => { const c = get(x + dx, y + dy, z); return !!c && c[0] === kind; };
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
        ctx.drawImage(IMG.house_walls, 56, 9, 16, 7, px, top + 16 * q, S, 7 * q); r(ink, 0, 23, 16, 1); r(ink, 0, 16, 16, 1);
        if (!get(x - 1, y, z)) r(ink, 0, 16, 1, 8);
        if (!get(x + 1, y, z)) r(ink, 15, 16, 1, 8);
      }
    }
    ctx.globalAlpha = 1;
  }
  // What stands on a block: a wall, a door (structures.js), or a thing as it is drawn on the ground, a block's height up
  function thing(ch, x, y, z, sx, sy, S, t, now, a) {
    const at = (yy) => sy(yy) - shOf(z) * zoom;
    if (Structures.WALLS.includes(ch)) return Structures.drawWall(ch, x, y, sx, at, S, now, a, z);
    if (ch === "l") return Climb.drawLadder(x, y, z, sx, sy, S, a);
    const spr = objectSprite(ch, x, y, t); if (!spr) return;
    ctx.globalAlpha = a;
    ctx.drawImage(spr[0], spr[1], spr[2], spr[3], spr[4], Math.round(sx(x) + spr[5] * zoom), Math.round(at(y) + spr[6] * zoom), spr[3] * zoom, spr[4] * zoom);
    ctx.globalAlpha = 1;
  }
  // The frame's blocks, each in its place among the rest: a row at a time, and in a row from the ground up. When what
  // is built south of you is drawn over your body (behind a house, at the back of a tower, up its back ladder), you are
  // seen through it as through a hill (xray.js): a circle round you, the blocks in front of you clear in its middle,
  // fading in rings to whole at its edge. It comes and goes over FADE seconds, and only for what is really over you.
  // (It was each block that covered you seen through whole: a stripe down a tower's top; and it took the place a
  // straight line had you at on a ladder and the tile you were leaving on a step: it came and went half way up a
  // ladder and on a flight's last step. Then it was left out on ladders and stairs, and you were lost behind a tower.)
  const RINGS = [[.45, 1], [.6, .8], [.72, .6], [.84, .4], [1, .2]], XR = 1.7;    // (radius, tiles; each ring's out edge and how clear)
  let seen = 0;                                      // how clear the circle is now (0 to 1)
  function draw(vis, list, sx, sy, S, t, now) {
    // you as drawn: on a ladder's rungs where the climb has you (climbing.js); at the height you are at, the higher of
    // the two tiles while you step between them: a block no higher than that covers nothing of you
    const me_ = ents.get("agent" + myId), q = zoom, cl = me_ ? Climb.climbOf(me_) : null;
    const myx = me_ ? me_.x + (cl ? cl.dx : 0) : 0, myy = me_ ? me_.y + (cl ? cl.dy : 0) : 0;
    const foot = me_ ? bodyY(me_, sy) + (cl ? cl.dy * S - cl.lift * q : 0) + S - 2 * q : 0, bx = sx(myx);
    const h = cl ? cl.h : me_ ? Math.max(standOf(me_, Math.floor(me_.x), Math.floor(me_.y)), standOf(me_, Math.ceil(me_.x), Math.ceil(me_.y))) : 0;
    const before = (y, z) => me_ && z > h && y > myy + .3;               // in front of you, and over your feet
    const covers = (x, y, z, roof) => { const top = sy(y) - shOf(z) * q; return before(y, z) && sx(x) < bx + S - 3 * q && sx(x) + S > bx + 3 * q && top - (roof ? 7 * q : 0) < foot && top + S + 8 * q > foot - 18 * q; };
    const cx = bx + S / 2, cy = foot - 9 * q, R = XR * S;
    const near = (x, y, z) => { const top = sy(y) - shOf(z) * q - 8 * q, l = sx(x) - 12 * q; return before(y, z) && Math.max(l - cx, 0, cx - l - S - 24 * q) ** 2 + Math.max(top - cy, 0, cy - top - S - 32 * q) ** 2 < R * R; };
    const tnow = performance.now(), step = Math.min(.1, (tnow - drawnAt) / 1000); drawnAt = tnow;
    let hidden = false;
    veils = 0;
    for (const b of vis) if (b.built) for (const [i, c] of b.built) {
      const x = b.bx * B + i % B, y = b.by * B + (i / B | 0), base = standAt(x, y);
      for (const [z, [kind, ch]] of c) {
        const a = alpha(x, y, z), key = y + (z - base) * K, hole = a > VEIL && near(x, y, z);
        if (!a) {                                      // (over you, cut away or as its edges)
          if (opt("above") === "outline") list.push({y: key - .005, x, fx: () => outline(kind, x, y, z, sx, sy, .85)});
          continue;
        }
        if (hole && covers(x, y, z, kind === "roof")) hidden = true;
        if (hole) veils++;
        const edge = (aa) => outline(kind, x, y, z, sx, sy, aa), paint = (fn, e = () => {}) => (hole ? () => holed(fn, a, cx, cy, R, e) : () => fn(a));
        list.push({y: key - .005, x, fx: paint((aa) => cell(kind, x, y, z, sx, sy, S, aa), edge)});
        if (ch) list.push({y: key, x, fx: paint((aa) => thing(ch, x, y, z, sx, sy, S, t, now, aa))});
      }
    }
    seen += ((hidden ? 1 : 0) - seen) * Math.min(1, step / FADE);
    if (seen < .01 && !hidden) { seen = 0; veils = 0; }
  }
  // A block in front of you drawn with the circle in it: ring by ring, clearer towards you (the hill's own way, xray.js);
  // in the other views, each block near you that is in front of you as a whole: gone, its edges, or faint
  function holed(fn, a, cx, cy, R, edge) {
    if (seen < .01) return fn(a);
    const v = opt("above");
    if (v !== "circle") {
      fn(a * (1 - seen * (v === "faded" ? FADED : 1)));
      if (v === "outline") edge(a * seen * .85);
      return;
    }
    let r0 = 0;
    for (const [k, clear] of [...RINGS, [99, 0]]) {
      const r1 = k * R;
      ctx.save(); ctx.beginPath();
      if (k < 99) { ctx.moveTo(cx + r1, cy); ctx.arc(cx, cy, r1, 0, 2 * Math.PI); } else ctx.rect(0, 0, W, H);
      if (r0) { ctx.moveTo(cx + r0, cy); ctx.arc(cx, cy, r0, 0, 2 * Math.PI); }
      ctx.clip("evenodd");
      fn(a * (1 - seen * clear * (1 - VEIL)));
      ctx.restore();
      r0 = r1;
    }
  }
  // What a click or a key means with a block in hand, or on a tile whose ground at your height is a built block
  // (intent.js asks first): said in a few words, with what does it. Nothing: the ground's own (intent.js goes on)
  const UP = new Set("W%+#ghLBpKrl");                // what stands on a built block (sim/storeys.py UPSTAIRS)
  function intent(p, shift) {
    const s = myPos(), it = selected && !shift ? selected : null, isMe = s.x === p.x && s.y === p.y;
    const z = settleNear(p.x, p.y, myZ(s.x, s.y)), c = FLOORS ? get(p.x, p.y, z) : null, on = c ? c[1] : "", zArg = (zz) => (FLOORS ? {z: zz} : {});
    const place = (zz, text) => ({text, ghost: it, ok: true, near: 1, z: zz, run: (d) => act("place", {dir: d, item: it, ...zArg(zz)})});
    const t = tile(p.x, p.y);                         // earth on open ground: the ground comes up a layer (as digging takes it down one)
    if (it === "dirt" && FLOORS && t && ".,'".includes(t[1]) && (GROUND.has(t[0]) || t[0] === "f") && !isMe && !c && z === topAt(p.x, p.y) && colAt(p.x, p.y) === colSolid(z) && !colOf(p.x, p.y))
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
    if (on === "B" && !shift) return {text: "Sleep (wake up here after dying)", near: 1, z, run: (d) => act("sleep", {dir: d})};
    if (on) { const tool = TOOL_FOR[on], w = inHand(); return {text: (HARVEST[on] || "Take down " + label(CH[on])) + (tool ? (w === tool ? ` with ${tool}` : " by hand (slow)") : ""), near: 1, z, run: (d) => act("dig", {dir: d, z, ...(w ? {with: w} : {})})}; }
    if (shift) return {text: c[0] === "roof" ? "Take the roof block" : c[0] === "stairs" ? "Take up the step" : "Take up the planks", near: 1, z, run: (d) => act("dig", {dir: d, z})};
    return {text: "Walk here", walk: true, run: () => act("move_to", {x: p.x, y: p.y, z})};
  }
  return {STOREY, K, UP, any: (x, y) => !!colOf(x, y), get, set, load, mask, thingAt, fits, standOf, rise, alpha, cell, thing, draw, intent, get ver() { return ver; }, get veils() { return veils; }, get seen() { return seen; }};
})();
