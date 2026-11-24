"""The land's height: a column of cells from -512 to 512 ("please make the underground reach -512 and the sky max
block should be 512 too"; it was 32 cells, -16 to 15). How it is kept, saved and sent, and what a world saved before
becomes (cells.py, chunks.py, sim/persistence.py)."""

import sqlite3
import zlib
from array import array

from helpers import run
from megastructure.cells import HIGH, LOW, col_cave, col_floor, col_runs, col_solid, col_surfaces, col_top, runs_col
from megastructure.chunks import FORMAT, Chunk
from megastructure.gen import CHUNK
from megastructure.sim import Simulation


def test_a_column_goes_from_the_bottom_to_the_top_and_is_said_as_the_heights_where_it_changes():
    assert (LOW, HIGH) == (-512, 512)
    assert col_runs(col_solid(7)) == [7] and col_runs(col_solid(-512)) == [-512] and col_runs(col_solid(512)) == [512]
    cave = col_cave(-500, 2, 6)                               # a room two cells high, five hundred down, under a hill
    assert col_runs(cave) == [-500, -498, 6] and col_surfaces(cave) == [-500, 6] and (col_floor(cave), col_top(cave)) == (-500, 6)
    both = runs_col([-300, -298, -10, -8, 40])               # two rooms one over the other
    assert col_surfaces(both) == [-300, -10, 40] and col_runs(both) == [-300, -298, -10, -8, 40]
    for col in (col_solid(0), cave, both, col_solid(512), col_cave(500, 2, 512)):
        assert runs_col(col_runs(col)) == col


def test_a_chunk_saved_with_32_cells_a_tile_is_read_as_it_was(tmp_path):
    """A save from before: each tile's column 32 bits, cell -16 the lowest. Read into the taller column it is the
    same land (solid under it, down to the bottom), and it is saved the new way."""
    n = CHUNK * CHUNK
    old = array("I", [(1 << 17) - 1]) * n                     # sea level everywhere (cells -16..0)...
    old[5] = (1 << 21) - 1 & ~(0b11 << 17)                    # ...a hill four high, hollow two cells over the ground
    old[6] = (1 << 9) - 1                                     # ...a pit eight deep
    old[7] = 0xFFFFFFFF                                       # ...and land as high as it went
    blob = zlib.compress(bytes(n) + bytes(n) + old.tobytes() + bytes([4]), 6)
    c = Chunk.unpack(0, 0, blob)
    assert [col_runs(c.cols[i]) for i in (0, 5, 6, 7)] == [[0], [0, 2, 4], [-8], [15]]
    again = c.pack()
    assert zlib.decompress(again)[-1] == FORMAT == 7 and Chunk.unpack(0, 0, again).cols == c.cols
    deep = Chunk(0, 0, bytearray(n), bytearray(n), [col_cave(-500, 2, 6)] * n)       # (and what the old one could not hold)
    assert Chunk.unpack(0, 0, deep.pack()).cols == deep.cols


def test_a_world_from_before_is_copied_aside_once_and_is_the_same_land(tmp_path):
    path = tmp_path / "w.sqlite"
    sim = Simulation(path, seed=7)
    a = sim.login("Ash", "tok")
    x, y = a.x, a.y
    sim.world.set(x + 2, y, level=0, roof=4)
    sim.world.set(x + 3, y, level=-8)
    sim.close()
    db = sqlite3.connect(path)                                # (made a save from before: its chunks 32 bits a tile, no word of the cells)
    for cx, cy, data in db.execute("SELECT cx, cy, data FROM chunks").fetchall():
        c, n = Chunk.unpack(cx, cy, data), CHUNK * CHUNK
        old = array("I", [(col >> (-16 - LOW)) & 0xFFFFFFFF for col in c.cols])
        db.execute("UPDATE chunks SET data=? WHERE cx=? AND cy=?", (zlib.compress(bytes(c.ground) + bytes(c.block) + old.tobytes() + bytes([4]), 6), cx, cy))
    db.execute("DELETE FROM meta WHERE key='cells'")
    db.commit(); db.close()
    aside = tmp_path / "w.before-tall.sqlite"
    assert not aside.exists()
    sim = Simulation(path, seed=7)
    assert aside.exists() and sim.store.get_meta("cells") == HIGH - LOW + 1
    assert col_runs(sim.world.col(x + 2, y)) == [0, 2, 4] and sim.world.level(x + 3, y) == -8 and sim.world.surfaces(x, y) == [sim.world.level(x, y)]
    sim.world.set_cell(x + 3, y, -8, False)                   # (dug on: saved the new way, read back)
    sim.close()
    aside.unlink()
    sim = Simulation(path, seed=7)
    assert not aside.exists() and sim.world.level(x + 3, y) == -9          # (once)
    sim.close()


def test_the_ground_is_dug_down_to_the_bottom_and_built_up_to_the_top(world):
    sim, a = world
    x, y = a.x, a.y
    c = sim.world.chunk(x >> 5, y >> 5)
    c.cols[(y & 31) * CHUNK + (x & 31)] = col_solid(LOW + 2)                 # you, two layers over the bottom, in a shaft
    c.cols[(y & 31) * CHUNK + ((x + 1) & 31)] = col_solid(LOW + 2)
    a.inventory["pickaxe"] = 1
    assert sim.height(a) == LOW + 2
    assert run(sim, a, "dig", {"x": x + 1, "y": y, "z": LOW + 2, "with": "pickaxe"})["ok"]
    assert run(sim, a, "dig", {"x": x + 1, "y": y, "z": LOW + 1, "with": "pickaxe"})["ok"] and sim.world.level(x + 1, y) == LOW
    r = run(sim, a, "dig", {"x": x + 1, "y": y, "z": LOW, "with": "pickaxe"})
    assert not r["ok"] and "deep as it goes" in r["detail"] and sim.world.solid(x + 1, y, LOW)        # the bottom cell stays
    assert sim.block_fits(x, y, HIGH + 1) == "nothing is built that high"
    assert sim.block_fits(x + 3, y, HIGH) != "nothing is built that high"
    sim.world.set_cell(x + 2, y, HIGH, True)                  # a block at the very top: it is there, and nothing is over it
    assert sim.world.solid(x + 2, y, HIGH) and not sim.world.solid(x + 2, y, HIGH + 1) and sim.world.top(x + 2, y) == HIGH


def test_a_tile_event_and_a_region_say_a_column_as_its_heights(world):
    from megastructure.server import GameServer  # noqa: F401 (the views are the server's)
    sim, a = world
    seen = []
    sim.listeners.append(seen.append)
    sim.set_tile(a.x + 2, a.y, level=-40, roof=44, head=2)
    ev = [e for e in seen if e["type"] == "tile"][-1]
    assert ev["col"] == [-40, -38, 4]


def test_the_block_under_your_feet_is_dug_by_hand_too(world):
    """"i should be able to break this block by putting myself in top of it then digging under my feets": digging
    down wanted a pickaxe in hand. By hand it is slower; you come down with the block either way."""
    sim, a = world
    x, y, z = a.x, a.y, sim.height(a)
    t0 = sim.tick
    r = run(sim, a, "dig_down", {})
    by_hand = sim.tick - t0
    assert r["ok"] and (a.x, a.y) == (x, y) and sim.height(a) == z - 1 and sim.world.level(x, y) == z - 1
    a.inventory["pickaxe"] = 1
    t0 = sim.tick
    assert run(sim, a, "dig_down", {"with": "pickaxe"})["ok"] and sim.height(a) == z - 2
    assert sim.tick - t0 < by_hand
