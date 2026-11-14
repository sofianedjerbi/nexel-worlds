"""The inventory (web/js/bag.js): a window of fixed cells where everything keeps its place, played with keys alone."""

CELLS = "(id) => [...$(id).children].map((c) => { const k = c.querySelector('canvas'), n = c.querySelector('span'); return c.title && !c.classList.contains('ghost') ? c.title.toLowerCase().replace(/ /g, '_') + (n ? ':' + n.textContent : '') : null; })"
BOX = "(() => { const r = $('bag').getBoundingClientRect(), q = parseFloat(getComputedStyle($('bag')).getPropertyValue('--q')); return [Math.round(r.width / q), Math.round(r.height / q), Math.round(r.left), Math.round(r.top)]; })()"
DETAIL = "[document.querySelector('#bagdetail .bname')?.textContent || document.querySelector('#bagdetail .bnone')?.textContent, [...document.querySelectorAll('#bagbtns .b')].map((b) => b.textContent)]"


def test_the_inventory_is_a_window_of_cells_where_everything_keeps_its_place(game):
    """It was a strip of pictures without names that wrapped, and changed size and order as you picked things up. It is
    one window of one size: what you wear (five cells), the pack (three rows of ten), your bar (ten, with their keys),
    and under them the thing the cursor is on, by name, with what it is for and what you can do. A thing stays in
    its cell; an empty cell stays empty; a new thing takes the first empty cell."""
    kinds = ["wood", "stone", "fiber", "seed", "flower", "rope", "torch", "plank", "path", "dirt", "egg", "bread"]
    game.give(**{k: 2 for k in kinds})
    game.press("i", 400)
    box = game.js(BOX)
    assert box[:2] == [214, 190] and game.js("[$('bagwear').children.length, $('bagpack').children.length, $('bagbar').children.length]") == [5, 30, 10]
    bar, pack = game.js(CELLS, "bagbar"), game.js(CELLS, "bagpack")
    assert [c.split(":")[0] for c in bar] == game.js("slots.slice(0, 10)") and all(c.endswith(":2") for c in bar)        # the bar's ten, each with how many
    assert sorted(c.split(":")[0] for c in pack if c) == sorted(set(kinds) - {c.split(":")[0] for c in bar}) and pack[2:] == [None] * 28   # the rest in the pack's first cells; the others empty
    assert game.js("[...document.querySelectorAll('#bagbar .k')].map((k) => k.textContent).join('')") == "1234567890"
    name, btns = game.js(DETAIL)
    assert name == bar[0].split(":")[0].capitalize().replace("_", " ") + " x2" and btns[0] == "HoldEnter" and btns[-1] == "MoveX"   # by name, with what can be done and its key
    assert game.js("document.querySelectorAll('#bagdetail .bwhat')[0].textContent") != ""
    game.rpc("dev_give", items={"carrot": 3, bar[4].split(":")[0]: 5})           # a new thing, and more of one you have
    game.sleep(900)
    assert game.js(CELLS, "bagpack")[:3] == pack[:2] + ["carrot:3"]              # the new one: the first empty cell
    after = game.js(CELLS, "bagbar")
    assert [c.split(":")[0] for c in after] == [c.split(":")[0] for c in bar] and after[4].endswith(":7")     # nothing moved; one count grew
    game.rpc("dev_give", items={bar[1].split(":")[0]: -2})                       # the last of a thing goes: its cell is empty, the others stay
    game.sleep(900)
    gone = game.js(CELLS, "bagbar")
    assert gone[1] is None and [c and c.split(":")[0] for c in gone[2:]] == [c.split(":")[0] for c in bar[2:]]
    assert game.js(BOX) == box                                                   # the window: where it was, the size it was
    game.press("Escape", 200)
    assert game.js("$('bag').style.display") == "none"


def test_the_inventory_is_played_with_keys_alone(game):
    """The arrows (or W A S D) move the cursor a cell at a time. Enter takes the thing in hand and closes (from the
    pack it comes onto the bar); E eats it, puts it on, takes it off; X picks it up and X puts it down where the
    cursor is; a number sends it to that cell of the bar. No key acts on the world behind."""
    game.give(wood=3, stone=2, bread=2, straw_hat=1, axe=1, seed=1, fiber=1, rope=1, plank=1, torch=1, egg=1, flower=1)
    game.rpc("dev_needs", hunger=8)
    game.stamp(0, 1, ["f"])
    game.press("i", 400)
    at = "[bagAt.zone, bagAt.i]"
    assert game.js(at) == ["bar", 0] and game.js("document.querySelector('#bag .cell.cur').dataset.zone") == "bar"
    game.press("ArrowRight", 80)
    game.press("d", 80)
    assert game.js(at) == ["bar", 2]
    game.press("ArrowUp", 80)
    assert game.js(at) == ["pack", 22]                                           # up from the bar: the pack's last row, the same column
    game.press("w", 80)
    game.press("ArrowUp", 80)
    game.press("ArrowLeft", 80)
    assert game.js(at) == ["pack", 1]
    game.press("ArrowUp", 80)
    assert game.js(at) == ["wear", 0]                                            # and up again: what you wear
    game.press("ArrowDown", 80)
    assert game.js(at) == ["pack", 5]                                            # (under its cell)
    for _ in range(5):
        game.press("ArrowLeft", 50)
    assert game.js(at) == ["pack", 0]
    first, bar0 = game.js("slots[10]"), game.js("slots[0]")
    game.press("x", 150)                                                         # pick it up...
    assert game.js("bagMove") == 10 and game.js(DETAIL)[1] == ["Put downX"]
    for _ in range(3):
        game.press("ArrowDown", 60)
    game.press("x", 200)                                                         # ...and put it down on the bar's first cell: the two change places
    assert game.js("[slots[0], slots[10], bagMove]") == [first, bar0, None] and game.js("[...document.querySelectorAll('#hotbar .slot canvas')].length") >= 9
    game.press("ArrowUp", 60)
    game.press("ArrowUp", 60)
    game.press("ArrowUp", 60)
    assert game.js(at) == ["pack", 0] and game.js("slots[10]") == bar0
    game.press("3", 200)                                                         # a number: to that cell of the bar
    assert game.js("slots[2]") == bar0 and game.js("$('bag').style.display") == "block"
    where = game.js("(() => { const i = slots.indexOf('bread'); return i < 10 ? ['bar', i] : ['pack', i - 10]; })()")
    game.js(f"(() => {{ bagAt = {{zone: {where[0]!r}, i: {where[1]}}}; bagDraw(true); }})()")
    assert game.js(DETAIL) == ["Bread x2", ["HoldEnter", "EatE", "MoveX"]]
    game.press("e", 1500)                                                        # eaten: one less, the window stays
    assert game.inv("bread") == 1 and game.server()["hunger"] == 18 and game.js("$('bag').style.display") == "block"
    where = game.js("(() => { const i = slots.indexOf('straw_hat'); return i < 10 ? ['bar', i] : ['pack', i - 10]; })()")
    game.js(f"(() => {{ bagAt = {{zone: {where[0]!r}, i: {where[1]}}}; bagDraw(true); }})()")
    assert game.js(DETAIL)[1] == ["HoldEnter", "WearE", "MoveX"]
    game.press("e", 1200)                                                        # put on
    assert game.server()["wearing"] == {"head": "straw_hat"} and game.js(CELLS, "bagwear")[0] == "straw_hat"
    game.js("(() => { bagAt = {zone: 'wear', i: 0}; bagDraw(true); })()")
    assert game.js(DETAIL) == ["Straw hat", ["Take offEnter"]]
    game.press("Enter", 1200)                                                    # ...and taken off
    assert game.server()["wearing"] == {} and game.inv("straw_hat") == 1
    assert game.inv("flower") == 1 and game.js("$('bag').style.display") == "block"       # (X, E and the numbers did nothing behind the window: the flower you face is there)
    far = game.js("slots.findIndex((n, i) => i >= 10 && n)")
    name = game.js(f"slots[{far}]")
    game.js(f"(() => {{ bagAt = {{zone: 'pack', i: {far - 10}}}; bagDraw(true); }})()")
    game.press("Enter", 300)                                                     # in hand: onto the bar, and the window closes
    assert game.js("selected") == name and name in game.js("slots.slice(0, 10)") and game.js("$('bag').style.display") == "none"
    game.press("i", 300)
    assert game.js("slots[bagAt.i]") == name and game.js("document.querySelector('#bag .cell.held').title.toLowerCase().replace(/ /g, '_')") == name   # it opens on what you hold
    game.press("x", 150)
    game.press("Escape", 150)                                                    # Esc lets go of what is carried, then closes
    assert game.js("bagMove") is None and game.js("$('bag').style.display") == "block"
    game.press("Escape", 200)
    assert game.js("$('bag').style.display") == "none" and not game.errors
