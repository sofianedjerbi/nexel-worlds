"""The home screen is never zoomed ("do not allow zooming out / in in the homescreen, it breaks the view"): the
island is at the first level whatever level was kept from the game, the wheel and -/+ do nothing there, and the
kept level comes back as you wake up."""

import pytest


@pytest.mark.e2e
def test_the_home_screen_is_not_zoomed_and_the_game_keeps_your_level(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    page.goto(server)
    page.evaluate("localStorage.setItem('nexel-zoom', '5')")
    page.reload()
    page.wait_for_function("typeof titleOpen === 'function' && titleOpen() && typeof zoom !== 'undefined'", timeout=20000)
    page.wait_for_timeout(500)
    assert page.evaluate("zoom") == 3
    page.mouse.move(640, 380)
    for _ in range(6):
        page.mouse.wheel(0, 400)
        page.wait_for_timeout(120)
    page.keyboard.press("-")
    page.wait_for_timeout(300)
    assert page.evaluate("zoom") == 3 and page.evaluate("localStorage.getItem('nexel-zoom')") == "5"
    page.evaluate("zoomForTitle(false)")
    assert page.evaluate("zoom") == 5
    page.close()
