"""Hunger (the one need): eating; beds (where you wake up); watering crops."""

from .. import tiles as T
from .constants import CAN_SIZE, EAT_SECONDS, PICNIC, sec
from .entities import ActionError


class Needs:
    """Simulation mixin: hunger (the one need): eating; beds (where you wake up); watering crops."""

    def step_needs(self):
        t = self.tick
        for a in self.agents.values():
            if not a.online:
                continue
            if t % sec(10) == 0 and a.hunger > 0:
                a.hunger -= 1
            if t % sec(5) == 0:
                if a.hunger == 0:
                    self.damage(a, 1, "starvation")
                elif a.hunger > 40 and a.hp < 100:
                    a.hp += 1
            if (a.x, a.y) in self.fires and t % sec(1) == 0:
                self.damage(a, 3, "fire")

    def _tool_eat(self, a, args):
        item = str(args.get("item", ""))
        if item not in T.FOOD:
            raise ActionError("not_food", f"food: {', '.join(T.FOOD)}")
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}")
        if a.hunger >= 100:
            raise ActionError("full", "you're full")
        yield from self.wait(a, EAT_SECONDS)       # a proper bite: moving or doing something else stops it
        if not a.count(item):
            raise ActionError("missing_item", "it's gone")
        a.add(item, -1)
        here = self.resolve(a.x, a.y)
        picnic = self.world.block(*here) == "picnic_blanket"
        a.hunger = min(100, a.hunger + int(T.FOOD[item] * (PICNIC if picnic else 1)))
        if picnic:
            self.emit("picnic", a.x, a.y, name=a.name)
        return {"picnic": picnic} if picnic else {}

    def _tool_sleep(self, a, args):
        """Lie down in a bed nearby: you'll wake up there after dying (and it heals a little)."""
        x, y = self.target(a, args)
        if self.world.block(x, y) != "bed":
            raise ActionError("no_bed", f"{args.get('dir')} is {self.describe(x, y)}, not a bed")
        yield from self.wait(a, 1)
        a.hp = min(100, a.hp + 10)
        a.spawn = [x, y]
        return {"spawn": [x, y]}

    def _tool_water(self, a, args):
        """Water a planted tile with a watering can: it grows twice as fast until the next stage."""
        x, y = self.resolve(*self.target(a, args))
        if self.held(a, args) != "watering_can":
            raise ActionError("need_tool", "watering needs the watering can in hand (with: watering_can)"
                              + ("" if a.count("watering_can") else "; craft one at a workbench"))
        if self.world.block(x, y) == "well" or (self.world.block(x, y) == "none" and self.world.ground(x, y) in T.DEPTH):
            yield from self.wait(a, 0.6)
            a.can = CAN_SIZE
            self.emit("fill", x, y, name=a.name)
            return {"can": a.can}
        if a.can <= 0:
            raise ActionError("empty", "your watering can is empty: fill it at a well or any water")
        if self.world.block(x, y) not in ("sprout", "crop") or self.world.ground(x, y) not in ("tilled", "wet_tilled"):
            raise ActionError("bad_target", "water a growing crop in tilled soil")
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
