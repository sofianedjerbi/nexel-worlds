"""Moving: walking and sprinting speeds, taps, turning with two keys held, and the screen agreeing with the server."""

import pytest


def game_s(a, b):
    """The game's time a recorded frame moved things by (s): the frame's own, 0.1 s at the most (render.js update: a
    longer one is cut there, as on any machine that cannot keep up)."""
    return min(b[0] - a[0], 100) / 1000


def gone(a, b):
    """Tiles a recorded frame moved you."""
    return abs(b[1] - a[1]) + abs(b[2] - a[2])


def free(rec):
    """The frames the walk went at its own pace, neither waiting for the world nor catching up with it (walk.js walkOn:
    past LEAD[0], 2 tiles ahead, it slows for a world that comes late, as it should; under -1 it goes a quarter faster).
    The lead that paced a frame is the one it began with: the one recorded after its move, less the move (a frame of
    0.625 tiles at 5 a second, catching up, was recorded at -0.42). On the runners the world comes late: the sprint by
    the page's clock was 8 for 10, a turn's pace 6.6."""
    return [(a, b) for a, b in zip(rec, rec[1:]) if b[0] > a[0] and -1 <= b[3] - gone(a, b) <= 2]


def speed(rec, skip_ms=300):
    """Tiles per second of the game's time the walk went at its own pace (free frames; a frame cut at 0.1 s counts 0.1 s:
    game_s. A runner's frames are 67 to 280 ms, and by the page's clock a walk read 2 tiles a second), ignoring the start
    and what follows the walk: its last frame that moved you (it ends on a tile, short of a frame's walk), and you
    standing after it (hold() waits for the server's answer once the key is up: 0.6 s of standing read 3.8)."""
    moved = [k for k in range(1, len(rec)) if gone(rec[k - 1], rec[k]) > 1e-6]
    pairs = free([r for r in rec[: moved[-1] if moved else 0] if r[0] > skip_ms])
    assert len(pairs) >= 3, ("too few frames at the walk's own pace", rec[:6])
    return sum(gone(a, b) for a, b in pairs) / sum(game_s(a, b) for a, b in pairs)


def slow(rec, pace):
    """The free frames of a walk under 0.8 of `pace`: [ms, frame ms, tiles, lead it began with]."""
    return [(round(a[0]), round(b[0] - a[0]), round(gone(a, b), 3), round(b[3] - gone(a, b), 2))
            for a, b in free([r for r in rec if r[0] > 300]) if gone(a, b) < .8 * pace * game_s(a, b)]


def backward_jumps(rec, axis, sign):
    i = 1 if axis == "x" else 2
    return max(((rec[k - 1][i] - rec[k][i]) * sign for k in range(1, len(rec))), default=0)


def test_walk_and_sprint_speeds(game):
    # (on a meadow of its own: 7.5 tiles east at a walk, then 15 west at a sprint. It walked over whatever the test before
    # it left, water at half the pace or a step to jump, and read 2.7 to 4 tiles a second now and then: #28)
    game.clear_area(14)
    game.start_recording()
    game.hold(["d"], 1500)
    walk = game.recording()
    game.sleep(400)
    game.start_recording()
    game.hold(["Shift", "a"], 1500)
    sprint = game.recording()
    assert 4.3 < speed(walk) < 5.7, (speed(walk), slow(walk, 5))
    assert 8.5 < speed(sprint) < 11.5, (speed(sprint), slow(sprint, 10))
    game.sleep(500)
    assert game.pos() == (game.server()["x"], game.server()["y"])


@pytest.mark.realtime
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


def test_letting_go_and_pressing_another_key_never_stalls(game):
    """Turning by releasing one key and pressing the next (not rolling onto it): the step under way is made first,
    on the server too, so you keep your pace (each such turn froze you 170-280 ms: sprinting round corners went at
    half speed), and turning right round goes straight back."""
    game.clear_area(14)
    page = game.page

    def turns(keys):
        game.start_recording()
        page.keyboard.down("Shift")
        for i in range(8):
            page.keyboard.down(keys[i % 2])
            game.sleep(300)
            page.keyboard.up(keys[i % 2])
        page.keyboard.up("Shift")
        rec = game.recording()
        still.extend((round(b[0]), round(b[3], 2)) for a, b in zip(rec, rec[1:]) if abs(b[1] - a[1]) + abs(b[2] - a[2]) < 1e-6)
        return speed(rec, 0)

    still = []                                                # (frames that did not move you: [ms, tiles ahead of the world])
    corner = turns("ds")
    game.sleep(600)
    assert game.pos() == (game.server()["x"], game.server()["y"])
    back = turns("da")
    game.sleep(600)
    assert game.pos() == (game.server()["x"], game.server()["y"])
    assert corner > 7.5 and back > 6.5, (corner, back, still[:30])        # (sprinting is 10 a second; it was 5.4 and 3)


def stops(rec, ms=60):
    """The pauses in a recorded walk, its ends left out: frames drawn with you where the frame before had you, two or
    more in a row and more than `ms` of the game's time (ms). (It was any gap of more than 60 ms between two frames that
    moved you: on the runners a frame alone is 70 to 180 ms, and every frame was a stop. At 60 frames a second the two
    frames are under the 60 ms: as it was)"""
    mid = [r for r in rec if rec[0][0] + 400 < r[0] < rec[-1][0] - 400]
    out, still, n = [], 0.0, 0
    for a, b in [*zip(mid, mid[1:]), (None, None)]:
        if b is not None and abs(b[1] - a[1]) + abs(b[2] - a[2]) <= 1e-6:
            still, n = still + game_s(a, b) * 1000, n + 1
            continue
        if n >= 2 and still > ms:
            out.append(round(still))
        still, n = 0.0, 0
    return out


@pytest.mark.realtime
def test_swimming_never_goes_tile_by_tile(game):
    """Nobody sprints in water. Sprint held (a phone's stick pushed far), your screen swam at sprint speed, got a
    tile ahead of the server and waited for it, at every tile."""
    game.clear_area(14)
    game.stamp(-12, -1, ["~" * 25] * 3); game.rest()
    page = game.page
    game.start_recording()
    page.keyboard.down("Shift")
    page.keyboard.down("d")
    game.sleep(1800)
    page.keyboard.up("d")
    page.keyboard.up("Shift")
    rec = game.recording()
    game.sleep(600)
    assert not stops(rec), stops(rec)
    assert game.pos() == (game.server()["x"], game.server()["y"])


@pytest.mark.realtime
def test_late_ticks_do_not_stop_you(game):
    """The server's word comes late and in lumps (a phone, a slow line): you walk on at your own pace (you were only
    ever allowed a tile ahead of its last word: sprinting, you stopped at every tile), and you end where it has you."""
    game.clear_area(14)
    game.rpc("dev_teleport", x=game.pos()[0] - 12, y=game.pos()[1])
    game.sleep(700)
    game.js("(() => { const o = onTick, q = []; onTick = (d) => q.push(d); setInterval(() => { for (const d of q.splice(0)) o(d); }, 220); return 1; })()")
    page = game.page
    game.start_recording()
    page.keyboard.down("Shift")
    page.keyboard.down("d")
    game.sleep(900)
    page.keyboard.down("s")
    game.sleep(600)
    page.keyboard.up("s")
    game.sleep(600)
    page.keyboard.up("d")
    page.keyboard.up("Shift")
    rec = game.recording()
    # (the walk's own pace in the game's time, where the world let it go: speed. It was the tiles gone, then the pace on
    # frames not cut: on a runner the lumps of late ticks put you past LEAD[0] and the walk slowed for them, as it
    # should, 6.8. Stopped at a tile ahead of the server's last word, as it was, the free frames would stand still)
    pace = speed(rec, 0)
    game.sleep(900)
    assert not stops(rec), stops(rec)
    assert pace > 8.5, (pace, slow(rec, 10))
    assert game.pos() == (game.server()["x"], game.server()["y"])


@pytest.mark.realtime
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
        # sliding diagonally is being off both lanes at once (sub-pixel snaps onto the lane don't count). (It was moving on
        # both axes in one frame: a frame of 85 ms on the runners finished the step east and began the one north, an L)
        off = lambda v: abs(v - round(v)) > .01
        where = [(round(r[0]), r[1:]) for r in rec if off(r[1]) and off(r[2])]
        assert not where, (first, second, where)
    assert game.pos() == (game.server()["x"], game.server()["y"])


def test_walls_stop_you_and_turn_you(game):
    game.stamp(1, 0, ["M"])                               # a rock right in front
    x0, y0 = game.pos()
    game.hold(["d"], 400)
    game.sleep(300)
    assert game.pos() == (x0, y0)                         # blocked: you stay
    assert game.js("ents.get('agent' + myId).fx") == 1    # but you now face it


@pytest.mark.realtime
def test_higher_ground_is_drawn_higher_and_clicks_find_it(game):
    # a terrace three layers up just north of you: drawn three blocks higher (relief.js, RELIEF_STEP art px a layer), you on it too
    game.clear_area(30)                                        # (the land round you the meadow: a ridge another test left 15 to 20 tiles north of you (hd_sky) was drawn where the click landed)
    game.stamp(-2, -4, ["....."] * 3, levels=["33333"] * 3)
    x, y = game.pos()
    z, L = game.js("zoom"), game.js("RELIEF_STEP")
    assert game.js(f"liftAt({x}, {y - 3})") == 3 * L * z and game.js(f"liftAt({x}, {y})") == 0
    # a click on where the terrace's tile is drawn finds that tile, not the one under it on the screen
    # (where the picture has that tile's middle, three layers up: the HD camera's place of it, view.js. It was where the classic flat picture
    #  would have drawn it, screenOrigin and Curve.y: a point of the sky in this picture, which the classic maths, asked last, answered for)
    mx, my = game.js(f"HdLook.screenOf({x} + .5, {y} - 2 + .5, 3)")
    at = game.js(f"tileAtScreen({mx}, {my})")
    assert at and (at["x"], at["y"]) == (x, y - 2) and abs(at["fy"] - .5) < .1, at       # (fy: how far down the tile)
    px = game.js(f"[...HdLook.read(Math.round({mx} * devicePixelRatio), Math.round(96 * devicePixelRatio), 1, 1).data]")
    assert px[2] > px[1] > px[0] and game.js(f"tileAtScreen({mx}, 96)") is None, px      # ...and a point of the sky over it is no tile
    game.js(f"ents.get('agent' + myId).y = {y - 3}")             # someone up there is lifted with it
    assert game.js("liftOf(ents.get('agent' + myId))") == 3 * L * z


def test_moved_far_just_as_you_stop_walking_you_are_drawn_where_the_world_has_you(game):
    """Let go of a walk and be moved far away at once (a teleport; waking again after a death): the page kept you where
    you stopped, for good, and walked you from there, the world's tiles under you twenty tiles off. Letting go leaves
    a guess of the tile you stop on (walk.js pred) until the world is there; the world's ticks tell of what is round the
    screen only, so where you stopped it never was again, and the guess, never dropped, kept the page from taking the
    place the world gave (agent.js refresh)."""
    x, y = game.pos()
    game.page.keyboard.down("d")
    game.wait("walking !== null && ents.get('agent' + myId).walking")
    game.sleep(150)
    # (the key let go and the world moving you, in one go: the next tick already has you far from here)
    game.js("""([x, y]) => { window.dispatchEvent(new KeyboardEvent('keyup', {key: 'd', code: 'KeyD'})); rpc('dev_teleport', {x, y}); return 1; }""", [x + 200, y + 200])
    game.page.keyboard.up("d")
    s = game.server()
    assert (s["x"], s["y"]) == (x + 200, y + 200), s
    game.wait(f"(() => {{ const p = myPos(); return p.x === {x + 200} && p.y === {y + 200}; }})()", 8000)
    game.arrive()
    assert game.pos() == (x + 200, y + 200)


def test_drawing_a_body_at_work_does_not_turn_it_back(game):
    """The way a body faces had nine writers, three of them in its drawing: while an action went on, each frame drawn
    turned you back to it, whatever a key had turned you to since (and the keys act on the way you face). Chopping a
    tree south of you, turned east (the turn key's own function): you stay turned east, frame after frame. One writer
    (body_place.js face), called by what turns a body; the picture reads."""
    game.clear_area(6)
    game.stamp(0, 1, ["T"])
    game.face(0, 1)
    game.page.keyboard.down("q")
    game.wait("myAction && myAction.tool === 'dig' && ents.get('agent' + myId).fy === 1", 4000)
    game.js("turn('E')")
    game.frames(4)
    faced = game.js("(() => { const p = ents.get('agent' + myId); return [p.fx, p.fy, !!myAction]; })()")
    game.page.keyboard.up("q")
    assert faced == [1, 0, True], faced
    assert not game.errors, game.errors
