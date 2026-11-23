"""The jump, frame by frame ("make the jumping animation smoother and better"; "the Space jump should be as high as 1
block and more"): a hop a block and more high, a step's jump as high over the step, the body never leaping a px more
than its speed from a frame to the next, no pose flashing, a staircase at one beat (jump.js)."""

import pytest
from test_e2e_jump import ORDER, drawn_over, step_east

pytestmark = pytest.mark.e2e


# every frame drawn: [ms, your x, your body's height over the line the eye follows (art px, as drawn), its pose, in the air]
BODY = """() => { window.__bd = []; window.__bdOn = true; const f = () => { const p = ents.get('agent' + myId), now = performance.now(), j = p && jumping(p, now);
  if (p) __bd.push([now, +p.x.toFixed(3), j ? Math.round(j.body) : 0, j && j.pose || '', !!(j && j.tuck)]); if (__bdOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def body_over(game, act):
    game.rest()
    game.js(BODY)
    act()
    rec = game.js("(() => { __bdOn = false; return __bd; })()")
    game.rest()
    return rec


def smooth(rec):
    """No jump of the body from a frame to the next: at most 3.5 art px in a 60th of a second (a jump's speed as it
    leaves the ground and lands), a px on a quicker frame; no pose shown and gone back from (a flash)."""
    for a, b in zip(rec, rec[1:]):
        assert abs(b[2] - a[2]) <= max(1, -(-3.5 * (b[0] - a[0]) // 16.67)), (a, b)
    runs = [r[3] for r, q in zip(rec, [None] + rec) if q is None or r[3] != q[3]]
    assert not [i for i in range(1, len(runs) - 1) if runs[i - 1] == runs[i + 1] and runs[i]], runs


@pytest.mark.realtime
def test_the_hop_goes_a_block_up_and_comes_down_smoothly(game):
    """"The Space jump should be as high as 1 block and more ... right now it looks like a weird 1/10th block
    animation": the hop on the level went 6 art px up in 0.28 s. Now its top is over a block (16 art px), it is in
    the air 0.35 to 0.5 s, its height changes a little each frame (a thrown thing's), the poses one after the other."""
    game.clear_area(6)
    rec = body_over(game, lambda: (game.press("Space", 0), game.sleep(800)))
    air = [r for r in rec if r[4]]
    k = game.js("Math.cos(HdLook.cam.pitch * Math.PI / 180)")              # (a height as the eye sees it, as the land's levels: leap.js)
    assert air and max(r[2] for r in rec) >= 18 * k, (max(r[2] for r in rec), k)
    assert 350 <= air[-1][0] - air[0][0] <= 500, air[-1][0] - air[0][0]
    smooth(rec)
    seen = [r[3] for r, q in zip(rec, [None] + rec) if r[3] and (q is None or r[3] != q[3])]
    assert seen[0] in ("crouch", "takeoff") and seen[-1] == "settle" and [ORDER.index(a) for a in seen] == sorted(ORDER.index(a) for a in seen), seen
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_auto_jump_up_a_staircase_is_smooth_and_keeps_its_rhythm(game):
    """Four steps up, walking: every step a jump as high (its top 4 art px over the step it lands on), the body never
    jumping a px more than its speed, no pose flashing, and a jump every step at the same beat (it was the same beat,
    but each 4 px up the screen in a frame and down 3 a frame in the top's pose)."""
    game.clear_area(8)
    game.stamp(2, -2, ["." * 10] * 5, levels=["1234444444"] * 5)
    x, _ = game.pos()
    rec = body_over(game, lambda: game.hold(["d"], 2000))
    assert game.server()["z"] == 4, game.server()
    smooth(rec)
    offs = [r[0] for r, q in zip(rec, [None] + rec) if r[3] == "takeoff" and (q is None or q[3] != "takeoff")]
    assert len(offs) == 4, offs
    beats = [b - a for a, b in zip(offs, offs[1:])]
    assert max(beats) - min(beats) <= 45 and min(beats) >= 250, beats       # (about the time a jump a layer up is in the air: leap.js)
    tops = [max(r[2] for r in rec if a <= r[0] < a + 300) for a in offs]
    assert min(tops) >= 8, tops                                             # (over the line the eye follows: 20 over the floor it left, the line 8 up half way)
    assert not game.errors, game.errors


# every frame, each creature near you: [ms, id, x, y, the level it is drawn at, its body over that (art px, as drawn)]
MOBS = """() => { window.__mb = []; window.__mbOn = true; const f = () => { const now = performance.now();
  for (const q of ents.values()) if (q.e && q.e.kind === 'chicken') { const z = HdLook.drawnAt(q), j = jumping(q, now); if (z !== null) __mb.push([now, q.e.id, q.x, q.y, z, j ? Math.round(j.body) : 0]); }
  if (__mbOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_a_creature_hops_up_and_down_a_step_without_a_teleport(game):
    """"JUMPING for player and mobs is bad and looks like a teleportation": the HD look put another body at the level
    of the server (a level up as its step began) or of the tile it was nearest, its arc over that: up a step a hen went
    a level up at once. Now a hen penned on two tiles, one a step up, goes up and down it on the line between them: its
    drawn height never moves more than a few art px from a frame to the next."""
    game.clear_area(8)
    game.stamp(-2, 2, ["." * 4] * 3, levels=["9999", "9019", "9999"])
    game.rpc("dev_creatures", clear=12, kind="chicken", dx=-1, dy=3)
    game.js(MOBS)
    game.wait("__mb.some((r) => r[4] > 0 && r[4] < 1) && __mb.some((r) => r[4] === 1) && __mb.some((r) => r[4] === 0)", 40000)   # (between the two, on each)
    game.sleep(1500)
    rec = game.js("(() => { __mbOn = false; return __mb; })()")
    h = [(r[0], r[4] * 16 + r[5]) for r in rec]
    assert max(v for _, v in h) - min(v for _, v in h) >= 16, h[:5]                    # (it went up the step)
    for (t0, a), (t1, b) in zip(h, h[1:]):
        assert abs(b - a) <= max(2, -(-4 * (t1 - t0) // 16.67)), ((t0, a), (t1, b))
    assert not game.errors, game.errors


LIT = """() => { window.__lt = []; window.__ltOn = true; const f = () => { const p = ents.get('agent' + myId), j = p && jumping(p, performance.now());
  __lt.push([!!j, HdLook.youLit]); if (__ltOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_your_lantern_stays_lit_up_and_down_steps_at_night(game):
    """"The player has a light around him, when going up and down this light disappears the time of the up/down
    animation": between two levels the tile's top was over the drawn body, the lantern cut to a window there was none of."""
    game.clear_area(8)
    game.stamp(2, -2, ["." * 10] * 5, levels=["1234444444"] * 5)
    game.hour(.9); game.rest()
    game.js(LIT)
    game.hold(["d"], 2000); game.hold(["a"], 2000)
    rec = game.js("(() => { __ltOn = false; return __lt; })()")
    assert any(j for j, _ in rec), "no step jumped"
    assert all(l is not False for _, l in rec), [i for i, (_, l) in enumerate(rec) if l is False][:20]
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
    assert game.server()["z"] == 1 and len(r) > 10, game.server()
    moves = [b[2] - a[2] for a, b in zip(r, r[1:]) if abs(b[2] - a[2]) > .01]
    assert len(moves) >= 4 and all(abs(v - round(v)) < .02 and v > 0 for v in moves), [(i, round(v, 3)) for i, v in enumerate(moves) if not (abs(v - round(v)) < .02 and v > 0)]
    assert not game.errors, game.errors


# every frame: [your body's height over the ground as drawn (art px), its pose, in a fall (in the air)]
FALLREC = """() => { window.__fr = []; window.__frOn = true; const f = () => { const p = ents.get('agent' + myId), now = performance.now(), j = jumping(p, now), fl = falling(p, now);
  __fr.push([j ? Math.round(j.body) : 0, j && j.pose || '', !!(fl && fl.air)]); if (__frOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_jump_pressed_falling_into_a_hole_does_not_play_its_hop_once_down(game):
    """"when i jump above a hole it glitches the player animation": walked off the edge of a hole three deep, Space
    pressed on the way down. The fall is drawn first (it is what the body does); its hop on the spot waited under it and
    played what was left of its arc once you were down: the body all but down, then 18 px up in a frame ("apex") and down
    again. A hop asked for in the air is no hop: once down, the body stays down (a heavy landing's bounce aside)."""
    game.clear_area(8)
    x, y = game.pos()
    game.rpc("dev_col", tiles=[[x + 1, y + j] for j in range(-2, 3)], col=[-3])
    game.rest()
    game.js(FALLREC)
    game.page.keyboard.down("d")
    game.wait("(() => { const f = falling(ents.get('agent' + myId), performance.now()); return !!(f && f.air); })()", 4000)
    game.page.keyboard.press("Space")
    game.page.keyboard.up("d")
    game.sleep(900)
    r = game.js("(() => { __frOn = false; return __fr; })()")
    down = max(i for i, v in enumerate(r) if v[2]) + 1                                 # (the first frame on the ground again)
    after = r[down:]
    assert after and max(v[0] for v in after) <= 3 and not {v[1] for v in after} & {"takeoff", "rise", "apex", "fall"}, r[down - 3:down + 12]
    assert game.server()["z"] == -3, game.server()
    assert not game.errors, game.errors


# every frame: [in the air (leap.js), drawn swimming, your body's top on the screen (art px), its height as drawn, your name's lift (art px)]
AIR = """() => { window.__ar = []; window.__arOn = true; const f = () => { const p = ents.get('agent' + myId), now = performance.now(), j = jumping(p, now), a = HdLook.art(), b = a && a.body;
  __ar.push([Leap.on(), swimsAt(p, p.e), b ? Math.round(b.y / a.u) : null, j ? Math.round(j.body) : 0, -Math.round(overBody(p, TS())[1] / zoom)]); if (__arOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
@pytest.mark.parametrize("over", ["hole", "water"])
def test_sprint_jumping_over_a_wide_hole_or_water_the_body_flies_the_arc(game, over):
    """"jumping above a biiiig hole still creates the exact same error as jumping above the water": "only the nametag
    jumps, and ... I get teleported into it". Over water you were drawn swimming under the arc (swim.js swimsAt: the tile
    under you); over a hole four deep a fall began under the arc (jump.js fallOf) and the name went with it; come down by
    the hole's far wall, the walk went on into the wall, drawn as a step four up (an arc, 20 px up and down). Sprinting
    off the edge with Space, over a hole 5 wide and 4 deep or water 3 wide: the body flies the arc and comes down where it
    ends (in the hole; on the far bank), never drawn swimming in the air, never more than 8 art px from a frame to the next."""
    game.clear_area(12)
    x, y = game.pos()
    if over == "hole":
        game.rpc("dev_col", tiles=[[x + t, y + k] for t in range(3, 8) for k in range(-2, 3)], col=[-4])
    else:
        game.stamp(3, -2, ["~~~"] * 5)
    game.rest()
    game.js(AIR)
    game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
    game.wait(f"ents.get('agent' + myId).x >= {x + 1.6}", 4000)
    game.page.keyboard.press("Space")
    game.wait("Leap.on()", 2000)
    game.wait("!Leap.on()", 4000)
    game.page.keyboard.up("d"); game.page.keyboard.up("Shift")
    game.sleep(700)
    r = game.js("(() => { __arOn = false; return __ar; })()")
    assert any(v[0] for v in r) and not [v for v in r if v[0] and v[1]], [v for v in r if v[0] and v[1]][:4]       # (in the air: never swimming)
    ys = [v[2] for v in r if v[2] is not None]
    jolts = [(i, a, b) for i, (a, b) in enumerate(zip(ys, ys[1:])) if abs(b - a) > 8]
    assert not jolts, jolts[:4]
    assert game.server()["z"] == (-4 if over == "hole" else 0), game.server()
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_space_while_swimming_moves_neither_the_body_nor_its_name(game):
    """"jumping IN water ... only the nametag jumps": Space while swimming hopped (jump.js hopOf), the name with it, while the
    body was drawn swimming. Swimming there is nothing to push off: no hop, the body and its name where they are."""
    game.clear_area(8)
    game.stamp(-2, -2, ["=" * 5] * 5)
    game.rest()
    game.wait("swimsAt(ents.get('agent' + myId), ents.get('agent' + myId).e)", 4000)
    game.js(AIR)
    game.page.keyboard.press("Space")
    game.sleep(700)
    r = game.js("(() => { __arOn = false; return __ar; })()")
    assert all(v[1] for v in r) and max(abs(v[3]) for v in r) == 0 and max(abs(v[4]) for v in r) == 0, r[:12]
    assert not game.errors, game.errors
