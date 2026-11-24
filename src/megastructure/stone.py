"""What the land is made of: earth or stone, the world generator's (chunks.py stone: each column's highest stone cell,
laid when its land is laid out; a high hill stone all through, lower land earth down to under the lowest ground round
it). The one rule for what a dig gives (sim/underground.py take_land) and what a screen paints (views.py stones;
web/js cells.js stoneAt). World's (world.py)."""

from .cells import col_top
from .chunks import CHUNK, ROUND, stone_at


class Stone:
    def stone(self, x: int, y: int) -> int:      # the highest stone cell of the tile's column (chunks.py: the generator's)
        return self.chunk(x >> 5, y >> 5).stone[(y & 31) * CHUNK + (x & 31)]

    def relay(self, x: int, y: int):
        """The tile's land laid out anew (dev tools): its stone as the generator would lay it, by the land round it now."""
        self.chunk(x >> 5, y >> 5).stone[(y & 31) * CHUNK + (x & 31)] = stone_at(self.top(x, y), min(self.top(x + dx, y + dy) for dx, dy in ROUND))

    def made_of(self, x: int, y: int, z: int) -> str:
        """A cell of the land where nobody put a block (landblocks.py): what a dig gives, what a screen paints."""
        return "stone_block" if z <= self.stone(x, y) else "dirt"

    def lay(self, c, top_of):
        """A chunk just generated: its stone by its own tops and the land round it (top_of(x, y): the generator's)."""
        x0, y0 = c.cx * CHUNK, c.cy * CHUNK
        c.lay_stone(lambda x, y: col_top(c.cols[(y - y0) * CHUNK + x - x0]) if 0 <= x - x0 < CHUNK and 0 <= y - y0 < CHUNK else top_of(x, y))
