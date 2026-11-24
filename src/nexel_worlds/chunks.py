"""A chunk of the world: 32x32 tiles, each with its ground, what stands on it, its column of cells and what that
column is made of (stone: the highest of its cells that is stone); packed for the save file and read back.
STONE: a column's material is the world generator's, set for good when its land is laid out: where its top stood at
STONE_FROM or over it is stone at every height (HIGH: the mountains); lower, stone starts EARTH cells under the lowest
ground round it (lay_stone), so no land laid out shows stone: a hill is earth and grass to its foot ("earth on top,
stone underneath should only be a matter of world generation. Grass shouldn't turn into stone"). Digging it, building
on it change nothing of that: a trench cut in a stone hill has stone walls; a hole dug in a meadow comes to stone.
world.py made_of is the one reader (what a dig gives, what a screen paints: views.py stones)."""

import struct
import zlib
from array import array

from .gen import CHUNK, HIGH, LOW, col_runs, col_solid, col_top, runs_col

# chunk format: the land as cells, each tile's column as the heights where it changes (gen.col_runs): how many of
# them a tile, then all of them; and (7) two bytes a tile, its stone. 6: a byte a tile, stone or earth (an earth
# column's stone is then the generator's: world.py). 5, before it: no rock kept: by the generator. 4: 32 cells a tile,
# a bit each, from -16 up: read as it was, in the taller column (solid under it down to the bottom).
FORMAT = 7
STONE_FROM = 5                      # a column laid out with its top here or over is stone at every height
EARTH = 2                           # under a lower top, this many cells of earth (the meadow's two layers), then stone
UNKNOWN = -32768                    # (a save that did not keep it: world.py asks the generator)


def stone_of(col: int) -> int:
    """The highest stone cell of a column laid out alone (its neighbours unknown: lay_stone has them)."""
    return stone_at(col_top(col))


def stone_at(top: int, low: int | None = None) -> int:
    """A column's highest stone cell, its top laid out at `top`, the lowest ground round it `low`."""
    return HIGH if top >= STONE_FROM else min(top, top if low is None else low) - EARTH


ROUND = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def cells(n: int, fill: int) -> list:
    return [fill] * n


class Chunk:
    __slots__ = ("cx", "cy", "ground", "block", "cols", "stone", "guessed", "dirty", "touched")

    def __init__(self, cx, cy, ground, block, cols=None, stone=None):
        self.cx, self.cy = cx, cy
        self.ground, self.block = ground, block
        self.cols = cols if cols is not None else cells(CHUNK * CHUNK, col_solid(0))   # each tile's column of cells
        self.guessed = stone is not None and UNKNOWN in stone   # (a save from before: world.py asks the generator)
        self.stone = stone if stone is not None else array("h", (stone_of(c) for c in self.cols))
        self.dirty = False
        self.touched = 0

    def lay_stone(self, top_of, unknown_only=False):
        """Each column's stone as the generator lays it (top_of(x, y): a tile's top as it was laid out): new land, or a
        save that did not keep it (unknown_only: its stone hills kept)."""
        for i, s in enumerate(self.stone):
            if unknown_only and s != UNKNOWN:
                continue
            x, y = self.cx * CHUNK + i % CHUNK, self.cy * CHUNK + i // CHUNK
            self.stone[i] = stone_at(top_of(x, y), min(top_of(x + dx, y + dy) for dx, dy in ROUND))
        self.guessed, self.dirty = False, True

    def pack(self) -> bytes:
        runs = [col_runs(c) for c in self.cols]
        flat = [z for r in runs for z in r]
        body = struct.pack(f"<{len(runs)}H", *map(len, runs)) + struct.pack(f"<{len(flat)}h", *flat)
        return zlib.compress(bytes(self.ground) + bytes(self.block) + body + self.stone.tobytes() + bytes([FORMAT]), 6)

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
        elif raw[-1] in (5, 6, FORMAT) and len(raw) > 4 * n:
            counts = struct.unpack_from(f"<{n}H", raw, 2 * n)
            flat = struct.unpack_from(f"<{sum(counts)}h", raw, 4 * n)
            cols, at = [], 0
            for k in counts:
                cols.append(runs_col(flat[at:at + k]))
                at += k
        else:
            return None
        stone = None
        if raw[-1] == FORMAT:
            stone = array("h")
            stone.frombytes(raw[-1 - 2 * n:-1])
        elif raw[-1] == 6:                                 # (stone or earth: an earth column's stone, the generator's)
            stone = array("h", (HIGH if r else UNKNOWN for r in raw[-1 - n:-1]))
        else:                                              # (5: nothing kept, all the generator's)
            stone = array("h", [UNKNOWN] * n)
        return cls(cx, cy, bytearray(raw[:n]), bytearray(raw[n:2 * n]), cols, stone)
