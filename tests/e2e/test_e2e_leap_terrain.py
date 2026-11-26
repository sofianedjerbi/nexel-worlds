"""Jumping over the land as it is: up a step and a flight of them, up a hill with the jump key, off a high ledge (web/js/
leap.js: stairArc, hits, dropDue; the eye, cam). The jump itself: test_e2e_leap.py."""

import json

import pytest

from test_e2e_leap import agree, frames

pytestmark = pytest.mark.e2e


@pytest.mark.realtime
@pytest.mark.parametrize("run", [False, True])
def test_a_jump_that_comes_down_against_a_step_goes_on_up_it(game, run):
    """"when sprinting + jumping the player is getting hit by the block AFTER jumping and it loses all his velocity"
    ("even when not sprinting"): the jump key pressed too far before a step comes down against its edge. With
    auto-jump you go on up it at once at the speed you had: never back along the way (you were put back to the
    tile's middle, then walked on from a standstill), up on it, the world there too."""
    game.clear_area(14)
    game.stamp(6, -1, ["." * 9] * 3, levels=["111111111"] * 3)
    x, _ = game.pos()
    game.face(1, 0)
    game.rest()
    keys = ["Shift", "d"] if run else ["d"]

    def act():
        for k in keys:
            game.page.keyboard.down(k)
        game.wait(f"ents.get('agent' + myId).x >= {x + (2.2 if run else 4.0)}", 3000)   # (a jump that comes down short of the step's top)
        game.page.keyboard.press("Space")
        # (on until up on the step and past its edge: it was 900 ms, and a runner whose world came late (the walk waits
        # for it, walk.js LEAD) let go of you on the edge, x + 6)
        game.wait(f"myAt && myAt.z === 1 && myPos().x > {x + 6}", 5000)
        for k in reversed(keys):
            game.page.keyboard.up(k)
    # (every landing and what it decided, leap.js land: past, bump, can, up, to, room; shown whole, as JSON, when you
    #  are sent back: which of them sends you to the tile's middle, #162)
    game.js("""() => { window.__lands = []; let last = null; const f = () => { const l = Leap.landed;
      if (l && l !== last) { last = l; __lands.push({...l, t: Math.round(lastT)}); } if (window.__lands) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }""")
    rec = frames(game, act)
    back = [(a[:5], b[:5]) for a, b in zip(rec, rec[1:]) if b[1] < a[1] - 1e-3]
    assert not back, json.dumps([back, game.js("__lands")])
    assert game.server()["z"] == 1 and game.server()["x"] > x + 6, (game.server(), x)
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
@pytest.mark.parametrize("run", [False, True])
def test_up_a_flight_of_steps_every_jump_clears_the_next_edge(game, run):
    """"when climbing (walking stairs up) it is bad because i hit the block above when automatically jumping": up eight
    steps a layer each, a tile deep, walking or running, the auto-jump's arcs (leap.js stairArc) never meet a step's face
    (the whole jump came down past the next edge: pinned against it six frames a step, 40 frames in all, 2.2 s up a
    flight that takes 1.6), you get to the top, and the world agrees. (Not "in under 2 s": what was pinned, `__hit`, is
    counted; the time is the machine's too, the walk waiting for a world that comes late: 3.9 s on a runner, no pin)"""
    game.clear_area(12)
    x, y = game.pos()
    for i in range(1, 12):
        game.rpc("dev_col", tiles=[[x + i, y]], col=[min(i, 8)])           # (and the top, three tiles of it: a run goes on a little after you let go)
    game.rest()
    game.face(1, 0)
    game.js("""() => { window.__hit = 0; if (!window.__hitHook) { window.__hitHook = true; const f = Leap.frame;
      Leap.frame = (p, dt, now) => { const a = Leap.state && {...Leap.state}; f(p, dt, now); const b = Leap.state;
        if (a && b && a.vx > 0 && b.x <= a.x + 1e-4) __hit++; }; } return 1; }""")
    keys = ["Shift", "d"] if run else ["d"]
    for k in keys:
        game.page.keyboard.down(k)
    game.wait(f"myPos().x >= {x + 8}", 10000)
    for k in reversed(keys):
        game.page.keyboard.up(k)
    game.rest()
    assert game.js("__hit") == 0, game.js("__hit")
    assert game.server()["z"] >= 8, game.server()
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
@pytest.mark.parametrize("how", ["jump", "walk", "tunnel"])
def test_off_a_high_ledge_the_fall_is_smooth_on_the_screen(game, how):
    """"weird issues when jumping from high heights": off a ledge six high, running with the jump key or walking off it,
    you come down as a thrown thing does, and on the screen no frame moves your feet or the land by more than 6 art px
    (walking off, the eye was put on the ground under the edge at once, the body 13 px up the screen a frame, then 26
    back; after a jump the eye came down a px a frame, the land scrolling a second after you were down). The world agrees."""
    game.clear_area(14)
    x, y = game.pos()
    top = [[x + i, y + j] for i in range(-3, 1) for j in (-1, 0, 1)]
    if how == "tunnel":                                                 # (walking off it in a tunnel, a roof two over your head: the old fall, the body 32 px down the screen in a frame)
        game.rpc("dev_col", tiles=top, col=[6, 9, 12]); game.rpc("dev_col", tiles=[[x + i, y + j] for i in range(1, 8) for j in (-1, 0, 1)], col=[0, 9, 12])
    else:
        game.rpc("dev_col", tiles=top, col=[6])
    game.rpc("dev_teleport", x=x - 2, y=y, z=6); game.arrive(); game.face(1, 0); game.rest()
    game.js("setOpt('shake', 0)")                                       # (six levels hurt: the hurt's shake is not the jump's)

    def act():
        game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
        if how == "jump":
            game.wait(f"myPos().x >= {x - .3}", 3000); game.page.keyboard.press("Space")
        # (till down on the ground under the ledge, and its landing's squash and settle drawn: 1 s held was a runner's few frames, #47)
        game.wait("!!myAt && myAt.z === 0 && !Leap.on() && !Leap.gliding()", 8000)
        game.frames(6)
        game.page.keyboard.up("d"); game.page.keyboard.up("Shift")
    try:
        rec = frames(game, act, z0=0)
    finally:
        game.js("setOpt('shake', 1)")
    air = ("takeoff", "rise", "apex", "fall", "touch", "land", "settle")   # (and the landing's squash and settle: the body's own drawing)
    # (6 art px in a frame of 1/60 s: by the frame's own time on a slower machine, the runners' 120 ms frames the land
    # following your fall 12 px a frame, as fast as it should)
    cap = lambda a, b: 6 * max(1, (b[0] - a[0]) / 16.67)
    jolts = [(a[:10], b[:10]) for a, b in zip(rec, rec[1:]) if abs(b[9] - a[9]) > cap(a, b) or (abs(b[8] - a[8]) > cap(a, b) and not {a[4], b[4]} & set(air))]   # (the land never; your feet on the ground never: in the air they go as fast as you fall, 7 px a frame at the end of six levels)
    assert not jolts, [(round(a[0]), a[4], round(a[5], 2), round(b[5], 2), a[8], b[8], round(a[9], 1), round(b[9], 1)) for a, b in jolts[:5]]
    # (the world come down too: since #257 the keys go up when the page has landed, and a runner's world was a tick behind, z 1)
    game.wait("!walking && !pred && (() => { const p = ents.get('agent' + myId); return !!p && p.e.z === 0 && p.e.x === Math.round(p.x) && p.e.y === Math.round(p.y); })()", 8000)
    assert game.server()["z"] == 0, game.server()
    agree(game)
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_walking_off_a_high_ledge_into_water_the_jump_s_fall_takes_you_down(game):
    """Off a ledge six high into a pond: the jump's own fall (leap.js ledge), the world with you. It was left to the old
    fall, which drew nothing (the body 60 px down the screen in a frame), and the world waited at the edge a second for
    a jump the screen never made."""
    game.clear_area(14)
    x, y = game.pos()
    game.rpc("dev_col", tiles=[[x + i, y + j] for i in range(-3, 1) for j in (-1, 0, 1)], col=[6])
    game.stamp(1, -1, ["~~~~~"] * 3)
    game.rpc("dev_teleport", x=x - 2, y=y, z=6); game.arrive(); game.face(1, 0); game.rest()
    game.js("setOpt('shake', 0)")
    try:
        # (__lp: how long the jump's fall drew you, ms. It counted frames, more than 10: on the runners a frame is 70 to
        # 130 ms, and a fall of six layers four of them)
        game.js("(() => { window.__lp = 0; let t = null; const f = (n) => { if (Leap.on()) { if (t !== null) __lp += n - t; t = n; } if (myAt.z > 5.5 || Leap.on()) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()")
        game.page.keyboard.down("d"); game.wait("myAt.z < .5", 4000); t = game.js("performance.now()")
        game.page.keyboard.up("d")
        game.wait("meObs.self.z < .5", 1500)                                # (the world down too, soon after)
        assert game.js("performance.now()") - t < 1500 and game.js("__lp") > 160, game.js("__lp")
    finally:
        game.js("setOpt('shake', 1)")
    game.rest()
    agree(game)
    assert game.server()["swimming"] and not game.errors, game.errors


@pytest.mark.realtime
@pytest.mark.parametrize("prof", ["hill", "stairs"])
def test_running_uphill_with_the_jump_key_never_meets_a_step_s_face(game, prof):
    """"sprinting uphill still do the same issue as before": running up a hill of uneven steps (or a flight a tile deep)
    with the jump key pressed all the way, every jump is played ahead before it leaves (leap.js hits) and goes no faster
    than comes down before the next rise or over it: never held against a step's face (18 frames up the hill, 15 up
    the flight), and the world agrees at the top."""
    game.clear_area(14)
    x, y = game.pos()
    prof = [0, 1, 1, 2, 2, 2, 3, 4, 4, 5, 5, 6, 7, 7, 7] if prof == "hill" else [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 13]
    prof += [prof[-1]] * 10          # (a top as long as a jump goes: the last one, the keys let go of in the air, comes down on it, not off its end)
    for i, h in enumerate(prof[1:], 1):
        game.rpc("dev_col", tiles=[[x + i, y - 1], [x + i, y], [x + i, y + 1]], col=[h])
    game.rest(); game.face(1, 0)
    game.js("""() => { window.__hit = 0; if (!window.__hitHook) { window.__hitHook = true; const f = Leap.frame;
      Leap.frame = (p, dt, now) => { const a = Leap.state && {...Leap.state}; f(p, dt, now); const b = Leap.state;
        if (a && b && Math.abs(a.vx) + Math.abs(a.vy) > 0 && Math.abs(b.x - a.x) + Math.abs(b.y - a.y) < 1e-4) __hit++; }; } return 1; }""")
    game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
    # (Space whenever you are on the ground, a frame looked at a time: it was pressed every 80 ms of the machine's, for 6 s at the most, #47)
    for _ in range(600):
        if game.js(f"myPos().x >= {x + 13}"):
            break
        if not game.js("Leap.on()"):
            game.page.keyboard.press("Space")
        game.frames(1)
    game.page.keyboard.up("d"); game.page.keyboard.up("Shift")
    game.rest()
    assert game.js("__hit") == 0, game.js("__hit")
    assert game.server()["z"] == prof[-1], (game.server(), prof[-1])
    agree(game)
    assert not game.errors, game.errors
