"""Water that flows (flow.py) in the world: its steps, four a second, only where someone is; what it does to who is
in it (deep enough, you swim; running, it carries you gently along); a can poured out (a source) and taken back up;
and, once, a save from before it flowed."""

import sqlite3

from ..cells import col_floor
from ..flow import N4, SOURCE, Water
from ..gen import CHUNK
from ..tiles import GROUNDS
from .constants import TICK_HZ, sec
from .entities import Agent

STEPS_HZ = 4            # steps of the water's rules a second
SWIM_DEEP = 4           # running water this deep in the cell you stand in (of 8) and you swim
PUSH_EVERY = sec(1)     # who stands idle in running water is carried a tile along it this often
UNPARK_EVERY = 20       # steps: the water left where nobody was is looked at again


class Waters:
    """Simulation mixin: water that flows."""

    def open_water(self, store):
        self.water = Water(store, self.world)
        self.water_steps = 0
        if store.get_meta("flow") is None:
            self.old_water(store)
            store.set_meta("flow", 1)
            store.commit()

    def old_water(self, store):
        """Once, when a save from before water flowed is first opened: it is copied aside first
        (world.before-flow.sqlite). Its seas, rivers and lakes (water grounds) are sources as they are: nothing in them
        changes. Where one lies beside an empty cell at its own height, or over one (a hole or a tunnel dug beside or
        under it, dry under the old rules), that cell is due: it floods from the first step someone is near. The old
        rule's list of pits (tilled soil that turned to water at once) is dropped."""
        if store.db.execute("SELECT 1 FROM chunks LIMIT 1").fetchone():
            store.commit()
            copy = sqlite3.connect(store.path.with_name(store.path.stem + ".before-flow.sqlite"))
            store.db.backup(copy)
            copy.close()
            saved = {(cx, cy) for cx, cy in store.db.execute("SELECT cx, cy FROM chunks")}
            for cx, cy in sorted(saved):
                c = self.world.chunk(cx, cy)
                for i, g in enumerate(c.ground):
                    if not GROUNDS[g].liquid:
                        continue
                    x, y, z = cx * CHUNK + i % CHUNK, cy * CHUNK + i // CHUNK, col_floor(c.cols[i])
                    for nx, ny, nz in [(x + dx, y + dy, z) for dx, dy in N4] + [(x, y, z - 1)]:
                        if (nx >> 5, ny >> 5) in saved and not self.water.firm(nx, ny, nz):
                            self.water.due.add((nx, ny, nz))
        store.db.execute("DELETE FROM meta WHERE key='pits'")

    # ------------------------------------------------------------------ the steps
    def near_water(self, cx: int, cy: int) -> bool:
        """Water runs in a chunk someone is near (spawning.py: the ticking area), its land and the land round it in
        memory (a step never makes land load or be made)."""
        if (cx, cy) not in self.ticking:
            return False
        return not self.keep_loaded or all((cx + dx, cy + dy) in self.world.chunks for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def step_water(self):
        if self.tick * STEPS_HZ // TICK_HZ != (self.tick - 1) * STEPS_HZ // TICK_HZ:
            self.water_steps += 1
            if self.water_steps % UNPARK_EVERY == 0:
                self.water.unpark()
            self.water.step(self.near_water)
        if self.water.sent:
            news = self.water.news()
            self.stats["tiles_changed"] += len(news)
            self.emit("water", news[0][0], news[0][1], cells=news)     # (for the screens: no agent is told each cell)
        if self.water.at and self.tick % PUSH_EVERY == 0:
            self.carry()

    # ------------------------------------------------------------------ who is in it
    def water_in(self, b) -> int:
        """The water in the cell a body stands in (over its feet): 0 to 8."""
        return self.water.column(b.x, b.y).get(self.height(b) + 1, 0)

    def wading(self, a: Agent) -> bool:
        """In running (or poured) water deep enough to swim in."""
        return not a.sailing and self.water_in(a) >= SWIM_DEEP

    def flow_way(self, x: int, y: int, z: int):
        """Where running water at (x, y, z) goes: the wet neighbour it falls down from, else the one it runs down to
        (the lowest level); None in still water (a source, a level pool)."""
        w = self.water
        here = w.lv(x, y, z)
        if not here or here == SOURCE:
            return None
        best, way = here, None
        for dx, dy in N4:
            nx, ny = x + dx, y + dy
            v = w.lv(nx, ny, z)
            if w.firm(nx, ny, z) or not v:
                continue
            if w.lv(nx, ny, z + 1) == 0 and w.lv(nx, ny, z - 1) and not w.firm(nx, ny, z - 1) and v <= here:
                return dx, dy                                  # it falls there
            if v < best:
                best, way = v, (dx, dy)
        return way

    def carry(self):
        """Running water gently carries who stands in it doing nothing, a tile along it (people, not boats)."""
        for aid in sorted(self.agents):
            a = self.agents[aid]
            if not a.online or a.hp <= 0 or a.sailing or a.action is not None or a.aside is not None or not self.water_in(a):
                continue
            way = self.flow_way(a.x, a.y, self.height(a) + 1)
            if way and self.can_go(a, a.x + way[0], a.y + way[1], jump=False):
                self.move(a, a.x + way[0], a.y + way[1])
                self.emit("carried", a.x, a.y, name=a.name)

    # ------------------------------------------------------------------ a can of it
    def pour_spot(self, x: int, y: int) -> int | None:
        """The cell a can is poured into on the tile: the empty one over its ground; None if it holds no water there."""
        z = self.world.top(x, y) + 1
        if self.water.firm(x, y, z) or GROUNDS[self.world.get(x, y)[0]].liquid or self.water.lv(x, y, z):
            return None
        return z

    def poured_at(self, x: int, y: int) -> int | None:
        """A source poured on the tile (the highest), to be taken back up into a can."""
        return max((z for z in self.water.column(x, y) if self.water.poured(x, y, z)), default=None)
