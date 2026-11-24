"""Glintbeetle: a gold beetle the size of a chicken, with one curved horn. Seen on a sunny afternoon, once in a long while.

Every frame is computed. The shell is a dome lit from the top left (a dark rim, a gold face, a sheen that slides across
it as it moves, a glint); the head is small and round with two shiny eyes and a horn with a pale tip. Six short legs walk
in two tripods, so the body never dips.
  dazzle  the warning: it tips its shell to the sun and a glint gathers on it, growing (held); then a flash of rays bursts
          off it. Caught looking, your view is white for a second. Turn away (or face it from behind) during the glint.
  fly     the wing cases split and lift, clear wings blur out, it rises and hovers, then drops and folds. It flies from
          you, never at you: the chase is the game.
"""
import math

from art import canvas, dot, ell, ground, over, part, rows

PAL = {"o": "6e4424", "g": "f0bd45", "y": "ffe382", "h": "fff8d8", "d": "c98a2a", "D": "9a6420", "k": "6b4a36",
       "K": "2e1f18", "T": "f0d49a", "w": "ffffff", "z": "f6f4ffd8", "Z": "f6f4ff90", "r": "fffbe6", "R": "fff3b0b0"}
W, H, BASE = 30, 28, 26


def star(g, x, y, n, ch="h", soft="R"):
    """A glint: a cross of light n pixels long each way, the ends soft."""
    dot(g, x, y, "w")
    for k in range(1, n + 1):
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            dot(g, x + dx, y + dy, ch if k < n else soft)


def rays(g, cx, cy, r0, r1):
    for k in range(12):
        a = k * math.pi / 6 + .26
        for t in range(int(r0), int(r1)):
            dot(g, cx + t * math.cos(a), cy + t * .8 * math.sin(a), "r" if t < (r0 + r1) / 2 else "R", on=".")


def sheen(sh, cx, cy, rx, ry, slide):
    ell(sh, cx - 2 + slide, cy - ry * .45, rx * .45, ry * .3, "y", on="g")
    ell(sh, cx - 2.5 + slide, cy - ry * .55, rx * .18, ry * .12, "h", on="y")


def legs_side(c, xs, y, phase, far):
    for k, x in enumerate(xs):
        up = 1 if phase is not None and (k + phase) % 2 == 0 else 0
        step = (1 if (k + (phase or 0)) % 2 == 0 else -1) if phase is not None else 0
        col = "K" if far else "k"
        dot(c, x, y, col)
        dot(c, x + step, y + 1 - up, col)
        dot(c, x + step, y + 2 - up, col)
        dot(c, x + step - 1, y + 3 - up, "K")


def side(phase=None, lift=0, open_=0, i=0, glint=0, tilt=0, flash=0):
    cy = BASE - 7 - lift
    out = rows(canvas(W, H))
    lg = canvas(W, H)
    legs_side(lg, (10, 15, 20), cy + 3, (phase if not lift else None), True)
    out = over(out, rows(lg))
    if open_:
        wg = canvas(W, H)
        for k in range(3):
            ell(wg, 20 + k * .5, cy - 4 - (i % 2) * 2 + k, 6.5, 2.2, "z" if k else "Z")
        out = over(out, rows(wg))
    b = canvas(W, H)
    ell(b, 16, cy + 1, 8, 5, "d", clip=(0, cy + 4))
    for x in range(W):
        for y in (cy + 3,):
            if b[y][x] == "d":
                b[y][x] = "D"
    hd = canvas(W, H)                                   # the head, round, and its horn curving up, a pale tip
    ell(hd, 7.5, cy + 2, 3.2, 2.8, "k")
    for k, (dx, dy) in enumerate(((-1, 0), (-2, -1), (-3, -2), (-3, -3), (-3, -4), (-2, -5))):
        ch = "T" if k >= 4 else "k"
        dot(hd, 6 + dx, cy + dy, ch)
        if k < 4:
            dot(hd, 7 + dx, cy + dy, ch)
    sh = canvas(W, H)                                  # the wing case: dark rim, gold, a sheen that slides, tipped by tilt
    sx, syy = 17 + open_, cy - open_ * 1.5 - tilt
    ell(sh, sx, syy, 8, 5, "D", clip=(0, cy + 3 - open_))
    ell(sh, sx - .6, syy - .6, 7.3, 4.4, "g", on="D")
    sheen(sh, sx, syy, 8, 5, [0, 1, 2, 1, 0, -1, -2, -1][i % 8] * .6)
    for y in range(round(syy - 5), round(syy + 4)):    # the seam between the two cases
        if 0 <= y < H and sh[y][round(sx + 3)] in "gyD":
            sh[y][round(sx + 3)] = "d"
    out = over(out, part(hd))
    out = over(out, part(b))
    out = over(out, part(sh))
    g = [list(r) for r in out]
    ex, ey = 7, cy + 1                                 # the eye: shiny black with a glint
    g[ey][ex] = "K"
    g[ey][ex - 1] = "K"
    g[ey + 1][ex] = "K"
    g[ey + 1][ex - 1] = "K"
    g[ey][ex - 1] = "w"
    lg2 = canvas(W, H)
    legs_side(lg2, (9, 14, 19), cy + 4, ((phase + 1) % 2 if phase is not None and not lift else None), False)
    g = over(rows(g), rows(lg2))
    g = [list(r) for r in g]
    if glint:
        star(g, 13, cy - 4 - tilt, glint)
    if flash:
        rays(g, 15, cy - 1, 6 + flash * 2, 10 + flash * 3)
        if flash == 1:
            star(g, 13, cy - 4 - tilt, 4)
    return ground(rows(g), 15, 16 - lift)


def facing(back=False, phase=None, lift=0, open_=0, i=0, glint=0, tilt=0, flash=0):
    cx, cy = 15, BASE - 7 - lift
    lg = canvas(W, H)
    for k, y in enumerate((cy - 1, cy + 2, cy + 5)):  # three legs a side, out from under the shell, then down
        for s in (-1, 1):
            up = 1 if phase is not None and not lift and (k + phase + (s > 0)) % 2 == 0 else 0
            x = cx + s * (5 + (k == 1)) - (s < 0)
            for j in range(3):
                dot(lg, x + s * j, y - up * (j == 2), "k")
            dot(lg, x + s * 3, y + 1 - up, "k")
            dot(lg, x + s * 3, y + 2 - up, "K")
    out = rows(lg)
    if open_:
        wg = canvas(W, H)
        for s in (-1, 1):
            ell(wg, cx + s * (7 + (i % 2)), cy - 2, 4, 3 - (i % 2), "z")
        out = over(out, rows(wg))
    sh = canvas(W, H)
    for s in (-1, 1):                                  # two cases meeting at the seam, apart when open
        ell(sh, cx + s * (2.2 + open_ * 1.2), cy - open_ - tilt, 4.4, 5.6, "D")
        ell(sh, cx + s * (2.2 + open_ * 1.2) - .5, cy - open_ - tilt - .6, 3.8, 5, "g", on="D")
    sheen(sh, cx - 1.5 - open_ * 1.2, cy - open_ - tilt, 4, 5.6, [0, 1, 2, 1, 0, -1, -2, -1][i % 8] * .4)
    for y in range(H):
        if sh[y][cx] in "gyhD":
            sh[y][cx] = "d"
    out = over(out, part(sh))
    hd = canvas(W, H)
    if not back:
        ell(hd, cx, cy + 5.5, 3.4, 2.4, "k")
        for k in range(5):
            dot(hd, cx - .5, cy + 3 - k, "T" if k > 3 else "k")
            dot(hd, cx + .5 - (k > 2), cy + 3 - k, "T" if k > 3 else "k")
        out = over(out, part(hd))
        g = [list(r) for r in out]
        for x in (cx - 3, cx + 1):
            g[cy + 5][x] = "w"
            g[cy + 5][x + 1] = "K"
            g[cy + 6][x] = g[cy + 6][x + 1] = "K"
    else:
        ell(hd, cx, cy - 6, 2.2, 1.6, "k")
        g = [list(r) for r in over(part(hd), out)]
    if glint and not back:
        star(g, cx - 3, cy - 3 - tilt, glint)
    if flash:
        rays(g, cx, cy, 6 + flash * 2, 10 + flash * 3)
    return ground(rows(g), cx, 16 - lift)


def frames(d):
    f = side if d == "left" else (lambda **k: facing(back=d == "up", **k))
    idle = [f(i=0)] * 3 + [f(i=1), f(i=2), f(phase=0, i=2), f(i=1), f(i=0)]
    walk = [f(phase=p, i=i) for i, p in enumerate((0, 0, None, None, 1, 1, None, None))]
    dazzle = [f(tilt=1, i=2), f(tilt=2, glint=1, i=2), f(tilt=2, glint=2, i=2), f(tilt=2, glint=3, i=2),
              f(tilt=2, flash=1, i=2), f(tilt=1, flash=2), f(flash=3), f()]
    fly = [f(open_=1), f(open_=2, i=0), f(open_=2, lift=2, i=1), f(open_=2, lift=4, i=0), f(open_=2, lift=5, i=1),
           f(open_=2, lift=4, i=0), f(open_=2, lift=5, i=1), f(open_=2, lift=2, i=0), f(open_=1), f()]
    return dict(idle=idle, walk=walk, dazzle=dazzle, fly=fly)


ENEMY = dict(
    key="glintbeetle", name="Glintbeetle", pal=PAL, role="rare, day", cell=(32, 32), move="scuttle", side="day",
    ms=dict(idle=[700, 400, 400, 300, 300, 120, 400, 300], walk=70, dazzle=[200, 220, 220, 260, 70, 120, 160, 240],
            fly=[160, 120, 70, 70, 70, 70, 70, 90, 140, 200]),
    beats=dict(dazzle="wwwwsssr", fly="wsssssssrr"), hit=dict(dazzle="blind"),
    where="sunny meadows and flower fields", when="day, clear weather; one in a long while",
    behaviour="Something glints in the grass. It is quick and shy: come within three tiles and it <b>flies</b> off, five or six "
              "tiles, lands and scuttles on. Cornered, it <b>dazzles</b>: it tips its shell to the sun and a glint gathers "
              "(look away now), then a flash of light, and your view is white for a second while it gets away. Catch it "
              "(from behind, or with a sweet fruit dropped and waited by) and it leaves a gold scale and flies off unhurt.",
    stats=dict(hp=2, damage="0 (blinds)", speed="quick, flies when chased", drops="gold scale"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
