"""Nightfleece: a round night sheep, its wool the colour of dusk with a few stars caught in it. It wanders out of the
dark, sleepy-eyed, and sends whoever it meets to sleep.

Every frame is computed: the fleece is a cloud (an oval with round bumps all along its edge, shaded under, a sheen on
top), the face a dark oval with curled pale horns, the eyes half shut and glowing; four short legs trot in diagonal
pairs like the cow's.
  lull   the warning: the fleece puffs up, the eyes close, it rocks from side to side; then a ring of star dust breaks
         out round it. Caught in the ring you are drowsy: slow, and your view dims, for a few seconds. Step out of it.
"""
import math

from art import canvas, dot, ell, ground, over, part, rows

PAL = {"o": "433d72", "w": "cbc4f0", "W": "a49cd8", "h": "efebff", "f": "5b5592", "F": "443f74", "e": "ffe9a0",
       "x": "f0e2b6", "y": "fff2b0", "Y": "fff2b090", "l": "4d4880", "L": "3a3566"}
W, H, BASE = 38, 32, 30


def cloud(c, cx, cy, rx, ry, puff=0.0, n=9, seed=0, curls=True):
    """A fleece: an oval and round bumps standing out along its edge, a shade underneath, a sheen on top, and a few
    curls (short arcs) in the wool."""
    ell(c, cx, cy, rx - 1, ry - 1, "w")
    for k in range(n):
        a = k * 2 * math.pi / n + seed
        r = 3 + puff * .7
        ell(c, cx + (rx - 1) * math.cos(a), cy + (ry - 1) * math.sin(a), r, r * .9, "w")
    ell(c, cx + .5, cy + ry * .6, rx + 2.5, ry * .6, "W", on="w", clip=(cy + 1, 99))
    ell(c, cx - rx * .35, cy - ry * .5, rx * .35, ry * .28, "h", on="w")
    if curls:
        for k in range(5):
            a = k * 2.1 + seed
            x, y = cx + rx * .55 * math.cos(a), cy + ry * .45 * math.sin(a)
            for dx in (-1, 0, 1):
                dot(c, x + dx, y + (1 if dx == 0 else 0), "W", on="wh")


def stars(g, cx, cy, rx, ry, i=0):
    for k, (a, f) in enumerate(((.9, .5), (2.6, .6), (4.4, .45), (5.6, .7))):
        if (k + i) % 4 != 3:                               # they twinkle out one at a time
            dot(g, cx + rx * f * math.cos(a), cy + ry * f * math.sin(a), "y", on="wWh")


def horn(c, x, y, s):
    """A curled horn beside the ear: a little spiral of three pixels round and one back."""
    for dx, dy in ((0, 0), (s, 0), (s * 2, 1), (s * 2, 2), (s, 3), (0, 2)):
        dot(c, x + dx, y + dy, "x")


def lull_ring(g, cx, cy, r):
    for k in range(14):
        a = k * 2 * math.pi / 14 + r * .15
        x, y = cx + r * math.cos(a), cy + r * .62 * math.sin(a)
        dot(g, x, y, "y", on=".")
        if k % 2 == 0:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                dot(g, x + dx, y + dy, "Y", on=".")


def side(step=None, bob=0, puff=0.0, rock=0, eyes="sleepy", ring=0, i=0):
    cx, cy = 21 + rock, BASE - 10 - bob
    lg = canvas(W, H)
    for k, x in enumerate((cx - 7, cx - 4, cx + 4, cx + 7)):  # legs: far ones darker; diagonal pairs lift together
        up = 1 if step is not None and (k in (0, 3)) == (step % 2 == 0) and step % 4 in (0, 2) else 0
        for y in range(cy + 4, BASE - up):
            dot(lg, x, y, "l" if k % 2 == 0 else "L")
            dot(lg, x + 1, y, "l" if k % 2 == 0 else "L")
    c = canvas(W, H)
    cloud(c, cx, cy, 9 + puff, 5.6 + puff * .6, puff, seed=.3)
    ell(c, cx + 10.5 + puff, cy - 1, 2.2, 2, "w")               # the tail
    hd = canvas(W, H)
    hx, hy = cx - 11.5 - puff * .5, cy + 1
    ell(hd, hx, hy, 3.6, 4.2, "f")
    ell(hd, hx - 1.2, hy + 2.4, 2.6, 2, "f")                    # the muzzle
    ell(hd, hx + 3.2, hy - 1, 2, 1.1, "F")                      # the ear, sticking out back
    ell(hd, hx + 1.5, hy - 3.8, 2.6, 1.6, "w")                  # a fringe of wool on the brow, part of the head
    ell(hd, hx + 1, hy - 4.2, 1.2, .6, "h", on="w")
    out = over(part(lg), part(c))
    out = over(out, part(hd))
    g = [list(r) for r in out]
    horn(g, round(hx + 1), round(hy - 2), 1)
    ey = round(hy) - 1
    ex = round(hx) - 2
    if eyes == "sleepy":
        g[ey][ex] = g[ey][ex + 1] = "e"
        g[ey - 1][ex] = g[ey - 1][ex + 1] = "F"
    elif eyes == "shut":
        g[ey][ex] = "e"
        g[ey][ex + 1] = "F"
    else:
        g[ey][ex] = g[ey][ex + 1] = g[ey - 1][ex] = "e"
    dot(g, hx - 3, hy + 3, "F")                                 # the nostril
    stars(g, cx, cy, 9, 5.6, i)
    if ring:
        lull_ring(g, cx - 2, cy + 3, 6 + ring * 3.5)
    return ground(rows(g), cx - 2, 20)


def facing(back=False, step=None, bob=0, puff=0.0, rock=0, eyes="sleepy", ring=0, i=0):
    cx, cy = 19 + rock, BASE - 11 - bob
    lg = canvas(W, H)
    for k, x in enumerate((cx - 5, cx + 4, cx - 2, cx + 1)):
        up = 1 if step is not None and step % 4 in (0, 2) and (k % 2 == 0) == (step % 4 == 0) else 0
        for y in range(cy + 5, BASE - up):
            dot(lg, x, y, "l" if k < 2 else "L")
            dot(lg, x + 1, y, "l" if k < 2 else "L")
    c = canvas(W, H)
    cloud(c, cx, cy, 8.5 + puff, 6.6 + puff * .6, puff, n=12, seed=.1)
    out = over(part(lg), part(c))
    if back:
        tl = canvas(W, H)
        ell(tl, cx, cy + 3, 2.2, 2, "w")
        ell(tl, cx - .5, cy + 2.4, 1, .8, "h")
        out = over(out, part(tl))
        g = [list(r) for r in out]
        stars(g, cx, cy, 8.5, 6.6, i)
    else:
        hd = canvas(W, H)
        hy = cy + 3
        for s in (-1, 1):
            ell(hd, cx + s * 5.4, hy - 1.2, 2, 1.1, "F")
        ell(hd, cx, hy, 4, 4.4, "f")
        ell(hd, cx, hy + 2.5, 2.6, 1.8, "f")
        ell(hd, cx, hy - 3.6, 3.6, 1.7, "w")
        ell(hd, cx - 1, hy - 4, 1.4, .6, "h", on="w")
        out = over(out, part(hd))
        g = [list(r) for r in out]
        for s in (-1, 1):
            horn(g, round(cx + s * 3.5) - (1 if s < 0 else 0), round(hy - 2), s)
        ey = round(hy)
        for x in (cx - 3, cx + 2):
            if eyes == "sleepy":
                g[ey][x] = g[ey][x + 1] = "e"
                g[ey - 1][x] = g[ey - 1][x + 1] = "F"
            elif eyes == "shut":
                g[ey][x] = g[ey][x + 1] = "F"
                g[ey + 1][x] = g[ey + 1][x + 1] = "e"
            else:
                g[ey][x] = g[ey][x + 1] = g[ey - 1][x] = g[ey - 1][x + 1] = "e"
        g[ey + 3][cx - 1] = g[ey + 3][cx] = "F"
        stars(g, cx, cy - 2, 8.5, 4, i)
    if ring:
        lull_ring(g, cx, cy + 5, 6 + ring * 3.5)
    return ground(rows(g), cx, 18)


def frames(d):
    f = side if d == "left" else (lambda **k: facing(back=d == "up", **k))
    idle = [f(i=i, bob=1 if i in (2, 3, 6, 7) else 0, eyes="shut" if i == 5 else "sleepy") for i in range(8)]
    walk = [f(step=i, bob=1 if i % 2 else 0, i=i // 2) for i in range(8)]
    lull = [f(puff=.6, eyes="shut"), f(puff=1, eyes="shut", rock=-1), f(puff=1.2, eyes="shut", rock=1),
            f(puff=1.2, eyes="shut", rock=-1), f(puff=.4, eyes="open", ring=1), f(eyes="open", ring=2),
            f(eyes="sleepy", ring=3), f(i=1)]
    return dict(idle=idle, walk=walk, lull=lull)


ENEMY = dict(
    key="nightfleece", name="Nightfleece", pal=PAL, role="night drowser", cell=(40, 36), move="trot", side="night",
    ms=dict(idle=[300, 300, 300, 300, 260, 160, 300, 300], walk=100, lull=[200, 220, 220, 220, 100, 160, 220, 260]),
    beats=dict(lull="wwwwsssr"), hit=dict(lull="sleep"),
    where="hills and open meadows, in twos and threes", when="night; it lies down in the grass at dawn and is gone",
    behaviour="Wanders up out of the dark as if it wanted company. Close to you it <b>lulls</b>: the fleece puffs up, its "
              "eyes close and it rocks side to side (the warning), then a ring of star dust breaks out round it. Caught in "
              "the ring you are drowsy: slow, your view dimming, for four seconds, which is when the others come. Step out "
              "of the ring in time and it only yawns. Shorn, it gives star wool, which glows a little.",
    stats=dict(hp=10, damage="0 (drowsy)", speed="a trot", drops="star wool"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
