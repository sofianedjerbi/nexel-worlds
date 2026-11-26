"""Jumping and the view: under a roof, up a hill under the open sky, behind a higher step, down off a high one
(web/js/leap.js: the eye, cam, level). The jump itself: test_e2e_leap.py."""

import pytest

from test_e2e_leap import agree, frames, smooth

pytestmark = pytest.mark.e2e


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
    # (the last step's answer may still be on its way when the key comes up: one run in six the world was asked
    # while it had you a tile back, z -1. Wait for the page to have no step in flight, then ask.)
    game.wait("!pred && !walking && !Leap.on()")
    assert game.pos()[0] <= x and game.server()["z"] == 0, (game.pos(), game.server(), game.js("({myAt, pred, srv})"))
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
    # (sprinted until on the hill's top: it was 2400 ms, and a runner whose world came late had you a step short, z 4)
    for k in ("Shift", key):
        game.page.keyboard.down(k)
    game.wait("myAt && myAt.z >= 5", 8000)
    for k in (key, "Shift"):
        game.page.keyboard.up(k)
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


# (slow: every frame made 95 ms long by a busy wait, as on a loaded runner. Either way, what the page told the world,
# with where you were (y, its tile, x, its tile, in the air, your height, the keys held) and what it said)
SLOW = """(slow) => { const raf = requestAnimationFrame; window.__slow = slow; window.__told = [];
  const spin = () => { const t = performance.now(); while (performance.now() - t < 95); if (__slow) raf(spin); }; if (slow) raf(spin);
  const f = window.rpc, me = () => { const p = ents.get("agent" + myId); return p && [+p.y.toFixed(2), p.ty, +p.x.toFixed(3), p.tx, Leap.on(), myAt && myAt.z, [...keys].join("")]; };
  window.rpc = (op, extra) => { const e = op === "act" && extra && ["walk", "stop", "jump", "leap"].includes(extra.tool) && [extra.tool, JSON.stringify(extra.args), me()];
    if (e) __told.push(e); return f(op, extra).then((r) => { if (e) e.push(r && (r.ok === false ? r.error : r.result && r.result.z)); return r; }); }; return 1; }"""


@pytest.mark.realtime
@pytest.mark.parametrize("slow", [False, True])
def test_sprint_jumping_down_off_a_high_step_you_go_on_south_never_put_back(game, slow):
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
    game.js(SLOW, slow)
    game.page.keyboard.down("Shift"); game.page.keyboard.down("s")
    game.wait(f"ents.get('agent' + myId).y >= {y + .8}", 4000)
    game.page.keyboard.press("Space")
    game.wait("Leap.on()", 2000)
    game.wait("!Leap.on()", 4000)
    game.sleep(700)
    game.page.keyboard.up("s"); game.page.keyboard.up("Shift")
    game.sleep(500)
    r = game.js("(() => { __fcOn = false; return __fc; })()")
    game.js("__slow = false")
    print("frames", r, "told", game.js("__told"), "world", game.server())         # (shown when it fails)
    assert not [i for i, v in enumerate(r) if v[1] == -1], [v for v in r if v[1] == -1][:4]
    assert not [(a[0], b[0]) for a, b in zip(r, r[1:]) if b[0] < a[0] - .05], [(a[0], b[0]) for a, b in zip(r, r[1:]) if b[0] < a[0] - .05][:4]
    game.wait("myPos().x === meObs.self.x && myPos().y === meObs.self.y", 4000)
    agree(game)
    assert game.pos()[1] >= y + 5 and not game.errors, (game.pos(), y, game.errors)
