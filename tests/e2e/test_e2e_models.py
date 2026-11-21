"""Models (models.js): what stands in the land as a few boxes, drawn with the blocks by the HD look. The first: a
bridge (bridge_model.js), a deck of planks over the water on posts. "blocks such as bridges should be low-poly
modelized"."""

import pytest

POND = ["~~~~~~~~~", "~~~~~~~~~", ":::::::::", "~~~~~~~~~", "~~~~~~~~~"]      # a bridge from bank to bank, two rows over you


def pond(game):
    x, y = game.pos()
    game.stamp(-4, -6, POND)
    game.rest()
    return x, y - 4                                              # the bridge's middle tile


def test_a_bridges_last_planks_step_down_to_the_bank(game):
    """Its last planks step down to the bank, a px a plank, at both ends."""
    x, y = pond(game)
    assert game.js(f"BridgeModel.planks({x - 4}, {y}, true)") == [1, 2, 3, 4] and game.js(f"BridgeModel.planks({x + 4}, {y}, true)") == [4, 3, 2, 1]
    assert game.js(f"Models.at({x}, {y})") and not game.errors          # (the deck: boxes in the land)


@pytest.mark.realtime
def test_models_cost_little_of_a_frame(game):
    """With a bridge in view, a frame's own work stays small."""
    pond(game)
    game.sleep(500)
    ms = game.js("new Promise((ok) => { const out = [], of = window.frame; window.frame = (now) => { const a = performance.now(); of(now); out.push(performance.now() - a); if (out.length >= 90) { window.frame = of; ok(out); } }; })")
    ms.sort()
    assert ms[len(ms) // 2] < 6 and ms[int(len(ms) * .95)] < 12, ms[-5:]


def test_a_click_on_the_bridge_picks_the_bridges_tile(game):
    """Pointing at the middle of the bridge's tile, as the HD look draws it, is pointing at the bridge's tile (where its
    planks step down to the bank too)."""
    x, y = pond(game)
    pick = """([x, y]) => { const c = Voxels.host.column(x, y), a = HdLook.screenOf(x + .5, y + .5, c[c.length - 1]), q = tileAtScreen(a[0], a[1]); return [q.x - x, q.y - y]; }"""      # (the middle of the tile's top as the HD look has it)
    assert [game.js(pick, [x + d, y]) for d in (0, -4, 4)] == [[0, 0]] * 3
    assert not game.errors
