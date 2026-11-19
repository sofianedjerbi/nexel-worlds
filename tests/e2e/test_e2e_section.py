"""The land cut open over the place you are hidden in is a section through blocks (web/js/vox_section.js, the cut:
xray.js): the walls of the hole stand, painted as the land's fronts are, the blocks that are sliced have a top, and
nothing of the picture is left to the flat fill that was all of it ("underground does not show any depth effect. we
should be able to see 3d holes"). (Which tiles are cut and who is seen: test_e2e_place.py, test_e2e_stacked.py.)"""

from test_e2e_digging import DRAWN, LAND, SEEN, cut, earth

FILL = [77, 54, 43]                                            # the cut's own colour (voxels.js cutMap: earth), as drawn by day


def fill_px(game):
    """How many px of the land's picture the engine had to fill flat: land left out with no face at all behind it."""
    game.js("(() => { Voxels.fillPx = -1; Voxels.probe = true; return 1; })()")
    game.wait("Voxels.fillPx >= 0", 8000)
    n = game.js("Voxels.fillPx")
    game.js("(() => { Voxels.probe = false; return 1; })()")
    return n


def under(game, x, y, z):
    game.rpc("dev_teleport", x=x, y=y, z=z)
    game.wait(f"myAt && myAt.x === {x} && myAt.y === {y} && myAt.z === {z}", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)


def test_the_wall_north_of_a_cut_floor_is_drawn_as_the_lands_front_not_the_fill(game):
    """A tunnel six down under the meadow, you in it. Its roof is lifted off: north of its floor the rock still
    stands up to the meadow, six levels, and its south face is there, earth in bands as any cliff's front (the
    tunnel's own two cells of wall, and the four over them that no face of the land's was made for: they were one
    flat dark slab). Nothing is left
    for the fill; and without the faces of the cut, it is: the count is not blind."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-5, 0, ["." * 6], levels=["f" * 6], roofs=["6" * 6], heads=["2" * 6]); game.stamp(1, 0, ["."], levels=["f"])
    under(game, x - 3, y, -6)
    assert game.js("Voxels.engine.section.faces") > 20
    wall = game.js(LAND, [[x + d, y, lv, 8, 3] for d in (-4, -3, -2) for lv in (0, -1, -2, -3, -4, -5)])
    assert all(c != FILL and c[0] > c[1] + 8 and c[0] > c[2] + 8 for c in wall), wall      # every level of it: earth
    assert all(earth(c) for c in wall[:2] + wall[6:8]), wall                               # its upper levels: as light as a front is, not the dark of a cut
    assert len({tuple(c) for c in wall}) >= 4, wall                                        # ...in bands, a shade darker a layer down: no flat slab
    seam = game.js(LAND, [[x - 3, y, lv, 8, 7] for lv in (0, -1, -2)])                      # the last px of a level: its seam, darker than its body
    assert all(sum(s) <= sum(b) for s, b in zip(seam, wall[6:9])) and any(sum(s) < sum(b) for s, b in zip(seam, wall[6:9])), (seam, wall[6:9])      # (a body's px may be a fleck as dark)
    floor = game.js(LAND, [[x - 3, y, -6, 8, 8]])[0]
    assert earth(floor), floor                                                             # the tunnel's floor
    assert fill_px(game) == 0
    # ...and with no faces made for the cut, the same place is thousands of px of fill
    game.js("(() => { VoxSection.build = () => ({...VoxMesh.pack([[]]), shapes: []}); return 1; })()")
    under(game, x - 2, y, -6)
    assert game.js("Voxels.engine.section.faces") == 0 and fill_px(game) > 2000
    assert not game.errors


def test_no_px_is_left_to_the_fill_in_two_rooms_one_over_the_other(game):
    """The worst of the flat fill: a pit with a hole under a tunnel (test_e2e_stacked.py), from the lower room and
    from the tunnel. The land is cut open, and every px of what was left out has a face behind it: a floor, a wall
    of the hole, a sliced top."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 4
    for i, col in ((-1, [-9, -4, 3]), (0, [-9, -7, -6, -4, 3]), (1, [-8, -7, -6, -4, 3]), (2, [-6, -4, 3]), (3, [-5, -3, 3])):
        game.rpc("dev_col", tiles=[[X + i, y]], col=col)
    under(game, X, y, -9)
    assert game.js("Voxels.engine.section.faces") > 20 and fill_px(game) == 0
    back = game.js(LAND, [[X, y, lv, 8, 3] for lv in (1, -1, -3)])                          # the wall behind your room, on up toward the hill's top
    assert all(c != FILL and c[0] > c[1] + 8 for c in back), back
    # the tile south of your floor is solid and cut down to it: its sliced top, the cut's colour (nine down: half a
    # tile of it shows before the meadow in front; the next ones, two levels higher a tile on, are drawn in that row)
    sliced = game.js(LAND, [[X, y + 1, -9, 8, 3]])[0]
    assert sliced == FILL, sliced
    under(game, X + 2, y, -6)
    assert fill_px(game) == 0
    assert not game.errors


def test_no_px_is_left_to_the_fill_on_a_stair_under_a_hill_and_behind_a_hill(game):
    """A stair dug down under a hill (test_e2e_underground.py), from half way and from its foot; then standing
    behind a hill five high, under no roof."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-9, -3, ["." * 10] * 7, levels=["3322110000"] * 7)
    game.stamp(-9, 0, ["." * 10], levels=["ffedcbba00"], roofs=["9976400000"], heads=["2222200000"])
    under(game, x - 6, y, -4)
    assert game.js("Voxels.engine.section.faces") > 20 and fill_px(game) == 0
    under(game, x - 8, y, -6)
    assert fill_px(game) == 0
    game.rpc("dev_teleport", x=x, y=y, z=0)
    game.wait(f"myAt && myAt.x === {x} && myAt.y === {y} && myAt.z === 0", 8000)
    game.clear_area(12)
    game.stamp(-3, 1, ["." * 7] * 3, levels=["5" * 7] * 3)                                # behind a hill
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js("xray.pic.cut.size") > 6 and fill_px(game) == 0
    assert not game.errors
