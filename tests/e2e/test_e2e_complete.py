"""The chat line finishes what you type: commands, their arguments, what an argument can be, a name (js/complete.js)."""

from conftest import open_game
from waits import QUIET

ROWS = "[...$('sayhelp').children].map((d) => (d.querySelector('b') || d).textContent)"
LINE = "$('say').value"
OPEN = "$('chatbox').classList.contains('open') && document.activeElement === $('say')"


def test_a_command_is_built_with_tab_and_the_arrows(game):
    """A "/" lists the commands a real player needs: the page's own (a sign is written as it goes up and an animal is
    named with a name tag: no command for those). "/ shouldn't confuse player with bot commands": a bot's action is
    not offered while its name is being typed, but once it is written in full its hint is there, then its arguments,
    then what an argument can be. Tab takes the marked one, the arrows move the mark. Enter sends the line as typed."""
    page = game.page
    game.give(wood=3, berries=2)
    page.keyboard.press("/")
    game.wait("!!tools && !!serverCmds && $('sayhelp').children.length === 4")          # (asked of the server once, when the line opens)
    assert game.js(ROWS) == ["coords", "perf", "help", "list"]       # (the page's, then the server's a player may use: commands.js)
    assert game.js("$('sayhelp').querySelector('.on b').textContent") == "coords"
    page.keyboard.type("nam")
    assert game.js(ROWS) == []
    page.keyboard.type("e")
    assert game.js(ROWS) == ["name"]
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/name " and game.js(ROWS) == ["target=", "text="]
    for typed, rows in (("/st", ["list"]), ("/ste", []), ("/step", ["step"]), ("/di", []), ("/dig", ["dig"])):   # a bot's: only when written in full
        page.fill("#say", typed)
        assert game.js(ROWS) == rows, typed
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig " and game.js(ROWS) == ["dir=", "with=", "z="]      # (z: the height of something built over the ground)
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=" and game.js(ROWS) == ["N", "E", "S", "W", "up"]
    for key in ("ArrowDown", "ArrowDown", "ArrowUp"):
        page.keyboard.press(key)
    assert game.js("$('sayhelp').querySelector('.on b').textContent") == "E"
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=E " and game.js(ROWS) == ["with=", "z="]    # (what is given already is not offered again)
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=E with=" and set(game.js(ROWS)) == {"wood", "berries"}   # what you carry
    page.keyboard.type("wo")
    page.keyboard.press("Tab")
    assert game.js(LINE) == "/dig dir=E with=wood " and game.js(ROWS) == ["z="]          # (only what is left)
    page.keyboard.type("z=0 ")
    assert game.js(ROWS) == [] and game.js("$('sayhelp').style.display") == "none"     # nothing left: no list
    assert game.js(OPEN) is True                                        # (Tab never leaves the line)
    page.keyboard.press("Escape")
    assert game.js("$('sayhelp').style.display") == "none" and not game.js("$('chatbox').classList.contains('open')")
    game.stamp(0, -1, ["f"])
    page.keyboard.press("/")
    page.keyboard.type("dig dir=N")
    assert game.js(ROWS) == ["N"]
    page.keyboard.press("Enter")                                        # sent as typed: the list is not in the way
    game.until(f"({QUIET})()")                                         # (the dig answered: an action is answered when it ends)
    assert game.inv("flower") == 1


def test_what_an_argument_can_be(game):
    """What you can eat of what you carry, the recipes, a slot of your clothes, who is near; a number or a text is
    yours to write, and the list says what it is. A click takes one; the line keeps the caret."""
    page = game.page
    game.give(wood=3, berries=2, bread=1)
    cow = game.rpc("dev_creatures", kind="cow", dx=2, dy=0, still=600)["spawned"]
    game.sleep(600)
    page.keyboard.press("/")
    game.wait("!!tools && !!serverCmds && $('sayhelp').children.length === 4")
    for line, want in (("/eat item=", ["berries", "bread"]), ("/drop item=w", ["wood"]), ("/craft recipe=plank", ["plank"]),
                       ("/unwear slot=", ["head", "top", "pants", "shoes", "effect"]), ("/step dir=N run=", ["true"]),
                       ("/sign", []), ("/read_sign", ["read_sign"]), ("/eat", ["eat"]), ("/ea", []), ("/say text=\"dig dir=", [])):
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
    game.until(f"({QUIET})()")                                         # (the step answered: what it says, it has said)
    assert game.js("$('toast').style.display") != "block" or "run" not in game.js("$('toastt').textContent")


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
    page.keyboard.type("/write_sign")
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


def test_the_arrows_bring_back_what_you_sent(game):
    """"implement up/down arrow to browse chat/command history": Up goes back through what you sent, Down forward, and
    past the newest the line you were writing is back; begun from a "/", only the commands; kept between visits; the
    arrows are still the list's while a list is being walked."""
    page = game.page

    def send(line, key="Enter"):
        page.keyboard.press(key)
        page.keyboard.type(line)
        page.keyboard.press("Enter")
        game.sleep(250)

    send("hello")
    send("coords", "/")
    send("how are you")
    send("coords", "/")                                        # (again: on, then off; kept once, at its latest place)
    page.keyboard.press("Enter")
    page.keyboard.type("draft")
    seen = []
    for key in ("ArrowUp", "ArrowUp", "ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowDown", "ArrowDown"):
        page.keyboard.press(key)
        seen.append(game.js(LINE))
    assert seen == ["/coords", "how are you", "hello", "hello", "how are you", "/coords", "draft", "draft"], seen
    assert game.js(OPEN) is True
    page.keyboard.press("Escape")
    page.keyboard.press("/")                                   # from a "/": the commands only; Down is the list's
    game.wait("!!serverCmds && $('sayhelp').children.length === 4")
    page.keyboard.press("ArrowDown")
    assert game.js(LINE) == "/" and game.js("$('sayhelp').querySelector('.on b').textContent") == "perf"
    page.keyboard.press("ArrowUp")
    assert game.js(LINE) == "/coords"
    page.keyboard.press("ArrowUp")
    assert game.js(LINE) == "/coords"                          # (the oldest command: it stays)
    page.keyboard.press("ArrowDown")
    assert game.js(LINE) == "/"
    page.fill("#say", "/dig dir=")                             # a list being walked: the arrows are its own
    page.keyboard.press("ArrowDown")
    assert game.js(LINE) == "/dig dir=" and game.js("$('sayhelp').querySelector('.on b').textContent") == "E"
    page.keyboard.press("Escape")
    assert game.js("JSON.parse(localStorage.getItem('nexel-said'))") == ["hello", "how are you", "/coords"]
    page.reload()                                              # kept between visits
    page.wait_for_function("typeof ready !== 'undefined'")
    assert game.js("said") == ["hello", "how are you", "/coords"]
