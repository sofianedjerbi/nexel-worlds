"""The drake: a boss rig for the high-energy track "Sugar rush" (E flat, 156 BPM, a kick on every beat), in three looks
to choose from (roster/solflare.py, voltwing.py, nyxwing.py): comet (fire), storm (lightning), eclipse (stars).

A big dragon that never lands. Everything is timed to the song: a wing beat is one musical beat (385 ms), the idle
hover two, each warning a beat and a half, and every strike lands on a beat.
Every frame is computed from parts (far wing, tail, body with its back spines, neck, head and horns, legs, near
wing), the wings from a shoulder angle and three fingers, so the flap is one number per frame. A theme only changes
the paint (palette, scale pattern, wing membrane), the spines down its back and the tip of its tail.
Attacks (the warning first, held, then the strike):
  breath   it rears back and sparks gather at its jaws, then it breathes a cone four tiles ahead
  storm    it climbs and throws its wings wide, then spins and fires rings of bolts, one ring on each beat
  dive     wings straight up, it shoots off the top of the screen, its shadow hunts you, and it crashes down on the beat
  sweep    the tail coils high over its back, then whips round in a ring
  rush     (below half health) a roar, its spines blaze: it gets faster and attacks on half beats
"""
import math

from art import ground, over, part

THEMES = {
    "comet": dict(key="solflare", name="Solflare", spines="flame", tip="plume", wing="fire", scales="scales", pal={
        "o": "5a2418", "w": "f6b84a", "W": "fff0b0", "v": "d9792e", "r": "e0702e", "R": "b5522a", "m": "fff0c8",
        "M": "f2cf8e", "p": "ff9a3c", "P": "ffe08a", "n": "e0482e", "b": "9a3426", "c": "fff6e0", "C": "e8cf98",
        "y": "fffbd0", "Y": "ffffff", "e": "5a1a10", "q": "7a1f1f", "t": "ff9a5a", "1": "ff4a2a", "2": "ff9d2e",
        "3": "ffe066", "4": "fff6d0", "5": "ff6a3a", "x": "fff6d0aa", "g": "ffd16699"}),
    "storm": dict(key="voltwing", name="Voltwing", spines="fins", tip="blade", wing="veins", scales="bolts", pal={
        "o": "141833", "w": "3f4f9a", "W": "7f95e8", "v": "2a3570", "r": "6fe3ff", "R": "3aa6df", "m": "a9c0ff",
        "M": "7a90e0", "p": "2f3a80", "P": "4656b0", "n": "1f2758", "b": "8ff3ff", "c": "e8ffff", "C": "7fe0ff",
        "y": "fffb9a", "Y": "ffffff", "e": "0e1030", "q": "1a1f45", "t": "6fe3ff", "1": "8ff3ff", "2": "ffffff",
        "3": "6fe3ff", "4": "fffb9a", "5": "b48cff", "x": "d8fbffaa", "g": "8ff3ff88"}),
    "eclipse": dict(key="nyxwing", name="Nyxwing", spines="gold", tip="orb", wing="stars", scales="runes", pal={
        "o": "1a0f2a", "w": "3d2a66", "W": "6a52a0", "v": "2a1c4a", "r": "ffcf5a", "R": "d9a63a", "m": "6b52a8",
        "M": "4e3a86", "p": "3a2468", "P": "5a3c94", "n": "24163f", "b": "ffcf5a", "c": "ffe08a", "C": "e0a83a",
        "y": "fff3c0", "Y": "ffffff", "e": "0b0614", "q": "12091f", "t": "c77dff", "1": "ffcf5a", "2": "fff3c0",
        "3": "c77dff", "4": "7fb8ff", "5": "ff7ac8", "x": "fff3c0aa", "g": "ffcf5a88"}),
}
TH = THEMES["comet"]
W, H = 128, 112
ACCENT = "12345"


def canvas():
    return [["."] * W for _ in range(H)]


def oval(c, cx, cy, rx, ry, ch, on=None):
    for y in range(max(0, int(cy - ry - 1)), min(H, int(cy + ry + 2))):
        for x in range(max(0, int(cx - rx - 1)), min(W, int(cx + rx + 2))):
            if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1 and (on is None or c[y][x] in on):
                c[y][x] = ch(x, y) if callable(ch) else ch


def put(c, x, y, ch, on=None):
    x, y = math.floor(x + .5), math.floor(y + .5)
    if 0 <= y < H and 0 <= x < W and (on is None or c[y][x] in on):
        c[y][x] = ch


def seg(c, pts, r0, r1, ch, on=None):
    """A thick stroke along a polyline, radius r0 to r1. ch may be a function of the place along it (0-1)."""
    lens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total, done = sum(lens) or 1, 0
    for (ax, ay), (bx, by), n in zip(pts, pts[1:], lens):
        k = max(1, int(n * 2))
        for i in range(k + 1):
            t = (done + n * i / k) / total
            r = r0 + (r1 - r0) * t
            oval(c, ax + (bx - ax) * i / k + .5, ay + (by - ay) * i / k + .5, r, r, ch(t) if callable(ch) else ch, on)
        done += n


def poly(c, pts, ch, on=None):
    ys = [p[1] for p in pts]
    for y in range(max(0, int(min(ys))), min(H, int(max(ys)) + 1)):
        yc, xs = y + .5, []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if (y0 <= yc < y1) or (y1 <= yc < y0):
                xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for a, b in zip(xs[::2], xs[1::2]):
            for x in range(max(0, math.ceil(a - .5)), min(W, math.floor(b - .5) + 1)):
                if on is None or c[y][x] in on:
                    c[y][x] = ch


def crystal(c, x, y, ang, n, w=2.6):
    """A shard of crystal from (x, y), n long, at angle ang (degrees, 0 = +x, -90 = up): two tones and a glint."""
    a = math.radians(ang)
    dx, dy, px, py = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    tip = (x + dx * n, y + dy * n)
    poly(c, [(x + px * w, y + py * w), tip, (x - px * w, y - py * w), (x - dx * 1.5, y - dy * 1.5)], "c")
    poly(c, [(x, y), tip, (x - px * w, y - py * w), (x - dx * 1.5, y - dy * 1.5)], "C")
    for i in range(1, int(n * .45)):
        put(c, x + dx * i + px * .8, y + dy * i + py * .8, "W")


def spine(c, x, y, r, i, lit=False, phase=0.):
    """One of the spines down its back, in the theme's kind: a tongue of flame, a fin of ice-blue glass, a gold thorn."""
    kind = TH["spines"]
    if kind == "flame":
        n = r * (3 + (.8 if lit else 0)) + 1.8 * math.sin(phase * 2.6 + i * 1.7)
        a = math.radians(-100 + 8 * math.sin(phase * 1.9 + i))
        seg(c, [(x, y), (x + n * math.cos(a), y + n * math.sin(a))], r * 1.05, .5, lambda t: "3" if t < .3 else "2" if t < .65 else "1")
    elif kind == "fins":
        crystal(c, x, y, -104 + i * 3, r * (2.4 + (.5 if lit else 0)), r * .62)
    else:
        crystal(c, x, y, -96 + i * 2, r * (1.9 + (.6 if lit else 0)), r * .5)
        if lit:
            put(c, x, y - r * 2.4, "Y")


def wing(sx, sy, arm, side=1, far=False, spread=1.0, glint=0):
    """A wing from the shoulder (sx, sy). arm: the arm's angle in degrees (-90 up, 0 out, 90 down),
    side=-1 mirrors it. The membrane hangs between three fingers with a scalloped edge."""
    c = canvas()
    a = math.radians(arm)
    wx, wy = sx + side * 19 * math.cos(a), sy + 19 * math.sin(a)
    tips = []
    for L, da in ((35, 30), (30, 62), (21, 96)):
        b = math.radians(arm + da * spread)
        tips.append((wx + side * L * math.cos(b), wy + L * math.sin(b)))
    root = (sx + side * 14, sy + 8)
    pts = [(sx, sy), (wx, wy), tips[0]]
    for t0, t1 in zip(tips, tips[1:]):
        mx, my = (t0[0] + t1[0]) / 2, (t0[1] + t1[1]) / 2
        pts += [(mx + (wx - mx) * .3, my + (wy - my) * .3), t1]
    mx, my = (tips[2][0] + root[0]) / 2, (tips[2][1] + root[1]) / 2
    pts += [(mx + (wx - mx) * .3, my + (wy - my) * .3), root]
    poly(c, pts, "n" if far else "p")
    if not far:                                                          # light by the wrist, deeper at the edge
        reach = max(math.dist((wx, wy), t) for t in tips)
        for y in range(H):
            for x in range(W):
                if c[y][x] == "p":
                    r = math.dist((x + .5, y + .5), (wx, wy)) / reach
                    c[y][x] = "P" if r < .38 else "n" if r > .82 else "p"
                    if TH["wing"] == "stars" and (x * 7 + y * 13 + glint) % 23 == 0:
                        c[y][x] = "W" if (x + y) % 3 else "y"
        if TH["wing"] == "veins":                                        # lightning cracks through the membrane
            for k, (tx, ty) in enumerate(tips):
                for i in range(1, 12):
                    f = i / 12
                    put(c, wx + (tx - wx) * f + (1.6 if (i + k + glint) % 2 else -1.6) * (ty - wy) / 30,
                        wy + (ty - wy) * f - (1.6 if (i + k + glint) % 2 else -1.6) * (tx - wx) / 30, "r", on="pPn")
        for k, (tx, ty) in enumerate(tips):                              # glints on the membrane
            if TH["wing"] != "veins":
                put(c, wx + (tx - wx) * (.5 + .1 * ((k + glint) % 3)), wy + (ty - wy) * (.5 + .1 * ((k + glint) % 3)) + 2, "W", on="pPn")
    seg(c, [(sx, sy), (wx, wy)], 2.4, 1.7, "R" if far else "b")
    for tx, ty in tips:
        seg(c, [(wx, wy), (tx, ty)], 1.2, .55, "R" if far else "b")
    put(c, wx - side * 1, wy - 2, "w"); put(c, wx - side * 2, wy - 2, "w")  # the thumb claw
    return part(c)


def pattern(c, x0=0, x1=W, on="w"):
    """The theme's markings over the body: rows of scales, zigzag bolts, scattered gold runes."""
    kind = TH["scales"]
    for y in range(H):
        for x in range(max(0, int(x0)), min(W, int(x1))):
            if c[y][x] not in on:
                continue
            if kind == "scales" and y % 3 == 2 and (x + 2 * ((y // 3) % 2)) % 4 in (0, 1):
                c[y][x] = "r"
            elif kind == "bolts" and (x + abs(y % 8 - 4)) % 13 == 0:
                c[y][x] = "r"
            elif kind == "runes" and ((x * 7 + y * 13) % 41 == 0 or (x * 5 + y * 3) % 53 == 0):
                c[y][x] = "r"


def shade(c, on="wr"):
    """Light from above: a glint along the top of each column, its lower third in shadow."""
    for x in range(W):
        ys = [y for y in range(H) if c[y][x] in on]
        if len(ys) < 4:
            continue
        y0, y1 = ys[0], ys[-1]
        for y in ys:
            if y == y0 + 1 and c[y][x] == "w":
                c[y][x] = "W"
            elif y > y1 - (y1 - y0) * .34:
                c[y][x] = {"w": "v", "r": "R" if TH["scales"] != "bolts" else "r"}[c[y][x]]


def tail(c, base, ang, sway=0., phase=0., n=10, step=4.2, curl=1.0):
    """The tail: long, tapering, and the theme's tip at the end (a plume of flame, a blade of lightning, an eclipse)."""
    pts, (x, y) = [base], base
    a = ang
    for i in range(n + 3):
        a = ang + sway * math.sin(i * .55 + phase) + (.03 - .1 * curl * (i > n)) * i
        x, y = x + step * math.cos(a), y + step * math.sin(a)
        pts.append((x, y))
    seg(c, pts, 5.4, 2.8, "w")
    pattern(c)
    shade(c)
    tip = TH["tip"]
    if tip == "plume":
        for k in range(5):
            b = a + (k - 2) * .32 + .15 * math.sin(phase * 2.3 + k)
            L = 14 + 3 * math.sin(phase * 3.1 + k * 1.3) - abs(k - 2) * 2.5
            seg(c, [(x, y), (x + L * math.cos(b), y + L * math.sin(b))], 3.2, .5, lambda t: "3" if t < .3 else "2" if t < .65 else "1")
    elif tip == "blade":
        crystal(c, x, y, math.degrees(a), 13, 3.2)
        for d in (-50, 50):
            crystal(c, x, y, math.degrees(a) + d, 6, 1.8)
    else:
        oval(c, x + 2 * math.cos(a), y + 2 * math.sin(a), 5, 5, "c")
        oval(c, x + 2 * math.cos(a) + .6, y + 2 * math.sin(a) - .6, 3.4, 3.4, "e")
        put(c, x + 2 * math.cos(a) - 2.6, y + 2 * math.sin(a) - 2.6, "Y")
    return pts


def effects(g, fx, mouth, cx, cy):
    """Marks painted on empty pixels: sparks gathering at the jaws, the first gout of fire, a rainbow ribbon, shards,
    sparkle stars, a trail of sparks."""
    c = [list(r) for r in g]
    mx, my = mouth
    for kind, k in fx:
        if kind == "gather":                                             # sparks drawn in to the mouth
            for i in range(10):
                a = i * 2.4 + k
                r = 16 - k * 4 + (i % 3) * 3
                put(c, mx + r * math.cos(a), my + r * math.sin(a) * .7, "2" if i % 2 else "W", on=".")
                if i % 3 == 0:
                    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        put(c, mx + r * math.cos(a) + d[0], my + r * math.sin(a) * .7 + d[1], "g", on=".")
        if kind == "fire":                                               # the first gout, at the jaws (the cone is the game's)
            for i in range(60):
                f = i / 59
                x = mx + k * (3 + f * 30)
                yy = my + 2 + math.sin(i * 2.3) * (1 + f * 10)
                for d in range(4 if f < .6 else 3):
                    put(c, x + d * k * -1, yy, "W" if f < .25 else "2" if f < .5 else "1" if i % 3 else "t", on=".")
        if kind == "ribbon":                                             # the tail's sweep, in five bands of colour
            a0, a1 = k
            for band, col in enumerate(ACCENT):
                for i in range(160):
                    a = a0 + (a1 - a0) * i / 159
                    put(c, cx + (40 + band) * math.cos(a), cy + 10 + (16 + band * .5) * math.sin(a), col, on=".")
        if kind == "shards":                                             # shards flung from the crash
            for i in range(18):
                a = math.pi + i * math.pi / 17
                r = 12 + k * 10 + (i % 3) * 4
                x, y = cx + r * 1.7 * math.cos(a), H - 6 + r * .6 * math.sin(a) - k * 3
                col = ACCENT[i % 5]
                poly(c, [(x - 2, y + 1), (x, y - 3), (x + 2, y + 1)], col, on=".")
                put(c, x, y - 1, "W", on=col)
        if kind == "stars":                                              # four-point sparkle stars
            for (sx, sy) in k:
                put(c, sx, sy, "W", on=".")
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    put(c, sx + d[0], sy + d[1], "2", on=".")
                for d in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                    put(c, sx + d[0], sy + d[1], "g", on=".")
        if kind == "trail":                                              # sparks left behind when it flies fast
            for i in range(9):
                x = cx + 34 + i * 6 + (k * 3) % 6
                y = cy - 4 + math.sin(i * 1.7 + k) * 9
                put(c, x, y, ACCENT[(i + k) % 5] if i % 2 else "W", on=".")
    return ["".join(r) for r in c]


FLAP_SIDE = [-108, -94, -64, -26, 6, -6, -44, -86]       # one wing beat in eight frames: up, the down-stroke, the lift
FLAP_FRONT = [-58, -46, -24, 4, 26, 16, -12, -40]
LIFT = [0, -1, -1, 0, 1, 2, 2, 1]                        # the body rises on the down-stroke


def side(flap=0, alt=0, rear=0, lunge=0, jaw=0, glare=False, blink=False, spread=1., tail_ang=.25, sway=.12, phase=0.,
         coil=0., lit=False, legs=0, fx=(), arm=None, far_arm=None):
    """Facing left. flap: frame of the wing beat. alt: height (px). rear: head pulled back; lunge: thrown forward.
    coil: the tail raised over the back (0-1). lit: the spines blaze (rush). legs: claws thrust down (0-1)."""
    arm = FLAP_SIDE[flap % 8] if arm is None else arm
    far_arm = arm - 6 if far_arm is None else far_arm
    by = 70 - alt + LIFT[flap % 8]
    g = ["." * W] * H
    g = over(g, wing(70, by - 12, far_arm, 1, far=True, spread=spread))
    c = canvas()
    if coil:
        tail(c, (86, by + 1), tail_ang + .3 - 2.4 * coil, sway * .5, phase, n=7, step=4, curl=.8)
    else:
        tail(c, (86, by + 2), tail_ang + .3, sway, phase, n=7, step=4)
    g = over(g, part(c))
    c = canvas()                                                         # the body, its markings, a pale belly
    oval(c, 66, by, 20, 12, "w")
    oval(c, 52, by - 3, 11, 11, "w")
    oval(c, 84, by + 1, 10, 9, "w")
    pattern(c, 40, 96)
    for y in range(H):
        for x in range(W):
            if c[y][x] in "wr" and y > by + 4 + (x - 66) ** 2 / 160:
                c[y][x] = "m" if y < by + 9 else "M"
    shade(c)
    for i in range(6):                                                   # spines down the back
        x = 50 + i * 7.5
        top = next(y for y in range(H) if c[y][round(x)] != ".")
        spine(c, x, top + 2, 4.2 - abs(i - 2) * .3, i, lit, phase)
    g = over(g, part(c))
    hx, hy = 28 + rear * 1.0 - lunge * 1.2, by - 30 - rear * .6 + lunge * .9
    c = canvas()                                                         # the neck, in rings
    seg(c, [(54, by - 6), (46, by - 14), (40 + rear * .4 - lunge * .5, by - 22 + lunge * .3), (hx + 6, hy + 2)], 7, 5.4, "w")
    pattern(c)
    shade(c)
    g = over(g, part(c))
    c = canvas()                                                         # horns, behind the head
    for bx, by_, ang, n in ((hx + 2, hy - 6, -80, 17), (hx + 8, hy - 5, -50, 14), (hx + 12, hy - 1, -20, 10)):
        crystal(c, bx, by_, ang, n)
    g = over(g, part(c))
    c = canvas()                                                         # the head
    oval(c, hx + 2, hy, 11, 8.5, "w")
    oval(c, hx - 10, hy + 2.5, 10.5, 5.4, "w")
    for y in range(H):
        for x in range(W):
            if c[y][x] == "w" and y >= hy + 4:
                c[y][x] = "v"
    for x in range(round(hx - 14), round(hx + 8)):                       # a glint along the top of the head
        top = next((y for y in range(H) if c[y][x] == "w"), None)
        if top is not None:
            c[top + 1][x] = "W"
    for i in range(3):                                                   # pink cheek frills
        poly(c, [(hx + 7, hy + 1 + i * 2), (hx + 15, hy - 1 + i * 3.5), (hx + 9, hy + 3 + i * 2)], "r")
    oval(c, hx - 8, hy + 7.5 + jaw, 10, 2.6, "v")                           # the lower jaw
    if jaw:
        poly(c, [(hx - 19, hy + 5), (hx + 2, hy + 5), (hx + 2, hy + 6 + jaw), (hx - 18, hy + 6 + jaw)], "q")
        oval(c, hx - 6, hy + 6 + jaw * .8, 5, 1.2 + jaw * .25, "t", on="q")
        for x in range(round(hx - 18), round(hx + 1), 2):
            put(c, x, hy + 5, "W"); put(c, x + 1, hy + 6 + jaw, "W")
    else:
        for x in range(round(hx - 19), round(hx + 1)):                  # a closed mouth: one flat line, two fangs
            put(c, x, hy + 5, "o")
        put(c, hx - 12, hy + 6, "W"); put(c, hx - 6, hy + 6, "W")
    put(c, hx - 19, hy + 1, "e")                                         # a nostril
    if blink:
        for i in range(-2, 3):
            put(c, hx - 1 + i, hy - 1, "v")
    else:
        oval(c, hx - 1, hy - 1, 3.6, 2.8, "y")
        for j in (-2, -1, 0, 1):
            put(c, hx - 1, hy + j, "e")
        put(c, hx - 3, hy - 2, "Y"); put(c, hx - 2, hy - 2, "Y")
    for i, j in ((-5, -2), (-4, -3), (-3, -3), (-2, -4), (-1, -4), (0, -4), (1, -5), (2, -5)):   # a brow, low in front
        put(c, hx + i, hy + j - (1 if glare else 0), "o")
        if glare:
            put(c, hx + i, hy + j, "o")
    g = over(g, part(c))
    c = canvas()                                                         # little arms and legs, claws thrust when it strikes
    for x0, y0, dx in ((54, by + 6, -2), (82, by + 7, -1)):
        foot = (x0 + dx - legs * 3, y0 + 9 + legs * 5)
        seg(c, [(x0, y0), (x0 + 2, y0 + 5), foot], 3, 2, "m")
        for i in (-2, 0, 2):
            put(c, foot[0] + i - 1, foot[1] + 2, "W")
    g = over(g, part(c))
    g = over(g, wing(64, by - 13, arm, 1, spread=spread, glint=flap))
    mouth = (hx - 21, hy + 4 + jaw * .5)
    return ground(effects(g, fx, mouth, 62, by), 64, 52 - min(20, alt // 2))


def front(flap=0, alt=0, rear=0, lunge=0, jaw=0, glare=False, blink=False, spread=1., tail_ang=.25, sway=.12, phase=0.,
          coil=0., lit=False, legs=0, fx=(), back=False, arm=None, far_arm=None):
    """Seen from in front, or from behind (back=True). The wings open to both sides."""
    arm = FLAP_FRONT[flap % 8] if arm is None else arm
    by = 72 - alt + LIFT[flap % 8]
    hy = by - 20 - rear * .5 + lunge * .8
    cx = 64
    g = ["." * W] * H
    c = canvas()                                                         # the tail, hanging behind (or towards you, from behind)
    if not back:
        tail(c, (cx + 4, by + 6), 1.15 - coil * 2.6, sway, phase, n=7, step=3.8)
        g = over(g, part(c))
    for s in (-1, 1):
        g = over(g, wing(cx + s * 9, by - 9, arm, s, spread=spread, glint=flap + (s > 0)))
    c = canvas()
    oval(c, cx, by, 16, 13, "w")
    if back:
        pattern(c, cx - 20, cx + 20)
        shade(c)
    else:
        pattern(c, cx - 20, cx + 20)
        shade(c)
        oval(c, cx, by + 3, 8, 9, lambda x, y: "m" if y < by + 7 else "M", on="wrWvR")
    for i in range(7):                                                   # spines: down the back from behind, a ruff of them in front
        if back:
            x, y = cx, by - 9 + i * 3.4
            spine(c, x, y, 3.6 - i * .2, i, lit, phase)
        else:
            a = math.pi + .5 + i * (math.pi - 1) / 6
            spine(c, cx + 15 * math.cos(a), by - 6 + 9 * math.sin(a), 3.8, i, lit, phase)
    g = over(g, part(c))
    if back:
        c = canvas()                                                     # the neck, rising away from you
        seg(c, [(cx, by - 8), (cx, hy + 2)], 7, 6, "w")
        pattern(c)
        shade(c)
        g = over(g, part(c))
        c = canvas()
        for s in (-1, 1):
            for bx, ang, n in ((cx + s * 5, -90 + s * 22, 17), (cx + s * 9, -90 + s * 52, 14), (cx + s * 11, -90 + s * 80, 9)):
                crystal(c, bx, hy - 7, ang, n)
        g = over(g, part(c))
        c = canvas()                                                     # the back of the head: plain, with its frills
        oval(c, cx, hy - 3, 11, 8.5, "w")
        for s in (-1, 1):
            for i in range(3):
                poly(c, [(cx + s * 9, hy - 3 + i * 2.5), (cx + s * 16, hy - 5 + i * 3.5), (cx + s * 10, hy - 1 + i * 2.5)], "r")
        for i in (-1, 0, 1):
            put(c, cx + i, hy - 9, "r"); put(c, cx + i, hy - 8, "r")
        shade(c, on="w")
        g = over(g, part(c))
        c = canvas()
        tail(c, (cx, by + 8), 1.4 - coil * 2.8, sway * .6, phase, n=6, step=3.6)
        g = over(g, part(c))
    c = canvas()                                                         # arms and legs
    for s in (-1, 1):
        x0, y0 = cx + s * 7, by + 8
        foot = (x0 + s * (1 + legs * 2), y0 + 8 + legs * 5)
        seg(c, [(x0, y0), foot], 3, 2.2, "m")
        for i in (-2, 0, 2):
            put(c, foot[0] + i, foot[1] + 2.5, "W")
    g = over(g, part(c))
    if not back:
        c = canvas()                                                     # horns, then the face over them
        for s in (-1, 1):
            for bx, ang, n in ((cx + s * 5, -90 + s * 22, 19), (cx + s * 9, -90 + s * 52, 15), (cx + s * 11, -90 + s * 80, 10)):
                crystal(c, bx, hy - 5, ang, n)
        g = over(g, part(c))
        c = canvas()
        oval(c, cx, hy, 12.5, 9.5, "w")
        oval(c, cx, hy + 8, 8.5, 6, "w")
        for y in range(H):
            for x in range(W):
                if c[y][x] == "w" and y > hy + 8:
                    c[y][x] = "v"
        for s in (-1, 1):                                                # cheek frills
            for i in range(3):
                poly(c, [(cx + s * 9, hy + i * 2.5), (cx + s * 16, hy - 2 + i * 3.5), (cx + s * 10, hy + 2 + i * 2.5)], "r")
        for i in (-1, 0, 1):                                             # a mark on the brow
            put(c, cx + i, hy - 6, "r"); put(c, cx + i, hy - 5, "r")
        if jaw:
            oval(c, cx, hy + 12 + jaw * .4, 5, 1.6 + jaw * .6, "q")
            oval(c, cx, hy + 13 + jaw * .7, 3, 1 + jaw * .2, "t", on="q")
            for i in (-3, -1, 1, 3):
                put(c, cx + i - .5, hy + 11 - (jaw > 3), "W")
        else:
            for i in range(-4, 4):
                put(c, cx + i, hy + 11, "o")
            put(c, cx - 3, hy + 12, "W"); put(c, cx + 2, hy + 12, "W")
        put(c, cx - 2, hy + 7, "e"); put(c, cx + 1, hy + 7, "e")
        for s in (-1, 1):
            ex = cx + s * 5 - (.5 if s < 0 else -.5) - .5
            if blink:
                for i in (-1, 0, 1):
                    put(c, ex + i, hy, "v")
            else:
                oval(c, ex + .5, hy, 2.8, 2.5, "y")
                for j in (-1, 0, 1):
                    put(c, ex, hy + j, "e")
                put(c, ex - 1, hy - 1, "Y")
            for i in range(1, 8):                                        # V brows
                put(c, cx + s * i - .5, hy - 2 - i * .45 - (1 if glare else 0), "o")
                if glare:
                    put(c, cx + s * i - .5, hy - 1 - i * .45, "o")
        g = over(g, part(c))
    mouth = (cx, hy + 13)
    return ground(effects(g, fx, mouth, cx, by), cx, 40 - min(16, alt // 2))


def spin(i, **k):
    """One frame of the spin, whatever row it is in: front, side, back, the other side."""
    v = i % 4
    if v == 1:
        return side(**k)
    if v == 3:
        return [r[::-1] for r in side(**k)]
    return front(back=v == 2, **k)


def frames(view):
    F = side if view == "left" else (lambda **k: front(back=view == "up", **k))
    star = lambda *p: ("stars", p)
    return dict(
        idle=[F(flap=i, alt=10, phase=i * .8, blink=i == 6, fx=(star(*TWINKLE[i % 4]),) if i % 2 == 0 else ()) for i in range(8)],
        walk=[F(flap=i, alt=12, lunge=2, phase=i * 1.6, tail_ang=.05, sway=.2, fx=(("trail", i),)) for i in range(8)],
        breath=[F(flap=0, alt=12, rear=4, jaw=1, glare=True, fx=(("gather", 0),)),
                F(flap=7, alt=13, rear=7, jaw=2, glare=True, fx=(("gather", 1),)),
                F(flap=6, alt=13, rear=8, jaw=3, glare=True, fx=(("gather", 2),)),            # held: the warning
                F(flap=3, alt=10, lunge=6, jaw=6, glare=True, legs=.5, fx=(("fire", -1),)),
                F(flap=4, alt=9, lunge=7, jaw=6, glare=True, legs=.5, fx=(("fire", -1),)),
                F(flap=5, alt=10, lunge=6, jaw=5, glare=True, fx=(("fire", -1),)),
                F(flap=6, alt=11, lunge=2, jaw=2), F(flap=7, alt=10)],
        storm=[F(alt=14, arm=-70 if view != "left" else -110, spread=1.2, glare=True, jaw=2, fx=(star((30, 20), (98, 22)),)),
               F(alt=18, arm=-75 if view != "left" else -115, spread=1.25, glare=True, jaw=3, fx=(star((24, 14), (104, 16), (64, 4)),)),
               F(alt=18, arm=-78 if view != "left" else -118, spread=1.3, glare=True, jaw=3, lit=True, fx=(star((20, 30), (108, 30), (64, 6)),))]
              + [spin(i + {"down": 0, "left": 1, "up": 2}[view], flap=i * 2 % 8, alt=18, jaw=4, glare=True, lit=True, spread=1.2,
                      fx=(star((20 + i * 11, 10 + i * 5 % 20), (110 - i * 9, 24)),)) for i in range(8)]
              + [F(flap=2, alt=14, jaw=1), F(flap=4, alt=11)],
        dive=[F(alt=10, arm=-100 if view == "left" else -62, rear=3, glare=True),
              F(alt=8, arm=-120 if view == "left" else -75, spread=.7, rear=4, glare=True, jaw=2),
              F(alt=6, arm=-125 if view == "left" else -80, spread=.6, rear=5, glare=True, jaw=2),     # held: the warning, crouched
              F(alt=12, arm=30 if view == "left" else 28, spread=1.1, glare=True, fx=(star((40, 90), (88, 92)),)),   # up and away
              F(alt=10, arm=-128 if view == "left" else -84, spread=.5, lunge=6, jaw=5, glare=True, legs=1),       # the fall
              F(alt=0, arm=26 if view == "left" else 30, spread=1.3, lunge=4, jaw=6, glare=True, legs=1, fx=(("shards", 0),)),
              F(alt=1, arm=10 if view == "left" else 20, spread=1.2, lunge=2, jaw=4, glare=True, fx=(("shards", 1),)),
              F(flap=6, alt=5, jaw=1, fx=(("shards", 2),)), F(flap=7, alt=9)],
        sweep=[F(flap=0, alt=10, coil=.4, glare=True), F(flap=1, alt=11, coil=.8, glare=True, jaw=2),
               F(flap=1, alt=11, coil=1., glare=True, jaw=2),                                    # held: the tail high
               F(flap=3, alt=9, coil=-.3, jaw=4, glare=True, fx=(("ribbon", (-2.6, -.4)),)),
               F(flap=4, alt=8, coil=-.6, jaw=4, glare=True, fx=(("ribbon", (-1.2, 1.2)),)),
               F(flap=5, alt=9, coil=-.2, jaw=3, fx=(("ribbon", (.4, 2.6)),)), F(flap=6, alt=10, jaw=1), F(flap=7, alt=10)],
        rush=[F(flap=0, alt=10, rear=3, glare=True), F(flap=1, alt=12, rear=6, jaw=3, glare=True, lit=True),
              F(flap=2, alt=13, rear=8, jaw=7, glare=True, lit=True, spread=1.3, fx=(star((20, 20), (108, 24), (64, 4), (40, 8)),)),
              F(flap=3, alt=13, rear=8, jaw=7, glare=True, lit=True, spread=1.3, fx=(star((14, 34), (114, 36), (30, 6), (96, 6)),)),
              F(flap=4, alt=12, rear=6, jaw=5, glare=True, lit=True, fx=(star((24, 12), (104, 14)),)),
              F(flap=5, alt=11, rear=2, jaw=2, glare=True, lit=True)],
    )


TWINKLE = [((18, 30), (104, 50)), ((110, 22), (30, 60)), ((24, 48), (100, 18)), ((114, 40), (14, 22))]
BEAT = 60000 / 156
TEXT = {
    "comet": ("a comet that grew wings: scales of gold, a mane of flame, wings like a sunset",
              "<b>Flare</b>: sparks gather at its jaws, then a cone of fire four tiles long. <b>Ember storm</b>: it climbs, wings "
              "wide, and spins out a ring of fireballs on each of three beats. <b>Meteor</b>: it leaves the sky, its shadow hunts "
              "you, and it lands on the beat in a burst of embers. <b>Comet tail</b>: the burning tail whips round in a ring. "
              "Below half health, <b>supernova</b>: its mane blazes and it attacks twice as often.",
              "a sun scale, a comet feather, an ember heart"),
    "storm": ("a thundercloud with a dragon inside: indigo scales veined with lightning, wings that crackle",
              "<b>Arc</b>: sparks gather at its jaws, then a crackling beam four tiles long. <b>Static storm</b>: it climbs, "
              "wings wide, and spins out a ring of sparks on each of three beats. <b>Thunderfall</b>: it vanishes into the "
              "clouds, its shadow hunts you, and it strikes down on the beat like a bolt. <b>Blade lash</b>: the bladed tail "
              "whips round in a ring of lightning. Below half health, <b>overcharge</b>: it glows white and attacks twice as often.",
              "a storm scale, a charged fin, a bottled bolt"),
    "eclipse": ("a piece of the night sky: violet-black scales with gold runes, wings full of stars, an eclipse on its tail",
                "<b>Void breath</b>: starlight gathers at its jaws, then a cone of dark fire four tiles long. <b>Starfall</b>: it "
                "climbs, wings wide, and spins out a ring of stars on each of three beats. <b>Eclipse</b>: it blots out the sky, "
                "its shadow hunts you, and it falls on the beat in a ring of gold. <b>Orbit</b>: the eclipse on its tail sweeps "
                "round in a ring. Below half health, <b>totality</b>: its runes blaze and it attacks twice as often.",
                "a night scale, a fallen star, the eclipse stone"),
}


def enemy(theme):
    """The drake in one of its looks: the frames are computed with that theme's paint and parts."""
    global TH
    TH = THEMES[theme]
    look, how, drops = TEXT[theme]
    return dict(
        key=TH["key"], name=TH["name"], pal=TH["pal"], role=f"boss to Sugar rush, look {list(THEMES).index(theme) + 1}: {theme}",
        cell=(128, 114), move="fly", theme=theme, look=look,
        ms=dict(idle=[96] * 8, walk=[48] * 8,
                breath=[192, 192, 193, 96, 96, 96, 96, 96], storm=[192, 192, 193] + [96] * 8 + [96, 96],
                dive=[192, 192, 193, 96, 96, 96, 96, 96, 96], sweep=[192, 192, 193, 64, 64, 64, 96, 96],
                rush=[96, 96, 193, 192, 192, 192]),
        where="the high plateau of a far island", when="wakes when the song starts",
        behaviour=f"A great dragon, always in the air and always on the beat. {how}",
        stats=dict(hp=600, breath="30, four tiles ahead", storm="10 a bolt, three rings", dive="40 under it, 15 out to five tiles",
                   sweep="25, five tiles round", speed="flies at twice yours", drops=drops),
        dirs={d: frames(d) for d in ("left", "down", "up")},
    )
