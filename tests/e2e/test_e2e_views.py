"""What is built over you, two ways (options.js: VIEWS): cut away (the house you are in, in build mode all over the
cursor's floor, is not drawn) or faded (drawn faint). V goes from one to the next, and the Picture page has them.
(Land over you: the HD look's x-ray window, whichever view: test_e2e_hd_window.py.)"""

from test_e2e_floors import go, house

ROW = "document.querySelector('#menu .row.on .name').textContent"


def test_v_goes_through_the_views_and_the_picture_page_has_them(game):
    assert game.js("opt('above')") == "cut"                   # (the usual one)
    seen = []
    for _ in range(2):
        game.press("v", 250)
        seen.append([game.js("opt('above')"), game.toast()])
    assert [s[0] for s in seen] == ["faded", "cut"] and "Faded" in seen[0][1] and "Cut away" in seen[1][1]
    assert game.js("JSON.parse(localStorage.getItem('megastructure-options') || '{}').above") is None     # (back at the usual one: nothing kept)
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab")
    for _ in range(14):
        if game.js(ROW) == "What is built over you":
            break
        game.press("ArrowDown", 40)
    game.press("ArrowRight")
    assert game.js("opt('above')") == "faded"
    game.press("Escape"); game.press("Escape")
    game.js("setOpt('above', 'cut')")


def test_in_a_house_what_is_over_you_is_cut_away_or_faint(game):
    """In the room of a house of two storeys, the floor over you: not drawn (cut away), or faint (faded); from outside, whole."""
    x, y = game.pos()
    x0, y0 = x + 2, y - 7
    house(game, x0, y0)
    floor = (x0 + 3, y0 + 2, 3)
    alpha = lambda: game.js("([x, y, z]) => Floors.alpha(x, y, z)", list(floor))
    go(game, x, y, 0)
    assert alpha() == 1
    go(game, x0 + 3, y0 + 2, 0)
    for view, want in (("cut", 0), ("faded", .12)):
        game.js(f"setOpt('above', '{view}')")
        assert alpha() == want, view
    game.js("setOpt('above', 'cut')")
    assert not game.errors
