"""Sporecap: a walking mushroom of the forest floor. Small, round-capped, harmless until crowded.

Every frame is computed, and the cap never changes shape (a pulsing dome is the wisp's move, not this one's).
It walks on two short legs: the cap leans over the foot that carries it and the body rises a pixel as the other
swings, like the player. At rest it is a mushroom: dead still, with eyes that glance about and blink.
Crowded, it ducks under its cap and shivers (the warning, held), then jumps up and throws a ring of spores.
"""
import math

from art import canvas, dot, ell, ground, over, part

PAL = {"o": "9a6a52", "O": "a8434f", "r": "ec7a66", "u": "cf5560", "h": "f8a58a", "w": "fff3d6", "c": "fbe9c6", "k": "e8caa0",
       "e": "3a2a30", "p": "f4a79c", "y": "f3f2a0", "z": "f3f2a078"}
W, H, CX, BASE = 28, 24, 14, 22
SPOTS = {"down": ((-6, -1), (-1, -4), (3, -2)), "left": ((-4, -2), (1, -4), (5, -1)), "up": ((4, -1), (-1, -4), (-5, -2))}


STEP = [-2, -1, 0, 1, 2, 1, 0, -1]                  # a foot's reach through one step, seen from the side
UP = [0, 0, 0, 0, 0, 1, 1, 1]                       # it is off the ground while it swings forward


def frame(facing, tip=0, lift=None, step=None, up=0, look=0, blink=False, hide=0, shake=0, ring=0):
    """tip: the cap leans a pixel left (-1) or right (1). lift: 'l'/'r' foot raised (front and back views).
    step: frame of the side walk. up: legs stretched by this much. hide: ducked under the cap by this much."""
    side = facing == "left"
    st = canvas(W, H)
    low = BASE - 2 - up
    for y in range(BASE - 9 - up + hide, low + 1):                    # the stem, a shade on its right side
        for x in range(CX - 3, CX + 3):
            st[y][x + shake] = "k" if x == CX + 2 else "c"
    feet = []
    if not hide:
        if side and step is not None:
            feet = [(CX - 1 + STEP[(step + 4) % 8], UP[(step + 4) % 8]), (CX - 1 + STEP[step], UP[step])]      # far foot, near foot
        else:
            feet = [(CX - 3, lift == "l"), (CX + 1, lift == "r")]
    for x, raised in feet:
        for y in range(low + 1, BASE + (0 if raised else 1)):
            st[y][x] = st[y][x + 1] = "k"
    cp, cy = canvas(W, H), BASE - 8 - up + hide * 2
    for y in range(H):                                                # the cap: a dome, flat underneath, always the same shape;
        for x in range(W):                                            # it slides a pixel over the foot that carries it
            lx, ly = x + .5 - CX - shake - tip, y + .5 - cy
            if (lx / 8) ** 2 + (ly / 6) ** 2 > 1 or ly > 2:
                continue
            spot = any(sx <= lx - .5 < sx + 2 and sy <= ly - .5 < sy + 2 for sx, sy in SPOTS[facing])
            shine = ((lx + 3) / 2.2) ** 2 + ((ly + 4.3) / .8) ** 2 <= 1
            cp[y][x] = "u" if ly > 1 else "w" if spot else "h" if shine else "r"
    g = [list(r) for r in over(part(st), part(cp, "O"))]
    ey = cy + 4
    if facing != "up" and hide < 2:
        for x in ((CX - 2, CX + 1) if not side else (CX - 3, CX - 1)):
            g[ey][x + look] = "k" if blink else "e"
        if not hide:
            for x in ((CX - 3, CX + 2) if not side else (CX - 2,)):
                g[ey + 1][x] = "p"
    for k in range(14 if ring else 0):                                 # the spores, in a widening ring
        a = k * math.pi / 7 + ring * .5
        x, y = CX + (7 + 2.5 * ring) * math.cos(a), cy - 2 + (5 + 2 * ring) * math.sin(a)
        if y < H - 2:
            dot(g, x, y, "z" if ring == 3 else "y", on=".")
    return ground(g, CX, 12)


def frames(d):
    if d == "left":                                                    # it nods forward as each foot lands
        walk = [frame(d, step=i, tip=(-1, -1, 0, 0)[i % 4], up=(0, 0, 1, 1)[i % 4]) for i in range(8)]
    else:
        walk = [frame(d, tip=t, lift=f, up=u) for t, f, u in ((-1, "r", 1), (-1, "r", 1), (0, None, 0), (0, None, 0),
                                                              (1, "l", 1), (1, "l", 1), (0, None, 0), (0, None, 0))]
    idle = [frame(d), frame(d), frame(d, look=-1), frame(d, look=-1), frame(d), frame(d, blink=True), frame(d, look=1), frame(d)]
    return dict(idle=idle, walk=walk,
                act=[frame(d, hide=2, shake=-1), frame(d, hide=2, shake=1), frame(d, hide=2, shake=-1), frame(d, up=2, ring=1),
                     frame(d, up=1, ring=2), frame(d, ring=3), frame(d, hide=1), frame(d)])


ENEMY = dict(
    key="sporecap", name="Sporecap", pal=PAL, role="nuisance", cell=(32, 32), act="puff", move="waddle",
    ms=dict(idle=280, walk=90, act=[160, 160, 160, 90, 140, 160, 120, 160]),
    where="forest shade, near old stumps", when="day and night",
    behaviour="Stands still among the trees and looks like any mushroom, then gets up and waddles off. Harmless at a distance. "
              "Stand next to it and it ducks under its cap, shivers, then jumps and throws a ring of spores: no damage, but you walk slowly for a few seconds. "
              "Agents learn to harvest it from two tiles away, or to wait until it has puffed.",
    stats=dict(hp=8, damage=0, speed="slower than you", drops="mushroom, spores (plant them to grow more)"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
