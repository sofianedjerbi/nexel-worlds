"""The world on its own: fire, growth timers, water and regrowth."""

from .. import tiles as T
from ..gen import gen_tile
from ..tiles import BLOCKS, DIRS, GROUNDS
from .constants import TICK_HZ, sec
from .entities import CREATURES, ActionError, Creature


class Environment:
    """Simulation mixin: the world on its own: fire, growth timers, flooding and regrowth."""

    # -------------------------------------------------------- environment

    def ignite(self, x, y, by=None) -> bool:
        x, y = self.resolve(x, y)
        g, b = self.world.get(x, y)
        ground, block = GROUNDS[g], BLOCKS[b]
        if (x, y) in self.fires or not ground.walkable:
            return False
        if block.flammable or (block.name == "none" and ground.flammable):
            # the tile keeps its block while it burns (flames are an overlay); it turns to ash when the fire dies
            self.fires[(x, y)] = sec(5) + self.rng.randrange(sec(10))
            self.emit("ignite", x, y, by=by.name if by else None)
            if by is not None and by.action is not None:
                by.action.tiles.append({"x": x, "y": y, "burning": True})
            return True
        return False

    def _tool_ignite(self, a, args):
        x, y = self.target(a, args)
        has_torch = self.held(a, args) == "torch"
        if not has_torch and not self.near_block(a, "campfire"):
            raise ActionError("need_fire", "ignite needs a torch in hand (with: torch) or a campfire within 2 tiles")
        yield from self.wait(a, 0.4)
        if not self.ignite(x, y, by=a):
            raise ActionError("wont_burn", f"{self.describe(x, y)} won't burn")
        if has_torch:
            a.add("torch", -1)
        a.bump("fires")
        return {}

    def step_environment(self):
        if self.fires:
            for pos in sorted(self.fires):
                x, y = pos
                self.fires[pos] -= 1
                for dx, dy in DIRS.values():
                    # fire jumps readily between trees and wooden things, but only creeps across bare grass
                    nb = self.world.block(x + dx, y + dy)
                    if self.rng.random() < (0.1 if nb != "none" else 0.03) / TICK_HZ:
                        self.ignite(x + dx, y + dy)
                if self.fires[pos] <= 0:
                    del self.fires[pos]
                    w, h = T.FOOTPRINT.get(self.world.block(x, y), (1, 1))
                    self.clear_structure(x, y, ground="ash", cause="burnt")
                    for j in range(h):
                        for i in range(w):
                            if self.world.ground(x + i, y - j) == "ash":
                                self.timers[(x + i, y - j)] = [self.tick + sec(240), "regrass"]   # the scar heals
        self.step_water()                                  # (waters.py: four steps a second)
        if self.timers and self.tick % sec(2) == 0:
            for pos in sorted(self.timers):
                due, kind = self.timers[pos]
                if self.tick < due:
                    continue
                del self.timers[pos]
                if kind == "ripen" and self.world.block(*pos) in ("sprout", "crop"):
                    nxt = "crop" if self.world.block(*pos) == "sprout" else "ripe_crop"
                    dry = "tilled" if self.world.ground(*pos) == "wet_tilled" else None  # water is used up
                    self.set_tile(*pos, ground=dry, block=nxt, cause="grew")
                    if nxt == "crop":
                        self.timers[pos] = [self.tick + sec(150), "ripen"]
                elif kind == "hatch" and self.items.get(pos, {}).get("egg") and (self.crowded(*pos) or not self.room_for("chick", *pos)):
                    self._take_items(pos, "egg")            # crowded, or enough animals round whoever is near (or nobody is): it rots away
                    self.emit("fade", *pos, item="egg")
                elif kind == "hatch" and self.items.get(pos, {}).get("egg"):
                    self._take_items(pos, "egg")
                    chick = Creature(self.next_creature, "chick", *pos, CREATURES["chick"]["hp"], born=self.tick)
                    self.next_creature += 1
                    self.creatures[chick.id] = chick
                    self.emit("hatch", *pos, id=chick.id)
                elif kind == "regrass" and self.world.ground(*pos) == "ash":
                    self.set_tile(*pos, ground="grass", cause="grew")
                elif kind == "fruit" and self.world.block(*pos) in T.REGROWN:
                    self.set_tile(*pos, block=T.REGROWN[self.world.block(*pos)], cause="grew")
                elif kind == "fruit" and self.world.block(*pos) == "tree":    # picked before bare trees existed
                    self.set_tile(*pos, block="fruit_tree", cause="grew")
                elif kind == "regrow" and self.world.block(*pos) in ("none", "stump") and self.entity_at(*pos) is None \
                        and self.world.ground(*pos) in ("grass", "dirt") and not self.world.roof(*pos):   # (the sky over
                    # it: a tree felled clearing a site never grows back inside the house built on it, under its floor)
                    self.set_tile(*pos, block="tree", cause="grew")
        if self.tick % sec(20) == 0:
            for key in sorted(self.world.chunks):
                cx, cy = key
                x = cx * 32 + self.rng.randrange(32)
                y = cy * 32 + self.rng.randrange(32)
                # nature grows back what was there at the start (bushes, flowers, mushrooms), never more
                if self.rng.random() < 0.1 and self.world.block(x, y) == "none" and self.entity_at(x, y) is None and (x, y) not in self.floors.at \
                        and self.world.ground(x, y) in ("grass", "dirt") and (x, y) not in self.items:
                    orig = BLOCKS[gen_tile(self.world.seed, x, y, self.world.level(x, y))[1]].name
                    if orig in ("berry_bush", "flower", "mushroom"):
                        self.set_tile(x, y, block=orig, cause="grew")
