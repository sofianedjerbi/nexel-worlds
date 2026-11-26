"""Where your body is (hd_level.js `place`) and the land over it (`cover`): one record each a frame, from the cells and your body's place and height, that
the light, the dark, the x-ray window and the veil over built floors all read. Climbing a ladder is being at a height
between two levels on the ladder's tile: it changes nothing that standing there would not. (Half way up a ladder the
window opened and the earth's light came on: the picture took the tile you were rounded to, the cliff's, with you
under its top: "under a roof".) And walking into a room dug under the meadow, or a tunnel's mouth in a hill, the
window opens once at its edge and shuts once on the way out: no flicker."""

import pytest
from test_e2e_hd_sun import LIGHT, hd

# every frame: [your y, x, how open the window is (this file's count), the painter's, behind land (hid), the record's roof, its dep, your lantern lit (night), then the light of each tile asked (null: off the picture), the frame's time]
REC = """(tiles) => { window.__r = []; window.__on = true; const light = """ + LIGHT + """, f = (now) => { const e = ents.get('agent' + myId), P = HdLevel.cover, H = innerHeight - 20;
  if (e && P) __r.push([+e.y.toFixed(3), +e.x.toFixed(3), +HdLook.u.toFixed(2), +HdLook.win.a.toFixed(2), HdLook.hid, P.roof ? 1 : 0, P.dep, HdLook.youLit === false ? 0 : 1,
    ...tiles.map(([x, y, z]) => { const a = HdLook.screenOf(x + .5, y + .5, z); return a && a[1] > 20 && a[1] < H && a[0] > 20 && a[0] < innerWidth - 20 ? Math.round(light([x, y, z])) : null; }), now]);
  if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""
STOP = "(() => { __on = false; return __r; })()"
OPEN = [0, 0, 0, 0, 1]             # (no window, nothing over you, no land over you, your lantern lit)
open_ = lambda r: r[2:4] + r[5:8]   # (all but hid: you are shown through what stands in front of you, a ladder too, as you would standing there)


def go(g, key, done, jump=False):
    g.page.keyboard.down(key)
    for _ in range(100):
        if g.js(done):
            break
        if jump:                                             # (up a step: Space at each)
            g.page.keyboard.press("Space")
        g.frames(1)                                          # (a frame drawn, not 100 ms of the machine's: #47)
    g.wait(done, timeout=8000)
    g.page.keyboard.up(key)
    g.wait("!walking && !pred && !HdLook.busy", timeout=6000)
    g.sleep(500); g.frames(5)                                # (settled: half a second and five frames. Five frames alone read the window open at the top)


@pytest.mark.realtime
def test_up_and_down_a_ladder_in_the_open_nothing_of_the_light_or_the_window_changes(browser, server):
    """A cliff six high north of the meadow, a ladder against it. Up and down it, every frame, by day and at night:
    the window stays shut, nothing hides you, nothing is over you, your lantern is lit, and a meadow tile by the
    ladder's foot and a cliff top by its top are as light as when you stand at the foot or at the top."""
    g = hd(browser, server)
    x, y = g.pos()
    g.stamp(-4, -6, ["........."] * 3, levels=["666666666"] * 3)
    g.rpc("dev_stamp", x=x, y=y - 3, rows=["l"])
    g.rest()
    tiles = [[x + 2, y - 2, 0], [x + 2, y - 4, 6]]
    for phase in (.3, .9):
        g.hour(phase, still=True)
        g.rpc("dev_teleport", x=x, y=y - 3, z=0); g.arrive(); g.rest(); g.sleep(400); g.frames(5)
        g.js(REC, tiles); g.sleep(300); g.wait("__r.length >= 5", 8000)   # (0.3 s standing at the foot, and five frames of it)
        foot = g.js(STOP)
        g.js(REC, tiles)
        go(g, "ArrowUp", "myAt.z === 6 && !Climb.climbOf(ents.get('agent' + myId))")
        up = g.js(STOP)
        g.js(REC, tiles); g.sleep(300); g.wait("__r.length >= 5", 8000)
        stood = g.js(STOP)
        g.js(REC, tiles)
        go(g, "ArrowDown", "myAt.z === 0 && !Climb.climbOf(ents.get('agent' + myId))")
        down = g.js(STOP)
        assert foot and stood and all(open_(r) == OPEN for r in foot + stood), (foot[:2], stood[:2])
        assert len(up) > 20 and len(down) > 20
        bad = [r for r in up + down if open_(r) != OPEN]
        assert not bad, (phase, bad[:6])
        assert flips(up, 4) <= 1 and flips(down, 4) <= 1 and up[-1][4] == stood[0][4] and down[-1][4] == foot[0][4], (up, down)   # (shown through the ladder once you are past it: as standing there)
        for i, tol in ((8, 4), (9, 30)):                     # (by day each tile as light while you climb as while you stand; the cliff's top is read at a px or two on as the eye rises: its speckles)
            ref = [r[i] for r in foot + stood if r[i] is not None]
            assert ref, i
            off = [r for r in up + down if r[i] is not None and not min(ref) - tol <= r[i] <= max(ref) + tol]
            assert phase > .5 or not off, (phase, i, min(ref), max(ref), off[:6])
        # (at night your lantern goes up the ladder with you: the meadow by its foot darkens as you go, a little a frame, no
        # light switched: 8 a sixtieth of a second at most, by the frame's own time (a frame moves you by it, 0.1 s at the
        # most): 22 in one frame of a runner's 15 a second was the climb, not a switch)
        for rows in (up, down):
            seq = [(r[8], r[-1]) for r in rows if r[8] is not None]
            fast = [(a, b, round(t2 - t1)) for (a, t1), (b, t2) in zip(seq, seq[1:]) if abs(a - b) > 8 * max(1, min(100, t2 - t1) / 16.7)]
            assert not fast, (phase, fast[:6])
    assert not g.errors


def flips(r, i):
    """how many times column i changes"""
    return sum(1 for a, b in zip(r, r[1:]) if a[i] != b[i])


def turns(r, i):
    """how many times column i changes its way (up, then down: one)"""
    d = [b[i] - a[i] for a, b in zip(r, r[1:]) if b[i] != a[i]]
    return sum(1 for a, b in zip(d, d[1:]) if a * b < 0)


@pytest.mark.realtime
def test_into_a_dug_room_and_a_tunnel_mouth_the_window_opens_once_and_shuts_once(browser, server):
    """East: two steps down to a room dug under the meadow. North: a hill three high, a tunnel into it at the meadow's
    level. In and out of each, every frame: the record's roof flips once at the edge each way, and the window opens
    once and shuts once (its count goes up, then down: no flicker)."""
    g = hd(browser, server)
    g.hour(.3, still=True)
    x, y = g.pos()
    g.stamp(-3, -9, ["......."] * 5, levels=["3333333"] * 5)                        # (the hill: rows y-9 to y-5)
    g.rpc("dev_col", tiles=[[x, y - j] for j in range(5, 10)], col=[0, 2, 3])          # (its tunnel, at the meadow's level)
    g.rpc("dev_col", tiles=[[x + 1, y]], col=[-1])
    g.rpc("dev_col", tiles=[[x + 2, y]], col=[-2])
    g.rpc("dev_col", tiles=[[x + i, y] for i in range(3, 8)], col=[-3, -1, 0])         # (the room: its floor -3, the meadow over it)
    g.rest()
    for name, (k_in, k_out, done_in, done_out, jump) in {
        "room": ("ArrowRight", "ArrowLeft", f"myPos().x >= {x + 6}", f"myPos().x <= {x} && myAt.z === 0", True),
        "tunnel": ("ArrowUp", "ArrowDown", f"myPos().y <= {y - 8}", f"myPos().y >= {y}", False),
    }.items():
        g.rpc("dev_teleport", x=x, y=y, z=0); g.arrive(); g.rest(); g.sleep(400)
        g.js(REC, [])
        go(g, k_in, done_in)
        go(g, k_out, done_out, jump)
        g.wait("HdLook.win.a === 0", 3000)                                            # (the window shuts 300 ms after the land last hid you, then fades)
        r = g.js(STOP)
        assert flips(r, 5) == 2 and r[-1][5] == 0 and max(q[5] for q in r) == 1, (name, [(q[0], q[1], q[5]) for q in r])   # (under the land: once in, once out)
        assert turns(r, 2) <= 1 and turns(r, 3) <= 1, (name, [(q[0], q[1], q[2], q[3]) for q in r])                      # (the window: open, then shut)
        assert max(q[3] for q in r) == 1 and r[-1][3] == 0
    assert not g.errors
