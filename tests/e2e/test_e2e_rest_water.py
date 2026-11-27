"""The land at rest (waits.py REST, every test's rest()) is the land with its water made for the tiles it has now (#362).
A block's water is made again a step a frame after its tiles change (voxels.js work); till then it shows the water it had.
The rest asked only that each block had come and had some water made: a test read the screen while a block still showed
the river stamped before, and the gorge test saw two rivers in one, cut at the block's edge (x 0)."""

import pytest

from test_e2e_hd_sun import hd
from waits import REST, WATCH

pytestmark = pytest.mark.e2e

# every block in view: its water made for its tiles as they are now
SEAS = """(() => { const [x, y, w, h] = viewRect(0), old = [];
  for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++) for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++) {
    const b = blocks.get(bkey(bx, by)); if (b && b.seaAt !== b.ver) old.push([bx, by]); }
  return old; })()"""


def test_the_land_is_not_at_rest_while_a_block_s_water_is_the_water_it_had(browser, server):
    """At rest, a river is stamped across the block edge west of you while the making of the blocks' water is held
    (Voxels.work: nothing): that block's water is the one before the river. The rest is asked then: it is not at rest
    (it says late after its 3 s). The making let go, it comes to rest, every block's water made. Held by the test, not
    by time: the water is not made while held whatever a frame's length, made once let go: the same at 16 ms a frame as
    at 200."""
    g = hd(browser, server)
    try:
        g.js(WATCH)
        g.js("(() => { window.__work = Voxels.work; Voxels.work = () => {}; return 1; })()")
        g.stamp(-6, -3, ["~" * 12] * 2)                     # (x -6..5: across the edge of the blocks at x 0)
        g.wait("dirtyTiles.length === 0")                    # (its tiles drawn: the blocks' versions gone up)
        old = g.js(SEAS)
        assert old, "the stamp left no block with its water still to make"
        late = g.js(REST, [3, 3000])
        assert late, f"at rest with blocks whose water is the one before the river: {old}"
        g.js("(() => { Voxels.work = window.__work; return 1; })()")
        g.rest()
        assert g.js(SEAS) == [], g.js(SEAS)
    finally:
        g.js("(() => { if (window.__work) Voxels.work = window.__work; return 1; })()")
        g.page.close()
