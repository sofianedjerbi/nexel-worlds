"""Two people: chat, giving, mail; a spectator watching; boats."""

import pytest
from conftest import open_game


@pytest.fixture
def friend(browser, server, game):
    """A second player standing two tiles east of the first."""
    g = open_game(browser, server)
    x, y = game.pos()
    g.rpc("dev_teleport", x=x + 2, y=y)
    g.sleep(1200)
    yield g
    errors = g.errors
    g.page.close()
    assert not errors, f"page errors: {errors}"


def test_chat_shows_and_fades(game, friend):
    game.press("Enter", 200)
    game.page.keyboard.type("hello over there")
    game.press("Enter", 1200)
    for g in (game, friend):                                 # both see it in the chat and as a bubble
        assert "hello over there" in g.js("$('chatlog').innerText")
        assert g.js("bubbles.some((b) => b.text === 'hello over there')")
    friend.sleep(10500)
    assert friend.js("[...$('chatlog').children].pop().classList.contains('old')")   # faded away


def test_give_and_see_each_other(game, friend):
    game.give(berries=3)
    assert game.js(f"[...ents.values()].some((q) => q.e && q.e.name === '{friend.name}')")
    assert friend.name in game.js("$('agents').innerText")
    game.hold_item("berries")
    x, y = friend.pos()
    me = game.pos()
    game.js(f"perform({{x: {x}, y: {y}}}, intent({{x: {x}, y: {y}}}, false))")
    game.sleep(1000)
    assert friend.inv("berries") == 1 and game.inv("berries") == 2


def test_letters_through_a_mailbox(game, friend):
    game.give(mailbox=1)
    game.hold_item("mailbox")
    game.face(1, 0)
    game.press("Space", 800)
    game.press("0", 100)
    game.press("Space", 500)                                 # open the mailbox panel
    assert game.js("$('mail').style.display") == "block"
    game.page.fill("#letter", "come see my farm")
    game.page.click("#postbtn")
    game.sleep(700)
    game.press("Escape", 200)
    mx, my = game.pos()[0] + 1, game.pos()[1]
    friend.js(f"(() => {{ actTarget = {{x: {mx}, y: {my}}}; openMailPanel(actTarget); }})()")
    friend.page.click("#openbtn")
    friend.sleep(800)
    assert "come see my farm" in friend.js("$('letters').innerText")


def test_watching_as_a_spectator(browser, server, game):
    page = browser.new_page(viewport={"width": 1000, "height": 700})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined'")
    page.click("#watch")
    page.wait_for_function("blocks.size > 0", timeout=8000)
    page.wait_for_timeout(1500)
    assert game.name in page.evaluate("$('agents').innerText")
    page.close()
    assert not errors


def test_boat_launch_sail_and_moor(game):
    game.stamp(1, -3, ["~~~~~~", "~~~~~~", "~~~~~~"])        # a pond to the north-east
    game.give(boat=1)
    game.rpc("dev_teleport", x=game.pos()[0] + 1, y=game.pos()[1] - 0)
    game.sleep(800)
    game.hold_item("boat")
    game.face(0, -1)
    game.press("Space", 800)
    x, y = game.pos()
    assert game.tile(0, -1) == "V"
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")       # board
    game.sleep(800)
    assert game.server()["sailing"]
    game.hold(["w"], 380)
    game.sleep(600)
    assert game.server()["sailing"]
    game.hold(["s"], 900)                                    # back to the shore: you step out, the boat stays
    game.sleep(800)
    assert not game.server()["sailing"]
