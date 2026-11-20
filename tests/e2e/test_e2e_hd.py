"""The HD look (hd.js, the default Look): the pointer aims at the tile drawn under it, and walking down a stair into
the land (the owner's kind: a trench, then steps under a roof) you are never hidden."""

from conftest import Game, new_name


def hd(browser, server):
    g = Game(browser.new_page(viewport={"width": 960, "height": 540}), server)
    g.join(new_name(), 3, look="hd")
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    g.sleep(1200)
    return g


def test_the_pointer_aims_at_the_tile_drawn_under_it(browser, server):
    """Points on the tops of tiles round you, as the HD camera draws them: tileAtScreen names that very tile."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(3, -2, ["..."] * 2, levels=["222"] * 2)             # (a raised step too: its top, not the land behind it)
        g.sleep(1500)
        for dx, dy in [(0, 2), (-3, 1), (2, -1), (4, -2), (-2, -3)]:
            got = g.js("""([x, y]) => { const z = Voxels.host.column(x, y).at(-1), p = HdLook.screenOf(x + .5, y + .5, z);
              return p && tileAtScreen(p[0], p[1]); }""", [x + dx, y + dy])
            assert got and (got["x"], got["y"]) == (x + dx, y + dy), (dx, dy, got)
    finally:
        g.page.close()


def test_walking_down_a_stair_under_a_roof_keeps_you_seen(browser, server):
    """A stair of five steps down to the south, the lower three under the land (a roof two levels over each); at every
    step the cat is on the screen, px for px as it is drawn."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(-1, -6, ["..."] * 6, levels=["666"] * 6)
        g.stamp(0, -5, ["."] * 5, levels=["5", "4", "3", "2", "1"], roofs=["", "", "6", "6", "6"], heads=["", "", "2", "2", "2"])
        g.sleep(1500)
        for i in range(5):
            g.rpc("dev_teleport", x=x, y=y - 5 + i, z=5 - i)
            g.sleep(1800)                                          # (the cut opens round you in a little over a second)
            seen = g.js("HdLook.catSeen()")
            assert seen > .8, (i, seen, g.js("({u: HdLook.u, box: HdLook.box})"))
    finally:
        g.page.close()


# the colour of the screen at a point of the land (x, y: tiles, z: levels), as the HD camera draws it: [r, g, b]
AT = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(ctx.getImageData(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data).slice(0, 3); }"""
green = lambda c: c[1] > c[0] + 20 and c[1] > c[2] + 20


def test_two_walls_side_by_side_touch_and_a_bridge_is_drawn(browser, server):
    """Built walls were a card a tile, drawn px for px: between two neighbours the meadow showed. They stand in the
    land, a tile wide (vox_style.js `flat`): across the join of two, at half their height, no px is the meadow's.
    And a bridge (a model: boxes, models.js) was not drawn at all: its tile is planks, not the water's blue."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        join = [[x + 3 + d / 16, y - 2, 1] for d in range(-4, 5)]    # (the walls' face: the south edge of row y - 3, a level up)
        assert all(green(g.js(AT, p)) for p in join)                 # (the meadow there, before)
        g.stamp(2, -3, ["%%"]); g.stamp(-4, 2, ["~~~", "~:~", "~~~"]); g.sleep(1800)
        seen = [g.js(AT, p) for p in join]
        assert not any(green(c) for c in seen), seen
        top = g.js(f"Voxels.host.waterTop({x - 3}, {y + 3})")
        deck, water = g.js(AT, [x - 2.5, y + 3.5, top]), g.js(AT, [x - 3.5, y + 2.5, top])
        assert water[2] > water[0] + 30 and not deck[2] > deck[0] + 30, (deck, water)
    finally:
        g.page.close()


def test_the_build_cursor_is_on_the_tile_you_point_at(browser, server):
    """Build mode stays in the HD look (it went back to the classic picture): the cursor is the tile under the pointer
    as this camera draws it, on a raised step too, and its mark is drawn round that tile on the screen."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(3, -2, ["..."] * 2, levels=["222"] * 2); g.sleep(1500)
        g.page.keyboard.press("b"); g.sleep(400)
        for dx, dy, z in [(-2, 1, 0), (4, -2, 2), (1, -3, 0)]:
            p = g.js("([x, y, z]) => HdLook.screenOf(x + .5, y + .5, z)", [x + dx, y + dy, z])
            g.page.mouse.move(p[0], p[1]); g.sleep(400)
            on, at, r = g.js("[HdLook.on && Build.on, Build.S.at, Build.S.rect]")
            assert on and (at["x"], at["y"]) == (x + dx, y + dy), (dx, dy, at)
            assert r["x"] - 2 <= p[0] <= r["x"] + r["w"] + 2 and r["y"] - 2 <= p[1] <= r["y"] + r["h"] + 2, (p, r)
    finally:
        g.page.close()


def test_the_night_is_darker_than_the_day_but_for_your_lamp(browser, server):
    """The land was as bright at night as at noon. The hour's light is the game's own (daylight.js): the meadow far
    from you is much darker at night; by you, in your lamp, it is lighter than out there."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        lum = lambda dx: sum(g.js(AT, [x + dx + .5, y + 2.5, 0]))
        g.rpc("dev_time", phase=.3); g.sleep(1500); day = lum(9)
        g.rpc("dev_time", phase=.9); g.sleep(1500); night, near = lum(9), lum(0)
        assert night < .7 * day and near > night + 30, (day, night, near)
    finally:
        g.page.close()
