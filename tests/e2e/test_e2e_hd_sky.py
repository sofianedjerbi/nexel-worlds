"""The HD look's sky (hd.js `eyeLine`, hd_view.js `skyOf`): fixed to the eye. Its horizon is where level ground at the
eye's own level meets it: the pitch and the screen alone. Land, however tall, covers it; it never moves with the land in
front of you, nor with how high you are. From a hill top the land ahead, lower, ends under it: that is the sky's EDGE
(the far hills stand on it, the sky goes on down to them: vox_sky.js), not the sky moved down.
(The owner: "if a big mountain is behind the player, the skybox bumps up in an unnatural way": the sky came down to the
lowest of the land's skylines north of you, eased: walking to a ridge the whole sky, sun, clouds and far hills, slid up
58 art px, a px or two a frame, and down again walking along it.)"""

import pytest

from game import Game, new_name

# each frame: the sky's line (art px from the picture's top), the eye's pitch, where you are
REC = """() => { window.__sk = []; window.__on = true; const f = () => { __sk.push([HdLook.sky(0).line / zoom, HdLook.cam.pitch, myPos().x, myPos().y]);
  if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def ridge(g, cx, cy, z0, r=8, rx=30, step=4):
    """A stepped ridge 61 tiles across and 17 deep, 36 levels high at its crest."""
    by = {}
    for j in range(-r, r + 1):
        for i in range(-rx, rx + 1):
            by.setdefault(z0 + max(1, (r + 1 - max(-(-abs(i) * r // rx), abs(j))) * step), []).append([cx + i, cy + j])
    for h, t in by.items():
        g.rpc("dev_col", tiles=t, col=[h])


def test_walking_past_a_tall_mountain_the_sky_does_not_move(browser, server):
    g = Game(browser.new_page(viewport={"width": 1440, "height": 900}), server)
    g.join(new_name("sky"), 3)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    x, y = g.pos()
    z0 = g.js(f"topAt({x}, {y})")
    # (all the land the sky's line looks at made one meadow: the lowest land ahead (hd.js lowAhead) is read 6 to 64 tiles
    #  north of you, 24 east and west. Only 34 north were laid out, by dev_col, which leaves what stands: a pond, a pit
    #  another test dug, out there lowered the line a px as you walked, every run after the x-ray tests; and a tree at
    #  (x + 23, y) stopped the walk west, two runs in eight; and the eye looks down more steeply over land south of you
    #  taller than you (hd.js clear, out to 24 rows): another test's plateau south of the walk tilted it, the line with it)
    g.stamp(-60, -72, ["." * 121] * 106)
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-72, 34) for i in range(-60, 61)], col=[z0])
    ridge(g, x, y - 18, z0)
    g.rest()
    flat = g.js("HdLook.sky(0).line / zoom")
    for sx, sy, key, ms in ((x, y + 8, "ArrowUp", 2400), (x + 24, y, "ArrowLeft", 4000)):   # to the ridge's foot; along it, its columns' heights coming and going north of you
        g.rpc("dev_teleport", x=sx, y=sy, z=z0); g.arrive(); g.rest()
        g.js(REC)
        g.page.keyboard.down(key)
        g.page.wait_for_timeout(ms)
        g.page.keyboard.up(key); g.rest()
        rec = g.js("(() => { __on = false; return __sk; })()")
        moved = abs(rec[-1][2] - sx) + abs(rec[-1][3] - sy)
        assert moved >= 8, (key, moved)
        steps = [(abs(b[0] - a[0]), a, b) for a, b in zip(rec, rec[1:]) if a[1] == b[1]]     # (frames with the same pitch)
        assert len(steps) > 30 and max(s[0] for s in steps) < 1, (key, max(steps))
        assert {r[0] for r in rec} == {flat}, (key, sorted({r[0] for r in rec}), flat)    # (the meadow's, before the ridge was there)
    # a hill top: the land round it is lower, and drops away past the bend lower on the screen: the sky's EDGE comes
    # down to where that land meets it (hd.js lowAhead), the far hills on it. The sky's line stays the eye's. (The edge
    # stayed where ground at your level would meet the sky, and the band between was the backdrop's flat colours, "that
    # blue mass behind": test_e2e_hd_horizon.py; then the whole sky came down with it, 9 art px a level climbed)
    g.rpc("dev_col", tiles=[[x + 20 + i, y + 2 + j] for j in range(-2, 3) for i in range(-2, 3)], col=[z0 + 12])
    g.rpc("dev_teleport", x=x + 20, y=y + 2, z=z0 + 12); g.arrive(); g.rest()
    g.wait(f"HdLook.low === {z0} && Math.abs(HdLook.sky(0).edge / zoom - HdLook.line[1] - 2) < 1", 5000)   # (eased down as the eye goes up)
    assert g.js("HdLook.sky(0).edge / zoom") > flat + 20
    assert g.js("HdLook.sky(0).line / zoom") == flat


# each frame: the sky's line, the sun's height on the screen (vox_sky.js: the line less its share of the line), the
# edge, the pitch, how far north you are (art px; y)
CALM = """() => { window.__sk = []; window.__on = true; const f = () => { const s = HdLook.sky(0), l = s.line / zoom;
  __sk.push([l, l - Math.floor(Math.max(l, 8) * s.at[1]), s.edge / zoom, HdLook.cam.pitch, myPos().y]); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def test_sprinting_over_a_hill_of_steps_the_sky_stays_put(browser, server):
    """"the skybox moves wildly when the player travels": up a hill of steps 6 levels high and down again, at a sprint,
    the whole sky (its bands, the sun, the clouds) came down 9 art px a level climbed and up again: 55 px in 3 s (the
    eye's height over the land ahead, hd.js). A real sky does not move as you walk: under the open sky, the pitch
    the same all the way, the sky's line moves 1 art px a frame at the most and 4 in all, the sun with it (the bend
    counts a share of a height as distance, vox_curve.js lean: the eye's own horizon rises half a px a level climbed;
    the line is on whole px); the land's edge comes down from the top as it should."""
    g = Game(browser.new_page(viewport={"width": 1440, "height": 900}), server)
    g.join(new_name("calm"), 3)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=80)
    # (a meadow 81 wide out to 100 tiles north: the lowest land ahead is read 64 north and 24 east and west. On it, 10
    #  tiles north, steps a level each 2 tiles up to 6, 4 tiles of top, and down again; past them a mountain 30 high
    #  to the east of the way)
    def lev(t, i):
        if 40 <= t <= 64 and 5 <= i <= 25:
            return max(0, 30 - 2 * max(abs(i - 15), abs(t - 52)))
        return max(0, min(6, (t - 10) // 2 + 1, 6 - (t - 26) // 2)) if 10 <= t < 38 else 0
    ch = lambda v: str(v) if v < 10 else chr(55 + v)
    g.stamp(-40, -100, ["." * 81] * 100, ["".join(ch(lev(t, i)) for i in range(-40, 41)) for t in range(100, 0, -1)])
    g.stamp(-40, 0, ["." * 81] * 30)                    # (and 30 south: the eye looks 24 rows south for land over you, hd.js clear)
    g.rest()
    # (the eye settled to the open sky's pitch first: woken by another test's land, it was still tilting back from 54 degrees, one run in eight)
    g.wait("HdLook.cam.pitch === HdLook.cam.want && HdLook.cam.want === HdLook.cam.base && !HdLook.hid", 5000)
    g.js(CALM)
    g.hold(["Shift", "ArrowUp"], 6000)
    g.rest()
    rec = g.js("(() => { __on = false; return __sk; })()")
    y0 = rec[0][4]
    assert y0 - rec[-1][4] >= 45, (y0, rec[-1])                                      # (over the hill and past the mountain)
    pitch = [r[3] for r in rec]
    assert max(pitch) - min(pitch) < .5, (min(pitch), max(pitch))                   # (under the open sky all the way)
    line, sun, edge = ([r[i] for r in rec] for i in range(3))
    steps = max(abs(b - a) for a, b in zip(line, line[1:]))
    assert steps <= 1 and max(line) - min(line) <= 4, (steps, min(line), max(line), [(r[0], round(r[3], 1), r[4]) for r in rec[::6]])   # (the state all along: the line, the pitch, your row)
    assert max(sun) - min(sun) <= 4, (min(sun), max(sun))
    assert max(edge) > min(line) + 20 and all(e >= l for e, l in zip(edge, line)), (max(edge), min(line))   # (on the top the land ahead ends lower: the edge, not the sky)
    assert not g.errors, g.errors


PITCH = """() => { window.__pt = []; window.__on = true; const f = () => { const p = ents.get('agent' + myId); __pt.push([+HdLook.cam.pitch.toFixed(2), +p.x.toFixed(2), +p.y.toFixed(2)]);
  if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.parametrize("way", ["N", "S", "E", "W"])
def test_sprinting_down_a_stepped_hill_the_eye_does_not_nod(game, way):
    """"sprinting north down the spawn hill the pitch nods 36 -> 43 -> 36 on each step": down a hill of steps two tiles
    deep, each step just down had the one two levels up behind it, and the eye looked down more steeply to see your feet
    over its edge (hd.js clear), then back as you went on: a nod a step. Down six such steps, any way, under the open
    sky: the eye's pitch moves less than a degree a frame and stays within two of the open sky's."""
    # (meadow out to 30 tiles: the eye looks 24 rows south for land over you, and 6 tiles round for land shutting you in
    #  (hd_level.js steep); the ridge of the test above, 36 high, stood a few tiles north of the slope's foot: a valley)
    game.clear_area(30)
    d = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}[way]
    x, y = game.pos()
    lv = {t: max(0, 6 - max(0, t) // 2) for t in range(-3, 16)}          # (on the top, then six steps down, two tiles each)
    for t, h in lv.items():
        tiles = [[x + d[0] * t + d[1] * k, y + d[1] * t + d[0] * k] for k in range(-2, 3)]
        game.rpc("dev_col", tiles=tiles, col=[h])
    game.rpc("dev_teleport", x=x, y=y, z=6); game.arrive(); game.rest()
    open_sky = game.js("HdLook.cam.pitch")
    game.js(PITCH)
    # (sprinting until you are past the sixth step, 13 tiles on: a frame over 0.1 s is cut there (render.js update), so
    #  on the runners' CPU-drawn frames 1400 ms of the machine's time took you 10 tiles, a step short of the foot)
    keys = ["Shift", {"N": "w", "S": "s", "E": "d", "W": "a"}[way]]
    for k in keys:
        game.page.keyboard.down(k)
    game.wait(f"(() => {{ const p = myPos(); return (p.x - {x}) * {d[0]} + (p.y - {y}) * {d[1]} >= 13; }})()", timeout=15000)
    for k in reversed(keys):
        game.page.keyboard.up(k)
    game.rest()
    rec = game.js("(() => { __on = false; return __pt; })()")
    assert game.server()["z"] == 0, game.server()
    # (on the meadow laid out here: past it, 14 tiles on, the land another test left there: a ridge north of you tilts the eye as it should)
    rec = [r for r in rec if (r[1] - x) * d[0] + (r[2] - y) * d[1] <= 13]
    jolts = [(a, b) for a, b in zip(rec, rec[1:]) if abs(b[0] - a[0]) >= 1]
    assert not jolts, (open_sky, jolts[:4])
    assert max(abs(r[0] - open_sky) for r in rec) < 2, (open_sky, max(rec), [r for r in rec if abs(r[0] - open_sky) >= 2][:6])
    assert not game.errors, game.errors
