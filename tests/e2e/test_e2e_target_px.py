"""A box on the screen is its block, px by px (target.js `pxOf`, `outline`): its line on every px of the cube's edge in
the colour of what the key does, nothing of it off the cube, on every side the eye sees."""

from test_e2e_hd_sun import hd


# A box on the screen, art px by art px: the cube's own px (an art px whose middle is inside the outline of its 8 corners, the
# land's rule), what the box changed (the picture with it and without it, Target.off), and which px are the line's colour.
# -> {outside: px it changed off the cube, missing: px of the cube's edge not in the line's colour, line: px in that colour}
ON_CUBE = r"""async (c) => {
  const art = HdLook.art(), k = devicePixelRatio, u = art.u, U = u * k, P = [], B = art.body;
  for (const i of [0, 1]) for (const j of [0, 1]) for (const l of [0, 1]) P.push(art.at(c.x + i, c.y + j, c.z - l));
  const pts = P.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]), cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]), lo = [], hi = [];
  for (const p of pts) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
  for (const p of pts.slice().reverse()) { while (hi.length >= 2 && cr(hi[hi.length - 2], hi[hi.length - 1], p) <= 0) hi.pop(); hi.push(p); }
  const hull = lo.slice(0, -1).concat(hi.slice(0, -1)), inH = (x, y) => hull.every((a, i) => cr(a, hull[(i + 1) % hull.length], [x, y]) >= 0);
  const i0 = Math.floor(Math.min(...P.map((p) => p[0])) / u) - 3, j0 = Math.floor(Math.min(...P.map((p) => p[1])) / u) - 3;
  const n = Math.ceil(Math.max(...P.map((p) => p[0])) / u) - i0 + 4, m = Math.ceil(Math.max(...P.map((p) => p[1])) / u) - j0 + 4;
  // (until the marks were painted again since: a busy machine skips frames, and the picture read was the one before)
  const raf = () => new Promise((r) => requestAnimationFrame(r)), frame = async () => { Target.drew = null; for (let t = 0; t < 120 && Target.drew === null; t++) await raf(); await raf(); await raf(); };
  Target.show = [c]; Target.off = true; await frame(); const off = HdLook.read(i0 * U, j0 * U, n * U, m * U).data;
  Target.off = false; await frame(); const on = HdLook.read(i0 * U, j0 * U, n * U, m * U).data;
  Target.off = true; await frame(); const off2 = HdLook.read(i0 * U, j0 * U, n * U, m * U).data;   // (what moved by itself meanwhile, the land's grass, you: not the box's)
  Target.off = false; Target.show = null;
  const col = c.ok === false ? [232, 85, 74] : c.kind === "break" ? [255, 157, 60] : [255, 248, 232], at = (i, j) => ((j * U + (U >> 1)) * n * U + i * U + (U >> 1)) * 4;
  const cube = (i, j) => i >= 0 && j >= 0 && i < n && j < m && inH((i0 + i + .5) * u, (j0 + j + .5) * u);
  let outside = 0, missing = 0, line = 0; const out = [];
  for (let j = 0; j < m; j++) for (let i = 0; i < n; i++) { const o = at(i, j), d = Math.abs(on[o] - off[o]) + Math.abs(on[o + 1] - off[o + 1]) + Math.abs(on[o + 2] - off[o + 2]);
    const isCol = Math.abs(on[o] - col[0]) + Math.abs(on[o + 1] - col[1]) + Math.abs(on[o + 2] - col[2]) < 30; if (isCol) line++;
    const X = (i0 + i + .5) * u, Y = (j0 + j + .5) * u, me = !!B && X >= B.x - u && X <= B.x + B.w + u && Y >= B.y - u && Y <= B.y + B.h + u;   // (you: your sprite breathes and blinks)
    const still = !me && Math.abs(off2[o] - off[o]) + Math.abs(off2[o + 1] - off[o + 1]) + Math.abs(off2[o + 2] - off[o + 2]) <= 6;
    if (d > 6 && still && !cube(i, j) && ++outside < 6) out.push([i - 3, j - 3, [...on.slice(o, o + 3)], [...off.slice(o, o + 3)]]);
    if (!me && cube(i, j) && !(cube(i - 1, j) && cube(i + 1, j) && cube(i, j - 1) && cube(i, j + 1)) && !isCol) missing++; }   // (nothing of a box is drawn on you: hd_level.js cut)
  return {outside, missing, line, out, n, m};
}"""


def test_a_box_lies_on_its_block_its_line_on_every_edge_px_and_none_outside(browser, server):
    """The owner: "does it respect the block structure?". Each box, a block to take right of the eye (its west side
    seen), left of it (its east side), north, a level up; earth to put on a block; a block that cannot go there: every
    px of the cube's edge on the screen is the line's colour (orange, cream, red), and nothing of the box is off the
    cube (an ink row lay under every box's bottom edge, on the grass, and a side's line stepped out of it)."""
    game = hd(browser, server)
    game.clear_area(6)
    for dx, dy, lv in ((2, 1, "1"), (-3, 1, "1"), (0, -2, "1"), (3, -2, "2")):
        game.stamp(dx, dy, ["."], levels=[lv])
    game.rest()
    x, y = game.pos()
    for c in ({"kind": "break", "x": x + 2, "y": y + 1, "z": 1}, {"kind": "break", "x": x - 3, "y": y + 1, "z": 1}, {"kind": "break", "x": x, "y": y - 2, "z": 1},
              {"kind": "break", "x": x + 3, "y": y - 2, "z": 2}, {"kind": "place", "x": x - 3, "y": y + 1, "z": 2, "item": "dirt"},
              {"kind": "place", "ok": False, "x": x + 2, "y": y + 1, "z": 2, "item": "dirt"}):
        r = game.js(ON_CUBE, c)
        assert r["outside"] == 0 and r["missing"] == 0 and r["line"] > 30, (c, r)
    assert not game.errors
