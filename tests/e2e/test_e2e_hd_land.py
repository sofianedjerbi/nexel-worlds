"""The HD look's land (hd.js, hd_sun.js, vox_style.js): a cliff throws the hour's shadow on the low land on the sun's
far side; under a roof you are seen through an x-ray window (vox_style_win.js): a hole of your room's own shape, its floor warm; every px outside it is the px of the land with no window at all (nothing is cut out of the land).
In a trench under the open sky the floor you stand on is seen through its south wall, and pointed at. Deep under the land the eye looks steeply down (68 degrees), land is drawn out to the screen's edges (no backdrop under the horizon) on a desk and on a phone held both ways,
and who is in the room with you is drawn at the room's level."""


import pytest
from conftest import Game, new_name
from test_e2e_hd_sun import LIGHT, hd, settled

# the picture now, kept under a name; two of them: the share of px that differ, the share that differ outside a box (px), the differing px's own box
SNAP = "(k) => { (window.__s = window.__s || {})[k] = HdLook.read(0, 0, cv.width, cv.height); return 1; }"
DIFF = """([a, b, bx]) => { const A = __s[a].data, B = __s[b].data, w = __s[a].width, h = __s[a].height; let n = 0, out = 0, x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let i = 0; i < A.length; i += 4) if (A[i] !== B[i] || A[i + 1] !== B[i + 1] || A[i + 2] !== B[i + 2]) { n++; const x = i / 4 % w, y = i / 4 / w | 0; if (x < bx[0] || y < bx[1] || x > bx[2] || y > bx[3]) out++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  return {share: n / (w * h), out: out / (w * h), box: [x0, y0, x1, y1]}; }"""
# the px box of some points of the world [x, y, z], m px wider
BOX = """([pts, m]) => { const k = devicePixelRatio, p = pts.map((v) => HdLook.screenOf(...v)); return [Math.min(...p.map((v) => v[0])) * k - m, Math.min(...p.map((v) => v[1])) * k - m, Math.max(...p.map((v) => v[0])) * k + m, Math.max(...p.map((v) => v[1])) * k + m]; }"""
WIN = "HdLook.win.a === 1 && HdLook.win.n >= %d && !HdLook.busy"


def window_off(g, off=True):
    """The same frame with no x-ray window (hd.js nowin), or with it again: what the land is with nothing looked through."""
    g.js(f"(() => {{ HdLook.nowin = {'true' if off else 'false'}; return 1; }})()")
    g.wait(f"HdLook.win.a === {0 if off else 1}")
    g.rest()


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
    g.rpc("dev_teleport", x=x, y=y, z=z - 14)
    g.wait(WIN % 35, timeout=4000)
    g.rest()
    assert g.js("HdLook.lag") < 600, g.js("HdLook.lag")              # (the window is there within a quarter of a second or so of the land hiding you)
    assert g.js(f"[HdLook.winAt({x}, {y}), HdLook.winAt({x + 3}, {y + 2}), HdLook.winAt({x + 14}, {y - 2}), HdLook.winAt({x}, {y - 3})]") == [[z - 14, z - 11]] * 2 + [None] * 2   # (the window: your room's tiles, floor to ceiling; nothing beside it, nothing north of it)
    c = g.js(AT_, [x + 2.5, y + 1.5, z - 14])
    assert c[0] > c[2] + 40 and sum(c) > 300, c                       # (your floor is seen: warm, bright)
    # the same frame with no window: the land is whole (what is over your floor there is the meadow). The two pictures differ only where the window is: the room as the eye has it and its rim;
    # everywhere else every px is the same px (the open pit took two thirds of the screen: cut rock in terraces)
    g.js(SNAP, "win")
    window_off(g)
    g.js(SNAP, "whole")
    c = g.js(AT_, [x + 2.5, y + 1.5, z - 14])
    assert c[1] > c[0] + 15 and c[1] > c[2] + 40, c                   # (no window: meadow green over your floor)
    window_off(g, False)
    room = g.js(BOX, [[[x + i, y + j, z - 14 + k] for i in (-3, 4) for j in (-2, 3) for k in (0, 3)], 64])   # (the room as the eye has it, and its rim of half a tile, with a little room for the lens)
    d = g.js(DIFF, ["win", "whole", room])
    assert .02 < d["share"] < .3 and d["out"] < .002, (d, room)        # (a room 7 x 5 is a sixth of this small screen)
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
        g.sleep(800)
        g.rpc("dev_teleport", x=x, y=y, z=z - 3)
        g.wait(WIN % 7, timeout=4000)
        g.rest()
        assert g.js("HdLook.win.n") < 20, g.js("HdLook.win.n")          # (the window's tiles: the tunnel)
        assert g.js("HdLook.catSeen()") > .8
        for dx, dy in [(-7, 0), (7, 0), (0, -2), (0, 5), (5, 4)]:
            c = g.js(AT_, [x + dx + .5, y + dy + .5, z])
            assert c[1] > c[0] + 15 and c[1] > c[2] + 40, (dx, dy, c)     # (meadow green)
            assert g.js(f"HdLook.winAt({x + dx}, {y + dy})") is None
    finally:
        g.page.close()


def test_in_a_trench_two_deep_under_the_open_sky_the_floor_you_stand_on_is_seen_and_pointed_at(browser, server):
    """(the owner in the open trench at their cave's mouth, at the surface's pitch: "perspective is just bugged. i should have xray here": the trench's south wall hid the floor, the cat stood as if on the meadow.)
    Whenever land is between the eye and your feet the window is on your floor, at any pitch: the floor's px are drawn, the land in front of them is not; and what you see there is what a click picks."""
    g = hd(browser, server)
    g.js("setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    g.hour(.3, still=True)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    g.stamp(-9, -6, ["." * 19] * 13, levels=[(str(z) if 0 <= z <= 9 else "0") * 19] * 13); g.rest()
    z = g.js(f"topAt({x}, {y})")
    base = g.js("HdLook.cam.pitch")
    g.rpc("dev_col", tiles=[[x + i, y] for i in range(-3, 4)], col=[z - 2])     # a trench one tile wide, two levels deep, open to the sky
    g.settle(f"topAt({x}, {y}) === {z - 2}")
    g.rpc("dev_teleport", x=x, y=y, z=z - 2)
    g.wait(f"HdLook.win.a === 1 && !!HdLook.winAt({x}, {y}) && !HdLook.busy", timeout=4000)
    g.rest()
    assert g.js("HdLook.cam.pitch") == base and g.js("HdLook.level[0]") == z - 2      # (the surface's pitch: nothing tilts)
    green = lambda c: c[1] > c[0] + 15 and c[1] > c[2] + 40
    seen = [g.js(AT_, [x + dx + .5, y + .5, z - 2]) for dx in (-1, 1)]
    assert not any(green(c) for c in seen), seen                      # (the floor beside you: its own px, not the grass of the land south of it)
    for dx in (-1, 1):                                                # ... and a click there is that floor's tile (it picked the rim north of the trench)
        p = g.js(f"(() => {{ const a = HdLook.screenOf({x + dx + .5}, {y + .5}, {z - 2}), q = HdLook.pick(a[0], a[1]); return q && [q.x, q.y]; }})()")
        assert p == [x + dx, y], (dx, p)
    assert g.js("HdLook.catSeen()") > .8
    window_off(g)
    hid = [g.js(AT_, [x + dx + .5, y + .5, z - 2]) for dx in (-1, 1)]
    assert all(green(c) for c in hid), hid                            # (with no window those px are the meadow south of the trench: it stands between the eye and the floor)
    window_off(g, False)
    for dx, dy in [(-7, 0), (7, 0), (5, -3), (-5, 5)]:                # (not the tiles over your head on the screen: the way out is marked there)
        c = g.js(AT_, [x + dx + .5, y + dy + .5, z]); assert green(c), (dx, dy, c)   # (the meadow round the trench: as ever)


# every frame: [your body's tile x (the body as it is drawn, between two tiles: not the server's last), land is between the eye and your feet there (a roof, or the land south two levels over your floor), the window is on that tile and whole]
FEET = """(() => { window.__d = []; window.__on = true; const f = () => { const p = ents.get('agent' + myId), x = Math.round(p.x), y = Math.round(p.y), L = HdLook.level[0];
  __d.push([x, +(topAt(x, y) > L || topAt(x, y + 1) - L >= 2), +(!!HdLook.winAt(x, y) && HdLook.win.a >= .99)]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""


@pytest.mark.realtime
def test_walking_into_a_trench_the_window_is_there_the_first_frame_your_feet_are_under_the_rim(browser, server):
    """(the owner: "when entering the stairs down, the game think the player is still out of it so it gets no xray, a lil delay": 54 frames of the walk into their cave with land in front of the feet and
    nothing looked through.) Your space is looked for from the surface too: the window is on a hole beside you before you step into it. Every frame of the walk in: none with your feet hidden and no window."""
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
    d = g.js("(() => { __on = false; return __d; })()")
    hid = [r for r in d if r[1]]
    late = [r for r in hid if not r[2]]
    assert len(hid) >= 10 and not late, (len(d), len(hid), late[:6])


@pytest.mark.realtime
def test_deep_in_a_room_the_eye_is_steep_land_fills_the_screen_and_others_are_at_your_level(browser, server):
    for w, h, touch, zoom in ((1440, 900, False, 3), (390, 844, True, 2), (844, 390, True, 2)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=3 if touch else 2, has_touch=touch, is_mobile=touch)
        try:
            g = Game(ctx.new_page(), server)
            g.join(new_name("dp"), zoom, look="hd")
            g.rpc("dev_creatures", clear=60)
            g.sleep(800)
            x, y = g.pos()
            z = g.js(f"topAt({x}, {y})")
            base = g.js("HdLook.cam.pitch")
            assert g.js("HdLook.bare()") == 0, (w, h, "surface")
            # (whole land round you first. The three of this test wake a few tiles from each other, some runs: the room of the one before, at the same depth, was one room with yours, and its pit, cut
            # north of your room, was read as a cut that "stayed" there: 2 runs in 9 alone, the third always at (-16, 17))
            g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-12, 13) for i in range(-14, 15)], col=[z])
            g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[z - 24, z - 21, z])   # a room 7 x 5 under 21 levels of land
            g.sleep(800)
            g.rpc("dev_teleport", x=x, y=y, z=z - 24)
            g.wait((WIN % 35) + " && HdLook.cam.pitch > 67.5", timeout=5000)
            g.spawn("chicken", 1, 0, still=300)
            g.wait("HdLook.bodies().length > 0", timeout=4000)
            g.sleep(500)
            assert base < 53 and g.js("HdLook.cam.pitch") == 68, (w, h, base)
            assert g.js("HdLook.bare()") == 0, (w, h, g.js("HdLook.bare()"))          # (no px of the backdrop under the horizon: it was a flat blue hole a quarter of a phone held sideways)
            assert [b for b in g.js("HdLook.bodies()") if b[0] != "agent"] == [["chicken", z - 24]], g.js("HdLook.bodies()")   # (not another test's player up on the land: it failed beside any test that stands near; it was drawn up on the grass)
            assert g.js("HdLook.catSeen()") > .8
            g.wait("!HdLook.busy && HdLook.u === 1")
            g.sleep(300)
            wins = g.js(f"[!!HdLook.winAt({x}, {y + 2}), !!HdLook.winAt({x}, {y + 3}), !!HdLook.winAt({x}, {y - 3}), !!HdLook.winAt({x + 4}, {y})]")
            assert wins == [True, False, False, False], (w, h, wins)   # (the window is the room, 7 x 5: no tile south, north or beside it: the land there is whole however deep you are)
        finally:
            ctx.close()
