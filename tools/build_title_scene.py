"""The first screen's background: a small island made by hand, baked into the page (web/js/title_map.js) so that it
shows at once, before any world is loaded. It is built here in a throwaway world with the game's own tiles and
exported as the page takes land in (six blocks of 32 x 32, and one of open sea for all the rest), with the places its
people go to and where they stand there (web/js/title_cast.js: they choose what to do themselves).

    uv run python tools/build_title_scene.py
"""

import json
import math
import tempfile
from pathlib import Path

from megastructure.server import GameServer
from megastructure.tiles import BLOCKS, GROUNDS

W, H = 96, 64
OUT = Path(__file__).parent.parent / "src" / "megastructure" / "web" / "js" / "title_map.js"


# Where its people stand for what was put there by hand, the way they face, and the tile they look at: [x, y, way, tx, ty]
FIXED = {
    "fire": [[40, 33, "E", 41, 33], [42, 33, "W", 41, 33], [41, 35, "N", 41, 33], [41, 32, "S", 41, 33]],      # (the one below it a tile off: a head hid the flame)
    "well": [[55, 28, "N", 55, 27]], "mail": [[44, 28, "W", 43, 28]], "trough": [[35, 38, "S", 35, 39]], "coop": [[33, 36, "W", 32, 36]],
    "sign": [[50, 44, "W", 49, 44]], "picnic": [[45, 35, "S", 45, 35], [46, 34, "W", 46, 34], [44, 34, "E", 44, 34]],
    # (the pier's end, the bridge, the hill's top by the flag, the pond's shore, the pen's gate, the field's edge)
    "views": [[77, 43, "E", 78, 43], [60, 43, "S", 60, 44], [61, 43, "N", 61, 42], [27, 24, "S", 27, 25], [58, 39, "E", 59, 39], [66, 40, "N", 66, 39], [39, 37, "W", 37, 37], [52, 29, "N", 52, 27]],
}


def build():
    gs = GameServer(Path(tempfile.mkdtemp()) / "title", seed=3)
    world = gs.sim.world
    gs.sim.creatures.clear()

    def put(x, y, **kw):
        world.set(x, y, **kw)

    land = set()
    for y in range(H):
        for x in range(W + 32):
            put(x, y, ground="deep_water", block="none", level=0)
            wob = 0.07 * math.sin(x * 0.45) * math.cos(y * 0.5) + 0.05 * math.sin((x + y) * 0.23)
            if x < W and ((x - 48) / 31) ** 2 + ((y - 32) / 20) ** 2 + wob < 1:
                land.add((x, y))
    for x, y in land:
        put(x, y, ground="grass", level=0)

    def near_land(x, y, r):
        return any((x + dx, y + dy) in land for dx in range(-r, r + 1) for dy in range(-r, r + 1))

    for y in range(H):
        for x in range(W):
            if (x, y) not in land:
                put(x, y, ground="water" if near_land(x, y, 2) else "mid_water" if near_land(x, y, 5) else "deep_water")

    # the pond, and the stream that runs from it to the sea, with a bridge over it
    pond = {(x, y) for y in range(28, 44) for x in range(50, 72) if ((x - 60) / 6.4) ** 2 + ((y - 35) / 3.6) ** 2 < 1}
    stream = {(x, y) for y in range(38, H) for x in (60, 61) if (x, y) in land}
    for x, y in pond | stream:
        put(x, y, ground="mid_water" if (x, y) in pond and ((x - 60) / 4.8) ** 2 + ((y - 35) / 2.6) ** 2 < 1 else "water", block="none")
        land.discard((x, y))
    for x in range(59, 63):
        put(x, 43, ground="bridge")

    # the hill, three steps high, with its flag
    for x, y in list(land):
        d = math.hypot((x - 27) / 1.25, y - 24)
        lv = 3 if d < 2.6 else 2 if d < 4.6 else 1 if d < 6.8 else 0
        if lv:
            put(x, y, level=lv)
    put(27, 23, block="flag")
    put(28, 25, block="tree")

    # the house: walls, a door, a floor, a bed, a table and a chair, a chest (and its roof)
    for y in range(22, 28):
        for x in range(38, 45):
            edge = x in (38, 44) or y in (22, 27)
            put(x, y, ground="floor", block="wood_wall" if edge else "none")
    put(41, 27, block="door")
    for y in range(22, 28):                                    # its roof: a tile over each of its tiles (sim/roofing.py)
        for x in range(38, 45):
            gs.sim.roofed.set(x, y, True)
    put(39, 23, block="bed"); put(42, 24, block="table"); put(43, 24, block="chair"); put(39, 25, block="chest")
    put(43, 28, block="mailbox")

    # the paths: from the door to the fire, east to the field and the well, south and over the bridge to the pier
    def path(x0, y0, x1, y1):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                if (x, y) in land:
                    put(x, y, ground="cobble", block="none")
    path(41, 28, 41, 31); path(41, 31, 54, 31); path(47, 31, 47, 43); path(47, 43, 58, 43); path(63, 43, 72, 43)
    for x in range(73, 78):                                   # the pier (Pip ties his boat up at its end when he comes ashore)
        put(x, 43, ground="bridge")
    put(41, 33, block="campfire"); put(39, 33, block="chair"); put(43, 33, block="chair")
    put(44, 35, block="picnic_blanket")
    for x, y in ((45, 35), (46, 35), (44, 34), (45, 34), (46, 34)):
        put(x, y, block="flat_part")                           # (walked on, as the game lays it)
    put(49, 44, block="sign")

    # the field, at every age, and the well beside it
    for y in range(24, 28):
        for x in range(48, 54):
            put(x, y, ground="wet_tilled" if (x + y) % 3 == 0 else "tilled", block=("sprout", "crop", "ripe_crop", "crop")[(x * 2 + y) % 4])
    put(55, 27, block="well"); put(56, 27, block="part"); put(55, 26, block="part"); put(56, 26, block="part")

    # the pen: a fence with a gate, a coop and a trough
    for x in range(30, 38):
        for y in range(34, 41):
            if x in (30, 37) or y in (34, 40):
                put(x, y, block="fence")
    put(37, 37, block="gate")
    put(31, 36, block="coop"); put(32, 36, block="part"); put(31, 35, block="part"); put(32, 35, block="part")
    put(35, 39, block="trough")

    # trees, bushes, flowers, rocks: the same every time (the dice have a seed)
    import random
    dice, taken = random.Random(11), set()
    def free(x, y):
        return (x, y) in land and world.block(x, y) == "none" and world.ground(x, y) == "grass" and (x, y) not in taken
    def scatter(block, n, box, gap=1):
        for _ in range(n * 30):
            if n <= 0:
                break
            x, y = dice.randint(box[0], box[2]), dice.randint(box[1], box[3])
            if free(x, y) and all(free(x + dx, y + dy) or (x + dx, y + dy) not in land for dx in range(-gap, gap + 1) for dy in range(-gap, gap + 1)):
                put(x, y, block=block); taken.add((x, y)); n -= 1
    reserve = [(x, y) for x in range(60, 72) for y in range(22, 31)]      # the cow's meadow stays open
    taken.update(reserve)
    taken.update((x, y) for x, y, *_ in sum(FIXED.values(), []))           # and where people stand, and the gate's way in
    taken.update([(38, 37), (39, 37), (36, 37)])
    scatter("tree", 26, (20, 13, 76, 20)); scatter("tree", 12, (18, 28, 28, 46)); scatter("tree", 14, (62, 45, 78, 52)); scatter("tree", 8, (36, 44, 56, 51))
    scatter("fruit_tree", 4, (46, 20, 58, 22), 0); scatter("berry_bush", 7, (30, 28, 70, 50), 0); scatter("rock", 6, (20, 18, 36, 32), 0); scatter("ore", 2, (22, 26, 32, 32), 0)
    scatter("mushroom", 5, (18, 26, 30, 44), 0); scatter("thicket", 4, (64, 14, 76, 22), 0)
    taken.difference_update(reserve)
    scatter("flower", 46, (16, 12, 80, 52), 0)

    put(52, 18, block="tree"); put(52, 19, block="none"); put(51, 19, block="none"); put(53, 19, block="none")      # a tree with room under it

    # the sea road round the island, a tile at a time, and the way to it from the pier's end
    def walk(*pts):
        out = [list(pts[0])]
        for x1, y1 in pts[1:]:
            while out[-1][0] != x1:
                out.append([out[-1][0] + (1 if x1 > out[-1][0] else -1), out[-1][1]])
            while out[-1][1] != y1:
                out.append([out[-1][0], out[-1][1] + (1 if y1 > out[-1][1] else -1)])
        return out
    ring = []
    for k in range(240):
        t = k / 240 * 2 * math.pi
        x, y = round(48 + 39 * math.cos(t)), round(32 + 27 * math.sin(t))
        if not ring or [x, y] != ring[-1]:
            ring += walk(ring[-1], (x, y))[1:] if ring else [[x, y]]
    ring += walk(ring[-1], ring[0])[1:-1]
    join = min(range(len(ring)), key=lambda i: abs(ring[i][0] - 84) + abs(ring[i][1] - 43))
    ring = ring[join:] + ring[:join]                           # (it starts where the pier's way meets it)
    moor = walk((78, 43), ring[0])[:-1]
    wet = ("water", "mid_water", "deep_water")
    assert all(world.ground(x, y) in wet and world.block(x, y) == "none" for x, y in ring + moor)

    # where its people can stand: bare ground a body can walk, reached from the door a step at a time (a level up or down at most)
    grounds, things = {g.name: g for g in GROUNDS}, {b.name: b for b in BLOCKS}
    def bare(x, y):
        return grounds[world.ground(x, y)].walkable and not things[world.block(x, y)].solid
    reach, edge = {(41, 28)}, [(41, 28)]
    while edge:
        x, y = edge.pop()
        for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):
            q = (x + dx, y + dy)
            if q not in reach and bare(*q) and abs(world.level(*q) - world.level(x, y)) <= 1:
                reach.add(q); edge.append(q)
    used = set()
    def stand(tx, ty, tall):
        """Where to stand to work at (tx, ty), and the way to face: under a tree for choice; beside a small thing (a
        head hides the tile over it: a rock, a bush or a flower worked at from below is not seen)."""
        under, sides = ((0, 1, "N"),), ((1, 0, "W"), (-1, 0, "E"))
        for dx, dy, d in (under + sides if tall else sides + under) + ((0, -1, "S"),):
            q = (tx + dx, ty + dy)
            if q in reach and q not in used and world.block(*q) == "none" and world.ground(*q) in ("grass", "cobble"):
                used.add(q)
                return [q[0], q[1], d, tx, ty]
    def spots(kind, most, near=(47, 31)):
        found = sorted(((x, y) for y in range(H) for x in range(W) if world.block(x, y) == kind), key=lambda q: abs(q[0] - near[0]) + abs(q[1] - near[1]) * 1.5)
        return [s for s in (stand(*q, "tree" in kind) for q in found) if s][:most]
    used.update((x, y) for x, y, *_ in sum(FIXED.values(), []))
    places = {**FIXED, "trees": spots("tree", 12), "rocks": spots("rock", 5) + spots("ore", 2), "bushes": spots("berry_bush", 7),
              "fruit": spots("fruit_tree", 4), "flowers": spots("flower", 18)}
    for kind, found in places.items():
        assert found and all((x, y) in reach for x, y, *_ in found), (kind, found)
    cast = {
        "centre": [47, 31], "view": [26, 18, 70, 46], "door": [41, 28], "field": [48, 24, 53, 27], "pen": [31, 35, 36, 39], "meadow": [61, 23, 70, 29],
        "pond": sorted([x, y] for x, y in pond if world.ground(x, y) == "mid_water"), "ring": ring, "moor": moor, "pier": [77, 43],
        "places": places,
    }

    blocks = []
    for by in range(H // 32):
        for bx in range(W // 32):
            r = gs.region(bx * 32, by * 32, 32, 32)
            blocks.append({k: r[k] for k in ("x", "y", "w", "h", "rows", "ground", "levels", "cols", "roofs") if k in r})
    sea = gs.region(W, 0, 32, 32)
    sea = {k: sea[k] for k in ("rows", "ground", "levels")}
    gs.sim.close()
    return {"w": W, "h": H, "blocks": blocks, "sea": sea, "cast": cast}


if __name__ == "__main__":
    data = build()
    OUT.write_text("// The first screen's island, baked (tools/build_title_scene.py makes this file: do not edit it by hand).\n"
                   "const TITLE_MAP = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print(OUT, OUT.stat().st_size, "bytes;", len(data["blocks"]), "blocks; ring", len(data["cast"]["ring"]), "tiles;", {k: len(v) for k, v in data["cast"]["places"].items()})
