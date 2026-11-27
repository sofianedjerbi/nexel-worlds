"""Saving the world: flushing agents, items, creatures and timers to SQLite; unloading idle chunks."""

import json
import sqlite3

from ..cells import HIGH, LOW
from ..ores import RENAMED


class Persistence:
    """Simulation mixin: saving the world: flushing agents, items, creatures and timers to SQLite; unloading idle chunks."""

    def old_items(self):
        """What an old save holds that is not so any more: eggs that will never hatch (gone), and items named otherwise
        now (ores.py RENAMED: the generic ore and ingot are the iron ones, the sword the iron sword), in every pack, pile and
        chest."""
        for pos, pile in list(self.items.items()):
            if set(pile) == {"egg"} and self.timers.get(pos, [0, ""])[1] != "hatch":
                del self.items[pos]
                self.dirty_items.add(pos)
        def renamed(d: dict) -> bool:
            old = [k for k in d if k in RENAMED]
            for k in old:
                d[RENAMED[k]] = d.get(RENAMED[k], 0) + d.pop(k)
            return bool(old)
        for a in self.agents.values():
            renamed(a.inventory)                           # (every agent is written at each flush)
        for pos, pile in self.items.items():
            if renamed(pile):
                self.dirty_items.add(pos)
        for pos, m in self.world.meta.items():
            if isinstance(m.get("items"), dict) and renamed(m["items"]):
                self.world.dirty_meta.add(pos)

    def flush(self):
        db = self.store.db
        for a in self.agents.values():
            db.execute("UPDATE agents SET json=? WHERE id=?", (json.dumps(a.to_json()), a.id))
        for pos in self.dirty_items:
            pile = self.items.get(pos)
            if pile:
                db.execute("INSERT OR REPLACE INTO ground_items VALUES(?,?,?)", (*pos, json.dumps(pile)))
            else:
                db.execute("DELETE FROM ground_items WHERE x=? AND y=?", pos)
        self.dirty_items.clear()
        self.floors.flush()
        db.execute("DELETE FROM creatures")
        db.executemany("INSERT INTO creatures VALUES(?,?)",
                       [(c.id, json.dumps(c.to_json())) for c in self.creatures.values()])
        self.store.set_meta("vitals", 2)                      # (the players above are in half hearts and half pieces: core.py)
        self.store.set_meta("tick", self.tick)
        self.store.set_meta("fires", [[list(k), v] for k, v in self.fires.items()])
        self.store.set_meta("timers", [[x, y, t, k] for (x, y), (t, k) in self.timers.items()])
        self.water.flush()
        self.world.flush()
        if self.event_log:
            self.event_log.flush()

    def taller(self, store):
        """Once, when a world saved with 32 cells a tile (-16 to 15) is first opened with these: the world file is
        copied aside first (world.before-tall.sqlite). Its chunks are read as they were, in the taller column, and
        saved that way as they change (chunks.py): a game from before could not read them again."""
        if store.get_meta("cells") is None:
            if store.db.execute("SELECT 1 FROM chunks LIMIT 1").fetchone():
                store.commit()
                copy = sqlite3.connect(store.path.with_name(store.path.stem + ".before-tall.sqlite"))
                store.db.backup(copy)
                copy.close()
            store.set_meta("cells", HIGH - LOW + 1)

    def maintain(self):
        anchors = [(a.x, a.y) for a in self.agents.values() if a.online]
        return self.world.unload_far(anchors)

    def close(self):
        self.flush()
        if self.event_log:
            self.event_log.close()
        self.store.close()
