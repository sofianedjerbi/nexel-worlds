"""A column is stone or earth for good (chunks.py rock): set when its land is laid out, kept through digging, saved,
and said to a screen as its tile's material ("r"). A cut in a stone hill is stone: nothing is guessed from heights."""

from megastructure.chunks import FORMAT, Chunk
from megastructure.gen import CHUNK, col_runs, col_solid
from megastructure.views import Views


def test_a_chunks_rock_is_its_tops_when_made_and_is_saved():
    c = Chunk(0, 0, bytearray(CHUNK * CHUNK), bytearray(CHUNK * CHUNK), [col_solid(6)] * 512 + [col_solid(2)] * 512)
    assert sum(c.rock) == 512 and c.rock[0] == 1 and c.rock[-1] == 0
    c.cols[0] = col_solid(1)                                 # dug low: still stone
    d = Chunk.unpack(0, 0, c.pack())
    assert FORMAT == 6 and d.rock == c.rock and d.rock[0] == 1 and not d.guessed and d.cols == c.cols


def test_digging_never_changes_what_a_column_is_made_of_and_a_screen_is_told(world):
    sim, a = world
    x, y = a.x + 3, a.y
    sim.set_tile(x, y, level=7)                              # laid out seven high: stone
    sim.set_tile(x + 1, y, level=3)                          # three high: earth
    assert sim.world.rock(x, y) and not sim.world.rock(x + 1, y)
    said = []
    sim.listeners.append(lambda ev: said.append(ev) if ev.get("type") == "tile" else None)
    for z in range(7, 1, -1):                                # dug down to 1
        sim.set_cell(x, y, z, False)
    assert sim.world.top(x, y) == 1 and sim.world.rock(x, y)
    assert said and all(ev["mat"] == "r" for ev in said if (ev["x"], ev["y"]) == (x, y)), said[-1]
    for z in (4, 5, 6):                                      # earth built up past stone's height: still earth
        sim.set_cell(x + 1, y, z, True)
    assert not sim.world.rock(x + 1, y)
    screen = Views.__new__(Views)
    screen.sim = sim
    mats = screen.region(x & ~31, y & ~31, 32, 32).get("mats", {})
    at = lambda i, j: mats.get(str((j & 31) * 32 + (i & 31)), "")
    assert at(x, y) == "r" and at(x + 1, y) == ""
    assert col_runs(sim.world.col(x, y)) == [1]
