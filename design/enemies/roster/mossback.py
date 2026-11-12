"""Old Mossback: the first boss. A tortoise so old that a garden grew on its shell: turf, an apple tree, mushrooms.
Asleep it is a small hill with a tree on it. Cut the tree, and the hill stands up.

Every frame is computed from parts (shell, garden, head, neck, four legs), so everything moves against everything else:
the shell sinks on each footfall, the head follows a frame late, the tree sways a frame after that.
Three attacks, each with its own warning:
  stomp   it rises on its legs and hangs there, then drops: a ring of dust, everything near is thrown back
  snap    the head pulls into the shell, eyes narrowed, then shoots out two tiles along the way it faces
  shake   the shell shudders and the tree thrashes, leaves fly, and sporecaps tumble off its back
"""
import math

from art import STEP_DX, STEP_UP, canvas, dot, ell, ground, over, part

PAL = {"o": "5a4048", "S": "d3a970", "R": "a97c55", "P": "8c6446", "g": "6fbb62", "G": "9ada7c", "D": "4c9556", "k": "ead79c",
       "K": "cbb27c", "p": "f0a39a", "e": "2b2a3a", "w": "fff6de", "m": "8a3a4a", "t": "9a6b4a", "c": "58a868", "C": "86cc7a",
       "O": "3a7350", "a": "ec6f5f", "r": "ec7a66", "Q": "a8434f", "y": "ffe07a", "x": "fff6de90", "z": "fff6de"}
W, H, BASE = 80, 62, 60
LEGS = 6


def dome_top(cx, bot, x, puff=0):
    u = max(-1, min(1, (x + .5 - cx) / 22))
    return bot - 4 - (18 + puff) * math.sqrt(1 - u * u)


def shell(cx, bot, view, puff=0):
    c = canvas(W, H)
    ell(c, cx, bot - 4, 22, 18 + puff, "S", clip=(0, bot + 1))
    for y in range(H):
        for x in range(W):
            if c[y][x] == ".":
                continue
            turf = bot - 13 - puff + 1.6 * math.sin(x * .9) + .8 * math.sin(x * 2.3)
            if y >= bot - 3:                                         # the rim: a band of plates
                c[y][x] = "P" if (x - cx) % 7 == 0 or y == bot - 3 else "R"
            elif y + .5 < turf - 1:
                c[y][x] = "G" if (x * 7 + y * 13) % 11 == 0 else "g"
            elif y + .5 < turf:
                c[y][x] = "D"
            elif view == "up" and ((x - cx) % 11 == 5 or y == bot - 8):   # the plates, seen from behind
                c[y][x] = "R"
            elif (x - cx) % 14 == 7 and view != "up":
                c[y][x] = "R"
    return part(c)


def garden(g, cx, bot, sway=0, puff=0, shed=False):
    """What grows on the shell: an apple tree (it sways), two mushrooms, flowers."""
    top = lambda x: round(dome_top(cx, bot, x, puff))
    t = canvas(W, H)
    tx = cx + 5
    for y in range(top(tx) - 7, top(tx) + 1):
        for x in range(tx - 1, tx + 2):
            t[y][x + (sway // 2 if y < top(tx) - 3 else 0)] = "t"
    g = over(g, part(t))
    cn, cy = canvas(W, H), top(tx) - 12
    ell(cn, tx + sway, cy, 9, 7, "c")
    ell(cn, tx + sway - 2, cy - 2, 6, 4, "C", on="c")
    for x, y in ((-5, 2), (3, 3), (5, -1), (-1, -4)):
        if not shed or (x + y) % 2:
            dot(cn, tx + sway + x, cy + y, "a")
    g = over(g, part(cn, "O"))
    for mx in (cx - 12, cx - 4):                                     # mushrooms
        m = canvas(W, H)
        y = top(mx)
        for x in (mx, mx + 1):
            m[y][x] = m[y - 1][x] = "w"
        for x in range(mx - 2, mx + 4):
            m[y - 2][x] = "r"
        for x in range(mx - 1, mx + 3):
            m[y - 3][x] = "r"
        m[y - 3][mx] = "w"
        g = over(g, part(m, "Q"))
    g = [list(r) for r in g]
    for fx, ch in ((cx - 17, "y"), (cx + 14, "w"), (cx + 17, "y"), (cx - 8, "w")):   # flowers
        dot(g, fx, top(fx) + 2, ch, on="gGD")
    return ["".join(r) for r in g]


def leg(x, bot, dx=0, up=0, far=False, w=8):
    """A stump of a leg: short, thick, with a wider foot and three nails."""
    c = canvas(W, H)
    for y in range(bot - 2, BASE + 1 - up):
        foot = y >= BASE - 1 - up
        for i in range(-1 if foot else 0, w + (1 if foot else 0)):
            c[y][x + dx + i] = "K" if far or i >= w - 2 or y < bot + 1 else "k"
    if not far:
        for i in (0, 3, 6):
            c[BASE - up][x + dx + i] = "w"
    return part(c)


def head(view, hx, hy, r=0.0, open_=False, angry=False, blink=False):
    c = canvas(W, H)
    ell(c, hx, hy, 7 + r, 6 + r, "K")
    ell(c, hx - .5, hy - 1, 6 + r, 4.6 + r, "k", on="K")
    g = [list(row) for row in part(c)]
    hx, hy = round(hx), round(hy)
    if view == "left":
        g[hy - 1][hx - 3] = "k" if blink else "e"; g[hy - 2][hx - 3] = "o" if blink else "e"
        if angry:
            g[hy - 3][hx - 4] = g[hy - 4][hx - 3] = g[hy - 4][hx - 2] = "o"
        g[hy + 1][hx - 1] = g[hy + 1][hx] = "p"
        for x in range(hx - 7, hx - 2):
            g[hy + 3][x] = "o"
        if open_:
            for y in (hy + 2, hy + 3, hy + 4):
                for x in range(hx - 7, hx - 2 - (y - hy - 2)):
                    if g[y][x] != ".":
                        g[y][x] = "m"
    else:
        for sx in (-4, 3):
            g[hy - 1][hx + sx] = "k" if blink else "e"; g[hy - 2][hx + sx] = "o" if blink else "e"
            if angry:
                g[hy - 4][hx + sx + (1 if sx < 0 else -1)] = g[hy - 4][hx + sx] = "o"; g[hy - 5][hx + sx + (-1 if sx < 0 else 1)] = "o"
        g[hy + 1][hx - 6] = g[hy + 1][hx + 5] = "p"
        for x in (hx - 2, hx + 1):
            g[hy + 2][x] = "o"
        g[hy + 3][hx - 1] = g[hy + 3][hx] = "o"
        if open_:
            ell(g, hx, hy + 3, 3.5, 2.6, "m")
    return ["".join(row) for row in g]


def frame(view, up=0, step=None, bob=0, neck=0, open_=False, angry=False, blink=False, sway=0, shake=0, dust=0, asleep=False,
          puff=0, zs=0, leaves=0, drops=0):
    """up: the body raised on its legs (negative: dropped). step: frame of the walk. neck: head pulled in (<0) or shot out (>0)."""
    side = view == "left"
    cx = (49 if side else 40) + shake
    bot = BASE if asleep else BASE - LEGS - up + bob
    g = ["." * W] * H
    ph = lambda off: (0, 0) if step is None else (STEP_DX[(step + off) % 8], STEP_UP[(step + off) % 8] * 2)
    low = lambda u: max(0, u + min(0, up))                           # a dropped body cannot lift a foot
    if side and not asleep:
        nk = canvas(W, H)                                            # the neck, from the shell to wherever the head is
        hx, hy = cx - 25 - neck, bot - 7 + (bob if step is not None else 0) - (2 if neck > 8 else 0)
        ell(nk, (hx + cx - 20) / 2, hy + 1, (cx - 20 - hx) / 2 + 3, 3.6, "K")
        g = over(g, part(nk))
        for x, off in ((cx - 8, 4), (cx + 4, 0)):                    # far legs
            g = over(g, leg(x, bot, ph(off)[0], low(ph(off)[1]), far=True, w=7))
        tl = canvas(W, H)                                            # tail
        for i in range(4):
            dot(tl, cx + 22 + i, bot - 3 + i // 2, "K"); dot(tl, cx + 22 + i, bot - 2 + i // 2, "K")
        g = over(g, part(tl))
    if view == "up" and not asleep and neck > 8:                     # from behind, the head only shows when it shoots out
        g = over(g, head("up", cx, round(dome_top(cx, bot, cx)) - 2, 0))
    g = over(g, shell(cx, bot, view, puff))
    g = garden(g, cx, bot, sway, puff, shed=drops > 0)
    if not asleep:
        if side:
            g = over(g, head(view, hx, hy, 0, open_, angry, blink))
            for x, off in ((cx - 18, 0), (cx + 11, 4)):              # near legs
                g = over(g, leg(x, bot, ph(off)[0], low(ph(off)[1])))
        else:
            lift = (0, 0) if step is None else ((2, 0) if step in (1, 2, 3) else (0, 2) if step in (5, 6, 7) else (0, 0))
            for k, x in enumerate((cx - 20, cx + 12)):
                g = over(g, leg(x, bot, 0, low(lift[k])))
            if view == "down":
                g = over(g, head(view, cx, bot - 4 + neck * .45 + (bob if step is not None else 0), max(-2, neck * .16), open_, angry, blink))
    g = [list(r) for r in g]
    for k in range(zs):                                              # asleep: a z or two drifting up
        x, y = cx + 20 + k * 5, BASE - 34 - k * 7
        for i, j in ((0, 0), (1, 0), (2, 0), (3, 0), (2, 1), (1, 2), (0, 3), (1, 3), (2, 3), (3, 3)):
            dot(g, x + i, y + j, "z", on=".")
    for k in range(leaves * 5):                                      # leaves torn off the tree
        a = k * 1.3 + leaves
        dot(g, cx + 5 + (10 + leaves * 3) * math.cos(a), BASE - 45 + (7 + leaves * 2) * math.sin(a) + leaves * 2, "C" if k % 2 else "c", on=".")
    for k in range(3 if drops else 0):                               # sporecaps tumbling off its back
        t = drops / 3
        sx = (-1, 1, -1)[k]
        x = round(cx + sx * (10 + k * 4) + sx * 20 * t)
        y = round(BASE - 26 * (1 - t * t) - (6 * math.sin(math.pi * t)))
        for i in range(-3, 4):                                       # a small sporecap, cap first
            dot(g, x + i, y - 3, "Q", on=".")
            if abs(i) < 3:
                dot(g, x + i, y - 4, "r", on="."); dot(g, x + i, y - 5, "r" if abs(i) < 2 else "Q", on=".")
        dot(g, x - 1, y - 5, "w"); dot(g, x + 1, y - 4, "w")
        for i in (-1, 0):
            dot(g, x + i, y - 2, "w", on="."); dot(g, x + i, y - 1, "w", on=".")
    for sx in (-1, 1) if dust else ():                               # the ring of dust
        x = cx + sx * (25 + dust * 4)
        ell(g, x, BASE - dust, 4.5 - dust * .6, 2.4, "w" if dust == 1 else "x", on=".")
        ell(g, x + sx * 5, BASE - 3 - dust * 2, 2, 1.4, "x", on=".")
        dot(g, x - sx * 3, BASE - 5 - dust * 2, "R", on="."); dot(g, x + sx * 2, BASE - 8 - dust, "P", on=".")
    return ground(g, cx, 46 if not asleep else 42)


BOB = [1, 0, 0, 0, 1, 0, 0, 0]                       # the shell sinks as each pair of feet lands
SWAY = [0, 1, 1, 0, 0, -1, -1, 0]                    # the tree answers a frame late


def frames(d):
    return dict(
        sleep=[frame(d, asleep=True, puff=p, zs=z) for p, z in ((0, 0), (0, 1), (1, 1), (1, 2), (1, 2), (0, 2), (0, 1), (0, 0))],
        idle=[frame(d, puff=p, sway=s, blink=b, bob=p) for p, s, b in ((0, 0, 0), (0, 0, 0), (1, 1, 0), (1, 1, 0), (0, 0, 0), (0, 0, 1), (1, -1, 0), (1, -1, 0))],
        walk=[frame(d, step=i, bob=BOB[i], sway=SWAY[i]) for i in range(8)],
        stomp=[frame(d, up=2, sway=-1), frame(d, up=5, angry=True, sway=-1), frame(d, up=5, angry=True, shake=1), frame(d, up=-3, dust=1, sway=3, open_=True),
               frame(d, up=-3, dust=2, sway=-2, angry=True), frame(d, up=-1, dust=3, sway=1), frame(d)],
        snap=[frame(d, neck=-4, angry=True), frame(d, neck=-7, angry=True, shake=1), frame(d, neck=-7, angry=True), frame(d, neck=17, open_=True, angry=True, sway=2),
              frame(d, neck=17, angry=True, sway=-1), frame(d, neck=8), frame(d)],
        shake=[frame(d, shake=-1, sway=-3, leaves=1), frame(d, shake=1, sway=3, leaves=2), frame(d, shake=-1, sway=-3, leaves=3, angry=True),
               frame(d, shake=1, sway=3, leaves=2, angry=True), frame(d, shake=-1, sway=-2, drops=1), frame(d, shake=1, sway=2, drops=2),
               frame(d, sway=-1, drops=3), frame(d)])


ENEMY = dict(
    key="mossback", name="Old Mossback", pal=PAL, role="first boss", cell=(80, 64), move="walk",
    ms=dict(sleep=320, idle=240, walk=120, stomp=[160, 300, 220, 80, 180, 220, 200], snap=[180, 200, 200, 70, 260, 140, 180],
            shake=[110, 110, 110, 110, 130, 130, 160, 200]),
    where="one, on the meadow of the biggest island", when="asleep until its tree is cut or its apples are picked",
    behaviour="A hill with an apple tree on it, until someone swings an axe at the tree. Then the hill stands up. It is slow "
              "and turns slowly. <b>Stomp</b>: it rises and hangs, then drops: step two tiles back or be thrown. "
              "<b>Snap</b>: the head pulls in, then shoots two tiles straight ahead: step sideways, then hit the stretched neck, "
              "its only soft spot. <b>Shake</b>: sporecaps fall off its back and waddle at you. Below half health it does two in a row. "
              "Beaten, it does not die: it lies down, and the island on its back becomes yours to plant. It wakes again in a season.",
    stats=dict(hp=400, stomp="25, two tiles round", snap="30, two tiles ahead", speed="a third of yours",
               drops="shell plate (first armour), apple sapling, a heart"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
