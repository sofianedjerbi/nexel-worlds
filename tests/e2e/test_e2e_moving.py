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


def test_cliffs_stop_you_and_stairs_take_you_up(game):
    # a hill two rows north: 7 wide, 6 deep, stairs (B: level 1, going down south) in the middle of its south edge
    game.stamp(-3, -7, ["......."] * 6, levels=["1111111"] * 5 + ["11BB111"])
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x + 2}, y: {y}}})")          # under the cliff, beside the stairs
    game.sleep(700)
    game.hold(["w"], 700)                                       # walk north: one tile, then the cliff
    game.sleep(400)
    assert game.pos() == (x + 2, y - 1) == (game.server()["x"], game.server()["y"])
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")          # to the stairs' landing
    game.sleep(800)
    game.hold(["w"], 900)                                       # up the stairs and onto the hill
    game.sleep(400)
    s = game.server()
    assert s["y"] <= y - 3 and game.pos() == (s["x"], s["y"])
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
    game.hold(["d"], 600)                                       # and no climbing back up the same edge
    game.sleep(400)
    assert game.server()["x"] == x - 3
