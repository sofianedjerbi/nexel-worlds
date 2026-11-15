"""Building: a plan made with a cursor, and your character builds it, block by block (web/js/build.js)."""

SLOT = "(n) => String((slots.indexOf(n) + 1) % 10)"           # the key of the bar's slot that holds it
WALLS = "([x, y, n]) => { let s = ''; for (let i = 0; i < n; i++) s += combAt(x + i, y); return s; }"


def test_a_wall_is_planned_with_a_cursor_and_built_by_keys_alone(game):
    """Placing was the tile you faced, one press a tile: a wall was a step, a turn, a press, again. In build mode
    (B) the arrows move a cursor and not you; Space plans the piece in hand, held while the cursor moves it plans a
    row; your character walks to each plan and builds it; X on something built plans to take it down. No mouse."""
    game.clear_area(8)
    game.give(wood_wall=6)
    x, y = game.pos()
    kb = game.page.keyboard
    game.press(game.js(SLOT, "wood_wall"))                     # the walls in hand, by their number
    game.press("b")
    assert game.js("Build.on && Build.S.at.x") == x and game.js("Build.S.at.y") == y + 1      # the cursor: the tile you face
    game.press("ArrowRight"); game.press("ArrowRight")         # the cursor moves; you do not
    assert game.js("[Build.S.at.x, Build.S.at.y]") == [x + 2, y + 1] and game.pos() == (x, y)
    assert [r[0] for r in game.js("Build.rows()")] == ["Space", "X", "B"] and "wooden wall" in game.js("Build.rows()[0][1]").lower()
    kb.down("Space")                                           # held: a row of four
    for _ in range(3):
        game.press("ArrowRight", 160)
    kb.up("Space")
    assert game.js("Build.S.plans.size") >= 1 or game.js(WALLS, [x + 2, y + 1, 4]) == "WWWW"
    game.wait(f"({WALLS})([{x + 2}, {y + 1}, 4]) === 'WWWW' && Build.S.plans.size === 0", 20000)      # built, one after the other
    assert game.inv("wood_wall") == 2 and game.pos() != (x, y)                                    # you walked to them
    game.press("x")                                            # on the last one built: a plan to take it down
    game.wait(f"combAt({x + 5}, {y + 1}) !== 'W' && Build.S.plans.size === 0", 20000)
    assert game.inv("wood_wall") == 3
    for _ in range(2):                                         # more plans than pieces in your pack: said, not planned
        game.press("ArrowDown", 120)
    kb.down("Space")
    for _ in range(5):
        game.press("ArrowLeft", 140)
    kb.up("Space")
    game.wait("Build.S.plans.size === 0", 20000)
    assert game.inv("wood_wall") == 0 and game.js(WALLS, [x, y + 3, 6]).count("W") == 3
    game.press("Escape")
    assert game.js("Build.on") is False
    game.press("ArrowRight", 500)                              # out of the mode the arrows walk you again
    assert game.js("Build.on") is False and not game.errors
