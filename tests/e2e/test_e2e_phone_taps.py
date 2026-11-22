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
        tap(g, "#bagbar .cell[draggable=true]")                      # (a cell with a thing: the first, the hand, is kept empty)
        g.wait("$('bagnote').innerText.includes('Axe') || $('bagnote').innerText.includes('Wood')", 2000)
        note, bag = g.js(BOX, "#bagnote"), g.js(BOX, "#bag")
        cells = g.js("[...document.querySelectorAll('#bag .cell, #bag .bkey')].filter((e) => e.offsetWidth).map((e) => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; })")
        hit = [c for c in cells if c[0] < note[0] + note[2] and note[0] < c[0] + c[2] and c[1] < note[1] + note[3] and note[1] < c[1] + c[3]]
        assert not hit and not g.js("document.querySelector('#bag .btip')"), hit
        assert bag[1] >= 0 and bag[1] + bag[3] <= 844 and all(c[2] >= 44 and c[3] >= 44 for c in cells), bag
        assert not g.errors
    finally:
        ctx.close()


def test_the_debug_screen_is_the_only_readout_and_stands_over_the_top_left_with_the_goals_and_chat_hidden(browser, server):
    """/perf in the HD look: two readouts were written, the new one on the old one and on the chat. Now one, the debug
    screen (f3.js), opened on a phone by holding the goals' chip; its lines in the screen's width."""
    from game import Game, new_name
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
    try:
        g = Game(ctx.new_page(), server)
        g.join(new_name("pf"), 2)
        g.js("F3.set(false)")
        hold = "(k) => $('goalhint').dispatchEvent(new PointerEvent(k, {bubbles: true, pointerType: 'touch'}))"
        g.js(hold, "pointerdown")
        g.sleep(700)                                           # (half a second held)
        g.js(hold, "pointerup")
        g.wait("F3.on && $('f3').innerText.includes('fps') && $('f3').innerText.includes('HD look')", 6000)
        box = lambda s: g.js(BOX, s)
        p = box("#f3")
        widest = g.js("Math.max(...[...document.querySelectorAll('#f3 .f3c div')].map((d) => d.getBoundingClientRect().right))")
        hid = g.js("['goalhint', 'chatlog'].map((id) => getComputedStyle($(id)).visibility)")
        assert not g.js("['xyz', 'debug', 'hdperf'].filter((id) => document.getElementById(id))") and p[1] <= 8 and p[0] >= 0 and widest <= 390 and hid == ["hidden", "hidden"], (p, widest, hid)   # (the top left, as F3 is; what it covers is hidden, not pushed down)
        g.js("$('f3').click()")                                # (a tap on its lines closes it: the chip is under it)
        g.wait("!F3.on && getComputedStyle($('goalhint')).visibility === 'visible'", 3000)
        assert not g.errors
    finally:
        ctx.close()



# the buttons of the HUD, the way's cap, you and the way's next block on the screen: [[id, text, x, y, w, h]], cap text, your tile's box, the block's box
HUD = """(() => { const box = (e) => { const r = e.getBoundingClientRect(); return [e.id, e.textContent.trim(), Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  const cap = document.getElementById('waycap'), s = myPos(), z = myZ(s.x, s.y), n = WayShow.cur && WayShow.cur.now, sq = (x, y, lv) => { const q = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([i, j]) => HdLook.screenOf(x + i, y + j, lv));
    const xs = q.map((v) => v[0]), ys = q.map((v) => v[1]); return [Math.min(...xs), Math.min(...ys) - 24, Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys) + 24]; };
  return {btns: [...document.querySelectorAll('#ttop div, #tctx div, #tbtns div, #goalhint')].filter((e) => e.getClientRects().length).map(box), cap: cap && cap.style.display === 'block' ? cap.textContent : null,
    lit: [...document.querySelectorAll('#tDig.way, #tA.way, #tB.way')].map((e) => e.textContent.trim()), me: sq(s.x, s.y, z), next: n ? sq(n.x, n.y, n.z) : null}; })()"""


def test_the_way_out_s_word_is_written_once_and_the_hud_leaves_you_and_its_block_alone(browser, server):
    """The fifth audit, phones: "Dig a step" twice (a big cap beside the block and the button), the cap over the
    dots; on its side the four buttons at the top lay over the room you stand in. One label: the lit button. No
    button on your tile or on the way's next block; on its side the middle of the top is the land's."""
    from game import Game, new_name
    for w, h in ((390, 844), (844, 390)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True, device_scale_factor=3)
        g = Game(ctx.new_page(), server)
        try:
            g.join(new_name("ph"), 3)
            g.clear_area()
            for depth in (1, 2, 3):
                assert g.rpc("act", tool="dig_down", args={})["ok"]
                g.wait(f"myAt && myAt.z === {-depth} && !myAction", 12000)
            g.wait("WayShow.cur && WayShow.cur.now && !WayShow.busy && document.querySelector('#tDig.way')", 8000)
            g.rest()
            s = g.js(HUD)
            assert s["lit"] == ["Dig a step"] and not (s["cap"] or "").strip(), s                    # the word once: on its button, lit
            hit = lambda b, r: b[2] < r[0] + r[2] and r[0] < b[2] + b[4] and b[3] < r[1] + r[3] and r[1] < b[3] + b[5]
            assert not [b[0] for b in s["btns"] if hit(b, s["me"]) or hit(b, s["next"])], s           # nothing on you, nothing on the block
            if w > h:
                top = [b for b in s["btns"] if b[3] < 60]
                assert len(top) == 5 and not [b[0] for b in top if b[2] < w / 2 + 130 and b[2] + b[4] > w / 2 - 130], top     # goals, Talk, Menu at the left, Items, Craft at the right: the middle is clear
                assert all(b[4] >= 44 and b[5] >= 44 for b in top), top
            assert not g.errors, g.errors
        finally:
            ctx.close()
