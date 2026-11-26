// What a key will act on, shown as the CELL it is ("block selection / placing looks confusing: i dont know which level
// am i interacting with. eye-level ? feet level ? air ? real block ?"). The marks were flat: brackets round a tile,
// a flat cursor, dashes at one place of the screen: the ground before you, a wall's top, the cell at your head and
// an empty cell in the air looked the same. One language now, out of build mode and in it (the HD look's marks pass,
// hd.js; the classic picture keeps its own):
//   - a cell is the BLOCK it is on the screen: the art px the land paints it with (its faces turned to the eye, by the
//     land's own rule, `pxOf`); a 1 px line in the key's colour on its outermost px and on its top/front seam, ink
//     inside that line, its faces its own paint faintly tinted (`outline`): nothing of it outside the block;
//   - Space puts a block there ("place"): cream; the block itself in it at 60 % (buildghost.js); red where it cannot go;
//   - orange: a key takes that block ("break": X, R or a pickaxe's Space), the block itself, not air.
//   - Space does something to that block ("use": till it, lay a floor in it, a thing put on it): cream, its top;
//   - DOTTED means one thing: out of reach yet (build mode: a block in the ground with no air beside it nor a dig planned
//     beside it; a block to place that nothing holds yet, built or planned beside or under it); reachable is a whole line. Behind land a box is not drawn, unless all of it is: then its whole line, seen through;
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
    if (api.show) return api.show.map((c) => ({key: "use", h: 1, ok: true, ...c}));   // (tests: these cells drawn, not the keys')
    const add = (key, kind, x, y, z, more) => { if (!out.some((c) => c.x === x && c.y === y && c.z === z && c.kind === "break")) out.push({key, kind, x, y, z, h: 1, ok: true, ...more}); };
    if (Build.on) {
      const p = Build.S.at, it = Build.hint(p), hit = Build.taking(p), L = Build.level();
      if (hit && !hit.plan) add("alt", "break", p.x, p.y, hit.dig || hit.up ? hit.z : hit.z + 1, hit.shut ? {far: true} : hit.dig || hit.up ? {} : {h: 1, thing: true});   // (a thing that stands: a block high, hd_things.js. far: out of reach yet, no air beside it nor a dig planned beside it (build.js `open`, the rule the work goes by): its box dotted)
      const q = it.at || p, far = it.far ? {far: true, ok: true} : {ok: it.ok !== false};      // (q: the cell beside the face the mouse is on, build.js; far: nothing holds it yet: dotted, no ghost in it)
      if (it.ghost && it.z !== undefined && !it.steps && it.ghost !== "ladder") add("use", solidAt(q.x, q.y, it.z) ? "use" : "place", q.x, q.y, it.z, {item: LAND_BLOCKS.has(it.ghost) && !it.far ? it.ghost : null, drawn: LAND_BLOCKS.has(it.ghost), ...far});
      else add("use", solidAt(p.x, p.y, L) ? "use" : "place", p.x, p.y, L, {flat: !!it.ghost && solidAt(p.x, p.y, L), ...far});
      return out;
    }
    // (the keys act whether the way out is shown or not: what each would take is drawn; the way's own block is drawn by wayshow.js: one mark. keyboard.js `useFacing`, digup.js `route`)
    const keys = byKeys(), h = myZ(s.x, s.y), way = keys ? WayShow.offer() : null, wc = WayShow.cur, nx = wc && wc.next, now = wc && wc.now;
    const ways = (x, y, z) => !!nx && nx.x === x && nx.y === y && nx.z === z;
    const at = !keys && mouse.in ? tileAtScreen(mouse.x, mouse.y) : null;      // (the mouse: E's box on what a right click uses, X's on what a left click breaks)
    const a = keys ? facedOnly(facingIntent(false)) : at && clickIntent(at, "use"), it = a && a.it, p = a && a.p, up = keys ? DigUp.aim() : null;
    const x0 = keys ? facingIntent(true) : at && clickIntent(at, "break"), alt = x0 && !x0.it.info && !x0.it.walk && x0.it.ok !== false && !x0.it.gather ? x0 : null;
    if (way && way.key === "alt" && now && now.down) add("alt", "break", s.x, s.y, h, {mine: true});      // the way out's X: the block you stand on
    if (up) add("up", "break", up.x, up.y, up.z, {way: ways(up.x, up.y, up.z)});                                   // R: the block it cuts
    if (way && way.key === "alt" && now && !now.down) add("alt", "break", now.x, now.y, now.z, {way: ways(now.x, now.y, now.z)});      // the way out's X: the wall in front
    if (it && p && tile(p.x, p.y) && !it.info && !it.walk) {
      const wetFill = !!it.ghostGround && wet(gndAt(p.x, p.y) || "");
      if (wetFill) add("use", "use", p.x, p.y, topAt(p.x, p.y) - WaterBed.would(p.x, p.y, it.ghostGround), {ok: it.ok !== false, flat: true});   // (earth into water: the tile's water gets shallower: the mark lies where its bed will be, seen through the water; the face when no bed is seen)
      else if (LAND_BLOCKS.has(it.ghost)) add("use", "place", p.x, p.y, it.z !== undefined ? it.z : topAt(p.x, p.y) + 1, {ok: it.ok !== false, item: it.ghost});
      else if (!api.opts.thing && !it.ent && !it.steps) add("use", "use", p.x, p.y, it.z !== undefined ? it.z : api.opts.shown ? api.opts.shown(p.x, p.y) : settleNear(p.x, p.y, h), {ok: it.ok !== false, flat: true});
    }
    if (!(way && way.key === "alt") && alt && alt.it.cell !== undefined) add("alt", "break", alt.p.x, alt.p.y, alt.it.cell);   // X: the block you face, its box (keyboard.js digAhead)
    else if (!(way && way.key === "alt") && alt && !alt.it.ent && !alt.it.self) {      // X: the thing it takes apart (a rock, a tree, a chest, a wall), the block it stands in; a path: its own block
      const z = alt.it.z !== undefined ? alt.it.z : alt.it.at !== undefined ? alt.it.at : floorAt(alt.p.x, alt.p.y);
      add("alt", "break", alt.p.x, alt.p.y, alt.it.ground ? z : z + 1, alt.it.ground ? {} : {thing: true});
    }
    return out;
  }
  api.cells = cells;
  api.target = (key = "use") => { const c = cells().find((q) => q.key === key); return c ? {x: c.x, y: c.y, z: c.z, kind: c.kind, ok: c.ok} : null; };

  // ---- the painter: P = {g, u: an art px, at(x, y, z) -> px, behind(x, y, z), ex: the eye's x}
  const R = (P, v) => onArt(v);   // (on the land's pixel: state.js)
  // a line between two places of the land, a px of paint at a time; hid: one px in two, fainter (behind a face, in the ground, behind land)
  function line(P, a, b, col, hid, c) {
    const A = P.at(...a), B = P.at(...b); if (!A || !B) return;
    const g = P.g, u = P.u, n = Math.max(1, Math.round(Math.max(Math.abs(B[0] - A[0]), Math.abs(B[1] - A[1])) / u)), ph = Math.round((A[0] + A[1]) / u), e = .02;
    const at = (k) => !!(c && P.behind && P.behind(Math.max(c.x + e, Math.min(c.x + 1 - e, a[0] + (b[0] - a[0]) * k)), Math.max(c.y + e, Math.min(c.y + 1 - e, a[1] + (b[1] - a[1]) * k)), a[2] + (b[2] - a[2]) * k));
    const hs = hid ? null : [0, .25, .5, .75, 1].map(at), on = [], off = [];   // (behind land: looked at five times a line, not at every px: the marks pass was .5 ms a frame on a phone)
    for (let i = 0; i <= n; i++) { const k = i / n, h = hid || (!!hs && hs[Math.round(k * 4)]); if (h && (i + ph) % 2) continue; (h ? off : on).push(R(P, A[0] + (B[0] - A[0]) * k), R(P, A[1] + (B[1] - A[1]) * k)); }
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
  const CHECK = (i, j) => ((i + j) & 1) === 0, CW = {T: 1, S: 1, W: 1, B: -1, N: -1, E: -1};   // (CW: a face's corners below go clockwise on the screen when its outside faces the eye)
  // the six faces of a cell: its corners, and the cell beyond it
  const FACES = {T: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1], 0, 0, 1], B: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], 0, 0, -1], S: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0], 0, 1, 0],
    N: [[0, 0, 1], [1, 0, 1], [1, 0, 0], [0, 0, 0], 0, -1, 0], W: [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0], -1, 0, 0], E: [[1, 0, 1], [1, 1, 1], [1, 1, 0], [1, 0, 0], 1, 0, 0]};
  // The cell's own px: every art px whose middle is in a face of it the eye sees (turned to it on the screen, and no block beside it covers it):
  // the land's own rule (GL fills a px by its middle), so its edge px are the block's edge px. -> {i0, j0, n, m, f: 0 not it, 1 its top, 2 another face; hid: behind land; seen}
  function pxOf(P, c, full, inside) {
    const {x, y, z} = c, flat = !!c.flat, h = flat ? 0 : c.h || 1, z0 = z - h, u = P.u, fs = [], seen = {}, S = P.behind && !inside ? 4 : 1;
    for (const f of flat ? "T" : "TSNWEB") {
      const F = FACES[f], w = F.slice(0, 4).map(([i, j, k]) => [x + i, y + j, z0 + k * h]), q = w.map((p) => P.at(...p)); let A = 0;
      if (q.some((v) => !v)) continue;
      for (let i = 0; i < 4; i++) A += q[i][0] * q[(i + 1) % 4][1] - q[(i + 1) % 4][0] * q[i][1];
      if (!flat && (A * CW[f] < u * u * .1 || (!inside && full(F[4], F[5], F[6])))) continue;
      seen[f] = !inside; fs.push([f === "T" ? 1 : 2, w]);
    }
    if (!fs.length && !flat && !inside) return pxOf(P, c, full, true);   // (a cell inside the land, every face of it against a block: the faces turned to the eye, all as behind land)
    const all = fs.flatMap(([, w]) => w.map((p) => P.at(...p))); if (!all.length) return null;
    const i0 = Math.floor(Math.min(...all.map((v) => v[0])) / u) - 1, j0 = Math.floor(Math.min(...all.map((v) => v[1])) / u) - 1, n = Math.ceil(Math.max(...all.map((v) => v[0])) / u) - i0 + 2, m = Math.ceil(Math.max(...all.map((v) => v[1])) / u) - j0 + 2;
    const out = {i0, j0, n, m, f: new Uint8Array(n * m), hid: new Uint8Array(n * m), seen};
    const fill = (q, v, hd) => { const ys = q.map((p) => p[1]), y1 = Math.max(...ys);
      for (let j = Math.ceil(Math.min(...ys) / u - .5); (j + .5) * u < y1; j++) { const yc = (j + .5) * u; let l = 1e9, r = -1e9;
        for (let k = 0; k < q.length; k++) { const A = q[k], B = q[(k + 1) % q.length]; if ((A[1] <= yc) === (B[1] <= yc)) continue; const xi = A[0] + (B[0] - A[0]) * (yc - A[1]) / (B[1] - A[1]); l = Math.min(l, xi); r = Math.max(r, xi); }
        for (let i = Math.ceil(l / u - .5); (i + .5) * u < r; i++) { const o = (j - j0) * n + i - i0; if (o >= 0 && o < n * m) { out.f[o] = v; out.hid[o] = hd; } } } };
    // (behind land: looked at on a 4 x 4 grid of each face, its middles: what of it is behind the land in front is that land's)
    // (the grid's corners put through the camera once each, (S + 1)^2 of them: not four a square, each a few small arrays, every frame the eye moves)
    const on = (w, s, t, k) => { const l1 = w[0][k] + (w[1][k] - w[0][k]) * s, l2 = w[3][k] + (w[2][k] - w[3][k]) * s; return l1 + (l2 - l1) * t; };
    for (const [v, w] of fs) { const G = [];
      for (let t = 0; t <= S; t++) for (let s = 0; s <= S; s++) G.push(P.at(on(w, s / S, t / S, 0), on(w, s / S, t / S, 1), on(w, s / S, t / S, 2)));
      for (let a = 0; a < S; a++) for (let b = 0; b < S; b++) {
        const sq = [G[b * (S + 1) + a], G[b * (S + 1) + a + 1], G[(b + 1) * (S + 1) + a + 1], G[(b + 1) * (S + 1) + a]]; if (!sq[0] || !sq[1] || !sq[2] || !sq[3]) continue;
        fill(sq, v, inside || (P.behind && P.behind(on(w, (a + .5) / S, (b + .5) / S, 0), on(w, (a + .5) / S, (b + .5) / S, 1), on(w, (a + .5) / S, (b + .5) / S, 2))) ? 1 : 0);
      } }
    // (what it shows of itself is edge-on, or a sliver: the block in front of your legs, east of you in a tunnel, had no box at all; in a 1-wide
    // shaft seen from above the cell east of your feet showed its south face, 3 px tall: a flat orange bar beside you. Under a quarter of the
    // block it is: the whole block, seen through, as one inside the land)
    if (!inside && !flat) { let n = 0; for (let o = 0; o < out.f.length; o++) if (out.f[o] && !out.hid[o]) n++;
      if (!n) return pxOf(P, c, full, true);
      if (n < 64) { const W = pxOf(P, c, full, true); let m = 0; if (W) for (let o = 0; o < W.f.length; o++) if (W.f[o]) m++; if (n * 4 < m) return W; } }
    return out;
  }
  // its outline (the owner: "can you improve the selection hint?": the hatch over an ink wash hid the block, and a row of ink lay under it, on the grass):
  // the px of its silhouette (a px of it beside one that is not) and the seam (the top's last row over its front or side) in colour, a line of ink
  // inside them, its faces its own paint with the colour faintly over them. Behind land: not drawn there; all of it behind land: all of it, seen through.
  // far (out of reach yet): its silhouette one px in two, nothing inside: the one meaning of a dotted box (the owner: "dotted only for unreachable blocks")
  function outline(P, M, col, tint, far) {
    const g = P.g, u = P.u; let L = M.ol;   // (its px lists, kept on M (kept itself while nothing it is made from changes, `kept`): not worked out again each frame)
    if (!L || L.far !== far || L.u !== u) { const {i0, j0, n, m, f} = M, F = (i, j) => (i < 0 || j < 0 || i >= n || j >= m ? 0 : f[j * n + i]), line = [], ink = [], face = [], dots = [];
      const hid = M.hid.every((v, o) => v || !f[o]) ? new Uint8Array(n * m) : M.hid;   // (all of it behind land: seen through, whole)
      const edge = (i, j) => { const v = F(i, j); return !!v && (!F(i - 1, j) || !F(i + 1, j) || !F(i, j - 1) || !F(i, j + 1) || (v === 1 && F(i, j + 1) === 2)); };
      for (let j = 0; j < m; j++) for (let i = 0; i < n; i++) { const o = j * n + i; if (!f[o]) continue; const X = (i0 + i) * u, Y = (j0 + j) * u, h = hid[o];
        if (far) { if (edge(i, j) && !((i0 + i + j0 + j) & 1)) dots.push(X, Y); continue; }
        if (edge(i, j)) { if (!h) line.push(X, Y); }
        else if (!h) (edge(i - 1, j) || edge(i + 1, j) || edge(i, j - 1) || edge(i, j + 1) ? ink : face).push(X, Y);
      }
      L = M.ol = {far, u, line, ink, face, dots}; }
    const {line, ink, face, dots} = L, put = (l, cl, al) => { g.globalAlpha = al; g.fillStyle = cl; for (let k = 0; k < l.length; k += 2) g.fillRect(l[k], l[k + 1], u, u); };
    put(face, col, tint); put(ink, col, tint); put(ink, INK, .45); put(line, col, 1); put(dots, col, 1); g.globalAlpha = 1;
    return {line: line.length / 2, dots: dots.length / 2};
  }
  // One cell, as the box it is. -> what is drawn of it (tests)
  function box(P, c, K) {
    const {x, y, z} = c, h = c.h || 1, z0 = z - h, col = c.ok === false && !c.far ? RED : c.kind === "break" ? TAKE : CREAM;   // (far: can't, not wrong: cream dotted)
    const full = (dx, dy, dz) => { for (let k = dz > 0 ? z + 1 : dz < 0 ? z0 : z0 + 1; k <= (dz > 0 ? z + 1 : dz < 0 ? z0 : z); k++) if (!solidAt(x + dx, y + dy, k)) return false; return true; };
    const M = K ? (K.M === undefined ? (K.M = pxOf(P, c, full)) : K.M) : pxOf(P, c, full); if (!M) return {x, y, z, kind: c.kind, held: "", seen: {}};   // (K: what is kept of this cell, `kept`)
    const o = outline(P, M, col, c.over ? .3 : c.ok === false ? .16 : c.kind === "break" ? .14 : c.flat ? .18 : .08, !!c.far);   // (over: drawn over your own sprite, which shows through it)
    // nothing under it: a dotted line from its foot down to the ground there, and its foot's place on that ground
    // (over you: you are what is under it; its shadow lay checkered on your body)
    if (!c.flat && !c.over && !full(0, 0, -1)) { const g0 = settleAt(x, y, z0); if (g0 < z0) { line(P, [x + .5, y + .5, z0], [x + .5, y + .5, g0], col, true, c); face(P, [[0, 0], [1, 0], [1, 1], [0, 1]].map(([i, j]) => [x + i, y + j, g0]), INK, .5, CHECK); } }   // (its foot's place: a shadow of the cell, one px in two)
    if (M.area === undefined) M.area = M.f.reduce((a, v) => a + (v ? 1 : 0), 0);   // (its px on the screen, tests)
    return {x, y, z, kind: c.kind, held: "", seen: M.seen, line: o.line, dots: o.dots, far: !!c.far, area: M.area};
  }
  // X's block, under your feet: NOT drawn (the owner, 2026-11-21: "remove that weird ugly arrow under my character, that is always active"); the corner's "Dig down X" says it. feet() is kept unused for now
  const DOWN = ["..###..", "..#o#..", "..#o#..", "###o###", "#ooooo#", ".#ooo#.", "..#o#..", "...#..."];
  function feet(P, c) {
    const g = P.g, u = P.u, T = [[0, .45], [1, .45], [1, 1], [0, 1]].map(([i, j]) => [c.x + i, c.y + j, c.z]), pe = ents.get("agent" + myId), ft = pe && P.at(pe.x + .5, pe.y + .5, c.z), west = !!pe && pe.fx > 0, E = P.at(c.x + (west ? 0 : 1), c.y + .7, c.z);   // (the floor round your feet, its front half: the whole top was a box round your body; the arrow on the side you do not face: there is what Space takes)
    g.save(); if (ft) { g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); g.rect(R(P, ft[0]) - 7 * u, R(P, ft[1]) - 22 * u, 14 * u, 25 * u); g.clip("evenodd"); }
    face(P, T, TAKE, .9, CHECK); for (let i = 0; i < 4; i++) line(P, T[i], T[(i + 1) % 4], TAKE, false, null);
    g.restore();
    if (E) DOWN.forEach((row, j) => [...row].forEach((ch, i) => { if (ch !== ".") { g.fillStyle = ch === "#" ? INK : TAKE; g.fillRect(R(P, E[0]) + (west ? i - 9 : i + 2) * u, R(P, E[1]) + (j - 5) * u, u, u); } }));
  }
  // a cell's box on the screen (its eight corners'), or null
  const boxRect = (Q, c) => { const q = [0, 1].flatMap((i) => [0, 1].flatMap((j) => [0, 1].map((k) => Q.at(c.x + i, c.y + j, c.z - k)))).filter((v) => v), xs = q.map((v) => v[0]), ys = q.map((v) => v[1]);
    return q.length ? {x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)} : null; };
  // WHAT IS KEPT OF A CELL's box from frame to frame (its px, its outline's px, its place and box on the screen), while nothing it is made from changes: where the land is drawn (view: HdLook.art, the
  // camera's numbers), the land and what is built (landVer, Floors.ver), behind-land on or off, the cell itself. Worked out again each frame, it would make 5 MB in 3 s standing still for the collector
  const keep = new Map();
  function kept(view, behind, c) {
    const k = view + "|" + landVer + "|" + Floors.ver + "|" + (behind ? 1 : 0) + "|" + c.kind + "|" + c.x + "," + c.y + "," + c.z + "," + (c.h || 1) + (c.flat ? "f" : "") + (c.ok === false ? "n" : "") + (c.far ? "d" : "");
    let K = keep.get(k); if (!K) { if (keep.size > 24) keep.clear(); keep.set(k, K = {}); } return K;
  }
  // a rect (the canvas's units) lies on a box drawn, or on the way's block (your own name is not written there: characters.js)
  api.over = (x, y, w, h) => [...api.drew.map((d) => d.r), typeof WayShow !== "undefined" && WayShow.block].some((r) => r && x < r.x + r.w && r.x < x + w && y < r.y + r.h && r.y < y + h);
  // once a frame, in the marks pass: g, what a painter of marks needs (HdLook.art()), opts: {thing: what is aimed at stands (its own brackets), shown(x, y): a tile's level as the picture has it}
  // THE SELECTED CELL (the one the key in focus acts on: build mode the cursor's, else E's when it puts a block, else X's, else E's): its box always whole
  // ("which level am I interacting with?": a box at your body's cell or over your head was cut out of your sprite, or not drawn). At your body or over it:
  // drawn over you, your sprite seen through it (top()); under you: a box under your feet, your sprite in front of it whole. And your body aims at it (aim_art.js)
  // (an empty paw: E's only, what it would use: X's ground before you is always there, and you looked down at the grass wherever you stood)
  const pick = (cs) => (Build.on ? cs.find((c) => c.z === Build.level()) || cs.find((c) => c.key === "use") || cs.find((c) => c.key === "alt")
    : cs.find((c) => c.key === "use" && c.kind === "place") || (typeof selected !== "undefined" && selected ? cs.find((c) => c.key === "alt") : null) || cs.find((c) => c.key === "use")) || null;
  // -> "up" | "ahead" | "down" | null: the selected cell against your body's cell (one over your floor)
  function aimOf(c) { const s = c && myPos(); if (!s) return null; const lv = c.z - (myZ(s.x, s.y) + 1); return lv > 0 ? "up" : lv < 0 ? "down" : "ahead"; }
  api.aim = null; api.sel = null; api.late = null;
  api.top = (g) => { const L = api.late; api.late = null; if (!L) return; api.drew.push({...box(L.Q, L.c, L.K), key: L.c.key, px: L.px, u: L.Q.u, r: L.r, over: true}); };
  api.paint = (g, art, opts = {}) => {
    api.opts = opts; api.drew = []; api.late = null; api.sel = null; api.aim = null;
    if (!art || api.off) return;   // (off: tests that count a ghost's own px)
    const s = myPos(), open = HdLook.win && HdLook.win.n && HdLook.win.a > 0, P = {g, u: art.u, at: art.at, behind: open ? null : art.behind, ex: s ? s.x + .5 : 0}, B = art.body;
    // (your sprite's box: nothing of a box is drawn in it, and out of build mode a box that shares much of it (40 % of the smaller of the two) is not drawn at all: the cell north of you, under your head from above, was a square round your head)
    const inB = (r) => (B && r ? Math.max(0, Math.min(r.x + r.w, B.x + B.w) - Math.max(r.x, B.x)) * Math.max(0, Math.min(r.y + r.h, B.y + B.h) - Math.max(r.y, B.y)) / Math.max(1e-6, Math.min(r.w * r.h, B.w * B.h)) : 0);
    const all = cells(), sel = pick(all), me0 = myPos(), own = !!sel && !!me0 && sel.x === me0.x && sel.y === me0.y, after = [];
    api.sel = sel; api.aim = aimOf(sel);
    g.save(); if (B) { g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); g.rect(B.x, B.y, B.w, B.h); g.clip("evenodd"); }
    for (const c of all.sort((a, b) => a.y - b.y || (a.kind === "break") - (b.kind === "break") || a.z - b.z)) {
      const W = art.wall && art.wall(c.x, c.y, c.z), Q = W ? {...P, at: W, behind: null} : P, K = W || !art.view ? null : kept(art.view, !!P.behind, c), px = K ? K.px || (K.px = Q.at(c.x, c.y, c.z)) : Q.at(c.x, c.y, c.z);   // (a cell in the wall between the eye and you: drawn as its face folded into the opening, seen: hd_level.js wallAt)
      const r = K ? (K.r === undefined ? (K.r = boxRect(Q, c)) : K.r) : boxRect(Q, c);
      if (c.mine) { api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, mine: true, px, u: P.u}); continue; }
      if (c.way) { api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, way: true, px, u: P.u}); continue; }   // (wayshow.js draws that block)
      // (a block to put where you stand, your body's cell or your head's: it cannot go, you are in it. Not an error: cream dotted, "can't" (not red, the
      // first thing seen in a shaft); red is for a place that is wrong)
      if (c === sel && !c.mine && !c.way) { const you = own && c.kind === "place" && c.ok === false && c.z - myZ(me0.x, me0.y) <= 2 ? {far: true, item: null} : {};
        if (own && api.aim !== "down") api.late = {Q, c: {...c, over: true, ...you}, K, r, px}; else after.push([Q, c, K, r, px]); continue; }   // (yours: no cut, no skip)
      if (!Build.on && inB(r) > .4) { api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, under: true, px, u: P.u}); continue; }
      if (c.kind === "place" && c.item && !c.drawn) BuildGhost.block(g, Q.at, Q.u, c.x, c.y, c.z, c.item, .6, c.ok === false, Q.behind);
      api.drew.push({...box(Q, c, K), key: c.key, px, u: P.u, r});
    }
    g.restore();
    for (const [Q, c, K, r, px] of after) { if (c.kind === "place" && c.item && !c.drawn) BuildGhost.block(g, Q.at, Q.u, c.x, c.y, c.z, c.item, .6, c.ok === false, Q.behind); api.drew.push({...box(Q, c, K), key: c.key, px, u: P.u, r, sel: true}); }
  };
  return api;
})();
