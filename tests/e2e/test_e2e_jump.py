"""The jump ("player size should be 2 blocks, so 2 blocks to destroy needed; also add a key to jump"; then "Jump looks
unnatural. Add automatic jump by default"): walking into a step jumps you up it (auto-jump, a setting); with it off
walking into a step stops you and the jump key (Space) hops you up it, on a phone its button; the way out of the ground
shows it on a step. The jump is a crouch, an arc that clears the step, a landing."""

import pytest
from test_e2e_touch import touch_game

pytestmark = pytest.mark.e2e


def step_east(game):
    """The meadow, a terrace a layer up from two tiles east of you."""
    game.clear_area(6)
    game.stamp(2, -2, ["." * 10] * 5, levels=["1" * 10] * 5)


AUTO = "(v) => { setOpt('autojump', v); return opt('autojump'); }"


def walk_up(game, keys, z=1):
    """Keys held until you are up on the step (`z`), then let go. (They were held a time, 800 ms: a runner whose world
    came late, the walk waiting for it (walk.js LEAD), was still at its foot.)"""
    for k in keys:
        game.page.keyboard.down(k)
    game.wait(f"myAt && myAt.z === {z}", 5000)
    for k in reversed(keys):
        game.page.keyboard.up(k)


@pytest.mark.quick
def test_auto_jump_is_on_by_default_and_walking_into_a_step_jumps_up_it(game):
    """No key: held east, you go up the step and on, never stopping; the world has you where the screen does."""
    step_east(game)
    x, y = game.pos()
    assert game.js("OPT_DEFAULT.autojump === true && opt('autojump') === true")
    assert game.js("MENU_PAGES.find((pg) => pg[0] === 'Keys')[1].filter((r) => r.name === 'Auto-jump' && r.kind === 'toggle').length") == 1   # (a setting on the Keys page)
    game.start_recording()
    # (held east until three tiles on, up the step at x + 2: on the screen, then let go. It was held 900 ms, three tiles at
    # the walk's pace with the step's jump: a runner a tick or two behind came two tiles on, "(9, 1, (9, 8))")
    game.page.keyboard.down("d")
    game.wait(f"myPos().x >= {x + 3}", 5000)
    game.page.keyboard.up("d")
    rec = game.recording()
    game.rest()
    # (and the world come to the tile you stop on: let go, the page has you on it at once (walk.js pred), the world a tick
    #  or two on. Read before that, it was a tile behind on a busy machine: "(4, 1, (5, 22))". Not there in 3 s: the assert says so)
    game.settle("pred === null", timeout=3000)
    s = game.server()
    assert s["x"] >= x + 3 and s["z"] == 1 and game.pos()[0] == s["x"], (s["x"], s["z"], game.pos(), game.js("[pred, trail.slice()]"))
    xs = [r[1] for r in rec if r[1] < x + 2.5]                # (up to past the step: never back, never a stop)
    assert all(b >= a - 1e-6 for a, b in zip(xs, xs[1:])), xs
    assert not game.errors, game.errors


@pytest.mark.quick
def test_walking_into_a_step_stops_you_and_the_jump_key_climbs_it(game):
    """Auto-jump off (the settings' Keys page): the step stops you and Space climbs it."""
    step_east(game)
    x, y = game.pos()
    assert game.js(AUTO, False) is False
    try:
        walk_into_a_step_then_jump(game, x, y)
    finally:
        game.js(AUTO, True)


def walk_into_a_step_then_jump(game, x, y):
    game.hold(["d"], 700)                                     # three tiles' worth of walking east
    game.rest()
    assert game.pos() == (x + 1, y) and game.server()["x"] == x + 1 and game.server()["z"] == 0     # stopped at the step
    game.frames(2)
    assert "Jump" in game.actions() and "Space" in game.js("$('actions').innerText")   # the corner: Space Jump
    game.page.keyboard.down("d")                             # walking into it, Space: up it, and on
    game.press("Space", 0)
    game.sleep(300)
    game.page.keyboard.up("d")
    game.rest()
    s = game.server()
    assert s["x"] >= x + 2 and s["z"] == 1 and game.pos()[0] == s["x"], (s["x"], s["z"], game.pos())
    game.rpc("dev_teleport", x=x + 1, y=y, z=0)              # standing, facing it: Space alone
    game.arrive()
    game.face(1, 0)
    game.press("Space", 0)
    game.wait(f"meObs.self.x === {x + 2} && meObs.self.z === 1", 4000)
    game.rpc("dev_teleport", x=x - 2, y=y, z=0)              # on the level: a hop where you stand, nothing more
    game.arrive()
    game.press("Space", 0)
    hop = game.js("(() => { const p = ents.get('agent' + myId); return [Leap.on() || performance.now() - p.settle < 400, myPos().x]; })()")
    assert hop == [True, x - 2]                               # (a jump through the air where you stand: leap.js)
    assert not game.errors, game.errors


ORDER = ["crouch", "takeoff", "rise", "apex", "fall", "touch", "land", "settle"]
ARC = """() => { window.__arc = []; window.__arcOn = true; const f = (now) => { const p = ents.get('agent' + myId), j = p && jumping(p, now);
  if (j) __arc.push([+p.x.toFixed(3), +j.body.toFixed(2), j.squash, j.pose]); if (__arcOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_the_jump_is_a_crouch_an_arc_over_the_step_and_a_landing(game):
    """Frame by frame up a step, walking (auto-jump): a jump through the air at the walk's speed (leap.js: "it stops
    the velocity and does an up-block animation"): the body rises and falls over the level the eye follows, the
    poses one after the other, a landing, never slower than the walk. (It left the ground at once, stiff; then it was a
    step's own hop, the walk slowed to a third of a second for it.)"""
    step_east(game)
    x, y = game.pos()
    game.js(ARC)
    walk_up(game, ["d"])
    game.sleep(300)
    rec = game.js("(() => { __arcOn = false; return __arc; })()")
    game.rest()
    assert game.server()["z"] == 1
    # (in the air, a good way up: up, a top, down, three frames at the least. It was five: on the runners a frame is 70
    # to 130 ms, a third of a second's jump four of them)
    air = [body for px, body, sq, pose in rec if pose in ("takeoff", "rise", "apex", "fall", "touch")]
    assert air and max(air) > 6, air                                    # (off the ground, a good way up)
    # (its shape, up, a top and down, where three frames of it were drawn: on a runner drawing every 117 ms a third of a
    # second's jump is two, "[12.34, 11.34]"; the arc itself, off jumpOf at 50 points, is test_a_hop_is_one_arc's)
    if len(air) >= 3:
        top = air.index(max(air))
        assert 0 < top < len(air) - 1 and air[-1] < max(air), air
    poses = [pose for px, _, _, pose in rec]
    seen = [a for a, b in zip(poses, [None] + poses) if a != b and a]          # each pose once, in the order shown
    # (its first pose the takeoff, or the rise where the takeoff fell between two frames; never the step's crouch)
    assert seen[0] in ("takeoff", "rise") and "apex" in seen and seen[-1] in ("touch", "land", "settle") and "crouch" not in seen, seen
    assert [ORDER.index(a) for a in seen] == sorted(ORDER.index(a) for a in seen), seen      # (never back to a pose it has left)
    assert not game.errors, game.errors


POSES = """() => { const c = document.createElement('canvas'); c.width = 384; c.height = 192; const g = c.getContext('2d', {willReadFrequently: true});
  g.drawImage(IMG.character, 0, ANIM.jump * 48, 384, 192, 0, 0, 384, 192); const d = g.getImageData(0, 0, 384, 192).data;
  const i0 = document.createElement('canvas'); i0.width = 48; i0.height = 192; const h = i0.getContext('2d', {willReadFrequently: true});
  h.drawImage(IMG.character, 0, 0, 48, 192, 0, 0, 48, 192); const s = h.getImageData(0, 0, 48, 192).data;
  const cols = new Set(); for (let i = 0; i < s.length; i += 4) if (s[i + 3]) cols.add(s[i] + ',' + s[i + 1] + ',' + s[i + 2]);
  const out = []; for (let r = 0; r < 4; r++) { const row = []; for (let c = 0; c < 8; c++) { let top = 99, bot = -1, n = 0, alien = 0, half = 0;
    for (let y = 0; y < 48; y++) for (let x = 0; x < 48; x++) { const i = (((r * 48 + y) * 384) + c * 48 + x) * 4; if (!d[i + 3]) continue;
      top = Math.min(top, y); bot = Math.max(bot, y); n++; if (d[i + 3] !== 255) half++; if (!cols.has(d[i] + ',' + d[i + 1] + ',' + d[i + 2])) alien++; }
    row.push([bot - top + 1, bot, alien, half]); } out.push(row); } return [IMG.character.height, out]; }"""


def test_the_jump_has_a_pose_drawn_for_each_part_in_every_facing(game):
    """The jump's own rows (jump_art.js), made from the standing frame by whole rows: the crouch a row shorter, the push
    off a row taller, the landing two shorter, every pose standing on the same row as the cat; no colour the cat has
    not, nothing half seen (never scaled). (It was the run's stride in the air and the frame drawn a row lower.)"""
    h, rows = game.js(POSES)
    assert h == 44 * 48 and game.js("ANIM.jump") == 36 and game.js("JPOSE.settle") == 6
    for facing, row in enumerate(rows):
        stand = row[7][0]
        tall = {pose: row[i][0] - stand for i, pose in enumerate(["crouch", "takeoff", "rise", "apex", "fall", "land", "settle"])}
        assert tall == {"crouch": -1, "takeoff": 1, "rise": -1, "apex": 0, "fall": 2, "land": -2, "settle": -1}, (facing, tall)
        assert len({f[1] for f in row}) == 1 and all(f[2] == 0 and f[3] == 0 for f in row), (facing, row)
    assert not game.errors, game.errors


def test_on_a_phone_the_jump_button_shows_at_a_step_and_climbs_it(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        step_east(g)
        x, y = g.pos()
        assert g.js("$('tJump').style.display") == "none"                   # nothing to jump onto
        g.rpc("dev_teleport", x=x + 1, y=y, z=0)
        g.arrive()
        g.face(1, 0)
        g.wait("$('tJump').style.display === 'flex'", 3000)
        r = g.js("(() => { const r = $('tJump').getBoundingClientRect(), a = $('tA').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, r.bottom <= a.top, r.right <= 390]; })()")
        assert r[2] and r[3], r                                              # over the buttons, on the screen
        g.touch("touchStart", r[0], r[1])
        g.touch("touchEnd")
        g.wait(f"meObs.self.x === {x + 2} && meObs.self.z === 1", 4000)
        assert not g.errors, g.errors
    finally:
        ctx.close()


def test_on_a_phone_the_stick_walks_up_a_step_by_itself(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        step_east(g)
        x, y = g.pos()
        g.touch("touchStart", 80, 600)                                       # left thumb, pushed east, held
        for i in range(1, 6):
            g.touch("touchMove", 80 + i * 8, 600)
            g.sleep(30)
        g.wait(f"myPos().x >= {x + 3}", 4000)
        g.touch("touchEnd")
        g.wait(f"meObs.self.x === myPos().x && meObs.self.z === 1 && meObs.self.x >= {x + 3}", 4000)
        assert not g.errors, g.errors
    finally:
        ctx.close()


def test_the_way_out_shows_the_jump_key_on_its_step(game):
    """A tunnel two cells high under a hill, its east end a step up to the open land: the way out's next move is that
    step, and its key is the jump's (the corner, and the cap beside the step), not nothing."""
    game.clear_area(14)
    x, y = game.pos()
    game.stamp(-1, -1, ["." * 12] * 3, levels=["6666" + "1" * 8, "6000" + "1" * 8, "6666" + "1" * 8],
               roofs=["0" * 12, "0666" + "0" * 8, "0" * 12])
    game.rpc("dev_teleport", x=x + 2, y=y, z=0)
    game.arrive()
    game.rest()
    game.wait("WayShow.cur && !WayShow.busy && WayShow.offer() && WayShow.offer().key === 'jump'", 8000)
    game.frames(3)
    assert "Jump" in game.js("$('actions').innerText")
    cap = game.js("(() => { const e = document.getElementById('waycap'); return e && e.style.display === 'block' ? e.innerText : ''; })()")
    assert "Space" in cap, cap
    game.press("Space", 0)
    game.wait(f"meObs.self.x === {x + 3} && meObs.self.z === 1", 4000)
    assert not game.errors, game.errors


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
    # (walked until three tiles west, down off the edge: it was 900 ms, and a runner whose world came late let go of you
    # on the hill, "17 <= 15 - 3"; then the way back until up on it)
    game.page.keyboard.down("a")
    game.wait(f"myPos().x <= {x - 3}", 5000)
    game.page.keyboard.up("a")
    game.settle("pred === null", timeout=3000)
    s = game.server()
    assert s["x"] <= x - 3 and game.js(f"levelAt({s['x']}, {s['y']})") == 0 and game.pos() == (s["x"], s["y"])
    low = s["x"]
    game.page.keyboard.down("d")                                # and a jump back up the same edge (Space)
    game.sleep(100); game.page.keyboard.press("Space"); game.wait(f"myAt && myAt.z === 1 && myPos().x >= {x - 2}", 5000)
    game.page.keyboard.up("d")
    game.settle("pred === null", timeout=3000)
    s = game.server()
    assert s["x"] > low and s["x"] >= x - 2 and game.js(f"levelAt({s['x']}, {s['y']})") == 1 and game.pos() == (s["x"], s["y"])


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
    # (from the frame the body set out: the frames before it, the key on its way and drawn standing, were walked at
    # nothing. Held 700 ms from the key down, on a runner drawing every 50 ms they were a fifth of it: "3.0")
    game.wait(f"Math.abs(ents.get('agent' + myId).x - {x}) > .05", 3000)
    game.hold(["d"], 700)
    rec = game.recording()
    game.sleep(500)
    rec = rec[next(i for i, (a, b) in enumerate(zip(rec, rec[1:])) if abs(b[1] - a[1]) > 1e-6):]
    # (each tile's time, read off the frames: the hop's tile in its jump's third of a second, the next in a walk's step, each a
    # frame late at the most. A mean speed over the frames was 2.9 at 50 ms frames, the long ones and the world's lead left out,
    # where the hop's tile had taken 190 ms and the next 190: "(2.93, [(19, 2.44), (216, 3.2), (368, 3.94), (519, 4.44)...])")
    at = lambda k: next((r[0] for r in rec if r[1] >= x + k), None)
    t0, t1, t2 = rec[0][0], at(1), at(2)
    frame = max(b[0] - a[0] for a, b in zip(rec, rec[1:]) if b[0] <= (t2 or rec[-1][0]))
    trace = [(round(r[0]), round(r[1], 2)) for r in rec[:30]]
    assert t1 is not None and t2 is not None, trace
    assert t1 - t0 <= 340 + frame + 20 and t2 - t1 <= 200 + frame + 20, (t1 - t0, t2 - t1, frame, trace)                                         # (5 tiles a second, the step a third of a second, at the walk's own pace: its jump's time, jump.js jumpMs. It was 2.5 tiles in 0.7 s by the page's clock: on a runner the walk waited for the world)
    assert game.pos() == (game.server()["x"], game.server()["y"])
