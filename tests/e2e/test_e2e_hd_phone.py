"""The HD look on a phone (390 x 844 held upright, 3 device px a CSS px, touch): it was only ever looked at on a desk's
screen at 1 device px a CSS px. There the land was half the size it should be, two fifths of the screen were sky, the
land ran out under you, and what stood more than six rows south of you was not drawn."""

import pytest
from game import Game, new_name

AT = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(HdLook.read(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data).slice(0, 3); }"""
meadow = lambda c: c[1] > c[0] and c[1] > c[2] + 50          # (the meadow's green; a wall is grey)


def phone(browser, server, w=390, h=844):
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True, device_scale_factor=3)
    g = Game(ctx.new_page(), server)
    g.join(new_name("hp"), 2)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    g.rest()
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
        g.js("setOpt('view', 17)"); g.rest()                           # (the old Normal on a phone: 17 tiles; the default, 13, is the desk's, more sky here)
        assert g.js("HdLook.sky(0).line") < .3 * 844                   # the sky: under three tenths of the screen (it was two fifths)
        g.js("setOpt('view', OPT_DEFAULT.view)")
        g.stamp(0, 10, ["%"]); g.rest()                           # a wall ten rows south of you, near the bottom: drawn (nothing was past six rows)
        foot = g.js("([x, y]) => HdLook.screenOf(x + .5, y + 11, 0)", [x, y])
        assert 600 < foot[1] < 844, foot
        seen = g.js(AT, [x - 2.5, y + 10.5, 0]), g.js(AT, [x + .5, y + 10.68, 1])      # (the wall's front: a wall is a thin box in the middle of its tile, hd_things.js, not a card at its south edge)
        assert meadow(seen[0]) and not meadow(seen[1]), seen
        assert not g.errors, g.errors
    finally:
        ctx.close()


@pytest.mark.realtime
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
        g.wait(f"myPos().x === {x + 2} && myPos().y === {y - 1}", 15000)
        g.rest()                                                                          # (the body and the camera at rest there: the next tile's px is where it will stay)
        p = g.js("([x, y]) => HdLook.screenOf(x + .5, y + .5, 0)", [x - 1, y + 3])      # (left of you: the stick's side of the screen: a tap there is a tap on the tile too)
        assert g.js("([a, b]) => document.elementFromPoint(a, b).id", p) == "pad"
        g.page.touchscreen.tap(p[0], p[1])
        try:
            g.wait(f"myPos().x === {x - 1} && myPos().y === {y + 3}", 20000)
        except Exception as e:  # noqa: BLE001 - where you are: walked part of the way (slow), or the tap was not a walk
            raise AssertionError((g.js("[myPos(), !!walking]"), [x - 1, y + 3])) from e
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


# What 60 frames ask of the GPU: the largest picture any WebGL draw paints into, the draws of a frame that was drawn, how often something
# the screen's size was painted on a 2D canvas, how many frames were not drawn at all
COST = """() => new Promise((done) => { const P = WebGL2RenderingContext.prototype, D = CanvasRenderingContext2D.prototype, C = {gl: 0, calls: 0, big: 0, same: 0, n: 0, draws: 0};
  const keep = [P.drawArrays, D.drawImage, D.fillRect, D.clearRect], area = (g, px) => { const t = g.getTransform(); if (Math.min(px * Math.abs(t.a * t.d), g.canvas.width * g.canvas.height) > 300000) C.big++; };
  P.drawArrays = function (...a) { const v = this.getParameter(this.VIEWPORT); C.gl = Math.max(C.gl, v[2] * v[3]); C.draws++; return keep[0].apply(this, a); };
  D.drawImage = function (...a) { area(this, a.length >= 9 ? a[7] * a[8] : a.length >= 5 ? a[3] * a[4] : a[0].width * a[0].height); return keep[1].apply(this, a); };
  D.fillRect = function (...a) { area(this, a[2] * a[3]); return keep[2].apply(this, a); }; D.clearRect = function (...a) { area(this, a[2] * a[3]); return keep[3].apply(this, a); };
  const f1 = frame; frame = function (now) { const d0 = C.draws; f1(now); C.n++; if (HdLook.drew) C.calls = Math.max(C.calls, C.draws - d0); else C.same++;
    if (C.n >= 60) { frame = f1; [P.drawArrays, D.drawImage, D.fillRect, D.clearRect] = keep; done(C); } }; })"""


@pytest.mark.realtime                              # (it counts frames: the words are painted again four times a second whatever, and on the tests' clock that was every other frame, 31 in 60)
def test_a_frame_costs_a_phone_little_one_small_picture_nothing_the_screens_size_few_draws_few_chunks(browser, server):
    """"Very laggy on phone": the classic frame was still painted under this look (its sky through a shader at the screen's size,
    1.3 million px; its pictures sent to the GPU every frame), and the look's own picture was laid on the game's canvas at that
    size; every tile walked made the whole land again."""
    ctx, g = phone(browser, server)
    try:
        g.wait("HdLook.live && !HdLook.busy && HdView.el")
        assert g.js("[HdView.el.width, HdView.el.height, HdView.el.style.width, HdView.el.nextElementSibling === cv, getComputedStyle(HdView.el).imageRendering]") == [195, 422, "390px", True, "pixelated"]   # ONE canvas for the world, an art px a px, under the game's
        c = max(((g.page.evaluate(COST), g.frames(3))[0] for _ in range(3)), key=lambda c: c["same"])     # (the best of three rounds, README.md rule 6: on a busy machine a frame comes so late that something has always moved since the last: 1 still frame in 60, with two browsers at work. Three frames between two rounds: the count's last frame puts the game's own back)
        assert 0 < c["gl"] <= 195 * 422, c            # no WebGL draw into anything bigger than the art's own picture (the classic sky: 780 x 1688)
        assert 0 < c["calls"] <= 10, c                 # a frame's draws (they were 25, and the classic picture's)
        assert c["big"] <= 20, c                       # the game's canvas: wiped when what is written changed, not each frame (it was 4 screens of px a frame)
        # and a frame in which nothing moved is not drawn again. (Counted over sixty frames as they come, 3 or more on a free
        # machine; on a busy one a frame comes so late that something has always moved, 0 in three rounds with two browsers at
        # work: there, the same frame asked for twice, README.md rule 2: the second is not drawn)
        twice = "(() => { const raf = window.requestAnimationFrame, T = performance.now(); window.requestAnimationFrame = () => 0; try { frame(T); frame(T); } finally { window.requestAnimationFrame = raf; } return !HdLook.drew; })()"
        assert c["same"] >= 3 or any(g.js(twice) for _ in range(3)), c     # (three times: what the look looks for four times a second may fall between the two)
        b0 = g.js("HdLook.builds"); g.stamp(1, 0, ["%"]); g.wait(f"HdLook.builds > {b0} && !HdLook.busy")
        assert 1 <= g.js("HdLook.made") <= 9, g.js("HdLook.made")       # a tile changed: its chunk and the ones round it, not the land (some 40 chunks)
        x, y = g.pos(); b0 = g.js("HdLook.builds"); g.page.keyboard.down("a"); g.wait(f"myAt.x <= {x - 1}"); g.page.keyboard.up("a"); g.wait(f"HdLook.builds > {b0} && !HdLook.busy")
        assert g.js("HdLook.made") <= 16 and g.js("HdLook.catSeen()") > .8, g.js("HdLook.made")   # a tile walked: only the chunks coming into view (a column or a row of them at the most, and where a tile just changed)
    finally:
        ctx.close()
