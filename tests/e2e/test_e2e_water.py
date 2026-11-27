"""Clear water (the settings' Picture page, on by default; waterbed.js): the water is seen through to a bed the world
does not have: a water tile is a kind, and its bed is made from the distance to its banks (the HD look draws it:
vox_style.js; its pictures: test_e2e_hd_*)."""

READY = "(() => { const [vx, vy, vw, vh] = viewRect(2); for (let y = vy; y <= vy + vh; y += 8) for (let x = vx; x <= vx + vw; x += 8) { const b = blockOf(x, y); if (b && !Voxels.made(b)) return false; } return dirtyTiles.length === 0; })()"
DEPTHS = "([X, Y]) => { const o = []; for (let j = 0; j < 8; j++) for (let i = 0; i < 12; i++) o.push(WaterBed.depth(X + i, Y + j)); return o; }"


RESET = "(() => { setOpt('clearwater', true); setOpt('shimmer', true); return 1; })()"

def test_a_pillar_and_an_islet_standing_in_a_pond_do_not_change_the_bed_round_them(game):
    """The bed is deeper by the distance to the water's banks, not to what stands in it: a step down round every pillar
    and islet was a quilt of squares. A tile beside the pillar is as deep as one three tiles from it at the same
    distance from the bank."""
    game.clear_area(10)
    game.stamp(-11, -10, ["."] * 10)                                              # (a bank west of the pond: its first column is the cleared meadow's last, and water there, the world's or a test's before, made that rim two deep)
    game.stamp(-10, -9, ["~" * 12] * 8); x, y = game.pos(); game.wait(READY, 20000); game.rest()
    X, Y = x - 10, y - 9                                                          # the pond's corner
    before = game.js(DEPTHS, [X, Y])
    assert before == [1 if i in (0, 11) or j in (0, 7) else 2 for j in range(8) for i in range(12)]      # a rim one deep, then one basin
    game.stamp(-6, -6, ["-"], levels=["3"]); game.stamp(-2, -6, ["..", ".."])      # a stone pillar, an islet of four tiles
    game.wait(READY, 20000); game.rest()
    after = game.js(DEPTHS, [X, Y])
    land = {(4, 3), (8, 3), (9, 3), (8, 4), (9, 4)}
    assert all(a == (0 if (i % 12, i // 12) in land else b) for i, (a, b) in enumerate(zip(after, before))), after
    game.stamp(-10, -9, ["." * 12] * 8, levels=["0" * 12] * 8)


def test_the_water_setting_turns_the_bed_on_and_off(game):
    """Clear water off: no bed (the water one face); on again: the bed as it was."""
    game.clear_area(10)
    game.stamp(-10, -9, ["~" * 12] * 8); x, y = game.pos(); game.wait(READY, 20000); game.rest()
    assert game.js("WaterBed.on") is True
    game.js("setOpt('clearwater', false)"); game.rest()
    assert game.js("WaterBed.on") is False
    game.js("setOpt('clearwater', true)"); game.rest()
    assert game.js("WaterBed.on") is True and game.js(f"WaterBed.depth({x - 5}, {y - 5})") == 2
    game.stamp(-10, -9, ["." * 12] * 8, levels=["0" * 12] * 8)


def test_a_river_just_made_in_a_gorge_shows_its_water_round_you_in_the_hd_look(browser, server):
    """A river laid where a meadow was (a gorge's floor, cliffs both sides: the eye from above): round you it is
    water, its face tinted over its bed. A tile that became water kept its answer "land" (waterbed.js) until the beds'
    next look, which waits for the tiles drawn to run out, and the HD look made its chunk from it at once: a slab at the
    water's face round you, a flat beige strip (200, 165, 120), as long as what was made before that look (it changed
    from run to run: tools/lookcheck.py's gorge). Here that look is held back until the land is made."""
    from test_e2e_hd_sun import hd
    from test_e2e_hd_trench import TILE
    g = hd(browser, server)
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer"):
        g.js(f"setOpt('{o}', 0)")
    g.js(RESET.replace("setOpt('shimmer', true); ", ""))
    x, y = g.pos()
    # the river's face on the tiles beside you, your own row and the one north of it (the south one: under its bank's lip from up here)
    face = "([x, y, T]) => { const f = eval(T), o = []; for (const dy of [-1, 0]) for (const dx of [-4, -3, -2, 2, 3, 4]) o.push([dx, dy, ...f([x + dx, y + dy, 2])]); return o; }"
    dry = lambda o: [c for c in o if c[4] <= c[2] + 25]                           # (water: blue over red)
    # the meadow's columns as the land asks for them while it is made (kept); then the beds' next look held back
    g.js("([x, y]) => { for (let j = y - 2; j <= y + 2; j++) for (let i = x - 12; i <= x + 12; i++) Voxels.host.column(i, j); const f0 = WaterBed.flush; window.__hold = () => { WaterBed.flush = f0; return 1; }; WaterBed.flush = () => {}; WayShow.paint = () => {}; return 1; }", [x, y])
    g.stamp(-11, -11, ["." * 23] * 10 + ["(" * 23] * 3 + ["." * 23] * 10, levels=["9" * 23] * 10 + ["2" * 23] * 3 + ["6" * 23] * 10)
    g.rpc("dev_teleport", x=x, y=y)
    g.wait("HdLook.cam.pitch > HdLook.steep - .1 && !HdLook.busy && HdLook.level[0] === 2 && !dirtyTiles.length", 8000)      # (the tiles all drawn: the land made of them)
    g.rest()
    g.wait("!HdLook.busy && !dirtyTiles.length", 8000)
    held = g.js(face, [x, y, TILE])
    g.js("__hold()")
    assert dry(held) == [], held                                                 # (it was (200, 165, 120) on your row, (170, 142, 104) north of it)
    g.arrive()
    g.rest()
    got = g.js(face, [x, y, TILE])
    assert dry(got) == [], got
    g.js(RESET)
