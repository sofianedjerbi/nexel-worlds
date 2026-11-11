"""Cairn: a heap of mossy stones that stands up. The big one: slow, heavy, hard to hurt.

Every frame is computed. Each stone is its own part (two feet, a body, a head, two fists that float beside it), so the
walk is the stones moving against each other: the body rocks onto the foot that carries it, the head lags, the fists
swing opposite each other. Its action is the slam: both fists go up and hang there (the warning, the longest in the
game), come down in one frame with a ring of dust, and stay down while it recovers. That is when to hit it.
"""
import math

from art import canvas, dot, ell, ground, over, part

PAL = {"o": "5a5560", "b": "b9b3a8", "d": "938c88", "h": "d9d4c6", "m": "86c06c", "M": "5f9a58", "t": "7ff0e0", "T": "d8fff6",
       "w": "f4eeda", "x": "f4eeda90", "l": "a8dc74"}
W, H, CX, BASE = 32, 30, 16, 28


def stone(cx, cy, rx, ry, moss=0.0, far=False):
    c = canvas(W, H)
    ell(c, cx, cy, rx, ry, "d")
    if not far:
        ell(c, cx - .6, cy - .9, rx - .9, ry - 1, "b", on="d")
        ell(c, cx - rx * .4, cy - ry * .5, max(1, rx * .25), .8, "h", on="b")
    if moss:                                                         # moss over the top, ragged at its edge
        for x in range(W):
            for y in range(H):
                if c[y][x] != "." and y + .5 < cy - ry + 2 * ry * moss + math.sin(x * 1.9) * .8:
                    c[y][x] = "m" if y + .5 < cy - ry + 2 * ry * moss - 1 + math.sin(x * 1.9) * .8 else "M"
    return part(c)


def frame(facing, rock=0, lift=None, bob=0, fists=(0, 0), raise_=0, slam=0, eyes=True):
    """rock: the body leans -1/0/1. lift: 'l' or 'r' foot off the ground. fists: each fist's height offset.
    raise_: fists over the head. slam: 1 fists on the ground with dust, 2 dust spreading."""
    side = facing == "left"
    fx = -1 if side else 0
    by = BASE - 10 + bob + (2 if slam else 0)
    hy = by - 9 + (1 if slam else 0) - (1 if raise_ else 0)
    g = ["." * W] * H
    for name, sx in (("l", -1), ("r", 1)):                           # feet
        up = 1 if lift == name else 0
        g = over(g, stone(CX + sx * (3 if side else 4) + (fx * up * 2 if side else 0), BASE - 1.5 - up, 3, 2))

    def fist(sx, k):
        if raise_:
            x, y = (CX - 3 + sx * 6, hy - 3 - k) if side else (CX + sx * 9, hy - 3)
        elif slam:
            x, y = (CX - 10 + sx * 2.5, BASE - 3 + (sx < 0)) if side else (CX + sx * 9, BASE - 3)
        else:
            x, y = (CX + sx * 6 - 2 + fists[k] * -sx * 1.5, by + 2) if side else (CX + sx * 11, by + 1 - fists[k])
        return stone(x, y, 3.2, 3.2, far=side and sx > 0 and not slam)
    if side and not slam:
        g = over(g, fist(1, 1))                                      # the far fist goes behind the body
    g = over(g, stone(CX + rock, by, 8, 7, moss=.22))
    g = over(g, stone(CX + rock + fx * 3, hy, 5, 4.2, moss=.3))
    g = [list(r) for r in g]
    hx = CX + rock + fx * 3
    dot(g, hx + 1, hy - 6, "l"); dot(g, hx + 2, hy - 7, "l"); dot(g, hx, hy - 7, "l"); dot(g, hx + 1, hy - 5, "M")     # a sprout
    if facing != "up" and eyes:
        for x in ((hx - 3, hx + 1) if not side else (hx - 4, hx - 1)):
            g[hy][x] = "t"; g[hy + 1][x] = "t"; g[hy][x] = "T" if raise_ or slam else "t"
    if facing != "up":                                               # a crack down its chest
        for k, x in enumerate((1, 0, 1, 2)):
            dot(g, CX + rock + x + fx * 3, by + k, "d", on="b")
    g = ["".join(r) for r in g]
    for sx, k in ((-1, 0), (1, 1)):
        if not (side and sx > 0 and not slam):
            g = over(g, fist(sx, k))
    g = [list(r) for r in g]
    if slam:                                                         # the ring of dust
        for sx in (-1, 1):
            x = (CX - 10 if side else CX) + sx * ((4 if side else 12) + slam)
            ell(g, x, BASE - .5 - slam, 2.2, 1.4 + slam * .4, "w" if slam == 1 else "x", on=".")
            for k in range(3):
                dot(g, x + sx * (k - 1) * 2, BASE - 3 - slam * 2 - k % 2, "w" if slam == 1 else "x", on=".")
    return ground(g, CX, 20)


ROCK = [-1, -1, 0, 0, 1, 1, 0, 0]
LIFT = ["r", "r", None, None, "l", "l", None, None]
SWING = [(1, -1), (1, -1), (0, 0), (0, 0), (-1, 1), (-1, 1), (0, 0), (0, 0)]


def frames(d):
    idle = [frame(d, bob=b, fists=(f, f), eyes=e) for b, f, e in ((0, 0, 1), (0, 0, 1), (1, 0, 1), (1, -1, 1), (0, -1, 1), (0, 0, 0), (1, 0, 1), (1, -1, 1))]
    return dict(idle=idle, walk=[frame(d, rock=ROCK[i], lift=LIFT[i], bob=i // 2 % 2, fists=SWING[i]) for i in range(8)],
                act=[frame(d, raise_=1, bob=-1), frame(d, raise_=1), frame(d, slam=1), frame(d, slam=2), frame(d, slam=2, eyes=False),
                     frame(d, bob=1, fists=(-1, -1)), frame(d)])


ENEMY = dict(
    key="cairn", name="Cairn", pal=PAL, role="guardian", cell=(32, 32), act="slam", move="trudge",
    ms=dict(idle=260, walk=110, act=[300, 300, 80, 200, 400, 180, 160]),
    where="mountains, cave mouths, old ruins", when="always there, asleep until disturbed",
    behaviour="Sleeps as a pile of mossy stones beside the ore it guards. Mine next to it and it stands up. It is slow and "
              "easy to outwalk, but tools barely scratch it. It raises both fists for more than half a second, then slams: "
              "everything within one tile is hurt and thrown back. While its fists are down it takes full damage. "
              "Leave its ore alone and it sits back down. One per mountain, never more.",
    stats=dict(hp=120, damage=20, speed="half yours", drops="stone, ore, a moss heart (rare)"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
