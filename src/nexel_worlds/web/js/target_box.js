// THE BOX OF A CELL, drawn (target.js says which cells, and when): the art px the land paints the block with, its outline in
// the key's colour, its faces faintly tinted, dotted when out of reach, a dotted line down to the ground under it. Its
// colours are the marks' language (target.js, its first lines).
//   TargetBox.box(P, c, K) -> what is drawn of it; boxRect(Q, c) -> its box on the screen; feet(P, c): X's mark round your feet (unused)
// the painter's lines and faces in whole art px (TargetBox): P = {g, u: an art px, at(x, y, z) -> px, behind(x, y, z)}
const TargetBoxDraw = (() => {
  const INK = "#5b3f36";
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
  return {R, line, face, INK};
})();

// a cell's own px on the screen (TargetBox.box): pxOf(P, c, full[, inside])
const TargetBoxPx = (() => {
  const CW = {T: 1, S: 1, W: 1, B: -1, N: -1, E: -1};   // (CW: a face's corners below go clockwise on the screen when its outside faces the eye)
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
  return pxOf;
})();

const TargetBox = (() => {
  const CREAM = "#fff8e8", TAKE = "#ff9d3c", RED = "#e8554a";
  const {R, line, face, INK} = TargetBoxDraw, pxOf = TargetBoxPx;   // (the painter's lines and faces, a cell's px: above in this file)
  const CHECK = (i, j) => ((i + j) & 1) === 0;
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
  return {box, boxRect, feet};
})();
