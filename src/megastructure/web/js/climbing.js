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
  // A step's tread, over its top (at screen px, top): lit at its nose, the next riser's shadow at its back
  function tread(x, y, z, px, top) {
    const q = zoom, up = WAYS.find(([dx, dy]) => solidAt(x + dx, y + dy, z + 1) && !solidAt(x + dx, y + dy, z + 2));
    if (!up) return;
    const r = (col, X, Y, W_, H_) => { ctx.fillStyle = col; ctx.fillRect(px + X * q, top + Y * q, W_ * q, H_ * q); };
    const [dx, dy] = up, back = "rgba(60,40,48,.35)";
    if (dy < 0) { r(back, 1, 1, 14, 3); r(LIGHT, 1, 14, 14, 1); }
    else if (dy > 0) { r(back, 1, 12, 14, 3); r(LIGHT, 1, 1, 14, 1); }
    else if (dx > 0) { r(back, 12, 1, 3, 14); r(LIGHT, 1, 1, 1, 14); }
    else { r(back, 1, 1, 3, 14); r(LIGHT, 14, 1, 1, 14); }
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
  return {openAt, climb, lean, onLadder, flight, drawLadder, tread, intent, ghostFlight};
})();
