"""Moving: walking and sprinting speeds, taps, turning with two keys held, and the screen agreeing with the server."""

import pytest


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
        return sum(abs(b[1] - a[1]) + abs(b[2] - a[2]) for a, b in zip(rec, rec[1:])) / ((rec[-1][0] - rec[0][0]) / 1000)

    corner = turns("ds")
    game.sleep(600)
    assert game.pos() == (game.server()["x"], game.server()["y"])
    back = turns("da")
    game.sleep(600)
    assert game.pos() == (game.server()["x"], game.server()["y"])
    assert corner > 7.5 and back > 6.5, (corner, back)        # (sprinting is 10 a second; it was 5.4 and 3)


def stops(rec, ms=60):
    """The pauses (ms) in a recorded walk, its ends left out."""
    mid = [r for r in rec if rec[0][0] + 400 < r[0] < rec[-1][0] - 400]
    out, i0 = [], 0
    for i in range(1, len(mid)):
        if abs(mid[i][1] - mid[i0][1]) + abs(mid[i][2] - mid[i0][2]) > 1e-6:
            if mid[i][0] - mid[i0][0] > ms:
                out.append(round(mid[i][0] - mid[i0][0]))
            i0 = i
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
    dist = sum(abs(b[1] - a[1]) + abs(b[2] - a[2]) for a, b in zip(rec, rec[1:]))
    game.sleep(900)
    assert not stops(rec), stops(rec)
    assert dist > 17, dist                                    # (2.1 s sprinting: 21 tiles at full speed)
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
    game.page.keyboard.down("w")                                # one tile, a jump up (Space: walking into it stops you), along the ledge, then the wall
    game.sleep(100); game.page.keyboard.press("Space"); game.sleep(1000)
    game.page.keyboard.up("w")
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
    game.page.keyboard.down("d")                                # and a jump back up the same edge (Space)
    game.sleep(100); game.page.keyboard.press("Space"); game.sleep(600)
    game.page.keyboard.up("d")
    game.sleep(500)
    s = game.server()
    assert s["x"] > low and s["x"] >= x - 2 and game.js(f"levelAt({s['x']}, {s['y']})") == 1 and game.pos() == (s["x"], s["y"])


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


def test_a_hop_is_one_arc_over_the_edge_at_the_pace_of_a_step(game):
    """Up or down a layer: a crouch on the ground it leaves, one arc from there to the ground it lands on, clear of the
    edge, a landing; your shadow on the ground under you, and as long as a jump that high takes (now a block and more:
    "the Space jump should be as high as 1 block and more", the walk waiting for it: a third of a second, not a fifth). (Seen frame by frame it hung:
    the step took half as long again, the body near the top of its arc for most of it, legs going; and it ended with
    a 2 px snap. Then "Jump looks unnatural": it left the ground the instant the step began, stiff.)"""
    game.clear_area(6)
    game.stamp(1, -1, ["..."] * 3, levels=["111"] * 3); game.rest()        # ground a layer up, east of you
    x, y = game.pos()
    L = game.js("RELIEF_STEP")                                # (art px a layer: a block)
    # your feet and your shadow over the lower ground (art px; the solver says levels), f of the way across, going east (up) or west (down)
    at = lambda f, to: game.js(f"""(() => {{ const j = jumpOf({{x: {x} + {f}, y: {y}, tx: {to}, ty: {y}, fx: {1 if to > x else -1}, fy: 0}});
      return {{feet: (j.body + {f}) * {L}, shadow: (j.ground + {f}) * {L}, squash: j.squash}}; }})()""")
    for to in (x + 1, x):
        way = [at(f / 50, to) for f in range(1, 50)]
        off, land = (way[0], way[-1]) if to > x else (way[-1], way[0])
        up = to > x
        assert abs(off["feet"] - (0 if up else L)) < 1e-6 and off["squash"] == up and abs(land["feet"] - (L if up else 0)) < 1.5   # on the ground as it sets off (up: crouched); a px or so from it as it lands (the landing's squash: after it, by the clock)
        assert max(abs(b["feet"] - a["feet"]) for a, b in zip(way, way[1:])) < L / 8          # one smooth arc: no snap anywhere
        assert all(abs(q["shadow"]) < 1e-6 for q in way[:24]) and all(abs(q["shadow"] - L) < 1e-6 for q in way[25:])
        assert all(q["feet"] >= L - (1e-6 if up else 2) for q in way[24:])                         # over the higher ground: never inside it (down: under two px)
        if up:
            assert max(q["feet"] for q in way) > L + 1                                      # clear of the edge
        else:                                                                               # down: no jump, a drop off the edge
            assert max(q["feet"] for q in way) <= L + 1e-6 and all(b["feet"] >= a["feet"] - 1e-6 for a, b in zip(way, way[1:]))
    assert game.js(f"jumpOf({{x: {x} - .5, y: {y}, tx: {x} - 1, ty: {y}, fx: -1, fy: 0}})") is None   # on the level: no hop
    game.start_recording()                                    # and it takes the time of a step: up the step (Space as you set off) and on, at walking pace
    game.page.keyboard.down("d"); game.page.keyboard.press("Space")
    game.hold(["d"], 700)
    rec = game.recording()
    game.sleep(500)
    gone = rec[-1][1] - rec[0][1]
    assert gone > 2.5, gone                                   # (5 tiles a second for 0.7 s, the step a third of a second: its jump's time, jump.js jumpMs)
    assert game.pos() == (game.server()["x"], game.server()["y"])


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
