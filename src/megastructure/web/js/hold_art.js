// A tool in the paw, gripped (the owner: "it should look like the player is really holding it, like the sword"). It was
// its 8 px icon pasted at the paw. Here it is drawn from its grip: the hand (the sheet's swing hand, a ring of outline
// round its fur) over the handle, the tool out of it at the angle the pose gives, in whole art px (redrawn at each
// angle as the swings draw their tools, never scaled or blurred). A sword and a spear are the attack's own
// (swing_art.js frame), so the cut starts from where they are held.
//   rest   (standing, walking, in a jump) the head up: beside you facing us, up and forward side on, over the shoulder
//          from behind (where it is drawn behind the body: held.js). The grip is where the tool's swing starts
//          (frame 0 of its row of the sheet), so a swing does not jump: the hand stays and the tool turns
//   up / ahead / down   (an aim, aim_art.js) the grip in the pose's paw, the tool raised, held out, lowered
// A torch keeps its flame up; a watering can hangs from its handle. One picture per tool, facing, pose and hand colours,
// made the first time it is drawn: a 48 x 48 cell laid over the body's.

const HoldArt = (() => {
  const CELL = 48, SS = 4, KINDS = ["axe", "pickaxe", "hoe", "sword", "spear", "torch", "watering_can"];
  // degrees on the screen, facing [down, up, right] (left: right's mirror); the paw is on the left of the picture facing us
  const ANG = {rest: [-120, -75, -60], up: [-100, -80, -80], ahead: [110, -90, -10], down: [100, 80, 45]};
  const UPRIGHT = {rest: [-100, -80, -75], up: [-95, -85, -80], ahead: [-110, -90, -50], down: [-115, -75, -65]};   // (a torch)
  // the paw's grip when the tool has no swing of the sheet's (a sword's, a spear's, a torch's): at the side of the belly
  const PAW = [[18, 28], [30, 28], [27, 27]];
  const ROW = {axe: "axe", pickaxe: "pickaxe", hoe: "hoe", watering_can: "water"};
  const CLAMP = 1, rad = (a) => a * Math.PI / 180, R = (row) => row === 3 ? 2 : row;

  // where the swing of `kind` starts (frame 0 of its rows of the cat's sheet): the end of the handle nearest the body,
  // in the picture facing right for the left (its mirror). Read once.
  let starts = null;
  function swingStarts() {
    if (starts) return starts;
    const S = typeof IMG !== "undefined" && IMG.character; if (!S || !S.complete) return {};
    starts = {};
    const g = document.createElement("canvas").getContext("2d", {willReadFrequently: true}); g.canvas.width = CELL; g.canvas.height = CELL;
    const read = (row) => { g.clearRect(0, 0, CELL, CELL); g.drawImage(S, 0, row * CELL, CELL, CELL, 0, 0, CELL, CELL); return g.getImageData(0, 0, CELL, CELL).data; };
    const body = new Set();
    for (let r = 0; r < 8; r++) { const d = read(r); for (let i = 0; i < d.length; i += 4) if (d[i + 3]) body.add(d[i] + "," + d[i + 1] + "," + d[i + 2]); }
    const flip = (r, x) => r === 3 ? CELL - 1 - x : x;
    for (const [kind, anim] of Object.entries(ROW)) starts[kind] = [0, 1, 2, 3].map((r) => {
      const d = read(ANIM[anim] + r), d0 = kind === "watering_can" && read(r), px = []; let near = null, nd = 1e9;
      for (let i = 0; i < CELL * CELL; i++) { if (!d[i * 4 + 3]) continue; const x = i % CELL, y = Math.floor(i / CELL), own = !body.has(d[i * 4] + "," + d[i * 4 + 1] + "," + d[i * 4 + 2]);
        if (own) { const dd = (x - 23.5) ** 2 + (y - 26) ** 2; if (dd < nd) { nd = dd; near = [x, y]; } }
        if (own) px.push(i); }
      // the can and the hand on it: from its own colours on through what is not on the body where it stands (8 ways round)
      const seen = new Set(px);
      for (let n = 0; d0 && n < px.length; n++) { const x = px[n] % CELL, y = Math.floor(px[n] / CELL);
        for (let v = -1; v <= 1; v++) for (let u = -1; u <= 1; u++) { const j = (y + v) * CELL + x + u; if (x + u < 0 || x + u >= CELL || y + v < 0 || y + v >= CELL || seen.has(j) || !d[j * 4 + 3] || d0[j * 4 + 3]) continue; seen.add(j); px.push(j); } }
      return near && {at: [flip(r, near[0]), near[1]], px: d0 ? px.map((i) => [flip(r, i % CELL), Math.floor(i / CELL), d[i * 4], d[i * 4 + 1], d[i * 4 + 2]]) : []};
    });
    return starts;
  }
  // the rest pose of `kind` facing `row`: [grip x, grip y (the middle of its px), angle] in the picture facing right for the left
  function rest(kind, row) {
    // (the swing's start, up to 2 px nearer the body: the hand held out at arm's length looked thrown, not held)
    const s = swingStarts()[kind], p = PAW[R(row)], at = s && s[row] ? s[row].at.map((v, i) => v + Math.max(-CLAMP, Math.min(CLAMP, p[i] - v))) : p;
    return [at[0] + .5, at[1] + .5, rad((kind === "torch" ? UPRIGHT : ANG).rest[R(row)])];
  }
  function place(kind, row, pose, paw) {
    if (pose === "rest" || !paw) return rest(kind, row);
    const x = row === 3 ? CELL - 1 - paw[0] : paw[0];
    return [x + .5, paw[1] + .5, rad((kind === "torch" ? UPRIGHT : ANG)[pose][R(row)])];
  }

  // The tools drawn as the swings draw theirs (tool_art.js, swing_art.js: the same colours, sizes and way of drawing):
  // solid shapes along the tool's axis, u from the hand out, v across (+v: the way the blade faces), each px the colour
  // that covers most of it. (Their 16 px icons read two px to one were a few px of mush: a torch was one px of flame.)
  const C = {wood: [170, 121, 89], dark: [144, 98, 93], iron: [129, 129, 129], steel: [183, 183, 183], flame: [233, 110, 60], glow: [250, 215, 90]};
  const box = (u0, u1, v0, v1) => [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
  const SHAPES = {
    axe: [[[[5.6, -1.3], [9.3, -1.3], [10, 3.2], [5.6, 1.8]], C.iron], [[[8.3, -1.3], [9.3, -1.3], [10, 3.2], [8.9, 3.2]], C.steel], [box(-2.5, 9.5, -.6, .6), C.wood], [box(-2.5, -1.5, -.6, .6), C.dark]],
    pickaxe: [[box(7.2, 9.4, -1.3, 1.3), C.iron], [[[7.4, -1.3], [9.2, -1.3], [8.2, -3.6], [6.6, -3.4]], C.iron], [[[7.4, 1.3], [9.2, 1.3], [8.2, 3.6], [6.6, 3.4]], C.iron],
      [[[6.4, -3.2], [8.2, -3.6], [6.6, -5.2]], C.steel], [[[6.4, 3.2], [8.2, 3.6], [6.6, 5.2]], C.steel], [box(-2.5, 7.4, -.6, .6), C.wood]],
    hoe: [[box(8, 10, .4, 3.4), C.iron], [box(8, 10, 2.4, 3.4), C.steel], [box(-2.5, 10, -.6, .6), C.wood], [box(-2.5, -1.5, -.6, .6), C.dark]],
    torch: [[[[4.6, -1.1], [6.4, -1.1], [8.2, 0], [6.4, 1.1], [4.6, 1.1]], C.flame], [box(4.6, 6.2, -.6, .6), C.glow], [box(-2.5, 4.6, -.7, .7), C.wood], [box(3.4, 4.6, -.8, .8), C.dark]],
  };
  const inside = (pts, x, y) => {                          // (a convex shape, its corners in order)
    let sign = 0;
    for (let i = 0; i < pts.length; i++) { const [ax, ay] = pts[i], [bx, by] = pts[(i + 1) % pts.length], c = (bx - ax) * (y - ay) - (by - ay) * (x - ax);
      if (c) { if (sign && Math.sign(c) !== sign) return false; sign = Math.sign(c); } }
    return true;
  };
  // the tool from the grip (gx, gy) at angle a into d (48 x 48, the picture facing right for the left); pointing left it
  // is mirrored across its axis (an axe's blade out, not in)
  function paint(d, name, gx, gy, a) {
    const shapes = SHAPES[name], ux = Math.cos(a), uy = Math.sin(a), m = ux < -1e-6 ? -1 : 1;
    for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++) {
      if (Math.abs(x + .5 - gx) > 13 || Math.abs(y + .5 - gy) > 13) continue;
      const votes = new Map(); let n = 0;
      for (let sy = 0; sy < SS; sy++) for (let sx = 0; sx < SS; sx++) {
        const px = x + (sx + .5) / SS - gx, py = y + (sy + .5) / SS - gy, lu = px * ux + py * uy, lv = (-px * uy + py * ux) * m;
        const hit = shapes.find(([pts]) => inside(pts, lu, lv)); if (!hit) continue;
        votes.set(hit[1], (votes.get(hit[1]) || 0) + 1); n++;
      }
      if (n < SS * SS * .45) continue;
      let best = null; for (const [k, v] of votes) if (!best || v > votes.get(best)) best = k;
      d.set([best[0], best[1], best[2], 255], (y * CELL + x) * 4);
    }
  }
  // the hand over the grip, as the sheet's swings draw a hand: 2 x 2 of fur in a ring of outline, the corners off
  function hand(d, gx, gy, h) {
    const hx = Math.round(gx - 2), hy = Math.round(gy - 2);
    for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) {
      const rim = x % 3 === 0 || y % 3 === 0; if (rim && x % 3 === 0 && y % 3 === 0) continue;
      const c = rim ? h[0] : x === 1 ? h[1] : h[2], X = hx + x, Y = hy + y; if (X < 0 || Y < 0 || X >= CELL || Y >= CELL) continue;
      d.set([c[0], c[1], c[2], 255], (Y * CELL + X) * 4);
    }
  }
  const mirror = (d) => { const o = new Uint8ClampedArray(d.length); for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++) o.set(d.subarray((y * CELL + x) * 4, (y * CELL + x) * 4 + 4), (y * CELL + CELL - 1 - x) * 4); return o; };

  // one tool held: 48 x 48 RGBA, the way it is faced (row: 0 down, 1 up, 2 right, 3 left)
  function frame(kind, row, pose, paw, h) {
    const [gx, gy, a] = place(kind, row, pose, paw);
    if (SwingArt.KINDS.includes(kind)) return SwingArt.frame(kind, row, 0, h, [gx, gy, a]);
    const d = new Uint8ClampedArray(CELL * CELL * 4);
    if (kind === "watering_can") {                         // the sheet's own can as its watering starts, the hand on its handle
      const S = swingStarts().watering_can, w = S && S[row]; if (!w) return d;
      const ox = Math.round(gx - .5) - w.at[0], oy = Math.round(gy - .5) - w.at[1], CAT = ["92,78,146", "221,213,222", "243,242,192"];
      for (const [x, y, r, g, b] of w.px) { const X = x + ox, Y = y + oy, k = CAT.indexOf(r + "," + g + "," + b), c = k < 0 ? [r, g, b] : h[k];
        if (X >= 0 && Y >= 0 && X < CELL && Y < CELL) d.set([c[0], c[1], c[2], 255], (Y * CELL + X) * 4); }
      return row === 3 ? mirror(d) : d;
    } else paint(d, kind, gx, gy, a);
    hand(d, gx, gy, h);
    return row === 3 ? mirror(d) : d;
  }
  const made = new Map();
  // the picture of `kind` held by someone drawn from `sheet` (`paw`: an aim pose's paw), or null when it is not a tool
  function art(kind, row, pose, sheet, paw) {
    if (!KINDS.includes(kind)) return null;
    const h = SwingArt.handOf(sheet), key = [kind, row, pose, paw, h].join();
    if (!made.has(key)) {
      const c = document.createElement("canvas"); c.width = c.height = CELL;
      try { c.getContext("2d").putImageData(new ImageData(frame(kind, row, pose, paw, h), CELL, CELL), 0, 0); } catch (e) { return null; }
      made.set(key, c);
    }
    return made.get(key);
  }
  return {KINDS, art, frame, rest, place, swingStarts};
})();
