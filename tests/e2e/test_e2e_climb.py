"""Ladders and stairs, by keys (web/js/climbing.js; the server: sim/climbing.py)."""

SLOT = "(n) => String((slots.indexOf(n) + 1) % 10)"           # the key of the bar's slot that holds it


def step(game, key):
    game.hold([key], 90)                                       # (a tap: a tile)
    game.sleep(550)
    s = game.server()
    return s["x"], s["y"], s["z"]


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
    game.press("Space", 900)
    assert game.js(f"[surfacesAt({x}, {y - 3}), surfacesAt({x - 1}, {y - 3})]") == [[2], [1]] and game.inv("stairs") == 2
    drawn = game.js("""() => new Promise((ok) => { const was = Climb.drawStep, ups = []; Climb.drawStep = function (...a) { ups.push(a.slice(0, 3)); return was(...a); };
      requestAnimationFrame(() => requestAnimationFrame(() => { Climb.drawStep = was; ok(ups.length); })); })""")
    assert drawn >= 2                                          # each step drawn as a step: treads, risers, stringers (it was a plank block)
    game.rpc("dev_teleport", x=x - 1, y=y - 2, z=0)
    game.sleep(600)
    for key, want in (("ArrowUp", (x - 1, y - 3, 1)), ("ArrowRight", (x, y - 3, 2)), ("ArrowUp", (x, y - 4, 3))):
        assert step(game, key) == want
    assert game.js("myAt.z") == 3 and not game.errors
    # in build mode: a flight down from the floor's other end, planned with Space and laid by your character
    game.rpc("dev_teleport", x=x + 3, y=y - 1, z=0)
    game.sleep(600)
    game.press("b")
    game.js(f"Build.S.at = {{x: {x + 1}, y: {y - 3}}}")       # (beside the first flight's top step: this one comes straight out)
    assert game.js("Build.hint(Build.S.at).text") == "Plan stairs (2 steps)"
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
    assert "A ladder goes against something taller" in game.actions()
    game.rpc("dev_teleport", x=x, y=y - 1, z=0)
    game.sleep(600)
    game.face(0, -1)
    game.press("Space", 700)
    assert game.js(f"combAt({x}, {y - 2})") == "l" and game.inv("ladder") == 1
    hp = game.server()["hp"]
    assert step(game, "ArrowUp") == (x, y - 2, 0)              # onto the ladder
    # up it: rung by rung on the ladder's own tile, facing it, for about a second (six layers), and only then over the
    # edge (it was a slide from foot to top in a fifth of a second, the ladder drawn over the body)
    game.js("""() => { window.__seen = []; const t0 = performance.now();
      const f = () => { const p = ents.get('agent' + myId), c = Climb.climbOf(p); if (c) __seen.push([Math.round(performance.now() - t0), c.on, +c.dx.toFixed(2), +c.dy.toFixed(2), p.fy, +(overBody(p, TS())[1] - (c.dy * TS() - c.lift * zoom)).toFixed(1)]);
        if (performance.now() - t0 < 1600) requestAnimationFrame(f); }; requestAnimationFrame(f); }""")
    game.hold(["ArrowUp"], 90)
    game.sleep(1700)
    seen = game.js("__seen")
    on = [c for c in seen if c[1]]
    assert on and on[-1][0] - on[0][0] >= 500, seen[:3]        # on the rungs for half a second and more
    assert all(c[2] == 0 for c in on) and all(c[4] == -1 for c in on)      # on the ladder's own tile, facing it
    assert all(c[5] == 0 for c in on)                          # its name goes with it, over its head (it stayed on the straight line)
    assert any(c[3] > .4 for c in on)                          # (held back over its foot while it rises: the straight line had it half way up the cliff)
    s = game.server()
    assert (s["x"], s["y"], s["z"]) == (x, y - 3, 6)           # up it, onto the cliff
    assert game.js("myAt.z") == 6
    assert step(game, "ArrowDown") == (x, y - 2, 0)            # and down it
    game.sleep(400)
    assert game.server()["hp"] == hp and game.js("ents.get('agent' + myId).fall") in (None, False) and not game.errors
    # up a ladder at the cliff's side: nothing hides you, the x-ray circle stays shut (it took your height from the
    # ground under you, and opened half way up)
    game.rpc("dev_stamp", x=x - 3, y=y - 3, rows=["l"])
    game.rpc("dev_teleport", x=x - 3, y=y - 3, z=0)
    game.sleep(900)
    game.js("() => { window.__xr = 0; const t0 = performance.now(); const f = () => { __xr = Math.max(__xr, xray.a); if (performance.now() - t0 < 1800) requestAnimationFrame(f); }; requestAnimationFrame(f); }")
    game.hold(["ArrowRight"], 90)
    game.sleep(1900)
    assert game.server()["z"] == 6 and game.js("__xr") < .1
    # up a ladder behind a block: hidden behind it at the foot, you are seen through it in a circle, as through a hill,
    # and on top the circle is gone (it was a see-through stripe down the block, then nothing: you were lost behind it)
    game.rpc("dev_stamp", x=x + 6, y=y - 3, rows=["W"])
    game.rpc("dev_teleport", x=x + 6, y=y - 2, z=0)
    game.sleep(400)
    game.give(plank=2)
    assert game.rpc("act", tool="place", args={"x": x + 6, "y": y - 3, "item": "plank", "z": 3})["ok"]
    game.rpc("dev_stamp", x=x + 6, y=y - 4, rows=["l"])
    game.rpc("dev_teleport", x=x + 6, y=y - 4, z=0)
    game.sleep(900)
    assert game.js("Floors.seen") > .9                          # (at the foot, behind it)
    game.js("""() => { window.__v = 0; window.__over = []; const t0 = performance.now(); const f = () => { __v = Math.max(__v, Floors.seen);
      const c = Climb.climbOf(ents.get('agent' + myId)); if (c && !c.on) __over.push(c.y);
      if (performance.now() - t0 < 1500) requestAnimationFrame(f); }; requestAnimationFrame(f); }""")
    game.hold(["ArrowDown"], 90)
    game.sleep(1600)
    assert game.server()["z"] == 3 and game.js("__v") > .9 and game.js("Floors.seen") < .05      # (gone, on top)
    over = game.js("__over")                                    # stepping over onto the block: drawn after it, on it (it was drawn
    assert over and min(over) > (y - 3) + 3 * game.js("Floors.K")   # under the block till the step was done)
