"""Blocks built over the land: a floor laid up on walls, a roof, a step. The land is cells (world.py, gen.py); a
built block is one more solid cell in its tile's column, so whoever walks, jumps or falls does it by the one rule.
Here is what that cell is made of and what stands on it: under it the tile keeps its ground and whatever stands on
that. Kept in its own table of the save."""

from .gen import LOW
from .world import Store

KINDS = ("plank", "roof", "stairs")           # a floor of planks; shingles; the steps of a flight of stairs (sim/climbing.py)


class Floors:
    def __init__(self, store: Store):
        self.store = store
        store.db.execute("CREATE TABLE IF NOT EXISTS floors(x INTEGER, y INTEGER, z INTEGER, kind TEXT, thing TEXT, "
                         "PRIMARY KEY(x, y, z))")
        self.at: dict[tuple[int, int], dict[int, list]] = {}       # (x, y) -> {z: [kind, what stands on it]}
        for x, y, z, kind, thing in store.db.execute("SELECT x, y, z, kind, thing FROM floors"):
            self.at.setdefault((x, y), {})[z] = [kind, thing]
        self.dirty: set[tuple[int, int, int]] = set()

    def __len__(self) -> int:
        return sum(len(col) for col in self.at.values())

    def get(self, x: int, y: int, z: int) -> list | None:
        """The block built in the cell (x, y, z): [kind, what stands on it], or None."""
        col = self.at.get((x, y))
        return col.get(z) if col else None

    def set(self, x: int, y: int, z: int, kind: str | None, thing: str = "none"):
        """Build the cell, change what stands on it, or (kind None) take it away."""
        col = self.at.setdefault((x, y), {})
        if kind is None:
            col.pop(z, None)
            if not col:
                del self.at[(x, y)]
        else:
            col[z] = [kind, thing]
        self.dirty.add((x, y, z))

    def mask(self, x: int, y: int) -> int:
        """The built cells of the tile's column, a bit each (as World.col has them)."""
        col = self.at.get((x, y))
        return sum(1 << (z - LOW) for z in col) if col else 0

    def within(self, x: int, y: int, w: int, h: int) -> list[tuple]:
        """Every built cell of the rectangle: (x, y, z, kind, thing)."""
        if len(self.at) < w * h:
            tiles = [p for p in self.at if x <= p[0] < x + w and y <= p[1] < y + h]
        else:
            tiles = [(i, j) for j in range(y, y + h) for i in range(x, x + w) if (i, j) in self.at]
        return [(i, j, z, *cell) for i, j in tiles for z, cell in sorted(self.at[(i, j)].items())]

    def flush(self):
        for x, y, z in self.dirty:
            cell = self.get(x, y, z)
            if cell:
                self.store.db.execute("INSERT OR REPLACE INTO floors VALUES(?,?,?,?,?)", (x, y, z, *cell))
            else:
                self.store.db.execute("DELETE FROM floors WHERE x=? AND y=? AND z=?", (x, y, z))
        self.dirty.clear()
