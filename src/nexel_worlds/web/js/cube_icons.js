// A block in your pack is drawn as a block: a small cube, three faces seen (the top lit, the left in its own tone,
// the right in shade), each face in the block's own paint, and the game's ink round it. ("Block icons look like textures
// put in inventory.") The paint is the land's: earth and stone as the build ghost has them (buildghost.js paintOf:
// the land's top, voxpaint.js `front` for the sides), planks as a built block of them (floors.js `cell`: the pack's
// house floor, its wall planks for the sides), a path its cobbles laid on bare earth. Made at load, at the size asked
// (13 in a 16 px cell: ui.js iconCanvas; 11 the slot's and the ground's, 8 in the hand), whole px, never a texture scaled: each px of a
// face takes the px of the paint under it.
const CubeIcon = (() => {
  const CUBES = new Set(["dirt", "stone_block", "plank", "path"]), INK = 0xff604c75 >>> 0;   // (Structures.INK, #754c60)
  const paints = new Map(), made = new Map();
  const rgbOf = (v) => [v & 255, v >>> 8 & 255, v >>> 16 & 255];
  const pack = ([r, g, b]) => (255 << 24 | b << 16 | g << 8 | r) >>> 0;
  const mix = (v, to, k) => pack(rgbOf(v).map((c, i) => Math.round(c * (1 - k) + to[i] * k)));
  const LIGHT = [255, 248, 232], SHADE = rgbOf(INK);
  // -> {top, side}: two 16 x 16 Uint32Arrays (a px: alpha, blue, green, red)
  function paint(name) {
    if (paints.has(name)) return paints.get(name);
    const top = new Uint32Array(256), side = new Uint32Array(256);
    if (name === "plank") {
      const d = sheetData(IMG.house_walls), at = (x, y) => d.px[y * d.w + x];
      for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) { top[j * 16 + i] = at(16 + i, 16 + j); side[j * 16 + i] = j === 0 || j === 15 ? INK : at(56 + i, 9 + j % 7); }   // (floors.js cell: two courses of the wall's planks, the ink over and under them)
    } else {
      const g = BuildGhost.paintOf(name === "path" ? "dirt" : name); if (!g) return null;
      top.set(g.subarray(0, 256)); side.set(g.subarray(256, 512));
      if (name === "path") { const d = sheetData(IMG.cobble); for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) { const v = d.px[(16 + j) * d.w + 16 + i]; if (v >>> 24 > 127) top[j * 16 + i] = v; } }
    }
    const p = {top, side}; paints.set(name, p); return p;
  }
  // Which face a px of a W x W cube is on, and where on the face (u, v in 0..1): null outside it.
  //   iso: the corner nearest you in the middle, its top a diamond twice as wide as high (the mockup's other choice: at 11 px it read as a barrel).
  //   box (the one shown): seen from the front and a little from the right and above (the land's own eye): the top a band, the front, a narrow right side.
  function face(style, W, x, y) {
    const H = W;
    if (style === "box") {
      const B = W >= 10 ? W - 1 : W, H = B; x -= (W - B) >> 1; y -= (W - B + 1) >> 1; if (x < 0 || y < 0 || x >= B || y >= B) return null;   // (a px less than the slot: as big as the other things in it)
      const d = Math.max(2, Math.round(B * .3)), fw = B - d, o = (16 - fw) >> 1, P = (i) => (i + .5) / 16;   // (the paint's px as they are, a px of it a px of the face: cut, never squeezed)
      if (y < d) { const s = d - 1 - y; if (x >= s && x < s + fw) return ["top", P(o + x - s), P(8 - d + y)]; }
      if (y >= d && x < fw) return ["left", P(o + x), P(y - d)];
      const k = x - fw + 1; if (k >= 1 && k <= d && y >= d - k && y <= H - 1 - k) return ["right", P(o + fw + k - 1), P(y - (d - k))];
      return null;
    }
    // (an even width w, a px or two under W, so the corners are two px; its top w / 2 high, its sides the rest: taller than the top, a cube and not a cake)
    const w = W >= 10 ? W - 2 + (W & 1) : W - (W & 1); x -= (W - w) >> 1; if (x < 0 || x >= w) return null;
    const c = (w - 1) / 2, dx = Math.floor(Math.abs(x - c)), e = dx >> 1, th = w / 2, half = w / 2, cl = (k) => Math.min(.999, Math.max(0, k));
    if (y >= e && y <= th - 1 - e) { const X = x - c, Y = y + .5; return ["top", cl(Y / th + X / w), cl(Y / th - X / w)]; }
    if (y >= th - e && y <= H - 1 - e) { const b = cl((y - (th - e) + .5) / (H - th)); return x <= c ? ["left", cl((x + .5) / half), b] : ["right", cl((x + .5 - half) / half), b]; }
    return null;
  }
  // -> ImageData W x W, the cube of `name` (null: not a block)
  function px(name, W, style = CubeIcon.style) {
    const key = name + W + style; if (made.has(key)) return made.get(key);
    const p = CUBES.has(name) ? paint(name) : null; if (!p) return null;
    const F = [], at = (x, y) => (x < 0 || y < 0 || x >= W || y >= W ? null : F[y * W + x]);
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) F.push(face(style, W, x, y));
    const out = new ImageData(W, W), o32 = new Uint32Array(out.data.buffer);
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
      const f = at(x, y); if (!f) continue;
      const [which, u, v] = f, t = Math.min(15, Math.floor(u * 16)), s = Math.min(15, Math.floor(v * 16));
      let c;
      if ([[-1, 0], [1, 0], [0, -1], [0, 1]].some(([a, b]) => !at(x + a, y + b))) c = INK;            // the ink round it
      else if (which === "top") { const n = at(x, y + 1); c = mix(p.top[s * 16 + t] | 0xff000000, LIGHT, n && n[0] !== "top" ? .5 : .08); }   // (its near edge: the lit rim)
      else c = which === "left" ? p.side[s * 16 + t] | 0xff000000 : mix(p.side[s * 16 + t] | 0xff000000, SHADE, .45);
      o32[y * W + x] = c >>> 0;
    }
    made.set(key, out); return out;
  }
  function canvas(name, W) { const im = px(name, W); if (!im) return null; const c = document.createElement("canvas"); c.width = c.height = W; c.getContext("2d").putImageData(im, 0, 0); return c; }
  // Where a cube's px go in a cell of W, its px in the middle: (not made at 16, a 15 px block filling the pack's cell, where a log or a loaf is
  // 12 or 13 px of a 16 px icon: the blocks stand out as tiles. Made at CELL, 12 px: as big as the others, and never scaled)
  function mid(im, W) {
    const d = new Uint32Array(im.data.buffer); let b = [1e9, 1e9, -1, -1];
    for (let y = 0; y < im.height; y++) for (let x = 0; x < im.width; x++) if (d[y * im.width + x] >>> 24) b = [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)];
    return b[2] < 0 ? [0, 0] : [((W - (b[2] - b[0] + 1)) >> 1) - b[0], ((W - (b[3] - b[1] + 1)) >> 1) - b[1]];
  }
  return {is: (n) => CUBES.has(n), px, canvas, mid, style: "box", CELL: 13};
})();
