"""Brittlewing: the sugar drake, a boss made for the high-energy track "Sugar rush" (E flat, 156 BPM, a kick on every beat).

A dragon made of candy, flying: a candy-cane body and tail (the tail ends in a cane's crook), wings of spun sugar,
horns of rock-candy crystal, a row of sugared gumdrops down its back, a mint belly. It never touches the ground.
Everything is timed to the song: a wing beat is one musical beat (385 ms), the idle hover two, each warning a beat
and a half, and every strike lands on a beat.

Every frame is computed from parts (far wing, tail, body with its gumdrops, neck, head and crystals, legs, near wing),
the wings from a shoulder angle and three fingers, so the flap is one number per frame.
Attacks (the warning first, held, then the strike):
  breath   it rears back and sugar sparks gather at its jaws, then it breathes a cone of pink fire four tiles ahead
  storm    it climbs and throws its wings wide, then spins and fires rings of sprinkles, one ring on each beat
  dive     wings straight up, it shoots off the top of the screen, its shadow hunts you, and it crashes down on the beat
  sweep    the tail coils high over its back, then whips round in a rainbow ribbon
  rush     (below half health) a roar, every gumdrop lights up: it gets faster and attacks on half beats
"""
import math

from art import ground, over, part

PAL = {"o": "5a2f4e", "w": "fff3e8", "v": "e9cfd3", "r": "f0607a", "R": "c8455f", "m": "9ee6c8", "M": "6cc3a4",
       "p": "ffb8d9", "P": "ffe2f0", "n": "e590bd", "b": "d14f7f", "c": "a8dcff", "C": "6fb0ee", "W": "ffffff",
       "y": "ffe066", "Y": "fffbd0", "e": "3b1f36", "q": "9c2f5a", "t": "ff86ad", "1": "ff6b8b", "2": "ffd166",
       "3": "7ee0b8", "4": "7fb8ff", "5": "c49bff", "x": "ffffffaa", "g": "ffd16699"}
W, H = 128, 112
SPRINKLE = "12345"


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
    """A shard of rock candy from (x, y), n long, at angle ang (degrees, 0 = +x, -90 = up): two tones and a glint."""
    a = math.radians(ang)
    dx, dy, px, py = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    tip = (x + dx * n, y + dy * n)
    poly(c, [(x + px * w, y + py * w), tip, (x - px * w, y - py * w), (x - dx * 1.5, y - dy * 1.5)], "c")
    poly(c, [(x, y), tip, (x - px * w, y - py * w), (x - dx * 1.5, y - dy * 1.5)], "C")
    for i in range(1, int(n * .45)):
        put(c, x + dx * i + px * .8, y + dy * i + py * .8, "W")


def gumdrop(c, x, y, r, col):
    """A sugared gumdrop: a dome in one of the sprinkle colours, white sugar grains on it."""
    oval(c, x, y - r * .5, r, r * 1.05, col, on=None)
    for i, j in ((-.4, -.6), (.3, -1.0), (.5, -.2)):
        put(c, x + i * r, y - r * .5 + j * r * .7, "W")


def wing(sx, sy, arm, side=1, far=False, spread=1.0, glint=0):
    """A wing of spun sugar from the shoulder (sx, sy). arm: the arm's angle in degrees (-90 up, 0 out, 90 down),
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
    if not far:                                                          # the pane by the leading edge is thinner, lighter
        poly(c, [(sx, sy), (wx, wy), (wx + (tips[0][0] - wx) * .7, wy + (tips[0][1] - wy) * .7),
                 (wx + (tips[1][0] - wx) * .35, wy + (tips[1][1] - wy) * .35)], "P", on="p")
        for k, (tx, ty) in enumerate(tips):                              # glints of sugar on the membrane
            put(c, wx + (tx - wx) * (.45 + .1 * ((k + glint) % 3)), wy + (ty - wy) * (.45 + .1 * ((k + glint) % 3)) + 2, "W", on="pP")
    seg(c, [(sx, sy), (wx, wy)], 2.4, 1.7, "R" if far else "b")
    for tx, ty in tips:
        seg(c, [(wx, wy), (tx, ty)], 1.2, .55, "R" if far else "b")
    put(c, wx - side * 1, wy - 2, "w"); put(c, wx - side * 2, wy - 2, "w")  # the thumb claw
    return part(c)


def stripes(c, x0, x1, on="w", step=9, width=3.2, slope=.8):
    """Candy-cane stripes, diagonal, across what is already painted `on`."""
    for y in range(H):
        for x in range(int(x0), int(x1)):
            if 0 <= x < W and c[y][x] in on and (x + y * slope) % step < width:
                c[y][x] = "r"


def tail(c, base, ang, sway=0., phase=0., n=10, step=4.2, curl=1.0):
    """The candy-cane tail: rings of red and white, ending in the cane's crook."""
    pts, (x, y) = [base], base
    a = ang
    for i in range(n):
        a = ang + sway * math.sin(i * .55 + phase) + .03 * i
        x, y = x + step * math.cos(a), y + step * math.sin(a)
        pts.append((x, y))
    for i in range(7):                                                   # the crook
        a -= .62 * curl
        x, y = x + 2.4 * math.cos(a), y + 2.4 * math.sin(a)
        pts.append((x, y))
    seg(c, pts, 5.2, 2.4, lambda t: "r" if int(t * 18) % 2 else "w")
    return pts


def effects(g, fx, mouth, cx, cy):
    """Marks painted on empty pixels: sparks gathering at the jaws, the first gout of fire, a rainbow ribbon, shards,
    sparkle stars, a sugar trail."""
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
            for band, col in enumerate(SPRINKLE):
                for i in range(160):
                    a = a0 + (a1 - a0) * i / 159
                    put(c, cx + (40 + band) * math.cos(a), cy + 10 + (16 + band * .5) * math.sin(a), col, on=".")
        if kind == "shards":                                             # candy shards flung from the crash
            for i in range(18):
                a = math.pi + i * math.pi / 17
                r = 12 + k * 10 + (i % 3) * 4
                x, y = cx + r * 1.7 * math.cos(a), H - 6 + r * .6 * math.sin(a) - k * 3
                col = SPRINKLE[i % 5]
                poly(c, [(x - 2, y + 1), (x, y - 3), (x + 2, y + 1)], col, on=".")
                put(c, x, y - 1, "W", on=col)
        if kind == "stars":                                              # four-point sparkle stars
            for (sx, sy) in k:
                put(c, sx, sy, "W", on=".")
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    put(c, sx + d[0], sy + d[1], "2", on=".")
                for d in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                    put(c, sx + d[0], sy + d[1], "g", on=".")
        if kind == "trail":                                              # sugar dust left behind when it flies fast
            for i in range(9):
                x = cx + 34 + i * 6 + (k * 3) % 6
                y = cy - 4 + math.sin(i * 1.7 + k) * 9
                put(c, x, y, SPRINKLE[(i + k) % 5] if i % 2 else "W", on=".")
    return ["".join(r) for r in c]


FLAP_SIDE = [-108, -92, -60, -18, 22, 8, -40, -84]       # one wing beat in eight frames: up, the down-stroke, the lift
FLAP_FRONT = [-58, -46, -24, 4, 26, 16, -12, -40]
LIFT = [0, -1, -1, 0, 1, 2, 2, 1]                        # the body rises on the down-stroke


def side(flap=0, alt=0, rear=0, lunge=0, jaw=0, glare=False, blink=False, spread=1., tail_ang=.25, sway=.12, phase=0.,
         coil=0., lit=False, legs=0, fx=(), arm=None, far_arm=None):
    """Facing left. flap: frame of the wing beat. alt: height (px). rear: head pulled back; lunge: thrown forward.
    coil: the tail raised over the back (0-1). lit: the gumdrops glow (rush). legs: claws thrust down (0-1)."""
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
    c = canvas()                                                         # the body, a candy cane, a mint belly
    oval(c, 66, by, 20, 12, "w")
    oval(c, 52, by - 3, 11, 11, "w")
    oval(c, 84, by + 1, 10, 9, "w")
    stripes(c, 40, 96)
    for y in range(H):
        for x in range(W):
            if c[y][x] in "wr" and y > by + 4 + (x - 66) ** 2 / 160:
                c[y][x] = "m" if y < by + 9 else "M"
    for i in range(6):                                                   # sugared gumdrops down the back
        x = 50 + i * 7.5
        top = next(y for y in range(H) if c[y][round(x)] != ".")
        gumdrop(c, x, top + 1.5, 4.4 - abs(i - 2) * .3, ("2" if lit else SPRINKLE[i % 3]) if not lit else SPRINKLE[i % 5])
    g = over(g, part(c))
    hx, hy = 28 + rear * 1.0 - lunge * 1.2, by - 30 - rear * .6 + lunge * .9
    c = canvas()                                                         # the neck, in rings
    seg(c, [(54, by - 6), (46, by - 14), (40 + rear * .4 - lunge * .5, by - 22 + lunge * .3), (hx + 6, hy + 2)], 7, 5.4,
        lambda t: "r" if int(t * 7) % 2 else "w")
    g = over(g, part(c))
    c = canvas()                                                         # rock-candy horns, behind the head
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
        oval(c, hx - 1, hy - 1, 3, 2.4, "y")
        for j in (-2, -1, 0):
            put(c, hx - 1, hy + j, "e")
        put(c, hx - 2, hy - 2, "Y")
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
        oval(c, cx, by - 12, 9, 9, "w")                                  # the neck going away
        stripes(c, cx - 20, cx + 20)
    else:
        stripes(c, cx - 20, cx + 20)
        oval(c, cx, by + 3, 8, 9, lambda x, y: "m" if y < by + 7 else "M", on="wr")
    for i in range(7):                                                   # gumdrops: down the spine from behind, a crown of them in front
        if back:
            x, y = cx, by - 18 + i * 4.6
            gumdrop(c, x, y, 3.3 - i * .15, SPRINKLE[i % (5 if lit else 3)])
        else:
            a = math.pi + .5 + i * (math.pi - 1) / 6
            gumdrop(c, cx + 15 * math.cos(a), by - 6 + 9 * math.sin(a), 4, SPRINKLE[i % (5 if lit else 3)])
    g = over(g, part(c))
    if back:
        c = canvas()
        for s in (-1, 1):
            for bx, ang, n in ((cx + s * 4, -90 + s * 22, 12), (cx + s * 8, -90 + s * 52, 10)):
                crystal(c, bx, hy - 4, ang, n)
        g = over(g, part(c))
        c = canvas()
        oval(c, cx, hy, 9.5, 7.5, "w")
        stripes(c, cx - 12, cx + 12, step=8)
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
        for i in (-1, 0, 1):                                             # a stripe of candy on the brow
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
ENEMY = dict(
    key="brittlewing", name="Brittlewing", pal=PAL, role="boss, to the track Sugar rush", cell=(128, 114), move="fly",
    ms=dict(idle=[96] * 8, walk=[48] * 8,
            breath=[192, 192, 193, 96, 96, 96, 96, 96], storm=[192, 192, 193] + [48] * 8 + [96, 96],
            dive=[192, 192, 193, 96, 96, 96, 96, 96, 96], sweep=[192, 192, 193, 64, 64, 64, 96, 96],
            rush=[96, 96, 193, 192, 192, 192]),
    where="the sugar fields of a far island, where the cane grows", when="wakes when the cane is harvested",
    behaviour="A dragon of candy, always in the air and always moving to the beat of its song. "
              "<b>Breath</b>: it rears back while sparks gather at its jaws, then breathes pink sugar fire four tiles ahead. "
              "<b>Storm</b>: it climbs with its wings thrown wide, then spins and fires a ring of sprinkles on every beat: "
              "find the gaps. <b>Dive</b>: wings straight up, it leaves the screen; its shadow hunts you; it crashes down on "
              "the beat and flings candy shards. <b>Sweep</b>: the tail coils high, then whips round in a rainbow ribbon. "
              "Below half health it <b>rushes</b>: every gumdrop lights up and it attacks on half beats.",
    stats=dict(hp=600, breath="30, four tiles ahead", storm="10 a sprinkle, three rings", dive="40 under it, 15 from the shards",
               sweep="25, three tiles round", speed="flies at twice yours", drops="a rock-candy crystal, spun sugar, a sweet tooth"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
