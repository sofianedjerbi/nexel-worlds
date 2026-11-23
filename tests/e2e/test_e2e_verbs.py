"""Two verbs, as in Minecraft (the owner: "E should be used to interact, right? Now it breaks things. Why do I break
rocks with E?"): X (a left click) breaks what it is on, E (a right click) uses it (intent.js)."""

SCREEN = "([x, y]) => { const r = cv.getBoundingClientRect(), a = HdLook.screenOf(x + .5, y + .5, topAt(x, y)); return [r.left + a[0], r.top + a[1]]; }"      # (the middle of a tile's top, as the HD look draws it)


def point(game, dx, dy):
    x, y = game.pos()
    sx, sy = game.js(SCREEN, [x + dx, y + dy])
    game.page.mouse.move(sx - 3, sy)
    game.page.mouse.move(sx, sy)
    game.frames(2)
    return sx, sy


def rows(game):
    return game.js("availableActions().map((r) => r[0] + ' ' + r[1])")


def test_e_does_not_mine_a_rock_x_does(game):
    game.stamp(1, 0, ["M"])
    game.face(1, 0)
    x, y = game.pos()
    assert rows(game) == [game.js("capOf('alt')") + " Mine rock (slow)"], rows(game)                     # (E has nothing to do with a rock: no row)
    game.js("$('toast').style.display = 'none'")
    for _ in range(3):
        game.press("e", 400)
    assert game.tile(1, 0) == "M" and game.toast() == "" and not game.js("myAction"), game.toast()      # nothing done, nothing said
    assert game.js("Target.cells().filter((c) => c.key === 'alt').map((c) => [c.kind, c.x, c.y])") == [["break", x + 1, y]]      # (X's box, orange, on the rock)
    game.page.keyboard.down("x")
    game.wait(f"combAt({x + 1}, {y}) !== 'M'", 15000)
    game.page.keyboard.up("x")
    assert game.inv("stone") >= 1


def test_e_opens_a_chest_x_takes_it_apart(game):
    game.stamp(1, 0, ["C"])
    game.face(1, 0)
    x, y = game.pos()
    assert rows(game) == ["E Open chest", game.js("capOf('alt')") + " Break chest open (slow)"], rows(game)
    game.press("e", 400)
    assert game.tile(1, 0) == "C"                                            # E opened it: it stands
    game.page.keyboard.down("x")
    game.wait(f"combAt({x + 1}, {y}) !== 'C'", 15000)
    game.page.keyboard.up("x")


def test_x_hits_e_does_not(game):
    game.spawn("chicken", 1, 0, still=60)
    game.face(1, 0)
    assert not game.js("(facingNow(false) || {it: {}}).it.attack") and game.js("facingNow(true).it.attack")
    assert game.js("facingNow(true).it.text") == "Punch chicken"


def test_left_click_breaks_right_click_uses_ground_walks(game):
    game.stamp(1, 0, ["M"])
    game.stamp(0, 1, ["C"])
    x, y = game.pos()
    point(game, 0, 1)
    assert game.js("$('hover').innerText") == "Break chest open (slow)\nRight click: Open chest"
    sx, sy = point(game, 1, 0)
    assert game.js("$('hover').innerText") == "Mine rock (slow)"             # (a right click has nothing to do with it)
    for _ in range(2):
        game.page.mouse.click(sx, sy, button="right")
        game.sleep(300)
    assert game.tile(1, 0) == "M" and not game.js("myAction")                # the right button mines nothing
    game.page.mouse.click(sx, sy)                                            # the left one does
    game.wait("!!myAction || combAt(%d, %d) !== 'M'" % (x + 1, y), 3000)
    game.wait("!myAction", 15000)
    for _ in range(6):
        if game.tile(1, 0) != "M":
            break
        game.page.mouse.click(sx, sy)
        game.wait("!myAction", 15000)
    assert game.tile(1, 0) != "M"
    sx, sy = point(game, -3, 0)                                              # open ground: a left click walks you there
    game.page.mouse.click(sx, sy)
    game.wait(f"myPos().x === {x - 3}", 5000)
