"""Digging down in build mode (web/js/build.js, keyhole.js, tiles.js). "depth visualisation is unintuitive", and of
five mockups the user chose "Earth and a keyhole": dug ground is earth, a shade darker a layer down; where the ground
hides the cursor only its own column is seen through; beside it, how far down it is. By keys: Q sinks the cursor a
layer into the ground, E brings it back, X digs the room to stand there: a way down is a tunnel, a step at a time."""

GRASS = 0xff70d4c0                                             # (the meadow's green, #c0d470, as a block's px has it)
GREEN = f"""([x, y, rows, cols]) => {{ const b = blockOf(x, y), o = (y - b.by * B) * 16 * BW + (x - b.bx * B) * 16; let n = 0;
  for (const j of rows) for (const i of cols) if (b.px[o + j * BW + i] === {GRASS}) n++; return n; }}"""
DRAWN = "dirtyTiles.length === 0"


def test_q_sinks_the_cursor_a_layer_and_x_digs_a_way_down_a_step_at_a_time(game):
    """On solid ground Q did nothing but say "floor -1" (it counted storeys); now each Q is a layer into the ground,
    said beside the cursor and in the corner. There X digs the room to stand in, and what is over it stays: a way down
    is dug a step at a time, a tunnel ("like minecraft ... this enforce me to dig huge columns": it dug every layer
    over the cursor). Where no air is beside it, it says so."""
    game.clear_area(8)
    game.give(pickaxe=1)
    x, y = game.pos()
    game.press("ArrowDown", 200)                              # (facing south: the cursor starts on the tile in front)
    game.press("b")
    rows = lambda: {r[0]: r[1:] for r in game.js("Build.rows()")}
    assert game.js("Build.level()") == 0 and rows()["Q E"][0] == "A layer down, up" and rows()["X"][0] == "Dig a hole"
    for depth in (1, 2, 3):
        game.press("q", 120)
        assert game.js("Build.level()") == -depth and rows()["B"][0] == f"BUILD · -{depth} · leave"
    assert rows()["X"] == ["Dig the step before it first", "bad"]       # (three down, beside you: shut in)
    game.wait("Keyhole.shown", 3000)                           # (in the ground: its column, faint, down to the cursor)
    game.press("x")
    assert game.js("Build.S.plans.size") == 0
    game.press("e", 120); game.press("e", 120)
    for k in range(3):                                         # a step down a tile, three tiles south
        if k:
            game.press("ArrowDown", 120); game.press("q", 120)
        below = game.js("Build.level() - myAt.z")             # (said from where you stand: you go down it as it is dug)
        assert game.js("Build.level()") == -1 - k and below < 0 and rows()["X"][0] == f"Dig a way to {below}"
        game.press("x")
        game.wait(f"surfacesAt({x}, {y + 1 + k})[0] === {-1 - k} && Build.S.plans.size === 0", 30000)
    assert game.js(f"surfacesAt({x}, {y + 3})") == [-3, 0]   # the third step: under a roof, the land over it left
    assert game.js("Build.level()") == -3 and game.inv("dirt") == 2 and game.inv("stone") == 3    # (under sea level: stone)
    game.press("b")
    assert not game.errors


def test_a_dug_floor_is_earth_with_no_grass_at_the_foot_of_its_walls(game):
    """A hole three deep had a grass floor and grass lips: it looked like a raised table; and the grass of the ground
    round it showed in a line at the foot of each wall ("weird lines in the middle")."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(-1, 2, ["..."] * 3, levels=["ccc"] * 3)      # a pit three deep (x-1..x+1, y+2..y+4)
    game.stamp(3, -2, ["...."], levels=["abcd"])            # a stair dug down, east
    game.wait(DRAWN, 8000); game.sleep(300)
    green = lambda dx, dy, rows=range(16), cols=range(16): game.js(GREEN, [x + dx, y + dy, list(rows), list(cols)])
    assert [green(0, 3), green(0, 4)] == [0, 0]               # the pit's floor: earth
    assert green(0, 1, [14, 15]) == 0                          # the ground north of it: no grass under its wall's foot
    assert green(2, -2, range(2, 14), [14, 15]) == 0 and green(3, -2) == 0     # west of the first step, past its wall's side; the step
    game.sleep(200)
    assert not game.errors


def test_the_keyhole_shows_the_cursor_where_the_ground_in_front_hides_it(game):
    """Down a hole the grass in front is drawn over the floor: the cursor's own tile is seen through, and no more (the
    x-ray circle that went round it is yours alone); on the ground, where nothing hides it, there is none."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(-1, 2, ["..."] * 3, levels=["ccc"] * 3)
    game.wait(DRAWN, 8000)
    game.press("b")
    game.js(f"Build.S.at = {{x: {x}, y: {y + 4}}}")           # the pit's south row: under the grass in front
    assert game.js("Build.level()") == -3
    game.wait("Keyhole.shown", 3000)
    assert game.js("xray.a") < .1
    game.js(f"Build.S.at = {{x: {x + 3}, y: {y}}}")
    game.wait("!Keyhole.shown", 3000)
    game.press("b")
    assert not game.errors


def test_a_pocket_dug_under_the_meadow_is_drawn_open_where_you_stand_in_it(game):
    """doben4 at the end of a stair dug east, eight down under a roof left at ground level: the cave view drew its
    floor four tiles south of its stair, on the grass ("dauben is completely buried and appear here... the underground
    view is buggy as hell"). A hollow dug under level ground is drawn open, as a hole is, joined to its stair."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(-5, 0, ["......"], levels=["cdefgh"], roofs=["000008"], heads=["000002"])
    game.rpc("dev_teleport", x=x, y=y, z=-8)
    game.wait(f"myAt && myAt.z === -8 && myAt.x === {x}", 5000)
    game.wait(DRAWN, 8000)
    assert game.js(f"[topAt({x}, {y}), levelAt({x}, {y}), standAt({x}, {y}), hiddenAt({x}, {y}), caveOpen]") == [0, -8, -8, False, False]
    assert game.js(f"[levelAt({x - 1}, {y}), levelAt({x + 1}, {y})]") == [-7, 0]        # (the stair beside it; the meadow)
    game.sleep(300)
    assert not game.errors
