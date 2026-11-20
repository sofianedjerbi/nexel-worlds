"""Where two things meet: a bridge and the land it runs onto, a gate and its fence, a tree and the brink of a hill."""

FLAT = ["0" * 12] * 11
# a stream with a bridge across it (its ends at x 3 and 7, the land it runs onto at x 2 and 8), and under it a
# pond with a pier that runs south from the land (x 4, rows 6 to 8), its end out in the water
BRIDGES = ["....~~~.....", "....~~~.....", "...:::::....", "....~~~.....", "............", "............",
           ".~~~:~~~....", ".~~~:~~~....", ".~~~:~~~....", ".~~~~~~~....", "............"]
# a tile's painted px: is it solid all over, the px asked for, and is there water under it
TILE = """([x, y, px, py]) => { const [b, i] = tileIdx(x, y), lx = i % B, ly = i / B | 0, o = ly * 16 * BW + lx * 16; let solid = true;
  for (let j = 0; j < 16; j++) for (let k = 0; k < 16; k++) if (b.px[o + j * BW + k] >>> 24 !== 255) solid = false;
  const v = b.px[o + py * BW + px], {un} = waterStuff(b);
  return {solid, px: [v & 255, v >> 8 & 255, v >> 16 & 255, v >>> 24], under: un[(ly + 2) * (B + 4) + lx + 2]}; }"""


def test_a_bridge_has_water_under_it_and_posts_at_its_ends(game):
    """Every tile of a bridge was the same planks. The land it ran onto was painted as a shore towards it, whose
    edge is see-through with water behind: there was none (a bridge was not water), and the dark behind the world
    showed, a black bar at each end. Now (web/js/bridge.js): water under every bridge; the land at its end is solid
    all over, no shore between them; its ends are the pack's end pieces with their posts, in foam where the end is
    out in the water."""
    x, y = game.pos()
    game.stamp(3, -13, BRIDGES, levels=FLAT); game.rest()
    at = lambda dx, dy, px=0, py=0: game.js(TILE, [x + 3 + dx, y - 13 + dy, px, py])
    post, foam = [220, 185, 138, 255], [243, 244, 231, 255]
    assert at(2, 2)["solid"] and at(8, 2)["solid"] and at(4, 5)["solid"]                   # the land at its ends: no see-through edge
    assert all(at(dx, 2)["under"] > 0 for dx in range(3, 8)) and all(at(4, dy)["under"] > 0 for dy in (6, 7, 8))      # water under all of it
    assert at(3, 2, 3, 1)["px"] == post and at(7, 2, 12, 1)["px"] == post and at(5, 2, 3, 1)["px"] != post           # a post at each end, none in the middle
    assert at(4, 6, 1, 1)["px"] == post and at(4, 8, 4, 10)["px"] == foam                  # the pier: a post where it leaves the land, foam round the ones at its end
    game.stamp(3, -13, ["." * 12] * 11, levels=FLAT)


PEN = ["#####", "#...g", "#...#", "##g##"]
GATES = """([x, y]) => { const was = occupied, out = {}, cell = (s) => [s[1], s[2], s[3], s[4]];
  occupied = new Set(); doors.clear();
  out.side = cell(objectSprite('g', x + 4, y + 1, 0)); out.front = cell(objectSprite('g', x + 2, y + 3, 0));
  occupied = new Set([(x + 3) + ',' + (y + 1), (x + 2) + ',' + (y + 2)]);                 // someone beside each: they open
  out.opening = []; for (let i = 0; i < 12; i++) out.opening.push([objectSprite('g', x + 4, y + 1, 0)[1], objectSprite('g', x + 2, y + 3, 0)[1]]);
  out.over = cell(fenceSprite(x + 4, y)); out.beside = cell(fenceSprite(x + 3, y + 3)); out.under = cell(fenceSprite(x + 4, y + 2));
  occupied = was; doors.clear(); return out; }"""


def test_a_gate_is_seen_from_the_side_in_a_fence_that_runs_north_and_south(game):
    """A gate was drawn from the front wherever it was: in a pen's east side, a door across a fence seen end on. And
    opening, it showed the sheet's first four cells one after the other: a gate hinged on the left, then on the
    right. Now (web/js/sprites.js): in a fence that runs north and south it is the pack's side-on gate, two tiles
    high, between the posts over and under it; it opens through five frames with its hinge on one side; a fence's
    rails go on to a gate beside it, not to one over or under it."""
    x, y = game.pos()
    game.stamp(3, -8, PEN, levels=["0" * 5] * 4); game.rest()
    g = game.js(GATES, [x + 3, y - 8])
    assert g["side"] == [0, 16, 32, 32] and g["front"] == [0, 0, 16, 16], g                # shut: the side-on one, the one from the front
    assert all(a % 32 == 0 and b % 32 == 0 for a, b in g["opening"]) and g["opening"][-1] == [128, 128], g      # opening: every other cell, to the last
    assert [a for a, _ in g["opening"]] == sorted(a for a, _ in g["opening"])               # (and never back on its way)
    assert g["over"][1] == 48 and g["under"][1] == 0 and g["beside"][0] == 32, g            # the fences over and under it: no rail to it; beside the other: rails both ways
    # a gate opens for someone beside it, not for a hen ("chickens shouldn't be able to open the doors": the hen
    # could not go through, animals work no gate, but the gate swung open at it)
    game.spawn("chicken", 5, -4, still=900)                    # a hen under the pen's front gate, outside
    game.stamp(1, 0, ["g"]); game.rest()                                    # and a gate beside you
    swung = lambda gx, gy: game.js("([x, y]) => doors.get(x + ',' + y) || 0", [gx, gy])
    game.settle("([x, y]) => doors.get((x + 1) + ',' + y) === 1 && [...ents.values()].some((p) => p.e && p.e.kind === 'chicken' && Math.round(p.x) === x + 5 && Math.round(p.y) === y - 4)", [x, y])      # (the hen has come with a tick, the gate beside you has swung open: it slept 0.9 s)
    game.sleep(300)                                            # (...and a gate that swings at a hen has had the time to)
    assert game.js("([x, y]) => [...ents.values()].some((p) => p.e && p.e.kind === 'chicken' && Math.round(p.x) === x && Math.round(p.y) === y)", [x + 5, y - 4])
    assert swung(x + 5, y - 5) == 0 and swung(x + 1, y) == 1
    game.rpc("dev_creatures", clear=40)
    game.stamp(1, 0, ["."])
    game.stamp(3, -8, ["." * 5] * 4)


HILL = [".......", "...T...", ".T.T.T.", ".T.T...", ".......", ".T~.T..", "....~.."]
HIGH = ["0000000", "0222220", "0222220", "0222220", "0000000", "0000000", "0000000"]


def test_a_tree_on_the_brink_of_a_hill_stands_back_from_it(game):
    """A hill's edge tile is the cliff's face from its 8th px down, and a tree's foot is at the bottom of its tile: a
    tree on the south edge of a plateau stood on the face of the cliff. What grows or lies on such a tile is drawn
    back from the drop (web/js/sprites.js brink): 8 px from one to the south, 4 from one to a side; not from the
    north edge, nor in the middle. And the same from water ("weird tree at sea border": a shore tile is cut as a
    hill's edge is, bank and foam where the cliff's face would be)."""
    x, y = game.pos()
    game.stamp(3, -8, HILL, levels=HIGH); game.rest()
    back = lambda dx, dy: game.js("([x, y]) => brink(x, y)", [x + 3 + dx, y - 8 + dy])
    assert back(3, 2) == [0, 0] and back(3, 1) == [0, 0]                                  # the middle, the north edge
    assert back(1, 5) == [-4, 0] and back(4, 5) == [0, -8]                                # by water: to its east, to its south
    assert back(3, 3) == [0, -8] and back(1, 2) == [4, 0] and back(5, 2) == [-4, 0] and back(1, 3) == [4, -8]      # south, west, east, the corner
    spr = game.js("([x, y]) => [objectSprite('T', x, y, 0).slice(5), spriteOf('T', x, y, 0).slice(5)]", [x + 6, y - 5])
    assert spr[0] == [spr[1][0], spr[1][1] - 8]                                           # (its picture: the same, 8 px up)
    game.stamp(3, -8, ["." * 7] * 7, levels=["0" * 7] * 7)


SEATS = ["h.^.h..", ".......", ".h.....", ".L....h", ".h....."]


def test_a_chair_is_turned_to_the_table_or_the_fire_it_is_set_at(game):
    """Every chair faced east (the sheet's first of four): of two chairs by a fire, the one east of it had its back
    to it ("the right chair in the firecamp is turned at the wrong side"). A chair faces a table or a fire a tile
    or two from it (web/js/world_decor.js chairFaces); with neither near, east as before."""
    x, y = game.pos()
    game.stamp(3, -8, SEATS, levels=["0" * 7] * 5); game.rest()
    faces = lambda dx, dy: game.js("([x, y]) => [chairFaces(x, y), objectSprite('h', x, y, 0)[1]]", [x + 3 + dx, y - 8 + dy])
    assert faces(0, 0) == ["E", 64] and faces(4, 0) == ["W", 80]                           # by the fire: both towards it
    assert faces(1, 2) == ["S", 96] and faces(1, 4) == ["N", 112] and faces(6, 3) == ["E", 64]      # over and under a table; on its own
    game.stamp(3, -8, ["." * 7] * 5)


FIELD = [".....", ".ooo.", ".ooo.", ".ooo.", "....."]
# a tile's px of the tilled sheet's darker tone: how many in each row, and in each column
DARK = """([x, y]) => { const [b, i] = tileIdx(x, y), o = (i / B | 0) * 16 * BW + (i % B) * 16, rows = new Array(16).fill(0), cols = new Array(16).fill(0);
  for (let j = 0; j < 16; j++) for (let k = 0; k < 16; k++) { const v = b.px[o + j * BW + k]; if ((v & 0xffffff) === (138 << 16 | 185 << 8 | 220)) { rows[j]++; cols[k]++; } }
  return {rows, cols}; }"""


def test_tilled_soil_is_furrows_not_a_line_round_a_patch(game):
    """The pack's tilled soil is a patch with a line round it, 10 px inside its outer tiles; on bare soil of its own
    colour only the line showed, a box floating inside the field ("see the weird line in the field?"). At sea level
    a tilled tile is furrows over the whole of it (web/js/furrows.js): a darker line every 4 px, the same on a
    field's rim as in its middle, and no line down the tile. Up on a hill, on grass, the patch is kept."""
    x, y = game.pos()
    game.stamp(3, -8, FIELD, levels=["0" * 5] * 5); game.rest()
    rim, mid = game.js(DARK, [x + 4, y - 6]), game.js(DARK, [x + 5, y - 6])                # the field's west side, its middle
    for t in (rim, mid):
        # furrows across; nothing down it (the patch's edge was 16 in a column; the soil's own specks under it are a few)
        assert all(t["rows"][r] >= 8 for r in (3, 7, 11, 15)) and max(t["cols"]) <= 10, t
    game.stamp(3, -8, FIELD, levels=["2" * 5] * 5); game.rest()
    assert max(game.js(DARK, [x + 4, y - 6])["cols"]) >= 12                                # on a hill: the patch's own edge
    game.stamp(3, -8, ["." * 5] * 5, levels=["0" * 5] * 5)


HOUSE = ["WWWWW", "WnnnW", "WnnnW", "WW+WW"]
# one frame: what was drawn of the house's front and of you, in the order it was drawn
ORDER = """() => new Promise((ok) => { const seq = [], w = Structures.drawWall, e = window.drawEntity;
  Structures.drawWall = function (...a) { seq.push('front'); return w(...a); };
  window.drawEntity = function (p, ...a) { if (p.e.id === myId) seq.push('me'); return e(p, ...a); };
  requestAnimationFrame(() => requestAnimationFrame(() => { Structures.drawWall = w; window.drawEntity = e; ok(seq.slice(-2)); })); })"""


def test_a_house_is_under_what_stands_before_it(game):
    """Houses were drawn last, over everything: the front wall hid the head of whoever stood before the door, and
    the mailbox beside it ("house layer is weird, it goes above mailbox and players"). A house is drawn in its
    place, each wall at its own row (web/js/structures.js): you before its door are drawn after it. And a mailbox with a
    letter in it shows the whole of the letter's bubble (the sheet's rows 62 to 88: it was cut from 64)."""
    x, y = game.pos()
    game.stamp(-2, -4, HOUSE, levels=["0" * 5] * 4); game.rest()            # its door straight over you
    assert game.js(ORDER) == ["front", "me"]                   # its walls, each drawn in its place: you after them
    letter = game.js("([x, y]) => { const was = mailAt; mailAt = new Set([x + ',' + y]); const s = objectSprite('X', x, y, .6); mailAt = was; return [s[2], s[2] + s[4], s[6] + s[4]]; }", [x + 3, y])
    assert letter[0] <= 62 and letter[1] >= 89 and letter[2] == 16, letter                 # all of it; its foot where it was
    game.stamp(-2, -4, ["." * 5] * 4)
