"""Digging down in build mode (web/js/build.js, keyhole.js, tiles.js). "depth visualisation is unintuitive", and of
five mockups the user chose "Earth and a keyhole": dug ground is earth, a shade darker a layer down; where the ground
hides the cursor only its own column is seen through; beside it, how far down it is. By keys: Q sinks the cursor a
layer into the ground, E brings it back, X digs the room to stand there: a way down is a tunnel, a step at a time."""

GRASS = 0xff70d4c0                                             # (the meadow's green, #c0d470, as a block's px has it)
GREEN = f"""([x, y, rows, cols]) => {{ const b = blockOf(x, y), o = (y - b.by * B) * 16 * BW + (x - b.bx * B) * 16; let n = 0;
  for (const j of rows) for (const i of cols) if (b.px[o + j * BW + i] === {GRASS}) n++; return n; }}"""
DRAWN = "dirtyTiles.length === 0"


def test_q_sinks_the_cursor_a_layer_and_x_digs_a_way_down_a_step_at_a_time(game):
    """On solid ground Q did nothing but say "floor -1" (it counted storeys); now each Q is a layer into the ground,
    said beside the cursor and in the corner. There X digs the room to stand in, and what is over it stays: a way down
    is dug a step at a time, a tunnel ("like minecraft ... this enforce me to dig huge columns": it dug every layer
    over the cursor). Where no air is beside it, it says so."""
    game.clear_area(8)
    game.give(pickaxe=1)
    x, y = game.pos()
    game.press("ArrowDown", 200)                              # (facing south: the cursor starts on the tile in front)
    game.press("b")
    rows = lambda: {r[0]: r[1:] for r in game.js("Build.rows()")}
    assert game.js("Build.level()") == 0 and rows()["Q E"][0] == "A layer down, up" and rows()["X"][0] == "Dig a hole"
    for depth in (1, 2, 3):
        game.press("q", 120)
        assert game.js("Build.level()") == -depth and rows()["B"][0] == f"BUILD · -{depth} · leave"
    assert rows()["X"] == ["Dig the step before it first", "bad"]       # (three down, beside you: shut in)
    game.wait("Keyhole.shown", 3000)                           # (in the ground: its column, faint, down to the cursor)
    game.press("x")
    assert game.js("Build.S.plans.size") == 0
    game.press("e", 120); game.press("e", 120)
    for k in range(3):                                         # a step down a tile, three tiles south
        if k:
            game.press("ArrowDown", 120); game.press("q", 120)
        below = game.js("Build.level() - myAt.z")             # (said from where you stand: you go down it as it is dug)
        assert game.js("Build.level()") == -1 - k and below < 0 and rows()["X"][0] == f"Dig a way to {below}"
        game.press("x")
        game.wait(f"surfacesAt({x}, {y + 1 + k})[0] === {-1 - k} && Build.S.plans.size === 0", 30000)
    assert game.js(f"surfacesAt({x}, {y + 3})") == [-3, 0]   # the third step: under a roof, the land over it left
    assert game.js("Build.level()") == -3 and game.inv("dirt") == 2 and game.inv("stone") == 3    # (under sea level: stone)
    game.press("b")
    assert not game.errors


def test_a_dug_floor_is_earth_with_no_grass_at_the_foot_of_its_walls(game):
    """A hole three deep had a grass floor and grass lips: it looked like a raised table; and the grass of the ground
    round it showed in a line at the foot of each wall ("weird lines in the middle")."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(-1, 2, ["..."] * 3, levels=["ccc"] * 3)      # a pit three deep (x-1..x+1, y+2..y+4)
    game.stamp(3, -2, ["...."], levels=["abcd"])            # a stair dug down, east
    game.wait(DRAWN, 8000); game.sleep(300)
    green = lambda dx, dy, rows=range(16), cols=range(16): game.js(GREEN, [x + dx, y + dy, list(rows), list(cols)])
    assert [green(0, 3), green(0, 4)] == [0, 0]               # the pit's floor: earth
    assert green(0, 1, [14, 15]) == 0                          # the ground north of it: no grass under its wall's foot
    assert green(2, -2, range(2, 14), [14, 15]) == 0 and green(3, -2) == 0     # west of the first step, past its wall's side; the step
    game.sleep(200)
    assert not game.errors


def test_the_keyhole_shows_the_cursor_where_the_ground_in_front_hides_it(game):
    """Down a hole the grass in front is drawn over the floor: the cursor's own tile is seen through, and no more (the
    x-ray circle that went round it is yours alone); on the ground, where nothing hides it, there is none."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(-1, 2, ["..."] * 3, levels=["ccc"] * 3)
    game.wait(DRAWN, 8000)
    game.press("b")
    game.js(f"Build.S.at = {{x: {x}, y: {y + 4}}}")           # the pit's south row: under the grass in front
    assert game.js("Build.level()") == -3
    game.wait("Keyhole.shown", 3000)
    assert game.js("xray.a") < .1
    game.js(f"Build.S.at = {{x: {x + 3}, y: {y}}}")
    game.wait("!Keyhole.shown", 3000)
    game.press("b")
    assert not game.errors


SEEN = "xray.a > .95 && !xray.job && xray.pic && xray.pic.any > 0"
# the screen without anybody on it: in each of the tiles [x, y, depth] as drawn, how many px are greener than earth
GREEN_ON_SCREEN = """(tiles) => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
  frame(performance.now()); const S = TS(), [ox, oy] = screenOrigin(S), out = [];
  for (const [x, y, d] of tiles) { const px = ctx.getImageData(Math.round((ox + x * S) * DPR), Math.round((oy + y * S + shOf(d) * zoom) * DPR), S * DPR, S * DPR).data; let n = 0;
    for (let i = 0; i < px.length; i += 4) if (px[i + 1] > px[i] + 12) n++; out.push(n); }
  Object.assign(window, keep); return out; }"""


def test_a_stair_dug_down_is_cut_square_and_seen_whole_with_no_gap_as_you_walk_it(game):
    """A stair dug east, a tile wide. Each step had a dark bar down its side and a green line beside it ("still got the
    weird green line issue"): the bar was the rim of a hill, drawn on a dug step; the line, a gap two px wide in the
    picture of the stair seen through the meadow in front, where the step's rounded shape ended. Dug ground is cut
    square: a step is all of its tile. And going down, it flashed at every step ("when going down/up blocks it
    flashes"): the steps two behind you were out of what is seen through; two pictures were put on the land each
    faint, which showed between them. The whole stair stays seen; the pictures are added up before they are drawn."""
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(1, 0, ["......"], levels=["abcdef"])
    game.rpc("dev_teleport", x=x + 4, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {x + 4} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000)
    even = game.js(f"""() => {{ const out = []; for (let k = 1; k <= 6; k++) {{ const b = blockOf({x} + k, {y}), o = ({y} - b.by * B) * 16 * BW + ({x} + k - b.bx * B) * 16, sum = [0, 0];
      for (let j = 0; j < 16; j++) for (let i = 1; i < 14; i++) if (i < 7 || i > 8) {{ const v = b.px[o + j * BW + i]; sum[i < 7 ? 0 : 1] += (v & 255) + (v >> 8 & 255) + (v >> 16 & 255); }}
      out.push(sum[1] / sum[0] * 6 / 5 > .95); }} return out; }}""")
    assert even == [True] * 6                                  # each step: earth all over its tile, no dark rim down its lower side
    assert game.js(GREEN_ON_SCREEN, [[x + k, y, k] for k in range(1, 7)]) == [0] * 6     # seen whole: no meadow in any of them
    # stepping off the step three down (your height is already the next one's): the steps over you are still of the place
    assert game.js(f"[1, 2, 3, 4, 5, 6].every((k) => xrayPlace({x + 3}, {y}, -4).z.get(({x} + k) + ',' + {y}) === -k)")
    # a picture coming over the one before, half way: the two make a whole one
    alpha = game.js("""() => { XRAY.turn = 1e9; xray.old = xray.pic; xray.mix = .5; frame(performance.now()); const P = xray.pic, f = P.seen.indexOf(1);
      const a = xray.cw.getContext('2d').getImageData(f % P.w, f / P.w | 0, 1, 1).data[3]; XRAY.turn = .12; xray.old = null; xray.mix = 1; return a; }""")
    assert alpha >= 253
    assert not game.errors


def test_a_tunnel_keeps_its_roof_from_above_and_is_seen_through_it_from_inside(game):
    """doben4 at the end of a stair, eight down under a roof left at ground level: a view of its own for caves drew its
    floor four tiles south of its stair, on the grass ("dauben is completely buried and appear here... the underground view is
    buggy as hell"); then, drawn open for good, who walked over a tunnel stood at its bottom. A hollow dug under the
    ground is the ground over it, from above; in it you are seen through that ground and the ground in front, as in a
    hole: you, its floor, the stair you came down."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(1, 0, ["........"], levels=["abcddddd"], roofs=["00004444"], heads=["00002222"])
    X = x + 6
    state = f"""(() => {{ const p = ents.get('agent' + myId); return [levelAt({X}, {y}), standAt({X}, {y}), hiddenAt({X}, {y}), xray.a > .95, unseen(p), xrayShows(p) > .9, xrayOverBody(p), liftOf(p) / zoom]; }})()"""
    game.rpc("dev_teleport", x=X, y=y, z=0)                  # walking over it
    game.wait(f"myAt && myAt.x === {X} && myAt.z === 0", 8000)
    game.wait(DRAWN, 8000); game.sleep(600)
    assert game.js(state) == [0, 0, True, False, False, False, 0, 0]
    assert game.js(GREEN_ON_SCREEN, [[X, y, 0]])[0] > 200      # (the meadow, whole)
    game.rpc("dev_teleport", x=X, y=y, z=-4)                 # in it
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(SEEN, 20000)
    assert game.js(state) == [0, -4, False, True, False, True, 0, -32]
    assert game.js(f"[seenUnder({X}, {y}), seenUnder({X - 1}, {y}), seenUnder({X}, {y + 1}), xrayGone({X}, {y + 1})]") == [-4, -4, None, True]
    assert game.js(GREEN_ON_SCREEN, [[X, y, 4], [X - 1, y, 4], [x + 3, y, 3]]) == [0, 0, 0]      # its floor where you stand, beside you, the stair down to it
    assert not game.errors


def test_under_ground_you_see_what_light_shows_a_fire_however_far(game):
    """"underground vision should display as much as player can see, it is player vision. if fire is here, player see
    it, so it should be visible": what was seen of a tunnel stopped four tiles from you, all of it as bright as day
    ("there's no gradient"), and a fire a little further on was not drawn. All of the place on the screen is seen;
    how bright, light says (cavelight.js): daylight a few tiles in from its mouth, you, a fire; the rest dark."""
    game.clear_area(16)
    x, y = game.pos()
    game.stamp(-8, 0, ["............^..."], levels=["abcddddddddddddd"], roofs=["0000444444444444"], heads=["0000222222222222"])
    game.rpc("dev_teleport", x=x - 5, y=y, z=-4)             # at the foot of the stair, the tunnel's mouth
    game.wait(f"myAt && myAt.x === {x - 5} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    fire, mid = x + 4, x                                       # the fire nine tiles from you; between it and you, five tiles in
    assert game.js(f"[combAt({fire}, {y}), seenUnder({fire}, {y}), hiddenAt({fire}, {y}), standAt({fire}, {y})]") == ["^", -4, False, -4]
    dark = f"""(X) => {{ const P = xray.pic, f = ({y} * 16 - shOf(-4) + 8 - P.y) * P.w + X * 16 + 8 - P.x; return [P.under.includes(f), +(P.img.data[f * 4 + 3] / 255).toFixed(2)]; }}"""
    at_mouth, between, by_fire = (game.js(dark, X) for X in (x - 4, mid, fire))
    assert at_mouth[0] and between[0] and by_fire[0]           # (floor under the roof, in the picture)
    assert at_mouth[1] < .15 and by_fire[1] < .1 and between[1] > .25, (at_mouth, between, by_fire)
    assert not game.errors


# a px of the picture seen through what hides you: of tile (x, y) as drawn at height lv, (ax, ay) art px from its
# corner -> [seen, r, g, b]
PIC = """([x, y, lv, ax, ay]) => { const P = xray.pic, X = x * 16 + ax - P.x, Y = y * 16 - shOf(lv) + ay - P.y;
  if (X < 0 || Y < 0 || X >= P.w || Y >= P.h) return [0, 0, 0, 0];
  return [P.seen[Y * P.w + X], ...Array.from(P.over.getContext('2d').getImageData(X, Y, 1, 1).data).slice(0, 3)]; }"""


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
    back, roof = px(x - 5, -3, 8, -12), px(X, -4, 8, -20)     # the same layer of earth: a hollow's back wall; the roof of the next, cut through
    assert back[0] and roof[0] and sum(back[1:]) - sum(roof[1:]) > 40, (back, roof)
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

