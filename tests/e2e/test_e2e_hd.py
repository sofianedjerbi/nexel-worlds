"""The HD look (hd.js, the default Look): the pointer aims at the tile drawn under it, and walking down a stair into
the land (the owner's kind: a trench, then steps under a roof) you are never hidden."""

from conftest import Game, new_name


def hd(browser, server):
    g = Game(browser.new_page(viewport={"width": 960, "height": 540}), server)
    g.join(new_name(), 3, look="hd")
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    g.rest()
    return g


def test_the_pointer_aims_at_the_tile_drawn_under_it(browser, server):
    """Points on the tops of tiles round you, as the HD camera draws them: tileAtScreen names that very tile."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(3, -2, ["..."] * 2, levels=["222"] * 2); g.rest()             # (a raised step too: its top, not the land behind it)
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
        g.stamp(0, -5, ["."] * 5, levels=["5", "4", "3", "2", "1"], roofs=["", "", "6", "6", "6"], heads=["", "", "2", "2", "2"]); g.rest()
        for i in range(5):
            g.rpc("dev_teleport", x=x, y=y - 5 + i, z=5 - i); g.arrive()    # (the cut opens round you in a little over a second)
            seen = g.js("HdLook.catSeen()")
            assert seen > .8, (i, seen, g.js("({u: HdLook.u, pit: HdLook.pit})"))
    finally:
        g.page.close()


# the colour of the screen at a point of the land (x, y: tiles, z: levels), as the HD camera draws it: [r, g, b]
AT = """([x, y, z]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(HdLook.read(Math.round(p[0] * k), Math.round(p[1] * k), 1, 1).data).slice(0, 3); }"""
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
        g.stamp(2, -3, ["%%"]); g.stamp(-4, 2, ["~~~", "~:~", "~~~"]); g.rest()
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
        g.stamp(3, -2, ["..."] * 2, levels=["222"] * 2); g.rest()
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
        g.hour(.3); day = lum(9)
        g.hour(.9); night, near = lum(9), lum(0)
        assert night < .7 * day and near > night + 30, (day, night, near)
    finally:
        g.page.close()


far = lambda a, b: sum(abs(p - q) for p, q in zip(a, b)) > 40
# the colour of the screen `up` art px over a point of the land
UP = """([x, y, z, up]) => { const p = HdLook.screenOf(x, y, z), k = cv.width / innerWidth;
  return Array.from(HdLook.read(Math.round(p[0] * k), Math.round((p[1] - up * zoom) * k), 1, 1).data).slice(0, 3); }"""
# a bed's card (hd_things.js) for a place X art px right of the screen's middle: [its lean, its width, how many of its px are not the sprite's own]
CARD = """([x, y, X]) => { const s = objectSprite('B', x, y, 0), c = HdThings.card('B', x, y, s, X), g = c.canvas.getContext('2d').getImageData(0, 0, c.canvas.width, c.canvas.height).data;
  const q = document.createElement('canvas'); q.width = 16; q.height = 32; const h = q.getContext('2d'); h.drawImage(s[0], s[1], s[2], 16, 32, 0, 0, 16, 32); const d = h.getImageData(0, 0, 16, 32).data;
  let off = 0; if (c.canvas.width === 16) for (let i = 0; i < d.length; i += 4) if (d[i + 3] >= 128 && (d[i] !== g[i] || d[i + 1] !== g[i + 1] || d[i + 2] !== g[i + 2])) off++;
  return [c.lean, c.canvas.width, off, c.y]; }"""


def test_a_bed_is_its_own_picture_px_for_px_with_a_top_a_side_and_a_shadow(browser, server):
    """Furniture was its flat picture stood up on tilted ground; then boxes that squeezed its art. A bed is a card
    (hd_things.js): every px of it is the sprite's own, wherever it is on the screen (it leant off to a side: it read
    as broken); on the screen its foot board and its blanket are there, one over the other, and a shadow lies on the
    ground under it."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        bx, by = x + 1, y - 2
        g.stamp(1, -2, ["B"]); g.rest()
        lean0, w0, off, foot = g.js(CARD, [bx, by, 0])
        assert (lean0, w0, off) == (0, 16, 0)
        assert g.js(CARD, [bx, by, 140])[:3] == [0, 16, 0]
        board, blanket = g.js(UP, [bx + .5, by + foot, 0, 2]), g.js(UP, [bx + .5, by + foot, 0, 9])
        assert not green(board) and far(board, blanket), (board, blanket)
        assert any(b.get("shade") for b in g.js("([x, y]) => HdThings.at(x, y)", [bx, by]))
        shade, meadow = [g.js(AT, [bx + d, by + foot + .12, 0]) for d in (.3, .5, .7)], [g.js(AT, [bx + d, by + 2.6, 0]) for d in (.3, .5, .7)]
        assert max(map(sum, shade)) < max(map(sum, meadow)) - 40, (shade, meadow)
    finally:
        g.page.close()


PUT = """async ([list, stand]) => { const bad = [];
  for (const [x, y, z, item] of list) { const s = stand.find((q) => (q[0] - x) ** 2 + (q[1] - y) ** 2 + ((z - q[2]) * .5) ** 2 <= 6 && !(q[0] === x && q[1] === y));
    await rpc('dev_teleport', {x: s[0], y: s[1], z: s[2]}); const r = await rpc('act', {tool: 'place', args: {x, y, item, z}}); if (!r.ok) bad.push([x, y, z, item, r.detail || r.error]); } return bad; }"""
ROOF = "([x, y]) => (HdThings.at(x, y) || []).some((b) => b.z >= 16)"


def test_a_built_house_has_its_roof_outside_and_is_open_inside(browser, server):
    """Walls, a door, a roof laid block by block (floors.js). From outside the roof is drawn, over walls that stand
    up to it; inside it the roof is open (the game's own rule for what is over your head) and you see the room."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        x0, y0 = x - 1, y - 5
        g.stamp(-1, -5, ["WWWW", "WnnW", "W+WW"])
        g.rpc("dev_give", items={"roof": 12})
        room = [[x0 + 1, y0 + 1, 0], [x0 + 2, y0 + 1, 0]]
        assert g.js(PUT, [[[x0 + i, y0 + j, 3, "roof"] for j in (2, 1, 0) for i in range(4)], room]) == []
        over = [x0 + 1.5, y0 + 1.5, 3]                                      # (a point of the roof's top, over the room)
        g.rpc("dev_teleport", x=x, y=y, z=0); g.arrive()
        out = g.js(AT, over)
        assert g.js(ROOF, [x0 + 1, y0 + 1]) and not green(out), out                # outside: the roof, drawn
        wall = max(b["z"] + b["h"] for b in g.js("([x, y]) => HdThings.at(x, y)", [x0, y0 + 1]) if b["z"] < 16)
        assert wall == 16                                                    # (the wall under it: up to the roof block's underside)
        g.rpc("dev_teleport", x=x0 + 1, y=y0 + 1, z=0); g.arrive()
        inside = g.js(AT, over)
        assert not g.js(ROOF, [x0 + 1, y0 + 1]) and not g.js(ROOF, [x0 + 3, y0 + 2]), "the roof is still there inside"
        assert sum(abs(p - q) for p, q in zip(out, inside)) > 20 and g.js("HdLook.catSeen()") > .8, (out, inside)   # (the roof's wood, then the north wall's planks seen crisp: nothing nearer than ten tiles is under the lens now)
    finally:
        g.page.close()


def test_the_aim_goes_round_the_piece_as_it_is_drawn(browser, server):
    """Pointing at a chest (a card) and at a wall (a box in the land): the aim's corners go round what is drawn, not
    round the old flat picture's place: the chest's own px (14 wide, 11 high), the wall's box (a tile wide, its cap
    over its front)."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(1, -1, ["C"]); g.stamp(-2, -1, ["W"]); g.rest()
        z = g.js("zoom")
        p = g.js("([x, y]) => { const s = objectSprite('C', x, y, 0), c = HdThings.card('C', x, y, s), f = HdLook.screenOf(x + .5, y + c.y, 0); return [f[0], f[1] - 5 * zoom, c.b]; }", [x + 1, y - 1])
        g.page.mouse.move(p[0], p[1]); g.sleep(600)
        r, b = g.js("HdLook.aim"), p[2]
        assert r and abs(r["w"] - (b[2] - b[0] - 1) * z) <= z and abs(r["h"] - (b[3] - b[1] - 1) * z) <= z, (r, b)
        assert r["x"] - z <= p[0] <= r["x"] + r["w"] + z and r["y"] - z <= p[1] <= r["y"] + r["h"] + z, (r, p)
        q = g.js("([x, y]) => HdLook.screenOf(x + .5, y + .6, 1)", [x - 2, y - 1])
        g.page.keyboard.down("Shift"); g.page.mouse.move(q[0] + 1, q[1]); g.page.mouse.move(q[0], q[1]); g.sleep(600)      # (Shift: take it down: the wall itself is aimed at)
        r = g.js("HdLook.aim"); g.page.keyboard.up("Shift")
        assert g.js("([x, y]) => { const a = aimedTile(); return a && a.p.x === x && a.p.y === y; }", [x - 2, y - 1]), "the pointer on a wall's front names the wall"
        assert r and 5 * z <= r["w"] <= 8 * z and 12 * z <= r["h"] <= 22 * z and r["x"] - z <= q[0] <= r["x"] + r["w"] + z, (r, q)
    finally:
        g.page.close()
