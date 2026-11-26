"""Jumping and stairs, frame by frame ("JUMPING for player and mobs is bad and looks like a teleportation"; "sprinting
+ jumping should preserve velocity ... just like minecraft"; at doben00's cave stairs: "sprinting down the stairs the
player glitches and at the end teleports", "drawn above the cave"). The jump key is a jump through the air
(web/js/leap.js, sim/leaping.py); a step down is a drop at the walk's pace; the world agrees at every landing."""

import math

import pytest

pytestmark = pytest.mark.e2e

# every frame drawn: [ms, x, y, body over the level drawn from (art px), pose, the level drawn from, the world's x, its z, feet on the screen (art px), a fixed place of the land (art px), your level, the land's top there, the eye's pitch,
#  the tile you are going to (x, y), how far ahead of the world you are (tiles: walk.js leadOf; in the air, from the tile the world has you on), which jump (the hop's start, the step's key, in the air)]
FRAMES = """([ox, oy, oz]) => { window.__fr = []; window.__frOn = true; if (!window.__frHook) { window.__frHook = true; const show = HdView.show;
  HdView.show = (...A) => { const r = show(...A); if (window.__frOn) { const p = ents.get('agent' + myId), lv = HdLook.level, a = HdLook.art(); if (p && a) {
    const now = lastT, j = jumping(p, now), b = HdLook.screenOf(p.x + .5, p.y + .5, lv[2]), o = HdLook.screenOf(window.__o[0] + .5, window.__o[1] + .5, window.__o[2]);
    __fr.push([now, p.x, p.y, j ? Math.round(j.body) : 0, j && j.pose || '', lv[2], p.e.x, p.e.z, Math.round(b[1] / a.u) - (j ? Math.round(j.body) : 0), o[1] / a.u, myAt ? myAt.z : null, topAt(Math.round(p.x), Math.round(p.y)), HdLook.cam.pitch, p.tx, p.ty, walking ? leadOf(p, now) : Math.abs(p.x - p.e.x) + Math.abs(p.y - p.e.y), (() => { const s = BodyPlace.state(p), q = jumpOf(p); return s.hop + '/' + (q ? q.key : '') + '/' + !!Leap.state; })()]); } } return r; }; }
  window.__o = [ox, oy, oz]; return 1; }"""


def frames(game, act, z0=0):
    x, y = game.pos()
    game.rest()
    game.js(FRAMES, [x, y, z0])
    act()
    game.wait("myPos().x === meObs.self.x && myPos().y === meObs.self.y && (typeof Leap === 'undefined' || !Leap.on())", 6000)
    game.rest()
    return game.js("(() => { __frOn = false; return __fr; })()")


def smooth(rec, speed=10):
    """Frame to frame: the body goes no faster than `speed` tiles a second (and a tenth of a tile for a frame's
    rounding), its height on the screen no more than 4 art px in a 60th of a second, and no pose shown for a frame
    and gone back from in the same jump (the same tile and the same jump: two jumps one after the other, the frame on
    the ground between them not drawn, were "apex, rise, apex" on the runners, a frame every 80 ms; and up a stair
    with Space pressed at each step, a hop on the tile you had just come up to, "rise, fall, rise"). -> the largest move along x in a frame, in tiles."""
    near = lambda i: "; ".join(str([round(v, 3) if isinstance(v, float) else v for v in r]) for r in rec[max(0, i - 3):i + 4])   # (the frames round it, every column: a string, not cut)
    for i, (a, b) in enumerate(zip(rec, rec[1:])):
        dt = max(b[0] - a[0], 1) / 1000
        assert abs(b[1] - a[1]) + abs(b[2] - a[2]) <= speed * dt * 1.35 + .1, "a jump along the ground: " + near(i)
        assert abs(b[8] - a[8]) <= max(2, -(-4 * dt * 1000 // 16.67)) + (4 if "takeoff" in (a[4], b[4]) else 0), "a jump on the screen: " + near(i)   # (more as it leaves the ground: a jump, as the brief has it)
    key = lambda r: (r[4], r[13], r[14], r[16])
    runs = [key(r) for r, q in zip(rec, [None] + rec) if q is None or key(r) != key(q)]
    assert not [i for i in range(1, len(runs) - 1) if runs[i - 1] == runs[i + 1] and runs[i][0]], runs


def agree(game):
    """The world has you where your screen does, to the tile and the height."""
    s = game.server()
    assert game.pos() == (s["x"], s["y"]) and game.js("myAt.z") == s["z"], (game.pos(), s, game.js("myAt"))


@pytest.mark.stepped
def test_sprinting_down_six_steps_is_smooth_and_never_put_back(game):
    """It jumped up off every step down, slowed to a jump's third of a second a step while the world sprinted down at
    a tenth: six tiles behind, it was put back on the world at once (the teleport at the foot of the stairs)."""
    game.clear_area(10)
    game.stamp(-1, -1, ["." * 12] * 3, levels=["665432100000"] * 3)
    game.rpc("dev_teleport", x=game.pos()[0], y=game.pos()[1], z=6); game.arrive(); game.face(1, 0)
    x, _ = game.pos()
    def run_down():     # (held until at the foot and on, x + 9: not for a time, which a loaded runner's game runs behind)
        for k in ("Shift", "d"):
            game.page.keyboard.down(k)
        game.wait(f"ents.get('agent' + myId).x >= {x + 9}", 6000)
        for k in ("d", "Shift"):
            game.page.keyboard.up(k)
    rec = frames(game, run_down, z0=6)
    smooth(rec)
    assert game.server()["z"] == 0 and game.pos()[0] >= x + 8, game.server()
    agree(game)
    assert not [r for r in rec if r[4] in ("rise", "apex")], ("no jump up off a step down", [(i, r) for i, r in enumerate(rec) if r[4] in ("rise", "apex")][:6], game.js("[autoJump(), sprinting()]"))
    assert not game.errors, game.errors


@pytest.mark.stepped
def test_down_a_stair_cut_into_a_hill_you_are_drawn_in_the_cut(game):
    """Down a stair cut into a hill four high, under its roof at the foot: on every frame you are drawn at the level
    of the stair you are on (between two steps, between theirs), never on the hill's top over it."""
    game.clear_area(10)
    lv = "4444444443210000"                                  # (from 6 tiles west of you: down from 3 east of you, under the roof from 6 east)
    game.stamp(-6, -2, ["." * 16] * 5, levels=["4" * 16, "4" * 16, lv, "4" * 16, "4" * 16], roofs=["0" * 16, "0" * 16, "0" * 12 + "4444", "0" * 16, "0" * 16])
    game.rpc("dev_teleport", x=game.pos()[0], y=game.pos()[1], z=4); game.arrive(); game.face(1, 0)
    x, _ = game.pos()
    for keys, ms in ((["d"], 1400), (["Shift", "a"], 800), (["Shift", "d"], 900)):
        rec = frames(game, lambda: game.hold(keys, ms), z0=4)
        for r in rec:
            k = math.cos(r[12] * math.pi / 180) * 16                           # (art px a level is drawn, as the eye sees it, that frame: the eye tilts under the roof)
            i, at = r[1] - (x - 6), r[5] + r[3] / k                            # (the level your feet are drawn at: the eye's, and your body over it)
            lo, hi = int(lv[max(0, min(15, int(i // 1)))]), int(lv[max(0, min(15, -int(-i // 1)))])
            assert min(lo, hi) - .2 <= at <= max(lo, hi) + 1.35, ("drawn off the stair", r, lo, hi, at)   # (up to a jump's top over it, never on the hill)
        smooth(rec)
        agree(game)
    assert not game.errors, game.errors


@pytest.mark.stepped
def test_a_jump_onto_a_block_is_smooth_and_agreed(game):
    """Walking into a block a layer up (auto-jump), and standing in front of one with the jump key: up on it, every
    frame smooth, no pose flashing, the world there too."""
    game.clear_area(8)
    game.stamp(2, -1, ["." * 4] * 3, levels=["1222"] * 3)
    x, _ = game.pos()
    game.face(1, 0)
    # (held until up on it: it was 500 ms, two tiles and a half at the walk's pace, and on a runner whose world came late
    # (the walk waits for it, walk.js LEAD) you were still at its foot)
    def walk_up():
        game.page.keyboard.down("d")
        game.wait("myAt && myAt.z >= 1", 5000)
        game.page.keyboard.up("d")
    rec = frames(game, walk_up)
    smooth(rec, 5)
    assert game.server()["z"] >= 1, game.server()
    agree(game)
    game.rpc("dev_teleport", x=x + 1, y=game.pos()[1], z=0); game.arrive(); game.face(1, 0); game.rest()
    rec = frames(game, lambda: (game.press("Space", 0), game.sleep(700)))
    smooth(rec, 5)
    # (the arc's top between two drawn frames is drawn at neither: up to half the longest gap from it, g/2 (gap/2)^2 art px
    # lower, about a px at a runner's 94 ms frames. The record's own gaps say how much its highest frame may miss by)
    gap = max(min(b[0] - a[0], 100) for a, b in zip(rec, rec[1:])) / 1000
    top, miss = max(r[3] for r in rec), game.js("JUMP.g * P") / 2 * (gap / 2) ** 2
    k = max(range(len(rec)), key=lambda i: rec[i][3])
    around = "; ".join(str([round(v, 3) if isinstance(v, float) else v for v in r]) for r in rec[max(0, k - 4):k + 5])   # (the frames round the top: a string, not cut)
    assert game.server()["z"] == 1 and game.pos()[0] == x + 2 and top + .5 >= 8 - miss, f"{game.server()}, top {top}, miss {miss:.2f}: {around}"
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.stepped
def test_a_sprint_jump_carries_over_a_two_tile_gap_and_lands_agreed(game):
    """Sprinting, the jump key a tile before a pit two wide: over it in the air (never down in it), down on the far
    side 3 to 5 tiles on from where you left the ground, at once where the world has you."""
    game.clear_area(10)
    game.stamp(3, -1, ["." * 2] * 3, levels=["cc"] * 3)
    x, _ = game.pos()
    game.face(1, 0)

    def go():
        # (Space pressed by the page on the frame you are there: pressed from here once it was seen, a runner's frames 100
        # to 200 ms apart, it came a frame or two late, a tile each at a sprint, and you had walked off the edge into the pit)
        game.js(f"""() => {{ const f = () => {{ const p = ents.get('agent' + myId); if (myPos().x >= {x} + 1 && p.x >= {x} + 1.2) {{
          dispatchEvent(new KeyboardEvent('keydown', {{key: ' ', code: 'Space', bubbles: true, cancelable: true}}));
          dispatchEvent(new KeyboardEvent('keyup', {{key: ' ', code: 'Space', bubbles: true, cancelable: true}})); }} else requestAnimationFrame(f); }};
          requestAnimationFrame(f); return 1; }}""")
        game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
        game.wait("Leap.on()", 4000)
        game.wait("!Leap.on()", 3000)
        game.page.keyboard.up("d"); game.page.keyboard.up("Shift")
    rec = frames(game, go)
    # (from the frame before the first drawn in the air to the one after the last, 3 tiles at the least; between those
    # two, 5.5 at the most. It was between the first and the last in the air: on the runners a frame every 120 ms, a
    # tile and more of a sprint, and the jump read 1.5 tiles)
    inair = [i for i, r in enumerate(rec) if r[4] in ("takeoff", "rise", "apex", "fall", "touch")]
    assert inair, rec[:3]
    i0, i1 = inair[0], inair[-1]
    out = rec[min(i1 + 1, len(rec) - 1)][1] - rec[max(i0 - 1, 0)][1]
    assert 3 <= out and rec[i1][1] - rec[i0][1] <= 5.5, (rec[i0][:3], rec[i1][:3], out)
    assert min(r[7] for r in rec) == 0, "the world never had you down in the pit"
    smooth(rec)
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.stepped
def test_steering_in_the_air(game):
    """A jump standing still, the way held once in the air: you drift that way and land off where you left."""
    game.clear_area(6)
    x, _ = game.pos()

    def go():
        game.page.keyboard.press("Space")
        game.wait("Leap.on()", 1000)
        game.page.keyboard.down("d")
        game.wait("!Leap.on()", 3000)
        game.page.keyboard.up("d")
    rec = frames(game, go)
    # (how far it took you: the furthest you were drawn. It was the last frame drawn in the air: a frame every 120 ms on
    # the runners, the last one early in the drift)
    air = [r for r in rec if r[4] in ("takeoff", "rise", "apex", "fall", "touch")]
    assert air and max(r[1] for r in rec) - x > .3, (air[-1][:3], max(r[1] for r in rec))
    smooth(rec, 5)
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.stepped
def test_sprinting_over_steps_up_and_down_keeps_its_speed(game):
    """"the whole jump physics are ruined when going on block above / below. it stops the velocity and does an
    up-block animation": sprinting over a run of steps up and down, you jump up each through the air and drop off each
    without slowing (never under 80% of a sprint, a frame at a time), with the jump's own poses (no step's crouch),
    the world where you end."""
    game.clear_area(12)
    game.stamp(-1, -1, ["." * 22] * 3, levels=["0001111000110000111000"] * 3)
    x, _ = game.pos()
    game.face(1, 0)
    # (the keys held until you are past the course's end, x + 19, not for a time: a loaded runner's game runs behind its
    # clock, and keys let go at 1.9 s of it stopped you on the course, read as speed lost)
    def run_over():
        for k in ("Shift", "d"):
            game.page.keyboard.down(k)
        game.wait(f"ents.get('agent' + myId).x >= {x + 19}", 8000)
        for k in ("d", "Shift"):
            game.page.keyboard.up(k)
    rec = frames(game, run_over)
    run = [r for r in rec if x + 1 <= r[1] <= x + 18]
    # (over three frames, a twentieth of a second: one frame of a landing went 0.132 of a tile in 16.6 ms, 7.96 tiles a
    # second against 8, one run in six: the body put back on its way as it comes down, not a speed that is lost. Where
    # the world was late and you were LEAD[0] tiles ahead of it, the walk waits for it, as it should (walk.js LEAD): a
    # runner's server, a tick late, had you at 4.4 tiles a second there. Those frames say the machine, not the jump)
    lead = game.js("LEAD[0]")
    ahead = lambda r: r[15] > lead
    # (by the game's time: a frame moves you by its time up to 0.1 s, render.js; a runner's 105 ms frames read 7.9)
    game_ms, t = {}, 0.0
    for a, b in zip([None] + rec, rec):
        t += min(b[0] - a[0], 100) if a else 0
        game_ms[id(b)] = t
    # (over 300 ms of game time at least, a jump up and its landing: a lost velocity is a stop, most of that; three frames
    # of a runner's, 216 ms with a landing in them, read 7.8 for a few hundredths of a tile)
    for i, a in enumerate(run):
        j = next((j for j in range(i + 3, len(run)) if game_ms[id(run[j])] - game_ms[id(a)] >= 300), None)
        if j is None or any(ahead(r) for r in run[i:j + 1]):
            continue
        b = run[j]
        v = (b[1] - a[1]) / (game_ms[id(b)] - game_ms[id(a)]) * 1000
        assert v >= 8, ("slowed", round(v, 1), game.js("Leap.landed"), [(round(game_ms[id(r)]), round(r[1], 2), r[4], round(r[15], 2), r[16]) for r in run[max(0, i - 2):j + 3]])
    assert "crouch" not in {r[4] for r in rec} and "rise" in {r[4] for r in rec}
    smooth(rec)
    agree(game)
    assert not game.errors, game.errors
