"""Zoom (zoom.js): "zooming is hard, uninturitive and ugly". The wheel is counted in distance, a level glides into the
next, a sign shows where you are, a player's view stops at 2, the level is kept."""


def test_a_wheel_notch_is_one_level_and_a_trackpad_swipe_is_not_a_dozen(game):
    page = game.page
    page.mouse.move(600, 300)
    z = game.js("zoom")
    page.mouse.wheel(0, -100)                                  # one notch of a mouse wheel
    game.wait(f"zoom === {z + 1}", 2000)
    for _ in range(40):                                        # one swipe on a trackpad: forty small events (it used to fly to the end)
        page.mouse.wheel(0, 4)
        page.wait_for_timeout(8)
    game.sleep(500)
    assert game.js("zoom") == z, game.js("zoom")
    assert game.js("localStorage.getItem('megastructure-zoom')") == str(z)      # kept for the next visit


def test_a_level_glides_and_the_sign_shows_where_you_are_and_where_it_stops(game):
    game.js("zoom = 3")
    game.press("-", 0)
    assert game.js("zoom") == 2 and game.js("cv.getAnimations().length") == 1   # drawn wide at once, the picture let down to it
    assert game.js("$('zoomer').classList.contains('show')") and game.js("document.querySelectorAll('#zoomer i.on').length") == 1
    game.sleep(400)
    assert game.js("cv.getAnimations().length") == 0 and game.js("getComputedStyle(cv).transform") == "none"
    game.press("-", 300)                                       # a player is never a few pixels tall: 2 is the widest
    assert game.js("zoom") == 2 and game.js("$('zoomer').classList.contains('nod')")
    game.page.click("#zoomer b[data-d='1']")                   # the sign's own +
    game.wait("zoom === 3", 2000)
    assert game.js("document.querySelectorAll('#zoomer i.on').length") == 2 and game.js("document.querySelectorAll('#zoomer i').length") == 5
    for _ in range(6):
        game.press("+", 200)
    assert game.js("zoom") == 6
    game.sleep(2200)
    assert not game.js("$('zoomer').classList.contains('show')")                # it goes away on its own
