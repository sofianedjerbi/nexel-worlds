"""Being under ground as it is seen (web/js/xray.js, xraycut.js, xrayviews.js, cavelight.js, daylight.js): one view
for a stair under a hill, a tunnel, a room; where the cut ends and its outline; the light in it, by day and by night.
(The dug look itself, and build mode's digging: test_e2e_digging.py; caves under hills: test_e2e_caves.py.)"""

from test_e2e_digging import DRAWN, GREEN_ON_SCREEN, SEEN

# a px of the picture seen through what hides you: of tile (x, y) as drawn at height lv, (ax, ay) art px from its
# corner -> [seen, r, g, b]
PIC = """([x, y, lv, ax, ay]) => { const P = xray.pic, X = x * 16 + ax - P.x, Y = y * 16 - shOf(lv) + ay - P.y;
  if (X < 0 || Y < 0 || X >= P.w || Y >= P.h) return [0, 0, 0, 0];
  return [P.seen[Y * P.w + X], ...Array.from(P.over.getContext('2d').getImageData(X, Y, 1, 1).data).slice(0, 3)]; }"""


# a px of that picture as the light has it (cavelight.js): [is it earth that was cut through, how dark it is, 0 to 1]
LIT = """([x, y, lv, ax, ay]) => { frame(performance.now()); const P = xray.pic, f = (y * 16 - shOf(lv) + ay - P.y) * P.w + x * 16 + ax - P.x;
  return [P.solid[f], +(P.img.data[f * 4 + 3] / 255).toFixed(3)]; }"""


def test_a_stair_dug_under_a_hill_is_a_burrow_in_the_bank_not_floors_lying_on_the_hill(game):
    """doben4's stair, dug west from a pit, under a hill that rises as it goes down ("this is very weird and ugly !"):
    under a hill a view of its own drew each floor alone where it is drawn, tiles south of the stair, squares of earth
    on the hill. "everything should have the same view ! ... an unique 'player is hided, xray on' view": under a hill
    as under the meadow you are seen through what hides you. Behind each floor its wall goes up to the top of the
    land, cut open: the hollow's own back wall, and over it the roof cut through, earth in the shade."""
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(-9, -3, ["." * 10] * 7, levels=["3322110000"] * 7)
    game.stamp(-9, 0, ["." * 10], levels=["ffedcbba00"], roofs=["9976400000"], heads=["2222200000"])
    X = x - 6                                                  # four down, under a hill two high
    game.rpc("dev_teleport", x=X, y=y + 1, z=2)               # on the hill beside it: the hill, whole
    game.wait(f"myAt && myAt.x === {X} && myAt.z === 2", 8000)
    game.wait(DRAWN, 8000); game.sleep(600)
    assert game.js(f"[xray.a, standAt({X}, {y}), hiddenAt({X}, {y})]") == [0, 2, True]
    game.rpc("dev_teleport", x=X, y=y, z=-4)                 # on the stair
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(SEEN, 20000)
    assert game.js(f"[-9, -8, -7, -6, -5, -4].map((d) => seenUnder({x} + d, {y}))") == [-6, -6, -5, -4, -3, None]
    assert game.js(f"[standAt({X}, {y}), hiddenAt({X}, {y}), xray.pic.floor.size]") == [-4, False, 5]
    px = lambda tx, lv, ax, ay: game.js(PIC, [tx, y, lv, ax, ay])
    for tx, floor, top in ((x - 9, -6, 3), (X, -4, 2)):       # behind a floor: its wall, from the top of the land down to it
        for up in range(2, 8 * (top - floor), 6):
            seen, r, g, b = px(tx, floor, 8, -up)
            assert seen and r > g, (tx, up, [seen, r, g, b])    # (earth: no hill showing in it)
    back, roof = game.js(LIT, [X, y, -4, 8, -4]), game.js(LIT, [X, y, -4, 8, -20])   # where you stand: the hollow's back wall, lit by you; the roof over it, cut through: earth, which you do not light
    assert back[0] == 0 and roof[0] == 1 and roof[1] > back[1] + .1, (back, roof)
    assert not game.errors


def test_earth_left_between_two_tunnels_is_cut_earth_not_a_strip_of_meadow(game):
    """Two tunnels side by side, four down, joined at one end: the earth between them hides the far one and is left
    out; where it stood the land as drawn showed, a strip of meadow between two floors, and the nearer tunnel was a
    floor lying on the grass. It is cut level with the floor behind it and shows as that."""
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(1, 0, ["...."], levels=["abcd"])
    game.rpc("dev_stamp", x=x + 5, y=y, rows=["......", ".", "......"], levels=["dddddd", "d", "dddddd"], roofs=["444444", "4", "444444"], heads=["222222", "2", "222222"])
    X = x + 8
    game.rpc("dev_teleport", x=X, y=y, z=-4)                 # in the far one
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000)
    assert game.js(f"[seenUnder({X}, {y}), seenUnder({X}, {y + 1}), seenUnder({X}, {y + 2}), xray.pic.cut.has('{X},{y + 1}')]") == [-4, None, -4, True]
    seen, r, g, b = game.js(PIC, [X, y + 1, -4, 8, 8])
    assert seen and r > g, [seen, r, g, b]
    assert game.js(GREEN_ON_SCREEN, [[X, y, 4], [X, y + 1, 4], [X, y + 2, 4]]) == [0, 0, 0]
    assert not game.errors


# the screen without anybody on it: the mean brightness (r + g + b) of each tile [x, y] where the land at sea level is drawn
BRIGHT = """(tiles) => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
  frame(performance.now()); const S = TS(), [ox, oy] = screenOrigin(S), out = [];
  for (const [x, y] of tiles) { const px = ctx.getImageData(Math.round((ox + x * S) * DPR), Math.round((oy + y * S) * DPR), S * DPR, S * DPR).data; let n = 0;
    for (let i = 0; i < px.length; i += 4) n += px[i] + px[i + 1] + px[i + 2]; out.push(Math.round(n / (px.length / 4))); }
  Object.assign(window, keep); return out; }"""


def test_at_night_a_fire_under_a_roof_lights_nothing_of_the_meadow_over_it(game):
    """Night's lights were drawn where they are on the screen, roof or no roof: a fire in a tunnel lit a ring of the
    meadow over it (and who hid under the ground glowed through it). A light under a roof lights what is under that
    roof: seen through, the picture of the place; hidden, nothing (daylight.js)."""
    game.clear_area(16)
    x, y = game.pos()
    game.stamp(-8, 0, ["........^......."], levels=["abcddddddddddddd"], roofs=["0000444444444444"], heads=["0000222222222222"])
    game.rpc("dev_time", phase=.85)
    game.rpc("dev_teleport", x=x + 7, y=y - 4, z=0)           # on the meadow, away from the fire (it is under (x, y), four down)
    game.wait(f"myAt && myAt.x === {x + 7} && myAt.y === {y - 4}", 8000)
    game.wait(DRAWN, 8000); game.sleep(900)
    assert game.js(f"[combAt({x}, {y}), hiddenAt({x}, {y}), xray.a]") == ["^", True, 0]
    over, beside, far = game.js(BRIGHT, [[x, y], [x, y + 1], [x + 15, y + 1]])
    assert far > 100 and abs(over - far) < 25 and abs(beside - far) < 25, (over, beside, far)   # the meadow over the fire: as dark as the meadow anywhere
    assert not game.errors


def test_where_the_cut_ends_it_has_an_edge_a_line_and_a_shadow_in_from_it(game):
    """"The borders are still abrupt, like cut without separation": the earth cut open stopped square against the
    grass. Where the cut ends against the land in front of it or beside it there is a line, and a shadow three px in
    from it (xraycut.js); none between two floors of the place."""
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(1, 0, ["........"], levels=["abcddddd"], roofs=["00004444"], heads=["00002222"])
    X = x + 6
    game.rpc("dev_teleport", x=X, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000)
    ink, px = game.js("CUT.ink"), lambda *a: game.js(PIC, list(a))
    front, in1, mid = px(X, y, -4, 8, 15), px(X, y, -4, 8, 14), px(X, y, -4, 8, 8)    # the floor's last row, against the meadow in front; a px in; its middle
    assert front[0] and front[1:] == ink and sum(mid[1:]) - sum(in1[1:]) > 30, (front, in1, mid)
    assert px(x + 8, y, -4, 15, 8)[1:] == ink                 # the tunnel's end
    assert px(X, y, -4, 0, 8)[1:] != ink and px(X, y, -4, 15, 8)[1:] != ink            # between two of its floors: nothing
    assert not game.errors


def test_the_outline_goes_round_the_place_itself_and_is_the_usual_view(game):
    """"Top outline is kinda broken. Also make outline the default": the outline was round all that the ground in
    front was drawn over, so a tile out from the cut on every side (the tiles beside the place are in the picture
    with their own edge) and across a stair's wall where the meadow's edge had been. It goes round the place itself,
    as one shape: along the top of its wall, its floor's front, its end; nothing a tile out, nothing across it."""
    assert game.js("opt('above')") == "outline"
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(1, 0, ["........"], levels=["abcddddd"], roofs=["00004444"], heads=["00002222"])
    X = x + 6
    game.rpc("dev_teleport", x=X, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000)
    line = lambda *a: game.js("""([x, y, lv, ax, ay]) => { const P = xray.pic, X = x * 16 + ax - P.x, Y = y * 16 - shOf(lv) + ay - P.y;
      return xrayEdges(P).getContext('2d').getImageData(X, Y, 1, 1).data[3] > 0; }""", list(a))
    assert line(X, y, 0, 8, 0) and line(X, y, -4, 8, 15) and line(x + 8, y, -4, 15, 8)       # the top of its wall, its floor's front, its end
    assert not line(X, y - 1, 0, 8, 0) and not line(X, y - 1, 0, 8, 8) and not line(x + 9, y, -4, 8, 8)   # a tile out: nothing
    assert not line(X, y, -4, 8, 8) and not line(X, y, 0, 8, 12) and not line(x + 2, y, -2, 8, 8) and not line(x + 2, y, 0, 8, 6)   # across it, the stair's wall too: nothing
    # "there shouldn't be a line where player can travel to outside": none where you step off the stair's top step
    # onto the meadow, west of it or in front of it; under the next step there is one (two layers up is a wall)
    assert not line(x + 1, y, -1, 0, 8) and not line(x + 1, y, -1, 8, 15) and line(x + 2, y, -2, 8, 15)
    assert not line(x + 2, y, 0, 8, 0) and not line(x + 2, y, 0, 8, -2)      # round the open stair the land has its own rim: no line under it
    assert not game.errors


def test_light_is_one_model_no_edge_where_a_roof_starts_and_none_through_the_earth(game):
    """"See how lightning is cut ? Uniformise it with a real lightning model, sun outside goes inside etc": the earth
    cut through over a tunnel was a flat shade darker from the roof's edge on, a line down the wall where the roof
    starts; and a fire lit the tunnel beside its own through the earth between them. One model (cavelight.js): the
    sun comes in where the place is open and fades along the way, earth and wall alike; a light goes along the
    tunnels, not through what stands between them."""
    game.clear_area(14)
    x, y = game.pos()
    game.stamp(1, 0, ["...."], levels=["abcd"])
    game.rpc("dev_stamp", x=x + 5, y=y, rows=[".....^..", ".", "........"], levels=["d" * 8, "d", "d" * 8], roofs=["4" * 8, "4", "4" * 8], heads=["2" * 8, "2", "2" * 8])
    game.rpc("dev_teleport", x=x + 4, y=y, z=-4)             # at the foot of the stair, by day
    game.wait(f"myAt && myAt.x === {x + 4} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    lit = lambda *a: game.js(LIT, list(a))
    # the top of the wall, where the roof starts (the stair's last step is open, the next tile is under the roof):
    # its last px under the sky, its first px under the roof, and the earth two and five tiles in
    sky, first, two, five = lit(x + 4, y, 0, 15, 2), lit(x + 5, y, 0, 0, 2), lit(x + 6, y, 0, 8, 2), lit(x + 9, y, 0, 8, 2)
    assert first[0] == 1 and abs(first[1] - sky[1]) < .08 and first[1] < two[1] < five[1] and five[1] > .4, (sky, first, two, five)
    game.rpc("dev_time", phase=.85)                           # by night: the fire, five tiles on in this tunnel
    game.sleep(600)
    near, through = lit(x + 8, y, -4, 8, 8), lit(x + 10, y + 2, -4, 8, 8)     # a floor two tiles from it; the floor of the tunnel beside, straight across the earth from it
    assert near[1] < .3 and through[1] > .5, (near, through)
    assert not game.errors


# the screen without anybody on it: the colour of each art px down a tile's column, ax px across it, from a0 to a1 px
# under its line at sea level -> [[r, g, b]...]
DOWN = """([x, y, ax, a0, a1]) => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
  frame(performance.now()); const S = TS(), [ox, oy] = screenOrigin(S), k = S / 16, out = [];
  for (let ay = a0; ay <= a1; ay++) out.push(Array.from(ctx.getImageData(Math.round((ox + x * S + (ax + .5) * k) * DPR), Math.round((oy + y * S + (ay + .5) * k) * DPR), 1, 1).data).slice(0, 3));
  Object.assign(window, keep); return out; }"""


def test_a_wall_under_a_roof_has_its_bands_where_the_pit_beside_it_has_them(game):
    """"Still got a weird tileset jump", where a stair open to the sky goes in under a roof: the wall cut through had
    its bands on the tiles' lines, the land's own wall has those over the sea's level two px up (a hill's edge is set
    in) and two px of the tile's foot under them, so every line of the wall broke where the roof starts. And at that
    corner two px of the cut's ink went up into the pit's rim, and the earth's dark started at half its strength."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, 0, ["........"], levels=["abcddddd"], roofs=["00004444"], heads=["00002222"])
    X = x + 5                                                # (the first tile under the roof; the one west of it is as deep, open to the sky)
    game.rpc("dev_teleport", x=X, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000)
    lines = lambda px: [r for r in range(1, 32) if sum(px[r]) < sum(px[r - 1]) - 15 and sum(px[r]) < sum(px[r + 1]) - 15]   # (the rows darker than those over and under them)
    assert lines(game.js(DOWN, [x + 4, y, 8, 0, 32])) == [5, 15, 23, 31]          # the land's own wall, four layers down
    assert lines(game.js(DOWN, [X, y, 8, 0, 32])) == [5, 15, 23, 31]              # the wall cut through: the same rows (they were 7, 15, 23, 31)
    assert lines(game.js(DOWN, [X, y, 1, 0, 32])) == [5, 15, 23, 31]              # ...right beside the pit too
    line = lambda *a: game.js("([x, y, ax, ay]) => { const P = xray.pic; return P.line[(y * 16 + ay - P.y) * P.w + x * 16 + ax - P.x]; }", list(a))
    assert line(X, y, 8, 0) and not line(X, y, 8, -1)                             # the cut starts on its tile's line, under a roof
    assert not line(x + 4, y, 15, -2) and not line(x + 4, y, 15, -1)              # no ink up the side of the pit's wall where it starts, two px over that line
    for r, g, b in game.js(DOWN, [X, y, 0, -2, -1]): assert g > r + 12            # the tile behind the roof: grass to its corner
    assert game.js(LIT, [X, y, 0, 0, 4])[1] < .04 < .06 < game.js(LIT, [X, y, 0, 8, 4])[1]   # the earth's dark: from next to nothing where the roof starts (it was half of it there)
    assert not game.errors

