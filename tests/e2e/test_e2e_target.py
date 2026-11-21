"""What a key acts on is drawn as the CELL it is (target.js): a box in the land at the cell's own height, and the
cell drawn is the cell that changes after the key, in the six situations the owner found confusing ("eye-level ?
feet level ? air ? real block ?")."""
import pytest

from test_e2e_hd_sun import hd

SNAP = """([x0, y0]) => { const o = []; for (let y = y0 - 2; y <= y0 + 2; y++) for (let x = x0 - 2; x <= x0 + 2; x++) for (let z = -8; z <= 7; z++) if (solidAt(x, y, z)) o.push([x, y, z].join()); return o; }"""
# is the box's colour on the picture at a place of the land (the HD look's own canvas, its marks on it), within 2 art px of it?
NEAR = """([x, y, z, c]) => { const a = HdLook.screenOf(x, y, z), k = devicePixelRatio, u = HdLook.art().u * k; if (!a) return false;
  const X = Math.round(a[0] * k - 2 * u), Y = Math.round(a[1] * k - 2 * u), n = Math.round(4 * u) + 1, d = HdLook.read(X, Y, n, n).data;
  for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - c[0]) + Math.abs(d[i + 1] - c[1]) + Math.abs(d[i + 2] - c[2]) < 40) return true; return false; }"""
# ...anywhere on a cell's top: [x, y, z, colour] -> how many px of that colour
ON_TOP = """([x, y, z, c]) => { const a = HdLook.screenOf(x, y, z), b = HdLook.screenOf(x + 1, y + 1, z), k = devicePixelRatio; if (!a || !b) return 0;
  const X = Math.round(a[0] * k), Y = Math.round(a[1] * k), d = HdLook.read(X, Y, Math.max(1, Math.round((b[0] - a[0]) * k)), Math.max(1, Math.round((b[1] - a[1]) * k))).data; let n = 0;
  for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - c[0]) + Math.abs(d[i + 1] - c[1]) + Math.abs(d[i + 2] - c[2]) < 40) n++; return n; }"""
CREAM, TAKE = (255, 248, 232), (255, 157, 60)


def stage(g, s):
    g.clear_area(6)
    if s == "block":
        g.stamp(1, 0, ["."], levels=["1"])
    if s == "wall":
        g.stamp(1, -1, ["."] * 3, levels=["2"] * 3)
    if s == "cave":
        g.stamp(-3, -2, ["......."] * 5, levels=["4444444", "4444444", "0000444", "4444444", "4444444"],
                roofs=["0000000", "0000000", "4444000", "0000000", "0000000"], heads=["0000000", "0000000", "2222000", "0000000", "0000000"])
    if s == "ledge":
        g.stamp(-3, -2, ["...."] * 5, levels=["2222"] * 5)
    if s == "room":
        g.stamp(-2, -2, ["....."] * 5, levels=["ddddd"] * 5)
    if s == "stair":
        g.stamp(-2, -1, ["......"] * 3, levels=["0abcde"] * 3)
    if s == "water":
        g.stamp(-1, -2, ["((((("] * 5)
    if s == "tree":
        g.stamp(1, 0, ["T"])
    g.rest()
    g.face(1, 0)


def changed(g, key, x, y):
    before = set(g.js(SNAP, [x, y]))
    g.press(key, 300)
    g.wait(f"(() => {{ const s = new Set({list(before)!r}); const n = ({SNAP})([{x}, {y}]); return n.length !== s.size || n.some((k) => !s.has(k)); }})()".replace("'", '"'), 8000)
    g.wait("!myAction && !Build.S.working", 8000)
    after = set(g.js(SNAP, [x, y]))
    return [tuple(int(v) for v in k.split(",")) for k in (before ^ after)]


@pytest.mark.quick
@pytest.mark.parametrize("s", ["meadow", "block", "wall", "ledge"])
def test_build_mode_the_box_is_the_cell_space_and_x_change(browser, server, s):
    """Build mode, earth in hand: Space's cell is drawn cream, X's orange and hatched, each at its own height (its
    top's corner on the screen is the box's colour), and each is the cell that changes."""
    game = hd(browser, server)
    game.give(dirt=6)
    stage(game, s)
    x, y = game.pos()
    game.hold_item("dirt")
    game.press("z")
    game.wait("Build.on", 3000)
    game.frames(3)
    put, take = game.js("Target.target('use')"), game.js("Target.target('alt')")
    assert put["kind"] == "place" and take["kind"] == "break", (put, take)
    drew = {d["key"]: d for d in game.js("Target.drew")}
    assert set(drew) == {"use", "alt"}
    assert all(game.js(NEAR, [put["x"] + i, put["y"], put["z"], CREAM]) for i in (0, 1)), put          # (Space's box: its top's far corners)
    assert game.js(ON_TOP, [take["x"], take["y"], take["z"], TAKE]) > 20, take                             # (X's: its top hatched, drawn over the ghost on it)
    assert changed(game, " ", x, y) == [(put["x"], put["y"], put["z"])]
    game.press("z")
    game.wait("!Build.on", 3000)
    game.rpc("dev_teleport", x=x, y=y)
    game.arrive()
    stage(game, s)
    game.press("z")
    game.wait("Build.on", 3000)
    take = game.js("Target.target('alt')")
    assert changed(game, "x", x, y) == [(take["x"], take["y"], take["z"])]
    assert not game.errors


@pytest.mark.parametrize("s", ["meadow", "block", "ledge", "stair"])
def test_playing_by_keys_the_drawn_cell_is_the_cell_that_changes(browser, server, s):
    """Out of build mode, earth in hand: Space raises the cell drawn (on the ground in front, on the block's top,
    on the low ground past the ledge); X digs the block you stand on, drawn orange under your feet."""
    game = hd(browser, server)
    game.give(dirt=6)
    stage(game, s)
    x, y = game.pos()
    game.hold_item("dirt")
    game.press("ArrowRight", 60)              # (playing by keys: the aim is the tile you face)
    game.rpc("dev_teleport", x=x, y=y)
    game.arrive()
    game.face(1, 0)
    game.frames(3)
    put, dig = game.js("Target.target('use')"), game.js("Target.target('alt')")
    assert put and put["kind"] == "place" and dig and dig["kind"] == "break", (put, dig)
    assert changed(game, " ", x, y) == [(put["x"], put["y"], put["z"])]
    assert changed(game, "x", x, y) == [(dig["x"], dig["y"], dig["z"])]
    assert not game.errors


def test_in_a_cave_space_r_and_build_x_take_the_cells_drawn(browser, server):
    """In a tunnel facing its end, a pickaxe in hand: Space takes the cell at your body, R the one at your head,
    build mode's X the one its box is on: each drawn as a box before, each the one that goes."""
    game = hd(browser, server)
    game.give(pickaxe=1, dirt=2)
    stage(game, "cave")
    x, y = game.pos()
    game.hold_item("pickaxe")
    game.press("ArrowRight", 60)
    game.face(1, 0)
    game.js("(() => { WayShow.mine && WayShow.mine(); return 1; })()")
    game.frames(3)
    cells = {c["key"]: c for c in game.js("Target.cells()")}
    if "use" in cells:
        assert cells["use"]["z"] == game.js("myZ(myPos().x, myPos().y)") + 1
        u = cells["use"]
        assert changed(game, " ", x, y) == [(u["x"], u["y"], u["z"])]
    up = game.js("Target.target('up')")
    if up:
        assert changed(game, "r", x, y) == [(up["x"], up["y"], up["z"])]
    game.hold_item("dirt")
    game.press("z")
    game.wait("Build.on", 3000)
    take = game.js("Target.target('alt')")
    assert take and take["kind"] == "break"
    assert changed(game, "x", x, y) == [(take["x"], take["y"], take["z"])]
    assert not game.errors


def test_a_cell_in_the_air_is_red_with_its_shadow_on_the_ground(browser, server):
    """E twice over the meadow: nothing holds it: red, and under it on the ground its shadow, one px in two."""
    game = hd(browser, server)
    game.give(dirt=2)
    stage(game, "meadow")
    game.hold_item("dirt")
    game.press("z")
    game.wait("Build.on", 3000)
    game.press("e", 100)
    game.press("e", 100)
    game.frames(3)
    t = game.js("Target.target('use')")
    assert t["ok"] is False and t["z"] == 3, t
    assert game.js(NEAR, [t["x"], t["y"], t["z"], [232, 85, 74]])
    assert not game.errors


# what was drawn this frame for a key, and the cell it names: one call (README rule 9)
DREW = """(k) => { frame(performance.now()); return [Target.target(k), Target.drew.filter((d) => d.key === k)]; }"""
KEY = {" ": "use", "r": "up", "x": "alt"}


def drawn(g, k):
    """The cell key k acts on, and that it was drawn this frame (a box; X: its mark under you; the way's block: drawn by wayshow.js)."""
    c, d = g.js(DREW, KEY[k])
    assert c and len(d) == 1 and (d[0]["x"], d[0]["y"], d[0]["z"]) == (c["x"], c["y"], c["z"]), (k, c, d)
    if KEY[k] == "alt" and d[0].get("mine"):
        assert g.js(ON_TOP, [c["x"], c["y"], c["z"], TAKE]) > 10, c                        # (X: orange round your feet, at your floor)
    elif d[0].get("way"):
        assert g.js("WayShow.block") is not None                                           # (one mark: the way's own box on that block)
    return c


def test_the_first_frame_after_arriving_has_its_boxes(browser, server):
    """Nothing pressed since arriving, the mouse not on the land: Space's and X's cells are drawn (it was empty until the first press or step)."""
    game = hd(browser, server)
    game.give(dirt=2)
    game.hold_item("dirt")
    stage(game, "meadow")
    game.frames(2)
    assert drawn(game, " ")["kind"] == "place" and drawn(game, "x")["kind"] == "break"
    assert not game.errors


@pytest.mark.parametrize("s,item,keys", [("cave", "pickaxe", "r "), ("room", "dirt", " "), ("room", "pickaxe", "x")])
def test_with_the_way_out_shown_each_key_has_its_mark_and_takes_that_cell(browser, server, s, item, keys):
    """A tunnel's end, a dug room: the way out of the ground is shown, and what Space, R and X would take is drawn all
    the same (it was only the guide: "what does Space hit?"), each the cell that changes."""
    game = hd(browser, server)
    game.give(pickaxe=1, dirt=4)
    stage(game, s)
    x, y = game.pos()
    game.hold_item(item)
    game.face(1, 0)
    game.wait("WayShow.cur", 12000)                          # (stood still: the guide is up)
    for k in keys:
        c = drawn(game, k)
        assert changed(game, k, x, y) == [(c["x"], c["y"], c["z"])], (k, c)
    assert not game.errors


def test_earth_into_water_marks_the_waters_face_not_a_block_on_it(browser, server):
    """Mid water, earth in hand: Space makes that tile's water shallower (its bed seldom shows it). What is drawn is
    that tile's face, flat: it was a block standing on the water, and nothing like it came."""
    game = hd(browser, server)
    game.give(dirt=2)
    stage(game, "water")
    x, y = game.pos()
    game.hold_item("dirt")
    game.face(1, 0)
    c = drawn(game, " ")
    assert c["kind"] == "use" and (c["x"], c["y"], c["z"]) == (x + 1, y, game.js(f"topAt({x + 1}, {y})")), c
    assert game.js(f"gndAt({x + 1}, {y})") == "("
    game.press(" ", 300)
    game.wait(f"gndAt({x + 1}, {y}) === '~'", 8000)             # (the tile drawn is the tile that changed)
    assert not game.errors


def test_build_mode_draws_no_brackets_on_you(browser, server):
    """Build mode at a two-high wall: a box for Space, a box for X, and nothing round your own cat (keyhole.js's marks)."""
    game = hd(browser, server)
    game.give(dirt=2)
    stage(game, "wall")
    game.hold_item("dirt")
    game.press("z")
    game.wait("Build.on", 3000)
    game.frames(2)
    assert sorted(d["key"] for d in game.js("Target.drew")) == ["alt", "use"]
    assert not game.js("(() => { frame(performance.now()); const m = Keyhole.marks; return !!m && m.drawn; })()")
    assert not game.errors


def test_a_phone_digs_a_step_with_the_way_out_shown(browser, server):
    """Upright phone in a tunnel, the way out shown: "Dig a step" is there and its tap takes R's cell (it was hidden
    while the guide's next block was Space's, and the tap went to nothing)."""
    from test_e2e_touch import touch_game
    ctx, game = touch_game(browser, server, 390, 844)
    try:
        game.rpc("dev_creatures", clear=60)
        game.give(pickaxe=1)
        stage(game, "cave")
        x, y = game.pos()
        game.hold_item("pickaxe")
        game.face(1, 0)
        game.wait("WayShow.cur && $('tDig').style.display === 'flex'", 12000)
        c = game.js("Target.target('up')")
        before = set(game.js(SNAP, [x, y]))
        b = game.js("(() => { const r = $('tDig').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
        game.page.touchscreen.tap(*b)
        game.wait(f"!solidAt({c['x']}, {c['y']}, {c['z']})", 8000)
        game.wait("!myAction && !pendingAct", 8000)
        after = set(game.js(SNAP, [x, y]))
        assert [tuple(int(v) for v in k.split(",")) for k in (before ^ after)] == [(c["x"], c["y"], c["z"])]
        assert not game.errors
    finally:
        ctx.close()
