"""The interface: the bar and the inventory by keys, crafting cards, zoom, help, debug, hints, and that actions make sounds."""


def test_hotbar_keys_and_q_cycle_what_is_in_hand(game):
    game.give(wood=1, stone=1, fiber=1)
    order = game.js("slotOrder(meObs.self.inventory).slice(0, 9).filter(Boolean)")
    game.press("1", 100)
    assert game.js("selected") == order[0]
    game.press("q", 100)
    assert game.js("selected") == order[1]
    game.press("0", 100)
    assert game.js("selected") is None


def test_the_bar_is_ten_slots_and_i_opens_the_inventory(game):
    """Ten slots (1-9 and 0), no bag or crafting button on the bar. I opens the inventory: everything you carry, by
    name; what is beyond the ten comes onto the bar when picked. C opens the crafting."""
    kinds = ["wood", "stone", "fiber", "seed", "flower", "rope", "torch", "plank", "path", "dirt", "egg", "bread"]
    game.give(**{k: 1 for k in kinds})
    assert game.js("[...document.querySelectorAll('#hotbar .slot .k')].map((e) => e.textContent).join('')") == "1234567890"
    assert game.js("document.querySelectorAll('#hotbar .slot').length") == 10 and game.js("!$('craftbtn') && !document.querySelector('.bagslot')")
    game.press("0", 100)
    assert game.js("selected") == game.js("slots[9]") and game.js("selected")       # the tenth slot
    game.press("b", 200)
    assert game.js("$('bag').style.display") != "block"                              # (B is no longer a key)
    game.press("i", 300)
    assert game.js("$('bag').style.display") == "block"
    assert game.js("document.querySelectorAll('#bagitems .slot').length") == len(kinds)
    game.press("ArrowRight", 100)
    picked = game.js("bagFocus")
    game.press("Enter", 300)
    assert game.js("selected") == picked and picked in game.js("slots.slice(0, 10)")
    beyond = game.js("[...document.querySelectorAll('#bagitems .slot')].pop().dataset.name")
    assert beyond not in game.js("slots.slice(0, 10)")
    game.js("[...document.querySelectorAll('#bagitems .slot')].pop().onclick()")     # one from beyond the bar: onto it, in hand
    assert game.js("selected") == beyond and beyond in game.js("slots.slice(0, 10)")
    game.press("Escape", 200)
    assert game.js("$('bag').style.display") == "none"
    game.press("c", 300)
    assert game.js("$('craft').style.display") == "block"
    game.press("Escape", 200)
    game.press("3", 100)
    game.press("0", 100) if not game.js("slots[9]") else game.press("`", 100)
    assert not game.errors


def test_crafting_cards_say_what_is_missing(game):
    game.press("c", 400)
    assert game.js("$('craft').style.display") == "block"
    assert "Missing materials" in game.js("document.querySelector('.rcard[data-name=axe]').title")
    game.give(wood=2, stone=2, fiber=1)
    game.sleep(300)
    assert "within 2 tiles of a workbench" in game.js("document.querySelector('.rcard[data-name=axe]').title")
    game.press("Escape", 200)


def test_crafting_tabs_detail_and_button(game):
    game.give(wood=4)
    game.press("c", 400)
    assert game.js("craftTab") == "All" and game.js("craftFocus") == "workbench"     # what you can make, first
    assert game.js("$('craftdetail').querySelector('.cbtn').textContent") == "Craft"
    game.press("Tab", 200)
    assert game.js("craftTab") == "Start"
    game.press("Tab", 200)                                                             # tools: you can't make them yet
    assert game.js("craftTab") == "Tools" and game.js("craftFocus") == "axe"
    assert game.js("$('craftdetail').querySelector('.cbtn').textContent") == "Missing materials"
    game.js("craftTab = 'Start'; craftFocus = 'workbench'; drawRecipes()")
    game.js("$('craftdetail').querySelector('.cbtn').click()")
    game.sleep(1200)
    assert game.inv("workbench") == 1
    game.press("Escape", 200)


def test_crafting_says_what_can_be_made_now_and_is_driven_by_keys(game):
    """What you can make right now wears a tick (the rest is faded) and is counted beside the category's name;
    Q and E change category like Tab, Home and End go to the first and the last recipe."""
    game.give(wood=4)
    game.press("c", 400)
    ticked = game.js("[...document.querySelectorAll('.rcard')].filter((c) => c.querySelector('.ok')).map((c) => c.dataset.name)")
    assert "workbench" in ticked and "axe" not in ticked
    assert game.js("document.querySelector('#crafttabs .ctitle').textContent") == f"Everything · {len(ticked)} ready"
    game.press("e", 200)
    assert game.js("craftTab") == "Start"
    game.press("q", 200)
    assert game.js("craftTab") == "All"
    names = game.js("[...document.querySelectorAll('.rcard')].map((c) => c.dataset.name)")
    game.press("End", 200)
    assert game.js("craftFocus") == names[-1]
    game.press("Home", 200)
    assert game.js("craftFocus") == names[0]
    game.press("Escape", 200)
    assert not game.errors


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


def test_coords_and_grid_are_typed_in_the_chat_line(game):
    """/coords and /grid are debugging aids, off until asked for (js/debug.js); any other /word is still an action."""
    say = lambda line: (game.page.keyboard.press("Enter"), game.page.keyboard.type(line), game.page.keyboard.press("Enter"), game.sleep(300))
    game.js("(() => { DEBUG.coords = DEBUG.grid = false; return 1; })()")
    game.sleep(200)
    x, y = game.pos()
    assert game.js("$('xyz').textContent") == ""
    say("/coords")
    assert game.js("$('xyz').textContent").startswith(f"X {x}  Y {y}  Z 0") and game.js("localStorage.getItem('megastructure-coords')") == "1"
    say("/coords")
    assert game.js("$('xyz').textContent") == ""
    lines = "(() => { let n = 0; ctx.strokeRect = function (...a) { n++; return CanvasRenderingContext2D.prototype.strokeRect.apply(ctx, a); }; return new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { delete ctx.strokeRect; ok(n); }))); })()"
    assert game.js(lines) == 0
    say("/grid")
    assert game.js("DEBUG.grid") and game.js(lines) > 100      # a tile, an outline
    say("/grid")
    assert game.js(lines) == 0
    say("/perf")                                               # what the last second cost
    game.sleep(1300)
    text = game.js("$('xyz').textContent")
    assert " fps" in text and "script " in text and "ticks " in text and "world " in text and "blocks" in text, text
    say("/perf")
    game.sleep(100)
    assert game.js("$('xyz').textContent") == ""
    game.stamp(0, -1, ["f"])
    say("/dig dir=N")                                          # (not one of ours: sent to the server)
    game.sleep(400)
    assert game.inv("flower") == 1 and not game.errors


def test_the_crafting_list_is_not_made_again_while_it_is_shut(game):
    """It was built again, every card of it, each time what is near you changed: every step you took."""
    made = "$('recipes').dataset.sig"
    before = game.js(made)
    game.give(wood=10)                                         # (enough for a workbench)
    game.press("d", 600)
    game.sleep(900)
    assert game.js(made) == before and game.js("$('craft').style.display") != "block"
    game.press("c", 300)                                       # opened: it is up to date
    assert game.js(made) != before
    assert "workbench" in game.js("[...document.querySelectorAll('.rcard')].filter((c) => c.querySelector('.ok')).map((c) => c.dataset.name)")
