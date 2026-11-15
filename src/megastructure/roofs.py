"""Roofs: where a roof tile lies. A roof is laid a tile at a time over what is built (sim/roofing.py) and is its own
layer: under it the tile keeps its ground and whatever stands on it. Kept in its own table of the save."""

from .world import Store


class Roofs:
    def __init__(self, store: Store):
        self.store = store
        store.db.execute("CREATE TABLE IF NOT EXISTS roofs(x INTEGER, y INTEGER, PRIMARY KEY(x, y))")
        self.at: set[tuple[int, int]] = {(x, y) for x, y in store.db.execute("SELECT x, y FROM roofs")}
        self.dirty: set[tuple[int, int]] = set()

    def __contains__(self, pos) -> bool:
        return pos in self.at

    def __len__(self) -> int:
        return len(self.at)

    def set(self, x: int, y: int, on: bool):
        (self.at.add if on else self.at.discard)((x, y))
        self.dirty.add((x, y))

    def within(self, x: int, y: int, w: int, h: int) -> list[tuple[int, int]]:
        if len(self.at) < w * h:
            return [p for p in self.at if x <= p[0] < x + w and y <= p[1] < y + h]
        return [(i, j) for j in range(y, y + h) for i in range(x, x + w) if (i, j) in self.at]

    def flush(self):
        for x, y in self.dirty:
            if (x, y) in self.at:
                self.store.db.execute("INSERT OR REPLACE INTO roofs VALUES(?,?)", (x, y))
            else:
                self.store.db.execute("DELETE FROM roofs WHERE x=? AND y=?", (x, y))
        self.dirty.clear()
