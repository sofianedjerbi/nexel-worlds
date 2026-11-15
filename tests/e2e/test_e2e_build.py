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
    rows = game.js("Build.rows()")                             # the corner: the mode's name, and only the keys that do something here
    assert [r[0] for r in rows] == ["B", "Space"] and "BUILD" in rows[0][1] and rows[1][1] == "Plan wooden wall"
    assert all(len(r[1]) <= 26 for r in rows)                  # (short: a long line ran under the bar)
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


ROW = "([x, y, n]) => { let s = ''; for (let i = 0; i < n; i++) s += Structures.roofAt(x + i, y) ? 'r' : '.'; return s; }"


def test_a_roof_is_laid_a_tile_at_a_time_and_seen_through_from_under_it(game):
    """A roof came by itself, whole, the moment walls closed a room. It is a piece like the rest (a `roof`, from
    wood): laid on a wall or beside a roof tile, planned with the cursor, taken back with X; and whoever stands
    under a roof sees through all of it."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(2, -3, ["WWWW", "W..W", "WW+W"])               # walls and a door, no roof: nothing draws one by itself
    game.sleep(700)
    assert game.js("ROOFS") is True and game.js(ROW, [x + 2, y - 3, 4]) == "...."
    game.give(roof=6)
    kb = game.page.keyboard
    game.press(game.js(SLOT, "roof"))
    game.press("b")
    for k in ["ArrowRight"] * 2 + ["ArrowUp"] * 6:             # the cursor in the open: no roof hangs in the air
        game.press(k, 110)
    assert game.js("Build.hint(Build.S.at).ok") is False and "wall" in game.js("Build.hint(Build.S.at).text")
    game.press("ArrowDown", 110)
    game.press("ArrowDown", 110)                               # on the north wall: a row of four
    kb.down("Space")
    for _ in range(3):
        game.press("ArrowRight", 130)
    kb.up("Space")
    game.wait(f"({ROW})([{x + 2}, {y - 3}, 4]) === 'rrrr' && Build.S.plans.size === 0", 30000)
    assert game.inv("roof") == 2
    game.press("ArrowDown", 130)                               # beside those, over the room: two more
    game.press("ArrowLeft", 130)
    kb.down("Space"); game.press("ArrowLeft", 130); kb.up("Space")
    game.wait(f"({ROW})([{x + 2}, {y - 2}, 4]) === '.rr.' && Build.S.plans.size === 0", 30000)
    game.press("x")                                            # the last one planned: taken back off
    game.wait(f"({ROW})([{x + 2}, {y - 2}, 4]) === '..r.' && Build.S.plans.size === 0", 30000)
    assert game.inv("roof") == 1
    game.press("b")
    assert game.js("([x, y]) => [Structures.seeThrough(x + 4, y - 2), Structures.seeThrough(x + 2, y - 3)]", [x, y]) == [1, 1]      # from outside: all of it
    assert game.server()["sheltered"] is False
    game.rpc("dev_teleport", x=x + 4, y=y - 2)                 # under it
    game.sleep(900)
    assert game.server()["sheltered"] is True and not game.errors
    assert game.js("([x, y]) => [Structures.seeThrough(x + 4, y - 2), Structures.seeThrough(x + 2, y - 3)]", [x, y]) == [.12, .12]  # from under it: seen through, the whole roof


def test_what_the_audit_of_build_mode_found_is_mended(game):
    """Played through and looked at, build mode had these faults: leaving it threw the plans away while its key said
    "Done"; nothing said B existed; a door needed the wall taken down first; Q went through food and tools; the X
    line showed over bare grass; a held arrow started late; the mouse was not the cursor. Each, mended."""
    game.clear_area(8)
    game.give(wood_wall=6, door=1, berries=2, axe=1)
    x, y = game.pos()
    kb = game.page.keyboard
    game.press(game.js(SLOT, "wood_wall"))
    assert ["B", "Build mode: plan a lot"] in game.js("availableActions()")           # a piece in hand: B is said
    game.press("b")
    assert [r[0] for r in game.js("Build.rows()")] == ["B", "Space"]                   # nothing built here: no X line
    kb.down("ArrowRight"); game.sleep(700); kb.up("ArrowRight")                        # an arrow held: at once, then at the cursor's own pace
    assert game.js("Build.S.at.x") - x >= 5
    game.js(f"Build.S.at = {{x: {x + 3}, y: {y + 1}}}")
    kb.down("Space")
    for _ in range(3):
        game.press("ArrowRight", 120)
    kb.up("Space")
    game.press("b")                                            # out of the mode at once: the plans wait where they are
    left = game.js("Build.S.plans.size")
    assert left >= 2 and ["B", f"Build: {game.js('Build.waiting()')} plans wait"] in game.js("availableActions()")
    game.sleep(1500)
    assert game.js("Build.S.plans.size") >= left - 1           # (nothing is built while you are out of it, but the one begun)
    game.press("b")                                            # back in: the work goes on
    game.wait(f"({WALLS})([{x + 3}, {y + 1}, 4]) === 'WWWW' && Build.S.plans.size === 0", 25000)
    game.js(f"Build.S.at = {{x: {x + 6}, y: {y + 1}}}")         # (the cursor on the last wall: coming back in, it is at the tile you face)
    game.press("q"); game.sleep(150)                           # Q: the next piece of the bar, not the berries nor the axe
    assert game.js("selected") == "door"
    game.press("q"); game.sleep(150)
    assert game.js("selected") == "wood_wall"
    game.press("q"); game.sleep(150)                           # a door, on the last wall: planned in its place
    rows = game.js("Build.rows()")
    assert rows[1][1] == "Plan door in its place" and ["X", "Take down wooden wall"] in rows
    game.press("Space")
    game.wait(f"combAt({x + 6}, {y + 1}) === '+' && Build.S.plans.size === 0", 25000)
    assert game.inv("wood_wall") == 3 and game.inv("door") == 0                        # (the wall is back in your pack)
    for k in ["ArrowDown", "ArrowDown"]:
        game.press(k, 120)
    game.press(game.js(SLOT, "wood_wall"))
    kb.down("Space"); game.press("ArrowLeft", 120); kb.up("Space")
    game.press("Escape")                                       # Esc: the plans are dropped; again: out of the mode
    assert game.js("Build.S.plans.size") <= 1 and game.js("Build.on") is True
    game.wait("Build.S.plans.size === 0", 20000)
    game.press("Escape")
    assert game.js("Build.on") is False
    game.press("b")                                            # the mouse: the cursor is where it points, and the label says what a click plans
    box = game.js("(() => { const r = cv.getBoundingClientRect(); return [r.left + r.width / 2 + 3 * TS(), r.top + r.height / 2 - 2 * TS()]; })()")
    game.page.mouse.move(box[0] - 20, box[1]); game.page.mouse.move(box[0], box[1])
    game.sleep(200)
    me = game.pos()
    assert game.js("[Build.S.at.x, Build.S.at.y]") == [me[0] + 3, me[1] - 2] and game.js("$('hover').textContent") == "Plan wooden wall"
    game.press("b")
    assert not game.errors
