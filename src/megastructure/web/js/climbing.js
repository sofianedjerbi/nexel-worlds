// Ladders and stairs, on the screen (the server's rules: sim/climbing.py, the same here so that your walk and the
// hints say what the server will do).
//   A ladder stands against something taller beside it (a wall with a floor on it, a terrace, a roof, a cliff):
//   walk into that from the ladder and you climb out on top; walk back off and you climb down, no fall. It is drawn
//   from its foot up to the top it leads to, two rails and their rungs, in the wood of the pack's houses.
//   Stairs are a flight laid with one press: beside a higher place, steps a tile each, a layer lower each, down to
//   the ground. A step is drawn as a block of planks with its tread: the nose lit where you come up from, the next
//   riser's shadow at the back.
const Climb = (() => {
  const CLIMB = 12, RISE = [2, 7], WAYS = [[0, -1], [1, 0], [0, 1], [-1, 0]];       // (N, E, S, W: the server's order)
  const RAIL = "#90625d", RUNG = "#c49a6c", LIGHT = "#e8cfa6";
  const ladderAt = (x, y, z) => FLOORS && Floors.thingAt(x, y, z) === "l";
  // Someone could stand at height z on (x, y)
  function openAt(x, y, z) {
    if (!surfacesAt(x, y).includes(z) || solidAt(x, y, z + 2)) return false;
    const c = Floors.get(x, y, z);
    return c ? !SOLID.has(c[1]) : z !== floorAt(x, y) || plainWalk(x, y);
  }
  // From a ladder at height h on (x0, y0), into (x, y): where you come out, or null
  function climb(h, x0, y0, x, y) {
    for (const s of surfacesAt(x, y)) {
      if (s <= h || s > h + CLIMB) continue;
      for (let c = h + 1; c <= s + 2; c++) if (solidAt(x0, y0, c)) return null;
      if (openAt(x, y, s)) return s;
    }
    return null;
  }
  // What a ladder at height z on (x, y) leans on: {dx, dy, top}, the first way with a top two layers up or more
  function lean(x, y, z) {
    for (const [dx, dy] of [[0, -1], [-1, 0], [1, 0], [0, 1]]) { const s = climb(z, x, y, x + dx, y + dy); if (s !== null && s >= z + 2) return {dx, dy, top: s}; }
    return null;
  }
  // A step from (x0, y0, h0) to (x, y, h) taken on a ladder: climbed, not hopped nor fallen (jump.js)
  const onLadder = (x0, y0, h0, x, y, h) => ladderAt(x0, y0, h0) || ladderAt(x, y, h);
  // A ladder is climbed rung by rung: CLIMB_S a layer (sim/constants.py), the next step waits for it. Your walk
  // crosses a climb at that pace (walk.js), and so is anyone else seen climbing (render.js): tiles a second, or 0
  const CLIMB_S = .15;
  function pace(fx, fy, h, x, y) {
    const z = landAt(h, x, y, fx, fy);
    return z !== null && Math.abs(z - h) > 1 && onLadder(fx, fy, h, x, y, z) ? 1 / (Math.abs(z - h) * CLIMB_S) : 0;
  }
  function paceOf(p) {
    let ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
    if (ax === bx && ay === by) { bx = p.tx; by = p.ty; if (Math.abs(bx - ax) + Math.abs(by - ay) !== 1) return 0; }
    const la = Floors.standOf(p, ax, ay), lb = Floors.standOf(p, bx, by);
    return Math.abs(la - lb) > 1 && onLadder(ax, ay, la, bx, by, lb) ? 1 / (Math.abs(la - lb) * CLIMB_S) : 0;
  }
  // Someone between two tiles on a ladder, as drawn: up its rungs on its own tile first, and only at the top over onto
  // what it leans on (coming down: over the edge first, then down the rungs); facing it all the way. (It was a straight
  // slide from the foot to the top in a fifth of a second, the ladder drawn over the body.) -> null, or {dx, dy: tiles
  // to move the body by, lift: art px higher, h: the height it is at (layers), on: on the rungs, u: how far up, fx, fy:
  // the way to the top, y: its row}
  const OVER = .8;                                    // (the part of the step spent on the rungs; the rest is the step over)
  function climbOf(p) {
    const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
    if ((ax === bx && ay === by) || !FLOORS) return null;
    const la = Floors.standOf(p, ax, ay), lb = Floors.standOf(p, bx, by);
    if (Math.abs(la - lb) < 2 || !onLadder(ax, ay, la, bx, by, lb)) return null;
    const footA = la < lb, u = footA ? (ax === bx ? p.y - ay : p.x - ax) : (ax === bx ? by - p.y : bx - p.x);
    const lo = Math.min(la, lb), hi = Math.max(la, lb), on = u <= OVER;
    const pos = on ? 0 : (u - OVER) / (1 - OVER), h = on ? lo + (hi - lo) * u / OVER : hi;
    const fx = footA ? bx - ax : ax - bx, fy = footA ? by - ay : ay - by, footY = footA ? ay : by;
    return {dx: fx * (pos - u), dy: fy * (pos - u), lift: (h - lo - (hi - lo) * u) * RELIEF_STEP, h, on, u, fx, fy, y: on ? footY : footY + fy};
  }

  // The flight of stairs put at (x, y) by you: [[x, y, ground, top], ...], or {why}
  function flight(x, y) {
    const s = myPos(); if (!s) return {why: ""};
    const base = settleNear(x, y, myZ(s.x, s.y));
    let why = null;
    for (const [dx, dy] of WAYS) {
      const top = surfacesAt(x + dx, y + dy).find((t) => t >= base + RISE[0] && t <= base + RISE[1] && openAt(x + dx, y + dy, t));
      if (top === undefined) continue;
      for (const [wx, wy] of [[-dx, -dy], [dy, dx], [-dy, -dx]]) {      // straight out from it; else along it
        const steps = down(x, y, wx, wy, top);
        if (Array.isArray(steps)) return steps;
        why = why || steps;
      }
    }
    return {why: why || "Stairs go up to something higher beside them"};
  }
  function down(x, y, dx, dy, top) {
    const out = [];
    for (let t = top - 1; ; t--, x += dx, y += dy) {
      const under = surfacesAt(x, y).filter((v) => v < t), g = under.length ? Math.max(...under) : null;
      if (g === null || t <= g) return out.length ? out : "The ground there is as high";
      for (let c = g + 1; c <= t + 2; c++) if (solidAt(x, y, c)) return "No room: leave the floor open over them";
      const cell = Floors.get(x, y, g), what = cell ? cell[1] : g === floorAt(x, y) ? combAt(x, y) : "";
      const me_ = myPos();
      if ((what && !GROUND.has(what) && what !== "f") || (!cell && !plainWalk(x, y)) || entityAt({x, y}) || (me_ && me_.x === x && me_.y === y)) return "Something is in the way";
      out.push([x, y, g, t]);
      if (t - g <= 1) return out;
      if (out.length >= RISE[1]) return "Too far down";
    }
  }

  // A ladder at height z on (x, y): its rails and rungs from its foot up to the top it leads to
  function drawLadder(x, y, z, sx, sy, S, a = 1) {
    const q = zoom, L = lean(x, y, z), top = L ? L.top : z + 2, shift = L ? L.dx * 3 : 0;
    // (its top: against a thing north of it, just over that thing's front edge; south of it, poking over its far edge
    // (the rest is behind it); beside it, along its side; leaning on nothing, two layers up)
    const edge = !L ? -shOf(top) : L.dy < 0 ? -shOf(top) - 2 : L.dy > 0 ? 16 - shOf(top) - 6 : -shOf(top) + 2;
    const X = sx(x) + (4 + shift) * q, y0 = sy(y) - shOf(z) * q + 14 * q, y1 = sy(y) + edge * q;
    ctx.globalAlpha = a;
    for (let yy = y0 - 3 * q; yy > y1 + q; yy -= 4 * q) { ctx.fillStyle = RAIL; ctx.fillRect(X + 2 * q, yy, 4 * q, q); ctx.fillStyle = RUNG; ctx.fillRect(X + 2 * q, yy - q, 4 * q, q); }
    for (const rx of [0, 6]) {
      ctx.fillStyle = Structures.INK; ctx.fillRect(X + rx * q, y1, 2 * q, y0 - y1);
      ctx.fillStyle = RAIL; ctx.fillRect(X + (rx + 1) * q, y1 + q, q, y0 - y1 - 2 * q);
      ctx.fillStyle = LIGHT; ctx.fillRect(X + (rx + 1) * q, y1 + q, q, q);
    }
    ctx.globalAlpha = 1;
  }
  // A step of a flight, drawn as stairs (it was a plank block, and a flight looked like boxes): over its top and its
  // front, small steps of the house's wood, a board to tread on and a darker riser, three to a tile, and a stringer
  // down each side; the same rhythm from the ground to the floor. Rising east or west, the treads are seen from above
  // across the tile and the front is the stringer, stepped as the flight climbs; rising south (towards you), each
  // step shows the front of its tread, the next one over the rest. (x, y, z: the cell; px, top: its top on screen)
  const TREAD = "#c49a6c", RISER = "#8a5f52", STRINGER = "#6e4a4f";
  function drawStep(x, y, z, px, top, a) {
    const q = zoom, ink = Structures.INK, up = WAYS.find(([dx, dy]) => solidAt(x + dx, y + dy, z + 1) && !solidAt(x + dx, y + dy, z + 2)) || [0, -1];
    const r = (col, X, Y, W_, H_) => { ctx.fillStyle = col; ctx.fillRect(px + X * q, top + Y * q, W_ * q, H_ * q); };
    const covered = solidAt(x, y, z + 1), front = !solidAt(x, y + 1, z), [dx, dy] = up;
    ctx.globalAlpha = a;
    if (dy < 0) {                                       // rising north: treads and risers face you
      const rows = (covered ? 0 : 16) + (front ? 8 : 0), y0 = covered ? 16 : 0;
      for (let k = 0; k < rows; k += 8) {
        r(RISER, 2, y0 + k, 12, 3); r(ink, 2, y0 + k, 12, 1);
        r(TREAD, 2, y0 + k + 3, 12, 5); r(LIGHT, 2, y0 + k + 7, 12, 1);
      }
      if (rows) for (const X of [0, 14]) { r(ink, X, y0, 2, rows); r(STRINGER, X + (X ? 0 : 1), y0, 1, rows); }
    } else if (dy > 0) {                                // rising south: the next step covers this one's back
      if (!covered) {
        r(TREAD, 2, 0, 12, 8); r(LIGHT, 2, 0, 12, 1); r(RISER, 2, 6, 12, 2);
        r(TREAD, 2, 8, 12, 8); r(LIGHT, 2, 8, 12, 1);
        for (const X of [0, 14]) { r(ink, X, 0, 2, 16); r(STRINGER, X + (X ? 0 : 1), 0, 1, 16); }
      }
      if (front) { r(STRINGER, 0, 16, 16, 8); r(ink, 0, 23, 16, 1); }
    } else {                                            // rising east or west: two treads across the tile, the lower one half a layer down
      const hi = dx > 0 ? 8 : 0, lo = 8 - hi;           // (the half nearer the top, the half nearer the foot: x of each)
      for (const [X, d] of [[hi, 0], [lo, 4]]) {
        if (!covered) {
          r(TREAD, X, d + 2, 8, 12); r(dx > 0 ? LIGHT : RISER, X, d + 2, 1, 12); r(dx > 0 ? RISER : LIGHT, X + 7, d + 2, 1, 12);
          r(ink, X, d, 8, 1); r(STRINGER, X, d + 1, 8, 1); r(STRINGER, X, d + 14, 8, 1); r(ink, X, d + 15, 8, 1);   // (the stringers, along its sides)
        }
        if (front) { const f0 = covered ? 16 : d + 16, f1 = 24; r(STRINGER, X, f0, 8, f1 - f0); if (!covered) r(LIGHT, X, f0, 8, 1); r(ink, X, 23, 8, 1); }
      }
    }
    ctx.globalAlpha = 1;
  }

  // What a click or a key means with stairs or a ladder in hand (intent.js asks first); nothing: not these
  function intent(p, shift) {
    const it = selected && !shift ? selected : null, s = myPos();
    if (!s || (it !== "stairs" && it !== "ladder") || (p.x === s.x && p.y === s.y)) return null;
    if (it === "stairs") {
      const f = flight(p.x, p.y), have = meObs ? meObs.self.inventory.stairs || 0 : 0;
      if (!Array.isArray(f)) return {text: f.why, ghost: it, ok: false};
      const ok = have >= f.length;
      return {text: ok ? `Build stairs (${f.length} step${f.length > 1 ? "s" : ""})` : `The flight takes ${f.length} stairs`, ghost: it, ok, near: 1, steps: f,
        draw: (sx, sy, S) => ghostFlight(f, sx, sy, S, ok), run: (d) => act("place", {dir: d, item: it})};
    }
    const z = settleNear(p.x, p.y, myZ(s.x, s.y)), c = FLOORS ? Floors.get(p.x, p.y, z) : null, on = c ? c[1] : z === standAt(p.x, p.y) ? combAt(p.x, p.y) : "";
    if ((on && !GROUND.has(on) && on !== "f") || !openAt(p.x, p.y, z)) return {text: "Something is in the way", ghost: it, ok: false, z};
    if (!FLOORS || !lean(p.x, p.y, z)) return {text: "A ladder goes against something taller", ghost: it, ok: false, z};
    return {text: "Place ladder", ghost: it, ok: true, near: 1, z, draw: (sx, sy, S) => drawLadder(p.x, p.y, z, sx, sy, S, .6), run: (d) => act("place", {dir: d, item: it, z})};
  }
  function ghostFlight(f, sx, sy, S, ok) {
    for (const [x, y, g, t] of f) for (let z = g + 1; z <= t; z++) Floors.cell("stairs", x, y, z, sx, sy, S, .55);
    for (const [x, y, , t] of f) { ctx.fillStyle = ok ? "rgba(120,220,120,.25)" : "rgba(230,80,70,.3)"; ctx.fillRect(sx(x), sy(y) - shOf(t) * zoom, S, S); }
  }
  return {openAt, climb, lean, onLadder, pace, paceOf, climbOf, flight, drawLadder, drawStep, intent, ghostFlight};
})();
