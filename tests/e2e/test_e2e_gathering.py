"""Gathering: picking plants, chopping trees, mining, stumps, regrowth, and aiming at things with keys and mouse."""

import time

SCREEN = "([x, y]) => { const r = cv.getBoundingClientRect(), a = HdLook.screenOf(x + .5, y + .5, topAt(x, y)); return [r.left + a[0], r.top + a[1]]; }"      # (the middle of a tile's top, as the HD look draws it)


def click_tile(game, dx, dy, shift=False):
    x, y = game.pos()
    sx, sy = game.js(SCREEN, [x + dx, y + dy])
    game.page.mouse.move(sx, sy)
    if shift:
        game.page.keyboard.down("Shift")
    game.page.mouse.click(sx, sy)
    if shift:
        game.page.keyboard.up("Shift")


def test_flowers_around_and_under_you(game):
    game.stamp(1, 1, ["f"])
    game.stamp(0, 0, ["f"])                                  # one under your feet too
    game.press("e", 500)                                 # underfoot first
    assert game.tile(0, 0) == "." and game.inv("flower") == 1
    game.press("e", 500)                                 # then the diagonal one
    assert game.tile(1, 1) == "." and game.inv("flower") == 2
    assert game.actions() == game.js("capOf('alt')") + " | Dig down"   # nothing left to pick here (the break key by hand digs down, as anywhere: the key over A since 24dae98, Q on this QWERTY, not X)


def test_space_never_stops_you(game):
    game.stamp(2, -1, ["f"])
    game.stamp(4, -1, ["T"])
    game.page.keyboard.down("d")
    game.sleep(150)
    game.press("e", 250)                                     # E on the flower: picked in passing
    moving = game.js("walking !== null")
    game.sleep(300)
    assert moving and game.inv("flower") == 1
    x0, _ = game.pos()
    game.page.keyboard.down("x")                             # X by the tree: chopping waits, you walk on
    game.sleep(500)
    x1, _ = game.pos()
    moving = game.js("walking !== null")
    game.page.keyboard.up("x")
    game.page.keyboard.up("d")
    assert moving and x1 >= x0 + 2 and game.server()["x"] >= x0 + 2


def test_a_click_picks_on_the_move(game):
    game.stamp(3, -1, ["f"])
    fx, fy = game.pos()[0] + 3, game.pos()[1] - 1
    game.page.keyboard.down("d")
    game.sleep(200)
    sx, sy = game.js(SCREEN, [fx, fy])                       # (the flower's own tile: you are moving, your tile is changing)
    game.page.mouse.click(sx, sy)                            # a click on the flower while walking...
    game.sleep(150)
    moving = game.js("walking !== null")
    game.page.keyboard.up("d")
    game.sleep(400)
    assert moving and game.inv("flower") >= 1                # ...picks it without stopping you


def test_chop_by_hand_and_with_an_axe(game):
    game.stamp(1, 0, ["T"])
    game.face(1, 0)
    assert "Chop tree (slow)" in game.actions()                # (a verb and a thing: "interaction sentences are wayyyy too long")
    t0 = time.time()
    game.press("x", 0)
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === 't'", 8000)
    by_hand = time.time() - t0
    assert game.inv("wood") == 3
    game.press("x", 0)                                   # the stump: one more wood
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === '.'", 8000)
    assert game.inv("wood") == 4
    game.give(axe=1)
    game.hold_item("axe")
    game.stamp(1, 0, ["T"])
    assert "Chop tree" in game.actions() and "(slow)" not in game.actions()
    t0 = time.time()
    game.press("x", 0)
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === 't'", 8000)
    assert time.time() - t0 < by_hand / 2


def test_rocks_and_ore(game):
    game.stamp(1, 0, ["*"])
    game.face(1, 0)
    assert "pickaxe" in game.actions() or "pickaxe" in game.js("intent(facingTile(), true).text")
    game.press("x", 400)
    assert game.tile(1, 0) == "*"                            # ore can't be mined without a pickaxe in hand
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.press("x", 0)
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === '.'", 8000)
    assert game.inv("ore") == 1 and game.inv("stone") >= 1


def test_bushes_and_fruit_trees_stay_and_bear_again(game):
    game.stamp(1, 0, ["b"])
    game.stamp(-1, 0, ["F"])
    game.face(1, 0)
    game.press("e", 600)
    assert game.tile(1, 0) == "v" and game.inv("berries") == 2
    game.face(-1, 0)
    game.press("e", 1500)
    assert game.tile(-1, 0) == "U" and game.inv("fruit") == 3
    game.rpc("dev_skip", seconds=250)
    game.sleep(800)
    assert game.tile(1, 0) == "b" and game.tile(-1, 0) == "F"


def test_clicking_a_tree_crown_means_the_tree(game):
    game.stamp(2, 1, ["T"])                                  # (within reach: a circle of two tiles and a half round you)
    x, y = game.pos()
    sx, sy = game.js(SCREEN, [x + 2, y])                     # the tile above the trunk, under the crown
    game.page.mouse.move(sx, sy)
    game.sleep(200)
    assert "Chop tree" in game.js("$('hover').innerText")
    game.page.mouse.click(sx, sy)
    game.wait(f"combAt({x + 2}, {y + 1}) === 't'", 9000)


def test_too_far_is_too_far(game):
    game.stamp(4, 0, ["M"])
    click_tile(game, 4, 0)
    game.sleep(300)
    assert "Too far" in game.toast() and game.tile(4, 0) == "M"
    assert game.pos() == (game.server()["x"], game.server()["y"])   # and nothing walked you there


def test_what_is_up_a_cliff_is_out_of_reach(game):
    """Reach is a circle round you and height is distance too (a layer is half a tile): a flower on a pillar in front
    of you, six layers up, is three tiles above you. It is not offered, and Space does nothing and says nothing (it
    said "Out of reach" in red: what your hand cannot get to is not spoken of, the picture shows the cliff); two
    layers up, you pick it. A flower two tiles off and one across is within the circle; two and two is its corner."""
    game.clear_area(8)
    game.stamp(0, -1, ["f"], levels=["6"])
    game.face(0, -1)
    game.sleep(500)
    assert not any("flower" in r[1].lower() for r in game.js("availableActions()"))
    game.press("e", 400)
    assert game.tile(0, -1) == "f" and "Out of reach" not in game.js("$('toastt').textContent") and "reach" not in game.actions()
    game.stamp(0, -1, ["f"], levels=["2"]); game.rest()
    assert any("flower" in r[1].lower() for r in game.js("availableActions()"))
    game.press("e", 500)
    assert game.tile(0, -1) != "f" and game.inv("flower") == 1
    x, y = game.pos()
    assert game.js(f"[reaches({x + 2}, {y + 1}, USE_R), reaches({x + 2}, {y + 2}, USE_R), reaches({x + 1}, {y}, USE_R, myZ({x}, {y}) + 5)]") == [True, False, False]
    assert not game.errors
