"""The HD look's land (hd.js, hd_sun.js, vox_style.js): a cliff throws the hour's shadow on the low land on the sun's
far side; under a roof you are seen through an x-ray window (vox_style_win.js): a hole of your room's own shape, its floor warm; every px outside it is the px of the land with no window at all (nothing is cut out of the land).
In a trench under the open sky the floor you stand on is seen through its south wall, and pointed at. Deep under the land the eye looks steeply down (68 degrees), land is drawn out to the screen's edges (no backdrop under the horizon) on a desk and on a phone held both ways,
and who is in the room with you is drawn at the room's level."""


import pytest
from conftest import Game, new_name
from test_e2e_hd_stair import MOST
from test_e2e_hd_sun import LIGHT, hd, settled

# meadow green: its light patches too (210,224,119: 224 is not over 210 + 15; it was read "not green" wherever you woke by one,
# on main too), and its dark ones (164,194,99)
MEADOW = lambda c: c[1] >= c[0] + 10 and c[1] > c[2] + 40   # noqa: E731
STEEP = 58          # the eye's pitch from above (hd.js STEEP: 78.6 till the x-ray cut what hides you, 68 when a level was 8 px)

# the picture now, kept under a name; two of them: the share of px that differ, the share that differ outside a box (px), the differing px's own box
# (outside the box by more than a step of rounding: the window's soft light ends a little beyond its rim, and where the meadow's own light
# was within half a unit of the next one, a unit of green came or went: rings of such px north of the room, 800 to 1200 of them by where you woke,
# .0016 to .0025 of the screen against the .002 asked for. Nothing cut out of the land is a unit of 255)
SNAP = "(k) => { (window.__s = window.__s || {})[k] = HdLook.read(0, 0, cv.width, cv.height); return 1; }"
DIFF = """([a, b, bx]) => { const A = __s[a].data, B = __s[b].data, w = __s[a].width, h = __s[a].height; let n = 0, out = 0, x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let i = 0; i < A.length; i += 4) if (A[i] !== B[i] || A[i + 1] !== B[i + 1] || A[i + 2] !== B[i + 2]) { n++; const x = i / 4 % w, y = i / 4 / w | 0; if ((x < bx[0] || y < bx[1] || x > bx[2] || y > bx[3]) && Math.abs(A[i] - B[i]) + Math.abs(A[i + 1] - B[i + 1]) + Math.abs(A[i + 2] - B[i + 2]) > 3) out++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  return {share: n / (w * h), out: out / (w * h), box: [x0, y0, x1, y1]}; }"""
# the px box of some points of the world [x, y, z], m px wider
BOX = """([pts, m]) => { const k = devicePixelRatio, p = pts.map((v) => HdLook.screenOf(...v)); return [Math.min(...p.map((v) => v[0])) * k - m, Math.min(...p.map((v) => v[1])) * k - m, Math.max(...p.map((v) => v[0])) * k + m, Math.max(...p.map((v) => v[1])) * k + m]; }"""
WIN = "HdLook.win.a === 1 && HdLook.win.n >= %d && !HdLook.busy"


def window_off(g, off=True):
    """The same frame with no x-ray window (hd.js nowin), or with it again: what the land is with nothing looked through."""
    g.js(f"(() => {{ HdLook.nowin = {'true' if off else 'false'}; return 1; }})()")
    g.wait(f"HdLook.win.a === {0 if off else 1}")
    made(g)


def made(g):
    """The land at rest out to its horizon: rest() knows the flat screen's rectangle, and the HD look draws more (README
    rule 12). (The first of two pictures compared was taken with the far meadow not all made: .24 to .42 % of its px
    other than in the next picture, and the next, one run in three, as if the window had changed them.)"""
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    g.frames(3)


AT_ = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(HdLook.read(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data).slice(0, 3); }"""


@pytest.mark.realtime
def test_a_cliff_throws_its_shadow_on_the_low_land_away_from_the_sun(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    g.stamp(-1, -4, ["..."] * 2, levels=["444"] * 2)                # a cliff 4 levels high, 3 tiles wide, north of you
    # (the land made with the cliff in it before the hour is changed. Asked for at once, the hour came while the land was
    # still being made for the cliff: one run in six that land was shown with no shadow of the morning on it, landAt
    # saying there was one, until the sun had moved an eighth of a tile on, 1.3 s later (hd.js: the land made is marked as
    # made for the new hour; hd_sun.js: the shadows painted into it were the hour's before). A jump of the hour is the
    # tests' own: in play the hour moves a step at a time)
    g.rest()
    for phase, dark, lit in ((.2, -3, 3), (.68, 3, -3)):             # morning: its shadow lies west; evening: east
        g.hour(phase)
        assert g.js(f"[HdSun.landAt({x + dark}, {y - 3}), HdSun.landAt({x + lit}, {y - 3})]") == [True, False], phase
        # ... and is seen on the screen: each tile against itself with no shadows. (It was the tile in the shadow against the
        # one in the sun, 7 % darker asked for: two tiles of meadow differ by up to 3 % by what grows on them, and the
        # morning's shadow darkens its tile by 7.4 %: where you woke decided, one run in four on any machine)
        a, b = g.js(LIGHT, [x + dark, y - 3, 0]), g.js(LIGHT, [x + lit, y - 3, 0])
        g.js("setOpt('shadows', 0)"); settled(g)
        a0, b0 = g.js(LIGHT, [x + dark, y - 3, 0]), g.js(LIGHT, [x + lit, y - 3, 0])
        g.js("setOpt('shadows', 100)"); settled(g)
        assert a < a0 * .95 and b > b0 * .99, (phase, a, a0, b, b0)
        assert not g.js(f"HdSun.landAt({x}, {y - 3})")                # the cliff's own top takes none
    g.hour(.9)
    assert not g.js(f"HdSun.landAt({x - 3}, {y - 3}) || HdSun.landAt({x + 3}, {y - 3})")      # none at night


@pytest.mark.realtime
def test_under_a_roof_an_xray_window_shows_your_floor_and_every_px_outside_it_is_the_whole_land_s(browser, server):
    g = hd(browser, server)
    g.js("setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    g.hour(.3, still=True)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    room = [[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)]
    g.rpc("dev_col", tiles=room, col=[z - 14, z - 11, z])           # a room 7 x 5 under 11 levels of land
    g.sleep(800)
    # (the window is there within a quarter of a second of the land hiding you: 15 frames at 60 a second, the land made 200 steps a
    #  frame (HdLook.hold: by the step, not by the ms a machine gives it), from a land at rest. It was `HdLook.lag < 600`, ms of the
    #  wall clock: 636 and 778 on runners whose frames are 100 to 200 ms, the land made 5 ms a frame. In frames: 14, whatever their length)
    g.rest(); g.js("HdLook.hold = 200; window.__b0 = HdLook.builds")
    g.rpc("dev_teleport", x=x, y=y, z=z - 14)
    g.wait(WIN % 35, timeout=20000)
    lag = g.js("[HdLook.lagF, HdLook.builds - __b0, HdLook.lag]"); g.js("HdLook.hold = null")
    g.rest()
    assert lag[0] <= 15, str({"frames, lands made, ms": lag})
    assert g.js(f"[HdLook.winAt({x}, {y}), HdLook.winAt({x + 3}, {y + 2}), HdLook.winAt({x + 14}, {y - 2}), HdLook.winAt({x}, {y - 3})]") == [[z - 14, z - 11]] * 2 + [None] * 2   # (the window: your room's tiles, floor to ceiling; nothing beside it, nothing north of it)
    c = g.js(AT_, [x + 2.5, y + 1.5, z - 14])
    assert c[2] <= c[0] + 3 and sum(c) > 300, c                       # (your floor is seen: its own colours, bright; never cold. It was warm, red 40 over blue)
    assert g.js("HdLook.catSeen()") > .8


def test_a_tunnel_one_level_under_the_meadow_opens_a_small_trench_not_the_whole_screen(browser, server):
    """Under one level of earth: the window is your tunnel; the meadow all round is drawn as ever."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        z = g.js(f"topAt({x}, {y})")
        g.stamp(-9, -6, ["." * 19] * 13, levels=[(str(z) if 0 <= z <= 9 else "0") * 19] * 13); g.rest()
        z = g.js(f"topAt({x}, {y})")
        g.rpc("dev_col", tiles=[[x + i, y] for i in range(-3, 4)], col=[z - 3, z - 1, z])
        g.rest()                                                        # (the tunnel made: it was a sleep of 0.8 s, then 4 s for the window: on a renderer with no GPU, not enough)
        g.rpc("dev_teleport", x=x, y=y, z=z - 3)
        g.arrive()
        try:
            g.wait(WIN % 7, timeout=8000)
        except Exception as e:  # noqa: BLE001 - say what the window was: never opened, or not on the tunnel's seven tiles
            raise AssertionError(g.js("({a: HdLook.win.a, n: HdLook.win.n, busy: HdLook.busy, level: HdLook.level[0]})")) from e
        g.rest()
        assert g.js("HdLook.win.n") < 20, g.js("HdLook.win.n")          # (the window's tiles: the tunnel)
        assert g.js("HdLook.catSeen()") > .8
        for dx, dy in [(-7, 0), (7, 0), (0, -2), (0, 5), (5, 4)]:
            c = g.js(MOST, [x + dx + .2, y + dy + .2, x + dx + .8, y + dy + .8, z])   # (the colour most px of the tile's middle have: one px is a tuft)
            assert MEADOW(c), (dx, dy, c)
            assert g.js(f"HdLook.winAt({x + dx}, {y + dy})") is None
    finally:
        g.page.close()


def test_in_a_trench_two_deep_under_the_open_sky_the_floor_you_stand_on_is_seen_and_pointed_at(browser, server):
    """(the owner in the open trench at their cave's mouth, at the surface's pitch: "perspective is just bugged. i should have xray here": the trench's south wall hid the floor, the cat stood as if on the meadow.
    Then a window cut the south wall away and the floor was drawn south of the rim: "a drawer pulled out onto the grass".) Two levels under the land round you the eye looks from above:
    the floor shows as it is (from 58 degrees the south wall that hides you is cut), and what you see there is what a click picks."""
    g = hd(browser, server)
    g.js("setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0); Target.off = true")   # (the boxes of what the keys act on lie on the floor read here, from the first frame: target.js)
    g.hour(.3, still=True)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    g.stamp(-9, -6, ["." * 19] * 13, levels=[(str(z) if 0 <= z <= 9 else "0") * 19] * 13); g.rest()
    z = g.js(f"topAt({x}, {y})")
    g.rpc("dev_col", tiles=[[x + i, y] for i in range(-3, 4)], col=[z - 2])     # a trench one tile wide, two levels deep, open to the sky
    g.settle(f"topAt({x}, {y}) === {z - 2}")
    g.rpc("dev_teleport", x=x, y=y, z=z - 2)
    g.wait("HdLook.cam.pitch === HdLook.steep && !HdLook.busy && HdLook.win.a === 1", timeout=4000)
    g.rest()
    assert g.js("HdLook.level[0]") == z - 2 and g.js("HdLook.catSeen()") > .9      # (from 58 degrees its south wall hides a part of you: cut, the window on the trench, hd.js PART)
    green = lambda c: c[1] > c[0] + 15 and c[1] > c[2] + 40
    seen = [g.js(AT_, [x + dx + .5, y + .25, z - 2]) for dx in (-1, 1)]
    assert not any(green(c) for c in seen), seen                      # (the floor beside you, its north part: its own px, inside the rim)
    for dx in (-1, 1):                                                # ... and a click there is that floor's tile (it picked the rim north of the trench)
        p = g.js(f"(() => {{ const a = HdLook.screenOf({x + dx + .5}, {y + .25}, {z - 2}), q = HdLook.pick(a[0], a[1]); return q && [q.x, q.y]; }})()")
        assert p == [x + dx, y], (dx, p)
    assert g.js("HdLook.catSeen()") > .3
    for dx, dy in [(-7, 0), (7, 0), (5, -3), (-5, 5), (-1, 3), (1, 3)]:   # (the meadow round the trench, past the cut south of it too: no floor hangs there. From 58 the cut wall shows the floor down to 1.3 tiles past the rim)
        c = g.js(AT_, [x + dx + .5, y + dy + .4, z]); assert c[1] >= c[0], (dx, dy, c)


# every frame: [your body's tile x, the eye's pitch]
FEET = """(() => { window.__d = []; window.__on = true; const f = () => { const p = ents.get('agent' + myId);
  __d.push([Math.round(p.x), HdLook.cam.pitch]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""


@pytest.mark.realtime
def test_walking_into_a_trench_the_eye_tips_once(browser, server):
    """(the owner: "when entering the stairs down, the game think the player is still out of it so it gets no xray, a lil delay".) Walking from the meadow into a trench two deep the eye
    tips to look from above, once, one way, as soon as your feet are two under the land round you: no frame goes back up."""
    g = hd(browser, server)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    g.stamp(-9, -6, ["." * 19] * 13, levels=[(str(z) if 0 <= z <= 9 else "0") * 19] * 13); g.rest()
    z = g.js(f"topAt({x}, {y})")
    g.rpc("dev_col", tiles=[[x + i, y] for i in range(-3, 4)], col=[z - 2])
    g.settle(f"topAt({x}, {y}) === {z - 2}")
    g.rpc("dev_teleport", x=x + 6, y=y, z=z)
    g.arrive(); g.rest()
    g.js(FEET)
    g.page.keyboard.down("ArrowLeft")
    g.wait(f"myPos().x <= {x}", timeout=8000)
    g.page.keyboard.up("ArrowLeft")
    g.wait("HdLook.cam.pitch === HdLook.steep", timeout=3000)
    d = g.js("(() => { __on = false; return __d; })()")
    p = [r[1] for r in d]
    assert p[0] < 53 and all(b >= a for a, b in zip(p, p[1:])), p
    first = next(r[0] for r in d if r[1] > p[0])
    assert first <= x + 3, (first, x)                                 # (not before the trench)


@pytest.mark.realtime
def test_deep_in_a_room_the_eye_is_steep_land_fills_the_screen_and_others_are_at_your_level(browser, server):
    for w, h, touch, zoom in ((1440, 900, False, 3), (390, 844, True, 2), (844, 390, True, 2)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=3 if touch else 2, has_touch=touch, is_mobile=touch)
        try:
            g = Game(ctx.new_page(), server)
            g.join(new_name("dp"), zoom)
            g.rpc("dev_creatures", clear=60)
            g.rest()
            x, y = g.pos()
            # (the land out to the horizon come: more of it than rest() knows of, on a screen this size. It slept 0.8 s, then waited 8 s without a
            # word (settle) and read 48 bare px on a busy machine: now it waits for the land to be made too, and says what it was waiting on)
            try:
                g.wait("!HdLook.busy && HdLook.bare() === 0", timeout=25000)
            except Exception as e:
                raise AssertionError((w, h, "surface", g.js("({bare: HdLook.bare(), busy: HdLook.busy, part: HdLook.part, far: HdLook.far, blocks: blocks.size, pitch: HdLook.cam.pitch, low: HdLook.low, line: HdLook.line})"))) from e
            z = g.js(f"topAt({x}, {y})")
            # (whole land round you first. The three of this test wake a few tiles from each other, some runs: the room of the one before, at the same depth, was one room with yours, and its pit, cut
            # north of your room, was read as a cut that "stayed" there: 2 runs in 9 alone, the third always at (-16, 17).
            # And a meadow with nothing on it: the columns alone were laid out, and what stood there stayed. A pond's tiles in the room were no room (16 tiles of 35: the wait's 5 s),
            # and the world's tree five tiles south of who woke at (-24, 8) stood between the eye and you: taken out of the picture by the window, you a checker behind it, catSeen .53 to .74)
            g.stamp(-14, -12, ["." * 29] * 25, levels=[(str(z) if 0 <= z <= 9 else "0") * 29] * 25)
            z = g.js(f"topAt({x}, {y})")
            g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-12, 13) for i in range(-14, 15)], col=[z]); g.rest()
            z = g.js(f"topAt({x}, {y})")
            base = g.js("HdLook.cam.pitch")
            g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[z - 18, z - 15, z])   # a room 7 x 5 under 15 levels of land (24 deep was past the eye: from 58 degrees on a phone held sideways the eye, 26 tiles off, is 22 levels over you: deeper, it is inside the land, the screen backdrop. At 78.6 that was 25)
            g.settle(f"surfacesAt({x + 3}, {y + 2})[0] === {z - 18}")
            g.rpc("dev_teleport", x=x, y=y, z=z - 18)
            g.wait((WIN % 35) + " && HdLook.cam.pitch > HdLook.steep - .1", timeout=5000)
            g.spawn("chicken", 1, 0, still=300)
            g.until("HdLook.bodies().length > 0")
            g.rest()                                                                 # (the eye and the land at rest)
            assert base < 53 and g.js("HdLook.cam.pitch") == STEEP, (w, h, base)
            assert g.js("HdLook.bare()") == 0, (w, h, g.js("HdLook.bare()"))          # (no px of the backdrop under the horizon: it was a flat blue hole a quarter of a phone held sideways)
            assert [b for b in g.js("HdLook.bodies()") if b[0] != "agent"] == [["chicken", z - 18]], g.js("HdLook.bodies()")   # (not another test's player up on the land: it failed beside any test that stands near; it was drawn up on the grass)
            assert g.js("HdLook.catSeen()") > .8
            g.until("!HdLook.busy && HdLook.u === 1")
            g.rest()
            wins = g.js(f"[!!HdLook.winAt({x}, {y + 2}), !!HdLook.winAt({x}, {y + 3}), !!HdLook.winAt({x}, {y - 3}), !!HdLook.winAt({x + 4}, {y})]")
            assert wins == [True, False, False, False], (w, h, wins)   # (the window is the room, 7 x 5: no tile south, north or beside it: the land there is whole however deep you are)
        finally:
            ctx.close()
