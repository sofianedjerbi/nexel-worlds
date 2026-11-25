// The land's ores on the blocks that show them (sim/underground.py shown_ores: a cell of ore with air on a side), painted into
// a face's own px by the land's painter (vox_style_land.js): over the stone, three or four NUGGETS, each a lump 3 x 2 art px
// lit along its top with a dark rim under it, in its ore's colours (the owner's pick of three looks: specks, nuggets, veins).
// Where they lie on a face comes from `seed` (the face's variant, the tile): the same block looks the same each time it is made.
const OrePaint = (() => {
  // [the ore, its light, its rim]: coal black with a grey glint; copper with its green; iron rust; gold; titanium a pale blue
  const COL = {coal: ["141418", "5c5c66", "000000"], copper_ore: ["cf6f3c", "7fd6ad", "6a3218"], iron_ore: ["c48a64", "f2d2b4", "6b4430"],
    gold_ore: ["eab532", "fff3b0", "7a5410"], titanium_ore: ["74a8e4", "eef8ff", "2c4f7c"]};
  const abgr = (h) => (255 << 24 | parseInt(h.slice(4, 6), 16) << 16 | parseInt(h.slice(2, 4), 16) << 8 | parseInt(h.slice(0, 2), 16)) >>> 0;
  const PX = Object.fromEntries(Object.entries(COL).map(([k, v]) => [k, v.map(abgr)]));
  // px of a face, w x h art px from `at` (rows `st` apart): its nuggets
  function nuggets(px, at, st, w, h, item, seed) {
    const c = PX[item]; if (!c) return;
    let s = (seed * 2654435761 + item.length * 97) >>> 0;
    const rnd = (n) => { s = (Math.imul(s, 1103515245) + 12345) >>> 0; return (s >>> 8) % n; };
    const put = (i, j, v) => { if (i >= 0 && j >= 0 && i < w && j < h) px[at + j * st + i] = v; };
    const n = 3 + rnd(2);
    for (let k = 0; k < n; k++) {
      const i = 1 + rnd(Math.max(1, w - 5)), j = 1 + rnd(Math.max(1, h - 4));
      for (let a = 0; a < 3; a++) put(i + a, j + 2, c[2]);                  // (its rim first, under it and at its end)
      put(i + 3, j + 1, c[2]);
      put(i, j, c[1]); put(i + 1, j, c[1]); put(i + 2, j, c[0]);             // (its top, lit)
      for (let a = 0; a < 3; a++) put(i + a, j + 1, c[0]);
    }
  }
  return {nuggets, has: (item) => !!COL[item]};
})();
