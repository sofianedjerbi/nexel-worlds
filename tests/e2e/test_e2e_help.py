"""The help in Chrome: a window of four short pages, a key and a few words a row."""

import os

SHOT = os.environ.get("HELP_SHOTS")          # a folder to keep a picture of each page in


def test_the_help_is_a_window_of_short_pages(game):
    game.press("h")
    box = game.js("(() => { const r = $('help').getBoundingClientRect(); return [r.left + r.width / 2, innerWidth / 2, r.width, r.height, innerHeight]; })()")
    assert abs(box[0] - box[1]) < 2 and box[3] < box[4]                          # in the middle, whole on the screen
    assert game.js("[...document.querySelectorAll('#help .tab')].map((t) => t.textContent)") == ["Move", "Do", "Carry", "Talk"]
    x0, sizes = game.server()["x"], []
    for n, name in enumerate(["Move", "Do", "Carry", "Talk"]):
        assert game.js("document.querySelector('#help .tab.on').textContent") == name
        rows = game.js("""[...document.querySelectorAll('#help .row')].map((r) => { const w = r.querySelector('.what'), b = r.getBoundingClientRect(), q = w.getBoundingClientRect();
          return [r.querySelectorAll('kbd').length, w.textContent.length, q.height / parseFloat(getComputedStyle(w).lineHeight), q.right <= b.right, r.scrollWidth <= r.clientWidth]; })""")
        assert 1 <= len(rows) <= 5, rows                                         # a few things to read at once
        assert all(k >= 1 and 0 < chars <= 24 and lines <= 1.01 and inside and fits for k, chars, lines, inside, fits in rows), (name, rows)
        sizes.append(game.js("$('help').getBoundingClientRect().height"))
        if SHOT:
            game.page.screenshot(path=f"{SHOT}/help{n}.png")
        game.press("ArrowRight")
    assert game.js("document.querySelector('#help .tab.on').textContent") == "Move"   # round to the first
    assert len(set(sizes)) == 1, sizes                                           # every page the same size: nothing jumps
    assert game.server()["x"] == x0                                              # the arrows turned pages: they did not walk you
    game.page.click("#help .tab[data-i='2']")
    assert game.js("document.querySelector('#help .tab.on').textContent") == "Carry"
    game.press("h")
    assert game.js("$('help').style.display") == "none"
    assert not game.errors
