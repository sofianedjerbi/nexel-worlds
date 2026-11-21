"""Going under the land in the HD look (hd_level.js, hd.js, vox_style.js, vox_style_glsl.js): walking down a covered
stair the x-ray window is open on you on every frame land is over you (you were drawn on the grass over the stair, the
window shut, for a second: the picture took your level from the classic x-ray, which never opens during a hop), your
body is steady on the screen (it went a level down and back at every tile), the eye tilts once on the way down and once
on the way out (a shaft was seen from the side and its way out from above), the sky's edge follows the tilt back (a pale
band lay over the meadow), and depth is told inside the window: a deep room's far floor is dimmer than a shallow one's,
its section thicker, no shade outside its rim."""

import pytest
from test_e2e_hd_sun import hd, settled

# every frame: [your x, the eye's pitch, land over you, the window open on your tile (half its px or more), your body's y on the screen (px), the level drawn, the level the game has you at, how open the window is]
REC = """(() => { window.__r = []; window.__on = true; const f = () => { const e = ents.get('agent' + myId), tx = Math.round(e.x), ty = Math.round(e.y), lv = HdLook.level, b = HdLook.screenOf(e.x + .5, e.y + .5, lv[2]);
  if (b && myAt) __r.push([e.x, HdLook.cam.pitch, topAt(tx, ty) > myAt.z ? 1 : 0, HdLook.win.a >= .5 && HdLook.winAt(tx, ty) ? 1 : 0, b[1], lv[0], myAt.z, HdLook.win.a]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
PX = """([x, y, z]) => { const a = HdLook.screenOf(x, y, z), k = devicePixelRatio; return [...HdLook.read(Math.round(a[0] * k), Math.round(a[1] * k), 1, 1).data.slice(0, 3)]; }"""
lum = lambda c: (c[0] * 3 + c[1] * 6 + c[2]) / 10


def stair(g):
    """East of you: six open steps down, eight more under the land, a flat passage 14 deep (the fifth audit's stair)"""
    x, y = g.pos()
    g.stamp(-9, -9, ["." * 34] * 19)
    g.rest()
    for i in range(1, 7):
        g.rpc("dev_col", tiles=[[x + i, y]], col=[-i])
    for i in range(7, 15):
        g.rpc("dev_col", tiles=[[x + i, y]], col=[-i, -i + 3, 0])
    g.rpc("dev_col", tiles=[[x + i, y] for i in range(15, 20)], col=[-14, -11, 0])
    g.rest()
    return x, y


def walk(g, key, done):
    g.js(REC)
    g.page.keyboard.down(key)
    g.wait(done, timeout=12000)
    g.page.keyboard.up(key)
    g.wait("!HdLook.busy", timeout=6000)
    g.sleep(600)
    return g.js("(() => { __on = false; return __r; })()")


def turns(r):
    """how many times the eye's tilt changes its way"""
    d = [b[1] - a[1] for a, b in zip(r, r[1:]) if abs(b[1] - a[1]) > .01]
    return sum(1 for a, b in zip(d, d[1:]) if a * b < 0)


@pytest.mark.realtime
def test_down_a_covered_stair_the_window_is_open_on_every_frame_and_your_body_is_steady(browser, server):
    g = hd(browser, server)
    g.rpc("dev_time", phase=.3)
    x, y = stair(g)
    r = walk(g, "ArrowRight", f"myPos().x >= {x + 18}")
    assert g.pos()[0] >= x + 18 and g.js("HdLook.level[0]") == -14
    under = [v for v in r if v[2]]
    assert len(under) > 60, len(under)                                           # (the eight covered steps and the passage)
    shut = [(round(v[0], 2), v[5], v[6]) for v in under if not v[3]]
    assert not shut, (len(shut), shut[:6])                                       # land over you: the window is open on your tile, that very frame
    part = [i for i, v in enumerate(r) if v[2] and v[7] < 1]
    assert len(part) <= 4, (len(part), part[:8])                                 # (where the search for your space was late: half its px that frame, all of them within three more; it was all in one frame: a pop)
    assert all(v[5] == v[6] for v in r), [(v[0], v[5], v[6]) for v in r if v[5] != v[6]][:6]    # drawn at the level the game has you at, never on the grass over it
    steps = [(round(a[0], 2), round(b[4] - a[4], 1)) for a, b in zip(r, r[1:]) if abs(b[4] - a[4]) > 4.5]
    assert not steps, steps[:8]                                                  # your body does not jump on the screen (it went 16 px at each tile's middle, and 100 at the roof)
    assert turns(r) == 0 and r[0][1] < 37 and r[-1][1] > 67.9, (turns(r), r[0][1], r[-1][1])    # one tilt, on the way down
    # and back up: one tilt back, near the top
    r = walk(g, "ArrowLeft", f"myPos().x <= {x}")
    assert not [v for v in r if v[2] and not v[3]] and turns(r) == 0 and r[-1][1] < 36.1
    back = next(v[0] for v in r if v[1] < 67.9)
    assert back < x + 2.6, back - x                                              # the eye stays over the stair until its last steps


def test_a_shaft_and_its_way_out_are_one_view(browser, server):
    """Six down a shaft a tile wide: seen from above, as the tunnel dug out of it is (it was the side view, then, one
    step on, the view from above); on a dug stair it stays so until the last step but one; at a cliff's foot on the
    surface the eye does not tilt."""
    g = hd(browser, server)
    g.rpc("dev_time", phase=.3)
    x, y = g.pos()
    g.stamp(-9, -9, ["." * 34] * 19)
    g.rest()
    g.rpc("dev_col", tiles=[[x, y]], col=[-6])
    for i in range(1, 6):
        g.rpc("dev_col", tiles=[[x + i, y]], col=[-6 + i])                       # the stair cut out of it, open to the sky
    g.rpc("dev_teleport", x=x, y=y, z=-6)
    g.arrive()
    g.wait("HdLook.cam.pitch > 67.9 && HdLook.win.n === 0 && !HdLook.busy", timeout=8000)      # (under the open sky no window: from above the shaft is seen as it is)
    for i, steep in ((2, True), (4, True), (5, False)):                          # levels -4, -2: walls of two beside you; -1: out
        g.rpc("dev_teleport", x=x + i, y=y, z=-6 + i)
        g.arrive()
        g.wait(f"HdLook.cam.pitch {'> 67.9' if steep else '< 36.1'}", timeout=8000)
    g.stamp(3, -4, ["...", "...", "..."], levels=["555", "555", "555"])          # a block of land five high, on the meadow: stand at its foot, south of it, then west
    g.rest()
    for dx, dy in ((4, -1), (2, -3)):
        g.rpc("dev_teleport", x=x + dx, y=y + dy)
        g.arrive()
        g.sleep(900)
        assert g.js("HdLook.cam.pitch") < 36.1, (dx, dy)


def deep_room(g, x, y, depth):
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[-depth, -depth + 3, 0])
    g.rpc("dev_teleport", x=x, y=y, z=-depth)
    g.arrive()
    g.wait(f"HdLook.win.a === 1 && HdLook.win.n >= 35 && !HdLook.busy && HdLook.cam.pitch > 67.9 && HdLook.level[1] === {-depth}", timeout=8000)     # (the eye come down to you: read before, the px were other places)
    g.js("(() => { WayShow.paint = () => {}; return 1; })()")
    g.rest()


# the colour most px of a piece of the land have (x0, y0 to x1, y1 at level z): the ground's own, whatever marks its picture has there
MOST = """([x0, y0, x1, y1, z]) => { const a = HdLook.screenOf(x0, y0, z), b = HdLook.screenOf(x1, y1, z), k = devicePixelRatio, d = HdLook.read(Math.round(a[0] * k), Math.round(a[1] * k), Math.round((b[0] - a[0]) * k), Math.round((b[1] - a[1]) * k)).data, n = new Map();
  for (let i = 0; i < d.length; i += 4) { const c = d[i] + ',' + d[i + 1] + ',' + d[i + 2]; n.set(c, (n.get(c) || 0) + 1); } return [...n].sort((p, q) => q[1] - p[1])[0][0].split(',').map(Number); }"""


def spot(g, x, y, z):
    """A floor's own colour round a place: the one most px of a tile of it have. (One px, and the middle one of seven, were a speck or
    a darker patch of the earth's own picture wherever you woke with one under it: the far floor 362 for 399, the near one 126 for 150.)"""
    return g.js(MOST, [x - .5, y - .5, x + .5, y + .5, z])


def test_depth_is_told_inside_the_window(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer"):
        g.js(f"setOpt('{o}', 0)")
    x, y = g.pos()
    g.stamp(-9, -9, ["." * 34] * 19)
    g.rest()
    seen, strata = {}, {}
    for depth, dx in ((4, 0), (14, 12)):
        deep_room(g, x + dx, y, depth)
        cx = x + dx
        near, far = spot(g, cx + 1.5, y + .5, -depth), spot(g, cx - 2.5, y + 1.5, -depth)      # the floor beside you; the floor 3.5 tiles off, away from the walls' feet
        # the section over the north edge: rows of earth counted up from the wall's top, in the room's middle column
        top = g.js(f"HdLook.screenOf({cx + .5}, {y - 2}, {-depth + 3})")
        col = g.js("([px, py]) => { const k = devicePixelRatio, o = []; for (let j = 0; j < 56; j++) o.push([...HdLook.read(Math.round(px * k), Math.round((py - (j + .5) * zoom) * k), 1, 1).data.slice(0, 3)]); return o; }", top)
        rows = next((i for i, c in enumerate(col) if c[1] > c[0] + 8), len(col))                     # up to the first green px: the meadow
        tones = [lum(c) for c in col[:rows]]
        bands = 1 + sum(1 for a, b in zip(tones, tones[1:]) if abs(a - b) > 2)                       # the strata: flat tones, one a level
        spots = [[cx + 4.4, y - 1.5 + j * .7, 0] for j in range(5)] + [[cx - 3.4, y - 1.5 + j * .7, 0] for j in range(5)]     # the meadow a little east and west of the hole's edges
        out = [g.js(PX, p) for p in spots]
        g.js("HdLook.nowin = true")
        g.wait("HdLook.win.a === 0", timeout=4000)
        g.frames(2)
        open_ = [g.js(PX, p) for p in spots]                                                          # the same px with the window shut
        g.js("HdLook.nowin = false")
        strata[depth] = (rows, bands, tones)
        seen[depth] = (lum(near), lum(far), rows, out, open_, g.js('[HdLook.level, myPos(), HdLook.win.n, HdLook.cam.pitch, clock.phase]'), near, far)
    assert seen[14][1] < seen[14][0] * .9, seen[14]                 # deep: the floor away from you is dimmer than the floor round you
    assert seen[4][1] > seen[4][0] * .93, seen[4]                   # shallow: one light
    # the section over the north wall is as tall as the ground over the ceiling is from this eye (3 px a level at the steep pitch): 1 level over the room 4 deep, 11 over the one 14 deep: two pictures at a glance
    # (it was 8 to 20 rows whatever the depth: 14 deep read 2 or 3 deep); in strata, a tone a level, darker level by level down: levels can be counted
    assert strata[4][0] <= 6 and strata[14][0] >= 26 and strata[14][1] >= 8, strata
    assert strata[14][2][1] < strata[14][2][strata[14][0] - 3] * .7, strata[14]
    for d in (4, 14):
        assert all(abs(p - q) <= 6 for a, b in zip(seen[d][3], seen[d][4]) for p, q in zip(a, b)), seen[d][3:5]                    # the grass beside the hole is the meadow's own px, not a step darker (a shade outside the rim read as a block standing on the grass)
