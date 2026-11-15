"""The chat line finishes what you type: commands, their arguments, what an argument can be, a name (js/complete.js)."""

from conftest import open_game

ROWS = "[...$('sayhelp').children].map((d) => (d.querySelector('b') || d).textContent)"
LINE = "$('say').value"
OPEN = "$('chatbox').classList.contains('open') && document.activeElement === $('say')"


def test_a_command_is_built_with_tab_and_the_arrows(game):
    """A "/" lists the commands: the few actions that have no key or click (naming an animal, writing on a sign) and
    the page's own. ("a lot of useless slash commands. like walk etc... no need for those": the thirty actions of the
    server are not listed, and are not commands.) Typing narrows the list, Tab takes the marked one, the arrows move
    the mark; then its arguments, then what an argument can be. Enter sends the line as it is typed."""
    page = game.page
    page.keyboard.press("/")
    game.wait("$('sayhelp').children.length === 5")                     # (asked of the server once, when the line opens)
    assert game.js(ROWS) == ["name", "write_sign", "coords", "grid", "perf"]
    assert game.js("$('sayhelp').querySelector('.on b').textContent") == "name"
    page.keyboard.type("wr")
    assert game.js(ROWS) == ["write_sign"]
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/write_sign " and game.js(ROWS) == ["dir=", "text="]
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/write_sign dir=" and game.js(ROWS) == ["N", "E", "S", "W"]
    for key in ("ArrowDown", "ArrowDown", "ArrowUp"):
        page.keyboard.press(key)
    assert game.js("$('sayhelp').querySelector('.on b').textContent") == "E"
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/write_sign dir=E " and game.js(ROWS) == ["text="]   # (what is given already is not offered again)
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/write_sign dir=E text=" and game.js("$('sayhelp').textContent") == "text: str"   # (yours to write)
    assert game.js(OPEN) is True                                        # (Tab never leaves the line)
    page.keyboard.press("Escape")
    assert game.js("$('sayhelp').style.display") == "none" and not game.js("$('chatbox').classList.contains('open')")
    at = game.js("myPos()")
    for line in ("walk dir=E", "dig dir=N"):                            # what a key does is not a command: nothing happens but a word
        page.keyboard.press("/")
        page.keyboard.type(line)
        assert game.js(ROWS) == []
        page.keyboard.press("Enter")
        game.sleep(500)
        assert "No command" in game.js("$('toastt').textContent") and game.js("myPos()") == at
    page.keyboard.press("/")                                            # the page's own still run
    page.keyboard.type("coords")
    page.keyboard.press("Enter")
    game.sleep(300)
    assert game.js("DEBUG.coords") is True
    game.js("(() => { flip('coords', 'Coordinates'); return 1; })()")


def test_what_an_argument_can_be(game):
    """Who is near, nearest first, for a name; a text is yours to write, and the list says what it is. A click takes
    one; the line keeps the caret. The command is sent as typed."""
    page = game.page
    cow = game.rpc("dev_creatures", kind="cow", dx=2, dy=0, still=600)["spawned"]
    game.sleep(600)
    page.keyboard.press("/")
    game.wait("$('sayhelp').children.length === 5")
    for line, want in (("/n", ["name", "write_sign"]), ("/na", ["name"]), ("/sign", ["write_sign"]), ("/write_sign dir=", ["N", "E", "S", "W"]), ("/name text=\"dig dir=", [])):
        page.fill("#say", line)
        assert game.js(ROWS) == want, line
    page.fill("#say", "/name target=")
    assert len(game.js(ROWS)) == 1 and "cow, 2 tiles away" in game.js("$('sayhelp').textContent")
    page.click("#sayhelp div")
    assert game.js(LINE) == f"/name target={cow} " and game.js(OPEN) is True
    page.keyboard.type("text=Daisy")
    page.keyboard.press("Enter")
    game.wait("[...ents.values()].some((p) => p.e && p.e.kind === 'cow' && p.e.name === 'Daisy')", 5000)


def test_tab_finishes_a_name_in_plain_talk(browser, server, game):
    """Nothing is listed while you talk; Tab finishes the name of someone near (two that start alike: the list)."""
    friends = [open_game(browser, server, name) for name in ("Marlow", "Marigold")]
    game.wait("['Marlow', 'Marigold'].every((n) => agents.some((a) => a.online && a.name === n))", 20000)   # (who is here: asked every 1.5 s)
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
    page.keyboard.type("/wr")
    page.wait_for_function("$('sayhelp').children.length === 1")
    page.tap("#sayhelp div")
    assert page.evaluate(LINE) == "/write_sign " and page.evaluate(OPEN) is True
    page.tap("#sayhelp div")
    assert page.evaluate(LINE) == "/write_sign dir=" and page.evaluate(ROWS) == ["N", "E", "S", "W"]
    box = page.evaluate("(() => { const r = $('sayhelp').getBoundingClientRect(), s = $('say').getBoundingClientRect(); return [r.left, r.right, r.bottom, s.top, innerWidth]; })()")
    assert box[0] >= 0 and box[1] <= box[4] and box[2] <= box[3]         # on the screen, over the line
    page.tap("#sayhelp div:nth-child(2)")
    assert page.evaluate(LINE) == "/write_sign dir=E " and page.evaluate(OPEN) is True
    ctx.close()
    assert not errors
