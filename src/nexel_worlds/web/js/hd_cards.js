// The HD look's furniture and what stands (hd_things.js): a CARD, its own sprite px for px with its top leaning, the oval of
// shade under what stands and its sun shadow, the shadow of what moves, a rug flat on the ground.
//   HdCards(S, LEAN) (S: HdSheet) -> {CARD, PLAIN, card, foot, shade, shadow, decal}
const HdCards = (S, LEAN) => {
  const {room, pix, solid, cut, push, span, flat} = S;
  // ---- furniture: a card (see the top). CARD: char -> [r0, rS, r2]: its top's first row, its front's first row, the row under its foot. PLAIN: char -> the row under its foot where that is not its last row (a coop's ramp runs on past its legs)
  const CARD = {B: [10, 28, 32], C: [3, 8, 14], L: [1, 12, 15], "&": [2, 7, 13], e: [1, 8, 15], y: [1, 7, 15], q: [1, 7, 14]}, PLAIN = {J: 42}, cards = new Map();
  // -> {canvas, fx, fy, y, lean, b}: its picture where it is on the screen (X: art px right of the middle), the px of it that is its foot's middle, how far south in its tile its foot is (tiles), its bounds in it
  function card(c, x, y, spr, X = 0) {
    const S = CARD[c]; if (!S || !spr || !spr[0] || !spr[0].width) return null;
    const [img, sx, sy, sw, sh, dx, dy] = spr, P = pix(img, sx, sy, sw, sh), [r0, rS, r2] = S, n = rS - r0, k = Math.max(-8, Math.min(8, Math.round(X * LEAN * n))), key = P.key + "|" + k;
    let cd = cards.get(key); if (cd) return cd;
    const a = Math.abs(k), off = k > 0 ? a : 0, W2 = sw + a, cv2 = document.createElement("canvas"); cv2.width = W2; cv2.height = sh;
    const g = cv2.getContext("2d"), im = g.createImageData(W2, sh), o = new Uint32Array(im.data.buffer), [c0, c1] = span(P, rS, r2), lean = (j) => (j >= rS ? 0 : -Math.sign(k) * Math.round(a * (rS - j) / n));      // (right of the middle: its far rows towards the left, and its west side shows)
    for (let t = 1; t <= a; t++) { const jt = rS - Math.round(t / a * n), X0 = (k > 0 ? c0 - t : c1 - 1 + t) + off;      // (the side: a column a px, each as high as the front, in the front's edge colour row by row)
      for (let i = 0; i < r2 - rS; i++) { let v = 0, m = 0; for (let q = k > 0 ? c0 : c1 - 1; q >= c0 && q < c1 && m < 2; q += k > 0 ? 1 : -1) if (solid(P.px[(rS + i) * sw + q])) { v = P.px[(rS + i) * sw + q]; m++; } if (v && jt + i >= 0) o[(jt + i) * W2 + X0] = v; } }
    for (let j = 0; j < sh; j++) for (let i = 0; i < sw; i++) { const v = P.px[j * sw + i]; if (solid(v)) o[j * W2 + i + off + lean(j)] = v; }
    const b = [W2, sh, 0, 0]; for (let j = 0; j < sh; j++) for (let i = 0; i < W2; i++) if (o[j * W2 + i]) { b[0] = Math.min(b[0], i); b[1] = Math.min(b[1], j); b[2] = Math.max(b[2], i + 1); b[3] = Math.max(b[3], j + 1); }
    g.putImageData(im, 0, 0); cd = {canvas: cv2, fx: 8 - dx + off, fy: r2, y: (dy + r2) / 16, lean: k, b, still: true, d: true}; cards.set(key, cd); return cd;
  }
  // the shadow under a thing that stands: an oval of shade on the ground round its foot (the engine lays it over the land: `shade`)
  const oval = (w, d) => room("o" + [w, d], w, d, (put) => { for (let j = 0; j < d; j++) for (let i = 0; i < w; i++) { const u = (i + .5) / w * 2 - 1, v = (j + .5) / d * 2 - 1; if (u * u + v * v <= 1) put(i, j, 0xff000000); } });
  // the row of a thing's sprite that is under its foot (its last row with a px): where it stands on the ground, and where its shadow lies
  function foot(c, spr) { if (CARD[c]) return CARD[c][2]; if (PLAIN[c] !== undefined) return PLAIN[c]; const P = pix(spr[0], spr[1], spr[2], spr[3], spr[4]), has = (j) => { for (let i = 0; i < P.w; i++) if (solid(P.px[j * P.w + i])) return true; return false; }; let r = P.h; while (r > 1 && !has(r - 1)) r--; return r; }
  function shade(out, c, x, y, base, L) {      // (L: it stands on the ground at that level: the hour's shadow too, hd_sun.js)
    const spr = objectSprite(c, x, y, 0); if (!spr || !spr[0] || !spr[0].width) return;
    const P = pix(spr[0], spr[1], spr[2], spr[3], spr[4]), r2 = foot(c, spr);
    const [c0, c1] = span(P, r2 - 4, r2), tall = P.h >= 40 && !CARD[c] && PLAIN[c] === undefined, w = tall ? 22 : c1 - c0 + 4, d = CARD[c] ? 11 : tall ? 9 : 8, mid = (c0 + c1) / 2;      // (a tree: its crown's, wider than its trunk)
    push(out, {x: Math.round(spr[5] + mid - w / 2), y: spr[6] + r2 - d + 4, z: base + .5, w, d, h: 0, top: oval(w, d), shade: true});
    if (L !== undefined && c !== "^" && c !== "x") HdSun.thing(out, x, y, L, P, spr[5], spr[6], r2);
  }
  // the shadow of what moves (a body, what lies on the ground): boxes for the engine's view.ghosts, w x d px round a point, z px up
  function shadow(w, d, z) { const l = []; push(l, {x: -Math.round(w / 2), y: -Math.round(d / 2), z, w, d, h: 0, top: oval(w, d), shade: true}); return l; }
  // a rug, a blanket: flat on the ground, its picture the top of a box with no height
  function decal(out, c, x, y, base) { const spr = objectSprite(c, x, y, 0); if (!spr || !spr[0] || !spr[0].width) return; push(out, {x: spr[5] - 1, y: spr[6] - 1, z: base + .5, w: spr[3] + 2, d: spr[4] + 2, h: 0, top: flat(0xff000000, spr[3] + 2, spr[4] + 2, 0xff000000), shade: true}); push(out, {x: spr[5], y: spr[6], z: base + 1, w: spr[3], d: spr[4], h: 0, top: cut(pix(spr[0], spr[1], spr[2], spr[3], spr[4]), 0, spr[3], 0, spr[4])}); }
  return {CARD, PLAIN, card, foot, shade, shadow, decal};
};
