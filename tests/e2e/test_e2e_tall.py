"""The land goes from -512 to 512 ("please make the underground reach -512 and the sky max block should be 512 too":
web/js/cells.js, a column as the heights where it changes), and what the screen shows far under the land or far
over it (state.js: away; render.js, xray.js)."""

from test_e2e_digging import DRAWN, SEEN

# the screen without anybody on it -> the colours [r, g, b] of some px, each (x, y) a share of the screen
SCREEN = """(spots) => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
  frame(performance.now()); const out = spots.map(([u, v]) => Array.from(ctx.getImageData(Math.round(cv.width * u), Math.round(cv.height * v), 1, 1).data).slice(0, 3));
  Object.assign(window, keep); return out; }"""


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
      return [at(0), at(1), at(2), at(3), colIn(0xFFFFFFFF), colIn([7]) === colSolid(7), surfacesAt(32003, 32000), landSolid(32003, 32000, 1), landSolid(32003, 32000, 3), ceilAt(32003, 32000, 0)]; })()""")
    assert out == [[4, 4, [4]], [0, 0, [0]], [-8, -8, [-8]], [0, 4, [0, 2, 4]], [15], True, [0, 4], False, True, 2]
    assert not game.errors


def test_far_under_the_land_the_screen_is_where_you_are_not_the_land_rows_away(game):
    """Forty layers down you are drawn twenty rows south of where you are: the corridor showed in the middle of
    whatever land is there, a forest twenty tiles away; at a hundred the page had let go of the tiles you stood on, and
    at five hundred you were not there at all. Within two dozen layers of the land drawn round you, nothing changes;
    further, that land is not drawn: earth, and the place you are in, seen as anywhere under a roof."""
    game.clear_area(12)
    game.js("Underground.force = 0")   # (the land as the game paints it: the underground view, underground.js, is laid over it)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    corridor(game, x + 2, y, -20); corridor(game, x + 2, y + 3, -60); corridor(game, x + 2, y + 6, -500)
    spots = [[.1, .2], [.9, .2], [.1, .8], [.9, .8]]
    for depth, row, far in ((-20, y, False), (-60, y + 3, True), (-500, y + 6, True)):
        game.rpc("dev_teleport", x=x + 4, y=row, z=depth)
        game.wait(f"myAt && myAt.y === {row} && myAt.z === {depth}", 8000)
        game.wait(f"{DRAWN} && away.a === {1 if far else 0}", 20000); game.wait(SEEN, 20000); game.rest()
        px = game.js(SCREEN, spots)
        if far:
            assert all(p == [43, 36, 32] for p in px), (depth, px)                       # earth: none of the land's green
        else:
            assert all(g > r for r, g, b in px), (depth, px)                             # the meadow, as ever
        st = game.js("({mine: !!blockOf(myAt.x, myAt.y), floor: xray.pic.floor.size, seen: seenUnder(myAt.x, myAt.y), shows: xrayShows(ents.get('agent' + myId)) > .9})")
        assert st == {"mine": True, "floor": 6, "seen": depth, "shows": True}, (depth, st)   # your tiles are here; the corridor is the place you are in; you are seen
        body = game.js("""() => { const S = TS(), [ox, oy] = screenOrigin(S), p = ents.get('agent' + myId), at = () => Array.from(ctx.getImageData(Math.round((ox + (p.x + .5) * S) * DPR), Math.round((oy + (p.y + .45) * S - liftOf(p)) * DPR), 1, 1).data).slice(0, 3).join();
          frame(performance.now()); const on = at(), keep = drawEntity; drawEntity = () => null; frame(performance.now()); const off = at(); drawEntity = keep; return on !== off; }""")
        assert body, depth                                    # (and drawn: at five hundred you were not)
    assert not game.errors


def test_high_over_the_land_the_sky_is_behind_you(game):
    """On top of what stands far over the land beside it, the screen round you is not land rows away: the sky."""
    game.clear_area(10)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.rpc("dev_col", tiles=[[x + 3 + i, y + j] for i in range(2) for j in range(2)], col=[200])       # a pillar two hundred high
    game.rpc("dev_teleport", x=x + 3, y=y, z=200)
    game.wait(f"myAt && myAt.x === {x + 3} && myAt.z === 200", 8000)
    game.wait(f"{DRAWN} && away.high", 20000); game.sleep(600)
    assert game.js("[!!blockOf(myAt.x, myAt.y), topAt(myAt.x, myAt.y)]") == [True, 200]
    # (the curved world's own sky, or under its horizon the far hills' colour: no land, no earth's dark; flat, it was one colour, [168, 216, 234])
    got = game.js(SCREEN, [[.1, .1], [.9, .1], [.1, .9]])
    assert all(p[2] > p[0] + 20 or min(p) > 225 or (p[1] > p[0] and p[2] > p[0]) for p in got), got
    assert not game.errors
