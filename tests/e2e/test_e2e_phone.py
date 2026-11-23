"""A phone's screens, upright (390 x 844) and on its side: the chat is two short lines out of your way, a thing to
tap is a finger wide (44 CSS px), the settings' list scrolls under a finger, build mode has its buttons."""
from test_e2e_touch import touch_game

BOX = "(s) => [...document.querySelectorAll(s)].filter((e) => e.offsetParent && getComputedStyle(e).visibility !== 'hidden').map((e) => { const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; })"
MID = "(s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }"


def test_the_chat_is_two_short_lines_top_left_and_a_tap_opens_it(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        g.js("(() => { for (const t of ['one', 'two is a long line that would not fit across the screen of a phone held upright', 'three', 'four']) chatLine(t, 'say', 'Mira'); return 1; })()")
        g.sleep(300)
        log = g.js("(() => { const b = $('chatlog').getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; })()")
        lines = [b for b in g.js(BOX, "#chatlog div") if b[1] + b[3] > log[1] + 1 and b[1] < log[3] - 1]      # (the ones in view)
        assert len(lines) == 2 and all(b[3] <= 20 for b in lines), lines                 # two, each one line high
        S, o = g.js("TS()"), g.js("screenOrigin(TS())"); x, y = g.pos()
        cat = [o[0] + x * S, o[1] + y * S - 2 * S]                                         # (you, your name over you)
        assert log[3] < cat[1] and log[2] <= 390 - 60, (log, cat)                         # over the land far from you, clear of the buttons
        assert g.js("chatKeep()") <= 6                                                    # gone after a few seconds
        g.page.touchscreen.tap(lines[0][0] + 20, lines[0][1] + 8); g.sleep(200)
        assert g.js("$('chatbox').classList.contains('peek')") and g.js("$('chatlog').getBoundingClientRect().height") > 60      # a tap: what was said
        g.page.touchscreen.tap(200, 700); g.sleep(200)
        assert not g.js("$('chatbox').classList.contains('peek')") and not g.errors
    finally:
        ctx.close()


def test_every_button_of_the_menu_the_inventory_and_the_top_is_a_finger_wide(browser, server):
    for w, h in ((390, 844), (844, 390)):
        ctx, g = touch_game(browser, server, w, h)
        try:
            small = lambda sel, least=44: [(sel, b) for b in g.js(BOX, sel) if b[2] < least or b[3] < least or b[0] < 0 or b[1] < 0 or b[0] + b[2] > w or b[1] + b[3] > h]
            assert not small("#ttop div") and not small("#tA") and not small("#tB") and not small("#goalhint")
            g.js("openMenu()"); g.sleep(200)
            assert not small("#menu .row") and not small("#menu [data-go]") and len(g.js(BOX, "#menu .row")) == 3      # (no Help: it is a list of keys)
            for page in range(3):
                g.js(f"menuShow('opts', {page})"); g.sleep(150)
                bad = small("#menu .tab") + small("#menu [data-go]") + [("pick", b) for b in g.js(BOX, "#menu .pick b") if b[2] < 44 or b[3] < 44] + [(s, b) for s in ("#menu .win",) for b in g.js(BOX, s) if b[0] < 0 or b[1] < 0 or b[0] + b[2] > w or b[1] + b[3] > h]
                rows = [b for b in g.js(BOX, "#menu .row") if b[3] < 44]
                assert not bad and not rows and len(g.js(BOX, "#menu .tab")) == 3, (w, page, bad, rows)
            # a finger drawn up the list scrolls it and changes nothing; a tap on a switch flips it
            g.js("menuShow('opts', 1)"); g.sleep(150)
            was = g.js("JSON.stringify(pageRows(1).map((r) => r.get()))")
            x, y = g.js(MID, "#menu .row[data-i='2']")
            g.touch("touchStart", x, y)
            for i in range(1, 9):
                g.touch("touchMove", x, y - i * 14); g.sleep(30)
            g.touch("touchEnd"); g.sleep(300)
            assert g.js("document.querySelector('#menu .well').scrollTop") > 40 and g.js("JSON.stringify(pageRows(1).map((r) => r.get()))") == was
            g.js("(() => { document.querySelector('#menu .row[data-i=\"6\"]').scrollIntoView({block: 'center'}); return 1; })()"); g.sleep(100)
            g.page.touchscreen.tap(*g.js(MID, "#menu .row[data-i='6'] .sw")); g.sleep(200)
            assert g.js("opt('depth')") is False
            g.page.touchscreen.tap(*g.js(MID, "#menu .row[data-i='6'] .sw")); g.sleep(200)
            assert g.js("opt('depth')") is True
            g.js("closeMenu()")
            g.give(wood=3, berries=2); g.js("toggleBag()"); g.sleep(300)
            least = 44 if h > w else 40                                              # (on its side the ten across are 42 px: the height is the limit)
            assert not small("#bag .cell", least) and not small("#bag .bkey:not(.konly)") and not small("#bagclose", least), (w, small("#bag .cell", least), small("#bag .bkey:not(.konly)"))
            assert not g.errors, g.errors
        finally:
            ctx.close()


def test_build_mode_by_thumbs(browser, server):
    """A wall in hand: a button comes over A; in the mode the stick moves the cursor, A plans, and the button leaves."""
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        g.give(wood_wall=4); g.js("selectItem('wood_wall')")
        g.wait("getComputedStyle($('tBuild')).display !== 'none'", 4000)
        g.page.touchscreen.tap(*g.js(MID, "#tBuild")); g.wait("Build.on", 3000)
        at, me = g.js("[Build.S.at.x, Build.S.at.y]"), g.pos()
        g.touch("touchStart", 80, 600)
        for i in range(1, 5):
            g.touch("touchMove", 80 + i * 8, 600); g.sleep(30)
        g.wait(f"Build.S.at.x > {at[0]}", 3000)
        g.touch("touchEnd")
        assert g.pos() == me                                                          # (the cursor went, not you)
        g.wait("$('tBuild').textContent === 'Done' && getComputedStyle($('tUp')).display !== 'none'", 3000)
        a = g.js(MID, "#tA"); g.touch("touchStart", *a); g.sleep(80); g.touch("touchEnd")
        g.wait("Build.S.plans.size >= 1", 3000)
        g.page.touchscreen.tap(*g.js(MID, "#tBuild")); g.wait("!Build.on", 3000)
        assert not g.errors, g.errors
    finally:
        ctx.close()
