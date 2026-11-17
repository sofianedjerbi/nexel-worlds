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
    """"Make the homepage more mobile friendly: better menu design (don't change desktop)". Upright: the name, the
    line, the window, one under the other. On its side the window was taller than the screen: the game's name was off
    it and its line ran behind the window; it is beside the name now, whole. Under a thumb the list is buttons: Wake up
    across the window, the others two abreast, each a finger high (they were lines of text 34 px high)."""
    box = """(() => { const b = (e) => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom].map(Math.round); };
      return [b(document.querySelector('#joinbox .menu')), b(document.querySelector('#joinbox .logo')), b($('join')), b($('splash')), b($('watch')), b($('titlesound')), b($('titleopts'))]; })()"""
    for w, h in ((390, 844), (844, 390), (740, 360)):
        page = browser.new_page(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True)
        page.goto(server)
        page.wait_for_function("typeof ready !== 'undefined' && document.querySelectorAll('#racepick button').length === 5")
        menu, logo, join, say, watch, sound, opts = r = page.evaluate(box)
        assert menu[0] >= 0 and menu[1] >= 0 and menu[2] <= w and menu[3] <= h and logo[1] >= 0 and logo[0] >= 0, (w, h, r)     # all of it on the screen
        if w < h:
            assert logo[3] <= say[1] + 2 and say[3] <= menu[1], r           # the name, the line, the window: one under the other
        else:
            assert logo[2] <= menu[0] and say[2] <= menu[0] and logo[3] <= say[1] + 2, r    # the name and its line beside the window, not behind it
        assert join[3] - join[1] >= 48 and join[0] <= menu[0] + 14 and join[2] >= menu[2] - 14, r     # Wake up: across the window, a thumb high
        assert watch[3] - watch[1] >= 44 and opts[3] - opts[1] >= 44 and watch[1] == sound[1] and watch[2] <= sound[0] and opts[1] >= watch[3] and opts[2] - opts[0] >= menu[2] - menu[0] - 28, r   # the others: two abreast, the one left over across
        assert page.evaluate("getComputedStyle($('join')).backgroundColor") == "rgb(255, 241, 168)"       # (lit, whatever row the keys would be on)
        assert not page.evaluate("/Tab/.test($('splash').textContent)")     # (no key to hold on a phone)
        if SHOT:
            page.screenshot(path=f"{SHOT}/phone_{w}.png")
        page.close()
    page = browser.new_page(viewport={"width": 1280, "height": 760})       # a desk's screen: the list as it was
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && document.querySelectorAll('#racepick button').length === 5")
    assert page.evaluate("[getComputedStyle(document.querySelector('#joinbox .menu')).display, getComputedStyle($('watch')).backgroundColor, $('watch').getBoundingClientRect().width > 250]") == ["flex", "rgba(0, 0, 0, 0)", True]
    page.close()


def test_the_first_screen_is_itself_before_any_script_has_come(browser, server):
    """"Instant loading": on a phone's slow line the page was bare text for as long as its seventy scripts took (eight
    seconds measured): the game's own bar over its name, a list without its window, no field for your name. What the
    first picture needs is said in the page itself (its sizes, a phone or not, the first step), so with every script
    held back the first screen is whole: the window, your name's field, Wake up."""
    page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    page.route("**/js/*.js*", lambda r: r.abort())
    page.goto(server, wait_until="domcontentloaded")
    js = page.evaluate
    assert js("[document.body.classList.contains('title'), document.body.classList.contains('touch'), typeof TITLE]") == [True, True, "undefined"]
    shown = lambda q: js(f"(() => {{ const e = document.querySelector('{q}'), r = e.getBoundingClientRect(); return getComputedStyle(e).display !== 'none' && r.width > 0 && r.height > 0; }})()")
    assert shown("#joinbox .menu") and shown("#name") and shown("#join") and shown("#watch") and not shown("#brand") and not shown("#side") and not shown("#email")
    menu = js("(() => { const e = document.querySelector('#joinbox .menu'), r = e.getBoundingClientRect(), c = getComputedStyle(e); return [Math.round(r.width), Math.round(r.bottom), c.backgroundColor, c.boxShadow !== 'none']; })()")
    assert menu[0] >= 280 and menu[1] <= 844 and menu[2] == "rgb(232, 207, 166)" and menu[3], menu      # its window, with its edge
    assert js("document.getElementById('join').getBoundingClientRect().height") >= 48
    page.close()


def test_wake_up_says_the_world_is_still_coming(browser, server):
    """The demo's world takes seconds to come (Python in the page): Wake up pressed meanwhile showed nothing for
    fourteen seconds. The row says so while it waits, and is itself again when the world is there."""
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && typeof TITLE !== 'undefined'")
    label = "document.querySelector('#join span').textContent"
    assert page.evaluate(label) == "Wake up"
    page.evaluate("(() => { document.body.classList.add('booting'); agentWs = {readyState: 0}; titleDraw(); })()")       # (as in the demo: asked to join, the socket not open yet)
    assert page.evaluate(label) == "Waking the world…" and page.evaluate("getComputedStyle($('join'), '::after').animationName") == "booting"
    page.evaluate("(() => { document.body.classList.remove('booting'); agentWs = null; titleDraw(); })()")
    assert page.evaluate(label) == "Wake up" and page.evaluate("getComputedStyle($('join'), '::after').content") == "none"
    page.close()
