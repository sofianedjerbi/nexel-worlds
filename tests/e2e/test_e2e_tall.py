"""The land goes from -512 to 512 ("please make the underground reach -512 and the sky max block should be 512 too":
web/js/cells.js, a column as the heights where it changes), and what the screen shows far under the land or far
over it (state.js: away; render.js)."""

DRAWN = "dirtyTiles.length === 0"


def corridor(game, x, y, depth, top=0, n=6):
    """A corridor west to east under the land, two cells high, its floor at `depth`."""
    game.rpc("dev_col", tiles=[[x + i, y] for i in range(n)], col=[depth, depth + 2, top])


def test_the_page_reads_land_from_a_server_from_before(game):
    """A server from before sends a height as the char 64 + it and a column as 32 bits from -16 up; so does the
    first screen's island, kept in the page. Both are read into the taller column as the land they were."""
    out = game.js("""(() => { const rows = Array(32).fill('.'.repeat(32)), levels = Array(32).fill('@'.repeat(32));
      levels[0] = 'D@8' + '@'.repeat(29);                       // a hill four high, the sea's level, a pit eight deep
      onRegion({x: 32000, y: 32000, w: 32, h: 32, rows, ground: rows, levels, cols: {"3": (1 << 21) - 1 & ~(3 << 17)}});
      const at = (i) => [floorAt(32000 + i, 32000), topAt(32000 + i, 32000), colAt(32000 + i, 32000)];
      return [at(0), at(1), at(2), at(3), colIn(0xFFFFFFFF), colIn([7]) === colSolid(7), surfacesAt(32003, 32000), landSolid(32003, 32000, 1), landSolid(32003, 32000, 3)]; })()""")
    assert out == [[4, 4, [4]], [0, 0, [0]], [-8, -8, [-8]], [0, 4, [0, 2, 4]], [15], True, [0, 4], False, True]
    assert not game.errors


def test_far_under_the_land_your_tiles_are_there_and_the_land_rows_away_is_left(game):
    """Forty layers down the page took the land twenty rows south of where you are; at a hundred it had let go of the
    tiles you stood on. Within two dozen layers of the land round you, nothing changes; further, the land is left
    (state.js away) and your own tiles are there (the HD look draws you in your corridor: test_e2e_hd_*)."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    corridor(game, x + 2, y, -20); corridor(game, x + 2, y + 3, -60); corridor(game, x + 2, y + 6, -500)
    for depth, row, far in ((-20, y, False), (-60, y + 3, True), (-500, y + 6, True)):
        game.rpc("dev_teleport", x=x + 4, y=row, z=depth)
        game.wait(f"myAt && myAt.y === {row} && myAt.z === {depth}", 8000)
        game.wait(f"{DRAWN} && away.a === {1 if far else 0}", 20000); game.rest()
        assert game.js("!!blockOf(myAt.x, myAt.y) && Voxels.made(blockOf(myAt.x, myAt.y))"), depth      # your tiles are here
    assert not game.errors


def test_high_over_the_land_the_sky_is_behind_you(game):
    """On top of what stands far over the land beside it, the land rows away is left: the sky is behind you (away.high)."""
    game.clear_area(10)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.rpc("dev_col", tiles=[[x + 3 + i, y + j] for i in range(2) for j in range(2)], col=[200])       # a pillar two hundred high
    game.rpc("dev_teleport", x=x + 3, y=y, z=200)
    game.wait(f"myAt && myAt.x === {x + 3} && myAt.z === 200", 8000)
    game.wait(f"{DRAWN} && away.high", 20000); game.sleep(600)
    assert game.js("[!!blockOf(myAt.x, myAt.y), topAt(myAt.x, myAt.y)]") == [True, 200]
    assert not game.errors
