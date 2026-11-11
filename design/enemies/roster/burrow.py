"""Burrow: a mole. You never see it walk: you see the earth move.

Every frame is computed. Tunnelling is one dig stroke in 8 frames: the mound heaves up and forward, its claws break
the surface at the front and throw earth ahead, it sinks, and the ridges of turned earth behind it slide back at
walking speed and flatten. At rest the mound sits still and a nose rises, sniffs twice and goes down again.
Its action: the mound trembles, then swells (the warning), the mole shoots out stretched thin, lands wide, waves
its claws, and dives back in a splash of earth.
It has no shadow (it is the ground), and its sheet leaves ten rows under it for the trail when it heads away from you.
"""
import math

from art import canvas, dot, ell, over, part

PAL = {"o": "6e4a3c", "m": "b98a62", "l": "d2a678", "k": "8d6347", "b": "8a7f8f", "f": "a59aa6", "O": "4e4658", "p": "f2a6a6",
       "e": "2b2a3a", "w": "fff3d6"}
W, H, BASE = 30, 30, 19                             # BASE: the ground line; the rows under it hold the trail in the 'up' view
AHEAD = {"left": (-1, 0), "down": (0, 1), "up": (0, -1)}
HEAVE = [math.sin(2 * math.pi * (i - 1) / 8) for i in range(8)]      # one dig stroke: up on frames 2-4, down on 6-8


def mound(c, cx, base, rx, ry, i=0):
    ell(c, cx, base, rx, ry, "m", clip=(0, base))
    ell(c, cx - 1, base - 1.2, rx - 1.6, ry - 1.4, "l", on="m", clip=(0, base - 1))
    for k in range(4):                                             # crumbs that roll down it as it moves
        dot(c, cx - rx + 2.5 + k * (2 * rx - 4) / 3, base - 1 - (k * 2 + i) % max(1, int(ry) - 1), "k", on="ml")


def frame(facing, i=0, moving=False, h=0, wide=5.0, shake=0, swell=0.0, crumbs=0, sniff=0, splash=0):
    """i: frame of the dig stroke. h: how far the mole is out of the ground; wide: its half-width (thin when it shoots up).
    swell: the mound bulges. crumbs: earth thrown up (1-3). splash: earth thrown sideways as it dives (1-2)."""
    cx = 10 if facing == "left" else 15
    ax, ay = AHEAD[facing]
    heave = HEAVE[i] if moving else 0
    g = [["."] * W for _ in range(H)]
    if moving:                                                     # turned earth behind it: ridges that slide back, 18 px a cycle
        for k in range(4):                                         # (the distance it travels), and flatten as they age
            d = 7 + (k * 6 + i * 2.25) % 18 if facing == "left" else (8 if facing == "down" else 5) + (k * 4 + i * 1.5) % 12
            if d > (19 if facing == "left" else 16 if facing == "down" else 9):
                continue
            w = max(2, round(6 - d * .22))
            x0, y = round(cx - ax * d + (0 if ax else (k % 2) * 2 - 1) - w / 2), BASE - 1 - round(ay * d * .9)
            for x in range(x0, x0 + w):
                dot(g, x, y, "l" if (x + k) % 3 else "m", on="."); dot(g, x, y + 1, "k", on=".")
            if d < 11:
                for x in range(x0 + 1, x0 + w - 1):
                    dot(g, x, y - 1, "m", on=".")
    g = ["".join(r) for r in g]
    if h:                                                          # the mole itself, as far out of the ground as h
        b = canvas(W, H)
        top = BASE - 3 - h
        ell(b, cx, top + 7, wide, 7, "b", clip=(0, BASE))
        if facing != "up":
            ell(b, cx - (2 if facing == "left" else 0), top + 5, wide - 2, 3, "f", on="b", clip=(0, BASE))
        if h >= 8:                                                 # the digging claws at its sides, white nails up
            for sx in (-1, 1):
                ell(b, cx + sx * (wide + 1.5), top + 9 - 2 * sniff * (sx if splash == 0 and crumbs == 0 else 1), 2, 2, "p")
                for x in (-1.5, .5):
                    dot(b, cx + sx * (wide + 1.5) + x, top + 7 - 2 * sniff * (sx if splash == 0 and crumbs == 0 else 1), "w", on="p")
        if facing == "left":                                       # a pointed snout
            for x, ch in ((cx - wide - 1, "f"), (cx - wide - 2, "p")):
                dot(b, x, top + 4 + (sniff if h < 8 else 0), ch)
            dot(b, cx - wide - 1, top + 5 + (sniff if h < 8 else 0), "f")
        g = [list(r) for r in over(g, part(b, "O"))]
        if facing == "down":
            g[top + 4 + (sniff if h < 8 else 0)][cx - 1] = g[top + 4 + (sniff if h < 8 else 0)][cx] = "p"
            if h >= 4:
                g[top + 3][cx - 3] = g[top + 3][cx + 2] = "e"
        elif facing == "left" and h >= 4:
            g[top + 3][cx - 3] = "e"
        g = ["".join(r) for r in g]
    m = canvas(W, H)
    rx, ry = (7.5, 3.2) if h else (7 - .8 * heave - swell * .5, 4.4 + 1.2 * heave + swell * 2)
    mx = cx + shake + round(ax * heave * 1.2)                      # it lurches forward as it heaves
    mound(m, mx, BASE, rx, ry, i)
    if moving and heave > .5 and facing != "up":                   # the claws break the surface at the front
        dot(m, mx + ax * (rx - 1) - (0 if ax else 3), BASE - 2 - (0 if ax else 1), "p", on="ml")
        dot(m, mx + ax * (rx - 2) + (0 if ax else 2), BASE - 3 - (0 if ax else 0), "p", on="ml")
    g = [list(r) for r in over(g, part(m))]
    if moving:                                                     # earth thrown ahead, each crumb on its own arc
        for k in range(3):
            t = ((i - 2 + k) % 8) / 4                              # 0..1 in flight, then gone
            if t < 1:
                reach = 3 + k * 2 + t * 4
                dot(g, mx + ax * (rx + reach - 2) + (0 if ax else (k - 1) * 4), BASE - 1 - (ry - 2) * (not ax) * 0
                    - (5 + k) * 4 * t * (1 - t) + ay * reach * .6 - (3 if not ax else 0), "k" if k % 2 else "l", on=".")
    for k in range(crumbs * 3):                                    # earth thrown up
        x = cx + (k * 7 + crumbs * 3) % 17 - 8
        dot(g, x, BASE - 5 - crumbs * 2 - (k * 5) % 5, "k" if k % 2 else "l", on=".")
    for k in range(splash * 4):                                    # earth thrown out to both sides as it goes under
        sx = 1 if k % 2 else -1
        dot(g, cx + sx * (6 + splash * 2 + k // 2 * 2), BASE - 2 - (3 - splash) * 2 + k // 2, "k" if k % 3 else "l", on=".")
    return ["".join(r) for r in g]


def frames(d):
    return dict(idle=[frame(d), frame(d), frame(d, h=2), frame(d, h=4), frame(d, h=5), frame(d, h=5, sniff=1), frame(d, h=5), frame(d, h=5, sniff=1)],
                walk=[frame(d, i, moving=True) for i in range(8)],
                act=[frame(d, shake=-1, crumbs=1), frame(d, shake=1, crumbs=1), frame(d, shake=-1, swell=.5, crumbs=2), frame(d, swell=1, crumbs=2),
                     frame(d, h=13, wide=4, crumbs=3), frame(d, h=10, wide=5.6), frame(d, h=11, sniff=1), frame(d, h=11, sniff=-1),
                     frame(d, h=11, sniff=1), frame(d, h=6, splash=1), frame(d, h=2, splash=2), frame(d, swell=-.3)])


ENEMY = dict(
    key="burrow", name="Burrow", pal=PAL, role="digger", cell=(32, 32), act="burst", move="tunnel",
    ms=dict(idle=220, walk=90, act=[110, 110, 110, 160, 70, 100, 140, 140, 140, 90, 90, 140]),
    where="soft ground: meadows, fields, gardens. Never under stone or paths", when="day",
    behaviour="A line of molehills coming your way is all you see. It tunnels under fences and walls, eats one root crop, and "
              "leaves. Under your feet it bursts out and knocks you back a tile (small damage). It can only be hit while it is "
              "out of the ground; a paved or stone floor keeps it away, so it teaches agents to pave what they care about.",
    stats=dict(hp=12, damage=4, speed="as fast as you walk", drops="hide; its molehills leave a seed or a pebble"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
