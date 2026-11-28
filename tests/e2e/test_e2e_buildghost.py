"""Build mode with a block of the land in hand (build.js, buildghost.js), as the fifth audit's newcomer played it: a wall
two high with no height key (Space on your own block puts the next on top), E and Q a level a press, a row begun on a
wall's top stays at that height (a roof), the ghost of the block where it will go (red where it cannot), a few words
and no red sentence; X by hand digs down (it answered "Needs a hoe"); a phone: A held with the stick is a row."""
import pytest

from clock import stepped_wait
from test_e2e_hd_sun import hd
from test_e2e_touch import touch_game

MID = "(s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }"
# the picture's px at the middle of the ghost's top (the HD look's own canvas, its marks on it): [r, g, b]
GHOST_PX = """(() => { const d = BuildGhost.drew, k = devicePixelRatio; if (!d || !d.at) return null; return [...HdLook.read(Math.round(d.at[0] * k), Math.round(d.at[1] * k), 1, 1).data.slice(0, 3)]; })()"""
BUILT = "!Build.S.working && ![...Build.S.plans.values()].some((j) => j.state !== 'bad') && !myAction"


def row(g, first, arrows):
    """Space held, the arrows pressed: a row; -> presses"""
    k = g.page.keyboard
    k.down(" ")
    for a in arrows:
        at = g.js("[Build.S.at.x, Build.S.at.y]")
        k.press(a)
        g.wait(f"Build.S.at.x !== {at[0]} || Build.S.at.y !== {at[1]}", 3000)
    k.up(" ")
    return 1 + len(arrows)


@pytest.mark.quick
def test_a_wall_four_long_two_high_with_no_height_key(game):
    """Z, Space held and three steps east, Space held and three steps back: nine presses, eight blocks, no E."""
    game.clear_area(8)
    x, y = game.pos()
    game.give(dirt=10)
    game.hold_item("dirt")
    game.face(1, 0)
    game.press("z")
    game.wait("Build.on", 3000)
    assert game.js("Build.rows()")[1][:2] == ["Space", "Place dirt"] and game.js("Build.rows()")[3] == ["X", "Break"]
    presses = 1 + row(game, " ", ["ArrowRight"] * 3)
    assert all(z == 1 for z in game.js("[...Build.S.plans.values()].map((j) => j.z)"))      # (some are built already)
    presses += row(game, " ", ["ArrowLeft"] * 3)                 # back over them: each on top of the one planned or built there
    game.wait(BUILT, 30000)
    assert game.js(f"[0, 1, 2, 3].map((i) => topAt({x + 1} + i, {y}))") == [2] * 4 and presses == 9, presses
    assert game.inv("dirt") == 2 and not game.errors


def test_e_goes_up_one_level_and_the_ghost_says_where_in_a_few_words(game):
    """The audit: "E jumped to +2 and says in red: 'Nothing holds it: put it against a block'"."""
    game.clear_area(8)
    x, y = game.pos()
    game.give(dirt=6, stone_block=6)
    game.stamp(1, 0, ["."], levels=["1"])                        # a block of earth east of you
    game.hold_item("dirt")
    game.face(1, 0)
    game.press("z")
    game.wait("Build.on && Build.level() === 1", 3000)
    game.frames(2)
    d = game.js("BuildGhost.drew")
    assert d and [d["x"], d["y"], d["z"], d["ok"]] == [x + 1, y, 2, True] and d["take"] == [x + 1, y, 1], d      # the ghost on top of the block; X's outline on the block
    game.press("e", 100)
    game.frames(2)
    h, d = game.js("Build.hint(Build.S.at)"), game.js("BuildGhost.drew")
    assert h["z"] == 3 and h["far"] is True and h["text"] == "", h         # one level up: in the air over it, nothing beside it: nothing said
    assert d.get("z") is None, d                                            # no ghost: its box dotted alone (test_e2e_build_face.py)
    assert game.js("Build.rows()")[0][1] == "BUILD · +1 · leave"
    game.press("q", 100)
    assert game.js("Build.hint(Build.S.at).z") == 2 and game.js("Build.hint(Build.S.at).ok")
    game.give(plank=2)                                            # (what is not a block of the land goes a storey, as it did)
    game.hold_item("plank")
    game.press("e", 100)
    assert game.js("Build.level()") == 1 + game.js("Floors.STOREY")
    assert not game.errors


def test_a_row_begun_on_a_wall_s_top_stays_at_its_height_a_roof(game):
    """Two walls two high, three tiles of open ground between them: Space held from the west wall's top to the east
    one's is a roof at their height: no E, no block on the floor."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(1, -2, ["....."], levels=["20002"])
    game.give(stone_block=8)
    game.hold_item("stone_block")
    game.js(f"(() => {{ Build.toggle(true); Build.S.at = {{x: {x + 1}, y: {y - 2}}}; Build.S.plane = Build.S.deep = null; return 1; }})()")
    game.wait("Build.on && Build.level() === 2", 3000)
    assert row(game, " ", ["ArrowRight"] * 4) == 5
    assert all(z == 3 for z in game.js("[...Build.S.plans.values()].map((j) => j.z)"))
    game.wait(BUILT, 40000)
    assert game.js(f"[0, 1, 2, 3, 4].map((i) => [solidAt({x + 1} + i, {y - 2}, 3), solidAt({x + 1} + i, {y - 2}, 1)])") == [[True, True]] + [[True, False]] * 3 + [[True, True]]
    assert game.inv("stone_block") == 3 and not game.errors


def test_x_by_hand_digs_down_and_does_not_ask_for_a_hoe(game):
    """Bare hands on the meadow: X is "Dig down", and it digs the block you face, the one its box is on (it dug the
    one under you, unmarked: "it should dig the selected highlighted block, not under the player")."""
    game.clear_area(6)
    x, y = game.pos()
    game.press("0", 200)
    game.face(1, 0)
    game.wait("$('actions').innerText.includes('Dig down')", 3000)
    assert game.js("(() => { const t = Target.target('alt'); return t && [t.x, t.y, t.z]; })()") == [x + 1, y, 0]
    game.press("x", 100)
    game.wait(f"topAt({x + 1}, {y}) === -1 && !myAction", 20000)
    assert game.js("myAt.z") == 0
    assert "hoe" not in game.toast() and game.inv("dirt") == 1 and not game.errors


def test_in_the_hd_look_the_ghost_is_the_block_in_its_own_paint_and_red_where_it_cannot_go(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    g.give(stone_block=4, dirt=4)
    g.hold_item("dirt")
    g.face(1, 0)
    g.rest()
    g.press("z")
    g.wait("Build.on", 3000)
    g.frames(3)
    d = g.js("BuildGhost.drew")
    assert d and d["ok"] and d["z"] == 1 and d["u"] == g.js("HdLook.art().u") and d["u"] >= 1 and g.js("WayShow.u === undefined"), d       # (whole art px of this look, from its own hook)
    soil = g.js(GHOST_PX)
    assert soil[0] > soil[1] > soil[2] and soil[0] - soil[2] > 40, soil                             # earth over the grass: warm (the grass is green: g over r)
    g.press("e", 100)
    g.frames(3)
    d = g.js("BuildGhost.drew")
    assert d.get("z") is None and g.js("Build.hint(Build.S.at).far"), d       # in the air, nothing beside it: no ghost, a dotted box
    g.js(f"(() => {{ Build.S.at = {{x: {x}, y: {y}}}; Build.S.plane = Build.S.deep = null; return 1; }})()")    # on your own tile: red where it cannot go (you stand there)
    g.frames(3)
    d = g.js("BuildGhost.drew")
    assert d["ok"] is False and d["z"] == 1, d                               # (its px: your body is over them)
    g.js(f"(() => {{ Build.S.at = {{x: {x + 1}, y: {y}}}; return 1; }})()")
    g.press("q", 100)
    g.hold_item("stone_block")
    g.frames(3)
    grey = g.js(GHOST_PX)
    assert grey[0] < soil[0] - 25 and abs(grey[0] - grey[1]) < 25, (grey, soil)                     # stone: grey over the grass, not the earth's beige
    assert not g.errors


# the picture in a box of 16 art px round a place of it (px of the page): its px as numbers
BOX = """([x, y, u]) => { const k = devicePixelRatio, w = 16 * u * k, q = HdLook.read(Math.round(x * k - w / 2), Math.round(y * k - w / 2), w, w).data, o = []; for (let i = 0; i < q.length; i += 4) o.push(q[i] << 16 | q[i + 1] << 8 | q[i + 2]); return o; }"""


def test_a_ghost_behind_a_wall_is_not_drawn_through_it_and_the_window_does_not_open_on_a_wall_you_stand_by(browser, server):
    """A wall three long, two high, of blocks of earth put down. Standing just south of it, or behind it, the x-ray window
    stays shut (it opened on the ground behind the wall: a block lost its top); the ghost of a block behind the wall
    keeps one px in two there (it was drawn whole, as if in front of the wall)."""
    g = hd(browser, server)
    x, y = g.pos()
    g.give(dirt=10)
    g.rpc("dev_teleport", x=x + 1, y=y - 1)
    g.arrive()
    for z in (1, 2):                                                             # (put, as a player puts them: the land's own ridge two high still has the window, test_e2e_hd_land.py)
        for i in range(3):
            g.js("(a) => rpc('act', a)", {"tool": "place", "args": {"x": x + i, "y": y - 2, "z": z, "item": "dirt"}})
            g.wait(f"topAt({x + i}, {y - 2}) === {z} && !myAction", timeout=15000)
    g.wait(f"[0, 1, 2].every((i) => matAt({x} + i, {y - 2}) === 'd')", timeout=4000)
    g.rest()
    for dx, dy in ((2, -1), (0, -1), (1, -3)):
        g.rpc("dev_teleport", x=x + dx, y=y + dy)
        g.arrive()
        g.rest()
        g.frames(2)                                              # (a window that opens shows from its first frame: its alpha grows each frame it has tiles)
        assert g.js("HdLook.win.a") == 0 and not g.js(f"[0, 1, 2].some((i) => HdLook.winAt({x} + i, {y - 3}) || HdLook.winAt({x} + i, {y - 2}))"), (dx, dy, g.js("JSON.stringify(HdLook.win)"))
    g.rpc("dev_teleport", x=x + 1, y=y)
    g.arrive()
    g.give(dirt=4)
    g.hold_item("dirt")
    seen = {}
    g.js("(() => { Target.off = true; return 1; })()")                          # (the ghost's own px: not the cell's box, target.js)
    for name, cy in (("behind", y - 3), ("front", y - 1)):
        g.js(f"(() => {{ Build.toggle(true); Build.S.at = {{x: {x + 1}, y: {cy}}}; Build.S.plane = Build.S.deep = null; return 1; }})()")
        g.wait("Build.on", 3000)
        g.frames(3)
        d = g.js("BuildGhost.drew")
        assert d and d["ok"] and d["z"] == 1, (name, d)
        on = g.js(BOX, [*d["at"], d["u"]])
        g.js("Build.toggle(false)")
        g.frames(3)
        seen[name] = (d["hid"], sum(1 for p, q in zip(on, g.js(BOX, [*d["at"], d["u"]])) if p != q))     # (how many px the ghost changed there)
    assert seen["behind"][0] is True and seen["front"][0] is False, seen
    assert 0 < seen["behind"][1] < seen["front"][1] * .6, seen                  # behind the wall: one px in two of it, fainter
    assert not g.errors


def test_on_a_phone_a_held_with_the_stick_is_a_row_and_held_still_places_once(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        cdp = ctx.new_cdp_session(g.page)
        send = lambda kind, pts: cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": px, "y": py, "id": i} for i, (px, py) in pts.items()]})
        x, y = g.pos()
        g.give(dirt=12); g.js("selectItem('dirt')")
        g.face(1, 0)
        g.wait("getComputedStyle($('tBuild')).display !== 'none'", 4000)   # (the button is up once the HUD drew it, touch.js: tapped before, the tap fell on nothing)
        g.page.touchscreen.tap(*g.js(MID, "#tBuild")); g.wait("Build.on", 3000)
        a = tuple(g.js(MID, "#tA"))
        send("touchStart", {2: a})
        g.wait("Build.S.plans.size + (topAt(%d, %d) > 0 ? 1 : 0) >= 1" % (x + 1, y), 3000)
        stepped_wait(g.page, 900)                                # held still: one block, not a pile (a second would go on top of the first)
        assert g.js(f"[...Build.S.plans.values()].filter((j) => j.x === {x + 1}).length + topAt({x + 1}, {y})") == 1
        # the stick pushed east, A still held, till the cursor is two tiles on; then both thumbs lift. (A held stick steps on
        # at the cursor's own pace, build.js: how far it goes before the lift reaches the page is the machine's, so the row
        # is checked to wherever it got: one block on every tile from your feet on, none past its end)
        send("touchStart", {2: a, 1: (90, 600)}); send("touchMove", {2: a, 1: (130, 600)})
        g.wait(f"Build.S.at.x >= {x} + 3", 3000)
        send("touchEnd", {})
        g.wait("!Build.S.dir && !Build.S.hold", 3000)
        g.wait(BUILT, 30000)
        tops = g.js(f"Array.from({{length: 13}}, (_, i) => topAt({x} + i, {y}))")      # (the cursor goes 10 tiles from you at most)
        n = tops.index(0, 1) - 1
        assert n >= 3 and tops[:n + 2] == [0] + [1] * n + [0] and not g.errors, (tops, g.errors)
    finally:
        ctx.close()
