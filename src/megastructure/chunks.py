"""A chunk of the world: 32x32 tiles, each with its ground, what stands on it, its column of cells and what that
column is made of (rock: stone, or earth); packed for the save file and read back.
ROCK: a column is stone or earth for good, from when its land was laid out (made by the generator, or laid out anew):
stone where its top stood at STONE_FROM or over. Digging it, building on it change nothing of that: a trench cut in a
stone hill has stone walls and a stone floor. (The land kept no material: a screen guessed it from the heights it saw
now, and a cut changed the guess.)"""

import struct
import zlib
from array import array

from .gen import CHUNK, LOW, col_runs, col_solid, col_top, runs_col

# chunk format: the land as cells, each tile's column as the heights where it changes (gen.col_runs): how many of
# them a tile, then all of them; and (6) a byte a tile, its rock. 5, before it: no rock kept: by its top as it is now
# (world.py asks the generator too, for what was dug). 4: 32 cells a tile, a bit each, from -16 up: read as it was,
# in the taller column (solid under it down to the bottom).
FORMAT = 6
STONE_FROM = 5                      # a column laid out with its top here or over is stone


def rock_of(col: int) -> int:
    return 1 if col_top(col) >= STONE_FROM else 0


def cells(n: int, fill: int) -> list:
    return [fill] * n


class Chunk:
    __slots__ = ("cx", "cy", "ground", "block", "cols", "rock", "guessed", "dirty", "touched")

    def __init__(self, cx, cy, ground, block, cols=None, rock=None):
        self.cx, self.cy = cx, cy
        self.ground, self.block = ground, block
        self.cols = cols if cols is not None else cells(CHUNK * CHUNK, col_solid(0))   # each tile's column of cells
        self.guessed = rock is None                     # (its rock by its tops as they are: new land, or a save from before)
        self.rock = rock if rock is not None else bytearray(rock_of(c) for c in self.cols)
        self.dirty = False
        self.touched = 0

    def pack(self) -> bytes:
        runs = [col_runs(c) for c in self.cols]
        flat = [z for r in runs for z in r]
        body = struct.pack(f"<{len(runs)}H", *map(len, runs)) + struct.pack(f"<{len(flat)}h", *flat)
        return zlib.compress(bytes(self.ground) + bytes(self.block) + body + bytes(self.rock) + bytes([FORMAT]), 6)

    @classmethod
    def unpack(cls, cx, cy, data: bytes) -> "Chunk | None":
        """The chunk as it was packed; None for a save from before the land was cells (it is made anew)."""
        raw = zlib.decompress(data)
        n = CHUNK * CHUNK
        if raw[-1] == 4 and len(raw) == 6 * n + 1:
            old = array("I")
            old.frombytes(raw[2 * n:6 * n])
            under = col_solid(-17)
            cols = [c << (-16 - LOW) | under for c in old]
        elif raw[-1] in (5, FORMAT) and len(raw) > 4 * n:
            counts = struct.unpack_from(f"<{n}H", raw, 2 * n)
            flat = struct.unpack_from(f"<{sum(counts)}h", raw, 4 * n)
            cols, at = [], 0
            for k in counts:
                cols.append(runs_col(flat[at:at + k]))
                at += k
        else:
            return None
        return cls(cx, cy, bytearray(raw[:n]), bytearray(raw[n:2 * n]), cols, bytearray(raw[-1 - n:-1]) if raw[-1] == FORMAT else None)
