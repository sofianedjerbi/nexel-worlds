"""The land is blocks (voxels.js and the engine in vox_*.js): the world's cells drawn as blocks by the GPU, laid on
the game's canvas, where everything else is drawn over it."""

# the colour of the game's canvas at a point of the world: a tile's middle, `up` art px over where its top is drawn
AT = """([x, y, dy]) => { const S = TS(), [ox, oy] = screenOrigin(S), d = ctx.getImageData(Math.round((ox + x * S + S / 2) * DPR), Math.round((oy + y * S + S / 2 - liftAt(x, y) + dy * zoom) * DPR), 1, 1).data; return [d[0], d[1], d[2]]; }"""

# ...and at an art px (i, j) of a tile, as it is drawn `up` levels high
PX = """([x, y, i, j, up]) => { const S = TS(), [ox, oy] = screenOrigin(S), d = ctx.getImageData(Math.round((ox + x * S + (i + .5) * zoom) * DPR), Math.round((oy + y * S + (j + .5 - up * RELIEF_STEP) * zoom) * DPR), 1, 1).data; return [d[0], d[1], d[2]]; }"""
green = lambda c: c[1] > c[0] + 15 and c[1] > c[2] + 15
earth = lambda c: c[0] > c[1] + 15 and c[0] > c[2] + 15


def blocks(game):
    game.wait("(() => { const b = blockOf(myPos().x, myPos().y); return Voxels.made(b); })() && dirtyTiles.length === 0", timeout=15000)
    game.sleep(300)


def test_the_land_is_drawn_as_blocks_where_it_was_painted(game):
    """A hill three high north of you: its top is where things on it are drawn, its front hangs under its south edge,
    and the ground before it is still the meadow."""
    game.flat()                                                  # (it counts the art px of faces north of you: whole px on the flat picture only)
    x, y = game.pos()
    game.stamp(-2, -5, ["....."] * 2, levels=["33333"] * 2)
    blocks(game)
    top, front, meadow = game.js(AT, [x, y - 4, 0]), game.js(AT, [x, y - 4, 16 + 12]), game.js(AT, [x, y - 2, 0])
    assert game.js("Voxels.engine.faces") > 1000
    assert green(top) and green(meadow)
    assert front[0] > front[1] + 15 and front[0] > front[2] + 15, front      # earth: its front, a level and a half under its edge


def test_land_that_changes_is_made_again(game):
    """A hill stamped while the land is blocks is there at once: its tiles painted again, its block's faces made again."""
    game.flat()                                                  # (it counts the art px of faces north of you: whole px on the flat picture only)
    x, y = game.pos()
    blocks(game)
    before = game.js("Voxels.engine.faces")
    game.stamp(-1, -4, ["..."], levels=["222"])
    game.wait("dirtyTiles.length === 0")
    game.sleep(400)
    # three tiles, two cells of front each; and at each end of it its thin side (its dark line and its wall: two
    # faces): a strip beside its top and a front a level
    assert game.js("Voxels.engine.faces") == before + 6 + 2 * (1 + 2) * 2
    front = game.js(AT, [x, y - 4, 16 + 3])
    assert front[0] > front[1] + 15


def test_a_block_shows_its_sides_where_the_land_drops(game):
    """A hill three high: every side of it tells its height. Its top has the sheet's lip along the edges where the
    land is lower (earth round the grass, west, east and north as well as south); west and east, where no face is in
    view, it shows a thin side for its whole height, in the px its cap leaves empty (the block is no wider than its
    tile); the ground is green past it."""
    game.flat()                                                  # (it counts the art px of faces north of you: whole px on the flat picture only)
    x, y = game.pos()
    game.stamp(-2, -5, ["....."] * 2, levels=["33333"] * 2)
    blocks(game)
    assert game.js("Voxels.engine.sides") >= 4                  # two rows, two sides
    at = lambda *q: game.js(PX, list(q))
    lip = [at(x - 2, y - 4, 3, 6, 3), at(x + 2, y - 4, 12, 6, 3)]      # its west tile's top, its east tile's: the lip
    assert all(earth(c) for c in lip) and green(at(x, y - 4, 8, 6, 3)), lip
    # beside its south row's top, in its own tile: its side (the wall), west and east; the tile past it is the meadow
    side = [at(x - 2, y - 4, 1, 8, 3), at(x + 2, y - 4, 14, 8, 3)]
    past = [at(x - 3, y - 4, 15, 8, 3), at(x + 3, y - 4, 0, 8, 3)]
    assert all(earth(c) for c in side) and not any(earth(c) for c in past), (side, past)
    # a hill one high has its lip (west, north) and its side too, at each end: every block is a box
    before, faces = game.js("Voxels.engine.sides"), game.js("Voxels.engine.faces")
    game.stamp(-2, 3, ["..."], levels=["111"])
    # (waited for, not looked at once: the stamp's three tiles come one by one, and the faces are made again at each: one side was there before the other)
    game.wait("dirtyTiles.length === 0 && Voxels.engine.faces > %d && Voxels.engine.sides === %d" % (faces, before + 2))
    lip, far, top = at(x - 2, y + 3, 3, 8, 1), at(x - 1, y + 3, 8, 1, 1), at(x - 1, y + 3, 8, 6, 1)
    grass = lambda c: c[1] > c[0] + 8 and c[1] > c[2] + 15      # (its top's px may be one of the meadow's light patches: yellower, still grass)
    assert earth(lip) and not earth(at(x - 3, y + 3, 4, 8, 0)) and grass(top) and green(far) and sum(far) < sum(top) - 30, (lip, far, top)      # (north: the sheet's dark line)


def test_a_shader_and_the_night_are_over_the_blocks_as_over_the_painted_land(game):
    """The blocks' picture is on the game's own canvas: a shader repaints it, the night darkens it."""
    x, y = game.pos()
    blocks(game)
    day = game.js(AT, [x + 3, y, 0])
    game.rpc("dev_time", phase=.9)
    game.wait("clock.phase > .85")
    game.sleep(500)
    night = game.js(AT, [x + 3, y, 0])
    assert sum(night) < sum(day) * .8, (day, night)
    game.rpc("dev_time", phase=.3)
    game.js("setOpt('shader', 'natural')")
    game.sleep(500)
    look = "(() => { const c = document.createElement('canvas'); c.width = 8; c.height = 8; const g = c.getContext('2d'); g.drawImage(Shader.el, Shader.el.width / 2 + 100, Shader.el.height / 2, 8, 8, 0, 0, 8, 8); const d = g.getImageData(4, 4, 1, 1).data; return [d[0], d[1], d[2]]; })()"
    game.js("window.shot = null; requestAnimationFrame(() => requestAnimationFrame(() => { window.shot = " + look + "; }))")      # (read in the frame it was drawn in)
    game.wait("window.shot")
    seen = game.js("window.shot")
    assert seen[1] > 100 and seen[1] > seen[2], seen             # the meadow, through the shader


def test_blocks_cost_little_of_a_frame(game):
    """Standing still on land that is there, a frame's own work stays small with the land as blocks."""
    blocks(game)
    game.sleep(500)
    ms = game.js("new Promise((ok) => { const out = [], of = window.frame; window.frame = (now) => { const a = performance.now(); of(now); out.push(performance.now() - a); if (out.length >= 90) { window.frame = of; ok(out); } }; })")
    ms.sort()
    assert ms[len(ms) // 2] < 6 and ms[int(len(ms) * .95)] < 12, ms[-5:]
