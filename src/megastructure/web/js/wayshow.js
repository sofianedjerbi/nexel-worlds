// The way out, SHOWN ("none of the view explain how i can get out the cave", "It looks like we can get out but no
// evident way or block to break !!"; the rule: show, don't tell). Under the land, when no way leads out on foot
// (trapped), or after two seconds standing still, the way wayout.js found is drawn in the picture:
//   - where you walk: small bright dots on the floors, in order, a light running along them towards the exit;
//   - every block to break: the BLOCK itself at its own place and height (a dashed box, an orange tint, a crack),
//     the next one brighter, its dashes marching, and the key that breaks it pinned on it (a phone: its button's
//     word; the button itself blinks). No pickaxe in hand: the boxes grey, a pickaxe drawn on the next;
//   - where the way comes under the open sky: a few rays and a glint.
// R (digup.js) breaks the next block whichever way you face while it is shown. The stair that only LOOKS like a
// way (cold, past a wall) is dimmed by the land's painter, and warms from where the way joins it (`land`).
// The finder runs a slice a frame (SLICE ms), again only when your tile, your level or the land changed.
const WayShow = (() => {
  const STILL = 2000, SLICE = 1.5, INK = "#5b3f36", DX = {N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0]};
  let gen = null, genKey = "", res = null, posKey = "", stoodAt = 0, cur = null, cap = null, capKey = "", capAt = 0, fno = 0, landOf = null, landKey = "", lit = null, heading = null;
  const api = {ms: 0, n: 0, runs: 0, get res() { return res; }, get cur() { return cur; }, get busy() { return !!gen; }};
  const W = {solid: (x, y, z) => solidAt(x, y, z), top: (x, y) => topAt(x, y), land: (x, y, z) => z > LOW + 2 && landSolid(x, y, z) && !Floors.built(x, y, z),
    step: (h, x, y, fx, fy) => landAt(h, x, y, fx, fy), ladder: (x, y, z, qx, qy, z2) => Climb.onLadder(x, y, z, qx, qy, z2),
    enter: (x, y, z) => { const c = Floors.get(x, y, z); return c && FLOORS ? !SOLID.has(c[1]) : z !== floorAt(x, y) || plainWalk(x, y); },
    can: (x, y, h, dx, dy) => topAt(x, y) > h || inHole({x, y}, {x: x + dx, y: y + dy}, h),                 // (as digup.js offers R)
    on: (x, y, z, qx, qy) => GROUND.has(combAt(qx, qy)) || floorAt(qx, qy) !== z + 1,                    // (as keyboard.js offers Space's "Dig on")
    down: (x, y) => { const c = combAt(x, y); return !!c && GROUND.has(c) && !":n".includes(c); }};       // (...and X's "Dig down")
  function clear() { heading = null; gen = null; genKey = ""; res = null; cur = null; }
  // Once a frame, before the pictures: a slice of the search, then what is shown now (cur), or nothing
  function tick(now) {
    fno++;
    const s = me && myId !== null && meObs && !Build.on ? myPos() : null;
    if (!s) { clear(); return hide(now); }
    const h = myZ(s.x, s.y), roof = topAt(s.x, s.y) > h, under = roof || !WayOut.out(W, s.x, s.y, h), pk      // (under a roof of land, or walled in: a shaft's bottom, the stair you are cutting out of it)
      = s.x + "," + s.y + "," + h;
    if (pk !== posKey || walking) { posKey = pk; stoodAt = now; }
    if (!under) { clear(); return hide(now); }
    const k = pk + "," + landVer + "," + Floors.ver;
    if (k !== genKey) { genKey = k; gen = WayOut.find(W, {x: s.x, y: s.y, z: h}, {d: heading}); api.runs++; }
    if (gen) { const t0 = performance.now(); let r; do r = gen.next(); while (!r.done && performance.now() - t0 < SLICE); api.ms = performance.now() - t0; if (r.done) { gen = null; res = r.value; api.n = res.n; } }
    cur = null;
    if (res && res.path && (res.trapped || (roof && now - stoodAt > STILL))) {      // (standing still: under a roof of land only; at a cliff's foot the pit is open too)
      const i = res.path.findIndex((p) => p.x === s.x && p.y === s.y && p.z === h);                     // (a step along it: the rest of it, until the new one is found)
      if (i >= 0 && i < res.path.length - 1) { const path = res.path.slice(i), solid = (c) => solidAt(c.x, c.y, c.z), digs = path.flatMap((p) => p.digs).filter(solid), first = path[1].digs.filter(solid)[0] || null;
        cur = {path, digs, next: digs[0] || null, now: first, sky: res.sky - i, grey: inHand() !== "pickaxe", trapped: res.trapped}; heading = path[1].d || heading; }
    }
    hide(now);
  }
  // R's block while the way is shown: the next one to break, if it is R's -> {q: the tile it is cut towards, d} (digup.js: whichever way you face)
  api.want = () => (cur && cur.now && cur.now.key === "up" && !cur.grey ? {q: {x: cur.path[1].x, y: cur.path[1].y}, d: cur.path[1].d} : null);
  // The keys beside what you face (prompts.js), while you are trapped and the next block carries its key: that key's row alone ("Space Dig on" stood first beside the wall, and led on into the rock)
  api.rows = (rows) => (cur && cur.trapped && !cur.grey ? rows.filter((r) => cur.now && r[0] === capOf(cur.now.key)) : rows);      // (...and none while the next move is a step: Space there breaks the block you are to hop onto)
  // For the land's painter (vox_style.js view.way): the floors of the way from its last block on ("x,y" -> level: they warm), and that floors off it are dimmed
  api.land = () => {
    if (!cur) return null; const k = genKey + "|" + cur.path.length + "|" + cur.digs.length; if (k === landKey) return landOf; landKey = k;
    let from = 0; cur.path.forEach((p, i) => { if (p.digs.some((c) => solidAt(c.x, c.y, c.z))) from = i; });
    const on = new Map(); for (const p of cur.path.slice(from)) on.set(p.x + "," + p.y, p.z);
    return (landOf = {on, dim: cur.trapped ? 1 : 0, key: k});
  };
  function hide(now) {      // the key on the block, the button that blinks: gone when nothing drew them this frame
    if (cap && capKey && (!cur || fno - capAt > 2)) { cap.style.display = "none"; capKey = ""; }
    const b = cur && cur.now && !cur.grey && document.body.classList.contains("touch") ? {up: "tDig", use: "tA", alt: "tB"}[cur.now.key] : null;
    if (b !== lit) { for (const id of [lit, b]) { const e = id && document.getElementById(id); if (e) e.classList.toggle("way", id === b); } lit = b; }
  }
  function pin(x, y, c) {   // the key that breaks block c, on it (css px). By keys, Space's wall not faced: the way to turn first
    const touch = document.body.classList.contains("touch"), p = ents.get("agent" + myId), d = c.d && DX[c.d], faced = !d || (p && (p.fx || 0) === d[0] && (p.fy || (p.fx ? 0 : 1)) === d[1]);
    const up = c.key === "up" && typeof DigUp !== "undefined" ? DigUp.aim() : null;
    const text = touch ? (c.key === "up" ? (up ? up.text : "Dig up") : c.key === "use" ? "A" : "B") : capOf(c.key), k = text + "|" + (c.key === "use" && !faced ? c.d : "");
    if (!cap) { cap = document.createElement("div"); cap.id = "waycap"; document.body.appendChild(cap); }
    if (k !== capKey) { capKey = k; cap.innerHTML = (c.key === "use" && !faced ? `<i class="${c.d}"></i>` : "") + esc(text); cap.style.display = "block"; }
    cap.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px) translate(-50%, -100%)`;
  }
  // The picture of it, on g: at(x, y, z) -> where a point of the world is on g, u: an art px there, css: g's units -> css px
  function paint(g, at, u, now, css) {
    if (!cur) return; const t = now / 1000, me0 = myPos(), R = (v) => Math.round(v / u) * u, beat = Math.floor(t * 3) % 2;
    const rect = (x, y, w, h, col) => { g.fillStyle = col; g.fillRect(R(x), R(y), w * u, h * u); };
    const line = (a, b, col, dash, ph) => { const n = Math.max(1, Math.round(Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) / u)); for (let i = 0; i <= n; i++) { g.fillStyle = !dash || (((i + ph) % 4) + 4) % 4 < 2 ? col : INK; g.fillRect(R(a[0] + (b[0] - a[0]) * i / n), R(a[1] + (b[1] - a[1]) * i / n), u, u); } };      // (dash: two px of the colour, two of ink: seen on any ground)
    const fill = (q, col) => { g.fillStyle = col; for (let y = R(q[0][1]); y < q[3][1]; y += u) { const k = (y - q[0][1]) / ((q[3][1] - q[0][1]) || 1), l = R(q[0][0] + (q[3][0] - q[0][0]) * k), r = R(q[1][0] + (q[2][0] - q[1][0]) * k); g.fillRect(l, y, r - l, u); } };
    const inq = (q, a, b) => { const l = [q[0][0] + (q[3][0] - q[0][0]) * b, q[0][1] + (q[3][1] - q[0][1]) * b], r = [q[1][0] + (q[2][0] - q[1][0]) * b, q[1][1] + (q[2][1] - q[1][1]) * b]; return [l[0] + (r[0] - l[0]) * a, l[1] + (r[1] - l[1]) * a]; };
    // (nothing of it is drawn on YOU: the block over your head, the one south of you lie on you in the picture: you stand in front of them, whole)
    const pe = ents.get("agent" + myId), ft = pe && at(pe.x + .5, pe.y + .5, myZ(me0.x, me0.y)), late = [];
    g.save(); if (ft) { g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); g.rect(R(ft[0]) - 8 * u, R(ft[1]) - 21 * u, 16 * u, 23 * u); g.clip("evenodd"); }
    // where you walk: a dot a tile and one between, a light running along them
    const P = cur.path, pts = [];
    for (let i = 1; i < P.length; i++) { const a = P[i - 1], b = P[i]; pts.push(at((a.x + b.x) / 2 + .5, (a.y + b.y) / 2 + .5, Math.max(a.z, b.z)), at(b.x + .5, b.y + .5, b.z)); }
    const wave = Math.floor(t * 9) % (pts.length + 5);
    pts.forEach((p, j) => { if (!p) return; const on = j === wave || j === wave - 1, o = j % 2 ? 0 : (j % 4 ? u : -u), v = P[(j >> 1) + 1].d, ox = v === "N" || v === "S" ? o : 0, oy = ox ? 0 : o;
      if (on) { rect(p[0] - 3 * u + ox, p[1] - 3 * u + oy, 6, 6, INK); rect(p[0] - 2 * u + ox, p[1] - 2 * u + oy, 4, 4, "#ffffff"); }
      else { rect(p[0] - 2 * u + ox, p[1] - 2 * u + oy, 4, 4, INK); rect(p[0] - u + ox, p[1] - u + oy, 2, 2, cur.grey && cur.digs.length ? "#e8e4d8" : "#ffe08a"); } });
    // the open sky: rays down on the first place under it, a glint
    const sk = cur.sky > 0 && cur.sky < P.length ? at(P[cur.sky].x + .5, P[cur.sky].y + .5, P[cur.sky].z) : null;
    if (sk) { for (const k of [-1, 0, 1]) for (let j = 5; j < 22; j++) if ((j + Math.floor(t * 6) + k * 2) % 6 < 4) rect(sk[0] + (k * 5 + (j >> 1) - 5) * u, sk[1] - j * u, 1, 1, k ? "rgba(255,240,180,.75)" : "rgba(255,252,225,.95)");
      const a = beat ? 3 : 2; rect(sk[0] - u, sk[1] - 9 * u, 2, 2, "#ffffff"); rect(sk[0] - a * u, sk[1] - 9 * u, 2 * a, 1, "#fff6c8"); rect(sk[0] - u, sk[1] - (8 + a) * u, 1, 2 * a, "#fff6c8"); }
    // the blocks to break, the far ones first
    const soon = new Set(cur.path.slice(1).find((p) => p.digs.some((c) => cur.digs.includes(c)))?.digs || []);      // (the blocks of the next step: whole; the ones after: their top's edges, thin: nine boxes on each other in a shaft were a heap)
    for (const c of cur.digs.slice().reverse()) {
      const far = !soon.has(c), T = [at(c.x, c.y, c.z), at(c.x + 1, c.y, c.z), at(c.x + 1, c.y + 1, c.z), at(c.x, c.y + 1, c.z)], B = [at(c.x, c.y + 1, c.z - 1), at(c.x + 1, c.y + 1, c.z - 1)]; if (T.some((v) => !v) || B.some((v) => !v)) continue;
      const nx = c === cur.next, F = [T[3], T[2], B[1], B[0]], col = cur.grey ? (nx ? "#e4e4ee" : "#a9a9ba") : nx ? (beat ? "#ffffff" : "#fff1a8") : far ? "#c98a3c" : "#ffb84a", ph = nx ? -Math.floor(t * 8) : 0;
      const mine = far;
      if (!mine) fill(T, cur.grey ? "rgba(150,150,170,.3)" : nx ? (beat ? "rgba(255,190,70,.5)" : "rgba(255,150,40,.38)") : "rgba(255,150,40,.24)"); if (!mine) fill(F, cur.grey ? "rgba(90,90,110,.34)" : nx ? "rgba(230,110,30,.46)" : "rgba(220,110,30,.26)");
      const crack = [[.18, .3], [.42, .48], [.36, .7], [.62, .62], [.82, .86]].map(([a, b]) => inq(T, a, b)), cf = [[.62, 0], [.55, .4], [.68, .7], [.6, 1]].map(([a, b]) => inq(F, a, b));
      if (!mine) for (const l of [crack, cf]) for (let i = 1; i < l.length; i++) line(l[i - 1], l[i], "rgba(60,36,30,.85)");
      const E = [[T[0], T[1]], [T[1], T[2]], [T[3], T[2]], [T[0], T[3]], ...(far ? [] : [[T[3], B[0]], [T[2], B[1]], [B[0], B[1]]])];
      for (const [a, b] of E) line(a, b, col, true, ph);
      if (nx) for (const [a, b] of E) line([a[0], a[1] - u], [b[0], b[1] - u], col, true, ph);                                    // (the next one: its dashes two px thick)
      const top = inq(T, .5, .1);
      // (the pickaxe: not on you: over your head, if its block lies on you)
      if (nx && cur.grey) late.push(() => { const ic = ghostIcon("pickaxe"), w = ic.width * u, x = R(top[0] - w / 2), hit = ft && Math.abs(top[0] - ft[0]) < 8 * u + w / 2 && top[1] > ft[1] - 22 * u - ic.height * u && top[1] < ft[1] + 14 * u, y = R((hit ? ft[1] - 24 * u : top[1]) - ic.height * u - 2 * u + (beat ? u : 0)); g.imageSmoothingEnabled = false; rect(x - u, y - u, ic.width + 2, ic.height + 2, "rgba(40,28,26,.7)"); g.drawImage(ic, x, y, w, ic.height * u); });
      else if (c === cur.now && !cur.grey) { pin(top[0] * css, top[1] * css - (me0 && c.x === me0.x && c.y === me0.y ? 30 : 6), c); capAt = fno; }
    }
    g.restore(); for (const f of late) f();
  }
  api.paint = paint; api.tick = tick;
  { const f0 = frame; frame = function (now) { try { tick(performance.now()); } catch (e) { clear(); } f0(now); }; }
  return api;
})();
