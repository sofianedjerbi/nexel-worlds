"""The HD look's sun (hd_sun.js): what stands throws the hour's shadow on the land, away from the sun, and none at
night; a roof is two pitched faces; and while the land is made again after a change, a shadow keeps its own px."""


from conftest import Game, new_name



def hd(browser, server):
    g = Game(browser.new_page(viewport={"width": 960, "height": 540}), server)
    g.join(new_name(), 3, look="hd")
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    g.sleep(1200)
    return g


# the mean light of a tile's top as it is on the screen (the px inside its four corners' box, a px in)
LIGHT = """([x, y, z]) => { const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + a, y + b, z)), k = devicePixelRatio;
  const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 1, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 1, y0 = Math.ceil(c[0][1] * k) + 1, y1 = Math.floor(c[2][1] * k) - 1;
  const d = ctx.getImageData(x0, y0, x1 - x0, y1 - y0).data; let s = 0; for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2]; return s / (d.length / 4); }"""


def settled(g):
    g.sleep(350)
    g.wait("!HdLook.busy")
    g.sleep(250)


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
    At night neither."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(0, -3, ["%"])
        wx, wy = x, y - 3
        for phase, shaded in ((.1, "west"), (.62, "east"), (.9, None)):
            g.rpc("dev_time", phase=phase)
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


def test_a_shadow_keeps_its_px_while_the_land_is_made_again(browser, server):
    """Your own shadow, each frame, while a change of the land makes the land again (its paints wiped, a new set made
    over several frames): as many px of it all along, the shape it had. (A guard: what is drawn each frame over the
    land asks for its paints while the land still shown has its own set, vox_style.js A and B.)"""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.rpc("dev_time", phase=.9)                                           # (night: the shadow under you alone, no cloud, no sun)
        g.wait("Math.abs((clock.phase || 0) - .9) < .02")
        g.stamp(-3, -3, ["T.b", "...", "M.C"])
        for dx, dy in ((3, 2), (-2, -1), (0, 0)):                             # (walked about: the paints are no longer in the order a new land makes them)
            g.rpc("dev_teleport", x=x + dx, y=y + dy, z=0)
            settled(g)
        g.js("""(() => { const p = myPos(), a = HdLook.screenOf(p.x + .5, p.y + .92, topAt(p.x, p.y)), k = devicePixelRatio, X = Math.round(a[0] * k), Y = Math.round(a[1] * k);
          const mid = ctx.getImageData(X, Y, 1, 1).data; window.__sh = []; window.__b0 = HdLook.builds; window.__busy = 0;
          const f = () => { const d = ctx.getImageData(X - 24 * k, Y - 9 * k, 48 * k, 18 * k).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - mid[0]) + Math.abs(d[i + 1] - mid[1]) + Math.abs(d[i + 2] - mid[2]) < 12) n++;
            window.__sh.push(n); if (HdLook.busy) window.__busy++; if (window.__sh.length < 150) requestAnimationFrame(f); };
          requestAnimationFrame(f); return 1; })()""")
        g.sleep(150)
        g.stamp(6, -6, ["M"])                                                 # (a rock, away from you: the land's version changes)
        g.wait("window.__sh.length >= 150", 15000)
        got = g.js("window.__sh")
        assert g.js("HdLook.builds > window.__b0 && window.__busy > 0"), "the land was not made again over frames"
        assert got[0] > 60 and max(got) - min(got) <= 4, (got[0], min(got), max(got))
    finally:
        g.page.close()
