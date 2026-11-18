"""A column of the place with two rooms, one over the other, and the brink of a floor (web/js/xraycut.js 6, 7): what
the picture of the place you are in shows of them. (What is of the place, who is drawn over it: test_e2e_place.py.)"""

from test_e2e_digging import DRAWN, SEEN
from test_e2e_place import LINE

# a px of the picture: [seen, the level it is of, how light it is] ([x, y, level: a tile as drawn; ax, ay: the px in it])
AT = """([x, y, lv, ax, ay]) => { const P = xray.pic, X = x * 16 + ax - P.x, Y = y * 16 - shOf(lv) + ay - P.y, d = P.over.getContext('2d').getImageData(X, Y, 1, 1).data;
  return [P.seen[Y * P.w + X], P.lev[Y * P.w + X], d[0] + d[1] + d[2]]; }"""


def test_a_block_dug_under_a_tunnels_floor_changes_that_block_and_the_tunnel_stays(game):
    """"digged another block and topology changed !! what the hell": from his hole he dug the block at his eyes under
    the tunnel's end. A tile was of the place at one height: the new room took it, and that tile of the tunnel went
    from the picture, the tunnel one tile shorter. A column shows both its rooms, cut along its south side: the
    tunnel's floor where it was, the rock under it, the new room through its opening; from over it, the same."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 4                 # a pit; east of it your hole, two layers high, the tunnel's first tile over it; the tunnel on east, a step up at its end
    for i, col in ((-1, [-9, -4, 3]), (0, [-9, -7, -6, -4, 3]), (1, [-6, -4, 3]), (2, [-6, -4, 3]), (3, [-5, -3, 3])):
        game.rpc("dev_col", tiles=[[X + i, y]], col=col)
    game.rpc("dev_teleport", x=X, y=y, z=-9)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -9", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    at, line = lambda *a: game.js(AT, list(a)), lambda *a: game.js(LINE, list(a))
    def column(i, low, rows):
        """the tunnel's floor on that tile, the layer of rock under it, and under that the room below, as much of its floor as its opening shows (rows of it, from its foot up)"""
        floor, rock, room = at(X + i, y, -6, 8, 8), at(X + i, y, -6, 8, 20), at(X + i, y, low, 8, 15)
        assert floor[:2] == [1, -6] and rock[0] == 1 and floor[2] > 1.3 * rock[2], (i, floor, rock)
        assert room[:2] == [1, low] and room[2] > 1.15 * rock[2], (i, room, rock)   # (a floor nine down is darker than one six down)
        # ...and no way from one room to the other: the foot of the tunnel's floor and the top of the room's opening have the line, the opening itself none
        # ("it looks like i am able to go up... but i cannot": the floor's brink was lit there, over one layer of rock and the room's floor: the next step of a stair)
        assert line(X + i, y, -6, 8, 15) and line(X + i, y, low, 8, 15 - rows) and not line(X + i, y, low, 8, 15 - rows // 2) and not line(X + i, y, -6, 8, 8), i
    column(0, -9, 16)                                         # over your own hole: the tunnel, a layer of rock, your floor whole
    wall = [at(X + 1, y, -6, 8, 16 + a) for a in (4, 12, 20)]  # the tunnel's next tile stands on its wall, three layers
    assert all(p[0] for p in wall) and at(X + 1, y, -6, 8, 8)[2] > 1.3 * max(p[2] for p in wall), wall
    col = game.js(f"JSON.stringify(colAt({X + 1}, {y}))")
    assert game.rpc("act", tool="dig", args={"x": X + 1, "y": y, "z": -7})["ok"]             # the block at your eyes, in that wall
    game.wait(f"JSON.stringify(colAt({X + 1}, {y})) !== '{col}'", 20000)
    game.wait(f"{DRAWN} && xray.pic && xray.pic.place.get('{X + 1},{y}') === -8 && xray.mix >= 1 && !xray.old", 20000)
    assert game.js(f"JSON.stringify(colAt({X + 1}, {y}))") == "[-8,-7,-6,-4,3]"
    column(1, -8, 8)                                          # the tunnel's floor is where it was; the wall has one block out, your new room: half its floor
    assert not line(X + 1, y, -6, 15, 8) and not line(X + 1, y, -6, 0, 8)      # ...and the tunnel goes on across it: no edge in its floor
    who = lambda z: game.js(f"(() => {{ const p = {{x: {X + 1}, y: {y}, e: {{kind: 'chicken', id: -1}}, zAt: {{x: {X + 1}, y: {y}, z: {z}}}}}; return [xrayShows(p) > .9, xrayOverBody(p) > .9]; }})()")
    assert [who(-6), who(-8), who(3)] == [[True, False], [True, False], [False, False]]      # who stands on the tunnel's floor there is seen, as who is in your new room; not who is up on the land
    game.rpc("dev_teleport", x=X + 2, y=y, z=-6)              # from the tunnel, over it: the same column
    game.wait(f"myAt && myAt.x === {X + 2} && myAt.z === -6", 8000)
    game.wait(f"{DRAWN} && xray.pic && xray.pic.place.get('{X + 1},{y}') === -6 && xray.mix >= 1 && !xray.old", 20000)
    column(1, -8, 8); column(0, -9, 16)
    assert not game.errors


def test_under_a_roof_the_brink_of_a_floor_is_lit(game):
    """"path isn't obvious to player": six pictures of his cave on the mockup page, and "go with 4": the brink of a
    floor is lit, a px of it, where it drops to its own front or to the wall of the room south of it, and down its
    side where the floor beside it is lower. A stair is seen as steps. Not the middle of a floor, not its high side."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 3                 # a tunnel going up east a layer a tile; from its low end one going down south a layer
    for i, f in enumerate([-7, -6, -5, -4]): game.rpc("dev_col", tiles=[[X + i, y]], col=[f, f + 3, 3])
    game.rpc("dev_col", tiles=[[X, y + 1]], col=[-8, -5, 3])
    game.rpc("dev_teleport", x=X, y=y, z=-7)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -7", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    lum = lambda *a: game.js(AT, list(a))[2]
    for i, f in ((1, -6), (2, -5)):                           # a step of the stair: its west side and its foot are lit, its middle and its east side are not
        mid = lum(X + i, y, f, 8, 8)
        assert lum(X + i, y, f, 0, 8) > 1.2 * mid and lum(X + i, y, f, 8, 15) > 1.2 * mid and lum(X + i, y, f, 15, 8) < 1.1 * mid, (i, mid, lum(X + i, y, f, 0, 8), lum(X + i, y, f, 8, 15), lum(X + i, y, f, 15, 8))
    mid = lum(X, y, -7, 8, 8)                                 # your tile: its foot, over the wall of the room south of it; not its west side (rock)
    assert lum(X, y, -7, 8, 15) > 1.2 * mid and lum(X, y, -7, 0, 8) < 1.1 * mid, (mid, lum(X, y, -7, 8, 15), lum(X, y, -7, 0, 8))
    assert not game.errors
