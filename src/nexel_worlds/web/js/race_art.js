// A race's frame from the cat's (races.js): what is in the frame, measured (analyse), and the head rebuilt with the
// race's own ears, eyes, muzzle or bill (remake). The colours and the races are race_list.js'.
//   RaceArt -> {analyse(d, row, col), remake(d, A, race)}

const RaceArt = (() => {
  const {rgb, BASE, DIRS, classes, EXTRA} = RaceList;
  function analyse(d, row, col) {
    // What is in the frame: the body, and on the swings a tool, its arc and sometimes a hand apart from the body. The
    // head is measured on the body alone (the piece that wears the collar). Measured on everything, a raised axe was
    // taken for the head: ears were put on it, the head came out as a slab, the tool above the head was wiped.
    const px = classes(d), raw = (x, y) => (x >= 0 && y >= 0 && x < CELL && y < CELL ? px[y * CELL + x] : null);   // (each px's class found once and kept: no string made and looked up at every look, hundreds of thousands a sheet)
    const body = new Uint8Array(CELL * CELL), stack = [];
    const own = (x, y) => { const c = raw(x, y); return c && c !== "?"; };
    for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++) if (raw(x, y) === "f") { body[y * CELL + x] = 1; stack.push([x, y]); }
    if (!stack.length) for (let y = 0; y < CELL && !stack.length; y++) for (let x = 0; x < CELL; x++) if (own(x, y)) { body[y * CELL + x] = 1; stack.push([x, y]); break; }
    while (stack.length) { const [x, y] = stack.pop();
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const u = x + dx, v = y + dy;
        if (u >= 0 && v >= 0 && u < CELL && v < CELL && !body[v * CELL + u] && own(u, v)) { body[v * CELL + u] = 1; stack.push([u, v]); } } }
    const at = (x, y) => x >= 0 && y >= 0 && x < CELL && y < CELL && body[y * CELL + x] ? raw(x, y) : null;
    let top = CELL, bottom = 0, k = null, sy = null;
    for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++) if (at(x, y)) { top = Math.min(top, y); bottom = Math.max(bottom, y); if (k === null && at(x, y) === "f") k = y; }
    if (k === null) k = top + 9;
    for (let y = top; y < k && sy === null; y++) {                 // the skull starts at the first row that is one unbroken run (the ears are two)
      let run = 0, best = 0, runs = 0;
      for (let x = 0; x < CELL; x++) { if (at(x, y)) { run++; best = Math.max(best, run); if (run === 1) runs++; } else run = 0; }
      if (runs === 1 && best >= 6) sy = y;
    }
    if (sy === null) sy = top + 1;
    let hmin = CELL, hmax = 0;
    for (let x = 0; x < CELL; x++) if (at(x, sy + 3)) { hmin = Math.min(hmin, x); hmax = Math.max(hmax, x); }
    const facing = DIRS[row % 4], side = facing === "left" || facing === "right";
    if (side) {                                    // side on, the cat's ear flops as it walks: measure the head lower down, where it
      // never changes (three rows and one row above the collar: the narrower of the two, so a hand resting against one
      // of them is not taken for the face), and find the top of the skull above the face, not above the ear.
      let mid = 0, nf = 0; for (let x = 0; x < CELL; x++) if (at(x, k) === "f") { mid += x; nf++; }
      mid = nf ? Math.round(mid / nf) : Math.round((hmin + hmax) / 2);
      let lo = -1, hi = CELL;
      for (const y of [k - 3, k - 1]) { if (!at(mid, y)) continue;
        let a = mid, b = mid; while (at(a - 1, y)) a--; while (at(b + 1, y)) b++; lo = Math.max(lo, a); hi = Math.min(hi, b); }
      if (lo >= 0) { hmin = lo; hmax = hi; }
      // A hand held out beside the face (the hoe's first frame) is the body's, but it is not the head: it is set apart
      // with the tool, so that rounding the head, taking the whiskers off and the rest leave it alone (it came out
      // flattened, and the muzzle or the bill was put on it). The head's box: its edges, the front one a pixel in above the snout.
      const front = facing === "right" ? 1 : -1;
      const out = (x, y) => y < k - 4 ? (front > 0 ? x < hmin || x > hmax - 1 : x < hmin + 1 || x > hmax) : x < hmin || x > hmax;
      const seen = new Uint8Array(CELL * CELL);
      for (let y = top; y < k + 2; y++) for (let x = 0; x < CELL; x++) {
        if (!body[y * CELL + x] || seen[y * CELL + x] || !out(x, y)) continue;
        const blob = [], st = [[x, y]]; seen[y * CELL + x] = 1;
        while (st.length) { const [u, v] = st.pop(); blob.push(v * CELL + u);
          for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const p = u + dx, q = v + dy;
            if (q >= 0 && q < k + 2 && p >= 0 && p < CELL && body[q * CELL + p] && !seen[q * CELL + p] && out(p, q)) { seen[q * CELL + p] = 1; st.push([p, q]); } } }
        if (blob.length >= 5) for (const i of blob) body[i] = 0;
      }
      const xf = facing === "right" ? hmax - 2 : hmin + 2;
      sy = top; while (sy < k && !at(xf, sy)) sy++;
    }
    return {top, bottom, k, sy, hmin, hmax, cx: Math.round((hmin + hmax + 1) / 2), facing, side, at, raw, body, walk: row >= 4 && row < 8, col};
  }
  function remake(d, A, race) {                    // d: the frame's pixels, rewritten in place
    const g = [], other = [];                      // the body as colour classes (null is empty); other: the tool, its arc, a hand apart
    for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++) { g.push(A.at(x, y)); other.push(A.at(x, y) ? null : A.raw(x, y)); }
    const get = (x, y) => x >= 0 && y >= 0 && x < CELL && y < CELL ? g[y * CELL + x] : null;
    const span = (y) => { let a = CELL, b = -1; for (let x = 0; x < CELL; x++) if (get(x, y)) { a = Math.min(a, x); b = x; } return [a, b]; };
    const H = {
      get,
      put(x, y, c, over) { if (x < 0 || y < 0 || x >= CELL || y >= CELL) return; if (!over || (get(x, y) && over.includes(get(x, y)))) g[y * CELL + x] = c; },
      round() {                                    // take the cat's ears off and close the top of the head in a curve
        for (let y = A.top; y < A.sy; y++) for (let x = 0; x < CELL; x++) g[y * CELL + x] = null;
        if (A.side) {                              // side on: the top three rows of the head are built new, a plain dome,
          for (let i = 0; i < 3; i++) {            // so nothing of the cat's ear (which moves) is left
            const y = A.sy + i, a = A.hmin + 2 - i, b = A.hmax - 2 + i;
            for (let x = A.hmin - 3; x <= A.hmax + 3; x++) g[y * CELL + x] = x < a || x > b ? null : x === a || x === b || i === 0 ? "a" : "b";
          }
          return;
        }
        const [a, b] = span(A.sy), inset = 2;
        for (let x = a; x <= b; x++) g[A.sy * CELL + x] = x < a + inset || x > b - inset ? null : "a";
        for (const [x, s] of [[a, 1], [b, -1]]) if (get(x, A.sy + 1)) { g[(A.sy + 1) * CELL + x] = null; g[(A.sy + 1) * CELL + x + s] = "a"; }
        for (let y = A.sy; y < A.k; y++) for (let x = 0; x < CELL; x++) if (get(x, y) === "c") g[y * CELL + x] = "b";
      },
      whiskers() { for (let y = A.sy + 2; y < A.k; y++) { const [a, b] = span(y), [ua, ub] = span(y - 1), [da, db] = span(y + 1);
        if (a < ua && a < da) g[y * CELL + a] = null; if (b > ub && b > db) g[y * CELL + b] = null; } },
      eyes() { for (let y = A.sy + 3; y < A.k - 1; y++) for (let x = 0; x < CELL; x++)           // outline pixels inside the face are the eyes
        if (get(x, y) === "a" && get(x - 1, y) && get(x + 1, y) && get(x, y - 1) && get(x, y + 1) && get(x - 1, y) !== "a" && get(x + 1, y) !== "a") g[y * CELL + x] = "b"; },
      plain() { for (let y = A.sy; y < A.k; y++) for (let x = 0; x < CELL; x++) if (get(x, y) === "d") g[y * CELL + x] = "b"; },    // no forehead patch
      feet() { for (let y = A.bottom - 1; y <= A.bottom; y++) for (let x = 0; x < CELL; x++) if ("bd".includes(get(x, y) || "?")) g[y * CELL + x] = "o"; },
      belly() { if (A.facing !== "up") for (let y = A.k + 2; y < A.bottom - 1; y++) for (let x = 0; x < CELL; x++) if (get(x, y) === "b") g[y * CELL + x] = "y"; },
    };
    race.head(H, A);
    // A tool held over the head is held by a hand, which on the cat is a few pixels above the skull, where its ears are:
    // rounding the head took the hand with the ears, and the tool hung in the air. What was body within two pixels of the
    // tool, above the skull, is put back.
    if (A.facing !== "down") for (let y = 0; y <= A.sy; y++) for (let x = 0; x < CELL; x++) {       // (facing us, the tool is in front of the body)
      const was = A.at(x, y); if (!was || g[y * CELL + x]) continue;
      let near = false;
      for (let dy = -2; dy <= 2 && !near; dy++) for (let dx = -2; dx <= 2; dx++) if (other[(y + dy) * CELL + x + dx] === "?") { near = true; break; }
      if (near) g[y * CELL + x] = was === "c" ? "b" : was;                // (the cat's pink ear lining is not a hand's colour)
    }
    for (let i = 0; i < g.length; i++) if (other[i]) g[i] = other[i];      // the tool, the arc and the hand go back on top, untouched
    for (let i = 0; i < g.length; i++) {
      const c = g[i], hex = c && (race.col[c] || EXTRA[c] || BASE[c]);
      if (!hex) { if (!c) d[i * 4 + 3] = 0; continue; }
      const v = rgb(hex); d[i * 4] = v[0]; d[i * 4 + 1] = v[1]; d[i * 4 + 2] = v[2]; d[i * 4 + 3] = 255;
    }
    return g;                                    // the frame as colour classes, for the clothes
  }
  return {analyse, remake};
})();
