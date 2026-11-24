"""Under the land, the real blocks round you (vox_style_land.js, the land's cut; the owner: "underground view should
show the real blocks around the player"): covered by the land, its cells over your space are not drawn, nor, south of
it, those that would hide it from the eye; what stands on them is not drawn either; the land itself, where you can
walk and what covers you, is as it is; out from under it, all of it is drawn again."""

from test_e2e_hd_sun import hd
from test_e2e_hd_window import PX, inside, room

CUT = "([x, y]) => HdLook.cut(x, y) ?? null"


def test_in_a_room_the_land_over_you_is_not_drawn_nor_what_grows_on_it_and_out_of_it_all_is(browser, server):
    g = hd(browser, server)
    x, y = room(g, flowers=True)
    over = [[x - 1, y - 1], [x - 2, y], [x + 2, y], [x + 1, y + 1]]             # (the room's flowers: on the meadow, level 4, over the room)
    mine = lambda: [s for s in g.js("HdLook.stands()") if s[:2] in over]
    assert len(mine()) == 4                                                       # on the meadow: all there
    inside(g, x, y)
    # the meadow is a level over your head: the cut reaches a tile round you and three south (hd: as far as the land over you is deep); the room's ends, the window as ever
    for t in ([x - 1, y - 1], [x + 1, y + 1]):                                    # over the room, near you: drawn down to your head at most
        assert g.js(f"topAt({t[0]}, {t[1]})") == 4 and g.js(CUT, t) <= 3, (t, g.js(CUT, t))
    assert g.js(CUT, [x, y + 2]) == 1                                             # the meadow just south: down to your floor, it would hide you
    assert g.js(CUT, [x, y + 3]) == 3                                             # further south: at your head
    for t in ([x, y - 3], [x, y + 5], [x + 9, y]):                                # north, far south, past the room: drawn whole (no crater)
        assert g.js(CUT, t) is None, t
    assert not mine()                                                             # what grows on the land not drawn: not drawn
    assert g.js("HdLook.level")[1] == 1 and g.js("HdLook.cam.pitch") > g.js("HdLook.steep") - .1   # (the eye knows you are under the land)
    g.rpc("dev_teleport", x=x, y=y + 4, z=4)                                      # out, onto the meadow
    g.arrive()
    g.wait(f"HdLook.cut({x}, {y}) === undefined && !HdLook.busy", timeout=8000)
    g.rest()
    assert len(mine()) == 4                                                       # all of it drawn again
    assert not g.errors


def test_under_the_land_no_grass_is_drawn_on_its_floors(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    x, y = room(g)
    inside(g, x, y)
    px = [g.js(PX, [x + i + .5, y + j + .5, 1]) for i in (-3, -1, 1, 3) for j in (-1, 0)]   # the room's floor, the land over it cut
    green = [c for c in px if c[1] > c[0] + 10 and c[1] > c[2] + 10]
    assert not green, px                                                          # earth or stone: nothing grows under the land
    assert not g.errors


def test_an_ore_over_your_room_is_not_seen_from_under_it(browser, server):
    """The owner: "x-ray should not allow to see ores in wall". What is over the land's cut is not drawn: an ore on the
    meadow over your room is not seen from in the room; out on the meadow it is."""
    g = hd(browser, server)
    x, y = room(g)
    g.stamp(1, -1, ["*"], levels=["4"])                                            # an ore on the meadow over the room
    g.rest()
    ore = lambda: [s for s in g.js("HdLook.stands()") if s[:2] == [x + 1, y - 1]]
    assert ore()
    inside(g, x, y)
    assert g.js(CUT, [x + 1, y - 1]) is not None and not ore()
    assert not g.errors
