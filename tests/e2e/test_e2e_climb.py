"""Ladders and stairs, by keys (web/js/climbing.js; the server: sim/climbing.py)."""

SLOT = "(n) => String((slots.indexOf(n) + 1) % 10)"           # the key of the bar's slot that holds it


def step(game, key):
    # (a tap: a tile. Down until the body has set out, then up, let go by the page itself on the first frame that moved
    # you: the tile it set out for is walked, and no more. It was held 90 ms of the game's time with a frame drawn first:
    # frames of 50 to 130 ms on the runners made it longer than a stride, and it went two tiles, "(16, -11, 0) == (15, -11,
    # 2)", up the ladder too. Let go when the walk was set, before a frame had moved you, it was a stop where you stood. Let
    # go by the test once it saw you move, the key was down 620 ms on a page drawing every 130 to 200 ms (the question
    # and the key's answer a frame each): two tiles, "(23, 2, 0)" from 21, and the frames said so)
    at = game.js("(() => { const p = ents.get('agent' + myId); return [p.x, p.y]; })()")
    game.js(TRACE)
    game.js(LET_GO, [key, at])
    game.page.keyboard.down(key)
    game.wait("window.__let", 3000)
    game.page.keyboard.up(key)                                 # (the page has let go already: this one changes nothing)
    game.sleep(550)
    # (the walk over AND the world come to where the screen stopped. It was settle(): a wait that gives up without a word after 3 s; on a busy
    # machine a climb down six layers was not over, and the world's place read was the top's: "(2, -3, 6) != (2, -2, 0)")
    try:
        game.wait("!walking && !pred && (() => { const p = ents.get('agent' + myId); return !!p && p.e.x === Math.round(p.x) && p.e.y === Math.round(p.y) && Math.abs(p.x - p.e.x) + Math.abs(p.y - p.e.y) < .01; })()", 10000)
    except Exception as e:
        raise AssertionError(game.js("(() => { const p = ents.get('agent' + myId); return {walking: !!walking, pred: !!pred, at: [p.x, p.y], world: [p.e.x, p.e.y, p.e.z], myAt, climb: !!Climb.climbOf(p)}; })()")) from e
    s = game.server()
    trace = game.js("(() => { cancelAnimationFrame(window.__tr.raf); return window.__tr.l; })()")
    if (s["x"], s["y"]) != (round(at[0]), round(at[1])) and abs(s["x"] - round(at[0])) + abs(s["y"] - round(at[1])) != 1:
        raise AssertionError(("more than one tile", (s["x"], s["y"], s["z"]), at, trace))
    return s["x"], s["y"], s["z"]


# (the key let go on the frame the body has moved, from the page: a keyup as the browser sends it)
LET_GO = """([key, at]) => { window.__let = false; const f = () => { const p = ents.get('agent' + myId);
  if (p && Math.abs(p.x - at[0]) + Math.abs(p.y - at[1]) > .05) { window.__let = true; dispatchEvent(new KeyboardEvent('keyup', {key, code: key})); } else requestAnimationFrame(f); };
  requestAnimationFrame(f); return 1; }"""
# (each frame of a step, while #65 is open: when it goes two tiles, which frame took the second: [ms, x, y, the tile it is
# entering, the walk's way (0: none), in the air, a stop awaited, the key held])
TRACE = """(() => { if (window.__tr) cancelAnimationFrame(window.__tr.raf); const t = window.__tr = {l: [], t0: performance.now()};
  const f = () => { const p = ents.get('agent' + myId); if (p) t.l.push([Math.round(performance.now() - t.t0), +p.x.toFixed(2), +p.y.toFixed(2), p.tx, p.ty,
    walking ? walking.dir : 0, Leap.on() ? 1 : 0, pred ? 1 : 0, [...keys].filter((k) => KEYDIR[k]).join()]); t.raf = requestAnimationFrame(f); };
  t.raf = requestAnimationFrame(f); return 1; })()"""


def test_stairs_are_laid_with_one_press_and_walked_up(game):
    """Beside a floor three layers up, Space with stairs in hand lays the whole flight: two steps down towards you.
    Up them by the arrows, a hop a step, onto the floor. In build mode a flight is planned the same way."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(-1, -4, ["WWW"])                                # a wall, and a floor on it three layers up
    game.give(plank=6, stairs=4)
    game.rpc("dev_teleport", x=x, y=y - 2, z=0)                # (within reach of it)
    for i in (-1, 0, 1):
        assert game.rpc("act", tool="place", args={"x": x + i, "y": y - 4, "item": "plank", "z": 3})["ok"]
    game.press(game.js(SLOT, "stairs"))
    game.face(0, -1)                                           # facing the wall under the floor: the flight can't come at you, it runs along it
    assert "Build stairs (2 steps)" in game.actions()
    game.press("e", 900)
    assert game.js(f"[surfacesAt({x}, {y - 3}), surfacesAt({x - 1}, {y - 3})]") == [[2], [1]] and game.inv("stairs") == 2
    game.rpc("dev_teleport", x=x - 1, y=y - 2, z=0); game.arrive()
    for key, want in (("ArrowUp", (x - 1, y - 3, 1)), ("ArrowRight", (x, y - 3, 2)), ("ArrowUp", (x, y - 4, 3))):
        assert step(game, key) == want
    assert game.js("myAt.z") == 3 and not game.errors
    # in build mode: a flight down from the floor's other end, planned with Space and laid by your character
    game.rpc("dev_teleport", x=x + 3, y=y - 1, z=0); game.arrive()
    game.press("b")
    game.js(f"Build.S.at = {{x: {x + 1}, y: {y - 3}}}")       # (beside the first flight's top step: this one comes straight out)
    assert game.js("Build.hint(Build.S.at).text") == "Build stairs (2 steps)"
    game.press("Space")
    game.wait(f"surfacesAt({x + 1}, {y - 3})[0] === 2 && surfacesAt({x + 1}, {y - 2})[0] === 1 && Build.S.plans.size === 0", 20000)
    game.press("b")
    assert game.inv("stairs") == 0 and not game.errors


def test_a_ladder_is_climbed_and_come_down_without_a_fall(game):
    """A cliff six layers up: a ladder against it, up it by walking into the cliff, down it by walking off: no fall,
    no hurt. Out in the open a ladder has nothing to lean on: it is not placed."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(-2, -4, ["....."] * 2, levels=["66666"] * 2)
    game.give(ladder=2)
    game.press(game.js(SLOT, "ladder"))
    game.face(1, 0)
    assert "Needs something taller behind" in game.actions()
    game.rpc("dev_teleport", x=x, y=y - 1, z=0); game.arrive()
    game.face(0, -1)
    game.press("e", 700)
    assert game.js(f"combAt({x}, {y - 2})") == "l" and game.inv("ladder") == 1
    hp = game.server()["hp"]
    assert step(game, "ArrowUp") == (x, y - 2, 0)              # onto the ladder
    # up it: rung by rung on the ladder's own tile, facing it, for about a second (six layers), and only then over the
    # edge (it was a slide from foot to top in a fifth of a second, the ladder drawn over the body)
    game.js("""() => { window.__seen = []; const t0 = performance.now();
      const f = () => { const p = ents.get('agent' + myId), c = Climb.climbOf(p); if (c) __seen.push([Math.round(performance.now() - t0), c.on, +c.dx.toFixed(2), +c.dy.toFixed(2), p.fy, BodyPlace.of(p).tx, BodyPlace.of(p).ty]);
        if (performance.now() - t0 < 1600) requestAnimationFrame(f); }; requestAnimationFrame(f); }""")
    game.hold(["ArrowUp"], 90)
    game.sleep(1700)
    seen = game.js("__seen")
    on = [c for c in seen if c[1]]
    assert on and on[-1][0] - on[0][0] >= 500, seen[:3]        # on the rungs for half a second and more
    assert all(c[2] == 0 for c in on) and all(c[4] == -1 for c in on)      # on the ladder's own tile, facing it
    # (and the body's place says the tile it is drawn on, the ladder's, for the whole climb: it said the tile it was nearest,
    #  the cliff's from half way up: what lights and covers a body read the cliff's top for it)
    assert {(c[5], c[6]) for c in on} == {(x, y - 2)}, sorted({(c[5], c[6]) for c in on})
    assert any(c[3] > .4 for c in on)                          # (held back over its foot while it rises: the straight line had it half way up the cliff)
    s = game.server()
    assert (s["x"], s["y"], s["z"]) == (x, y - 3, 6)           # up it, onto the cliff
    assert game.js("myAt.z") == 6
    assert step(game, "ArrowDown") == (x, y - 2, 0)            # and down it
    game.sleep(400)
    assert game.server()["hp"] == hp and game.js("BodyPlace.state(ents.get('agent' + myId)).fall") in (None, False) and not game.errors
    # up a ladder at the cliff's side
    game.rpc("dev_stamp", x=x - 3, y=y - 3, rows=["l"])
    game.rpc("dev_teleport", x=x - 3, y=y - 3, z=0); game.arrive()
    game.hold(["ArrowRight"], 90)
    game.sleep(1900)
    assert game.server()["z"] == 6
    # up a ladder behind a block, onto it
    game.rpc("dev_stamp", x=x + 6, y=y - 3, rows=["W"])
    game.rpc("dev_teleport", x=x + 6, y=y - 2, z=0); game.arrive()
    game.give(plank=2)
    assert game.rpc("act", tool="place", args={"x": x + 6, "y": y - 3, "item": "plank", "z": 3})["ok"]
    game.rpc("dev_stamp", x=x + 6, y=y - 4, rows=["l"])
    game.rpc("dev_teleport", x=x + 6, y=y - 4, z=0); game.arrive()
    game.hold(["ArrowDown"], 90)
    game.sleep(1600)
    assert game.server()["z"] == 3


def test_out_of_your_own_shaft_by_keys(game):
    """Four down, in a
    shaft one tile wide, a ladder in hand: whichever wall you face, Space puts it where you stand (it was "Needs
    something taller behind" three ways of four); walking into the wall climbs out onto its top."""
    game.clear_area(8)
    x, y = game.pos()
    game.give(pickaxe=1, ladder=1)
    game.press(game.js(SLOT, "pickaxe"))
    game.face(0, 1)
    for depth in (1, 2, 3, 4):                                         # (the shaft, dug from on it: X digs the block you face, its box: keyboard.js digAhead)
        game.act("dig_down", **{"with": "pickaxe"})
        game.wait(f"myAt && myAt.z === {-depth} && !myAction", 8000)
        assert game.server()["z"] == -depth
    assert game.js("facingNow(true).it.text") == "Dig into the wall" and "Dig into" not in game.actions()      # (a hole in a meadow: no hill. Not written while the way out is shown: its key alone, wayshow.js)
    game.press(game.js(SLOT, "ladder"))
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        game.face(dx, dy)
        game.wait("$('prompts').innerText.includes('Place ladder')", 3000)
        aim = game.js("(() => { const a = aimedTile(); return [a.p.x, a.p.y, a.it.ok, a.it.z]; })()")
        assert aim == [x, y, True, -4], (dx, dy, aim)          # the ghost: on your own tile, at your feet
    game.press("e", 100)
    game.wait(f"combAt({x}, {y}) === 'l'", 5000)
    assert game.inv("ladder") == 0 and "way" not in game.actions()     # (on your ladder: nothing red said)
    hp = game.server()["hp"]
    game.hold(["ArrowLeft"], 90)
    game.wait(f"myAt && myAt.x === {x - 1} && myAt.z === 0", 6000)
    game.sleep(300)
    s = game.server()
    assert (s["x"], s["y"], s["z"], s["hp"]) == (x - 1, y, 0, hp) and not game.errors


AIM = "(() => { const c = DigUp.aim(); return c && [c.x, c.y, c.z, c.text]; })()"
WAYBOX = "([x, y, z]) => { const n = WayShow.cur && WayShow.cur.next; return !!n && n.x === x && n.y === y && n.z === z; }"


def test_out_of_your_own_shaft_with_a_pickaxe_alone(game):
    """"how do i climb up? why i cant??": four down in a shaft a tile wide, a pickaxe and no ladder: Space dug level,
    X dug down, nothing dug upward. R (Dig up) takes the cell in front of you at your head's height ("Dig a step"),
    Space jumps you up onto the block under it; then the cell over your head ("Dig up") and the next step: a stair out, a
    layer each time. The cell it will take is marked, at its own height. And under the land, the tree on top of the
    wall you face, three up, is not offered ("Chop tree (slow)" with the aim on a tunnel wall): the wall is."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(1, -1, ["T"])
    game.give(pickaxe=1)
    game.press(game.js(SLOT, "pickaxe"))
    game.face(1, 0)
    for depth in (1, 2, 3, 4):                                         # (the shaft, dug from on it)
        game.act("dig_down", **{"with": "pickaxe"})
        game.wait(f"myAt && myAt.z === {-depth} && !myAction", 8000)
    X, z, said = x, -4, []
    while z < 0:
        if (X, z) == (x + 1, -3):                              # on the first step, the land over you: the tree north, on top of the wall
            game.face(0, -1)
            game.wait("facingNow(true) && facingNow(true).it.text === 'Dig on'", 3000)   # (what X would do there; while the way out is shown its own key alone is written: wayshow.js)
            assert "Chop" not in game.actions(), game.actions()
            game.face(1, 0)
        # (the way out moves on to its next block once the dug one is gone from the land: a frame or two later. Read before, on
        # a 100 ms frame, R's cell was the one just dug: "(4, -2, [5, -18, 0, 'Dig a step'])", solidAt false)
        game.wait("(() => { const c = DigUp.aim(); return !c || solidAt(c.x, c.y, c.z); })()", 3000)
        aim = game.js(AIM)
        if aim:
            assert aim[0] in (X, X + 1) and aim[1] == y and z + 2 <= aim[2] <= z + 3 and game.js(f"solidAt({aim[0]}, {aim[1]}, {aim[2]})"), (X, z, aim)   # a block over your head or before it (the way out the HD look shows may take the one over that: wayshow.js)
            game.wait("document.getElementById('waycap') && document.getElementById('waycap').style.display === 'block' && document.getElementById('waycap').textContent === 'R'", 3000)   # its key, beside the block (the way out, shown)
            game.page.wait_for_function(WAYBOX, arg=aim[:3], timeout=3000)           # and marked: that cell, at its own height
            said.append(aim[3])
            game.press("r", 100)
            game.wait(f"!solidAt({aim[0]}, {aim[1]}, {aim[2]}) && !myAction", 8000)
        else:                                                  # (walking into the step stops you: Space jumps it)
            game.press("Space", 0)
            game.wait(f"myAt && myAt.z > {z} && !walking", 6000)
            X, z = game.js("[myAt.x, myAt.z]")
    assert said and set(said) <= {"Dig a step", "Dig up"}, said
    game.wait("!walking && (!pred || performance.now() > pred.until)", 4000)
    srv = game.server()
    assert (srv["y"], srv["z"], srv["hp"]) == (y, 0, 20) and srv["x"] >= x + 4
    assert game.js(f"[1, 2, 3].map((k) => surfacesAt({x} + k, {y})[0])") == [-3, -2, -1] and not game.errors
