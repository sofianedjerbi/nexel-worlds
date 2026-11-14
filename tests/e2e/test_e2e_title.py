"""The first screen in Chrome: the classic menu. The name beside your character, a list played with the keys."""

import os

SHOT = os.environ.get("TITLE_SHOTS")         # a folder to keep a picture of the screen in

ON = "document.querySelector('#racepick.on, #joinbox .item.on').id"


def test_the_first_screen_is_a_menu_played_with_the_keys(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && IMG.character && IMG.character.complete && document.querySelectorAll('#racepick button').length === 5")
    js = page.evaluate
    assert js("document.body.classList.contains('title')") and js("getComputedStyle($('brand')).display") == "none"   # the name is said once
    assert js("$('joinbox').querySelector('.logo').innerText.replace(/\\s+/g, ' ')") == "NEXEL WORLDS" and js("SPLASH.includes($('splash').textContent)")
    box = js("""(() => { const r = (id) => { const b = (typeof id === 'string' ? $(id) : id).getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
      return {menu: r(document.querySelector('#joinbox .menu')), me: r('titleme'), name: r('name'), logo: r(document.querySelector('#joinbox .logo'))}; })()""")
    m, who, name, logo = box["menu"], box["me"], box["name"], box["logo"]
    assert m[0] >= 0 and m[2] <= 1280 and m[1] >= 0 and m[3] <= 760 and logo[2] < m[0]              # whole on the screen, the name left of it
    assert who[0] >= m[0] and name[2] <= m[2] and name[0] > who[2] and who[1] < name[1] < name[3] <= who[3] + 1   # your name: in the window, beside you
    assert js("document.activeElement === $('name')") and js(ON) == "join"
    page.keyboard.press("Enter")                                           # no name yet: nothing but the field asking for it
    assert js("!me") and js("$('name').classList.contains('need')")
    page.keyboard.type("Ash")
    tint = js("agentTint('Ash')")
    page.wait_for_timeout(200)
    assert js("(() => { const d = $('titleme').getContext('2d').getImageData(0, 0, 24, 26).data; let n = 0; for (let i = 3; i < d.length; i += 4) n += d[i] > 0; return n; })()") > 100   # you are drawn
    page.keyboard.press("ArrowUp")
    assert js(ON) == "racepick"
    page.keyboard.press("ArrowRight")
    assert js("myRace") == "bunny" and js("$('name').value") == "Ash" and js("document.querySelector('#racepick button.on').dataset.race") == "bunny"
    page.keyboard.press("ArrowLeft")
    assert js("myRace") == "cat"
    for want in ("join", "watch", "titlehelp", "titlesound"):
        page.keyboard.press("ArrowDown")
        assert js(ON) == want
    was = js("muted")
    page.keyboard.press("Enter")
    assert js("muted") is (not was) and js("$('titlesoundv').textContent") == ("off" if not was else "on")
    page.keyboard.press("Enter")
    if SHOT:
        page.screenshot(path=f"{SHOT}/title.png")
    page.keyboard.press("ArrowUp"); page.keyboard.press("ArrowUp")
    assert js(ON) == "watch"
    page.keyboard.press("Enter")                                           # just watch: the menu goes, the brand is back
    assert js("$('joinbox').style.display") == "none" and js("getComputedStyle($('brand')).display") != "none"
    page.click("#brand")                                                   # and comes back from the brand
    assert js("document.body.classList.contains('title')")
    page.click("#join")
    page.wait_for_function("me === 'Ash' && meObs", timeout=25000)
    assert js("$('joinbox').style.display") == "none" and not js("document.body.classList.contains('title')")
    assert tint and not errors, errors
    page.close()


def test_the_first_screen_fits_a_phone(browser, server):
    page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && document.querySelectorAll('#racepick button').length === 5")
    r = page.evaluate("""(() => { const b = (e) => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
      return [b(document.querySelector('#joinbox .menu')), b(document.querySelector('#joinbox .logo')), b($('join')), b($('splash'))]; })()""")
    menu, logo, join, say = r
    assert menu[0] >= 0 and menu[2] <= 390 and menu[3] <= 844 and logo[3] <= say[1] + 2 and say[3] <= menu[1], r   # the name, the line, the window: one under the other
    assert join[3] - join[1] >= 30                                         # a row a thumb can hit
    if SHOT:
        page.screenshot(path=f"{SHOT}/phone.png")
    page.close()
