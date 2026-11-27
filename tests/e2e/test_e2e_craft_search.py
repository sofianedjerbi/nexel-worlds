"""The crafting book's search ("add a research feature in the crafting menu"): a name, or what a thing is made of,
in every kind at once; its letters are its own; the arrows, Enter and Esc still do their work from it."""

from waits import QUIET


ROWS = "[...$('recipes').querySelectorAll('.rcard')].map((d) => d.dataset.name)"
IN = "document.activeElement === $('craftfind')"


def test_the_book_is_searched_by_name_and_by_what_things_are_made_of(game):
    page = game.page
    game.give(wood=4, fiber=4, plank=2)
    game.press("c", 500)
    first = game.js(ROWS)
    game.press("/", 200)                                       # the key of the search
    assert game.js(IN) and game.js("$('craftfind').value") == ""
    page.keyboard.type("bed")
    game.until(f"JSON.stringify({ROWS}) === '[\"bed\"]'")
    assert game.js(ROWS) == ["bed"] and game.js("craftFocus") == "bed" and game.js("$('craftmore').textContent").startswith("Search")
    assert game.js("document.querySelectorAll('#crafttabs .ctab.on').length") == 0          # no kind is the one: all are searched
    page.keyboard.press("Escape")                              # empties it: the kind's list is back
    assert game.js(IN) and game.js("$('craftfind').value") == "" and game.js(ROWS) == first
    page.keyboard.type("fiber")                                # nothing is called fiber: what is made of it
    game.until("$('craftfind').value === 'fiber' && craftView().all.includes('rope')")
    found = game.js("craftView().all")
    assert {"rope", "torch", "name_tag", "flag"} <= set(found) and "workbench" not in found
    page.keyboard.type("zz")
    game.until("$('recipes').textContent.includes('Nothing called')")
    assert game.js(ROWS) == [] and "Nothing called" in game.js("$('recipes').textContent")
    page.fill("#craftfind", "name")
    game.until(f"{ROWS}[0] === 'name_tag'")
    assert game.js(ROWS)[0] == "name_tag"
    at = game.pos()
    page.keyboard.type(" wasd")                                # (letters: nobody walks, no kind turns)
    assert game.pos() == at and game.js("isOpen('craft')")
    page.fill("#craftfind", "name tag")
    game.until("craftFocus === 'name_tag'")
    page.keyboard.press("Enter")                               # made from the search
    game.until(f"({QUIET})()")                           # (made: the server has answered)
    assert game.inv("name_tag") == 1
    page.fill("#craftfind", "wall")
    game.until(f"$('craftfind').value === 'wall' && {ROWS}.length >= 2")
    two = game.js(ROWS)
    assert len(two) >= 2
    page.keyboard.press("ArrowDown")
    assert game.js("craftFocus") == two[1]
    page.keyboard.press("Escape")                              # empties
    page.keyboard.press("Escape")                              # leaves the search
    assert not game.js(IN) and game.js("isOpen('craft')")
    game.press("e", 200)                                       # the book's keys again
    assert game.js("craftTab") != "Basics"
    page.keyboard.press("Escape")
    assert not game.js("isOpen('craft')")
