"""The HD look on a phone (390 x 844 held upright, 3 device px a CSS px, touch): it was only ever looked at on a desk's
screen at 1 device px a CSS px. There the land was half the size it should be, two fifths of the screen were sky, the
land ran out under you, and what stood more than six rows south of you was not drawn."""

from game import Game, new_name

AT = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(ctx.getImageData(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data).slice(0, 3); }"""
meadow = lambda c: c[1] > c[0] and c[1] > c[2] + 50          # (the meadow's green; a wall is grey)


def phone(browser, server, w=390, h=844):
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True, device_scale_factor=3)
    g = Game(ctx.new_page(), server)
    g.join(new_name("hp"), 2, look="hd")
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    g.sleep(1200)
    cdp = ctx.new_cdp_session(g.page)
    g.touch = lambda kind, pts=(): cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(pts)]})
    return ctx, g


def test_the_land_is_the_size_the_zoom_says_and_fills_a_screen_held_upright(browser, server):
    ctx, g = phone(browser, server)
    try:
        x, y = g.pos()
        assert g.js("HdLook.on && devicePixelRatio === 3 && zoom === 2")
        a, b = (g.js("([x, y]) => HdLook.screenOf(x, y, 0)", [x + d, y + .5]) for d in (0, 1))
        assert abs(b[0] - a[0] - 16 * 2) < 1.5, (a, b)                 # a tile where you stand: 16 art px of `zoom` CSS px each (it was half that)
        me = g.js("([x, y]) => HdLook.screenOf(x + .5, y + .5, 0)", [x, y])
        assert abs(me[0] - 195) < 2 and 380 < me[1] < 470, me          # you: in the middle
        assert g.js("HdLook.catSeen()") > .8                           # and drawn there, px for px
        assert g.js("HdLook.sky(0).line") < .3 * 844                   # the sky: under three tenths of the screen (it was two fifths)
        g.stamp(0, 10, ["%"]); g.sleep(1800)                           # a wall ten rows south of you, near the bottom: drawn (nothing was past six rows)
        foot = g.js("([x, y]) => HdLook.screenOf(x + .5, y + 11, 0)", [x, y])
        assert 600 < foot[1] < 844, foot
        seen = g.js(AT, [x - 2.5, y + 10.5, 0]), g.js(AT, [x + .5, y + 10.68, 1])      # (the wall's front: a wall is a thin box in the middle of its tile, hd_things.js, not a card at its south edge)
        assert meadow(seen[0]) and not meadow(seen[1]), seen
        assert not g.errors, g.errors
    finally:
        ctx.close()


def test_a_tap_goes_to_the_tile_under_the_finger(browser, server):
    ctx, g = phone(browser, server)
    try:
        x, y = g.pos()
        for dx, dy in [(2, -1), (-3, 4), (4, 6)]:
            p = g.js("([x, y]) => HdLook.screenOf(x + .5, y + .5, 0)", [x + dx, y + dy])
            got = g.js("([a, b]) => tileAtScreen(a, b)", p)
            assert (got["x"], got["y"]) == (x + dx, y + dy), (dx, dy, got)
        p = g.js("([x, y]) => HdLook.screenOf(x + .5, y + .5, 0)", [x + 2, y - 1])
        g.page.touchscreen.tap(p[0], p[1])
        g.wait(f"myPos().x === {x + 2} && myPos().y === {y - 1}", 6000)
        p = g.js("([x, y]) => HdLook.screenOf(x + .5, y + .5, 0)", [x - 1, y + 3])      # (left of you: the stick's side of the screen: a tap there is a tap on the tile too)
        assert g.js("([a, b]) => document.elementFromPoint(a, b).id", p) == "pad"
        g.page.touchscreen.tap(p[0], p[1])
        g.wait(f"myPos().x === {x - 1} && myPos().y === {y + 3}", 6000)
        assert not g.errors, g.errors
    finally:
        ctx.close()


def test_a_pinch_with_one_finger_on_the_sticks_side_zooms_and_does_not_walk(browser, server):
    """Held upright, the left of the screen is the stick's: a pinch across the middle put a finger on it, walked you
    away and did not zoom."""
    ctx, g = phone(browser, server)
    try:
        pos = g.pos()
        pts = lambda d: [(195 - d, 420), (195 + d, 420)]
        assert g.js("(() => { const r = $('pad').getBoundingClientRect(); return 195 - 40 < r.right && 420 > r.top; })()")   # (the left finger is on the stick's side)
        g.touch("touchStart", pts(40))
        for i in range(1, 9):
            g.touch("touchMove", pts(40 + 10 * i)); g.sleep(40)
        g.touch("touchEnd"); g.sleep(900)
        assert g.js("zoom") > 2 and g.pos() == pos and not g.js("!!stick")
        g.touch("touchStart", [(80, 600)])                            # and the stick still walks, alone
        for i in range(1, 6):
            g.touch("touchMove", [(80 + i * 8, 600)]); g.sleep(30)
        g.wait(f"myPos().x > {pos[0]}", 4000)
        g.touch("touchEnd")
        assert not g.errors, g.errors
    finally:
        ctx.close()
