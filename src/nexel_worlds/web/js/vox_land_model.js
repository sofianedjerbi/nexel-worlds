// VOX: what stands in the land as boxes (host.models: a bridge's deck and posts, a built block), as faces: vox_style_land.js makes
// them with a chunk's land (and the frame's ghosts and shadows: vox_style.js, through VoxStyleLand's model). Split out of
// VoxStyleLand's create (#154): the same code, given what it reads (K: host, cfg, slot: a paint's place, SL: places a row of the
// sheet, C: art px a tile, emit and TRI: the vertex writer and a quad's triangles, FACES: each face's light).
//   VoxLandModel(K) -> model(x, y, b, dst): box b on tile (x, y) onto dst
const VoxLandModel = ({host, cfg, slot, SL, C, emit, TRI, FACES}) => {
  const H = VoxStyleGLSL.H;
  let msh = null;
  // what stands in the land as boxes (host.models: a bridge's deck and posts): a top and a south front each, its paint from the host's sheet px for px into a slot; each face lit as the land's own face that way is (FACES k: it had its own .85, .68, .74)
  const paintOf = new WeakMap(), QC = new Float64Array(12);   // (model: a uv's paint name and painter; a face's four corners)
  const sheet = () => { if (!msh) { const q = host.modelSheet(); msh = q.px ? q : {px: new Uint32Array(q.getContext("2d").getImageData(0, 0, q.width, q.height).data.buffer), w: q.width}; } return msh; };
  const model = (x, y, b, dst) => { const X = x + b.x / C, Y = y + b.y / C, X1 = X + b.w / C, Y1 = Y + b.d / C, Z0 = b.z / cfg.up, Z1 = (b.z + b.h) / cfg.up, Zn = Z1 + (b.tilt ? b.tilt[0] / cfg.up : 0), Zs = Z1 + (b.tilt ? b.tilt[1] / cfg.up : 0);
    const face = (uv, w, h, k) => { if (!uv) return; w = Math.min(C, w); h = Math.min(C, h); const wi = b.win ? b.win[0] : 0, wj = b.win ? b.win[1] : 0, ins = b.shade ? .02 : 0, pw = b.win ? C : w, ph = b.win ? C : h, id = b.sheet ? b.sheet.id : "";
      const ob = typeof uv === "object"; let pk = ob ? paintOf.get(uv) : null; if (!pk || pk.id !== id || pk.pw !== pw || pk.ph !== ph) { const ms = b.sheet; pk = {id, pw, ph, k: "m" + id + uv + "," + pw + "," + ph, paint: (px, at, st) => { const m = ms || sheet(); for (let j = 0; j < ph; j++) for (let i = 0; i < pw; i++) px[at + j * st + i] = m.px[(uv[2] ? uv[1] : uv[1] + j) * m.w + (uv[2] ? uv[0] : uv[0] + i)]; }}; if (ob) paintOf.set(uv, pk); }   // (its paint's name and painter, made once per uv and kept: a shadow's faces share them, frame to frame)
      const sl = slot(pk.k, pk.paint), u0 = (sl % SL) * C + wi, v0 = (sl / SL | 0) * C + wj, kind = b.shade ? 10 : b.ghost ? 9 : 8;
      for (let t = 0; t < 6; t++) { const n = TRI[t], o = n * 3; emit(dst, QC[o], QC[o + 2] * H, QC[o + 1], u0 + (n === 0 || n === 3 ? ins : w - ins), v0 + (n < 2 ? ins : h - ins), k, 1, kind, Z1, 0); } };   // (corners in QC: x, y, z each)
    const cq = (a, b2, c, d, e, f, g, h, i, j, k, l) => { QC[0] = a; QC[1] = b2; QC[2] = c; QC[3] = d; QC[4] = e; QC[5] = f; QC[6] = g; QC[7] = h; QC[8] = i; QC[9] = j; QC[10] = k; QC[11] = l; };
    cq(X, Y, Zn, X1, Y, Zn, X1, Y1, Zs, X, Y1, Zs); face(b.top, b.w, b.d, b.k || 1); const fh = b.fh || b.h; if (b.h) { cq(X, Y1, Zs, X1, Y1, Zs, X1, Y1, Z0, X, Y1, Z0); face(b.front, b.w, fh, FACES[2].k);
      cq(X, Y, Zn, X, Y1, Zs, X, Y1, Z0, X, Y, Z0); face(b.west, b.d, fh, FACES[5].k); cq(X1, Y1, Zs, X1, Y, Zn, X1, Y, Z0, X1, Y1, Z0); face(b.east, b.d, fh, FACES[4].k); } };   // (b.sheet: a paint sheet of its own, {px, w, id}; west, east: its sides, d x h px; fh: its front and sides are that many rows of paint over its height; win: [i, j]: its paint is 16 x 16 px and the face shows it from px (i, j) on; a shade's paint is read a hair inside its edges: at an edge it took a px of the paint beside it in the atlas, a thin dark line on the ground; tilt: [n, s]: its top a slope: px its north and its south edge are over its height (a roof's pitch); k: its top's light)
  return model;
};
