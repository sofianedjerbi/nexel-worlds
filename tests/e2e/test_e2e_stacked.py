"""A column of the place with two rooms, one over the other (web/js/xray.js xrayPlace, xrayShows, xrayOverBody): what
is of the place you are in there, and who is seen in it. (What is of the place, who is drawn over it:
test_e2e_place.py.)"""

from test_e2e_digging import DRAWN, SEEN


def test_a_block_dug_under_a_tunnels_floor_changes_that_block_and_the_tunnel_stays(game):
    """"digged another block and topology changed !! what the hell": from his hole he dug the block at his eyes under
    the tunnel's end. A tile was of the place at one height: the new room took it, and that tile of the tunnel went
    from the picture, the tunnel one tile shorter. A column has both its rooms: the world has the tunnel's floor
    where it was and the new room under it; who stands on the tunnel's floor there is seen, as who is in the new
    room, not who is up on the land; from over it, the same."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 4                 # a pit; east of it your hole, two layers high, the tunnel's first tile over it; the tunnel on east, a step up at its end
    for i, col in ((-1, [-9, -4, 3]), (0, [-9, -7, -6, -4, 3]), (1, [-6, -4, 3]), (2, [-6, -4, 3]), (3, [-5, -3, 3])):
        game.rpc("dev_col", tiles=[[X + i, y]], col=col)
    game.rpc("dev_teleport", x=X, y=y, z=-9)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -9", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000)
    assert game.js(f"[seenUnder({X}, {y}), seenUnder({X + 1}, {y}), seenUnder({X + 2}, {y})]") == [-9, -6, -6]
    col = game.js(f"JSON.stringify(colAt({X + 1}, {y}))")
    assert game.rpc("act", tool="dig", args={"x": X + 1, "y": y, "z": -7})["ok"]             # the block at your eyes, in the wall the tunnel's next tile stands on
    game.wait(f"JSON.stringify(colAt({X + 1}, {y})) !== '{col}'", 20000)
    game.wait(f"{DRAWN} && xray.pic && xray.pic.floor.get('{X + 1},{y}') === -8", 20000)
    assert game.js(f"JSON.stringify(colAt({X + 1}, {y}))") == "[-8,-7,-6,-4,3]"            # the tunnel's floor is where it was; the wall has one block out, your new room
    assert game.js(f"seenUnder({X + 2}, {y})") == -6                                         # ...and the tunnel goes on past it
    who = lambda z: game.js(f"(() => {{ const p = {{x: {X + 1}, y: {y}, e: {{kind: 'chicken', id: -1}}, zAt: {{x: {X + 1}, y: {y}, z: {z}}}}}; return [xrayShows(p) > .9, xrayOverBody(p) > .9]; }})()")
    assert [who(-6), who(-8), who(3)] == [[True, False], [True, False], [False, True]]       # who stands on the tunnel's floor there is seen, as who is in your new room; not who is up on the land: that land is cut away under their feet, they go with it (test_e2e_place.py)
    game.rpc("dev_teleport", x=X + 2, y=y, z=-6)              # from the tunnel, over it: the same column
    game.wait(f"myAt && myAt.x === {X + 2} && myAt.z === -6", 8000)
    game.wait(f"{DRAWN} && xray.pic && xray.pic.floor.get('{X + 1},{y}') === -6", 20000)
    assert [who(-6), who(-8), who(3)] == [[True, False], [True, False], [False, True]]
    assert not game.errors
