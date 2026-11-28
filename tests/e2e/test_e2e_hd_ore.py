"""The land's ore on the HD look (ore_paint.js, vox_style_land.js; the world's sim/underground.py shown_ores): a cell of ore
that shows (air on a side) has nuggets on its faces, in its ore's colours; one shut in the rock is not told to the page."""

import tempfile
from pathlib import Path

import pytest
from test_e2e_hd_sun import hd

from nexel_worlds.world import Store, World


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
    g.rpc("dev_teleport", x=x, y=y + 4); g.arrive(); g.rest()
    cx, cy, cz = coal[0]
    g.until(f"oreAt({cx}, {cy}, {cz}) === 'coal'")             # (told by the server: waited for)
    assert g.js(f"oreAt({cx}, {cy}, {cz})") == "coal"                          # told: it shows
    assert g.js(f"oreAt({cx}, {cy}, 0)") is None                               # (the cell under it: rock on its south too, not told)
    box = g.js(FACE, [cx, cy, cz])
    with_ore = g.js(READ, box)
    g.js(f"(() => {{ oresAt({cx}, {cy}, {{}}); HdLook.touch({cx}, {cy}); return 1; }})()")   # the same face with no ore in it
    g.frames(8); g.rest()                                      # (made again with no ore, and drawn)
    bare = g.js(READ, box)
    changed = sum(1 for i in range(0, len(bare), 4) if abs(bare[i] - with_ore[i]) + abs(bare[i + 1] - with_ore[i + 1]) + abs(bare[i + 2] - with_ore[i + 2]) > 30)
    assert changed > len(bare) // 4 * .04, (changed, len(bare) // 4)          # its nuggets: a few px of the face in their own colours
    assert not g.errors


# the px of a cell's top on the screen (device px): [x0, y0, w, h], a px in from its edges
TOPF = """([x, y, z]) => { const a = HdLook.screenOf(x + .15, y + .15, z), b = HdLook.screenOf(x + .85, y + .85, z), k = devicePixelRatio;
  return [Math.round(a[0] * k), Math.round(a[1] * k), Math.max(1, Math.round((b[0] - a[0]) * k)), Math.max(1, Math.round((b[1] - a[1]) * k))]; }"""


def test_no_ore_shows_on_a_face_only_the_cut_opens(browser, server):
    """#4's face rule, point 4: a cell of ore beside your room shows (air on its side), but the top the x-ray cut lays bare over
    it (the land over it cut to two levels over your floor, rock over it in the real land) is the rock's own: no nuggets there."""
    w = World(Store(Path(tempfile.mkdtemp()) / "w.db"), seed=7)
    g = hd(browser, server)
    g.js("setOpt('clouds', 0); setOpt('shadows', 0)")
    g.hour(.3, still=True)
    x, y = g.pos()
    vein = [(i, j, z) for j in range(y - 6, y + 7) for i in range(x - 8, x + 8) for z in (2, 3, 4) if w.ore(i, j, z)]
    assert vein, "the tests' world changed: look for another vein near home.PLACE"
    cx, cy, cz = vein[0]
    g.rpc("dev_col", tiles=[[cx + i, cy + j] for i in (-1, 0) for j in (-1, 0, 1)], col=[cz + 6])                        # (rock over the vein, six over it)
    g.rpc("dev_col", tiles=[[cx + 1 + i, cy + j] for i in (0, 1) for j in (-1, 0, 1)], col=[cz - 2, cz + 2, cz + 6])       # a room east of it: floor cz - 2, air to cz + 2, land over it
    g.rpc("dev_teleport", x=cx + 1, y=cy, z=cz - 2)
    g.arrive()
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=10000)
    g.rest()
    assert g.js(f"oreAt({cx}, {cy}, {cz})"), "the vein's cell beside the room is told to the page (it shows: the room's air on its side)"
    box = g.js(TOPF, [cx, cy, cz])
    with_ore = g.js(READ, box)
    g.js(f"(() => {{ oresAt({cx}, {cy}, {{}}); HdLook.touch({cx}, {cy}); return 1; }})()")   # the same top with no ore told
    g.frames(8)
    g.rest()
    bare = g.js(READ, box)
    changed = sum(1 for i in range(0, len(bare), 4) if abs(bare[i] - with_ore[i]) + abs(bare[i + 1] - with_ore[i + 1]) + abs(bare[i + 2] - with_ore[i + 2]) > 30)
    assert changed <= len(bare) // 4 * .01, (changed, len(bare) // 4, (cx, cy, cz))   # the cut's top over the vein: no nugget px
    assert not g.errors
