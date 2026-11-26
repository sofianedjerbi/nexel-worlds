"""The jump, frame by frame ("make the jumping animation smoother and better"; "the Space jump should be as high as 1
block and more"): a hop a block and more high, a step's jump as high over the step, the body never leaping a px more
than its speed from a frame to the next, no pose flashing, a staircase at one beat (jump.js)."""

import pytest
from test_e2e_jump import ORDER, step_east

pytestmark = pytest.mark.e2e


# every frame drawn: [ms, your x, your body's height over the line the eye follows (art px, as drawn), its pose, in the air]
# (at the frame's own time, as the game draws it: it was the clock when this was called, and two calls close together
# after a slow frame, 8 ms apart on a runner, read a whole frame's move as a jolt)
BODY = """() => { window.__bd = []; window.__bdOn = true; const f = (now) => { const p = ents.get('agent' + myId), j = p && jumping(p, now);
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
    for a, b in zip(rec, rec[1:]):           # (4 px more as it leaves the ground, as test_e2e_leap's smooth: up a flight, one jump's touch to the next one's takeoff, 13 to 8 in a 60th of a second)
        assert abs(b[2] - a[2]) <= max(1, -(-3.5 * (b[0] - a[0]) // 16.67)) + (4 if "takeoff" in (a[3], b[3]) else 0), (a, b)
    # (a flash: a pose shown and gone back from, where the frames round it were short enough to show every pose (34 ms: two
    # 60ths). Up a flight each step is a jump of its own; on a frame of 83 to 117 ms one's takeoff or touch falls between two
    # frames, and its rise came straight after the last one's apex or touch: "rise, apex, rise", "rise, touch, rise")
    starts = [i for i in range(len(rec)) if i == 0 or rec[i][3] != rec[i - 1][3]] + [len(rec)]
    runs = [(rec[a][3], a, b) for a, b in zip(starts, starts[1:])]
    quick = lambda a, b: all(rec[j][0] - rec[j - 1][0] <= 34 for j in range(max(1, a), min(len(rec), b + 1)))
    assert not [k for k in range(1, len(runs) - 1) if runs[k - 1][0] == runs[k + 1][0] and runs[k][0] and quick(*runs[k][1:])], [p for p, _, _ in runs]


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
    # (in the air from the first frame drawn in it to the last: a frame short at each end at the most. And the poses
    # in their order; not "the first a crouch, the last the settle": on the runners a frame is 70 to 130 ms, longer
    # than either, and a frame drew the rise first, the landing last)
    frame = max(b[0] - a[0] for a, b in zip(rec, rec[1:]))
    assert 350 - 2 * frame <= air[-1][0] - air[0][0] <= 500, (air[-1][0] - air[0][0], frame)
    smooth(rec)
    seen = [r[3] for r, q in zip(rec, [None] + rec) if r[3] and (q is None or r[3] != q[3])]
    assert seen and [ORDER.index(a) for a in seen] == sorted(ORDER.index(a) for a in seen), seen
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_auto_jump_up_a_staircase_is_smooth_and_keeps_its_rhythm(game):
    """Four steps up, walking: every step a jump as high (its top 4 art px over the step it lands on), the body never
    jumping a px more than its speed, no pose flashing, and a jump every step at the same beat (it was the same beat,
    but each 4 px up the screen in a frame and down 3 a frame in the top's pose)."""
    game.clear_area(8)
    game.stamp(2, -2, ["." * 10] * 5, levels=["1234444444"] * 5)
    x, _ = game.pos()
    # (walked until on the top step, and a little on: it was held 2 s, and a runner whose world came late (the walk
    # waits for it, walk.js LEAD) was a step short)
    def up():
        game.page.keyboard.down("d")
        game.wait("myAt && myAt.z === 4", 8000)
        game.sleep(300)
        game.page.keyboard.up("d")
    rec = body_over(game, up)
    assert game.server()["z"] == 4, game.server()
    smooth(rec)
    # (a jump begins where the poses begin again: off the ground, or back to an earlier pose. It was the takeoff's first
    # frame: on the runners a frame is 70 to 130 ms and one takeoff of four fell between two, "[10522, 10972, 11422]")
    at = lambda r: ORDER.index(r[3]) if r[3] in ORDER else -1
    offs = [r[0] for r, q in zip(rec, [None] + rec) if at(r) >= 0 and (q is None or at(q) < 0 or at(r) < at(q))]
    assert len(offs) == 4, offs
    # (from the second step: the first is jumped from the flat ground before the flight, a whole jump; a flight is walked at a walk's
    # pace from its second step, leap.js stairArc. Counted with it, a runner drawing every 83 ms read "[517, 183, 217]")
    beats = [b - a for a, b in zip(offs[1:], offs[2:])]
    frame = sorted(b[0] - a[0] for a, b in zip(rec, rec[1:]))[len(rec) // 2]      # (a takeoff is seen on the first frame drawn in it: a frame late at the most)
    assert max(beats) - min(beats) <= max(45, 2 * frame) and min(beats) >= 180 - frame, (beats, frame, [r[:4] for r in rec if offs[0] - 50 <= r[0] <= offs[-1] + 50])       # (a step at the walk's pace, 0.2 s a tile: up a flight each jump is planned, leap.js stairArc. It was a whole jump each step, 0.25 s and more, against the next step's face)
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


# every frame: [your body's height over the ground as drawn (art px), its pose, in a fall (in the air)]
FALLREC = """() => { window.__fr = []; window.__frOn = true; const f = () => { const p = ents.get('agent' + myId), now = performance.now(), j = jumping(p, now), fl = falling(p, now);
  __fr.push([j ? Math.round(j.body) : 0, j && j.pose || '', !!(fl && fl.air) || Leap.on()]); if (__frOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""   # (in the air: a fall's, or the jump's: walking off a ledge is the jump's fall, leap.js dropDue)


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
    game.wait("(() => { const f = falling(ents.get('agent' + myId), performance.now()); return !!(f && f.air) || !!(Leap.state && Leap.state.z < -.3); })()", 4000)   # (on the way down: walked off the edge, the jump's fall)
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
AIR = """() => { window.__ar = []; window.__arOn = true; const f = (now) => { const p = ents.get('agent' + myId), j = jumping(p, now), a = HdLook.art(), b = a && a.body;
  __ar.push([Leap.on(), swimsAt(p, p.e), b ? Math.round(b.y / a.u) : null, j ? Math.round(j.body) : 0, BodyPlace.of(p).up, now]); if (__arOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


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
    game.js("setOpt('shake', 0)"); game.js(AIR)   # (a fall into the hole hurts: its shake is the hurt's, not the jump's; set back below)
    # (Space pressed by the page on the frame you are 1.2 tiles on, as test_e2e_leap's gap: pressed from here once seen,
    # on a runner's frames of 80 ms and more it came a tile late at a sprint, in the water, and no jump)
    game.js(f"""() => {{ const f = () => {{ const p = ents.get('agent' + myId); if (p.x >= {x} + 1.2) {{
      dispatchEvent(new KeyboardEvent('keydown', {{key: ' ', code: 'Space', bubbles: true, cancelable: true}}));
      dispatchEvent(new KeyboardEvent('keyup', {{key: ' ', code: 'Space', bubbles: true, cancelable: true}})); }} else requestAnimationFrame(f); }};
      requestAnimationFrame(f); return 1; }}""")
    game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
    game.wait("Leap.on()", 2000)
    game.wait("!Leap.on()", 4000)
    game.page.keyboard.up("d"); game.page.keyboard.up("Shift")
    game.sleep(700)
    r = game.js("(() => { __arOn = false; return __ar; })()")
    game.js("setOpt('shake', 1)")
    assert any(v[0] for v in r) and not [v for v in r if v[0] and v[1]], [v for v in r if v[0] and v[1]][:4]       # (in the air: never swimming)
    # (8 art px in a frame of 1/60 s; by the frame's own time on a slower one: the runners' frames of 70 to 130 ms
    # went 10 to 20 px, the arc as fast as it is)
    ys = [(v[5], v[2]) for v in r if v[2] is not None]
    jolts = [(i, a[1], b[1]) for i, (a, b) in enumerate(zip(ys, ys[1:])) if abs(b[1] - a[1]) > 8 * max(1, (b[0] - a[0]) / 16.67)]
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


# every frame: [where your name is written (art px down the screen), your drawn body's top (art px), jump shadows drawn]
NAMED = """() => { window.__nm = []; window.__nmOn = true; const sh = jumpShadow, ol = outlined; let shadows = 0, ny = null;
  jumpShadow = (...a) => { shadows++; return sh(...a); }; outlined = (t, x, y, c) => { if (t === me) ny = y; return ol(t, x, y, c); };
  const f = (now) => { const a = HdLook.art(), b = a && a.body; if (b && ny !== null) __nm.push([Math.round(ny / a.u), Math.round(b.y / a.u), shadows, now]); shadows = 0;
    if (__nmOn) requestAnimationFrame(f); else { jumpShadow = sh; outlined = ol; } }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_space_in_a_boat_moves_neither_the_boat_nor_your_name(game):
    """The audit's P-E: in a boat the jump key's hop ran (not swimming, no jump through the air): the name rose 20 px
    and a jump's shadow was drawn, the boat and the sailor did not move. A body in a boat is in a boat (body_place.js:
    one mode for all that draws it): its name stays, no shadow."""
    game.clear_area(8)
    game.stamp(1, -6, ["~~~~~~"] * 6)
    game.give(boat=1)
    game.rpc("dev_teleport", x=game.pos()[0] + 1, y=game.pos()[1]); game.arrive()
    game.hold_item("boat"); game.face(0, -1)
    game.press("e", 800)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")
    game.wait("meObs.self.sailing && ents.get('agent' + myId).e.sail", 5000)
    game.rest()
    game.js(NAMED)
    game.frames(3)
    game.page.keyboard.press("Space")
    game.sleep(600)
    r = game.js("(() => { __nmOn = false; return __nm; })()")
    assert len(r) > 10 and len({v[0] for v in r}) == 1 and sum(v[2] for v in r) == 0, (sorted({v[0] for v in r}), sum(v[2] for v in r))
    assert not game.errors, game.errors


@pytest.mark.realtime
def test_after_a_jump_down_three_levels_your_name_stays_over_your_head(game):
    """The audit's P-A: come down 2+ levels lower, the body is drawn lifted while the eye catches up (leap.js lift); the
    name and the bars had their own sum (jump.js overBody) without it, and sat 30 px and more off the head for a third
    of a second. They read the body's place: the name the same few px over the drawn body, every frame."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(-1, -2, ["." * 9] * 5, levels=["333000000"] * 5)
    game.rpc("dev_teleport", x=x, y=y, z=3); game.arrive(); game.rest()
    game.js(NAMED)
    game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
    game.sleep(60)
    game.page.keyboard.press("Space")
    game.wait("Leap.on()", 2000)
    game.wait("!Leap.on()", 4000)
    game.page.keyboard.up("d"); game.page.keyboard.up("Shift")
    game.sleep(600)
    r = game.js("(() => { __nmOn = false; return __nm; })()")
    # (the same few px over the body: never two frames in a row more than 6 off the usual. It was every frame, twenty
    # and more: on a runner, frames of 70 to 130 ms, one frame was 12 off as the eye glided down after you (leap.js
    # lift), the next back. What was wrong was a third of a second off: many frames, on any machine)
    gaps = [v[1] - v[0] for v in r]
    usual = sorted(gaps)[len(gaps) // 2]
    off = [abs(g - usual) > 6 for g in gaps]
    assert len(r) > 5 and not any(a and b for a, b in zip(off, off[1:])), str([(g, round(v[3])) for g, v in zip(gaps, r)])
    assert game.server()["z"] == 0 and not game.errors, (game.server(), game.errors)
