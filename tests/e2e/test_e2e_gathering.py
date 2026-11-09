"""Gathering: picking plants, chopping trees, mining, stumps, regrowth, and aiming at things with keys and mouse."""

import time

SCREEN = "([x, y]) => { const S = TS(), [ox, oy] = screenOrigin(S); return [ox + x * S + S / 2, oy + y * S + S / 2]; }"


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
    game.press("Space", 500)                                 # underfoot first
    assert game.tile(0, 0) == "." and game.inv("flower") == 1
    game.press("Space", 500)                                 # then the diagonal one
    assert game.tile(1, 1) == "." and game.inv("flower") == 2
    assert game.actions() == ""                              # nothing left to do here


def test_space_never_stops_you(game):
    game.stamp(2, -1, ["f"])
    game.stamp(4, -1, ["T"])
    game.page.keyboard.down("d")
    game.sleep(150)
    game.press(" ", 250)                                     # Space on the flower: picked in passing
    moving = game.js("walking !== null")
    game.sleep(300)
    assert moving and game.inv("flower") == 1
    x0, _ = game.pos()
    game.page.keyboard.down(" ")                             # Space by the tree: chopping waits, you walk on
    game.sleep(500)
    x1, _ = game.pos()
    moving = game.js("walking !== null")
    game.page.keyboard.up(" ")
    game.page.keyboard.up("d")
    assert moving and x1 >= x0 + 2 and game.server()["x"] >= x0 + 2


def test_a_click_picks_on_the_move(game):
    game.stamp(3, -1, ["f"])
    fx, fy = game.pos()[0] + 3, game.pos()[1] - 1
    game.page.keyboard.down("d")
    game.sleep(200)
    x, y = game.pos()
    click_tile(game, fx - x, fy - y)                         # a click on the flower while walking...
    game.sleep(150)
    moving = game.js("walking !== null")
    game.page.keyboard.up("d")
    game.sleep(400)
    assert moving and game.inv("flower") >= 1                # ...picks it without stopping you


def test_chop_by_hand_and_with_an_axe(game):
    game.stamp(1, 0, ["T"])
    game.face(1, 0)
    assert "Chop tree by hand (slow)" in game.actions()
    t0 = time.time()
    game.press("Space", 0)
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === 't'", 8000)
    by_hand = time.time() - t0
    assert game.inv("wood") == 3
    game.press("Space", 0)                                   # the stump: one more wood
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === '.'", 8000)
    assert game.inv("wood") == 4
    game.give(axe=1)
    game.hold_item("axe")
    game.stamp(1, 0, ["T"])
    assert "with axe" in game.actions()
    t0 = time.time()
    game.press("Space", 0)
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === 't'", 8000)
    assert time.time() - t0 < by_hand / 2


def test_rocks_and_ore(game):
    game.stamp(1, 0, ["*"])
    game.face(1, 0)
    assert "pickaxe" in game.actions() or "pickaxe" in game.js("intent(facingTile(), false).text")
    game.press("Space", 400)
    assert game.tile(1, 0) == "*"                            # ore can't be mined without a pickaxe in hand
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.press("Space", 0)
    game.wait(f"combAt({game.pos()[0] + 1}, {game.pos()[1]}) === '.'", 8000)
    assert game.inv("ore") == 1 and game.inv("stone") >= 1


def test_bushes_and_fruit_trees_stay_and_bear_again(game):
    game.stamp(1, 0, ["b"])
    game.stamp(-1, 0, ["F"])
    game.face(1, 0)
    game.press("Space", 600)
    assert game.tile(1, 0) == "v" and game.inv("berries") == 2
    game.face(-1, 0)
    game.press("Space", 1500)
    assert game.tile(-1, 0) == "U" and game.inv("fruit") == 3
    game.rpc("dev_skip", seconds=250)
    game.sleep(800)
    assert game.tile(1, 0) == "b" and game.tile(-1, 0) == "F"


def test_clicking_a_tree_crown_means_the_tree(game):
    game.stamp(2, 2, ["T"])
    x, y = game.pos()
    sx, sy = game.js(SCREEN, [x + 2, y + 1])                 # the tile above the trunk, under the crown
    game.page.mouse.move(sx, sy)
    game.sleep(200)
    assert "Chop tree" in game.js("$('hover').innerText")
    game.page.mouse.click(sx, sy)
    game.wait(f"combAt({x + 2}, {y + 2}) === 't'", 9000)


def test_too_far_is_too_far(game):
    game.stamp(4, 0, ["M"])
    click_tile(game, 4, 0)
    game.sleep(300)
    assert "Too far" in game.toast() and game.tile(4, 0) == "M"
    assert game.pos() == (game.server()["x"], game.server()["y"])   # and nothing walked you there
