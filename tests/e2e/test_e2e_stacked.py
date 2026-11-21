"""A column with two rooms, one over the other (cells.js): a block dug under a tunnel's floor changes that block, and
the tunnel stays where it was."""

DRAWN = "dirtyTiles.length === 0"


def test_a_block_dug_under_a_tunnels_floor_changes_that_block_and_the_tunnel_stays(game):
    """"digged another block and topology changed !! what the hell": from his hole he dug the block at his eyes under
    the tunnel's end. A column has both its rooms: the world has the tunnel's floor where it was and the new room under it."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 4                 # a pit; east of it your hole, two layers high, the tunnel's first tile over it; the tunnel on east, a step up at its end
    for i, col in ((-1, [-9, -4, 3]), (0, [-9, -7, -6, -4, 3]), (1, [-6, -4, 3]), (2, [-6, -4, 3]), (3, [-5, -3, 3])):
        game.rpc("dev_col", tiles=[[X + i, y]], col=col)
    game.rpc("dev_teleport", x=X, y=y, z=-9)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -9", 8000)
    game.wait(DRAWN, 8000)
    col = game.js(f"JSON.stringify(colAt({X + 1}, {y}))")
    assert game.rpc("act", tool="dig", args={"x": X + 1, "y": y, "z": -7})["ok"]             # the block at your eyes, in the wall the tunnel's next tile stands on
    game.wait(f"JSON.stringify(colAt({X + 1}, {y})) !== '{col}'", 20000)
    game.wait(DRAWN, 8000)
    assert game.js(f"JSON.stringify(colAt({X + 1}, {y}))") == "[-8,-7,-6,-4,3]"            # the tunnel's floor is where it was; the wall has one block out, your new room
    assert game.js(f"[surfacesAt({X}, {y})[0], surfacesAt({X + 2}, {y})[0]]") == [-9, -6] and not game.errors      # ...and the tunnel goes on past it
