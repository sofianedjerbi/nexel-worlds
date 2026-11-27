// The way out, SHOWN ("none of the view explain how i can get out the cave", "It looks like we can get out but no
// evident way or block to break !!"; the rule: show, don't tell). Under the land, when no way leads out on foot
// (trapped: wayout.js), or after two seconds standing still under a roof of land, the way it found is drawn in the picture:
//   - where you walk: small bright dots on the floors, in order, a light running along them towards the exit. Down
//     a drop they go down its wall. Past a block still to break, when you walk first, they are small and faint.
//   - the NEXT block to break: the block itself at its own place and height (a dashed box, an orange tint, a crack
//     that grows while it is dug); the ones after it: an orange pip on the way, where their step is (nine boxes in
//     a shaft were a heap, and over a meadow they floated);
//   - ONE key cap: beside that block the key that breaks it (a phone: its button's word; the button blinks), or,
//     when the next move is a step, an arrow beside its tile. Never on the block, on you, on your name or on a key's box (target.js);
//   - where the way comes under the open sky: a few rays and a glint; off the screen: an arrow at its edge.
// The key shown breaks the block whatever is in your hand and whichever way you face (digup.js `route`): with the
// pickaxe if you carry one anywhere, by hand if not (slower). Once it has been shown to somebody trapped it stays
// until they stand on the surface (`led`: the last open steps too), and the keys of what you face are not offered
// meanwhile (keyboard.js: "Space Dig into the wall" two levels under the grass). The stair that only LOOKS like a
// way (cold, past a wall) is dimmed by the land's painter, and warms from where the way joins it (`land`).
// The finder runs a slice a frame (SLICE ms), again only when your tile, your level or the land changed.
const WayShow = (() => {
  const STILL = 2000, SLICE = 1.5, DX = {N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0]};
  let gen = null, genKey = "", res = null, posKey = "", stoodAt = 0, cur = null, fno = 0, landOf = null, landKey = "", heading = null, led = false, follow = false, off = false;
  const api = {ms: 0, n: 0, runs: 0, get res() { return res; }, get cur() { return fresh(); }, get busy() { return !!gen; }, get led() { return led; }, get stood() { return performance.now() - stoodAt; }};   // (stood: ms you have stood where you are, as the frames count it: STILL of it shows the way)
  const W = {solid: (x, y, z) => solidAt(x, y, z), top: (x, y) => topAt(x, y), land: (x, y, z) => z > LOW + 2 && landSolid(x, y, z) && !Floors.built(x, y, z),
    step: (h, x, y, fx, fy) => landAt(h, x, y, fx, fy), ladder: (x, y, z, qx, qy, z2) => Climb.onLadder(x, y, z, qx, qy, z2),
    enter: (x, y, z) => stand(x, y, z),
    can: (x, y, h, dx, dy) => topAt(x, y) > h || inHole({x, y}, {x: x + dx, y: y + dy}, h),                 // (where R cuts a step: under the land, in a hole)
    on: (x, y, z, qx, qy) => GROUND.has(combAt(qx, qy)) || floorAt(qx, qy) !== z + 1,                    // (as keyboard.js offers Space's "Dig on")
    down: (x, y) => { const c = combAt(x, y); return !!c && GROUND.has(c) && !":n".includes(c); }};       // (...and X's "Dig down")
  function clear() { heading = null; gen = null; genKey = ""; res = null; cur = null; }
  // Once a frame, before the pictures: a slice of the search, then what is shown now (cur), or nothing
  function tick(now) {
    fno++;
    const s = me && myId !== null && meObs && !Build.on ? myPos() : null;
    if (!s) { led = follow = false; clear(); return hide(now); }
    const h = myZ(s.x, s.y), roof = topAt(s.x, s.y) > h, under = roof || !WayOut.out(W, s.x, s.y, h), pk      // (under a roof of land, or walled in: a shaft's bottom, the stair you are cutting out of it)
      = s.x + "," + s.y + "," + h;
    if (pk !== posKey || walking) { if (pk !== posKey) off = false; posKey = pk; stoodAt = now; }      // (put away: until you have WALKED: a key held against the wall you work on brought it back)
    if (!under) {      // (out, but for the last step up onto the surface, the way you were going: its dots, until you stand there)
      const d = (led || follow) && heading && DX[heading], q = d && {x: s.x + d[0], y: s.y + d[1]}, hd = heading, on = !!q && topAt(q.x, q.y) === h + 1 && landAt(h, q.x, q.y, s.x, s.y) === h + 1;
      if (!on) led = follow = false; clear();
      if (on) { heading = hd; cur = {path: [{x: s.x, y: s.y, z: h, d: null, digs: []}, {x: q.x, y: q.y, z: h + 1, d: hd, digs: []}], digs: [], next: null, now: null, sky: 1, trapped: false}; }
      return hide(now);
    }
    const k = pk + "," + landVer + "," + Floors.ver;
    if (k !== genKey) { genKey = k; const i = res && res.path ? res.path.findIndex((p) => p.x === s.x && p.y === s.y && p.z === h) : -1, rest = i >= 0 ? res.path.slice(i) : null;
      if (rest && WayOut.holds(W, rest)) { res = {...res, path: rest, sky: res.sky - i}; gen = null;      // (a step along the way shown, a block of it broken: it is the way still. Found again when you leave it or the land breaks it)
        if (rest.some((p) => p.digs.some((c) => solidAt(c.x, c.y, c.z)))) { gen = WayOut.find(W, {x: s.x, y: s.y, z: h}, {d: heading, sky: !roof, keep: res}); api.runs++; } }      // (...unless a way on foot is there now: looked for first, it wins. a tunnel's end opening beside you replaces "dig the wall west" at once, not once you have run off it)
      else { gen = WayOut.find(W, {x: s.x, y: s.y, z: h}, {d: heading, sky: !roof}); api.runs++; } }
    if (gen) { const t0 = performance.now(); let r; do r = gen.next(); while (!r.done && performance.now() - t0 < SLICE); api.ms = performance.now() - t0; if (r.done) { gen = null; res = r.value; api.n = res.n; } }
    cur = null;
    if (res && res.path && res.trapped) led = true;
    if (res && res.path && (led || follow || (!off && now - stoodAt > STILL && roof))) { follow = !led;      // (standing still under a roof of land. Under the sky only when trapped (led): a gorge's river you swim along, a valley you walk out of, is no trap: "the escape detection triggers when swimming between canyons")      // (follow: shown to somebody standing in a cave: it stays while they walk it, out from under the roof too)
      cur = from(s, h); if (cur) heading = cur.path[1].d || heading;
    }
    hide(now);
  }
  // The way from where you stand (s, h), the rest of the one found: a step along it, until the new one is found; null: you are not on it
  function from(s, h) {
    const i = res.path.findIndex((p) => p.x === s.x && p.y === s.y && p.z === h); if (i < 0 || i >= res.path.length - 1) return null;
    // (the finder's moves to the keys that break them: dig on and dig down are both X's, the break key's: "why do I break rocks with E?")
    const press = (c) => (c.key === "use" ? {...c, key: "alt", on: true} : c.key === "alt" ? {...c, down: true} : c);
    const path = res.path.slice(i), solid = (c) => solidAt(c.x, c.y, c.z), digs = path.flatMap((p) => p.digs).filter(solid).map(press), first = path[1].digs.filter(solid).map(press)[0] || null;
    return {path, digs, next: digs[0] || null, now: first, sky: res.sky - i, trapped: res.trapped};
  }
  // The way shown, as it is from where you stand NOW: a key pressed between two frames (you came down a level, the land changed) acted on the last frame's way: out of your own shaft, R dug
  // at the cell three over your new feet, out of reach, and nothing happened (the way of the level above was still shown till the next frame)
  function fresh() {
    if (!cur) return cur; const s = myPos(), h = s && myZ(s.x, s.y), p = cur.path[0];
    if (s && p.x === s.x && p.y === s.y && p.z === h) return cur;
    return (cur = s && res && res.path ? from(s, h) : null);
  }
  // The way's own key, for the corner, a phone's buttons and the press itself: null: no way is shown (the keys of what
  // you face are yours); {}: the next move is a step (no key); {key, text}: the next block's (keyboard.js, digup.js)
  api.offer = () => { const n = fresh() && cur.now, s = myPos(), moved = !!s && s.x + "," + s.y + "," + myZ(s.x, s.y) !== posKey;      // (moved: since the last frame: the way from here is not looked for yet)
    return n ? {key: n.key, text: n.on ? "Dig on" : n.down ? "Dig down" : n.x === s.x && n.y === s.y ? "Dig up" : "Dig a step"} : cur && hops() ? {key: "jump", text: "Jump"} : cur || ((led || follow) && (gen || moved)) ? {} : null; };
  // The next move is up a step: the jump key's (walk.js jumpKey: walking into it stops you)
  const hops = () => !!cur && !cur.now && cur.path.length > 1 && !cur.path[1].down && cur.path[1].z === cur.path[0].z + 1;
  // A key of your own pressed in a cave you can walk out of: you are at work here: the way is put away until you have walked and stood again
  api.mine = () => { if (cur && !led) { off = true; follow = false; } };
  api.rows = (rows) => rows;      // (hd.js: the keys beside what you face: keyboard.js `wayHides` has taken out what the way replaces)
  // For the land's painter (vox_style.js view.way): the floors of the way from its last block on ("x,y" -> level: they warm), and that floors off it are dimmed
  api.land = () => {
    if (!cur) return null; const k = genKey + "|" + cur.path.length + "|" + cur.digs.length; if (k === landKey) return landOf; landKey = k;
    let from = 0; cur.path.forEach((p, i) => { if (p.digs.some((c) => solidAt(c.x, c.y, c.z))) from = i; });
    const on = new Map(); for (const p of cur.path.slice(from)) if (!p.digs.some((c) => solidAt(c.x, c.y, c.z))) on.set(p.x + "," + p.y, p.z);      // (not a step still to cut: the land was opened on rock there: a black wedge and a thin line on the grass where the way comes out, "a rendering glitch")
    return (landOf = {on, dim: cur.trapped ? 1 : 0, key: k});
  };
  const shown = () => ({cur, api, hops, fno});      // (what the picture draws, once a frame: wayshow_draw.js)
  const hide = () => WayDraw.hide(shown());
  api.paint = (g, at, u, now, css, wall) => WayDraw.paint(g, at, u, now, css, wall, shown()); api.tick = tick; api.frame = () => { try { tick(performance.now()); } catch (e) { clear(); } };   // (once a frame, first: render.js frame)
  return api;
})();
