"""Building: crafting with the keyboard, placing things in front of you, structures, farming, containers."""


def craft_with_keys(game, recipe):
    """Open crafting (C), find the recipe (each kind in turn, down its names page after page), Enter."""
    game.press("c", 400)
    for _ in range(8):
        seen = set()
        while game.js("craftFocus") != recipe and game.js("craftFocus") not in seen:
            seen.add(game.js("craftFocus"))
            game.press("ArrowDown", 60)
        if game.js("craftFocus") == recipe:
            break
        game.press("e", 100)
    assert game.js("craftFocus") == recipe
    game.press("Enter", 1200)
    game.press("Escape", 200)


def test_craft_and_place_a_workbench_by_keyboard(game):
    game.give(wood=4)
    craft_with_keys(game, "workbench")
    assert game.inv("workbench") == 1 and game.inv("wood") == 0
    game.hold_item("workbench")
    game.face(0, -1)
    assert "Place workbench" in game.actions()
    assert game.js("aimedTile().it.ghost") == "workbench"    # the ghost shows where it goes
    game.press("e", 800)
    assert game.tile(0, -1) == "&"


def test_cant_place_on_things_and_says_why(game):
    game.give(fence=2)
    game.stamp(1, 0, ["t"])                                  # a stump in the way
    game.hold_item("fence")
    game.face(1, 0)
    assert "Can't place fence here" in game.actions()
    game.press("e", 300)
    assert "Can't place" in game.toast() and game.tile(1, 0) == "t"
    game.spawn("chicken", 0, -1, still=10 ** 6)
    game.face(0, -1)
    game.sleep(300)
    assert "Something is in the way" in game.actions()


def test_structures_grow_away_from_you_and_come_down_whole(game):
    game.give(well=1, pickaxe=1)
    game.hold_item("well")
    game.face(0, 1)                                          # facing south: the well goes south, not onto you
    game.press("e", 1200)
    tiles = [game.tile(dx, dy) for dy in (1, 2) for dx in (0, 1)]
    assert sorted(tiles) == ["Y", "Z", "Z", "Z"]
    game.hold_item("pickaxe")
    game.face(0, 1)
    game.press("x", 0)                                       # X: take it down
    game.wait(f"combAt({game.pos()[0]}, {game.pos()[1] + 2}) === '.'", 8000)
    assert all(game.tile(dx, dy) == "." for dy in (1, 2) for dx in (0, 1)) and game.inv("well") == 1


def test_farming_hoe_seed_water_harvest(game):
    game.give(hoe=1, seed=1, watering_can=1)
    game.face(1, 0)
    game.hold_item("hoe")
    assert "Till soil" in game.actions()
    game.press("e", 1200)
    assert game.tile(1, 0) == "o"
    game.hold_item("seed")
    game.press("e", 800)
    assert game.tile(1, 0) == ";"
    game.hold_item("watering_can")
    game.press("e", 1500)
    x, y = game.pos()
    assert game.js(f"gndAt({x + 1}, {y})") == "u"           # watered soil
    game.rpc("dev_skip", seconds=230)
    game.sleep(800)
    assert game.tile(1, 0) == "w"                            # ripe
    game.press("0", 200)                                     # empty hands: harvest
    game.press("e", 1000)
    assert game.tile(1, 0) == "o" and game.inv("seed") >= 2


def test_tilling_needs_a_hoe(game):
    """Without a hoe nothing is tilled; and X does not answer "Needs a hoe" in red: X digs the tile down, by hand too."""
    x, y = game.pos()
    game.face(1, 0)
    assert "hoe" not in game.js("intent(facingTile(), true).text")           # (asked of that tile alone: tilling is E's, with a hoe)
    assert game.js("facingNow(true).it.text") == "Dig down"
    game.press("x", 100)
    game.wait(f"topAt({x + 1}, {y}) === -1 && !myAction", 20000)
    assert game.tile(1, 0) == "." and "hoe" not in game.toast()


def test_paths_and_planks(game):
    game.give(path=1, plank=1)
    game.hold_item("path")
    game.face(1, 0)
    game.press("e", 700)
    x, y = game.pos()
    assert game.js(f"gndAt({x + 1}, {y})") == "_"
    game.hold_item("plank")
    game.face(-1, 0)
    game.press("e", 700)
    assert game.js(f"gndAt({x - 1}, {y})") == "n"


def test_chest_store_and_take(game):
    game.give(chest=1, stone=5)
    game.hold_item("chest")
    game.face(1, 0)
    game.press("e", 800)
    game.hold_item("stone")
    assert "Store in chest" in game.actions()
    game.press("e", 800)
    assert game.inv("stone") == 0
    game.press("0", 200)
    game.press("e", 800)                                 # empty hands: open (take out)
    assert game.inv("stone") == 5
