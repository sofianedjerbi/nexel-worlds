"""Digging down in build mode (web/js/build.js, keyhole.js, tiles.js). "depth visualisation is unintuitive", and of
five mockups the user chose "Earth and a keyhole": dug ground is earth, a shade darker a layer down; where the ground
hides the cursor only its own column is seen through; beside it, how far down it is. By keys: Q sinks the cursor a
layer into the ground, E brings it back, X digs the room to stand there: a way down is a tunnel, a step at a time.
(The land is blocks, voxels.js: what is seen of it is read off the screen, LAND.)"""

GRASS = 0xff70d4c0                                             # (the meadow's green, #c0d470, as a block's px has it)
GREEN = f"""([x, y, rows, cols]) => {{ const b = blockOf(x, y), o = (y - b.by * B) * 16 * BW + (x - b.bx * B) * 16; let n = 0;
  for (const j of rows) for (const i of cols) if (b.px[o + j * BW + i] === {GRASS}) n++; return n; }}"""
DRAWN = "dirtyTiles.length === 0"


def test_q_sinks_the_cursor_a_layer_and_x_digs_the_block_it_is_on(game):
    """On solid ground Q did nothing but say "floor -1" (it counted storeys); now each Q is a layer into the ground,
    said beside the cursor and in the corner. There the cursor is on a block, and X digs that block, no other, where
    air is beside it; what is over it stays ("like minecraft ... this enforce me to dig huge columns": it dug every
    layer over the cursor; then two blocks at once from the lower one: "why am i unable to break block at my eye
    level ? why do i need to target the one down to dig both at once ?"). Where no air is beside it, it says so."""
    game.clear_area(8)
    game.give(pickaxe=1)
    x, y = game.pos()
    game.face(0, 1)                                           # (facing south: the cursor starts on the tile in front. Turned, not by a key: an arrow held a fifth of a second walks a tile on a busy machine)
    game.press("b")
    rows = lambda: {r[0]: r[1:] for r in game.js("Build.rows()")}
    assert game.js("Build.level()") == 0 and rows()["Q E"][0] == "A layer down, up" and rows()["X"][0] == "Dig a hole"
    for depth in (1, 2, 3):
        game.press("q", 120)
        assert game.js("Build.level()") == -depth and rows()["B"][0] == f"BUILD · -{depth} · leave"
    assert rows()["X"] == ["Plan the step before it first", "bad"]      # (three down, beside you: shut in)
    game.press("x")
    assert game.js("Build.S.plans.size") == 0
    game.press("b")
    game.stamp(0, 0, ["."], levels=["c"])                     # you, three down in a hole: earth in front of your legs and of your eyes
    game.rpc("dev_teleport", x=x, y=y, z=-3)
    game.wait(f"myAt && myAt.x === {x} && myAt.z === -3", 8000); game.wait(DRAWN, 8000)
    game.face(0, 1); game.press("b")
    assert game.js("[[Build.S.at.x, Build.S.at.y], Build.level()]") == [[x, y + 1], -1] and rows()["X"][0] == "Dig the block"   # the block in front of your eyes: it is dug by itself
    game.press("x")
    game.wait(f"surfacesAt({x}, {y + 1}).join() === '-2,0' && Build.S.plans.size === 0", 30000)
    assert game.js("Build.level()") == -2 and rows()["X"][0] == "Dig a hole"     # (the cursor is on the one under it now)
    game.press("x")                                           # ...dug too: the room, and the land over it left
    game.wait(f"surfacesAt({x}, {y + 1}).join() === '-3,0' && Build.S.plans.size === 0", 30000)
    assert game.inv("stone") == 2
    game.press("b")
    assert not game.errors


def test_blocks_are_planned_ahead_each_where_the_one_before_it_will_have_made_room(game):
    """"I dig down my stair, I get stopped 2 block on front of me because it is out of range. I'd like to not be
    blocked if the block I want to destroy will be accessible by destroying the previous ones": a block in the ground
    with no air beside it was refused until the one before it was dug: a block, a wait, a block. It is planned once
    the one before it is: three one behind the other, at once, and your character digs them in their order. A block
    with nothing planned before it is still refused."""
    game.clear_area(8)
    game.give(pickaxe=1)
    x, y = game.pos()
    game.stamp(0, 0, ["."], levels=["c"])
    game.rpc("dev_teleport", x=x, y=y, z=-3)
    game.wait(f"myAt && myAt.x === {x} && myAt.z === -3", 8000); game.wait(DRAWN, 8000)
    game.face(0, 1); game.press("b"); game.press("q", 120)    # (it starts on the block in front of your eyes: Q, the one in front of your legs)
    game.js("(() => { window.__work = Build.S.working; Build.S.working = true; return 1; })()")   # (the work held: every plan is made before a block is dug)
    rows = lambda: {r[0]: r[1:] for r in game.js("Build.rows()")}
    sizes = []
    for k in range(3):                                         # three blocks at your legs' height, one behind the other: none of them dug yet
        if k:
            game.press("ArrowDown", 120)
        assert game.js("Build.level()") == -2 and rows()["X"][0] == "Dig the block", (k, rows())
        game.press("x", 120); sizes.append(game.js("Build.S.plans.size"))
    assert sizes == [1, 2, 3]
    game.press("ArrowDown", 120); game.press("ArrowDown", 120)  # two tiles on from the last: nothing planned beside it
    assert rows()["X"] == ["Plan the step before it first", "bad"]
    game.press("x", 120)
    assert game.js("Build.S.plans.size") == 3
    game.js("(() => { Build.S.working = false; Build.toggle(false); Build.toggle(true); return 1; })()")   # the work goes on
    try:
        game.wait(f"surfacesAt({x}, {y + 3}).join() === '-3,0' && Build.S.plans.size === 0", 60000)
    except Exception:                                         # (what there is when it does not come: the plans left, how far it got, you)
        raise AssertionError(game.js(f"""JSON.stringify({{plans: [...Build.S.plans.values()].map((j) => [j.x - {x}, j.y - {y}, j.z, j.state, j.why || '', !!j.tried]), working: Build.S.working, on: Build.on,
          steps: [1, 2, 3].map((k) => surfacesAt({x}, {y} + k)), me: [myAt.x - {x}, myAt.y - {y}, myAt.z], said: (document.getElementById('toast') || {{}}).textContent}})"""))
    assert [game.js(f"surfacesAt({x}, {y + k})") for k in (1, 2, 3)] == [[-3, 0]] * 3     # a way a block high, under the land
    assert not game.errors


def test_the_block_you_stand_on_is_dug_from_on_it_and_you_come_down_with_it(game):
    """"i should be able to break this block by putting myself in top of it then digging under my feets": X on the
    block under you sent you off it to dig it from beside (a hole next to you); by the game's own way, digging down,
    it wanted a pickaxe. It is dug from on it, by hand too, and you come down with it."""
    game.clear_area(8)
    x, y = game.pos()
    game.face(0, 1); game.press("b")
    game.press("ArrowUp", 150)                                # the cursor on your own tile: the block you stand on
    assert game.js("[[Build.S.at.x, Build.S.at.y], Build.level()]") == [[x, y], 0]
    for depth in (1, 2):
        game.press("x")
        game.wait(f"myAt && myAt.x === {x} && myAt.y === {y} && myAt.z === {-depth} && surfacesAt({x}, {y})[0] === {-depth} && Build.S.plans.size === 0", 30000)
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


# the land under the build cursor (the cursor itself not drawn): the colour in the middle of its tile as drawn
UNDER_CURSOR = """() => { const draw = Build.draw; Build.draw = () => null; for (const m of Marks.list) m.a = 0; frame(performance.now()); Build.draw = draw;      // (nor the cursor's own box: mark.js)
  const r = Build.S.rect; return Array.from(ctx.getImageData(Math.round((r.x + r.w / 2) * DPR), Math.round((r.y + r.w / 2) * DPR), 1, 1).data).slice(0, 3); }"""


def test_the_keyhole_shows_the_cursor_where_the_ground_in_front_hides_it(game):
    """Down a hole the grass in front is drawn over the floor: the cursor's own tile is seen through, and no more (the
    cut that shows you when you are hidden is yours alone); on the ground, where nothing hides it, the land is
    as it is. (The land painted flat, keyhole.js painted that tile cut open; with blocks it is read off the screen:
    under the cursor, the pit's floor, earth, not the meadow in front of it.)"""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(-1, 2, ["..."] * 3, levels=["ccc"] * 3)
    game.wait(DRAWN, 8000)
    game.press("b")
    game.js(f"Build.S.at = {{x: {x}, y: {y + 4}}}")           # the pit's south row: under the grass in front
    assert game.js("Build.level()") == -3
    game.sleep(600)                                            # (the view goes half way to the cursor)
    under = game.js(UNDER_CURSOR)
    assert game.js("xray.a") < .1
    assert earth(under), under                                 # its floor, three down: seen through the grass in front
    game.js(f"Build.S.at = {{x: {x + 3}, y: {y}}}")
    game.sleep(600)
    assert green(game.js(UNDER_CURSOR))                        # on the meadow: the meadow
    game.press("b")
    assert not game.errors


SEEN = "xray.a > .95 && !!xray.pic"                           # hidden, the land cut open over the place you are in (xray.js)
HIDE = "['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']"
# the screen without anybody on it: the land's colour [r, g, b] at each [x, y, lv, ax, ay]: tile (x, y) as drawn at
# level lv, the art px (ax, ay) from its corner
LAND = """(spots) => { const keep = {}; for (const f of %s) { keep[f] = window[f]; window[f] = () => null; }
  parts.length = puffs.length = 0; frame(performance.now()); const S = TS(), [ox, oy] = screenOrigin(S), k = S / 16;
  const out = spots.map(([x, y, lv, ax, ay]) => Array.from(ctx.getImageData(Math.round((ox + x * S + (ax + .5) * k) * DPR), Math.round((oy + y * S - shOf(lv) * zoom + (ay + .5) * k) * DPR), 1, 1).data).slice(0, 3));
  Object.assign(window, keep); return out; }""" % HIDE
cut = lambda c: sum(c) < 220 and c[0] >= c[1]                  # the ground cut open with nothing behind, a cave's mouth: dark earth
earth = lambda c: c[0] > c[1] + 8 and not cut(c)               # a dug floor, a front: earth, lighter than the cut
sliced = lambda c: c[0] > c[1] + 30 and c[0] > c[2] + 40       # ground cut through where you are hidden: the top of a sliced block, earth as its front has it, browner than any floor (vox_section.js; it was the cut's flat dark)
green = lambda c: c[1] > c[0] + 12                             # the meadow
# the screen without anybody on it: in each of the tiles [x, y, depth] as drawn, how many px are greener than earth
GREEN_ON_SCREEN = """(tiles) => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
  frame(performance.now()); const S = TS(), [ox, oy] = screenOrigin(S), out = [];
  for (const [x, y, d] of tiles) { const px = ctx.getImageData(Math.round((ox + x * S) * DPR), Math.round((oy + y * S + shOf(d) * zoom) * DPR), S * DPR, S * DPR).data; let n = 0;
    for (let i = 0; i < px.length; i += 4) if (px[i + 1] > px[i] + 12) n++; out.push(n); }
  Object.assign(window, keep); return out; }"""


def test_a_stair_dug_down_is_cut_square_and_seen_whole_with_no_gap_as_you_walk_it(game):
    """A stair dug east, a tile wide. Each step had a dark bar down its side and a green line beside it ("still got the
    weird green line issue"): the bar was the rim of a hill, drawn on a dug step. Dug ground is cut square: a step is
    all of its tile. And going down, it flashed at every step ("when going down/up blocks it flashes"): the steps two
    behind you were out of what is seen through. The whole stair stays seen: on the screen every step near you is
    earth, the ones over you too, not the meadow in front of it and not the dark of ground cut open."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, 0, ["......"], levels=["abcdef"])
    game.rpc("dev_teleport", x=x + 4, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {x + 4} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    even = game.js(f"""() => {{ const out = []; for (let k = 1; k <= 6; k++) {{ const b = blockOf({x} + k, {y}), o = ({y} - b.by * B) * 16 * BW + ({x} + k - b.bx * B) * 16, sum = [0, 0];
      for (let j = 0; j < 16; j++) for (let i = 1; i < 14; i++) if (i < 7 || i > 8) {{ const v = b.px[o + j * BW + i]; sum[i < 7 ? 0 : 1] += (v & 255) + (v >> 8 & 255) + (v >> 16 & 255); }}
      out.push(sum[1] / sum[0] * 6 / 5 > .95); }} return out; }}""")
    assert even == [True] * 6                                  # each step: earth all over its tile, no dark rim down its lower side
    # stepping off the step three down (your height is already the next one's): the steps over you are still of the place
    assert game.js(f"[1, 2, 3, 4, 5, 6].every((k) => xrayPlace({x + 3}, {y}, -4).z.get(({x} + k) + ',' + {y}) === -k)")
    green = game.js(GREEN_ON_SCREEN, [[x + k, y, k] for k in range(1, 7)])
    assert green[1:] == [0] * 5, green                         # seen whole: no meadow in any of them (but the first: the step up in front of it is the way out, its edge as on the land)
    steps = game.js(LAND, [[x + k, y, -k, 8, 8] for k in range(1, 7)])       # the three you came down, yours, the two under you
    assert all(earth(c) for c in steps), steps
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


def test_under_ground_you_see_all_of_the_place_a_fire_however_far(game):
    """"underground vision should display as much as player can see, it is player vision. if fire is here, player see
    it, so it should be visible": what was seen of a tunnel stopped four tiles from you, and a fire a little further
    on was not drawn. All of the place is seen: nine tiles on, the fire's tile is of the place, its floor is on the
    screen, earth, not the meadow over it, and who stands by the fire is seen."""
    game.clear_area(16)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-8, 0, ["............^..."], levels=["abcddddddddddddd"], roofs=["0000444444444444"], heads=["0000222222222222"])
    game.rpc("dev_teleport", x=x - 5, y=y, z=-4)             # at the foot of the stair, the tunnel's mouth
    game.wait(f"myAt && myAt.x === {x - 5} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    fire = x + 4                                               # the fire, nine tiles from you
    assert game.js(f"[combAt({fire}, {y}), seenUnder({fire}, {y}), hiddenAt({fire}, {y}), standAt({fire}, {y})]") == ["^", -4, False, -4]
    by, mid = game.js(LAND, [[fire - 1, y, -4, 8, 8], [x, y, -4, 8, 8]])          # the floor beside the fire, and half way to it
    assert earth(by) and earth(mid), (by, mid)
    assert game.js(GREEN_ON_SCREEN, [[fire, y, 4], [fire - 1, y, 4]]) == [0, 0]
    who = game.js(f"(() => {{ const p = {{x: {fire - 1}, y: {y}, e: {{kind: 'chicken', id: -1}}, zAt: {{x: {fire - 1}, y: {y}, z: -4}}}}; return [xrayShows(p) > .9, unseen(p)]; }})()")
    assert who == [True, False], who
    assert not game.errors


def test_the_cursor_starts_on_the_block_in_front_of_your_eyes(game):
    """"when pressing B ... please show the most pertinent block first: in front of the player, direction where he's
    facing at his exact level": the cursor started on the tile you face, at the ground nearest your height there: in
    a tunnel, facing its end, that was the top of the land over the wall (a mountain: seventeen layers up), and Q, a
    layer a press, brought it down to where you dig. Facing a wall it starts on the block in front of your eyes
    ("default block to dig should be the one at player eye-level": it was the one in front of your legs; that one
    gone, of your legs). On the level, or a step up, it is on that ground, as it was."""
    game.clear_area(10)
    game.give(pickaxe=1)
    x, y = game.pos()
    game.stamp(-6, -2, ["." * 6] * 5, levels=["7" * 6] * 5)                # high ground west of you, seven layers
    game.stamp(1, 0, ["."], levels=["1"])                                   # a step up east of you
    for key, front, level, text in (((-1, 0), [x - 1, y], 2, "Dig the block"), ((1, 0), [x + 1, y], 1, "Dig a hole"), ((0, 1), [x, y + 1], 0, "Dig a hole")):
        game.face(*key)
        game.press("b")
        at, lv, rows = game.js("[[Build.S.at.x, Build.S.at.y], Build.level(), Object.fromEntries(Build.rows().map((r) => [r[0], r[1]]))]")
        assert (at, lv, rows["X"]) == (front, level, text), (key, at, lv, rows)
        game.press("b")
    game.face(-1, 0)                                          # into the high ground: X, and that block is dug, the land over it left
    game.press("b"); game.press("x")
    game.wait(f"surfacesAt({x - 1}, {y}).join() === '1,7' && Build.S.plans.size === 0", 30000)
    game.press("b"); game.press("b")                          # in again: the block in front of your legs, now
    assert game.js("[[Build.S.at.x, Build.S.at.y], Build.level()]") == [[x - 1, y], 1]
    game.press("b")
    assert not game.errors


MARK = """() => { frame(performance.now()); const m = Keyhole.marks; if (!m) return null;
  const d = ctx.getImageData(Math.round((m.x + zoom / 2) * DPR), Math.round((m.y + m.h / 2) * DPR), 1, 1).data; return [m.n, d[0] > 235 && d[1] > 215 && d[2] > 130 && d[2] < 205]; }"""


def test_a_block_in_the_ground_is_a_box_its_layer_is_marked_on_you_and_e_goes_up_the_rock_a_layer_at_a_time(game):
    """"going up in tunnel really isn't intuitive: +1 mean whaT ? +1 above player ? please make the block selection
    with position relative to player more evident": the cursor was the top of its block, a flat square a layer up the
    wall, "+1" beside the block in front of your legs; and E went up through rock a storey at a time, three layers.
    A block in the ground is a box, its front a layer high; the layer of you it is level with is marked on you; a
    number is how far over your head it is (under your floor: as it was); E and Q go a layer at a time in the ground."""
    game.clear_area(10)
    game.give(pickaxe=1)
    x, y = game.pos()
    game.stamp(-6, -2, ["." * 6] * 5, levels=["7" * 6] * 5)                # high ground west of you, seven layers
    game.face(-1, 0); game.press("b")
    see = lambda: game.js("[Build.level(), Build.rows()[0][1], Build.S.rect.h / zoom]") + [game.js(MARK)]
    assert see() == [2, "BUILD MODE · leave", 24, [2, True]]              # the block in front of your eyes: a box, nothing written, your head marked
    game.press("q", 120)
    assert see() == [1, "BUILD MODE · leave", 24, [1, True]]              # of your legs
    game.press("e", 120); game.press("e", 120)
    assert see() == [3, "BUILD · +1 · leave", 24, [3, True]]              # the one over your head: +1, the mark over your head
    game.press("e", 120)
    assert see()[:3] == [4, "BUILD · +2 · leave", 24]                     # a layer at a time up the rock (it went to 5: a storey over the ground it rode)
    game.press("b"); game.face(1, 0); game.press("b")                     # on the ground, level with you: a square, no mark
    assert see() == [0, "BUILD MODE · leave", 16, None]
    game.press("b")
    assert not game.errors
