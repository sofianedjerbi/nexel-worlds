"""Sporecap: a walking mushroom of the forest floor. Small, round-capped, harmless until crowded.

Every frame is computed. It waddles: the cap sways over the foot that carries it and settles a pixel when both feet
are down. At rest the cap breathes. Crowded, it squats (the warning, held), then pops tall and throws a ring of spores.
"""
import math

from art import canvas, dot, ell, ground, over, part

PAL = {"o": "9a6a52", "O": "a8434f", "r": "ec7a66", "u": "cf5560", "h": "f8a58a", "w": "fff3d6", "c": "fbe9c6", "k": "e8caa0",
       "e": "3a2a30", "p": "f4a79c", "y": "f3f2a0", "z": "f3f2a078"}
W, H, CX, BASE = 28, 24, 14, 22
SPOTS = {"down": ((-6, -1), (-1, -4), (3, -2)), "left": ((-4, -2), (1, -4), (5, -1)), "up": ((4, -1), (-1, -4), (-5, -2))}


def frame(facing, sq=0, lean=0, lift=None, blink=False, ring=0):
    fx = -1 if facing == "left" else 0
    st = canvas(W, H)
    for y in range(BASE - 8, BASE):                                    # the stem, a shade on its right side
        for x in range(CX - 3, CX + 3):
            st[y][x] = "k" if x == CX + 2 else "c"
    for foot, xs in (("l", (CX - 3, CX - 2)), ("r", (CX + 1, CX + 2))):  # two small feet; a lifted one tucks into the stem
        if lift != foot:
            for x in xs:
                st[BASE][x] = "k"
    cp, cy = canvas(W, H), BASE - 7 + sq
    ell(cp, CX + lean, cy, 8 + sq, 6 - sq, "r", clip=(0, cy + 2))      # the cap: a dome, flat underneath
    for x in range(W):
        if cp[cy + 1][x] == "r":
            cp[cy + 1][x] = "u"
    ell(cp, CX + lean - 3, cy - 4.3 + sq, 2.2, .8, "h", on="r")
    for dx, dy in SPOTS[facing]:
        for i, j in ((0, 0), (1, 0), (0, 1), (1, 1)):
            dot(cp, CX + lean + dx + i, cy + dy + j + (sq if dy < -2 else 0), "w", on="rh")
    g = [list(r) for r in over(part(st), part(cp, "O"))]
    if facing != "up":
        for x in ((CX - 2, CX + 1) if not fx else (CX - 3, CX - 1)):
            g[cy + 4][x] = "k" if blink else "e"
        for x in ((CX - 3, CX + 2) if not fx else (CX - 2,)):
            g[cy + 5][x] = "p"
    for k in range(14 if ring else 0):                                 # the spores, in a widening ring
        a = k * math.pi / 7 + ring * .5
        x, y = CX + (7 + 2.5 * ring) * math.cos(a), cy - 2 + (5 + 2 * ring) * math.sin(a)
        if y < H - 2:
            dot(g, x, y, "z" if ring == 3 else "y", on=".")
    return ground(g, CX, 12)


LEAN = [-1, -1, 0, 0, 1, 1, 0, 0]
LIFT = ["r", "r", None, None, "l", "l", None, None]


def frames(d):
    return dict(idle=[frame(d, sq=s, blink=b) for s, b in ((0, 0), (0, 0), (1, 0), (1, 0), (0, 0), (0, 1), (1, 0), (1, 0))],
                walk=[frame(d, sq=i // 2 % 2, lean=LEAN[i], lift=LIFT[i]) for i in range(8)],
                act=[frame(d, sq=2, blink=True), frame(d, sq=-1, ring=1), frame(d, sq=-1, ring=2), frame(d, ring=3), frame(d)])


ENEMY = dict(
    key="sporecap", name="Sporecap", pal=PAL, role="nuisance", cell=(32, 32), act="puff", move="waddle",
    ms=dict(idle=240, walk=90, act=[450, 90, 140, 180, 200]),
    where="forest shade, near old stumps", when="day and night",
    behaviour="Stands still among the trees and looks like any mushroom, then gets up and waddles off. Harmless at a distance. "
              "Stand next to it and it squats, then pops a ring of spores: no damage, but you walk slowly for a few seconds. "
              "Agents learn to harvest it from two tiles away, or to wait until it has puffed.",
    stats=dict(hp=8, damage=0, speed="slower than you", drops="mushroom, spores (plant them to grow more)"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
