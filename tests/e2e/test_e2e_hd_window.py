"""The x-ray window's manners in the HD look (vox_style_glsl.js, vox_style_win.js, vox_style_land.js, vox_style.js, hd.js):
the window is your whole space (its edge dithered: test_e2e_hd_xray.py); in it the land over your head is cut (its section: the ground's own earth, not a grey bar), outside it nothing is shaded or cut (depth: test_e2e_hd_stair.py);
in a river between cliffs the hole is whole (no sliver of the south bank left in it, no path
of the way's boxes through the bank); what grows on the meadow over your room does not stand on its floor; the aim on a
wall is on the cell you hit, at your level, and turning to a wall puts the shown way out away; a block of stone or earth put down is drawn as what it is."""

from test_e2e_hd_pocket import TOP
from test_e2e_hd_sun import hd

# the px of the picture at a place of the world: [r, g, b]
PX = """([x, y, z]) => { const a = HdLook.screenOf(x, y, z), k = devicePixelRatio; return [...HdLook.read(Math.round(a[0] * k), Math.round(a[1] * k), 1, 1).data.slice(0, 3)]; }"""
FLOWERS = [(-1, -1), (-2, 0), (2, 0), (1, 1)]
# the colour most px of a row of the picture have, ROW px wide, at a place of the world: [r, g, b] (one px was a tuft or a
# light patch of the meadow: "the meadow" read 184,225,162 and the rim's last px 236,254,198, one run in a few)
ROW = 9
BAND = """([x, y, z, w]) => { const a = HdLook.screenOf(x, y, z), k = devicePixelRatio, d = HdLook.read(Math.round(a[0] * k - w / 2), Math.round(a[1] * k), w, 1).data, n = new Map();
  for (let i = 0; i < d.length; i += 4) { const c = d[i] + ',' + d[i + 1] + ',' + d[i + 2]; n.set(c, (n.get(c) || 0) + 1); } return [...n].sort((p, q) => q[1] - p[1])[0][0].split(',').map(Number); }"""


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
    g.wait("HdLook.win.a === 1 && HdLook.win.n >= 21 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=8000)
    g.js("(() => { WayShow.paint = () => {}; Target.off = true; return 1; })()")       # (the way out's marks and the keys' boxes are painted over these px)
    g.rest()


def test_in_a_river_between_cliffs_the_hole_is_whole(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    # a river three wide from west to east, its face at 2; a cliff north of it, a bank four levels over it south
    rows = ["." * 31] * 10 + ["~" * 31] * 3 + ["." * 31] * 10
    g.stamp(-15, -11, rows, levels=["9" * 31] * 10 + ["2" * 31] * 3 + ["6" * 31] * 10)
    g.rest()
    g.rpc("dev_teleport", x=x, y=y)
    g.wait("HdLook.cam.pitch === HdLook.steep && !HdLook.busy && HdLook.win.a === 1", timeout=8000)
    g.rest()
    # four levels under the land round you: the eye looks from above (STEEP, 58), and the south bank that hides you is cut: the
    # window on the river, you whole; no box of it on the banks (it was a strip of boxes along the river, then the river's floor
    # laid south of the bank; at 78.6 nothing was cut)
    assert g.js("HdLook.win.a") == 1 and g.js("HdLook.catSeen()") > .7     # (swimming: your feet under the water's face)
    assert g.js(f"HdLook.winAt({x}, {y})") and not any(g.js(f"HdLook.winAt({x + i}, {y + j})") for i in (-2, 0, 2) for j in (-3, 3))


# the mean light of the px round a place of the world (a 9 x 9 px square)
LUM = """([x, y, z]) => { const a = HdLook.screenOf(x, y, z), k = devicePixelRatio, d = HdLook.read(Math.round(a[0] * k) - 4, Math.round(a[1] * k) - 4, 9, 9).data; let s = 0;
  for (let i = 0; i < d.length; i += 4) s += .3 * d[i] + .59 * d[i + 1] + .11 * d[i + 2]; return s / (d.length / 4); }"""


def gorge(g):
    """A river five wide at 0 between stone cliffs 12 high (C), you in its south row against the south cliff (the owner's
    doben0, caves -20,-38). -> (x, y): you"""
    x, y = g.pos()
    rows = ["." * 31] * 8 + ["~" * 31] * 5 + ["." * 31] * 8
    g.stamp(-15, -12, rows, levels=["C" * 31] * 8 + ["0" * 31] * 5 + ["C" * 31] * 8)
    g.rest()
    return x, y


def test_swimming_at_the_foot_of_a_deep_river_s_bank_its_far_wall_is_stone(browser, server):
    """(A player fell 12 into a river five wide between stone cliffs and swam at its south bank: "no x-ray, black boxes".)
    The hole's walls were darkened by its depth as a shaft's are (vox_style_glsl.js ho): the far wall, whole in sight, black
    under its first level within six tiles of you, a black stepped slab. The floor of this hole is seen (hd_level.js shut)."""
    g = hd(browser, server)
    x, y = gorge(g)
    g.rpc("dev_teleport", x=x, y=y)
    g.wait("HdLook.cam.pitch === HdLook.steep && !HdLook.busy && HdLook.win.a === 1", timeout=8000)
    g.rest()
    face = [g.js(LUM, [x + dx + .5, y - 4, 3]) for dx in (-3, -1, 1)]     # the north bank's face over the river, 48 px up (a level is 16 px: 6 was off the screen's top), a few tiles from you
    assert min(face) > 50, face                                           # (grey stone: it was 2, black)


# where your body is drawn (CSS px), where your place is (your tile at your level), the window, how much of you is seen
FOOT = """(() => { const e = ents.get('agent' + myId), a = HdLook.screenOf(e.x + .5, e.y + .5, HdLook.level[0]);
  return {b: HdLook.art().body, a, lv: HdLook.level, win: [HdLook.win.n, HdLook.win.a], mine: HdLook.winAt(Math.round(e.x), Math.round(e.y)), seen: HdLook.catSeen()}; })()"""


def test_at_the_foot_of_a_cliff_in_a_gorge_the_x_ray_shows_you_at_your_own_level(browser, server):
    """The owner, his bunny in a river against the cliff south of it, 12 high: "It should trigger x-ray. Instead the game
    acts like he's above." Under the open sky you were LIFTED (hd_level.js lift): drawn 11 levels up, on the cliff's top
    edge. Land between the eye and you that hides you, a roof or a cliff, opens the x-ray window on your space at your
    level (hd_level.js hides): swimming, and on a dry ledge one tile wide at the cliff's foot alike."""
    g = hd(browser, server)
    x, y = gorge(g)
    for ledge in (False, True):
        if ledge:
            g.stamp(0, 0, ["."], levels=["0"])                           # (a dry tile at the cliff's foot, the river north of it)
            g.rest()
        g.rpc("dev_teleport", x=x, y=y)
        try:
            g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=8000)          # (it was 0: no window under the open sky)
        except Exception:
            raise AssertionError(g.js("(() => { const e = ents.get('agent' + myId), tx = Math.round(e.x), ty = Math.round(e.y), L = HdLook.level[0]; return [myAt, e.x, e.y, L, HdLook.cam.pitch, HdLook.win.n, HdLook.win.a, HdLevel.cover.roof, HdLevel.over(tx, ty, L, eyeRise(HdLook.steep)), [-1, 0, 1, 2].map((d) => Voxels.host.column(tx, ty + d)), HdLook.force]; })()"))
        g.rest()
        s = g.js(FOOT)
        assert s["lv"][0] == 0 and s["lv"][3] == 0, s                     # at your level, not lifted (it was 11.1: the cliff's rim)
        assert s["mine"] and s["mine"][0] == 0, s                         # your own tile is in the window, at its own level
        b, a = s["b"], s["a"]
        assert b and b["y"] < a[1] < b["y"] + b["h"] + 16, s               # your body stands on your place as the eye sees it (it was 11 levels up the screen)
        assert s["seen"] > .7, s


def test_in_a_gorge_the_river_is_one_water_through_the_window_no_strip_of_the_cliff_s_top_over_it(browser, server):
    """The owner, x-ray in the gorge: the river a patchwork, "a dark outline floating in the water". Only the tiles the
    cliff hid WHOLE were in the window (and in a diamond four steps round you): the cliff's top over a tile it hid in part
    stayed, a strip of it with its dark rim across the river, the river seen again past it. Now any tile it hides at all
    is (hd_level.js veils), in a square round you: from you north to the far bank, along every column near you, water
    alone, each px of it as the river's px are (one depth: one tone, give or take its waves)."""
    g = hd(browser, server)
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer"):
        g.js(f"setOpt('{o}', 0)")
    x, y = gorge(g)
    g.rpc("dev_teleport", x=x, y=y)
    g.wait("HdLook.win.a === 1 && !HdLook.busy", timeout=8000)
    g.js("(() => { WayShow.paint = () => {}; Target.off = true; return 1; })()")
    g.rest()
    lum = lambda c: .3 * c[0] + .59 * c[1] + .11 * c[2]
    cols = {}
    for dx in (-2, -1, 1, 2):                                              # (not your own column: you stand in it) (in the porthole round you: past it the land is whole)
        cols[dx] = [g.js(PX, [x + dx + .5, y + .5 - i * .1, 0]) for i in range(36)]   # your row to near the river's north row, a px every tenth of a tile
    for dx, scan in cols.items():
        land = "".join("L" if c[2] - c[0] < 15 else "w" for c in scan)   # (water is blue over red; the cliff's stone and its dark rim are not: a strip of them, three px or more)
        assert "LLL" not in land, (dx, land, sorted((t[0] - x, t[1] - y) for t in g.js("HdLook.win.tiles")))   # (before: wwww...LLLLLLLLLLLLLLLLwwww at -4: the cliff's top across the river)
    # the river runs west to east, its depth by row: at each row every column is one tone, its waves' glints aside (a px in ten at most): no slab of it in another
    off = [(i, dx) for i in range(36) for dx, scan in cols.items() if abs(lum(scan[i]) - sorted(lum(s[i]) for s in cols.values())[1]) > 25]
    assert len(off) <= 17, off


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
    g.wait("HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=8000)
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
