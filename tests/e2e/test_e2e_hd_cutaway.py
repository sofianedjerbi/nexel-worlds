"""Under the land, the real blocks round you (vox_style_land.js, the land's cut; the owner: "underground view should
show the real blocks around the player"): covered by the land, its cells over your space are not drawn, nor, south of
it, those that would hide it from the eye; what stands on them is not drawn either; the land itself, where you can
walk and what covers you, is as it is; out from under it, all of it is drawn again."""

import json

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
    # the cut is your space (the whole room) and the tile of land round it, at your head; just south, down to your floor
    for t in over:                                                                # over the room (floor 1): the land is there, drawn down to your head at most
        assert g.js(f"topAt({t[0]}, {t[1]})") == 4 and g.js(CUT, t) <= 3, (t, g.js(CUT, t))
    assert g.js(CUT, [x, y + 2]) == 1                                             # the meadow just south: down to your floor, it would hide you
    assert g.js(CUT, [x, y - 2]) == 3 and g.js(CUT, [x - 4, y]) == 3              # the tile round the room: at your head, its walls two levels high
    for t in ([x, y - 3], [x, y + 3], [x + 6, y], [x + 9, y]):                    # past that: drawn whole (no crater)
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


# each frame, after it is drawn: what stands on the meadow over the room ([what, x, y], a hen by its id) -> [[what, the land's cut there or null, drawn]...]
ON_CUT = """([things, hen]) => { const drawn = new Set(HdLook.stands().map(([x, y]) => x + ',' + y)), q = ents.get('chicken' + hen), out = [];
  for (const [c, x, y] of things) out.push([c, HdLook.cut(x, y) ?? null, drawn.has(x + ',' + y)]);
  if (q) out.push(['hen', HdLook.cut(Math.round(q.x), Math.round(q.y)) ?? null, HdLook.drawnAt(q) !== null]); else out.push(['hen', null, null]);
  return out; }"""


def test_what_stands_on_the_cut_land_goes_and_comes_back_with_it_on_the_same_frames(browser, server):
    """#409, the owner: in a hole, "trees, rocks and hens on the cut-away land stay drawn floating over the x-ray". A tree,
    a stone and a hen on the meadow (level 4) beside a room, where the cut opens round it: you go down into it and out again. On every frame its land is
    cut under it (the cut's height under the meadow's 4), none of it is drawn; on every frame you are on the meadow and
    it is not, all of it is. Each frame reads its own picture's cut (HdLook.cut: the land drawn) and what that picture
    drew: the same at 16 ms a frame as at 300."""
    g = hd(browser, server)
    x, y = room(g)
    g.stamp(-2, -2, ["T...M"], levels=["4" * 5])                                  # (a tree and a stone on the meadow just north of the room: the land the cut opens round it, at your head)
    hen = g.rpc("dev_creatures", kind="chicken", dx=0, dy=-2, still=100000)["spawned"]
    g.rest()
    g.until(f"ents.has('chicken{hen}') && Math.round(ents.get('chicken{hen}').x) === {x} && Math.round(ents.get('chicken{hen}').y) === {y - 2}", 300)
    things = [["T", x - 2, y - 2], ["M", x + 2, y - 2]]
    g.rpc("dev_teleport", x=x, y=y + 4, z=4)                                      # (beside it on the meadow: all of it drawn)
    g.arrive()
    g.until(f"HdLook.cut({x}, {y}) === undefined && !HdLook.busy", 600)
    g.rest()
    first = g.js(ON_CUT, [things, hen])
    assert all(r[1] is None and r[2] for r in first), "on the meadow, not all of it drawn: " + json.dumps(first)
    g.js("([a]) => { window._oc = []; const f0 = window._f0 = frame; frame = function (now) { f0(now); if (HdLook.live) window._oc.push([HdLook.level[1], (" + ON_CUT + ")(a)]); }; return 1; }", [[things, hen]])
    inside(g, x, y)                                                               # (down into the room: the land over it cut)
    g.until(f"HdLook.cut({x - 2}, {y - 2}) !== undefined && HdLook.cut({x + 2}, {y - 2}) !== undefined", 300)
    g.rest()
    g.rpc("dev_teleport", x=x, y=y + 4, z=4)                                      # (out onto the meadow again)
    g.arrive()
    g.until(f"HdLook.cut({x - 2}, {y - 2}) === undefined && HdLook.cut({x + 2}, {y - 2}) === undefined && !HdLook.busy", 600)
    g.rest()
    rec = g.js("(() => { frame = window._f0; return window._oc; })()")
    g.rpc("dev_creatures", clear=40)                                            # (its hen stood still: no later test's page is told of it)
    cut = [f for f in rec if any(r[1] is not None and r[1] < 4 for r in f[1])]
    assert cut, f"the land over the room never cut: {len(rec)} frames, last {json.dumps(rec[-1:])}"
    on = lambda r: r[1] is not None and r[1] < 4                                   # (its land cut under it: the cut's height under the meadow's top)
    bad = [f for f in rec if any((on(r) and r[2]) or (f[0] == 4 and not on(r) and not r[2]) for r in f[1])]   # (up on the meadow, what is not on cut land is drawn; under it, your space's window hides who is over you whatever the cut)
    assert not bad, f"{len(bad)} of {len(rec)} frames with a thing drawn on cut land or not drawn on uncut land ([your level, [[what, cut, drawn]...]]): " + json.dumps(bad[:8])
    assert not g.errors
