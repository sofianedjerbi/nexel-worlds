"""On a phone: the joystick walks, the main button (held) chops what you face, the HUD fits the screen."""

import random

from game import Game


def touch_game(browser, server, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True, device_scale_factor=3)
    page = ctx.new_page()
    g = Game(page, server)
    g.join(f"ph{random.randint(1000, 9999)}", 3)
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
        g.sleep(500)
        assert g.pos() == (x0 + 2, y0) and g.server()["x"] == x0 + 2
        assert "Chop" in g.js("$('tA').innerText")                            # the button says what it will do
        a = g.js("(() => { const r = $('tA').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
        g.touch("touchStart", *a)                                             # held: chops on
        g.wait("(meObs.self.inventory.wood || 0) > 0", 15000)
        g.touch("touchEnd")
        assert not g.errors, g.errors
    finally:
        ctx.close()
