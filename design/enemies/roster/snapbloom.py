"""Snapbloom: a big pink flower that walks on its roots. Standing still it is a flower like any other, a little too big,
with its eyes shut.

Every frame is computed: a stem that bends from the roots to the head, two broad leaves on it like arms, a head of eight
petals round a gold heart, and a tuft of roots underneath that shuffle in turn as it walks. The face is on the heart:
two sleepy arcs while it pretends.
  bite   the warning: its eyes snap open under a frown, the petals fold back and the heart splits into a mouth of
         little teeth (held); then the head lunges a tile and snaps shut, and it shakes itself and is a flower again.
"""
import math

from art import canvas, dot, ell, ground, over, part, rows

PAL = {"o": "7d3d56", "p": "f7a8bf", "P": "e07a9a", "h": "ffdbe6", "y": "ffd45c", "Y": "e09a32", "k": "5a2838",
       "w": "fff6ea", "x": "ff8fa8", "g": "7cc35a", "G": "5a9a44", "n": "3f6e30", "r": "b07a4f", "R": "8a5a3a"}
W, H, BASE = 34, 38, 36


def roots(c, cx, phase):
    for k, s in enumerate((-1, 1)):
        for j in range(3):
            up = phase is not None and (j + k + phase) % 2 == 0
            x0, length = cx + s * (j * .6), 2 + j - up
            for t in range(length + 1):
                dot(c, x0 + s * t, BASE - 1 - up - (t == length and up) - (1 if t == 0 else 0), "r" if j < 2 else "R")


def leaf(c, x, y, s, flap):
    """A broad leaf on a short stalk, a vein down its middle; flap tips it up or down."""
    x = math.floor(x + .5)                             # a whole pixel to start from, or columns skip and the leaf breaks up
    for k in range(7):
        t = k / 6
        lx, ly = x + s * (1 + k), y - flap * t * 2 - math.sin(t * math.pi) * 1.2
        half = 1.9 * math.sin(math.pi * min(1, t * 1.15)) + .3
        for dy in range(-round(half), round(half) + 1):
            dot(c, lx, ly + dy, "g")
        dot(c, lx, ly, "G")


def face(g, hx, hy, look, mood, bite, side):
    """On the heart. mood: 'asleep' (two arcs), 'awake' (eyes and a frown). bite: 0 shut .. 1 wide."""
    ex = (round(hx) - 2 + look, round(hx) + 1 + look) if not side else (round(hx) - 2,)
    ey = round(hy) - 1 - (1 if bite > .3 else 0)
    for x in ex:
        if mood == "asleep":
            dot(g, x, ey, "Y")
            dot(g, x + 1, ey, "Y")
            dot(g, x - (0 if side else 0), ey - 1, "y")
        else:
            g[ey][x] = g[ey][x + 1] = "k"
            g[ey - 1][x] = "k"
            g[ey - 1][x + 1] = "w"
            dot(g, x + (1 if x < hx or side else 0), ey - 2, "k")      # the frown, slanting in
    if bite:
        mh = round(bite * 3)
        mw = 2 + round(bite * 1.5)
        mx = round(hx) - mw // 2 - (2 if side else 0) + (0 if side else look)
        top = ey + 2
        for y in range(top, top + mh + 1):
            for x in range(mx, mx + mw + 1):
                g[y][x] = "k"
        for x in range(mx, mx + mw + 1, 2):            # little teeth top and bottom
            g[top][x] = "w"
            g[top + mh][x + 1 if x + 1 <= mx + mw else x] = "w"
        dot(g, mx + mw // 2, top + mh - 1, "x")        # a tongue


def head(c, hx, hy, facing, fold=0.0, bite=0.0, sway=0.0):
    if facing == "left":
        for k in range(6):                             # petals fanned back from the face, seen side on
            a = math.pi * (.35 + k * .26) - fold * .5
            ell(c, hx + 2.5 + 3.8 * math.cos(a) * .7 + 2, hy - 3.8 * math.sin(a), 2.5, 2, "P" if k % 2 else "p")
        ell(c, hx, hy, 3.6, 3.8, "Y")
        ell(c, hx - .4, hy - .5, 3, 3.2, "y", on="Y")
    else:
        r = 5.8 - fold * 2
        for k in range(8):
            a = k * math.pi / 4 + .2 + sway * .2
            ell(c, hx + r * math.cos(a), hy + r * .9 * math.sin(a), 2.7 - fold * .5, 2.4 - fold * .4, "p" if k % 2 else "P")
            dot(c, hx + (r + 1.2) * math.cos(a), hy + (r + 1.2) * .9 * math.sin(a) - .5, "h", on="pP")
        ell(c, hx, hy, 3.9 + bite * .6, 3.6 + bite * .6, "Y")
        if facing == "down":
            ell(c, hx - .4, hy - .4, 3.2 + bite * .6, 2.9 + bite * .6, "y", on="Y")
        else:
            ell(c, hx, hy, 3.4, 3.1, "G", on="Y")         # from behind: the green cup
            for k in range(5):
                a = k * 2 * math.pi / 5 - math.pi / 2
                dot(c, hx + 2.7 * math.cos(a), hy + 2.5 * math.sin(a), "n", on="G")


def snap_burst(g, x, y, side):
    """The snap: short white strokes out from where the jaws met."""
    for a in ((-2.4, -1.6, -.8, 0, .8) if side else (-2.4, -1.2, 0, 1.2, 2.4, 3.6)):
        ang = a + (math.pi if side else 0)
        for r in (4, 5):
            dot(g, x + r * math.cos(ang), y + r * math.sin(ang) * .8, "w", on=".")


def frame(facing="down", sway=0.0, phase=None, fold=0.0, bite=0.0, lunge=0, bob=0, flap=0.0, mood="asleep", look=0,
          rear=0.0, shake=0, snap=False):
    side = facing == "left"
    cx = W // 2
    top = BASE - 23 + bob + (lunge if not side else 0)
    hx = cx + sway * 2.5 - (lunge * 1.5 if side else 0) + (rear * 2 if side else 0) + shake
    hy = top - (rear * 1.5 if not side else rear * .5)
    st = canvas(W, H)
    for y in range(round(hy) + 2, BASE - 1):            # the stem: bending from the roots to the head
        t = (BASE - 1 - y) / (BASE - 1 - hy)
        x = cx + (hx - cx) * t ** 1.6
        dot(st, x - .5, y, "g")
        dot(st, x + .5, y, "G")
    ly = BASE - 10 + bob
    lx = cx + (hx - cx) * .3
    for s in ((-1, 1) if not side else (-1, 1)):
        leaf(st, lx + s * .5, ly - (s > 0) * 2, s, flap * s)
    rt = canvas(W, H)
    roots(rt, cx, phase)
    hd = canvas(W, H)
    head(hd, hx, hy, facing, fold, bite, sway)
    out = over(part(rt, "R"), part(st, "n"))
    g = [list(r) for r in over(out, part(hd))]
    if facing != "up":
        face(g, hx, hy, look, mood, bite, side)
    if snap:
        snap_burst(g, hx - (4 if side else 0), hy + (0 if side else 1), side)
    return ground(rows(g), cx, 13)


def frames(d):
    sw = [math.sin(i * math.pi / 4) for i in range(8)]
    idle = [frame(d, sway=.5 * sw[i], flap=.6 * sw[(i + 2) % 8]) for i in range(8)]
    walk = [frame(d, sway=.35 * sw[i], phase=i // 2 % 2, bob=1 if i % 4 in (1, 2) else 0, flap=sw[i]) for i in range(8)]
    bite = [frame(d, mood="awake", bob=-1),                                          # eyes snap open, a start
            frame(d, mood="awake", rear=.7, fold=.5, bite=.4, flap=-.6),                # it rears back, the petals fold
            frame(d, mood="awake", rear=1.4, fold=1, bite=1, bob=1, flap=-1),          # mouth wide: the warning
            frame(d, mood="awake", rear=1.4, fold=1, bite=1, bob=1, flap=-1, shake=1),  # ...trembling, held
            frame(d, mood="awake", rear=1.4, fold=1, bite=1, bob=1, flap=-1, shake=-1),
            frame(d, mood="awake", lunge=4, fold=.2, bite=0, flap=1, snap=True),        # the lunge: snapped shut
            frame(d, mood="awake", lunge=5, fold=0, bob=1, flap=1),                      # overshoot
            frame(d, mood="awake", lunge=1, fold=-.5, flap=.4),                          # recoil, petals spring wide
            frame(d, sway=.5, fold=-.2, flap=-.6), frame(d, sway=-.5, flap=.6), frame(d)]
    return dict(idle=idle, walk=walk, bite=bite)


ENEMY = dict(
    key="snapbloom", name="Snapbloom", pal=PAL, role="rare, day", cell=(36, 40), move="shuffle", side="day",
    ms=dict(idle=220, walk=110, bite=[160, 180, 220, 150, 150, 70, 110, 140, 140, 140, 200]),
    beats=dict(bite="wwwwwssrrrr"), hit=dict(bite="knock"),
    where="among flowers, at the edge of gardens", when="day, in bloom season; rare",
    behaviour="A flower a little too big, among the others, its eyes shut. It does not move while you look at it. Turn your "
              "back and it shuffles a step closer on its roots. Close enough, it <b>bites</b>: its eyes snap open, the petals "
              "fold back and a mouth of little teeth opens where the heart was (that is the warning), then it lunges a tile "
              "and snaps. Cut it while its petals are back. Beaten, it drops a seed that grows into a tame one.",
    stats=dict(hp=6, damage=2, speed="slow, only when unseen", drops="snap seed"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
