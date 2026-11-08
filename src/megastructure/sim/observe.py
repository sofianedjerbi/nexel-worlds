"""What an agent perceives: the observation dict of the agent API."""

from .constants import VIEW_R
from .entities import CREATURES, Agent
from .specs import LEGEND


class Observation:
    """Simulation mixin: what an agent perceives: the observation dict of the agent API."""

    # -------------------------------------------------------- observation

    def observe(self, a: Agent, consume_events=True) -> dict:
        R = VIEW_R
        ents = {}
        out_ents = []
        for o in self.agents.values():
            if o is not a and o.online and abs(o.x - a.x) <= R and abs(o.y - a.y) <= R:
                ents[(o.x, o.y)] = "P"
                out_ents.append({"id": o.id, "kind": "agent", "name": o.name, "dx": o.x - a.x, "dy": o.y - a.y,
                                 "hp": o.hp, "holding": self.best_weapon(o) or "nothing",
                                 "doing": o.action.tool if o.action else "idle"})
        for c in self.creatures.values():
            if abs(c.x - a.x) <= R and abs(c.y - a.y) <= R:
                ents.setdefault((c.x, c.y), CREATURES[c.kind]["char"])
                out_ents.append({"id": c.id, "kind": c.kind, "dx": c.x - a.x, "dy": c.y - a.y, "hp": c.hp})
        out_ents.sort(key=lambda e: abs(e["dx"]) + abs(e["dy"]))
        grid, used = [], set()
        for y in range(a.y - R, a.y + R + 1):
            row = []
            for x in range(a.x - R, a.x + R + 1):
                if (x, y) == (a.x, a.y):
                    ch = "@"
                elif (x, y) in ents:
                    ch = ents[(x, y)]
                else:
                    ch = self.world.char(x, y)
                    if ch in "Zz":     # the rest of a structure shows as the structure
                        ch = self.world.char(*self.resolve(x, y))
                    if (x, y) in self.items and self.world.block(x, y) == "none":
                        ch = "$"
                used.add(ch)
                row.append(ch)
            grid.append("".join(row))
        items, signs = [], []
        for (x, y), pile in self.items.items():
            if abs(x - a.x) <= R and abs(y - a.y) <= R and pile:
                items.append({"dx": x - a.x, "dy": y - a.y, "items": pile})
        for (x, y), m in self.world.meta.items():
            if abs(x - a.x) <= R and abs(y - a.y) <= R and "text" in m:
                signs.append({"dx": x - a.x, "dy": y - a.y, "kind": self.world.block(x, y), "text": m["text"]})
        items.sort(key=lambda e: abs(e["dx"]) + abs(e["dy"]))
        events = a.events
        if consume_events:
            a.events = []
        here_g, here_b = self.world.ground(a.x, a.y), self.world.block(a.x, a.y)
        return {
            "tick": self.tick,
            "time": self.clock(),
            "self": {"id": a.id, "name": a.name, "x": a.x, "y": a.y, "hp": a.hp, "hunger": a.hunger,
                     "energy": a.energy, "inventory": dict(sorted(a.inventory.items())), "deaths": a.deaths,
                     "action": a.action.tool if a.action else None,
                     "spawn": a.spawn, "sailing": a.sailing, "can": a.can,
                     "standing_on": here_g if here_b == "none" else f"{here_g}+{here_b}",
                     "sheltered": self.sheltered(a.x, a.y)},
            "grid": grid,
            "legend": {ch: LEGEND[ch] for ch in sorted(used) if ch in LEGEND},
            "entities": out_ents[:20],
            "items": items[:15],
            "signs": signs[:10],
            "events": events,
        }
