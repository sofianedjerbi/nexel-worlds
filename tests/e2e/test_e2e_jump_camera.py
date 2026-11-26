"""The eye and the land through a jump (test_e2e_jump.py has the jump itself): up a step the eye's level is yours on
every frame, the land goes by whole art px one way, your feet stay put on the screen, the pitch and the x-ray window do
not stir back and forth."""

import math
import pytest
from test_e2e_jump import step_east, walk_up

pytestmark = pytest.mark.e2e


# every frame: [your x, the eye's level, yours on the line between the two tiles, how much you are lifted, the eye's pitch, how open the window is,
# a fixed tile of the land on the screen (y, art px), your feet on the screen (y, art px, no arc)]
CAM = """([ox, oy]) => { window.__cam = []; window.__camOn = true; const f = () => { const p = ents.get('agent' + myId), lv = HdLook.level, a = HdLook.art();
  if (p && a && lv[1] !== null) { const o = HdLook.screenOf(ox + .5, oy + .5, 0), b = HdLook.screenOf(p.x + .5, p.y + .5, lv[2] + lv[3]);
    __cam.push([p.x, lv[1], lv[2], lv[3], HdLook.cam.pitch, HdLook.win.a, o[1] / a.u, b[1] / a.u, performance.now()]); } if (__camOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def camera_over(game, keys, ms):
    x, y = game.pos()
    game.rest()
    # (and the eye's tilt done: by a terrace three up the eye tips down to the pitch from above over 400 ms; recorded half
    #  way, the pitch went on up to 58 and then down again off the step, "back and forth", one run in eight on a busy machine)
    game.wait("Math.abs(HdLook.cam.pitch - HdLook.cam.want) < .01", 3000)
    game.js(CAM, [x, y])
    if keys:
        walk_up(game, keys)
    else:
        game.press("Space", 0)
        game.sleep(ms)
    game.sleep(300)
    rec = game.js("(() => { __camOn = false; return __cam; })()")
    game.rest()
    return x, rec


@pytest.mark.realtime
def test_the_camera_follows_the_ground_through_a_hop_and_a_step_jump(game):
    """"When jumping the camera goes crazy": the eye's level went after yours eased over 100 ms, so up a step it was a third of
    a level behind as you landed and the land slid on 200 ms after (your body went 5 art px up the screen and back); half way
    over by a cliff's foot your lift was the next tile's, half a level in one frame. Now: a hop moves nothing but your body; up a
    step the eye's level is yours, frame for frame, the land moves one way and stops when you land, your feet stay put on the
    screen, the pitch and the window do not stir."""
    _, hop = camera_over(game, None, 400)
    assert len(hop) > 5 and len({round(r[6], 2) for r in hop}) == 1 and len({r[4] for r in hop}) == 1, hop[:3]   # (the land and the pitch stand still)
    step_east(game)
    x, rec = camera_over(game, ["d"], 0)
    assert game.server()["z"] == 1 and len(rec) > 5, game.server()
    assert all(abs(r[1] - r[2]) < .01 for r in rec), [r[:4] for r in rec if abs(r[1] - r[2]) >= .01]             # the eye's level: yours (no lag, no drift after)
    land = [r[6] for r in rec]
    d = [b - a for a, b in zip(land, land[1:]) if abs(b - a) > .01]
    assert d and all(v > 0 for v in d), d                                               # the land goes down the screen, one way
    after = [r[6] for r in rec if r[8] > rec[-1][8] - 130]                             # (the last 130 ms: eight frames of 1/60 s, two of a runner's)
    assert max(after) - min(after) < .01, after                                         # and stands still once the eye has come to you
    # (your feet on the screen: up a step now a jump through the air, the eye coming up after you a px a frame: leap.js cam)
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_a_step_jump_by_a_cliffs_foot_keeps_the_camera_and_the_window_steady(game):
    """A terrace three up just south of you, a step east along its foot: the eye's level is yours on every frame, the pitch
    and the x-ray window change one way at the most (never back and forth), your feet stay put on the screen."""
    step_east(game)
    game.stamp(-6, 3, ["." * 16] * 3, levels=["3" * 16] * 3)
    game.stamp(-6, 1, ["." * 8] * 2, levels=["3" * 8] * 2)
    x, rec = camera_over(game, ["d"], 0)
    assert game.server()["z"] == 1 and len(rec) > 5, game.server()
    assert all(abs(r[1] - r[2]) < .01 for r in rec), [r[:4] for r in rec if abs(r[1] - r[2]) >= .01]
    for k in (4, 5):                                                                    # the pitch, the window
        d = [b[k] - a[k] for a, b in zip(rec, rec[1:]) if abs(b[k] - a[k]) > 1e-3]
        assert all(a * b > 0 for a, b in zip(d, d[1:])), (k, [round(r[k], 3) for r in rec])
    feet = [r[7] for r in rec if r[4] == rec[0][4]]                                    # (while the pitch is as it was: the tilt after, back to the open sky's pitch once on the step, moves them as a pitch does)
    assert max(feet) - min(feet) <= 1.5, feet
    assert not game.errors, game.errors


# after each frame drawn: [ms, your x, the drawn y of a fixed place of the land by you (art px), your feet's (art px, rounded as the sprite is)]
DRAWN = """([ox, oy, oz]) => { window.__px = []; window.__pxOn = true; if (!window.__pxHook) { window.__pxHook = true; const show = HdView.show;
  HdView.show = (...A) => { const r = show(...A); if (window.__pxOn) { const p = ents.get('agent' + myId), lv = HdLook.level, a = HdLook.art(); if (p && a) {
    const o = HdLook.screenOf(ox + .5, oy + .5, oz), b = HdLook.screenOf(p.x + .5, p.y + .5, lv[2]); __px.push([lastT, p.x, o[1] / a.u, Math.round(b[1] / a.u)]); } } return r; }; } return 1; }"""


def drawn_over(game, act):
    x, y = game.pos()
    game.rest()
    game.js(DRAWN, [x, y, game.server()["z"]])
    act()
    game.sleep(300)
    rec = game.js("(() => { __pxOn = false; return __px; })()")
    game.rest()
    return x, rec


@pytest.mark.realtime
def test_the_land_moves_by_whole_art_px_never_back_and_your_feet_stay_put(game):
    """"It is still jumping vertically by a few pixels": the eye's place was rounded to 1/16 tile and 1/16 level, so up a step
    the land went 1.6 px a frame, drawn 1 or 2 px on, and your body (rounded to a px as every sprite) a px up and down (3 screen
    px on a phone) at every step. Now: walking flat and hopping the land does not move up or down at all; up a step it goes
    whole art px, one way, a px a frame at the most (on a frame of 1/60 s); your feet keep their px."""
    _, flat = drawn_over(game, lambda: game.hold(["d"], 500))
    _, hop = drawn_over(game, lambda: (game.press("Space", 0), game.sleep(600)))
    for r in (flat, hop):                                         # (the hop's time, not a count of frames: on a runner drawing every 117 ms it was 5)
        assert len(r) >= 3 and r[-1][0] - r[0][0] >= 400 and max(v[2] for v in r) - min(v[2] for v in r) < .01 and len({v[3] for v in r}) == 1, r[:4]   # (zero, on flat ground and through a hop)
    step_east(game)
    x, r = drawn_over(game, lambda: game.hold(["d"], 800))
    assert game.server()["z"] == 1 and len(r) > 10, game.server()
    d = [(b[2] - a[2], max(1, math.ceil((b[0] - a[0]) * .06 - .02))) for a, b in zip(r, r[1:])]   # (a px each 1/60 s: a frame of 75 ms may carry 4.5 px of it, drawn 4 or 5 whole: rounded, the cap read 4)
    moves = [v for v, _ in d if abs(v) > .01]
    # (whole art px; at least one frame that moved it. It was four: on the runners the step's few frames came 80 ms and
    # more apart, the land 3 to 5 px a frame, "[5, 3, 4]": the cap a frame, below, is by the frame's own time)
    assert moves and all(abs(v - round(v)) < .02 for v in moves), moves                          # whole art px
    assert all(v > 0 for v in moves), moves                                                      # one way
    assert all(abs(v) <= cap + .02 for v, cap in d), d                                           # a px a frame at the most
    feet = [v[3] for v in r]
    assert max(feet) - min(feet) <= 1, feet
    assert not game.errors, game.errors


@pytest.mark.realtime
@pytest.mark.parametrize("how, up", [("woken", 3), ("dropped", 3), ("dropped", 1)])
def test_off_a_pillar_the_land_still_goes_up_a_step_by_whole_px(game, how, up):
    """test_e2e_jump's camera test failed one run in eight, the land by you going 0.965 px a frame up a step, then -0.035:
    the place of the land the picture is pinned to (hd.js pin) stood a level from your feet, nearer the eye, and as the
    eye rose it went a little more than the land by you: a swim of the whole picture. It was made at the eye's level,
    which glides a px a frame after a teleport (woken on a pillar and back on the meadow), and kept through a drop (on
    the pillar, then its ground taken away: a player woken on a hill a level up, then the test's meadow laid under
    them). Up the step east after either: the land by you goes whole px, one way."""
    step_east(game)
    x, y = game.pos()
    game.stamp(0, -1, ["."], levels=[str(up)])
    game.rpc("dev_teleport", x=x, y=y - 1, z=up); game.arrive()
    if how == "woken":
        game.rpc("dev_teleport", x=x, y=y, z=0); game.arrive()
    else:
        game.stamp(0, 0, ["."], levels=["0"]); game.rest()                # (the ground under you taken away)
    _, r = drawn_over(game, lambda: game.hold(["d"], 800))
    assert game.server()["z"] == 1, game.server()
    # (whole px, one way, in every frame that moved it: there were to be four and more, and ten frames drawn; on the
    # runners the step was a few frames 80 ms and more apart, "10 > 10")
    moves = [b[2] - a[2] for a, b in zip(r, r[1:]) if abs(b[2] - a[2]) > .01]
    assert moves and all(abs(v - round(v)) < .02 and v > 0 for v in moves), [(i, round(v, 3)) for i, v in enumerate(moves) if not (abs(v - round(v)) < .02 and v > 0)]
    assert not game.errors, game.errors
