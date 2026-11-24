"""The cave showcase: a flat field with every way a cave meets the world built on it (the in-browser demo starts
here). Three hills (mouths on all four sides; entries at an outer corner, another, and in an inner corner; openings
of every size on one face, one ragged, and a shaft from the top), a hollow under flat ground with steps down to it,
and pits."""

from .tiles import BLOCKS

FIELD = (-66, 42, 78, 50)          # x, y, w, h: flattened first
SPAWN = (-25, 62)                  # newcomers start here, south of the hills


def layout() -> dict:
    """(x, y) -> [floor, rock over it, empty cells of that over the floor, block char]"""
    t = {}
    box = lambda x0, x1, y0, y1: [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]

    def hill(x0, y0, w, h, top):
        for p in box(x0, x0 + w - 1, y0, y0 + h - 1):
            t[p] = [top, 0, 0, "."]

    def cave(tiles, head=2, floor=0):
        for p in tiles:
            top = t[p][0] + t[p][1] if p in t else floor
            t[p] = [floor, top - floor, head, "."] if top - floor >= 2 else [floor, 0, 0, "."]

    # 1. a hill with a room and a mouth on each of its four sides
    hill(-60, 48, 16, 12, 5)
    for b in [(-55, -50, 52, 55), (-53, -52, 56, 59), (-53, -52, 48, 51), (-60, -56, 53, 54), (-49, -45, 53, 54)]:
        cave(box(*b))
    t[(-54, 53)][3], t[(-51, 55)][3] = "^", "Q"
    # 2. corner entries: at an outer corner (two faces of one corner), another outer corner, and in an inner corner
    hill(-38, 48, 12, 12, 5)
    for p in box(-38, -35, 56, 59):                           # (a bite out of the hill: it has an inner corner)
        t[p] = [0, 0, 0, "."]
    cave(box(-34, -31, 52, 55))
    cave(box(-28, -27, 58, 59) + [(-29, 58), (-29, 57), (-30, 57), (-30, 56), (-31, 56)])     # south-east, a stair of a passage in
    cave(box(-38, -37, 48, 49) + [(-36, 49), (-36, 50), (-35, 50), (-35, 51), (-34, 51)])     # north-west
    cave([(-34, 56), (-35, 55)])                              # the inner corner: open on both of its faces
    t[(-32, 53)][3] = "^"
    # 3. openings of every size on one face, one of them a ragged shape; a shaft down from the top
    hill(-20, 48, 26, 10, 6)
    cave(box(-18, 4, 53, 54))
    for x0, w, hd in [(-18, 1, 1), (-15, 1, 2), (-12, 2, 2), (-8, 3, 2), (-3, 2, 3), (1, 1, 1), (2, 1, 2), (3, 1, 3), (4, 1, 2)]:
        cave(box(x0, x0 + w - 1, 55, 57), head=hd)
    cave([(-13, 52)])
    t[(-13, 51)] = [0, 0, 0, "."]                             # the shaft: open from the hilltop down to the floor
    t[(-6, 53)][3], t[(0, 54)][3] = "*", "Q"
    # 4. a hollow under flat ground, with steps down to it; and pits
    for p in box(-60, -52, 66, 72):
        t[p] = [-3, 3, 2, "."]
    for x, lv in [(-51, -3), (-50, -2), (-49, -1)]:
        t[(x, 68)] = t[(x, 69)] = [lv, 0, 0, "."]
    for p in box(-44, -42, 66, 68) + [(-39, 67)]:
        t[p] = [-1, 0, 0, "."]
    t[(-43, 67)] = [-2, 0, 0, "."]
    return t


def build(sim):
    """Stamp the showcase into the world and make it where newcomers start."""
    x0, y0, w, h = FIELD
    blocks, t = {b.char: b.name for b in BLOCKS}, layout()
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            lv, rf, hd, ch = t.get((x, y), (0, 0, None, "."))
            sim.set_tile(x, y, ground="grass", block=blocks.get(ch, "none"), level=lv, roof=rf, head=hd if rf else None)
    sim.store.set_meta("spawn", list(SPAWN))
    sim.store.set_meta("showcase", "caves")
