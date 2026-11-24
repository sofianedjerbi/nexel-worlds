"""Grumblestump: a tree stump that was cut and did not forgive it. By day a stump like the pack's own; at night two
embers open in the bark and it pulls its roots out of the ground.

Every frame is computed from parts: a short, wide stump of warm bark (lit on the left, a few bark marks, roots flaring at
its foot), the cut top with its rings under a blanket of moss that drips over the rim, a red mushroom and a sprout; a
face of two round hollows with an ember in each under a heavy brow, and a knothole of a mouth; two thick branch arms
with a leaf tuft and twig fingers.
  idle   the sprout nods, the embers dim and brighten, a slow creak (the body leans a pixel)
  walk   a heavy shuffle: it rocks onto one side's roots, then the other, arms swinging
  slam   the warning: both arms go up high over its head, the embers flare wide, the mouth opens (held); then it brings
         them down on the ground in front, its whole body squashes, and a ring of cracks and flying pebbles runs out.
"""
import math

from art import canvas, dot, ell, ground, over, part, rows

PAL = {"o": "4d3022", "B": "c48d5e", "b": "a6724a", "d": "875a3a", "D": "6b4430", "t": "f0d29c", "T": "d8b27a",
       "q": "c79a62", "m": "8cc25e", "M": "6aa048", "n": "4e7f36", "k": "3a2620", "e": "ffcf5a", "E": "fff6c8",
       "r": "e0574a", "w": "fff3e0", "g": "8fd06a", "u": "d9c49a", "U": "d9c49a90", "p": "a89a8a"}
W, H, BASE = 40, 42, 40


def stump(c, cx, top, w, h, side):
    """The barrel: wider at the foot; lit on the left, shaded on the right; a few short bark marks."""
    for y in range(top, top + h):
        t = (y - top) / max(1, h - 1)
        half = w / 2 + (1.5 * t ** 3)                    # the foot flares out into the roots
        x0, x1 = round(cx - half), round(cx + half)
        for x in range(x0, x1):
            u = (x - x0) / max(1, x1 - x0)
            c[y][x] = "B" if u < .18 else ("b" if u < .62 else ("d" if u < .85 else "D"))
    for k, (fx, y0, ln) in enumerate(((.3, 4, 3), (.55, 7, 4), (.72, 3, 3), (.42, 10, 2), (.8, 9, 3))):
        x = round(cx - w / 2 + w * fx)
        for y in range(top + y0, min(top + y0 + ln, top + h - 1)):
            if c[y][x] in "Bb":
                c[y][x] = "d"
            elif c[y][x] == "d":
                c[y][x] = "D"


def top_of(c, cx, top, w, nod):
    """The cut top: rings, and moss over the back half dripping down the rim; a red mushroom; a sprout."""
    ell(c, cx, top, w / 2, 2.6, "t")
    ell(c, cx, top, w / 2 - 1.4, 1.7, "T", on="t")
    ell(c, cx, top, w / 2 - 2.8, 1, "q", on="T")
    ell(c, cx, top, 1.2, .5, "T", on="q")
    for x in range(round(cx - w / 2) - 1, round(cx + w / 2) + 1):    # the moss: over the back of the top and the rim
        drip = (2, 1, 3, 1, 0, 2, 1, 3, 2, 0, 1, 2, 3, 1, 2, 1, 0, 2)[(x * 7) % 18]
        for y in range(top - 3, top - 1 + drip):
            if 0 <= x < W and (y < top - 1 or c[y][x] != "."):
                c[y][x] = "m" if y < top or (x + y) % 3 else "M"
        dot(c, x, top - 3, "M" if x % 2 else "m")
    for dx, dy, ch in ((-4, -4, "r"), (-3, -4, "r"), (-5, -3, "r"), (-4, -3, "w"), (-3, -3, "r"), (-2, -3, "r"),   # a mushroom
                       (-4, -2, "w"), (-3, -2, "w")):
        dot(c, cx + dx, top + dy, ch)
    for k in range(3):                                   # the sprout, nodding
        dot(c, cx + 3, top - 3 - k, "M")
    dot(c, cx + 2 + nod, top - 6, "g")
    dot(c, cx + 1 + nod, top - 6, "g")
    dot(c, cx + 4 + nod, top - 7, "g")
    dot(c, cx + 5 + nod, top - 7, "g")


def branch(c, sx, sy, s, lift):
    """A thick arm from the shoulder: out and down at rest, up over the head when lift is 1; a leaf tuft, twig fingers."""
    a = 50 - lift * 112                                  # degrees, screen y down: 50 hangs down and out, -75 is up over the head
    ang = math.radians(a) if s > 0 else math.radians(180 - a)
    ln = round(7 + 3 * lift)
    ex, ey = sx + ln * math.cos(ang), sy + ln * math.sin(ang)
    for k in range(ln + 1):
        t = k / ln
        bend = math.sin(t * math.pi) * 1.2 * (1 if lift < .5 else -1)
        x = sx + (ex - sx) * t + bend * -math.sin(ang) * s
        y = sy + (ey - sy) * t + bend * math.cos(ang) * s * .3
        dot(c, x, y, "b")
        dot(c, x, y + 1, "d")
    mx, my = sx + (ex - sx) * .45, sy + (ey - sy) * .45  # a tuft of leaves at the elbow
    ell(c, mx, my - 1.5, 1.6, 1.2, "m")
    for fa in (-.6, 0, .6):                              # three twig fingers
        for k in (1, 2):
            dot(c, ex + k * math.cos(ang + fa), ey + k * math.sin(ang + fa), "d")


def roots(c, cx, w, phase):
    for k, (x, s) in enumerate(((cx - w / 2 - 1, -1), (cx - w / 5, -1), (cx + w / 5, 1), (cx + w / 2, 1))):
        up = phase is not None and (k + phase) % 2 == 0
        for t in range(4):
            y = BASE - 2 - up + min(t, 1)
            dot(c, x + s * t, y, "d" if t < 3 else "D")
            dot(c, x + s * t, y - 1, "b" if t < 2 else "d")


def face(g, cx, ey, side, embers, mouth):
    xs = (cx - 4, cx + 1) if not side else (cx - 6,)
    for x in xs:                                         # a round hollow, a heavy brow over it, the ember inside
        for dx, dy in ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, -1), (1, 2)):
            g[ey + dy][x + dx] = "k"
        for dx in (-1, 0, 1, 2, 3):
            if g[ey - 2][x + dx] in "Bbd":
                g[ey - 2][x + dx] = "D"
        if embers > .3:
            g[ey][x + 1] = "e"
            g[ey + 1][x + 1] = "e" if embers > .8 else "k"
            if embers > 1.2:                             # flaring: wide and bright
                g[ey][x] = g[ey][x + 2] = g[ey + 1][x] = g[ey + 1][x + 2] = "e"
                g[ey][x + 1] = "E"
                g[ey - 1][x + 1] = "e"
            else:
                g[ey][x + 2] = "E"
    my = ey + 5
    mx = cx - 1 if not side else cx - 5
    for dx, dy in ((0, 0), (1, 0)) + (((-1, 1), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2)) if mouth else ()):
        g[my + dy][mx + dx] = "k"
    if mouth:
        g[my + 1][mx] = "r"
        g[my + 1][mx + 1] = "r"


def frame(facing="down", phase=None, rock=0, lift=0.0, squash=0, embers=1.0, nod=0, ring=0, mouth=False, lean=0):
    side, back = facing == "left", facing == "up"
    w = (16 if not side else 14) + squash * 2
    h = 15 - squash * 2 + round(lift)
    cx = W // 2 + rock
    top = BASE - 3 - h
    arms_back, arms_front = canvas(W, H), canvas(W, H)
    shoulders = ((-1, cx - w / 2 + 1), (1, cx + w / 2 - 1)) if not side else ((1, cx + w / 2 - 2),)
    for s, sx in shoulders:
        branch(arms_back if back else arms_front, sx, top + 6, s, lift)
    rt = canvas(W, H)
    roots(rt, cx, w, phase)
    b = canvas(W, H)
    stump(b, cx + lean, top, w, h, side)
    top_of(b, cx + lean, top, w, nod)
    out = over(part(arms_back), part(rt))
    out = over(out, part(b))
    g = [list(r) for r in over(out, part(arms_front))]
    if not back:
        face(g, cx + lean, top + 5, side, embers, mouth)
    g = rows(g)
    if ring:                                             # the shock: cracks and dust out along the ground, pebbles flung up
        g = [list(r) for r in g]
        r = 6 + ring * 4
        for k in range(28):
            ang = k * 2 * math.pi / 28
            x, y = cx + r * math.cos(ang), BASE - 2 + r * .32 * math.sin(ang)
            dot(g, x, y, "u" if k % 3 else "U", on=".")
            if k % 4 == 0:                               # a crack running in
                dot(g, x - math.cos(ang), y - .32 * math.sin(ang), "D", on=".")
            if k % 7 == 0 and ring < 3:                  # pebbles flung up
                dot(g, x + math.cos(ang) * 2, y - 3 - (3 - ring) * 2, "p", on=".")
        g = rows(g)
    return ground(g, cx, w + 6)


def frames(d):
    idle = [frame(d, nod=n, embers=e, lean=l) for n, e, l in ((0, 1, 0), (0, 1, 0), (1, 1, 0), (1, .8, 1), (0, .6, 1),
                                                              (0, .8, 0), (-1, 1, 0), (0, 1, 0))]
    walk = [frame(d, phase=i // 2 % 2, rock=(-1 if i // 2 % 2 else 1) if i % 2 else 0, nod=(i // 2) % 2) for i in range(8)]
    slam = [frame(d, lift=.5, embers=1.3), frame(d, lift=1, embers=1.6, mouth=True), frame(d, lift=1, embers=1.6, rock=1, mouth=True),
            frame(d, lift=1, embers=1.6, rock=-1, mouth=True), frame(d, lift=0, squash=2, ring=1, embers=1.3), frame(d, squash=1, ring=2),
            frame(d, ring=3, nod=1), frame(d)]
    sleep = [frame(d, embers=0, nod=n) for n in (0, 0, 0, 1, 1, 0, 0, -1)]   # by day: only a stump, eyes shut, the sprout nodding
    return dict(idle=idle, walk=walk, slam=slam, sleep=sleep)


ENEMY = dict(
    key="grumblestump", name="Grumblestump", pal=PAL, role="night bruiser", cell=(40, 44), move="shuffle", side="night",
    ms=dict(idle=[400, 300, 260, 300, 400, 300, 260, 300], walk=130, slam=[180, 260, 200, 200, 80, 160, 200, 260], sleep=600),
    beats=dict(slam="wwwwsssr"), hit=dict(slam="knock"),
    where="where trees were cut: clearings, the edge of your wood pile", when="night; a plain stump by day",
    behaviour="By day it is a stump, the kind you chopped. At night its eyes open and it pulls its roots out and shuffles "
              "after whoever cut trees near it. It is slow; what it has is the <b>slam</b>: both arms go up and its embers "
              "flare (held long: that is your time), then it brings them down and a ring of cracks runs out two tiles. "
              "Step clear. Hit it from behind while it pulls its arms back. Beaten, it is firewood, a lot of it.",
    stats=dict(hp=24, damage="4, knocked down", speed="slow", drops="old wood, a seedling"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
