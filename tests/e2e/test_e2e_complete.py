"""The chat line finishes what you type: commands, their arguments, what an argument can be, a name (js/complete.js)."""

from conftest import open_game

ROWS = "[...$('sayhelp').children].map((d) => (d.querySelector('b') || d).textContent)"
LINE = "$('say').value"
OPEN = "$('chatbox').classList.contains('open') && document.activeElement === $('say')"


def test_a_command_is_built_with_tab_and_the_arrows(game):
    """A "/" lists the commands (the server's actions, and the ones done in the page); typing narrows the list, Tab
    takes the marked one, the arrows move the mark; then its arguments, then what an argument can be. Enter sends
    the line as it is typed."""
    page = game.page
    game.give(wood=3, berries=2)
    page.keyboard.press("/")
    game.wait("$('sayhelp').children.length > 20")                      # (asked of the server once, when the line opens)
    rows = game.js(ROWS)
    assert rows[:3] == ["step", "walk", "stop"] and {"dig", "craft", "say", "perf", "coords", "grid"} <= set(rows)
    assert game.js("$('sayhelp').querySelector('.on b').textContent") == "step"
    page.keyboard.type("di")
    assert game.js(ROWS) == ["dig", "dig_down"]                         # (the shortest first)
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig " and game.js(ROWS) == ["dir=", "with="]
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=" and game.js(ROWS) == ["N", "E", "S", "W"]
    for key in ("ArrowDown", "ArrowDown", "ArrowUp"):
        page.keyboard.press(key)
    assert game.js("$('sayhelp').querySelector('.on b').textContent") == "E"
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=E " and game.js(ROWS) == ["with="]    # (what is given already is not offered again)
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=E with=" and set(game.js(ROWS)) == {"wood", "berries"}   # what you carry
    page.keyboard.type("wo")
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=E with=wood " and game.js(ROWS) == [] and game.js("$('sayhelp').style.display") == "none"
    assert game.js(OPEN) is True                                        # (Tab never leaves the line)
    page.keyboard.press("Escape")
    assert game.js("$('sayhelp').style.display") == "none" and not game.js("$('chatbox').classList.contains('open')")
    game.stamp(0, -1, ["f"])
    page.keyboard.press("/")
    page.keyboard.type("dig dir=N")
    assert game.js(ROWS) == ["N"]
    page.keyboard.press("Enter")                                        # sent as typed: the list is not in the way
    game.sleep(500)
    assert game.inv("flower") == 1


def test_what_an_argument_can_be(game):
    """What you can eat of what you carry, the recipes, a slot of your clothes, who is near; a number or a text is
    yours to write, and the list says what it is. A click takes one; the line keeps the caret."""
    page = game.page
    game.give(wood=3, berries=2, bread=1)
    cow = game.rpc("dev_creatures", kind="cow", dx=2, dy=0, still=600)["spawned"]
    game.sleep(600)
    page.keyboard.press("/")
    game.wait("$('sayhelp').children.length > 20")
    for line, want in (("/eat item=", ["berries", "bread"]), ("/drop item=w", ["wood"]), ("/craft recipe=plank", ["plank"]),
                       ("/unwear slot=", ["head", "top", "pants", "shoes", "effect"]), ("/step dir=N run=", ["true"]),
                       ("/sign", ["write_sign", "read_sign"]), ("/say text=\"dig dir=", [])):
        page.fill("#say", line)
        assert game.js(ROWS) == want, line
    page.fill("#say", "/move_to x=")
    assert game.js("$('sayhelp').textContent") == "x: int"              # (yours to write)
    page.fill("#say", "/milk target=")
    assert len(game.js(ROWS)) == 1 and "cow, 2 tiles away" in game.js("$('sayhelp').textContent")
    page.keyboard.press("Tab")
    assert game.js(LINE) == f"/milk target={cow} "
    page.fill("#say", "/unwear slot=")
    page.click("#sayhelp div:nth-child(3)")
    assert game.js(LINE) == "/unwear slot=pants " and game.js(OPEN) is True
    page.fill("#say", "/step dir=N run=false")                          # (and "false" is not a yes: it was, sent as a text)
    page.keyboard.press("Enter")
    game.sleep(600)
    assert game.js("$('toast').style.display") != "block" or "run" not in game.js("$('toastt').textContent")


def test_tab_finishes_a_name_in_plain_talk(browser, server, game):
    """Nothing is listed while you talk; Tab finishes the name of someone near (two that start alike: the list)."""
    friends = [open_game(browser, server, name) for name in ("Marlow", "Marigold")]
    game.sleep(1800)                                                    # (who is here: asked every 1.5 s)
    page = game.page
    page.keyboard.press("Enter")
    page.keyboard.type("hello marl")
    assert game.js(ROWS) == []
    page.keyboard.press("Tab")
    assert game.js(LINE) == "hello Marlow " and game.js(ROWS) == []
    page.keyboard.type("and mar")
    page.keyboard.press("Tab")
    assert sorted(game.js(ROWS)) == ["Marigold", "Marlow"] and game.js(LINE) == "hello Marlow and mar"
    game.js("(() => { comp.at = comp.items.findIndex((it) => it.show === 'Marigold'); drawSuggest(); return 1; })()")
    page.keyboard.press("Tab")
    assert game.js(LINE) == "hello Marlow and Marigold " and game.js(OPEN) is True
    page.keyboard.press("Escape")
    errors = [e for g in friends for e in g.errors]
    for g in friends:
        g.page.close()
    assert not errors


def test_a_tap_takes_one_on_a_phone(browser, server):
    """No Tab on a phone: a tap on the list takes it, and the keyboard stays up (the line keeps the caret)."""
    ctx = browser.new_context(viewport={"width": 844, "height": 390}, has_touch=True, is_mobile=True, device_scale_factor=3)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined'")
    page.fill("#name", "Thumb")
    page.tap("#join")
    page.wait_for_function("meObs && myPos()", timeout=8000)
    page.tap("#tTalk")
    page.keyboard.type("/unw")
    page.wait_for_function("$('sayhelp').children.length === 1")
    page.tap("#sayhelp div")
    assert page.evaluate(LINE) == "/unwear " and page.evaluate(OPEN) is True
    page.tap("#sayhelp div")
    assert page.evaluate(LINE) == "/unwear slot=" and page.evaluate(ROWS) == ["head", "top", "pants", "shoes", "effect"]
    box = page.evaluate("(() => { const r = $('sayhelp').getBoundingClientRect(), s = $('say').getBoundingClientRect(); return [r.left, r.right, r.bottom, s.top, innerWidth]; })()")
    assert box[0] >= 0 and box[1] <= box[4] and box[2] <= box[3]         # on the screen, over the line
    page.tap("#sayhelp div:nth-child(2)")
    assert page.evaluate(LINE) == "/unwear slot=top " and page.evaluate(OPEN) is True
    ctx.close()
    assert not errors
