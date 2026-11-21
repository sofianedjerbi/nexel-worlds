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
    for want in ("join", "titlehelp", "titlesound"):
        page.keyboard.press("ArrowDown")
        assert js(ON) == want
    was = js("muted")
    page.keyboard.press("Enter")
    assert js("muted") is (not was) and js("$('titlesoundv').textContent") == ("off" if not was else "on")
    page.keyboard.press("Enter")
    if SHOT:
        page.screenshot(path=f"{SHOT}/title.png")
    assert js("document.getElementById('watch') === null")                # (no "Just watch": you play)
    page.click("#join")
    page.wait_for_function("me === 'Ash' && meObs", timeout=25000)
    assert js("$('joinbox').style.display") == "none" and not js("document.body.classList.contains('title')")
    assert tint and not errors, errors
    page.close()


def test_the_first_screen_fits_a_phone(browser, server):
    """"Make the homepage more mobile friendly: better menu design (don't change desktop)". Upright: the name, the
    line, the window, one under the other. On its side the window was taller than the screen: the game's name was off
    it and its line ran behind the window; it is beside the name now, whole. Under a thumb the list is buttons: Wake up
    across the window, the others (Sound, Settings) two abreast, each a finger high (they were lines of text 34 px high)."""
    box = """(() => { const b = (e) => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom].map(Math.round); };
      return [b(document.querySelector('#joinbox .menu')), b(document.querySelector('#joinbox .logo')), b($('join')), b($('splash')), b($('titlesound')), b($('titleopts'))]; })()"""
    for w, h in ((390, 844), (844, 390), (740, 360)):
        page = browser.new_page(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True)
        page.goto(server)
        page.wait_for_function("typeof ready !== 'undefined' && document.querySelectorAll('#racepick button').length === 5")
        menu, logo, join, say, sound, opts = r = page.evaluate(box)
        assert menu[0] >= 0 and menu[1] >= 0 and menu[2] <= w and menu[3] <= h and logo[1] >= 0 and logo[0] >= 0, (w, h, r)     # all of it on the screen
        if w < h:
            assert logo[3] <= say[1] + 2 and say[3] <= menu[1], r           # the name, the line, the window: one under the other
        else:
            assert logo[2] <= menu[0] and say[2] <= menu[0] and logo[3] <= say[1] + 2, r    # the name and its line beside the window, not behind it
        assert join[3] - join[1] >= 48 and join[0] <= menu[0] + 14 and join[2] >= menu[2] - 14, r     # Wake up: across the window, a thumb high
        assert sound[3] - sound[1] >= 44 and opts[3] - opts[1] >= 44 and sound[1] == opts[1] and sound[2] <= opts[0] and sound[1] >= join[3], r   # the others: two abreast, under Wake up
        assert page.evaluate("getComputedStyle($('join')).backgroundColor") == "rgb(255, 241, 168)"       # (lit, whatever row the keys would be on)
        assert not page.evaluate("/Tab/.test($('splash').textContent)")     # (no key to hold on a phone)
        if SHOT:
            page.screenshot(path=f"{SHOT}/phone_{w}.png")
        page.close()
    page = browser.new_page(viewport={"width": 1280, "height": 760})       # a desk's screen: the list as it was
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && document.querySelectorAll('#racepick button').length === 5")
    assert page.evaluate("[getComputedStyle(document.querySelector('#joinbox .menu')).display, getComputedStyle($('titlehelp')).backgroundColor, $('titlehelp').getBoundingClientRect().width > 250]") == ["flex", "rgba(0, 0, 0, 0)", True]
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
    assert shown("#joinbox .menu") and shown("#name") and shown("#join") and shown("#titlesound") and not shown("#brand") and not shown("#side") and not shown("#email")
    menu = js("(() => { const e = document.querySelector('#joinbox .menu'), r = e.getBoundingClientRect(), c = getComputedStyle(e); return [Math.round(r.width), Math.round(r.bottom), c.backgroundColor, c.boxShadow !== 'none']; })()")
    assert menu[0] >= 280 and menu[1] <= 844 and menu[2] == "rgb(232, 207, 166)" and menu[3], menu      # its window, with its edge
    assert js("document.getElementById('join').getBoundingClientRect().height") >= 48
    page.close()


def test_wake_up_says_the_world_is_still_coming(browser, server):
    """The demo's world takes seconds to come (Python in the page): Wake up pressed meanwhile showed nothing for
    fourteen seconds. The row says so while it waits, and is itself again when the world is there. The strip at its
    foot is as long as the share of the world that has come (local.js says it in px: --boot-w), on a dark track."""
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && typeof TITLE !== 'undefined'")
    label = "document.querySelector('#join span').textContent"
    assert page.evaluate(label) == "Wake up"
    page.evaluate("(() => { document.body.classList.add('booting'); agentWs = {readyState: 0}; titleDraw(); })()")       # (as in the demo: asked to join, the socket not open yet)
    assert page.evaluate(label) == "Waking the world…" and page.evaluate("getComputedStyle($('join'), '::after').width") == "0px"
    page.evaluate("$('join').style.setProperty('--boot-w', '96px')")
    assert page.evaluate("[getComputedStyle($('join'), '::after').width, getComputedStyle($('join'), '::after').animationName, getComputedStyle($('join'), '::before').width === $('join').clientWidth + 'px']") == ["96px", "none", True]
    page.evaluate("(() => { document.body.classList.remove('booting'); agentWs = null; titleDraw(); })()")
    assert page.evaluate(label) == "Wake up" and page.evaluate("getComputedStyle($('join'), '::after').content") == "none"
    page.close()


def test_the_island_is_there_at_once_as_a_still_picture_and_comes_in_over_it_in_the_hd_look(browser, server):
    """"I want the demo background to load beautifully asap": behind the first screen's window there was the sea's flat
    colour until every picture of the game had come (seven seconds on a slow line), then the island a block at a
    time. Its still picture is asked for first of all (tools/build_title_poster.py: what the game paints at the
    island's first moment, nobody on it); the island comes in over it once all of it is made, the view held still
    until it has, the name and the window where they were.
    "Update main menu to the new voxel view": the island was the flat picture of the classic look, the game's own look
    came only once you had woken up. It is drawn by the HD look (hd.js: its eye on the middle of the view): the tilted
    land, its sky over it; so is its still picture. And you wake up from it into the world, in the same look."""
    # the HD look's picture as the screen shows it: how many colours, how blue its top row is (sky), how green its lower half (meadow)
    seen = """() => { const d = HdLook.read(0, 0, cv.width, cv.height).data, w = cv.width, h = cv.height, kinds = new Set(); let sky = 0, land = 0, n = 0, clear = 0;
      for (let i = 0; i < d.length; i += 4 * 97) { kinds.add(d[i] >> 3 << 10 | d[i + 1] >> 3 << 5 | d[i + 2] >> 3); if (d[i + 3] === 0) clear++; }
      for (let x = 2; x < w; x += 7) { const a = (2 * w + x) * 4, b = (Math.floor(h * .7) * w + x) * 4; n++; if (d[a + 2] >= d[a] && d[a + 2] > 150) sky++; if (d[b + 1] > d[b + 2] + 20) land++; }
      return {kinds: kinds.size, sky: sky / n, land: land / n, clear}; }"""
    boxes = "[document.querySelector('#joinbox .logo'), document.querySelector('#joinbox .menu'), $('join')].map((e) => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })"
    still = "Math.abs(cam.x - TitleScene.S.ox - TitleScene.S.C.centre[0]) + Math.abs(cam.y - TitleScene.S.oy - TitleScene.S.C.centre[1] - TITLE_DY)"
    for kw, zoom, small in ((dict(viewport={"width": 1281, "height": 760}), 3, False), (dict(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3), 2, True),
                            (dict(viewport={"width": 844, "height": 390}, has_touch=True, is_mobile=True, device_scale_factor=3), 2, True)):
        page = browser.new_page(**kw)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("**/js/title_scene.js*", lambda r: (page.wait_for_timeout(700), r.continue_()))        # (the island's own script late: its picture is there before it)
        page.goto(server, wait_until="commit")
        page.wait_for_function("!!document.querySelector('#poster.in')", timeout=5000)
        js = page.evaluate
        assert js("[typeof TitleScene, document.body.classList.contains('scene'), getComputedStyle(document.getElementById('c')).opacity, /title_hd_s\\.webp/.test(document.getElementById('poster').currentSrc), /title_hd\\.webp/.test(document.getElementById('poster').currentSrc)]") == ["undefined", False, "0", small, not small]
        # the still picture is the HD look's: sky along its top, a whole number of screen px an art px
        img = js("""(() => { const img = document.getElementById('poster'), c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = 4; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
          const d = g.getImageData(0, 0, c.width, 1).data; let sky = 0; for (let x = 0; x < c.width; x++) if (d[x * 4 + 2] >= d[x * 4] && d[x * 4 + 2] > 150) sky++; return [sky / c.width, img.getBoundingClientRect().width / img.naturalWidth]; })()""")
        assert img[0] > .9 and img[1] == zoom, img
        before = js(boxes)
        page.wait_for_function("document.body.classList.contains('scene')", timeout=30000)
        assert js(still) < 1e-6 and js(boxes) == before, (kw["viewport"], js(still), before, js(boxes))      # the view has not moved; the name and the window are where they were
        assert js("[HdLook.live, HdLook.builds > 0, getComputedStyle(document.getElementById('hd')).display, !!HdLook.eye, Curve.on]") == [True, True, "block", True, True]
        got = js(seen)
        assert got["kinds"] > 40 and got["clear"] == 0 and got["sky"] > .8 and got["land"] > .5, (kw["viewport"], got)      # drawn, all of it: the sky over the land (not the clear colour, not one flat colour)
        page.wait_for_function("getComputedStyle(document.getElementById('hd')).opacity === '1' && getComputedStyle(document.getElementById('poster')).visibility === 'hidden'", timeout=5000)
        page.wait_for_function(still + " > .05", timeout=20000)   # then the view goes after someone, as ever
        assert js(boxes) == before
        if not small:                                             # the menu still works: you wake up, in the world, in the same look, its eye on you
            page.fill("#name", "Hedy")
            page.click("#join")
            page.wait_for_function("me === 'Hedy' && meObs && !TitleScene.on && HdLook.eye === null && HdLook.live && !HdLook.busy && !arrivingNow", timeout=25000)
            assert js("$('joinbox').style.display") == "none" and js("[...blocks.values()].every((b) => b.bx > -200 && b.by > -200)")
            assert js(seen)["kinds"] > 20
        page.close()
        assert not errors, errors
