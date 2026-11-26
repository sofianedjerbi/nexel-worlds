"""Creatures: wandering, laying, breeding limits, coops, troughs, milking and feeding."""

from .. import tiles as T
from ..tiles import DIRS
from .constants import (
    COOP_R,
    CROWD_N,
    CROWD_R,
    FARM,
    FLEE_STRIDE,
    NAME_MAX,
    TROUGH_EVERY,
    TROUGH_R,
    sec,
)
from .entities import CREATURES, ActionError, Creature
from .wild import WILD


class Animals:
    """Simulation mixin: creatures: wandering, laying, breeding limits, coops, troughs, milking and feeding."""

    # ---------------------------------------------------------- creatures

    def step_creatures(self):
        online = [a for a in self.agents.values() if a.online]
        self.step_spawning(online)            # which chunks tick; herds and wild creatures come and go (spawning.py)
        for cid in sorted(self.creatures):
            c = self.creatures.get(cid)
            if c is None or not self.ticks(c):          # far from everyone: frozen until someone comes back
                continue
            if c.kind == "chicken":
                if not c.lay:
                    c.lay = self.tick + sec(120) + self.rng.randrange(sec(120))
                elif self.tick >= c.lay and self.crowded(c.x, c.y):
                    c.lay = self.tick + sec(90)            # no room for more: try again later
                elif self.tick >= c.lay:
                    coop = self.coop_near(c.x, c.y)
                    c.lay = self.tick + (sec(180) + self.rng.randrange(sec(180))) // (2 if coop else 1)
                    ex, ey = coop or (c.x, c.y)     # eggs go into the nest box at the coop's door
                    self.add_items(ex, ey, {"egg": 1})
                    self.emit("lay", ex, ey, id=c.id, coop=bool(coop))
            if (c.kind in ("chicken", "cow") and (self.tick + c.id) % sec(TROUGH_EVERY) == 0
                    and c.love <= self.tick and not self.crowded(c.x, c.y)):
                self.trough_feed(c)
            grows = CREATURES[c.kind].get("grows")
            if grows and self.tick - c.born >= sec(grows[1]):
                c.kind = grows[0]
                c.hp = CREATURES[c.kind]["hp"]
                self.emit("grew_up", c.x, c.y, id=c.id, kind=c.kind)
            if c.cooldown > 0:
                c.cooldown -= 1
                continue
            if c.kind in FARM and c.scared > self.tick:          # running from whoever hit it
                c.cooldown = sec(FLEE_STRIDE) - 1
                tx, ty = c.threat
                away = sorted(DIRS.values(), key=lambda d: (-(abs(c.x + d[0] - tx) + abs(c.y + d[1] - ty)), self.rng.random()))
                for d in away[:3]:                                 # the best way out that isn't toward the threat
                    if abs(c.x + d[0] - tx) + abs(c.y + d[1] - ty) >= abs(c.x - tx) + abs(c.y - ty) \
                            and self._creature_move(c, c.x + d[0], c.y + d[1]):
                        break
            elif c.kind in WILD:
                self.step_wild(c, online)
            elif c.kind in FARM:
                c.cooldown = sec(0.8) + self.rng.randrange(sec(1.2))
                d = list(DIRS.values())[self.rng.randrange(4)]
                self._creature_move(c, c.x + d[0], c.y + d[1])

    def _creature_move(self, c, x, y) -> bool:
        """A creature's step to the neighbouring (x, y): as a person's (Bodies: a jump up a layer, down onto the
        ground under it, in under a hill at its own height), where it is let. Creatures can't work doors or gates
        (houses keep them out, fenced pens keep animals in), don't walk onto someone, and take no fall that would
        hurt them."""
        if self.world.block(x, y) in ("door", "gate") or not self.stand(x, y) or self.entity_at(x, y) is not None:
            return False
        if not self.safe_step(c, x, y):
            return False
        self.step_onto(c, x, y)
        return True

    def _take_items(self, pos, item, n=1):
        pile = self.items.get(pos)
        if not pile or not pile.get(item):
            return
        pile[item] -= n
        if pile[item] <= 0:
            del pile[item]
        if not pile:
            del self.items[pos]
        self.dirty_items.add(pos)

    def crowded(self, x, y) -> bool:
        """Too many farm animals here for another one to be born."""
        return sum(1 for c in self.creatures.values()
                   if c.kind in FARM and abs(c.x - x) <= CROWD_R and abs(c.y - y) <= CROWD_R) >= CROWD_N

    def _thin_herds(self):
        """Older worlds bred without limits (thousands of chickens): keep at most CROWD_N per neighbourhood,
        oldest first."""
        cells = {}
        for cid in sorted(self.creatures):
            c = self.creatures[cid]
            if c.kind not in FARM:
                continue
            cell = (c.x // (2 * CROWD_R + 1), c.y // (2 * CROWD_R + 1))
            if cells.get(cell, 0) >= CROWD_N:
                del self.creatures[cid]
                continue
            cells[cell] = cells.get(cell, 0) + 1

    def coop_near(self, x, y):
        """The door tile (just in front of the coop) of the closest coop within COOP_R, or None."""
        best = None
        for dy in range(-COOP_R, COOP_R + 1):
            for dx in range(-COOP_R, COOP_R + 1):
                if self.world.block(x + dx, y + dy) == "coop":
                    d = abs(dx) + abs(dy)
                    if best is None or d < best[0]:
                        best = (d, x + dx, y + dy + 1)
        if best and self.stand(best[1], best[2]):
            return best[1], best[2]
        return None

    def _creature_target(self, a, args, kind=None):
        t = self._find_target(args.get("target"))
        if not isinstance(t, Creature) or (kind and t.kind != kind):
            raise ActionError("bad_target", f"that is not a {kind or 'creature'}")
        self.reach(a, t.x, t.y, self.height(t), "animal")
        return t

    def _tool_milk(self, a, args):
        cow = self._creature_target(a, args, "cow")
        if cow.milked and self.tick - cow.milked < sec(120):
            raise ActionError("not_ready", "this cow was milked recently; try again in a while")
        cow.cooldown = max(cow.cooldown, sec(1.5))  # stands still while being milked
        yield from self.wait(a, 1.2)
        cow.milked = self.tick
        a.add("milk")
        self.emit("milk", cow.x, cow.y, name=a.name, id=cow.id)
        return {"got": {"milk": 1}}

    def _tool_feed(self, a, args):
        """Feed an animal: it loves you for a while; a fed chicken lays an egg soon."""
        animal = self._creature_target(a, args)
        item = str(args.get("item", ""))
        if animal.kind not in FARM:
            raise ActionError("bad_target", f"a {animal.kind} doesn't eat that")
        if item not in T.FEED or not a.count(item):
            raise ActionError("missing_item", "feed it something edible you carry (or hay)", food=True)
        yield from self.wait(a, 0.5)
        a.add(item, -1)
        self._fed(animal)
        self.emit("love", animal.x, animal.y, by=a.name, id=animal.id, kind=animal.kind)
        return {}

    def _tool_name(self, a, args):
        """Name a creature within reach: it is yours from then on, and never goes away (spawning.py: kept).
        It takes a name tag ("Naming mobs = naming tag required"), which stays on the animal."""
        animal = self._creature_target(a, args)
        text = " ".join(str(args.get("text", "")).split())[:NAME_MAX]
        if not text:
            raise ActionError("bad_args", "give it a name: text=...")
        if a.inventory.get("name_tag", 0) < 1:
            raise ActionError("missing_item", "a name needs a name tag (craft one: 1 plank, 1 fiber)", item="name_tag", have=0)
        yield from self.wait(a, 0.3)
        if a.inventory.get("name_tag", 0) < 1:
            raise ActionError("missing_item", "the name tag is gone", item="name_tag", have=0)
        a.add("name_tag", -1)
        animal.name = text
        self.emit("named", animal.x, animal.y, by=a.name, id=animal.id, kind=animal.kind, name=text)
        return {"named": text}

    def _fed(self, animal):
        """A fed animal is in love for a while: hens lay soon, two cows in love nearby make a calf."""
        animal.love = self.tick + sec(8)
        if animal.kind == "cow":
            mate = next((o for o in self.creatures.values() if o is not animal and o.kind == "cow" and o.love > self.tick
                         and max(abs(o.x - animal.x), abs(o.y - animal.y)) <= 3), None)
            if mate and not self.crowded(animal.x, animal.y):
                calf = Creature(self.next_creature, "calf", animal.x, animal.y, CREATURES["calf"]["hp"], z=animal.z, born=self.tick)
                self.next_creature += 1
                self.creatures[calf.id] = calf
                animal.love = mate.love = 0
                self.emit("born", animal.x, animal.y, id=calf.id, kind="calf")
        if animal.kind == "chicken":
            animal.lay = min(animal.lay or self.tick + sec(3), self.tick + sec(3))

    def trough_feed(self, c):
        """Every so often an animal near a filled trough eats from it by itself."""
        for dy in range(-TROUGH_R, TROUGH_R + 1):
            for dx in range(-TROUGH_R, TROUGH_R + 1):
                x, y = c.x + dx, c.y + dy
                if self.world.block(x, y) != "trough":
                    continue
                m = self.world.meta.get((x, y)) or {}
                items = dict(m.get("items") or {})
                if not items:
                    continue
                food = sorted(items)[0]
                bites = int(m.get("bites", 0)) + 1          # a bale of hay lasts T.FEED["hay"] meals
                if bites >= T.FEED.get(food, 1):
                    bites = 0
                    items[food] -= 1
                    if not items[food]:
                        del items[food]
                self.world.set_meta(x, y, {**m, "items": items, "bites": bites})
                self._fed(c)
                self.emit("trough", x, y, id=c.id, kind=c.kind)
                return True
        return False
