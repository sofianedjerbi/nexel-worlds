"""A phone's taps and its HUD (touch.js, ui.js hudFit, bag.js): a window opened by a tap stays open (the tap's own click
went to the "x" that had come up under the finger: Items and Craft opened and shut at once, held upright); on its side
the HUD is one band, 14% of the height at most, a slot 40 px at least; the inventory's label, upright, is on no cell."""
from test_e2e_touch import touch_game

BOX = "(s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }"


def tap(g, sel):
    x, y, w, h = g.js(BOX, sel)
    g.page.touchscreen.tap(x + w / 2, y + h / 2)


def test_a_tap_opens_a_window_and_it_stays_open(browser, server):
    for w, h in ((390, 844), (844, 390)):
        ctx, g = touch_game(browser, server, w, h)
        try:
            for sel, shown, shut in (("#tBag", "$('bag').style.display === 'block'", "#bagclose"), ("#tCraft", "$('craft').style.display === 'block'", "#craftclose"),
                                     ("#tMenu", "getComputedStyle($('menu')).display !== 'none'", None), ("#goalhint", "getComputedStyle($('goals')).display === 'block'", None)):
                tap(g, sel)
                g.wait(shown, 2000)
                g.sleep(400)                                   # (the click that follows the touch has come by now)
                assert g.js(shown), (w, sel)
                if shut:                                       # its own "x", under the same finger held upright: a tap of its own shuts it
                    tap(g, shut)
                    g.wait(f"!({shown})", 2000)
                else:
                    g.js("(() => { closeMenu(); if (!goalsOff) toggleGoals(); return 1; })()")
                    g.wait(f"!({shown})", 2000)
            assert not g.errors
        finally:
            ctx.close()


def test_on_its_side_the_hud_is_one_low_band(browser, server):
    ctx, g = touch_game(browser, server, 844, 390)
    try:
        g.wait("hudSide", 3000)
        g.settle("$('hud').getBoundingClientRect().height < 60")
        hud, slot, vit, xp, b = (g.js(BOX, s) for s in ("#hud", ".slot", "#vitals", "#xpwrap", "#tB"))
        assert 390 - hud[1] <= .14 * 390, hud                           # the band, and what is under it
        assert slot[2] >= 40 and slot[3] >= 40, slot                    # a slot under a finger
        bar = g.js(BOX, "#hotbar")
        assert vit[0] + vit[2] <= bar[0] and xp[0] + xp[2] <= bar[0] and vit[1] + vit[3] <= xp[1] + 1     # the hearts and the food over the experience, at the bar's left
        assert hud[0] >= 0 and hud[0] + hud[2] <= b[0], (hud, b)        # clear of the thumbs' buttons
        assert not g.errors
    finally:
        ctx.close()


def test_upright_the_inventorys_label_is_on_no_cell(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        g.give(axe=1, wood=3)
        tap(g, "#tBag")
        g.wait("$('bag').style.display === 'block'", 2000)
        g.sleep(300)
        tap(g, "#bagbar .cell")
        g.wait("$('bagnote').innerText.includes('Axe') || $('bagnote').innerText.includes('Wood')", 2000)
        note, bag = g.js(BOX, "#bagnote"), g.js(BOX, "#bag")
        cells = g.js("[...document.querySelectorAll('#bag .cell, #bag .bkey')].filter((e) => e.offsetWidth).map((e) => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; })")
        hit = [c for c in cells if c[0] < note[0] + note[2] and note[0] < c[0] + c[2] and c[1] < note[1] + note[3] and note[1] < c[1] + c[3]]
        assert not hit and not g.js("document.querySelector('#bag .btip')"), hit
        assert bag[1] >= 0 and bag[1] + bag[3] <= 844 and all(c[2] >= 44 and c[3] >= 44 for c in cells), bag
        assert not g.errors
    finally:
        ctx.close()


def test_the_hd_looks_readout_is_the_only_one_and_lies_on_nothing(browser, server):
    """/perf in the HD look: two readouts were written, the new one on the old one and on the chat."""
    from game import Game, new_name
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
    try:
        g = Game(ctx.new_page(), server)
        g.join(new_name("pf"), 2, look="hd")
        g.js("(() => { flip('perf', 'Performance'); return 1; })()")
        g.wait("document.getElementById('hdperf') && $('hdperf').textContent.includes('fps')", 6000)
        g.sleep(400)
        box = lambda s: g.js(BOX, s)
        p, lows = box("#hdperf"), [b[1] + b[3] for b in (box("#goalhint"), box("#chatlog")) if b[3]]
        assert g.js("$('xyz').textContent") == "" and p[1] >= max(lows) and p[0] >= 0 and p[0] + p[2] <= box("#ttop")[0], (p, lows)
        g.js("(() => { flip('perf', 'Performance'); return 1; })()")
        assert not g.errors
    finally:
        ctx.close()
