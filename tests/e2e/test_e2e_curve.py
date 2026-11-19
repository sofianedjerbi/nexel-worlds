"""The curved world (web/js/curve.js, the engine's vox_curve.js and vox_sky.js): the ground bends away to a horizon
in the upper part of the screen, with a sky over it; where you stand nothing changes. The settings' "Curved world":
off, the flat picture as ever (what every other file of these tests looks at)."""
import pytest

# where a tile is drawn, as the game's own function says: [its middle x, its middle y, its top, its foot] (px)
PROJ = """([x, y]) => { const S = TS(), [ox, oy] = screenOrigin(S), up = liftAt(x, y), top = Curve.y(oy + y * S, up), foot = Curve.y(oy + (y + 1) * S, up);
  return [ox + x * S + S / 2, (top + foot) / 2, top, foot]; }"""
FLAT = """([x, y]) => { const S = TS(), [ox, oy] = screenOrigin(S), top = oy + y * S - liftAt(x, y); return [ox + x * S + S / 2, top + S / 2, top, top + S]; }"""
PIXEL = """([x, y]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const d = ctx.getImageData(Math.round(x * DPR), Math.round(y * DPR), 1, 1).data; ok([d[0], d[1], d[2]]); })))"""
green = lambda c: c[1] > c[0] + 15 and c[1] > c[2] + 15
earth = lambda c: c[0] > c[1] + 15 and c[0] > c[2] + 15
close = lambda a, b: all(abs(p - q) < 1e-6 for p, q in zip(a, b))


def curved(game, mode="near"):
    game.js(f"(() => {{ Curve.force = '{mode}'; return 1; }})()")      # (these tests' pages come with it off: game.py)
    game.wait("Curve.on" if mode != "off" else "!Curve.on")
    game.wait("(() => { const b = blockOf(myPos().x, myPos().y); return Voxels.made(b); })() && dirtyTiles.length === 0", timeout=15000)
    if mode != "off":
        game.wait("Math.abs(Curve.line - Curve.c.line) < 1")     # (the sky's line has glided to the land's edge)
    game.sleep(300)


def test_off_the_picture_is_the_flat_one(game):
    """The setting off: every row where it was, far north too, and a click there finds its tile."""
    game.clear_area(10)
    x, y = game.pos()
    curved(game, "off")
    for dx, dy in ((0, 0), (2, 3), (-3, -5), (1, -6)):
        assert close(game.js(PROJ, [x + dx, y + dy]), game.js(FLAT, [x + dx, y + dy]))
        px, py, _, _ = game.js(FLAT, [x + dx, y + dy])
        got = game.js("([a, b]) => tileAtScreen(a, b)", [px, py])
        assert (got["x"], got["y"]) == (x + dx, y + dy)
    assert green(game.js(PIXEL, [600, 4]))                       # no sky: the meadow goes to the top of the picture


def test_on_where_you_stand_nothing_moves_and_far_rows_go_up_to_a_horizon(game):
    """Curved: your own row and all that is south of it are where the flat picture has them, to the px; rows north
    of where the bend starts are closer and closer together and never over the horizon line."""
    game.clear_area(10)
    x, y = game.pos()
    curved(game)
    c = game.js("Curve.c")
    assert 0 < c["yh"] < c["y0"] < 400                           # (the horizon in the upper part of the screen; the bend starts over you)
    for dx, dy in ((0, 0), (1, 0), (-2, 1), (3, 4), (0, 5)):
        assert close(game.js(PROJ, [x + dx, y + dy]), game.js(FLAT, [x + dx, y + dy])), (dx, dy)
        px, py, _, _ = game.js(FLAT, [x + dx, y + dy])
        got = game.js("([a, b]) => tileAtScreen(a, b)", [px, py])
        assert (got["x"], got["y"]) == (x + dx, y + dy)
    tall = [game.js(PROJ, [x, y - k]) for k in range(1, 5)]      # (four rows north: before the horizon, Near)
    sizes = [foot - top for _, _, top, foot in tall]
    assert all(a >= b for a, b in zip(sizes, sizes[1:])) and sizes[0] > 50 and sizes[-1] < 30, sizes
    assert all(top >= c["yh"] - 1e-6 for _, _, top, _ in tall)


def test_a_click_in_the_bend_finds_the_tile_drawn_there(game):
    """Flat land far north, then a hill stamped there: the tile under a click is the one drawn under it, on its top
    and on its front; and the GPU has drawn the land where the game's own function says it is."""
    game.clear_area(10)
    x, y = game.pos()
    curved(game, "far")
    for dx, dy in ((0, -3), (2, -4), (-4, -4), (5, -2)):
        px, py, top, foot = game.js(PROJ, [x + dx, y + dy])
        for at in (py, top + 1, foot - 1):
            got = game.js("([a, b]) => tileAtScreen(a, b)", [px, at])
            assert (got["x"], got["y"]) == (x + dx, y + dy), (dx, dy, at, got)
    game.stamp(-2, -5, ["....."] * 2, levels=["33333"] * 2)
    game.wait("dirtyTiles.length === 0")
    game.sleep(500)
    for dx, dy in ((0, -4), (1, -5), (-2, -4)):
        px, py, top, foot = game.js(PROJ, [x + dx, y + dy])
        got = game.js("([a, b]) => tileAtScreen(a, b)", [px, py])
        assert (got["x"], got["y"]) == (x + dx, y + dy), (dx, dy, got)
        assert green(game.js(PIXEL, [px, top + (foot - top) * .25]))      # its top, drawn there (its far part: the near part is its lip, earth)
    px, py, top, foot = game.js(PROJ, [x, y - 4])
    front = foot + 6 * 4                                         # the front of the hill's near row: three levels of earth under its edge
    got = game.js("([a, b]) => tileAtScreen(a, b)", [px, front])
    assert (got["x"], got["y"]) == (x, y - 4), got
    assert earth(game.js(PIXEL, [px, front])), game.js(PIXEL, [px, front])
    px, py, top, foot = game.js(PROJ, [x + 4, y - 4])            # and the meadow beside it is found as itself
    got = game.js("([a, b]) => tileAtScreen(a, b)", [px, py])
    assert (got["x"], got["y"]) == (x + 4, y - 4)


def test_the_sky_is_over_the_horizon_and_the_land_under_it_with_nothing_between(game):
    game.clear_area(12)
    curved(game)
    line = game.js("Curve.line")
    sky = game.js(PIXEL, [300, 6])
    assert sky[2] > sky[0] + 20 and sky[2] > 150, sky            # blue, at the top of the picture
    for px in (100, 500, 900, 1150):
        c = game.js(PIXEL, [px, line + 30])
        assert c[1] > c[2] + 40 and c[1] > 150, (px, line, c)    # the meadow, just under the line (its grass, or a paler tuft of it)
    # what the land leaves open under the line, painted magenta by the sky (its audit): none of it is seen
    game.js("(() => { Curve.audit = true; return 1; })()")
    game.sleep(300)
    holes = game.js("""() => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const d = ctx.getImageData(0, 0, cv.width, cv.height).data; let n = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i] > 240 && d[i + 1] < 20 && d[i + 2] > 240) n++; ok(n); })))""")
    assert holes == 0
    # (and the audit does paint where there is no land: the same view drawn with none)
    bare = game.js("""() => { const S = TS(), [ox, oy] = screenOrigin(S), el = Voxels.engine.draw({w: W, h: H, pw: cv.width, ph: cv.height, ox, oy, tile: S, row: cam.y, chunks: [], light: [1, 1, 1], clear: [0, 0, 0], water: null, window: null, curve: Curve.c, sky: Curve.sky(0)});
      const c = document.createElement('canvas'); c.width = el.width; c.height = el.height; const g = c.getContext('2d'); g.drawImage(el, 0, 0); const d = g.getImageData(c.width / 2, c.height / 2, 1, 1).data; return [d[0], d[1], d[2]]; }""")
    assert bare == [255, 0, 255], bare
    game.js("(() => { Curve.audit = false; return 1; })()")


def test_a_body_far_north_stands_on_the_bent_land(game):
    """A cow five tiles north: its feet under the horizon line and over the line where the bend starts, on its own
    tile as that tile is drawn, lower than the flat picture had it; not smaller."""
    game.clear_area(10)
    x, y = game.pos()
    game.spawn("cow", 0, -3, still=9999)
    game.tick(2)
    curved(game, "far")
    px, py, top, foot = game.js(PROJ, [x, y - 3])
    got = game.js("""() => { const p = [...ents.values()].find((q) => q.e && q.e.kind === 'cow'), S = TS(), [ox, oy] = screenOrigin(S), sy = Curve.sy(oy, S);
      return {y: bodyY(p, sy), flat: oy + p.y * S - liftOf(p) - STAND * zoom, c: Curve.c, row: p.y}; }""")
    c, feet = got["c"], got["y"] + 16 * 4                        # (its feet: a tile under where its picture starts)
    assert c["yh"] < feet < c["y0"], got
    assert top - 1 <= feet <= foot + 1, (got, top, foot)         # on its own tile, as that tile is drawn
    assert got["y"] > got["flat"] + 15, got                      # (the flat picture had it higher up: its row is nearer now)
    # and it is drawn there, as big as ever: a cow's pale body somewhere in its tile's column over its feet
    seen = game.js("""([x, y]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const d = ctx.getImageData(Math.round((x - 40) * DPR), Math.round((y - 70) * DPR), Math.round(80 * DPR), Math.round(80 * DPR)).data; let n = 0;
      for (let i = 0; i < d.length; i += 4) if (!(d[i + 1] > d[i] + 15 && d[i + 1] > d[i + 2] + 15)) n++; ok(n / (DPR * DPR)); })))""", [px, foot])
    assert seen > 600, seen                                      # (px that are not meadow: its body, 4 px an art px)


def test_curved_world_is_a_setting_on_the_picture_page_far_unless_chosen_otherwise(game):
    """The settings' "Curved world": Off, Near or Far on the Picture page, Far by default, and what it says is what
    is drawn: Far shows more land before the horizon than Near, Off none of the bend."""
    assert game.js("OPT_DEFAULT.curve") == "far" and game.js("opt('curve')") == "far"
    assert game.js("MENU_PAGES.find((p) => p[0] === 'Picture')[1].find((r) => r.name === 'Curved world').list.map((q) => q[0])") == ["off", "near", "far"]
    game.js("(() => { Curve.force = null; return 1; })()")       # (the setting decides, not the page's address)
    game.wait("Curve.on")
    far = game.js("[Curve.c.yh, VoxCurve.edge(Curve.c)]")
    game.js("setOpt('curve', 'near')")
    game.wait(f"Curve.on && Curve.c.yh > {far[0]} + 20")         # Near: the horizon lower down the screen
    assert game.js("VoxCurve.edge(Curve.c)") > far[1] + 60       # ...and less ground before it (px of the flat picture)
    game.js("setOpt('curve', 'off')")
    game.wait("!Curve.on")
    game.js("setOpt('curve', 'far')")
    game.wait("Curve.on")


# ---- with the land's sides, models and the cut (the merge): Far, the default, where the bend holds the most

# the colour of the canvas at an art px (ax, ay) of the tile (x, y) at a height of `up` art px, as the game's own
# function places it (a row and a height: vox_curve.js)
AT = """([x, y, ax, ay, up]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const S = TS(), [ox, oy] = screenOrigin(S);
  const d = ctx.getImageData(Math.round((ox + x * S + (ax + .5) * zoom) * DPR), Math.round(Curve.y(oy + (y + (ay + .5) / 16) * S, up * zoom) * DPR), 1, 1).data; ok([d[0], d[1], d[2]]); })))"""
alike = lambda a, b, by=14: all(abs(p - q) <= by for p, q in zip(a, b))


def test_a_bank_bends_with_the_land(game):
    """A hill three high has banks down its west wall, a level a strip. The same hill far north in the bend: each
    strip is where the function says its level is, in the colours of the same hill beside you; no gap in between."""
    game.clear_area(10)
    x, y = game.pos()
    curved(game, "far")
    for dy in (2, -5):                                           # one in the flat part, south of you; one far in the bend
        game.stamp(2, dy, ["..."] * 2, levels=["333"] * 2)
    game.wait("dirtyTiles.length === 0")
    game.sleep(600)
    assert game.js("Voxels.engine.sides") > 0
    assert game.js(f"Curve.y(screenOrigin()[1] + ({y} - 4) * TS(), 0) > screenOrigin()[1] + ({y} - 4) * TS() + 30")      # (it is in the bend: far lower down the screen than flat)
    # in the hill's west column, its second row: its top (its far part: the near part is its lip); the bank of its second level (the first 2 px of the tile,
    # 16 art px up); the bank of its first level (the 2 px west of the tile, 8 up); the meadow west of that
    spots = [(8, 3, 24), (0, 8, 16), (1, 8, 16), (-2, 8, 8), (-1, 8, 8), (-6, 8, 0)]
    near_, far_ = [[game.js(AT, [x + 2, y + dy + 1, ax, ay, up]) for ax, ay, up in spots] for dy in (2, -5)]
    assert green(near_[0]) and green(far_[0]), (near_[0], far_[0])      # its top (its grass, by a tuft or not)
    for spot, a, b in list(zip(spots, near_, far_))[1:5]:        # (not the meadow's px: a tuft of grass may lie on one and not the other)
        assert alike(a, b), (spot, a, b)
    assert not alike(near_[1], near_[0]) or not alike(near_[3], near_[5])      # (a bank is not the grass's colour: the strips are there to be told)


def test_a_bridge_far_north_bends_with_the_water_and_who_is_on_it_stands_on_its_deck(game):
    """A bridge in the bend: its deck is drawn four px over the water's row as that row is bent (its planks under
    the px the function gives), the water north and south of it is water, and a body on it stands on the deck."""
    from test_e2e_models import POND, PLANK
    game.clear_area(10)
    x, y = game.pos()
    curved(game, "far")
    game.stamp(-4, -5, POND)
    game.wait("dirtyTiles.length === 0")
    game.sleep(800)
    by = y - 3                                                   # the bridge's row
    assert game.js("Voxels.engine.models") > 40 and game.js(f"liftAt({x}, {by}) / zoom") == 4
    deck = [game.js(AT, [x + dx, by, 1, 8, 4]) for dx in (-2, 0, 2)]
    assert all(alike(c, PLANK) for c in deck), deck              # its planks, where a point 4 px up on that row is drawn
    for dy, ay in ((-1, 3), (1, 10)):                            # the water north and south of it, not planks
        w = game.js(AT, [x, by + dy, 8, ay, 0])
        assert min(w) > 150 and not alike(w, PLANK, 30), (dy, w)   # (a shallow pond: pale over its sand)
    game.spawn("cow", 0, -3, still=9999)
    game.tick(2)
    game.sleep(500)
    got = game.js("""() => { const p = [...ents.values()].find((q) => q.e && q.e.kind === 'cow'), S = TS(), [ox, oy] = screenOrigin(S), sy = Curve.sy(oy, S);
      return {lift: liftOf(p) / zoom, y: bodyY(p, sy), deck: Curve.y(oy + (p.y + 13 / 16) * S, 4 * zoom), water: Curve.y(oy + (p.y + 13 / 16) * S, 0)}; }""")
    assert got["lift"] == 4
    feet = got["y"] + 16 * 4                                     # (a tile under where its picture starts)
    assert abs(feet - got["deck"]) <= 1 and got["water"] - feet >= 10, got      # on the deck (four art px over the water), not in the water


def test_a_tunnel_that_runs_north_into_the_bend_is_cut_open_to_its_floor_and_a_click_finds_what_is_drawn(game):
    """You in a tunnel under a hill four high that runs north: the land over it is cut open (voxels.js), in the bend
    too: its floor is drawn where the function puts a point of that tile at the floor's height, darker than the
    hill's top beside it; a click there finds the tunnel's tile, a click on the hill beside it the hill, and a click
    on the meadow further north than the hill that tile."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(-2, -12, ["....."] * 11, levels=["44444"] * 11)
    game.stamp(0, -11, ["."] * 10, levels=["0"] * 10, roofs=["4"] * 10, heads=["2"] * 10)
    game.rpc("dev_teleport", x=x, y=y - 2, z=0)
    game.wait(f"myPos().y === {y - 2}")
    curved(game, "far")
    game.wait("xray.a > .95 && xray.pic && xray.pic.cut.size > 5", timeout=8000)
    far = y - 6                                                  # four tiles north of you, in the tunnel
    assert game.js(f"xray.pic.cut.has('{x},{far}')")
    assert game.js(f"Curve.y(screenOrigin()[1] + {far} * TS(), 0) > screenOrigin()[1] + {far} * TS() + 60")      # (in the bend)
    floor, top = game.js(AT, [x, far, 8, 8, 0]), game.js(AT, [x + 2, far, 8, 8, 32])
    assert sum(floor) < sum(top) - 60, (floor, top)              # the floor under its roof's dark, not the hill's lit top
    assert top[1] > top[0] and top[1] > top[2]                   # (the hill's top beside it: grass, at its own height)
    click = """([x, y, up]) => { const S = TS(), [ox, oy] = screenOrigin(S), q = tileAtScreen(ox + x * S + S / 2, Curve.y(oy + (y + .5) * S, up * zoom)); return [q.x, q.y]; }"""
    assert game.js(click, [x, far, 0]) == [x, far]               # the tunnel's floor
    assert game.js(click, [x + 2, far, 32]) == [x + 2, far]      # the hill beside it
    assert game.js(click, [x + 5, y - 7, 0]) == [x + 5, y - 7]   # the meadow beside the hill, further north still


# ---- a horizon, always ("i dont see the horizon at all": on a mountain's side the land climbed the screen as fast as
# the bend brought it down). The roll is a square of the distance: every slope has its horizon (vox_curve.js).

# is this px the sky's (its blue, a cloud's white, the sun) and not land (grass, stone, earth)?
sky_px = lambda c: c[2] > c[0] + 25 or min(c) > 235
TOP = """() => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const out = [];
  for (let i = 1; i < 12; i++) for (const y of [3, 12]) { const d = ctx.getImageData(Math.round(W * i / 12 * DPR), y * DPR, 1, 1).data; out.push([d[0], d[1], d[2]]); } ok(out); })))"""


@pytest.mark.parametrize("per", [1, 2])
def test_a_staircase_that_rises_north_for_forty_rows_has_its_horizon_and_the_sky_over_it(game, per):
    """Terraces going up to the north, a level every row (or every two), forty rows: the top of the screen is the
    sky, not land, Near and Far."""
    lv = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    game.stamp(-20, -41, ["." * 41] * 40, levels=[lv[min(35, (40 - j) // per)] * 41 for j in range(40)])
    for m in ("far", "near"):
        curved(game, m)
        game.wait("arrivingNow === false")
        got = game.js(TOP)
        assert all(sky_px(c) for c in got), (m, per, got)


def test_on_the_mountain_a_new_player_wakes_on_there_is_a_horizon(browser, tmp_path_factory):
    """Seed 12 wakes you by a terraced mountain. On its side the top of the screen is the sky, Near and Far (the
    staircase above is the land rising north)."""
    import socket, subprocess, sys, time
    from conftest import ROOT, open_game
    with socket.socket() as k:
        k.bind(("127.0.0.1", 0)); port = k.getsockname()[1]
    proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", str(tmp_path_factory.mktemp("saves12")), "--world", "e2e12", "--port", str(port), "--seed", "12", "--dev"],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=.2).close(); break
            except OSError:
                time.sleep(.1)
        g = open_game(browser, f"http://127.0.0.1:{port}", zoom=3)
        # (where a new player wakes is at its foot: on to its side, three levels up)
        spot = g.js("""() => { const p = myPos(); for (let r = 0; r < 28; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) { const x = p.x + dx, y = p.y + dy, t = topAt(x, y);
          if (Math.max(Math.abs(dx), Math.abs(dy)) === r && tile(x, y) && tile(x, y - 6) && t >= 3 && !wet(gndAt(x, y))) return [x, y, t]; } return null; }""")
        assert spot, "no mountain round the spawn"
        g.rpc("dev_teleport", x=spot[0], y=spot[1], z=spot[2])
        g.wait(f"myPos().x === {spot[0]} && myPos().y === {spot[1]} && cam.lift > 0 && !arrivingNow", timeout=15000)
        for m in ("far", "near"):
            curved(g, m)
            got = g.js(TOP)
            assert sum(sky_px(c) for c in got) >= len(got) - 4, (m, got)      # (but for where a far height still stands over the line)
        g.page.close()
    finally:
        proc.terminate()


def test_a_click_on_a_far_body_finds_the_body_not_the_tile_behind_its_head(game):
    """A cow three tiles north, in the roll: its picture is as big as ever on rows that are closer together, so its
    head is drawn over the tile behind it. A click on its head means the cow, as a click on its tile does."""
    game.clear_area(10)
    x, y = game.pos()
    game.spawn("cow", 2, -3, still=9999)
    game.tick(2)
    curved(game, "far")
    head = game.js("""() => { const p = [...ents.values()].find((q) => q.e && q.e.kind === 'cow'), S = TS(), [ox, oy] = screenOrigin(S), sy = Curve.sy(oy, S);
      return [ox + p.x * S + S / 2, bodyY(p, sy) + 3 * zoom, p.x, p.y]; }""")
    got = game.js("([a, b]) => tileAtScreen(a, b)", head[:2])
    assert (got["x"], got["y"]) == (head[2], head[3]), (got, head)
    assert game.js(f"VoxCurve.y(Curve.c, screenOrigin()[1] + {head[3]} * TS(), 0)") > head[1]      # (the px is over the cow's own tile as that tile is drawn: behind it)
    game.flat()
    flat = game.js("([a, b]) => tileAtScreen(a, b)", [head[0], game.js(f"screenOrigin()[1] + {head[3]} * TS() + 8")])
    assert (flat["x"], flat["y"]) == (head[2], head[3])          # (flat: its tile says it, as ever)
