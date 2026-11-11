"""Hush: an owl. The only one that flies: it hangs above its own shadow and beats its wings.

Every frame is computed. One wing beat is 8 frames: the wings sweep from high to low and back, and the body rises as
they push down. Its action is the swoop: wings held high and still (the warning), a drop to the ground talons first in
one frame, a moment pinned there, then it climbs back.
"""
import math

from art import canvas, dot, ell, ground, over, part

PAL = {"o": "5e4350", "b": "c79a72", "d": "9d7458", "w": "a98063", "f": "f6e7c8", "y": "ffd866", "e": "2b2a3a", "k": "f0a04a",
       "t": "e9d2ac"}
W, H, CX = 30, 30, 15
BEAT = [math.sin(2 * math.pi * i / 8) for i in range(8)]        # +1 wings up, -1 wings down


def wing(c, x0, y0, sx, ang, length=8, wide=4):
    """A wing from the shoulder: a band that tapers to the tip, feathers hanging under it."""
    for t in range(length * 2 + 1):
        u = t / (length * 2)
        x, y = x0 + sx * u * length * math.cos(ang), y0 - u * length * math.sin(ang)
        for k in range(round(wide * (1 - u * .7)) + 1):
            dot(c, x, y + k, "d" if u > .75 or k == round(wide * (1 - u * .7)) else "w")


def frame(facing, beat=0.0, drop=0, tuck=False):
    side = facing == "left"
    cy = 14 - round(1.5 * -beat) + drop                              # the body lifts as the wings push down
    ang = math.radians(15 + 50 * beat)
    c = canvas(W, H)
    if side:
        for x, y in ((4, 5), (5, 6), (5, 5), (6, 6)):                # tail feathers
            dot(c, CX + x, cy + y - 2, "d")
        ell(c, CX, cy, 4.6, 6, "b")
        ell(c, CX - 1.5, cy - 2, 3, 3, "f", on="b")                  # the pale face, turned left
        ell(c, CX - 1.5, cy + 3, 2.4, 2.4, "t", on="b")
        dot(c, CX - 3, cy - 6, "b"); dot(c, CX + 1, cy - 6, "b")
    else:
        for sx in (-1, 1):
            wing(c, CX + sx * 4, cy - 1, sx, ang)
        ell(c, CX, cy, 5, 6, "b")
        for sx in (-1, 1):
            dot(c, CX + sx * 3.5 - .5, cy - 6, "b")                  # ear tufts
            if facing == "down":
                ell(c, CX + sx * 2.3, cy - 2, 2.5, 2.5, "f", on="b")
        if facing == "down":
            ell(c, CX, cy + 3, 3, 2.6, "t", on="b")
        else:
            for x, y in ((-2, -3), (1, -2), (-1, 0), (2, 1), (-2, 2), (0, 3)):
                dot(c, CX + x, cy + y, "d", on="b")
    for sx in (-1, 1) if not side else (-.4,):                       # talons
        dot(c, CX + sx * 2 - .5, cy + 6, "k"); dot(c, CX + sx * 2 - .5, cy + 7 if drop or tuck else cy + 6, "k")
    g = part(c)
    if side:                                                         # the near wing, over the body
        n = canvas(W, H)
        wing(n, CX + 1, cy - 1, 1, math.radians(5 + 60 * beat), length=7, wide=4)     # it sweeps behind it, clear of the face
        g = over(g, part(n))
    g = [list(r) for r in g]
    if side:
        g[cy - 2][CX - 3] = "y"; g[cy - 2][CX - 2] = "e"; g[cy - 1][CX - 5] = "k"; g[cy][CX - 5] = "k"
    elif facing == "down":
        for sx in (-3, 2):
            g[cy - 2][CX + sx] = "y"; g[cy - 2][CX + sx + (1 if sx < 0 else -1)] = "e"
        g[cy - 1][CX - 1] = g[cy - 1][CX] = g[cy][CX] = "k"
    return ground(g, CX, 10 if drop else 7)


def frames(d):
    fly = [frame(d, BEAT[i]) for i in range(8)]
    return dict(idle=fly, walk=fly,
                act=[frame(d, 1.15, drop=-2), frame(d, 1.15, drop=-2), frame(d, 1.2, drop=7, tuck=True), frame(d, -.5, drop=7),
                     frame(d, .6, drop=3), frame(d, -.6, drop=0)])


ENEMY = dict(
    key="hush", name="Hush", pal=PAL, role="raider", cell=(32, 32), act="swoop", move="fly",
    ms=dict(idle=95, walk=85, act=[230, 230, 70, 260, 130, 130]),
    where="perches in tall trees at the forest edge", when="night",
    behaviour="By day it sleeps in a tree and is only a pair of eyes. At night it glides over fences and water, silent, and "
              "goes for small animals left outside: a chicken or chick in the open is carried off. It holds still in the air "
              "before it drops, so a player or agent standing by the coop can hit it then. It never attacks people; a roof or a "
              "lit torch near the coop keeps it away.",
    stats=dict(hp=10, damage="takes a chicken", speed="faster than you", drops="feathers (arrows, pillows)"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
