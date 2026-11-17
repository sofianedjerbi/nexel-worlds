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
    assert rows()["X"] == ["Plan the step before it first", "bad"]      # (three down, beside you: shut in)
    game.wait("Keyhole.shown", 3000)                           # (in the ground: the room X would dig there, faint: a floor, two layers of wall)
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


def test_a_way_down_is_planned_ahead_each_step_where_the_one_before_it_will_have_made_room(game):
    """"I dig down my stair, I get stopped 2 block on front of me because it is out of range. I'd like to not be
    blocked if the block I want to destroy will be accessible by destroying the previous ones": a cell in the ground
    with no air beside it was refused until the step before it was dug: a step, a wait, a step. It is planned once
    the step before it is: three steps one after the other, at once, and your character digs them in their order.
    A step with nothing planned before it is still refused."""
    game.clear_area(8)
    game.give(pickaxe=1)
    game.press("ArrowDown", 200)
    game.press("b")
    x, y = game.js("[Build.S.at.x, Build.S.at.y]")             # (the cursor: on the tile in front of you; the first step is dug there)
    game.js("(() => { window.__work = Build.S.working; Build.S.working = true; return 1; })()")   # (the work held: every plan is made before a hole is dug)
    rows = lambda: {r[0]: r[1:] for r in game.js("Build.rows()")}
    sizes = []
    for k in range(4):                                         # four steps down, a tile south each: none of them dug yet
        if k:
            game.press("ArrowDown", 120)
        game.press("q", 120)
        assert game.js("Build.level()") == -1 - k and rows()["X"][0].startswith("Dig a way to"), (k, rows())
        game.press("x", 120); sizes.append(game.js("Build.S.plans.size"))
    assert sizes == [1, 3, 5, 7]                               # (the first: the land's top cell; then the room of each, two cells)
    game.press("ArrowDown", 120); game.press("ArrowDown", 120)  # two tiles on from the last, as deep: nothing planned beside it
    assert rows()["X"] == ["Plan the step before it first", "bad"]
    game.press("x", 120)
    assert game.js("Build.S.plans.size") == 7
    game.js("(() => { Build.S.working = false; Build.toggle(false); Build.toggle(true); return 1; })()")   # the work goes on
    try:
        game.wait(f"surfacesAt({x}, {y + 3})[0] === -4 && Build.S.plans.size === 0", 60000)
    except Exception:                                         # (what there is when it does not come: the plans left, the stair as far as it got, you)
        raise AssertionError(game.js(f"""JSON.stringify({{plans: [...Build.S.plans.values()].map((j) => [j.x - {x}, j.y - {y}, j.z, j.state, j.why || '', !!j.tried]), working: Build.S.working, on: Build.on,
          steps: [0, 1, 2, 3].map((k) => surfacesAt({x}, {y} + k)), me: [myAt.x - {x}, myAt.y - {y}, myAt.z], said: (document.getElementById('toast') || {{}}).textContent}})"""))
    assert [game.js(f"surfacesAt({x}, {y + k})") for k in (0, 1, 2, 3)] == [[-1], [-2], [-3, 0], [-4, 0]]   # two steps open to the sky, then under the land
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
    green = game.js(GREEN_ON_SCREEN, [[x + k, y, k] for k in range(1, 7)])
    assert green[0] > 0 and green[1:] == [0] * 5              # seen whole: no meadow in any of them, but the first: the step up in front of it is the way out, its edge as on the land
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
    dark = f"""(X) => {{ const P = xray.pic, f = ({y} * 16 - shOf(-4) + 8 - P.y) * P.w + X * 16 + 8 - P.x; return [!!P.deep[f], +(P.img.data[f * 4 + 3] / 255).toFixed(2)]; }}"""
    at_mouth, between, by_fire = (game.js(dark, X) for X in (x - 4, mid, fire))
    assert at_mouth[0] and between[0] and by_fire[0]           # (floor under the roof, in the picture)
    assert at_mouth[1] < .15 and by_fire[1] < .1 and between[1] > .25, (at_mouth, between, by_fire)
    assert not game.errors
