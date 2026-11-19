"""Models (web/js/vox_models.js, models.js): what stands in the land as a few boxes, drawn with the blocks. The
first: a bridge (bridge_model.js), a deck of planks over the water on posts. "blocks such as bridges should be
low-poly modelized"."""

from test_e2e_blocks import blocks

# the colour of the game's canvas at an art px (ax, ay) of the tile (x, y), counted on the flat (no height)
PX = """([x, y, ax, ay]) => { const S = TS(), [ox, oy] = screenOrigin(S), d = ctx.getImageData(Math.round((ox + x * S + (ax + .5) * zoom) * DPR), Math.round((oy + y * S + (ay + .5) * zoom) * DPR), 1, 1).data; return [d[0], d[1], d[2]]; }"""
PLANK, LIT, LINE = [196, 154, 108], [220, 185, 138], [144, 98, 93]      # the pack's bridge sheet: a plank, its lit edge, its line
POND = ["~~~~~~~~~", "~~~~~~~~~", ":::::::::", "~~~~~~~~~", "~~~~~~~~~"]      # a bridge from bank to bank, two rows over you
near = lambda a, b, by=12: all(abs(p - q) <= by for p, q in zip(a, b))


def pond(game):
    x, y = game.pos()
    game.stamp(-4, -6, POND)
    blocks(game)
    return x, y - 4                                              # the bridge's middle tile


def test_a_bridge_is_a_deck_over_the_water(game):
    """Its planks are four px over the water (the flat one's lay on it): the deck's top is drawn four px up the
    picture, its lit front edge and its dark one under it, then the water in its shade; north of it, water."""
    game.flat()                                                  # (it counts the art px of faces north of you: whole px on the flat picture only)
    x, y = pond(game)
    assert game.js("Voxels.engine.models") > 40                  # a box a plank, their fronts, posts
    px = lambda ax, ay, dx=0: game.js(PX, [x + dx, y, ax, ay])
    assert near(px(1, 4), PLANK) and near(px(1, -1), LINE), (px(1, 4), px(1, -1))      # its top: from a px over its tile (the deck's far edge, a line)
    assert near(px(1, 10), LIT) and near(px(1, 11), LINE), (px(1, 10), px(1, 11))      # its front: two px under the top's last row
    shade, open_ = px(1, 13), game.js(PX, [x, y + 1, 1, 13])
    assert not near(shade, PLANK, 30) and sum(shade) < sum(open_) - 20, (shade, open_)   # under it: water, darker than the water south of it
    assert not near(px(1, -3), PLANK, 30) and not near(px(1, -3), LINE, 30)           # north of it: no planks
    # its last planks step down to the bank, a px a plank; a pair of posts stands on the bank at its mouth
    assert game.js(f"BridgeModel.planks({x - 4}, {y}, true)") == [1, 2, 3, 4] and game.js(f"BridgeModel.planks({x + 4}, {y}, true)") == [4, 3, 2, 1]
    assert near(px(-2, 14, dx=-4), PLANK) and near(px(-3, 11, dx=-4), LIT) and near(px(-3, -3, dx=-4), LIT), [px(-2, 14, dx=-4), px(-3, 11, dx=-4), px(-3, -3, dx=-4)]   # the south post's front and top, the north one's top


def test_a_bridge_taken_away_takes_its_model_with_it(game):
    x, y = pond(game)
    n = game.js("Voxels.engine.models")
    game.stamp(-4, -6, ["~" * 9] * 5)
    game.wait("dirtyTiles.length === 0")
    game.sleep(400)
    assert game.js("Voxels.engine.models") < n - 40
    assert not near(game.js(PX, [x, y, 1, 4]), PLANK, 30)


def test_who_stands_on_a_bridge_stands_on_its_deck(game):
    """A body on the bridge is drawn four px higher than on the bank (on the deck, not in it), three on its last
    tile (where the planks step down), and what lies on the bridge too."""
    x, y = pond(game)
    lift = "(() => { const p = ents.get('agent' + myId); return [p.x, p.y, liftOf(p) / zoom]; })()"
    game.rpc("dev_teleport", x=x, y=y)
    game.wait(f"myPos().x === {x} && myPos().y === {y}")
    game.sleep(600)
    assert game.js(lift) == [x, y, 4] and game.js(f"liftAt({x}, {y}) / zoom") == 4
    # (the px under its feet: the deck's planks beside its shadow, not water)
    assert near(game.js(PX, [x, y, 1, 4]), PLANK) or near(game.js(PX, [x, y, 14, 4]), PLANK)
    game.rpc("dev_teleport", x=x - 4, y=y)
    game.wait(f"myPos().x === {x - 4}")
    game.sleep(600)
    assert game.js(lift) == [x - 4, y, 3]
    game.rpc("dev_teleport", x=x - 5, y=y)
    game.wait(f"myPos().x === {x - 5}")
    game.sleep(600)
    assert game.js(lift) == [x - 5, y, 0]


def test_models_cost_little_of_a_frame(game):
    """With a bridge in view, a frame's own work stays small."""
    pond(game)
    game.sleep(500)
    ms = game.js("new Promise((ok) => { const out = [], of = window.frame; window.frame = (now) => { const a = performance.now(); of(now); out.push(performance.now() - a); if (out.length >= 90) { window.frame = of; ok(out); } }; })")
    ms.sort()
    assert ms[len(ms) // 2] < 6 and ms[int(len(ms) * .95)] < 12, ms[-5:]


def test_a_body_is_behind_the_posts_in_front_of_it_and_before_the_ones_behind(game):
    """Bodies are drawn over the land's picture: a bridge's posts were under anybody. What is drawn of a body on the
    deck, two tiles meeting under it, leaves the near side's posts (south of its feet) as they are, and covers the
    far side's (north of them) and the planks it stands on."""
    game.flat()                                                  # (it reads art px of the model north of you)
    x, y = pond(game)
    seen = game.js("""([x, y]) => { const S = TS(), [ox, oy] = screenOrigin(S), sx = (v) => ox + v * S, sy = Curve.sy(oy, S), p = {x: x - .5, y, e: {kind: 'chicken', id: -1}};
      frame(performance.now());
      const px = (ax, ay) => { const d = ctx.getImageData(Math.round((ox + x * S + (ax + .5) * zoom) * DPR), Math.round((oy + y * S + (ay + .5) * zoom) * DPR), 1, 1).data; return [d[0], d[1], d[2]]; };
      const spots = [[-1, 12], [-1, -2], [-6, 4]], was = spots.map((s) => px(...s)), cut = clipModels(p, sx, sy);
      ctx.fillStyle = '#f0f'; ctx.fillRect(ox + (x - 2) * S, oy + (y - 2) * S, 4 * S, 4 * S); if (cut) ctx.restore();
      return [cut, was, spots.map((s) => px(...s))]; }""", [x, y])
    cut, was, now = seen
    assert cut and now[0] == was[0] and near(was[0], [196, 154, 108], 60), seen      # the near post, where two tiles meet: not drawn over
    assert now[1] == [255, 0, 255] and now[2] == [255, 0, 255], seen                  # the far one, and the deck under the body: drawn over
    assert not game.errors


def test_a_click_on_a_plank_picks_the_bridges_tile_at_the_decks_height(game):
    """The deck is four px over the water: its far planks are drawn over the tile north of it. Pointing at any px of
    the deck's top is pointing at the bridge's tile (where its planks step down to the bank too), flat or in the curved world."""
    x, y = pond(game)
    pick = """([x, y, ax, ay]) => { const S = TS(), [ox, oy] = screenOrigin(S), sy = Curve.sy(oy, S), up = liftAt(x, y), q = tileAtScreen(ox + x * S + (ax + .5) * zoom, sy.row(y + (ay + .5) / 16, up) + .5); return [q.x - x, q.y - y]; }"""
    spots = [[x + d, y, ax, ay] for d in (0, -4, 4) for ax, ay in ((1, 0), (9, 3), (9, 8), (14, 13))]
    assert game.js("Curve.on") and [game.js(pick, s) for s in spots] == [[0, 0]] * len(spots)
    game.flat()
    assert [game.js(pick, s) for s in spots] == [[0, 0]] * len(spots)
    assert not game.errors
