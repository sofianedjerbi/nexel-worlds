"""Building: a plan made with a cursor, and your character builds it, block by block (web/js/build.js)."""

import pytest

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
    assert [r[0] for r in rows] == ["Z", "Space", "Q E", "X"] and "BUILD" in rows[0][1] and rows[1][1] == "Place wooden wall"     # (Q E: the cursor a floor down, up)
    assert rows[3][1] == "Break"                          # (X on bare ground: a hole)
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


ROW = "([x, y, n]) => { let s = ''; for (let i = 0; i < n; i++) s += (Floors.get(x + i, y, 3) || [])[0] === 'roof' ? 'r' : '.'; return s; }"


def test_a_roof_is_laid_a_block_at_a_time_and_seen_through_from_under_it(game):
    """A roof came by itself, whole, the moment walls closed a room; then it was a tile laid over a tile by a rule of
    its own. It is a block like the rest (a `roof`, from wood): a storey up, on a wall or beside a block, planned
    with the cursor (with a roof in hand, over what the cursor is on), taken back with X; and whoever stands under
    it sees through all of it."""
    game.js("setOpt('above', 'circle')")                       # (the view that fades what is over you: test_e2e_views.py has the rest)
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(2, -3, ["WWWW", "W..W", "WW+W"]); game.rest()               # walls and a door, no roof: nothing draws one by itself
    assert game.js("FLOORS") is True and game.js(ROW, [x + 2, y - 3, 4]) == "...."
    # what was wrong in the clip: a door that looked like a window in hand and as a plan, a floor that let the grass through
    assert game.js("objectSprite('+', 0, 0, 0)[0] === IMG.door && fullIcon('door') !== fullIcon('wood_wall')")
    game.stamp(-3, 2, ["nn"]); game.rest()
    solid = game.js("""([x, y]) => { const [b, i] = tileIdx(x, y), o = (i / B | 0) * 16 * BW + (i % B) * 16; let n = 0, green = 0;
      for (let j = 0; j < 16; j++) for (let k = 0; k < 16; k++) { const v = b.px[o + j * BW + k]; if (v >>> 24 === 255) n++; if ((v & 0xffffff) === (112 << 16 | 212 << 8 | 192)) green++; } return [n, green]; }""", [x - 3, y + 2])
    assert solid == [256, 0], solid                            # a floor tile: solid all over, no grass in it
    game.stamp(-3, 2, [".."])
    game.give(roof=7)                                          # (one left in hand: with a roof in hand X is about roofs)
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
    assert game.inv("roof") == 3
    game.press("ArrowDown", 130)                               # beside those, over the room: two more
    game.press("ArrowLeft", 130)
    kb.down("Space"); game.press("ArrowLeft", 130); kb.up("Space")
    game.wait(f"({ROW})([{x + 2}, {y - 2}, 4]) === '.rr.' && Build.S.plans.size === 0", 30000)
    game.press("x")                                            # the last one planned: taken back off
    game.wait(f"({ROW})([{x + 2}, {y - 2}, 4]) === '..r.' && Build.S.plans.size === 0", 30000)
    assert game.inv("roof") == 2
    game.press("b")
    game.rpc("dev_teleport", x=x, y=y); game.arrive()                         # (the work may have left you under it: reach counts height)
    assert game.js("([x, y]) => [Floors.alpha(x + 4, y - 2, 3), Floors.alpha(x + 2, y - 3, 3)]", [x, y]) == [1, 1]      # from outside: all of it
    assert game.server()["sheltered"] is False
    game.rpc("dev_teleport", x=x + 4, y=y - 2, z=0); game.arrive()            # under it (on the ground: without a height you are set down on top, on the roof)
    assert game.server()["sheltered"] is True and not game.errors
    assert game.js("([x, y]) => [Floors.alpha(x + 4, y - 2, 3), Floors.alpha(x + 2, y - 3, 3)]", [x, y]) == [.12, .12]  # from under it: seen through, the whole roof
    assert game.server()["z"] == 0 and game.js(f"solidAt({x + 4}, {y - 2}, 3) && !solidAt({x + 4}, {y - 2}, 2)")      # a block: it can be stood on


@pytest.mark.realtime
def test_what_the_audit_of_build_mode_found_is_mended(game):
    """Played through and looked at, build mode had these faults: leaving it threw the plans away while its key said
    "Done"; nothing said B existed; a door needed the wall taken down first; Q went through food and tools; the X
    line showed over bare grass; a held arrow started late; the mouse was not the cursor. Each, mended."""
    game.clear_area(8)
    game.give(wood_wall=6, door=1, berries=2, axe=1)
    x, y = game.pos()
    kb = game.page.keyboard
    game.press(game.js(SLOT, "wood_wall"))
    assert ["Z", "Build mode: plan a lot"] in game.js("availableActions()")           # a piece in hand: B is said
    game.press("b")
    assert game.js("Build.rows()")[3] == ["X", "Break"]                           # nothing built here: X digs
    kb.down("ArrowRight"); game.sleep(700); kb.up("ArrowRight")                        # an arrow held: at once, then at the cursor's own pace
    assert game.js("Build.S.at.x") - x >= 5
    game.js(f"Build.S.at = {{x: {x + 3}, y: {y + 1}}}")
    kb.down("Space")
    for _ in range(3):
        game.press("ArrowRight", 120)
    kb.up("Space")
    game.press("b")                                            # out of the mode at once: the plans wait where they are
    left = game.js("Build.S.plans.size")
    assert left >= 2 and ["Z", f"Build: {game.js('Build.waiting()')} plans wait"] in game.js("availableActions()")
    game.sleep(1500)
    assert game.js("Build.S.plans.size") >= left - 1           # (nothing is built while you are out of it, but the one begun)
    game.press("b")                                            # back in: the work goes on
    game.wait(f"({WALLS})([{x + 3}, {y + 1}, 4]) === 'WWWW' && Build.S.plans.size === 0", 25000)
    game.js(f"Build.S.at = {{x: {x + 6}, y: {y + 1}}}")         # (the cursor on the last wall: coming back in, it is at the tile you face)
    game.press(game.js(SLOT, "door")); game.sleep(150)         # (Q went to the next piece: Q and E are the floors now; the bar's numbers)
    assert game.js("selected") == "door"                       # a door, on the last wall: planned in its place
    rows = game.js("Build.rows()")
    assert rows[1][1] == "Place door in its place" and ["X", "Break wooden wall"] in rows
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
    assert game.js("[Build.S.at.x, Build.S.at.y]") == [me[0] + 3, me[1] - 2] and game.js("$('hover').textContent") == "Place wooden wall"
    game.press("b")
    assert not game.errors


def test_walls_are_thin_and_hide_nothing_and_a_side_door_has_its_leaf_and_shadow(game):
    """Walls were blocks a tile high: their tops hid the row behind them, were seen through near you to make up for
    it ("xray that trigger without roof"), and a gap in a wall running north showed as a patch of planks ("weird
    wall connexion"). A wall is thin and drawn on its own tile: the ground of the tile north of one is as it is, a
    gap is a gap, nothing of a wall is ever seen through. A door in a run going north is seen from above: its leaf
    between two posts, the doorway's shadow under it (the dark of the game's holes); it opens for whoever is by it."""
    game.clear_area(8)
    x, y = game.pos()
    try:
        game.stamp(3, -3, ["W", "+", "W"])                         # a run going north, a door in its middle
        game.stamp(-3, -3, ["W+W"])                                # one in a run going east: the door from the front
        game.stamp(-4, 2, ["WWW"]); game.rest()                                 # and a wall south of open ground
        assert game.js("([x, y]) => [Structures.sideDoor(x + 3, y - 2), Structures.sideDoor(x - 2, y - 3), Structures.sideDoor(x + 3, y - 3)]", [x, y]) == [True, False, False]
        lum = "([dx, dy, up]) => { const t = TS(), d = ctx.getImageData(Math.round(cv.width / 2 + dx * t), Math.round(cv.height / 2 + (dy - up) * t), 1, 1).data; return d[0] + d[1] + d[2]; }"
        grass = game.js(lum, [6, -2, 0])
        game.wait(f"({lum})([3, -2, .25]) < {grass - 150}", 5000)  # (on a busy machine the stamped tiles take a few frames)
        assert game.js(lum, [3, -2, .25]) < grass - 150 and game.js(lum, [2.78, -2, .25]) < grass - 60     # the leaf across the way; its shadow beside it, on the ground
        assert abs(game.js(lum, [-3, 1, 0]) - grass) < 40          # the tile north of a wall: its ground, nothing over it
        game.rpc("dev_teleport", x=x - 3, y=y + 1); game.arrive()                 # standing there, behind the wall: nothing of it is seen through
        px = game.js("(() => { const d = ctx.getImageData(Math.round(cv.width / 2 + TS() * .3), Math.round(cv.height / 2 + TS()), 1, 1).data; return [d[0], d[1], d[2]]; })()")
        assert px in ([170, 121, 89], [144, 98, 93], [220, 185, 138]), px       # the wall just south of you: its planks' own colours, not thinned
        # a lower corner is joined as an upper one is: where a wall comes down onto a front, its band runs into the
        # front's cap (there was the cap's dark line across it: "lower corners should be linked to upper")
        game.rpc("dev_stamp", x=x - 4, y=y + 4, rows=["W..", "WWW"])          # (a place in the world: you are no longer where you woke)
        game.rpc("dev_teleport", x=x - 3, y=y + 4); game.arrive()
        join = game.js("(() => { const t = TS(), z = t / 16, d = ctx.getImageData(Math.round(cv.width / 2 - t + 7.5 * z - t / 2), Math.round(cv.height / 2 + t - t / 2 - 3.5 * z), 1, 1).data; return [d[0], d[1], d[2]]; })()")
        assert join == [196, 154, 108], join                       # the cap's own colour where the band meets it, not its outline
        game.rpc("dev_teleport", x=x + 3, y=y - 2); game.arrive()                 # in the doorway: its leaf is back against a post
        game.settle("doors.get(myPos().x + ',' + myPos().y) === 1")              # (it swings open over a few frames: read when it has; it was read at 0.9, one run in ten on a busy machine)
        assert game.js("doors.get(myPos().x + ',' + myPos().y)") == 1 and not game.errors
    finally:                                                   # (the land as it was, whatever happened: a door left there is on the screen of the tests that wake here after)
        game.rpc("dev_stamp", x=x - 6, y=y - 5, rows=["." * 13] * 12)


def test_x_breaks_anything_and_digs_holes(game):
    """X in build mode was "take a plan back, or take down what was built": a tree, a rock, the ground itself could not
    be planned away. Now X breaks whatever is at the cursor (a tree, a rock, a wall...) and on bare ground digs a hole,
    a layer deeper each time; held while the cursor moves, a row. Your character does it, with the right tool if it
    has one."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(1, -2, ["TM"])                                  # a tree and a rock
    game.give(axe=1, pickaxe=1)
    game.press("b")
    game.js(f"Build.S.at = {{x: {x + 1}, y: {y - 2}}}")
    assert game.js("Build.rows()")[3] == ["X", "Chop tree"]
    game.press("x")
    game.press("ArrowRight", 150)
    assert game.js("Build.rows()")[3] == ["X", "Mine rock"]
    game.press("x")
    game.wait(f"combAt({x + 1}, {y - 2}) !== 'T' && combAt({x + 2}, {y - 2}) !== 'M' && Build.S.plans.size === 0", 30000)
    game.js(f"Build.S.at = {{x: {x - 2}, y: {y + 2}}}")       # a row of holes, X held
    kb = game.page.keyboard
    kb.down("x")
    for _ in range(2):
        game.press("ArrowRight", 150)
    kb.up("x")
    game.wait("Build.S.plans.size === 0", 30000)
    assert game.js(f"[0, 1, 2].map((i) => surfacesAt({x - 2} + i, {y + 2})[0])") == [-1, -1, -1]
    game.js(f"Build.S.at = {{x: {x - 1}, y: {y + 2}}}")       # again on one of them: a layer deeper
    assert game.js("Build.rows()")[3] == ["X", "Break"]
    game.press("x")
    game.wait(f"surfacesAt({x - 1}, {y + 2})[0] === -2 && Build.S.plans.size === 0", 20000)
    # two layers down the hole's floor is behind the grass in front of it: the window on you is yours alone, it does
    # not open on the cursor (that the cursor's own tile is seen there: test_e2e_digging.py, the keyhole)
    game.sleep(300)
    assert game.js("xray.a") < .1
    game.press("b")
    assert game.inv("dirt") == 3 and game.inv("stone") == 2 and game.inv("stone_block") == 1 and not game.errors      # (the rock gives two stones; the deeper layer is stone: its block)
