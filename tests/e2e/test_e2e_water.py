"""Clear water (the settings' Picture page, on by default; waterbed.js): the water is seen through to a bed the world
does not have: a water tile is a kind, and its bed is made from the distance to its banks (the HD look draws it:
vox_style.js; its pictures: test_e2e_hd_*)."""

READY = "(() => { const [vx, vy, vw, vh] = viewRect(2); for (let y = vy; y <= vy + vh; y += 8) for (let x = vx; x <= vx + vw; x += 8) { const b = blockOf(x, y); if (b && !Voxels.made(b)) return false; } return dirtyTiles.length === 0; })()"
DEPTHS = "([X, Y]) => { const o = []; for (let j = 0; j < 8; j++) for (let i = 0; i < 12; i++) o.push(WaterBed.depth(X + i, Y + j)); return o; }"


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
    game.js("setOpt('clearwater', false)"); game.frames(3)
    assert game.js("WaterBed.on") is False
    game.js("setOpt('clearwater', true)"); game.frames(3)
    assert game.js("WaterBed.on") is True and game.js(f"WaterBed.depth({x - 5}, {y - 5})") == 2
    game.stamp(-10, -9, ["." * 12] * 8, levels=["0" * 12] * 8)
