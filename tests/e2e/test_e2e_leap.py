"""Jumping and stairs, frame by frame ("JUMPING for player and mobs is bad and looks like a teleportation"; "sprinting
+ jumping should preserve velocity ... just like minecraft"; at doben00's cave stairs: "sprinting down the stairs the
player glitches and at the end teleports", "drawn above the cave"). The jump key is a jump through the air
(web/js/leap.js, sim/leaping.py); a step down is a drop at the walk's pace; the world agrees at every landing."""

import math

import pytest

pytestmark = pytest.mark.e2e

# every frame drawn: [ms, x, y, body over the level drawn from (art px), pose, the level drawn from, the world's x, its z, feet on the screen (art px), a fixed place of the land (art px), your level, the land's top there, the eye's pitch]
FRAMES = """([ox, oy, oz]) => { window.__fr = []; window.__frOn = true; if (!window.__frHook) { window.__frHook = true; const show = HdView.show;
  HdView.show = (...A) => { const r = show(...A); if (window.__frOn) { const p = ents.get('agent' + myId), lv = HdLook.level, a = HdLook.art(); if (p && a) {
    const now = lastT, j = jumping(p, now), b = HdLook.screenOf(p.x + .5, p.y + .5, lv[2]), o = HdLook.screenOf(window.__o[0] + .5, window.__o[1] + .5, window.__o[2]);
    __fr.push([now, p.x, p.y, j ? Math.round(j.body) : 0, j && j.pose || '', lv[2], p.e.x, p.e.z, Math.round(b[1] / a.u) - (j ? Math.round(j.body) : 0), o[1] / a.u, myAt ? myAt.z : null, topAt(Math.round(p.x), Math.round(p.y)), HdLook.cam.pitch]); } } return r; }; }
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
    assert not [r for r in rec if r[4] in ("rise", "apex")], ("no jump up off a step down", [(i, r) for i, r in enumerate(rec) if r[4] in ("rise", "apex")][:6], game.js("[autoJump(), sprinting()]"))
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
    # (over three frames, a twentieth of a second: one frame of a landing went 0.132 of a tile in 16.6 ms, 7.96 tiles a
    # second against 8, one run in six: the body put back on its way as it comes down, not a speed that is lost)
    for a, b in zip(run, run[3:]):
        v = (b[1] - a[1]) / max(b[0] - a[0], 1) * 1000
        assert v >= 8, ("slowed", round(v, 1), a[:5], b[:5])
    assert "crouch" not in {r[4] for r in rec} and "rise" in {r[4] for r in rec}
    smooth(rec)
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_up_a_stair_under_a_roof_with_the_jump_key_never_on_the_land_over_it(game):
    """Up a stair cut under the land, three cells high, the jump key pressed at every step (as the HD stair test
    does): no jump through the air there (no room for its top), so you are never taken for on the land over the
    stair, never put back where the world has you (nothing moves more than its speed in a frame), and the world
    ends where you are. (It jumped into the roof: your level read as the land's top for a dozen frames, the eye tilted
    up and back, and once you were put back 8 tiles.)"""
    game.clear_area(10)
    x, y = game.pos()
    for i in range(1, 7):
        game.rpc("dev_col", tiles=[[x + i, y]], col=[-i, -i + 3, 0])
    game.rest()
    game.rpc("dev_teleport", x=x + 6, y=y, z=-6); game.arrive(); game.face(-1, 0)

    def go():
        game.page.keyboard.down("a")
        for _ in range(80):
            if game.js(f"myPos().x <= {x}"):
                break
            game.page.keyboard.press("Space")
            game.page.wait_for_timeout(100)
        game.page.keyboard.up("a")
    rec = frames(game, go, z0=-6)
    assert game.pos()[0] <= x and game.server()["z"] == 0, (game.pos(), game.server())
    under = [r for r in rec if r[11] > r[10] + 2]                      # (land over you)
    assert under and all(r[10] < 0 for r in under), [r[:2] + r[10:] for r in under if r[10] >= 0][:4]
    smooth(rec, 5)
    agree(game)
    assert not game.errors, game.errors


# every frame: [the eye's pitch, how open the x-ray window is, your x, your y]
VIEW = """() => { window.__vw = []; window.__vwOn = true; const f = () => { const p = ents.get('agent' + myId);
  if (p) __vw.push([HdLook.cam.pitch, HdLook.win.a, p.x, p.y]); if (__vwOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
@pytest.mark.parametrize("way", ["S", "N", "E", "W"])
def test_sprint_jumping_up_a_hill_under_the_open_sky_keeps_the_open_view(game, way):
    """"when sprinting and jumping south blocks up (hills) the blocks cause the camera to trigger the underground
    angle": in the air the view took your level as the ground under you, the step ahead higher than it (in front of
    the eye, going south): under the land. Up five steps of a hill, three tiles each, sprinting (each a jump through
    the air), any way: the eye keeps the open sky's pitch and the x-ray never opens."""
    # (the meadow all round the way, out past its end: past ten tiles the world's own hills beside the strip shut you in
    #  (hd_level.js steep: land a level over you in ten ways of sixteen), and the eye tilted as it should, one run in six)
    game.clear_area(30)
    dx, dy = {"S": (0, 1), "N": (0, -1), "E": (1, 0), "W": (-1, 0)}[way]
    n, w = 28, 5                                                              # (tiles along the way, across it)
    lv = ["0" if t < 2 else str(min(5, (t + 1) // 3)) for t in range(n)]     # (five steps up, three tiles each, then the top)
    if dx:
        rows = ["".join(lv if dx > 0 else lv[::-1])] * w
        game.stamp(1 if dx > 0 else -n, -2, ["." * n] * w, levels=rows)
    else:
        rows = [c * w for c in (lv if dy > 0 else lv[::-1])]
        game.stamp(-2, 1 if dy > 0 else -n, ["." * w] * n, levels=rows)
    game.rest()
    pitch = game.js("HdLook.cam.pitch")
    game.js(VIEW)
    key = {"S": "s", "N": "w", "E": "d", "W": "a"}[way]
    game.hold(["Shift", key], 2400)
    game.rest()
    rec = game.js("(() => { __vwOn = false; return __vw; })()")
    assert game.server()["z"] == 5, game.server()
    assert max(abs(r[0] - pitch) for r in rec) < .5, (pitch, [r for r in rec if abs(r[0] - pitch) >= .5][:4])
    assert max(r[1] for r in rec) == 0, [r for r in rec if r[1] > 0][:4]
    assert not game.errors, game.errors



def test_on_the_lower_step_behind_a_higher_one_your_legs_are_behind_it(game):
    """"on stone steps ... it looks like I am above the border but I am under": standing on a step just north of one a
    level higher, the higher step is between the eye and your legs: they are hidden by it (its edge at your waist),
    not drawn over it one px in two (HdLook.hid 0: the picture's pass of you behind land is not made). Behind land
    higher than that, a wall a level and more over the eye's line to your feet: you still show through it."""
    game.clear_area(8)
    game.stamp(-4, -4, ["." * 9] * 9, levels=["1" * 9] * 4 + ["2" * 9] * 5)
    x, y = game.pos()
    game.rpc("dev_teleport", x=x, y=y - 1, z=1); game.arrive(); game.face(0, 1); game.rest()
    game.frames(3)
    assert game.js("HdLook.hid") == 0
    game.stamp(-4, 1, ["." * 9] * 4, levels=["4" * 9] * 4)                      # (a wall three levels up just south of you)
    game.frames(3)
    assert game.js("HdLook.hid") == 1
    assert not game.errors, game.errors


# every frame: [your y, the way you face (y), in the air]
FACE = """() => { window.__fc = []; window.__fcOn = true; const f = () => { const p = ents.get('agent' + myId); __fc.push([p.y, p.fy, Leap.on()]); if (__fcOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_sprint_jumping_down_off_a_high_step_you_go_on_south_never_put_back(game):
    """"sprinting [down the north mountain] my character ends up getting into the floor and glitching, facing the north
    direction": off a step 9 high a sprint jump came down 9 lower and the walk went on; the world, making the flight
    first, ended that walk where the landing hurt (sim/movement.py walk), a tile behind; the page was put back on it,
    turned north by the step back. Sprinting south off the edge with Space: never facing north, never a step back, and
    the world has you where the screen does."""
    game.clear_area(12)
    game.stamp(-2, 0, ["." * 5] * 10, levels=["99999"] * 2 + ["00000"] * 8)
    x, y = game.pos()
    game.rpc("dev_teleport", x=x, y=y, z=9); game.arrive(); game.face(0, 1); game.rest()
    game.js(FACE)
    game.page.keyboard.down("Shift"); game.page.keyboard.down("s")
    game.wait(f"ents.get('agent' + myId).y >= {y + .8}", 4000)
    game.page.keyboard.press("Space")
    game.wait("Leap.on()", 2000)
    game.wait("!Leap.on()", 4000)
    game.sleep(700)
    game.page.keyboard.up("s"); game.page.keyboard.up("Shift")
    game.sleep(500)
    r = game.js("(() => { __fcOn = false; return __fc; })()")
    assert not [i for i, v in enumerate(r) if v[1] == -1], [v for v in r if v[1] == -1][:4]
    assert not [(a[0], b[0]) for a, b in zip(r, r[1:]) if b[0] < a[0] - .05], [(a[0], b[0]) for a, b in zip(r, r[1:]) if b[0] < a[0] - .05][:4]
    game.wait("myPos().x === meObs.self.x && myPos().y === meObs.self.y", 4000)
    agree(game)
    assert game.pos()[1] >= y + 5 and not game.errors, (game.pos(), y, game.errors)
