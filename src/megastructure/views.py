"""What spectators are sent about the part of the world they watch."""

from .tiles import DIRS, GROUNDS


class Views:
    """GameServer mixin: the entities, items, mail, troughs and tiles inside a watched rectangle."""

    def entities_in(self, x, y, w, h) -> list:
        ents = [{"kind": "agent", "name": a.name, "id": a.id, "x": a.x, "y": a.y, "hp": a.hp,
                 "doing": a.action.tool if a.action else None, "weapon": self.sim.best_weapon(a),
                 "dir": a.action.args.get("dir") if a.action else None,
                 "tid": a.action.args.get("target") if a.action else None,
                 "at": self.aimed(a),
                 "with": a.action.args.get("with") if a.action else None,
                 "item": a.action.args.get("item") if a.action else None,
                 "run": bool(a.action.args.get("run")) if a.action else False, "sail": a.sailing}
                for a in self.sim.agents.values() if a.online and x <= a.x < x + w and y <= a.y < y + h]
        ents += [{"kind": c.kind, "id": c.id, "x": c.x, "y": c.y, "hp": c.hp, "love": c.love > self.sim.tick, "scared": c.scared > self.sim.tick}
                 for c in self.sim.creatures.values() if x <= c.x < x + w and y <= c.y < y + h]
        return ents

    def mail_in(self, x, y, w, h) -> list:
        return [[mx, my, len(m["letters"])] for (mx, my), m in self.sim.world.meta.items()
                if m.get("letters") and x <= mx < x + w and y <= my < y + h]

    def aimed(self, a) -> list | None:
        """The tile an agent's current action works on (for the strike effects other players see)."""
        args = a.action.args if a.action else {}
        if "x" in args and "y" in args and args.get("dir") is None:
            return [args["x"], args["y"]]
        d = DIRS.get(str(args.get("dir", "")).upper())
        return [a.x + d[0], a.y + d[1]] if d else None

    def troughs_in(self, x, y, w, h) -> list:
        """Troughs with feed in them (the client draws hay in the box)."""
        return [[tx, ty] for (tx, ty), m in self.sim.world.meta.items()
                if m.get("items") and x <= tx < x + w and y <= ty < y + h and self.sim.world.block(tx, ty) == "trough"]

    def items_in(self, x, y, w, h) -> list:
        return [[ix, iy, pile] for (ix, iy), pile in self.sim.items.items() if pile and x <= ix < x + w and y <= iy < y + h]

    def region(self, x, y, w, h) -> dict:
        w, h = min(int(w), 256), min(int(h), 256)
        world = self.sim.world
        rows = ["".join(world.char(i, j) for i in range(x, x + w)) for j in range(y, y + h)]
        ground = ["".join(GROUNDS[world.get(i, j)[0]].char for i in range(x, x + w)) for j in range(y, y + h)]
        # heights: a digit per tile, or a capital letter (A = 0, B = 1...) where stairs lead down to the south
        levels = ["".join(chr(48 + (v & 15)) for v in (world.level_raw(i, j) for i in range(x, x + w)))
                  for j in range(y, y + h)]
        return {"x": x, "y": y, "w": w, "h": h, "rows": rows, "ground": ground, "levels": levels, "entities": self.entities_in(x, y, w, h), "tick": self.sim.tick, "time": self.sim.clock(),
                "night": self.sim.is_night(), "phase": round(self.sim.time_of_day(), 4)}
