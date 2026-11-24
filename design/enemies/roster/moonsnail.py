"""Moonsnail: a snail as big as a sheep, with a pale shell that holds the moonlight. It comes out at night and is slow.

Every frame is computed. The shell is a disc lit from the top left (a dark rim under, a sheen over), with a spiral
wound twice on it and flecks that glow; the body is one long soft foot with a round head, two stalks with a bead of an
eye at each tip, a pink cheek. It does not step, it glides: a ripple runs back along the foot, the head stretches out a
pixel and draws back, and it leaves a wet trail.
  spit   the warning: it rears its head up, stalks back, and its cheeks swell (held); then it spits a glob of slime that
         flies a tile and a half and splats. The splat is a puddle you walk slowly through.
  hide   the stalks pull in, the head slides under the shell, the shell rocks and settles; then it peeks out.
"""
import math

from art import canvas, dot, ell, ground, over, pad, part, rows

PAL = {"o": "4a4168", "b": "a596c4", "B": "85779f", "m": "cdc3e4", "c": "e3e8f8", "l": "f8f9ff", "d": "b2bbe0",
       "D": "8a93c4", "q": "7f87b8", "y": "c9fff0", "e": "2d2848", "w": "ffffff", "x": "f2a7c0",
       "g": "a6f0d6", "G": "6fcfb0", "z": "cfefff70"}
W, H, BASE = 36, 28, 26
LEFT = 10                                           # room in front of it for the spit


def shell(c, cx, cy, r, turn=0.0):
    ell(c, cx, cy, r, r * .95, "D")                    # a dark rim, then the face of the shell over it, then the sheen
    ell(c, cx - .7, cy - .7, r - .8, r * .95 - .8, "d", on="D")
    ell(c, cx - 1.2, cy - 1.3, r - 1.8, r * .95 - 1.8, "c", on="d")
    ell(c, cx - 2.6, cy - 3, r * .35, r * .24, "l", on="c")
    for k in range(150):                               # the spiral: one clean line wound twice to the eye
        a = k * .085
        rr = (r - 2.2) * (1 - a / (4.6 * math.pi))
        dot(c, cx + rr * math.cos(a + turn), cy + rr * .95 * math.sin(a + turn), "q", on="cdlD")
    for a, f in ((.6, .55), (2.4, .7), (4.1, .35), (5.4, .8)):
        dot(c, cx + r * f * math.cos(a + turn * .3), cy + r * f * math.sin(a + turn * .3), "y", on="cdlqD")


def eye_stalks(g, bases, ln, sway, col="B"):
    for s, (bx, by, lean) in enumerate(bases):
        sw = .5 * math.sin(sway + s)
        for k in range(ln):
            dot(g, bx + lean * k * .35 + sw * k / max(1, ln), by - k, col)
        tx, ty = round(bx + lean * ln * .35 + sw), by - ln
        for dx, dy, ch in ((0, 0, "e"), (1, 0, "e"), (0, -1, "e"), (1, -1, "w")):   # a bead with a glint
            dot(g, tx + dx - 1 + (lean > 0), ty + dy, ch)


def side(i=0, tuck=0, rock=0, rear=0, puff=0, spit=None):
    """Facing left. i: the glide phase. tuck 0..4: into the shell. rear 0..2: head raised to spit. spit: glob progress."""
    reach = [0, 0, 1, 1, 1, 0, 0, 0][i % 8] if not (tuck or rear) else 0
    fo = canvas(W, H)
    x0 = 5 - reach + tuck * 3
    for x in range(x0, 31):                            # the foot: low and long, a ripple travelling back along it
        t = (x - x0) / (31 - x0)
        top = BASE - 3 - round(1.6 * math.sin(math.pi * min(1, t * 1.3)) + .8 * math.sin(x * .7 - i * math.pi / 4) * (t > .15))
        for y in range(top, BASE):
            fo[y][x] = "m" if y == top else ("B" if y == BASE - 1 else "b")
    if not tuck:
        hy = BASE - 4.5 - rear * 1.6
        ell(fo, x0 + 3 + rear * .3, hy, 4.2 + puff * .6, 3.7 + puff * .3, "b")
        ell(fo, x0 + 2.4, hy - 1.2, 1.6, .9, "m", on="b")
    head = part(fo)
    sh = canvas(W, H)
    shell(sh, 20 + rock * .5, BASE - 11 + abs(rock) * .3 - [0, 0, 0, 1, 1, 1, 0, 0][i % 8] * (not tuck), 8.5)
    g = [list(r) for r in over(head, part(sh))]
    if tuck < 2:
        hy = round(BASE - 4.5 - rear * 1.6)
        ln = (6 if not tuck else 2) - rear
        eye_stalks(g, ((x0 + 2, hy - 2, -.3 + rear * .6), (x0 + 4, hy - 2, .1 + rear * .6)), ln, i * math.pi / 4)
        dot(g, x0 + 2 + puff, hy + 1, "x")             # a pink cheek, swelling to spit
        if puff:
            dot(g, x0 + 3, hy + 1, "x")
        dot(g, x0 - 1 + rear * 0, hy + 1 + (rear == 0), "e")
    g = rows(g)
    g = pad(g, left=LEFT)
    g = [list(r) for r in g]
    for x in range(30 + LEFT, W + LEFT):              # the wet trail behind
        if (x + i) % 3:
            dot(g, x, BASE, "z")
    if spit is not None:                               # the glob, flying low, then a splat on the ground
        hx, hy = LEFT + x0 - 1, BASE - 5 - rear * 1.6
        if spit < 1:
            gx, gy = hx - spit * 9, hy - math.sin(spit * math.pi) * 3 + spit * 4
            ell(g, gx, gy, 2.6, 2.2, "G")
            ell(g, gx - .3, gy - .3, 1.8, 1.5, "g", on="G")
            dot(g, gx - 1, gy - 1, "w")
            for k in range(3):                         # drips trailing behind it
                dot(g, gx + 3 + k * 1.5, gy + .5 - k * .4, "g", on=".")
        else:
            sp = spit - 1
            ell(g, LEFT + x0 - 10, BASE - .5, 3.5 + sp * 2, 1.2, "G", on=".")
            ell(g, LEFT + x0 - 10, BASE - .7, 2.6 + sp * 2, .7, "g")
            for k in range(6):                         # droplets thrown out by the splat
                dx = (k - 2.5) * (2 + sp * 2)
                dot(g, LEFT + x0 - 10 + dx, BASE - 2 - (k % 2) - (1 - sp) * 2, "g", on=".")
    return ground(rows(g), 18 + LEFT, 26)


def facing(i=0, back=False, tuck=0, rock=0, rear=0, puff=0, spit=None):
    cx = W // 2
    fo = canvas(W, H)
    w = 6 + [0, 0, 1, 1, 1, 0, 0, 0][i % 8]
    if tuck < 3:
        ell(fo, cx, BASE - 1, w, 3, "b", clip=(0, BASE))
        ell(fo, cx, BASE - 2.4, w - 1, .8, "m", on="b")
    if not back and tuck < 3:
        ell(fo, cx, BASE - 4 + tuck - rear, 4.2 + puff * .4, 3.6, "b")
        ell(fo, cx - 1, BASE - 5.4 + tuck - rear, 2, 1, "m", on="b")
    sh = canvas(W, H)
    shell(sh, cx + rock, BASE - 13 + abs(rock) * .3 + (2 if back else 0), 7.8, turn=1.4 if back else 2.6)
    body = part(fo)
    g = [list(r) for r in (over(body, part(sh)) if back or tuck else over(part(sh), body))]
    if not back and tuck < 2:
        hy = BASE - 4 - rear
        eye_stalks(g, ((cx - 2, hy - 3, -.8), (cx + 2, hy - 3, .8)), 4 - rear, i * math.pi / 4)
        dot(g, cx - 1, hy + 1, "e")
        dot(g, cx, hy + 1, "e")
        for x in (cx - 3 - puff, cx + 2 + puff):
            dot(g, x, hy + .5, "x")
    if spit is not None and not back:                  # coming straight at you: the glob grows and lands in front
        if spit < 1:
            r = 1.8 + spit * 1.8
            ell(g, cx, BASE - 4 - math.sin(spit * math.pi) * 3 + spit * 3, r, r * .9, "G")
            ell(g, cx - .3, BASE - 4.3 - math.sin(spit * math.pi) * 3 + spit * 3, r - .7, r * .9 - .7, "g", on="G")
            dot(g, cx - .5, BASE - 5 - math.sin(spit * math.pi) * 3 + spit * 3, "w")
        else:
            ell(g, cx, BASE - .5, 5 + (spit - 1) * 3, 1.2, "G", on=".")
            ell(g, cx, BASE - .7, 4 + (spit - 1) * 3, .7, "g", on="G.")
    g = rows(g)
    g = pad(g, left=LEFT // 2, right=LEFT - LEFT // 2)
    g = [list(r) for r in g]
    if back:
        for x in range(cx - 2, cx + 3):
            if (x + i) % 3:
                dot(g, x + LEFT // 2, BASE, "z")
    return ground(rows(g), cx + LEFT // 2, 18)


def frames(d):
    f = side if d == "left" else (lambda **k: facing(back=d == "up", **k))
    idle = [f(i=0)] * 3 + [f(i=1), f(i=2), f(i=2), f(i=1), f(i=0)]
    walk = [f(i=i) for i in range(8)]
    spit = [f(rear=1), f(rear=2, puff=1), f(rear=2, puff=1), f(rear=1, spit=.3), f(rear=0, spit=.7), f(spit=1),
            f(spit=1.5), f(i=1, spit=1.8)]
    hide = [f(i=0, tuck=1), f(i=0, tuck=2), f(i=0, tuck=4), f(i=0, tuck=4, rock=-1), f(i=0, tuck=4, rock=1),
            f(i=0, tuck=4), f(i=0, tuck=4), f(i=0, tuck=2), f(i=0, tuck=1), f(i=0)]
    return dict(idle=idle, walk=walk, spit=spit, hide=hide)


ENEMY = dict(
    key="moonsnail", name="Moonsnail", pal=PAL, role="night grazer", cell=(48, 32), move="glide", side="night",
    ms=dict(idle=[900, 300, 300, 260, 400, 260, 260, 300], walk=150, spit=[220, 260, 220, 70, 90, 160, 200, 300],
            hide=[120, 140, 200, 120, 120, 160, 1200, 200, 220, 300]),
    beats=dict(spit="wwwssrrr", hide="sssssssrrr"), hit=dict(spit="slow"),
    where="damp meadows, gardens, the edge of ponds", when="night; back under a stone by dawn",
    behaviour="Slow and in no hurry: it heads for whatever you planted and eats it, a crop a minute. Come near and it "
              "<b>spits</b>: it rears up and its cheeks swell (plenty of time to step aside), then a glob of slime splats "
              "where you stood; walking through the puddle you are half speed. Strike it and it <b>hides</b>: in its shell "
              "nothing hurts it, so wait till it peeks out. Beaten, it leaves its shell, a lamp that glows faintly forever.",
    stats=dict(hp=14, damage="0 (slime slows)", speed="very slow", drops="moon shell"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
