"""The HD look far from the world's middle (vox_style.js `draw`: the fog's and the lantern's uniforms): 150 tiles from
where you woke the land round you is drawn in the colours it has there, not in the air's haze. (The calls that give the
shader the eye and the lamp sat inside a trailing note: both stayed at the world's origin: the fog began 44 tiles from it
and 60 tiles out the whole meadow was flat sky blue, on any screen, shader and curve on or off.)"""


import pytest

from test_e2e_hd_sun import hd

# the mean colour of the meadow round you as the screen shows it: 3 x 2 tiles' tops beside you, [r, g, b]
MEADOW = """([x, y, z]) => { const s = [0, 0, 0]; let n = 0, k = devicePixelRatio;
  for (const [i, j] of [[2, 0], [3, 0], [4, 0], [2, 1], [3, 1], [4, 1], [-3, 0], [-4, 0]]) {
    const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + i + a, y + j + b, z));
    const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 1, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 1, y0 = Math.ceil(c[0][1] * k) + 1, y1 = Math.floor(c[2][1] * k) - 1;
    const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data; for (let q = 0; q < d.length; q += 4) { s[0] += d[q]; s[1] += d[q + 1]; s[2] += d[q + 2]; n++; } }
  return s.map((v) => v / n); }"""


@pytest.mark.quick
def test_150_tiles_from_where_you_woke_the_land_is_drawn_in_its_own_colours(browser, server):
    g = hd(browser, server)
    g.js("setOpt('shader', 'off'); setOpt('clouds', 0); setOpt('shadows', 0)")
    g.hour(.375)
    x, y = g.pos()
    near = g.js(MEADOW, [x, y, g.js(f"topAt({x}, {y})")])
    assert near[1] > near[2] + 40, near                              # a meadow: green, not blue
    for dx, dy in ((150, 0), (-150, 150)):
        g.rpc("dev_teleport", x=x + dx, y=y + dy)
        g.arrive()
        # the same flat meadow as where you woke, out to 30 tiles: the world's own hills 13 tiles south of a far place stood
        # in front of the meadow beside you (the eye looks down on you over them: pitch 40.7) and their grey stone was read
        # as its colour, [149, 160, 126] for [193, 213, 113], one run in eight by where the test took you
        g.clear_area(30)
        g.rpc("dev_teleport", x=x + dx, y=y + dy)
        g.arrive()
        fx, fy = g.pos()
        assert abs(fx - x - dx) + abs(fy - y - dy) < 8, (fx, fy)
        far = g.js(MEADOW, [fx, fy, g.js(f"topAt({fx}, {fy})")])
        # (in the haze every channel went to the air's: red +60, blue +120)
        assert all(abs(a - b) < 12 for a, b in zip(near, far)), (dx, dy, near, far)
