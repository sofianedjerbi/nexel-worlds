"""Jumping and stairs, frame by frame ("JUMPING for player and mobs is bad and looks like a teleportation"; "sprinting
+ jumping should preserve velocity ... just like minecraft"; at doben00's cave stairs: "sprinting down the stairs the
player glitches and at the end teleports", "drawn above the cave"). The jump key is a jump through the air
(web/js/leap.js, sim/leaping.py); a step down is a drop at the walk's pace; the world agrees at every landing."""

import pytest

pytestmark = pytest.mark.e2e

# every frame drawn: [ms, x, y, body over the level drawn from (art px), pose, the level drawn from, the world's x, its z, feet on the screen (art px), a fixed place of the land (art px)]
FRAMES = """([ox, oy, oz]) => { window.__fr = []; window.__frOn = true; if (!window.__frHook) { window.__frHook = true; const show = HdView.show;
  HdView.show = (...A) => { const r = show(...A); if (window.__frOn) { const p = ents.get('agent' + myId), lv = HdLook.level, a = HdLook.art(); if (p && a) {
    const now = lastT, j = jumping(p, now), b = HdLook.screenOf(p.x + .5, p.y + .5, lv[2]), o = HdLook.screenOf(window.__o[0] + .5, window.__o[1] + .5, window.__o[2]);
    __fr.push([now, p.x, p.y, j ? Math.round(j.body) : 0, j && j.pose || '', lv[2], p.e.x, p.e.z, Math.round(b[1] / a.u) - (j ? Math.round(j.body) : 0), o[1] / a.u]); } } return r; }; }
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
    and gone back from. -> the largest move along x in a frame, in tiles."""
    for a, b in zip(rec, rec[1:]):
        dt = max(b[0] - a[0], 1) / 1000
        assert abs(b[1] - a[1]) + abs(b[2] - a[2]) <= speed * dt * 1.35 + .1, ("a jump along the ground", a, b)
        assert abs(b[8] - a[8]) <= max(2, -(-4 * dt * 1000 // 16.67)) + (4 if "takeoff" in (a[4], b[4]) else 0), ("a jump on the screen", a, b)   # (more as it leaves the ground: a jump, as the brief has it)
    runs = [r[4] for r, q in zip(rec, [None] + rec) if q is None or r[4] != q[4]]
    assert not [i for i in range(1, len(runs) - 1) if runs[i - 1] == runs[i + 1] and runs[i]], runs


def agree(game):
    """The world has you where your screen does, to the tile and the height."""
    s = game.server()
    assert game.pos() == (s["x"], s["y"]) and game.js("myAt.z") == s["z"], (game.pos(), s, game.js("myAt"))


@pytest.mark.realtime
def test_sprinting_down_six_steps_is_smooth_and_never_put_back(game):
    """It jumped up off every step down, slowed to a jump's third of a second a step while the world sprinted down at
    a tenth: six tiles behind, it was put back on the world at once (the teleport at the foot of the stairs)."""
    game.clear_area(10)
    game.stamp(-1, -1, ["." * 12] * 3, levels=["665432100000"] * 3)
    game.rpc("dev_teleport", x=game.pos()[0], y=game.pos()[1], z=6); game.arrive(); game.face(1, 0)
    x, _ = game.pos()
    rec = frames(game, lambda: game.hold(["Shift", "d"], 1300), z0=6)
    smooth(rec)
    assert game.server()["z"] == 0 and game.pos()[0] >= x + 8, game.server()
    agree(game)
    assert not [r for r in rec if r[4] in ("rise", "apex")], "no jump up off a step down"
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_down_a_stair_cut_into_a_hill_you_are_drawn_in_the_cut(game):
    """Down a stair cut into a hill four high, under its roof at the foot: on every frame you are drawn at the level
    of the stair you are on (between two steps, between theirs), never on the hill's top over it."""
    game.clear_area(10)
    lv = "4444444443210000"                                  # (from 6 tiles west of you: down from 3 east of you, under the roof from 6 east)
    game.stamp(-6, -2, ["." * 16] * 5, levels=["4" * 16, "4" * 16, lv, "4" * 16, "4" * 16], roofs=["0" * 16, "0" * 16, "0" * 12 + "4444", "0" * 16, "0" * 16])
    game.rpc("dev_teleport", x=game.pos()[0], y=game.pos()[1], z=4); game.arrive(); game.face(1, 0)
    x, _ = game.pos()
    k = game.js("Math.cos(HdLook.cam.pitch * Math.PI / 180)") * 16              # (art px a level is drawn, as the eye sees it)
    for keys, ms in ((["d"], 1400), (["Shift", "a"], 800), (["Shift", "d"], 900)):
        rec = frames(game, lambda: game.hold(keys, ms), z0=4)
        for r in rec:
            i, at = r[1] - (x - 6), r[5] + r[3] / k                            # (the level your feet are drawn at: the eye's, and your body over it)
            lo, hi = int(lv[max(0, min(15, int(i // 1)))]), int(lv[max(0, min(15, -int(-i // 1)))])
            assert min(lo, hi) - .2 <= at <= max(lo, hi) + 1.35, ("drawn off the stair", r, lo, hi, at)   # (up to a jump's top over it, never on the hill)
        smooth(rec)
        agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_a_jump_onto_a_block_is_smooth_and_agreed(game):
    """Walking into a block a layer up (auto-jump), and standing in front of one with the jump key: up on it, every
    frame smooth, no pose flashing, the world there too."""
    game.clear_area(8)
    game.stamp(2, -1, ["." * 4] * 3, levels=["1222"] * 3)
    x, _ = game.pos()
    game.face(1, 0)
    rec = frames(game, lambda: game.hold(["d"], 500))
    smooth(rec, 5)
    assert game.server()["z"] >= 1, game.server()
    agree(game)
    game.rpc("dev_teleport", x=x + 1, y=game.pos()[1], z=0); game.arrive(); game.face(1, 0); game.rest()
    rec = frames(game, lambda: (game.press("Space", 0), game.sleep(700)))
    smooth(rec, 5)
    assert game.server()["z"] == 1 and game.pos()[0] == x + 2 and max(r[3] for r in rec) >= 8, (game.server(), max(r[3] for r in rec))
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_a_sprint_jump_carries_over_a_two_tile_gap_and_lands_agreed(game):
    """Sprinting, the jump key a tile before a pit two wide: over it in the air (never down in it), down on the far
    side 3 to 5 tiles on from where you left the ground, at once where the world has you."""
    game.clear_area(10)
    game.stamp(3, -1, ["." * 2] * 3, levels=["cc"] * 3)
    x, _ = game.pos()
    game.face(1, 0)

    def go():
        game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
        game.wait(f"myPos().x >= {x} + 1 && ents.get('agent' + myId).x >= {x} + 1.6", 3000)
        game.page.keyboard.press("Space")
        game.wait("Leap.on()", 1000)
        game.wait("!Leap.on()", 3000)
        game.page.keyboard.up("d"); game.page.keyboard.up("Shift")
    rec = frames(game, go)
    air = [r for r in rec if r[4] in ("takeoff", "rise", "apex", "fall", "touch")]
    assert air and 3 <= air[-1][1] - air[0][1] <= 5.5, (air[0][:3], air[-1][:3])
    assert min(r[7] for r in rec) == 0, "the world never had you down in the pit"
    smooth(rec)
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
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
    air = [r for r in rec if r[4] in ("takeoff", "rise", "apex", "fall", "touch")]
    assert air and air[-1][1] - x > .3, air[-1][:3]
    smooth(rec, 5)
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_sprinting_over_steps_up_and_down_keeps_its_speed(game):
    """"the whole jump physics are ruined when going on block above / below. it stops the velocity and does an
    up-block animation": sprinting over a run of steps up and down, you jump up each through the air and drop off each
    without slowing (never under 80% of a sprint, a frame at a time), with the jump's own poses (no step's crouch),
    the world where you end."""
    game.clear_area(12)
    game.stamp(-1, -1, ["." * 22] * 3, levels=["0001111000110000111000"] * 3)
    x, _ = game.pos()
    game.face(1, 0)
    rec = frames(game, lambda: game.hold(["Shift", "d"], 1900))
    run = [r for r in rec if x + 1 <= r[1] <= x + 18]
    for a, b in zip(run, run[1:]):
        v = (b[1] - a[1]) / max(b[0] - a[0], 1) * 1000
        assert v >= 8, ("slowed", round(v, 1), a[:5], b[:5])
    assert "crouch" not in {r[4] for r in rec} and "rise" in {r[4] for r in rec}
    smooth(rec)
    agree(game)
    assert not game.errors, game.errors
