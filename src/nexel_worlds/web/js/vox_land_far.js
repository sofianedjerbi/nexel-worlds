// VOX: the far land's patches, kept (vox_style_land.js makes them past the box of land, to the horizon). Split out of
// VoxStyleLand's create (#154): what is kept of them and when it goes; how a patch is drawn stays in create (it reads the
// land being made), handed in to rows() as make.
//   VoxLandFar({P, CH}) -> {dirty(x0, y0, x1, y1): tiles changed, the patches reading them go at the next row; clear();
//     keep(): the sheet full, the paints of the patches round the land being made are kept (P.use); free(kept): the patches naming
//     a paint given away go; box(cx, cy, r): where the land being made lies; *rows(rows, make, fl, fs); fars: patches made; forgot: patches let go for a changed tile; fresh: patches made at a new place}
const VoxLandFar = ({P, CH}) => {
  const farOf = new Map(), farDirty = []; let farN = 0, fars = 0, forgot = 0, fresh = 0, farBox = null; const ever = new Set();   // (farOf: the far land's patches made, by where they are: "bx,by" (8 tiles) -> "x,y,w,h" -> faces; farDirty: boxes of tiles changed since)
  // the far land's patches a changed tile reaches (what they read: the tiles round them, a tile's paint by its rock five tiles off) are made again; a patch is 8 tiles at most
  const forget = () => { for (const [x0, y0, x1, y1] of farDirty) for (let by = Math.floor((y0 - 16) / CH); by <= Math.floor((y1 + 7) / CH); by++) for (let bx = Math.floor((x0 - 16) / CH); bx <= Math.floor((x1 + 7) / CH); bx++) { const m = farOf.get(bx + "," + by); if (m) { farN -= m.size; forgot += m.size; farOf.delete(bx + "," + by); } } farDirty.length = 0; };
  const clear = () => { farOf.clear(); farDirty.length = 0; farN = 0; };
  // THE SHEET FULL (vox_style.js evict): the far patches of the land being made name their paints' places (farBox: where its
  // patches lie): kept, as its chunks' are, and only the patches that name a place given away go. (Letting every far patch go
  // at once, walking 8 tiles and back fills the sheet twice, and the way back makes 1063 patches again of 1218)
  return {
    dirty(x0, y0, x1, y1) { farDirty.push([x0, y0, x1, y1]); },
    clear,
    keep() { if (!farBox) return; const [a, b, c, d] = farBox; for (const [bk, m] of farOf) { const [bx, by] = bk.split(",").map(Number); if (bx >= a && bx <= c && by >= b && by <= d) for (const f of m.values()) P.use(f[2]); } },
    free(kept) { for (const [bk, m] of farOf) { for (const [fk, f] of m) if (f[2].some((v) => !kept(v))) { m.delete(fk); farN--; } if (!m.size) farOf.delete(bk); } },
    box(cx, cy, r) { farBox = [Math.floor((cx - r - 48) / CH), Math.floor((cy - r - 48) / CH), Math.floor((cx + r + 48) / CH), Math.floor((cy + r + 48) / CH)]; },
    *rows(rows, make, fl, fs) {   // (the patches of each row: kept ones again, others made by make(x, y, w, h, land, sea) -> the places of the paints they name)
      for (const [y, h, cols] of rows) { yield "far"; if (farDirty.length) forget(); for (const [x, w] of cols) { const bk = Math.floor(x / CH) + "," + Math.floor(y / CH), fk = x + "," + y + "," + w + "," + h; let m = farOf.get(bk); const had = m && m.get(fk);
        if (had) { P.use(had[2]); if (had[0].length) fl.push(had[0]); if (had[1].length) fs.push(had[1]); continue; } const a = [], b = []; fars++; if (!ever.has(fk)) { fresh++; if (ever.size >= 30000) ever.clear(); ever.add(fk); } const s = make(x, y, w, h, a, b), f = [new Float32Array(a), new Float32Array(b), s]; if (!m) farOf.set(bk, m = new Map()); m.set(fk, f); farN++; if (a.length) fl.push(f[0]); if (b.length) fs.push(f[1]); if (farN % 6 === 0) yield "far"; }   // (a step: six patches made, not a row of them: a slow phone's frame waited for 27)
        if (farN > 12000) clear(); }   // (a patch's faces kept by where it is: walking, the patches 4, 8 tiles back are this one's; 4 ms of each land's 6 were the far land made again)
    },
    get fars() { return fars; },
    get forgot() { return forgot; },   // (patches let go as a tile they read changed: made again rightly, tests: hd_work)
    get fresh() { return fresh; },   // (patches made at a place where none was made yet: walking back over land made, none; tests: hd_work, #240)
  };
};
