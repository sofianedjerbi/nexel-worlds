"""What spectators are sent about the part of the world they watch."""

import json
from types import SimpleNamespace

from .gen import HIGH, SEA, col_floor, col_runs
from .sim.constants import TICK_HZ
from .sim.hearing import LAND, hears
from .sim.wild import WILD
from .tiles import BLOCKS, DIRS, GROUNDS, B

FAR_VIEW = 160          # tiles past what a page watches that it may ask the far land of (server.py `region` far: the HD look's horizon, hd.js viewOf)
QUEUE_MAX = 2000       # messages a spectator may have waiting: past that, new ones are dropped (Views._broadcast)


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
                 "run": bool(a.action.args.get("run")) if a.action else False, "sail": a.sailing, "z": self.sim.height(a),
                 **({"worn": a.worn} if a.worn else {}), **({"race": a.race} if a.race != "cat" else {}), **({"bot": True} if a.bot else {}), **({"swim": True} if self.sim.swimming(a) else {}), **({"vn": a.via_done} if a.via_done else {}),
                 **({"eats": a.aside.args.get("item")} if a.aside else {}), **({"held": a.held} if a.held and a.count(a.held) else {})}       # (what their hands are doing meanwhile)
                for a in self.sim.agents.values() if a.online and x <= a.x < x + w and y <= a.y < y + h]
        ents += [{"kind": c.kind, "id": c.id, "x": c.x, "y": c.y, "z": self.sim.height(c), "hp": c.hp, "love": c.love > self.sim.tick, "scared": c.scared > self.sim.tick,
                  **({"act": c.mode, "dir": list(c.dir), "run": c.mode == "charge"} if c.kind in WILD else {}), **({"angry": True} if c.angry > self.sim.tick else {}), **({"name": c.name} if c.name else {})}
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

    @staticmethod
    def far_near(watch, x, y, w, h) -> bool:
        """Is a far region within FAR_VIEW tiles of the rectangle the page watches (its screen and the land its HD look shows,
        state.js `watch`)? A page that has said nothing yet is given nothing far."""
        if not watch or w > 64 or h > 64:
            return False
        wx, wy, ww, wh = watch
        return max(wx - (x + w), x - (wx + ww), wy - (y + h), y - (wy + wh)) <= FAR_VIEW

    def far_ready(self, x, y, w, h) -> bool:
        """The far land a page's HD look draws to its horizon (state.js: `far`): its chunks are brought in off the tick
        (world.prefetch: from disk, or made on a thread) and the page asks again. Made at once, 30 ms a chunk, they
        stalled the ticks: a player on a mountain walked in jerks."""
        world, cs = self.sim.world, 32
        return all([world.prefetch(cx, cy) for cy in range(y // cs, (y + h - 1) // cs + 1) for cx in range(x // cs, (x + w - 1) // cs + 1)])

    def region(self, x, y, w, h) -> dict:
        w, h = min(int(w), 256), min(int(h), 256)
        world = self.sim.world
        rows = ["".join(world.char(i, j) for i in range(x, x + w)) for j in range(y, y + h)]
        ground = ["".join(GROUNDS[world.get(i, j)[0]].char for i in range(x, x + w)) for j in range(y, y + h)]
        # the land (without what is built over it): a char per tile, SEA + its lowest ground's height; and for the tiles where that
        # isn't all (a cave under a hill), their whole column of cells, by index in the region: the heights where it changes (gen.col_runs)
        raw = [self.sim.land_col(i, j) for j in range(y, y + h) for i in range(x, x + w)]
        levels = ["".join(chr(SEA + col_floor(v)) for v in raw[j * w:(j + 1) * w]) for j in range(h)]
        cols = {str(i): col_runs(v) for i, v in enumerate(raw) if v & (v + 1)}
        # what a tile is made of: the block put on its top ("s", "d": landblocks.py), where one was; and every tile's highest stone cell, a
        # char each, SEA + it, as the levels (world.py made_of: earth over it, stone from it down; HIGH and over: stone at every height)
        mats = {str((j - y) * w + i - x): m for j in range(y, y + h) for i in range(x, x + w) if (m := self.sim.placed.mat(i, j, col_runs(raw[(j - y) * w + i - x])))}
        stones = ["".join(chr(SEA + min(HIGH, world.stone(i, j))) for i in range(x, x + w)) for j in range(y, y + h)]
        # the ore that shows (sim/underground.py shown_ores: a cell of it with air on a side), by tile index: {z: item}. Never what is shut in the rock
        ores = {str((j - y) * w + i - x): {str(z): o for z, o in sh.items()} for j in range(y, y + h) for i in range(x, x + w) if (sh := self.sim.shown_ores(i, j))}
        # what is built over the land (sim/storeys.py): [tile's index, height, kind, the char of what stands on it]
        floors = [[(j - y) * w + i - x, z, kind, BLOCKS[B[thing]].char] for i, j, z, kind, thing in self.sim.floors.within(x, y, w, h)]
        water = [[(j - y) * w + i - x, z, v] for i, j, z, v in self.sim.water.within(x, y, w, h)]       # (water that runs, and what was poured: [tile's index, height, level], flow.py)
        return {**({"cols": cols} if cols else {}), **({"mats": mats} if mats else {}), **({"floors": floors} if floors else {}), **({"water": water} if water else {}), **({"ores": ores} if ores else {}), "sea": SEA, "x": x, "y": y, "w": w, "h": h, "rows": rows, "ground": ground, "stones": stones, "levels": levels, "entities": self.entities_in(x, y, w, h), "tick": self.sim.tick, "time": self.sim.clock(),
                "night": self.sim.is_night(), "phase": round(self.sim.time_of_day(), 4)}

    # ----------------------------------------------------------- what they are sent, as it happens

    def listener(self, q, rect):
        """Who a screen is, for what it perceives (hearing.py): the player on it (the page says who: `me`), where they
        stand; a screen that only watches, the middle of what it watches."""
        a = self.sim.agents.get(self.players.get(q))
        x, y = (a.x, a.y) if a else (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2) if rect else (None, None)
        return SimpleNamespace(x=x, y=y, z=a and a.z, name=a and a.name, rect=rect)

    def _broadcast(self, ev):
        """A screen is sent the events it perceives, by the rule an agent hears by (hearing.py), and every change of
        the land. One whose queue is full (thousands of tiles changing at once: a flood) misses some: once it has
        caught up it is told to ask for its land again (`resync`: push_ticks), so its picture of the world never
        stays wrong."""
        msg = None
        for q, rect in list(self.spectators.items()):
            if ev["type"] not in LAND and not hears(self.listener(q, rect), ev):
                continue
            msg = msg or json.dumps({"type": "event", "ev": ev})
            if q.qsize() < QUEUE_MAX:
                q.put_nowait(msg)
            else:
                self.behind.add(q)

    def push_ticks(self):
        """Every tick, each spectator gets the entities inside the rect it watches; agents whose
        multi-tick action just started get a progress notice (so clients can show a bar at once)."""
        for aid, push in list(self.notify.items()):
            for act in (self.sim.agents[aid].action, self.sim.agents[aid].aside):       # (and what the hands are doing: eating)
                if (act is not None and act.started_tick == self.sim.tick and act.tool not in ("step", "move_to", "walk")
                        and act.expected >= 2):
                    push({"type": "progress", "tool": act.tool, "ticks": act.expected, "tick_hz": TICK_HZ})
        for q in [q for q in self.behind if q.qsize() < QUEUE_MAX // 2]:
            self.behind.discard(q)
            if q in self.spectators:
                q.put_nowait('{"type":"resync"}')
        if not self.spectators:
            return
        head = {"type": "tick", "tick": self.sim.tick, "time": self.sim.clock(), "night": self.sim.is_night(),
                "phase": round(self.sim.time_of_day(), 4)}
        for q, rect in list(self.spectators.items()):
            if rect is not None and q.qsize() < QUEUE_MAX:
                q.put_nowait(json.dumps({**head, "entities": self.entities_in(*rect), "items": self.items_in(*rect),
                                         "mail": self.mail_in(*rect), "troughs": self.troughs_in(*rect),
                                         "fires": [[fx, fy] for fx, fy in self.sim.fires
                                                   if rect[0] <= fx < rect[0] + rect[2] and rect[1] <= fy < rect[1] + rect[3]]},
                                        separators=(",", ":")))
