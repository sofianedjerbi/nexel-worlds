"""Carrying things: picking up, dropping, giving, chests/baskets/troughs."""

from .. import tiles as T
from .constants import SAY_R
from .entities import ActionError, Agent


class Items:
    """Simulation mixin: carrying things: picking up, dropping, giving, chests/baskets/troughs."""

    @staticmethod

    def _n(args) -> int:
        try:
            return max(1, int(args.get("n", 1)))
        except (TypeError, ValueError):
            raise ActionError("bad_args", "n must be a positive integer")

    def _tool_pick_up(self, a, args):
        yield from self.wait(a, 0.1)
        pile = self.items.get((a.x, a.y))
        if not pile:
            raise ActionError("nothing_here", "no items on your tile")
        want = args.get("item")
        got = {}
        for k in list(pile):
            if want and k != want:
                continue
            got[k] = pile.pop(k)
            a.add(k, got[k])
        if not pile:
            del self.items[(a.x, a.y)]
        self.dirty_items.add((a.x, a.y))
        if not got:
            raise ActionError("nothing_here", f"no {want} on your tile")
        self.emit("pick_up", a.x, a.y, name=a.name, items=got)
        return {"got": got}

    def _tool_drop(self, a, args):
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}")
        yield from self.wait(a, 0.1)
        n = min(n, a.count(item))
        a.add(item, -n)
        self.add_items(a.x, a.y, {item: n})
        self.emit("drop", a.x, a.y, name=a.name, items={item: n})
        return {}

    def _tool_give(self, a, args):
        t = self._find_target(args.get("target"))
        if not isinstance(t, Agent) or t is a:
            raise ActionError("bad_target", "you can only give to another agent")
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}")
        if not self.near(a, t.x, t.y, 2, self.height(t)):
            raise ActionError("out_of_range", "target must be within 2 tiles")
        yield from self.wait(a, 0.2)
        if a.count(item) < n or not self.near(a, t.x, t.y, 2, self.height(t)):
            raise ActionError("failed", "conditions changed")
        a.add(item, -n)
        t.add(item, n)
        self.stats["trades"] += 1
        a.bump("gave")
        self.emit("give", a.x, a.y, radius=SAY_R, **{"from": a.name}, to=t.name, items={item: n})
        return {"to": t.name}

    def _chest(self, a, args):
        x, y = self.target(a, args)
        if self.world.block(x, y) not in ("chest", "basket", "trough"):
            raise ActionError("no_chest", f"{args.get('dir') or 'that tile'} is {self.describe(x, y)}")
        return x, y

    def _tool_store(self, a, args):
        x, y = self._chest(a, args)
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}")
        if self.world.block(x, y) == "trough" and item not in T.FEED:
            raise ActionError("bad_item", "troughs take animal feed: hay or food")
        yield from self.wait(a, 0.2)
        self._chest(a, args)
        n = min(n, a.count(item))
        m = dict(self.world.meta.get((x, y), {}))
        m["items"] = self._merge(m.get("items", {}), {item: n})
        a.add(item, -n)
        self.world.set_meta(x, y, m)
        self.emit("chest", x, y, radius=4, name=a.name, stored={item: n})
        return {"chest": m["items"]}

    def _tool_take(self, a, args):
        x, y = self._chest(a, args)
        yield from self.wait(a, 0.2)
        self._chest(a, args)
        m = dict(self.world.meta.get((x, y), {}))
        items = dict(m.get("items", {}))
        item = args.get("item")
        if args.get("list"):
            return {"chest": items}
        if not item:                                  # no item named: take everything (opening a chest)
            for k, n in items.items():
                a.add(k, n)
            m["items"] = {}
            self.world.set_meta(x, y, m)
            if items:
                self.emit("chest", x, y, radius=4, name=a.name, took=items)
            return {"chest": {}, "took": items}
        n = min(self._n(args), items.get(item, 0))
        if n <= 0:
            raise ActionError("missing_item", f"chest has no {item}; contents: {items}")
        items[item] -= n
        if not items[item]:
            del items[item]
        m["items"] = items
        self.world.set_meta(x, y, m)
        a.add(item, n)
        self.emit("chest", x, y, radius=4, name=a.name, took={item: n})
        return {"chest": items}
