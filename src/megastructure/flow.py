"""Water that flows, a cell at a time, after the sandbox classic.

Water lies in the land's empty cells (cells.py), each at a level: 1 to 7 as it runs, 8 full. The sea, rivers and
lakes are sources where they are (a water ground, at its tile's own height: tiles.py); what a player pours from a can
is one too (kept here, with what runs). The rules, at each step (sim/waters.py: four a second, only near players):
  under the sea's face it is full: a cell lower than the sea, river or lake its water comes from (its HEAD), lying on
  something (land, water), fills (8): a hole dug beside a river fills to the river's face, from its floor up, and a
  tunnel dug on under it floods on as far as it goes (MAXD cells of water from the source at most);
  down first: a cell with water over it is 7, falling;
  then sideways, a level less a tile, from a neighbour that lies on land, or on water that others may lie on (full,
  or a layer of running water full from wall to wall: Water.settled): water over air only falls, a waterfall stays
  a column and the film at its foot spreads; a can poured on flat ground runs 7 tiles, no more;
  what has no source behind it any more goes down (a level, or a cell further from its source) a step at a time, and
  is gone at 0: it dries up;
  a cell that is solid holds none: any block put in it stops it (a dam).
Each cell of water is (level, head, distance): the head the height of the natural source it is fed from (NOHEAD: a
can's), the distance how many cells of water lie between (0: a source).
Only the cells next to a change are looked at (`due`), a bounded number a step (BUDGET): a flood runs on over the
steps that follow. Kept in its own table of the save, with the cells still to look at (they go on after a restart)."""

from .tiles import BLOCKS, GROUNDS

SOURCE, FULL, FALL = 8, 8, 7
NOHEAD = -10 ** 6                  # the head of water poured from a can: nothing is under its face (it only runs)
MAXD = 64                          # the furthest (cells of water) a source fills what is under its face
BUDGET = 512                       # cells looked at in one step, at most (the rest wait for the next)
SETTLE = 256                       # the most cells of a layer of running water that others may lie on (Water.settled)
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
AROUND = ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


class Water:
    def __init__(self, store, world):
        self.store, self.world = store, world
        store.db.execute("CREATE TABLE IF NOT EXISTS water(x INTEGER, y INTEGER, z INTEGER, level INTEGER, head INTEGER, "
                         "dist INTEGER, PRIMARY KEY(x, y, z))")
        self.at: dict[tuple[int, int], dict[int, int]] = {}      # (x, y) -> {z: level} (what runs, and what was poured)
        self.how: dict[tuple[int, int, int], tuple[int, int]] = {}   # cell -> (head, distance)
        for x, y, z, lv, head, dist in store.db.execute("SELECT x, y, z, level, head, dist FROM water"):
            self.at.setdefault((x, y), {})[z] = lv
            self.how[(x, y, z)] = (head, dist)
        self.due: set[tuple[int, int, int]] = {tuple(c) for c in store.get_meta("water_due", [])}
        self.parked: set[tuple[int, int, int]] = set()            # due, but where nobody is: looked at when someone comes
        self.dirty: set[tuple[int, int, int]] = set()             # (to be saved)
        self.sent: dict[tuple[int, int, int], int] = {}          # changed since the screens were last told: cell -> level
        self.cache: dict | None = None                             # (in a step: which layers others lie on, settled)
        world.water = self

    # ---------------------------------------------------------------- what is where
    def natural(self, x: int, y: int, z: int) -> bool:
        """The sea, a river, a lake: a water ground, its source at its tile's own height."""
        return GROUNDS[self.world.get(x, y)[0]].liquid and z == self.world.level(x, y)

    def cell(self, x: int, y: int, z: int):
        """The water in the cell: (level, head, distance), or None."""
        col = self.at.get((x, y))
        if col:
            v = col.get(z)
            if v:
                return (v, *self.how[(x, y, z)])
        return (SOURCE, z, 0) if self.natural(x, y, z) else None

    def lv(self, x: int, y: int, z: int) -> int:
        """The water in the cell: 0 none, 1 to 7 running, 8 full (a source, or under one's face)."""
        c = self.cell(x, y, z)
        return c[0] if c else 0

    def firm(self, x: int, y: int, z: int) -> bool:
        """The cell holds no water: land, a built block, or what stands solid on the ground (a wall, a door)."""
        w = self.world
        if w.solid(x, y, z):
            return True
        return z == w.top(x, y) + 1 and z == w.level(x, y) + 1 and BLOCKS[w.get(x, y)[1]].solid   # (on open ground: a wall over a tunnel stands on the hill)

    def poured(self, x: int, y: int, z: int) -> bool:
        return self.at.get((x, y), {}).get(z) == SOURCE and self.how[(x, y, z)][1] == 0

    def column(self, x: int, y: int) -> dict[int, int]:
        """The tile's cells with running or poured water: {z: level} (the sea's own is not here)."""
        return self.at.get((x, y), {})

    def want(self, x: int, y: int, z: int):
        """What the rules make of the cell now: (level, head, distance), or None."""
        if self.poured(x, y, z):
            return (SOURCE, NOHEAD, 0)
        if self.natural(x, y, z):
            return (SOURCE, z, 0)
        if self.firm(x, y, z):
            return None
        below = self.cell(x, y, z - 1)
        if below and self.natural(x, y, z - 1):
            return None                                  # (over the sea: it is the sea)
        up = self.cell(x, y, z + 1)
        if below or self.firm(x, y, z - 1):              # under a head: full, from the nearest
            near = [c for c in (up, *(self.cell(x + dx, y + dy, z) for dx, dy in N4)) if c and c[1] > z and c[2] < MAXD]
            if near:
                h, d = min((c[2], -c[1]) for c in near)
                return (FULL, -d, h + 1)
        if up:
            return (FALL, up[1], up[2] + 1)
        best = None
        for dx, dy in N4:
            nx, ny = x + dx, y + dy
            c = self.cell(nx, ny, z)
            if c and c[0] - 1 > (best[0] if best else 0) and (self.firm(nx, ny, z - 1) or self.bears(nx, ny, z - 1)):
                best = (c[0] - 1, c[1], c[2] + 1)        # (on air it only falls: down first)
        return best

    def bears(self, x: int, y: int, z: int) -> bool:
        """Water here that others lie on: full, or settled."""
        return self.lv(x, y, z) == FULL or self.settled(x, y, z)

    def settled(self, x: int, y: int, z: int) -> bool:
        """Running water here that others lie on: its layer, the wet cells joined to it at this height, is full from
        wall to wall (no dry cell beside it that could still take water), each lying on land or on water. A film run
        out on open ground is not (a waterfall's foot does not stack up), a pit's floor full of water is (the next layer
        fills). Worked out once a layer a step (`cache`); a layer of more than SETTLE cells is not."""
        if self.cache is not None and (x, y, z) in self.cache:
            return self.cache[(x, y, z)]
        if not self.lv(x, y, z):
            return False
        seen, todo, ok = {(x, y)}, [(x, y)], True
        while todo and ok:
            cx, cy = todo.pop()
            if not self.firm(cx, cy, z - 1) and not self.lv(cx, cy, z - 1):
                ok = False
            for dx, dy in N4:
                n = (cx + dx, cy + dy)
                if n in seen or self.firm(*n, z):
                    continue
                if not self.lv(*n, z) or len(seen) >= SETTLE:
                    ok = False
                    break
                seen.add(n)
                todo.append(n)
        if self.cache is not None:
            for cx, cy in seen:
                self.cache[(cx, cy, z)] = ok
        return ok

    # ---------------------------------------------------------------- changes
    def _put(self, x: int, y: int, z: int, c):
        """Set the cell's water ((level, head, distance), or None: dry)."""
        col = self.at.get((x, y))
        if c:
            if col is None:
                col = self.at[(x, y)] = {}
            if col.get(z) != c[0]:
                self.sent[(x, y, z)] = c[0]
            col[z] = c[0]
            self.how[(x, y, z)] = (c[1], c[2])
        elif col and z in col:
            del col[z]
            del self.how[(x, y, z)]
            if not col:
                del self.at[(x, y)]
            self.sent[(x, y, z)] = 0
        else:
            return
        self.dirty.add((x, y, z))

    def poke(self, x: int, y: int, z: int):
        for dx, dy, dz in AROUND:
            self.due.add((x + dx, y + dy, z + dz))

    def wet_near(self, x: int, y: int) -> bool:
        """Is there water on the tile or beside it (worth looking at when the land there changes)?"""
        for dx, dy in ((0, 0), *N4):
            if (x + dx, y + dy) in self.at or GROUNDS[self.world.get(x + dx, y + dy)[0]].liquid:
                return True
        return False

    def cell_changed(self, x: int, y: int, z: int, solid: bool):
        """A cell of the land was filled or emptied (world.set_cell)."""
        if solid and self.at.get((x, y), {}).get(z):
            self._put(x, y, z, None)                     # a block put in the water: it is gone from there (a dam)
            self.poke(x, y, z)
        elif self.wet_near(x, y):
            self.poke(x, y, z)

    def tile_changed(self, x: int, y: int):
        """A tile's ground, what stands on it or its height changed (world.set)."""
        if self.wet_near(x, y):
            lv = self.world.level(x, y)
            for z in (lv, lv + 1):
                self.poke(x, y, z)
            for dx, dy in N4:                            # (the column laid out anew: at every height water stands beside it)
                n = (x + dx, y + dy)
                for z in self.at.get(n, ()):
                    self.poke(x, y, z)
                if GROUNDS[self.world.get(*n)[0]].liquid:
                    self.poke(x, y, self.world.level(*n))
            col = self.at.get((x, y))
            if col and BLOCKS[self.world.get(x, y)[1]].solid and col.get(lv + 1):
                self._put(x, y, lv + 1, None)            # (a wall put in it)

    def pour(self, x: int, y: int, z: int):
        """A source where a player poured it (a can)."""
        self._put(x, y, z, (SOURCE, NOHEAD, 0))
        self.poke(x, y, z)

    def take(self, x: int, y: int, z: int):
        """A poured source taken back up (into a can): what ran from it dries."""
        self._put(x, y, z, None)
        self.poke(x, y, z)

    def step(self, near, budget: int = BUDGET) -> int:
        """One step of the rules over the cells due, where `near(cx, cy)` (a chunk someone is near, its land in
        memory). Every cell is worked out from the water as it was before the step, then all change at once.
        -> how many cells were looked at."""
        if not self.due:
            return 0
        here = []
        for c in self.due:
            if near(c[0] >> 5, c[1] >> 5):
                here.append(c)
            else:
                self.parked.add(c)
        here.sort()
        todo, rest = here[:budget], here[budget:]
        self.due = set(rest)
        self.cache = {}
        changes = [(c, v) for c in todo if (v := self.want(*c)) != self.cell(*c)]
        for (x, y, z), v in changes:
            self._put(x, y, z, v)
            self.poke(x, y, z)
        self.cache = {}                                  # (a layer full from wall to wall now: what lies over it is looked at)
        for (x, y, z), v in changes:
            if v and (x, y, z) not in self.cache:
                n0 = len(self.cache)
                if self.settled(x, y, z):
                    self.due.update((cx, cy, z + 1) for cx, cy, _ in list(self.cache)[n0:])
        self.cache = None
        return len(todo)

    def unpark(self):
        """Cells left where nobody was: looked at again (someone may be near now)."""
        self.due |= self.parked
        self.parked.clear()

    def news(self) -> list[list[int]]:
        """What the screens see changed since they were last told: [x, y, z, level] each (0: dry now)."""
        out = [[x, y, z, v] for (x, y, z), v in sorted(self.sent.items())]
        self.sent.clear()
        return out

    def within(self, x: int, y: int, w: int, h: int) -> list[tuple]:
        """Every cell with water of the rectangle: (x, y, z, level)."""
        tiles = [p for p in self.at if x <= p[0] < x + w and y <= p[1] < y + h]
        return [(i, j, z, v) for i, j in tiles for z, v in sorted(self.at[(i, j)].items())]

    def flush(self):
        db = self.store.db
        for x, y, z in self.dirty:
            v = self.at.get((x, y), {}).get(z)
            if v:
                db.execute("INSERT OR REPLACE INTO water VALUES(?,?,?,?,?,?)", (x, y, z, v, *self.how[(x, y, z)]))
            else:
                db.execute("DELETE FROM water WHERE x=? AND y=? AND z=?", (x, y, z))
        self.dirty.clear()
        self.store.set_meta("water_due", sorted(list(c) for c in self.due | self.parked))
