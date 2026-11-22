"""A block of the land dug out is a block in your pack (earth, stone), shown as the pack's own block; stones are made
of it in the book; put down, it is the land again (landblocks.py). B_SHOTS=<folder>: the screens are saved there."""
import os

from test_e2e_touch import touch_game

CELLS = "(id) => [...$(id).children].map((c) => { const n = c.querySelector('span'); return c.title && !c.classList.contains('ghost') ? c.title.toLowerCase().replace(/ /g, '_') + (n ? ':' + n.textContent : '') : null; }).filter(Boolean)"
NEEDS = "[...document.querySelectorAll('#craftdetail .cneed')].map((e) => [e.querySelector('span').textContent, e.querySelector('b').textContent, e.classList.contains('miss')])"
# a block's icon: the pack's cube (cube_icons.js), every px of it drawn as CubeIcon made it from the land's own paint,
# its top (lit) and its front (the land's side) told apart. -> how many colours the top and the front have in common, or -1
SAME = """(name) => { const b = iconCanvas(name).getContext('2d').getImageData(0, 0, 16, 16).data, a = CubeIcon.px(name, 16).data, top = new Set(), front = new Set();
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return -1;
  for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) { const o = (y * 16 + x) * 4; if (b[o + 3] !== 255) continue; const k = b[o] << 16 | b[o + 1] << 8 | b[o + 2];
    if (y >= 2 && y <= 4 && x >= 5 && x <= 10) top.add(k); else if (y >= 8 && y <= 13 && x >= 2 && x <= 8) front.add(k); }
  return top.size && front.size ? [...top].filter((k) => front.has(k)).length : -1; }"""
HAS = "(n) => (meObs.self.inventory[n] || 0)"


def shot(g, name):
    if os.environ.get("B_SHOTS"):
        g.page.screenshot(path=os.path.join(os.environ["B_SHOTS"], f"b_{name}.png"))


def dig_two(g):
    """The ground east of you, two layers: the meadow's earth, then the stone under it."""
    for z, item in ((0, "dirt"), (-1, "stone_block")):
        r = g.rpc("act", tool="dig", args={"dir": "E", "z": z})
        assert r["ok"], r
        g.wait(f"({HAS})('{item}') === 1", 20000)


def test_dug_land_is_a_block_in_the_pack_and_stones_are_made_of_it(game):
    game.give(wood=2, stone=1)
    dig_two(game)
    assert game.inv("stone") == 1 and game.inv("stone_block") == 1 and game.inv("dirt") == 1      # the block: not a stone more
    game.press("i", 400)
    cells = game.js(CELLS, "bagbar") + game.js(CELLS, "bagpack")
    assert {"stone_block", "dirt", "stone"} <= set(cells)                # (one of a thing: no number on it)
    assert game.js(SAME, "stone_block") == 0 and game.js(SAME, "dirt") == 0     # drawn as blocks, of the land's paint: a top and a wall of other colours
    assert game.js("BLURB.stone_block && label('stone_block')") == "stone block"
    shot(game, "bag_desktop")
    game.press("Escape", 200)
    game.press("c", 400)                                       # the book: Stone, of one stone block, by hand
    game.js("craftTurn({page: 1})")
    game.js("focusRecipe('stone')")
    assert game.js("craftFocus") == "stone" and game.js(NEEDS) == [["Stone block", "1/1", False]]
    shot(game, "craft_desktop")
    game.press("Enter", 300)
    game.wait(f"({HAS})('stone') === 3 && ({HAS})('stone_block') === 0", 8000)
    game.press("Escape", 200)
    game.give(stone_block=1)                                   # in hand: put on open ground, the ground comes up; dug, the same block
    x, y = game.pos()
    game.hold_item("stone_block")
    game.face(-1, 0)
    assert "Raise the ground" in game.actions()
    game.press("e", 300)
    game.wait(f"topAt({x - 1}, {y}) === 1 && ({HAS})('stone_block') === 0", 8000)
    assert game.rpc("act", tool="dig", args={"dir": "W", "z": 1})["ok"]
    game.wait(f"({HAS})('stone_block') === 1 && topAt({x - 1}, {y}) === 0", 20000)
    assert game.inv("dirt") == 1 and not game.errors


def test_on_a_phone_the_pack_and_the_book_show_the_blocks(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        g.give(stone_block=3, dirt=2, stone=4, wood=3)
        g.press("i", 400)
        cells = g.js(CELLS, "bagbar") + g.js(CELLS, "bagpack")
        assert "stone_block:3" in cells and "dirt:2" in cells
        box = g.js("(() => { const r = $('bag').getBoundingClientRect(); return [r.left, r.right]; })()")
        assert box[0] >= 0 and box[1] <= 390
        shot(g, "bag_phone")
        g.press("Escape", 200)
        g.js("openCraft()")
        g.js("craftTurn({page: 1})")
        g.js("focusRecipe('stone')")
        assert g.js(NEEDS) == [["Stone block", "3/1", False]]
        box = g.js("(() => { const r = $('craft').getBoundingClientRect(); return [r.left, r.right]; })()")
        assert box[0] >= 0 and box[1] <= 390
        shot(g, "craft_phone")
        assert not g.errors
    finally:
        ctx.close()


def test_in_build_mode_space_puts_the_block_at_the_cursor_and_x_takes_it(game):
    """"why cant i place block in that mode also ??": Z (under A: the hand stays on WASD; B still does it) is build
    mode; a stone block in hand, Space puts it where the cursor is: on the ground, then on that block (a wall two
    high), then a tile on at the same height, in the air, held by the block beside it; X takes the top one back."""
    game.clear_area(8)
    x, y = game.pos()
    game.give(stone_block=4)
    game.hold_item("stone_block")
    game.face(1, 0)
    game.press("z")
    game.wait("Build.on", 3000)
    rows = game.js("Build.rows()")
    assert rows[0][0] == "Z" and rows[1][:2] == ["Space", "Place stone block"], rows
    for z in (1, 2):
        game.press("Space", 100)
        game.wait(f"landSolid({x + 1}, {y}, {z}) && Build.S.plans.size === 0 && !myAction", 12000)
    assert game.js(f"topAt({x + 1}, {y})") == 2 and game.js("Build.level()") == 2
    game.press("ArrowUp", 100)                                    # a tile north, the cursor on the ground there: up to the wall's height
    game.press("e", 100)
    game.js("Build.S.plane = 2")                                  # (E goes a storey at a time in the air: the cell beside the wall's top is named here)
    assert game.js("Build.hint(Build.S.at).text") == "Place stone block" and game.js("Build.hint(Build.S.at).z") == 2
    game.press("Space", 100)
    game.wait(f"landSolid({x + 1}, {y - 1}, 2) && !landSolid({x + 1}, {y - 1}, 1) && Build.S.plans.size === 0 && !myAction", 12000)
    game.js("Build.S.plane = 3")                                  # in the open air over it: on top of the block there, still a place
    game.press("ArrowUp", 100)
    assert game.js("Build.hint(Build.S.at).ok") is False and "holds" in game.js("Build.hint(Build.S.at).text")      # nothing beside that cell
    game.press("ArrowDown", 100); game.press("ArrowDown", 100)    # back onto the wall
    game.js("Build.S.plane = null")
    game.press("x", 100)
    game.wait(f"topAt({x + 1}, {y}) === 1 && Build.S.plans.size === 0 && !myAction", 12000)
    game.press("b")                                               # (its first key leaves it too)
    s = game.server()
    assert not game.js("Build.on") and s["inventory"].get("stone_block") == 2 and not game.errors, s["inventory"]
