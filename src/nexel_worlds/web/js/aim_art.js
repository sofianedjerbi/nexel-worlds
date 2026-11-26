// Where you aim, shown by your face and your paw ("which block am I selecting?"): standing with a target (the key's
// cell, the build cursor, the hovered cell), the body looks at it. Three poses, made once when the sheet loads (assets.js,
// after jump_art.js), so a person's colour, their race and their clothes have them too. ANIM.aim in sprites.js names the
// rows (a row per way it faces: down, up, right, left), a column per pose (AimArt.COL). All of them the standing frame
// (idle, first column) with whole rows or columns of it moved and a paw of the sheet's own colours: nothing scaled.
//   up     the body a row taller (stretching), the head tilted up: side on its front half a px higher, facing us the
//          eyes a px higher, from behind the head a px higher still; a paw raised before the face
//   ahead  the paw held out toward the target at the body's height (facing us: its pad before the chest)
//   down   the body a row lower (as the crouch), the head tilted down to the feet: side on its front half a px lower,
//          facing us the eyes a px lower, from behind the head sunk into the collar; a paw down before the feet
// The ears are the head's: they move with it.

const AimArt = (() => {
  const COL = {up: 0, ahead: 1, down: 2};
  const INK = {a: [92, 78, 146, 255], b: [243, 242, 192, 255], d: [221, 213, 222, 255], c: [232, 181, 172, 255]}, COLLAR = [118, 109, 170];
  const ix = (x, y) => (y * CELL + x) * 4, on = (d, x, y) => x >= 0 && y >= 0 && x < CELL && y < CELL && d[ix(x, y) + 3] > 0;
  const is = (d, x, y, c) => on(d, x, y) && d[ix(x, y)] === c[0] && d[ix(x, y) + 1] === c[1] && d[ix(x, y) + 2] === c[2];
  function measure(d) {
    let top = -1, bottom = -1, k = -1, x0 = CELL, x1 = -1;
    for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++) if (on(d, x, y)) { if (top < 0) top = y; bottom = y; x0 = Math.min(x0, x); x1 = Math.max(x1, x); if (k < 0 && is(d, x, y, COLLAR)) k = y; }
    return {top, bottom, k, x0, x1};
  }
  // n = 1: a row of the body drawn twice; -1: left out. The feet stay on their row
  function body(d, M, n) {
    const mid = M.k + 3, rows = [];
    for (let y = M.top; y <= M.bottom; y++) { const r = d.slice(y * CELL * 4, (y + 1) * CELL * 4); if (!(n < 0 && y === mid)) rows.push(r); if (n > 0 && y === mid) rows.push(r); }
    const out = new Uint8ClampedArray(CELL * CELL * 4), y0 = M.bottom + 1 - rows.length;
    rows.forEach((r, i) => { if (y0 + i >= 0) out.set(r, (y0 + i) * CELL * 4); });
    return out;
  }
  // the head's px (over the collar) in columns c0..c1 moved dy rows: up, its last row is kept under it; down, over the collar's top
  function head(d, M, dy, c0 = 0, c1 = CELL - 1) {
    const out = d.slice();
    for (let x = c0; x <= c1; x++) {
      for (let y = M.top - 1; y < M.k; y++) if (y >= 0 && (dy > 0 || y < M.k - 1)) out.set([0, 0, 0, 0], ix(x, y));
      for (let y = M.top; y < M.k; y++) { const t = y + dy; if (t >= 0 && on(d, x, y)) out.set(d.subarray(ix(x, y), ix(x, y) + 4), ix(x, t)); }
    }
    return out;
  }
  // facing us: the eyes (outline px inside the face, fill on both sides) a row up or down
  function eyes(d, M, dy) {
    const out = d.slice(), found = [];
    for (let y = M.top + 3; y < M.k - 1; y++) for (let x = 1; x < CELL - 1; x++) if (is(d, x, y, INK.a) && is(d, x - 1, y, INK.b) && is(d, x + 1, y, INK.b) && is(d, x, y + dy, INK.b)) found.push([x, y]);
    for (const [x, y] of found) { out.set(INK.b, ix(x, y)); out.set(INK.a, ix(x, y + dy)); }
    return out;
  }
  // a paw: rows of a (outline), b (fur), c (pad), "." left as it is, its top left at x, y
  function paw(d, rows, x, y) { rows.forEach((r, j) => [...r].forEach((ch, i) => { if (INK[ch] && x + i >= 0 && x + i < CELL && y + j >= 0 && y + j < CELL) d.set(INK[ch], ix(x + i, y + j)); })); return d; }
  // an arm: fur two px thick from the shoulder (ax, ay) to the paw (bx, by) (and on to (cx, cy): a bent arm), outlined all round, in front of the body
  function limb(d, ax, ay, bx, by, cx, cy) {
    const fur = new Set(), seg = (ax, ay, bx, by) => { const n = Math.max(Math.abs(bx - ax), Math.abs(by - ay)), tall = Math.abs(by - ay) > Math.abs(bx - ax);
      for (let t = 0; t <= n; t++) { const x = Math.round(ax + (bx - ax) * t / (n || 1)), y = Math.round(ay + (by - ay) * t / (n || 1)); fur.add(x + "," + y); fur.add(tall ? x + 1 + "," + y : x + "," + (y + 1)); } };
    seg(ax, ay, bx, by); if (cx !== undefined) seg(bx, by, cx, cy);
    const put = (x, y, c) => { if (x >= 0 && y >= 0 && x < CELL && y < CELL) d.set(c, ix(x, y)); };
    for (const k of fur) { const [x, y] = k.split(",").map(Number); for (const [u, v] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) if (!fur.has(x + u + "," + (y + v))) put(x + u, y + v, INK.a); }
    for (const k of fur) { const [x, y] = k.split(",").map(Number); put(x, y, INK.b); }
    return cx !== undefined ? [cx, cy] : [bx, by];
  }
  const edge = (d, y, s) => { if (s > 0) { for (let x = CELL - 1; x >= 0; x--) if (on(d, x, y)) return x; } else for (let x = 0; x < CELL; x++) if (on(d, x, y)) return x; return -1; };
  // side on, facing right (the left: the right's mirror). -> [frame, the paw's place]
  function side(d0, aim) {
    const M0 = measure(d0), d = body(d0, M0, aim === "up" ? 1 : aim === "down" ? -1 : 0), M = measure(d), mid = Math.round((M.x0 + M.x1) / 2), s = aim === "up" ? -1 : 1;
    // the head tilted: its front half a px; up, its front third a px more (a stair of whole px, not a cut; down, a beak pushed
    // two px onto the paw was a jumble)
    const o = aim === "ahead" ? d : ((h) => aim === "up" ? head(h, measure(h), s, mid + 3, CELL - 1) : h)(head(d, M, s, mid, CELL - 1)), F = edge(o, M.k + 2, 1), S = edge(o, M.k - 3, 1);
    // down: the arm held out as ahead, its paw bent down at the ground before you (it ran across the body to the feet: crumpled; a lower arm is a leg)
    const at = aim === "ahead" ? limb(o, F - 2, M.k + 1, F + 2, M.k + 1) : aim === "up" ? limb(o, F - 2, M.k + 1, S + 1, M.top + 3) : limb(o, F - 2, M.k + 1, F, M.k + 1, F, M.k + 2);
    return [o, at];
  }
  // facing us: the paw on the left of the picture (the paw a thing is held in, held.js)
  function facing(d0, aim) {
    const M0 = measure(d0), d = body(d0, M0, aim === "up" ? 1 : aim === "down" ? -1 : 0), M = measure(d), e = aim === "up" ? -1 : 1;
    const o = aim === "ahead" ? d : eyes(eyes(d, M, e), M, e), cx = Math.round((M.x0 + M.x1) / 2), L = edge(o, M.k + 3, -1);
    if (aim === "ahead") { paw(o, [".aaa.", "abbba", "abcba", ".aaa."], cx - 5, M.k + 2); return [o, [cx - 3, M.k + 3]]; }
    // down: the paw before the belly, its pad at its foot, pointing at the ground (an arm to the feet was a third leg)
    if (aim === "down") { paw(o, [".aa.", "abba", "abba", "acca", ".aa."], cx - 4, M.k); return [o, [cx - 2, M.k + 2]]; }
    return [o, limb(o, L + 1, M.k + 2, M.x0, M.k - 5)];
  }
  // from behind: the paw on the right of the picture
  function back(d0, aim) {
    const M0 = measure(d0), d = body(d0, M0, aim === "up" ? 1 : aim === "down" ? -1 : 0), M = measure(d);
    const o = aim === "ahead" ? d : head(d, M, aim === "up" ? -1 : 1), R = edge(o, M.k + 3, 1);
    return [o, aim === "ahead" ? limb(o, R - 2, M.k + 2, R + 1, M.k + 2) : aim === "up" ? limb(o, R - 2, M.k + 2, M.x1 - 1, M.k - 5) : [R - 3, M.k + 2]];   // (down: the paw before the body, unseen from behind: the bowed head says it)
  }
  const mirror = (d) => { const o = new Uint8ClampedArray(d.length); for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++) o.set(d.subarray(ix(x, y), ix(x, y) + 4), ix(CELL - 1 - x, y)); return o; };
  // one pose of a standing frame d (facing: 0 down, 1 up, 2 right, 3 left) -> the frame; its paw's place kept in PAW[aim][facing]
  const PAW = {up: [], ahead: [], down: []};
  function pose(d, aim, f) {
    if (measure(d).k < 0) return d.slice();
    if (f === 3) { const [o, at] = side(mirror(d), aim); PAW[aim][f] = [CELL - 1 - at[0], at[1]]; return mirror(o); }
    const [o, at] = f === 0 ? facing(d, aim) : f === 1 ? back(d, aim) : side(d, aim); PAW[aim][f] = at; return o;
  }
  // the sheet with the aim's four rows under it (the standing frame in the columns after the poses)
  function extend(img) {
    const W = img.width, H = img.height, c = document.createElement("canvas");
    c.width = W; c.height = H + 4 * CELL;
    const g = c.getContext("2d"); g.drawImage(img, 0, 0);
    const rd = document.createElement("canvas"); rd.width = CELL; rd.height = 4 * CELL;
    const rg = rd.getContext("2d", {willReadFrequently: true}); rg.drawImage(img, 0, 0, CELL, 4 * CELL, 0, 0, CELL, 4 * CELL);
    const src = rg.getImageData(0, 0, CELL, 4 * CELL).data, names = Object.keys(COL);
    for (let r = 0; r < 4; r++) {
      const d = src.slice(r * CELL * CELL * 4, (r + 1) * CELL * CELL * 4);
      for (let col = 0; col < W / CELL; col++) g.putImageData(new ImageData(col < names.length ? pose(d, names[col], r) : d.slice(), CELL, CELL), col * CELL, H + r * CELL);
    }
    c.complete = true; c.src = img.src;
    return c;
  }
  return {extend, pose, COL, PAW};
})();
