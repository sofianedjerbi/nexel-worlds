// The way out, SHOWN ("none of the view explain how i can get out the cave", "It looks like we can get out but no
// evident way or block to break !!"; the rule: show, don't tell). Under the land, when no way leads out on foot
// (trapped), or after two seconds standing still, the way wayout.js found is drawn in the picture:
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
  const STILL = 2000, FAR = 12, SLICE = 1.5, INK = "#5b3f36", DX = {N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0]};
  let gen = null, genKey = "", res = null, posKey = "", stoodAt = 0, cur = null, cap = null, capKey = "", capAt = 0, capSize = [0, 0], fno = 0, landOf = null, landKey = "", lit = null, heading = null, led = false, follow = false, off = false;
  const api = {ms: 0, n: 0, runs: 0, get res() { return res; }, get cur() { return cur; }, get busy() { return !!gen; }, get led() { return led; }};
  const W = {solid: (x, y, z) => solidAt(x, y, z), top: (x, y) => topAt(x, y), land: (x, y, z) => z > LOW + 2 && landSolid(x, y, z) && !Floors.built(x, y, z),
    step: (h, x, y, fx, fy) => landAt(h, x, y, fx, fy), ladder: (x, y, z, qx, qy, z2) => Climb.onLadder(x, y, z, qx, qy, z2),
    enter: (x, y, z) => { const c = Floors.get(x, y, z); return c && FLOORS ? !SOLID.has(c[1]) : z !== floorAt(x, y) || plainWalk(x, y); },
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
      if (rest && WayOut.holds(W, rest)) { res = {...res, path: rest, sky: res.sky - i}; gen = null; }      // (a step along the way shown, a block of it broken: it is the way still. Found again when you leave it or the land breaks it)
      else { gen = WayOut.find(W, {x: s.x, y: s.y, z: h}, {d: heading}); api.runs++; } }
    if (gen) { const t0 = performance.now(); let r; do r = gen.next(); while (!r.done && performance.now() - t0 < SLICE); api.ms = performance.now() - t0; if (r.done) { gen = null; res = r.value; api.n = res.n; } }
    cur = null;
    if (res && res.path && res.trapped) led = true;
    if (res && res.path && (led || follow || (!off && now - stoodAt > STILL && (roof || res.blocks > 0 || res.path.length > FAR)))) { follow = !led;      // (standing still: under a roof of land; or under the sky where the way is long or has a block to break: a gorge's floor. Not at a cliff's foot, three steps from the open)      // (follow: shown to somebody standing in a cave: it stays while they walk it, out from under the roof too)
      const i = res.path.findIndex((p) => p.x === s.x && p.y === s.y && p.z === h);                     // (a step along it: the rest of it, until the new one is found)
      if (i >= 0 && i < res.path.length - 1) { const path = res.path.slice(i), solid = (c) => solidAt(c.x, c.y, c.z), digs = path.flatMap((p) => p.digs).filter(solid), first = path[1].digs.filter(solid)[0] || null;
        cur = {path, digs, next: digs[0] || null, now: first, sky: res.sky - i, trapped: res.trapped}; heading = path[1].d || heading; }
    }
    hide(now);
  }
  // The way's own key, for the corner, a phone's buttons and the press itself: null: no way is shown (the keys of what
  // you face are yours); {}: the next move is a step (no key); {key, text}: the next block's (keyboard.js, digup.js)
  api.offer = () => { const n = cur && cur.now, s = n && myPos(); return n ? {key: n.key, text: n.key === "use" ? "Dig on" : n.key === "alt" ? "Dig down" : n.x === s.x && n.y === s.y ? "Dig up" : "Dig a step"} : cur || ((led || follow) && gen) ? {} : null; };
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
    const b = cur && cur.now && touching() ? {up: "tDig", use: "tA", alt: "tB"}[cur.now.key] : null;
    if (b !== lit) { for (const id of [lit, b]) { const e = id && document.getElementById(id); if (e) e.classList.toggle("way", id === b); } lit = b; }
  }
  // The one cap, BESIDE r (css px: the block's box, or the tile of the step): at the first of the sides in `pref` where it lies on nothing of you, of your name, nor off the screen
  function pin(r, html, pref, not) {
    if (!cap) { cap = document.createElement("div"); cap.id = "waycap"; document.body.appendChild(cap); }
    if (html !== capKey) { capKey = html; cap.innerHTML = html; cap.style.display = "block"; capSize = [cap.offsetWidth, cap.offsetHeight]; }
    const [w, h] = capSize, G = 6, keep = [...(Prompts.keep || []), ...(not ? [not] : []), ...Target.drew.map((d) => d.r).filter((v) => v)], my = r.y + r.h / 2 - h / 2, mx = r.x + r.w / 2 - w / 2, at = {right: [r.x + r.w + G, my], left: [r.x - G - w, my], over: [mx, r.y - G - h], under: [mx, r.y + r.h + G]};
    const bad = ([x, y]) => x < 4 || y < 4 || x + w > innerWidth - 4 || y + h > innerHeight - 4 || keep.some((k) => x < k.x + k.w && k.x < x + w && y < k.y + k.h && k.y < y + h);
    const p = at[pref.find((k) => !bad(at[k])) || pref[0]];
    cap.style.transform = `translate(${Math.round(p[0])}px, ${Math.round(p[1])}px)`; capAt = fno;
  }
  const bound = (q, css) => { const xs = q.map((v) => v[0] * css), ys = q.map((v) => v[1] * css), x = Math.min(...xs), y = Math.min(...ys); return {x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y}; };
  // The picture of it, on g: at(x, y, z) -> where a point of the world is on g, u: an art px there, css: g's units -> css px
  function paint(g, at, u, now, css) {
    api.block = null; if (!cur) return; const t = now / 1000, me0 = myPos(), R = (v) => Math.round(v / u) * u, beat = Math.floor(t * 3) % 2, solid = (c) => solidAt(c.x, c.y, c.z);
    const rect = (x, y, w, h, col) => { g.fillStyle = col; g.fillRect(R(x), R(y), w * u, h * u); };
    const line = (a, b, col, dash, ph) => { const n = Math.max(1, Math.round(Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) / u)); for (let i = 0; i <= n; i++) { g.fillStyle = !dash || (((i + ph) % 4) + 4) % 4 < 2 ? col : INK; g.fillRect(R(a[0] + (b[0] - a[0]) * i / n), R(a[1] + (b[1] - a[1]) * i / n), u, u); } };      // (dash: two px of the colour, two of ink: seen on any ground)
    const fill = (q, col) => { g.fillStyle = col; for (let y = R(q[0][1]); y < q[3][1]; y += u) { const k = (y - q[0][1]) / ((q[3][1] - q[0][1]) || 1), l = R(q[0][0] + (q[3][0] - q[0][0]) * k), r = R(q[1][0] + (q[2][0] - q[1][0]) * k); g.fillRect(l, y, r - l, u); } };
    const inq = (q, a, b) => { const l = [q[0][0] + (q[3][0] - q[0][0]) * b, q[0][1] + (q[3][1] - q[0][1]) * b], r = [q[1][0] + (q[2][0] - q[1][0]) * b, q[1][1] + (q[2][1] - q[1][1]) * b]; return [l[0] + (r[0] - l[0]) * a, l[1] + (r[1] - l[1]) * a]; };
    // (nothing of it is drawn on YOU: the block over your head, the one south of you lie on you in the picture: you stand in front of them, whole)
    const pe = ents.get("agent" + myId), ft = pe && at(pe.x + .5, pe.y + .5, myZ(me0.x, me0.y));
    g.save(); if (ft) { g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); g.rect(R(ft[0]) - 8 * u, R(ft[1]) - 21 * u, 16 * u, 23 * u); g.clip("evenodd"); }
    // where you walk: a dot a tile and one between (down a drop: one a level, on its wall), a light running along them; a pip a block of that step still to break
    const P = cur.path, pts = [], k0 = P.findIndex((p, i) => i && p.digs.some(solid)), far = k0 > 1 ? k0 : 1e9;      // (you walk first: what comes after the first block is faint)
    for (let i = 1; i < P.length; i++) { const a = P[i - 1], b = P[i], top = Math.max(a.z, b.z);
      const pips = b.digs.filter((c) => solid(c) && c !== cur.next).length;
      if ((a.x !== b.x || a.y !== b.y) && !pips) pts.push({p: at((a.x + b.x) / 2 + .5, (a.y + b.y) / 2 + .5, top), i});
      for (let z = top - 1; z > b.z; z--) pts.push({p: at(b.x + .5, b.y + .5, z), i});
      pts.push({p: at(b.x + .5, b.y + .5, b.z), i, pips}); }
    const wave = Math.floor(t * 9) % (pts.length + 5);
    pts.forEach(({p, i, pips}, j) => { if (!p) return; const on = j === wave || j === wave - 1, o = j % 2 ? 0 : (j % 4 ? u : -u), v = P[i].d, ox = v === "N" || v === "S" ? o : 0, oy = ox ? 0 : o;
      if (pips) { rect(p[0] - 3 * u, p[1] - 3 * u, 6, 6, INK); rect(p[0] - 2 * u, p[1] - 2 * u, 4, 4, on ? "#ffe08a" : "#ff9d3c"); rect(p[0] - u, p[1] - u, 2, 2, INK); }      // (one a step, however many blocks it takes)
      else if (i > far) { rect(p[0] - u + ox, p[1] - u + oy, 3, 3, INK); rect(p[0] + ox, p[1] + oy, 1, 1, on ? "#ffffff" : "#ffe08a"); }
      else if (on) { rect(p[0] - 3 * u + ox, p[1] - 3 * u + oy, 6, 6, INK); rect(p[0] - 2 * u + ox, p[1] - 2 * u + oy, 4, 4, "#ffffff"); }
      else { rect(p[0] - 2 * u + ox, p[1] - 2 * u + oy, 4, 4, INK); rect(p[0] - u + ox, p[1] - u + oy, 2, 2, "#ffe08a"); } });
    // OUT IS HERE: where the way ends on the surface, one mark in the dots' own colours: a big dot on the ground and an arrow up over it, bobbing (it was faint rays where the sky
    // opens, unseen on grass, beside the wedge above); off the screen or under a button of a phone: an arrow at the edge, pointing to it
    const end = P[P.length - 1], sk = at(end.x + .5, end.y + .5, end.z); let edge = null; api.out = null;
    if (sk) { const tch = touching(), m = 16, sx = sk[0] * css, sy = (sk[1] - 9 * u) * css, cl = (v, a, b) => Math.max(a, Math.min(b, v)); let x = cl(sx, m, innerWidth - m), y = cl(sy, m + (tch ? 44 : 0), innerHeight - (tch ? 150 : 100));
      if (tch && x === sx && y === sy) for (const e of document.querySelectorAll("#tctx div, #tbtns div, #ttop div")) { const r = e.getBoundingClientRect(); if (r.width && sx > r.left - 8 && sx < r.right + 8 && sy > r.top - 30 && sy < r.bottom + 8) x = r.left - m; }
      if (x !== sx || y !== sy) edge = [x / css, y / css, Math.abs(sx - x) >= Math.abs(sy - y) ? [Math.sign(sx - x), 0] : [0, Math.sign(sy - y)]]; }
    if (sk && !edge) { const x = sk[0], y = sk[1], top = y - (beat ? 14 : 13) * u; api.out = [x * css, y * css];
      rect(x - 4 * u, y - 4 * u, 8, 8, INK); rect(x - 3 * u, y - 3 * u, 6, 6, "#ffe08a"); rect(x - 2 * u, y - 2 * u, 4, 4, "#ff9d3c"); rect(x - u, y - u, 2, 2, "#fff8e8");
      OUT.forEach((row, j) => [...row].forEach((ch, i) => { if (ch !== ".") rect(x + (i - 5) * u, top + j * u, 1, 1, ch === "#" ? INK : beat ? "#ffffff" : "#ffe08a"); })); }
    // the next block to break: the block itself; its crack grows while it is dug (by hand: three times as long)
    let box = null; const c = cur.next, T = c && [at(c.x, c.y, c.z), at(c.x + 1, c.y, c.z), at(c.x + 1, c.y + 1, c.z), at(c.x, c.y + 1, c.z)], B = c && [at(c.x, c.y + 1, c.z - 1), at(c.x + 1, c.y + 1, c.z - 1)];
    if (c && T.every((v) => v) && B.every((v) => v)) {
      const F = [T[3], T[2], B[1], B[0]], col = beat ? "#ffffff" : "#fff1a8", ph = -Math.floor(t * 8), dug = progress && (myAction || pendingAct) && /^dig/.test(progress.tool) ? Math.min(1, (performance.now() - progress.t0) / progress.ms) : 0;
      fill(T, beat ? "rgba(255,190,70,.5)" : "rgba(255,150,40,.38)"); fill(F, `rgba(230,110,30,${(.46 + .3 * dug).toFixed(2)})`);
      const cr = (q, l) => l.map(([a, b]) => inq(q, a, b)), cracks = [cr(T, [[.18, .3], [.42, .48], [.36, .7], [.62, .62], [.82, .86]]), cr(F, [[.62, 0], [.55, .4], [.68, .7], [.6, 1]]), cr(T, [[.42, .48], [.7, .2], [.9, .34]]), cr(F, [[.55, .4], [.3, .55], [.2, 1]]), cr(T, [[.36, .7], [.12, .8]]), cr(F, [[.68, .7], [.9, .8]])];
      cracks.slice(0, 2 + Math.round(dug * 4)).forEach((l) => { for (let i = 1; i < l.length; i++) line(l[i - 1], l[i], "rgba(60,36,30,.85)"); });
      // (a block north or south of you lies behind you or on you in the picture, and nothing is drawn on you: the cap says which way it is)
      const E = [[T[0], T[1]], [T[1], T[2]], [T[3], T[2]], [T[0], T[3]], [T[3], B[0]], [T[2], B[1]], [B[0], B[1]]];
      for (const [a, b] of E) { line(a, b, col, true, ph); line([a[0], a[1] - u], [b[0], b[1] - u], col, true, ph); }                 // (its dashes two px thick, marching)
      box = api.block = bound([...T, ...B], css); const word = touching() ? (c.key === "up" ? "" : c.key === "use" ? "A" : "B") : capOf(c.key), turn = c.x === me0.x && c.y !== me0.y ? `<i class="${c.y < me0.y ? "N" : "S"}${word ? "" : " go"}"></i>` : "";      // (a phone: R's word is on its button, lit, and nowhere else: "Dig a step" stood twice, the cap's over the dots)
      if (c === cur.now && (word || turn)) pin(box, turn + esc(word), ft && (T[0][0] + T[1][0]) / 2 < ft[0] - u ? ["left", "over", "right", "under"] : ["right", "over", "left", "under"]);
    }
    if (!cur.now && P[1].d) { const b = P[1], q = [at(b.x, b.y, b.z), at(b.x + 1, b.y, b.z), at(b.x + 1, b.y + 1, b.z), at(b.x, b.y + 1, b.z)];      // (the next move is a step: the way to go, beside its tile)
      if (q.every((v) => v)) pin(bound(q, css), `<i class="${b.d} go"></i>`, b.d === "E" || b.d === "W" ? ["over", "under", b.d === "E" ? "right" : "left"] : ["right", "left", "over", "under"], box); }
    g.restore();
    if (edge) { const [x, y, d] = edge, tri = (n, back, col) => { for (let i = 0; i < n; i++) rect(x - (i + back) * u * d[0] - (d[0] ? 0 : i * u), y - (i + back) * u * d[1] - (d[1] ? 0 : i * u), d[0] ? 1 : 2 * i + 1, d[1] ? 1 : 2 * i + 1, col); };
      tri(7, -1, INK); tri(5, 1, beat ? "#ffffff" : "#fff1a8"); }
  }
  api.paint = paint; api.tick = tick;
  { const f0 = frame; frame = function (now) { try { tick(performance.now()); } catch (e) { clear(); } f0(now); }; }
  return api;
})();
