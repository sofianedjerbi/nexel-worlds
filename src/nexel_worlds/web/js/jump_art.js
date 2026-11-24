// The jump's own poses ("improve the jumping animation"). The sheet has no jump: it was a row of the body drawn a row
// lower for the crouch and the run's stride in the air. Each pose is now a frame of its own, made once when the sheet
// loads (assets.js, after tool_art.js), so everything built from the sheet afterwards (a person's colour, their race,
// their clothes) has it too. ANIM.jump in sprites.js names the rows: a row per way it faces, a column per pose.
// A pose is the standing frame (idle, first column) with whole rows of it left out or drawn twice: nothing scaled.
//   crouch   a row of the body left out: the head and collar a row lower (the anticipation)
//   takeoff  a row of the body drawn twice: a px taller, the feet still on the ground as it pushes off (the stretch)
//   rise     the legs tucked up into the body: their row closed with the outline, the feet left out
//   apex     tucked, the ears a px higher: they lag behind the head as it slows and turns over
//   fall     the legs a row longer, reaching for the ground, the ears still up
//   land     two rows of the body left out, facing or back on the feet set apart (the squash)
//   settle   a row left out, as the crouch: on its way back up to standing
// Rows of the cat's frame (the standing one): ears over the skull at top..top+1, the collar from k (its colour, f), the
// body k+2..bottom-2, the feet the last two rows.

const JumpArt = (() => {
  const CELL = 48, POSES = ["crouch", "takeoff", "rise", "apex", "fall", "land", "settle"];
  const LINE = [92, 78, 146], COLLAR = [118, 109, 170];
  const same = (d, i, c) => d[i + 3] && d[i] === c[0] && d[i + 1] === c[1] && d[i + 2] === c[2];

  // -> the frame's rows (each CELL * 4 bytes), and where its parts are
  function measure(d) {
    const rows = [];
    let top = -1, bottom = -1, k = -1, cx = 0, nc = 0;
    for (let y = 0; y < CELL; y++) {
      rows.push(d.slice(y * CELL * 4, (y + 1) * CELL * 4));
      for (let x = 0; x < CELL; x++) {
        const i = (y * CELL + x) * 4;
        if (!d[i + 3]) continue;
        if (top < 0) top = y;
        bottom = y;
        if (same(d, i, COLLAR)) { if (k < 0) k = y; if (y === k) { cx += x; nc++; } }
      }
    }
    return {rows, top, bottom, k, cx: nc ? cx / nc : CELL / 2};
  }
  // The ear row: the row under the ears' tips again, with the skull's top line taken out of it (what is left of an
  // outline run is its ends against the ears' fill), so the ears come out a px taller and the skull stays where it is
  function earRow(row) {
    const out = row.slice(), line = (x) => x >= 0 && x < CELL && same(row, x * 4, LINE), solid = (x) => x >= 0 && x < CELL && row[x * 4 + 3];
    for (let x = 0; x < CELL; x++) {
      if (!line(x)) continue;
      let b = x; while (line(b + 1)) b++;
      if (b - x >= 2) for (let u = x; u <= b; u++) if (!((solid(u - 1) && !line(u - 1)) || (solid(u + 1) && !line(u + 1)))) out[u * 4 + 3] = 0;
      x = b;
    }
    return out;
  }
  // Feet set apart (facing or back on): each foot a px out to its side, the gap under the body closed with the outline
  function splay(row, cx, close) {
    const out = new Uint8ClampedArray(CELL * 4);
    for (let x = 0; x < CELL; x++) { if (!row[x * 4 + 3]) continue; const to = x < cx ? x - 1 : x + 1; if (to >= 0 && to < CELL) out.set(row.subarray(x * 4, x * 4 + 4), to * 4); }
    if (close) { let a = CELL, b = -1; for (let x = 0; x < CELL; x++) if (out[x * 4 + 3]) { a = Math.min(a, x); b = x; }
      for (let x = a; x <= b; x++) if (!out[x * 4 + 3]) out.set([...LINE, 255], x * 4); }
    return out;
  }
  // The legs drawn up into the body: the row of the legs all outline, the feet under it left out (a round bottom)
  function closed(row) {
    const out = row.slice();
    for (let x = 0; x < CELL; x++) if (out[x * 4 + 3]) out.set([...LINE, 255], x * 4);
    return out;
  }
  // One pose of a standing frame d (its facing: 0 down, 1 up, 2 right, 3 left) -> a new frame, its feet on the same row
  function pose(d, name, facing, moved) {
    const M = measure(d), {rows, top, bottom, k} = M;
    if (top < 0 || k < 0) return d.slice();
    const mid = k + 3, low = bottom - 2, feet = bottom - 1, side = facing >= 2;
    const tuck = name === "rise" || name === "apex";
    const drop = {crouch: [mid], rise: [bottom], apex: [bottom], land: [mid, low], settle: [mid]}[name] || [];
    const twice = {takeoff: [mid], fall: [feet]}[name] || [];
    const ears = name === "apex" || name === "fall";
    let list = [], from = [];                 // (from: the standing frame's row each row is)
    for (let y = top; y <= bottom; y++) {
      if (drop.includes(y)) continue;
      if (ears && y === top + 1) { list.push(earRow(rows[y])); from.push(-1); }
      list.push(tuck && y === feet ? closed(rows[y]) : rows[y]); from.push(y);
      if (twice.includes(y)) { list.push(rows[y]); from.push(-1); }
    }
    if (name === "land" && !side) { const n = list.length; list[n - 2] = splay(list[n - 2], M.cx, true); list[n - 1] = splay(list[n - 1], M.cx, false); }
    const out = new Uint8ClampedArray(CELL * CELL * 4), y0 = bottom + 1 - list.length;
    list.forEach((r, i) => { if (y0 + i >= 0) out.set(r, (y0 + i) * CELL * 4); });
    if (moved) { const m = new Int8Array(CELL); for (let y = 0; y < CELL; y++) { let i = from.indexOf(y), b = y; while (i < 0 && b > top) i = from.indexOf(--b); m[y] = i < 0 ? 0 : y0 + i - b; } moved.push(m); }
    return out;
  }
  // How many rows a row of the standing frame is moved by in each pose (SHIFT[facing][column][row]): what is held in the
  // paw goes with the paw (held.js; it went by the frame's top, measured from the crouch: a px off in every pose, two in the fall)
  const SHIFT = [];
  const shift = (facing, col, y) => { const f = SHIFT[facing], m = f && f[col]; return m ? m[Math.max(0, Math.min(CELL - 1, y))] : 0; };
  // The sheet with the jump's four rows under it (the standing frame in the last column: every frame is a body)
  function extend(img) {
    const W = img.width, H = img.height, c = document.createElement("canvas");
    c.width = W; c.height = H + 4 * CELL;
    const g = c.getContext("2d"); g.drawImage(img, 0, 0);
    const rd = document.createElement("canvas"); rd.width = CELL; rd.height = 4 * CELL;
    const rg = rd.getContext("2d", {willReadFrequently: true}); rg.drawImage(img, 0, 0, CELL, 4 * CELL, 0, 0, CELL, 4 * CELL);   // (the idle rows' first column)
    const src = rg.getImageData(0, 0, CELL, 4 * CELL).data;
    const first = !SHIFT.length;              // (the cat's own sheet, the first made: every race's rows are its rows)
    for (let r = 0; r < 4; r++) {
      const d = src.slice(r * CELL * CELL * 4, (r + 1) * CELL * CELL * 4), moved = first ? [] : null;
      for (let col = 0; col < W / CELL; col++) g.putImageData(new ImageData(col < POSES.length ? pose(d, POSES[col], r, moved) : d.slice(), CELL, CELL), col * CELL, H + r * CELL);
      if (first) SHIFT.push(moved);
    }
    c.complete = true; c.src = img.src;
    return c;
  }
  return {extend, POSES, pose, shift};
})();
