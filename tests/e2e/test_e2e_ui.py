"""The interface: hotbar and bag by keys, crafting cards, zoom, help, debug, hints, and that actions make sounds."""


def test_hotbar_keys_and_q_cycle_what_is_in_hand(game):
    game.give(wood=1, stone=1, fiber=1)
    order = game.js("slotOrder(meObs.self.inventory).slice(0, 9).filter(Boolean)")
    game.press("1", 100)
    assert game.js("selected") == order[0]
    game.press("q", 100)
    assert game.js("selected") == order[1]
    game.press("0", 100)
    assert game.js("selected") is None


def test_the_bag_holds_the_rest_and_arrows_pick_from_it(game):
    game.give(**{k: 1 for k in ["wood", "stone", "fiber", "seed", "flower", "rope", "torch", "plank", "path", "dirt", "egg"]})
    game.press("b", 300)
    assert game.js("$('bag').style.display") == "block"
    assert game.js("document.querySelectorAll('#bagitems .slot').length") >= 2
    game.press("ArrowRight", 100)
    picked = game.js("bagFocus")
    game.press("Enter", 300)
    assert game.js("selected") == picked and picked in game.js("slots.slice(0, 9)")
    game.press("Escape", 200)
    assert game.js("$('bag').style.display") == "none"


def test_crafting_cards_say_what_is_missing(game):
    game.press("c", 400)
    assert game.js("$('craft').style.display") == "block"
    assert "Missing materials" in game.js("document.querySelector('.rcard[data-name=axe]').title")
    game.give(wood=2, stone=2, fiber=1)
    game.sleep(300)
    assert "within 2 tiles of a workbench" in game.js("document.querySelector('.rcard[data-name=axe]').title")
    game.press("Escape", 200)


def test_zoom_help_and_debug_keys(game):
    z0 = game.js("zoom")
    game.press("+", 100)
    assert game.js("zoom") == z0 + 1
    game.press("-", 100)
    assert game.js("zoom") == z0
    game.press("h", 200)
    assert game.js("$('help').style.display") == "block"
    game.press("h", 200)
    game.press("F3", 300)
    assert game.js("$('debug').style.display") == "block" and "ms/tick" in game.js("$('debug').innerText")
    game.press("F3", 100)


def test_hover_hints_follow_the_mouse(game):
    game.stamp(2, 0, ["M"])
    x, y = game.pos()
    sx, sy = game.js("([x, y]) => { const S = TS(), [ox, oy] = screenOrigin(S); return [ox + x * S + S / 2, oy + y * S + S / 2]; }", [x + 2, y])
    game.page.mouse.move(sx - 3, sy)
    game.page.mouse.move(sx, sy)
    game.sleep(200)
    assert "Mine rock" in game.js("$('hover').innerText")
    assert game.js("inputMode") == "mouse"
    game.press("d", 100)
    assert game.js("inputMode") == "keys"


def test_actions_make_their_sounds(game):
    game.js("window.__snd = []; const s0 = sfx; window.sfx = (n, x, y) => { __snd.push(n); s0(n, x, y); }")
    game.stamp(1, 0, ["f"])
    game.stamp(-1, 0, ["T"])
    game.face(1, 0)
    game.press("Space", 600)
    game.face(-1, 0)
    game.give(axe=1)
    game.hold_item("axe")
    game.press("Space", 0)
    game.wait(f"combAt({game.pos()[0] - 1}, {game.pos()[1]}) === 't'", 8000)
    game.sleep(800)
    heard = set(game.js("__snd"))
    assert {"rustle", "collect", "chop", "creak", "fallthud", "ui"} <= heard, heard
