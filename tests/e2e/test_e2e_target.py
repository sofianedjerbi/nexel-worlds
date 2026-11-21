"""What a key acts on is drawn as the CELL it is (target.js): a box in the land at the cell's own height, and the
cell drawn is the cell that changes after the key, in the six situations the owner found confusing ("eye-level ?
feet level ? air ? real block ?")."""
import pytest

from test_e2e_hd_sun import hd

SNAP = """([x0, y0]) => { const o = []; for (let y = y0 - 2; y <= y0 + 2; y++) for (let x = x0 - 2; x <= x0 + 2; x++) for (let z = -3; z <= 7; z++) if (solidAt(x, y, z)) o.push([x, y, z].join()); return o; }"""
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


@pytest.mark.parametrize("s", ["meadow", "block", "ledge"])
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
