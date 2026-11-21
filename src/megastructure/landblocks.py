"""The land's blocks as things you carry. A cell of the land dug out is a block in your pack: earth (`dirt`) or stone
(`stone_block`), and put down again it is the land again. ("breaked blocks should stay blocks in inventory: not items.
blocks -> item should be a craft": digging gave `stone`, the material, which nothing could put back.)
The land keeps no material of its own: a cell is stone or earth by its height (natural). So a block put where the
land would be the other kind is remembered here, in its own table of the save, until it is dug again: what you put
down is what you get back. Only those cells are kept: a hole filled with its own earth leaves nothing."""

LAND_BLOCKS = ("dirt", "stone_block")


def natural(z: int) -> str:
    """What the land is made of at height z where nobody put a block: earth at the meadow's two layers, stone over and under."""
    return "stone_block" if z > 1 or z < 0 else "dirt"


class Placed:
    def __init__(self, store):
        self.db = store.db
        self.db.execute("CREATE TABLE IF NOT EXISTS placed(x INTEGER, y INTEGER, z INTEGER, kind TEXT, PRIMARY KEY(x, y, z))")
        self.at: dict[tuple[int, int], dict[int, str]] = {}
        for x, y, z, kind in self.db.execute("SELECT x, y, z, kind FROM placed"):
            self.at.setdefault((x, y), {})[z] = kind

    def kind(self, x: int, y: int, z: int) -> str:
        """The block the cell (x, y, z) of the land is."""
        return self.at.get((x, y), {}).get(z) or natural(z)

    def put(self, x: int, y: int, z: int, kind: str):
        """A block of the pack became the cell."""
        self.take(x, y, z)
        if kind != natural(z):
            self.at.setdefault((x, y), {})[z] = kind
            self.db.execute("INSERT OR REPLACE INTO placed VALUES(?,?,?,?)", (x, y, z, kind))

    def take(self, x: int, y: int, z: int) -> str:
        """The cell is dug: the block it was; nothing is kept of it."""
        col = self.at.get((x, y))
        if not col or z not in col:
            return natural(z)
        kind = col.pop(z)
        if not col:
            del self.at[(x, y)]
        self.db.execute("DELETE FROM placed WHERE x=? AND y=? AND z=?", (x, y, z))
        return kind

    def clear(self, x: int, y: int):
        """The land of the tile is laid out anew (dev tools): it is what its height says again."""
        for z in list(self.at.get((x, y), {})):
            self.take(x, y, z)
