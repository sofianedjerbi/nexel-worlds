"""The land made round you reaches as far south as the screen shows (#354): land south of you higher than you, a hill
climbed south, is nearer the eye and more rows of it show. The land reached as far as flat land shows, three rows
more: on the owner's stone terraces that was one row more than the screen, and jumping up them, the land shown was
still the one made a few tiles back: the screen's foot showed no land, a dark band, for a moment."""

import pytest

from test_e2e_hd_behind import calm
from test_e2e_hd_open_terrace import seed12  # noqa: F401 (the fixture: the owner's world, seed 12)
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# the southmost row the screen shows: down each column of its width, from your row south, the rows whose top's north
# edge is over the screen's foot (as the eye has it now), till the first under it; [that row, you: x, y, level]
LAST_ROW = """(() => { const p = myPos(), W = innerWidth, H = innerHeight; let last = p.y;
  for (let x = p.x - 30; x <= p.x + 30; x++) for (let y = p.y; y <= p.y + 60; y++) { const s = HdLook.screenOf(x + .5, y, topAt(x, y));
    if (!s || s[1] >= H) break; if (s[0] >= 0 && s[0] <= W) last = Math.max(last, y); }
  return [last, [p.x, p.y, myAt.z]]; })()"""


def test_the_land_shown_reaches_the_screen_s_foot_up_a_hill_climbed_south(browser, seed12):  # noqa: F811
    """On the owner's stone terraces (seed 12, x 13, the news clip's path) the land is made where you stand, then held
    (HdLook.hold = 0: no land made after it), and you walk south up four rows, jumping up two levels (or five rows:
    the key let go between two frames; the screen then shows one row more still). Once you stand and the eye has come
    to your level, every row the screen shows is in the land shown: the one made four rows back. Nothing here waits on
    a frame's length: the land is held, the walk ends where you stand (either row fails without the land reaching far
    enough, passes with it), the eye's level is waited for: the same at 16 ms a frame as at 200."""
    g = hd(browser, seed12)
    try:
        calm(g)
        g.rpc("dev_teleport", x=13, y=-76, z=3)
        g.arrive()
        g.rest()
        box = g.js("HdLook.box")                             # (the land shown is the one made here: rest)
        g.js("HdLook.hold = 0")
        g.page.keyboard.down("ArrowDown")
        try:
            g.wait("myPos().y >= -72", 15000)
        finally:
            g.page.keyboard.up("ArrowDown")
        g.wait("myAt && !BodyPlace.of(ents.get('agent' + myId)).jump && HdLook.level[1] === myAt.z", 8000)   # (you stand, the eye at your level)
        g.frames(2)
        last, me = g.js(LAST_ROW)
        assert me[1] >= -72 and me[2] >= 5, me                # (four rows south, two levels up, or a row more)
        assert last <= box[3], f"the screen shows row {last}, the land shown ends at row {box[3]} (made at -76: {box})"
    finally:
        g.js("HdLook.hold = null")
        g.page.close()
