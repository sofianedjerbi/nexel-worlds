"""Burrow: a mole. You never see it walk: you see the earth move.

Every frame is computed. It travels as a mound that ripples forward and leaves smaller mounds behind it. At rest the
mound sits still and a pink nose comes up to sniff. Its action: the mound trembles and throws crumbs (the warning, held),
then the mole bursts out with its claws up, hangs there, and sinks back.
It has no shadow (it is the ground), and its sheet leaves ten rows under it for the trail when it heads away from you.
"""
from art import canvas, dot, ell, over, part

PAL = {"o": "6e4a3c", "m": "b98a62", "l": "d2a678", "k": "8d6347", "b": "8a7f8f", "f": "a59aa6", "O": "4e4658", "p": "f2a6a6",
       "e": "2b2a3a", "w": "fff3d6"}
W, H, BASE = 30, 30, 19                             # BASE: the ground line; the rows under it hold the trail in the 'up' view
# the trail, oldest last: (dx, dy, size) from the mound, per facing. Sideways the mound leads, off-centre, the trail behind it.
TRAIL = {"left": ((10, 0, 2.5), (15, 0, 2), (19, 0, 1.5)), "down": ((1, -7, 2.5), (-1, -11, 2), (1, -14, 1.5)),
         "up": ((-1, 4, 2.5), (1, 7, 2), (-1, 10, 1.5))}


def mound(c, cx, base, rx, ry, i=0):
    ell(c, cx, base, rx, ry, "m", clip=(0, base))
    ell(c, cx - 1, base - 1.2, rx - 1.6, ry - 1.4, "l", on="m", clip=(0, base - 1))
    for k in range(4 if rx > 4 else 1):                            # crumbs that crawl over it as it moves
        dot(c, cx - rx + 2 + (k * 3 + i) % max(1, int(2 * rx - 3)), base - 1 - (k * 2 + i) % max(1, int(ry) - 1), "k", on="ml")


def frame(facing, i=0, moving=False, h=0, shake=0, crumbs=0, sniff=0):
    cx = 10 if facing == "left" else 15
    g = ["." * W] * H

    def trail():
        """Turned earth behind it: low ridges, no outline, each one flatter than the one before."""
        nonlocal g
        t = [list(r) for r in g]
        for k, (dx, dy, r) in enumerate(TRAIL[facing]):
            w = round(2 * r) - (i + k) % 2
            x0, y = round(cx + dx - w / 2), BASE + dy - 1
            for x in range(x0, x0 + w):
                dot(t, x, y, "l" if (x + i) % 3 else "m", on="."); dot(t, x, y + 1, "k", on=".")
            if k == 0:
                for x in range(x0 + 1, x0 + w - 1):
                    dot(t, x, y - 1, "m", on=".")
        g = ["".join(r) for r in t]
    if moving and facing != "up":
        trail()
    if h:                                                          # the mole itself, as far out of the ground as h
        b = canvas(W, H)
        top = BASE - 3 - h
        ell(b, cx, top + 7, 5, 7, "b", clip=(0, BASE))
        if facing != "up":
            ell(b, cx - (2 if facing == "left" else 0), top + 5, 3, 3, "f", on="b", clip=(0, BASE))
        if h >= 8:                                                 # the digging claws, flung up
            for sx in (-1, 1):                                     # held out at its sides, three white nails each
                ell(b, cx + sx * 6.5, top + 9 - 2 * sniff, 2, 2, "p")
                for x in (-1.5, .5):
                    dot(b, cx + sx * 6.5 + x, top + 7 - 2 * sniff, "w", on="p")
        if facing == "left":                                       # a pointed snout
            for x, ch in ((cx - 6, "f"), (cx - 7, "p")):
                dot(b, x, top + 4 + sniff, ch)
            dot(b, cx - 6, top + 5 + sniff, "f")
        g = [list(r) for r in over(g, part(b, "O"))]
        if facing == "down":
            g[top + 4 + sniff][cx - 1] = g[top + 4 + sniff][cx] = "p"
            g[top + 3][cx - 3] = g[top + 3][cx + 2] = "e"
        elif facing == "left":
            g[top + 3][cx - 3] = "e"
        g = ["".join(r) for r in g]
    m = canvas(W, H)
    ripple = i % 2 if moving else 0
    mound(m, cx + shake, BASE, 7.5 if h else 7 + ripple, 3.2 if h else 4.6 - ripple, i)
    g = over(g, part(m))
    if moving and facing == "up":                                  # heading away: the trail is nearer the camera, over it
        trail()
    g = [list(r) for r in g]
    for k in range(crumbs * 3):                                    # earth thrown up
        x = cx + (k * 7 + crumbs * 3) % 17 - 8
        dot(g, x, BASE - 5 - crumbs * 2 - (k * 5) % 5, "k" if k % 2 else "l", on=".")
    return ["".join(r) for r in g]


def frames(d):
    return dict(idle=[frame(d), frame(d), frame(d), frame(d, h=3), frame(d, h=5), frame(d, h=5, sniff=1), frame(d, h=5), frame(d, h=2)],
                walk=[frame(d, i, moving=True) for i in range(8)],
                act=[frame(d, shake=-1, crumbs=1), frame(d, shake=1, crumbs=2), frame(d, h=12, crumbs=3, sniff=1), frame(d, h=11), frame(d, h=11),
                     frame(d, h=5), frame(d)])


ENEMY = dict(
    key="burrow", name="Burrow", pal=PAL, role="digger", cell=(32, 32), act="burst", move="tunnel",
    ms=dict(idle=260, walk=90, act=[220, 220, 80, 200, 200, 140, 160]),
    where="soft ground: meadows, fields, gardens. Never under stone or paths", when="day",
    behaviour="A line of molehills coming your way is all you see. It tunnels under fences and walls, eats one root crop, and "
              "leaves. Under your feet it bursts out and knocks you back a tile (small damage). It can only be hit while it is "
              "out of the ground; a paved or stone floor keeps it away, so it teaches agents to pave what they care about.",
    stats=dict(hp=12, damage=4, speed="as fast as you walk", drops="hide; its molehills leave a seed or a pebble"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
