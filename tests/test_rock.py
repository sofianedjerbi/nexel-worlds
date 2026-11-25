"""What the land is made of is set for good when it is laid out (chunks.py stone: each column's highest stone cell):
a high hill is stone at every height; lower land is EARTH cells of earth under its top, stone under them ("earth on
top and rock underneath"). Kept through digging and building, saved, read by one rule (world.py made_of) for what a
dig gives and what a screen is told ("r"; "~" and the stone cell where the screen cannot tell it from the top)."""

from nexel_worlds.chunks import EARTH, FORMAT, HIGH, Chunk
from nexel_worlds.gen import CHUNK, col_runs, col_solid
from nexel_worlds.views import Views


def test_a_chunks_stone_is_set_by_its_tops_when_made_and_is_saved():
    c = Chunk(0, 0, bytearray(CHUNK * CHUNK), bytearray(CHUNK * CHUNK), [col_solid(6)] * 512 + [col_solid(2)] * 512)
    assert c.stone[0] == HIGH and c.stone[-1] == 2 - EARTH
    c.cols[0] = col_solid(1)                                 # dug low: still stone
    d = Chunk.unpack(0, 0, c.pack())
    assert FORMAT == 7 and d.stone == c.stone and not d.guessed and d.cols == c.cols


def test_a_save_from_before_keeps_its_stone_hills_and_takes_the_rest_from_the_generator():
    import zlib
    c = Chunk(0, 0, bytearray(CHUNK * CHUNK), bytearray(CHUNK * CHUNK), [col_solid(6)] * 512 + [col_solid(2)] * 512)
    raw = zlib.decompress(c.pack())
    n = CHUNK * CHUNK
    old = raw[:-1 - 2 * n] + bytes([1] * 512 + [0] * 512) + bytes([6])      # (format 6: a byte a tile, stone or earth)
    d = Chunk.unpack(0, 0, zlib.compress(old))
    assert d.guessed and d.stone[0] == HIGH
    d.lay_stone(lambda x, y: 3, unknown_only=True)                           # (the generator laid it out three high)
    assert d.stone[-1] == 3 - EARTH and not d.guessed and d.dirty


def test_a_hill_is_earth_to_its_foot_a_stone_hill_stone_all_down_and_both_are_kept(world):
    """No land laid out shows stone: a hill's stone starts under the lowest ground round it. Kept through digging and
    building; a screen is told each tile's stone cell (views.py stones, a tile event's mat)."""
    from nexel_worlds.cells import SEA
    sim, a = world
    x, y = a.x + 3, a.y
    w = sim.world
    ground = min(w.top(x + 1 + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (-1, 0))
    sim.set_tile(x, y, level=7)                              # laid out seven high: stone (a mountain's)
    sim.set_tile(x + 1, y, level=3)                          # three high: earth and grass to the meadow's foot
    from nexel_worlds.tiles import ORE_OF
    stony = {"stone_block", *ORE_OF}                         # (stone, or an ore in it: tiles.py ORES)
    assert w.stone(x, y) == HIGH and all(w.made_of(x, y, z) in stony for z in (7, 1, -5))
    assert all(w.made_of(x + 1, y, z) == "dirt" for z in range(ground - EARTH + 1, 4))
    assert w.made_of(x + 1, y, ground - EARTH) in stony
    said = []
    sim.listeners.append(lambda ev: said.append(ev) if ev.get("type") == "tile" else None)
    for z in range(7, 1, -1):                                # dug down to 1
        sim.set_cell(x, y, z, False)
    assert said and all(ev["mat"] == f"~{HIGH}" for ev in said if (ev["x"], ev["y"]) == (x, y)), said[-1]
    stone = w.stone(x + 1, y)
    sim.set_cell(x + 1, y, 3, False)                          # dug a layer, then earth built up high: its stone is as laid out
    for z in (3, 4, 5, 6):
        sim.set_cell(x + 1, y, z, True)
    assert w.stone(x + 1, y) == stone and w.made_of(x + 1, y, 6) == "dirt"
    screen = Views.__new__(Views)
    screen.sim = sim
    r = screen.region(x & ~31, y & ~31, 32, 32)
    at = lambda i, j: ord(r["stones"][j & 31][i & 31]) - SEA
    assert at(x, y) == HIGH and at(x + 1, y) == stone and not r.get("mats")
    assert col_runs(sim.world.col(x, y)) == [1]
