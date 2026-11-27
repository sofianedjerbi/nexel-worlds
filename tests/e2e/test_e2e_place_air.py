"""A block of the land in hand, out of build mode, over ground lower than your own (floors.js intent, mouse.js
tileAtScreen): it goes at your own level, the ground you stand on carried on in a straight line through the air."""

import pytest

pytestmark = pytest.mark.e2e


def terrace(game):
    """You on the east edge of a terrace six levels over the meadow, facing east, earth in hand."""
    game.clear_area(10)
    x, y = game.pos()
    game.rpc("dev_col", tiles=[[x + i, y + j] for i in range(-3, 1) for j in (-1, 0, 1)], col=[6])
    game.rpc("dev_teleport", x=x, y=y, z=6); game.arrive()
    game.give(dirt=6)
    game.hold_item("dirt")
    game.face(1, 0); game.rest()
    return x, y


def test_over_a_cliff_the_block_goes_at_your_level_in_a_straight_line_not_down_on_its_foot(game):
    """"placing above a cliff shouldn't make the bloc go right down on the cliff it should allow player to place it in a
    straight line in the air at player feet". The block went onto the meadow at the cliff's foot, six levels down."""
    x, y = terrace(game)
    for k in (1, 2):
        assert game.js("Target.target('use')") == {"x": x + k, "y": y, "z": 6, "kind": "place", "ok": True}
        game.press("e", 600)
        game.wait(f"solidAt({x + k}, {y}, 6)", 3000)
        assert not game.js(f"solidAt({x + k}, {y}, 1)")                     # (nothing on the meadow down there)
        if k == 1:
            game.act("step", dir="E"); game.rest()                         # out onto it, on along the line (one tile: a tap of the key walked two on a busy runner, its key let go a frame late)
            assert game.pos() == (x + 1, y)
    assert game.inv("dirt") == 4 and not game.errors


def test_the_pointer_over_the_drop_is_on_the_plane_of_your_level_with_a_block_in_hand(game):
    """With earth in hand the pointer over the drop names the cell at your own level there; with nothing in hand it is
    on the land the pointer shows, as it was (there, none: the air before the cliff)."""
    x, y = terrace(game)
    m = game.js(f"HdLook.screenOf({x + 2.5}, {y + .5}, 6)")
    game.page.mouse.move(m[0], m[1]); game.frames(3)
    q = game.js(f"(() => {{ const q = tileAtScreen({m[0]}, {m[1]}); return [q.x, q.y, clickIntent(q, 'use').it.z]; }})()")
    assert q == [x + 2, y, 6], (q, game.js(f"(() => {{ const p = HdLook.pick({m[0]}, {m[1]}), s = myPos(); return [p && [p.x, p.y, topAt(p.x, p.y)], s && myZ(s.x, s.y)]; }})()"))   # (what the pointer shows past the drop, and your level)
    # (nothing in hand and the read in one task: each observation takes in hand what the hand's slot holds (ui.js handSync),
    # so a tick between two calls put the earth back, one run in some)
    g = game.js(f"(() => {{ selected = null; const q = tileAtScreen({m[0]}, {m[1]}), p = HdLook.pick({m[0]}, {m[1]}); return [q && [q.x, q.y], p && [p.x, p.y]]; }})()")
    # (the land the pointer shows, if any, as the picture names it: never the cell in the air. What lies there is the world's
    # own, past the meadow made for the test: "[-6, -34, 3]", a hill on a runner, where a quick machine had had the meadow)
    assert g[0] == g[1] and g[0] != [x + 2, y], g
    assert not game.errors
