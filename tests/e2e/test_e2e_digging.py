"""Digging down in build mode (web/js/build.js, keyhole.js, tiles.js). "depth visualisation is unintuitive", and of
five mockups the user chose "Earth and a keyhole": dug ground is earth, a shade darker a layer down; where the ground
hides the cursor only its own column is seen through; beside it, how far down it is. By keys: Q sinks the cursor a
layer into the ground, E brings it back, X digs the room to stand there: a way down is a tunnel, a step at a time."""

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
    assert game.js("Build.level()") == 0 and rows()["Q E"][0] == "A layer down, up" and rows()["X"][0] == "Break"
    for depth in (1, 2, 3):
        game.press("q", 120)
        assert game.js("Build.level()") == -depth and rows()["Z"][0] == f"BUILD · -{depth} · leave"
    assert rows()["X"] == ["Plan the step before it first", "bad"]      # (three down, beside you: shut in)
    game.press("x")
    assert game.js("Build.S.plans.size") == 0
    game.press("b")
    game.stamp(0, 0, ["."], levels=["c"])                     # you, three down in a hole: earth in front of your legs and of your eyes
    game.rpc("dev_teleport", x=x, y=y, z=-3)
    game.wait(f"myAt && myAt.x === {x} && myAt.z === -3", 8000); game.wait(DRAWN, 8000)
    game.face(0, 1); game.press("b")
    assert game.js("[[Build.S.at.x, Build.S.at.y], Build.level()]") == [[x, y + 1], -1] and rows()["X"][0] == "Break"   # the block in front of your eyes: it is dug by itself
    game.press("x")
    game.wait(f"surfacesAt({x}, {y + 1}).join() === '-2,0' && Build.S.plans.size === 0", 30000)
    assert game.js("Build.level()") == -2 and rows()["X"][0] == "Break"     # (the cursor is on the one under it now)
    game.press("x")                                           # ...dug too: the room, and the land over it left
    game.wait(f"surfacesAt({x}, {y + 1}).join() === '-3,0' && Build.S.plans.size === 0", 30000)
    assert game.inv("stone_block") == 2                      # (the blocks themselves: landblocks.py)
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
        assert game.js("Build.level()") == -2 and rows()["X"][0] == "Break", (k, rows())
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
    for key, front, level, text in (((-1, 0), [x - 1, y], 2, "Break"), ((1, 0), [x + 1, y], 1, "Break"), ((0, 1), [x, y + 1], 0, "Break")):
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


MARK = "(() => { const m = Keyhole.marks; return m ? m.n : null; })()"      # (the layer of you the cursor is level with: keyhole.js)


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
    see = lambda: game.js("[Build.level(), Build.rows()[0][1]]") + [game.js(MARK)]
    assert see() == [2, "BUILD MODE · leave", 2]              # the block in front of your eyes: a box, nothing written, your head marked
    game.press("q", 120)
    assert see() == [1, "BUILD MODE · leave", 1]              # of your legs
    game.press("e", 120); game.press("e", 120)
    assert see() == [3, "BUILD · +1 · leave", 3]              # the one over your head: +1, the mark over your head
    game.press("e", 120)
    assert see()[:2] == [4, "BUILD · +2 · leave"]                     # a layer at a time up the rock (it went to 5: a storey over the ground it rode)
    game.press("b"); game.face(1, 0); game.press("b")                     # on the ground, level with you: a square, no mark
    assert see() == [0, "BUILD MODE · leave", None]
    game.press("b")
    assert not game.errors
