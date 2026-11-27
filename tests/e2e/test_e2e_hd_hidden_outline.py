"""Under the open sky, land in front of you that hides part of you, not all of you (no x-ray window there, #280; the land
in front of your legs, not you drawn over it, #281): your outline is drawn through it (#359, the owner's pick). Up the
owner's stone terraces the step south of you hid you to the ears and nothing showed where the rest of you was."""

import pytest

from test_e2e_hd_behind import calm
from test_e2e_hd_open_terrace import seed12  # noqa: F401 (the fixture: the owner's world, seed 12)
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# the px of your body's box under the edge of the step south of you, past the shadow you cast on the step's top just under
# its edge (5 px): [x0, y0, x1, y1] device px, and that box's px as an array
BOX = """(() => { const p = myPos(), k = devicePixelRatio, a = View.of(ents.get('agent' + myId)), u = View.u, e = HdLook.screenOf(p.x + .5, p.y + 1, topAt(p.x, p.y + 1));
  return [Math.round((a[0] - 9 * u) * k), Math.round((e[1] + 8) * k), Math.round((a[0] + 9 * u) * k), Math.round((a[1] - u) * k)]; })()"""
READ = """([x0, y0, x1, y1]) => [...HdLook.read(x0, y0, x1 - x0, y1 - y0).data]"""


def test_on_a_hillside_the_part_of_you_the_step_hides_shows_as_your_outline(browser, seed12):  # noqa: F811
    """At the news clip's climb's end (13, -72, level 5) the step south of you (level 6) hides most of you, not all: no
    window, no checker. Under the step's edge, in your body's box, the picture with you differs from the land alone: your
    outline (a few px, more than 12), not your whole body (less than a third of the box): the step stays in front of you.
    Read standing, the land at rest: the same at 16 ms a frame as at 200."""
    g = hd(browser, seed12)
    try:
        calm(g)
        g.rpc("dev_teleport", x=13, y=-72, z=5)
        g.arrive()
        g.rest()
        g.js("(() => { WayShow.paint = () => {}; Target.off = true; return 1; })()")   # (the way out's marks and the keys' boxes are painted over these px)
        g.frames(3)
        assert g.js("HdLook.hid") == 0 and g.js("HdLook.win.a") == 0, "hidden here: the window, not this"
        box = g.js(BOX)
        assert box[3] - box[1] > 6, ("the step's edge is not over your body", box)
        with_you = g.js(READ, box)
        g.js("(() => { HdLook.landOnly = true; return 1; })()")
        g.frames(3)
        land = g.js(READ, box)
        g.js("(() => { HdLook.landOnly = false; return 1; })()")
        n = len(land) // 4
        diff = sum(1 for i in range(0, len(land), 4) if sum(abs(with_you[i + c] - land[i + c]) for c in range(3)) > 40)
        assert diff > 12, f"under the step's edge nothing of you shows: {diff} px of {n}"
        assert diff < n / 3, f"under the step's edge {diff} px of {n} are you: drawn over the step, not behind it"
    finally:
        g.page.close()
