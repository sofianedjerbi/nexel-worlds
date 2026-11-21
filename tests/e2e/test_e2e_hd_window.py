"""The x-ray window's manners in the HD look (vox_style_glsl.js, vox_style_win.js, vox_style_land.js, vox_style.js, hd.js):
nothing is shaded outside it (its depth is told inside: test_e2e_hd_stair.py), its near edge is the land's lit lip, and the section over its top edge is the ground's
own earth, not a grey bar; in a river between cliffs the hole is whole (no sliver of the south bank left in it, no path
of the way's boxes through the bank); what grows on the meadow over your room does not stand on its floor; the aim on a
wall is on the cell you hit, at your level, and turning to a wall puts the shown way out away; a block of stone or earth put down is drawn as what it is."""

from test_e2e_hd_pocket import TOP
from test_e2e_hd_sun import hd

# the px of the picture at a place of the world: [r, g, b]
PX = """([x, y, z]) => { const a = HdLook.screenOf(x, y, z), k = devicePixelRatio; return [...HdLook.read(Math.round(a[0] * k), Math.round(a[1] * k), 1, 1).data.slice(0, 3)]; }"""
FLOWERS = [(-1, -1), (-2, 0), (2, 0), (1, 1)]


STATE = "(() => { const a = aimedTile(), p = myPos(), e = ents.get('agent' + myId); return {aim: HdLook.aim, it: a && a.it, at: a && a.p, pos: p, f: [e.fx, e.fy], z: myAt && myAt.z, way: WayShow.cur && WayShow.cur.path.length, led: WayShow.led, offer: WayShow.offer(), mode: inputMode, now: facingNow(false), hand: inHand(), busy: WayShow.busy, pitch: HdLook.cam.pitch, win: HdLook.win.a, act: typeof myAction !== 'undefined' && myAction}; })()"


def room(g, flowers=False):
    """A meadow at level 4; under it a room 7 x 3, its floor at 1, two cells of air, a roof one block thick; a stair
    out of its east end. -> (x, y): the room's middle"""
    x, y = g.pos()
    g.stamp(-9, -6, ["." * 19] * 13, levels=["4" * 19] * 13)
    g.rest()
    rows = ["..f....", ".f...f.", "....f.."] if flowers else ["......."] * 3
    g.stamp(-3, -1, rows, levels=["1" * 7] * 3, roofs=["3" * 7] * 3, heads=["2" * 7] * 3)
    g.rpc("dev_col", tiles=[[x + 4, y]], col=[2])
    g.rpc("dev_col", tiles=[[x + 5, y]], col=[3])
    g.rest()
    return x, y


def inside(g, x, y):
    g.rpc("dev_teleport", x=x, y=y, z=1)
    g.wait("HdLook.win.a === 1 && HdLook.win.n >= 21 && !HdLook.busy && HdLook.cam.pitch > 67.5", timeout=8000)
    g.js("(() => { WayShow.paint = () => {}; return 1; })()")       # (the way out's marks are painted over these px)
    g.rest()


def test_the_window_has_no_shade_outside_it_a_lit_lip_at_its_near_edge_and_its_section_is_earth(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer"):
        g.js(f"setOpt('{o}', 0)")
    x, y = room(g)
    inside(g, x, y)
    lum = lambda c: c[0] + c[1] + c[2]
    meadow = g.js(PX, [x + .5, y + 4.5, 4])
    assert meadow[1] > meadow[0] + 10, meadow                              # (grass)
    # south of the room (its south wall's plane is y + 2): from the hole's edge out onto the meadow, a px every 50th of a tile
    scan = [g.js(PX, [x + .5, y + 2 + i * .02, 4]) for i in range(50)]
    k = next(i for i, c in enumerate(scan) if c[1] > c[0])                 # (before it: the room, seen in the hole)
    south = scan[k:]
    assert len(south) >= 10 and all(c[1] > c[0] and lum(c) > lum(meadow) * .93 for c in south), scan    # outside the hole the meadow is the meadow: no shade round the rim (a shade outside it read as a block standing on the grass; before that a checker of dark px in a black line)
    assert lum(south[0]) > lum(meadow) + 12 and lum(south[-1]) < lum(meadow) + 12, (south[0], south[-1], meadow)      # the hole's near edge: the land's lip, lit; then the grass as it is
    # over the window's top edge (the north wall's plane is y - 1): the section
    north = [g.js(PX, [x + .5, y - 1.5 + i * .02, 4]) for i in range(40)]
    earth = [c for c in north if c[0] > c[1] > c[2] and c[0] - c[2] > 30]
    grey = [c for c in north if max(c) - min(c) < 16 and 70 < c[0] < 150]
    assert len(earth) >= 6 and not grey, north                             # earth's own px, a few rows of them; no flat grey band
    assert g.js("HdLook.catSeen()") > .8


def test_in_a_river_between_cliffs_the_hole_is_whole(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    # a river three wide from west to east, its face at 2; a cliff north of it, a bank four levels over it south
    rows = ["." * 31] * 10 + ["~" * 31] * 3 + ["." * 31] * 10
    g.stamp(-15, -11, rows, levels=["9" * 31] * 10 + ["2" * 31] * 3 + ["6" * 31] * 10)
    g.rest()
    g.rpc("dev_teleport", x=x, y=y)
    g.wait("HdLook.win.a === 1 && HdLook.win.n >= 9 && !HdLook.busy", timeout=8000)
    g.settle("!!WayShow.land()", timeout=4000)                             # (the way out along the river, once it is found: its floors were boxes too)
    g.rest()
    tiles = g.js("HdLook.win.tiles")
    at = {(t[0], t[1]) for t in tiles}
    # the bank hides the whole river from the eye: the three rows of water round you are of the hole, the middle one too
    # (it was the tiles with a wall beside them only: the middle of the water was not, a strip of the bank stood there)
    assert all((x + i, y + j) in at for i in (-1, 0, 1) for j in (-1, 0, 1)), sorted(at)
    # ... and nothing of it further than your own reach of four steps: no path of boxes one tile wide along the river
    assert max(abs(t[0] - x) + abs(t[1] - y) for t in tiles) <= 4, sorted(at)
    assert all(y - 1 <= t[1] <= y + 1 for t in tiles), sorted(at)           # (water only: no box on the banks)


def test_what_grows_on_the_meadow_over_your_room_is_not_on_its_floor(browser, server):
    g = hd(browser, server)
    x, y = room(g, flowers=True)
    where = lambda: {(s[0] - x, s[1] - y): s[2] for s in g.js("HdLook.stands()")}
    g.rpc("dev_teleport", x=x - 8, y=y + 5)                                # on the meadow, far from the stair's mouth: no window
    g.wait("HdLook.win.a === 0 && !HdLook.busy", timeout=8000)
    g.rest()
    got = where()
    assert [got.get(f) for f in FLOWERS] == [4] * 4, got                   # each flower on the grass (the game has them on the tile's lowest ground: they stood at 1, on the room's floor)
    inside(g, x, y)
    got = where()
    assert not any(f in got for f in FLOWERS), got                         # in the room, the meadow over it left out: its flowers with it


def test_the_aim_on_a_cave_s_wall_is_on_the_cell_you_hit(browser, server):
    g = hd(browser, server)
    x, y = room(g)
    g.give(pickaxe=1)
    g.rpc("dev_teleport", x=x - 3, y=y, z=1)                               # the room's west end
    g.wait("HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > 67.5", timeout=8000)
    g.hold_item("pickaxe")
    AIM = "HdLook.aim && aimedTile() && aimedTile().it && aimedTile().it.cell === 2"
    g.hold(["ArrowLeft"], 250)                                             # (the way out, shown after two seconds standing, is put away when you turn to a wall: the test below; this one failed with it shown: {aim: None, way: 9})
    try:
        g.wait(AIM, timeout=4000)
    except Exception:                                                      # (what the page has when the aim is not there: it failed "under load" with nothing said)
        raise AssertionError(g.js(STATE)) from None
    g.rest()
    a = g.js("HdLook.aim")
    c = [g.js(f"HdLook.screenOf({x - 4 + i}, {y + j}, 2)") for i, j in ((0, 0), (1, 1))]     # the wall's cell at your level: its top, one level over your floor
    want = [(c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2]
    assert abs(a["x"] + a["w"] / 2 - want[0]) < 4 and abs(a["y"] + a["h"] / 2 - want[1]) < 4, (a, want)      # (it was round the wall's top, a level higher: 9 px up the screen)


def test_turning_to_a_wall_puts_the_shown_way_out_away_and_the_wall_is_aimed_at(browser, server):
    """Standing two seconds in a cave you can walk out of, the way out is shown, and while it is shown nothing you face
    is offered (keyboard.js). Turning to a wall where you stand is work of your own: the way is put away, the wall's
    cell is aimed at, and it stays so while you stand there (a key held against the wall brought the way back); it
    comes back when you have walked and stood again. (It stayed: no bracket and no key on a cave's wall, for good.)"""
    g = hd(browser, server)
    x, y = room(g)
    g.give(pickaxe=1)
    g.rpc("dev_teleport", x=x - 3, y=y, z=1)
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=8000)
    g.hold_item("pickaxe")
    g.wait("WayShow.cur && !WayShow.led && !aimedTile()", timeout=12000)
    AIM = "!WayShow.cur && HdLook.aim && aimedTile() && aimedTile().it && aimedTile().it.cell === 2"
    g.hold(["ArrowLeft"], 250)
    try:
        g.wait(AIM, timeout=4000)
    except Exception:
        raise AssertionError(g.js(STATE)) from None
    g.hold(["ArrowLeft"], 500)
    g.sleep(2600)                                                          # (time that has to pass in the game: longer than the two seconds that show the way)
    assert g.js(AIM), g.js(STATE)
    g.hold(["ArrowRight"], 250)
    g.wait("WayShow.cur", timeout=12000)                                   # walked and stood: shown again


def test_a_block_put_down_is_drawn_as_what_it_is(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    x, y = g.pos()
    g.stamp(-9, -6, ["." * 19] * 13, levels=["3" * 19] * 13)
    g.rest()
    g.give(stone_block=2, dirt=1)
    for dx, item in ((-2, "stone_block"), (2, "dirt")):
        g.rpc("dev_teleport", x=x + dx, y=y - 1)
        g.arrive()
        assert g.act("place", x=x + dx, y=y - 2, z=4, item=item)["ok"]
    g.rpc("dev_teleport", x=x, y=y + 1)
    g.arrive()
    g.wait(f"matAt({x - 2}, {y - 2}) === 's' && matAt({x + 2}, {y - 2}) === 'd'")
    g.rest()
    stone, earth, grass = g.js(TOP, [x - 2, y - 2, 4]), g.js(TOP, [x + 2, y - 2, 4]), g.js(TOP, [x, y - 2, 3])
    assert grass[1] > grass[0] + 15, grass
    assert max(stone[:3]) - min(stone[:3]) < 30 and stone[1] < stone[0] + 12, stone        # stone: grey, no grass on it (it was earth with a grass top)
    assert earth[0] > earth[1] + 12 and earth[0] > earth[2] + 30, earth                     # earth: bare, brown: no grass on it
    # its sides too: the px under the block's south edge
    side = [g.js(PX, [x - 2 + .5, y - 1, 3.5]), g.js(PX, [x + 2 + .5, y - 1, 3.5])]
    assert max(side[0]) - min(side[0]) < 30, side                                           # the stone block's front: grey
    assert side[1][0] > side[1][2] + 30, side                                               # the earth block's: brown
