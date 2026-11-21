"""What stands behind higher ground, in Chrome (js/behind.js): a tree, a rock, things dropped are cut at its edge as
anybody is, and show through it in the x-ray circle."""

import pytest

pytestmark = pytest.mark.usefixtures("circle_view")      # (the circle's tests: the view that has it, conftest.py)


def test_a_tree_behind_a_hill_is_hidden_by_it_and_shows_in_the_circle(game):
    """A tree standing behind a hill was drawn over the hill, as if it stood on top of it (only bodies were cut at a
    hill's edge). Now the hill hides it; in the x-ray circle, beside you behind that hill, it shows through."""
    game.clear_area(10)
    game.js("(() => { mouse.in = true; mouse.x = mouse.y = -9999; return 1; })()")   # (no aim drawn: it follows you by keys from the first frame, and the tree beside you is aimed at once it stands)
    game.stamp(-8, 1, ["." * 17] * 3, levels=["6" * 17] * 3); game.rest()       # a wall six layers high right in front of you: its top is drawn over your row
    x, y = game.pos()
    look = lambda x0, x1: game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S), k = DPR, X = Math.round((ox + {x0} * S) * k), Y = Math.round((oy + ({y} - 2) * S) * k);
      return Array.from(ctx.getImageData(X, Y, Math.round(({x1} - {x0}) * S * k), Math.round(3 * S * k)).data); }})()""")
    far, near = (x - 7, x - 5), (x - 2, x - .25)                    # two tiles of your row, and what is drawn over them: out of the circle, and in it beside you
    circle = lambda on: (game.js(f"(() => {{ XRAY.from = {'.5' if on else '9'}; XRAY.full = {'.6' if on else '10'}; return 1; }})()"), game.sleep(700))
    circle(False); bare_far, bare_near = look(*far), look(*near)    # no tree yet
    # (the hill is cut over your own column, XRAY.side 0: "the cut invents shapes", three tiles wide a hill read as a U.
    # A tile each side of you, XRAY.side 1, is the cut this test was written for: what is beside you shows through)
    side = lambda n: (game.js(f"(() => {{ XRAY.side = {n}; return 1; }})()"), game.sleep(700))
    circle(True); seen_near = look(*near); side(1); wide_near = look(*near); side(0)
    game.stamp(-6, 0, ["T....T"]); game.rest()                                   # a tree on each
    assert game.js(f"combAt({x - 6}, {y}) === 'T' && combAt({x - 1}, {y}) === 'T' && tileBehind({x - 6}, {y})")
    assert look(*near) == seen_near                                 # beside your column: behind the hill that stands there
    side(1)
    assert look(*near) != wide_near                                 # in the cut: the tree, through the hill
    side(0)
    assert look(*far) == bare_far                                   # out of it: hidden, as if it were not there
    circle(False)
    assert look(*far) == bare_far and look(*near) == bare_near      # without the circle: both hidden
    assert not game.errors


def test_a_tree_behind_a_ledge_is_cut_at_its_edge(game):
    """Behind a ledge two layers high the foot of a tree is hidden and its crown shows over the ledge."""
    game.clear_area(10)
    game.js("(() => { XRAY.from = 9; XRAY.full = 10; return 1; })()")
    game.stamp(2, 1, ["...."] * 2, levels=["2222"] * 2); game.rest()               # a ledge, east of you: its top is drawn over the row behind it
    x, y = game.pos()
    look = lambda ty, h: game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S), k = DPR;
      return Array.from(ctx.getImageData(Math.round((ox + {x + 3} * S) * k), Math.round((oy + {ty} * S) * k), Math.round(S * k), Math.round({h} * S * k)).data); }})()""")
    foot, crown = look(y + .5, .5), look(y - 1, 1)                  # (the ledge's edge is set in a few px from the top of the tile)
    game.stamp(3, 0, ["T"]); game.rest()
    assert game.js(f"combAt({x + 3}, {y}) === 'T'")
    assert look(y + .5, .5) == foot                                 # its tile: under the ledge's top, as before
    assert look(y - 1, 1) != crown                                  # over the ledge: its crown
    assert not game.errors
