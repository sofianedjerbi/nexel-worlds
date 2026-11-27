"""The recipe book without a mouse: every button has its key, the keys are the book's while it is open, and what a
key does is written on it while you play by keys."""

from test_e2e_touch import touch_game
from waits import QUIET

LIST = "[...document.querySelectorAll('#recipes .rcard')].map((c) => c.dataset.name)"
LIT = "[...document.querySelectorAll('#recipes .rcard:not(.no)')].map((c) => c.dataset.name)"
CAPS = "[...document.querySelectorAll('#craft kbd')].filter((k) => getComputedStyle(k).display !== 'none').map((k) => k.textContent)"
OPEN = "['craft', 'bag'].filter((id) => $(id).style.display === 'block').join()"


def test_the_recipe_book_is_done_without_a_mouse(game):
    """Open it with C: the switch is F (it had no key), Enter makes one however long it is held, Shift+Enter five.
    No key acts on the world behind the book (X picked the flower you faced, a number changed what you hold), and I
    goes from the book to the inventory instead of opening it on top."""
    game.give(wood=30)
    game.stamp(0, 1, ["f"])
    game.press("c", 400)
    assert game.js(OPEN) == "craft" and game.js("document.body.classList.contains('bykeys')")
    assert game.js(CAPS) == ["Q", "E", "F", "Enter", "Shift"]                    # under the bookmarks, on the switch, on the two buttons
    hand = game.js("[handSlot, selected]")
    game.press("x", 400)
    game.press("2", 150)
    game.press("`", 150)
    assert game.inv("flower") == 0 and game.js("[handSlot, selected]") == hand and "hands" not in game.toast()   # nothing happened behind the book (` says "Empty hands")
    game.press("f", 250)                                                         # the switch
    assert game.js("craftOnly") is True and game.js("$('craftonly').classList.contains('on')") and game.js(LIST) == game.js(LIT) != []
    game.press("f", 250)
    assert game.js("craftOnly") is False and len(game.js(LIST)) == 5
    game.page.keyboard.down("Enter")                                             # held: it repeats, and makes one
    for _ in range(5):
        game.page.keyboard.down("Enter")
    game.page.keyboard.up("Enter")
    game.until(f"meObs.self.inventory.workbench >= 1 && ({QUIET})()"); game.tick()   # (made, every craft asked answered, and a tick after)
    assert game.inv("workbench") == 1
    for _ in range(4):
        game.press("s", 80)                                                      # (W and S, A and D do what the arrows do)
    assert game.js("craftFocus") == "plank"
    game.press("Shift+Enter", 0)
    game.until(f"meObs.self.inventory.plank >= 1 && ({QUIET})()"); game.tick()   # (five a craft of 1.5 s, its bar: read once it has ended and been answered, not after 1.5 s of sleep, which ended with it)
    assert game.inv("plank") == 10                                               # five at once, two a time
    game.press("i", 250)
    assert game.js(OPEN) == "bag"                                                # one of the two at a time
    game.press("c", 250)
    assert game.js(OPEN) == "craft" and game.js("craftFocus") == "plank"         # (where you left it)
    game.page.mouse.move(400, 300)
    game.page.mouse.move(430, 320)                                               # the mouse is back: the caps are put away
    assert game.js(CAPS) == []
    game.press("d", 200)
    assert game.js("craftTab") == "Tools" and "F" in game.js(CAPS)
    game.press("Escape", 200)
    game.press("e", 500)
    assert game.js(OPEN) == "" and game.inv("flower") == 1                       # shut, E is the game's again


def test_no_key_caps_on_a_phone(browser, server):
    ctx, g = touch_game(browser, server, 844, 390)
    try:
        g.give(wood=30)
        g.js("toggleCraft()")
        g.until(f"$('craft').style.display === 'block' && ({QUIET})()")              # (open, nothing sliding)
        g.js("document.body.classList.add('bykeys')")                             # (as the thumb stick has it)
        assert g.js("document.querySelectorAll('#craft kbd').length") >= 4 and g.js(CAPS) == []
    finally:
        ctx.close()
