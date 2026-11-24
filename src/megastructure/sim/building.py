"""Changing the world: digging, placing (including multi-tile structures) and crafting."""

from .. import tiles as T
from ..tiles import BLOCKS, GROUNDS, PLACEABLE, RECIPES
from .constants import MAX_TEXT, sec
from .entities import ActionError
from .progress import XP_CRAFT, XP_DIG


class Building:
    """Simulation mixin: changing the world: digging, placing (including multi-tile structures) and crafting."""

    def resolve(self, x, y) -> tuple[int, int]:
        """Point a part of a multi-tile structure at the structure's own tile (dig, burn, describe it)."""
        if self.world.block(x, y) in ("part", "flat_part"):
            hit = T.structure_at(self.world.block, x, y)
            if hit:
                return hit[0], hit[1]
        return x, y

    def clear_structure(self, x, y, by=None, cause=None, ground=None):
        """Remove a structure (given its own tile) together with the rest of its footprint."""
        name = self.world.block(x, y)
        w, h = T.FOOTPRINT.get(name, (1, 1))
        tiles = [(x + i, y - j) for j in range(h) for i in range(w)]
        for tx, ty in tiles:
            if (tx, ty) == (x, y) or self.world.block(tx, ty) in ("part", "flat_part"):
                self.set_tile(tx, ty, block="none", ground=ground, by=by, cause=cause)

    def describe(self, x, y) -> str:
        x, y = self.resolve(x, y)
        g, b = self.world.ground(x, y), self.world.block(x, y)
        return g if b == "none" else f"{b} on {g}"

    def _tool_dig(self, a, args):
        if str(args.get("dir", "")).lower() == "up":       # (the cell over your own head: underground.py)
            return (yield from self.dig_over(a, args))
        up = self.dig_up(a, args) or self.dig_land(a, args)   # (a block built over the ground, or what stands on one: storeys.py;
        if up is not None:                                     #  the land's own top at a height: a hole, underground.py)
            return (yield from up)
        x, y = self.resolve(*self.target(a, args, flat=True))   # (flat: a wall is dug at your own height, whatever is on top of it)
        g, b = self.world.get(x, y)
        block, ground = BLOCKS[b], GROUNDS[g]
        z = self.height(a) + 1                             # the cell in front of you, at your body's height
        bare = block.name == "none" or self.world.level(x, y) != z      # (what stands on the tile is not on this cell: up on the hill over your tunnel, a tree was chopped for the wall)
        if bare and self.world.solid(x, y, z) and self.held(a, args) == "pickaxe":
            yield from self.wait(a, 1.0)                   # into a wall: that cell goes (a step cut down, or a tunnel)
            if not self.world.solid(x, y, z) or self.height(a) + 1 != z:
                raise ActionError("changed", "something changed there")
            got = self.take_land(a, x, y, z)               # (the block itself, earth or stone: underground.py)
            return {"got": {got: 1}, "cell": [x, y, z]}
        self.reach(a, x, y, z=self.world.level(x, y))      # (anything else is on the tile's ground, its lowest: too high up, or down, is out of reach. It was the
                                                           #  ground there nearest your own height: a flower was picked from a stair 24 layers over it)
        if block.name != "none" and self.land_between(a, x, y, self.world.level(x, y)):
            raise ActionError("out_of_range", f"the {block.name.replace('_', ' ')} at ({x},{y}) is behind the land: nothing is reached through it")
        if block.name == "none" and ground.liquid:           # the bottom of the water: a layer deeper
            return (yield from self.deepen(a, x, y))
        if block.name == "none":
            built ={"cobble": ("path", "dirt"), "floor": ("plank", "dirt"), "bridge": ("plank", "water")}
            if ground.name in built:                       # what you lay, you can take up again
                item, under = built[ground.name]
                if under == "water" and self.entity_at(x, y):
                    raise ActionError("occupied", "someone is standing on it")
                yield from self.wait(a, 0.5)
                a.add(item)
                self.set_tile(x, y, ground=under, by=a, cause="dig")
                return {"got": {item: 1}}
            if not ground.diggable or ground.name in ("tilled", "wet_tilled"):
                raise ActionError("cannot_dig", f"{ground.name} cannot be dug")
            if self.held(a, args) != T.TILL_TOOL:
                raise ActionError("need_tool", f"tilling needs a {T.TILL_TOOL} in hand (with: {T.TILL_TOOL})"
                                  + ("" if a.count(T.TILL_TOOL) else "; craft one at a workbench"))
            yield from self.wait(a, 0.6)
            if self.world.block(x, y) != "none":
                raise ActionError("changed", "something was placed there")
            self.set_tile(x, y, ground="tilled", by=a, cause="dig")
            return {}
        if block.hardness <= 0:
            raise ActionError("cannot_dig", f"{block.name} cannot be dug")
        tool = self.held(a, args)
        if block.needs_tool and tool != block.needs_tool:
            raise ActionError("need_tool", f"digging {block.name} needs a {block.needs_tool} in hand "
                              f"(with: {block.needs_tool})" + ("" if a.count(block.needs_tool) else "; you have none"))
        seconds = block.hardness / 20                       # with the right tool in hand
        if block.tool and tool != block.tool:
            seconds *= T.BY_HAND[block.tool]
        if block.quick:
            seconds = 0                                     # picking and plucking: instant, even on the run
        yield from self.wait(a, seconds)
        if self.world.get(x, y)[1] != b:
            raise ActionError("changed", "the block changed while digging")
        drops = dict(block.drops)
        if block.name == "ripe_crop":
            drops = {T.crop_species(x, y): 3, "seed": 2}
        if block.name in ("chest", "basket", "trough"):
            drops = self._merge(drops, self.world.meta.get((x, y), {}).get("items", {}))
        for k, n in drops.items():
            a.add(k, n)
        self.gain_xp(a, XP_DIG.get(block.name, 0), x, y)
        if block.hardness > 3:                       # (work: not a flower picked in passing)
            self.tire(a, "dig")
        if block.name in T.PICKED:
            # picking takes the fruit or berries; the plant stays, bare, and bears again later
            bare, seconds = T.PICKED[block.name]
            self.set_tile(x, y, block=bare, by=a, cause="pick")
            self.timers[(x, y)] = [self.tick + sec(seconds), "fruit"]
            a.bump("dug")
            return {"got": drops}
        if block.name in ("tree", "bare_fruit_tree"):
            # a felled tree leaves its stump (dig it up for a last bit of wood); a new tree grows there later
            self.set_tile(x, y, block="stump", by=a, cause="dig")
            self.timers[(x, y)] = [self.tick + sec(1200), "regrow"]
        else:
            self.clear_structure(x, y, by=a, cause="dig")
        a.bump("dug")
        return {"got": drops}

    @staticmethod

    def _merge(a: dict, b: dict) -> dict:
        out = dict(a)
        for k, n in b.items():
            out[k] = out.get(k, 0) + n
        return out

    def _tool_place(self, a, args):
        up = self.place_up(a, args)                        # (a block for a cell over the ground, a thing for a built block, earth: storeys.py)
        if up is not None:
            return (yield from up)
        x, y = self.target(a, args)
        item = str(args.get("item", ""))
        if self.world.rim(x, y):
            raise ActionError("cliff_edge", "nothing stays on the edge of a hill: build further in")
        if not a.count(item):
            raise ActionError("missing_item", f"you have no {item}")
        g, b = self.world.ground(x, y), self.world.block(x, y)
        picked = b == "flower"   # flowers are decoration: building over one picks it for you
        if picked:
            b = "none"
        if item in T.FILLERS:
            options = T.FILLERS[item]
            if b != "none":
                raise ActionError("occupied", f"{args.get('dir') or 'that tile'} has {b}")
            if g not in options:
                raise ActionError("bad_target", f"{item} goes on {', '.join(sorted(options))}, not {g}")
            yield from self.wait(a, 0.3)
            if self.world.ground(x, y) != g or self.world.block(x, y) not in ("none", "flower"):
                raise ActionError("changed", "the tile changed")
            if self.world.block(x, y) == "flower":
                a.add("flower")
            a.add(item, -1)
            self.set_tile(x, y, ground=options[g], by=a, cause="place")
            a.bump("placed")
            return {}
        if item not in PLACEABLE:
            raise ActionError("not_placeable", f"{item} cannot be placed. Placeable: "
                              f"{', '.join(sorted(PLACEABLE) + sorted(T.FILLERS))}")
        block = PLACEABLE[item]
        if block in T.FOOTPRINT:
            return (yield from self._place_structure(a, item, block, x, y))
        if b != "none":
            raise ActionError("occupied", f"{args.get('dir') or 'that tile'} has {b}")
        if block == "boat":
            if g not in T.DEPTH:
                raise ActionError("bad_target", "boats go on water next to you")
        elif not GROUNDS[T.G[g]].walkable:
            raise ActionError("bad_target", f"cannot place on {g}")
        if item == "seed" and g not in T.SEED_GROUNDS:
            raise ActionError("bad_target", "seeds only grow in tilled soil (dig the ground first)")
        if BLOCKS[T.B[block]].solid and self.entity_at(x, y):
            raise ActionError("occupied", "someone is standing there")
        yield from self.wait(a, 0.3)
        if self.world.block(x, y) not in ("none", "flower"):
            raise ActionError("changed", "tile was taken")
        if self.world.block(x, y) == "flower":
            a.add("flower")
        if BLOCKS[T.B[block]].solid and self.entity_at(x, y):
            raise ActionError("occupied", "someone stepped there")
        a.add(item, -1)
        self.set_tile(x, y, block=block, by=a, cause="place")
        if block == "sprout":
            self.timers[(x, y)] = [self.tick + sec(150), "ripen"]
        if block == "mailbox":
            self.world.set_meta(x, y, {"owner": a.name, "letters": []})
        if block == "flag" or (block == "sign" and str(args.get("text") or "").strip()):     # ("Signs = write when placing")
            text = str(args.get("text") or f"claimed by {a.name}").strip()[:MAX_TEXT]
            self.world.set_meta(x, y, {"text": text, "by": a.name})
        a.bump("placed")
        return {}

    def _structure_spot(self, a, block, x, y):
        anchor, tiles = T.footprint(block, x, y, a.x, a.y)
        for tx, ty in tiles:
            if (tx, ty) == (a.x, a.y):
                raise ActionError("occupied", f"stand outside the {block.replace('_', ' ')}'s spot (it covers "
                                  f"{T.FOOTPRINT[block][0]}x{T.FOOTPRINT[block][1]} tiles in front of you)")
            if self.world.rim(tx, ty) or self.world.level(tx, ty) != self.world.level(x, y):
                raise ActionError("cliff_edge", f"the {block.replace('_', ' ')} has to stand on one level, clear of the edge")
            g = GROUNDS[self.world.get(tx, ty)[0]]
            if not g.walkable or g.liquid:
                raise ActionError("bad_target", f"{block.replace('_', ' ')} needs dry land ({tx},{ty} is {g.name})")
            if self.world.block(tx, ty) not in ("none", "flower"):
                raise ActionError("occupied", f"({tx},{ty}) has {self.world.block(tx, ty)}")
            if BLOCKS[T.B[block]].solid and self.entity_at(tx, ty):
                raise ActionError("occupied", "something is standing in the way")
        return anchor, tiles

    def _place_structure(self, a, item, block, x, y):
        self._structure_spot(a, block, x, y)
        yield from self.wait(a, 0.5)
        anchor, tiles = self._structure_spot(a, block, x, y)
        part = "part" if BLOCKS[T.B[block]].solid else "flat_part"
        a.add(item, -1)
        for tx, ty in tiles:
            if self.world.block(tx, ty) == "flower":
                a.add("flower")
            self.set_tile(tx, ty, block=block if (tx, ty) == anchor else part, by=a, cause="place")
        a.bump("placed")
        return {"at": list(anchor), "tiles": [list(t) for t in tiles]}

    def _tool_craft(self, a, args):
        name = str(args.get("recipe", args.get("item", "")))
        r = RECIPES.get(name)
        if r is None:
            raise ActionError("unknown_recipe", f"recipes: {', '.join(RECIPES)}")
        n = min(self._n(args), 20)
        if r.station and not self.near_block(a, r.station):
            raise ActionError("need_station", f"{name} must be crafted within 2 tiles of a {r.station}")
        missing = {k: v * n - a.count(k) for k, v in r.inputs.items() if a.count(k) < v * n}
        if missing:
            raise ActionError("missing_items", f"need {missing} more for {n}x {name}")
        yield from self.wait(a, r.ticks / 10 * n)
        if r.station and not self.near_block(a, r.station):
            raise ActionError("need_station", f"the {r.station} is gone")
        if any(a.count(k) < v * n for k, v in r.inputs.items()):
            raise ActionError("missing_items", "inputs changed while crafting")
        for k, v in r.inputs.items():
            a.add(k, -v * n)
        for k, v in r.output.items():
            a.add(k, v * n)
        self.stats["crafts"] += 1
        a.bump("crafted", n)
        self.gain_xp(a, XP_CRAFT * n, a.x, a.y)
        self.emit("craft", a.x, a.y, radius=4, name=a.name, made={k: v * n for k, v in r.output.items()})
        return {"made": {k: v * n for k, v in r.output.items()}}
