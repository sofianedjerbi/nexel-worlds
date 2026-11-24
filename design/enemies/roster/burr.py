"""Burr: a hedgehog as big as a sheepdog, and as loyal. It keeps your chickens and your garden, and stands in front of you.

Every frame is computed from a few parts: a round coat, a fan of quills along its back (each one a short line out from
the coat, pale at the tip), a cream face with a pointed snout, four stubby feet.
  idle     a breath, the nose twitching, a blink
  walk     a busy waddle: the body bobs on each step, the quills sway a pixel behind
  curl     it tucks its face in and is a ball of quills (held): nothing gets past it, and anything that runs into it hurts
  bristle  the warning is a hunch and a shiver of the quills; then every quill stands out at once and what is close is
           thrown back a tile
"""
import math

from art import canvas, dot, ell, ground, over, part, rows

PAL = {"o": "4d3024", "c": "a8744f", "C": "c08a5e", "q": "6e4630", "Q": "f1dcb0", "f": "f7e4c2", "F": "e3c79c",
       "n": "3b2620", "e": "2e1f1c", "w": "ffffff", "p": "f3a7a0", "k": "7a5038", "z": "ffffffb0"}
W, H, BASE = 36, 30, 28


def quills(c, cx, cy, rx, ry, a0, a1, n, length, shake=0, sway=0.0):
    """A fan of quills out of the coat's edge between angles a0..a1 (degrees, 0 = right, 90 = up)."""
    for k in range(n):
        for row in (0, 1):                                 # two rows, the second between and shorter
            t = (k + .5 * row) / max(1, n - 1)
            if t > 1:
                continue
            a = math.radians(a0 + (a1 - a0) * t) + sway * .12
            bx, by = cx + rx * math.cos(a), cy - ry * math.sin(a)
            nx, ny = math.cos(a) / rx, -math.sin(a) / ry
            d = math.hypot(nx, ny)
            nx, ny = nx / d, ny / d
            L = length - row * 1.2 + (shake * ((k % 2) * 2 - 1) * .5)
            steps = max(1, round(L * 1.6))
            for s in range(-2, steps + 1):
                f = s / steps * L
                dot(c, bx + nx * f, by + ny * f, "Q" if s >= steps - 0 and L > 1.5 else "q")


def ball(body, cx, cy, rx, ry, spin):
    """Curled up: the coat is all quill, a pattern of short strokes that turns as it rolls."""
    for y in range(len(body)):
        for x in range(len(body[0])):
            if body[y][x] in "cC" and ((x + y * 2 + spin * 2) % 5 == 0) and ((x - spin) % 3 != 2):
                body[y][x] = "q"
                if y + 1 < len(body) and body[y + 1][x] in "cC":
                    body[y + 1][x] = "Q"


def side(step=None, bob=0, blink=False, sniff=0, curl=0.0, spin=0, bristle=0.0, shake=0, squint=False):
    cx, cy = 18, BASE - 8 + bob + round(curl * 1.5)
    rx, ry = 9.5 + bristle * .6 - curl * 2, 6.5 + bristle * .4 - curl * .2
    q = canvas(W, H)
    if curl >= 1:
        quills(q, cx + shake, cy, rx, ry + .5, spin * 25, 360 + spin * 25, 17, 2.8 + bristle * 2, shake)
    else:
        quills(q, cx + shake, cy, rx, ry, -25, 150 + curl * 40, 12, 3 + bristle * 2.2, shake, sway=-bob)
    body = canvas(W, H)
    ell(body, cx + shake, cy, rx, ry, "c", clip=(0, BASE - 1))
    ell(body, cx + 1 + shake, cy - 2, rx - 3, ry - 3, "C", on="c")
    if curl >= 1:
        ball(body, cx, cy, rx, ry, spin)
    if curl < 1:                                       # the face: cream, snout to the left, an ear, a pink cheek
        fx = cx - 6.5 + curl * 3
        ell(body, fx, cy + 1.5, 4.6 - curl * 2, 4 - curl * 1.5, "f")
        ell(body, fx - 4 + curl * 2, cy + 2.8, 2.4, 1.7, "f")
        ell(body, fx + 1, cy + 4.6, 4, 1.2, "F", on="f")
        ell(body, fx + 2.6, cy - 3, 1.4, 1.4, "f")
    out = part(q, "q")
    out = [r.replace("o", "q") for r in out]
    out = over(out, part(body))
    g = [list(r) for r in out]
    if curl < 1:
        fx = cx - 6.5 + curl * 3
        dot(g, fx - 6.3 + curl * 2 - sniff, cy + 2.2, "n")             # the nose, twitching
        dot(g, fx - 6.3 + curl * 2 - sniff, cy + 3.2, "n")
        ex, ey = round(fx - 1), round(cy)
        if blink or squint:
            g[ey + 1][ex] = g[ey + 1][ex + 1] = "e"
        else:
            g[ey][ex] = g[ey + 1][ex] = "e"
            g[ey][ex + 1] = "w"
            g[ey + 1][ex + 1] = "e"
        dot(g, fx + .5, cy + 3, "p", on="fF")
        dot(g, fx + 1.5, cy + 3, "p", on="fF")
    feet = canvas(W, H)
    if curl < 1:                                       # four stubby feet, two near, two far; one pair lifted in turn
        for k, x in enumerate((cx - 6, cx - 3, cx + 3, cx + 6)):
            up = 1 if step is not None and (k + step) % 2 == 0 else 0
            for y in range(BASE - 3, BASE - up):
                dot(feet, x, y, "k" if k % 2 else "n")
                dot(feet, x + 1, y, "k" if k % 2 else "n")
    g = over(part(feet), rows(g))
    if bristle >= 1.5:                                 # the burst: streaks thrown out round it
        g = [list(r) for r in g]
        for k in range(12):
            a = k * math.pi / 6 + .2
            for r in (14, 15):
                dot(g, cx + r * math.cos(a), min(BASE - 1, cy + r * .7 * math.sin(a)), "z", on=".")
        g = rows(g)
    return ground(g, cx, 18 - round(curl * 2))


def facing(back=False, step=None, bob=0, blink=False, curl=0.0, spin=0, bristle=0.0, shake=0, squint=False):
    cx, cy = 18, BASE - 8 + bob + round(curl * 1.5)
    rx, ry = 9 + bristle * .6 - curl * 1.5, 7 + bristle * .4
    q = canvas(W, H)
    if curl >= 1 or back:
        quills(q, cx + shake, cy, rx, ry, -20 + spin * 25, 200 + spin * 25, 15, 2.8 + bristle * 2, shake)
    else:
        quills(q, cx + shake, cy - 1, rx, ry - 1, -15, 195, 15, 2.6 + bristle * 2.2, shake, sway=bob)
    body = canvas(W, H)
    ell(body, cx + shake, cy, rx, ry, "c", clip=(0, BASE - 1))
    ell(body, cx - 2 + shake, cy - 3, rx - 4, ry - 4, "C", on="c")
    if curl >= 1:
        ball(body, cx, cy, rx, ry, spin)
    if not back and curl < 1:
        ell(body, cx + shake, cy + 2.6 + curl, 5.6 - curl * 2.5, 4.2 - curl * 2, "f")
        ell(body, cx + shake, cy + 4.2 + curl, 2.1, 1.4, "F", on="f")
        for s in (-1, 1):
            ell(body, cx + s * 5.4 + shake, cy - 3.2, 1.5, 1.5, "f")
    if back and curl < 1:
        ell(body, cx, cy + ry - 1, 1.2, 1, "C")
    out = [r.replace("o", "q") for r in part(q, "q")]
    out = over(out, part(body))
    g = [list(r) for r in out]
    if not back and curl < 1:
        ey = round(cy + 1.5 + curl)
        for x in (cx - 3 + shake, cx + 2 + shake):
            if blink or squint:
                g[ey + 1][x] = g[ey + 1][x + 1] = "e"
            else:
                g[ey][x] = g[ey + 1][x] = g[ey + 1][x + 1] = "e"
                g[ey][x + 1] = "w"
        g[ey + 3][cx - 1 + shake] = g[ey + 3][cx + shake] = "n"
        for x in (cx - 5 + shake, cx + 4 + shake):
            dot(g, x, ey + 3, "p", on="fF")
    feet = canvas(W, H)
    if curl < 1:
        for k, x in enumerate((cx - 5, cx + 3)):
            up = 1 if step is not None and (k + step) % 2 == 0 else 0
            for y in range(BASE - 3, BASE - up):
                dot(feet, x, y, "n")
                dot(feet, x + 1, y, "n")
    g = over(part(feet), rows(g))
    if bristle >= 1.5:
        g = [list(r) for r in g]
        for k in range(12):
            a = k * math.pi / 6 + .2
            for r in (14, 15):
                dot(g, cx + r * math.cos(a), min(BASE - 1, cy + r * .7 * math.sin(a)), "z", on=".")
        g = rows(g)
    return ground(g, cx, 18 - round(curl * 2))


def frames(d):
    f = side if d == "left" else (lambda **k: facing(back=d == "up", **{a: b for a, b in k.items() if a != "sniff"}))
    idle = [f(), f(), f(bob=1), f(bob=1, sniff=1), f(), f(blink=True), f(bob=1), f(bob=1, sniff=1)]
    walk = [f(step=i % 2, bob=0 if i % 2 else 1) for i in range(8)]
    curl = [f(curl=.5), f(curl=1, spin=0), f(curl=1, spin=1, shake=1), f(curl=1, spin=2), f(curl=1, spin=3, shake=-1),
            f(curl=1, spin=4), f(curl=.5), f()]
    bristle = [f(bob=1, squint=True), f(bob=1, squint=True, shake=1), f(bob=1, squint=True, shake=-1),
               f(bristle=2, squint=True), f(bristle=1.6), f(bristle=.8), f(bristle=.3), f()]
    return dict(idle=idle, walk=walk, curl=curl, bristle=bristle)


ENEMY = dict(
    key="burr", name="Burr", pal=PAL, role="ally", cell=(40, 32), move="waddle", side="ally",
    ms=dict(idle=[300, 260, 260, 140, 300, 160, 260, 140], walk=95, curl=[120, 160, 140, 140, 140, 160, 160, 200],
            bristle=[220, 160, 160, 90, 160, 140, 140, 200]),
    beats=dict(curl="wssssssr", bristle="wwwssrrr"), hit=dict(curl="block", bristle="knock"),
    where="tamed with a bowl of berries left out three nights running", when="always; it sleeps in the day by the coop",
    behaviour="A guard that waddles. It keeps to your chickens and your garden, and when something comes for you it "
              "<b>bristles</b>: it hunches and its quills shiver (the warning, for anything with sense), then they all stand out "
              "and whatever is close is thrown back a tile. Hard pressed it <b>curls</b> into a ball of quills in the way: "
              "nothing gets past it, and what runs into it is hurt. It never hurts you or your animals.",
    stats=dict(hp=40, damage="2 and knocked back", speed="your walk", eats="berries, beetles"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
