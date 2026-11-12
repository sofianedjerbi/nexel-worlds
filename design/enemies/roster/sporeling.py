"""Sporeling: a small sporecap, the size of the chicken. Old Mossback shakes them off its back.

Computed like the sporecap and moved the same way (a rigid cap, two short legs, a lean over the carrying foot), only
quicker. It has one more animation, the landing: it falls cap first, hits the ground tucked under its cap, and pops up.
"""
import math

from art import canvas, dot, ell, ground, over, part, shift

PAL = {"o": "9a6a52", "O": "a8434f", "r": "ec7a66", "u": "cf5560", "h": "f8a58a", "w": "fff3d6", "c": "fbe9c6", "k": "e8caa0",
       "e": "3a2a30", "y": "f3f2a0", "z": "f3f2a078"}
W, H, CX, BASE = 24, 20, 12, 18                    # CX: the middle pixel of the stem
SPOTS = {"down": ((-4, -1, 2), (0, -4, 1), (3, -1, 1)), "left": ((-2, -3, 2), (2, -2, 1), (4, 0, 1)), "up": ((2, -1, 2), (-1, -4, 1), (-4, -1, 1))}


def frame(facing, lean=0, lift=None, up=0, hide=0, shake=0, blink=False, ring=0, air=0):
    side = facing == "left"
    st = canvas(W, H)
    for y in range(BASE - 5 - up + hide, BASE - up):
        for x in range(CX - 2, CX + 3):
            st[y][x + shake] = "k" if x == CX + 2 else "c"
    if not hide:
        for foot, xs in (("l", (CX - 2, CX - 1)), ("r", (CX + 1, CX + 2))):
            for y in range(BASE - up, BASE + (0 if lift == foot else 1)):
                for x in xs:
                    st[y][x] = "k"
    cp, cy = canvas(W, H), BASE - 5 - up + (hide * 3 + 1) // 2
    ell(cp, CX + .5 + lean + shake, cy, 6, 4.6, "r", clip=(0, cy + 2))
    for x in range(W):
        if cp[cy + 1][x] == "r":
            cp[cy + 1][x] = "u"
    ell(cp, CX - 1.5 + lean + shake, cy - 3.3, 1.6, .6, "h", on="r")
    for dx, dy, n in SPOTS[facing]:
        for i in range(n):
            for j in range(n):
                dot(cp, CX + lean + shake + dx + i, cy + dy + j, "w", on="rh")
    g = [list(r) for r in over(part(st), part(cp, "O"))]
    if facing != "up" and hide < 2:
        for x in ((CX - 1, CX + 1) if not side else (CX - 2, CX)):
            g[cy + 3][x] = "k" if blink else "e"
    for k in range(10 if ring else 0):
        a = k * math.pi / 5 + ring * .5
        dot(g, CX + (5 + 2 * ring) * math.cos(a), min(BASE - 1, cy - 1 + (4 + 1.5 * ring) * math.sin(a)), "z" if ring == 3 else "y", on=".")
    g = ground(g, CX + .5, 8 - min(4, air // 2))
    return shift(g, 0, -air, keep=1) if air else g


def frames(d):
    walk = [frame(d, lean=t, lift=f, up=u) for t, f, u in ((-1, "r", 1), (-1, "r", 1), (0, None, 0), (0, None, 0),
                                                           (1, "l", 1), (1, "l", 1), (0, None, 0), (0, None, 0))]
    return dict(idle=[frame(d), frame(d), frame(d), frame(d, blink=True), frame(d), frame(d, up=1), frame(d), frame(d)],
                walk=walk,
                land=[frame(d, hide=2, air=9), frame(d, hide=2, air=4), frame(d, hide=2), frame(d, hide=2, shake=1), frame(d, up=2), frame(d)],
                puff=[frame(d, hide=2, shake=-1), frame(d, hide=2, shake=1), frame(d, up=2, ring=1), frame(d, up=1, ring=2), frame(d, ring=3), frame(d)])


ENEMY = dict(
    key="sporeling", name="Sporeling", pal=PAL, role="boss's brood", cell=(24, 24), move="waddle",
    ms=dict(idle=240, walk=75, land=[80, 80, 160, 120, 90, 140], puff=[150, 150, 90, 130, 150, 140]),
    where="only around Old Mossback: three fall off its back each time it shakes", when="during the fight",
    behaviour="It lands tucked under its cap, pops up, and waddles straight at the nearest player, quicker than a sporecap. "
              "Next to you it ducks, shivers and puffs: no damage, but you walk slowly for two seconds, which is what makes "
              "the next stomp or snap land. One hit kills it. Any still alive after twenty seconds root where they stand and "
              "become ordinary mushrooms you can pick.",
    stats=dict(hp=1, damage="0 (slows)", speed="nearly yours", drops="a mushroom, sometimes"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
