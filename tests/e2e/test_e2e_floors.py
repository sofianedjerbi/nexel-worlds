"""Building up: a floor laid on the walls of a room, steps of blocks, the room upstairs (web/js/floors.js, build.js;
the server: sim/storeys.py)."""

SLOT = "(n) => String((slots.indexOf(n) + 1) % 10)"           # the key of the bar's slot that holds it
# the blocks at height z over w x h tiles: p planks, r roof, or the char of what stands on the block
CELLS = "([x, y, w, h, z]) => { let s = ''; for (let j = 0; j < h; j++) { for (let i = 0; i < w; i++) { const c = Floors.get(x + i, y + j, z); s += c ? c[1] || c[0][0] : '.'; } s += '/'; } return s; }"


def cells(game, x, y, w, h, z):
    return game.js(CELLS, [x, y, w, h, z])


def test_a_second_floor_is_built_and_climbed_by_keys_alone(game):
    """Nothing could be built over anything: one piece a tile, and a roof nobody stood on. Now the cursor of build
    mode has a height (E up, Q down): planks planned in the air over a room are a floor, on the walls and from block to
    block; planks on a floor are a step, two of them a higher one; up you walk, a jump a block, and upstairs you
    build as on the ground. All of it by keys."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(1, -5, ["WWWWW", "WnnnW", "WnnnW", "WW+WW"])   # a room (x+2..x+4, y-4..y-3), its door at (x+3, y-2)
    game.give(plank=30, wood_wall=4, roof=12)
    kb = game.page.keyboard
    at = lambda i, j: game.js(f"Build.S.at = {{x: {x + i}, y: {y + j}}}")
    game.press(game.js(SLOT, "plank"))
    game.press("b")
    assert game.js("Build.level()") == 0 and "Q E" in [r[0] for r in game.js("Build.rows()")]
    game.press("e")                                            # the cursor up a floor: over the house, in the air
    assert game.js("[Build.S.plane, Build.level()]") == [3, 3] and "floor +1" in game.js("Build.rows()")[0][1]
    at(0, -6)
    assert game.js("Build.hint(Build.S.at)")["ok"] is False    # in the open: nothing under it, nothing beside it
    for row in range(4):                                       # a row over each line of the house, walls and room
        at(1, -2 - row)
        kb.down("Space")
        for _ in range(4):
            game.press("ArrowRight", 110)
        kb.up("Space")
    game.wait(f"({CELLS})([{x + 1}, {y - 5}, 5, 4, 3]) === 'ppppp/ppppp/ppppp/ppppp/' && Build.S.plans.size === 0", 60000)
    assert game.inv("plank") == 10 and game.js(f"[combAt({x + 1}, {y - 5}), tile({x + 2}, {y - 4})[1]]") == ["W", "n"]    # what is under it is as it was
    assert all(len(r[1]) <= 26 for r in game.js("Build.rows()"))
    at(2, -4)                                                  # the stairwell: two blocks taken back, at the cursor's level
    game.press("x"); game.press("ArrowDown", 120); game.press("x")
    game.wait(f"({CELLS})([{x + 1}, {y - 5}, 5, 4, 3]) === 'ppppp/p.ppp/p.ppp/ppppp/' && Build.S.plans.size === 0", 30000)
    game.press("q")                                            # down again: the cursor rides the ground
    assert game.js("[Build.S.plane, Build.S.down, runKey]") == [None, 0, False]
    at(2, -3)
    assert game.js("Build.hint(Build.S.at).text") == "Plan plank on top"
    game.press("Space")                                        # a step: planks on the floor
    game.wait(f"!!Floors.get({x + 2}, {y - 3}, 1) && Build.S.plans.size === 0", 30000)
    at(2, -4)
    game.press("Space")
    game.wait(f"!!Floors.get({x + 2}, {y - 4}, 1) && Build.S.plans.size === 0", 30000)
    game.press("Space")                                        # ...and on that one, another
    game.wait(f"!!Floors.get({x + 2}, {y - 4}, 2) && Build.S.plans.size === 0", 30000)
    game.press("b")
    assert game.inv("plank") == 9 and not game.errors
    game.rpc("dev_teleport", x=x + 3, y=y - 1, z=0)            # before the door
    game.sleep(700)
    for key, to in (("ArrowUp", (3, -2, 0)), ("ArrowUp", (3, -3, 0)), ("ArrowLeft", (2, -3, 1)), ("ArrowUp", (2, -4, 2)), ("ArrowRight", (3, -4, 3))):
        game.hold([key], 90)                                   # (a tap: a tile)
        game.sleep(500)
        s = game.server()
        assert (s["x"] - x, s["y"] - y, s["z"]) == to, (key, to, s["x"] - x, s["y"] - y, s["z"])
    assert game.js("myAt.z") == 3 and game.js("liftOf(ents.get('agent' + myId)) / zoom") == 24      # drawn where you stand: three layers up
    game.press("b")                                            # upstairs, the cursor down a floor: the room under it
    game.js(f"Build.S.at = {{x: {x + 3}, y: {y - 3}}}")
    assert game.js("Build.level()") == 3
    game.press("q")
    assert game.js("[Build.level(), Build.rows()[0][1]]") == [0, "BUILD · floor -1 · leave"]
    game.press("e")
    assert game.js("[Build.level(), Build.S.down, Build.S.plane]") == [3, 0, None]
    game.press("b")
    game.press(game.js(SLOT, "wood_wall"))                     # upstairs, by hand: a wall on the floor before you
    game.press("Space", 700)
    assert cells(game, x + 4, y - 4, 1, 1, 3) == "W/" and game.js(f"combAt({x + 4}, {y - 4})") == "n"      # (on the floor: the room under it is as it was)
    game.hold(["ArrowRight"], 90)
    game.sleep(450)
    assert game.server()["x"] == x + 3                          # it shuts the way
    game.press("x")                                            # and comes down again (by hand: two seconds)
    game.wait(f"({CELLS})([{x + 4}, {y - 4}, 1, 1, 3]) === 'p/'", 8000)
    assert game.inv("wood_wall") == 4
    assert not game.errors


PUT = """async ([list, stand]) => { const bad = [];
  for (const [x, y, z, item] of list) {
    const s = stand.find((q) => (q[0] - x) ** 2 + (q[1] - y) ** 2 + ((z - q[2]) * .5) ** 2 <= 6 && !(q[0] === x && q[1] === y));
    if (!s) { bad.push([x, y, z, item, 'no stand']); continue; }
    await rpc('dev_teleport', {x: s[0], y: s[1], z: s[2]});
    const r = await rpc('act', {tool: 'place', args: {x, y, item, z}});
    if (!r.ok) bad.push([x, y, z, item, r.detail || r.error]);
  } return bad; }"""


def house(game, x0, y0, W=5, H=5):
    """Two storeys at (x0, y0), by the game's own `place`: walls and a door (stamped), a floor on them with a
    stairwell by the west wall, two steps, walls upstairs, a bed, a roof over it all."""
    x, y = game.pos()
    game.stamp(x0 - x, y0 - y, ["".join("+" if (i, j) == (W // 2, H - 1) else "W" if i in (0, W - 1) or j in (0, H - 1) else "n" for i in range(W)) for j in range(H)])
    game.rpc("dev_give", items={"plank": 60, "roof": 40, "wood_wall": 30, "bed": 1})
    room = [(x0 + i, y0 + j, 0) for j in range(1, H - 1) for i in range(1, W - 1)]
    well = [(x0 + 1, y0 + 1), (x0 + 1, y0 + 2)]
    up = [(x0 + i, y0 + j, 3) for j in range(1, H - 1) for i in range(2, W - 1)] + [(x0 + 1, y0 + 3, 3), (x0 + 1, y0 + 1, 2)]
    for part, stand in (([(x0 + i, y0 + j, 3, "plank") for j in range(H) for i in range(W) if (x0 + i, y0 + j) not in well], room),
                        ([(x0 + 1, y0 + 2, 1, "plank"), (x0 + 1, y0 + 1, 1, "plank"), (x0 + 1, y0 + 1, 2, "plank")], room),
                        ([(x0 + i, y0 + j, 3, "wood_wall") for j in range(H) for i in range(W) if i in (0, W - 1) or j in (0, H - 1)], up),
                        ([(x0 + 3, y0 + 1, 3, "bed")], up),
                        ([(x0 + i, y0 + j, 6, "roof") for j in range(H - 1, -1, -1) for i in range(W)], up)):
        assert game.js(PUT, [part, stand]) == []


def go(game, x, y, z):
    """Put us at (x, y), height z, and wait till the page has us there (on a busy machine: a few frames)."""
    game.rpc("dev_teleport", x=x, y=y, z=z)
    game.wait(f"myAt && myAt.x === {x} && myAt.y === {y} && myAt.z === {z} && Math.abs(ents.get('agent' + myId).x - {x}) < .01 && Math.abs(ents.get('agent' + myId).y - {y}) < .01", 8000)
    game.sleep(400)


def test_you_see_the_floor_you_are_on_and_fall_off_its_edge(game):
    """A house of two storeys. From outside all of it is drawn; in the room, what is over your head is seen through,
    the floor above and the roof with it; on the steps still; upstairs, only the roof, and the floor you stand on is
    whole. Behind the house, only the blocks drawn over you are a veil. A bed upstairs is slept in; off the edge of
    a floor you fall to the ground."""
    game.js("setOpt('above', 'circle')")                       # (the view that fades what is over you: test_e2e_views.py has the rest)
    game.clear_area(10)
    x, y = game.pos()
    x0, y0 = x + 2, y - 7
    house(game, x0, y0)
    alpha = lambda *cells: game.js("(cs) => cs.map(([x, y, z]) => Floors.alpha(x, y, z))", [list(c) for c in cells])
    floor, roof, wall = (x0 + 3, y0 + 2, 3), (x0 + 3, y0 + 2, 6), (x0 + 2, y0 + 4, 3)
    go(game, x, y, 0)
    assert alpha(floor, roof, wall) == [1, 1, 1] and game.server()["sheltered"] is False            # from outside
    go(game, x0 + 3, y0 + 2, 0)                                               # in the room
    assert alpha(floor, roof, wall) == [.12, .12, .12] and game.server()["sheltered"] is True and game.server()["in_cave"] is False
    assert game.js("!caveOpen")                                                                     # (a room is no cave: nothing of the land is opened, nor darkened)
    go(game, x0 + 1, y0 + 2, 1)                                               # on the first step: the room still
    assert alpha(floor, roof) == [.12, .12]
    go(game, x0 + 2, y0 + 2, 3)                                               # upstairs
    assert alpha(floor, roof, wall) == [1, .12, 1] and game.js("liftOf(ents.get('agent' + myId)) / zoom") == 24
    # others see you up there: the server says your height
    assert game.js("ents.get('agent' + myId).e.z") == 3
    game.hold(["ArrowUp"], 90)                                                                      # a tile north: the bed is to the east
    game.sleep(500)
    game.face(1, 0)
    game.press("Space", 1500)
    assert game.server()["spawn"] == [x0 + 3, y0 + 1, 3]                                            # slept in: you wake upstairs
    assert game.js("Floors.veils") == 0
    go(game, x0 + 2, y0 - 2, 0)                                               # behind the house: two tiles north of its north wall
    game.wait("Floors.seen > .9", 8000)                                                             # (once its land is drawn: a busy machine takes a moment)
    assert alpha((x0 + 2, y0, 6), (x0 + 2, y0 + 3, 6)) == [1, 1] and game.js("Floors.veils") >= 1      # not seen through as a room is: a circle round you, as through a hill
    go(game, x0 + 2, y0 + 6, 0)                                                                     # before the house: nothing is over you
    assert game.js("Floors.veils") == 0
    go(game, x0 + 3, y0 + 3, 3)                                               # upstairs again; a gap is cut in the south wall, and off you walk
    assert game.rpc("act", tool="dig", args={"x": x0 + 3, "y": y0 + 4, "z": 3, "with": "axe"})["ok"]
    game.sleep(400)
    game.hold(["ArrowDown"], 500)
    game.sleep(900)
    s = game.server()
    assert (s["x"], s["z"]) == (x0 + 3, 0) and s["y"] >= y0 + 5 and s["hp"] == 20                    # down on the ground before the door, unhurt (three layers)
    assert not game.errors


def test_earth_raises_the_ground_and_planks_go_on_from_a_floor(game):
    """The land is blocks too: earth in hand, Space on open ground, and the ground there comes up a layer, grass and
    all (digging takes it down one); again, another. In build mode: a row of it. And standing on a built floor with
    planks in hand, the air before you at your own height takes the next one: the floor goes on."""
    game.clear_area(10)
    x, y = game.pos()
    game.give(dirt=6, plank=6)
    game.press(game.js(SLOT, "dirt"))
    game.face(1, 0)
    assert "Raise the ground" in game.actions()
    game.press("Space", 700)
    assert game.js(f"[topAt({x + 1}, {y}), combAt({x + 1}, {y})]") == [1, "."] and game.inv("dirt") == 5       # up a layer, its grass on it
    game.hold(["ArrowRight"], 90)                              # a jump up onto it
    game.sleep(500)
    assert (game.server()["x"], game.server()["z"]) == (x + 1, 1)
    game.press("b")                                            # in build mode: a row of three, north of you
    game.js(f"Build.S.at = {{x: {x}, y: {y - 2}}}")
    game.page.keyboard.down("Space")
    for _ in range(2):
        game.press("ArrowRight", 120)
    game.page.keyboard.up("Space")
    game.wait(f"[0, 1, 2].every((i) => topAt({x} + i, {y - 2}) === 1) && Build.S.plans.size === 0", 30000)
    game.press("b")
    assert game.inv("dirt") == 2 and not game.errors
    # a floor that goes on from a block: by hand, from the block you stand on
    game.rpc("dev_stamp", x=x + 3, y=y + 3, rows=["W"])
    game.rpc("dev_teleport", x=x + 3, y=y + 4, z=0)
    game.sleep(600)
    assert game.rpc("act", tool="place", args={"x": x + 3, "y": y + 3, "item": "plank", "z": 3})["ok"]       # one block on a wall
    game.rpc("dev_stamp", x=x + 4, y=y + 4, rows=["nn"])
    game.rpc("dev_teleport", x=x + 4, y=y + 5, z=0)
    for step in ((x + 4, y + 4, 1), (x + 5, y + 4, 1), (x + 5, y + 4, 2)):                             # two steps up to it
        assert game.rpc("act", tool="place", args={"x": step[0], "y": step[1], "item": "plank", "z": step[2]})["ok"]
    assert game.rpc("act", tool="place", args={"x": x + 5, "y": y + 3, "item": "plank", "z": 3})["error"] == "bad_target"      # (not beside a block: nothing holds it)
    assert game.rpc("act", tool="place", args={"x": x + 4, "y": y + 3, "item": "plank", "z": 3})["ok"]
    game.rpc("dev_teleport", x=x + 4, y=y + 3, z=3)
    game.sleep(700)
    game.press(game.js(SLOT, "plank"))
    game.face(0, -1)                                           # the air to the north, at your feet's height
    assert "Lay planks" in game.actions()
    game.press("Space", 700)
    assert game.js(f"!!Floors.get({x + 4}, {y + 2}, 3)") and game.inv("plank") == 0
    game.hold(["ArrowUp"], 90)
    game.sleep(500)
    assert (game.server()["y"], game.server()["z"]) == (y + 2, 3) and not game.errors                  # and you walk out on it
