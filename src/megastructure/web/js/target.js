// What a key will act on, shown as the CELL it is ("block selection / placing looks confusing: i dont know which level
// am i interacting with. eye-level ? feet level ? air ? real block ?"). The marks were flat: brackets round a tile,
// a flat cursor, dashes at one place of the screen: the ground before you, a wall's top, the cell at your head and
// an empty cell in the air looked the same. One language now, out of build mode and in it (the HD look's marks pass,
// hd.js; the classic picture keeps its own):
//   - a cell is a BOX in the land, in the land's own projection, whole art px: its twelve edges; the ones the eye
//     sees are whole lines, the ones behind its own faces, in the ground or behind land are one px in two;
//   - Space puts a block there ("place"): cream; the block itself in it at 60 % (buildghost.js), and WHAT HOLDS IT
//     is lit: the ring of its foot on the block under it, or the side it leans on; red where it cannot go;
//   - a key takes that block ("break": X, a pickaxe's Space, R): orange, and every face of the REAL block that
//     shows is hatched: a block of the land is hatched, air never is;
//   - Space does something to that block ("use": till it, lay a floor in it, a thing put on it): cream, its edges;
//   - a cell nothing stands under: a dotted line down to the ground under it and its shadow there, one px in two;
// `cells()` is the one answer to "which cell": what is drawn is what the key sends (tests: the drawn cell is the
// cell that changes). X's block under you: its own mark, round your feet (`feet`). `target(key)`: the cell of Space ("use"), X ("alt") or R ("up").
const Target = (() => {
  const INK = "#5b3f36", CREAM = "#fff8e8", TAKE = "#ff9d3c", RED = "#e8554a";
  const api = {drew: [], opts: {}};
  // -> [{key: "use" | "alt" | "up", kind: "place" | "break" | "use", x, y, z: the level of its top, h: levels tall, ok, item}]
  function cells() {
    const s = typeof me !== "undefined" && me && meObs ? myPos() : null, out = [];
    if (!s) return out;
    const add = (key, kind, x, y, z, more) => { if (!out.some((c) => c.x === x && c.y === y && c.z === z && c.kind === "break")) out.push({key, kind, x, y, z, h: 1, ok: true, ...more}); };
    if (Build.on) {
      const p = Build.S.at, it = Build.hint(p), hit = Build.taking(p), L = Build.level();
      if (hit && !hit.plan && !hit.shut) add("alt", "break", p.x, p.y, hit.dig || hit.up ? hit.z : hit.z + 2, hit.dig || hit.up ? {} : {h: 2, thing: true});
      if (it.ghost && it.z !== undefined && !it.steps && it.ghost !== "ladder") add("use", solidAt(p.x, p.y, it.z) ? "use" : "place", p.x, p.y, it.z, {ok: it.ok !== false, item: LAND_BLOCKS.has(it.ghost) ? it.ghost : null, drawn: LAND_BLOCKS.has(it.ghost)});
      else add("use", solidAt(p.x, p.y, L) ? "use" : "place", p.x, p.y, L, {ok: it.ok !== false, flat: !!it.ghost && solidAt(p.x, p.y, L)});
      return out;
    }
    // (the keys act whether the way out is shown or not: what each would take is drawn; the way's own block is drawn by wayshow.js: one mark. keyboard.js `useFacing`, digup.js `route`)
    const keys = byKeys(), h = myZ(s.x, s.y), way = keys ? WayShow.offer() : null, wc = WayShow.cur, nx = wc && wc.next, now = wc && wc.now;
    const ways = (x, y, z) => !!nx && nx.x === x && nx.y === y && nx.z === z;
    const a = keys ? facingIntent(false) : aimedTile(), it = a && a.it, p = a && a.p, alt = keys ? facingIntent(true) : null, up = keys ? DigUp.aim() : null;
    if ((way && way.key === "alt") || (alt && alt.it.here)) add("alt", "break", s.x, s.y, h, {mine: true});      // X: the block you stand on (its own mark: under you)
    if (up) add("up", "break", up.x, up.y, up.z, {way: ways(up.x, up.y, up.z)});                                   // R: the block it cuts
    if (way && way.key === "use" && now) add("use", "break", now.x, now.y, now.z, {way: ways(now.x, now.y, now.z)});
    else if (it && p && tile(p.x, p.y) && !it.info && !it.walk) {
      const wetFill = !!it.ghostGround && wet(gndAt(p.x, p.y) || "");
      if (it.cell !== undefined) add("use", "break", p.x, p.y, it.cell);                                // a pickaxe into a wall: the cell at your body
      else if (wetFill) add("use", "use", p.x, p.y, topAt(p.x, p.y), {ok: it.ok !== false, flat: true});   // (earth into water: the tile's water gets shallower, its bed seldom shows it: the water's face, not a block standing on it)
      else if (LAND_BLOCKS.has(it.ghost)) add("use", "place", p.x, p.y, it.z !== undefined ? it.z : topAt(p.x, p.y) + 1, {ok: it.ok !== false, item: it.ghost});
      else if (!api.opts.thing && !it.ent && !it.steps) add("use", "use", p.x, p.y, it.z !== undefined ? it.z : api.opts.shown ? api.opts.shown(p.x, p.y) : settleNear(p.x, p.y, h), {ok: it.ok !== false, flat: true});
    }
    return out;
  }
  api.cells = cells;
  api.target = (key = "use") => { const c = cells().find((q) => q.key === key); return c ? {x: c.x, y: c.y, z: c.z, kind: c.kind, ok: c.ok} : null; };

  // ---- the painter: P = {g, u: an art px, at(x, y, z) -> px, behind(x, y, z), ex: the eye's x}
  const R = (P, v) => Math.round(v / P.u) * P.u;
  // a line between two places of the land, a px of paint at a time; hid: one px in two, fainter (behind a face, in the ground, behind land)
  function line(P, a, b, col, hid, c) {
    const A = P.at(...a), B = P.at(...b); if (!A || !B) return;
    const g = P.g, u = P.u, n = Math.max(1, Math.round(Math.max(Math.abs(B[0] - A[0]), Math.abs(B[1] - A[1])) / u)), ph = Math.round((A[0] + A[1]) / u), e = .02;
    const at = (k) => !!(c && P.behind && P.behind(Math.max(c.x + e, Math.min(c.x + 1 - e, a[0] + (b[0] - a[0]) * k)), Math.max(c.y + e, Math.min(c.y + 1 - e, a[1] + (b[1] - a[1]) * k)), a[2] + (b[2] - a[2]) * k));
    const hs = hid ? null : [0, .25, .5, .75, 1].map(at), on = [], off = [];   // (behind land: looked at five times a line, not at every px: the marks pass was .5 ms a frame on a phone)
    for (let i = 0; i <= n; i++) { const k = i / n, h = hid || hs[Math.round(k * 4)]; if (h && (i + ph) % 2) continue; (h ? off : on).push(R(P, A[0] + (B[0] - A[0]) * k), R(P, A[1] + (B[1] - A[1]) * k)); }
    const put = (l, dy, cl, al) => { if (!l.length) return; g.globalAlpha = al; g.fillStyle = cl; for (let i = 0; i < l.length; i += 2) g.fillRect(l[i], l[i + 1] + dy, u, u); };
    put(on, u, INK, .7); put(on, 0, col, 1); put(off, 0, col, .6);
    g.globalAlpha = 1;
  }
  // a face between places of the land (three or four, in order), filled row by row; pat(i, j): which of its px
  function face(P, pts, col, a, pat) {
    const q = pts.map((p) => P.at(...p)); if (q.some((v) => !v)) return;
    const g = P.g, u = P.u, y0 = R(P, Math.min(...q.map((v) => v[1]))), y1 = R(P, Math.max(...q.map((v) => v[1]))), x0 = R(P, q[0][0]);
    g.globalAlpha = a; g.fillStyle = col;
    for (let Y = y0; Y < y1; Y += u) {
      const yc = Y + u / 2; let l = 1e9, r = -1e9;
      for (let i = 0; i < q.length; i++) { const A = q[i], B = q[(i + 1) % q.length]; if ((A[1] <= yc) === (B[1] <= yc)) continue; const xi = A[0] + (B[0] - A[0]) * (yc - A[1]) / (B[1] - A[1]); l = Math.min(l, xi); r = Math.max(r, xi); }
      l = R(P, l); r = R(P, r); if (!(r > l)) continue;
      if (!pat) g.fillRect(l, Y, r - l, u); else for (let X = l; X < r; X += u) if (pat(Math.round((X - x0) / u), Math.round((Y - y0) / u))) g.fillRect(X, Y, u, u);
    }
    g.globalAlpha = 1;
  }
  const HATCH = (i, j) => (((i + j) % 4) + 4) % 4 === 0, CHECK = (i, j) => ((i + j) & 1) === 0;
  // the six faces of a cell: its corners, and the cell beyond it
  const FACES = {T: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1], 0, 0, 1], B: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], 0, 0, -1], S: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0], 0, 1, 0],
    N: [[0, 0, 1], [1, 0, 1], [1, 0, 0], [0, 0, 0], 0, -1, 0], W: [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0], -1, 0, 0], E: [[1, 0, 1], [1, 1, 1], [1, 1, 0], [1, 0, 0], 1, 0, 0]};
  // its twelve edges: from, to, the two faces it is between
  const EDGES = [[[0, 0, 1], [1, 0, 1], "TN"], [[1, 0, 1], [1, 1, 1], "TE"], [[0, 1, 1], [1, 1, 1], "TS"], [[0, 0, 1], [0, 1, 1], "TW"], [[0, 0, 1], [0, 0, 0], "NW"], [[1, 0, 1], [1, 0, 0], "NE"],
    [[0, 1, 1], [0, 1, 0], "SW"], [[1, 1, 1], [1, 1, 0], "SE"], [[0, 0, 0], [1, 0, 0], "BN"], [[1, 0, 0], [1, 1, 0], "BE"], [[0, 1, 0], [1, 1, 0], "BS"], [[0, 0, 0], [0, 1, 0], "BW"]];
  // One cell, as the box it is. -> what was drawn of it (tests)
  function box(P, c) {
    const {x, y, z} = c, h = c.h || 1, z0 = z - h, at = ([i, j, k]) => [x + i, y + j, z0 + k * h], col = c.ok === false ? RED : c.kind === "break" ? TAKE : CREAM;
    const full = (dx, dy, dz) => { for (let k = dz > 0 ? z + 1 : dz < 0 ? z0 : z0 + 1; k <= (dz > 0 ? z + 1 : dz < 0 ? z0 : z); k++) if (!solidAt(x + dx, y + dy, k)) return false; return true; };
    // the faces the eye sees: its top, its south front, the side turned to the middle of the picture; and not what a block beside it covers
    const seen = {}; for (const f of "TBSNWE") { const F = FACES[f]; seen[f] = (f === "T" || f === "S" || (f === "W" && x > P.ex) || (f === "E" && x + 1 < P.ex)) && !full(F[4], F[5], F[6]); }
    const near = x > P.ex ? "W" : x + 1 < P.ex ? "E" : "S", held = c.kind === "place" && c.ok !== false ? (full(0, 0, -1) ? "B" : "WENS".split("").find((f) => full(FACES[f][4], FACES[f][5], 0)) || (full(0, 0, 1) ? "T" : "")) : "";
    if (c.flat) { for (const [a, b, fs] of EDGES) if (fs[0] === "T") line(P, at(a), at(b), col, !seen.T, c); face(P, FACES.T.slice(0, 4).map(at), col, .22); return {x, y, z, kind: c.kind, held: "", seen}; }
    if (held && held !== "B" && held !== "T") face(P, FACES[held].slice(0, 4).map(at), CREAM, .75, CHECK);          // the side it leans on
    if (c.kind === "break" && !c.thing && !c.mine) for (const f of "TSWE") if (seen[f] || f === near) { face(P, FACES[f].slice(0, 4).map(at), INK, .28); face(P, FACES[f].slice(0, 4).map(at), TAKE, .9, HATCH); }
    if (c.kind !== "break") { const bh = P.behind && P.behind(x + .5, y + .5, z) ? CHECK : null; face(P, FACES.T.slice(0, 4).map(at), CREAM, c.drawn ? .25 : .4, bh); if (seen.S) face(P, FACES.S.slice(0, 4).map(at), INK, .18, bh); }   // (behind land: one px in two, as the ghost)
    if (held === "B") face(P, FACES.B.slice(0, 4).map(at), CREAM, .5, CHECK);   // (what holds it: the top under it)
    for (const [a, b, fs] of EDGES) if (!c.mine || !fs.includes("T") || fs === "TS") line(P, at(a), at(b), col, !(seen[fs[0]] || seen[fs[1]] || (held && held !== "T" && fs.includes(held))), c.kind === "break" && fs.includes(near) ? null : c);
    // nothing under it: a dotted line from its foot down to the ground there, and its foot's place on that ground
    if (!full(0, 0, -1)) { const g0 = settleAt(x, y, z0); if (g0 < z0) { line(P, [x + .5, y + .5, z0], [x + .5, y + .5, g0], col, true, c); face(P, [[0, 0], [1, 0], [1, 1], [0, 1]].map(([i, j]) => [x + i, y + j, g0]), INK, .5, CHECK); } }   // (its foot's place: a shadow of the cell, one px in two)
    return {x, y, z, kind: c.kind, held, seen};
  }
  // X's block, under your feet: its top hatched round you at your floor (nothing on your body), and a stepped arrow down beside it
  const DOWN = ["..###..", "..#o#..", "..#o#..", "###o###", "#ooooo#", ".#ooo#.", "..#o#..", "...#..."];
  function feet(P, c) {
    const g = P.g, u = P.u, T = [[0, .45], [1, .45], [1, 1], [0, 1]].map(([i, j]) => [c.x + i, c.y + j, c.z]), pe = ents.get("agent" + myId), ft = pe && P.at(pe.x + .5, pe.y + .5, c.z), west = !!pe && pe.fx > 0, E = P.at(c.x + (west ? 0 : 1), c.y + .7, c.z);   // (the floor round your feet, its front half: the whole top was a box round your body; the arrow on the side you do not face: there is what Space takes)
    g.save(); if (ft) { g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); g.rect(R(P, ft[0]) - 7 * u, R(P, ft[1]) - 22 * u, 14 * u, 25 * u); g.clip("evenodd"); }
    face(P, T, TAKE, .9, HATCH); for (let i = 0; i < 4; i++) line(P, T[i], T[(i + 1) % 4], TAKE, false, null);
    g.restore();
    if (E) DOWN.forEach((row, j) => [...row].forEach((ch, i) => { if (ch !== ".") { g.fillStyle = ch === "#" ? INK : TAKE; g.fillRect(R(P, E[0]) + (west ? i - 9 : i + 2) * u, R(P, E[1]) + (j - 5) * u, u, u); } }));
  }
  // a rect (the canvas's units) lies on a box drawn, or on the way's block (your own name is not written there: characters.js)
  api.over = (x, y, w, h) => [...api.drew.map((d) => d.r), typeof WayShow !== "undefined" && WayShow.block].some((r) => r && x < r.x + r.w && r.x < x + w && y < r.y + r.h && r.y < y + h);
  // once a frame, in the marks pass: g, what a painter of marks needs (HdLook.art()), opts: {thing: what is aimed at stands (its own brackets), shown(x, y): a tile's level as the picture has it}
  api.paint = (g, art, opts = {}) => {
    api.opts = opts; api.drew = [];
    if (!art || api.off) return;   // (off: tests that count a ghost's own px)
    const s = myPos(), open = HdLook.win && HdLook.win.n && HdLook.win.a > 0, P = {g, u: art.u, at: art.at, behind: open ? null : art.behind, ex: s ? s.x + .5 : 0};
    for (const c of cells().sort((a, b) => a.y - b.y || (a.kind === "break") - (b.kind === "break") || a.z - b.z)) {
      const Q = P, px = P.at(c.x, c.y, c.z);
      if (c.kind === "place" && c.item && !c.drawn) BuildGhost.block(g, Q.at, Q.u, c.x, c.y, c.z, c.item, .6, c.ok === false, Q.behind);
      if (c.mine) { feet(P, c); api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, mine: true, px, u: P.u}); continue; }
      if (c.way) { api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, way: true, px, u: P.u}); continue; }   // (wayshow.js draws that block)
      const d = {...box(Q, c), key: c.key, px, u: P.u}, q = [0, 1].flatMap((i) => [0, 1].flatMap((j) => [0, 1].map((k) => P.at(c.x + i, c.y + j, c.z - k)))).filter((v) => v);
      if (q.length) { const xs = q.map((v) => v[0]), ys = q.map((v) => v[1]); d.r = {x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)}; }
      api.drew.push(d);
    }
  };
  return api;
})();
