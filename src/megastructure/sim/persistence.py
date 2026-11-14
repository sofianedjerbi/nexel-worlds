"""Saving the world: flushing agents, items, creatures and timers to SQLite; unloading idle chunks."""

import json


class Persistence:
    """Simulation mixin: saving the world: flushing agents, items, creatures and timers to SQLite; unloading idle chunks."""

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
        db.execute("DELETE FROM creatures")
        db.executemany("INSERT INTO creatures VALUES(?,?)",
                       [(c.id, json.dumps(c.to_json())) for c in self.creatures.values()])
        self.store.set_meta("vitals", 2)                      # (the players above are in half hearts and half pieces: core.py)
        self.store.set_meta("tick", self.tick)
        self.store.set_meta("fires", [[list(k), v] for k, v in self.fires.items()])
        self.store.set_meta("timers", [[x, y, t, k] for (x, y), (t, k) in self.timers.items()])
        self.store.set_meta("pits", [list(p) for p in self.pits])
        self.world.flush()
        if self.event_log:
            self.event_log.flush()

    def maintain(self):
        anchors = [(a.x, a.y) for a in self.agents.values() if a.online]
        return self.world.unload_far(anchors)

    def close(self):
        self.flush()
        if self.event_log:
            self.event_log.close()
        self.store.close()
