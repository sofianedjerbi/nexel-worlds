"""Wyrm: a sea serpent. Its head rides above the water and its back breaks the surface in humps that travel down its length.

Only the heads are drawn by hand. The body is computed from a phase, 8 frames to a cycle, so it moves as smoothly as
the player: side-on, a wave whose crests rise out of the water (with a spine along each and foam where it enters);
from above, a thick ribbon swimming, with a fin down its back.
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
FACE = G("""
...ofo...
..ogfgo..
.ogggggo.
ogkgggkgo
ogggggggo
.ogcccgo.
..occco..
...ooo...
""")
NAPE = [r.replace("k", "g").replace("c", "g") for r in FACE[::-1]]      # the back of the head, pointing up the screen


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


def above(i, down, pull=0, jaws=False):
    """Seen from above, swimming up the screen (or down, with its face showing)."""
    i %= 8
    w, n = 16, 20
    fill = [["."] * w for _ in range(n + 10)]
    for r in range(n):
        t = r / n
        cx = 8 + round(3 * min(1, r / 5) * math.sin(2 * math.pi * r / 13 - 2 * math.pi * i / 8))
        half = 2 if t < .6 else 1 if t < .85 else 0
        for x in range(cx - half, cx + half + 1):
            fill[10 + r][x] = "G" if half == 2 and abs(x - cx) == 2 else "g"
        if half == 2 and r % 3 == 1:
            fill[10 + r][cx] = "f"
    g = outline(["".join(r) for r in fill])
    g = over(g, NAPE if not down else FACE[::-1], 3, 3 + pull)       # (drawn head-up; the whole picture is flipped for "down")
    if jaws and down:
        g = over(g, ["ttt", "omo"], 6, 2 + pull)
    for k in range(4):                                               # a little wake beside the bends
        y = 12 + k * 5 + (i % 4)
        if y < n + 9:
            for x in (1, 14):
                if g[y][x] == ".":
                    g = over(g, ["W"], x, y)
    return g[::-1] if down else g


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
          "down": frames(lambda i: above(i, True), above(0, True, pull=2), above(0, True, pull=-2, jaws=True)),
          "up": frames(lambda i: above(i, False), above(0, False, pull=2), above(0, False, pull=-2))},
)
