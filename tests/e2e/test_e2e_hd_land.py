"""The HD look's land (hd.js, hd_sun.js, vox_style.js): a cliff throws the hour's shadow on the low land on the sun's
far side; under a roof a room's floor is warm and far brighter than the rock cut round it; the cut opens at once."""


from conftest import Game, new_name
from test_e2e_hd_sun import LIGHT, hd, settled


def test_a_cliff_throws_its_shadow_on_the_low_land_away_from_the_sun(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    g.stamp(-1, -4, ["..."] * 2, levels=["444"] * 2)                # a cliff 4 levels high, 3 tiles wide, north of you
    for phase, dark, lit in ((.2, -3, 3), (.68, 3, -3)):             # morning: its shadow lies west; evening: east
        g.rpc("dev_time", phase=phase)
        settled(g)
        assert g.js(f"[HdSun.landAt({x + dark}, {y - 3}), HdSun.landAt({x + lit}, {y - 3})]") == [True, False], phase
        a, b = g.js(LIGHT, [x + dark, y - 3, 0]), g.js(LIGHT, [x + lit, y - 3, 0])
        assert a < b * .93, (phase, a, b)                              # ... and is seen on the screen
        assert not g.js(f"HdSun.landAt({x}, {y - 3})")                # the cliff's own top takes none
    g.rpc("dev_time", phase=.9)
    settled(g)
    assert not g.js(f"HdSun.landAt({x - 3}, {y - 3}) || HdSun.landAt({x + 3}, {y - 3})")      # none at night


def test_under_a_roof_the_floor_is_bright_and_the_cut_opens_at_once(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    room = [[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)]
    g.rpc("dev_col", tiles=room, col=[z - 14, z - 11, z])           # a room 7 x 5 under 11 levels of land
    g.sleep(800)
    g.rpc("dev_teleport", x=x, y=y, z=z - 14)
    g.wait("HdLook.u > .95 && HdLook.box && HdLook.box.w > 10 && !HdLook.busy", timeout=4000)
    g.sleep(400)
    assert g.js("HdLook.lag") < 600, g.js("HdLook.lag")              # (250 ms on a free machine; the land is made in one go, no ease)
    floor, rock = g.js(LIGHT, [x + 2, y + 1, z - 14]), g.js(LIGHT, [x + 6, y + 1, z - 12])
    assert floor > rock + 180, (floor, rock)                         # (the sum of r, g, b: a warm bright floor in dark rock)
    assert g.js("HdLook.catSeen()") > .8
