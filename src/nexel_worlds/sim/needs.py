"""Health and food, as the sandbox classic has them; eating; beds (where you wake up); watering crops.

Health is ten hearts, counted in halves (20); food ten pieces, counted in halves (20). Food does not go down by
itself: what you do tires you (constants.TIRES: walking a little, sprinting three times that, a swing, a blow taken,
digging, and most of all healing), and each time tiredness reaches 4 a point of saturation goes, or of food when
there is none left. Saturation is food in reserve, unseen: eating gives both, good food more of it.
With nine pieces of food or more you heal, half a heart every 4 s; with the bar full and saturation left, every half
second. With three pieces or fewer you cannot sprint. With none, half a heart goes every 4 s.
"""

from .. import tiles as T
from .constants import (
    CAN_SIZE,
    EAT_SECONDS,
    FAST_HEAL_EVERY,
    FOOD_MAX,
    HEAL_EVERY,
    HEAL_FOOD,
    HP_MAX,
    OLD_SCALE,
    PICNIC,
    STARVE_EVERY,
    TIRED_MAX,
    TIRES,
    sec,
)
from .entities import ActionError


class Needs:
    """Simulation mixin: health and food; eating; beds (where you wake up); watering crops."""

    def old_vitals(self, before: bool):
        """On opening a world: players saved when health and food were 0 to 100 are put in half hearts and half
        pieces. The save says which it is (`vitals`, written with the players: persistence.py), and so do the
        numbers: more than full is the old scale. (The mark was written on opening: a server that opened the world
        and died before saving left it marked and not converted, and the players would have woken with fifty hearts.)"""
        for a in self.agents.values():
            if before or a.hp > HP_MAX or a.hunger > FOOD_MAX:
                a.hp, a.hunger = max(0.5, round(a.hp / OLD_SCALE * 2) / 2), round(a.hunger / OLD_SCALE)

    def tire(self, a, what: str, n: float = 1):
        """Something that tires (constants.TIRES), n times: at 4, a point of saturation goes, or of food."""
        a.tired += TIRES[what] * n
        while a.tired >= TIRED_MAX:
            a.tired -= TIRED_MAX
            if a.sat > 0:
                a.sat = max(0.0, a.sat - 1)
            elif a.hunger > 0:
                a.hunger -= 1

    def step_needs(self):
        t = self.tick
        for a in self.agents.values():
            if not a.online:
                continue
            if 0 < a.hp < HP_MAX:
                if a.hunger >= FOOD_MAX and a.sat >= TIRES["heal"] / TIRED_MAX and t % FAST_HEAL_EVERY == 0:
                    a.hp = min(HP_MAX, a.hp + 1)              # (the reserve pays for it: a point and a half each time)
                    self.tire(a, "heal")
                elif a.hunger >= HEAL_FOOD and t % HEAL_EVERY == 0:
                    a.hp = min(HP_MAX, a.hp + 1)
                    self.tire(a, "heal")
            if a.hunger <= 0 and t % STARVE_EVERY == 0:
                self.damage(a, 1, "starvation")
            if (a.x, a.y) in self.fires and t % sec(1) == 0:
                self.damage(a, 1, "fire")

    def _tool_eat(self, a, args):
        item = str(args.get("item", ""))
        if item not in T.FOOD:
            raise ActionError("not_food", f"food: {', '.join(T.FOOD)}")
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}", item=item, have=0)
        if a.hunger >= FOOD_MAX:
            raise ActionError("full", "you're full")
        yield from self.wait(a, EAT_SECONDS)       # a proper bite, with the hands (constants.ASIDE): walking goes on, doing something else stops it
        if not a.count(item):
            raise ActionError("missing_item", "it's gone", item=item, have=0)
        a.add(item, -1)
        here = self.resolve(a.x, a.y)
        picnic = self.world.block(*here) == "picnic_blanket"
        gain = int(T.FOOD[item] * (PICNIC if picnic else 1))
        a.hunger = min(FOOD_MAX, a.hunger + gain)
        a.sat = min(float(a.hunger), a.sat + gain * 2 * T.RICH.get(item, T.PLAIN))     # (never more in reserve than on the bar)
        if picnic:
            self.emit("picnic", a.x, a.y, name=a.name)
        return {"picnic": picnic} if picnic else {}

    def _tool_sleep(self, a, args):
        """Lie down in a bed nearby: you'll wake up there after dying (and it heals a little)."""
        x, y = self.target(a, args)
        z = self.surface(a, x, y)                          # (a bed upstairs: on the floor nearest your own height)
        if self.thing(x, y, z) != "bed":
            raise ActionError("no_bed", f"{args.get('dir')} is {self.describe(x, y)}, not a bed")
        yield from self.wait(a, 1)
        a.hp = min(HP_MAX, a.hp + 2)
        a.spawn = [x, y, z] if self.floors.get(x, y, z) else [x, y]
        return {"spawn": a.spawn}

    def _tool_water(self, a, args):
        """Water a planted tile with a watering can: it grows twice as fast until the next stage."""
        x, y = self.resolve(*self.target(a, args))
        if self.held(a, args) != "watering_can":
            raise ActionError("need_tool", "watering needs the watering can in hand (with: watering_can)"
                              + ("" if a.count("watering_can") else "; craft one at a workbench"), tool="watering_can", have=a.count("watering_can") > 0)
        if self.world.block(x, y) == "well" or (self.world.block(x, y) == "none" and self.world.ground(x, y) in T.DEPTH):
            yield from self.wait(a, 0.6)
            a.can = CAN_SIZE
            self.emit("fill", x, y, name=a.name)
            return {"can": a.can}
        if self.water.column(x, y):                           # running or poured water (waters.py): a poured source is taken back up
            yield from self.wait(a, 0.6)
            z = self.poured_at(x, y)
            if z is not None:
                self.water.take(x, y, z)
            a.can = CAN_SIZE
            self.emit("fill", x, y, name=a.name)
            return {"can": a.can}
        if args.get("pour"):                                  # a full can poured out: a source of water there (waters.py)
            return (yield from self.pour(a, x, y))
        if a.can <= 0:
            raise ActionError("empty", "your watering can is empty: fill it at a well or any water")
        if self.world.block(x, y) not in ("sprout", "crop") or self.world.ground(x, y) not in ("tilled", "wet_tilled"):
            raise ActionError("bad_target", "water a growing crop in tilled soil", why="not_a_crop")
        if self.world.ground(x, y) == "wet_tilled":
            raise ActionError("already", "it's already watered")
        yield from self.wait(a, 0.8)
        timer = self.timers.get((x, y))
        if timer and timer[1] == "ripen":
            timer[0] = self.tick + max(1, (timer[0] - self.tick) // 2)
        self.set_tile(x, y, ground="wet_tilled", by=a, cause="water")
        a.can -= 1
        a.bump("watered")
        return {"can": a.can}

    def pour(self, a, x, y):
        if a.can < CAN_SIZE:
            raise ActionError("empty", "pouring takes a full can: fill it at a well or any water")
        if self.pour_spot(x, y) is None:
            raise ActionError("bad_target", "pour it on open ground (not into water, a wall or a block)", why="not_open_ground")
        yield from self.wait(a, 0.6)
        z = self.pour_spot(x, y)
        if z is None:
            raise ActionError("changed", "something changed there")
        self.water.pour(x, y, z)
        a.can = 0
        self.emit("pour", x, y, name=a.name)
        return {"can": a.can, "cell": [x, y, z]}
