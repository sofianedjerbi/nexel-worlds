"""Dropping things ("add the ability to drop items"): Y lets go of one of what is in hand, Shift Y of all of it; in the
inventory, a cell dragged out of the window (or its word "drop", a phone's button) drops its stack. It hops from you
down onto the ground in front of you (loot.js), and stays there (the magnet does not hand it straight back:
sim/progress.py); walk onto it and F takes it back. Each test sweeps what it left on the ground (dev_creatures clear=)."""

import pytest

# what lies on the tile in front of you (you face south: the tile under you on the screen), of one thing
FRONT = "(n) => groundItems.find(([x, y]) => x === myPos().x && y === myPos().y + 1)?.[2]?.[n] || 0"
HOPS = "(() => { window.__hops = []; const o = dropLoot; dropLoot = function (x, y, items, now, ox, oy) { __hops.push([items, ox, oy]); return o(x, y, items, now, ox, oy); }; return 1; })()"


@pytest.fixture
def ground(game):
    game.clear_area(4)
    game.js(HOPS)
    game.face(0, 1)
    yield game
    game.rpc("dev_creatures", clear=40)              # (what lies on the ground goes with the clearing: devtools.py)


def onto_it_and_f(game, want):
    x, y = game.server()["x"], game.server()["y"]
    game.rpc("dev_teleport", x=x, y=y + 1)           # (a step onto it)
    game.arrive()
    game.press("f")
    game.wait(f"Object.entries({want!r}).every(([k, n]) => meObs.self.inventory[k] === n) && !groundItems.some(([x, y]) => x === myPos().x && y === myPos().y)")


def test_y_drops_one_in_front_and_it_stays_down_until_f_takes_it_back(ground):
    game = ground
    game.give(plank=3)
    game.hold_item("plank")
    game.press("y")
    game.wait(f"({FRONT})('plank') === 1 && meObs.self.inventory.plank === 2")
    assert game.js("__hops") == [[{"plank": 1}, 0, -1]]                             # it hopped from you to there (loot.js)
    game.sleep(2400)                                                                # longer than the magnet waits (1.2 s)
    assert game.inv("plank") == 2 and game.js(FRONT, "plank") == 1 and game.js("selected") == "plank"     # still there; the rest in hand
    onto_it_and_f(game, {"plank": 3})
    assert not game.errors


def test_shift_y_drops_the_whole_stack_and_empty_hands_say_so(ground):
    game = ground
    game.give(stone=5)
    game.hold_item("stone")
    game.press("Shift+y")
    game.wait(f"({FRONT})('stone') === 5 && !meObs.self.inventory.stone")
    assert game.server()["inventory"].get("stone", 0) == 0 and game.js("__hops")[0][0] == {"stone": 5}
    game.press("y")                                                                 # nothing in hand now: a no, over the bar
    game.wait("$('heldname').classList.contains('bad') && $('heldname').textContent === 'Nothing in hand to drop.'")
    onto_it_and_f(game, {"stone": 5})
    assert not game.errors


def test_a_cell_dragged_out_of_the_inventory_drops_its_stack(ground):
    game = ground
    game.give(wood=4, fiber=2)
    game.press("i", 400)
    cell = "#bag .cell[title='Wood']"
    game.wait(f"document.querySelector(\"{cell}\")")
    b = game.js(f"(() => {{ const c = document.querySelector(\"{cell}\").getBoundingClientRect(), w = $('bag').getBoundingClientRect(); return [c.left + c.width / 2, c.top + c.height / 2, w.top]; }})()")
    page = game.page
    page.mouse.move(b[0], b[1]); page.mouse.down()
    page.mouse.move(b[0], b[1] - 20, steps=4); page.mouse.move(b[0], max(5, b[2] - 40), steps=8)   # up and out of the window
    page.mouse.up()
    game.wait(f"({FRONT})('wood') === 4 && !meObs.self.inventory.wood")
    assert game.js("$('bag').style.display") == "block" and game.inv("fiber") == 2    # the window stays open; the rest stays
    game.js("(() => { bagAt = {zone: 'bar', i: slots.indexOf('fiber')}; bagDraw(true); return 1; })()")
    game.page.click("#bagkeys .bkey:has-text('drop')")                             # its word (a phone's button): the stack
    game.wait(f"({FRONT})('fiber') === 2 && !meObs.self.inventory.fiber")
    game.press("Escape", 200)
    onto_it_and_f(game, {"wood": 4, "fiber": 2})
    assert not game.errors
