"""A way in whose mouth opens into a pit (vox_style_land.js `mouths`): the ground in front of it is a hole's floor
(sunk), so neither that floor nor the land's top over the mouth is shaded. The owner's land at doben00's terraces
(caves world, x -21..-11, y -9..1): an old stair dug down west from a 1x2 pit under stepped terraces; the top over
its mouth, at an inner corner of two terrace walls, was a dark smudge: "shadow shouldn't appear here"."""

import json

from test_e2e_hd_behind import calm, go
from test_e2e_hd_mouth import PIECE
from test_e2e_hd_sun import hd

# the owner's columns (cells.col_runs), west to east from x -21, north to south from y -9
LAND = """
5 4 4 3 3 2 2 1 1 0 0
5 4 4 3 3 2 1 1 0 0 0
4 4 3 3 2 2 1 1 0 0 0
4 4 3 3 2 1 1 0 0 0 0
4 4 3 2 2 1 1 0 0 0 0
4 3 3 2 2 1 0 0 0 0 0
-8,-5,4 -7,-4,3 -6,-4,3 -5,-3,2 -4,-1,2 -3,-1,1 -2 -2 -1 0 0
4 3 3 2 1 1 0 0 0 0 0
4 3 3 2 1 1 0 0 0 0 0
"""
FILLED = "4 3 3 2 2 1 0 0 0 0 0"           # (the stair's row as the terraces round it: no way in)


def lay(g, x0, y0, rows):
    by = {}
    for j, row in enumerate(rows):
        for i, c in enumerate(row.split()):
            by.setdefault(c, []).append([x0 + i, y0 + j])
    for c, tiles in by.items():
        g.rpc("dev_col", tiles=tiles, col=[int(v) for v in c.split(",")])


def test_the_top_over_a_stair_dug_from_a_pit_is_not_shaded_as_a_mouth(browser, server):
    """The owner's terraces laid as they are, you where doben00 stood (on the terrace, x -15, y -5); the top over the
    stair's mouth (x -16, y -3, its middle, clear of its east rim over the pit) read with the stair open and then filled with the
    terraces' own land: as light (it was a dark smudge, the open one ~30 % darker)."""
    g = hd(browser, server)
    calm(g)
    g.js("setOpt('shadows', 0)")
    x, y = g.pos()
    x0, y0 = x - 6, y - 8                     # (the box's north-west corner: x -21, y -9 of the owner's)
    rows = [r for r in LAND.strip().splitlines()]
    top = [x0 + 5 + .15, y0 + 6 + .2, x0 + 5 + .55, y0 + 6 + .8, 1]
    read = "(() => { const P = " + PIECE + "; return Math.round(P(%s)); })()" % json.dumps(top)

    def look():
        go(g, x0 + 6, y0 + 4, 1)
        g.frames(2)
        return g.js(read)
    try:
        lay(g, x0, y0, rows)
        opened = look()
        lay(g, x0, y0 + 6, [FILLED])
        shut = look()
        assert opened > 0 and shut > 0, (opened, shut)
        assert opened > .95 * shut, (opened, shut)          # no mouth's shade over a way in from a hole's floor
    finally:
        go(g, x, y, 0)
        g.rpc("dev_col", tiles=[[x0 + i, y0 + j] for j in range(len(rows)) for i in range(11)], col=[0])
        g.js("setOpt('shadows', 100)")
