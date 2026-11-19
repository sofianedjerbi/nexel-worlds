"""What you aim at is shown as the block it is (web/js/mark.js, the engine's vox_mark.js): "block selection is
messy. it is still 2d. make the hint highlight the 3d block properly". The cell a click would dig or fill, as a
box in the land: its top at the block's own level, its front down to the land before it, hidden where nearer land
hides it, bent with the curved world; and it is the cell the action changes."""
import pytest

# where a point of the land is on the screen: tile (x, y) and (ax, ay) art px into it, `lv` levels up: the game's own function
AT = """([x, y, ax, ay, lv]) => { const S = TS(), [ox, oy] = screenOrigin(S); return [ox + x * S + ax * zoom, VoxCurve.snap(Curve.c, oy + (y + ay / 16) * S, shOf(lv) * zoom, oy, zoom)]; }"""      # (in the roll: on a whole px of the paint, as the land is)
PIXEL = """([x, y]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const d = ctx.getImageData(Math.round(x * DPR), Math.round(y * DPR), 1, 1).data; ok([d[0], d[1], d[2]]); })))"""
MARK = "Marks.list.map((m) => [m.to.x, m.to.y, m.to.z0, m.to.z1])"
pale = lambda c: min(c) > 205 and c[0] >= c[2]                    # the selector's own colour (#fff8e8), not the meadow, not earth


def mode(game, m):
    game.js(f"(() => {{ Curve.force = '{m}'; setOpt('names', false); return 1; }})()")      # (no names: your own, over your head, is on the corner of the tile north-east of you, where a box's edge is read)
    game.wait("Curve.on" if m != "off" else "!Curve.on")
    game.wait("(() => { const b = blockOf(myPos().x, myPos().y); return Voxels.made(b); })() && dirtyTiles.length === 0", timeout=15000)
    game.sleep(300)


def point(game, x, y, lv):
    """The mouse on the top of tile (x, y) at level lv, a third down it."""
    px, py = game.js(AT, [x, y, 8, 5, lv])
    game.page.mouse.move(px, py)
    game.wait("Marks.list.length === 1 && Marks.list[0].a >= 1 && ['x', 'y', 'z0', 'z1'].every((f) => Math.abs(Marks.list[0][f] - Marks.list[0].to[f]) < .01)", timeout=4000)      # (there: it glides)


def corner(game, x, y, ax, ay, lv, dx, dy):
    """Is the selector's colour at the corner of a box: on the px of paint of the cell's own corner (its outline, at
    rest) or the one outside it (dx, dy: which way out; where its breath puts it). Read in one frame (it breathes)."""
    px, py = game.js(AT, [x, y, ax, ay, lv])
    got = game.js("""([px, py, dx, dy]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const out = [];
      for (const k of [-.5, .5]) for (const j of [-.5, .5]) { const d = ctx.getImageData(Math.round((px + dx * k * zoom) * DPR), Math.round((py + dy * j * zoom) * DPR), 1, 1).data; out.push([d[0], d[1], d[2]]); } ok(out); })))""", [px, py, dx, dy])
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
    assert game.js(MARK) == [[x + 1, y - 1, -1, 0]] and game.js("Marks.list[0].to.flat")      # (its front is behind the land before it: a tile's top)
    west, east = corner(game, x + 1, y - 1, 0, 0, 0, -1, -1), corner(game, x + 1, y - 1, 16, 0, 0, 1, -1)
    assert west[0] and east[0], (curve, west, east)


PIXELS = """(pts) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { const g = ctx.getImageData(0, 0, cv.width, cv.height).data;
  ok(pts.map(([x, y]) => { const i = (Math.floor(y * DPR) * cv.width + Math.floor(x * DPR)) * 4; return [g[i], g[i + 1], g[i + 2]]; })); })))"""
FORCE = "(c) => { Marks.force = c && [{...c, colour: [1, .973, .91]}]; return 1; }"


def line(game, x, y, pts, lv):
    """Where the px of paint (ax, ay) of tile (x, y), `lv` levels up, are on the screen: each one's own px, and the
    one beside it `out` px of paint off ([ax, ay, ox, oy]: where a breath puts an edge)."""
    return [(game.js(AT, [x, y, ax + .5, ay + .5, lv]), game.js(AT, [x, y, ax + .5 + ox, ay + .5 + oy, lv])) for ax, ay, ox, oy in pts]


def drawn(game, spots, before):
    """Which of the spots (pairs: a px and the one a breath puts it on) are not the land's own colour: one frame."""
    flat = [p for pair in spots for p in pair]
    now = game.js(PIXELS, flat)
    return [now[2 * i] != before[2 * i] or now[2 * i + 1] != before[2 * i + 1] for i in range(len(spots))]


def test_the_box_is_the_four_edges_of_its_top_and_the_two_uprights_and_the_foot_of_its_front(game):
    """ "The aim box reads 2D: corner brackets with a faint fill": the block at the south edge of a plateau three
    high: every px of paint along the four edges of its top is drawn (a full outline, not brackets), every px down
    the two uprights of its front and along the front's foot, and its top is washed lighter than it was."""
    x, y = game.pos()
    mode(game, "off")
    game.js("(() => { setOpt('shader', 'off'); return 1; })()")
    game.stamp(2, -5, ["...."] * 3, levels=["3333"] * 3)
    game.wait("dirtyTiles.length === 0")
    game.sleep(500)
    bx, by = x + 3, y - 3
    top = line(game, bx, by, [(a, 0, 0, -1) for a in range(16)] + [(a, 15, 0, 1) for a in range(16)] + [(0, a, -1, 0) for a in range(1, 15)] + [(15, a, 1, 0) for a in range(1, 15)], 3)
    front = [p for lv in (.5, 1, 1.5, 2, 2.5) for p in line(game, bx, by + 1, [(0, -1, -1, 0), (15, -1, 1, 0)], lv)] + line(game, bx, by + 1, [(a, -1, 0, 1) for a in range(16)], 0)
    mid = game.js(AT, [bx, by, 8.5, 8.5, 3])
    before = game.js(PIXELS, [p for pair in top + front for p in pair] + [mid])
    game.js(FORCE, {"x": bx, "y": by, "z0": 0, "z1": 3, "a": 1})
    game.wait("Marks.list.length === 1 && Marks.list[0].a >= 1")
    game.sleep(300)
    got = drawn(game, top + front, before)
    assert all(got[:len(top)]), ("the top's edges", got[:len(top)])
    assert all(got[len(top):]), ("the front's uprights and foot", got[len(top):])
    assert sum(game.js(PIXELS, [mid])[0]) > sum(before[-1])      # its top: washed with the selector's light colour
    game.js(FORCE, None)


def test_what_nearer_land_hides_of_the_hint_is_dotted_through_the_land_not_absent(game):
    """ "Behind a plateau nothing shows at all": a block just north of a plateau three high is behind it: its box is
    drawn through the plateau as a dotted outline, a px of paint on and a px off along each edge, and no wash; the
    same box where nothing is in front of it is a full outline."""
    x, y = game.pos()
    mode(game, "off")
    game.js("(() => { setOpt('shader', 'off'); return 1; })()")
    game.stamp(2, -4, ["...."] * 3, levels=["3333"] * 3)
    game.wait("dirtyTiles.length === 0")
    game.sleep(500)
    edge = lambda bx: line(game, bx, y - 5, [(a, 0, 0, -1) for a in range(16)] + [(0, a, -1, 0) for a in range(1, 15)], 0)
    hid, mid = edge(x + 3), game.js(AT, [x + 3, y - 5, 8.5, 8.5, 0])
    before = game.js(PIXELS, [p for pair in hid for p in pair] + [mid])
    game.js(FORCE, {"x": x + 3, "y": y - 5, "z0": -1, "z1": 0, "a": 1, "flat": True})
    game.wait("Marks.list.length === 1 && Marks.list[0].a >= 1")
    game.sleep(300)
    got = drawn(game, hid, before)
    assert 10 <= sum(got) <= 20 and all(a != b for a, b in zip(got[1:15], got[2:16])), got      # dotted: every other px of paint
    assert game.js(PIXELS, [mid])[0] == before[-1]               # no wash on the plateau
    seen = edge(x - 3)
    before = game.js(PIXELS, [p for pair in seen for p in pair])
    game.js(FORCE, {"x": x - 3, "y": y - 5, "z0": -1, "z1": 0, "a": 1, "flat": True})
    game.sleep(500)
    assert all(drawn(game, seen, before))                        # in the open: every px of its edges
    game.js(FORCE, None)


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
