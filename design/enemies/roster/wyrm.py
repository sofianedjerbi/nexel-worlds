"""Wyrm: a sea serpent. Its head rides above the water and its back breaks the surface in humps that travel down its length.

Only the heads are drawn by hand. The body is computed from a phase, 8 frames to a cycle, so it moves as smoothly as
the player: side-on, a wave whose crests rise out of the water (with a spine along each and foam where it enters);
coming at you or swimming away, the head stands out of the water and the coils break the surface behind it one
after another, sliding from side to side and shrinking toward the tail.
  the lunge   the head rears up and back (held: the warning), then snaps forward with its jaws open, holds, and returns
"""
import math

from art import G, outline, over

PAL = {"o": "234a58", "g": "5fbfa8", "G": "3a8f8c", "c": "eef2cc", "f": "f0a35e", "k": "1f2a3a", "y": "ffe27a",
       "w": "f4fdfd", "W": "bfe6ee", "t": "f6f4ea", "m": "a8404e"}
SIDE_W, SIDE_H, WL = 48, 22, 18                 # the side view, and its water line
HEAD = G("""
......of....
.....offo...
...ooogfo...
..ogggggo...
.ogkygggGo..
ogggggggGGo.
occcoggggGo.
.ooo.oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
""")
HEAD_OPEN = G("""
......of....
.....offo...
...ooogfo...
..ogggggo...
.ogkygggGo..
otgtgggggGo.
.ommmogggGo.
otctcogggGo.
.oooooggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
.....oggGGo.
""")
BOB = [0, 0, 1, 1, 1, 0, 0, 0]


def both(text):
    """A face is symmetric: draw the left half, get the whole."""
    return [r + r[::-1] for r in G(text)]


FACE = both("""
....of
o..off
foooog
ofgggg
.ogggg
.oykgg
.ogggg
..oggc
..oGcc
..ockc
..oGcc
..oooo
""")
FACE_OPEN = FACE[:10] + both("""
..ottt
..ommm
..ottt
...ooo
""")
NAPE = both("""
....of
o..off
foooof
ofgggf
.ogggf
.oggGf
.ogGGf
..oGGg
..oGGG
..oGGG
..oGGG
..oGGG
..oGGG
""")


def side(i, head=HEAD, hx=1, hy=0):
    i %= 8
    fill = [["."] * SIDE_W for _ in range(SIDE_H)]
    for x in range(14, SIDE_W - 1):
        t = (x - 14) / (SIDE_W - 15)
        wave = math.sin(2 * math.pi * (x - 14) / 17 - 2 * math.pi * i / 8)
        rise = round(7.5 * (1 - 0.5 * t) * math.sqrt(wave)) if wave > 0 else 0        # (the root rounds the crest: an arch, not a fin)
        if rise < 1:
            continue
        top = WL - rise
        for y in range(top, WL):
            fill[y][x] = "g" if y - top < 2 else "G"
        if rise >= 3 and x % 3 == 0:
            fill[top - 1][x] = "f"                                   # a spine along the crest
    g = [list(r) for r in outline(["".join(r) for r in fill])]
    for j, row in enumerate(head):                                   # the head and neck, cut off at the water
        for k, ch in enumerate(row):
            y, x = WL - 11 + BOB[i] + hy + j, hx + k
            if ch != "." and 0 <= y < WL and 0 <= x < SIDE_W:
                g[y][x] = ch
    for x in range(SIDE_W):                                          # the surface: foam where a body breaks it, ripples elsewhere
        above = g[WL - 1][x] != "."
        if g[WL][x] == "o" or above:
            g[WL][x] = "w"
            g[WL + 1][x] = "W" if (x + i) % 3 else "."
        elif (x + i) % 5 < 2 and 2 < x < SIDE_W - 2:
            g[WL][x] = "W"
    return ["".join(r) for r in g]


def hump(w, h):
    """One coil of the body breaking the surface, seen end-on: a rounded mound with a spine, standing in its own foam."""
    half = w // 2
    rows = [["."] * (w + 4) for _ in range(h + 2)]
    for r in range(h):
        reach = max(1, round(half * math.sqrt(1 - ((h - 1 - r) / h) ** 2)))
        for x in range(half + 2 - reach, half + 2 + reach):
            rows[1 + r][x] = "g" if r < max(1, h // 2) else "G"
    g = [list(r) for r in outline(["".join(r) for r in rows])]
    if h >= 3:
        g[0][half + 1] = g[0][half + 2] = "f"
    g[h + 1] = list("W" + "w" * (w + 2) + "W")                    # the water line: foam under it, a ripple either side
    return ["".join(r) for r in g]


def above(i, down, lift=0, head=None):
    """Coming at you (down) or swimming away (up): the head stands out of the water and the coils of the body break the
    surface one after another behind it, sliding from side to side and shrinking toward the tail as the wave runs down."""
    i %= 8
    w, h = 20, 30
    g = ["." * w] * h
    head_y = (14 if down else 2) + BOB[i] + lift
    coils = []
    for j in range(-1, 4):
        s = j + i / 8                                              # how far down the body this crest is, in coils
        if not 0.15 < s < 3.0:
            continue
        size = min(1, s / 0.7) * (1 - 0.16 * s)                    # it rises out of the water behind the head, then tapers
        hh, ww = round(5 * size), 2 * round(4.2 * size * (1 - 0.06 * s))        # slim: about as wide as its head
        if hh < 1 or ww < 4:
            continue
        cx = w // 2 + round(3 * math.sin(math.pi * s + 0.6))
        base = round(16 - 4.3 * s) if down else round(13 + 4.3 * s)
        coils.append((base, cx, hump(ww, hh)))
    for base, cx, m in sorted(coils, key=lambda c: c[0]):          # far ones first, near ones over them
        g = over(g, m, cx - len(m[0]) // 2, base - len(m) + 1)
    stamp = head or (FACE if down else NAPE)
    g = over(g, stamp, (w - 12) // 2, head_y)
    if down:                                                        # the chin in its foam
        y = head_y + len(stamp)
        g = over(g, ["W" + ("w" * 8 if i % 2 else "w.wwww.w") + "W", ("..W....W.." if i % 4 < 2 else ".W......W.")], (w - 10) // 2, y)
    return g


def frames(make_idle, windup, strike):
    swim = [make_idle(i) for i in range(8)]
    return dict(idle=swim, walk=swim, act=[windup, strike, strike, make_idle(0)])


ENEMY = dict(
    key="wyrm", name="Wyrm", pal=PAL, ground="water", role="leviathan", cell=(48, 32), act="lunge", move="swim",
    ms=dict(idle=150, walk=95, act=[480, 90, 240, 280]),
    where="deep water, far from shore", when="day and night",
    behaviour="You see the humps first, sliding along the surface, then the head. It circles boats and swimmers; when it rears "
              "its head back it is about to lunge, two tiles ahead of itself: row or swim across its line, not along it. It never "
              "comes into the shallows, so the shore is safe.",
    stats=dict(hp=60, damage=18, speed="fast in deep water", drops="scales, a great fish"),
    dirs={"left": frames(side, side(0, hx=3, hy=-3), side(0, head=HEAD_OPEN, hx=0, hy=2)),
          "down": frames(lambda i: above(i, True), above(0, True, lift=-2), above(0, True, lift=1, head=FACE_OPEN)),
          "up": frames(lambda i: above(i, False), above(0, False, lift=2), above(0, False, lift=-2))},
)
