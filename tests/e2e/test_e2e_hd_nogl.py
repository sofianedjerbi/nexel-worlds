"""No WebGL 2: the game says so, in a panel of its own (index.html #nogl, hd.js begin). It was the page's dark with the
classic picture's chips and smoke drawn on it: all that was left of that picture, and no word of why."""

from test_e2e_hd_sun import hd

NOGL = "(() => { const g0 = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function (kind, ...a) { return kind === 'webgl2' ? null : g0.call(this, kind, ...a); }; })()"
SHOWN = "(() => { const e = document.getElementById('nogl'); return [!!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 100, e ? e.innerText.trim() : '']; })()"


def test_without_webgl_2_a_panel_says_the_game_cannot_be_drawn(browser, server):
    page = browser.new_page(viewport={"width": 960, "height": 540})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script(NOGL)
    page.goto(server)
    page.wait_for_function("typeof HdLook !== 'undefined' && HdLook.none === true", timeout=20000)
    shown, text = page.evaluate(SHOWN)
    assert shown and text == "This browser can't draw the game (WebGL 2 is missing)", (shown, text)
    assert page.evaluate("getComputedStyle(document.getElementById('nogl')).borderImageSource").startswith("url(")   # (the game's own panel: its pixel frame)
    assert not errors, errors
    page.close()


def test_with_webgl_2_the_panel_is_not_shown(browser, server):
    g = hd(browser, server)
    assert g.js(SHOWN)[0] is False and g.js("HdLook.none") is False and not g.errors
