"""The land's blocks as things you carry. A cell of the land dug out is a block in your pack: earth (`dirt`) or stone
(`stone_block`), and put down again it is the land again. ("breaked blocks should stay blocks in inventory: not items.
blocks -> item should be a craft": digging gave `stone`, the material, which nothing could put back.)
The land's own material is its column's (world.py made_of: earth on top, stone under). A block put down is
remembered here, in its own table of the save, until it is dug again: what you put down is what you get back. Every block put down is kept, also where the land would be that kind anyway: the picture
draws a put block as what it is (`mat`: stone as stone on a meadow, earth as bare earth: a hut of stone blocks was
drawn as an earth hut with a grass top)."""

LAND_BLOCKS = ("dirt", "stone_block")


class Placed:
    def __init__(self, store):
        self.db = store.db
        self.db.execute("CREATE TABLE IF NOT EXISTS placed(x INTEGER, y INTEGER, z INTEGER, kind TEXT, PRIMARY KEY(x, y, z))")
        self.at: dict[tuple[int, int], dict[int, str]] = {}
        for x, y, z, kind in self.db.execute("SELECT x, y, z, kind FROM placed"):
            self.at.setdefault((x, y), {})[z] = kind

    def kind(self, x: int, y: int, z: int) -> str | None:
        """The block put as the cell (x, y, z) of the land; None: nobody put one there (world.py made_of says)."""
        return self.at.get((x, y), {}).get(z)

    def put(self, x: int, y: int, z: int, kind: str):
        """A block of the pack became the cell."""
        self.take(x, y, z)
        self.at.setdefault((x, y), {})[z] = kind
        self.db.execute("INSERT OR REPLACE INTO placed VALUES(?,?,?,?)", (x, y, z, kind))

    def mat(self, x: int, y: int, runs: list) -> str:
        """The block put on the tile's top (runs: its column as it is sent, the last height its top): "s" stone, "d" earth,
        "": none was put, the land is what world.py made_of says."""
        col = self.at.get((x, y))
        return {"stone_block": "s", "dirt": "d"}.get(col.get(runs[-1]), "") if col and runs else ""

    def take(self, x: int, y: int, z: int) -> str | None:
        """The cell is dug: the block put there (None: none was); nothing is kept of it."""
        col = self.at.get((x, y))
        if not col or z not in col:
            return None
        kind = col.pop(z)
        if not col:
            del self.at[(x, y)]
        self.db.execute("DELETE FROM placed WHERE x=? AND y=? AND z=?", (x, y, z))
        return kind

    def clear(self, x: int, y: int):
        """The land of the tile is laid out anew (dev tools): it is what its height says again."""
        for z in list(self.at.get((x, y), {})):
            self.take(x, y, z)
