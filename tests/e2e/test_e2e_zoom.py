"""Zoom (zoom.js): "zooming is hard, uninturitive and ugly". The wheel is counted in distance, a level glides into the
next, a sign shows where you are, a player's view stops at 2, the level is kept."""

import pytest


@pytest.mark.realtime
def test_a_wheel_notch_is_one_level_and_a_trackpad_swipe_is_not_a_dozen(game):
    page = game.page
    page.mouse.move(600, 300)
    z = game.js("zoom")
    page.mouse.wheel(0, -100)                                  # one notch of a mouse wheel
    game.wait(f"zoom === {z + 1} && performance.now() - ZOOM.stepped > 250", 2000)   # (a swipe right after a step waits its turn: 200 ms)
    # one swipe on a trackpad: forty small events (it used to fly to the end). Sent by the page in one go: sent one by
    # one from here, a slow machine's frames put more than a gesture's pause (220 ms) between two and none counted.
    game.js("(() => { for (let i = 0; i < 40; i++) cv.dispatchEvent(new WheelEvent('wheel', {deltaY: 4, clientX: 600, clientY: 300, bubbles: true, cancelable: true})); return 1; })()")
    game.wait(f"zoom === {z} && !ZOOM.busy", 2000)
    assert game.js("[zoom, ZOOM.to]") == [z, z]                                 # one level, and no more on its way
    assert game.js("localStorage.getItem('nexel-zoom')") == str(z)      # kept for the next visit


def test_a_level_glides_and_the_sign_shows_where_you_are_and_where_it_stops(game):
    game.js("zoom = 3")
    # (the glides, counted as they start: a glide is ZOOM.ms, 140 ms, a quarter of it on the tests' clock: 35 ms. Read after
    # the key, it was seen only if no frame was drawn between the key and the read: one was, and it was over.
    # "cv.getAnimations().length == 1" read 0: main 45878195525)
    game.js("(() => { window.__glides = 0; const a = cv.animate.bind(cv); cv.animate = (...k) => { __glides++; return a(...k); }; return 1; })()")
    game.press("-", 0)
    assert game.js("zoom") == 2 and game.js("__glides") == 1   # drawn wide at once, the picture let down to it
    assert game.js("$('zoomer').classList.contains('show')") and game.js("document.querySelectorAll('#zoomer i.on').length") == 1
    game.wait("cv.getAnimations().length === 0 && getComputedStyle(cv).transform === 'none'", 2000)   # (the glide over: the picture at its size)
    game.press("-", 300)                                       # a player is never a few pixels tall: 2 is the widest
    assert game.js("zoom") == 2 and game.js("$('zoomer').classList.contains('nod')")
    game.page.click("#zoomer b[data-d='1']")                   # the sign's own +
    game.wait("zoom === 3", 2000)
    assert game.js("document.querySelectorAll('#zoomer i.on').length") == 2 and game.js("document.querySelectorAll('#zoomer i').length") == 5
    for _ in range(6):
        game.press("+", 200)
    assert game.js("zoom") == 6
    game.wait("!$('zoomer').classList.contains('show')", 6000)                 # it goes away on its own


def test_the_keys_of_the_main_row_zoom_on_any_layout_and_for_a_watcher_too(game, browser, server):
    """"qwerty -+ does not work. you use the numpad ones ?": the keys right of 0, with or without Shift, and the numpad."""
    game.js("zoom = 3")
    for key, want in (("Equal", 4), ("Minus", 3), ("Shift+Equal", 4), ("Shift+Minus", 3), ("NumpadAdd", 4), ("NumpadSubtract", 3)):
        game.page.keyboard.press(key)
        game.wait(f"zoom === {want}", 2000)
    sign = game.js("(() => { const r = $('zoomer').getBoundingClientRect(), v = $('vitals').getBoundingClientRect(); return [r.left + r.width / 2, r.bottom, v.top]; })()")
    assert abs(sign[0] - 600) < 2 and 0 < sign[2] - sign[1] < 20, sign          # the sign: in the middle, just over the hearts
    game.press("t", 200)                                       # typing a dash in the chat is not a zoom
    game.page.keyboard.type("a-b=c")
    game.sleep(300)
    assert game.js("zoom") == 3
    game.page.keyboard.press("Escape")
    page = browser.new_page(viewport={"width": 1000, "height": 700})            # someone who only watches
    page.goto(f"{server}/?zoom=3&follow={game.name}")
    page.wait_for_function("typeof ready !== 'undefined'")
    page.keyboard.press("Minus")
    page.wait_for_function("zoom === 2", timeout=2000)
    page.keyboard.press("Minus")                               # a watcher may see wide
    page.wait_for_function("zoom === 1", timeout=2000)
    page.close()
