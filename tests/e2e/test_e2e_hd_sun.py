import pytest
"""The HD look's sun (hd_sun.js): what stands throws the hour's shadow on the land, away from the sun, and none at
night; a roof is two pitched faces; and while the land is made again after a change, a shadow keeps its own px."""


import game as game_module
import home
from conftest import Game, new_name



def hd(browser, server):
    """A player on the HD tests' place (home.py: flat dry land, the same for every test), the meadow laid out round it:
    every run of a test on the same land. (It played where the player woke, by chance: the world's hills and the
    meadow's patches there were read with what the test laid out, one run in eight.) What tests before it on this
    worker's world laid out near the place is laid out again as meadow too (game.py BUILT): it leaves nothing; and
    only that, not 30 tiles round each time (+15 % on five HD files at -n 2)."""
    g = Game(browser.new_page(viewport={"width": 960, "height": 540}), server)
    g.join(new_name(), 3)
    g.js("setOpt('names', false); setOpt('hints', false)")
    x, y = home.PLACE
    g.rpc("dev_teleport", x=x, y=y)
    g.arrive()
    near = [b for b in game_module.BUILT if b[2] >= x - 60 and b[0] <= x + 60 and b[3] >= y - 60 and b[1] <= y + 60]
    game_module.BUILT.clear()
    for x0, y0, x1, y1 in near:
        if not (x0 >= x - 12 and x1 <= x + 12 and y0 >= y - 12 and y1 <= y + 12):      # (inside the square laid out below anyway)
            g.js("(a) => rpc('dev_stamp', a)", {"x": x0, "y": y0, "rows": ["." * (x1 - x0 + 1)] * (y1 - y0 + 1), "levels": [], "roofs": [], "heads": []})
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    game_module.BUILT.clear()                                # (the square: laid out by every HD test anyway)
    g.rpc("dev_teleport", x=x, y=y)
    g.arrive()
    g.rest()                                                 # (the land made and shown: it slept 1.2 s)
    return g


# the mean light of a tile's top as it is on the screen (the px inside its four corners' box, a px in)
LIGHT = """([x, y, z]) => { const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + a, y + b, z)), k = devicePixelRatio;
  const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 1, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 1, y0 = Math.ceil(c[0][1] * k) + 1, y1 = Math.floor(c[2][1] * k) - 1;
  const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data; let s = 0; for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2]; return s / (d.length / 4); }"""


def settled(g):
    """The land made again and shown (game.py rest: nothing being built, its water made once more, three frames since).
    It slept 0.35 s, waited for the build to be over and slept 0.25 s: on a busy machine the build had not begun after
    the first sleep, or the picture was not drawn yet after the second, and the old one was read."""
    g.rest()


def sides(g, x, y):
    """how much darker the tile west of (x, y) and the one east of it are with the shadows than without: [west, east], 1: the same"""
    out = []
    for much in (100, 0):
        g.js(f"setOpt('shadows', {much})")
        settled(g)
        out.append([g.js(LIGHT, [x - 1, y, 0]), g.js(LIGHT, [x + 1, y, 0])])
    g.js("setOpt('shadows', 100)")
    return [out[0][0] / out[1][0], out[0][1] / out[1][1]]


def test_a_cast_shadow_lies_on_the_suns_far_side_by_day_and_is_absent_at_night(browser, server):
    """A stone wall of one tile on a flat meadow. In the morning the sun is in the east: the tile west of the wall is
    darker with the shadows on than with them off, the tile east of it is not. In the evening the other way round.
    At night neither. (The two pictures of a side, shadows on then off, are two frames with the land made again between
    them: the hour is held still for them (hour(still=True)). At dawn the light grows by the second: on a busy machine
    the second picture was lighter all over, and both sides were "shaded", west .89 and east .82.)"""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(0, -3, ["%"])
        wx, wy = x, y - 3
        for phase, shaded in ((.1, "west"), (.62, "east"), (.9, None)):
            g.hour(phase, still=True)
            g.wait(f"Math.abs((clock.phase || 0) - {phase}) < .02")
            settled(g)
            west, east = sides(g, wx, wy)
            if shaded == "west":
                assert west < .97 and east > .995, (phase, west, east, g.js("HdSun.hour"))
            elif shaded == "east":
                assert east < .97 and west > .995, (phase, west, east, g.js("HdSun.hour"))
            else:
                assert west > .995 and east > .995, (phase, west, east, g.js("HdSun.hour"))
    finally:
        g.page.close()


PUT = """async ([list, stand]) => { const bad = [];
  for (const [x, y, z, item] of list) { const s = stand.find((q) => (q[0] - x) ** 2 + (q[1] - y) ** 2 + ((z - q[2]) * .5) ** 2 <= 6 && !(q[0] === x && q[1] === y));
    await rpc('dev_teleport', {x: s[0], y: s[1], z: s[2]}); const r = await rpc('act', {tool: 'place', args: {x, y, item, z}}); if (!r.ok) bad.push([x, y, z, item, r.detail || r.error]); } return bad; }"""


def test_a_roof_has_two_slopes(browser, server):
    """A roof of three rows on walls: its tops are pitched (hd_things.js `tilt`): the north rows rise towards the
    south, the south rows fall, they meet at one ridge, each row begins at the height the row north of it ended, and
    the eaves are at the roof block's own height (it was a slab that stepped 4 px a row)."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        x0, y0 = x - 1, y - 5
        g.stamp(-1, -5, ["WWWW", "WnnW", "W+WW"])
        g.rpc("dev_give", items={"roof": 12})
        room = [[x0 + 1, y0 + 1, 0], [x0 + 2, y0 + 1, 0]]
        assert g.js(PUT, [[[x0 + i, y0 + j, 3, "roof"] for j in (2, 1, 0) for i in range(4)], room]) == []
        g.rpc("dev_teleport", x=x, y=y, z=0)
        settled(g)
        tops = g.js("""([x, y0]) => { const out = []; for (let j = 0; j < 3; j++) for (const b of HdThings.at(x, y0 + j) || []) if (b.tilt) out.push([j * 16 + b.y, j * 16 + b.y + b.d, b.tilt[0], b.tilt[1], b.k]); return out.sort((a, b) => a[0] - b[0]); }""", [x0 + 1, y0])
        assert len(tops) == 4, tops                                          # (the ridge's row is two halves)
        assert tops[0][0] == 0 and tops[-1][1] == 48 and tops[0][2] == 0 and tops[-1][3] == 0, tops      # from eave to eave
        assert all(a[1] == b[0] and a[3] == b[2] for a, b in zip(tops, tops[1:])), tops               # one surface, no step
        up = [t for t in tops if t[3] > t[2]]
        down = [t for t in tops if t[3] < t[2]]
        assert up and down and len(up) + len(down) == 4, tops                # two pitched faces, nothing flat
        assert max(t[0] for t in up) < min(t[0] for t in down), tops         # the rising ones north of the falling ones: one ridge
        assert all(t[4] < 1 for t in up) and all(t[4] == 1 for t in down), tops   # the far face in less light: two faces to the eye
    finally:
        g.page.close()


@pytest.mark.parametrize("run", range(4))   # (PROBE #106: not for merge)
def test_a_shadow_keeps_its_px_while_the_land_is_made_again(browser, server, run):
    """Your own shadow, each frame, while a change of the land makes the land again (its paints wiped, a new set made
    over several frames): as many px of it all along, the shape it had. (A guard: what is drawn each frame over the
    land asks for its paints while the land still shown has its own set, vox_style.js A and B.)"""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.hour(.9)                                           # (night: the shadow under you alone, no cloud, no sun)
        g.wait("Math.abs((clock.phase || 0) - .9) < .02")
        g.stamp(-3, -3, ["T.b", "...", "M.C"])
        for dx, dy in ((3, 2), (-2, -1), (0, 0)):                             # (walked about: the paints are no longer in the order a new land makes them)
            g.rpc("dev_teleport", x=x + dx, y=y + dy, z=0)
            settled(g)
        g.js("""(() => { const p = myPos(), a = HdLook.screenOf(p.x + .5, p.y + .92, topAt(p.x, p.y)), k = devicePixelRatio, X = Math.round(a[0] * k), Y = Math.round(a[1] * k);
          const mid = HdLook.read(X, Y, 1, 1).data; window.__sh = []; window.__st = []; window.__b0 = HdLook.builds; window.__busy = 0;
          const f = () => { const d = HdLook.read(X - 24 * k, Y - 9 * k, 48 * k, 18 * k).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - mid[0]) + Math.abs(d[i + 1] - mid[1]) + Math.abs(d[i + 2] - mid[2]) < 12) n++;
            window.__sh.push(n); window.__st.push([n, HdLook.why, HdLook.busy ? 1 : 0, HdLook.builds, HdThings.sheet.id, [...HdLook.read(X, Y, 1, 1).data.slice(0, 3)].join(), "out " + [...HdLook.read(X + 30 * k, Y, 1, 1).data.slice(0, 3)].join(), "outN " + [...HdLook.read(X, Y - 14 * k, 1, 1).data.slice(0, 3)].join(), "lamps " + JSON.stringify(self.__lampsDbg || null), JSON.stringify(HdLook.work)]); if (HdLook.busy) window.__busy++; if (window.__sh.length < 150) requestAnimationFrame(f); };
          requestAnimationFrame(f); return 1; })()""")
        g.sleep(150)
        # (rocks, away from you, along a row 25 tiles long: the land's version changes, in more than one of its chunks. It was
        # one rock: that one chunk was sometimes made again within a single frame's share, and then nothing was "made over
        # frames" for this test to watch: "builds 8 -> 9, frames it was being made: 0")
        g.stamp(-12, -6, ["M" + "." * 11 + "M" + "." * 11 + "M"])
        g.wait("window.__sh.length >= 150", 15000)
        got = g.js("window.__sh")
        assert g.js("HdLook.builds > window.__b0 && window.__busy > 0"), f"the land was not made again over frames: builds before, now, frames it was being made, its version: {g.js('[window.__b0, HdLook.builds, window.__busy, landVer]')}"
        # (the frames round the one that lost it, each [its px, why the frame was drawn, land being made, lands made, the things' sheet, the px under you, the paints' work]:
        #  it reads 0 px on one frame one run in twenty on a machine loaded past 15, never in 70 runs under that: the state is said so that the next one tells)
        k = min(range(len(got)), key=lambda q: got[q])
        st = g.js("window.__st"); print("PROBE #106 frames:"); [print(r[:9]) for r in st]            # (PROBE #106: not for merge)
        assert False, "probe: see the frames printed above"
        assert got[0] > 60 and max(got) - min(got) <= 4, (got[0], min(got), max(got), k, g.js("window.__st")[max(0, k - 3):k + 4], g.js("[window.__busy, HdLook.builds, window.__b0]"))   # (all of it: which frame lost it)
    finally:
        g.page.close()


# the light (r + g + b) of the screen px below a two-tile block's foot, across its middle, row by row from 2 px under the foot
ROWS = """([bx, by, n]) => { const k = devicePixelRatio, a = HdLook.screenOf(bx + .25, by + 1, 0), b = HdLook.screenOf(bx + 1.75, by + 1, 0);
  const x0 = Math.round(a[0] * k), x1 = Math.round(b[0] * k), y0 = Math.round(a[1] * k) + 2, d = HdLook.read(x0, y0, x1 - x0, n).data, w = x1 - x0, out = [];
  for (let j = 0; j < n; j++) { const r = []; for (let i = 0; i < w; i++) { const q = (j * w + i) * 4, s = d[q] + d[q + 1] + d[q + 2]; r.push(s); } out.push(r); } return out; }"""


def test_a_shadow_is_cast_in_the_world_and_the_eye_alone_foreshortens_it(browser, server):
    """A stone block 6 high at noon (the sun straight north: its shadow straight south). Seen from 36 degrees and from
    78.6 (the eye's view from above: the window forced on, HdLook.force; it looks from above only under cover), its shadow ends on the screen where the
    world's shadow (6 levels times the sun's way) ends as the eye projects it, within a few px, and it is one shape,
    no gap at a tile's edge. (It was stretched by 1 / .6 for the 36-degree eye: from 78.6 a cliff's shadow lay 1.6x as
    long on the screen, in flat slabs.)"""
    g = hd(browser, server)
    try:
        R = 7
        lv = ["".join("6" if (i, j) in ((-1, -5), (0, -5)) else "0" for i in range(-R, R + 1)) for j in range(-R, R + 1)]
        g.stamp(-R, -R, ["." * (2 * R + 1)] * (2 * R + 1), levels=lv)
        g.hour(.375, still=True)
        x, y = g.pos()
        bx, by = x - 1, y - 5
        for pitch in (36, 78.6):
            g.js(f"HdLook.steep = {pitch}; HdLook.force = {'null' if pitch < 40 else 1}")
            g.wait(f"Math.abs(HdLook.cam.pitch - {pitch}) < .05", 8000)
            ky = g.js("Math.round(SunLand.hour().ky * 8) / 8")                 # (the sun's way in the world: ground px a px of height)
            want = g.js("([bx, by, L]) => { const k = devicePixelRatio; return (HdLook.screenOf(bx + 1, by + 1 + L, 0)[1] - HdLook.screenOf(bx + 1, by + 1, 0)[1]) * k; }", [bx, by, 6 * ky])
            n = int(want * 1.8) + 20
            shots = []
            for much in (100, 0):
                g.js(f"setOpt('shadows', {much})")
                g.rest()
                shots.append(g.js(ROWS, [bx, by, n]))
            g.js("setOpt('shadows', 100)")
            mask = [[on < off - 12 for on, off in zip(ro, rf)] for ro, rf in zip(*shots)]
            rows = [sum(r) / len(r) for r in mask]
            # (its length: the rows more than half in shadow from the foot on (2 px under it), to the first that is not: past it lies your own)
            got = next((j for j, f in enumerate(rows) if f <= .5), len(rows)) + 2
            assert abs(got - want) <= 4 * g.js("devicePixelRatio") + 2, (pitch, got, want, ky, " ".join(f"{f:.1f}" for f in rows))
            # (one shape: every row from the foot to its end mostly in shadow: no lit row across it at a tile's edge)
            assert all(f > .8 for f in rows[: max(0, got - 6)]), (pitch, " ".join(f"{f:.1f}" for f in rows))
    finally:
        g.js("HdLook.force = null")
        g.page.close()


def test_by_day_no_halo_lies_round_you(browser, server):
    """"When it's luminous, remove the halo around the player: it's ugly, especially in daylight." By day (the clock's
    day: noon, a sunset, a dawn, the sky already rose and the land lit by it) the ground 2 to 5 tiles from you is the
    colour of the ground 9 tiles off: no pool of lamp light round you. (Your lamp was drawn once the hour's light was a
    fifth down: from the sunset on, a yellow disc of rings on a meadow still in daylight.) North and south of you: the
    low sun's shadow of you lies east or west."""
    from test_e2e_hd_stair import MOST
    g = hd(browser, server)
    try:
        x, y = g.pos()
        near = [(0, 2), (0, 3), (0, -2), (0, -3), (1, 4), (-1, 5)]
        for phase in (.375, .72, .745, .005, .02):                                         # (.745, .005: the day's last and first minutes, the hour's light well down: the lantern was lit there, from .45 of dark)
            g.hour(phase, still=True)
            g.wait(f"Math.abs((clock.phase || 0) - {phase}) < .02 && !clock.night")
            settled(g)
            assert g.js("Light.now().open") == 0, phase                                      # (daylight.js Light: your lantern under the sky is none by day)
            far = [g.js(MOST, [x + 9, y + j, x + 10, y + j + 1, 0]) for j in (-1, 1)]
            assert max(abs(a - b) for a, b in zip(*far)) <= 3, (phase, far)               # (the far ground: one colour)
            for dx, dy in near:
                c = g.js(MOST, [x + dx, y + dy, x + dx + 1, y + dy + 1, 0])
                assert max(abs(a - b) for a, b in zip(c, far[0])) <= 3, (phase, (dx, dy), c, far[0])
    finally:
        g.page.close()
