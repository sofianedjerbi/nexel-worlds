"""The HD look's sides are painted, not flat (the owner: "the quality of the rendering SUCKS. see the sides etc?").
A wall of earth or stone is the pack's own cliff px (voxpaint.js front: its light and mid in blobs, a stratum and
pebbles on earth, blocks on stone), and the land past the box (vox_style_land.js patches, the shader's kind 7) is
the land's own px at the land's own size: it was its paint's corner px, one flat tone a face, in a haze that took it
whole. A face is read as the screen shows it; the README's rule 7: no one px, the share of its commonest colour."""

import pytest

from test_e2e_hd_sun import hd

# the px in a rectangle of the screen (css px) a few px in from its edges: {n: px, most: the commonest colour's share,
# ch: of its art px, the share not the colour of the art px to their right (a slab: its tone's steps only; paint: a
# change every few px), rgb: its commonest colours}
READ = """([x0, x1, y0, y1]) => { const k = devicePixelRatio, u = Math.max(1, Math.round(HdLook.art().u * k));
  const X0 = Math.ceil(x0 * k) + 2, X1 = Math.floor(x1 * k) - 2, Y0 = Math.ceil(y0 * k) + 2, Y1 = Math.floor(y1 * k) - 2;
  if (X1 - X0 < 8 || Y1 - Y0 < 8) return {box: [X0, X1, Y0, Y1]};
  const w = X1 - X0, d = HdLook.read(X0, Y0, w, Y1 - Y0).data, n = new Map(), at = (i, j) => (j * w + i) * 4; let m = 0, ch = 0, cm = 0;
  for (let i = 0; i < d.length; i += 4) { const c = d[i] + ',' + d[i + 1] + ',' + d[i + 2]; n.set(c, (n.get(c) || 0) + 1); m++; }
  for (let j = 0; j < Y1 - Y0; j += u) for (let i = 0; i + u < w; i += u) { const q = at(i, j), r = at(i + u, j); cm++; if (d[q] !== d[r] || d[q + 1] !== d[r + 1] || d[q + 2] !== d[r + 2]) ch++; }
  return {box: [X0, X1, Y0, Y1], n: m, most: +(Math.max(...n.values()) / m).toFixed(3), ch: +(ch / cm).toFixed(3), rgb: [...n].sort((p, q) => q[1] - p[1]).slice(0, 3).map((p) => p[0])}; }"""


def scene(g):
    g.js("setOpt('shader', 'off'); setOpt('clouds', 0); setOpt('shadows', 0)")
    g.hour(.375)
    return g.pos()


def south_face(g, x0, x1, y, top, bot):
    """a south face as the screen shows it: tiles x0..x1 of row y, level top down to level bot"""
    (ax, ay), (bx, by) = g.js(f"[HdLook.screenOf({x0}, {y}, {top}), HdLook.screenOf({x1}, {y}, {bot})]")
    return g.js(READ, [ax, bx, ay, by])


def painted(f):
    """a face of paint: no colour has most of it, and its colour changes every few art px across (a slab: .07 to .11)"""
    return f and f.get("n", 0) > 200 and f["most"] < .5 and f["ch"] > .2


def grey(f, haze=0):
    """stone's grey (far off: the haze's blue over it, `haze` more of blue), not the meadow's green nor the sky's blue (b - r: 100)"""
    r, g, b = map(int, f["rgb"][0].split(","))
    return abs(r - g) < 25 and -10 < b - r < 25 + haze


@pytest.mark.quick
def test_a_wall_of_earth_and_one_of_stone_are_painted_not_flat(browser, server):
    g = hd(browser, server)
    x, y = scene(g)
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in (-6, -5) for i in range(-7, -1)], col=[4])          # earth: four high, 6 x 2
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in (-7, -6, -5) for i in range(1, 8)], col=[8])        # stone: eight high, a mass 7 x 3
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    earth, stone = south_face(g, x - 7, x - 1, y - 4, 4, 0), south_face(g, x + 1, x + 8, y - 4, 8, 0)
    assert painted(earth), earth
    assert painted(stone), stone
    r, _, b = map(int, earth["rgb"][0].split(","))
    assert r > b + 30, earth                                         # earth: brown
    assert grey(stone), stone


def test_a_mountain_past_the_box_is_painted_not_flat(browser, server):
    g = hd(browser, server)
    x, y = scene(g)
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-44, -24) for i in range(-12, 12)], col=[60])   # stone sixty high, 25 to 44 tiles north: past the box (24), over the world's bend there (some 37 levels down)
    g.stamp(-12, -24, ["." * 25] * 12)                               # the meadow up to it: nothing of the world's (a tree, a pond) stands in front of it
    if g.js(f"(Voxels.host.column({x}, {y - 34}) || [0]).slice(-1)[0]") != 60:     # (the page has the land that far only if it was near once: go and see it)
        g.rpc("dev_teleport", x=x, y=y - 30); g.arrive()
        g.rpc("dev_teleport", x=x, y=y); g.arrive()
    g.wait(f"(Voxels.host.column({x}, {y - 34}) || [0]).slice(-1)[0] === 60", 15000)
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    # its face over the meadow's far edge (the bend takes the land down there: the screen's rows over that edge are the mountain's)
    (ax, ay), (bx, _) = g.js(f"[HdLook.screenOf({x - 8}, {y - 24}, 12), HdLook.screenOf({x + 8}, {y - 24}, 12)]")
    face = g.js(READ, [ax, bx, max(4, ay - 70), ay - 6])
    assert grey(face, 20), face                                          # the mountain, not the sky nor the meadow
    assert painted(face), face
