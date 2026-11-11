"""Moving: walking and sprinting speeds, taps, turning with two keys held, and the screen agreeing with the server."""


def speed(rec, skip_ms=300):
    """Tiles per second over a recording, ignoring the start."""
    pts = [r for r in rec if r[0] > skip_ms]
    return abs(pts[-1][1] - pts[0][1]) / ((pts[-1][0] - pts[0][0]) / 1000)


def backward_jumps(rec, axis, sign):
    i = 1 if axis == "x" else 2
    return max(((rec[k - 1][i] - rec[k][i]) * sign for k in range(1, len(rec))), default=0)


def test_walk_and_sprint_speeds(game):
    game.start_recording()
    game.hold(["d"], 1500)
    walk = game.recording()
    game.sleep(400)
    game.start_recording()
    game.hold(["Shift", "a"], 1500)
    sprint = game.recording()
    assert 4.3 < speed(walk) < 5.7, speed(walk)
    assert 8.5 < speed(sprint) < 11.5, speed(sprint)
    game.sleep(500)
    assert game.pos() == (game.server()["x"], game.server()["y"])


def test_taps_move_one_tile_and_never_snap_back(game):
    x0, _ = game.pos()
    for hold in (20, 60, 120):
        game.start_recording()
        game.hold(["d"], hold)
        game.sleep(500)
        rec = game.recording()
        assert backward_jumps(rec, "x", 1) < .1
    x1, _ = game.pos()
    assert x1 - x0 == 3                                   # three taps, three tiles
    game.start_recording()
    for _ in range(6):                                    # rapid taps: never thrown back to the start
        game.hold(["a"], 40)
        game.sleep(50)
    game.sleep(600)
    assert backward_jumps(game.recording(), "x", -1) < .1
    assert game.pos() == (game.server()["x"], game.server()["y"])


def test_two_keys_never_slide_diagonally(game):
    for first, second in (("d", "w"), ("s", "a")):
        game.start_recording()
        game.page.keyboard.down(first)
        game.sleep(130)
        game.page.keyboard.down(second)
        game.sleep(700)
        game.page.keyboard.up(second)
        game.page.keyboard.up(first)
        game.sleep(500)
        rec = game.recording()
        # a diagonal step moves visibly on both axes in one frame (sub-pixel snaps onto the lane don't count)
        where = [(round(rec[k][0]), rec[k - 1][1:], rec[k][1:]) for k in range(1, len(rec))
                 if abs(rec[k][1] - rec[k - 1][1]) > .01 and abs(rec[k][2] - rec[k - 1][2]) > .01]
        assert not where, (first, second, where)
    assert game.pos() == (game.server()["x"], game.server()["y"])


def test_walls_stop_you_and_turn_you(game):
    game.stamp(1, 0, ["M"])                               # a rock right in front
    x0, y0 = game.pos()
    game.hold(["d"], 400)
    game.sleep(300)
    assert game.pos() == (x0, y0)                         # blocked: you stay
    assert game.js("ents.get('agent' + myId).fx") == 1    # but you now face it


def test_you_jump_up_a_layer_but_not_two(game):
    # north of you: a ledge one layer up (2 rows), then ground three layers up
    game.stamp(-3, -6, ["......."] * 5, levels=["3333333"] * 3 + ["1111111"] * 2)
    x, y = game.pos()
    game.hold(["w"], 1100)                                      # one tile, a jump up, along the ledge, then the wall
    game.sleep(500)
    s = game.server()
    assert (s["x"], s["y"]) == (x, y - 3) and game.pos() == (s["x"], s["y"])
    assert game.js(f"levelAt({s['x']}, {s['y']})") == 1


def test_hop_down_off_a_hill_edge(game):
    # you stand on a hill (level 1) two tiles in from its west edge: walk west and hop down
    game.stamp(-3, -2, ["......."] * 5, levels=["0111110"] * 4 + ["0000000"])
    x, y = game.pos()
    assert game.js(f"levelAt({x}, {y})") == 1
    game.hold(["a"], 900)
    game.sleep(500)
    s = game.server()
    assert s["x"] <= x - 3 and game.js(f"levelAt({s['x']}, {s['y']})") == 0 and game.pos() == (s["x"], s["y"])
    low = s["x"]
    game.hold(["d"], 700)                                       # and a jump back up the same edge
    game.sleep(500)
    s = game.server()
    assert s["x"] > low and s["x"] >= x - 2 and game.js(f"levelAt({s['x']}, {s['y']})") == 1 and game.pos() == (s["x"], s["y"])


def test_higher_ground_is_drawn_higher_and_clicks_find_it(game):
    # a terrace three layers up just north of you: drawn 18 art px higher (relief.js, 6 a layer), you on it too
    game.stamp(-2, -4, ["....."] * 3, levels=["33333"] * 3)
    x, y = game.pos()
    z = game.js("zoom")
    assert game.js(f"liftAt({x}, {y - 3})") == 24 * z and game.js(f"liftAt({x}, {y})") == 0
    # a click on where the terrace's tile is drawn finds that tile, not the one under it on the screen
    S, ox, oy = game.js("TS()"), *game.js("screenOrigin()")
    mx, my = ox + x * S + S / 2, oy + (y - 2) * S - 24 * z + S / 2
    assert game.js(f"tileAtScreen({mx}, {my})") == {"x": x, "y": y - 2}
    game.js(f"ents.get('agent' + myId).y = {y - 3}")             # someone up there is lifted with it
    assert game.js("liftOf(ents.get('agent' + myId))") == 24 * z
