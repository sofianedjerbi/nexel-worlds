"""Carrying things: picking up, dropping, giving, chests/baskets/troughs."""

from .. import tiles as T
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
        got = self.take_pile(a, (a.x, a.y), args.get("item"), asked=True)
        if not got:
            raise ActionError("nothing_here", f"no {args.get('item') or 'items'} on your tile")
        return {"got": got}

    def take_pile(self, a, pos, want=None, asked=False, **how) -> dict:
        """Put what lies at `pos` into `a`'s bag (all of it, or only `want`): the one way a pile is taken, walked
        over (Movement.arrive), drawn in (Progress.attract_items) or picked up. What `a` let go of there stays down
        unless `asked` for (it was only the magnet that left it: stepping onto your drop took it straight back)."""
        pile = self.items.get(pos)
        if not pile or (not asked and self.item_left.get(pos) == a.id):
            return {}
        got = {k: pile.pop(k) for k in list(pile) if not want or k == want}
        for k, n in got.items():
            a.add(k, n)
        if not pile:
            del self.items[pos]
            self.item_since.pop(pos, None)
        if got:
            self.dirty_items.add(pos)
            self.emit("pick_up", *pos, name=a.name, items=got, **how)
        return got

    def _tool_drop(self, a, args):
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}", item=item, have=a.count(item), need=n)
        yield from self.wait(a, 0.1)
        n = min(n, a.count(item))
        a.add(item, -n)
        x, y = a.x, a.y                                    # on your tile; or, given `dir`, on the one in front if you could
        d = T.DIRS.get(str(args.get("dir") or "").upper())  # walk there (a person lets go of it before their feet: seen)
        if d and self.can_go(a, a.x + d[0], a.y + d[1]):
            x, y = a.x + d[0], a.y + d[1]
        self.add_items(x, y, {item: n})
        self.item_left[(x, y)] = a.id                      # (it stays down: the magnet does not hand it straight back, progress.py)
        self.emit("drop", x, y, name=a.name, items={item: n}, ox=a.x - x, oy=a.y - y)   # (ox, oy: where it was let go of, from where it lies)
        return {}

    def _tool_give(self, a, args):
        t = self._find_target(args.get("target"))
        if not isinstance(t, Agent) or t is a:
            raise ActionError("bad_target", "you can only give to another agent")
        item, n = str(args.get("item", "")), self._n(args)
        if a.count(item) < n:
            raise ActionError("missing_item", f"you have {a.count(item)} {item}", item=item, have=a.count(item), need=n)
        self.reach(a, t.x, t.y, self.height(t), "give")
        yield from self.wait(a, 0.2)
        if a.count(item) < n or not self.within(a, "give", t.x, t.y, self.height(t)):
            raise ActionError("failed", "conditions changed")
        a.add(item, -n)
        t.add(item, n)
        self.stats["trades"] += 1
        a.bump("gave")
        self.emit("give", a.x, a.y, **{"from": a.name}, to=t.name, items={item: n})
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
            raise ActionError("missing_item", f"you have {a.count(item)} {item}", item=item, have=a.count(item), need=n)
        if self.world.block(x, y) == "trough" and item not in T.FEED:
            raise ActionError("bad_item", "troughs take animal feed: hay or food")
        yield from self.wait(a, 0.2)
        self._chest(a, args)
        n = min(n, a.count(item))
        m = dict(self.world.meta.get((x, y), {}))
        m["items"] = self._merge(m.get("items", {}), {item: n})
        a.add(item, -n)
        self.world.set_meta(x, y, m)
        self.emit("chest", x, y, name=a.name, stored={item: n})
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
                self.emit("chest", x, y, name=a.name, took=items)
            return {"chest": {}, "took": items}
        n = min(self._n(args), items.get(item, 0))
        if n <= 0:
            raise ActionError("missing_item", f"chest has no {item}; contents: {items}", item=item, have=0, where="chest")
        items[item] -= n
        if not items[item]:
            del items[item]
        m["items"] = items
        self.world.set_meta(x, y, m)
        a.add(item, n)
        self.emit("chest", x, y, name=a.name, took={item: n})
        return {"chest": items}
