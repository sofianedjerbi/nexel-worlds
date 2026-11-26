"""On a phone: the joystick walks, the main button (held) chops what you face, the HUD fits the screen."""


import pytest
from game import Game, new_name
from waits import QUIET


def touch_game(browser, server, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True, device_scale_factor=3)
    page = ctx.new_page()
    g = Game(page, server)
    g.join(new_name("ph"), 3)
    g.clear_area()
    cdp = ctx.new_cdp_session(page)
    g.touch = lambda kind, x=0, y=0: cdp.send("Input.dispatchTouchEvent", {
        "type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y}]})
    return ctx, g


def test_play_with_thumbs(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        assert g.js("document.body.classList.contains('touch')")
        hud = g.js("(() => { const r = $('hud').getBoundingClientRect(); return [r.left, r.right]; })()")
        assert hud[0] >= 0 and hud[1] <= 390                                  # the hotbar fits the screen
        g.stamp(3, 0, ["T"])
        g.give(axe=1)
        g.js("selectItem('axe')")
        x0, y0 = g.pos()
        g.touch("touchStart", 80, 600)                                        # left thumb, pushed east
        for i in range(1, 6):
            g.touch("touchMove", 80 + i * 8, 600)
            g.sleep(30)
        g.wait(f"myPos().x === {x0 + 2}", 4000)                               # up to the tree, and stops there
        g.sleep(400)
        g.touch("touchEnd")
        g.until(f"({QUIET})()")                                          # (let go: what it asked answered, you at rest)
        assert g.pos() == (x0 + 2, y0) and g.server()["x"] == x0 + 2
        assert "Chop" in g.js("$('tB').innerText")                            # B (break) says what it will do
        a = g.js("(() => { const r = $('tB').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
        g.touch("touchStart", *a)                                             # held: chops on
        g.wait("(meObs.self.inventory.wood || 0) > 0", 15000)
        g.touch("touchEnd")
        assert not g.errors, g.errors
    finally:
        ctx.close()


def test_crafting_on_a_phone_takes_the_screen_and_a_tap_makes_a_lit_card(browser, server):
    """Open, the recipe book is in the middle of the screen, all of it, and nothing lies over it (the thumbs' buttons
    and the ones at the top did: they are put away while it is open); a tap on a name, a tap on the button."""
    ctx, g = touch_game(browser, server, 844, 390)
    try:
        g.give(wood=4)
        g.js("toggleCraft()")
        g.until(f"({QUIET})()")                                                # (open, nothing sliding)
        box = g.js("(() => { const b = $('craft').getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; })()")
        assert box[0] >= 0 and box[1] >= 0 and box[2] <= 844 and box[3] <= 390 and box[2] - box[0] > 500
        shown = "['ttop', 'tbtns', 'tctx'].map((id) => getComputedStyle($(id)).visibility).join()"
        assert g.js(shown) == "hidden,hidden,hidden"
        assert g.js("craftFocus") == "workbench" and g.js("parseFloat(getComputedStyle(document.querySelector('#craft .line')).fontSize)") >= 18
        assert g.js("document.querySelector('#craft .line').getBoundingClientRect().height") >= 40      # (a name is a finger high)
        for sel in (".rcard[data-name=campfire]", ".rcard[data-name=workbench]", "#craftdetail .cbtn"):   # a tap on a name takes you to it; the button makes it
            x, y = g.js("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }", sel)
            g.page.touchscreen.tap(x, y)
            g.until(f"({QUIET})()")                                     # (lit, or made: the server has answered)
        assert g.inv("workbench") == 1
        g.js("$('craftclose').click()")
        assert g.js(shown) == "visible,visible,visible" and not g.errors
    finally:
        ctx.close()


def test_out_of_your_own_shaft_with_the_thumbs(browser, server):
    """As by keys: B digs down a layer a tap, A puts the ladder where you stand, the stick climbs out. And leaving
    build mode with plans waiting names no key (it said "B to go on building")."""
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        mid = lambda i: g.js(f"(() => {{ const r = $('{i}').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }})()")
        tap = lambda i: (g.page.touchscreen.tap(*mid(i)), g.until(f"({QUIET})()"))   # (what it did answered)
        g.give(pickaxe=1, ladder=1, plank=2)
        g.js("selectItem('pickaxe')")
        x, y = g.pos()
        g.face(1, 0)
        g.wait("$('tB').innerText.includes('Dig down')", 3000)
        for depth in (1, 2, 3, 4):
            g.act("dig_down", **{"with": "pickaxe"})                  # (the shaft, dug from on it: the button digs the block you face)
            g.wait(f"myAt && myAt.z === {-depth} && !myAction", 8000)
        assert g.server()["z"] == -4 and g.js("facingNow(true).it.text") == "Dig into the wall"      # (not on the button while the way out is shown: its own button alone, wayshow.js)
        g.js("selectItem('ladder')")
        g.wait("$('tA').innerText.includes('Place ladder')", 3000)
        tap("tA")
        g.wait(f"combAt({x}, {y}) === 'l'", 5000)
        g.touch("touchStart", 80, 600)                                        # the stick, east: up the ladder
        for i in range(1, 6):
            g.touch("touchMove", 80 + i * 8, 600)
            g.sleep(30)
        g.wait(f"myAt && myAt.x === {x + 1} && myAt.z === 0", 6000)
        g.touch("touchEnd")
        g.wait("!walking && !myAction", 3000)
        s = g.server()
        # out of the shaft, on the ground, east: the tile where it stops is when the thumb is lifted, and on a slow runner
        # the walk went on before the release came (#47: x + 2; a runner's 100 ms frames: x + 3). Not where the stick is let
        # go, the climb out.
        assert s["z"] == 0 and s["y"] == y and s["x"] > x, (s["x"] - x, s["y"] - y, s["z"])
        g.js("selectItem('plank')")
        g.wait("$('tBuild').style.display === 'flex'", 3000)
        at = mid("tBuild")
        tap("tBuild")
        g.wait("Build.on && $('tJump').style.display === 'flex'", 3000)      # (by the step you climbed out by: Jump comes, a moment after)
        assert mid("tBuild") == at, (at, mid("tBuild"))                       # ...and Build has not moved under your thumb (it went 52 px up, Jump in its place: the next tap jumped)
        g.js("Build.S.plans.set('far', {x: Build.S.at.x + 40, y: Build.S.at.y, z: 0, item: 'plank', state: 'todo', tried: true}); $('toast').style.display = 'none'")
        tap("tBuild")
        assert not g.js("Build.on") and "building" not in g.toast() and g.js("$('tBuild').style.display") == "flex"     # (its button stays up while plans wait)
        assert not g.errors, g.errors
    finally:
        ctx.close()


def test_out_of_your_own_shaft_with_the_thumbs_and_a_pickaxe_alone(browser, server):
    """As by keys (test_e2e_climb.py): no ladder. "Dig up" is a button of its own over A and B, there when it is the
    way out, saying what it takes: the step in front of you, the cell over your head."""
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        mid = lambda i: g.js(f"(() => {{ const r = $('{i}').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }})()")
        tap = lambda i: (g.page.touchscreen.tap(*mid(i)), g.until(f"({QUIET})()"))   # (what it did answered)
        g.give(pickaxe=1)
        g.js("selectItem('pickaxe')")
        x, y = g.pos()
        g.face(1, 0)
        g.wait("$('tB').innerText.includes('Dig down')", 3000)
        assert g.js("$('tDig').style.display") != "flex"                       # on the meadow: no such button
        for depth in (1, 2, 3):
            g.act("dig_down", **{"with": "pickaxe"})                  # (the shaft, dug from on it: the button digs the block you face)
            g.wait(f"myAt && myAt.z === {-depth} && !myAction", 8000)
        X, z, said = x, -3, []
        while z < 0:
            aim = g.js("(() => { const c = DigUp.aim(); return c && [c.x, c.y, c.z, c.text]; })()")
            if aim:
                g.wait(f"$('tDig').style.display === 'flex' && $('tDig').innerText === '{aim[3]}'", 3000)
                said.append(aim[3])
                tap("tDig")
                try:
                    g.wait(f"!solidAt({aim[0]}, {aim[1]}, {aim[2]}) && !myAction", 8000)
                except Exception:                                             # (what there is when it does not come)
                    raise AssertionError(g.js(f"JSON.stringify({{aim: {aim!r}, said: {said!r}, me: [myAt.x - {x}, myAt.y - {y}, myAt.z], now: WayShow.cur && WayShow.cur.now, walking: !!walking, act: !!myAction, pending: !!pendingAct, pred: !!pred && performance.now() < pred.until, dig: [$('tDig').style.display, $('tDig').className], toast: $('toast').innerText}})") + " server " + str(g.server()["z"]))
            else:
                g.touch("touchStart", 80, 600)                                # the stick, east: up the step (auto-jump: by itself)
                for i in range(1, 6):
                    g.touch("touchMove", 80 + i * 8, 600)
                    g.sleep(30)
                g.touch("touchEnd")
                try:
                    g.wait(f"myAt && myAt.z > {z}", 6000)
                except Exception:                                             # (what there is when it does not come)
                    raise AssertionError(g.js(f"JSON.stringify({{me: [myAt.x - {x}, myAt.y - {y}, myAt.z], said: {said!r}, cols: [0, 1, 2].map((k) => surfacesAt({x} + k, {y})), walking: !!walking, act: !!myAction, toast: $('toast').innerText}})"))
                g.wait("!walking", 3000)
                X, z = g.js("[myAt.x, myAt.z]")
        assert said == ["Dig a step", "Dig up", "Dig a step"], said             # (the last step is a hop: the sky is over it)
        g.wait("!walking && (!pred || performance.now() > pred.until)", 4000)
        try:                                                                  # (the server's word on it, once it has come: on a runner's 83 ms
            g.wait("meObs && meObs.self.z === 0", 3000)                      #  frames it was read a tick before, still on the step, z -1)
        except Exception:
            pass
        s = g.server()
        assert (s["y"], s["z"]) == (y, 0) and s["x"] >= x + 3, (s["x"] - x, s["y"] - y, s["z"], g.js("[myAt.x - %d, myAt.z]" % x))
        assert not g.errors, g.errors
    finally:
        ctx.close()
