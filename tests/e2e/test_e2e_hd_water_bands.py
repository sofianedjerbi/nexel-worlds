"""Deep water's tone goes deeper in pixel bands, not a step at each tile (#347, the owner's pick, take 2 "Pixel bands"; the
owner: "see water changing color on deep levels? make it a nice beautiful gradient"). Each water tile had one tint by its
whole depth: a lake 2 to 4 levels deep was flat tones meeting at tile edges, a level's step at each."""

import pytest

from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# a lake 18 wide, 11 rows, north of you: its kind mid, deep, abyss west to east (3 and 4 levels deep only 4 tiles from a bank
# or more, waterbed.js; 2 nearer). Along its middle rows its depth goes 2, 3, 4 from its west bank: the tiles read, 15 of them
LAKE = ["(((((======)))))))"] * 11
ROWS, TILES = (4, 7), 15

# the depth of each tile read, the game's own (its face over its bed), in its middle row
DEPTHS = """([x0, y0]) => Array.from({length: %d}, (_, i) => { const c = Voxels.host.column(x0 + i, y0 + 5); return topAt(x0 + i, y0 + 5) - c[c.length - 1]; })""" % TILES

# the tone (r + g + b) of the water's top along the lake, an art px at a time west to east: for each art px column, the median
# of its art px down the lake's 3 middle rows of tiles (the waves' glints on a few of them left out), read on the screen
PROFILE = """([x0, y0]) => { const k = devicePixelRatio, at = [];
  for (let i = 0; i < %d * 16; i++) { const tx = x0 + (i >> 4), r = []; at.push(r);
    for (let j = %d * 16; j < %d * 16; j++) { const ty = y0 + (j >> 4), s = HdLook.screenOf(tx + ((i & 15) + .5) / 16, ty + ((j & 15) + .5) / 16, topAt(tx, ty)); r.push([Math.round(s[0] * k), Math.round(s[1] * k)]); } }
  const all = at.flat(), X0 = Math.min(...all.map((p) => p[0])), Y0 = Math.min(...all.map((p) => p[1])), W = Math.max(...all.map((p) => p[0])) - X0 + 1, H = Math.max(...all.map((p) => p[1])) - Y0 + 1;
  const d = HdLook.read(X0, Y0, W, H).data;
  return at.map((r) => { const v = r.map(([x, y]) => { const o = ((y - Y0) * W + x - X0) * 4; return d[o] + d[o + 1] + d[o + 2]; }).sort((a, b) => a - b); return v[v.length >> 1]; }); }""" % (TILES, *ROWS)


def test_deep_water_goes_deeper_across_its_tiles_with_no_step_at_a_tiles_edge(browser, server):
    """Along a lake 2, 3 then 4 levels deep from its west bank, the water's tone, art px by art px: at the edge between
    two tiles of different depths, the tone each side is the same (less than a third of a level's change: it was a whole
    level's, 42 and 61 for a level of 35); inside the tile west of that edge it already changes (more than a third of a
    level: it was flat, 4). Read once, the land at rest (rest(): made and drawn) and the same state whatever the frames'
    rhythm: the tone is the shader's, from the depths at the tiles' corners, not from time; the waves' glints are left
    out by the median of 48 art px down each column: the same at 16 ms a frame as at 200."""
    g = hd(browser, server)
    try:
        g.stamp(-9, -12, LAKE)
        g.rest()
        x, y = g.pos()
        at = [round(x) - 9, round(y) - 12]
        depths = g.js(DEPTHS, at)
        assert depths == sorted(depths) and set(depths) == {2, 3, 4}, f"the lake is not 2, 3 then 4 levels deep west to east: {depths}"
        cols = g.js(PROFILE, at)
        mean = lambda a, b: sum(cols[a:b]) / (b - a)  # noqa: E731
        level = abs(mean(16, 32) - mean(12 * 16, 13 * 16)) / 2      # (a level's change of tone: from the tiles 2 deep to those 4 deep, inside them)
        edges = [i for i in range(1, TILES) if depths[i] != depths[i - 1]]
        jumps = [abs(mean(e * 16, e * 16 + 4) - mean(e * 16 - 4, e * 16)) for e in edges]     # (the 4 art px each side of a tile's edge where the depth changes)
        inner = [abs(mean(e * 16 - 4, e * 16) - mean(e * 16 - 16, e * 16 - 12)) for e in edges]   # (from one side to the other of the tile west of that edge)
        state = f"depths {depths}, level {level:.1f}, edges {edges}, jumps {jumps}, inside {inner}, profile {cols}"
        assert level > 20, f"the lake 2 to 4 levels deep is one tone: {state}"
        assert len(edges) == 2 and max(jumps) < level / 3, f"the tone steps at a tile's edge, a level at a time: {state}"
        assert min(inner) > level / 3, f"a tile one tone, its whole depth's: no bands: {state}"
    finally:
        g.page.close()
