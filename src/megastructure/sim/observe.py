"""What an agent perceives: the observation dict of the agent API."""

from .constants import VIEW_R


def height_char(lv: int) -> str:
    """A height for the agents: 0-9 and A, B, C (10-12) up; a, b, c... (-1, -2, -3...) down in pits."""
    return str(lv) if 0 <= lv <= 9 else chr(55 + lv) if lv > 9 else chr(96 - lv)


from .entities import CREATURES, Agent
from .progress import level_of
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
        # heights, same window: a digit per tile (0 is low ground), a capital letter (B = 1...) for stairs going south;
        # only sent when there is any relief in view
        inside = self.in_cave(a)            # (outside the caves, their roofs are the ground)
        heights = ["".join(height_char(self.world.level(x, y) + (0 if inside else self.world.roof(x, y))) for x in range(a.x - R, a.x + R + 1))
                   for y in range(a.y - R, a.y + R + 1)]
        if all(set(h) <= {"0"} for h in heights):
            heights = None
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
                     "inventory": dict(sorted(a.inventory.items())), "wearing": dict(a.worn), "armor": self.armor(a), "race": a.race, "deaths": a.deaths,
                     "action": a.action.tool if a.action else None,
                     "spawn": a.spawn, "sailing": a.sailing, "can": a.can, "xp": a.xp, "level": level_of(a.xp)[0], "in_cave": self.in_cave(a), "z": self.height(a),
                     "standing_on": here_g if here_b == "none" else f"{here_g}+{here_b}",
                     "sheltered": self.sheltered(a.x, a.y)},
            "grid": grid,
            **({"heights": heights} if heights else {}),
            "legend": {ch: LEGEND[ch] for ch in sorted(used) if ch in LEGEND},
            "entities": out_ents[:20],
            "items": items[:15],
            "signs": signs[:10],
            "events": events,
        }
