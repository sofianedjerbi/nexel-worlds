"""The eye (hd.js: one source, the cover, one easing): out in the open it looks from the surface's pitch whatever the land's
shape round you; it tilts to look from above only while land covers or hides you. doben00 walking north across a dip one
level deep: the eye tilted to 58 and back within a second, the mountain south of him sliding up the screen and down, "like
the mountain is moving". Every frame: the pitch, and where a fixed tile of the land is on the screen."""

import pytest
from test_e2e_hd_sun import hd

REC = """([fx, fy, fz]) => { window.__r = []; window.__on = true; const f = () => { const e = ents.get('agent' + myId), a = HdLook.screenOf(fx + .5, fy + .5, fz);
  if (e && a) __r.push([+e.x.toFixed(3), +e.y.toFixed(3), +HdLook.cam.pitch.toFixed(2), +a[1].toFixed(1), HdLevel.cover.roof ? 1 : 0]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def walk(g, key, done, mark):
    g.js(REC, mark)
    g.page.keyboard.down(key)
    g.wait(done, timeout=8000)
    g.page.keyboard.up(key)
    g.wait("!walking && !pred && !HdLook.busy", timeout=6000)
    g.sleep(700)
    r = g.js("(() => { __on = false; return __r; })()")
    return [b for a, b in zip(r, r[1:]) if b != a]               # (a frame a row: rAF ran twice a picture)


def turns(v):
    d = [b - a for a, b in zip(v, v[1:]) if abs(b - a) > .05]
    return sum(1 for a, b in zip(d, d[1:]) if a * b < 0)


@pytest.mark.realtime
def test_across_a_dip_the_eye_keeps_its_pitch_and_under_a_hill_it_tilts_once(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + i, y - 3] for i in range(-6, 7)], col=[-1])                # (a dip a level deep across the way, a tile wide)
    g.rpc("dev_col", tiles=[[x + i, y - j] for j in range(9, 14) for i in range(-3, 4)], col=[4])   # (north: a hill four high ...)
    g.rpc("dev_col", tiles=[[x, y - j] for j in range(9, 14)], col=[0, 2, 4])                # (... a tunnel into it at the meadow's level)
    g.rest()
    r = walk(g, "ArrowUp", f"myPos().y <= {y - 6}", [x + 3, y + 1, 0])
    assert len(r) > 15 and {q[2] for q in r} == {r[0][2]}, [q[2] for q in r]                # across the dip: one pitch, every frame
    dy = [b[3] - a[3] for a, b in zip(r, r[1:])]
    assert min(dy) > -4 and sum(v for v in dy if v < 0) > -12, dy                           # the land does not slide back up the screen: only the eye's own level down the dip and up (it slid 16 px a frame, then back)
    r = walk(g, "ArrowUp", f"myPos().y <= {y - 11}", [x + 2, y - 7, 0])                      # into the tunnel
    p = [q[2] for q in r]
    assert p[-1] > p[0] + 10 and turns(p) == 0, p                                           # under the hill: the eye tilts up, once, never back
    assert sum(1 for a, b in zip(r, r[1:]) if a[4] != b[4]) == 1, [q[4] for q in r]           # (the cover comes once)
    d2 = [abs((c[3] - b[3]) - (b[3] - a[3])) for a, b, c in zip(r, r[1:], r[2:])]
    step = sorted(abs(b[3] - a[3]) for a, b in zip(r, r[1:]))[len(r) // 2]
    assert max(d2) < max(8, 2 * step), (max(d2), step, [q[3] for q in r])                    # the land moves on smoothly through the tilt: no jolt from one frame to the next
    assert not g.errors
