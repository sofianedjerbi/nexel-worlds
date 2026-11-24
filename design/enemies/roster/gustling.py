"""Gustling: a little whirlwind that got a mind of its own. A funnel of air with leaves going round in it and two eyes
in the middle. No legs, no body: it is all spin.

Every frame is computed from one phase. The funnel is a stack of rings, narrow at the ground and wide at the top, each
ring a little behind the one under it, so the column leans and wobbles. Streaks run round the rings (bright on the near
side, faint on the far side) and leaves orbit on three heights, passing in front of the funnel and behind it.
  snatch  it draws itself up thin and tall and spins hard (the warning: the leaves tighten), then pops wide, throwing
          the leaves out, and whatever you held in your free hand is in it. Hit it before the pop to keep it.
"""
import math

from art import dot, ground, rows

PAL = {"c": "eef8f9a0", "q": "c4dfe4", "w": "ffffff", "o": "9cc4cc", "e": "45566a", "E": "ffffff",
       "g": "86c45c", "G": "5f9a45", "r": "f0a050", "R": "c9733a", "u": "e6d7ad", "U": "e6d7ad90",
       "a": "e8574a", "A": "b23a3c", "l": "7fbf5a", "m": "5a6e86"}
W, H, BASE = 30, 34, 32


def frame(i, facing="down", tall=0, tight=0, pop=0, eyes=True, loot=False):
    """i: the spin phase (any number; 8 a turn). tall: rows taller and thinner. pop: 0..2, flung wide."""
    g = [["."] * W for _ in range(H)]
    cx0 = W / 2
    top = BASE - 22 - tall
    ph = i * math.pi / 4
    centres = {}
    for y in range(top, BASE):                         # the funnel: one ring a row
        t = (BASE - y) / (BASE - top)                  # 0 at the ground, 1 at the top
        r = 1 + (8.5 - tall * .45 + pop * 2.5) * t ** 1.3
        if y < top + 3:
            r -= (top + 3 - y) * 1.3                   # the top rolls over, round
        cx = cx0 + 1.6 * math.sin(ph + t * 2.2) * t + (pop * (1 if (y % 2) else -1) * .5)
        centres[y] = (cx, r)
        for x in range(W):
            if abs(x + .5 - cx) <= r:
                g[y][x] = "c"
        if r >= 1.5:
            g[y][max(0, round(cx - r))] = "o"
            g[y][min(W - 1, round(cx + r) - 1)] = "o"
    for y0 in range(top + 1, BASE - 1, 3):             # bands of wind: an arc sweeping round each ring, bright in front
        cx, r = centres[y0]
        if r < 2:
            continue
        a0 = ph * (1.5 + tight) + y0 * .9
        for k in range(14):
            a = a0 + k * .16
            x = round(cx + r * .92 * math.sin(a) - .5)
            y = y0 + round(.9 * math.cos(a))
            if 0 <= x < W and top <= y < BASE:
                g[y][x] = "w" if math.cos(a) > -.1 else "q"
    if eyes and facing != "up":                         # the eyes, in the middle, looking where it goes
        ey = BASE - 12 - tall // 2
        cx, r = centres[ey]
        fx = {"left": -2, "down": 0}[facing]
        for x in (round(cx) - 3 + fx, round(cx) + 1 + fx):    # tall round eyes with a glint; squeezed shut in the hard spin
            if tight >= 1.5:
                g[ey][x] = g[ey][x + 1] = "e"
                continue
            for dy in (-2, -1, 0):
                g[ey + dy][x] = g[ey + dy][x + 1] = "e"
            g[ey - 2][x] = "E"
        mx = round(cx) - 1 + fx                        # a small mouth: an o in the hard spin, otherwise a dot
        g[ey + 2][mx] = "m"
        if tight >= 1:
            g[ey + 2][mx + 1] = g[ey + 3][mx] = g[ey + 3][mx + 1] = "m"
    for k, (h, rad, col) in enumerate(((.25, 1.0, "g"), (.55, 1.25, "r"), (.85, 1.15, "g"), (.4, 1.2, "R"), (.7, 1.1, "G"))):
        y = round(BASE - h * (BASE - top))             # leaves orbiting at three heights
        cx, r = centres[y]
        a = ph * (1.3 + tight * 1.5) + k * 2.4
        rr = r * rad * (1 - tight * .3) + pop * 5
        x = cx + rr * math.sin(a)
        front = math.cos(a) > 0
        if not front and abs(x - cx) < r - 1 and not pop:
            continue                                   # behind the funnel: hidden
        lx = round(x - .5)
        for dx, dy, ch in ((0, 0, col), (1, 0, col), (0, 1, col.upper() if col.islower() else col), (-1, -1, col)):
            if 0 <= lx + dx < W and 0 <= y + dy - pop * 2 < BASE:
                g[y + dy - pop * 2][lx + dx] = ch
    if loot:                                           # what it took: an apple going round and round inside it
        y = BASE - 7
        cx, r = centres[y]
        a = ph * 1.6
        x = round(cx + (r - 3) * math.sin(a) - 1)
        for dx, dy, ch in ((0, 0, "a"), (1, 0, "a"), (0, 1, "A"), (1, 1, "a"), (-1, 1, "a"), (2, 1, "A"), (0, 2, "A"), (1, 2, "A"), (1, -1, "l"), (2, -2, "l")):
            if 0 <= x + dx < W:
                g[y + dy][x + dx] = ch
    for k in range(6):                                 # dust kicked up where it touches the ground
        a = ph * 2 + k
        x = round(cx0 + 3.5 * math.sin(a) + (k - 3) * .6)
        y = BASE - 1 - (k % 2) - (1 if math.cos(a) > .5 else 0)
        if 0 <= x < W and g[y][x] == ".":
            g[y][x] = "u" if k % 3 else "U"
    return ground(rows(g), cx0, 10)


def frames(d):
    snatch = [frame(i, d, tall=t, tight=tg) for i, t, tg in ((0, 2, .5), (1, 4, 1), (2, 6, 1.5), (3, 6, 1.5), (4, 6, 1.5))]
    snatch += [frame(5, d, pop=1), frame(6, d, pop=2, eyes=False), frame(7, d, pop=1, loot=True), frame(0, d, loot=True),
               frame(1, d, loot=True), frame(2, d, loot=True)]
    return dict(idle=[frame(i, d) for i in range(8)], walk=[frame(i, d) for i in range(8)], snatch=snatch)


ENEMY = dict(
    key="gustling", name="Gustling", pal=PAL, role="rare, day", cell=(32, 40), move="drift", side="day",
    beats=dict(snatch="wwwwwsssrrr"), hit=dict(snatch="steal"),
    ms=dict(idle=110, walk=70, snatch=[170, 130, 100, 100, 100, 80, 160, 160, 130, 130, 160]),
    where="open hills and fields on a windy day", when="day, wind only; rare",
    behaviour="A breeze that wanders against the wind. It drifts up to whoever is busiest and <b>snatches</b>: it draws up thin "
              "and spins hard (the leaves tighten round it), then pops wide and takes whatever is in your free hand, then runs. "
              "Hit it during the spin and it scatters into a harmless breeze. Catch it after a snatch and it drops "
              "everything it took that day, which is sometimes a lot.",
    stats=dict(hp=4, damage="0 (steals)", speed="as fast as you", drops="what it stole"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
