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
  const OUT = ["....##....", "...#oo#...", "..#oooo#..", ".#oooooo#.", "#oooooooo#", "####oo####", "...#oo#...", "...#oo#...", "...####..."];      // (the arrow up over the way's end, art px: ink round cream)
  const STILL = 2000, SLICE = 1.5, INK = "#5b3f36", DX = {N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0]};
  let gen = null, genKey = "", res = null, posKey = "", stoodAt = 0, cur = null, cap = null, capKey = "", capAt = 0, capSize = [0, 0], capSide = "", capBad = 0, youAt = null, fno = 0, landOf = null, landKey = "", lit = null, heading = null, led = false, follow = false, off = false;
  const api = {ms: 0, n: 0, runs: 0, get res() { return res; }, get cur() { return fresh(); }, get busy() { return !!gen; }, get led() { return led; }};
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
        if (rest.some((p) => p.digs.some((c) => solidAt(c.x, c.y, c.z)))) { gen = WayOut.find(W, {x: s.x, y: s.y, z: h}, {d: heading, sky: !roof, keep: res}); api.runs++; } }      // (...unless a way on foot is there now: looked for first, it wins. The tunnel's end opened beside you, "dig the wall west" stayed until you had run off it)
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
  const touching = () => document.body.classList.contains("touch");
  function hide(now) {      // the cap, the button that blinks: gone when nothing drew them this frame
    if (cap && capKey && (!cur || fno - capAt > 2)) { cap.style.display = "none"; capKey = ""; }
    const b = !touching() || !cur ? null : cur.now ? {up: "tDig", use: "tA", alt: "tB"}[cur.now.key] : hops() ? "tJump" : null;
    if (b !== lit) { for (const id of [lit, b]) { const e = id && document.getElementById(id); if (e) e.classList.toggle("way", id === b); } lit = b; }
  }
  // The one cap, BESIDE r (css px: the block's box, or the tile of the step): at the first of the sides in `pref` where it lies on nothing of you, of your name, of a key's box, nor off the screen.
  // Its side is kept while it lies on nothing of you nor off the screen ("the key glitches up and down" while sprinting: over and under took turns a tile, as the keys' boxes came and went), and its place is
  // whole art px of r's (u), as a body's: it moves with the land, never a px against it.
  // You are where you are drawn THIS frame (youAt, your feet; your body there: what paint() leaves bare), your name where it sits on you (Prompts.keep: drawn after this, hd.js, and only when
  // you are seen: it was the last frame's, or older, moved on by a frame's walk: at a sprint's start the cap sat 30 px off for 13 frames, then leapt over). Lying on your name (it lifts over
  // what you aim at, frame by frame) moves the cap only when it lasts 4 frames; on your body or off the screen, at once
  function pin(r, html, pref, not, u) {
    if (!cap) { cap = document.createElement("div"); cap.id = "waycap"; document.body.appendChild(cap); }
    if (html !== capKey) { capKey = html; cap.innerHTML = html; cap.style.display = "block"; capSize = [cap.offsetWidth, cap.offsetHeight]; capSide = ""; }
    const S = (v) => Math.round(v / u) * u, rx = S(r.x), ry = S(r.y), [w, h] = capSize, G = 6, keys = Target.drew.map((d) => d.r).filter((v) => v);
    const k = Prompts.keep || [], b0 = k[0], body = youAt ? [{x: youAt[0] - 8 * u, y: youAt[1] - 21 * u, w: 16 * u, h: 23 * u}] : [];
    const you = [...body, ...(youAt && b0 ? k.map((q) => ({...q, x: q.x - b0.x - b0.w / 2 + youAt[0], y: q.y - b0.y - b0.h + youAt[1]})) : k), ...(not ? [not] : [])];
    const my = ry + Math.round(r.h / 2 - h / 2), mx = rx + Math.round(r.w / 2 - w / 2), at = {right: [rx + Math.round(r.w) + G, my], left: [rx - G - w, my], over: [mx, ry - G - h], under: [mx, ry + Math.round(r.h) + G]};
    const on = (l, t = 0) => ([x, y]) => l.some((k) => x < k.x + k.w - t && k.x + t < x + w && y < k.y + k.h - t && k.y + t < y + h), off = ([x, y]) => x < 4 || y < 4 || x + w > innerWidth - 4 || y + h > innerHeight - 4, onYou = on(you), onKey = on(keys);
    // (the side kept until it is on you by more than your step's bob, 2 art px: a cap flush under your name went over the tile and back for one frame each step at a sprint)
    const kept = pref.includes(capSide) && !off(at[capSide]) && !on(body)(at[capSide]) && (!on(you, 2 * u)(at[capSide]) ? !(capBad = 0) : ++capBad < 4);
    const side = kept ? capSide : pref.find((k) => !off(at[k]) && !onYou(at[k]) && !onKey(at[k])) || pref.find((k) => !off(at[k]) && !onYou(at[k])) || pref[0];
    if (side !== capSide) capBad = 0;
    const p = at[capSide = side];
    cap.style.transform = `translate(${Math.round(p[0])}px, ${Math.round(p[1])}px)`; capAt = fno;
  }
  const bound = (q, css) => { const xs = q.map((v) => v[0] * css), ys = q.map((v) => v[1] * css), x = Math.min(...xs), y = Math.min(...ys); return {x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y}; };
  // Is a place of the land behind land as the eye sees it (hd.js `art().behind`, the same line: land south of it over the eye's line to it, 2 tan(pitch) levels a tile), its own tile's
  // roof too (own: a block of the land itself is not hidden by its own column); not what the x-ray window shows (a tile of it, or land it has opened: its floor there is the top). -> (x, y, z, own) -> bool
  function hider() {
    const H = typeof HdLook !== "undefined" && HdLook.on ? HdLook : null; if (!H || !H.cam) return () => false;
    const k = Math.tan(H.cam.pitch * Math.PI / 180) * 2, open = H.win && H.win.a > 0, top = (x, y) => { const w = open && H.winAt(x, y); return w ? Math.min(w[0], topAt(x, y)) : topAt(x, y); };
    return (x, y, z, own = true) => { const x0 = Math.floor(x), y0 = Math.floor(y), w = open && H.winAt(x0, y0); if (w && z >= w[0] - 1 && z <= w[1]) return false;      // (a tile of the window is seen, what stands before it cut away, as a body there: hd.js)
      for (let d = own ? 0 : 1; d <= 8; d++) if (top(x0, y0 + d) > z + Math.max(0, y0 + d - y) * k) return true; return false; };
  }
  // The picture of it, on g: at(x, y, z) -> where a point of the world is on g, u: an art px there, css: g's units -> css px
  function paint(g, at, u, now, css, wall) {
    api.block = null; api.hidden = 0; if (!cur) return; const t = now / 1000, me0 = myPos(), R = (v) => Math.round(v / u) * u, beat = Math.floor(t * 3) % 2, solid = (c) => solidAt(c.x, c.y, c.z);
    const rect = (x, y, w, h, col) => { g.fillStyle = col; g.fillRect(R(x), R(y), w * u, h * u); };
    const line = (a, b, col, dash, ph) => { const n = Math.max(1, Math.round(Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) / u)); for (let i = 0; i <= n; i++) { g.fillStyle = !dash || (((i + ph) % 4) + 4) % 4 < 2 ? col : INK; g.fillRect(R(a[0] + (b[0] - a[0]) * i / n), R(a[1] + (b[1] - a[1]) * i / n), u, u); } };      // (dash: two px of the colour, two of ink: seen on any ground)
    const fill = (q0, col) => { const q = q0[3][1] < q0[0][1] ? [q0[3], q0[2], q0[1], q0[0]] : q0; g.fillStyle = col; for (let y = R(q[0][1]); y < q[3][1]; y += u) { const k = (y - q[0][1]) / ((q[3][1] - q[0][1]) || 1), l = R(q[0][0] + (q[3][0] - q[0][0]) * k), r = R(q[1][0] + (q[2][0] - q[1][0]) * k); g.fillRect(l, y, r - l, u); } };
    const inq = (q, a, b) => { const l = [q[0][0] + (q[3][0] - q[0][0]) * b, q[0][1] + (q[3][1] - q[0][1]) * b], r = [q[1][0] + (q[2][0] - q[1][0]) * b, q[1][1] + (q[2][1] - q[1][1]) * b]; return [l[0] + (r[0] - l[0]) * a, l[1] + (r[1] - l[1]) * a]; };
    // (nothing of it is drawn on YOU: the block over your head, the one south of you lie on you in the picture: you stand in front of them, whole)
    const pe = ents.get("agent" + myId), ft = pe && at(pe.x + .5, pe.y + .5, myZ(me0.x, me0.y)), hid = hider(); let nh = 0;
    youAt = ft ? [R(ft[0]) * css, R(ft[1]) * css] : null;      // (you, as you are drawn this frame: pin)
    g.save(); if (ft) { g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); g.rect(R(ft[0]) - 8 * u, R(ft[1]) - 21 * u, 16 * u, 23 * u); g.clip("evenodd"); }
    // where you walk: a dot a tile and one between (down a drop: one a level, on its wall), a light running along them; a pip a block of that step still to break
    const P = cur.path, pts = [], k0 = P.findIndex((p, i) => i && p.digs.some(solid)), far = k0 > 1 ? k0 : 1e9;      // (you walk first: what comes after the first block is faint)
    for (let i = 1; i < P.length; i++) { const a = P[i - 1], b = P[i], top = Math.max(a.z, b.z);
      const pips = b.digs.filter((c) => solid(c) && c !== cur.next).length;
      const put = (x, y, z, o) => pts.push({p: at(x, y, z), i, h: hid(x, y, z), ...o});
      if ((a.x !== b.x || a.y !== b.y) && !pips) put((a.x + b.x) / 2 + .5, (a.y + b.y) / 2 + .5, top);
      for (let z = top - 1; z > b.z; z--) put(b.x + .5, b.y + .5, z);
      put(b.x + .5, b.y + .5, b.z, {pips}); }
    const wave = Math.floor(t * 9) % (pts.length + 5);
    pts.forEach(({p, i, pips, h}, j) => { if (!p) return; const on = j === wave || j === wave - 1, o = j % 2 ? 0 : (j % 4 ? u : -u), v = P[i].d, ox = v === "N" || v === "S" ? o : 0, oy = ox ? 0 : o;
      if (h) { nh++; g.globalAlpha = .6; rect(p[0] - u + ox, p[1] - u + oy, 1, 1, pips ? "#ff9d3c" : "#ffe08a"); rect(p[0] + ox, p[1] + oy, 1, 1, pips ? "#ff9d3c" : "#ffe08a"); g.globalAlpha = 1; }      // (behind land: two px of its middle, a checker, faint: "path rendering when hid by mountain")
      else if (pips) { rect(p[0] - 3 * u, p[1] - 3 * u, 6, 6, INK); rect(p[0] - 2 * u, p[1] - 2 * u, 4, 4, on ? "#ffe08a" : "#ff9d3c"); rect(p[0] - u, p[1] - u, 2, 2, INK); }      // (one a step, however many blocks it takes)
      else if (i > far) { rect(p[0] - u + ox, p[1] - u + oy, 3, 3, INK); rect(p[0] + ox, p[1] + oy, 1, 1, on ? "#ffffff" : "#ffe08a"); }
      else if (on) { rect(p[0] - 3 * u + ox, p[1] - 3 * u + oy, 6, 6, INK); rect(p[0] - 2 * u + ox, p[1] - 2 * u + oy, 4, 4, "#ffffff"); }
      else { rect(p[0] - 2 * u + ox, p[1] - 2 * u + oy, 4, 4, INK); rect(p[0] - u + ox, p[1] - u + oy, 2, 2, "#ffe08a"); } });
    // OUT IS HERE: where the way ends on the surface, one mark in the dots' own colours: a big dot on the ground and an arrow up over it, bobbing (it was faint rays where the sky
    // opens, unseen on grass, beside the wedge above); off the screen or under a button of a phone: an arrow at the edge, pointing to it
    const end = P[P.length - 1], sk = at(end.x + .5, end.y + .5, end.z); let edge = null; api.out = null;
    if (sk) { const tch = touching(), m = 16, sx = sk[0] * css, sy = (sk[1] - 9 * u) * css, cl = (v, a, b) => Math.max(a, Math.min(b, v)); let x = cl(sx, m, innerWidth - m), y = cl(sy, m + (tch ? 44 : 0), innerHeight - (tch ? 150 : 100));
      if (tch && x === sx && y === sy) for (const e of document.querySelectorAll("#tctx div, #tbtns div, #ttop div")) { const r = e.getBoundingClientRect(); if (r.width && sx > r.left - 8 && sx < r.right + 8 && sy > r.top - 30 && sy < r.bottom + 8) x = r.left - m; }
      if (x !== sx || y !== sy) edge = [x / css, y / css, Math.abs(sx - x) >= Math.abs(sy - y) ? [Math.sign(sx - x), 0] : [0, Math.sign(sy - y)]]; }
    if (sk && !edge) { const x = sk[0], y = sk[1], top = y - (beat ? 14 : 13) * u; api.out = [x * css, y * css]; if (hid(end.x + .5, end.y + .5, end.z)) { nh++; g.globalAlpha = .45; }      // (behind land: faint)
      rect(x - 4 * u, y - 4 * u, 8, 8, INK); rect(x - 3 * u, y - 3 * u, 6, 6, "#ffe08a"); rect(x - 2 * u, y - 2 * u, 4, 4, "#ff9d3c"); rect(x - u, y - u, 2, 2, "#fff8e8");
      OUT.forEach((row, j) => [...row].forEach((ch, i) => { if (ch !== ".") rect(x + (i - 5) * u, top + j * u, 1, 1, ch === "#" ? INK : beat ? "#ffffff" : "#ffe08a"); })); g.globalAlpha = 1; }
    // the next block to break: the block itself; its crack grows while it is dug (by hand: three times as long)
    let box = null; const c = cur.next, W = c && wall && wall(c.x, c.y, c.z), A = W || at, T = c && [A(c.x, c.y, c.z), A(c.x + 1, c.y, c.z), A(c.x + 1, c.y + 1, c.z), A(c.x, c.y + 1, c.z)], B = c && [A(c.x, c.y + 1, c.z - 1), A(c.x + 1, c.y + 1, c.z - 1)];   // (wall(cell) -> its own at: in the wall between the eye and you it is drawn folded into the opening, hd_level.js wallAt)
    if (c && T.every((v) => v) && B.every((v) => v)) { if (!W && hid(c.x + .5, c.y + .5, c.z, false)) { nh++; g.globalAlpha = .5; }      // (behind land south of it: faint; the land it is part of does not hide it)
      const F = [T[3], T[2], B[1], B[0]], col = beat ? "#ffffff" : "#fff1a8", ph = -Math.floor(t * 8), dug = progress && (myAction || pendingAct) && /^dig/.test(progress.tool) ? Math.min(1, (performance.now() - progress.t0) / progress.ms) : 0;
      fill(T, beat ? "rgba(255,190,70,.5)" : "rgba(255,150,40,.38)"); fill(F, `rgba(230,110,30,${(.46 + .3 * dug).toFixed(2)})`);
      const cr = (q, l) => l.map(([a, b]) => inq(q, a, b)), cracks = [cr(T, [[.18, .3], [.42, .48], [.36, .7], [.62, .62], [.82, .86]]), cr(F, [[.62, 0], [.55, .4], [.68, .7], [.6, 1]]), cr(T, [[.42, .48], [.7, .2], [.9, .34]]), cr(F, [[.55, .4], [.3, .55], [.2, 1]]), cr(T, [[.36, .7], [.12, .8]]), cr(F, [[.68, .7], [.9, .8]])];
      cracks.slice(0, 2 + Math.round(dug * 4)).forEach((l) => { for (let i = 1; i < l.length; i++) line(l[i - 1], l[i], "rgba(60,36,30,.85)"); });
      // (a block north or south of you lies behind you or on you in the picture, and nothing is drawn on you: the cap says which way it is)
      const E = [[T[0], T[1]], [T[1], T[2]], [T[3], T[2]], [T[0], T[3]], [T[3], B[0]], [T[2], B[1]], [B[0], B[1]]];
      for (const [a, b] of E) { line(a, b, col, true, ph); line([a[0], a[1] - u], [b[0], b[1] - u], col, true, ph); }                 // (its dashes two px thick, marching)
      g.globalAlpha = 1;
      box = api.block = bound([...T, ...B], css); const word = touching() ? (c.key === "up" ? "" : c.key === "use" ? "A" : "B") : capOf(c.key), turn = c.x === me0.x && c.y !== me0.y ? `<i class="${c.y < me0.y ? "N" : "S"}${word ? "" : " go"}"></i>` : "";      // (a phone: R's word is on its button, lit, and nowhere else: "Dig a step" stood twice, the cap's over the dots)
      if (c === cur.now && (word || turn)) pin(box, turn + esc(word), ft && (T[0][0] + T[1][0]) / 2 < ft[0] - u ? ["left", "over", "right", "under"] : ["right", "over", "left", "under"], null, u * css);
    }
    if (!cur.now && P[1].d && pe) { const b = P[1], [dx, dy] = DX[b.d], lv = typeof HdLook !== "undefined" && HdLook.level[2] !== null ? HdLook.level[2] : myZ(me0.x, me0.y), ex = pe.x + dx, ey = pe.y + dy;      // (the next move is a step: the way to go, beside the tile a step ahead of YOU as you are drawn (your eased place, your level between two tiles): it was beside the next tile of the way, a tile on at each step: it ran back to you and leapt a tile on, ten times a second at a sprint)
      const q = [at(ex, ey, lv), at(ex + 1, ey, lv), at(ex + 1, ey + 1, lv), at(ex, ey + 1, lv)];
      if (q.every((v) => v)) pin(bound(q, css), `<i class="${b.d}${hops() && !touching() ? "" : " go"}"></i>` + (hops() && !touching() ? esc(capOf("jump")) : ""), b.d === "E" || b.d === "W" ? ["over", "under", b.d === "E" ? "right" : "left"] : ["right", "left", "over", "under"], box, u * css); }
    g.restore(); api.hidden = nh; api.dots = pts.length;
    if (cap && capKey && capAt !== fno) { cap.style.display = "none"; capKey = ""; }      // (drawn by nothing this frame: gone now, not left two frames where it was while you ran on)
    if (edge) { const [x, y, d] = edge, tri = (n, back, col) => { for (let i = 0; i < n; i++) rect(x - (i + back) * u * d[0] - (d[0] ? 0 : i * u), y - (i + back) * u * d[1] - (d[1] ? 0 : i * u), d[0] ? 1 : 2 * i + 1, d[1] ? 1 : 2 * i + 1, col); };
      tri(7, -1, INK); tri(5, 1, beat ? "#ffffff" : "#fff1a8"); }
  }
  api.paint = paint; api.tick = tick; api.frame = () => { try { tick(performance.now()); } catch (e) { clear(); } };   // (once a frame, first: render.js frame)
  return api;
})();
