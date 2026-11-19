"""What you aim at is shown as the block it is (web/js/mark.js, the engine's vox_mark.js): "block selection is
messy. it is still 2d. make the hint highlight the 3d block properly". The cell a click would dig or fill, as a
box in the land: its top at the block's own level, its front down to the land before it, hidden where nearer land
hides it, bent with the curved world; and it is the cell the action changes."""
import pytest

# where a point of the land is on the screen: tile (x, y) and (ax, ay) art px into it, `lv` levels up: the game's own function
AT = """([x, y, ax, ay, lv]) => { const S = TS(), [ox, oy] = screenOrigin(S); return [ox + x * S + ax * zoom, Curve.y(oy + (y + ay / 16) * S, shOf(lv) * zoom)]; }"""
PIXEL = """([x, y]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const d = ctx.getImageData(Math.round(x * DPR), Math.round(y * DPR), 1, 1).data; ok([d[0], d[1], d[2]]); })))"""
MARK = "Marks.list.map((m) => [m.to.x, m.to.y, m.to.z0, m.to.z1])"
pale = lambda c: min(c) > 205 and c[0] >= c[2]                    # the selector's own colour (#fff8e8), not the meadow, not earth


def mode(game, m):
    game.js(f"(() => {{ Curve.force = '{m}'; return 1; }})()")
    game.wait("Curve.on" if m != "off" else "!Curve.on")
    game.wait("(() => { const b = blockOf(myPos().x, myPos().y); return Voxels.made(b); })() && dirtyTiles.length === 0", timeout=15000)
    game.sleep(300)


def point(game, x, y, lv):
    """The mouse on the top of tile (x, y) at level lv, a third down it."""
    px, py = game.js(AT, [x, y, 8, 5, lv])
    game.page.mouse.move(px, py)
    game.wait("Marks.list.length === 1 && Marks.list[0].a >= 1 && ['x', 'y', 'z0', 'z1'].every((f) => Math.abs(Marks.list[0][f] - Marks.list[0].to[f]) < .01)", timeout=4000)      # (there: it glides)


def corner(game, x, y, ax, ay, lv, dx, dy):
    """Is the selector's colour at the corner of a box: in the two px of paint outside the point (dx, dy: which way
    out), where it is at rest or where its breath puts it. Read in one frame (it breathes)."""
    px, py = game.js(AT, [x, y, ax, ay, lv])
    got = game.js("""([px, py, dx, dy]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const out = [];
      for (const k of [.5, 1.5]) for (const j of [.5, 1.5]) { const d = ctx.getImageData(Math.round((px + dx * k * zoom) * DPR), Math.round((py + dy * j * zoom) * DPR), 1, 1).data; out.push([d[0], d[1], d[2]]); } ok(out); })))""", [px, py, dx, dy])
    return any(pale(c) for c in got), got


@pytest.mark.parametrize("curve", ["off", "far"])
def test_the_hint_is_the_block_its_top_at_its_level_and_its_front_down_to_the_land_before_it(game, curve):
    """The south edge of a plateau three high, aimed at from below: the box's top is the block's top, three levels
    up (its far corners' brackets are drawn there, where the game's own function puts that level), and its front
    goes down the wall to the meadow (its feet's brackets are at the wall's foot). Flat, and in the curved world."""
    x, y = game.pos()
    game.give(hoe=1)
    game.hold_item("hoe")
    mode(game, curve)
    game.stamp(2, -5, ["...."] * 3, levels=["3333"] * 3)
    game.wait("dirtyTiles.length === 0")
    game.sleep(500)
    point(game, x + 3, y - 3, 3)
    assert game.js(MARK) == [[x + 3, y - 3, 0, 3]]               # the block, from its top down to the land before it
    for ax, dx in ((0, -1), (16, 1)):
        top, far = corner(game, x + 3, y - 3, ax, 0, 3, dx, -1)
        foot, low = corner(game, x + 3, y - 3, ax, 16, 0, dx, 1)
        assert top and foot, (curve, ax, far, low)
    # and on the level: the block of the meadow under the pointer, its top alone in view
    point(game, x + 1, y - 1, 0)
    assert game.js(MARK) == [[x + 1, y - 1, -1, 0]]
    assert corner(game, x + 1, y - 1, 0, 0, 0, -1, -1)[0] and corner(game, x + 1, y - 1, 16, 0, 0, 1, -1)[0]


def test_nearer_land_hides_the_hint_as_it_hides_the_block(game):
    """A block just north of a plateau three high is behind it: nothing of its box is drawn over the plateau; the
    same box where nothing is in front of it is drawn."""
    x, y = game.pos()
    mode(game, "off")
    game.stamp(2, -4, ["...."] * 3, levels=["3333"] * 3)
    game.wait("dirtyTiles.length === 0")
    game.sleep(500)
    spots = [game.js(AT, [x + 3, y - 5, ax, ay, 0]) for ax, ay in ((-.5, -.5), (16.5, -.5), (8, 8))]
    before = [game.js(PIXEL, p) for p in spots]
    box = lambda bx: f"(() => {{ Marks.force = [{{x: {bx}, y: {y - 5}, z0: -1, z1: 0, colour: [1, .973, .91]}}]; return 1; }})()"
    game.js(box(x + 3))
    game.wait("Marks.list.length === 1 && Marks.list[0].a >= 1")
    game.sleep(300)
    assert [game.js(PIXEL, p) for p in spots] == before          # behind the plateau: not a px of it
    game.js(box(x - 3))
    game.sleep(500)
    assert corner(game, x - 3, y - 5, 0, 0, 0, -1, -1)[0] and corner(game, x - 3, y - 5, 16, 0, 0, 1, -1)[0]      # in the open: its far corners
    game.js("(() => { Marks.force = null; return 1; })()")


def test_the_cell_shown_is_the_cell_the_action_changes(game):
    """Earth in hand: the hint is the empty cell over the meadow, a level high, and a click raises the ground into
    exactly that cell. The build cursor in the mode: the block it is on, and X digs that block."""
    x, y = game.pos()
    game.give(dirt=3)
    game.hold_item("dirt")
    point(game, x + 1, y - 1, 0)
    assert game.js(MARK) == [[x + 1, y - 1, 0, 1]]               # the cell over the ground
    game.page.mouse.down(); game.page.mouse.up()
    game.wait(f"topAt({x + 1}, {y - 1}) === 1", timeout=8000)    # ...is the cell that is earth now
    game.page.mouse.move(5, 5)
    game.press("b")
    game.js(f"(() => {{ Build.S.at = {{x: {x - 1}, y: {y - 1}}}; return 1; }})()")
    game.wait(f"Marks.list.length === 1 && Marks.list[0].to.x === {x - 1}")
    assert game.js(MARK) == [[x - 1, y - 1, -1, 0]]              # the block the cursor is on
    game.press("x")
    game.wait(f"topAt({x - 1}, {y - 1}) === -1", timeout=10000)  # ...is the block that is dug
