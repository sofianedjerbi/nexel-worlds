"""Your body against a block in front of you, in the HD look (vox_style_sprites.js: how deep your px are drawn)."""

import pytest

from test_e2e_hd_behind import calm, go
from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e


def test_behind_a_block_your_body_below_its_top_edge_is_behind_it_not_drawn_over_it(browser, server):
    """(#281) Right behind a block a level up, on the meadow: the block's top edge crosses you at your middle. Below that
    edge the block is nearer the eye than you: there you are behind it (one px in two of you through it), not drawn whole
    over its top with its edge running out on both sides of you: "player and block look fused" (vox_style_sprites.js:
    you were one depth, your head's, and only the part of the block's top nearer than your head hid you)."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.give(dirt=1)
    r = g.js("(a) => rpc('act', a)", {"tool": "place", "args": {"x": x, "y": y - 1, "item": "dirt", "z": 1}})
    assert r.get("ok"), r
    g.settle(f"topAt({x}, {y - 1}) === 1")
    s = go(g, x, y - 2)                                                    # behind it, as in the wall's test
    edge = g.js(f"HdLook.screenOf({x} + .5, {y - 1}, 1)[1]")              # (the block's top, its north edge: CSS px)
    seen, out, below = g.js("(b) => HdLook.catSeen(b, true)", [0, 0, 10000, edge])
    print("PROBE #281", {"seen": seen, "drawn whole below the edge": out, "yours below it": below, "state": s})
    assert below > 20 and s["n"] == 0, (below, s)                          # (part of you is below its edge; no window: it does not hide most of you)
    assert out / below < .6, (out, below, seen)                            # below its edge: behind it, not over it
    assert seen > .3 and not g.errors, (seen, g.errors)                    # your head over it, whole
