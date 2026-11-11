"""A chunk of the world: 32x32 tiles, each with its ground, what stands on it and its column of cells; packed for
the save file and read back."""

import zlib
from array import array

from .gen import CHUNK, col_solid

FORMAT = 4                               # chunk format: the land as cells, solid or empty (gen.col_solid...)


def cells(n: int, fill: int) -> array:
    return array("I", [fill]) * n


class Chunk:
    __slots__ = ("cx", "cy", "ground", "block", "cols", "dirty", "touched")

    def __init__(self, cx, cy, ground, block, cols=None):
        self.cx, self.cy = cx, cy
        self.ground, self.block = ground, block
        self.cols = cols if cols is not None else cells(CHUNK * CHUNK, col_solid(0))   # each tile's column of cells
        self.dirty = False
        self.touched = 0

    def pack(self) -> bytes:
        return zlib.compress(bytes(self.ground) + bytes(self.block) + self.cols.tobytes() + bytes([FORMAT]), 6)

    @classmethod
    def unpack(cls, cx, cy, data: bytes) -> "Chunk | None":
        """The chunk as it was packed; None for a save from before the land was cells (it is made anew)."""
        raw = zlib.decompress(data)
        n = CHUNK * CHUNK
        if len(raw) != 6 * n + 1 or raw[-1] != FORMAT:
            return None
        cols = array("I")
        cols.frombytes(raw[2 * n:6 * n])
        return cls(cx, cy, bytearray(raw[:n]), bytearray(raw[n:2 * n]), cols)
