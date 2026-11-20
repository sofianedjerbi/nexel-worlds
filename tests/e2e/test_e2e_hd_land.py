"""The HD look's land (hd.js, hd_sun.js, vox_style.js): a cliff throws the hour's shadow on the low land on the sun's
far side; under a roof a room's floor is warm and brighter than the rock of the open pit round it, the pit opens within a quarter of a second or so and the meadow stays as it is.
Deep under the land the eye looks steeply down (68 degrees): the pit is a hole with walls all round, land is drawn out to the screen's edges (no backdrop under the horizon) on a desk and on a phone held both ways,
and who is in the room with you is drawn at the room's level."""


from conftest import Game, new_name
from test_e2e_hd_sun import LIGHT, hd, settled

AT_ = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(HdLook.read(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data).slice(0, 3); }"""


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


def test_under_a_roof_an_open_pit_shows_a_bright_floor_and_the_meadow_stays(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    room = [[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)]
    g.rpc("dev_col", tiles=room, col=[z - 14, z - 11, z])           # a room 7 x 5 under 11 levels of land
    g.sleep(800)
    g.rpc("dev_teleport", x=x, y=y, z=z - 14)
    g.wait("HdLook.u > .95 && HdLook.pit > 40 && !HdLook.busy", timeout=4000)
    g.sleep(400)
    assert g.js("HdLook.lag") < 600, g.js("HdLook.lag")              # (250 ms on a free machine: the pit grows from your tile, a few sizes)
    floor, rock = g.js(LIGHT, [x + 2, y + 1, z - 14]), g.js(LIGHT, [x + .5, y - 2, z - 9])   # (the pit's back wall, the room's north)
    assert floor > rock + 60 and rock > 120, (floor, rock)           # (the sum of r, g, b: a warm bright floor; the pit's wall darker, never black)
    assert g.js(f"HdLook.cut({x}, {y}, {z}) && !HdLook.cut({x + 14}, {y - 2}, {z}) && !HdLook.cut({x}, {y - 3}, {z})")   # (cut over your room; whole beside it and north of it: the back wall)
    assert g.js("HdLook.catSeen()") > .8


def test_a_tunnel_one_level_under_the_meadow_opens_a_small_trench_not_the_whole_screen(browser, server):
    """Under one level of earth: the pit is your tunnel and a few tiles south of it; the meadow all round is drawn as ever."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        z = g.js(f"topAt({x}, {y})")
        g.stamp(-9, -6, ["." * 19] * 13, levels=[(str(z) if 0 <= z <= 9 else "0") * 19] * 13); g.rest()
        z = g.js(f"topAt({x}, {y})")
        g.rpc("dev_col", tiles=[[x + i, y] for i in range(-3, 4)], col=[z - 3, z - 1, z])
        g.sleep(800)
        g.rpc("dev_teleport", x=x, y=y, z=z - 3)
        g.wait("HdLook.u > .95 && HdLook.pit > 6 && !HdLook.busy", timeout=4000)
        g.sleep(400)
        assert g.js("HdLook.pit") < 60, g.js("HdLook.pit")              # (tiles cut: the tunnel and its trench)
        assert g.js("HdLook.catSeen()") > .8
        for dx, dy in [(-7, 0), (7, 0), (0, -2), (0, 5), (5, 4)]:
            c = g.js(AT_, [x + dx + .5, y + dy + .5, z])
            assert c[1] > c[0] + 15 and c[1] > c[2] + 40, (dx, dy, c)     # (meadow green)
            assert not g.js(f"HdLook.cut({x + dx}, {y + dy}, {z})")
    finally:
        g.page.close()


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
            g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[z - 24, z - 21, z])   # a room 7 x 5 under 21 levels of land
            g.sleep(800)
            g.rpc("dev_teleport", x=x, y=y, z=z - 24)
            g.wait("HdLook.u > .95 && HdLook.pit > 40 && !HdLook.busy && HdLook.cam.pitch > 67.5", timeout=5000)
            g.spawn("chicken", 1, 0, still=300)
            g.wait("HdLook.bodies().length > 0", timeout=4000)
            g.sleep(500)
            assert base < 53 and g.js("HdLook.cam.pitch") == 68, (w, h, base)
            assert g.js("HdLook.bare()") == 0, (w, h, g.js("HdLook.bare()"))          # (no px of the backdrop under the horizon: it was a flat blue hole a quarter of a phone held sideways)
            assert [b for b in g.js("HdLook.bodies()") if b[0] != "agent"] == [["chicken", z - 24]], g.js("HdLook.bodies()")   # (not another test's player up on the land: it failed beside any test that stands near; it was drawn up on the grass)
            assert g.js("HdLook.catSeen()") > .8
            g.wait("!HdLook.busy && HdLook.u === 1")
            g.sleep(300)
            cuts = g.js(f"[HdLook.cut({x}, {y + 4}, {z}), HdLook.cut({x}, {y + 14}, {z}), HdLook.cut({x}, {y - 3}, {z})]")
            assert cuts == [True, False, False], (w, h, cuts)   # (the south side steps up 3 levels a tile: the land's top is back 10 tiles south at most; it was 16)
        finally:
            ctx.close()
