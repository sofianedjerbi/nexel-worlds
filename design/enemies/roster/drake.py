"""The drake: a boss rig for the high-energy track "Sugar rush" (E flat, 156 BPM, a kick on every beat), : Nyxwing, a piece
of the night sky, in three prototypes to choose from: eclipse (gold runes, star wings, a corona behind it), moonveil
(silver, crescent horns, nebula wings, a moon on its tail), abyss (black, magenta cracks, rim-lit wings, a black hole).

A big dragon that never lands. Everything is timed to the song: a wing beat is one musical beat (385 ms), the idle
hover two, each warning a beat and a half, and every strike lands on a beat.
Every frame is computed from parts (far wing, tail, body with its back spines, neck, head and horns, legs, near
wing), the wings from a shoulder angle and three fingers, so the flap is one number per frame. A prototype only changes
the paint (palette, markings, wing membrane), the horns, the spines down its back, the tip of its tail and the halo.
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
    "eclipse": dict(key="nyxwing", name="Nyxwing", proto="Eclipse", spines="gold", tip="orb", wing="stars", scales="runes", horns="crystal",
                    halo=True, pal={
        "o": "1a0f2a", "w": "3d2a66", "W": "6a52a0", "v": "2a1c4a", "r": "ffcf5a", "R": "d9a63a", "m": "6b52a8",
        "M": "4e3a86", "p": "3a2468", "P": "5a3c94", "n": "24163f", "k": "8a64d8", "K": "fff3c0", "b": "ffcf5a", "c": "ffe08a",
        "C": "e0a83a", "y": "fff3c0", "Y": "ffffff", "e": "0b0614", "q": "12091f", "t": "c77dff", "1": "ffcf5a", "2": "fff3c0",
        "3": "c77dff", "4": "7fb8ff", "5": "ff7ac8", "x": "fff3c0aa", "g": "ffcf5a88"}),
    "moonveil": dict(key="nyxwing", name="Nyxwing", proto="Moonveil", spines="fins", tip="moon", wing="nebula", scales="dust", horns="crescent",
                     halo=False, pal={
        "o": "0d1a2a", "w": "8fb4d8", "W": "d8ecff", "v": "5a7fa8", "r": "f4faff", "R": "b0cce8", "m": "c9e4f0",
        "M": "9cc2dc", "p": "4a3f8f", "P": "6fd0dc", "n": "1e1f4f", "k": "b77ad6", "K": "ffffff", "b": "d8ecff", "c": "f4f8ff",
        "C": "a8c4e8", "y": "7ff0ff", "Y": "ffffff", "e": "08101c", "q": "1a1030", "t": "7ff0ff", "1": "7ff0ff", "2": "ffffff",
        "3": "c79bff", "4": "9fd0ff", "5": "ff9fd8", "x": "e8f8ffaa", "g": "7ff0ff88"}),
    "abyss": dict(key="nyxwing", name="Nyxwing", proto="Abyss", spines="fins", tip="hole", wing="rim", scales="bolts", horns="crown",
                  halo=False, pal={
        "o": "05030a", "w": "241a34", "W": "45345e", "v": "130d1e", "r": "ff3fb4", "R": "c02a8a", "m": "35223f",
        "M": "24162c", "p": "160e24", "P": "2c1c44", "n": "0a0612", "k": "3fe8ff", "K": "c8faff", "b": "4a3866", "c": "ff6ad0",
        "C": "b03a9a", "y": "3fe8ff", "Y": "ffffff", "e": "000000", "q": "2a0018", "t": "ff3fb4", "1": "ff3fb4", "2": "ffffff",
        "3": "3fe8ff", "4": "b46aff", "5": "ff9ae0", "x": "ffd0f0aa", "g": "ff3fb488"}),
}
TH = THEMES["eclipse"]
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
    """One of the spines down its back, in the prototype's kind: a fin of glass (its colour is the horns'), a gold thorn."""
    kind = TH["spines"]
    if kind == "fins":
        crystal(c, x, y, -104 + i * 3, r * (2.4 + (.5 if lit else 0)), r * .62)
    else:
        crystal(c, x, y, -96 + i * 2, r * (1.9 + (.6 if lit else 0)), r * .5)
        if lit:
            put(c, x, y - r * 2.4, "Y")


def horn(c, x, y, ang, n):
    """A horn in the prototype's kind: a crystal shard, a crescent that sweeps back, or a crown of short thorns."""
    kind = TH["horns"]
    if kind == "crescent":
        a, pts, (px, py) = math.radians(ang), [(x, y)], (x, y)
        bend = .07 if ang < -90 else -.07
        for i in range(int(n)):
            a += bend
            px, py = px + math.cos(a), py + math.sin(a)
            pts.append((px, py))
        seg(c, pts, 2.6, .5, lambda t: "c" if t < .55 else "C")
    elif kind == "crown":
        crystal(c, x, y, ang, n * .7, 2.2)
        crystal(c, x, y, ang + 24, n * .45, 1.5)
    else:
        crystal(c, x, y, ang, n)


def halo(g, cx, cy, phase):
    """Eclipse only: a corona behind it, a ring of gold with flickering rays, painted where nothing else is."""
    if not TH.get("halo"):
        return g
    c = [list(r) for r in g]
    for i in range(220):
        a = i * math.tau / 220
        for r, ch in ((27, "C"), (28, "c"), (29, "c")):
            put(c, cx + r * math.cos(a), cy + r * .92 * math.sin(a), ch, on=".")
    for k in range(16):
        a = k * math.tau / 16 + phase * .05
        L = 5 + 3 * ((k * 5 + int(phase * 2)) % 3)
        for d in range(L):
            put(c, cx + (31 + d) * math.cos(a), cy + (31 + d) * .92 * math.sin(a), "1" if d < 2 else "g", on=".")
    return ["".join(r) for r in c]


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
                    kind = TH["wing"]
                    if kind == "nebula":                                 # bands of colour, wrist to edge, and a few stars
                        c[y][x] = "P" if r < .3 else "k" if r < .52 else "p" if r < .8 else "n"
                        if (x * 11 + y * 5 + glint) % 47 == 0:
                            c[y][x] = "K"
                    elif kind == "rim":                                  # dark as a hole, lit along its edge
                        c[y][x] = "P" if r < .3 else "k" if r > .86 else "p" if r < .6 else "n"
                        if (x * 7 + y * 13 + glint) % 37 == 0 and r < .8:
                            c[y][x] = "K"
                    else:
                        c[y][x] = "P" if r < .38 else "n" if r > .82 else "p"
                        if (x * 7 + y * 13 + glint) % 23 == 0:
                            c[y][x] = "W" if (x + y) % 3 else "y"
        if TH["wing"] == "stars":                                        # two constellations across the membrane
            for t0, t1 in ((tips[0], tips[1]), (tips[1], tips[2])):
                stars = [(wx + (t0[0] - wx) * f + (t1[0] - t0[0]) * g_, wy + (t0[1] - wy) * f + (t1[1] - t0[1]) * g_)
                         for f, g_ in ((.45, .1), (.62, .3), (.55, .55), (.75, .6))]
                for (ax, ay), (bx, by) in zip(stars, stars[1:]):
                    for i in range(1, 6):
                        put(c, ax + (bx - ax) * i / 6, ay + (by - ay) * i / 6, "k", on="pPn")
                for ax, ay in stars:
                    put(c, ax, ay, "y", on="pPnk")
        for k, (tx, ty) in enumerate(tips):                              # glints on the membrane
            if TH["wing"] == "stars":
                put(c, wx + (tx - wx) * (.5 + .1 * ((k + glint) % 3)), wy + (ty - wy) * (.5 + .1 * ((k + glint) % 3)) + 2, "W", on="pPn")
    if TH["wing"] == "rim" and not far:                                  # the rim glows on the bones too
        seg(c, [(sx, sy), (wx, wy)], 2.4, 1.7, "b")
        for tx, ty in tips:
            seg(c, [(wx, wy), (tx, ty)], 1.2, .55, lambda t: "b" if t < .6 else "k")
        put(c, wx - side * 1, wy - 2, "w"); put(c, wx - side * 2, wy - 2, "w")
        return part(c)
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
            elif kind == "dust" and ((x * 11 + y * 7) % 29 == 0 or (x * 3 + y * 17) % 61 == 0):
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


def core(c, ox, oy, a):
    """The portal core at the end of its tail, in the prototype's kind (an eclipse, a crescent moon, a black hole),
    centred on (ox, oy), a: the tail's heading. The same drawing is the core it drops when it dies (DROP)."""
    tip = TH["tip"]
    if tip == "moon":                                                    # a crescent moon: a disc with a bite out of it
        oval(c, ox, oy, 6, 6, "c")
        oval(c, ox + 2.6 * math.cos(a + 1.2), oy + 2.6 * math.sin(a + 1.2), 4.6, 4.6, ".")
        put(c, ox - 3, oy - 3, "Y")
    elif tip == "hole":                                                  # a black hole: a ring of light round nothing
        oval(c, ox, oy, 8.5, 3, lambda px, py: "k" if (px + py) % 3 else "K")
        oval(c, ox, oy, 4.4, 4.4, "c")
        oval(c, ox, oy, 3.4, 3.4, "e")
        for d in range(-6, 7):
            put(c, ox + d, oy, "K" if abs(d) > 4 else "e")
    else:                                                                # the eclipse: a dark moon over a gold sun
        oval(c, ox, oy, 5, 5, "c")
        oval(c, ox + .6, oy - .6, 3.4, 3.4, "e")
        put(c, ox - 2.6, oy - 2.6, "Y")


def drop_icon():
    """What it leaves where it died: its portal core, as an item, cropped to its outline."""
    c = canvas()
    core(c, W / 2, H / 2, -0.6)
    g = part(c)
    ys = [y for y, r in enumerate(g) if r.strip(".")]
    xs = [x for r in g for x, ch in enumerate(r) if ch != "."]
    return [r[min(xs) - 1:max(xs) + 2] for r in g[min(ys) - 1:max(ys) + 2]]


def tail(c, base, ang, sway=0., phase=0., n=10, step=4.2, curl=1.0):
    """The tail: long, tapering, and the prototype's tip at the end (an eclipse, a crescent moon, a black hole)."""
    pts, (x, y) = [base], base
    a = ang
    for i in range(n + 3):
        a = ang + sway * math.sin(i * .55 + phase) + (.03 - .1 * curl * (i > n)) * i
        x, y = x + step * math.cos(a), y + step * math.sin(a)
        pts.append((x, y))
    seg(c, pts, 5.4, 2.8, "w")
    pattern(c)
    shade(c)
    core(c, x + 2 * math.cos(a), y + 2 * math.sin(a), a)
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
        if kind == "swirl":                                              # the spin: three arcs of light whirling round it
            for arc in range(3):
                a0 = k * math.pi / 4 + arc * math.tau / 3
                for i in range(40):
                    a = a0 + i * .022
                    col = "W" if i > 34 else ACCENT[arc % 5] if i > 14 else "g"
                    put(c, cx + 46 * math.cos(a), cy - 6 + 15 * math.sin(a), col, on=".")
                    if i > 20:
                        put(c, cx + 46 * math.cos(a), cy - 5 + 15 * math.sin(a), col, on=".")
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
        horn(c, bx, by_, ang, n)
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
    return ground(halo(effects(g, fx, mouth, 62, by), 62, by - 14, phase), 64, 52 - min(20, alt // 2))


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
                horn(c, bx, hy - 7, ang, n)
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
                horn(c, bx, hy - 5, ang, n)
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
    return ground(halo(effects(g, fx, mouth, cx, by), cx, by - 14, phase), cx, 40 - min(16, alt // 2))


def squeeze(g, k, cx=64):
    """The frame narrowed about its centre to k of its width: the in-between of a turn."""
    return ["".join(r[round(cx + (x - cx) / k)] if 0 <= round(cx + (x - cx) / k) < W else "." for x in range(W)) for r in g]


def spin(i, **k):
    """One step of the spin, eight to a turn: front, turning, side, turning, back, turning, the other side, turning.
    The in-betweens are the view before narrowed (a body turning edge-on), the whirl painted round it."""
    v = i % 8
    k["fx"] = tuple(k.get("fx", ())) + (("swirl", i),)
    g = (lambda **q: front(**q), side, lambda **q: front(back=True, **q), lambda **q: [r[::-1] for r in side(**q)])[v // 2](**k)
    return squeeze(g, .62) if v % 2 else g


def frames(view, jaws=None):
    """Every animation in one view. jaws, if given, gets each frame's jaw (0: shut), in order: the game opens its
    voice on a frame where the jaw opens."""
    base = side if view == "left" else (lambda **k: front(back=view == "up", **k))

    def F(**k):
        if jaws is not None:
            jaws.append(k.get("jaw", 0))
        return base(**k)

    def turning(i, **k):
        if jaws is not None:
            jaws.append(k.get("jaw", 0))
        return spin(i, **k)
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
              + [turning(i + {"down": 0, "left": 2, "up": 4}[view], flap=i % 8, alt=18, jaw=4, glare=True, lit=True, spread=1.2,
                      fx=(star((20 + i % 8 * 11, 10 + i * 5 % 20), (110 - i % 8 * 9, 24)),)) for i in range(16)]
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
HOW = ("<b>Void breath</b>: starlight gathers at its jaws, then a cone of dark fire four tiles long. <b>Starfall</b>: it "
       "climbs, wings wide, and spins out a ring of stars on each of three beats. <b>Eclipse</b>: it blots out the sky, its "
       "shadow hunts you, and it falls on the beat in a ring of light. <b>Orbit</b>: its tail sweeps round in a ring. Below "
       "half health, <b>totality</b>: its markings blaze and it attacks twice as often.")
TEXT = {
    "eclipse": "a piece of the night sky at the moment of an eclipse: violet-black scales with gold runes, wings full of "
               "constellations, a corona of gold behind it and an eclipse on its tail",
    "moonveil": "the night at full moon: silver scales dusted with light, horns like crescents, wings like a nebula (teal, "
                "orchid, indigo) and a crescent moon on its tail",
    "abyss": "the dark between the stars: black scales cracked with magenta light, a crown of thorns, wings dark as holes "
             "with a cyan rim, and a black hole on its tail",
}


def enemy(theme):
    """The drake in one of its looks: the frames are computed with that theme's paint and parts."""
    global TH
    TH = THEMES[theme]
    jaws = []
    dirs = {"left": frames("left", jaws)} | {d: frames(d) for d in ("down", "up")}
    mouth, k = {}, 0
    for anim, fs in dirs["left"].items():                                # each frame: is its mouth open
        mouth[anim], k = [j > 0 for j in jaws[k:k + len(fs)]], k + len(fs)
    look, how, drops = TEXT[theme], HOW, "a portal core"
    return dict(
        key=TH["key"], name=TH["name"], pal=TH["pal"], role=f"boss to Sugar rush, prototype {list(THEMES).index(theme) + 1}: {TH['proto']}", proto=TH["proto"],
        cell=(128, 114), move="fly", theme=theme, look=look,
        ms=dict(idle=[96] * 8, walk=[48] * 8,
                breath=[192, 192, 193, 96, 96, 96, 96, 96], storm=[192, 192, 193] + [48] * 16 + [96, 96],
                dive=[192, 192, 193, 96, 96, 96, 96, 96, 96], sweep=[192, 192, 193, 64, 64, 64, 96, 96],
                rush=[96, 96, 193, 192, 192, 192]),
        where="the high plateau of a far island", when="wakes when the song starts",
        behaviour=f"A great dragon, always in the air and always on the beat. {how}",
        stats=dict(hp=600, breath="30, four tiles ahead", storm="10 a bolt, three rings", dive="40 under it, 15 out to five tiles",
                   sweep="25, five tiles round", speed="flies at twice yours", drops=drops),
        dirs=dirs, mouth=mouth, drop=dict(name="portal core", icon=drop_icon(),
                                          about="the core at the end of its tail: a piece of the night it came through"),
    )
