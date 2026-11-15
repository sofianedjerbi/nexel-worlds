"""The first screen's background (web/js/title_scene.js): an island of the page's own, with its little life."""

CAST = "[...ents.values()].map((p) => [p.e.kind, p.e.name || '', p.e.x - (-8000), p.e.y - (-8000), !!p.e.sail, !!p.e.swim])"
ASKED = "window.__asked"


def open_page(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("window.__asked = []; const W = window.WebSocket; window.WebSocket = function (...a) { const s = new W(...a), send = s.send.bind(s);"
                         " s.send = (m) => { try { window.__asked.push(JSON.parse(m).op); } catch (e) {} return send(m); }; return s; }; window.WebSocket.prototype = W.prototype;")
    page.goto(server)
    return page, errors


def test_the_first_screen_shows_an_island_of_its_own_at_once(browser, server):
    """Behind the first screen there was the world, once the server had sent it (in the demo, once Python had
    started: many seconds of an empty screen). There is an island that is part of the page: it shows as soon as the
    pictures are loaded, asks the server for no land, and has its own life: Mira walks to her field, Pip sails round,
    Lou swims the pond, hens in their pen; the hours pass; the view drifts."""
    page, errors = open_page(browser, server)
    page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on && !arrivingNow", timeout=10000)
    assert page.evaluate("blocks.size") >= 6 and page.evaluate("[...blocks.values()].every((b) => b.bx < -200 && b.by < -200)")      # its land: far from where anyone lives
    cast = page.evaluate(CAST)
    names = sorted(c[1] for c in cast if c[0] == "agent")
    assert names == ["Lou", "Mira", "Pip", "Tobi"] and sorted(c[0] for c in cast if c[0] != "agent") == ["chick", "chicken", "chicken", "chicken", "cow", "cow"]
    look = "(() => { const c = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, kinds = new Set(); for (let i = 0; i < c.length; i += 4 * 97) kinds.add(c[i] >> 3 << 10 | c[i + 1] >> 3 << 5 | c[i + 2] >> 3); return kinds.size; })()"
    assert page.evaluate(look) > 40                                 # drawn: land, water, things (not one colour)
    start, cam0, phase0 = {c[1] or f"{c[0]}{i}": c[2:4] for i, c in enumerate(cast)}, page.evaluate("[cam.x, cam.y]"), page.evaluate("clock.phase")
    page.wait_for_timeout(4000)
    cast = page.evaluate(CAST)
    now = {c[1] or f"{c[0]}{i}": c[2:4] for i, c in enumerate(cast)}
    assert now["Mira"] != start["Mira"] and now["Pip"] != start["Pip"] and now["Lou"] != start["Lou"] and now["Tobi"] == start["Tobi"]     # they go their ways; Tobi stays at his tree
    pip, lou = [c for c in cast if c[1] == "Pip"][0], [c for c in cast if c[1] == "Lou"][0]
    wet = "([x, y]) => { const t = tile(-8000 + x, -8000 + y); return !!t && '~=()'.includes(t[1]); }"
    assert pip[4] and lou[5] and page.evaluate(wet, pip[2:4]) and page.evaluate(wet, lou[2:4])           # the boat and the duck are on water
    pen = page.evaluate("TITLE_MAP.cast.pen")
    assert all(pen[0] <= c[2] <= pen[2] and pen[1] <= c[3] <= pen[3] for c in cast if c[0] in ("chicken", "chick"))      # the hens keep to their pen
    assert page.evaluate("clock.phase") > phase0 and page.evaluate("[cam.x, cam.y]") != cam0             # the hours pass; the view drifts
    assert set(page.evaluate(ASKED)) <= {"recipes", "agents", "metrics"}, page.evaluate(ASKED)           # the server was asked for no land, and told of nothing watched
    assert page.evaluate("document.querySelector('#joinbox .logo') !== null && titleOpen()")
    page.click("#watch")                                            # just watch: the island is forgotten, the world's own land comes
    page.wait_for_function("!TitleScene.on && blocks.size > 0 && !arrivingNow", timeout=20000)
    assert page.evaluate("[...blocks.values()].every((b) => Math.abs(b.bx) < 20 && Math.abs(b.by) < 20)") and not any(c[1] in ("Mira", "Pip") for c in page.evaluate(CAST))
    assert {"watch", "region"} <= set(page.evaluate(ASKED)) and page.evaluate("[cam.x, cam.y]") == [0, 0]
    page.close()
    assert not errors, errors


def test_waking_up_leaves_the_island_for_the_world(game):
    """A player who wakes up: the island's land and its cast are gone, the land round them is the world's."""
    assert game.js("!TitleScene.on && typeof TITLE_MAP === 'object'")
    x, y = game.pos()
    assert game.js("[...blocks.values()].every((b) => b.bx > -200 && b.by > -200)") and game.js(f"!!tile({x}, {y})")
    assert not any(c[1] in ("Mira", "Tobi", "Pip", "Lou") for c in game.js("[...ents.values()].map((p) => [p.e.kind, p.e.name || ''])"))
