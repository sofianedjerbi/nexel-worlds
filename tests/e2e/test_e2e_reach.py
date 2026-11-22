"""Build mode in a tunnel: the aimed block's box is a whole line when it can be planned now (air beside it, or a dig
planned beside it: build.js `open`, the rule the work goes by) and dotted when it cannot yet (target.js `outline`
far). The owner, a red dotted box and "X Plan the step before it first" in red: "make a selection hint dotted only for
unreachable blocks and not dotted for reachable blocks (reachable includes the previous planned steps) so it is clear
to the user without adding a stupid 'plan the step before it' hint"."""

import pytest

pytestmark = pytest.mark.e2e

# the cursor on the block (x, y, z): its tile, and the level it rides moved to z (as E and Q move it)
AIM = """([x, y, z]) => { const S = Build.S; S.at = {x, y}; S.plane = null; S.deep = null; const r = Build.level(); if (z > r) S.plane = z; else if (z < r) S.deep = z; return Build.level(); }"""
# its box as drawn the next frames: [dotted, px of whole line, px of dots], and X's row
BOX = """async ([x, y, z]) => { const raf = () => new Promise((r) => requestAnimationFrame(r)); Target.drew = []; for (let i = 0; i < 60 && !Target.drew.length; i++) await raf(); await raf();
  const d = Target.drew.find((c) => c.x === x && c.y === y && c.z === z && c.kind === "break"); const r = Build.rows().find((w) => w[0] === "X");
  return [d ? [d.far, d.line > 0, d.dots > 0] : null, r ? r[1] : null]; }"""


def test_a_box_is_dotted_only_while_its_block_cannot_be_reached_and_whole_once_the_one_before_it_is_planned(game):
    game.clear_area(8)
    game.give(pickaxe=1)
    x, y = game.pos()
    game.stamp(-6, -4, ["." * 13] * 9, levels=["4" * 13] * 9)                          # a hill, four levels
    game.stamp(-6, 0, ["." * 7], levels=["0" * 7], roofs=["4" * 7], heads=["2" * 7])   # a tunnel in it, ending at you
    game.rpc("dev_teleport", x=x, y=y, z=0)
    game.wait(f"myAt && myAt.x === {x} && myAt.z === 0", 8000); game.rest()
    game.face(1, 0); game.js("Build.toggle(true)")
    game.js("(() => { Build.S.working = true; return 1; })()")                     # (the work held: only plans)
    box = lambda dx, z: (game.js(AIM, [x + dx, y, z]), game.js(BOX, [x + dx, y, z]))[1]
    DOTS, WHOLE = [True, False, True], [False, True, False]

    assert box(2, 1) == [DOTS, None]                          # two blocks into the rock at your legs: dotted, nothing said
    game.press("x", 120)
    assert game.js("Build.S.plans.size") == 0 and game.toast() == ""     # (X on it: nothing)
    # the one in front of your legs, then a staircase three down and two up, block by block: each next block is
    # dotted till the one before it is planned (but the first up: the step down beside it already opened it), whole right after
    chain = [(1, 1), (1, 0), (2, 0), (2, -1), (3, -1), (3, -2), (4, -1), (4, 0), (5, 0), (5, 1)]
    for k, c in enumerate(chain):
        nxt = chain[k + 1] if k + 1 < len(chain) else None
        if nxt and nxt != (4, -1):
            assert box(*nxt) == [DOTS, None], (k, nxt)
        assert box(*c) == [WHOLE, "Break"], (k, c)
        game.press("x", 120)
        assert game.js("Build.S.plans.size") == k + 1, (k, c)
        if nxt:
            assert box(*nxt) == [WHOLE, "Break"], (k, nxt)
        if k == 0:
            assert box(2, 1) == [WHOLE, "Break"]              # ...and the one behind the first is whole now too
    assert "Plan the step" not in game.actions()
    assert not game.errors
