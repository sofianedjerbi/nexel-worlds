"""The land's ore on the HD look (ore_paint.js, vox_style_land.js; the world's sim/underground.py shown_ores): a cell of ore
that shows (air on a side) has nuggets on its faces, in its ore's colours; one shut in the rock is not told to the page."""

import tempfile
from pathlib import Path

import pytest
from test_e2e_hd_sun import hd

from nexel_worlds.world import Store, World

pytestmark = [pytest.mark.e2e, pytest.mark.realtime]

# the px of a cell's south face on the screen (device px): [x0, y0, w, h], a px in from its edges
FACE = """([x, y, z]) => { const a = HdLook.screenOf(x + .1, y + 1, z - .1), b = HdLook.screenOf(x + .9, y + 1, z - .9), k = devicePixelRatio;
  return [Math.round(a[0] * k), Math.round(a[1] * k), Math.round((b[0] - a[0]) * k), Math.round((b[1] - a[1]) * k)]; }"""
READ = """([x, y, w, h]) => [...HdLook.read(x, y, w, h).data]"""


def test_a_cell_of_ore_that_shows_has_nuggets_on_its_face(browser, server):
    w = World(Store(Path(tempfile.mkdtemp()) / "w.db"), seed=7)               # (the tests' world: tests/e2e/conftest.py)
    g = hd(browser, server)
    g.js("setOpt('clouds', 0); setOpt('shadows', 0)")
    g.hour(.3, still=True)
    x, y = g.pos()
    row = [(x + i, y) for i in range(-4, 0)]
    coal = [(i, j, z) for i, j in row for z in (1, 2) if w.ore(i, j, z)]
    assert coal, "the tests' world changed: look for another vein near home.PLACE"
    g.rpc("dev_col", tiles=[list(t) for t in row], col=[6])                    # a stone block six high, its south face to the eye
    g.rpc("dev_teleport", x=x, y=y + 4); g.arrive(); g.rest(); g.sleep(600)
    cx, cy, cz = coal[0]
    assert g.js(f"oreAt({cx}, {cy}, {cz})") == "coal"                          # told: it shows
    assert g.js(f"oreAt({cx}, {cy}, 0)") is None                               # (the cell under it: rock on its south too, not told)
    box = g.js(FACE, [cx, cy, cz])
    with_ore = g.js(READ, box)
    g.js(f"(() => {{ oresAt({cx}, {cy}, {{}}); HdLook.touch({cx}, {cy}); return 1; }})()")   # the same face with no ore in it
    g.frames(8); g.sleep(300)
    bare = g.js(READ, box)
    changed = sum(1 for i in range(0, len(bare), 4) if abs(bare[i] - with_ore[i]) + abs(bare[i + 1] - with_ore[i + 1]) + abs(bare[i + 2] - with_ore[i + 2]) > 30)
    assert changed > len(bare) // 4 * .04, (changed, len(bare) // 4)          # its nuggets: a few px of the face in their own colours
    assert not g.errors
