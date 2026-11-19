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
    game.flat()                                                  # (it reads art px of a wall three tiles up the picture: whole px on the flat one)
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
    game.js("(() => { VoxSection.build = () => ({...VoxMesh.pack([[]]), shapes: [], lit: []}); return 1; })()")
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
    # the tile south of your floor is solid and cut down to it: its sliced top (nine down: half a tile of it shows
    # before the meadow in front; the next ones, two levels higher a tile on, are drawn in that row). It is earth as
    # that level's front has it, in the day's light: the cut face of the ground, not a dark slab (a pit before the room)
    sliced = game.js(LAND, [[X, y + 1, -9, 8, 3]])[0]
    assert sliced != FILL and not cut(sliced) and earth(sliced), sliced
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
    assert game.js("xray.pic.cut.size") >= 3 and fill_px(game) == 0      # (your own column, the three rows of it)
    assert not game.errors


def test_the_front_of_a_hole_is_one_straight_edge_and_a_higher_floor_stands_on_its_block(game):
    """The pit, the hole under the tunnel and the tunnel's steps (test_e2e_stacked.py), from the lowest room. Each
    column was cut for its own floor: a dark square south of every step, a sill under the lowest floor alone ("a pit
    in front of the room"). The tiles in front are cut to the lowest of the row, all of them: one edge; a step's
    floor stands on its block, whose front is seen under it down to that edge: earth, as any front."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 4
    for i, col in ((-1, [-9, -4, 3]), (0, [-9, -7, -6, -4, 3]), (1, [-8, -7, -6, -4, 3]), (2, [-6, -4, 3]), (3, [-5, -3, 3])):
        game.rpc("dev_col", tiles=[[X + i, y]], col=col)
    under(game, X, y, -9)
    front = game.js(f"[-1, 0, 1, 2, 3].map((i) => [1, 2, 3].map((j) => xray.pic.cut.get(({X} + i) + ',' + ({y} + j))))")
    assert front == [[-9, -7, -5]] * 5, front                     # every column, a row at a time: as low as the lowest room needs
    assert fill_px(game) == 0
    # under the tunnel's floor (six down) and its step (five down), south of them: the front of the block they are on
    block = game.js(LAND, [[X + 2, y + 1, -7, 8, 3], [X + 2, y + 1, -8, 8, 3], [X + 3, y + 1, -6, 8, 3], [X + 3, y + 1, -8, 8, 3]])
    assert all(c != FILL and c[0] > c[1] + 8 and c[0] > c[2] + 8 for c in block), block
    floors = game.js(LAND, [[X + 2, y, -6, 8, 8], [X + 3, y, -5, 8, 8]])          # (and their floors over it, where they were)
    assert all(earth(c) for c in floors), floors
    # no dark earth anywhere in the row in front of the place: not the cut's flat colour, not a void
    row = game.js(LAND, [[X + i, y + 1, -9, ax, 3] for i in (-1, 0, 1, 2, 3) for ax in (2, 8, 13)])
    assert all(c != FILL and sum(c) > 200 for c in row), sorted(set(map(tuple, row)))      # (the sliced rock's body, and its dark flecks: nine down, [99, 70, 57])
    assert not game.errors


def test_one_wall_has_one_light(game):
    """A tunnel six down that opens into a pit three tiles wide at its east end, you in it. Its north wall and the
    pit's are one wall: the pit's is out of doors, so all of it is in the day's light, the tunnel's own two cells of
    wall as the cells cut through over them (they were in the cave's dark beside the pit's lit front: a seam down the
    wall). A room with no wall out of doors keeps the cave's dark. (A pit one tile wide is a shaft, dark the deeper
    it goes: no daylight for the tunnel either; test_e2e_holes.py.)"""
    game.flat()                                                  # (art px of a wall up the picture, as above)
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-5, 0, ["." * 6], levels=["f" * 6], roofs=["6" * 6], heads=["2" * 6]); game.stamp(1, -1, ["..."] * 3, levels=["fff"] * 3)
    under(game, x - 2, y, -6)
    mid = lambda px: sorted(px, key=sum)[len(px) // 2]            # (a level's body, whatever fleck one px of it is)
    at = lambda tx, ty, lv: mid(game.js(LAND, [[tx, ty, lv, ax, 2] for ax in (1, 4, 7, 10, 13)]))
    for lv in (-1, -3):                                          # over the tunnel (cut through), and the pit's wall beside it (a row further north)
        tunnel, pit = at(x - 1, y, lv), at(x + 2, y - 1, lv)
        assert abs(sum(tunnel) - sum(pit)) <= 12, (lv, tunnel, pit)
    cell = at(x - 1, y, -5)                                      # the tunnel's own cell of wall: no cave's dark on it (a third of the way to near black)
    assert sum(cell) > sum(at(x + 2, y - 1, -5)) - 30, cell
    lit = at(x - 1, y, -1)
    game.stamp(3, -1, ["..."] * 3, levels=["fff"] * 3, roofs=["666"] * 3, heads=["222"] * 3)            # (you are two tiles west of where you came) the pit roofed over: no wall of the place is out of doors
    game.wait(f"roofAt({x + 1}, {y}) === 6", 8000)
    under(game, x - 3, y, -6)
    dark = at(x - 1, y, -1)
    assert sum(dark) < sum(lit) - 25, (dark, lit)
    assert fill_px(game) == 0 and not game.errors


def test_a_sliced_top_is_the_rock_seen_inside_not_one_flat_colour(game):
    """On the floor of a gorge in stone, the wall in front of you, one tile thick, cut where it hides you and the floor beside you (a keyhole,
    xray.js: all eight tiles of it were cut to the floor, a dark mat; a wall one tile thick keeps a level, its foot): its sliced top is three tiles
    of rock. It was one flat colour (the level's wall-foot line: in stone a blank grey slab, "untextured"); it is the
    rock's own body with its flecks, a touch darker than the wall that still stands north of you, the same rock."""
    game.flat()                                                  # (art px of a wall a level up the picture: whole px on the flat one)
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-4, -3, ["." * 8] * 7, levels=["6" * 8] * 3 + ["0" * 8] + ["6" * 8] * 3)      # (three tiles thick: stone is a mass, a wall one tile thick is earth: voxpaint.js rocky)
    under(game, x, y, 0)
    lv = game.js(f"[-1, 0, 1].map((i) => xray.pic.cut.get(({x} + i) + ',' + ({y} + 1)))")
    assert lv[0] == lv[1] == lv[2] and lv[1] in (0, 1) and game.js("xray.pic.cut.size") < 20, lv      # (a keyhole: the three tiles at you, to the floor; a wall one tile thick would keep a level)
    top = [tuple(c) for c in game.js(LAND, [[x + i, y + 1, lv[1], ax, ay] for i in (-1, 0, 1) for ax in range(1, 15) for ay in range(2, 14)])]
    assert len(set(top)) >= 3, set(top)                           # its body, its light flecks, its dark ones
    mid = lambda px: sorted(px, key=sum)[len(px) // 2]
    body, wall = mid(top), mid(game.js(LAND, [[x + i, y, 2, ax, 3] for i in (-2, -1, 0, 1) for ax in range(1, 15)]))
    assert max(body) - min(body) < 30 and max(wall) - min(wall) < 30, (body, wall)      # stone, both: grey
    assert sum(wall) - 90 < sum(body) < sum(wall) - 15, (body, wall)                    # darker than the wall beside it, not black
    assert fill_px(game) == 0 and not game.errors


def test_the_ground_beside_the_opening_keeps_the_shadow_of_the_land_that_stands(game):
    """Under a slab on nothing (an overhang), in the morning: the slab is cut over your column alone, and the ground
    under its south row is in its shadow, your column's tile as the one beside it. The whole tile of the cut was lit
    evenly ("a light square in the slab's shadow"): only the px seen through the opening are (vox_section.js mark)."""
    game.flat()
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.3)
    game.stamp(-1, -1, ["...."] * 3, levels=["0000"] * 3, roofs=["4444"] * 3, heads=["3333"] * 3)
    under(game, x, y, 0)
    assert game.js(f"xray.pic.cut.get('{x},{y + 1}')") == 0 and not game.js("!!xray.pic.hole")
    mid = lambda px: sorted(px, key=sum)[len(px) // 2]
    at = lambda tx, ty: mid(game.js(LAND, [[tx, ty, 0, ax, ay] for ax in (2, 5, 8, 11, 14) for ay in (9, 11, 13)]))
    mine, beside, open_ = at(x, y + 1), at(x + 1, y + 1), at(x - 4, y + 1)
    assert abs(sum(mine) - sum(beside)) <= 40, (mine, beside)     # one shadow, across the cut's edge (the roof's own dark is a little less where it is lifted off)
    assert sum(mine) < sum(open_) - 90, (mine, open_)             # ...and it is a shadow: the meadow in the sun is far lighter
    assert not game.errors
