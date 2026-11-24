"""Clothes and armor: five slots (head, top, pants, shoes, effect), one item in each.

Wearing takes the item out of your bag and puts it on you; what was in that slot comes back. Clothes are looks only;
leather, iron, gold and Old Mossback's shell also turn part of a blow. Charms (the effect slot) are looks only.
How each piece is drawn is the client's business (web/js/wear.js); the recipes are in tiles.py.
"""

from ..tiles import ARMOR, WEAR
from .entities import ActionError, Agent

SLOTS = ("head", "top", "pants", "shoes", "effect")
ARMOR_CAP = 45                                   # percent of a blow that armor can turn, at most


class Wear:
    """Simulation mixin: wearing and taking off, and what armor does."""

    def _tool_wear(self, a, args):
        item = str(args.get("item", ""))
        if item not in WEAR:
            raise ActionError("not_wearable", "that is not something to wear")
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}")
        yield from self.wait(a, 0.4)
        if not a.count(item):
            raise ActionError("missing_item", "it's gone")
        slot = WEAR[item]
        old = a.worn.get(slot)
        a.add(item, -1)
        if old:
            a.add(old)
        a.worn[slot] = item
        self.emit("wear", a.x, a.y, name=a.name, item=item, slot=slot)
        return {"wearing": dict(a.worn), **({"took_off": old} if old else {})}

    def _tool_unwear(self, a, args):
        slot = str(args.get("slot", ""))
        if slot not in SLOTS:
            raise ActionError("bad_args", f"slot must be one of {', '.join(SLOTS)}")
        if not a.worn.get(slot):
            raise ActionError("nothing_worn", f"you wear nothing on your {slot}")
        yield from self.wait(a, 0.3)
        item = a.worn.pop(slot, None)
        if item:
            a.add(item)
            self.emit("wear", a.x, a.y, name=a.name, item=None, slot=slot)
        return {"wearing": dict(a.worn), "took_off": item}

    def armor(self, a: Agent) -> int:
        """The percent of a blow that what `a` wears turns."""
        return min(ARMOR_CAP, sum(ARMOR.get(item, 0) for item in a.worn.values()))

    def guarded(self, target, dmg: float) -> float:
        """A blow of `dmg` half hearts on `target`, after armor: to the half, never less than one."""
        if not isinstance(target, Agent) or not target.worn:
            return dmg
        return max(0.5, round(dmg * (100 - self.armor(target)) / 100 * 2) / 2)
